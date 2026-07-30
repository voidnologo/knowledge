# Primer — Decision Log

Append-only record of engineering decisions: the **why**, the tradeoffs, and what was rejected. Git history is the *what*; this is the *why*. New decisions go at the top. Each entry is dated and numbered.

Format: decision, context, alternatives considered, tradeoff accepted.

---

## D-0025 · 2026-07-30 · The source-discovery pass gets a ledger; promotion writes to the instance, never to the public core

**Decision:** The mandatory per-lesson discovery pass becomes a **procedure with a memory**. (a) `primer/research-protocol.md` holds the durable procedure — query templates per source class, a vetting decision procedure with explicit verdicts, a coverage floor, and how verdicts get recorded. (b) `tools/primer_sources.py` owns the deterministic half against `$DATA_DIR/learner/source-ledger.md`: what has been vetted, with what verdict, when it was last checked, and what still needs grounding. (c) The sweep runs in a **subagent**, off the lesson thread. (d) Each domain carries a **cached sweep** with a freshness horizon; inside it a lesson reads the ledger and does a narrow top-up, past it the full sweep re-runs. (e) **Promotion writes to the learner's ledger, not to `primer/source-canon.md`.**

**Context:** currency is the top non-negotiable in `GOALS.md`, and it was the only one with **no code behind it** — the pass was specified entirely as prose. Four concrete costs followed. It was reconstructed from scratch every session, so a source vetted in one lesson was re-swept and re-judged in the next. The freshness rule ("more than ~3 months stale") was hand-computed arithmetic, which D-0018 already ruled should be code because models miscount and mis-date. The sweep ran inside the lesson thread, spending on search results the context that should have been teaching. And `[from-training, verify]` tags were written into artifacts and never revisited, so the verify never happened. The net effect: the one non-negotiable the project cares most about was the one most likely to degrade quietly under time pressure.

**Part (e) resolves a latent conflict, not just an ergonomic one.** `source-canon.md` said promoted sources "get added to the floor at recap" — and that floor lives in the **public core**, a repo the learner *pulls updates into*. So the documented behaviour had every lesson writing per-learner findings into a shared repo: it leaks what the learner studies (against the privacy non-negotiable and D-0001/D-0013) and conflicts on every `git pull`. The ledger in the private instance is now the learner's own accreted floor, `sources-floor --domain <d>` is what a future lesson reads as its starting set, and the core canon stays a shared *starter pack* that a lesson never writes to. Contributing a source upstream is a deliberate PR — the same shape as the D-0013 lesson-derivation step.

**Alternatives:** keep the pass as prose and accept the cost (rejected — the cost falls hardest on the non-negotiable, and "run a full sweep every lesson forever" is the kind of rule that gets skipped rather than followed); cache sweeps without a horizon (rejected — that *is* freezing knowledge, which is what D-0006 exists to prevent; the horizon plus a mandatory narrow top-up keeps the guardrail); a SQLite ledger (rejected for the same reason as D-0020 — binary in git breaks cross-machine sync); write promotions into the core and let the learner resolve conflicts (rejected — see above).

**Tradeoff:** one more state file in the instance and the discipline of writing verdicts down, including for rejects, in exchange for a pass that gets **cheaper the more it runs** and two backlogs (`sources-stale`, `sources-unverified`) that are queryable lists instead of remembered rituals. Ledger values come from web pages and model output, so they are treated as untrusted: the file is pipe-delimited and a `|`, newline, non-`http(s)`/`file` scheme, or over-long field is rejected with an actionable message — hostile-input tests shipped in the first commit this time, which is the direct lesson from the Wave A review (D-0023). Implements Proposal 0003 Wave E (R1–R4).

## D-0024 · 2026-07-30 · Visuals are first-class; figures are specs rendered by a template library

**Decision:** Lessons carry figures. A figure is authored **once**, as a `<!--primer-figure ... -->` spec block in the lesson artifact, and rendered by a stdlib template library (`tools/primer_view.py`) into three channels: ASCII for the live terminal, Mermaid for the artifact, SVG for the view page. Six forms ship — `sequence` `state` `quorum` `layers` `curve` `timeline` — each with a blanked variant. The model writes labels and values; the templates own geometry, theming, and accessibility. **Supersedes `visuals.md`'s "No images in v1" / "Generating images: out of scope."** Generated *raster* images remain out of scope, now for a stated reason rather than by omission.

