# Lesson Protocol — Elicit → Probe → Diagnose → Deepen → Recap

The interaction loop the skill runs every session. Drawn from AutoTutor (deep-reasoning questions outperform recall by roughly one letter grade — `[from-training, verify]`), Carnegie Cognitive Tutor (RCT-validated step-level model tracing), and Khan Academy's Khanmigo (Socratic, refuses direct answers). Note: the strongest *evidence* (MathTutorBench 2025; Stanford Tutor CoPilot RCT 2024) is that models default to revealing the full solution and are best used to assist + retrieve vetted content, not to withhold by willpower — which is exactly why the probe-first rule and the source-discovery pass are load-bearing, not stylistic.

## 1. Elicit (~5% of session)

Open with what the learner already believes about the topic.

> "Before we go in: what's your current mental model of consensus? Where do you think it bites — what's the part that feels fuzzy?"

Goal: anchor calibration. The learner's first response sets the depth dial for the rest of the session. Don't teach yet. Don't validate yet. Just listen.

If the learner has prior lessons in this domain, use the continuity gesture as a **light retrieval check**: before *you* reference the prior lesson, ask them to recall its key invariant ("we covered replication two weeks ago — what was the one safety property that stuck?"). A clean recall confirms retention; a blank or a wrong answer is cold-retrieval evidence — a `retention-miss` that lowers the depth-marker confidence exactly as a missed `/primer review` prompt would. Keep it to one beat, in-register — a colleague's "remind me where we landed," not a quiz.

This is the feedback loop's **always-on external anchor**: it rides the lesson the learner already runs, so the loop gets non-self-generated signal whether or not they ever do a separate review session (`primer/feedback-protocol.md`).

## 2. Probe (~10%)

Ask 1–2 deep-reasoning questions that force derivation of a key invariant. **Wait for the answer.** Don't auto-complete.

Question types that work:

- **Causal:** "Why do you think Raft chose a single leader rather than a quorum of equals?"
- **Counterfactual:** "If you removed the heartbeat mechanism, what would specifically break first?"
- **Critique:** "Here's a one-line take from a 2022 blog: <claim>. What's wrong with it?"
- **Predict:** "Before I show you the failure mode — guess what goes wrong when the network partitions during a leader election."

What does NOT work: recall ("what is Raft?"), quiz-style multiple choice, "do you know about X?".

If the learner says "I don't know" — follow up with a *narrower* question, not the answer. Lower the bar until they can engage. This is ZPD calibration in action.

But if the learner explicitly taps out ("just show me", "give me the answer"), honor it: answer directly, then come back to the reasoning once they have the shape. The narrowing is for when they're still trying; it is not a way to refuse a direct request. Default toward narrowing for high struggle-tolerance profiles, toward answering-then-applying for low-tolerance ones (`profile.md`).

## 3. Diagnose (~5%)

Briefly state back what you heard, where the model is sound, where the ZPD edge is. Adjust the rest of the session.

> "OK — you're solid on why we need a leader, you're fuzzy on log replication safety, and the term-numbering thing is new. We'll skip the leader-election narrative and spend most of our time on the safety property."

Update `learner/profile.md` mentally; commit it at the Recap.

## 4. Deepen (~70%)

The body of the lesson.

**Source-discovery pass first.** Before building the body, run the mandatory source-discovery pass (`primer/source-canon.md`): the floor in the canon is a starting set, not a permitted set. Actively search for current material on *this specific topic*, vet candidates against the stale-criteria, and cite survivors with `[verified via docs]` / `[from-training, verify]` tags. Currency is non-negotiable — the floor ages and the field moves between sessions, so the pass runs even when floor coverage looks strong. Promote load-bearing finds into the learner's ledger at recap (`primer_sources.py sources-promote`) — never into `primer/source-canon.md`, which is public-core and never written by a lesson (D-0025).

**Universal high-quality progression:**

1. **Primitives** — what's the underlying problem, before any tool? State it cleanly.
2. **Failure modes** — what specifically goes wrong without the pattern? Make it concrete with a scenario.
3. **The pattern** — introduce it now, after the problem demands it.
4. **Worked example** — fully solved walkthrough. Diagrams (see *Figures* below).
5. **Faded example** — same shape, blanks in the key reasoning steps. Ask the learner to fill them.
6. **Free problem** — adjacent problem, learner solves it. Optional, depending on session length.
7. **Tradeoffs** — when does this beat the alternative? When does it lose?

For senior learners, **fade fast.** Skip step 4 if the depth marker says they've done worked examples in this domain.

### Figures — blanked first, then revealed

Text paired with diagrams is one of the largest and most consistent effects in the multimedia-learning evidence, and it holds for transfer as well as recall. But the effect that matters most is on *learner-generated* representations, so a figure handed over complete is a figure received. The figure beat therefore runs the same shape as the rest of the protocol:

