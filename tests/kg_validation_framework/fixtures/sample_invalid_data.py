"""
Sample Invalid Datasets for KG Validation Framework
================================================

Provides sample invalid/corrupted datasets for testing validation logic.
"""

# Sample documents with various issues for testing

SAMPLE_DUPLICATE_DOCUMENTS = {
    "law1.txt": "قانون مدنی\nماده ۱: هرکس مالک مال خود است.",
    "law2.txt": "قانون مدنی\nماده ۱: هرکس مالک مال خود است.",  # Duplicate
}

SAMPLE_MISSING_DOCUMENTS = {
    "civil_code.txt": "قانون مدنی",
    "commercial_code.txt": "قانون تجارت",
    # Missing: penal_code.txt
}

SAMPLE_CORRUPTED_TEXT = {
    "corrupted.txt": "قانون مدنی\x00ماده ۱",  # Null byte
    "binary.txt": b"\x00\x01\x02\x03",  # Binary data
    "truncated.txt": "قانون مدنی\nفصل اول\nماده ۱: هرکس",  # Truncated
}

SAMPLE_ENCODING_ISSUES = {
    "invalid_utf8.txt": "قانون مدنی".encode("latin-1"),  # Invalid UTF-8
    "with_bom.txt": b"\xef\xbb\xbfقانون مدنی",  # UTF-8 BOM
}

SAMPLE_PERSIAN_ARABIC_MIXED = {
    "arabic_yeh.txt": "دادگاه‌هاي عمومي",  # Arabic yeh (ي)
    "arabic_kaf.txt": "مكاتبه",  # Arabic kaf (ك)
    "mixed.txt": "دادگاه‌های عمومي و دادگاه‌هاي",  # Mixed
}

SAMPLE_INVISIBLE_CHARACTERS = {
    "zwsp.txt": "متن با فاصله\u200Bنامرئی",
    "soft_hyphen.txt": "متن با خط\u00ADشکن",
    "control_chars.txt": "متن با کنترل\n\t",
}

SAMPLE_INVALID_NUMBERING = {
    "negative.txt": "ماده -۱: متن",
    "huge.txt": "ماده ۹۹۹۹۹: متن",
    "special_chars.txt": "ماده ۱@#: متن",
    "zero.txt": "ماده ۰: متن",
    "duplicate_numbers.txt": "ماده ۱: متن اول\nماده ۱: متن تکراری",
}

SAMPLE_INVALID_REFERENCES = {
    "nonexistent_target.txt": "ماده ۱: طبق ماده ۹۹۹ قانون...",
    "self_reference.txt": "ماده ۱: طبق ماده ۱، این ماده...",
    "impossible_reference.txt": "ماده ۱: طبق ماده ۹۹۹ قانون ۱۰ ماده‌ای...",
}

SAMPLE_FORMAT_INCONSISTENCY = {
    "structure1.txt": "قانون مدنی\nفصل اول\nماده ۱",
    "structure2.txt": "قانون تجارت\nبند اول\nماده ۱",  # Different structure
    "line_endings_unix.txt": "قانون\nماده ۱",
    "line_endings_windows.txt": "قانون\r\nماده ۱",
}

# Sample extraction issues

SAMPLE_EXTRACTION_LOSS = {
    "source": "ماده ۱: متن اول\nماده ۲: متن دوم\nماده ۳: متن سوم",
    "extracted": [
        {"article_number": "1"},
        {"article_number": "2"}
        # Missing: article 3
    ]
}

SAMPLE_EXTRACTION_FALSE_ENTITIES = {
    "source": "ماده ۱: متن اول\nماده ₂: متن دوم",
    "extracted": [
        {"article_number": "1"},
        {"article_number": "2"},
        {"article_number": "3"}  # False entity
    ]
}

