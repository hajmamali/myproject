"""
Uncertainty Estimation using Gaussian Processes
================================================

Quantify prediction uncertainty for legal AI decisions.
Extracted and upgraded from legacy codebase.

Features:
- Gaussian Process regression
- Confidence intervals
- Uncertainty quantification
- Calibration metrics
"""


import torch
import gpytorch
from gpytorch.models import ExactGP
from gpytorch.means import ConstantMean
from gpytorch.kernels import ScaleKernel, RBFKernel
from gpytorch.distributions import MultivariateNormal
from typing import Tuple, Optional, List, Dict

from core.models import UncertaintyEstimate
from mahoun.pipelines._logging import setup_logger

log = setup_logger("uncertainty_estimator")


class LegalGaussianProcess(ExactGP):
    """
    Gaussian Process for legal prediction uncertainty

    Upgraded from legacy code with:
    - Better initialization
    - Configurable kernels
    - Type hints
    """

    def __init__(
        self,
        train_x: torch.Tensor,
        train_y: torch.Tensor,
        likelihood: gpytorch.likelihoods.Likelihood,
    ):
        """
        Initialize Gaussian Process

        Args:
            train_x: Training features [N, D]
            train_y: Training targets [N]
            likelihood: GP likelihood
        """
        super(LegalGaussianProcess, self).__init__(train_x, train_y, likelihood)

        self.mean_module = ConstantMean()
        self.covar_module = ScaleKernel(RBFKernel())

        log.info(
            f"Initialized LegalGaussianProcess with "
            f"{train_x.shape[0]} training points, "
            f"feature_dim={train_x.shape[1]}"
        )

    def forward(self, x: torch.Tensor) -> MultivariateNormal:
        """
        Forward pass through GP

        Args:
            x: Input features [N, D]

        Returns:
            Multivariate normal distribution
        """
        mean_x = self.mean_module(x)
        covar_x = self.covar_module(x)
        return MultivariateNormal(mean_x, covar_x)


