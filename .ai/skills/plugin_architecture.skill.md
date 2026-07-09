# Plugin Architecture Skill

## Purpose
Guide the design of extensible components that integrate with the repository’s architecture through well-defined interfaces.

## When To Apply
Use when introducing new plugins, extensions, or modular capabilities.

## Required Knowledge
- Plugin architecture principles
- Repository extension points
- Governance standards

## Workflow
1. Identify the extension need.
2. Define the interface and responsibilities.
3. Ensure the plugin fits within the shared model.
4. Validate that the plugin does not weaken boundaries.

## Rules
- Keep plugin boundaries explicit.
- Make extension points stable and documented.

## Forbidden Actions
- Creating implicit coupling between plugins and core logic.
- Allowing plugins to bypass shared architectural controls.

## Quality Gate
A plugin architecture is sound when it is extensible, isolated, and governable.
