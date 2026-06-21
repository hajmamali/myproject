"""
Runtime Configuration Validator
================================

Validates MAHOUN runtime configuration at startup to prevent invalid
combinations that could compromise zero-hallucination guarantees.

CRITICAL RULES:
1. desktop_minimal + local graph backend = INVALID
2. Verdict generation requires graph operations
3. Neo4j credentials required for local_full backend
4. Mode-specific resource constraints enforced

This module ensures fail-fast behavior on misconfiguration rather than
runtime failures that could compromise system integrity.
"""

import logging
from dataclasses import dataclass

from mahoun.core.runtime_config import MahounRuntimeSettings, get_runtime_settings

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """Configuration validation error"""

    rule: str
    message: str
    severity: str  # "error" | "warning"
    remediation: str


class ConfigurationError(Exception):
    """Raised when configuration is invalid"""


def validate_runtime_config() -> None:
    """
    Validate runtime configuration at startup.

    Raises:
        ConfigurationError: If configuration is invalid

    Logs:
        Warnings for non-critical issues
        Errors for critical issues
    """
    settings = get_runtime_settings()
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []

    # Run all validation rules
    _validate_mode_graph_consistency(settings, errors, warnings)
    _validate_graph_backend(settings, errors, warnings)
    _validate_neo4j_credentials(settings, errors, warnings)
    _validate_verdict_generation_requirements(settings, errors, warnings)
    _validate_resource_constraints(settings, errors, warnings)

    # Log warnings
    for warning in warnings:
        logger.warning(f"Configuration warning [{warning.rule}]: {warning.message}. Remediation: {warning.remediation}")

    # Raise errors
    if errors:
        error_messages = []
        for error in errors:
            error_messages.append(f"[{error.rule}] {error.message}\n  Remediation: {error.remediation}")

        raise ConfigurationError("Invalid runtime configuration detected:\n\n" + "\n\n".join(error_messages))

    # Log successful validation
    logger.info(
        f"Runtime configuration validated successfully: "
        f"mode={settings.mode}, "
        f"graph_enabled={settings.graph_enabled}, "
        f"graph_backend={settings.graph_backend}"
    )


def _validate_mode_graph_consistency(
    settings: MahounRuntimeSettings, errors: list[ValidationError], warnings: list[ValidationError]
) -> None:
    """
    Rule 1: Mode and graph configuration must be consistent.

    desktop_minimal mode:
    - graph_enabled=False (default) → OK
    - graph_enabled=True + graph_backend=remote → OK
    - graph_enabled=True + graph_backend=local_* → INVALID
    """
    if settings.mode == "desktop_minimal":
        if settings.graph_enabled:
            if settings.graph_backend in ["local_small", "local_full"]:
                errors.append(
                    ValidationError(
                        rule="MODE_GRAPH_CONSISTENCY",
                        message=(
                            f"desktop_minimal mode cannot use local graph backend "
                            f"(graph_backend='{settings.graph_backend}'). "
                            f"Local graph operations require significant resources "
                            f"(>8GB RAM, GPU recommended)."
                        ),
                        severity="error",
                        remediation=(
                            "Choose one of:\n"
                            "  1. Set MAHOUN_GRAPH_BACKEND=remote (use remote graph service)\n"
                            "  2. Set MAHOUN_GRAPH_BACKEND=disabled_fallback (disable graph)\n"
                            "  3. Set MAHOUN_MODE=server_full (enable full features)"
                        ),
                    )
                )


def _validate_graph_backend(
    settings: MahounRuntimeSettings, errors: list[ValidationError], warnings: list[ValidationError]
) -> None:
    """
    Rule 2: Graph backend must be valid for current mode.
    """
    valid_backends = ["disabled_fallback", "local_small", "local_full", "remote"]

    if settings.graph_backend not in valid_backends:
        errors.append(
            ValidationError(
                rule="GRAPH_BACKEND_INVALID",
                message=(
                    f"Invalid graph_backend='{settings.graph_backend}'. Must be one of: {', '.join(valid_backends)}"
                ),
                severity="error",
                remediation=(f"Set MAHOUN_GRAPH_BACKEND to one of: {', '.join(valid_backends)}"),
            )
        )


