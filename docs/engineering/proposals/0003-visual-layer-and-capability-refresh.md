# Proposal 0003 — Visual layer + capability refresh

> **Status:** proposed, awaiting scope decision. Written 2026-07-30 (Session 4).
>
> **Evidence base:** `docs/engineering/research/2026-07-30-capability-and-evidence-refresh.md` (this session's sweep), on top of the two 2026-06-15 artifacts. Section references below (§1–§12) point into that artifact.
>
> **Motivation.** The design was conceived several model generations ago. Its capability assumptions — text-only output, a single agent doing both teaching and grading, no engine test suite, SM-2, "no images in v1" — predate both the harness features and the published evidence that now exist. Plus a direct maintainer request: build in the ability to author flowcharts and diagrams, and let the learner click a link in a lesson to open a local page carrying the visual material the CLI can't.
>
> **Item IDs.** `V` = presentation layer (the maintainer's request), `R` = research abilities, `H` = honesty hardening (the engine grading itself), `M` = mechanics, `S` = optional surface. Each item states the goal it serves and the non-negotiable it could threaten, per the `GOALS.md` anti-drift checklist.
>
> **Organizing principle (maintainer directive, this session):** *durable internal skills and scripts beat figuring it out each time.* Anything the engine does every lesson — authoring a figure, running the source-discovery pass, vetting a source, checking freshness — should be a reusable asset (a template, a script, a decision procedure), not improvisation reconstructed per session. Improvisation costs latency mid-lesson, burns context that should be teaching the learner, and produces inconsistent output. Waves A and E are the two places this bites hardest, and they are the stated next tasks.

---

## Wave A — the visual layer (V1–V5)

### The evidence this is built on

Four findings constrain the design (§11), and they pull in different directions:

1. **Text + diagrams is one of the largest and most consistent effects in the multimedia corpus** — across factual, inferential, *and* transfer outcomes. Reliable and cheap.
2. **Interactivity is inconsistent** — smaller on factual, larger on inferential/transfer, and head-to-head simulation-vs-static-graphic comparisons show no significant difference. The PhET d ≈ 0.83 is confounded with activity design.
3. **Removing seductive detail is among the largest effects measured.** A visual that doesn't carry an invariant is worse than no visual.
4. **Learner-generated representations carry g ≈ 0.69**, and technology-based drawing shows no advantage over paper — so the active ingredient is *generation*, not the canvas.

And one hard constraint: **AI-generated interactives break in a measurable, specific way.** The FSM-based interactivity evaluation (arXiv:2606.31012) finds most AI-generated explorables fail state management and respond incorrectly to manipulation. Mermaid correctness can't be string-matched — MermaidSeqBench normalizes nodes/edges and scores structural F1 instead.

So: **diagrams by default, interactivity only where a parameter is worth varying, nothing decorative, the learner predicts before the reveal, and everything is validated before it reaches the learner.**

### V1 — Rewrite `primer/visuals.md`; add `primer/diagramming.md`

`visuals.md` currently says "No images in v1" and "Generating images. Out of scope for v1." Both are superseded. It also has no guidance on *choosing* or *composing* a diagram — it lists which Mermaid types exist. The maintainer's ask ("skills for how to make flow charts, diagrams, and more visual things") is that missing half.

Split along the progressive-disclosure line: `visuals.md` stays the short conventions file loaded in-context; `diagramming.md` becomes the on-demand reference read only when a lesson is actually building a figure.

`diagramming.md` carries:

- **A selection table** — what each form is *for*, and when the answer is "no diagram." Sequence for temporal ordering and interleaving; state for lifecycle and legal transitions; flowchart for decision structure; ER for relational cardinality; table for rows-and-columns tradeoffs (already a rule); timeline/swimlane for concurrency; and a "prose is better" row, because the seductive-detail finding means a marginal figure is a net negative.
- **One invariant per figure.** A figure earns its place by making exactly one claim visible. If a figure needs two captions, it's two figures.
- **The faded-diagram pattern** — the highest-value item in this wave. Emit the figure with the causal step blanked (`?` on the edge that carries the invariant, or a labeled gap), ask the learner to predict what fills it, *then* reveal. This is the g ≈ 0.69 generation effect in the form primer can actually deliver, and it is the productive-struggle non-negotiable expressed visually rather than a second, competing pedagogy.
- **Cognitive-load rules** carried over from the fading evidence already in the repo: label in place rather than in a legend (split-attention), no color-only encoding, ≤ ~7 nodes before splitting, fade figure density for high-depth markers exactly as worked examples fade.
- **Composition recipes** — concrete before/after pairs for the three or four figure types a technical lesson actually reaches for, since the examples pattern conveys style better than description.

### V2 — The local visual page: `<slug>.view.html`

**What the learner sees.** At the point in the lesson where a figure would help, the Primer prints a `file://` link inline in the terminal and says what's on the other side of it. The learner clicks it; their browser opens a local page. No server, no network, no account.

**Where it lives.** `$DATA_DIR/lessons/<domain-slug>/<YYYY-MM-DD>-<slug>.view.html` — beside the lesson artifact, inside the private instance.

**Why a local file rather than a published artifact.** Two non-negotiables decide this. Privacy: lesson content is personal (D-0013) and publishing is a deliberate, separate derivation step — a published page would push calibrated personal material to an external host by default. Self-contained: no external tool or service is ever a *requirement*, and a local file works offline. Publishing a *sanitized* view page can be an opt-in verb later, riding the same derivation step D-0013 already reserves for lessons; it is not the default and not in this wave.

**Hard file constraints:**

- **Single file, zero external requests.** Inline CSS, inline JS, inline SVG, `data:` URIs only. No CDN, no fonts, no remote images. This is what makes it work on a plane and what keeps it from leaking a page-view to a third party.
- **Markdown stays the source of truth.** The page is *generated from* the lesson artifact and is regenerable, never a second source of truth. This preserves D-0020 and keeps the instance hand-editable and git-mergeable. Because it's a derived build product, `*.view.html` is gitignored in the instance (the `.md` artifact syncs; the page regenerates on demand) — unlike `.STATE.md`, which is a checkpoint and must sync (D-0021).
- **Diagrams as hand-authored inline SVG by default.** Zero dependencies, renders anywhere, no JS, and theme-able. Mermaid stays in the `.md` artifact where GitHub renders it natively; the page does *not* pull `mermaid.min.js` from a CDN, and vendoring ~3MB into a public core repo isn't worth it for a figure that SVG already handles.
- **Theme-aware and accessible** — `prefers-color-scheme`, no color-only encoding, real `<figcaption>` per figure.

**Page structure:** figure gallery at readable size (each with its caption and its one invariant); the faded-reveal control (the blanked figure, a commit affordance, then the answer — so the page enforces predict-before-reveal rather than just displaying both); the tradeoff table; and any explorable widget from V3.

### V3 — Explorables, gated and contracted

Interactivity is opt-in per lesson and justified per lesson: it appears only when the concept has a parameter whose variation *is* the insight (queue utilization vs latency, quorum size vs availability under partition, cache hit rate vs tail latency, backoff parameters vs collapse). Anything else gets a static figure.

Every widget declares an **interaction contract** in the page source:

```html
<!-- contract: input#lambda 0.1..0.95 -> #utilization, #latency-p99 -->
```

The contract does three jobs. The validator (V4) checks every named input has a listener and every named output is actually written — which is a direct, cheap answer to the measured state-management failure mode. The Primer states the contract to the learner in words ("drag λ; watch p99 — predict the shape before you drag it"). And the learner gets told what to predict, which keeps the widget inside the productive-struggle loop instead of becoming a toy.

Vanilla JS only, no framework, no build step.

### V4 — `tools/primer_view.py` — generate and validate (stdlib only)

Deterministic work runs as code, not in-context (D-0018). The script owns generation-from-artifact and, more importantly, the validation gate — the feedback-loop pattern that the skills best-practices guidance recommends for quality-critical output:

- **Well-formedness** — parse the SVG/HTML fragments with `xml.etree`; a malformed figure fails loudly instead of rendering blank.
- **No external requests** — scan for `http://`, `https://`, `//`, `src=`, `@import`; any hit fails. This is the enforcement of the offline/no-leak constraint, rather than a promise the model keeps by intention.
- **Caption coverage** — every figure has a `<figcaption>`. Already a stated rule with no enforcement.
- **Contract satisfaction** — every declared input has a handler; every declared output is assigned.
- **Faded-reveal integrity** — the answer is not visible before the commit affordance is used (a `<details>`/hidden-until-clicked check), so the page can't accidentally hand over what the learner was supposed to predict.

Non-zero exit with a specific message per failure; the Primer fixes and re-runs before showing the learner anything. Commands: `render <artifact.md>`, `validate <view.html>`.

### V5 — `/primer view [lesson]` and the protocol hook

**New verb** — `/primer view [lesson-slug]` regenerates and opens the page for any lesson, defaulting to the most recent. This is what lets *existing* lessons gain visuals retroactively instead of the feature only applying going forward.

**Protocol placement** (`lesson-protocol.md` §4 Deepen): the figure arrives *before* the pattern is named, blanked at the causal step; the learner predicts; then the reveal. At Recap the figures become part of the artifact and the page is written. This deliberately reuses the existing worked → faded → free progression rather than adding a parallel visual track, and it inherits the existing fade rule — high-depth markers get fewer, denser figures.

**Threatens:** nothing structural. Self-contained holds (local file, stdlib, no service). Privacy holds (private instance, gitignored derived file, no publishing). Productive struggle is *strengthened* by the faded-diagram pattern. The real cost is engine surface area and per-lesson token spend on figure authoring — bounded by making `diagramming.md` an on-demand read (M1), by the figure template library (V6), and by the "no decorative figure" rule.

### V6 — A figure template library, so figures aren't authored from scratch each lesson

Authoring SVG geometry mid-lesson is the exact "figure it out each time" cost: it's slow at the worst moment, it burns context that should be teaching, and it's where malformed output comes from. A technical lesson also reaches for a small, predictable set of shapes.

Ship them as **parameterized templates the engine fills with data**, not as prose instructions the model re-derives:

- **sequence lanes** — N participants, ordered messages, optional partition marker
- **state machine** — states, legal transitions, illegal-transition highlight
- **quorum / partition** — node set, partition line, majority shading
- **layered boxes** — request path through N layers with a labeled boundary
- **parameter curve** — one input axis against one or two outputs, the shape that carries most "why does this fall over" invariants
- **timeline / swimlane** — concurrent actors, overlap windows

Each template ships with its blanked variant (the faded-diagram form from V1), so predict-before-reveal is the default path rather than extra work. Emitted by `tools/primer_view.py` (V4) from a small data dict — the model supplies labels and values, the template supplies geometry. Consistency, speed, and one less class of validation failure.

**Serves** the durable-assets directive directly. The template list is a starter set that accretes the same way the source canon does — a figure shape that proves load-bearing gets promoted into the library.

---

## Wave E — research abilities (R1–R4)

Currency is the project's **top** non-negotiable, and it is the only non-negotiable with no code behind it. The source-discovery pass is mandatory every lesson and is specified as prose: search for current material, vet against the stale-criteria, cite with tags, promote load-bearing finds. In practice that means the discovery pass is reconstructed from scratch every session, inside the lesson thread, with no memory of what was already vetted — the "figuring it out each time" cost, applied to the one thing the project cares most about.

Concretely, four costs today: the freshness rule ("more than ~3 months stale") is hand-computed arithmetic, which D-0018 already ruled should be code; a source vetted in one lesson is re-vetted in the next because nothing records the verdict; the sweep consumes lesson context that should be teaching; and `[from-training, verify]` tags are written into artifacts and then never revisited, so the verify never happens.

### R1 — `primer/research-protocol.md`: the discovery pass as a durable procedure

Promote the discovery pass from prose scattered through `source-canon.md` into a reusable decision procedure, read on demand:

- **Query templates per source class** — official docs, the spec itself, actively-maintained reference implementation, primary-source practitioner writing, recent talk/paper. The current text says "search for current material," which leaves the model to invent a search strategy per topic.
- **The vetting checklist as a decision procedure** with explicit verdicts (cite / cite-with-caveat / drop) rather than four prose criteria to weigh freshly each time.
- **Tagging rules and what earns `[verified via docs]`** — a fetch this session, not a plausible recollection.
- **Promotion rules** — what makes a find load-bearing enough to enter the canon floor.
- **Coverage floor per lesson** — a minimum of one primary source and one current-practice source before Deepen proceeds, so a thin sweep is visible rather than silent.

### R2 — Run the sweep in a subagent, off the lesson thread

The discovery pass is verbose retrieval whose *output* matters and whose *process* the learner never needs to see. Running it in the lesson thread spends the lesson's context on search results and puts search latency in the middle of teaching.

Move it to a subagent that returns a compact vetted list: URL, tag, one-line why-load-bearing, and the specific claim it grounds. The lesson thread stays for teaching. This also makes the sweep cacheable (R3) and parallelizable across sub-topics, which is what turns a mandatory-every-lesson cost into an affordable one.

### R3 — `tools/primer_sources.py` + `learner/source-ledger.md` (stdlib only)

A durable source ledger in the instance, with the mechanical parts as code — the same argument D-0018 made for review scheduling, applied to currency:

| Field | Purpose |
|---|---|
| `url`, `domain` | identity and grouping |
| `first_seen`, `last_verified` | deterministic freshness arithmetic, not eyeballed dates |
| `tag` | `verified` / `from-training` |
| `verdict` | `cite` / `caveat` / `dropped` + why |
| `used_in` | which lessons leaned on it |

Commands: `sources-add`, `sources-check <url>` (already vetted? what verdict? still fresh?), `sources-stale --days N` (what needs re-verification), `sources-promote` (ledger → canon floor), `sources-unverified` (the `[from-training, verify]` backlog).

Three things this buys. **Speed:** a source already vetted inside the freshness horizon is reused, not re-swept — the discovery pass gets cheaper the more it's run, which is the opposite of today. **Consistency:** the same source gets the same verdict across lessons instead of being re-judged. **Closure on currency:** `sources-stale` and `sources-unverified` turn the canon's periodic re-validation and the from-training backlog from remembered rituals into a queryable list, and give the deep recalibrate's "flag stale canon" step something real to read.

### R4 — Per-domain research cache, and claim-level provenance

**Domain cache.** primer's own engineering research artifacts (the two June docs, this one) demonstrate the pattern that the learner-facing side lacks: a dated sweep with an explicit freshness horizon, reused rather than repeated. Give each domain the same thing in the instance — a cached sweep with a horizon. Within the horizon, a lesson reads the cache and does a *narrow* top-up sweep for its specific topic; past it, the full sweep re-runs. This preserves the currency non-negotiable (the horizon is the guardrail, and the top-up is still mandatory) while removing the redundant work, which is what makes the mandatory pass sustainable rather than something that quietly degrades under time pressure.

**Claim-level provenance.** Tags are currently per-claim in prose with nothing tracking them, so `[from-training, verify]` is a note to a future reader who never comes back. Carry claim → source mapping in the artifact frontmatter, so `sources-unverified` can list the actual outstanding claims and a later session can close them.

**Serves** the currency non-negotiable and Goal 2. **Threatens** self-containment not at all (stdlib, local markdown, no service); the search tools were already in `allowed-tools`. The cost is one more state file in the instance and the discipline of writing verdicts down.

---

## Wave B — honesty hardening (H1–H3)

This wave exists because two findings converge on the same structural flaw, and it is a flaw the project already knows about: D-0015 admits the loop grades itself, and the mitigations added then (cold retrieval, time decay) anchor the *learner's recall* — not the *Primer's judgment*.

### H1 — Separate the examiner from the tutor (subagent)

**The evidence.** Models score 94–99% F1 judging *correct* answers, 0–76% on valid-but-suboptimal, and 4–55% on incorrect; over-rejection reaches 91%, over-validation 71%; giving the model the full solution changes nothing (§2). Meanwhile an 8B model with an adversarial critic panel beat GPT-4o on pedagogical judgment, and removing the Devil's Advocate cost more than removing fine-tuning entirely (§4).

Read together: the judgment primer depends on for every confidence move is its weakest measured capability, more context won't fix it, and the fix that works is architectural separation.

**The change.** At Recap, before writing marker deltas, spawn an **examiner subagent** that receives the learner's actual answers and the lesson's invariants but **not** the Primer's proposed confidence changes, and is prompted to argue *against* an upgrade. Then:

- Examiner and Primer agree → apply the delta.
- They disagree → hold confidence where it is, log the disagreement to `calibration-log.md`, and queue a reprobe. Disagreement is information, not a tie to break.

The valid-but-unconventional answer — the senior learner's normal output, and the worst case in §2 — is exactly what this catches, because the examiner has to defend a verdict rather than pattern-match agreement.

**Cost:** one subagent call per lesson, at Recap, outside the conversational path. §4's ~10× latency finding is about batch grading and is fine here.

**Serves** Goal 2 (the profile gets more true with use) and the honesty-about-confidence non-negotiable. **Threatens** self-containment only in appearance — a subagent is part of the harness, not an external service — but if subagents are unavailable the fallback is a same-context adversarial pass with the proposal withheld, which is weaker and should be labeled as such.

### H2 — A sycophancy trap set as the first real test of a non-negotiable

**The evidence.** EduFrameTrap measures post-pressure sycophancy at ~14% overall for both GPT-5.2 and Claude Sonnet 4.5, but the fragility profile is model-specific: **Claude models are weakest on context-switch frame attacks (17.9%), worst at low learner confidence**, with domain spikes to 30.2% (§1).

That is primer's exact operating condition. The senior-peer register invites the learner to push back and reframe; the profile explicitly tracks low-confidence markers. The register that makes primer good maximizes its measured failure mode — and "hold the line under pushback" is currently an instruction with no test.

**The change.** ~12 trap families in the learner's own domains, each = misconception + correct explanation + a plausible advanced frame, crossed with the three pressure modes (context-switch, authority, social-affective). Run headless against the engine; report **pressure-resolved** failure rates, not a single number, since the aggregate hides where the failure lives. Add a context-switch-specific counter-move to `anti-patterns.md` #1: when the learner reframes into a narrower or more advanced frame, restore the instructional frame explicitly before engaging the new one.

### H3 — Count the escape hatch

**The evidence.** AI dependence correlates with lower critical thinking, cognitive fatigue mediating; "metacognitive laziness" is documented behaviorally (§7).

T7's "just show me" hatch is right and should stay — misaligned Socratic pressure causes overload. But a *rising* hatch rate per domain is precisely the dependence signal the literature describes, and today it's invisible. Log it as a calibration signal; surface the trend at deep recalibrate. Cheap (one log line), and it's the difference between an escape hatch and an unnoticed slide.

---

## Wave C — mechanics (M1–M3)

### M1 — Progressive disclosure for the engine

All eight engine files are statically `@`-included in `SKILL.md`'s `<execution_context>` — ~10,900 words (~15k tokens) loaded on **every** invocation, including `/primer index` and `/primer profile`, which need almost none of it. Current skill guidance is the opposite: keep the body under 500 lines, put detail in files one level deep, load on demand.

Keep `system-prompt.md` and `lesson-protocol.md` static (they apply to every lesson). Make `intake-protocol.md` (init only), `feedback-protocol.md` (recap/recalibrate), `source-canon.md` (discovery pass), `lesson-template.md` (artifact write), and `diagramming.md` (figure authoring) on-demand reads routed by verb. This is what pays for Wave A's added instructions instead of stacking them on top.

### M2 — FSRS-6 with default parameters (revisits D-0020c)

D-0020 chose SM-2 because "FSRS needs trained parameters and review volume we won't have." FSRS-6 ships **21 pretrained default parameters** trained on ~700M reviews from ~20k users, is Anki's default for new profiles, and delivers roughly 20–30% fewer reviews for the same retention (§6). The objection was about training data; the default vector means there is none to collect.

The two constraints that actually drove D-0020 are untouched: markdown stays the source of truth, and the scheduler stays stdlib arithmetic over a fixed weight vector — no dependency, no install. Same `review-due` / `review-grade` / `review-add` CLI surface; the queue lines gain stability/difficulty alongside the existing interval. ~100 lines plus tests.

Fewer reviews for the same retention matters most for the learner whose review habit is fragile — which is the learner Goal 5 exists for.

### M3 — Ground prompt generation in graded exemplars

**The evidence.** No model exceeds 70% accuracy judging whether a prompt is usable; ambiguity detection is near-chance (F1 0.32–0.50); preference selection lands at 40–50%; the strongest model still emits unusable prompts ~36% of the time. The one intervention that worked: **grounding on labeled reference prompts from the same source lifted precision 56% → 78%** (§5).

T2 shipped a prose rubric. §5 measures what rubric-only buys — the 40–50% band. The fix is few-shot grounding, and primer already accumulates the corpus: past lessons plus the review queue's graded history.

Two changes. Add `learner/prompt-exemplars.md` holding the learner's own T3 (good) and T0 (off-target) examples, harvested from review outcomes, and few-shot the prompt writer on it. Then fix a live bug it exposes: primer currently cannot distinguish "the learner forgot" from "the prompt is bad." A prompt repeatedly missed while the learner demonstrably holds the concept is a bad prompt, and today it silently lowers the domain's confidence — a false negative wired into the learner model. Retire such prompts to T0 instead of docking confidence.

---

## Wave D — optional surface (S1–S3)

### S1 — Simulated-learner regression suite

`test_primer_state.py` covers the state layer (19 tests) and nothing covers the protocol — the part that determines lesson quality. Every protocol change since Session 1 shipped unverified, and a public core inviting contribution has no regression net for a contributor's change to land against. Simulated learners are now the standard methodology for exactly this (§9).

4–6 personas (novice, senior, impatient, overconfident, quiet, wrong-but-confident), run the protocol headless, score against `anti-patterns.md`'s existing self-check list — which is already written as a checklist and needs no new rubric. Pairs naturally with H2's trap set (same harness).

### S2 — SessionStart hook to surface due reviews (opt-in)

Goal 5 is habit formation, and the current design waits for the learner to remember `/primer review`. A `SessionStart` hook can inject `additionalContext` — verified against current hook documentation — so a local command reports "3 recalls due" at session start without nagging and without the learner initiating.

Opt-in and documented, not installed by default: it writes to the learner's global Claude Code settings, which is their environment, not primer's. Local command, no service — self-containment holds. (A *cloud* scheduled agent would be the obvious alternative and is rejected: it makes an external service load-bearing for a core goal.)

### S3 — Teach-it-back mode (`/primer teach <topic>`)

A tutee subagent, seeded with confusions drawn from the learner's own weak markers, that the learner has to teach. **Framed as a calibration instrument, not a retention booster** — the N=96 four-condition study found *no* significant difference in objective test scores across tutee/peer/challenger/control; the measured effects were on effort, perceived competence, and self-assessment accuracy (§8).

Its value here is specific: the learner's explanation to a naive listener is signal the Primer did not author, which `feedback-protocol.md` already says to prefer over its own assessments. Capped and opt-in, because the same study found the tutee role produced the highest learner anxiety of the four.

---

## Corrections to existing claims (X1–X2)

### X1 — The "session-scoped" differentiator claim needs a hedge

The June artifact's finding that "every existing learning skill is session-scoped" was accurate then and is too strong now: `learn-faster-kit`, `AI-learning-skill`, `fluent` (SM-2 + adaptive difficulty + tracking), and `obsidian-learning-loop` all ship persistence or scheduling (§10). Three vendors also now ship Socratic study modes, so the answer-refusing loop is table stakes rather than a differentiator.

What remains uncommon is the *combination*: an evidence-backed learner model with honest bidirectional confidence, a durable artifact per session, and class/instance privacy. That's a defensible claim; "the gap is persistence" no longer is. Currency is the project's top non-negotiable and it applies to claims about the project itself.

### X2 — Freshness horizon on the June artifacts, and re-verify before citing

Both 2026-06-15 artifacts declare themselves fresh until ~2026-09; that horizon is close. Three specific items should be fetched from primary sources before their numbers appear in `REQUIREMENTS.md` or a lesson: the Mayer multimedia meta-analysis, the learning-by-drawing meta-analysis, and the PhET meta-analysis (all snippet-only in this sweep, §11), plus the LearnLM RCT figures, which are secondary-sourced (§10). The ~0.4–0.7σ target from D-0016 is unaffected — nothing in this sweep moves it.

---

## What was deliberately *not* proposed

- **Image generation.** No evidence it beats a diagram for technical invariants, and it adds a service dependency. `visuals.md`'s exclusion of *generated images* stands even as its exclusion of *visuals* falls.
- **Voice mode.** The 2026 evidence base is second-language speaking practice (fluency, anxiety, engagement) and doesn't transfer to systems concepts. It also breaks the artifact-as-unit-of-value: the durable markdown is the product.
- **Publishing lessons as claude.ai artifacts.** Violates privacy-by-architecture as a default. Reserved for the D-0013 derivation step, opt-in, sanitized at that point.
- **Deep / neural knowledge tracing.** 2026 work reinforces the June finding — interpretable forgetting-aware models match deep KT, and LLMs don't build explicit learner models. Neural-symbolic KT is heavier than warranted at one-learner scale.
- **Cloud scheduled agents for review nudges.** Makes an external service load-bearing for a core goal. S2's local hook is the self-contained equivalent.
- **A multi-critic debate panel for live tutoring.** §4's architecture is validated for *batch grading*, at ~10× latency. H1 takes the part that fits (one examiner at Recap) and leaves the five-act debate, which would wreck the conversational loop.

---

## Suggested order

**Next tasks, per the maintainer: Wave A (presentation) and Wave E (research).** They're independent of each other and of everything below, and they share a shape — both convert per-lesson improvisation into durable assets, so both pay off on every subsequent lesson rather than once.

Within that: **M1 should land first**, before or alongside A. Wave A adds figure-authoring instructions and Wave E adds a research procedure; stacking both on top of an engine that already static-loads ~15k tokens every invocation is how the context budget gets spent on instructions instead of on the learner. M1 is also small.

Then **A and E in parallel** — A's script work (V4/V6) and E's script work (R3) are separate files, and A's protocol hook (V5) and E's subagent move (R2) touch different steps of `lesson-protocol.md`.

**Wave B** is the highest-leverage *correctness* work and is independent of both; it's the right next block once presentation and research land. **M2** (FSRS-6) and **M3** (grounded prompts) are self-contained and can slot anywhere, though M3 wants some review history to harvest exemplars from.

**Wave D** is real surface area and should wait for the first real intake and some lesson data — pending-tasks has carried "run a real `/primer init`" since Session 3, and several items across this proposal (M3's exemplars, H2's domain-specific traps, R4's domain caches, S1's personas) are better designed against actual lessons than imagined ones.

Also still open from Session 3, unrelated to this proposal: `proposal-0001-review-and-fixes` and `state-sidecar-portability-d0021` exist on the remote and `main` has advanced past both.
