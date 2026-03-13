# Metadata
- ID: QRP-XXXX
- Recipient: Manager | Coder
- Parent Request: IRQ-YYYY
- Target Implementation Report: IRP-ZZZZ
- QA Actor: QA-ID
- Implementation Round: 1..N
- Repo: repo-name
- Tested Commit: hash
- Feature Branch: branch-name

Outcome: accepted | changes needed | escalation needed

# Summary
## Context
1-2 sentences describing the testing scope. 
State what was tested (the specific implementation round) and the baseline environment.

## High-level Verdict
2-3 sentences summarizing the quality status.
Is the feature ready for merge? Does it meet the core requirements of the IRQ? Are there critical blockers?

# Test Execution

## New Tests Added
List the new test files or cases created to verify this specific implementation.
Explain *why* these tests were chosen (e.g., "Added `test_edge_case_x.py` to verify the boundary condition mentioned in IRQ").
Confirm that these tests passed.

## Regression & Existing Tests
Report on the status of the existing test suite.
Did any unrelated tests fail? If so, is it a regression or a necessary update?
Confirm that the full suite (or relevant subset) passes.

## Manual & Visual Verification
Describe any manual steps taken to verify behavior that automated tests might miss (e.g., UI glitching, terminal output formatting, user experience flows).
What did you see? Does it look "polished"?

# Implementation Verification

## Adherence to Implementation Request (IRQ)
Did the Coder build what was asked?
- [ ] Core Requirements Met?
- [ ] "Definition of Done" criteria met?
- [ ] Constraints respected?
If "No" to any, explain the gap.

## Verification of Implementation Report (IRP) Claims
The Coder claimed certain changes and logic in their IRP.
Did you verify these claims?
- Are the "Design choices" actually implemented as described?
- Are the "Files touched" consistent with the commit?
- Are the "Edge cases" actually handled?

## Code Quality & Style
Is the code idiomatic and maintainable?
- Comments/Documentation present?
- Naming conventions followed?
- No debug prints or "dead code" left behind?

# Defects & Issues

## Blocking Issues (Must Fix)
List critical bugs, missing requirements, or severe regressions that prevent acceptance.
- **Issue 1**: Description...
- **Issue 2**: Description...

## Non-blocking Issues (Technical Debt / Polish)
List minor issues, suggestions for future refactoring, or edge cases that are acceptable for now but should be noted.
- **Suggestion 1**: ...

# Performance & Safety

## Performance
Did you observe any slowdowns?
Are there any obvious inefficiencies (e.g., O(n^2) loops on large datasets, excessive file I/O)?

## Safety & Security
Are there any risky file operations, potential crashes, or security gaps (e.g., unvalidated input)?

# Recommendation
## Next Steps
Select one:
- **MERGE**: The implementation is solid. Ready for Manager approval.
- **FIX REQUIRED**: Return to Coder (Round N+1). Address the "Blocking Issues" above.
- **ESCALATE**: Requirements are unclear or contradictory. Manager intervention needed.

## Instruction for Coder (if returned)
Specific guidance on what to prioritize in the next round.
