# Detector Development Skill

## Purpose
Guide the development of detectors that consume shared architecture information rather than inventing their own model.

## When To Apply
Use when creating or updating detectors, rules, or architectural checks.

## Required Knowledge
- Detector system concepts
- Rule engine expectations
- Shared architecture model

## Workflow
1. Define the detection objective.
2. Confirm the relevant model and graph inputs.
3. Implement the detector as a consumer of shared data.
4. Validate the result against known examples and edge cases.

## Rules
- Keep detectors focused on observation and reporting.
- Avoid hard-coding assumptions that should come from the model.

## Forbidden Actions
- Building private representations inside detectors.
- Treating detectors as a substitute for architecture.

## Quality Gate
A detector is valuable when it is accurate, maintainable, and clearly scoped.
