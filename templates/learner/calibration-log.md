# Calibration Log

Append-only record of where the Primer mis-estimated the learner, and the adjustment. Mined by `recalibrate` (`primer/feedback-protocol.md`): repeated miss-types get promoted to stable traits or anti-preferences.

Miss-types: `too-basic` · `too-advanced` · `vocab-gap` · `dead-analogy` · `pacing` · `struggle-mismatch` · `retention-miss` · `escape-hatch` · `examiner-disagree` · `register-miss` · `analogy-transfer`

**This list is the vocabulary the trigger counts.** `recalibrate-check` counts a row only when its miss-type *begins with* one of these tokens, so `too-advanced (intake mis-scope)` counts and `(mastery signal, not a miss)` does not. That is deliberate — annotation rows belong here (see below) and must not inflate the count. It also means an undocumented token is invisible to the trigger, so add it here and to `MISS_TYPES` in `tools/primer_state.py` together; a test asserts the two agree.

Five of these are written by code or by a protocol step, so the exact token matters — the trend queries key on it:

- `retention-miss` — a failed cold retrieval (Elicit-step recall or `/primer review`). The external anchor on the *learner's* recall; lowers the domain's confidence.
- `escape-hatch` — the learner asked for the answer outright. Written by `primer_state.py hatch-log`; `hatch-trend` reports the rate per domain. The hatch is right to offer, so read a rising rate as the register being mis-set here, not as a failure.
- `examiner-disagree` — the Recap examiner reached a different verdict than the Primer, so confidence was **held** and a reprobe queued (`primer/examiner-protocol.md`). The external anchor on the *Primer's own judgment*. A high rate is a finding about the engine, not the learner.
- `register-miss` — the voice, vocabulary, or figure delivery didn't fit, and the learner said so. This is the "style confirmation" signal `feedback-protocol.md` asks the Primer to infer; before it existed there was nowhere to write it. A recurring one is a candidate anti-preference.
- `analogy-transfer` — an analogy carried the *structure* across correctly and the *magnitude or cost* incorrectly. Distinct from `dead-analogy`, which is an analogy that failed to connect at all: this one connected and was productive, and then mispriced something. Worth its own token because the correction is different — you keep the analogy and fix the number.

**Annotation rows are welcome and are not counted.** A row whose miss-type is written in parentheses — `(mastery signal, not a miss)`, `(intake floor-finding, not a miss)`, `(examiner outcome: agreement)` — records evidence that belongs in this file without registering as miscalibration. Mastery signals in particular should be written here; they are the strongest evidence the log carries.

`recalibrate-mark` is written by `primer_state.py recalibrate-mark` when a minor recalibrate runs. It is a positional marker: everything below the last one is what the next check counts. It is not a miss-type and never counts itself.

Format: `<date> | <domain> | <miss-type> | <what happened> | <adjustment>`

---
