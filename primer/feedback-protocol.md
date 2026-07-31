# Feedback Protocol — How the Primer Learns the Learner

The loop that keeps the profile true after intake. Intake produces a profile that is mostly assumption; this protocol turns lessons into evidence and periodically corrects the model rather than only appending to it.

The core failure of a naive loop is conflating things that change at different rates and only updating at one timescale. This protocol runs at three.

**Deterministic bookkeeping runs as code, not in-context.** The mechanical parts of this loop — spaced-repetition scheduling (SM-2), confidence decay over time, and the recalibration trigger (counting misses/lessons) — are handled by `tools/primer_state.py`, which reads and rewrites the markdown state files. The model *calls* it and interprets the result; it does not recompute dates and counts by hand (token-expensive, and models miscount). Markdown stays the source of truth so the learner model remains hand-editable and git-syncs cleanly across machines. See DECISIONS D-0018/D-0020.

## Stable vs. volatile — the split that makes the loop work

Two kinds of fact live in the profile, and mixing them in one file means the volatile churn drags the stable traits along and the stable traits never get deliberately revisited.

- **Stable traits** → `profile.md`. Identity, real context, register, productive-struggle tolerance, correction style, narrative density, visual prefs, session length, anti-preferences, goals (semi-stable). Changes deliberately — at `recalibrate`, or when the learner edits.
- **Volatile state** → `learner/`. Depth markers (with confidence + evidence), `[status]` tags, ZPD edges → `topic-index.md`. Calibration misses → `calibration-log.md`. These churn every session.

Depth markers live in `topic-index.md`, **not** `profile.md`. Each marker carries `[confidence: low/med/high]` and the evidence that earned it (which session, what was demonstrated). Intake claims start `low`; each lesson that confirms raises confidence. This lets the Primer distinguish what it *knows* about the learner from what it *assumed*.

## Timescale 1 — within a lesson (silent)

The Diagnose step (`primer/lesson-protocol.md`) already adjusts depth live. Add: when a **calibration miss** happens, note it silently and carry it to session end. Never break flow to ask about it.

Miss types to watch for:

- too basic / too advanced
- vocabulary gap (used a term before establishing it)
- dead analogy (the framing didn't connect)
- pacing off (rushed or dragged)
- struggle-tolerance mismatch (learner bounced off a Socratic probe and wanted the answer) — **log it**: `primer_state.py hatch-log --domain <d>`. The "just show me" hatch is the right call in the moment, but a *rising* rate is the AI-dependence signal, and it was invisible until it was counted. `hatch-trend` reports the rate per domain over the last N lessons; read it at recalibrate as "the register is mis-set for this learner here", not as a failure.
- **register miss** — the voice, vocabulary, or figure delivery didn't fit and the learner said so. Token: `register-miss`. This is the *Style confirmation* signal below, which the protocol asked the Primer to infer while giving it nowhere to write the result; a recurring one is a candidate anti-preference. Both instances so far traced back to the engine's own prose rather than to a per-learner preference, so check the instruction files before recording it as a trait.
- **analogy transfer** — an analogy carried the structure across correctly and the magnitude or cost incorrectly. Token: `analogy-transfer`. Distinct from a dead analogy, which never connected: this one connected, was productive, and mispriced something. The correction differs too — keep the analogy, fix the number.

## Timescale 2 — end of each lesson (signal capture)

Beyond the existing depth-marker and topic-index updates:

### Calibration-log entry

Append to `learner/calibration-log.md` any misses observed:

`<date> | <domain> | <miss-type> | <what happened> | <adjustment made / to make>`

This is the routine version of what currently happens by luck. The existing "lead with vocabulary in new domains" rule was a vocabulary-gap miss that got hand-promoted to a trait; this makes that capture systematic so patterns surface instead of being caught ad hoc.

### Confidence + evidence on depth markers

Update each touched marker in `topic-index.md`: adjust the depth description, set `[confidence]`, append the evidence. Confidence moves **both ways**, and the direction matters more than the level:

- **Up** — a clean answer raises it; **the learner correcting a Primer error** raises it most, because it demonstrates mastery beyond passive recall.
- **Down** — stumbling on something the marker claimed was solid, needing heavy narrowing to engage, or **missing a cold retrieval prompt in `/primer review`** (see *External anchor* below) lowers it. A downgrade is not a failure to hide; it is the loop working.

A marker that only ever goes up is the warning sign in *Profile rot* — see the decay rule next.

### Confidence decays with time (forgetting-aware)

A confidence level is a claim about the **present**, and two things age out from under it: the learner's recall (knowledge decays without retrieval) and the Primer's own calibration (the evidence was a demonstration on one past day). So an untouched high-confidence marker is not "still high" — it is **unverified and getting staler**.

This mirrors how production learner models handle it: estimates lapse toward "needs review" over time rather than staying mastered forever (the forgetting-aware approach behind Duolingo's scheduler — Half-Life Regression, DAS3H). primer's version is coarse and runs at recalibrate, not a formula per turn: a `[confidence: high]` marker untouched for several lessons should **drift toward `med` and surface as a reprobe candidate**, not sit at `high` indefinitely. The decay is what keeps the model honest in the absence of fresh evidence — and what stops the loop from quietly inflating its own certainty over time (the closed-self-assessment drift this protocol exists to resist).

### External anchor — the loop is not allowed to grade only itself

The depth markers are the Primer's *own* assessment of the learner. A loop that updates its model only from its own prior assessments drifts optimistic imperceptibly. The anchor is **cold retrieval** — recall of *past* material with the answer not in front of the learner — and it comes from two places, plus a passive guard:

- **Always-on — the Elicit-step recall** (`primer/lesson-protocol.md`): every lesson in a domain with prior coverage opens by asking the learner to recall a prior invariant. This rides the lesson flow, so the anchor fires whether or not the learner ever runs a separate review. It is the primary anchor, because it doesn't depend on a habit the learner may not form.
- **Optional — `/primer review`**: a deliberate cold-retrieval pass over the queue, for learners who want spaced refreshers. Not every learner will; the loop must not depend on it.
- **Passive guard — time decay** (above): when no retrieval happens at all, confidence still lapses toward reprobe rather than sitting high forever.

All three anchor the *learner's recall*. None checks the *Primer's judgment*, which is the weaker half: models judge a correct answer at 94–99% F1 and a valid-but-unconventional one at 0–76% — and the valid-but-unconventional answer is what a senior learner produces. That gap is what `primer/examiner-protocol.md` closes: at Recap a separate examiner, which never sees the proposed delta, argues against an upgrade. Agreement applies it; disagreement holds confidence and queues a reprobe. Disagreement is information, not a tie to break.

A miss in either retrieval path is evidence the model didn't generate this session, so it feeds back hard:

- On a missed recall (Elicit or review), append a `calibration-log.md` entry (`<date> | <domain> | retention-miss | missed cold retrieval on <prompt topic> | lower <domain> confidence, requeue`) and **lower the relevant marker's confidence**.
- On a clean answer to an *old* prompt (the older, the stronger), confirm or raise confidence — that is durable retention, not session-fresh recall.

This is a coarse anchor, not a clean measurement: the prompts are Primer-authored, so a high review score is a calibration signal, **not** a mastery claim or an effect size (self-authored tests inflate). Weight it as "the model's estimate survived contact with delayed recall," and prefer signal the Primer did *not* author — the learner reporting they applied a pattern in real work — when it surfaces.

### Silent micro-feedback (inferred, never asked)

The Primer does **not** ask "did the difficulty land?" — that crosses into the fluff the protocol elsewhere refuses. Instead it *infers* from the conversation and writes the signals:

| Signal class | Inferred from |
|---|---|
| **Calibration** | Did the learner anticipate points before they were made (too basic) or repeatedly ask for narrowing (too advanced)? |
| **Engagement** | Did they pull on threads and push back (engaged), or give short acknowledgments and stop asking (disengaging)? |
| **Mastery evidence** | Did they derive an invariant, correct an error, or only restate? |
| **Style confirmation** | Did the chosen register / correction style / narrative density fit, or did friction show? |

These feed the calibration-log and, when a pattern is clear, the anti-preferences. If a single lesson contradicts a stable trait, note it — don't rewrite the trait on one data point; that's what `recalibrate` is for.

## Timescale 3 — recalibration (two tiers)

The append-only loop accretes volatile state until it needs compacting and the model needs correcting. Two tiers, by the user's design.

### Minor recalibrate — auto, evidence-triggered (capped)

System-triggered, but on *evidence* rather than a fixed count: it fires at the start of the next lesson when **either**

- **M+ calibration-log misses** have accumulated since the last recalibrate (default M = 4; the importance-threshold idea — a model that's missing a lot needs correcting sooner), **or**
- **N lessons** have passed since the last recalibrate regardless of misses (default N = 8 — the cap, so a quiet stretch still gets periodic hygiene).

Both defaults are configurable. This replaces the old fixed "every 5 lessons": it fires *sooner* when the model is visibly miscalibrated and *no later* than the cap. Lightweight, ~2–3 minutes, shows a short diff and proceeds:

1. Scan `calibration-log.md` since the last recalibrate for **repeated** miss-types in the same domain → fold into the relevant depth marker or anti-preference.
2. Flip any `[status]` that the evidence clearly warrants (e.g., `[in-progress]` → `[covered]`).
3. Apply time decay (forgetting-aware): **drift any `[confidence: high]` marker untouched for several lessons toward `med`** and flag it as a reprobe candidate; and surface — don't resolve — any `[confidence: low]` marker untouched for several lessons (a standing assumption worth a probe next time). Both are about markers going stale; the difference is high-confidence ones decay, low-confidence ones just get re-flagged.
4. Show a 3–5 line "changed since last check" diff. Proceed into the lesson.
5. **Close with `primer_state.py recalibrate-mark`.** It writes a positional marker into `calibration-log.md`, and everything below the last marker is what the next check counts. This is not bookkeeping for its own sake: the trigger used to compare dates across two files, so every miss logged on the same calendar day as a recalibrate was invisible — and since a recalibrate runs at session start while the session's misses are written at its end, *the common case silently dropped a whole session's evidence*.

**What the trigger counts.** Only rows whose miss-type begins with a documented token (`templates/learner/calibration-log.md` holds the list; `MISS_TYPES` in `tools/primer_state.py` must agree, and a test asserts it). Rows written as annotations — `(mastery signal, not a miss)`, `(examiner outcome: agreement)` — are deliberately not counted. Counting them inverted the signal for the strongest evidence the log carries: a demonstration of mastery raised the apparent need to correct the model.

Minor recalibrate does **not** rewrite stable traits or goals.

### Deep recalibrate — user-invoked (`/primer recalibrate`)

On demand, a full meta-session (not a lesson):

1. **Mine `calibration-log.md` for patterns** across all domains → promote recurring misses to stable traits / anti-preferences. (This is how a one-off observation legitimately becomes a rule.)
2. **Detect drift:** Are the goals in `profile.md` still current? Should any domain flip to `[mastered]`? Are the ZPD edges stale?
3. **Confidence audit:** List low-confidence markers — assumptions never actually tested — as candidates to probe in upcoming lessons.
4. **Re-confirm stable traits** with the learner: has register / struggle tolerance / correction style changed? People change; the profile should be allowed to.
5. **Compact volatile churn:** collapse superseded depth-marker history; archive resolved open-questions.
6. **Flag stale sources:** ask the ledger rather than re-reading the canon by eye — `primer_sources.py sources-stale` (past the freshness horizon, most-used first) and `sources-unverified` (the `[from-training, verify]` backlog). Both are queryable lists now, not remembered rituals; work the top of each. See `primer/research-protocol.md`.
7. **Output a "what I changed and why" diff** and apply on confirmation.

The distinction that matters: the minor tier keeps volatile state honest cheaply and automatically; the deep tier is the only place stable traits and goals get rewritten, and it does so on accumulated evidence with the learner in the loop — never on a single session.

## What this protocol is defending against

- **Profile rot** — markers that were true at intake and silently went stale. Confidence + evidence + time decay + the confidence audit catch it.
- **Optimism drift** — a closed self-assessment loop inflating its own certainty over time because it reads its own prior assessments as ground truth. The external anchor (cold retrieval feeds confidence both ways) and time decay are the guard.
- **Lucky-catch dependence** — useful observations (like the vocabulary-calibration rule) being noticed only when someone happens to. The calibration-log makes capture routine.
- **Append-only sprawl** — volatile state piling up until the profile is noise. The two recalibrate tiers compact it.
- **Over-fitting to one session** — rewriting a stable trait because of a single off day. Only deep recalibrate touches stable traits, and only on patterns.
