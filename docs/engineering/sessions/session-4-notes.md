# Session 4 — first live end-to-end run of v0.5.2

**Date:** 2026-07-30
**Mode:** live lesson (learner-facing) + engine observation
**Engine:** v0.5.2, `/Users/salt/personal/primer` (symlinked to `~/.claude/skills/primer`)
**Instance:** `/Users/salt/personal/primer-data`
**Lesson:** `backend-engineering / async-event-loop` — resumed the 2026-06-16 `.STATE.md` sidecar, completed, artifact written, sidecar removed.

The v0.5.2 machinery had unit tests and had never been watched running. This session ran it in front of a real learner and recorded what happened, including where nothing happened. Observations were logged continuously during the session rather than reconstructed at the end, per D-0027's own reasoning about self-assessment.

---

## Verdict summary

| Path | Result |
|---|---|
| Injection (`!` update notice in SKILL.md) | **PASS** — silent, no stray output, nothing learner-visible |
| M1 on-demand engine reads | **PASS** — read at the named points; two near-misses worth recording |
| Minor recalibrate | **FIRED, on a miscount** — trigger counts non-miss rows |
| `markers-decay` | **Ran, no-op, and structurally inert for this instance** |
| Elicit prior-lesson recall | **PASS, and the highest-value single result of the session** |
| Research / source-discovery pass | **PASS** — ledger asked first, sweep in a subagent, verdicts recorded including rejects |
| Visuals — spec authoring | **PASS** — authored as `<!--primer-figure-->`, not improvised |
| Visuals — blanked reveal | **FAIL** — the blank leaks its answer in *both* channels, and `render` passes it |
| Visuals — render + 6 checks + `file://` | **PASS** |
| Examiner pass | **PASS on mechanism, gap in the outcome table** |
| State updates via tooling | **PASS** — no hand-edited state; one ordering slip in `log.md`, self-caught |
| Artifact per template with `grounds:` | **PASS** |
| Escape hatch (`hatch-log`) | **PASS** — fired, logged; command undocumented in SKILL.md |

Two findings are severe enough to sit above the rest:

1. **The faded-figure guarantee does not hold** (F-06). A blanked `timeline` renders its span at true geometry in both ASCII and HTML, so position answers the prediction while the label shows `?`. `render` reports "faded-reveal integrity: passed".
2. **The evidence model has no defence against a client that completes the learner's turn** (F-07). Prompt-suggestion ghost text pre-filled a complete correct answer to a probe. Last session recorded this as fixed; the fix was never written. A second attempt this session also failed.

---

## Fixed in-session: F-06 + F-15 (and F-14, which shared their code path)

After the report was written, the maintainer asked for F-06 and F-15 fixed together — correctly, since fixing F-15 alone would have converted a *missing* prediction beat into a *spoiled* one.

**F-06 — blanking now conceals the claim, in both channels.** A blanked `timeline` span emits no coordinates: the page draws a full-plot-width `pv-blank-region` on that actor's row, the terminal fills every cell not claimed by a visible span with `░`. Unresolved bands are emitted before visible spans so a same-row visible span still draws on top.

The subtler half was the **axis leak**, which the original finding missed. A derived axis is exactly the hull of every span, so it is precisely wide enough for the true answer and no wider — and at the limit it gives the whole game away: a blanked span on a 0–2000 axis has nowhere to sit but on top of the other one, which *is* the prediction. Blanking a span now requires a declared `axis {min, max}` with room for the wrong answer too, and a span outside the declared range is rejected. The error message says why rather than just what.

**Audit of the other five forms**, since the pending item asked: `curve` was already correct (it cuts the series at the knee and draws an unresolved region — position is its claim and position is what it hides). `quorum` correct (blanking `progress` removes both the shading and the caption). `sequence`, `state`, `layers` blank labels only, which matches their claims — you are asking *what this message is* or *why this transition is forbidden*, not whether one exists. This is now a table in `diagramming.md` rather than five implicit choices, with the rule stated: wanting to blank something the table says isn't concealable means the form is wrong for the claim, not that you should blank the nearest label. One residual limitation recorded — `layers` cannot blank *where* the boundary sits, only its label, and the docs were ambiguous about which was the invariant.

