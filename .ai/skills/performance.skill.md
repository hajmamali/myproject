# Performance Skill

## Purpose
Guide changes so they preserve or improve performance while maintaining architectural discipline.

## When To Apply
Use when evaluating the cost of a change, especially around algorithms, traversal, or large-scale analysis.

## Required Knowledge
- Performance constraints
- Architectural boundaries
- Repository scale expectations

## Workflow
1. Understand the performance concern.
2. Measure or reason about the relevant cost profile.
3. Choose a change that preserves scalability.
4. Report trade-offs and risks.

## Rules
- Avoid performance changes that undermine clarity or correctness.
- Prefer scalable structure over local optimization.

## Forbidden Actions
- Introducing premature optimization that obscures architecture.
- Ignoring scaling implications in graph or analysis workflows.

## Quality Gate
Performance work is acceptable when it improves efficiency without compromising maintainability or correctness.
