"""
Causal Effect Estimation
=========================

Estimate causal effects from observational data.
"""


import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from scipy import stats
logger = logging.getLogger(__name__)


class IPWEstimator:
    """
    Inverse Probability Weighting (IPW) for causal effect estimation
    
    Features:
    - Estimate ATE (Average Treatment Effect)
    - Handle confounding
    - Bootstrap confidence intervals
    """
    
    def __init__(self, clip_weights: Tuple[float, float] = (0.01, 100.0)):
        """
        Initialize IPW estimator
        
        Args:
            clip_weights: (min, max) for weight clipping
        """
        self.clip_weights = clip_weights
        
        logger.info("Initialized IPWEstimator")
    
    def estimate_propensity(
        self,
        X: np.ndarray,
        treatment: np.ndarray
    ) -> np.ndarray:
        """
        Estimate propensity scores
        
        Args:
            X: Covariates [N, D]
            treatment: Treatment indicator [N]
            
        Returns:
            Propensity scores [N]
        """
        from sklearn.linear_model import LogisticRegression
        
        model = LogisticRegression(max_iter=1000)
        model.fit(X, treatment)
        
        propensity = model.predict_proba(X)[:, 1]
        
        return propensity
    
    def estimate_ate(
        self,
        X: np.ndarray,
        treatment: np.ndarray,
        outcome: np.ndarray
    ) -> Tuple[float, float]:
        """
        Estimate Average Treatment Effect using IPW
        
        Args:
            X: Covariates [N, D]
            treatment: Treatment indicator [N]
            outcome: Outcome variable [N]
            
        Returns:
            (ate, standard_error)
        """
        # Estimate propensity scores
        propensity = self.estimate_propensity(X, treatment)
        
        # Compute weights
        weights_treated = treatment / np.clip(propensity, *self.clip_weights)
        weights_control = (1 - treatment) / np.clip(1 - propensity, *self.clip_weights)
        
        # Estimate potential outcomes
        y1_hat = np.sum(weights_treated * outcome) / np.sum(weights_treated)
        y0_hat = np.sum(weights_control * outcome) / np.sum(weights_control)
        
        # ATE
        ate = y1_hat - y0_hat
        
        # Standard error (simplified)
        n = len(outcome)
        var_treated = np.var(weights_treated * outcome) / np.sum(weights_treated)
        var_control = np.var(weights_control * outcome) / np.sum(weights_control)
        se = np.sqrt((var_treated + var_control) / n)
        
        logger.info(f"IPW ATE: {ate:.4f} ± {se:.4f}")
        
        return ate, se


