# Pending Tasks

Live checklist for primer engineering. `session-end` checks off / prunes completed items and adds new ones. Completed work lives permanently in the session notes, not here.

## Next Up

- [ ] **Run a real intake** (`/primer init`) to replace the generic migrated profile with a rich, evidence-backed one in primer-data.
- [ ] Confirm `session-start`/`session-end` skills match the house style after first real use.

### From Proposal 0001 (cold review — see `proposals/0001-cold-review-and-improvements.md`)

Wave A — corrections (factual + de-personalization), low risk: **[done — Session 3]**
- [x] **C4** — fixed overstated effect-size claims in `REQUIREMENTS.md §2`; tagged AutoTutor claim.
- [x] **C3** — tagged canon floor edition/date entries `[edition — verify]`; added verify discipline.
- [x] **C1** — de-personalized `system-prompt.md`; canon → starter pack; per-instance domain list; generalized `anti-patterns.md` #4 + fixed stale depth-marker path.

Wave B — close the feedback loop (the structural fix): **[done — Session 3]**
- [x] **C2** — forgetting-aware confidence decay + bidirectional confidence + decay in minor-recalibrate.
- [x] **T1** — `/primer review` miss → calibration-log + confidence drop.
- [x] **E1** — cold-retrieval score recorded; `review-queue.md` Review-history section (self-authored caveat).
- [x] **T7** — "just show me" escape hatch gated on struggle-tolerance.
- [x] Promoted to `DECISIONS.md`: D-0014 (no hardcoded learner), D-0015 (external anchor + decay), D-0016 (effect-size target).