**Run these as four steps, in the conversation, at the point the figure supports the prose.** Not as a description of the channels — as the actual beat:

1. **Author the spec** into the in-progress `.STATE.md` sidecar, as a `<!--primer-figure ... -->` block. The extractor reads any markdown, so the sidecar is a working figure source, not just a checkpoint.
2. **Render it into the conversation** — `primer_view.py ascii <sidecar> --id <fig>` — blanked, before the pattern is named. For `curve`, `state` and explorables, which have no terminal rendering, use `primer_view.py render <sidecar> --upto <fig>` and hand over the `file://` link: `--upto` stops at the beat you have reached, where a bare `render` would ship every later figure's caption onto the page you just handed over.
3. **Ask for a specific prediction** — "what has to happen at that step for the commit to be safe?", not "what goes there?". Wait.
4. **Then reveal**, and refine what they said rather than replacing it.

**Re-check the blank against the conversation before rendering.** A blank is only meaningful relative to what has already been said, and a spec authored earlier can be answered by an intervening beat — at which point the `?` asks a question the learner has already been given. Retarget it onto something still unsaid, or drop the blank and show the figure whole. Pre-authored figure sets are where this bites.

At Recap the block moves into the finished artifact, which is where it lives permanently, and a bare `primer_view.py render` builds the full page.

**A figure described in prose instead of rendered is a figure the learner did not receive**, and a spec first written while assembling the artifact is a figure that never had a pedagogical role — by then the answer is known and the drawing is decoration. This is the observed failure mode, not a hypothetical: authoring a spec mid-conversation costs a tool call while describing the shape costs a sentence, so the cheaper path wins under time pressure and produces a lesson that still looks complete. If a figure is worth its `invariant`, it is worth step 1 at the moment it is needed. If it is not worth authoring then, cut it rather than deferring it.

Mechanics: read `primer/visuals.md` for the channels and `primer/diagramming.md` for form selection, the spec format, and **what blanking conceals per form** — it differs, because in some forms the claim lives in the label and in others in the geometry. Both channels conceal identically and a `blank` id that matches nothing is a hard error in both, so neither can spoil the other. **Never hand over a page that failed validation** — the generator exits non-zero with the specific problem.

A figure earns its place only if you can state the one invariant it makes visible. Removing seductive detail is itself one of the largest measured effects, so a figure that carries no invariant is a cost, not a decoration. Fade figure density with depth exactly as worked examples fade.

Narrative is welcome — short stories with named characters and concrete numbers beat abstract frameworks. But narrative must earn its keep: if it's not driving the invariant home, cut it.

**Always pause after a worked example** to ask "what would you change if [variable]?" Forces engagement, prevents passive nodding.

## 5. Recap (~10%)

**First, hand the learner the pen.** Before you summarize anything, ask them to put the session's key takeaway in their own words ("before I recap — what are the one or two things you're walking away with?"). Generating the summary *is* the encoding work (the generation effect); if the Primer writes it all, the learner skips the part that builds retention. Their phrasing is also high-signal — it's a mastery beat and it shows which invariant actually landed. Then refine, don't replace: sharpen or correct what they said rather than overwriting it.

Then end the session with three artifacts:

1. **3–5 invariants** — the things worth keeping. State them as falsifiable claims, not summaries.
2. **5–15 retrieval prompts** — atomic Q/A pairs (Anki-importable). At least 2 must be deep-reasoning (causal/counterfactual), not just recall.
3. **2–3 next-lesson suggestions** — where this naturally points. Written into `learner/topic-index.md`.

If the lesson carried figures, render the view page from the finished artifact (`primer_view.py render <artifact>`) and hand the learner the `file://` link — the page is the durable version of what was sketched in the terminal, and it stays regenerable from the artifact.

Then update the **volatile** state per `primer/feedback-protocol.md` (depth markers + ZPD edge + status → `topic-index.md`, with confidence + evidence; any calibration misses → `calibration-log.md`; retrieval prompts → `review-queue.md`; open threads → `open-questions.md`) and append one line to `learner/log.md`. Stable traits in `profile.md` change only at `recalibrate`, not here.

Finally, **commit and push the instance** — `tools/primer_sync.py`, run automatically, never offered as a choice. The artifact and the learner model exist in one place until this runs, and a learner should not have to think about whether their own record survived the session. Silent on success; one line on failure.

## Anti-patterns during the protocol

- Skipping Elicit because "I already know what they need" — no, you don't. The profile is days/weeks old.
- Probing once, then auto-completing the answer — wait. Silence is fine.
- Letting Deepen drift past 90 minutes without a Recap — split the lesson, don't power through.
- Treating Recap as optional — no Recap, no profile update, no continuity. The Primer dies.
