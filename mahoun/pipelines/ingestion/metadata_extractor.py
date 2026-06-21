"""
Metadata Extractor for MAHOUN
=============================

استخراج خودکار metadata از مدارک پیمانکاری:
- تاریخ (تاریخ نامه، تاریخ دریافت)
- شماره نامه/سند
- موضوع
- طرفین (فرستنده/گیرنده)
- امضا
- پیوست‌ها

از کامپوننت‌های موجود استفاده می‌کند:
- LegalNEREngine برای استخراج entities
- Pattern matching برای استخراج اطلاعات ساختاریافته
"""

import logging
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """
    Metadata Extractor برای استخراج خودکار اطلاعات از مدارک

    این کلاس از کامپوننت‌های موجود استفاده می‌کند:
    - LegalNEREngine برای استخراج entities (اگر موجود باشد)
    - Pattern matching برای استخراج اطلاعات ساختاریافته
    """

    def __init__(self):
        """Initialize Metadata Extractor"""
        # Legal NER Engine (optional)
        self.ner_engine = None
        try:
            from .legal_ner import LegalNEREngine

            self.ner_engine = LegalNEREngine()
            logger.info("✅ LegalNEREngine initialized for metadata extraction")
        except ImportError:
            logger.warning("LegalNEREngine not available, using pattern matching only")

        # Persian date patterns
        self.date_patterns = [
            r"(\d{4})/(\d{1,2})/(\d{1,2})",  # 1403/01/15
            r"(\d{1,2})/(\d{1,2})/(\d{4})",  # 15/01/1403
            r"(\d{4})-(\d{1,2})-(\d{1,2})",  # 1403-01-15
        ]

        logger.info("MetadataExtractor initialized")

    async def extract(self, text: str, doc_type: str) -> Dict[str, Any]:
        """
        Extract metadata from document text

        Args:
            text: متن سند
            doc_type: نوع سند (contract, letter, report, etc.)

        Returns:
            Dictionary of extracted metadata
        """
        metadata = {
            "doc_type": doc_type,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }

        # Extract basic metadata
        metadata.update(self._extract_dates(text))
        metadata.update(self._extract_document_number(text))
        metadata.update(self._extract_subject(text))
        metadata.update(self._extract_parties(text, doc_type))
        metadata.update(self._extract_signatures(text))
        metadata.update(self._extract_attachments(text))

        # Extract entities using NER (if available)
        if self.ner_engine:
            try:
                entities = self.ner_engine.extract(text)
                metadata["entities"] = {
                    "persons": entities.get("persons", []),
                    "organizations": entities.get("organizations", []),
                    "courts": entities.get("courts", []),
                    "laws": entities.get("laws", []),
                    "topics": entities.get("topics", []),
                }
            except Exception as e:
                logger.warning(f"NER extraction failed: {e}")

        return metadata

    def _extract_dates(self, text: str) -> Dict[str, Any]:
        """Extract dates from text"""
        dates = {
            "date": None,
            "date_received": None,
            "date_issued": None,
            "dates_found": [],
        }

        # Find all date patterns
        for pattern in self.date_patterns:
            matches = re.findall(pattern, text[:2000])  # First 2000 chars
            if matches:
                dates["dates_found"].extend(
                    [m[0] if isinstance(m, tuple) else m for m in matches]
                )

        # Extract specific dates
        # Date issued (usually at the beginning)
        first_200 = text[:200]
        for pattern in self.date_patterns:
            match = re.search(pattern, first_200)
            if match:
                dates["date_issued"] = match.group(0)
                dates["date"] = match.group(0)  # Default to first date
                break

        # Date received (look for keywords)
        received_keywords = ["تاریخ دریافت", "تاریخ وصول", "received", "received_date"]
        for keyword in received_keywords:
            if keyword in text:
                # Find date after keyword
                keyword_pos = text.find(keyword)
                snippet = text[keyword_pos : keyword_pos + 100]
                for pattern in self.date_patterns:
                    match = re.search(pattern, snippet)
                    if match:
                        dates["date_received"] = match.group(0)
                        break
                if dates["date_received"]:
                    break

        return dates

    def _extract_document_number(self, text: str) -> Dict[str, Any]:
        """Extract document number"""
        doc_number: Optional[Any] = None
        # Look for document number patterns
        patterns = [
            r"شماره[:\s]+(\d+[-\d]*)",
            r"ش\.\s*(\d+[-\d]*)",
            r"No[:\s]+(\d+[-\d]*)",
            r"Number[:\s]+(\d+[-\d]*)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text[:500], re.IGNORECASE)
            if match:
                doc_number = match.group(1)
                break

        return {"document_number": doc_number}

    def _extract_subject(self, text: str) -> Dict[str, Any]:
        """Extract subject/title"""
        subject: Optional[Any] = None
        # Look for subject keywords
        keywords = [
            ("موضوع", ":"),
            ("عنوان", ":"),
            ("Subject", ":"),
            ("Title", ":"),
        ]

        for keyword, separator in keywords:
            pattern = f"{keyword}{separator}\\s*(.+?)(?:\\n|$)"
            match = re.search(pattern, text[:1000], re.IGNORECASE)
            if match:
                subject = match.group(1).strip()
                if len(subject) > 5:  # Valid subject
                    break

        # If not found, use first line
        if not subject:
            first_line = text.split("\n")[0].strip()
            if len(first_line) > 10 and len(first_line) < 200:
                subject = first_line

        return {"subject": subject}

    def _extract_parties(self, text: str, doc_type: str) -> Dict[str, Any]:
        """Extract parties (sender/receiver)"""
        parties = {"sender": None, "receiver": None, "parties": []}

        # For contracts, look for party keywords
        if doc_type == "contract":
            party_keywords = ["طرف اول", "طرف دوم", "کارفرما", "پیمانکار"]
            for keyword in party_keywords:
                if keyword in text:
                    # Extract party name after keyword
                    pattern = f"{keyword}[:\\s]+(.+?)(?:\\n|،|$)"
                    match = re.search(pattern, text[:2000])
                    if match:
                        party_name = match.group(1).strip()
                        parties["parties"].append({"role": keyword, "name": party_name})

        # For letters, look for sender/receiver
        elif doc_type == "letter":
            # Sender keywords
            sender_keywords = ["از", "فرستنده", "sender", "from"]
            for keyword in sender_keywords:
                if keyword in text[:500]:
                    pattern = f"{keyword}[:\\s]+(.+?)(?:\\n|،|$)"
                    match = re.search(pattern, text[:500])
                    if match:
                        parties["sender"] = match.group(1).strip()
                        break

            # Receiver keywords
            receiver_keywords = ["به", "گیرنده", "receiver", "to"]
            for keyword in receiver_keywords:
                if keyword in text[:500]:
                    pattern = f"{keyword}[:\\s]+(.+?)(?:\\n|،|$)"
                    match = re.search(pattern, text[:500])
                    if match:
                        parties["receiver"] = match.group(1).strip()
                        break

        return parties

    def _extract_signatures(self, text: str) -> Dict[str, Any]:
        """Extract signature information"""
        signatures = {"has_signature": False, "signature_text": None, "signers": []}

        # Look for signature keywords
        signature_keywords = ["امضا", "مهر", "signature", "signed"]

        for keyword in signature_keywords:
            if keyword in text.lower():
                signatures["has_signature"] = True

                # Extract signature section
                keyword_pos = text.lower().find(keyword)
                signature_section = text[keyword_pos : keyword_pos + 200]
                signatures["signature_text"] = signature_section
                break

        return signatures

    def _extract_attachments(self, text: str) -> Dict[str, Any]:
        """Extract attachment information"""
        attachments = {
            "has_attachments": False,
            "attachment_count": 0,
            "attachments": [],
        }

        # Look for attachment keywords
        attachment_keywords = ["پیوست", "ضمیمه", "attachment", "enclosure"]

        for keyword in attachment_keywords:
            if keyword in text.lower():
                attachments["has_attachments"] = True

                # Count attachments
                pattern = f"{keyword}[:\\s]*(\\d+)"
                matches = re.findall(pattern, text.lower())
                if matches:
                    attachments["attachment_count"] = len(matches)
                    attachments["attachments"] = [
                        {"number": int(m), "keyword": keyword} for m in matches
                    ]
                break

        return attachments
