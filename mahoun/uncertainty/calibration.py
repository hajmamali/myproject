#!/usr/bin/env python3
"""
Uncertainty Calibration
=======================
Temperature Scaling + Conformal Prediction for better calibration
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

# Optional torch import
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    torch: Optional[Any] = None
    nn: Optional[Any] = None
    F: Optional[Any] = None
import torch.optim as optim
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass
class CalibrationResult:
    """Calibration result"""
    calibrated_scores: np.ndarray
    confidence_intervals: Optional[List[Tuple[float, float]]] = None
    uncertainty_score: Optional[float] = None
    metrics: Optional[Dict[str, float]] = None


class TemperatureScaling:
    """
    Temperature Scaling for probability calibration
    
    Learns a single temperature parameter T to scale logits:
    p_calibrated = softmax(logits / T)
    """
    
    def __init__(self, device: str = "cpu"):
        """
        Initialize temperature scaling
        
        Args:
            device: Device for computation
        """
        self.device = device
        self.temperature = nn.Parameter(torch.ones(1).to(device))
        self.is_fitted = False
        
        log.info("TemperatureScaling initialized")
    
    def fit(
        self,
        logits: np.ndarray,
        labels: np.ndarray,
        lr: float = 0.01,
        max_iter: int = 50
    ):
        """
        Fit temperature parameter on calibration set
        
        Args:
            logits: Logits from model (N, C)
            labels: True labels (N,)
            lr: Learning rate
            max_iter: Maximum iterations
        """
        # Convert to tensors
        logits_tensor = torch.FloatTensor(logits).to(self.device)
        labels_tensor = torch.LongTensor(labels).to(self.device)
        
        # Optimize temperature
        optimizer = optim.Adam([self.temperature], lr=lr)
        criterion = nn.CrossEntropyLoss()
        
        best_loss = float('inf')
        
        for epoch in range(max_iter):
            optimizer.zero_grad()
            
            # Scale logits
            scaled_logits = logits_tensor / self.temperature
            
            # Compute loss
            loss = criterion(scaled_logits, labels_tensor)
            
            # Backward
            loss.backward()
            optimizer.step()
            
            # Track best
            if loss.item() < best_loss:
                best_loss = loss.item()
            
            if (epoch + 1) % 10 == 0:
                log.debug(f"Epoch {epoch+1}/{max_iter}, Loss: {loss.item():.4f}, T: {self.temperature.item():.4f}")
        
        self.is_fitted = True
        log.info(f"Temperature fitted: T={self.temperature.item():.4f}")
    
    def calibrate(self, logits: np.ndarray) -> np.ndarray:
        """
        Calibrate logits using learned temperature
        
        Args:
            logits: Logits to calibrate (N, C)
            
        Returns:
            Calibrated probabilities (N, C)
        """
        if not self.is_fitted:
            log.warning("Temperature not fitted, using T=1.0")
            return torch.softmax(torch.FloatTensor(logits), dim=-1).numpy()
        
        with torch.no_grad():
            logits_tensor = torch.FloatTensor(logits).to(self.device)
            scaled_logits = logits_tensor / self.temperature
            probs = torch.softmax(scaled_logits, dim=-1)
        
        return probs.cpu().numpy()
    
    def calibrate_scores(self, scores: np.ndarray) -> np.ndarray:
        """
        Calibrate confidence scores
        
        Args:
            scores: Confidence scores (N,)
            
        Returns:
            Calibrated scores (N,)
        """
        if not self.is_fitted:
            return scores
        
        # Convert scores to logits (inverse sigmoid)
        epsilon = 1e-7
        scores = np.clip(scores, epsilon, 1 - epsilon)
        logits = np.log(scores / (1 - scores))
        
        # Scale
        with torch.no_grad():
            logits_tensor = torch.FloatTensor(logits).to(self.device)
            scaled_logits = logits_tensor / self.temperature
            calibrated = torch.sigmoid(scaled_logits)
        
        return calibrated.cpu().numpy()


class ConformalPrediction:
    """
    Conformal Prediction for uncertainty quantification
    
    Provides prediction intervals with guaranteed coverage
    """
    
    def __init__(
        self,
        alpha: float = 0.1,
        method: str = "split"
    ):
        """
        Initialize conformal prediction
        
        Args:
            alpha: Significance level (1-alpha coverage)
            method: Conformal method (split, jackknife)
        """
        self.alpha = alpha
        self.method = method
        self.quantile = None
        self.is_fitted = False
        
        log.info(f"ConformalPrediction initialized (alpha={alpha}, method={method})")
    
    def fit(
        self,
        predictions: np.ndarray,
        targets: np.ndarray
    ):
        """
        Fit conformal predictor on calibration set
        
        Args:
            predictions: Model predictions (N,)
            targets: True targets (N,)
        """
        # Compute nonconformity scores (absolute errors)
        scores = np.abs(predictions - targets)
        
        # Compute quantile
        n = len(scores)
        q_level = np.ceil((n + 1) * (1 - self.alpha)) / n
        self.quantile = np.quantile(scores, q_level)
        
        self.is_fitted = True
        log.info(f"Conformal quantile fitted: {self.quantile:.4f} (coverage={1-self.alpha:.1%})")
    
    def predict_interval(
        self,
        predictions: np.ndarray
    ) -> List[Tuple[float, float]]:
        """
        Predict confidence intervals
        
        Args:
            predictions: Model predictions (N,)
            
        Returns:
            List of (lower, upper) intervals
        """
        if not self.is_fitted:
            log.warning("Conformal not fitted, returning point predictions")
            return [(p, p) for p in predictions]
        
        intervals = [
            (pred - self.quantile, pred + self.quantile)
            for pred in predictions
        ]
        
        return intervals
    
    def get_interval_width(self) -> float:
        """Get average interval width"""
        if not self.is_fitted:
            return 0.0
        return 2 * self.quantile


class UncertaintyCalibrator:
    """
    Combined uncertainty calibration
    
    Fuses GP variance, temperature-scaled confidence, and conformal intervals
    """
    
    def __init__(
        self,
        enable_gp: bool = True,
        enable_temperature: bool = True,
        enable_conformal: bool = True,
        fusion_weights: Optional[Dict[str, float]] = None
    ):
        """
        Initialize calibrator
        
        Args:
            enable_gp: Enable GP uncertainty
            enable_temperature: Enable temperature scaling
            enable_conformal: Enable conformal prediction
            fusion_weights: Weights for fusion
        """
        self.enable_gp = enable_gp
        self.enable_temperature = enable_temperature
        self.enable_conformal = enable_conformal
        
        # Default weights
        self.fusion_weights = fusion_weights or {
            "gp_var": 0.5,
            "temp_conf": 0.3,
            "conformal_width": 0.2
        }
        
        # Components
        self.temp_scaler = TemperatureScaling() if enable_temperature else None
        self.conformal = ConformalPrediction() if enable_conformal else None
        
        log.info(
            f"UncertaintyCalibrator initialized: "
            f"GP={enable_gp}, Temp={enable_temperature}, Conformal={enable_conformal}"
        )
    
    def fit(
        self,
        calibration_data: Dict[str, Any]
    ):
        """
        Fit calibration components
        
        Args:
            calibration_data: Dict with logits, labels, predictions, targets
        """
        # Fit temperature scaling
        if self.enable_temperature and self.temp_scaler:
            logits = calibration_data.get("logits")
            labels = calibration_data.get("labels")
            
            if logits is not None and labels is not None:
                self.temp_scaler.fit(logits, labels)
        
        # Fit conformal prediction
        if self.enable_conformal and self.conformal:
            predictions = calibration_data.get("predictions")
            targets = calibration_data.get("targets")
            
            if predictions is not None and targets is not None:
                self.conformal.fit(predictions, targets)
        
        log.info("Calibration components fitted")
    
    def calibrate(
        self,
        gp_variance: Optional[float] = None,
        confidence_score: Optional[float] = None,
        prediction: Optional[float] = None
    ) -> CalibrationResult:
        """
        Calibrate uncertainty
        
        Args:
            gp_variance: GP variance
            confidence_score: Model confidence
            prediction: Model prediction
            
        Returns:
            CalibrationResult
        """
        components: List[Any] = []
        weights: List[Any] = []
        # GP variance
        if self.enable_gp and gp_variance is not None:
            components.append(gp_variance)
            weights.append(self.fusion_weights["gp_var"])
        
        # Temperature-scaled confidence
        if self.enable_temperature and confidence_score is not None and self.temp_scaler:
            if self.temp_scaler.is_fitted:
                calibrated_conf = self.temp_scaler.calibrate_scores(
                    np.array([confidence_score])
                )[0]
                # Convert to uncertainty (1 - confidence)
                temp_uncertainty = 1 - calibrated_conf
                components.append(temp_uncertainty)
                weights.append(self.fusion_weights["temp_conf"])
            else:
                components.append(1 - confidence_score)
                weights.append(self.fusion_weights["temp_conf"])
        
        # Conformal interval width
        if self.enable_conformal and prediction is not None and self.conformal:
            if self.conformal.is_fitted:
                interval_width = self.conformal.get_interval_width()
                # Normalize to [0, 1]
                normalized_width = min(interval_width / 10.0, 1.0)
                components.append(normalized_width)
                weights.append(self.fusion_weights["conformal_width"])
        
        # Fuse
        if components:
            # Normalize weights
            total_weight = sum(weights)
            weights = [w / total_weight for w in weights]
            
            # Weighted average
            uncertainty_score = sum(c * w for c, w in zip(components, weights))
        else:
            uncertainty_score = 0.5  # Default
        
        # Get confidence interval
        confidence_intervals: Optional[Any] = None
        if self.enable_conformal and prediction is not None and self.conformal:
            if self.conformal.is_fitted:
                confidence_intervals = self.conformal.predict_interval(
                    np.array([prediction])
                )
        
        return CalibrationResult(
            calibrated_scores=np.array([1 - uncertainty_score]),
            confidence_intervals=confidence_intervals,
            uncertainty_score=uncertainty_score
        )
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "UncertaintyCalibrator":
        """Create calibrator from config"""
        return cls(
            enable_gp=config.get("enable_gp", True),
            enable_temperature=config.get("enable_temperature_scaling", True),
            enable_conformal=config.get("enable_conformal", True),
            fusion_weights=config.get("fusion", {}).get("weights")
        )


def compute_ece(
    confidences: np.ndarray,
    predictions: np.ndarray,
    targets: np.ndarray,
    n_bins: int = 10
) -> float:
    """
    Compute Expected Calibration Error (ECE)
    
    Args:
        confidences: Confidence scores (N,)
        predictions: Predicted classes (N,)
        targets: True classes (N,)
        n_bins: Number of bins
        
    Returns:
        ECE score
    """
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    bin_lowers = bin_boundaries[:-1]
    bin_uppers = bin_boundaries[1:]
    
    ece = 0.0
    for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
        # Find samples in bin
        in_bin = (confidences > bin_lower) & (confidences <= bin_upper)
        prop_in_bin = in_bin.mean()
        
        if prop_in_bin > 0:
            accuracy_in_bin = (predictions[in_bin] == targets[in_bin]).mean()
            avg_confidence_in_bin = confidences[in_bin].mean()
            ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin
    
    return ece
