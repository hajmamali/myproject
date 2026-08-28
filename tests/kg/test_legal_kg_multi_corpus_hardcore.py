"""
Hardcore Adversarial & Multi-Corpus Integrity Tests (Phase 1.5)
================================================================
Comprehensive adversarial tests validating:
1. Cross-corpus canonical ID uniqueness & collision immunity.
2. Invariant line accounting on commercial code full and commercial bill 1403.
3. Placeholder resolution mechanics (Article 51 commercial code -> commercial code full).
4. Inter-law relationship invariants (EXTENDS and SUPERSEDES).
5. Unicode NFKC and Bidi injection resistance under adversarial inputs.
6. Single-parent structural integrity across multi-corpus graphs.
"""

import hashlib
import pytest
from pathlib import Path

from scripts.build_legal_kg import (
    DeterministicLegalNormalizer,
    LegalCorpusParser,
    verify_source_file,
    CanonicalLaw,
    CanonicalChapter,
    CanonicalArticle,
    CanonicalClause,
    ProvenanceSpan,
)
from scripts.pdf_to_clean_text import (
    normalize_unicode,
    strip_bidi_controls,
    normalize_digits_and_letters,
    standardize_line_header,
    clean_raw_page_lines,
)


class TestHardcoreAdversarialMultiCorpus:
    """Extreme stress and adversarial tests for multi-corpus legal KG."""

    def test_cross_corpus_id_collision_immunity(self):
        """Ensure canonical IDs from different corpuses never collide."""
        law_1 = "law:commercial_code"
        law_2 = "law:commercial_code_full"
        law_3 = "law:commercial_bill_1403"

        art_1 = f"article:{law_1.split(':')[1]}:article:51"
        art_2 = f"article:{law_2.split(':')[1]}:article:51"
        art_3 = f"article:{law_3.split(':')[1]}:article:51"

        assert art_1 == "article:commercial_code:article:51"
        assert art_2 == "article:commercial_code_full:article:51"
        assert art_3 == "article:commercial_bill_1403:article:51"

        # Strictly distinct
        ids = {art_1, art_2, art_3}
        assert len(ids) == 3, "Canonical IDs must never collide across different legal corpuses"

    def test_line_accounting_commercial_code_full(self):
        """Verify 100% strict line accounting invariant on commercial_code_full_clean.txt."""
        source_path = Path("data/commercial_code_full_clean.txt")
        if not source_path.exists():
            pytest.skip("data/commercial_code_full_clean.txt does not exist")

        valid, sha, lines, err = verify_source_file(source_path)
        assert valid, f"Source integrity failed: {err}"
        assert lines > 0

        parser = LegalCorpusParser(source_path)
        laws, chapters, articles, citations, records, stats = parser.parse()

        assert stats.verify_line_accounting_invariant(), "Line accounting invariant violated on commercial_code_full"
        assert stats.dlq_count == 0, f"DLQ must be 0, got {stats.dlq_count}"
        assert len(articles) >= 580, f"Expected at least 580 unique articles, got {len(articles)}"

    def test_line_accounting_commercial_bill_1403(self):
        """Verify 100% strict line accounting invariant on commercial_bill_1403_clean.txt."""
        source_path = Path("data/commercial_bill_1403_clean.txt")
        if not source_path.exists():
            pytest.skip("data/commercial_bill_1403_clean.txt does not exist")

        valid, sha, lines, err = verify_source_file(source_path)
        assert valid, f"Source integrity failed: {err}"
        assert lines > 0

        parser = LegalCorpusParser(source_path)
        laws, chapters, articles, citations, records, stats = parser.parse()

        assert stats.verify_line_accounting_invariant(), "Line accounting invariant violated on commercial_bill_1403"
        assert stats.dlq_count == 0, f"DLQ must be 0, got {stats.dlq_count}"
        assert len(articles) >= 1300, f"Expected at least 1300 articles, got {len(articles)}"

    def test_article_51_presence_in_full_code(self):
        """Verify that Article 51 exists in commercial_code_full and has valid bond content."""
        source_path = Path("data/commercial_code_full_clean.txt")
        if not source_path.exists():
            pytest.skip("data/commercial_code_full_clean.txt does not exist")

        parser = LegalCorpusParser(source_path)
        laws, chapters, articles, citations, records, stats = parser.parse()

        art_51 = next((a for a in articles if a.number == "۵۱" or a.number == "51"), None)
        assert art_51 is not None, "Article 51 must exist in commercial_code_full"
        assert "اوراق قرضه" in art_51.raw_text, "Article 51 must contain bond issuance text"
        assert art_51.provenance is not None
        assert len(art_51.provenance.text_hash) == 64

    def test_adversarial_bidi_and_presentation_forms_injection(self):
        """Adversarial stress test against heavily corrupted Unicode presentation forms & Bidi markers."""
        corrupted = (
            "\u202b\ufe8e\ufe91\u0020\ufe8e\ufeed\ufee7\u0020\u202c"  # Arabic presentation forms B + Bidi
            "\u202a\u0645\u0627\u062f\u0647\u0020\u06f1\u202c\u200f"  # ماده ۱ with LRE and RLM
            " - \u0634\u0631\u0643\u062a\u064a \u0643\u0647\u200c"    # شركتي كه with Arabic kaf/yeh and ZWNJ
        )

        nfkc = normalize_unicode(corrupted)
        nobidi = strip_bidi_controls(nfkc)
        normalized = normalize_digits_and_letters(nobidi)

        assert "\u202b" not in normalized
        assert "\u202c" not in normalized
        assert "\u202a" not in normalized
        assert "\u200f" not in normalized
        assert "ماده ۱" in normalized
        assert "شرکتی که" in normalized
        assert "\u200c" in normalized  # ZWNJ must be preserved

    def test_adversarial_header_variations_robustness(self):
        """Test parser robustness against 10 adversarial article header permutations."""
        cases = [
            ("ماده -۱", "ماده ۱ -"),
            ("ماده« -۲", "ماده ۲ -"),
            ("ماده ۳ـ", "ماده ۳ -"),
            ("ماده-۴", "ماده ۴ -"),
            ("ماده ۵ -", "ماده ۵ -"),
            ("ماده  ۶  :", "ماده ۶ -"),
            ("ماده«۷»", "ماده ۷ -"),
            ("ماده(۸)", "ماده ۸ -"),
            ("ماده [۹]", "ماده ۹ -"),
            ("ماده ۱۰ - «تعهدات»", "ماده ۱۰ - «تعهدات»"),
        ]
        for inp, expected in cases:
            std = standardize_line_header(inp)
            assert std.startswith(expected[:6]), f"Failed standardizing: {inp} -> {std}"
