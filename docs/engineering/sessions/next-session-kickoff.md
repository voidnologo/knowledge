# Kick-off prompt — first instrumented lesson (engine v0.5.2)

> Paste the block below to start a fresh session. It exists because v0.5.2 shipped a lot of engine surface that was written and tested but **never watched execute**, and the first real lesson is the only place several of those paths run at all.

---

Today has two deliverables, and the second one is the reason this session exists.

**1. Run a real lesson.** Not a simulation and not a demo — I'm the learner, teach me something I actually want to know. The lesson's quality comes first. If instrumenting it would degrade it, degrade the instrumenting.

**2. Report on the engine.** primer v0.5.2 shipped a large amount of new machinery that has unit tests but has never been observed running end to end in a live lesson. You are the first person to see it work or not work. Collect that.

## Setup you should know

- Engine (public core): `/Users/salt/personal/primer` — this is also `~/.claude/skills/primer` via symlink. Version in `VERSION`.
- My private instance: `/Users/salt/personal/primer-data` (resolved from `~/.config/primer/config`). Profile, depth markers, lessons, ledger.
- Design record: `docs/engineering/` — `GOALS.md` (north star + non-negotiables), `DECISIONS.md` (D-0022…D-0027 are all from the last session), `proposals/0003-*.md`.
- Five test suites under `tools/`, all green. CI runs them on 3.11 and 3.13.

Start with `/primer resume` — there's an in-progress `async-event-loop` lesson with a `.STATE.md` sidecar. If you'd rather start fresh, `/primer <topic>` is fine; say which and why.

## What to watch, specifically

These are the paths that were built blind. Note what actually happens for each — including "didn't fire", which is the most useful answer.

**Invocation and loading**
- Does the `` !`…` `` update-notice injection at the top of `SKILL.md` produce anything? It should print **nothing** when up to date. Silence is the pass condition; an error message or a stray line is the finding.
- M1 made the engine files **on-demand reads** instead of static includes. Did you actually read them at the points the load table names, or did you proceed on the gist? A skipped read is the exact failure mode M1 introduced, and only you can see it.

**Recalibrate**
- `recalibrate-check` was firing before this session (`5 misses ≥ 4`). It should run the **minor recalibrate before teaching**, apply `markers-decay`, show a 3–5 line diff, and log `recalibrate-minor`. Did it?

**The protocol**
- Elicit-step retrieval check: I have prior lessons, so it should ask me to recall a prior invariant *before* referencing it. That's the always-on external anchor — did it happen, or did the lesson open by summarising at me?
- Was there a genuine predict-before-explain beat, or did fluent prose arrive first?

**Research (Wave E)**
- Did the discovery pass ask the ledger *before* sweeping — `sweep-check`, `sources-check` — or start from a blank search? Reuse is the whole point.
- Did it run in a **subagent**, off the lesson thread?
- Were verdicts recorded with `sources-add`, including the rejects? Did anything get `sources-promote`d?

**Visuals (Wave A)**
- Was a figure spec authored as a `<!--primer-figure ... -->` block, or did you improvise a diagram?
- Did the ASCII rendering honour the blank (the terminal must not spoil what the page gates)?
- Did `primer_view.py render` produce a page that passed all six checks, and did I get a clickable `file://` link?
- Was the reveal actually gated behind the commit affordance?

**Examiner (Wave B)**
- At Recap, did a **subagent** examiner run with the proposed marker delta **withheld**?
- Agree or disagree? If disagree, was confidence *held* and a reprobe queued — not averaged, not adjudicated by you?

**State**
- Were the state updates made by calling `primer_state.py` / `primer_sources.py`, or by hand-editing markdown? Hand-editing is the regression.
- If I tap out and ask for an answer, log it: `hatch-log`.
- Artifact written per `lesson-template.md`, with `grounds:` provenance on each source?

## How to record it

**Keep a running observation log as you go.** Do not rely on end-of-session recall of your own behaviour — self-assessment of one's own adherence is the weakest available signal, which is the same reasoning that put the examiner subagent in the engine in the first place (D-0027). Write observations down when they happen.

**Do not fix things mid-lesson.** Note the finding and carry on. A derailed lesson is a worse outcome than a logged bug, and the lesson is deliverable #1.

At the end, write it up in the house convention:
- A numbered session log in `docs/engineering/sessions/`.
- New items in `docs/engineering/pending-tasks.md`.
- A `DECISIONS.md` entry only if something needs *deciding*, not merely fixing.

## Known-open items, so you don't re-discover them

- **The self-updater can't install itself.** First-time adoption needs one manual `git pull`; only later updates are self-serve. This is undocumented and belongs in the README install section (D-0026 deferred npm/tarball for this reason).
- The sycophancy trap set (`evals/sycophancy/`) exists with a scorer but **has never been run** — no baseline. Separate task from the lesson; don't do it inside the lesson.
- Still unbuilt from Proposal 0003: **M2** (FSRS-6 with pretrained defaults, revisiting D-0020c), **M3** (grounded prompt exemplars — wants real review history), **Wave D** (persona regression suite, opt-in SessionStart hook, teach-back mode).

Last session found two template-drift bugs where the code and the templates disagreed, both of which would only ever have broken *new* users. If you find a third, look for the class rather than fixing the instance.
