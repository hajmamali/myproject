"""
Core Data Models for MAHOUN - Compatibility Shim

This module provides backward compatibility for core data models that have been 
moved to their canonical locations as part of the architectural consolidation.

ARCHITECTURAL NOTICE: This is a compatibility shim. Models have been moved to:
- AI models → mahoun.ai.models
- Audit models → mahoun.audit.models  
- Infrastructure models → mahoun.infrastructure.models

G-0 FREEZE STATUS: These models are candidates for G-0 freeze
and should not be modified without architecture review.
"""

# Import reasoning and legal models from the reasoning module (FIRST for immediate availability)
from .reasoning import (
    ReasoningStep,
    ReasoningResult,
    CausalRelation,
    LegalDocument,
    LegalDocType,
    LegalEntity,
    UncertaintyEstimate,
    RetrievalResult,
)

# Import Phase 2B Semantic models
from .semantic import (
    VerificationStatus,
    SemanticIdentity,
    SemanticFact,
    SemanticAssertion,
    ConditionClause,
    SanctionClause,
    ExceptionClause,
    ArticleDecomposition,
)

# Import entity system
from .entity import (
    Entity,
    EntityType,
    FrozenEntity,
    EntityFactory,
    EntityNormalizer,
    EntityFingerprint,
    EntityValidationError,
    # Legacy aliases for backward compatibility
    LegacyEntity,
    NEREntity,
    GraphEntity,
    RAGEntity,
    EvidenceEntity,
    create_entity,
    normalize_text
)

# Import from canonical locations - AI models
from mahoun.ai.models import (
    AIResponse,
    TokenUsage,
    GenerationMetadata,
    ResponseStatus,
    create_success_response,
    create_error_response,
    PromptTemplate,
    EvidenceSlot,
    ContextRequirement,
    EvidenceSlotType,
    LEGAL_REASONING_TEMPLATE,
    CONTRACT_ANALYSIS_TEMPLATE,
    create_custom_template
)

# Import from canonical locations - Audit models
from mahoun.audit.models import (
    AuditEvent,
    AuditEventType,
    AuditContext,
    AuditSeverity,
    create_audit_event,
    create_model_load_event,
    create_generation_event,
    create_fortress_validation_event,
    create_governance_violation_event,
    create_security_breach_event
)

# Import from canonical locations - Infrastructure models
from mahoun.infrastructure.models import (
    DeploymentProfile,
    ResourceLimits,
    PerformanceTargets,
    ProfileType,
    DESKTOP_MINIMAL,
    ENTERPRISE_FULL,
    load_profile_from_env,
    validate_profile_compatibility,
    create_custom_profile
)

__all__ = [
    # Reasoning
    "ReasoningStep",
    "ReasoningResult",
    "CausalRelation",
    "LegalDocument",
    "LegalDocType",
    "UncertaintyEstimate",
    "RetrievalResult",
    
    # AI Response
    "AIResponse",
    "TokenUsage", 
    "GenerationMetadata",
    "ResponseStatus",
    "create_success_response",
    "create_error_response",
    
    # Prompt Template
    "PromptTemplate",
    "EvidenceSlot",
    "ContextRequirement",
    "EvidenceSlotType",
    "LEGAL_REASONING_TEMPLATE",
    "CONTRACT_ANALYSIS_TEMPLATE",
    "create_custom_template",
    
    # Audit Event
    "AuditEvent",
    "AuditEventType",
    "AuditContext",
    "AuditSeverity",
    "create_audit_event",
    "create_model_load_event",
    "create_generation_event",
    "create_fortress_validation_event",
    "create_governance_violation_event",
    "create_security_breach_event",
    
    # Deployment Profile
    "DeploymentProfile",
    "ResourceLimits",
    "PerformanceTargets",
    "ProfileType",
    "DESKTOP_MINIMAL",
    "ENTERPRISE_FULL",
    "load_profile_from_env",
    "validate_profile_compatibility",
    "create_custom_profile",
    
    # 🚀 Ultra-Advanced Entity System
    "Entity",
    "EntityType", 
    "FrozenEntity",
    "LegalEntity",
    "EntityFactory",
    "EntityNormalizer",
    "EntityFingerprint",
    "EntityValidationError",
    # Legacy aliases  
    "LegacyEntity",
    "NEREntity",
    "GraphEntity", 
    "RAGEntity", 
    "EvidenceEntity",
    "create_entity",
]