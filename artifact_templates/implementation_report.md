# Metadata
- ID: IRP-XXXX
- Outcome: ready | needs info | blocked
- Recepient: QA-ID | Manager
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

# Sumary
## Context
1-2 sentences of the situation before the work started. 

State the pre-work baseline: what the system looked like, what was already implemented, and what the last known status was (including whether this round started from a prior fix attempt or a clean base). This orients QA to what assumptions are safe and what may have been in flux.

## Work performed
2-3 sentences of what changed?

Describe what you changed at a high level and why those changes address the request (and/or the last QA report). Focus on observable outcomes and the main mechanism, not a step-by-step changelog.

# Guideline realization

## Deviations from the Implementation Request and QA report
Should be NONE in principle, UNLESS major unforseen block or issue discocvered. 

In that case list any places where you did not follow the Implementation Request and/or QA Report literally, and explain why (new evidence, constraints, better alignment with goals, or a clarification discovered in code).  Make explicit what risk the deviation introduces and why it is acceptable or requires manager approval. Any? why were they accepted?

## Failing and changed test rationale
Should be NONE in principle, UNLESS past assumptios, interfaces or methods were changed and thus you think some tests are expected to be changed or removed.

In this case explain the reason for all failing or changedtests and why was this accepted?

# Implementation details

## Design & implementation choices 
Explain key design decisions and tradeoffs: the chosen approach, alternatives considered, and why this choice best fits constraints (correctness, maintainability, performance, compatibility). Call out any important invariants, tricky logic, or “gotchas” that QA should keep in mind when validating.

## Files/Modules touched
Enumerate the concrete surface area changed so reviewers can focus their attention and QA can infer likely impact zones. If relevant, note whether changes are localized vs cross-cutting and whether any public APIs/contracts were affected.

## Documentation updates
State what docs/comments/readmes were updated (or not) and why, tied to user/dev-facing behavior changes. If documentation is missing or deferred, explain what should be documented and where.

# Relation to past and future work

## Implementation effort history
What was the trajectory of the implementation effort before this round?
What was attempted/wrong in each round?
How this round relates to this context?

Take special care to detect/point out any possible loops in the implement-test procedure. In prolonged extreme cases this may cause Blocked status and escalation to the Manager.

## Open potential follow-ups, TODOs, out of scope items
Capture anything intentionally left undone, including cleanup, refactors, tests, or edge handling that you discovered but did not address. Explain why each item stayed out of scope (risk, time, permission boundaries, missing requirements) and whether it should be a new task or handled in a later round. 

# Self Assessment

## Edge cases and known limitations
List situations where behavior may still be incorrect or undefined, and why those cases weren’t fully resolved. Include practical guidance: severity, frequency, and how a user or system might encounter the issue so QA can target validation appropriately.

## Performance considerations 
Describe any performance-impacting changes (time, memory, I/O, startup, latency) and why the impact is acceptable. If you did not measure, state that explicitly and provide reasoning based on complexity or expected workloads, plus where performance risk might hide.

## QA handoff 
Translate the implementation into an actionable validation plan: what to test, why those tests matter, and what signals confirm success or regression. Highlight high-risk areas, tricky scenarios, and any setup details (flags, configs, data) QA needs for reliable reproduction.

# References
Links to Design docs, diagrams, prior tasks, discussions.
