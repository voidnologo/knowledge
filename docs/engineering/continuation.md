# Continuation — fast resume

> Lean pointer for picking up primer dev. Read first at `session-start`. Kept short and current; history lives in `sessions/` and `DECISIONS.md`.

**Project:** primer — adaptive Primer-style learning system. Class/instance: public core (engine) + private per-user data repo (profile + lessons).

**Engine:** v0.5.2. Five test suites under `tools/`, all green.

## Last session (4) — first live end-to-end run

Sessions 2–3 reviewed and built. Session 4 was the first time any of it ran in front of a learner. A real lesson was taught (`backend-engineering / async-event-loop`, resumed from its `.STATE.md` sidecar, artifact written, sidecar removed) and the engine was observed doing it, with observations logged continuously rather than recalled at the end. Full record in `sessions/session-4-notes.md`; 15 findings, ranked, in `pending-tasks.md`.

**Validated:** the `!` injection notice (silent, as designed); M1's on-demand load table (read at the named points, with a note on which files are most tempting to skip and why); the research pass end to end (ledger asked first, sweep in a subagent, 20 verdicts recorded including 4 rejects, floor accreted from empty); `render`'s six checks and the `file://` handoff; state updates through the tooling rather than by hand; the examiner's separation, which produced a **better-argued verdict than the Primer's** and was applied over it.

The research pass earned its keep concretely: a source cited in the pre-built lesson body (`www.uvicorn.org`) no longer resolves, the `--workers` claim was attributed to a page that never discusses `--workers`, and the flat GIL claim needed a build-conditional qualifier after PEP 779. Four corrections to material already marked verified six weeks earlier.

**The three findings that matter most:**

- **The faded-figure guarantee does not hold** (F-06). A blanked `timeline` span renders at true geometry in both channels, so position answers the prediction while the label shows `?` — and `render` reports `faded-reveal integrity: passed`, because that check verifies the reveal *text* is DOM-gated. 97 passing tests were consistent with a validated page that hands over the answer. → **D-0029**.
- **The Deepen figure beat gets skipped entirely** (F-15). The learner raised this twice, unprompted: the staircase diagram arrived at evaluation time instead of while he was deriving it, and *"that was the whole point of adding the drawing tools."* The cause is not forgetfulness — the spec did not exist at the moment it was needed, because prose is faster than authoring a spec mid-conversation and reads as adequate. The visual layer's first live outing did not deliver its value despite working correctly. F-06 and F-15 compound: the beat that was skipped is also the beat that was broken.
- **The evidence model has no defence against a client that completes the learner's turn** (F-07). Prompt-suggestion ghost text pre-filled a complete correct answer to a probe, so every probe that session is void as evidence. Two recorded remediations have now failed to land — the 2026-06-16 one was never written to any file, and this session's was written and had no effect. The calibration log asserted a fix that did not exist, which is worse than the unfixed bug.

## Next up

1. **The figure subsystem — F-06, F-15, F-14, renderer parity.** Highest value: the faded beat is load-bearing pedagogy and it currently neither fires at the right time nor conceals what it should. Fix them together — F-15 alone produces a spoiled prediction beat instead of a missing one. Check `curve` and `quorum` for the same blanking hole. Give `ascii` a validation pass: it reaches the learner live and is the only channel with no gate.
2. **F-07** — assert the ghost-text setting at session start instead of trusting a log entry, and make the calibration log unable to record an unverified fix as resolved.
3. **F-01 / F-02 / F-13** — the Class A parser-vs-template items. All small, all mechanical.
4. **F-03 / F-08** — the adoption-path items (`sources-import` backfill; a re-calibration beat on resume). Both break exactly once per existing instance, which is why tests never see them.
5. **F-04 / F-05** — vocabulary and voice. The learner rejected two engine-authored phrasings within two turns, and `profile.md` attributes a word to him ("invariant") that he does not hold.
6. **Sycophancy baseline** — still unrun, and Session 4 argues it can't come from live lessons: sycophancy went untested because the learner never pushed back on a correct claim.

Unbuilt from Proposal 0003: **M2** (FSRS-6), **M3** (grounded prompt exemplars), **Wave D**. Known-open: the self-updater can't install itself (first adoption needs one manual `git pull`; belongs in the README).

## Don't re-litigate

`DECISIONS.md` D-0001…D-0029 are settled. Recent ones worth knowing before touching adjacent code: **D-0022** (progressive disclosure / on-demand load table), **D-0023/D-0024** (visual layer; specs not SVG; contracted explorables), **D-0025** (promotion writes to the learner's ledger, never to the public core's canon), **D-0027** (examiner never sees the proposed delta; disagreement holds rather than resolves), **D-0028** (third examiner outcome for magnitude divergence; `med` decays), **D-0029** (guarantees stated in prose get tests written from the prose). Touch them only with new evidence.

**Class-level lessons that keep recurring** — read before adding machinery:

- Session 3: 56 passing tests were consistent with six exploitable holes, because nothing adversarial was tested.
- Session 4: 97 passing tests were consistent with a documented guarantee not being provided, because the tests were written from the code. Where one spec has two renderers, the unvalidated one drifts — and it's the one with the tighter feedback loop.
- Session 4: a capability can be correct, documented, and never invoked, because the protocol describes it in a reference file instead of a numbered step and the cheaper alternative reads as adequate (F-15).
- Both sessions: new machinery assumes a greenfield instance, and the gap only shows at adoption.
