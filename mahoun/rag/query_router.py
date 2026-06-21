"""
Query Router for MAHOUN
=======================

تشخیص نوع سؤال و routing به RAG مناسب:
- پیمانی (Contract-related)
- تحلیل تأخیر (Delay Analysis)
- استعلام قانونی (Legal Inquiry)
- استعلام فنی (Technical Inquiry)

از کامپوننت‌های موجود استفاده می‌کند:
- HybridRAGService برای retrieval
- Pattern matching و keyword detection برای classification
"""

import logging
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from mahoun.llm.orchestrator import get_orchestrator, ModelCapability

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """انواع سؤالات"""

    CONTRACT = "contract"  # سؤالات پیمانی
    DELAY_ANALYSIS = "delay_analysis"  # تحلیل تأخیر
    LEGAL_INQUIRY = "legal_inquiry"  # استعلام قانونی/استدلال
    TECHNICAL_INQUIRY = "technical_inquiry"  # استعلام فنی
    CYPHER_GENERATION = "cypher_generation"  # تولید کوئری گراف
    GENERAL = "general"  # سؤال عمومی


@dataclass
class QueryClassification:
    """نتیجه classification سؤال"""

    query: str
    query_type: QueryType
    confidence: float
    keywords_found: List[str]
    metadata: Dict[str, Any]
    required_capability: Optional[str] = None  # ModelCapability value


@dataclass
class RoutedQueryResult:
    """نتیجه routed query"""

    query: str
    query_type: QueryType
    rag_result: Any  # HybridRAGResult
    classification: QueryClassification
    metadata: Dict[str, Any]
    model_capability: Optional[str] = None  # Capability used


