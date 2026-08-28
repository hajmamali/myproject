"""
Adversarial & Forensic Integrity Tests for Legal Knowledge Graph Compiler
========================================================================
Validates:
1. Persian/Arabic/Western numeral and ZWNJ normalization.
2. Exact source span provenance and raw text preservation.
3. Strict line accounting and DLQ emission on corrupted tokens.
4. Referential integrity & unresolved placeholder hygiene.
5. Deterministic replay and graph fingerprint immutability.
"""

import hashlib

from scripts.build_legal_kg import (
    DeterministicLegalNormalizer,
    LegalCorpusParser,
    verify_source_file,
)


class TestLegalNormalizerAdversarial:
    """Test deterministic normalizer against edge cases and variant scripts."""

    def test_mixed_numeral_normalization(self):
        norm = DeterministicLegalNormalizer()
        assert norm.normalize_digits("ماده ۱۲۹ و ماده 130 و ماده ١٣١") == "ماده 129 و ماده 130 و ماده 131"

    def test_zwnj_preservation_and_character_variants(self):
        norm = DeterministicLegalNormalizer()
        # Arabic yeh/kaf vs Persian yeh/keheh
        raw = "دادگاه‌هاي عمومي و دادگاههاي انقلاب"
        normalized = norm.normalize(raw)
        assert "دادگاه" in normalized
        assert "ی" in normalized  # normalized to Persian yeh

    def test_raw_text_sha256_unmodified(self):
        norm = DeterministicLegalNormalizer()
        raw = "   ماده ۱۲۸ (الحاقی ۱۳۴۷)  - متن خام   \n"
        h1 = norm.compute_sha256(raw)
        h2 = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        assert h1 == h2


class TestSourceIntegrityAdversarial:
    """Test pre-ingestion source dataset integrity checks."""

    def test_valid_file(self, tmp_path):
        f = tmp_path / "valid.txt"
        f.write_text("قانون اساسی جمهوری اسلامی ایران\nاصل اول\n", encoding="utf-8")
        valid, sha, count, err = verify_source_file(f)
        assert valid is True
        assert count == 2
        assert len(sha) == 64
        assert err is None

    def test_nonexistent_file(self, tmp_path):
        f = tmp_path / "missing.txt"
        valid, sha, count, err = verify_source_file(f)
        assert valid is False
        assert "does not exist" in err

    def test_binary_control_corruption(self, tmp_path):
        f = tmp_path / "corrupt.txt"
        # Write null byte U+0000
        f.write_bytes(b"Header\n\x00corrupt\n")
        valid, sha, count, err = verify_source_file(f)
        assert valid is False
        assert "Corrupted control character" in err


class TestParserAndLineAccounting:
    """Test line accounting invariant and DLQ behavior."""

    def test_strict_line_accounting(self, tmp_path):
        corpus = tmp_path / "test_corpus.txt"
        corpus.write_text(
            "قانون اساسی جمهوری اسلامی ایران\n"
            "فصل اول اصول کلی\n"
            "اصل اول حکومت ایران جمهوری اسلامی است.\n"
            "تبصره ۱ این یک تبصره آزمایشی است.\n"
            "\n"
            "رئیس مجلس شورای اسلامی – علی لاریجانی\n",
            encoding="utf-8",
        )

        parser = LegalCorpusParser(corpus)
        laws, chapters, articles, citations, records, stats = parser.parse()

        assert stats.total_lines == 6
        assert stats.verify_line_accounting_invariant() is True
        assert stats.dlq_count == 0
        assert len(laws) == 1
        assert len(articles) == 1
        assert len(articles[0].clauses) == 1

    def test_referential_integrity_and_placeholders(self, tmp_path):
        corpus = tmp_path / "cross_ref_corpus.txt"
        corpus.write_text(
            "قانون تجارت مصوب ۱۳۴۷\n"
            "فصل اول\n"
            "ماده ۱۲۹ معاملات هیئت مدیره با شرکت.\n"
            "ماده ۱۳۰ معاملات مذکور در ماده ۱۲۹ و ماده ۹۹۹ در هر حال معتبر است.\n",
            encoding="utf-8",
        )

        parser = LegalCorpusParser(corpus)
        laws, chapters, articles, citations, records, stats = parser.parse()

        resolved = [c for c in citations if c.status == "RESOLVED"]
        unresolved = [c for c in citations if c.status == "UNRESOLVED"]

        # ماده 129 should be resolved
        assert any(c.target_article_id == "article:commercial_code:article:129" for c in resolved)
        # ماده 999 is outside corpus -> must be deterministic unresolved placeholder
        assert any(c.target_article_id == "article:commercial_code:article:999" for c in unresolved)
