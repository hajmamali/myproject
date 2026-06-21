"""
Example: Import Iranian Laws
============================

This script demonstrates how to import major Iranian laws into the knowledge graph.
Imports:
- قانون مدنی (Civil Code) - 1,335 articles
- قانون مجازات اسلامی (Islamic Penal Code) - 729 articles  
- قانون آیین دادرسی مدنی (Civil Procedure Code) - 515 articles
- قانون آیین دادرسی کیفری (Criminal Procedure Code) - 588 articles
"""
from typing import Any, List

import logging
from datetime import date
from mahoun.graph.neo4j.connection import get_connection
from mahoun.graph.importers.law_importer import LawImporter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Sample law data structures
# In production, these would be loaded from actual law databases or files

CIVIL_CODE_SAMPLE = {
    "name": "قانون مدنی",
    "full_name": "قانون مدنی مصوب 1307",
    "year": 1307,
    "category": "مدنی",
    "approval_date": date(1928, 5, 8),  # Approximate Gregorian date
    "articles": [
        {
            "number": 1,
            "content": "در امور مدنی در صورتی که قانون حکمی نداشته باشد باید طبق منابع معتبر اسلامی یا فتاوی معتبر شرعی حکم نمود.",
            "has_note": False,
            "has_clause": False,
        },
        {
            "number": 2,
            "content": "در صورتی که در منابع مذکور در ماده قبل حکمی یافت نشود قاضی باید بر طبق منابع معتبر اسلامی حکم نماید.",
            "has_note": False,
            "has_clause": False,
        },
        {
            "number": 3,
            "content": "اشخاص حقیقی و حقوقی در حدود قانون دارای شخصیت حقوقی می‌باشند.",
            "has_note": False,
            "has_clause": False,
        },
        # Add more articles as needed...
    ],
}

PENAL_CODE_SAMPLE = {
    "name": "قانون مجازات اسلامی",
    "full_name": "قانون مجازات اسلامی مصوب 1392",
    "year": 1392,
    "category": "کیفری",
    "approval_date": date(2013, 5, 1),
    "articles": [
        {
            "number": 1,
            "content": "مجازات‌ها به شرح زیر تقسیم می‌شوند: حدود، قصاص، دیات، تعزیرات، مجازات‌های بازدارنده.",
            "has_note": False,
            "has_clause": True,
            "clauses": [
                {"number": 1, "content": "حدود"},
                {"number": 2, "content": "قصاص"},
                {"number": 3, "content": "دیات"},
                {"number": 4, "content": "تعزیرات"},
                {"number": 5, "content": "مجازات‌های بازدارنده"},
            ],
        },
        {
            "number": 2,
            "content": "حد مجازاتی است که نوع و میزان آن در شرع مقدس تعیین شده است.",
            "has_note": False,
            "has_clause": False,
        },
        # Add more articles as needed...
    ],
}

CIVIL_PROCEDURE_CODE_SAMPLE = {
    "name": "قانون آیین دادرسی مدنی",
    "full_name": "قانون آیین دادرسی دادگاه‌های عمومی و انقلاب در امور مدنی مصوب 1379",
    "year": 1379,
    "category": "آیین دادرسی",
    "approval_date": date(2000, 7, 21),
    "articles": [
        {
            "number": 1,
            "content": "دادگاه‌های عمومی و انقلاب در امور مدنی به شرح زیر تشکیل می‌شوند.",
            "has_note": False,
            "has_clause": True,
            "clauses": [
                {"number": 1, "content": "دادگاه عمومی حقوقی"},
                {"number": 2, "content": "دادگاه خانواده"},
                {"number": 3, "content": "دادگاه اطفال"},
            ],
        },
        {
            "number": 2,
            "content": "صلاحیت دادگاه‌ها در رسیدگی به دعاوی بر حسب موضوع و مکان تعیین می‌شود.",
            "has_note": False,
            "has_clause": False,
        },
        # Add more articles as needed...
    ],
}

CRIMINAL_PROCEDURE_CODE_SAMPLE = {
    "name": "قانون آیین دادرسی کیفری",
    "full_name": "قانون آیین دادرسی کیفری مصوب 1392",
    "year": 1392,
    "category": "آیین دادرسی",
    "approval_date": date(2013, 2, 1),
    "articles": [
        {
            "number": 1,
            "content": "تعقیب و رسیدگی به جرایم و اجرای مجازات‌ها طبق مقررات این قانون انجام می‌شود.",
            "has_note": False,
            "has_clause": False,
        },
        {
            "number": 2,
            "content": "هیچ کس را نمی‌توان تحت تعقیب، بازداشت یا زندانی کرد مگر به حکم قانون.",
            "has_note": False,
            "has_clause": False,
        },
        # Add more articles as needed...
    ],
}