**F-14 — the ASCII gutter.** Fixed in the same function: it sizes to the longest actual label now, capped at `MAX_LABEL`, and actor labels go through `_plain_label`, so an over-budget label is *rejected* in the terminal exactly as on the page instead of being clipped. (Reported alongside F-06/F-15 rather than folded in silently — it's a separate finding that happened to live in the three lines being rewritten.)

**F-15 — the beat is now a numbered step.** `lesson-protocol.md` states it as four steps in order: author the spec into the `.STATE.md` sidecar → `primer_view.py ascii` it into the conversation → ask the prediction → reveal. Surfaced in `SKILL.md` step 4 so a run that never opens the reference file still gets it, and named as an anti-pattern in `visuals.md`. The prose carries the consequence, because the mechanism isn't obvious from a channel description: a figure described in prose is a figure the learner did not receive, and if it isn't worth authoring at the moment it's needed, cut it rather than deferring it. `SKILL.md` step 6 adds that a spec first written while assembling the artifact missed its beat and should be flagged in the artifact's open threads rather than left looking taught.

**Tests, written from the prose per D-0029.** `TestBlankConcealsTheClaim` asserts the promise `diagramming.md` actually makes — that nothing the learner is asked to predict is readable before the reveal — by diffing the blanked render against the revealed one and requiring every rect unique to the blanked span to be absent. `TestAsciiLabelBudgetParity` pins the `requests 81-100` regression by name. Parity between channels is asserted directly rather than assumed from two implementations having made the same choice.

**Mutation-verified**, because a new test that cannot fail is worth nothing: reverting all four behaviours (SVG true-coordinate rect, ASCII bar fill, 14-char gutter, no axis requirement) fails 9 tests. Restored, the view suite is 121 tests and all five suites are green.

**Verified end-to-end on the real artifact** — the only check that would have caught the original bug. `blank` was restored on the lesson's `await-handoff-overlap` figure with a declared 0–4000 axis. Pre-gate, the page emits exactly one `pv-span` rect (request A, width 190 of a 380 plot) and one `pv-blank-region` (request B, width 380). The learner cannot tell whether B overlaps A or follows it. The terminal agrees:

```
  request A │████████████████████                    │ await db (2s)
  request B │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│ ?
            └0                                   4000 ms
```

**One follow-up left open:** `ascii` still has no validation *pass* of its own. It now rejects what `render` rejects on the paths exercised, but that parity rests on tests rather than on a shared gate. A single validate-then-emit entry point for both channels would make it structural rather than maintained.

---

## Findings

### F-01 — `recalibrate-check` counts non-miss rows as misses

**Severity:** medium. **Class:** code/template disagreement about what a row means — the third instance of last session's class.

`recalibrate-check` returned `fire=yes | misses=5 | lessons=3 | 5 misses ≥ 4`. `calibration-log.md` held 5 rows, of which 2 are explicitly annotated as not misses — `(intake floor-finding, not a miss)` and `(mastery signal, not a miss)`. Real count was 3, below the M=4 threshold. The trigger should not have fired.

The counter keys on entry lines; the template invites annotation rows and documents mastery signals as legitimate content. Worse than the wasted 2–3 minutes: a mastery signal — the strongest evidence class the log carries — *increases* the apparent need for correction. The signal is inverted where it matters most.

**Fix shape.** Not "filter rows containing 'not a miss'" (free text, unparseable). The miss-type column already has a documented token vocabulary (`too-basic`, `too-advanced`, `vocab-gap`, `dead-analogy`, `pacing`, `struggle-mismatch`, `retention-miss`, `escape-hatch`, `examiner-disagree`). Count rows whose miss-type is in that vocabulary; treat anything else as an annotation. That also makes the trigger consistent with the `hatch-trend` / `examiner-disagree` queries, which already key on tokens.

### F-02 — the miss-type vocabulary has no token for a register/voice miss

**Severity:** medium. **Class:** the protocol asks for a signal it provides no way to record.

Two register corrections arrived in two consecutive turns (F-04, F-05) and no documented miss-type fits: `struggle-mismatch` is about probe difficulty, `vocab-gap` is about an unestablished term. Yet `feedback-protocol.md` explicitly instructs the Primer to infer **"Style confirmation — did the chosen register / correction style / narrative density fit, or did friction show?"** There is nowhere to write it.

Combined with F-01's fix (count only documented tokens), an unlisted type is both unwritable and uncountable. Logged this session as `register-miss (NEW TOKEN — not in the documented miss-type list)`.

**Fix shape.** Add `register-miss` to the documented vocabulary in `templates/learner/calibration-log.md` and to `feedback-protocol.md`'s miss-type list.

### F-03 — the ledger has no backfill path; already-vetted sources are invisible to it

**Severity:** medium. **Class:** new machinery assumes a greenfield instance.

`sweep-check --domain backend-engineering` → `no recorded sweep`. `sources-floor` → `no accreted floor yet`. But the instance had two prior lesson artifacts with populated `sources_consulted` frontmatter and a sidecar carrying 8 sources vetted 6 weeks earlier. The ledger shipped in v0.5.2, after those lessons ran, and `primer_update.py migrate` creates the file without backfilling.

Consequence: every pre-existing instance pays for a full sweep it has already paid for, once per domain, and re-litigates sources it already vetted. The artifacts' `sources_consulted` blocks are already a structured, parseable record of exactly what the ledger wants.

**Fix shape.** `primer_sources.py sources-import` walking `$DATA_DIR/lessons/**/*.md` frontmatter, invoked by `migrate`. Note the key drift while doing it: the old sidecar used `backs:` where the template and `research-protocol.md` both specify `grounds:` — an importer has to accept both.

### F-04 — `invariant` is unglossed engine vocabulary, and intake wrote it into the learner model as the learner's own

**Severity:** high (for lesson quality). **Class:** the engine's register leaked into the learner model.

The learner's first response to the Elicit recall was: *"AI uses 'invariant' all the time. I don't know what you mean by that word."* The recall question was unanswerable because its framing used a term the learner does not hold.

This is not lesson-local. `invariant` is core engine vocabulary and unglossed everywhere it appears: `lesson-protocol.md` ("force derivation of a key invariant", "3–5 invariants"), `feedback-protocol.md` ("recall a prior invariant"), `visuals.md` and `diagramming.md` (figures are gated on carrying "one invariant"), and the Recap contract section is literally named `### Invariants`.

The sharpest part is in `profile.md`, under Preferences: *"Productive-struggle tolerance: High. **Wants to derive invariants**, not be handed them."* An intake-authored sentence attributing to the learner a word he does not know. The profile is the defence against generic-curriculum drift (`anti-patterns.md` #6); here the profile itself absorbed house style and was then read back as evidence.

**Fix shape.** Three parts. (a) Gloss or replace `invariant` in learner-facing protocol text — "the rules worth keeping" worked live. (b) Audit `templates/learner/*` and the intake protocol for other unglossed house terms; `ZPD edge` is next and it appears as a section header in a file the learner is invited to hand-edit. (c) Intake should not phrase a learner trait in vocabulary the learner has not used.

### F-05 — the engine's instruction prose trains the register the learner rejects

**Severity:** medium–high. **Class:** instruction text style-transfers into output; the avoid-list is a snapshot.

Second unprompted correction, before any lesson content: *"don't use 'the one X' 'load bearing' 'the one thing that everything hinges on'. That type of framing reads very artificial… constant bombardment of these non-native english phrasing destroys immersion."* Confirmed in my own output — "the one invariant from that session", "the one rule you'd still bet money on", in consecutive turns.

These are the house dialect of primer's own files. `load-bearing`: `SKILL.md`, `system-prompt.md`, `research-protocol.md` (×4), `source-canon.md` (×3), `feedback-protocol.md`. `the one X`: `lesson-protocol.md` ("the one invariant it makes visible", "the one safety property that stuck"), and the pre-built sidecar body.

`system-prompt.md` has a *Voice — what to avoid* list, and it catches a previous generation of tics ("let's dive in", "so basically", motivational closers) while the current ones sit unlisted in the surrounding prose.

**Fix shape.** Two parts, and the second matters more. (a) Add the current constructions to the avoid-list. (b) De-tic the engine's own prose — the instruction text is a style corpus whether or not it was meant as one, so an avoid-list that contradicts the volume of surrounding text loses.

### F-06 — the faded-figure guarantee does not hold: blanking preserves geometry, and `render` passes it

**Severity:** high. **Class:** a validated check that does not check the thing it protects.

Authored the refresher figure as a spec with `"blank": ["s-b"]` on the second request's span. Both channels leak.

ASCII:
```
       request A │████████████████████████████████████████│ await db (2s)
       request B │████████████████████████████████████████│ ?
                 └0                                   2000 ms
```

HTML, pre-gate, verified by inspecting the emitted page:
```html
<rect class="pv-span "      x="130" y="27" width="380" height="24" rx="4"/>
<text ...>await db (2s)</text>
<rect class="pv-span pv-blank" x="130" y="73" width="380" height="24" rx="4"/>
<text ...>?</text>
```

Identical geometry, `x="130" width="380"` in both. The figure's claim is *where B's span sits* — overlapping A rather than following it — and position is exactly what blanking does not conceal. Only the label is replaced.

`render` reported `checks passed: … faded-reveal integrity`. That check verifies the reveal *text* is DOM-gated; it has no notion of a drawing that answers its own prediction. So "never hand the learner a page that failed validation" is satisfied by a page that spoils.

This hits the form `diagramming.md` recommends most for concurrency: *"If the lesson's invariant is about concurrency, it's a timeline."* And it contradicts a stated guarantee — *"The blanked ASCII rendering honours the same blanks, so the terminal can't spoil the page"* — which is true for label-carrying elements and false for position-carrying ones.

**Handling in the lesson:** did not show the blanked figure. Asked the prediction in prose, then showed the figure complete. Removed `blank`/`reveal`/`predict` from the artifact's spec and put the prediction in prose, so the shipped page is not a puzzle that answers itself. Re-rendered; six checks pass.

**Fix shape.** Each template must define what blanking *means* per element kind — for `timeline`, a blanked span should render as an unresolved region (full-axis hatch, or a floating `?` bar at no fixed offset), not at true coordinates. Then the validator should reject a `blank` whose element carries its claim in geometry the renderer cannot conceal. Check `curve` (blank-past-the-knee is documented and may have the same hole) and `quorum` (a blanked node's side is its answer).

### F-07 — the evidence model has no defence against a client that completes the learner's turn

**Severity:** high. **Class:** an assumption the engine cannot verify and does not state.

The learner sent a screenshot of their input bar containing `20 seconds, they serialize since requests.get never yields` — a complete correct answer to the probe just asked, generated by the client before they typed anything.

`calibration-log.md` from 2026-06-16 records this as already handled: *"the client prompt-suggestion ghost-text was also pre-filling answers — now disabled for the primer repo via promptSuggestionEnabled:false"*. Verified: neither `primer/.claude/settings.json`, `primer/.claude/settings.local.json`, `primer-data/.claude/settings.json` nor `primer-data/.claude/settings.local.json` existed, and `~/.claude/settings.json` has no such key. `log.md` line for that session says the same thing. **The fix was recorded as done in two state files and was never written anywhere.**

Wrote `primer/.claude/settings.json` with `promptSuggestionEnabled: false` this session. **It did not work** — the learner reported hints still appearing. Either the key name is wrong or project settings need a session restart. Recorded as applied-and-unverified, explicitly not as fixed, which is the discipline F-07's own history shows was missing.

Two distinct problems:

- **The confound.** Every probe this session is void as evidence — a correct answer cannot be distinguished from a read-back. Probe 1 was excluded from the examiner's brief for exactly this reason.
- **The recording defect.** The calibration log is prose written by the teacher at recap, and nothing verifies that an asserted remediation landed. This is worse than an unfixed bug: the log actively asserted the channel was clean, so this session planned probes on that basis. It also means last session's split attribution of the telegraphed-probe miss ("partial confound") can't be settled.

The learner's framing, which I initially got wrong and then accepted: *"To a standard user, the client is 'you'. It's our interface to interact with you."* Correct. From the learner's seat there is no engine/client boundary, so a feature that completes their turn *is* the Primer violating `anti-patterns.md` #7 (direct-answer-on-first-attempt) and #2 (the LLM fallacy). Every anti-pattern in that file is written as something the model does; none is written as something the surrounding system does.

**Fix shape.** (a) Assert the setting at session start rather than trusting a log entry — and if it can't be asserted, say so to the learner once. (b) The calibration log needs to distinguish *observed* from *fixed*; an asserted fix with no verification should not be writable as resolved. (c) `anti-patterns.md` should name the environment as a source of the failures it lists.

### F-08 — a resumed `.STATE.md` sidecar is a frozen plan, and nothing re-checks it against moved state

**Severity:** medium. **Class:** resume has no re-calibration beat.

`/primer resume` in SKILL.md is three sentences: find the sidecar, ask whether to resume it. The sidecar found today was pre-structured at intake on 2026-06-16 and had gone stale in three independent ways:

1. **Sources** — `freshness_check: 2026-06-16`, six weeks old. One of its eight cited sources (`www.uvicorn.org`) no longer resolves at all. It would have been cited today without the discovery pass. Nothing in the resume path checks `freshness_check`; the sweep covered it because I chose to run one.
2. **Probe design** — the sidecar's primary probe reads *"`/b` is `async def` and does `time.sleep(2)` **(the blocking one)**"*. The parenthetical labels the answer. `calibration-log.md`, written *after* the sidecar, records the learner rejecting telegraphed probes by name: *"In-lesson probes must be open free-form with the answer NOT embedded in phrasing."* Deploying it verbatim would have repeated the exact logged miss.
3. **Premise** — the sidecar's §Deepen §2 says it "resolves the open question from intake" about whether blocking yields. `fastapi-orientation` ran later the same day and resolved it; `topic-index.md` recorded the model as locked. Roughly 40% of the pre-built body was re-teaching ground the log said to fade past.

Note the twist, which is the interesting part: I re-scoped §§1–3 down on the strength of `topic-index.md`, and then the cold recall (F-09) showed `topic-index.md` was wrong and the frozen plan was right. Both the plan and the live state were unreliable; the *probe* settled it.

**Fix shape.** The resume verb needs a re-calibration beat before deploying a pre-built body: re-check `freshness_check` against the horizon, diff the sidecar's assumptions against `calibration-log.md` entries written after its date, and confirm the premise against the current marker. Cheap — three reads — and all three would have fired today.

### F-09 — `markers-decay` is structurally inert for an instance with no `high` markers

**Severity:** low as a bug, medium as a documentation claim. **Class:** a documented guarantee the instance does not have.

`markers-decay` output `no markers decayed`, correctly: nothing in this index sits at `high` (all `med`, `med–high`, or `low`), and the rule only drifts `high` → `med`.

But `feedback-protocol.md` sells decay as a **passive guard**: *"when no retrieval happens at all, confidence still lapses toward reprobe rather than sitting high forever."* For this instance that guard does not exist and will not until some marker reaches `high`. Meanwhile a `med` marker built from one demonstration six weeks ago is precisely the "unverified and getting staler" case the section describes — and nothing touched it. The always-on Elicit anchor is what caught it (F-10), not the passive guard.

Also unaddressed: step 3 of the minor recalibrate says to *surface* stale `[confidence: low]` markers as standing assumptions. `markers-decay` said nothing about them, and `staff-trajectory` has been `low` and untouched since intake. Unclear whether that half belongs to the tool or the model; neither did it.

**Decision needed, not just a fix:** does `med` decay to `low`, or does the protocol accept `med` as already meaning "needs reprobe"? Either is defensible; the current state — docs claiming a guard the code doesn't provide at this confidence level — is not.

### F-10 — the always-on Elicit anchor worked, and it was the most valuable mechanism in the session

Not a defect. Recording it because it is the thing that saved the lesson from being mis-scoped, and because it is the mechanism that would be easiest to quietly skip.

`topic-index.md` claimed the async concurrency model was **locked**, `[confidence: med, demonstrated]`, earned from unprompted derivation six weeks earlier. `calibration-log.md` said "fade fast on async fundamentals; go straight to where-blocking-lives." The Elicit-step cold recall was asked before referencing the prior lesson and returned: *"That is fairly gone. Let's do a refresher and then pick up again."*

One question, asked before any teaching, overturned a marker and re-scoped the session. The examiner later built its downgrade primarily on this datum. This is `feedback-protocol.md`'s external anchor doing exactly what it was designed for, and it caught what the passive guard (F-09) structurally could not.

One sequencing conflict worth noting: SKILL.md orders **Plan** (step 3) before **Run the protocol** (step 4, containing Elicit). Followed literally, the plan paragraph — "we're going straight to where blocking lives, the async model is locked" — hands over the invariant the recall is meant to cold-test. Resolved live by giving a deliberately non-spoiling one-line frame and holding the real plan until after Diagnose. The step order should say so.

### F-11 — the examiner protocol has no outcome for agree-on-direction, differ-on-magnitude

**Severity:** medium. **Class:** an outcome table that doesn't cover the case that arose.

The examiner ran as designed: separate subagent, given the learner's verbatim answers, the lesson's rules, and the current marker; **not** given the proposed delta or the diagnosis narrative; prompted adversarially. The separation held — I wrote the brief before forming a final delta and withheld it.

It returned a **downgrade**, and a steeper one than I had planned: I intended `med → low-med`; it argued `med → low`, resting on (a) the nil cold recall and (b) the keyword-as-parallelism misconception surfacing twice independently — once in the `def`/`async def` probe and again in offering `async def` + `await` as the CPU-bound escape. It weighted the Recap takeaway at approximately zero as ability evidence, on the grounds that it was my own sentence returned nearly verbatim while stating the principle the two failures violate. That is a sharper read than mine and I applied it.

But the outcome table has two rows — **agree → apply**, **disagree → hold confidence, log, queue reprobe** — and neither fits. "Hold" would have been actively wrong: it preserves `med`, a value *both* reads reject. The asymmetry clause ("disagreement blocks an upgrade but does not block a downgrade") is what makes applying the steeper read defensible, but it is inference, not a documented outcome. Logged as `examiner-disagree` with the resolution described, since the verdicts did differ and a reprobe was queued — but that pollutes the disagreement rate with a case the token was not defined for.

The examiner also produced a calibration observation about the engine that belongs in the record: *within-session unprompted derivation in this domain did not predict six-week retention, so it should not by itself buy "demonstrated."* That is a claim about how confidence is earned, and it came from the adversarial position rather than from the teacher.

### F-12 — `hatch-log` and `hatch-trend` are undocumented in SKILL.md

**Severity:** low. **Class:** command surface split across a statically-loaded file and an on-demand one — a risk M1 introduced.

`hatch-log` worked (`logged: 2026-07-30 | backend-engineering | escape-hatch | …`). SKILL.md's deterministic-helpers line documents `review-due`, `review-grade`, `review-add`, `review-history`, `markers-decay`, `recalibrate-check` — not `hatch-log` or `hatch-trend`. Those appear only in `feedback-protocol.md`, which under M1 is an on-demand read. A run that never opens `feedback-protocol.md` cannot know the hatch counter exists, and the escape hatch is offered from `lesson-protocol.md` and `system-prompt.md`, both of which mention the hatch without mentioning the logging.

### F-13 — `sources-add` exits 0 on validation failure

**Severity:** medium. **Class:** silent skip.

Reported by the sweep subagent, verbatim errors:
```
error: why is 547 chars, over the 400 limit
error: why may not contain '|' — the ledger is pipe-delimited, one entry per line. Rephrase it.
error: why is 425 chars, over the 400 limit
```
The messages are good — specific and actionable. But `sources-add` returns exit 0 on these, so a `set -e` loop silently drops entries; the agent caught them only by reading stdout. Rejects are the entries most worth keeping (the whole point of recording drops is to avoid re-litigating them), so a silent skip loses exactly the data the ledger exists to preserve.

### F-14 — the ASCII channel silently truncates labels that are well inside the documented budget

**Severity:** medium. **Class:** C — a documented guarantee the implementation does not provide.

Rendering the staircase figure inline (prompted by F-15) produced:

```
   requests 1-40 │██████████████                          │ 40 tokens held
  requests 41-80 │             ██████████████             │ queued, then held
  requests 81-10 │                          ██████████████│ queued, then held
                 └0                                   6000 ms
```

`requests 81-100` rendered as `requests 81-10`. The same page's HTML renders `requests 81-100` correctly, so this is ASCII-specific. The label is 15 characters against a documented budget of 34, and `diagramming.md` states the rule explicitly: *"a longer label would be clipped by the viewBox and silently lost. The generator rejects it instead."* The ASCII gutter appears fixed at 14 characters and clips without warning — the exact behaviour the documented rule exists to prevent, in the channel the rule isn't applied to.

Semantically load-bearing here: the truncated label is a range, and `81-10` reads as a malformed or descending range rather than as a clipped one.

**Consolidation with F-06 — the ASCII renderer is the weaker implementation of the same spec, twice.** Both figure defects this session are ASCII/HTML divergences and in both the ASCII side is the lossy one: blanking leaks geometry there (it leaks in HTML too, but the label/blank handling differs), and labels clip there and not in HTML. That matters more than either bug alone, because **ASCII is the channel used live, in front of the learner, where the Primer cannot inspect the output before the learner sees it.** The HTML channel has `render`'s six checks and a validation gate; the ASCII channel has neither, and it is the one that ships to the conversation.

**Fix shape.** Two parts: (a) apply the same label-budget rejection to the ASCII renderer, or widen/wrap the gutter to fit the declared budget; (b) more generally, give `ascii` a validation pass equivalent to `render`'s, since it is the channel with the tighter feedback loop and no gate.

### F-15 — the Deepen figure beat gets skipped: specs get authored at artifact time, so figures arrive after the reasoning they were meant to support

**Severity:** high. **Class:** E — a documented capability with no numbered step that invokes it, where the value is entirely in the timing.

Learner feedback, unprompted, twice — first on seeing the view page, then more pointedly:

> *"That's a good diagram, would be helpful to have those diagrams demonstrated in line when the lesson was discussing them specifically to look at and reference while still in the mental context."*
>
> *"What would have helped was when we discussed the stairstep timing, to show the stair-step diagram right then and there. I can visualize it in my head, but that was the whole point of adding the drawing tools. Now we are done and doing evaluation and then the diagram shows up isn't as helpful."*

Initially logged as under-use of a stated preference — `profile.md` already specifies *"ASCII inline during the live conversation"* — which was true but too kind. The real cause is worse.

**At the moment the staircase was being discussed, its spec did not exist.** The refresher figure was authored into the `.STATE.md` sidecar mid-lesson and rendered inline, which is the designed path (`lesson-protocol.md`: *"Mid-lesson, the spec's home is the in-progress `.STATE.md` sidecar"*). For the staircase I described the shape in prose while the learner derived it, and wrote the spec afterwards, while assembling the artifact. So the Deepen figure beat was not run late — **it was not run at all for that figure, and was reconstructed retroactively.** The inline render at the end of the session was me satisfying the request after the fact, on a spec authored for the artifact.

Two things follow that a "remember to render inline" note would not fix:

1. **The figure beat's value is entirely in its position.** `lesson-protocol.md` already specifies the ordering — blanked figure → specific prediction → reveal — and the whole sequence is upstream of the prediction. A figure shown after the learner has the answer isn't a late figure; it's a different artifact with no pedagogical function. The learner's word for it is right: at that point it's something he'd already visualized himself.
2. **The path of least resistance runs the other way.** Authoring a spec costs a tool call and a JSON block mid-conversation; describing the shape in prose costs a sentence. Prose is always available and always faster, and it *reads* as adequate — which is exactly why the beat gets skipped under time pressure, and why the session that skipped it still produced a lesson that looked complete.

**Compounding with F-06.** The correct beat for the staircase was a *blanked* staircase shown before the prediction — asking the learner to predict where the second and third waves sit. That is precisely the beat F-06 breaks: a blanked `timeline` span renders at true geometry, so the blank would have handed over the answer. The one place in this lesson where the faded-figure mechanism was most clearly indicated is the place it would have failed. Fixing F-15 without F-06 produces a spoiled prediction beat instead of a missing one.

**Fix shape.** Make the inline render a numbered step inside Deepen rather than prose in a reference file: at each figure, author the spec into the sidecar, `ascii` it into the conversation, ask the prediction, then continue. State the consequence explicitly, because it is not obvious from the current text — **a figure described in prose instead of rendered is a figure the learner did not receive**, and one authored at Recap is a figure that never had a pedagogical role. Consider making the artifact-writing step *check* that every figure spec it emits was rendered inline during the session, since a spec first seen at artifact time is by definition one that missed its beat.

---

## What worked, without qualification

- **Injection.** Silent. Nothing learner-visible, no error, no stray line. The pass condition was silence and silence is what happened.
- **The research pass, end to end.** Ledger asked first (`sweep-check` → `no recorded sweep` → full sweep, correctly routed). Sweep dispatched to a subagent, so the lesson thread never carried search output. 20 verdicts recorded including 4 drops. `sweep-record` written, `sweep-check` re-queried afterwards and reported `fresh: last full sweep 0d ago (horizon 60d)`. Coverage floor met with seven primary sources and a genuine current-practice source.
  It earned its keep in a way a synthetic test could not have: **`www.uvicorn.org` no longer resolves**, and it was cited in the pre-built body. It also caught that the `--workers` claim was attributed to a page that never discusses `--workers`, that the greenlet claim rests on a specific named section rather than the page generally, and that the flat GIL claim now needs a build-conditional qualifier because PEP 779 made free-threading officially supported in 3.14. Four corrections to material that had already been "verified" six weeks earlier.
- **`render`'s six checks and the `file://` handoff.** Ran twice, passed both times, reported which checks passed, gitignore rule for `*.view.html` already in place in the instance. The page is self-contained. (Its blind spot is F-06.)
- **State updates through tooling.** `review-add` ×11 (scheduler set the dates, none hand-written), `hatch-log`, `markers-decay`, `recalibrate-check`, `sources-add` ×20 via the sweep, `sources-promote` ×7 building a floor that was empty this morning, `sweep-record`. No state file was hand-authored except the narrative fields that are meant to be prose — depth-marker text, ZPD edges, calibration-log entries, open-questions, `log.md`.
  One self-caught slip: I appended the two `log.md` lines above the 2026-06-16 entry, breaking chronology, then rewrote the file in order. Worth noting only because `log.md` is the one state file with no helper command — every other append goes through code, and the one that doesn't is the one I got wrong.
- **Artifact per template**, with `grounds:` claim-level provenance on all 16 sources, `[verified]`/`[dropped]`/`[caveat]` sub-lists, and no outstanding `[from-training, verify]` claims.
- **The examiner's separation.** It reached a materially different and better-argued verdict than mine, which is the whole point. Mechanism validated even though the outcome table needs work (F-11).

---

## M1 — did the on-demand reads actually happen?

Read at the points the load table names, before the work each governs: `feedback-protocol.md` before the minor recalibrate; `lesson-protocol.md` + `anti-patterns.md` before opening the loop; `research-protocol.md` + `source-canon.md` before dispatching the sweep; `visuals.md` + `diagramming.md` before authoring the figure; `examiner-protocol.md` + `lesson-template.md` at Recap before any marker change.

The useful part is where the pull to skip was strongest, since that is what M1 has to survive:

- **`anti-patterns.md`** — because the pre-built sidecar carried its own copy of the self-check list. A sidecar that inlines the checklist is a standing incentive to skip the file that defines it.
- **`source-canon.md`** — because `system-prompt.md` restates most of its content (currency non-negotiable, floor-not-allowlist, promote-to-ledger-not-canon). The read felt redundant right up to the stale-criteria, which is the part only in that file, and the part that changed behaviour: *"predates a known consensus shift"* is what prompted sending the free-threaded-Python question to the sweep, which produced the session's most substantive currency correction.

So M1's failure mode is real and specific: the files most likely to be skipped are the ones whose *summary* is available elsewhere, and the value is concentrated in the part the summary omits. Worth considering whether `system-prompt.md`'s restatements should be trimmed to pointers, so the on-demand read is the only place the content lives.

---

## Lesson quality — honest self-check

Per `anti-patterns.md`, recorded in the artifact too:

- **Predicted before explained:** yes, twice, both substantive (the `def`-keyword probe and the 40-token ceiling derivation).
- **Claims tagged:** yes, all grounded, no outstanding `from-training`.
- **Profile facts in the framing:** yes — the migration, team-lead framing, goal-3 stake, and the psycopg3 correction the learner supplied.
- **Probed before answering:** yes.
- **Sycophancy: untested.** The learner never pushed back on a correct technical claim, so no line was held under pressure. Not a pass; an absence of evidence. This is the second thing pointing at the sycophancy trap set needing its baseline — a live lesson does not reliably generate the pressure modes.
- **Faded-figure beat: failed** (F-06). The learner received both figures rather than generating one.
- **Expertise reversal: nearly, in the wrong direction.** I planned to compress the fundamentals on the strength of the marker, and the cold recall showed the fundamentals were gone. Caught by the anchor, not by judgment.
- **Cost of the meta:** two turns went to register corrections before any content, against a 45-minute preferred budget; the session ran ~55. The corrections were worth having, and the lesson absorbed them, but the tics came from the engine's own prose (F-05) and were avoidable.

---

## Cross-cutting: the class behind the instances

Last session found two template-drift bugs where code and templates disagreed, both of which would only ever have broken new users. The instruction for this session was to look for the class rather than the instance if a third appeared.

A third appeared (F-01), and it is not quite the same class. Sorting today's findings:

**Class A — code and template disagree about a format.** F-01 (`recalibrate-check` counting non-miss rows), F-02 (a signal the protocol requests with no token to record it), F-13's pipe-delimiter constraint. Same shape as last session: a parser keys on structure the template invites humans to violate. **The generalisable defence is that every parsed field needs a documented closed vocabulary, and the parser and the template must both cite the same list.** Free-text annotation columns adjacent to parsed columns are where this recurs.

**Class B — new machinery assumes a greenfield instance.** F-03 (no ledger backfill), and the known-open self-updater problem that can't install itself. Both break exactly once per existing instance, at adoption, which is why unit tests never see them. **Defence: every migration should ask what an instance with history already has that the new machinery wants, and import it.**

**Class C — a documented guarantee the implementation does not provide.** F-06 (faded-reveal integrity checks text, not the drawing), F-14 (labels clip in ASCII where the docs promise rejection), F-09 (passive decay guard inert below `high`), F-11 (outcome table missing the case that arose), F-07's recording defect (a log asserting a fix that was never applied). This is the class that most needs naming, because it is the one that *cannot* be caught by unit tests against the implementation — the tests encode the implementation's own view. Each of these passed its own checks. **Defence: for any guarantee stated in prose in the engine docs, the test must be written from the prose, not from the code.** F-06 is the sharpest example: a test asserting "the blanked channel does not contain the answer" would have failed; the test that exists asserts "the reveal element is gated", which passes.

A sub-pattern inside Class C worth pulling out, because two of five instances share it: **where one spec has two renderers, the unvalidated one drifts.** F-06 and F-14 are both ASCII/HTML divergences and the ASCII side is lossy in both. `render` has six checks and exits non-zero; `ascii` has no validation at all — and `ascii` is the channel that goes to the learner live, unreviewed. Parity between renderers of a shared spec needs to be a tested property, not an assumption.

**Class E — a documented channel or preference with no step that invokes it.** F-15 (nothing prompts the inline render, so figures arrive after the moment they were needed) and F-12 (the hatch counter exists but is documented only in an on-demand file). Adjacent to Class C but distinct: the capability works correctly and simply never gets called. `profile.md` asked for inline figures and the protocol has no beat that acts on it. **Defence: a capability the engine documents should be reachable from a numbered step in the flow that uses it, not only from the reference file that describes it.**

**Class D — the engine's own text as an uncontrolled style and vocabulary corpus.** F-04, F-05. Instruction prose style-transfers into teaching voice, and intake writes engine vocabulary into the learner model where it is then read back as evidence about the learner. No test catches this and no avoid-list keeps up with it; the fix is to treat the engine's prose as part of the product's voice.

Class C and Class D are new findings about *where to look*, and both were only visible from a live run.

---

## Follow-ups

Written to `pending-tasks.md`. Two items are proposed for `DECISIONS.md` because they need a decision rather than a fix:

- **`med` marker decay** (F-09) — does `med` decay, or is `med` already "needs reprobe"? The docs currently promise a guard the code doesn't provide at that level.
- **Examiner outcome for magnitude divergence** (F-11) — the table needs a third row, and the `examiner-disagree` token needs to either cover this case or gain a sibling.

Also carried forward, unchanged from the known-open list: the sycophancy trap set still has no baseline, and this session adds evidence for why it needs one — a real lesson did not generate a single pressure mode.
