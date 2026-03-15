link: https://www.perplexity.ai/search/analize-this-project-specifica-7xRa._21QPCzqTtfJosrgQ#37


# I think I also need to write a blogpost like this repo [https://github.com/steveyegge/gastown](https://github.com/steveyegge/gastown) has this blogpost [https://steve-yegge.medium.com/welcome-to-gas-town-4f25ee16dd04](https://steve-yegge.medium.com/welcome-to-gas-town-4f25ee16dd04) for soft introduction. this formal project description in not enough.

I put some thoughts together (below). Propose a short version of a blogpost similar to the one I posted, that explains the system and approach I advocate in a similar style. Here are my notes, you do not have to stick to them religiously. Actually stat by listing out points and perspectives that should be added. Next look for links, resources, research or posts that would support some of the specific points made and link them as references in the text.

You’re right: a formal spec won’t sell the *why*, the *feel*, or the “this changes your day” story. Below is (1) what to add beyond your notes, then (2) a short blogpost draft in a “Gas Town”-adjacent style (opinionated, concrete, slightly narrative), with references inline.

## Points to add

- The “babysitting trap” as the core experiential problem (why engineers can’t scale beyond one agent).
- The *one scarce resource* framing: “productivity per human attention unit” (your PHA idea), not model benchmarks.
- A clear “what’s new” claim: determinism comes from **workflow + artifacts + git gates**, not from better prompts.
- Explicit separation of **intent**, **execution**, and **verification** (and why mixing them causes self-justifying failure).
- “Repetitive workflows beat clever prompts”: why standardized flows are a feature, not a limitation.
- Human-collaboration integration: Kanban + approvals + traceability as the bridge from solo vibe-coding to teams.
- A small concrete scenario (feature dev loop) with the artifacts produced and how the orchestrator prevents foot-guns.
- Where you agree/disagree with popular orchestration patterns (sequential, maker-checker), and what you hard-enforce.
- Security/abuse angle: why “capability scoping + gates” is not paranoia but an architectural necessity for agentic coding.


## Short blogpost draft (soft intro)

### The problem isn’t that agents can’t code.

It’s that they can’t be trusted to code **unsupervised**.

A year ago “AI-assisted coding” mostly meant autocomplete. Now we have CLI agents that will happily churn through tasks: edit files, run commands, open PRs, “fix” errors, and explain everything with conviction.

And yet, if you ask engineers how they actually use them, you get a recurring pattern:

They pick one task.
They attach to one agent.
And then they watch it like a hawk.

Not because they’re control freaks. Because they’re rational.

If the agent drifts, it doesn’t drift politely. It drifts into refactors, drive-by changes, and architectural violations that turn a 20-minute task into a three-hour whack‑a‑mole cycle. So engineers don’t orchestrate at the project level. They don’t run multiple agents. They babysit one.

That’s the trap: as agents get more capable, **human attention becomes the bottleneck**.

### My metric: productivity per human attention (PHA)

There are lots of resources involved in “vibe-coding”: compute, model quality, context window size, tool access.

But in practice, the limiting resource is human cognitive capacity.

If a system is “productive” only when an engineer is continuously monitoring terminal output, diff-by-diff, then it isn’t scaling engineering—it’s just relocating the work into a higher-stress form of supervision.

So instead of optimizing “lines of code per prompt,” I want to optimize *PHA*: how much real engineering progress happens per unit of human attention.

### The diagnosis: why vibe-coding breaks

In long-running, real-world usage, coding agents tend to fail in a few predictable ways:

1) **Scope drift and constraint violations**
Prompted constraints (“don’t touch X”, “no refactor”) aren’t enforceable the way a compiler error is. Eventually the agent wanders.
2) **Workflow violations**
Review, testing, and version-control discipline are optional unless you make them impossible to bypass. GitHub itself has “rulesets” for requiring PRs, status checks, signed commits, etc.—because humans also need guardrails, and bots definitely do. The platform can block merges unless gates pass. That’s the point.
3) **Informal quality control (leaky separation of duties)**
If the same agent both implements and validates, you get the equivalent of letting a student grade their own exam. You’ll see “coding to pass” instead of verifying requirements.
4) **Context fragmentation**
Once you involve multiple agents or multiple attempts, you get diverging plans, partial implementations, and contradictory explanations. The human becomes the reconciliation engine.
5) **Granularity failure**
There’s no systematic way to zoom out (project status, architectural intent) and zoom back in (terminal-level interventions) without losing control.
6) **Human collaboration mismatch**
Most orgs don’t run on “a genius in a terminal.” They run on boards, handoffs, approvals, traceability. Typical agent workflows don’t map cleanly onto that, so one operator becomes a gateway between agents and everyone else.

### The strategic pivot: limit freedom to increase capability