class UncertaintyEstimator:
    """
    Estimate prediction uncertainty using Gaussian Processes

    Features:
    - Train GP on features and targets
    - Predict with uncertainty estimates
    - Compute confidence intervals
    - Calibration analysis

    Upgraded from legacy code with:
    - Pydantic models for output
    - Better error handling
    - Configurable parameters
    - Device management
    """

    def __init__(
        self, feature_dim: int = 64, device: str = "cuda" if torch.cuda.is_available() else "cpu"
    ):
        """
        Initialize Uncertainty Estimator

        Args:
            feature_dim: Dimension of input features
            device: Device for computation
        """
        self.feature_dim = feature_dim
        self.device = device
        self.likelihood = gpytorch.likelihoods.GaussianLikelihood().to(device)
        self.model: Optional[LegalGaussianProcess] = None
        self.is_trained = False

        log.info(
            f"Initialized UncertaintyEstimator: " f"feature_dim={feature_dim}, device={device}"
        )

    def fit(
        self,
        features: torch.Tensor,
        targets: torch.Tensor,
        num_iterations: int = 100,
        learning_rate: float = 0.1,
        verbose: bool = True,
    ) -> Dict[str, List[float]]:
        """
        Train Gaussian Process on features and targets

        Args:
            features: Training features [N, D]
            targets: Training targets [N]
            num_iterations: Number of training iterations
            learning_rate: Learning rate for optimizer
            verbose: Print training progress

        Returns:
            Training history (losses)
        """
        try:
            # Move to device
            features = features.to(self.device)
            targets = targets.to(self.device)

            # Validate dimensions
            if features.shape[1] != self.feature_dim:
                log.warning(
                    f"Feature dimension mismatch: expected {self.feature_dim}, "
                    f"got {features.shape[1]}. Updating feature_dim."
                )
                self.feature_dim = features.shape[1]

            # Initialize model
            self.model = LegalGaussianProcess(features, targets, self.likelihood)
            self.model = self.model.to(self.device)
            self.model.train()
            self.likelihood.train()

            # Optimizer
            optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)

            # Loss function
            mll = gpytorch.mlls.ExactMarginalLogLikelihood(self.likelihood, self.model)

            # Training loop
            losses = []

            for i in range(num_iterations):
                optimizer.zero_grad()
                output = self.model(features)
                loss = -mll(output, targets)
                loss.backward()
                optimizer.step()

                losses.append(loss.item())

                if verbose and (i % 20 == 0 or i == num_iterations - 1):
                    log.debug(
                        f"GP training iteration {i}/{num_iterations}, " f"loss: {loss.item():.4f}"
                    )

            self.is_trained = True
            log.info(
                f"GP training completed: {num_iterations} iterations, "
                f"final loss: {losses[-1]:.4f}"
            )

            return {"losses": losses}

        except Exception as e:
            log.error(f"Error training Gaussian Process: {e}")
            raise

    def predict_with_uncertainty(self, features: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Predict with uncertainty estimates

        Args:
            features: Input features [N, D]

        Returns:
            mean: Mean predictions [N]
            uncertainty: Uncertainty (std dev) [N]
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")

        # Move to device
        features = features.to(self.device)

        # Set to eval mode
        self.model.eval()
        self.likelihood.eval()

        # Predict
        with torch.no_grad(), gpytorch.settings.fast_pred_var():
            observed_pred = self.likelihood(self.model(features))
            mean = observed_pred.mean
            uncertainty = observed_pred.variance.sqrt()

        return mean, uncertainty

    def get_confidence_interval(
        self, features: torch.Tensor, confidence: float = 0.95
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Get confidence intervals for predictions

        Args:
            features: Input features [N, D]
            confidence: Confidence level (0.95 or 0.99)

        Returns:
            lower: Lower confidence bounds [N]
            upper: Upper confidence bounds [N]
        """
        mean, uncertainty = self.predict_with_uncertainty(features)

        # Calculate z-score for confidence level
        if confidence == 0.95:
            z_score = 1.96
        elif confidence == 0.99:
            z_score = 2.58
        else:
            # Approximate z-score
            from scipy import stats

            z_score = stats.norm.ppf((1 + confidence) / 2)

        z_score = torch.tensor(z_score, device=self.device)

        lower = mean - z_score * uncertainty
        upper = mean + z_score * uncertainty

        return lower, upper

    def estimate_uncertainty(
        self, features: torch.Tensor, confidence_level: float = 0.95
    ) -> UncertaintyEstimate:
        """
        Get uncertainty estimate as Pydantic model

        Args:
            features: Input features [1, D] (single sample)
            confidence_level: Confidence level for intervals

        Returns:
            UncertaintyEstimate model
        """
        if features.dim() == 1:
            features = features.unsqueeze(0)

        mean, uncertainty = self.predict_with_uncertainty(features)
        lower, upper = self.get_confidence_interval(features, confidence_level)

        return UncertaintyEstimate(
            mean=mean[0].item(),
            uncertainty=uncertainty[0].item(),
            confidence_level=confidence_level,
            lower_bound=lower[0].item(),
            upper_bound=upper[0].item(),
        )

    def calibration_analysis(
        self, features: torch.Tensor, true_values: torch.Tensor
    ) -> Dict[str, float]:
        """
        Analyze calibration of uncertainty estimates

        Args:
            features: Test features [N, D]
            true_values: True target values [N]

        Returns:
            Calibration metrics
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before calibration analysis")

        mean, uncertainty = self.predict_with_uncertainty(features)

        # Compute errors
        errors = torch.abs(mean - true_values)

        # Correlation between uncertainty and error
        correlation = torch.corrcoef(torch.stack([uncertainty, errors]))[0, 1].item()

        # Mean calibration error
        # (uncertainty should match actual error)
        calibration_error = torch.mean(torch.abs(uncertainty - errors)).item()

        # Fraction of points within 1-sigma
        within_1sigma = (errors <= uncertainty).float().mean().item()

        # Fraction within 2-sigma
        within_2sigma = (errors <= 2 * uncertainty).float().mean().item()

        return {
            "uncertainty_error_correlation": correlation,
            "mean_calibration_error": calibration_error,
            "within_1sigma": within_1sigma,
            "within_2sigma": within_2sigma,
            "mean_uncertainty": uncertainty.mean().item(),
            "mean_error": errors.mean().item(),
        }

    def save(self, path: str):
        """Save model state"""
        if not self.is_trained:
            raise ValueError("Cannot save untrained model")

        torch.save(
            {
                "model_state_dict": self.model.state_dict(),
                "likelihood_state_dict": self.likelihood.state_dict(),
                "feature_dim": self.feature_dim,
                "is_trained": self.is_trained,
            },
            path,
        )

        log.info(f"Saved uncertainty estimator to {path}")

    def load(self, path: str, train_x: torch.Tensor, train_y: torch.Tensor):
        """Load model state"""
        checkpoint = torch.load(path, map_location=self.device)

        self.feature_dim = checkpoint["feature_dim"]
        self.is_trained = checkpoint["is_trained"]

        # Reinitialize model
        self.model = LegalGaussianProcess(train_x, train_y, self.likelihood)
        self.model = self.model.to(self.device)

        # Load state
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.likelihood.load_state_dict(checkpoint["likelihood_state_dict"])

        log.info(f"Loaded uncertainty estimator from {path}")
    
    def update(
        self,
        new_features: torch.Tensor,
        new_targets: torch.Tensor,
        max_training_samples: int = 1000,
        num_iterations: int = 50,
        learning_rate: float = 0.1,
        verbose: bool = False
    ) -> Dict[str, List[float]]:
        """
        Incrementally update GP with new data (online learning)
        
        Uses sliding window to keep recent N samples for efficiency.
        
        Args:
            new_features: New training features [M, D]
            new_targets: New training targets [M]
            max_training_samples: Maximum number of samples to keep (sliding window)
            num_iterations: Number of training iterations
            learning_rate: Learning rate for optimizer
            verbose: Print training progress
            
        Returns:
            Training history
        """
        try:
            if not self.is_trained:
                # First time training
                log.info("No existing model, performing initial training")
                return self.fit(
                    new_features,
                    new_targets,
                    num_iterations=num_iterations,
                    learning_rate=learning_rate,
                    verbose=verbose
                )
            
            # Get existing training data
            old_features = self.model.train_inputs[0]
            old_targets = self.model.train_targets
            
            # Combine old and new data
            combined_features = torch.cat([old_features, new_features.to(self.device)], dim=0)
            combined_targets = torch.cat([old_targets, new_targets.to(self.device)], dim=0)
            
            # Apply sliding window if needed
            if combined_features.shape[0] > max_training_samples:
                # Keep most recent samples
                combined_features = combined_features[-max_training_samples:]
                combined_targets = combined_targets[-max_training_samples:]
                log.info(
                    f"Applied sliding window: kept {max_training_samples} most recent samples"
                )
            
            log.info(
                f"Incremental training: {old_features.shape[0]} old + "
                f"{new_features.shape[0]} new = {combined_features.shape[0]} total samples"
            )
            
            # Retrain with combined data (warm start from existing parameters)
            old_state = self.model.state_dict()
            
            # Reinitialize model with new data
            self.model = LegalGaussianProcess(
                combined_features,
                combined_targets,
                self.likelihood
            )
            self.model = self.model.to(self.device)
            
            # Warm start: load previous parameters
            try:
                self.model.load_state_dict(old_state, strict=False)
                log.debug("Warm start: loaded previous model parameters")
            except Exception as e:
                log.warning(f"Could not warm start model: {e}")
            
            self.model.train()
            self.likelihood.train()
            
            # Optimizer
            optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
            
            # Loss function
            mll = gpytorch.mlls.ExactMarginalLogLikelihood(self.likelihood, self.model)
            
            # Training loop
            losses = []
            
            for i in range(num_iterations):
                optimizer.zero_grad()
                output = self.model(combined_features)
                loss = -mll(output, combined_targets)
                loss.backward()
                optimizer.step()
                
                losses.append(loss.item())
                
                if verbose and (i % 10 == 0 or i == num_iterations - 1):
                    log.debug(
                        f"Incremental training iteration {i}/{num_iterations}, "
                        f"loss: {loss.item():.4f}"
                    )
            
            log.info(
                f"Incremental training completed: {num_iterations} iterations, "
                f"final loss: {losses[-1]:.4f}"
            )
            
            return {"losses": losses}
            
        except Exception as e:
            log.error(f"Error in incremental training: {e}")
            raise
    
    def estimate_uncertainty_batch(
        self,
        features: torch.Tensor,
        confidence_level: float = 0.95,
        batch_size: int = 32
    ) -> List[UncertaintyEstimate]:
        """
        Estimate uncertainty for batch of samples (optimized for efficiency)
        
        Args:
            features: Input features [N, D]
            confidence_level: Confidence level for intervals
            batch_size: Batch size for processing (for memory efficiency)
            
        Returns:
            List of UncertaintyEstimate objects
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")
        
        if features.dim() == 1:
            features = features.unsqueeze(0)
        
        num_samples = features.shape[0]
        estimates = []
        
        # Process in batches
        for i in range(0, num_samples, batch_size):
            batch_features = features[i:i + batch_size]
            
            # Get predictions
            mean, uncertainty = self.predict_with_uncertainty(batch_features)
            lower, upper = self.get_confidence_interval(batch_features, confidence_level)
            
            # Create UncertaintyEstimate objects
            for j in range(batch_features.shape[0]):
                estimate = UncertaintyEstimate(
                    mean=mean[j].item(),
                    uncertainty=uncertainty[j].item(),
                    confidence_level=confidence_level,
                    lower_bound=lower[j].item(),
                    upper_bound=upper[j].item(),
                )
                estimates.append(estimate)
        
        log.debug(f"Batch uncertainty estimation completed for {num_samples} samples")
        
        return estimates
