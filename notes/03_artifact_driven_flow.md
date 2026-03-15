# Artefact-based 3 Agent Flow

## Roles
- **Human**: 
    - Discusses intent, constraints, general architectural, implementational and QA approach, and final acceptance criteria with Manager-agent. 
    - Receives reports from Manager-agent when desired.
- **Manager agent**: 
    - Gathers all the relevant information to translates human input into two artefacts: an *Implementation Request* (for Coder) and a *QA Request* (for QA).  
    - Reports the status of the tasks to human when asked
- **Coder agent**: Implements based on the *Implementation Request*, optionally using the latest *QA Report*, and produces an *Implementation Report*. 
- **QA agent**: Validates the implementation using the *QA Request*, the latest *Implementation Report*, and (if present) the previous *QA Report*, producing a new *QA Report*. 

## Artefacts
- **Implementation Request (IRQ-…)**: What to build, boundaries, DoD, constraints (created by Manager). 
- **QA Request (QAR-…)**: What to validate, acceptance checks, risk areas (created by Manager). 
- **Implementation Report (IRP-…)**: What changed, why, deviations/tests, handoff (created by Coder each round). 
- **QA Report (QRP-…)**: Validation results; either `to correct` (back to Coder) or `final` (to Manager). 

## Loop / State Machine
1. Human → Manager: discussion, clarifications, priorities. 
2. Manager → (IRQ + QAR): publishes/updates the two requests. 
3. Coder → IRP(round k): implements from IRQ (+ latest QRP if exists), publishes IRP with commit/branch references. 
4. QA → QRP(round k):
   - Inputs: QAR + IRP(k) + QRP(k-1, if any). 
   - Output status:
     - `to correct` → sent to Coder for another round. 
     - `final` → sent to Manager to close/finish. 
5. Round limit: stop after at most **N** QA rounds; the last QRP/IRP must summarize prior attempts and include the “current best” state if the limit is reached. 

## Escalation
- If the loop is oscillating (fix A breaks B repeatedly) or missing information blocks progress, mark the report as `blocked` / `needs info` and escalate to Manager for resolution. 