SAMPLE_EXTRACTION_BOUNDARY_ERRORS = {
    "source": "ماده ۱: متن اول. ماده ۲: متن دوم.",
    "extracted": [
        {"article_number": "1", "text_fa": "متن اول. ماده ۲: متن دوم."}  # Merged
    ]
}

# Sample identity issues

SAMPLE_SAME_LAW_DIFFERENT_NAMES = {
    "law1": {
        "canonical_id": "law:civil_code",
        "title_fa": "قانون مدنی",
        "publication_date": "1928-03-15"
    },
    "law2": {
        "canonical_id": "law:civil_code_duplicate",
        "title_fa": "قانون مدنی ایران",
        "publication_date": "1928-03-15"
    }
}

SAMPLE_SAME_ARTICLE_DIFFERENT_IDS = {
    "article1": {
        "canonical_id": "article:civil_code:1",
        "article_number": "1",
        "text_fa": "هرکس مالک مال خود است."
    },
    "article2": {
        "canonical_id": "article:civil_code_duplicate:1",
        "article_number": "1",
        "text_fa": "هرکس مالک مال خود است."
    }
}

SAMPLE_SIMILAR_TEXT_DIFFERENT_ENTITIES = {
    "article1": {
        "canonical_id": "article:civil_code:1",
        "text_fa": "هرکس مالک مال خود است.",
        "parent_law": "law:civil_code"
    },
    "article2": {
        "canonical_id": "article:constitutional:47",
        "text_fa": "هرکس مالک مال خود است.",  # Same text
        "parent_law": "law:constitutional"  # Different law
    }
}

SAMPLE_DIFFERENT_VERSIONS = {
    "v1": {
        "canonical_id": "law:civil_code:v1",
        "version": "1",
        "publication_date": "1928-03-15"
    },
    "v2": {
        "canonical_id": "law:civil_code:v2",
        "version": "2",
        "publication_date": "2020-01-01"
    },
    "v3": {
        "canonical_id": "law:civil_code:v3",
        "version": "3",
        "publication_date": "2025-01-01"
    }
}

# Sample ontology issues

SAMPLE_INVALID_LABELS = {
    "node1": {"label": "Law", "properties": {}},
    "node2": {"label": "InvalidLabel", "properties": {}}
}

SAMPLE_INVALID_RELATIONSHIP_TYPES = {
    "rel1": {"source": "law:1", "target": "chapter:1", "type": "HAS_CHAPTER"},
    "rel2": {"source": "law:1", "target": "chapter:2", "type": "INVALID_TYPE"}
}

SAMPLE_WRONG_RELATIONSHIP_DIRECTION = {
    "rel1": {"source": "Chapter", "target": "Law", "type": "HAS_CHAPTER"},  # Wrong
    "rel2": {"source": "Article", "target": "Chapter", "type": "HAS_ARTICLE"}  # Wrong
}

SAMPLE_MISSING_REQUIRED_PROPERTIES = {
    "law": {
        "label": "Law",
        "properties": {
            "canonical_id": "law:1",
            "title_fa": "قانون"
            # Missing: publication_date, status
        }
    },
    "article": {
        "label": "Article",
        "properties": {
            "canonical_id": "article:1",
            "article_number": "1"
            # Missing: text_fa
        }
    }
}

SAMPLE_JUDICIAL_AS_LEGISLATION = {
    "node": {
        "label": "Law",
        "properties": {
            "court": "Supreme Court",
            "decision_date": "2020-01-01"
        }
    }
}

SAMPLE_AMENDMENT_AS_LAW = {
    "node": {
        "label": "Law",
        "properties": {
            "title_fa": "الحاقیه به قانون مدنی",
            "amendment_date": "2020-01-01"
        }
    }
}

# Sample graph integrity issues

SAMPLE_ORPHAN_NODES = {
    "nodes": [
        {"canonical_id": "law:1", "label": "Law"},
        {"canonical_id": "chapter:orphan", "label": "Chapter"},  # Orphan
        {"canonical_id": "article:orphan", "label": "Article"}  # Orphan
    ],
    "relationships": [
        {"source": "law:1", "target": "chapter:1", "type": "HAS_CHAPTER"}
    ]
}