def import_single_law(importer: LawImporter, law_data: dict) -> str:
    """
    Import a single law
    
    Args:
        importer: LawImporter instance
        law_data: Law data dictionary
    
    Returns:
        Law ID
    """
    logger.info(f"Importing {law_data['name']}...")
    
    law_id = importer.import_law(
        name=law_data["name"],
        full_name=law_data["full_name"],
        year=law_data["year"],
        category=law_data["category"],
        articles=law_data["articles"],
        approval_date=law_data.get("approval_date"),
        source_url=law_data.get("source_url"),
        full_text=law_data.get("full_text"),
    )
    
    # Get statistics
    stats = importer.get_law_statistics(law_id)
    logger.info(
        f"✓ Imported {law_data['name']}: "
        f"{stats.get('article_count', 0)} articles, "
        f"{stats.get('note_count', 0)} notes, "
        f"{stats.get('clause_count', 0)} clauses"
    )
    
    return law_id


def import_all_laws():
    """Import all major Iranian laws"""
    logger.info("=== Importing Iranian Laws ===\n")
    
    # Get connection
    connection = get_connection()
    
    # Verify connection
    if not connection.verify_connectivity():
        logger.error("Failed to connect to Neo4j")
        return
    
    # Create importer
    importer = LawImporter(connection)
    
    # Import laws
    laws = [
        CIVIL_CODE_SAMPLE,
        PENAL_CODE_SAMPLE,
        CIVIL_PROCEDURE_CODE_SAMPLE,
        CRIMINAL_PROCEDURE_CODE_SAMPLE,
    ]
    
    imported_ids: List[Any] = []
    for law_data in laws:
        try:
            law_id = import_single_law(importer, law_data)
            imported_ids.append(law_id)
        except Exception as e:
            logger.error(f"Failed to import {law_data['name']}: {e}")
    
    logger.info(f"\n✓ Successfully imported {len(imported_ids)} laws")
    
    return imported_ids


def import_civil_code_full():
    """
    Import full Civil Code (قانون مدنی)
    
    Note: This is a placeholder. In production, you would:
    1. Load all 1,335 articles from a database or file
    2. Parse article content, notes, and clauses
    3. Import in batches for better performance
    """
    logger.info("=== Importing Full Civil Code ===\n")
    logger.warning(
        "This is a sample implementation. "
        "Full import requires loading all 1,335 articles from source."
    )
    
    # For demonstration, we'll just import the sample
    connection = get_connection()
    importer = LawImporter(connection)
    
    law_id = import_single_law(importer, CIVIL_CODE_SAMPLE)
    
    logger.info(f"\n✓ Civil Code imported with ID: {law_id}")
    logger.info(
        "Note: This is a sample with only a few articles. "
        "Full import requires complete article data."
    )
    
    return law_id


def verify_imports():
    """Verify imported laws"""
    logger.info("\n=== Verifying Imports ===\n")
    
    connection = get_connection()
    
    # Query to count laws
    query = """
    MATCH (l:Law)
    RETURN l.name as name, l.year as year, l.article_count as articles
    ORDER BY l.year
    """
    
    results = connection.execute_query(query)
    
    if results:
        logger.info(f"Found {len(results)} laws in database:")
        for row in results:
            logger.info(f"  - {row['name']} ({row['year']}): {row['articles']} articles")
    else:
        logger.warning("No laws found in database")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Import Iranian laws into Neo4j")
    parser.add_argument(
        "--mode",
        choices=["sample", "full", "verify"],
        default="sample",
        help="Import mode: sample (demo), full (all articles), or verify (check imports)",
    )
    
    args = parser.parse_args()
    
    if args.mode == "sample":
        # Import sample laws
        import_all_laws()
        verify_imports()
    
    elif args.mode == "full":
        # Import full civil code
        import_civil_code_full()
        verify_imports()
    
    elif args.mode == "verify":
        # Just verify existing imports
        verify_imports()
    
    logger.info("\n✓ Done!")