**Context:** the exclusion was a capability assumption from conception, and the evidence contradicts it — text paired with diagrams is one of the largest and most consistent effects in the multimedia-learning corpus, holding for factual, inferential, *and* transfer outcomes (Mayer meta-analysis, *Educational Research Review* 2025). Separately, the maintainer asked for durable diagramming ability and a clickable page for what the CLI can't show. Templates rather than model-authored SVG because authoring geometry mid-lesson is slow at the worst moment, spends context that should be teaching, and is where malformed output comes from — the maintainer's directive was explicit that durable skills and scripts beat figuring it out each time.

**Two evidence-driven constraints inside the design.** (a) **Blanked by default.** The measured effect concentrates on *learner-generated* representations (drawing-to-learn meta-analysis, g ≈ 0.69, and the medium doesn't matter), so a complete figure is a figure received. The element carrying the invariant renders as `?`; the learner predicts; then the reveal. This makes the visual layer an expression of the productive-struggle non-negotiable rather than a second, competing pedagogy. (b) **No decorative figures.** Removing seductive detail is itself among the largest effects measured, so a figure that carries no invariant is a cost. Every spec must state the one invariant it makes visible, and the validator requires a caption.

**Alternatives:** Mermaid-only, no page (rejected — Mermaid doesn't render in a terminal, can't gate a reveal, and the maintainer's ask was specifically for what text can't convey); model-authored SVG per lesson with prose guidance (rejected — the improvisation cost is the thing being removed, and LLM diagram output needs semantic rather than string-level checking, per MermaidSeqBench); generated raster images (rejected — a spec is inspectable, diffable, correctable, and regenerable; a PNG is none of those).

**Tradeoff:** primer owns a template library and a spec format (~1,100 lines with 56 tests) instead of leaving figures to per-lesson improvisation, in exchange for consistency, speed at the moment it matters, and a class of malformed output that can't reach the learner. The template list is a starter set that accretes like the source canon — a figure shape that proves load-bearing gets promoted in. Implements Proposal 0003 V1/V6.

## D-0023 · 2026-07-30 · The visual channel is a local self-contained page, and validation is a gate

**Decision:** The rich figure channel is `$DATA_DIR/lessons/<domain>/<slug>.view.html` — a **single local file with zero external requests** (inline CSS/JS/SVG, `data:` URIs only), opened by the learner clicking a `file://` link the Primer prints. It is a **derived build product**: regenerated from the artifact, gitignored in the instance. And it is **validated before it is written** — `render` runs six checks and exits non-zero with the specific problem, so a page that failed validation never exists at the path the learner is told to click.

**Context:** three of primer's own non-negotiables decide the shape. *Self-contained* — no external tool or service may be a requirement, so no CDN, no server, and it works offline. *Privacy* — lesson content is personal (D-0013); publishing to an external host by default would push calibrated personal material off the machine, and would also leak a page-view. *Markdown is source of truth* (D-0020) — so the page must be regenerable and must not become a second place where figure content lives. The validation gate exists because the failure modes are known and specific: AI-generated interactives measurably fail at state management (arXiv:2606.31012), and an ungated reveal silently hands over the answer the learner was supposed to predict.

**The six checks:** comment integrity (exactly one comment terminator), figure well-formedness (each SVG parses as XML — a malformed figure renders blank otherwise), no external requests, caption coverage, contract satisfaction (every declared input has a listener, every declared output is written), faded-reveal integrity (the answer sits inside that figure's own closed `<details>` and nowhere else, checked structurally per figure). The page carries a manifest so `validate` works standalone; the manifest omits the reveal *text*, so a learner reading source doesn't find the answer in JSON beside its figure.

**Spec strings are untrusted input.** This is the correction an adversarial review forced, and it is the load-bearing part of the decision. A caption is model-authored text that lands in HTML, in SVG, and (via ids) in generated JavaScript, so "escape carefully" is not a design — it is a hope. What shipped instead: ids are constrained to a safe character set at spec load, so every downstream interpolation is safe by construction; numeric fields are coerced rather than trusted, because a string flowing into an HTML attribute can inject arbitrary attributes including event handlers; the manifest comment is serialized so it cannot terminate itself (a caption containing `-->` — Mermaid edge syntax, a plausible thing to write *about* — would otherwise hand the rest of the comment to the HTML parser); the external-reference scan works per tag attribute rather than as a regex over the document, which both catches `srcset`/`poster`/`data`/`http-equiv` and stops false-positiving on inert prose in a lesson about HTML; and a `Content-Security-Policy` meta tag backs all of it at runtime, because a regex over generated markup can be outrun and a browser policy cannot.

**Explorables get a contract, not JavaScript.** Interactivity is opt-in per lesson and justified per lesson — the evidence for it is inconsistent (smaller effects on factual outcomes, larger on transfer; head-to-head simulation-vs-static comparisons often show no difference), so it earns its place only when a parameter's variation *is* the insight. When it does, the spec declares inputs, outputs, and one arithmetic formula per output, and the wiring is **generated**.

The formula compiler **parses a grammar** rather than filtering an alphabet — the second correction from review, and the one that made the difference between a claim and a guarantee. A token-filter accepts sequences that are individually legal and collectively not JavaScript-arithmetic: `1/*2` opens a comment and swallows every statement after it, a lone `(` is a SyntaxError that kills the whole script block, `min(/1/,2)` smuggles in a regex literal. All three passed the filter and all six checks. Emitting from a parse tree makes the output arithmetic-over-declared-inputs by construction. Two contract rules complete it: every declared input must be *read* by some formula (a slider that moves and changes nothing is exactly the failure the contract exists to prevent, and the outputs↔formulas check alone missed it), and duplicate ids are rejected (`getElementById` silently resolves the first, so the second figure's wiring would be dead but validated).

**Alternatives:** publish to a claude.ai Artifact (rejected as a default — violates privacy-by-architecture; reserved for the deliberate D-0013 derivation step, opt-in and sanitized at that point); a local HTTP server (rejected — a service dependency for a core capability); vendoring `mermaid.min.js` for in-page Mermaid (rejected — ~3MB in a public core repo for something inline SVG already covers offline); trusting the model to produce a correct page (rejected — the specific failure modes are measured, and the cost of a gate is one script run).

**One residual limit, stated rather than papered over:** the reveal is in the page's DOM, so a browser's find-in-page expands closed `<details>`. That is inherent to a static local page. The gate is not a defence against a learner who wants the answer — it is a defence against *receiving* it without choosing to, which is the thing the evidence is about.

**Tradeoff:** a generated page can't be hand-tuned (edits are lost on regeneration) and the validator will occasionally reject a figure the model thought was fine, in exchange for a channel that is private by construction, works offline, and cannot spoil its own pedagogy. Implements Proposal 0003 V2/V3/V4/V5.

## D-0022 · 2026-07-30 · Engine files load on demand; only `system-prompt.md` is static

**Decision:** `SKILL.md` no longer `@`-includes all eight `primer/*` files. Only `system-prompt.md` is statically loaded; the rest are an explicit **on-demand load table** routed per verb, and each verb section names the read it requires before the work it governs.

**Context:** every invocation loaded ~10,900 words (~15k tokens) of engine, including `/primer index` and `/primer profile`, which need almost none of it. Current skill-authoring guidance is the opposite — keep the body small, put detail in files one level deep, load on demand. The forcing function was Wave A: adding figure-authoring instructions and (next) a research protocol on top of an already-maximal static baseline spends the budget on instructions rather than on the learner.

**Alternatives:** leave it static and accept the cost (rejected — the baseline only grows as the engine does, and the cost lands hardest on lessons, where context is most valuable); split the engine into a second skill (rejected — the verbs share the learner model and the register; splitting would duplicate both).

**Tradeoff:** the model must actually perform the reads, which is a weaker guarantee than a static include — mitigated by making the table explicit and imperative ("do not proceed without it") and by naming the read inside each verb's own steps. The honest accounting: a *lesson* still loads most of the engine, so the win is (a) non-lesson verbs, and (b) headroom and ordering — the canon and template arrive when they're needed rather than competing with the Elicit step. Implements Proposal 0003 M1.

## D-0021 · 2026-06-16 · In-progress lesson sidecars (`.STATE.md`) are committed, not gitignored

**Decision:** `lessons/**/*.STATE.md` resume sidecars are **committed and git-synced**, reversing the earlier
"local-only, gitignored" treatment. The sidecar is written as a **self-contained handoff checkpoint** —
capturing what the learner answered (Elicit/Probe), where the diagnosis landed, and what's next — and flushed
at any natural stopping point, not used as a scratchpad that leans on the live session's in-context memory.
Updated `primer/lesson-template.md` (the convention), the core repo `.gitignore` (removed the ignore rule),
and confirmed `tools/init-instance.sh` writes instance gitignores without the rule. (`init-instance.sh`
already did; no change needed there.)

**Context:** the maintainer's portability goal — pause a lesson on machine 1, resume it on machine 2 —
requires the sidecar to sync, and gitignoring it directly blocked that. The earlier "regenerated per session"
rationale only holds for same-machine scratch. Gitignoring `.STATE.md` also contradicted the project's
own load-bearing principle that the private instance is fully git-syncable across machines (D-0001, and the
explicit reason markdown-not-SQLite was chosen in D-0018/D-0020). The one genuine limit is narrow and
inherent: the live Claude session transcript (conversational turns since the last flush) does **not** cross
machines, so cross-machine resume picks up from the last checkpoint written into the sidecar, not mid-dialogue.
The fix for that gap is to flush often, not to gitignore.

**Alternatives:** keep gitignored, accept no cross-machine resume (rejected — defeats the stated goal and
contradicts D-0001 sync); sync the full session transcript too (rejected — machine-local and Claude-session-
bound, not primer's to move; the checkpoint-in-sidecar discipline is the portable subset). Concurrent edits to
the same sidecar from two machines don't arise because the engine enforces max one in-progress session
(SKILL.md constraint); an abandoned sidecar is a cleanup nuisance, not a correctness issue.

**Tradeoff:** the sidecar must be authored as a durable handoff (slightly more discipline per flush, and a
stale sidecar can linger after an abandoned lesson) in exchange for cross-machine resume and consistency with
the all-markdown-git-syncs design. Refines the resume-state design (Proposal 0001's `.STATE.md` path
reconciliation); the path/format from that work stands.

## D-0020 · 2026-06-16 · State layer: markdown is source of truth; Python+SM-2; no committed DB

**Decision:** Resolves Proposal 0002. (a) **Markdown stays the source of truth**; a stdlib Python module
(`tools/primer_state.py`) does the deterministic bookkeeping by reading/rewriting it. (b) **No SQLite** — not
now, and never as a committed source of truth. (c) Scheduler is **SM-2** (lightweight, transparent). (d)
Scripts are **Python 3.11+, stdlib-only** (portable mac/linux/windows, nothing to install). Refines D-0018's
"committed SQLite DB" — the DB idea is dropped.

**Context:** the maintainer delegated the source-of-truth (A/B/C) and scheduler choices, asking for the
best-on-merits option (familiar preferred only if equal-or-better). On merits: the private instance **syncs
across machines via git**, and a SQLite file is binary — git can't merge it, so concurrent/forgotten-pull
edits produce unmergeable conflicts and lost writes. Markdown merges line-by-line and stays human-readable. At
one-learner scale (hundreds of prompts) a script parsing markdown is instant, so SQLite buys nothing here. SM-2
over FSRS because FSRS needs trained parameters and review volume we won't have, and the *habit* (Goal 5)
matters more than optimal intervals.

**Alternatives:** A (DB-of-record + markdown snapshots) and committed-DB hybrids — rejected (binary-in-git
breaks D-0001 sync, no scale benefit); FSRS — rejected for now (needs data; upgradeable later); a gitignored
rebuildable SQLite *cache* — deferred (add only if query needs ever outgrow markdown; never source of truth).

**Tradeoff:** primer owns a small parsing/scheduling module (with tests) instead of leaning on a DB engine, in
exchange for clean git sync, hand-editability (the Open-Learner-Model property), and zero install. Built this
session: `tools/primer_state.py` (`review-due/grade/add/history`, `markers-decay`, `recalibrate-check`) +
`tools/test_primer_state.py` (19 tests, passing); wired into `SKILL.md` and `feedback-protocol.md`.

## D-0019 · 2026-06-15 · Cultivating learning habits & meta-learning is a project goal (GOALS Goal 5)

**Decision:** primer's job is not only to teach content but to **gradually make the learner better at learning** — building spaced-retrieval, active-recall, and metacognitive habits over time. Added as Goal 5 in `GOALS.md`. The spaced-review capability is justified by *habit-formation* (the system grows the habit), not by assuming the learner already reviews.

**Context:** the maintainer stated this directly, and that they personally won't do periodic refreshers today (they skim prior lesson logs). Those reconcile: the system's role is to cultivate the habit the learner lacks, riding the flow they *do* use (the Elicit-step recall in every lesson) and gently expanding — not requiring review, not abandoning it. Matuschak's "Why books don't work": the medium must own the metacognitive scaffolding because the learner can't be assumed to.

**Alternatives:** treat review as the learner's responsibility (rejected — abdicates the scaffolding); force/nag review (rejected — off-register, and the desirable-difficulties illusion means learners undervalue it, so pressure backfires).

**Tradeoff:** more product surface (habit nudges, explaining the *why* of retrieval-over-rereading), in exchange for pursuing the actual goal — a learner who learns better over time, not just well-answered single sessions.

## D-0018 · 2026-06-15 · primer is self-contained; deterministic bookkeeping is code, not in-context LLM work

**Decision:** primer delivers its full core loop (lessons, review, learner model) with nothing but the skill and the user's own data repo — **no external tool or service is ever a requirement** (now a `GOALS.md` non-negotiable). Scripts, code, and a **local SQLite DB committed in the private data repo** are explicitly in-scope as implementation: deterministic bookkeeping (confidence decay, recalibration triggers, review scheduling, miss-counting) should run as code, not as in-context LLM work.

**Context:** maintainer directives — "the primer should be self-contained"; "no problems with scripts/code, even a local sqlite db… not everything has to be pure ai usage (that will become very token and context expensive)." The Wave B feedback loop introduced real arithmetic (decay, triggers, scheduling); doing it by having the model read/rewrite markdown each session is costly and unreliable (LLMs miscount and mis-date).

**Alternatives:** external SRS as the scheduler (rejected — external dependency); all-LLM markdown state (rejected — token/context cost + arithmetic unreliability).

**Tradeoff:** primer owns more code and a state-store design decision, in exchange for self-containment, lower per-session cost, and reliable bookkeeping. Supersedes REQUIREMENTS P7/§11's "an external SRS does the scheduling." The concrete state-layer architecture (what moves to SQLite, source of truth, how inspectability is preserved) is **Proposal 0002** — pending the maintainer's scope decision.

## D-0017 · 2026-06-15 · Minor recalibrate is evidence-triggered with a cap (supersedes D-0004's fixed N=5)

**Decision:** The minor recalibrate fires when **either** M+ calibration-log misses have accumulated since the last one (default M=4) **or** N lessons have passed (default N=8, the cap). **Supersedes the "auto every 5 lessons" cadence in D-0004** (the two-tier minor/deep structure from D-0004 stands).

**Context:** D-0004 admitted N=5 was an untuned guess. A fixed count fires on a schedule blind to whether the model is actually miscalibrated — too late when misses are piling up, wasteful when nothing's wrong. The importance-threshold idea (Generative Agents) triggers reflection on accumulated evidence instead.

**Alternatives:** keep fixed N and just tune it after real data (rejected — tuning a count doesn't fix the blindness to evidence); pure threshold with no cap (rejected — a quiet stretch would never get hygiene, and stale markers wouldn't decay). The cap preserves periodic decay/compaction.

**Tradeoff:** two thresholds to tune instead of one, in exchange for recalibration that responds to how miscalibrated the model actually is. Implements Proposal 0001 T4.

## D-0016 · 2026-06-15 · Design target is ~0.4–0.7σ on transfer-valid assessments; 2σ is folklore

**Decision:** State the system's evidence-grounded effect-size target as **~0.4–0.7σ on transfer-valid (not self-authored) assessments**, and stop citing Bloom's "2-sigma" and "generative-AI tutors at 0.73–1.3σ" as design grounding.

**Context:** `REQUIREMENTS.md §2` grounded the design in figures that don't survive verification — ironic in a project whose top non-negotiable is currency. 2σ traces to unpublished dissertations and never replicated (pooled tutoring ~0.37σ, Nickow 2020; human tutoring ~0.79σ, VanLehn 2011); ITS medians are ~0.42–0.66σ (Ma 2014; Kulik & Fletcher 2016), inflated by local tests; the headline gen-AI RCT is 0.63σ honest (Kestin 2025), the higher figures quantile-derived.

**Alternatives:** keep the aspirational numbers (rejected — they fail the project's own source-grounding rule); drop effect sizes entirely (rejected — a target is useful, and the honest range still motivates the design).

**Tradeoff:** a less impressive headline, in exchange for a defensible bar. Implication captured in the feedback loop: self-authored retrieval prompts inflate, so cold-review scores are a calibration signal, not a mastery/effect-size claim (see D-0015). Verified citations: `docs/engineering/research/2026-06-15-ai-tutoring-and-learning-science.md`.

## D-0015 · 2026-06-15 · The feedback loop gets an external anchor + forgetting-aware confidence decay

**Decision:** Depth-marker confidence moves **both ways** and **decays with time**. Cold retrieval in `/primer review` is the external anchor: a miss lowers confidence and logs a calibration entry; a clean answer to an old prompt raises it. Untouched `[high]` markers drift toward `[med]`/reprobe at minor-recalibrate. Review scores are recorded as a calibration signal, explicitly *not* a mastery metric.

**Context:** The loop updated the model only from its own prior assessments, and confidence only ratcheted up — a closed self-assessment loop that drifts optimistic imperceptibly (Boucle "Optimism Feedback Loop"), compounding the BKT monotonicity gap (no forgetting). This worked *against* the goal that the profile gets more true with use.

**Alternatives:** a formal forgetting model (FSRS/Half-Life Regression) per marker (rejected for now — heavier than warranted before real lesson data; revisit under Proposal 0001 T3); leave the loop self-referential (rejected — the drift is the core risk a self-training system must defend against).

**Tradeoff:** the anchor is coarse and the prompts are self-authored, so review scores can't be read as effect sizes — accepted, because "the estimate survived delayed recall" is still the strongest non-self-generated signal available without external assessments. Implements Proposal 0001 C2 + T1 + E1.

## D-0014 · 2026-06-15 · The public engine carries no hardcoded learner

**Decision:** The engine (`primer/*`) is learner-agnostic. `system-prompt.md` reads the learner from `$DATA_DIR/learner/profile.md` rather than asserting a fixed bio; senior-peer/meetup is the *default* register, overridable by the profile; the source canon is framed as a domain *starter pack*, not a universal canon; the lesson-template domain list is per-instance, not a fixed enum.

**Context:** The public core hardcoded the maintainer's bio ("15+ years … technical lead …"), a backend-only canon, and a five-value domain enum — while the README promised "any learner and any goal." This put personal data in the public repo (violating the sharable-without-leaking goal) and mis-onboarded a stranger. It is also a pedagogical miscalibration: an engine that assumes an expert under-scaffolds novice adopters, and over/under-scaffolding is a measured harm (expertise reversal, asymmetric — Tetzlaff 2025).

**Alternatives:** physically split the backend canon into the maintainer's instance and ship a thin starter, or ship multiple domain packs (deferred — Proposal 0001 ⚑ decision; this change does the *framing* now and leaves the content move for later); keep the bio and document it as "the reference learner" (rejected — still personal data in the public core).

**Tradeoff:** the senior-peer voice is now explicitly a default rather than the identity, so the engine reads slightly less opinionated up front — accepted, since the non-negotiable register traits (no sycophancy, productive struggle, currency, confidence-honesty) are preserved as universal. Implements Proposal 0001 C1 (and fixed a stale `profile.md`→`topic-index.md` depth-marker path in `anti-patterns.md`).

## D-0013 · 2026-06-15 · Lessons are private/personal, not shareable-by-default

**Decision:** Lesson artifacts are personal — calibrated to the learner — and live only in the private instance, alongside the profile. The public core ships no personal lessons. Publishing is a deliberate, separate step. **Supersedes the lesson-sharing aspect of D-0001** (which framed "only lessons are sanitized," implying lessons were the shareable surface).

**Context:** The point of the project is deep personalization; a lesson is shaped by the learner's profile, gaps, and scenarios, so it's as sensitive as the profile. Calling lessons "shareable" and sanitizing them by default both undercut that and add friction.

**Alternatives:** lessons sanitized-and-public-by-default (rejected — caps personalization, leaks calibration signal); a public/private split per lesson (rejected — premature).

**Tradeoff:** no public lesson corpus for now. A future **derivation skill** will turn a chosen personal lesson into a sanitized, shareable artifact on demand — sanitization happens at that step, not on every lesson. Resolved: `examples/` removed from the public core (no provisional public lessons); samples will come from the derivation skill.

## D-0012 · 2026-06-15 · Rename to `primer`; skill name from symlink; `${CLAUDE_SKILL_DIR}` for engine includes

**Decision:** Skill renamed `learn-me-up` → `primer`. The command name is set by the installed symlink name (`~/.claude/skills/primer`), not frontmatter or the repo dir name. Engine `@`-includes switched from absolute `$HOME/...` paths to `@${CLAUDE_SKILL_DIR}/primer/...`.

**Context:** The Wave-2 rename risked breaking the live skill (frontmatter/symlink/path mismatch) and the local-dir move risked breaking the session working dir.

**Findings (via claude-code-guide):** command name derives from the skill dir/symlink name; `${CLAUDE_SKILL_DIR}` resolves to the skill's install location at runtime.

**Tradeoff:** the physical repo dir name and the local-dir move become cosmetic — nothing depends on them. Engine includes are now location-independent, so the GitHub repo rename and local-dir move carry zero functional impact.

## D-0011 · 2026-06-15 · Engineering session/decision logs in the public core

**Decision:** Track development "why" in `docs/engineering/` — `GOALS.md` (north star), `DECISIONS.md` (this file), `sessions/` (per-session logs) — plus a `/session-start` / `/session-end` mechanism.

**Context:** Git records what changed; the reasoning and rejected alternatives were living only in chat. Need durable design memory to maintain focus and prevent drift across sessions.

**Alternatives:** keep it in commit messages only (rejected — no room for tradeoffs/alternatives, not browsable as a design narrative); a single CHANGELOG (rejected — conflates what/why).

**Tradeoff:** a small per-session documentation cost, paid back as anti-drift and onboarding for future contributors. Logs live in the public core (they document the engine and carry no personal data).

**Format basis:** adapted the maintainer's existing session-skill convention from the public `~/personal/card-game` project (session_start/end + numbered notes + pending-tasks + continuation), with two primer changes: a `GOALS.md` north-star read for anti-drift, and a dedicated ADR-style `DECISIONS.md`. Implemented as **modern skills** (`.claude/skills/<name>/SKILL.md`), not legacy `.claude/commands/`. The proprietary work repos were not read.

## D-0010 · 2026-06-15 · Project name is "primer", not "the-primer"

**Decision:** Name the project/repo/skill `primer`.

**Context:** "the-primer" reads truer to the source material but the leading "the" gets dropped or questioned in practice.

**Tradeoff:** slight loss of fidelity to *The Diamond Age* framing for everyday memorability. Internal engine directory `primer/` and the skill name share the word — acceptable (different namespaces).

## D-0009 · 2026-06-15 · Data-repo layout mirrors the core (`learner/` + `lessons/`)

**Decision:** The private data repo root contains `learner/` (state) and `lessons/` (artifacts); `$DATA_DIR` points at the root.

**Context:** Initial scaffold flattened state to the data-dir root, which contradicted the `learner/…` paths used throughout the protocol docs.

**Alternatives:** flat root with bare filenames (rejected — would have required rewriting ~13 references across the engine docs and lost the state/artifact grouping).

**Tradeoff:** one extra path segment, in exchange for a clean wholesale migration (move existing `learner/` + `lessons/` as-is) and zero protocol-doc churn. Dev-fallback ($DATA_DIR = core repo root) then works unchanged.

## D-0008 · 2026-06-15 · init scaffolds locally and prints commands; never calls GitHub

**Decision:** `tools/init-instance.sh` scaffolds the data dir, git-inits it, writes the per-machine config, and **prints** the `gh`/`git` commands for the user to run.

**Context:** The public core can't assume how others host or auth their private data.

**Alternatives:** auto-create via `gh` (rejected for the core — assumes gh auth and a hosting choice); point-at-existing only (rejected — more manual for the common case).

**Tradeoff:** one manual push step, in exchange for portability across unknown user setups. (For the maintainer's *own* instance migration, using `gh` directly is fine — that's not the core's job.)

## D-0007 · 2026-06-15 · Per-machine data pointer in `~/.config/primer/config` (XDG)

**Decision:** The skill resolves `$DATA_DIR` from `~/.config/primer/config`.

**Context:** The same private data repo is cloned to different paths on personal vs. work machines.

**Alternatives:** gitignored pointer file in the core (rejected — lost on re-clone); env var (rejected — invisible, easy to forget on a new machine).

**Tradeoff:** a config file outside both repos to manage, in exchange for surviving re-clones and being naturally per-machine.

## D-0006 · 2026-06-15 · Currency: canon is a vetted floor, not a ceiling

**Decision:** The allowlist is a pre-vetted *starting set*; every lesson runs a mandatory source-discovery pass beyond it; the stale-list + stale-criteria are the real currency guardrail; load-bearing finds get promoted back into the floor.

**Context:** A closed allowlist would freeze knowledge at list-authoring time — the opposite of the currency goal.

**Alternatives:** strict allowlist (rejected — restricts current info); no canon at all (rejected — discards vetting already done, every lesson re-explores from scratch).

**Tradeoff:** per-lesson search cost, in exchange for non-negotiable currency plus a floor that ages forward through use.

## D-0005 · 2026-06-15 · Micro-feedback is silent (inferred), never asked

**Decision:** The Primer infers engagement/difficulty/style-fit from the conversation and records it; it does not ask end-of-lesson rating questions.

**Context:** Explicit rating prompts read as the fluff the learner profile explicitly rejects.

**Tradeoff:** inference is noisier than a direct answer, but avoids friction and stays in-register. Patterns get confirmed across sessions via the calibration log, not a single self-report.

## D-0004 · 2026-06-15 · Two-tier recalibration (minor auto every 5, deep on demand)

**Decision:** A lightweight minor recalibrate auto-runs every 5 lessons (compacts volatile state, shows a diff); a deep recalibrate the user invokes rewrites stable traits and goals.

**Context:** An append-only loop accretes volatile state and never corrects the model; but stable traits shouldn't be rewritten on one session.

**Alternatives:** only-manual (rejected — drift goes uncaught); only-automatic deep (rejected — too heavy to run often, risks over-fitting traits).

**Tradeoff:** N=5 is a guess to tune. Two mechanisms instead of one, in exchange for cheap continuous hygiene + deliberate, evidence-based trait changes.

## D-0003 · 2026-06-15 · Feedback loop runs at three timescales; stable/volatile split

**Decision:** Capture silently within a lesson, capture signals at lesson end (calibration log + confidence/evidence on depth markers), recalibrate periodically. Stable traits → `profile.md`; volatile state (depth markers, ZPD edges, calibration misses) → `learner/`.

**Context:** The original loop only updated at session end and mixed stable traits with volatile depth markers in one file, so the file churned and traits were never deliberately revisited.

**Tradeoff:** more files and more moving parts, in exchange for a profile that gets more true with use and is honest about confidence.

## D-0002 · 2026-06-15 · Intake = self-report + one live diagnostic probe per domain

**Decision:** The cold-start interview grounds each self-rated domain with a single live diagnostic probe (causal/counterfactual/critique), and records the gap at low confidence.

**Context:** Self-rated skill level is unreliable in both directions; a blank or self-report-only profile mis-calibrates the first lessons.

**Alternatives:** self-report only (rejected — unreliable); placement-exam depth (rejected — too much onboarding friction).

**Tradeoff:** ~30–45 min onboarding and one probe's worth of uncertainty per domain, in exchange for a first profile grounded in demonstrated behavior. Real depth is refined by later lessons.

## D-0001 · 2026-06-15 · Privacy via class/instance repo split, not a public-safe profile

**Decision:** Separate a public core (engine) from a private instance data repo (profile + lessons). The profile is private and may be rich; only lessons are sanitized.

**Context:** The original model made the profile "public-safe," which capped its richness — the genuinely useful tailoring signal (real stack, stakes, anxieties) couldn't be stored. The maintainer also needs profile + lessons synced across two machines.

**Alternatives:** two files (public + gitignored private) in one repo (rejected — superseded; doesn't give cross-machine sync); keep fully public-safe (rejected — caps quality); all data gitignored local-only (rejected — no sync).

**Tradeoff:** managing two repos and a private remote (trust boundary: private GitHub repo, not local-only), in exchange for a rich profile, clean sharing, and git-based multi-machine sync.