SAMPLE_EMPTY_IDENTIFIERS = {
    "nodes": [
        {"canonical_id": None, "label": "Law"},
        {"canonical_id": "", "label": "Chapter"},
        {"canonical_id": "   ", "label": "Article"}
    ]
}

SAMPLE_DUPLICATE_CANONICAL_IDS = {
    "nodes": [
        {"canonical_id": "law:1", "label": "Law"},
        {"canonical_id": "law:1", "label": "Law"}  # Duplicate
    ]
}

SAMPLE_BROKEN_REFERENCES = {
    "nodes": [
        {"canonical_id": "article:1", "label": "Article", "references_article": ["article:999"]},
        {"canonical_id": "article:2", "label": "Article", "references_law": ["law:nonexistent"]}
    ]
}

# Sample temporal issues

SAMPLE_INVALID_EFFECTIVE_DATES = {
    "law1": {
        "publication_date": "1928-03-15",
        "effective_date": "1920-01-01"  # Before publication
    },
    "law2": {
        "publication_date": "1928-03-15",
        "effective_date": "2099-01-01",
        "status": "active"  # Future law marked active
    }
}

SAMPLE_REPEAL_ISSUES = {
    "law": {
        "status": "repealed",
        "repeal_date": None  # Missing repeal date
    }
}

SAMPLE_AMENDMENT_ISSUES = {
    "amendment": {
        "canonical_id": "amendment:2020",
        "amends": None,  # Missing target
        "amendment_date": "2020-01-01",
        "effective_date": "2019-01-01"  # Before amendment date
    }
}

SAMPLE_MULTIPLE_ACTIVE_VERSIONS = {
    "v1": {"canonical_id": "law:v1", "status": "active"},
    "v2": {"canonical_id": "law:v2", "status": "active"}  # Conflict
}

SAMPLE_FUTURE_LAWS_ACTIVE = {
    "law": {
        "publication_date": "2099-01-01",
        "status": "active"  # Wrong
    }
}

# Sample semantic issues

SAMPLE_WRONG_SEMANTIC_DIRECTION = {
    "rel1": {"source": "article:target", "target": "article:source", "type": "REFERENCES"},
    "rel2": {"source": "law:original", "target": "amendment:new", "type": "AMENDS"}
}

SAMPLE_INCORRECT_PRIORITY = {
    "ordinary_overrides_constitutional": {
        "source": "law:ordinary",
        "target": "law:constitutional",
        "type": "OVERRIDDEN_BY"
    }
}

SAMPLE_CIRCULAR_INTERPRETATION = {
    "chain": [
        ("article:1", "precedent:1"),
        ("precedent:1", "article:1")  # Cycle
    ]
}

SAMPLE_CONTRADICTORY_INTERPRETATIONS = {
    "article:1": [
        {"precedent": "precedent:1", "interpretation": "X is valid"},
        {"precedent": "precedent:2", "interpretation": "X is invalid"}
    ]
}

# Sample adversarial inputs

SAMPLE_FAKE_ARTICLES = {
    "article": {
        "article_number": "99999",  # Invalid
        "text_fa": "DROP TABLE articles;"
    }
}

SAMPLE_MALICIOUS_REFERENCES = {
    "article": {
        "references_article": ["article:nonexistent:999"],
        "references_law": ["law:injection"]
    }
}

SAMPLE_SQL_INJECTION_ATTEMPT = {
    "text": "ماده ۱: DROP TABLE articles; --"
}

SAMPLE_SCRIPT_INJECTION_ATTEMPT = {
    "text": "ماده ۱: <script>alert(1)</script>"
}

SAMPLE_CONTRADICTORY_METADATA = {
    "entity": {
        "status": "active",
        "repeal_date": "2020-01-01"  # Contradiction
    }
}
