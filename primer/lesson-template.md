# Lesson Artifact Template

Every session writes one `LESSON.md` to `lessons/<domain-slug>/<YYYY-MM-DD>-<lesson-slug>.md`. The template is strict — deviations are a smell. The artifact is the unit of value; the conversation is just how it gets made.

## Filename

`lessons/<domain-slug>/<YYYY-MM-DD>-<lesson-slug>.md`

- `domain-slug`: the top-level domain from the learner's `topic-index.md` that this lesson belongs to. Domains are **per-instance**, not a fixed set — they come from the learner's own topic map. (The starter pack happens to ship `ai-agentic`, `distributed-systems`, `event-driven-architecture`, `docker`, `backend-engineering`, but another learner's index will have different ones.)
- `YYYY-MM-DD`: session start date.
- `lesson-slug`: 2–6 hyphenated words, content-bearing (`consensus-and-raft`, not `lesson-3`).

**In-progress state:** while a lesson is unfinished, its resume state lives in a sidecar next to the
(eventual) artifact: `lessons/<domain-slug>/<YYYY-MM-DD>-<lesson-slug>.STATE.md`. `/primer resume` looks for
these. On completion the sidecar is deleted and only the `.md` artifact remains.

`.STATE.md` files are **committed, not gitignored** — they sync across machines so a lesson paused on one
machine can resume on another. Write the sidecar as a **self-contained handoff checkpoint**: capture what the
learner answered (Elicit/Probe), where the diagnosis landed, and what's next — not as a scratchpad that leans
on the live session's in-context memory. Flush it at any natural stopping point before the session ends.

The one thing that does **not** cross machines is the live Claude session transcript itself — the
conversational turns since the last flush. So cross-machine resume picks up from the last checkpoint written
into the sidecar, not mid-dialogue. That residual gap is inherent to interactive sessions; the fix is to
flush often, not to gitignore. (Because the engine enforces max one in-progress session, concurrent edits to
the same sidecar from two machines don't arise; an abandoned sidecar is a cleanup nuisance, not a correctness
issue.)

## Frontmatter

```yaml
---
topic: distributed-systems
slug: 2026-05-09-consensus-and-raft
duration_minutes: 75
zpd_edge_before: <one line — the learner's edge entering this session>
zpd_edge_after:  <one line — what is it now>
sources_consulted:
  - url: https://...
    tag: verified
    accessed: 2026-05-09
  - url: https://...
    tag: from-training
freshness_check: 2026-05-09
prior_lessons_referenced:
  - lessons/distributed-systems/2026-04-22-replication-flavors.md
---
```

## Body sections (in order)

### `# <Lesson Title>`

Title is descriptive, not cute. "Consensus without implementing Paxos" beats "Going deep on consensus".

### `## TL;DR`

3–5 bullets. Each a falsifiable invariant — the thing worth keeping. Written for someone scanning the file in two years to remember whether they covered this.

### `## Where you started`

The Elicit-step anchor: the learner's mental model entering the session. One paragraph. This is the receipts — proof the system actually calibrated rather than running a generic curriculum.

### `## The problem`

Primitives → failure modes. What's the underlying problem before any tool? What specifically goes wrong without one? Concrete, with a named scenario.

### `## The pattern(s)`

Worked example → faded example → free problem. Diagrams inline (Mermaid for sequence/state/flow; ASCII for in-terminal recall).

For multi-pattern lessons (e.g., "outbox vs CDC vs change-streams"), each pattern gets its own subsection.

**Figure specs live here, as HTML comment blocks.** They are invisible in rendered markdown, greppable, hand-editable, and stdlib-parseable — so the artifact stays the single source of truth and the view page is always regenerable from it. One block per figure, next to the prose it supports:

```
<!--primer-figure
{"id":"raft-minority-partition","type":"sequence",
 "caption":"Leader isolated in a minority partition.",
 "invariant":"A leader that cannot reach a majority cannot advance the commit index.",
 "blank":["m3"],
 "reveal":"The majority-side ack. Safety holds by refusing to commit, not by detecting the partition.",
 "spec":{ }}
-->
```

Every figure carries a `caption` and exactly one `invariant`; a blanked figure carries the `reveal`. Form selection and the per-type spec payload are in `primer/diagramming.md`; `primer_view.py templates` prints the schema. The rendered page is `<YYYY-MM-DD>-<slug>.view.html` beside the artifact — a **derived build product**, gitignored in the instance and rebuilt on demand. (Contrast `.STATE.md`, which is checkpoint state and must sync.)

### `## Tradeoffs`

A table. When does pattern X beat Y? Cost axes: operational complexity, latency, consistency, blast radius on failure, team cognitive load. Honest, not advocacy.

### `## Q&A`

The substantive questions the learner asked and how they were answered. Verbatim where it matters. This is high-signal — it captures the *specific* gaps this learner had on this day.

### `## Open threads`

Things pulled-on and set down. Each entry is a one-liner with enough hook to revisit.

> - The CRAQ paper — read before next replication lesson.
> - Why does Postgres logical replication ship deltas, not state? — open.

These also append to `learner/open-questions.md`.

### `## Retrieval prompts`

5–15 atomic Q/A pairs in `Q::A` format (Anki-importable). At least 2 must be deep-reasoning (causal/counterfactual).

**Quality bar (write to it; the easy failure is "prompt-shaped text" — prompts that look right but test the surface phrasing, not the understanding).** Each prompt should be:

- **focused** — one idea per prompt; if the answer is a list, split it.
- **precise** — the question admits one defensible answer; vague questions train vague recall.
- **consistent** — cues the same retrieval each time, so spaced review measures the same thing.
- **tractable** — answerable from what the lesson actually built; not a trivia lookup.
- **effortful** — retrieval, not recognition. No yes/no, no "is X important?".

For *conceptual* material (where LLM-written prompts most often test phrasing), reach for a pattern beyond
definition-recall: **why-it-matters** ("what breaks if you skip X?"), **contrast** ("when does X beat Y, and
when does it lose?"), **application** ("given <concrete situation>, what would you reach for?"), or
**prediction** ("what fails first if <invariant> is removed?"). The deep-reasoning prompts should come from
these, not from reworded definitions.

```
Q:: What's the safety property Raft enforces, in one sentence?
A:: At most one log entry can be committed at a given index across all terms — no two leaders ever commit conflicting entries.

Q:: If a network partition isolates the leader, why doesn't the partition's followers commit log entries?
A:: They lack a majority quorum, so AppendEntries cannot achieve replication-to-majority; the leader on the minority side cannot advance the commit index.
```

These also append to `learner/review-queue.md`.

### `## Sources`

Two sub-lists with URLs and access dates:

- **[verified]** — sources fetched/cited during the session.
- **[from-training, verify]** — claims from model training rather than tool-grounded retrieval. Flagged so future-you knows to verify.

### `## Next`

2–3 follow-on lesson suggestions, with one-line rationale each. Written into `learner/topic-index.md`.

## What NOT to put in a lesson artifact

- Proprietary code. No `~/Work/*` snippets, no internal service names, no employer-identifiable scenarios.
- Filler ("In conclusion...", "Hopefully this was helpful...").
- Fabricated quotes from real engineers.
- Diagrams without captions. Every Mermaid block has a one-line caption above it.
