"""
Citation Engine for MAHOUN
==========================

ارجاع دقیق به بندها و مستندات:
- شماره صفحه/بند
- لینک به مستندات اصلی
- Context extraction
- Citation formatting

از کامپوننت‌های موجود استفاده می‌کند:
- HybridRAGService results برای استخراج citations
- Metadata برای اطلاعات مستندات
"""

import logging
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """یک citation به یک منبع"""
    doc_id: str
    doc_title: Optional[str]
    page_number: Optional[int]
    section: Optional[str]
    clause_number: Optional[str]
    content: str
    score: float
    metadata: Dict[str, Any]
    citation_text: str  # Formatted citation text


@dataclass
class CitationResult:
    """نتیجه Citation Engine"""
    query: str
    citations: List[Citation]
    formatted_citations: str
    metadata: Dict[str, Any]


class CitationEngine:
    """
    Citation Engine برای ارجاع دقیق به بندها و مستندات
    
    این کلاس از نتایج HybridRAGService استفاده می‌کند و:
    - Citations را از retrieval results استخراج می‌کند
    - اطلاعات دقیق (صفحه، بند، ماده) را استخراج می‌کند
    - Citations را format می‌کند
    
    Usage:
        engine = CitationEngine()
        
        result = await engine.extract_citations(
            rag_result=hybrid_rag_result,
            query="شرایط پرداخت چیست؟"
        )
    """
    
    def __init__(self):
        """Initialize Citation Engine"""
        # Patterns for extracting citation information
        self.patterns = {
            "clause": [
                r"بند\s+(\d+)",
                r"ماده\s+(\d+)",
                r"clause\s+(\d+)",
                r"article\s+(\d+)"
            ],
            "page": [
                r"صفحه\s+(\d+)",
                r"ص\s+(\d+)",
                r"page\s+(\d+)",
                r"p\.\s*(\d+)"
            ],
            "section": [
                r"بخش\s+([^،\n]+)",
                r"فصل\s+([^،\n]+)",
                r"section\s+([^،\n]+)",
                r"chapter\s+([^،\n]+)"
            ]
        }
        
        logger.info("CitationEngine initialized")
    
    async def extract_citations(
        self,
        rag_result: Any,
        query: str,
        max_citations: int = 10
    ) -> CitationResult:
        """
        Extract citations from RAG results
        
        Args:
            rag_result: HybridRAGResult از HybridRAGService
            query: سؤال اصلی
            max_citations: حداکثر تعداد citations
        
        Returns:
            CitationResult با citations و formatted text
        """
        citations: List[Any] = []
        # Extract citations from retrieval results
        for result in rag_result.results[:max_citations]:
            citation = self._build_citation(result, query)
            if citation:
                citations.append(citation)
        
        # Format citations
        formatted_citations = self._format_citations(citations)
        
        return CitationResult(
            query=query,
            citations=citations,
            formatted_citations=formatted_citations,
            metadata={
                "total_citations": len(citations),
                "source": rag_result.mode_used
            }
        )
    
    def _build_citation(
        self,
        retrieval_result: Any,
        query: str
    ) -> Optional[Citation]:
        """
        Build Citation from RetrievalResult
        
        Args:
            retrieval_result: RetrievalResult از HybridRAGService
            query: سؤال اصلی
        
        Returns:
            Citation object
        """
        # Extract basic information
        doc_id = retrieval_result.doc_id
        content = retrieval_result.content
        score = retrieval_result.score
        metadata = retrieval_result.metadata or {}
        
        # Extract document title
        doc_title = metadata.get("title") or metadata.get("doc_title") or doc_id
        
        # Extract citation details from content
        clause_number = self._extract_clause_number(content)
        page_number = self._extract_page_number(content, metadata)
        section = self._extract_section(content, metadata)
        
        # Build citation text
        citation_text = self._build_citation_text(
            doc_title=doc_title,
            clause_number=clause_number,
            page_number=page_number,
            section=section,
            content=content[:200]  # First 200 chars
        )
        
        return Citation(
            doc_id=doc_id,
            doc_title=doc_title,
            page_number=page_number,
            section=section,
            clause_number=clause_number,
            content=content,
            score=score,
            metadata=metadata,
            citation_text=citation_text
        )
    
    def _extract_clause_number(self, content: str) -> Optional[str]:
        """Extract clause/article number from content"""
        for pattern in self.patterns["clause"]:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_page_number(self, content: str, metadata: Dict[str, Any]) -> Optional[int]:
        """Extract page number from content or metadata"""
        # Try metadata first
        if "page" in metadata:
            try:
                return int(metadata["page"])
            except (ValueError, TypeError):
                pass
        
        # Try content
        for pattern in self.patterns["page"]:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    pass
        
        return None
    
    def _extract_section(self, content: str, metadata: Dict[str, Any]) -> Optional[str]:
        """Extract section from content or metadata"""
        # Try metadata first
        if "section" in metadata:
            return str(metadata["section"])
        
        # Try content
        for pattern in self.patterns["section"]:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _build_citation_text(
        self,
        doc_title: str,
        clause_number: Optional[str],
        page_number: Optional[int],
        section: Optional[str],
        content: str
    ) -> str:
        """
        Build formatted citation text
        
        Format: [Doc Title, Clause X, Page Y, Section Z]
        """
        parts = [str(doc_title)]
        
        if clause_number:
            parts.append(f"بند {clause_number}")
        
        if page_number:
            parts.append(f"صفحه {page_number}")
        
        if section:
            parts.append(f"بخش {section}")
        
        citation = f"[{', '.join(map(str, parts))}]"
        
        # Add content snippet
        if content:
            citation += f": {content[:100]}..."
        
        return citation
    
    def _format_citations(self, citations: List[Citation]) -> str:
        """
        Format all citations as text
        
        Returns:
            Formatted citations string
        """
        if not citations:
            return "هیچ ارجاعی یافت نشد."
        
        formatted: List[Any] = []
        for i, citation in enumerate(citations, 1):
            formatted.append(f"{i}. {citation.citation_text}")
        
        return "\n".join(formatted)
    
    def format_citation_markdown(self, citation: Citation) -> str:
        """
        Format citation in Markdown format
        
        Args:
            citation: Citation object
        
        Returns:
            Markdown formatted citation
        """
        parts: List[Any] = []
        if citation.doc_title:
            parts.append(f"**{citation.doc_title}**")
        
        if citation.clause_number:
            parts.append(f"بند {citation.clause_number}")
        
        if citation.page_number:
            parts.append(f"صفحه {citation.page_number}")
        
        if citation.section:
            parts.append(f"بخش {citation.section}")
        
        citation_text = " - ".join(parts)
        
        # Add content quote
        if citation.content:
            citation_text += f"\n> {citation.content[:200]}"
        
        return citation_text
    
    def format_citations_markdown(self, citations: List[Citation]) -> str:
        """Format all citations in Markdown"""
        if not citations:
            return "*هیچ ارجاعی یافت نشد.*"
        
        formatted: List[Any] = []
        for i, citation in enumerate(citations, 1):
            formatted.append(f"### ارجاع {i}\n{self.format_citation_markdown(citation)}")
        
        return "\n\n".join(formatted)


# ============================================================================
# Helper Functions
# ============================================================================

async def extract_citations_from_rag(
    rag_result: Any,
    query: str,
    max_citations: int = 10
) -> CitationResult:
    """
    Helper function to extract citations from RAG result
    
    Args:
        rag_result: HybridRAGResult
        query: سؤال اصلی
        max_citations: حداکثر تعداد citations
    
    Returns:
        CitationResult
    """
    engine = CitationEngine()
    return await engine.extract_citations(rag_result, query, max_citations)