class PropensityScoreMatching:
    """
    Propensity Score Matching for causal effect estimation
    
    Features:
    - Match treated and control units
    - Estimate ATT (Average Treatment effect on Treated)
    - Multiple matching methods
    """
    
    def __init__(
        self,
        n_neighbors: int = 1,
        caliper: Optional[float] = None
    ):
        """
        Initialize PSM
        
        Args:
            n_neighbors: Number of matches per treated unit
            caliper: Maximum propensity score distance
        """
        self.n_neighbors = n_neighbors
        self.caliper = caliper
        
        logger.info(f"Initialized PropensityScoreMatching: n_neighbors={n_neighbors}")
    
    def match(
        self,
        propensity_treated: np.ndarray,
        propensity_control: np.ndarray
    ) -> Dict[int, list]:
        """
        Match treated units to control units
        
        Args:
            propensity_treated: Propensity scores for treated
            propensity_control: Propensity scores for control
            
        Returns:
            Dictionary mapping treated index to list of control indices
        """
        matches: Dict[str, Any] = {}
        for i, p_t in enumerate(propensity_treated):
            # Compute distances
            distances = np.abs(propensity_control - p_t)
            
            # Apply caliper
            if self.caliper:
                valid = distances <= self.caliper
                if not np.any(valid):
                    continue
                distances = np.where(valid, distances, np.inf)
            
            # Find k nearest neighbors
            nearest_indices = np.argsort(distances)[:self.n_neighbors]
            
            # Filter out infinite distances
            nearest_indices = [
                idx for idx in nearest_indices
                if distances[idx] != np.inf
            ]
            
            if nearest_indices:
                matches[i] = nearest_indices
        
        return matches
    
    def estimate_att(
        self,
        X: np.ndarray,
        treatment: np.ndarray,
        outcome: np.ndarray
    ) -> Tuple[float, float]:
        """
        Estimate Average Treatment effect on Treated
        
        Args:
            X: Covariates
            treatment: Treatment indicator
            outcome: Outcome variable
            
        Returns:
            (att, standard_error)
        """
        from sklearn.linear_model import LogisticRegression
        
        # Estimate propensity scores
        model = LogisticRegression(max_iter=1000)
        model.fit(X, treatment)
        propensity = model.predict_proba(X)[:, 1]
        
        # Split by treatment
        treated_mask = treatment == 1
        control_mask = treatment == 0
        
        propensity_treated = propensity[treated_mask]
        propensity_control = propensity[control_mask]
        outcome_treated = outcome[treated_mask]
        outcome_control = outcome[control_mask]
        
        # Match
        matches = self.match(propensity_treated, propensity_control)
        
        # Compute ATT
        effects: List[Any] = []
        for treated_idx, control_indices in matches.items():
            y_treated = outcome_treated[treated_idx]
            y_control_matched = outcome_control[control_indices].mean()
            
            effect = y_treated - y_control_matched
            effects.append(effect)
        
        if not effects:
            logger.warning("No matches found")
            return 0.0, 0.0
        
        att = np.mean(effects)
        se = np.std(effects) / np.sqrt(len(effects))
        
        logger.info(f"PSM ATT: {att:.4f} ± {se:.4f} ({len(effects)} matches)")
        
        return att, se


class DoublyRobustEstimator:
    """
    Doubly Robust Estimation
    
    Features:
    - Combines outcome regression and propensity weighting
    - Robust to misspecification of either model
    """
    
    def __init__(self):
        """Initialize doubly robust estimator"""
        logger.info("Initialized DoublyRobustEstimator")
    
    def estimate_ate(
        self,
        X: np.ndarray,
        treatment: np.ndarray,
        outcome: np.ndarray
    ) -> Tuple[float, float]:
        """
        Estimate ATE using doubly robust method
        
        Args:
            X: Covariates
            treatment: Treatment indicator
            outcome: Outcome variable
            
        Returns:
            (ate, standard_error)
        """
        from sklearn.linear_model import LogisticRegression, LinearRegression
        
        n = len(outcome)
        
        # Estimate propensity scores
        prop_model = LogisticRegression(max_iter=1000)
        prop_model.fit(X, treatment)
        propensity = prop_model.predict_proba(X)[:, 1]
        
        # Estimate outcome models
        # Model for treated
        X_treated = X[treatment == 1]
        y_treated = outcome[treatment == 1]
        
        if len(X_treated) > 0:
            model_treated = LinearRegression()
            model_treated.fit(X_treated, y_treated)
            mu1 = model_treated.predict(X)
        else:
            mu1 = np.zeros(n)
        
        # Model for control
        X_control = X[treatment == 0]
        y_control = outcome[treatment == 0]
        
        if len(X_control) > 0:
            model_control = LinearRegression()
            model_control.fit(X_control, y_control)
            mu0 = model_control.predict(X)
        else:
            mu0 = np.zeros(n)
        
        # Doubly robust estimator
        dr_treated = (
            treatment * (outcome - mu1) / np.clip(propensity, 0.01, 0.99) + mu1
        )
        
        dr_control = (
            (1 - treatment) * (outcome - mu0) / np.clip(1 - propensity, 0.01, 0.99) + mu0
        )
        
        ate = np.mean(dr_treated - dr_control)
        se = np.std(dr_treated - dr_control) / np.sqrt(n)
        
        logger.info(f"Doubly Robust ATE: {ate:.4f} ± {se:.4f}")
        
        return ate, se


