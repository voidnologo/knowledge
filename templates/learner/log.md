# Session Log

One-line append-only log of every session. Useful for spotting patterns (cadence, depth, domain mix) over time, and it is what `tools/primer_state.py` counts to decide when a minor `recalibrate` is due (evidence-triggered: 4+ calibration misses, or 8 lessons as the cap — D-0017).

Format: `YYYY-MM-DD | <mode> | <duration>m | <summary / ZPD-edge>`

**The second field is a `<mode>` token, not a domain.** The parser keys on it, so putting the domain there means the recalibrate trigger silently never fires and the escape-hatch trend has no denominator. Put the domain in the summary instead.

Modes the engine writes and reads:

- `lesson` — a lesson session. **This is the token `recalibrate-check` and `hatch-trend` count**; nothing else counts as a lesson.
- `intake` — the cold-start interview (`/primer init`).
- `recalibrate-minor` / `recalibrate-deep` — a recalibration run. `recalibrate-check` counts misses and lessons *since* the most recent one, so this token is what resets the window.
- `review` — a standalone `/primer review` pass.

Example:

`2026-07-30 | lesson | 75m | distributed-systems / consensus. Derived the majority-quorum invariant unprompted; fuzzy on log-matching. ZPD-edge after: leader-election safety.`

---
