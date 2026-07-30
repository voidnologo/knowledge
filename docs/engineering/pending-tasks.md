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
- [ ] **Run the sycophancy eval** against a live primer session and record the baseline — the trap set and scorer exist; no results yet.
- [ ] **Self-updater follow-ups** — bump `VERSION` per release; consider a tarball path if non-git installs appear.
- [ ] **M2** revisit D-0020c → FSRS-6 with pretrained defaults; **M3** ground prompt generation in graded exemplars (+ fix bad-prompt-vs-forgotten conflation).
- [ ] **Wave D** (defer until real lesson data) — S1 simulated-learner regression suite; S2 opt-in SessionStart hook; S3 teach-it-back mode.
- [ ] **X1** — hedge the "every existing learning skill is session-scoped" claim in the README/research (several Claude Code learning skills now ship persistence; three vendors ship Socratic study modes).
- [ ] **X2** — re-verify snippet-only figures before citing (Mayer / drawing / PhET meta-analyses, LearnLM RCT); June artifacts' freshness horizon is ~2026-09.

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
