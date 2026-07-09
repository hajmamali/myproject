# Engineering Standards

## Purpose
This document defines the engineering standards expected for work in this repository. It is intended to preserve quality, reduce rework, and make collaboration reliable.

## Scope
These standards apply to implementation work, architectural changes, analysis logic, tests, and documentation.

## Coding Standards
- Write code that is explicit, readable, and maintainable.
- Favor clear names and coherent abstractions.
- Keep functions and modules focused on a single responsibility.
- Avoid hidden side effects and unnecessary complexity.

## Design Standards
- Prefer composition and shared interfaces over duplication.
- Isolate concerns and preserve modularity.
- Keep dependencies intentional and documented.
- Design for extension before optimization.

## Testing Standards
- Validate behavior with targeted tests.
- Cover architectural regressions as well as functional changes.
- Prefer tests that verify observable outcomes.
- Preserve testing discipline even when the change is documentation-only.

## Documentation Standards
- Document intent, boundaries, assumptions, and trade-offs.
- Keep architecture guidance aligned with implementation reality.
- Update documentation when behavior or design changes.

## Maintainability Rules
- Reduce cognitive load.
- Avoid introducing brittle shortcuts.
- Ensure code can be reasoned about by future agents and engineers.

## Rules
- Do not merge changes that lack adequate explanation.
- Do not add complexity without a clear architectural justification.
- Do not bypass review because a change appears trivial.

## Expected Behavior
Contributors should make work understandable to others and robust to future change.

## Anti-Patterns
- Copy-paste implementation with minimal abstraction.
- Overly clever code that obscures intent.
- Silent dependency growth without review.

## Quality Criteria
Standards are met when the work is correct, maintainable, documented, and consistent with the repository architecture.
