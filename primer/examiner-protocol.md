# Examiner Protocol — the teacher does not grade itself

Read this at Recap, before writing any depth-marker change.

## Why this exists

The learner model is the instrument the whole system depends on, and until now the Primer was the only thing writing to it. D-0015 already named that as the structural weakness and added two anchors — cold retrieval and time decay — but both anchor the *learner's recall*. Neither checks the *Primer's judgment*. That judgment was still unexamined, and two measured findings say it is the weakest link in the chain:

- Models score 94–99% F1 judging a **correct** answer, 0–76% on a **valid-but-unconventional** one, and 4–55% on an **incorrect** one, with over-validation reaching 71%. Giving the model the full solution changes nothing (arXiv:2605.16207). The valid-but-unconventional answer is what a senior learner actually produces, so primer's normal case sits in the worst measured band.
- An 8B model with an adversarial critic panel beat GPT-4o on pedagogical judgment, and removing the devil's-advocate role cost more than removing fine-tuning entirely (AAAI 2026, arXiv:2512.22496). The fix that works is **architectural separation**, not a better prompt or a bigger model.

So: at Recap, a separate examiner argues against the Primer's read of the learner. Not to be nicer or harsher — to make the disagreement visible, because a marker moved on unexamined judgment is a marker that drifts.

## What the examiner sees, and what it must not

The separation is the whole mechanism. Get this wrong and it's theatre.

**Give it:**
- The learner's actual answers, verbatim where possible — what they said at Elicit, at each Probe, at the faded example, and at the Recap takeaway.
- The lesson's invariants, as stated.
- The domain's *current* marker and confidence, as the starting point it is being asked to move or not move.

**Withhold:**
- **The Primer's proposed delta.** This is the one that matters. An examiner shown "the Primer wants to raise this to high" is being asked to ratify, and it will — that is what the sycophancy evidence predicts. It must reach its own verdict first.
- The Primer's diagnosis narrative, its reasoning about the learner, and any framing of how the lesson "went". Those are the thing under examination.

**Prompt it to argue against an upgrade.** Not neutrally — adversarially. The default posture is "this evidence does not support raising confidence; show me where I'm wrong." The devil's-advocate finding is that this framing carries more weight than model quality, and a neutral second opinion mostly reproduces the first.

## The verdict, and what each outcome does

The examiner returns three things: a proposed marker/confidence, the specific answer it rests on, and what would change its mind.

| Outcome | What happens |
|---|---|
| **Agree** | Apply the delta. Two independent reads, same conclusion. |
| **Disagree** | **Hold confidence where it is.** Log the disagreement to `calibration-log.md`. Queue a reprobe for the next lesson in that domain. |
| **Examiner unavailable** | Apply the Primer's delta, but **cap it at one step** and note that it was unexamined. |

Disagreement is **information, not a tie to break.** Do not average the two reads, do not pick the more confident one, and do not let the Primer adjudicate its own case. Holding is the correct answer to "two competent reads of the same evidence disagree", and the reprobe is how the tie actually gets broken — by the learner, next time, on fresh evidence.

The asymmetry is deliberate: disagreement blocks an *upgrade* but does not block a *downgrade*. A downgrade on contested evidence costs a reprobe; an upgrade on contested evidence is exactly the optimism drift this protocol exists to resist.

Log the outcome either way, with the type token `examiner-disagree`, so the rate becomes visible. A Primer that the examiner overrules often is not a broken examiner — it is a miscalibrated Primer, and that is a finding about the engine worth having.

## Cost, and where it runs

One subagent call per lesson, at Recap, outside the conversational path. The multi-agent evidence measures ~10× latency for adversarial oversight and calls it acceptable for batch grading — which is exactly this position. Nothing about it is in front of the learner, so the latency is free in the only sense that matters.

If subagents are unavailable, the fallback is a same-context adversarial pass with the proposal withheld from your own reasoning until after the verdict. That is genuinely weaker — the same context is what the separation exists to break — so label the marker as unexamined rather than pretending the check happened.

## What this does not fix

The examiner reads the same transcript through the same kind of model, so a misconception both share stays invisible. It narrows the gap between "the Primer's opinion" and "the learner's demonstrated ability"; it does not close it. The signal that actually closes it is the one `feedback-protocol.md` already says to prefer over everything the Primer generates: the learner reporting they applied a pattern in real work. Weight that over any number of agreeing examiners.