class QueryRouter:
    """
    Query Router برای تشخیص نوع سؤال و routing به RAG مناسب

    این کلاس از کامپوننت‌های موجود استفاده می‌کند:
    - HybridRAGService برای retrieval
    - Pattern matching برای classification

    Usage:
        router = QueryRouter(rag_service=HybridRAGService(...))

        result = await router.route(
            query="شرایط پرداخت در قرارداد چیست؟"
        )
    """

    def __init__(self, rag_service=None):
        """
        Initialize Query Router

        Args:
            rag_service: HybridRAGService instance (created if None)
        """
        self.rag_service = rag_service
        self.orchestrator = get_orchestrator()

        # Query type patterns
        self.patterns = self._build_patterns()

        # Statistics
        self.stats = {
            "total_queries": 0,
            "type_distribution": {qt.value: 0 for qt in QueryType},
            "avg_confidence": 0.0,
        }

        logger.info("QueryRouter initialized")

    def _build_patterns(self) -> Dict[QueryType, List[Dict[str, Any]]]:
        """Build pattern matching rules for each query type"""
        return {
            QueryType.CONTRACT: [
                {
                    "keywords": [
                        "قرارداد",
                        "پیمان",
                        "شرایط",
                        "بند",
                        "ماده",
                        "contract",
                        "agreement",
                    ],
                    "weight": 1.0,
                },
                {
                    "keywords": ["پرداخت", "تعهد", "مسئولیت", "payment", "obligation"],
                    "weight": 0.8,
                },
                {
                    "patterns": [r"شرایط\s+[^؟]*\?", r"بند\s+\d+", r"ماده\s+\d+"],
                    "weight": 0.9,
                },
            ],
            QueryType.DELAY_ANALYSIS: [
                {
                    "keywords": ["تأخیر", "delay", "زمان", "مهلت", "deadline"],
                    "weight": 1.0,
                },
                {"keywords": ["تحلیل", "بررسی", "analysis", "review"], "weight": 0.7},
                {
                    "patterns": [r"تأخیر\s+[^؟]*\?", r"چرا\s+تأخیر", r"علت\s+تأخیر"],
                    "weight": 0.9,
                },
            ],
            QueryType.LEGAL_INQUIRY: [
                {
                    "keywords": [
                        "قانون",
                        "مقررات",
                        "آیین‌نامه",
                        "law",
                        "regulation",
                        "legal",
                    ],
                    "weight": 1.0,
                },
                {
                    "keywords": ["حقوقی", "قضایی", "دادگاه", "legal", "court"],
                    "weight": 0.8,
                },
                {
                    "patterns": [
                        r"قانون\s+[^؟]*\?",
                        r"مقررات\s+[^؟]*\?",
                        r"آیین‌نامه\s+[^؟]*\?",
                    ],
                    "weight": 0.9,
                },
            ],
            QueryType.TECHNICAL_INQUIRY: [
                {
                    "keywords": ["فنی", "تکنیکی", "مهندسی", "technical", "engineering"],
                    "weight": 1.0,
                },
                {
                    "keywords": ["مشخصات", "استاندارد", "specification", "standard"],
                    "weight": 0.7,
                },
                {
                    "patterns": [
                        r"چگونه\s+[^؟]*\?",
                        r"روش\s+[^؟]*\?",
                        r"نحوه\s+[^؟]*\?",
                    ],
                    "weight": 0.8,
                },
            ],
            QueryType.CYPHER_GENERATION: [
                {
                    "keywords": [
                        "گراف",
                        "graph",
                        "cypher",
                        "neo4j",
                        "رابطه",
                        "relationship",
                        "query",
                        "کوئری",
                        "کد",
                    ],
                    "weight": 2.0,  # High weight to override domain keywords
                },
                {
                    "patterns": [
                        r"list all .* connected to",
                        r"show me .* relationships",
                        r"چه کسانی با .* ارتباط دارند",
                        r"نمودار .* را رسم کن",
                        r"یک کوئری .* بنویس",
                    ],
                    "weight": 2.0,
                },
            ],
        }

    async def classify(self, query: str) -> QueryClassification:
        """
        Classify query type

        Args:
            query: سؤال کاربر

        Returns:
            QueryClassification با type و confidence
        """
        query_lower = query.lower()
        scores = {qt: 0.0 for qt in QueryType}
        keywords_found = {qt: [] for qt in QueryType}

        # Score each query type
        for query_type, patterns_list in self.patterns.items():
            for pattern_group in patterns_list:
                weight = pattern_group.get("weight", 1.0)

                # Check keywords
                if "keywords" in pattern_group:
                    for keyword in pattern_group["keywords"]:
                        if keyword in query_lower:
                            scores[query_type] += weight
                            keywords_found[query_type].append(keyword)

                # Check regex patterns
                if "patterns" in pattern_group:
                    for pattern in pattern_group["patterns"]:
                        if re.search(pattern, query, re.IGNORECASE):
                            scores[query_type] += weight

        # Normalize scores to confidence (0-1)
        max_score = max(scores.values()) if scores.values() else 0
        if max_score > 0:
            for qt in QueryType:
                scores[qt] = min(scores[qt] / max_score, 1.0)

        # Determine query type
        if max_score == 0:
            query_type = QueryType.GENERAL
            confidence = 0.5
        else:
            query_type = max(scores.items(), key=lambda x: x[1])[0]
            confidence = scores[query_type]

        # Update statistics
        self.stats["total_queries"] += 1
        self.stats["type_distribution"][query_type.value] += 1
        self._update_avg_confidence(confidence)

        # Determine required capability
        capability = self._map_type_to_capability(query_type)

        return QueryClassification(
            query=query,
            query_type=query_type,
            confidence=confidence,
            keywords_found=keywords_found[query_type],
            required_capability=capability.value,
            metadata={
                "scores": {qt.value: scores[qt] for qt in QueryType},
                "max_score": max_score,
            },
        )

    def _map_type_to_capability(self, query_type: QueryType) -> ModelCapability:
        """Map QueryType to ModelCapability."""
        if query_type in [
            QueryType.CYPHER_GENERATION,
            QueryType.TECHNICAL_INQUIRY,
            QueryType.DELAY_ANALYSIS,
        ]:
            return ModelCapability.CODING  # Qwen-Coder
        elif query_type in [QueryType.LEGAL_INQUIRY, QueryType.CONTRACT]:
            return ModelCapability.REASONING  # Granite-Legal
        else:
            return ModelCapability.GENERAL

    async def route(
        self, query: str, top_k: int = 10, rag_mode: Optional[str] = None
    ) -> RoutedQueryResult:
        """
        Route query to appropriate RAG service

        Args:
            query: سؤال کاربر
            top_k: تعداد نتایج
            rag_mode: RAG mode (اگر None باشد، بر اساس query type انتخاب می‌شود)

        Returns:
            RoutedQueryResult با نتایج retrieval
        """
        # Step 1: Classify query
        classification = await self.classify(query)

        # Step 2: Determine RAG mode based on query type
        if rag_mode is None:
            rag_mode = self._determine_rag_mode(classification.query_type)

        # Step 3: Initialize RAG service if needed
        if self.rag_service is None:
            from mahoun.rag.hybrid_rag_service import create_hybrid_rag_service, RAGMode

            self.rag_service = await create_hybrid_rag_service()

        # Step 4: Retrieve using RAG service
        from mahoun.rag.hybrid_rag_service import RAGMode as RAGModeEnum

        # Convert string mode to enum
        if isinstance(rag_mode, str):
            rag_mode_enum = (
                RAGModeEnum[rag_mode.upper()]
                if hasattr(RAGModeEnum, rag_mode.upper())
                else RAGModeEnum.AUTO
            )
        else:
            rag_mode_enum = rag_mode

        rag_result = await self.rag_service.retrieve(
            query=query, mode=rag_mode_enum, top_k=top_k
        )

        return RoutedQueryResult(
            query=query,
            query_type=classification.query_type,
            rag_result=rag_result,
            classification=classification,
            model_capability=classification.required_capability,
            metadata={
                "routing_strategy": "capability_based",
                "rag_mode_used": rag_result.mode_used,
                "model_routed": classification.required_capability,
            },
        )

    def _determine_rag_mode(self, query_type: QueryType) -> str:
        """
        Determine RAG mode based on query type

        Args:
            query_type: نوع سؤال

        Returns:
            RAG mode string
        """
        # Contract queries: prefer hybrid (graph + text)
        if query_type == QueryType.CONTRACT:
            return "hybrid_graph_first"

        # Delay analysis: prefer text (more structured)
        elif query_type == QueryType.DELAY_ANALYSIS:
            return "text_only"

        # Legal inquiries: prefer graph (legal relationships)
        elif query_type == QueryType.LEGAL_INQUIRY:
            return "hybrid_graph_first"

        # Technical: prefer text
        elif query_type == QueryType.TECHNICAL_INQUIRY:
            return "text_only"

        # General: auto
        else:
            return "auto"

    def _update_avg_confidence(self, confidence: float):
        """Update average confidence"""
        n = self.stats["total_queries"]
        current_avg = self.stats["avg_confidence"]
        self.stats["avg_confidence"] = ((current_avg * (n - 1)) + confidence) / n

    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics"""
        return self.stats.copy()


# ============================================================================
# Helper Functions
# ============================================================================


async def route_query(
    query: str, rag_service=None, top_k: int = 10
) -> RoutedQueryResult:
    """
    Helper function to route a query

    Args:
        query: سؤال کاربر
        rag_service: Optional HybridRAGService
        top_k: تعداد نتایج

    Returns:
        RoutedQueryResult
    """
    router = QueryRouter(rag_service=rag_service)
    return await router.route(query, top_k=top_k)
