"""
Unit Tests for PDF Cleaner Pipeline
===================================
Tests Unicode NFKC, Persian letter/digit conversion, article syntax standardization,
and running header removal.
"""

import pytest
from scripts.pdf_to_clean_text import (
    normalize_unicode,
    strip_bidi_controls,
    normalize_digits_and_letters,
    standardize_line_header,
    clean_raw_page_lines,
)


class TestPDFCleaner:
    """Test PDF text cleaner components."""

    def test_nfkc_arabic_presentation_forms(self):
        arabic_forms = "ﻣﺎده ﺗﺠﺎرت ﺷﺮﮐﺖ"
        normalized = normalize_unicode(arabic_forms)
        assert normalized == "ماده تجارت شرکت"

    def test_bidi_control_stripping(self):
        text_with_bidi = "\u202bماده ۱\u202c\u200e - متن قانون"
        clean = strip_bidi_controls(text_with_bidi)
        assert "\u202b" not in clean
        assert "\u202c" not in clean
        assert "\u200e" not in clean

    def test_digit_and_letter_normalization(self):
        raw = "ماده 123 و شركت سهامي"
        norm = normalize_digits_and_letters(raw)
        assert "۱۲۳" in norm
        assert "شرکت" in norm
        assert "سهامی" in norm

    def test_article_syntax_standardization(self):
        cases = [
            ("ماده -۱مقررات این قانون", "ماده ۱ - مقررات این قانون"),
            ("ماده« -۷تعهد یکطرفه»", "ماده ۷ - «تعهد یکطرفه»"),
            ("ماده ۱ـ تاجر کسی است", "ماده ۱ - تاجر کسی است"),
            ("ماده ۱۳۴۳-کلیه قوانین", "ماده ۱۳۴۳ - کلیه قوانین"),
        ]
        for inp, expected in cases:
            res = standardize_line_header(inp)
            assert res.startswith(expected[:8]), f"Failed for {inp}: got {res}"

    def test_page_header_removal(self):
        raw_page = "\fقانون تجارت\n۱۲\nماده ۱ - متن اول\n\fقانون تجارت\n۱۳\nماده ۲ - متن دوم\n"
        lines = clean_raw_page_lines(raw_page)
        assert not any("قانون تجارت" == l.strip() for l in lines)
        assert not any(l.strip() in ["۱۲", "۱۳"] for l in lines)
        assert any("ماده ۱ - متن اول" in l for l in lines)
        assert any("ماده ۲ - متن دوم" in l for l in lines)
