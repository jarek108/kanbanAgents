# Metadata
- ID: IRP-XXXX
- Status: ready | needs info | blocked
- Recipient: QA-ID | Manager
- Parent Request: IRQ-YYYY
- Implementing Actor: Coder-ID
- Implementation Round: 1..N
- Last Implementation Report: None | IRP-ZZZZ
- Last QA Report: None | QRP-YYYY
- Repo: repo-name
- Result Commit: hash
- Base Commit: Start Hash for this round of implementation
- Original Base Commit: Starting hash from the Implementation Request
- Feature Branch: branch-name

# Summary
## Context
State the pre-work baseline in 1-2 sentences. What did the system look like before this specific round? Explicitly state if this round started from a prior fix attempt or a clean base to orient QA on what assumptions are safe.

## Work performed
Describe what changed in 2-3 sentences. Focus on observable outcomes and the main mechanism used to address the request (or the previous QA report), rather than a step-by-step changelog.

# Guideline realization

## Deviations from the Implementation Request and QA report
**Default: NONE.** 
Only list content here if there is a major unforeseen block or discovery. If deviations exist, explain strictly why the Implementation Request/QA Report could not be followed literally (e.g., new evidence, technical impossibility). Explicitly state the risk this deviation introduces.

## Failing and changed test rationale
**Default: NONE.** 
If tests are failing, or if you modified/deleted existing tests to make the build pass, list them here. Explain why the logic was changed or why the failure is acceptable for this round.

# Implementation details

## Design & implementation choices 
Explain key design decisions and tradeoffs. Why does this approach best fit the constraints (correctness, maintainability, performance)? Call out any invariants, tricky logic, or "gotchas" QA must be aware of.

## Files/Modules touched
Enumerate the concrete surface area changed. Note whether changes are localized vs. cross-cutting and if public APIs were affected.

## Documentation updates
State what docs/comments/readmes were updated and why. If documentation was required but deferred, explain where and why.

# Relation to past and future work

## Implementation effort history
Summarize the trajectory of the implementation effort.
1. What was attempted in previous rounds?
2. How does this round differ from previous failures?
3. **Loop Detection:** Analyze if we are oscillating between two imperfect states. If a fix is reverting a previous fix, mark Status as BLOCKED and request Manager intervention.

## Open potential follow-ups, TODOs, out of scope items
Capture anything intentionally left undone (refactors, edge handling, cleanup). Explain why it is out of scope for *this* specific task ID.

# Self Assessment

## Edge cases and known limitations
List situations where behavior may still be incorrect or undefined. Provide practical guidance: severity, frequency, and how to trigger the issue so QA can target validation.

## Performance considerations 
Describe performance-impacting changes (time, memory, I/O). If not measured, provide reasoning based on complexity.

## QA handoff 
Translate the implementation into an actionable validation plan. 
- What specific signals confirm success?
- What are the high-risk areas?
- Are there specific flags, configs, or data setups required for reproduction?

# References
Links to Design docs, diagrams, prior tasks, discussions.