Wave C — quality & hygiene: **[done — Session 3]**
- [x] **T2** — prompt-quality rubric (Matuschak's 5 attributes + conceptual pattern language) + self-check.
- [x] **T5** — reconciled resume/artifact path → sidecar `<date>-<slug>.STATE.md` (SKILL.md, lesson-template, .gitignore).
- [x] **T6** — privacy hardening documented in README (recommended global `~/.claude/settings.json` deny block; repo `.claude/*` is gitignored).
- [x] **T4** — evidence-triggered recalibration (M=4 misses OR N=8 cap); D-0017 supersedes D-0004's fixed N=5.

Wave D — resolved into goals + Proposal 0002:
- [x] **T3** — resolved: self-contained in-repo scheduling (not Anki). Folded into Proposal 0002. (D-0018)
- [x] New goals captured: **D-0018** (self-contained; bookkeeping-as-code), **D-0019** (Goal 5 — cultivate learning habits). Anchor reworked onto the lesson flow (Elicit recall); `/primer review` now optional + habit-building.
- [x] **E3** — generation-effect tweak (learner states the takeaway before the Primer summarizes). `lesson-protocol.md §5`.
- [x] Consistency sweep: fixed stale "every 5 lessons" in SKILL.md and two depth-marker→`profile.md` paths (→ `topic-index.md`).
- [ ] **E2** / **E4** — still deferred until post-use data.

### Proposal 0002 — deterministic state layer + habit-formation: **[decided & built — D-0020]**

See `proposals/0002-…md`. Decisions resolved:
- [x] **Source of truth** — markdown stays source of truth; **no SQLite** (binary-in-git breaks cross-machine sync; no scale benefit). A gitignored rebuildable cache is a future option only.
- [x] **Scheduler** — SM-2 (FSRS deferred until there's review volume).
- [x] **Build order** — state layer first. **Script language** — Python 3.11+ stdlib-only (portable).
- [x] Built `tools/primer_state.py` + `tools/test_primer_state.py` (19 tests passing) + `tools/README.md`; wired into SKILL.md / feedback-protocol.md / review-queue template.

### Next up (morning)
- [ ] Run a real `/primer init` intake against the de-personalized engine, writing into the new state layer (first true end-to-end run).
- [ ] Verify `init-instance.sh` seeds the new `review-queue.md` format on a fresh instance.
- [ ] Consider merging `proposal-0001-review-and-fixes` → `main` (rebase first; `origin/main` advanced).
- [ ] Remaining habit-formation surface (proactive nudges, retention-trend payoff, meta-learning asides) — grow with real use.

### Proposal 0003 — visual layer + capability refresh: **[proposed — awaiting scope decision]**

See `proposals/0003-visual-layer-and-capability-refresh.md`; evidence in `research/2026-07-30-capability-and-evidence-refresh.md`. Maintainer-stated next tasks are **Wave A (presentation)** and **Wave E (research)**, with **M1 first** so the added instructions fit the context budget.

- [x] **M1** — progressive disclosure: only `system-prompt.md` is static; the rest are an on-demand load table routed per verb. (D-0022, PR #5)
- [x] **Wave A** — V1 `diagramming.md` + `visuals.md` rewrite; V2 local `<slug>.view.html` (single file, zero external requests, gitignored derived product); V3 contracted explorables (generated wiring, no model-authored JS); V4 `tools/primer_view.py` render+validate (5 gates) + 56 tests; V5 `/primer view` verb, Deepen-step blanked-figure beat, lesson-template spec convention, instance gitignore; V6 six-form figure template library with blanked variants. (D-0023, D-0024, PRs #5/#6/#7)
- [x] **Wave A hardening** — adversarial code review found 6 criticals with reproductions (manifest comment breakout → script injection; attribute injection via untyped slider bounds; write-before-validate leaving an invalid page at the clickable path; ASCII channel not honouring blanks; external-request scan gaps + false positives; formula compiler filtering an alphabet instead of parsing a grammar). All fixed, 97 tests. See D-0023.
- [ ] **Wave A follow-ups** — author figures for the first real lesson and see which forms the template library is missing; promote load-bearing shapes in (the library accretes like the canon). Consider ASCII renderers for `state`/`curve` if the terminal beat wants them.
- [x] **Wave A re-verification** — asked the reviewer to check its own six criticals rather than trusting the patch. Five held; **C-6 did not**: the unary fix concatenated sign tokens into JS `--`/`++`, so `- -rho` emitted valid pre-decrement that returned the wrong number *and* mutated the shared input object — worse than the bug it replaced, and passing all six checks. Fixed in #8, now node-verified.
- [ ] **Review-loop lesson worth keeping:** 56 passing tests were consistent with six exploitable holes, because nothing adversarial was tested. Any future engine code that interpolates model-authored strings should get hostile-input tests as part of the first commit, not after a review.
- [x] **Wave E** — R1 `primer/research-protocol.md` (query classes, vetting decision procedure, coverage floor); R2 sweep runs in a subagent, off the lesson thread; R3 `tools/primer_sources.py` + `templates/learner/source-ledger.md` (35 tests, hostile-input coverage from the first commit); R4 per-domain sweep cache with a freshness horizon + `grounds:` claim provenance in the artifact frontmatter. Resolved a latent conflict: promotion was documented as writing into the public core's canon, which leaks what the learner studies and conflicts on every pull. (D-0025)
- [x] **Wave B** — H1 `primer/examiner-protocol.md` + Recap wiring (examiner never sees the proposed delta; disagreement holds rather than resolves); H2 `evals/sycophancy/traps.json` (12 traps, 3 pressure modes, 5 domains) + `tools/primer_eval.py` pressure-resolved scorer + per-mode counter-moves in `anti-patterns.md`; H3 `hatch-log`/`hatch-trend` with lessons as the denominator. (D-0027)
- [x] **Fixed stale template drift** — `templates/learner/log.md` documented the second field as `<domain>` while the parser keys on a `<mode>` token, so a *fresh* instance would have had a silently dead recalibrate trigger and no hatch-trend denominator. The maintainer's own instance was correct, which is why it never surfaced. Added template↔parser agreement tests (mutation-verified) so the class can't recur.
- [ ] **Run the sycophancy eval** against a live primer session and record the baseline — the trap set and scorer exist; no results yet.
- [ ] **Self-updater follow-ups** — bump `VERSION` per release; consider a tarball path if non-git installs appear.
- [ ] **M2** revisit D-0020c → FSRS-6 with pretrained defaults; **M3** ground prompt generation in graded exemplars (+ fix bad-prompt-vs-forgotten conflation).
- [ ] **Wave D** (defer until real lesson data) — S1 simulated-learner regression suite; S2 opt-in SessionStart hook; S3 teach-it-back mode.
- [ ] **X1** — hedge the "every existing learning skill is session-scoped" claim in the README/research (several Claude Code learning skills now ship persistence; three vendors ship Socratic study modes).
- [ ] **X2** — re-verify snippet-only figures before citing (Mayer / drawing / PhET meta-analyses, LearnLM RCT); June artifacts' freshness horizon is ~2026-09.

### From Session 4 — first live end-to-end run of v0.5.2 (see `sessions/session-4-notes.md`)

Ranked by severity. F-numbers match the session notes.

**Blocking a correct lesson beat: [fixed — Session 4, together]**
- [x] **F-06 — the faded-figure guarantee did not hold.** A blanked `timeline` span rendered at true geometry in *both* channels, so position answered the prediction while the label showed `?`, and `render` reported "faded-reveal integrity: passed" (that check verifies only that the reveal *text* is DOM-gated). Fixed: a blanked span now emits no coordinates at all — the page draws a full-plot-width `pv-blank-region` on that actor's row, the terminal fills every cell not claimed by a visible span with `░`. Also closed the **axis leak**, which was the subtler half: a derived axis is exactly the hull of the spans, so it is precisely wide enough for the true answer and the bounds give the position away — at the limit totally, since a blanked span on a 0–2000 axis has nowhere to sit but on top of the other one. Blanking a span now **requires a declared `axis {min,max}`** with room for the wrong answer, and a span outside it is rejected. Audited the other five forms: `curve` was already correct (it cuts the series and draws an unresolved region), `quorum` correct (blanking `progress` removes the shading *and* the caption). `sequence`/`state`/`layers` blank labels only, which matches their claims — now documented per form in `diagramming.md` rather than left implicit, with the note that wanting to blank something the table says isn't concealable means the form is wrong for the claim.
- [x] **F-14 — `ascii` silently truncated labels well inside the documented budget.** The gutter was a hard 14 chars, so `requests 81-100` (15 chars, budget 34) became `requests 81-10` — which reads as a different range, not as truncation. Fixed: the gutter sizes to the longest actual label, capped at `MAX_LABEL`, and actor labels now go through `_plain_label` so an over-budget label is *rejected* in the terminal exactly as on the page.
- [x] **Renderer parity as a tested property.** `TestBlankConcealsTheClaim` and `TestAsciiLabelBudgetParity` assert it directly rather than trusting two implementations to have made the same choice: for each blanked id, both channels conceal the same row, emit exactly one unresolved region/field, and reject the same specs. Tests written **from the prose**, per D-0029. Mutation-verified — reverting each of the four behaviours fails 9 tests. 121 tests in the view suite, all five suites green.
- [x] **F-15 — the Deepen figure beat got skipped entirely; specs were authored at artifact time.** Fixed as a **numbered four-step beat** in `lesson-protocol.md` (author the spec into the `.STATE.md` sidecar → `primer_view.py ascii` into the conversation → ask the prediction → reveal), surfaced in `SKILL.md` step 4 so it reaches a run that never opens the reference file, and named as an anti-pattern in `visuals.md` ("describing a figure in prose instead of rendering it", "authoring the spec at Recap"). The prose now states the consequence explicitly — a figure described in prose is a figure the learner did not receive, and if it isn't worth authoring at the moment it's needed, cut it rather than deferring it. `SKILL.md` step 6 also says that a spec first written while assembling the artifact missed its beat and should be flagged in open threads rather than left looking taught.
- [x] **Verified end-to-end on the real artifact**, which is the only check that would have caught the original: restored `blank` on the lesson's `await-handoff-overlap` figure with a declared 0–4000 axis. Pre-gate the page now emits one `pv-span` rect (A, width 190 of a 380 plot) and one `pv-blank-region` (B, width 380) — the learner cannot tell whether B overlaps A or follows it, which is the prediction. Terminal agrees.

**Follow-ups this opened (not blocking):**
- [ ] `layers` cannot blank the boundary's *position*, only its label — and `diagramming.md` says "the boundary is usually the invariant", which is ambiguous between the two. If positional boundary blanking is wanted, it needs the same treatment `timeline` just got. Documented as a limitation for now.
- [ ] `ascii` still has no validation *pass* equivalent to `render`'s six checks; it now rejects what `render` rejects for the paths exercised, but that parity is asserted by tests rather than by a shared gate. A single validate-then-emit entry point for both channels would make it structural.

**Evidence integrity:**
- [ ] **F-07 — the engine has no defence against a client that completes the learner's turn.** Prompt-suggestion ghost text pre-filled a complete correct answer to a probe; every probe this session is void as evidence. Two recorded remediations have now failed to land (2026-06-16's was never written to any file; this session's `promptSuggestionEnabled: false` in project settings had no effect). Needed: assert the setting at session start rather than trusting a log entry; make the calibration log distinguish *observed* from *fixed* so an unverified fix can't be recorded as resolved; and name the environment as a source of failure in `anti-patterns.md`, where every entry is currently written as something the model does.
- [ ] **F-01 — `recalibrate-check` counts non-miss rows as misses.** Fired on "5 misses ≥ 4" when 2 of the 5 rows are annotated `(not a miss)`; real count 3. Count only rows whose miss-type is in the documented token vocabulary; treat the rest as annotations. Note the inversion this creates: a *mastery signal* currently increases the apparent need for correction.
- [ ] **F-02 — add `register-miss` to the miss-type vocabulary.** `feedback-protocol.md` instructs the Primer to infer "style confirmation" and there is no token to record it. Two register corrections landed in two turns this session with nowhere to file them.
- [ ] **F-13 — `sources-add` exits 0 on validation failure.** A `set -e` loop silently drops entries; the sweep agent caught three only by reading stdout. Rejects are the entries most worth keeping. Exit non-zero. (Error messages themselves are good — specific and actionable.)

**Adoption / migration:**
- [ ] **F-03 — no ledger backfill path.** `sweep-check` reported "no recorded sweep" for a domain with two prior artifacts and 8 already-vetted sources, so the first post-upgrade lesson re-pays for a sweep it has already done, once per domain, in every existing instance. Add `sources-import` walking `$DATA_DIR/lessons/**/*.md` frontmatter; invoke it from `migrate`. Accept both `grounds:` and the older `backs:` key.
- [ ] **F-08 — resume has no re-calibration beat.** The resumed sidecar was stale three independent ways: a cited source's domain no longer resolves; its primary probe telegraphed the answer in exactly the way a *later* calibration-log entry forbids; and its premise had been resolved by a lesson that ran after it was drafted. Resume should re-check `freshness_check` against the horizon, diff the sidecar's assumptions against calibration-log entries newer than its date, and confirm the premise against the current marker. Three reads, all three would have fired.

**Vocabulary and voice (Class D — the engine's own text as an uncontrolled corpus):**
- [ ] **F-04 — `invariant` is unglossed engine vocabulary, and intake wrote it into the learner model as the learner's own.** The learner does not hold the word; `profile.md` nonetheless asserts he *"wants to derive invariants"*. Gloss or replace it in learner-facing protocol text; audit `templates/learner/*` and the intake protocol for other house terms (`ZPD edge` is next, and it appears as a section header in a file the learner is invited to edit); stop intake phrasing learner traits in vocabulary the learner hasn't used.
- [ ] **F-05 — the engine's instruction prose trains the register the learner rejects.** "the one X" and "load-bearing" are house dialect across `SKILL.md`, `system-prompt.md`, `research-protocol.md`, `source-canon.md`, `feedback-protocol.md`, `lesson-protocol.md` — and they surfaced in the teaching voice twice in consecutive turns. Add them to the avoid-list, and de-tic the engine's prose: an avoid-list that contradicts the volume of surrounding text loses.

**Documentation / smaller:**
- [ ] **F-12 — `hatch-log`/`hatch-trend` are absent from SKILL.md's command list.** They exist only in `feedback-protocol.md`, which M1 made an on-demand read, so a run that never opens it can't know the hatch counter exists. Same risk applies to any command documented only in a deferred file — audit the set.
- [ ] **F-10 follow-up — SKILL.md's step order spoils the Elicit anchor.** **Plan** (step 3) precedes **Run the protocol** (step 4, containing Elicit), so a literal plan paragraph hands over the invariant the cold recall is meant to test. Say explicitly that the plan stays non-spoiling until after Diagnose.
- [ ] **M1 observation — trim `system-prompt.md`'s restatements to pointers.** The on-demand files most tempting to skip are the ones whose summary lives elsewhere, and the value is concentrated in the part the summary omits (`source-canon.md`'s stale-criteria is the example — it's what prompted the free-threading currency check).
- [ ] **`log.md` is the one state file with no helper command**, and it's the one append I got wrong (inserted out of chronological order, self-caught). Consider a `log-add` for ordering.
- [ ] **Wave A follow-up, now with data.** `timeline` was the right form twice and is the form with the blanking hole. Terminal renderers for `state`/`curve` were not needed this session; `timeline` and the tradeoff tables carried everything.

**Reinforced from the known-open list:**
- [ ] The sycophancy baseline is still unrun, and this session adds an argument for why it can't be gathered from live lessons: **sycophancy went untested** because the learner never pushed back on a correct technical claim. A real lesson doesn't reliably generate the pressure modes.

## Done (this session)

- [x] Wave 1: intake, feedback cycle, currency reframe, profile restructure.
- [x] init-instance.sh + `~/.config/primer/config` + data-repo layout.
- [x] Engineering logs (GOALS, DECISIONS, sessions, these docs) + session skills.
- [x] Class/instance split + migration: `voidnologo/primer-data` (private) created and pushed; personal data removed from core.
- [x] Rename to `primer` (skill name + verbs, install.sh, README, REQUIREMENTS, memory). Live skill reinstalled as `/primer`.
- [x] GitHub repo renamed `knowledge → primer` (`voidnologo/primer`), remote updated, pushed. Local dir moved to `~/personal/learning/primer`.
- [x] Lessons reframed as private-by-default (D-0013); `examples/` removed from the public core.

## Ideas / proposals (not committed)

- **Lesson → public-artifact derivation skill** (D-0013): take a personal lesson from the private instance and derive a sanitized, shareable artifact on demand. The only sanctioned path to a public lesson.
- Tune `N` (minor-recalibrate cadence) after real lesson data; currently 5. *(Superseded by Proposal 0001 T4 — make recalibration evidence-triggered rather than a fixed count.)*
- Possible `/primer config` verb to set N and register without a full recalibrate.
- Consider a "transfer-confirm" micro-probe in the first lesson that touches an assumed-held skill (closes the Phase-3 transfer assumption).