Here’s the contrarian part:

The way to make agents *more useful* is to make them *less free*.

Not through better prompts. Through **hard workflows**.

If this sounds familiar, it should. We do it everywhere else:

- Databases enforce schemas.
- CI enforces checks.
- Release trains enforce gates.
- Git enforces history.

So why are we letting stochastic systems roam freely through our repos?

### The approach: Kanban-driven agent orchestration

I’m building a system that treats “agentic coding” like a controlled production line rather than an improv session.

Core idea: a project is a **workflow graph** (states + transitions). Every transition requires **artifacts**. The orchestrator enforces the rules. Agents produce the artifacts.

Think of it as: *Kanban as the human interface; git as the state store; artifacts as the truth; local orchestrators as supervisors; agents as workers.*

Concretely:

- **Kanban board (browser UI)** is the project-level truth: what exists, what state it’s in, what’s blocked, what’s next.
- **Manager agent** is the single point of contact: it explains the board, plans the next move, shapes specs, and produces the next “contract artifact.”
- **Local orchestrators** supervise workers: spawn/kill agents, restrict commands, enforce which branch they can touch, and only allow state transitions when required artifacts exist.
- **Git** is not just storage—it’s the control plane: branches/worktrees become sandboxes, and merge gates become enforcement points (PRs, required checks, signed commits, etc.).

This aligns with well-known agent orchestration patterns—especially deterministic/sequential workflows and maker-checker loops—but with a twist: the workflow engine is the *boss*, not the agents.[^1]

### What “artifact-driven” actually means

Instead of trusting chat logs, we require durable outputs.

Example: Feature development might mandate:

- a spec artifact (“MUST / MUST NOT”, invariants, acceptance criteria)
- an implementation report artifact (what changed, what didn’t)
- a QA report artifact (evidence: tests, checks, diffs)

No artifact, no transition.
Wrong artifact, no transition.
Artifact says “blocked,” the workflow stops.

That gives you a clean audit trail, reproducibility, and a stable way for humans to jump in without reconstructing a week of prompt history.

### Why this matters: escaping the babysitting loop

This isn’t about making agents “autonomous.” It’s about making them **governable**.

When workflows are explicit and enforced, engineers can:

- stop staring at the terminal,
- move up to project-level control,
- safely run multiple agents in parallel (where appropriate),
- and integrate the whole thing into how teams already work.

That’s what “PHA optimization” looks like: fewer heroic interventions, more reliable throughput.

### What’s next

If this resonates, the next step is to describe the actual mechanics:

- the workflow definition schema,
- the local orchestrator runtime,
- the exact artifact types,
- and how git discipline is enforced so “ghost commits” and workflow bypasses simply don’t happen.

If you’ve been vibe-coding and thinking “this is amazing, but I don’t trust it,” then: yes. That’s the point. The solution isn’t more vibes. It’s more structure.

***

### Notes on references you can sprinkle in later

- GitHub rulesets / merge gating features (great for “gates exist for a reason”).
- Azure’s agent orchestration patterns (useful for framing sequential pipelines, maker-checker loops, and the warning about coordination complexity).[^1]
- Prompt injection / agent security papers (if you want a “capabilities must be scoped + gated” argument; the arXiv prompt injection paper snippet you found is very on-point).[^2]

If you want, paste the specific tone you like from Yegge’s post (e.g., “jargon-y playful,” “ranty,” “more technical, less narrative”), and I’ll adjust the voice while keeping it short.
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^3][^4][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://arxiv.org/html/2506.06971v1

[^2]: https://arxiv.org/html/2601.17548v1

[^3]: image.jpg

[^4]: https://www.linkedin.com/posts/steveyegge_welcome-to-gas-town-activity-7412601550629437440-hpeJ

[^5]: https://x.com/Steve_Yegge/status/2006835043503845445

[^6]: https://myhub.ai/items/welcome-to-gas-town

[^7]: https://news.ycombinator.com/item?id=46458936

[^8]: https://www.youtube.com/watch?v=-0_8gPam4tM\&list=UU9rJrMVgcXTfa8xuMnbhAEA

[^9]: https://github.com/steveyegge/gastown/blob/main/LICENSE

[^10]: https://www.youtube.com/watch?v=APojy4uF3Po

[^11]: https://libraries.io/go/github.com%2Fsteveyegge%2Fgastown

[^12]: https://arxiv.org/html/2510.23883v1

[^13]: https://www.youtube.com/watch?v=ZfL8ggfiK7o

[^14]: https://www.sourcepulse.org/projects/21857965

[^15]: https://www.linkedin.com/posts/tvykruta_founders-quick-heads-up-on-something-you-activity-7423044789018804225-F1iI

[^16]: https://news.ycombinator.com/item?id=46679906

