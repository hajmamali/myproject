# Rule Engine Skill

## Purpose
Guide the design and maintenance of rules that enforce architectural and governance constraints.

## When To Apply
Use when defining rules, evaluating policies, or improving enforcement logic.

## Required Knowledge
- Rule engine architecture
- Governance principles
- ProjectModel semantics

## Workflow
1. Clarify the intended constraint.
2. Identify the relevant source of truth.
3. Implement the rule with explicit scope and rationale.
4. Validate the rule against representative scenarios.

## Rules
- Keep rules precise, understandable, and explainable.
- Avoid coupling rules to incidental implementation details.

## Forbidden Actions
- Writing vague or overly broad rules.
- Encoding policy in hidden or duplicated logic.

## Quality Gate
A rule is effective when it is enforceable, comprehensible, and aligned with architectural goals.
