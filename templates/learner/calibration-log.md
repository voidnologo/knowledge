# Calibration Log

Append-only record of where the Primer mis-estimated the learner, and the adjustment. Mined by `recalibrate` (`primer/feedback-protocol.md`): repeated miss-types get promoted to stable traits or anti-preferences.

Miss-types: `too-basic` · `too-advanced` · `vocab-gap` · `dead-analogy` · `pacing` · `struggle-mismatch` · `retention-miss` · `escape-hatch` · `examiner-disagree`

Three of those are written by code or by a protocol step, so the exact token matters — the trend queries key on it:

- `retention-miss` — a failed cold retrieval (Elicit-step recall or `/primer review`). The external anchor on the *learner's* recall; lowers the domain's confidence.
- `escape-hatch` — the learner asked for the answer outright. Written by `primer_state.py hatch-log`; `hatch-trend` reports the rate per domain. The hatch is right to offer, so read a rising rate as the register being mis-set here, not as a failure.
- `examiner-disagree` — the Recap examiner reached a different verdict than the Primer, so confidence was **held** and a reprobe queued (`primer/examiner-protocol.md`). The external anchor on the *Primer's own judgment*. A high rate is a finding about the engine, not the learner.

Format: `<date> | <domain> | <miss-type> | <what happened> | <adjustment>`

---