def _validate_neo4j_credentials(
    settings: MahounRuntimeSettings, errors: list[ValidationError], warnings: list[ValidationError]
) -> None:
    """
    Rule 3: Neo4j credentials required for local graph backends.
    """
    if settings.graph_enabled and settings.graph_backend in ["local_small", "local_full"]:
        # Check Neo4j URI
        if not settings.graph_neo4j_uri or settings.graph_neo4j_uri == "bolt://localhost:7687":
            warnings.append(
                ValidationError(
                    rule="NEO4J_URI_DEFAULT",
                    message=("Using default Neo4j URI (bolt://localhost:7687). Ensure Neo4j is running locally."),
                    severity="warning",
                    remediation=("Set NEO4J_URI environment variable if using custom Neo4j instance"),
                )
            )

        # Check Neo4j password
        if not settings.graph_neo4j_password:
            errors.append(
                ValidationError(
                    rule="NEO4J_PASSWORD_MISSING",
                    message=(
                        f"Neo4j password required for graph_backend='{settings.graph_backend}'. "
                        f"Cannot connect to Neo4j without credentials."
                    ),
                    severity="error",
                    remediation=("Set NEO4J_PASSWORD environment variable with your Neo4j password"),
                )
            )


def _validate_verdict_generation_requirements(
    settings: MahounRuntimeSettings, errors: list[ValidationError], warnings: list[ValidationError]
) -> None:
    """
    Rule 4: Verdict generation requires graph operations.

    This is a WARNING, not an ERROR, because the system can still run
    (e.g., for data ingestion, maintenance), but verdict generation
    will be unavailable.
    """
    if not settings.graph_enabled or settings.graph_backend == "disabled_fallback":
        warnings.append(
            ValidationError(
                rule="VERDICT_GENERATION_UNAVAILABLE",
                message=(
                    "Graph operations disabled - verdict generation will be UNAVAILABLE. "
                    "Evidence-linked verdict engine requires full graph reasoning to "
                    "maintain zero-hallucination guarantee."
                ),
                severity="warning",
                remediation=(
                    "To enable verdict generation:\n"
                    "  1. Set MAHOUN_GRAPH_ENABLED=true\n"
                    "  2. Set MAHOUN_GRAPH_BACKEND=local_full (or remote)\n"
                    "  3. Configure Neo4j credentials (NEO4J_PASSWORD)\n"
                    "  4. Restart the service"
                ),
            )
        )


def _validate_resource_constraints(
    settings: MahounRuntimeSettings, errors: list[ValidationError], warnings: list[ValidationError]
) -> None:
    """
    Rule 5: Validate resource-intensive features against mode.
    """
    if settings.mode == "desktop_minimal":
        # Check LoRA training
        if settings.lora_training_enabled:
            warnings.append(
                ValidationError(
                    rule="LORA_TRAINING_RESOURCE_WARNING",
                    message=(
                        "LoRA training enabled in desktop_minimal mode. "
                        "This may cause performance issues on resource-constrained systems."
                    ),
                    severity="warning",
                    remediation=("Consider setting MAHOUN_LORA_TRAINING_ENABLED=false for desktop_minimal mode"),
                )
            )

        # Check local GPU backends
        if settings.llm_backend == "local_gpu":
            warnings.append(
                ValidationError(
                    rule="LOCAL_GPU_RESOURCE_WARNING",
                    message=(
                        "Local GPU LLM backend enabled in desktop_minimal mode. "
                        "Ensure sufficient GPU memory (>8GB VRAM recommended)."
                    ),
                    severity="warning",
                    remediation=("Consider using MAHOUN_LLM_BACKEND=openai for desktop_minimal mode"),
                )
            )


def validate_config_file(config_path: str) -> None:
    """
    Validate YAML configuration file.

    Args:
        config_path: Path to YAML config file

    Raises:
        ConfigurationError: If config file is invalid
    """
    from pathlib import Path

    import yaml

    config_file = Path(config_path)

    if not config_file.exists():
        raise ConfigurationError(f"Configuration file not found: {config_path}")

    try:
        with open(config_file, encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in configuration file: {e}")

    if not isinstance(config, dict):
        raise ConfigurationError("Configuration file must contain a YAML dictionary")

    # Validate required fields
    if "mode" not in config:
        raise ConfigurationError("Configuration file missing required field: 'mode'")

    valid_modes = ["desktop_minimal", "server_full", "enterprise_graph"]
    if config["mode"] not in valid_modes:
        raise ConfigurationError(f"Invalid mode '{config['mode']}'. Must be one of: {', '.join(valid_modes)}")

    logger.info(f"Configuration file validated: {config_path}")


# Example usage
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    try:
        validate_runtime_config()
        print("✅ Configuration valid")
        sys.exit(0)
    except ConfigurationError as e:
        print(f"❌ Configuration invalid:\n{e}")
        sys.exit(1)
