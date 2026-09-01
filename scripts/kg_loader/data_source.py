"""
Real Legal Data Source
======================

Integrates with the canonical LegalCorpusParser to provide real legal data
for batch processing. No mock data, only verified legal corpus.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import sys

# Add project root to path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import canonical parser
from scripts.build_legal_kg import LegalCorpusParser

logger = logging.getLogger(__name__)


class RealLegalDataSource:
    """
    Real legal data source using canonical LegalCorpusParser
    
    Features:
    - Uses the SAME parser as build_legal_kg.py (zero duplication)
    - Caches parsed results (parse once, use many times)
    - Provides batch-friendly data accessors
    - Tracks parsing statistics
    """
    
    def __init__(self, corpus_path: Path):
        """
        Initialize data source
        
        Args:
            corpus_path: Path to legal corpus file (e.g., all_legal_sentences.txt)
        """
        self.corpus_path = Path(corpus_path)
        
        # Validation
        if not self.corpus_path.exists():
            raise FileNotFoundError(f"Corpus file not found: {self.corpus_path}")
        
        # Initialize parser with same config as build_legal_kg.py
        self.parser = LegalCorpusParser(
            source_path=self.corpus_path,
            default_law_id=None,  # Auto-detect from text
            default_law_name=None,  # Auto-detect from text
        )
        
        # Cached results
        self._parsed_data: Optional[Dict[str, Any]] = None
        self._parse_stats: Optional[Dict[str, Any]] = None
        
        logger.info(f"Initialized RealLegalDataSource for: {self.corpus_path}")
    
    def parse(self, force_reparse: bool = False) -> Dict[str, Any]:
        """
        Parse corpus using canonical parser
        
        Args:
            force_reparse: If True, reparse even if cached
            
        Returns:
            Dict with parsed data: laws, chapters, articles, citations, stats
        """
        if self._parsed_data is None or force_reparse:
            logger.info("Parsing legal corpus...")
            
            # Use canonical parser (SAME as build_legal_kg.py!)
            laws, chapters, articles, citations, records, stats = self.parser.parse()
            
            # Cache results
            self._parsed_data = {
                'laws': laws,
                'chapters': chapters,
                'articles': articles,
                'citations': citations,
                'records': records,
                'stats': stats,
            }
            self._parse_stats = stats
            
            logger.info(f"Parsing complete: "
                       f"{len(laws)} laws, "
                       f"{len(chapters)} chapters, "
                       f"{len(articles)} articles, "
                       f"{len(citations)} citations")
            
            # Log statistics
            if stats:
                logger.info(f"Parse stats: {stats}")
        
        return self._parsed_data
    
    def get_parse_stats(self) -> Dict[str, Any]:
        """Get parsing statistics"""
        if self._parse_stats is None:
            self.parse()
        return self._parse_stats or {}
    
    def get_laws(self) -> List[Any]:
        """Get all parsed laws"""
        data = self.parse()
        return data['laws']
    
    def get_chapters(self) -> List[Any]:
        """Get all parsed chapters"""
        data = self.parse()
        return data['chapters']
    
    def get_articles(self) -> List[Any]:
        """Get all parsed articles"""
        data = self.parse()
        return data['articles']
    
    def get_citations(self) -> List[Any]:
        """Get all parsed citations"""
        data = self.parse()
        return data['citations']
    
    def get_resolved_citations(self) -> List[Any]:
        """Get only RESOLVED citations (ready for graph links)"""
        citations = self.get_citations()
        return [cite for cite in citations if cite.status == "RESOLVED"]
    
    def get_unresolved_citations(self) -> List[Any]:
        """Get UNRESOLVED citations (will go to DLQ)"""
        citations = self.get_citations()
        return [cite for cite in citations if cite.status == "UNRESOLVED"]
    
    def get_law_by_id(self, law_id: str) -> Optional[Any]:
        """Get specific law by ID"""
        laws = self.get_laws()
        for law in laws:
            if law.id == law_id:
                return law
        return None
    
    def get_article_by_id(self, article_id: str) -> Optional[Any]:
        """Get specific article by ID"""
        articles = self.get_articles()
        for article in articles:
            if article.id == article_id:
                return article
        return None
    
    def get_chapter_by_id(self, chapter_id: str) -> Optional[Any]:
        """Get specific chapter by ID"""
        chapters = self.get_chapters()
        for chapter in chapters:
            if chapter.id == chapter_id:
                return chapter
        return None
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary"""
        data = self.parse()
        stats = self.get_parse_stats()
        resolved_citations = self.get_resolved_citations()
        unresolved_citations = self.get_unresolved_citations()
        
        return {
            'corpus_path': str(self.corpus_path),
            'corpus_size_mb': self.corpus_path.stat().st_size / (1024 * 1024),
            'entities': {
                'laws': len(data['laws']),
                'chapters': len(data['chapters']),
                'articles': len(data['articles']),
                'total_citations': len(data['citations']),
                'resolved_citations': len(resolved_citations),
                'unresolved_citations': len(unresolved_citations),
            },
            'resolution_rate': len(resolved_citations) / len(data['citations']) if data['citations'] else 0,
            'parse_stats': stats,
        }
    
    def validate_integrity(self) -> Tuple[bool, List[str]]:
        """
        Validate data integrity
        
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            data = self.parse()
            
            # Check basic counts
            if not data['laws']:
                issues.append("No laws found in corpus")
            
            if not data['articles']:
                issues.append("No articles found in corpus")
            
            # Check referential integrity
            law_ids = {law.id for law in data['laws']}
            chapter_ids = {chapter.id for chapter in data['chapters']}
            article_ids = {article.id for article in data['articles']}
            
            # Validate chapter -> law references
            for chapter in data['chapters']:
                if hasattr(chapter, 'law_id') and chapter.law_id not in law_ids:
                    issues.append(f"Chapter {chapter.id} references non-existent law {chapter.law_id}")
            
            # Validate article -> chapter references
            for article in data['articles']:
                if hasattr(article, 'chapter_id') and article.chapter_id and article.chapter_id not in chapter_ids:
                    issues.append(f"Article {article.id} references non-existent chapter {article.chapter_id}")
            
            # Validate resolved citations
            resolved_citations = self.get_resolved_citations()
            for citation in resolved_citations:
                if citation.source_article_id not in article_ids:
                    issues.append(f"Citation source {citation.source_article_id} not found in articles")
                if citation.target_article_id not in article_ids:
                    issues.append(f"Citation target {citation.target_article_id} not found in articles")
            
        except Exception as e:
            issues.append(f"Parsing failed: {e}")
        
        return len(issues) == 0, issues


class BatchJobFactory:
    """
    Factory for creating BatchJob instances from parsed legal data
    
    Features:
    - Priority assignment (Laws > Chapters > Articles > Citations)
    - Proper job metadata
    - Task name mapping
    """
    
    @staticmethod
    def create_law_jobs(laws: List[Any]) -> List[Dict[str, Any]]:
        """Create BatchJob configs for laws (CRITICAL priority)"""
        return [
            {
                'task_name': 'load_law',
                'data': {'law': law},
                'priority': 'CRITICAL',  # Laws first (dependencies)
                'metadata': {
                    'entity_type': 'Law',
                    'entity_id': law.id,
                    'size': len(law.raw_text) if hasattr(law, 'raw_text') else 0,
                }
            }
            for law in laws
        ]
    
    @staticmethod
    def create_chapter_jobs(chapters: List[Any]) -> List[Dict[str, Any]]:
        """Create BatchJob configs for chapters (HIGH priority)"""
        return [
            {
                'task_name': 'load_chapter',
                'data': {'chapter': chapter},
                'priority': 'HIGH',  # Chapters after laws
                'metadata': {
                    'entity_type': 'Chapter',
                    'entity_id': chapter.id,
                    'law_id': getattr(chapter, 'law_id', None),
                    'size': len(chapter.raw_text) if hasattr(chapter, 'raw_text') else 0,
                }
            }
            for chapter in chapters
        ]
    
    @staticmethod
    def create_article_jobs(articles: List[Any]) -> List[Dict[str, Any]]:
        """Create BatchJob configs for articles (HIGH priority)"""
        return [
            {
                'task_name': 'load_article',
                'data': {'article': article},
                'priority': 'HIGH',  # Articles after chapters
                'metadata': {
                    'entity_type': 'Article',
                    'entity_id': article.id,
                    'law_id': getattr(article, 'law_id', None),
                    'chapter_id': getattr(article, 'chapter_id', None),
                    'size': len(article.raw_text) if hasattr(article, 'raw_text') else 0,
                }
            }
            for article in articles
        ]
    
    @staticmethod
    def create_citation_jobs(citations: List[Any], only_resolved: bool = True) -> List[Dict[str, Any]]:
        """Create BatchJob configs for citations (NORMAL priority)"""
        if only_resolved:
            citations = [cite for cite in citations if cite.status == "RESOLVED"]
        
        return [
            {
                'task_name': 'load_citation',
                'data': {'citation': citation},
                'priority': 'NORMAL',  # Citations after articles
                'metadata': {
                    'entity_type': 'Citation',
                    'entity_id': f"{citation.source_article_id}->{citation.target_article_id}",
                    'source_id': citation.source_article_id,
                    'target_id': citation.target_article_id,
                    'status': citation.status,
                }
            }
            for citation in citations
        ]
    
    @staticmethod
    def create_all_jobs(data_source: RealLegalDataSource, include_unresolved: bool = False) -> List[Dict[str, Any]]:
        """Create all BatchJob configs in correct order"""
        data = data_source.parse()
        
        jobs = []
        
        # Order matters for dependencies!
        jobs.extend(BatchJobFactory.create_law_jobs(data['laws']))
        jobs.extend(BatchJobFactory.create_chapter_jobs(data['chapters']))
        jobs.extend(BatchJobFactory.create_article_jobs(data['articles']))
        
        # Citations (resolved + optionally unresolved)
        if include_unresolved:
            jobs.extend(BatchJobFactory.create_citation_jobs(data['citations'], only_resolved=False))
        else:
            jobs.extend(BatchJobFactory.create_citation_jobs(data['citations'], only_resolved=True))
        
        logger.info(f"Created {len(jobs)} batch jobs")
        return jobs