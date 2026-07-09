# Agent Workflow

## Purpose
This workflow defines the mandatory operating process for AI agents working in this repository. It ensures that action is grounded in context, architecture, and evidence.

## Scope
It applies to feature work, bug fixes, architectural changes, and governance-related analysis.

## Mandatory Workflow
1. Understand context
   - Read the request, surrounding files, and repository guidance.
   - Identify constraints, expected outcomes, and relevant architecture boundaries.

2. Inspect architecture
   - Review the relevant architecture documents, project model, and existing abstractions.
   - Confirm whether the change fits the model or requires a governed exception.

3. Create plan
   - Outline the intended change, affected components, risks, and validation steps.
   - Avoid implementation before the plan is clear.

4. Perform architecture review
   - Evaluate whether the planned change introduces drift, duplication, or unnecessary coupling.
   - Challenge the plan if it conflicts with repository principles.

5. Implement
   - Make the minimal change that advances the objective without violating architectural rules.
   - Preserve existing behavior unless the task explicitly requires change.

6. Test
   - Run or inspect the relevant validation path.
   - Confirm that the change is consistent with the intended outcome.

7. Report
   - Summarize what changed, why it changed, what was validated, and what risks remain.

## Rules
- Do not skip a step because the request appears simple.
- Do not implement before understanding the architecture.
- Do not hide uncertainty; report it.

## Expected Behavior
Agents should move through work in a disciplined sequence that preserves quality and governance.

## Anti-Patterns
- Jumping directly to code changes without analysis.
- Reporting completion without evidence.
- Treating review as a formality rather than a control.

## Quality Criteria
A workflow is successful when it produces a clear plan, a well-scoped implementation, and a transparent validation report.
