# Testing Skill

## Purpose
Ensure that changes are validated in a way that protects correctness and architectural integrity.

## When To Apply
Use whenever behavior, architecture, or governance rules are changed or challenged.

## Required Knowledge
- Testing strategy
- Validation expectations
- Relevant repository conventions

## Workflow
1. Identify the behavior or rule under test.
2. Choose the most relevant validation approach.
3. Execute or inspect the validation path.
4. Record results and any residual risk.

## Rules
- Test the observable outcome, not the implementation shortcut.
- Preserve regression coverage for important behavior.

## Forbidden Actions
- Shipping changes without validation.
- Relying on assumptions instead of evidence.

## Quality Gate
Testing is complete when it demonstrates the change is correct and does not introduce obvious regressions.
