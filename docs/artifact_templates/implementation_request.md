# Metadata
ID: IRQ-XXXX  
Recepient: Coder-ID  
Repo: repo-name
Base Commit: Hash of commit agent *starts work on*, or `TBD` if not branched yet.

# Summary
1–2 sentences describing the task’s purpose and expected outcome.  
Include what “done” looks like at a glance (e.g., “adds X behavior” or “fixes Y bug”), not the how.

# Problem statement
What is wrong / missing (current missing feature, limitation, or bug).  
Why it matters

# Expected Behavior
Primary behavior changes/additions.  
Key edge cases/failure modes.  
Component interactions.

# Goals
What outcome is expected and why it matters in broader context.  
List 2–5 concrete goals (e.g., correctness, performance threshold, compatibility, maintainability)

# Non-goals
Explicitly limited scope to prevent “helpful” extra work.  
Call out adjacent improvements that are intentionally deferred (even if tempting).

# Definition of Done
Existing tests are passing
Code refactored and cleaned up, old code removed
Documentation updated to reflect changes
Visua inspection confirms changes are as expected

# Implementation Guidance
High-level direction (desired shape, not step-by-step instructions).  
Preferred approaches/algorithms and what to avoid if relevant.  
Components to reuse/extend, and expected quality signals (tests, logging, readability).

# Constraints, Assumptions, 'Why nots'
System preconditions.  
Performance/security limits.  
Explicit “why not X” decisions already made (with brief rationale)

# Allowed architectural Scope
Define the implementation boundaries, ranging from broad architectural layers (e.g., "UI components only", "Backend services") to surgical permissions (e.g., "only modify method X", "touch specific file Y"). Explicitly state if adding new files, extending APIs, or refactoring logic is permitted within these boundaries; anything not listed here is assumed out of bounds.

# Disallowed architectural Scope
List specific areas, layers, or components that must be preserved exactly as is to prevent unintended side effects. Use this to block access to general domains (e.g., "do not touch the DB schema") or specific protected code artifacts (e.g., "do not modify the `legacy_auth` function"). Mention specific invariants or critical subsystems that must not be impacted.

# References
Links to Design docs, diagrams, prior tasks, discussions.

