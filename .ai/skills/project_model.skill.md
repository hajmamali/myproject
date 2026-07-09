# Project Model Skill

## Purpose
Protect the integrity of the ProjectModel as the single source of truth for repository architecture.

## When To Apply
Use when changes affect structure, ownership, relationships, or repository interpretation.

## Required Knowledge
- ProjectModel concept
- Architecture definitions
- Repository conventions

## Workflow
1. Confirm the relevant model state.
2. Evaluate the intended change against this model.
3. Update the model only through approved architectural channels.
4. Verify that downstream analysis remains consistent.

## Rules
- Treat the ProjectModel as authoritative.
- Avoid introducing parallel representations.

## Forbidden Actions
- Creating competing interpretations of repository structure.
- Updating the model without reflecting the underlying architectural change.

## Quality Gate
The model remains trustworthy only when it is consistent, current, and shared.
