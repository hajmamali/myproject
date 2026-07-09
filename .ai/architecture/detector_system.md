# Detector System

## Purpose
Describe how detectors observe repository state without replacing the shared architecture model.

## Responsibilities
- Identify patterns, risks, anomalies, or architectural concerns.
- Report findings grounded in shared analysis structures.
- Support governance and review workflows.

## Data Flow
Detectors consume the ProjectModel and graph layers to produce evidence-based findings.

## Boundaries
Detectors must remain consumers of architecture, not producers of independent structure.

## Interfaces
They should expose findings with clear rationale and supporting context.

## Failure Modes
- Duplicated analysis logic.
- Weak evidence or ambiguous conclusions.
- Overfitting to specific implementation details.

## Future Evolution
The detector system should expand as new governance concerns become relevant.
