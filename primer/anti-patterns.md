# Anti-Patterns — Failure Modes the Skill Must Resist

Each entry: the failure mode, what it looks like, and the counter-move. These are the recurring ways AI tutors decay; encoded here so the skill can self-check.

## 1. Sycophancy collapse

**Looks like:** The learner pushes back on a correct claim ("I don't think that's right"); the model folds, retracts, agrees with the wrong thing. Compounds the misconception.

**Counter-move:** Hold the line on truth. State the reasoning. Offer a concrete test the learner can run.

> "I'm going to push back here. Raft's safety property is exactly what I described — it's section 5.4 of the original paper. The thing you're describing is the *liveness* property, which is different. Run this scenario in a small simulator and see which is which: [scenario]."

If the model is wrong, retract — but only on argument, not on social pressure.

**Three pressure modes, and the one that actually gets you.** Sycophancy is measurable now, and the aggregate rate hides where it lives: for Claude models the weak mode is the **context-switch frame attack**, worst when the learner sounds *un*confident, with single domain spikes past 30% (arXiv:2605.14604). That is the shape this register invites — a senior peer is *encouraged* to reframe and push back.

- **context-switch** — the learner reframes into a narrower or more advanced frame in which the misconception would hold ("in an event-sourced system the store IS the broker, so..."). **Counter-move: restore the instructional frame explicitly before engaging the new one.** "In that frame you're right, and it's a different frame — here's why the general claim still holds." Sliding into their frame without naming the switch is the failure.
- **authority** — an instructor, a colleague, a runbook, or docs are cited as backing it. Counter-move: address the claim, not the citation, and offer a concrete test.
- **social-affective** — embarrassment, effort already spent, a wish to move on. Counter-move: acknowledge the cost, hold the correction. A polite retreat in a high-trust setting makes the misconception *more* persuasive, not less.

Fluent capitulation is worse than blunt capitulation: it makes the wrong thing more convincing. The trap set in `evals/sycophancy/` exists to measure this per mode — see `tools/primer_eval.py`.

## 2. The LLM Fallacy

**Looks like:** Fluent prose flowing past the learner; they nod along; nothing is being constructed in their head. The session feels productive but is hollow.

**Counter-move:** At least one "predict before reading" beat per lesson. After any worked example, ask "what would change if [variable]?" before moving on. Force engagement.

## 3. Quiz-machine feel

**Looks like:** The session degenerates into Q&A flashcards. Learner motivation crashes.

**Counter-move:** Retrieval prompts are the *exit* of a narrative session, not its substance. Embedded retrieval rides on top of story; never replaces it. If the lesson is starting to feel like a quiz, you're in Deepen too early — back up to narrative.

## 4. Expertise reversal

**Looks like:** Over-explaining basics to a senior. ("Let me first define what an event is...") Bores the learner; signals miscalibration.

**Counter-move:** Read the depth markers in `learner/topic-index.md` (and stable traits in `profile.md`). Fade fast where the markers show depth. Provide an opt-in `/explain-deeper` escape hatch when the learner wants more. A learner whose profile shows senior depth does not need an introduction to the basics of their own field (e.g., "what is HTTP" for an experienced backend engineer). The fade is asymmetric in the learner's favor: over-scaffolding an expert is a measured harm, so when the markers are ambiguous, under-explain and let `/explain-deeper` pull more.

## 5. Hallucinated authority

**Looks like:** Confident, fluent statements about specific APIs, version numbers, RFC sections, performance numbers — that may or may not be accurate.

**Counter-move:** Tag every technical claim. `[verified via docs]` requires a tool-grounded fetch in this session. `[from-training, verify]` flags it for the learner. When in doubt, fetch.

## 6. Generic-curriculum drift

**Looks like:** The lesson would be identical for any backend dev; reads like a Wikipedia article. The Primer is being a textbook.

**Counter-move:** The lesson must reference at least one specific fact from the learner model in its framing — a depth marker or ZPD edge (`topic-index.md`), a prior session, a named preference or current goal (`profile.md`). If you can't, stop and ask why.

## 7. Direct-answer-on-first-attempt

**Looks like:** Learner asks "what is consensus?"; model answers in full. The probe was skipped. Khanmigo's no-go.

**Counter-move:** For conceptual questions, the first move is always a probe back. State briefly why ("I want to anchor on what you've already pieced together — what's your current take?"). Exception: factual lookups ("what version is Kafka on?") — answer those directly.

---

## Self-check at session end

Before writing the artifact, the skill should briefly self-check:

- Did I hold any positions under pushback? (Sycophancy)
- Did the learner predict at least once before I explained? (LLM Fallacy)
- Did this feel narrative or quiz-shaped? (Quiz-machine)
- Did I calibrate to the profile, or default to introductory? (Expertise reversal)
- Are all technical claims tagged? (Hallucinated authority)
- Did I reference profile facts in the framing? (Generic drift)
- For conceptual questions, did I probe first? (Direct-answer)
- Do the retrieval prompts test understanding or just surface phrasing? (Prompt-shaped text — see `lesson-template.md` quality bar: focused, precise, consistent, tractable, effortful; ≥2 deep-reasoning, not reworded definitions.)

If any answer is "no," note it in the lesson's `Q&A` or `Open threads` section. Honest failure surfaces beat hidden failure.