class BootstrapCI:
    """
    Bootstrap confidence intervals for causal effects
    """
    
    def __init__(self, n_bootstrap: int = 1000, alpha: float = 0.05):
        """
        Initialize bootstrap CI
        
        Args:
            n_bootstrap: Number of bootstrap samples
            alpha: Significance level
        """
        self.n_bootstrap = n_bootstrap
        self.alpha = alpha
        
        logger.info(f"Initialized BootstrapCI: n_bootstrap={n_bootstrap}")
    
    def compute_ci(
        self,
        estimator,
        X: np.ndarray,
        treatment: np.ndarray,
        outcome: np.ndarray
    ) -> Tuple[float, float, float]:
        """
        Compute bootstrap confidence interval
        
        Args:
            estimator: Causal effect estimator
            X: Covariates
            treatment: Treatment
            outcome: Outcome
            
        Returns:
            (point_estimate, lower_ci, upper_ci)
        """
        n = len(outcome)
        estimates: List[Any] = []
        # Point estimate
        point_estimate, _ = estimator.estimate_ate(X, treatment, outcome)
        
        # Bootstrap
        for _ in range(self.n_bootstrap):
            # Resample
            indices = np.random.choice(n, size=n, replace=True)
            X_boot = X[indices]
            treatment_boot = treatment[indices]
            outcome_boot = outcome[indices]
            
            # Estimate
            try:
                est, _ = estimator.estimate_ate(X_boot, treatment_boot, outcome_boot)
                estimates.append(est)
            except (ValueError, RuntimeError, np.linalg.LinAlgError) as e:
                # Bootstrap sample may be degenerate - skip and continue
                logger.debug(f"Bootstrap iteration failed: {e}")
                continue
        
        if not estimates:
            return point_estimate, point_estimate, point_estimate
        
        # Compute CI
        lower = np.percentile(estimates, self.alpha / 2 * 100)
        upper = np.percentile(estimates, (1 - self.alpha / 2) * 100)
        
        logger.info(
            f"Bootstrap CI: {point_estimate:.4f} "
            f"[{lower:.4f}, {upper:.4f}]"
        )
        
        return point_estimate, lower, upper


class CausalEffectEstimator:
    """
    Unified interface for causal effect estimation
    """
    
    def __init__(self, method: str = 'ipw', **kwargs):
        """
        Initialize estimator
        
        Args:
            method: Estimation method ('ipw', 'psm', 'dr')
            **kwargs: Method-specific parameters
        """
        self.method = method
        
        if method == 'ipw':
            self.estimator = IPWEstimator(**kwargs)
        elif method == 'psm':
            self.estimator = PropensityScoreMatching(**kwargs)
        elif method == 'dr':
            self.estimator = DoublyRobustEstimator(**kwargs)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        logger.info(f"Initialized CausalEffectEstimator: method={method}")
    
    def estimate(
        self,
        X: np.ndarray,
        treatment: np.ndarray,
        outcome: np.ndarray,
        bootstrap_ci: bool = False
    ) -> Dict[str, float]:
        """
        Estimate causal effect
        
        Args:
            X: Covariates
            treatment: Treatment
            outcome: Outcome
            bootstrap_ci: Compute bootstrap CI
            
        Returns:
            Dictionary with estimates
        """
        if bootstrap_ci:
            boot = BootstrapCI()
            point, lower, upper = boot.compute_ci(
                self.estimator, X, treatment, outcome
            )
            
            return {
                'estimate': point,
                'ci_lower': lower,
                'ci_upper': upper,
                'method': self.method
            }
        else:
            if self.method == 'psm':
                estimate, se = self.estimator.estimate_att(X, treatment, outcome)
            else:
                estimate, se = self.estimator.estimate_ate(X, treatment, outcome)
            
            return {
                'estimate': estimate,
                'std_error': se,
                'ci_lower': estimate - 1.96 * se,
                'ci_upper': estimate + 1.96 * se,
                'method': self.method
            }
