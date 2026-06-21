#!/usr/bin/env python3
"""
Cross-Encoder Reranker
======================
Two-stage reranking with cross-encoder for improved precision
"""

import logging
from typing import List, Tuple, Optional, Dict, Any
import torch
from sentence_transformers import CrossEncoder
import numpy as np

log = logging.getLogger(__name__)


class CrossEncoderReranker:
    """
    Cross-encoder reranker for two-stage retrieval
    
    Stage 1: Bi-encoder retrieves top-K candidates
    Stage 2: Cross-encoder reranks to top-M
    """
    
    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        device: str = "auto",
        batch_size: int = 16,
        max_length: int = 512,
        score_activation: str = "sigmoid",
        use_fp16: bool = True,
        **kwargs
    ):
        """
        Initialize cross-encoder reranker
        
        Args:
            model_name: HuggingFace cross-encoder model
            device: Device (auto, cuda, cpu)
            batch_size: Batch size for scoring
            max_length: Max sequence length
            score_activation: Activation function (sigmoid, softmax, none)
            use_fp16: Use FP16 for faster inference
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.max_length = max_length
        self.score_activation = score_activation
        self.use_fp16 = use_fp16
        
        # Determine device
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        # Load model
        log.info(f"Loading cross-encoder: {model_name}")
        self.model = CrossEncoder(
            model_name,
            max_length=max_length,
            device=self.device
        )
        
        # Enable FP16 if requested
        if use_fp16 and self.device == "cuda":
            self.model.model = self.model.model.half()
            log.info("Enabled FP16 inference")
        
        log.info(f"Cross-encoder initialized: {model_name} (device={self.device})")
    
    def rank(
        self,
        query: str,
        candidates: List[str],
        top_k: Optional[int] = None,
        return_scores: bool = False
    ) -> List[int] | Tuple[List[int], List[float]]:
        """
        Rerank candidates using cross-encoder
        
        Args:
            query: Query string
            candidates: List of candidate passages
            top_k: Return only top-K (default: all)
            return_scores: Return scores along with indices
            
        Returns:
            Ranked indices (and optionally scores)
        """
        if not candidates:
            return ([], []) if return_scores else []
        
        # Create query-passage pairs
        pairs = [[query, candidate] for candidate in candidates]
        
        # Score pairs
        scores = self.model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            activation_fct=self._get_activation()
        )
        
        # Sort by score (descending)
        ranked_indices = np.argsort(scores)[::-1]
        
        # Limit to top-K
        if top_k:
            ranked_indices = ranked_indices[:top_k]
        
        ranked_indices = ranked_indices.tolist()
        
        if return_scores:
            ranked_scores = [scores[i] for i in ranked_indices]
            return ranked_indices, ranked_scores
        else:
            return ranked_indices
    
    def score(
        self,
        query: str,
        candidates: List[str]
    ) -> List[float]:
        """
        Score query-candidate pairs
        
        Args:
            query: Query string
            candidates: List of candidates
            
        Returns:
            Scores for each candidate
        """
        if not candidates:
            return []
        
        pairs = [[query, candidate] for candidate in candidates]
        
        scores = self.model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            activation_fct=self._get_activation()
        )
        
        return scores.tolist()
    
    def _get_activation(self):
        """Get activation function"""
        if self.score_activation == "sigmoid":
            return torch.nn.Sigmoid()
        elif self.score_activation == "softmax":
            return torch.nn.Softmax(dim=-1)
        else:
            return None
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "CrossEncoderReranker":
        """Create reranker from config"""
        return cls(
            model_name=config.get("model_name", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
            device=config.get("device", "auto"),
            batch_size=config.get("batch_size", 16),
            max_length=config.get("max_length", 512),
            score_activation=config.get("score_activation", "sigmoid"),
            use_fp16=config.get("use_fp16", True)
        )


class TwoStageReranker:
    """
    Two-stage reranking pipeline
    
    Combines bi-encoder retrieval with cross-encoder reranking
    """
    
    def __init__(
        self,
        cross_encoder: CrossEncoderReranker,
        stage1_top_k: int = 200,
        stage2_top_m: int = 20,
        fallback_on_error: bool = True
    ):
        """
        Initialize two-stage reranker
        
        Args:
            cross_encoder: Cross-encoder instance
            stage1_top_k: Top-K from stage 1
            stage2_top_m: Top-M from stage 2
            fallback_on_error: Fall back to stage 1 on error
        """
        self.cross_encoder = cross_encoder
        self.stage1_top_k = stage1_top_k
        self.stage2_top_m = stage2_top_m
        self.fallback_on_error = fallback_on_error
        
        log.info(
            f"Two-stage reranker initialized: "
            f"K={stage1_top_k}, M={stage2_top_m}"
        )
    
    def rerank(
        self,
        query: str,
        candidates: List[Any],
        candidate_texts: Optional[List[str]] = None
    ) -> List[Any]:
        """
        Rerank candidates using two-stage approach
        
        Args:
            query: Query string
            candidates: List of candidate objects
            candidate_texts: Optional list of texts (if candidates are objects)
            
        Returns:
            Reranked candidates
        """
        if not candidates:
            return []
        
        # Extract texts if needed
        if candidate_texts is None:
            if hasattr(candidates[0], 'text'):
                candidate_texts = [c.text for c in candidates]
            elif isinstance(candidates[0], str):
                candidate_texts = candidates
            else:
                raise ValueError("Cannot extract text from candidates")
        
        # Stage 1: Already done (bi-encoder retrieval)
        # Take top-K
        stage1_candidates = candidates[:self.stage1_top_k]
        stage1_texts = candidate_texts[:self.stage1_top_k]
        
        try:
            # Stage 2: Cross-encoder reranking
            ranked_indices = self.cross_encoder.rank(
                query=query,
                candidates=stage1_texts,
                top_k=self.stage2_top_m
            )
            
            # Reorder candidates
            reranked = [stage1_candidates[i] for i in ranked_indices]
            
            log.debug(
                f"Two-stage reranking: {len(candidates)} → "
                f"{len(stage1_candidates)} → {len(reranked)}"
            )
            
            return reranked
            
        except Exception as e:
            log.error(f"Cross-encoder reranking failed: {e}")
            
            if self.fallback_on_error:
                log.warning("Falling back to stage 1 results")
                return stage1_candidates[:self.stage2_top_m]
            else:
                raise
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "TwoStageReranker":
        """Create two-stage reranker from config"""
        # Load cross-encoder
        ce_config = config.get("stage2", {})
        cross_encoder = CrossEncoderReranker.from_config(ce_config)
        
        # Get stage settings
        stage1_config = config.get("stage1", {})
        stage1_top_k = stage1_config.get("top_k", 200)
        
        stage2_top_m = ce_config.get("top_m", 20)
        
        fallback_config = config.get("fallback", {})
        fallback_on_error = fallback_config.get("on_error") == "use_stage1"
        
        return cls(
            cross_encoder=cross_encoder,
            stage1_top_k=stage1_top_k,
            stage2_top_m=stage2_top_m,
            fallback_on_error=fallback_on_error
        )
