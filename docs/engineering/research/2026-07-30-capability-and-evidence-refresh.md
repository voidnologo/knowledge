# Research — Capability & evidence refresh (June–July 2026)

> **Durable research artifact.** Captured 2026-07-30 (Session 4). This is a *delta* on the two 2026-06-15 artifacts, not a replacement — read those first for the foundational evidence (effect sizes, BKT/OLM, expertise reversal, Matuschak's corpus, the comparable-projects landscape). Treat as **fresh until ~2026-10**; re-verify quantitative claims past that.
>
> **Provenance.** Web sweep + primary-source fetches. Tags follow the project's own discipline: **[verified]** = the primary source was fetched this session; **[partial]** = fetched but the extraction was lossy (large PDF); **[snippet]** = search-result summary only, primary not read. Effect sizes are Cohen's *d* / Hedges' *g* unless noted.
>
> **Why this sweep happened.** The design was conceived several model generations ago and its capability assumptions (text-only, single-agent, no test suite, SM-2, "no images in v1") predate the harness features and the published evidence that now exist. Feeds Proposal 0003.

---

## 1. Pedagogical sycophancy is now a named, measured, benchmarked failure mode

**EduFrameTrap** — Kasneci & Kasneci, arXiv:2605.14604, May 2026 **[verified]**. 360 trap families across math, physics, economics, chemistry, biology, CS; 3,240 four-turn dialogues crossing learner confidence (3 levels) with three pressure modes: context-switch frame attacks, authority claims, and social-affective face-saving. A trap = misconception + correct explanation + a plausible "advanced frame" that makes the misconception sound credible. The measured event is whether the tutor *maintains* a correction after pressure arrives in turn 2.

Findings: overall post-pressure sycophancy ~14% for both GPT-5.2 and Claude Sonnet 4.5 — but the aggregate hides the useful part, because **fragility profiles differ by pressure mode and model**. GPT-5.2 fails most on authority (16.8%) and social-affective (18.1%), least on context-switch (7.7%). Claude Sonnet 4.5 inverts it: context-switch is the weak point (17.9%, worst at *low* learner confidence), social-affective the strongest (8.9%). Failures cluster in specific domain × pressure combinations rather than distributing evenly (Claude/chemistry/context-switch spiked to 30.2%; GPT/economics/social-affective to 28.6%). The authors name a "reasoning–sycophancy paradox": pressure resilience is separable from reasoning ability, and *fluent* capitulation makes a misconception more persuasive even when the rate is flat. Stated limitations: two models, synthetic benchmark, no measurement of downstream learning harm.

Related: **SycEval** reports 58% overall sycophancy across GPT-4o/Claude/Gemini on math and medical reasoning; **ELEPHANT** finds GPT-5 substantially sycophantic in open-ended advice **[snippet]**.

**Why this matters here.** "Hold positions under pushback; sycophancy is failure" is one of primer's non-negotiables, and it is currently an *instruction with no test*. It is now testable. Worse, the specific vulnerability measured for Claude models — context-switch frame attacks, strongest at low learner confidence — is the exact shape primer's register invites: a senior-peer voice actively encourages the learner to push back and reframe, and the profile explicitly records low-confidence depth markers. The register that makes primer good is the register that maximizes its measured failure mode.

## 2. Diagnostic asymmetry: models confirm correct answers and miss almost everything else

**"Confirming Correct, Missing the Rest"** — arXiv:2605.16207, May 2026 **[verified]**. Knowledge graph over 516 propositional-logic proof states establishing ground truth for all valid inference paths; 10,836 solution-feedback pairs; seven models simulating student responses then evaluating them under three roles (Peer with minimal context, Teacher with the full solution, Judge as verifier); human raters scored feedback on four pedagogical dimensions.

Results by solution category: **optimal solutions 94–99% F1; valid-but-suboptimal alternatives 0–76% F1; incorrect solutions 4–55% F1.** Two failure modes: over-rejection (marking valid reasoning wrong) up to 91%, and over-validation (accepting incorrect solutions) up to 71%. Model selection explained 95% of performance variance; **giving the model the complete solution had negligible effect**. Recommendation: hybrid architecture where a symbolic/graph classifier owns diagnostic judgment and the LLM owns dialogue and scaffolding.

**Why this matters here.** primer's Probe → Diagnose steps assume the model can judge a free-form answer well enough to move a depth marker. It can judge *correct* answers. The valid-but-unconventional answer is the worst case in the study — and that is precisely what a senior learner produces. Every confidence upgrade and downgrade in `topic-index.md` currently rests on the weakest measured capability in the loop, and the study says more context does not fix it.

## 3. Adaptivity is the industry-wide weak link — which is primer's bet

**TutorBench** — Srinivasa et al. (Scale AI), arXiv:2510.02663, Oct 2025 **[verified]**. 1,490 expert-curated samples across six STEM subjects, 15,220 weighted rubric criteria, 16 frontier models, LLM judge validated at F1 0.82 against human majority vote.

**No model exceeds 56%** (Gemini 2.5 Pro 55.65%, GPT-5 55.33%). By competency: adaptive explanation generation is the *worst* at 47.16%, assessment/feedback 51.56%, active-learning support 54.07%. The single lowest-scoring skill is "including alternative solutions, examples, analogies" at **32.8%**, against 53% on error identification. Claude models excel at active-learning support but lag overall. Named failure modes: personalization gaps, missing alternative explanations, cognitive-calibration misalignment (counterintuitively worse on "remembering" than "evaluating" tasks), and weak attention to frustration/confusion signals. Notably **828 of 1,490 samples are multimodal** — images of handwritten or printed student work. The reference benchmark for tutoring now assumes a visual channel in both directions.

**Why this matters here.** Two readings, both useful. The bet is validated: adaptivity is where every frontier model is weakest, and a persistent evidence-backed profile is a direct attack on it. The warning: the model will *not* volunteer a second framing — 32.8% — so "give an alternative analogy" has to be an explicit engine instruction, not an emergent property of a good register.

## 4. Separating the grader from the teacher beats scaling the teacher

**Hierarchical Pedagogical Oversight (HPO)** — Sadhu & Dhor, AAAI 2026 EGSAI, arXiv:2512.22496 **[verified]**. Three phases: specialist distillers (conceptual / behavioral / trajectory analysts) ground the context; a five-act structured adversarial debate stress-tests the tutor response with a Permissive Critic and a Strict Critic proposing opposing theses and a Devil's Advocate attacking both; then Judge, Stress Analyst, and Lead Evaluator synthesize.

An **8B-parameter HPO model reached macro F1 0.845, beating GPT-4o at 0.812**. Ablation: removing the Devil's Advocate cost 4.2% — **more than removing fine-tuning entirely (2.0%)**. Cost: ~4.2s per evaluation on an A100, ~10× a single-agent baseline, which the authors call acceptable for batch grading.

**Why this matters here.** D-0015 already admits primer's structural weakness — the tutor grades its own learner model, and a closed self-assessment loop drifts optimistic. The mitigations in place (cold retrieval, time decay) are anchors on the *learner's* recall, not on the *Primer's* judgment. The judgment itself is still unchecked. HPO says the fix is architectural and that the adversarial role carries more weight than model quality; §2 says the judgment being checked is the weakest link in the pipeline. The two findings converge on one move: an examiner that is not the teacher, run as batch work between lessons.

## 5. LLM-authored retrieval prompts: quantified, and worse than the rubric assumes

**Memory Machines** — Ozzie Kirkby & Andy Matuschak, 2026 **[verified]**. An `srs-prompts` dataset of ~1,500 prompts across 93 sources with a four-tier quality taxonomy (T0 off-target, T1 needs refactoring, T2 needs polish, T3 ready to review), used to test evaluation approaches, generation quality, and grounding strategies.

- Binary "is this prompt usable": **no model exceeded 70% accuracy.**
- Rubric dimensions: models reliably caught missing context (F1 0.87) but were near-chance on ambiguity (F1 0.32–0.50).
- Preference selection among 2–4 candidates: best prompt chosen only **~40–50%** of the time.
- Fine-tuned models matched frontier performance but did not exceed it.
- **GPT-5.2, the strongest model tested, still produced unusable prompts ~36% of the time.**
- The one intervention that worked: **grounding.** Showing the judge labeled reference prompts *from the same passage* lifted precision from **56% to 78%**.

**Why this matters here.** T2 shipped a prose quality bar (Matuschak's five attributes plus a conceptual pattern language) and a self-check. This study measures what a rubric-only approach buys: the 40–50% band. The thing that works is few-shot grounding against labeled exemplars from the same source — and primer is unusually well positioned to supply them, because it already accumulates a per-learner corpus (past lessons, plus the review queue's graded history). Nothing in the engine currently harvests it.

A second-order finding this exposes: primer cannot presently distinguish "the learner forgot" from "the prompt is bad." A prompt the learner keeps missing while demonstrably holding the concept is a T0/T1 prompt, and today it silently lowers the domain's confidence. That is a false negative wired straight into the learner model.

## 6. FSRS-6 removes the objection that ruled it out

FSRS-6 shipped late 2025: **21 parameters with pretrained defaults** trained on ~700M reviews from ~20k Anki users; Anki ships FSRS as the default scheduler for new profiles; roughly **20–30% fewer reviews for the same retention** **[verified]** for the parameter/default facts via the open-spaced-repetition wiki, **[snippet]** for the review-count and training-corpus figures. It models stability, difficulty, and retrievability per card with a trainable forgetting curve, versus SM-2's single ease factor. Implementation is more involved than SM-2 — retrievability, stability updates, difficulty adjustment, exponential/power terms — but it is still closed-form arithmetic over a fixed weight vector. A `fsrs` PyPI package was released 2026-03-10; SuperMemo announced SM-20 (fully ML-derived parameters) and an API in early 2026 **[snippet]** — neither is relevant to a stdlib-only design.

**Why this matters here.** D-0020(c) chose SM-2 on the reasoning that "FSRS needs trained parameters and review volume we won't have." The pretrained default vector is exactly the counter-evidence: FSRS-6 works cold. The two constraints that actually drove D-0020 — markdown as source of truth, Python stdlib only — are untouched by the swap, because the default-parameter path needs no training, no data collection, and no dependency.

## 7. The cognitive-offloading literature has hardened

AI dependence is associated with lower critical thinking, with cognitive fatigue as a partial mediator and information literacy as a buffer (*Acta Psychologica*, 2025, N=580 university students) **[snippet]**. "Metacognitive laziness" — reduced self-regulation, less problem verification, less self-questioning, less independent reasoning before consulting the AI — is documented in a vocational-education co-design study, arXiv:2512.12306 **[partial]**. Younger users show higher dependence and lower critical-thinking scores **[snippet]**. The consistent qualifier across this literature: generative AI supports critical thinking *under guided, reflective use*, and erodes it under unstructured reliance.

**Why this matters here.** productive-struggle-over-fluent-answers is now defensible as harm reduction, not only as pedagogy. But it also puts an honest tension on T7's "just show me" escape hatch: the hatch is the right call (misaligned Socratic pressure causes overload — 2026-06-15 artifact §1), yet a *rising* escape-hatch rate is precisely the dependence signal this literature describes. Today that rate is invisible; nothing counts it.

## 8. Learning-by-teaching: the effect is on effort and self-calibration, not test scores

**"Who You Explain To Matters"** — Xu, Zhang, Tang & Lee, 2026, arXiv:2601.16583 **[verified]**. Between-subjects, N=96, four conditions (tutee agent simulating a novice, peer agent, challenger agent using Socratic questioning, minimal-feedback control), five rounds of explaining a supply-and-demand scenario. **No statistically significant difference in objective test scores across any condition.** Differences were subjective: peer and challenger groups reported higher perceived competence; all agent conditions reported stronger perceived critical thinking than control. Per-role character: tutee elicited maximum cognitive effort but produced high pressure and anxiety about teaching accurately; peer produced the most relaxed engagement but excessive agreement sometimes reduced critical reasoning; challenger promoted metacognitive acts at moderate pressure. Conclusion: match the agent role to the pedagogical goal; there is no universally superior role.

Supporting: 500+ students in an undergraduate algorithms course diagnosing a deliberately-erring teachable agent gained 0.72 points on a 1–6 scale (L@S 2026) **[snippet]**; MatlabTutee (119 students, four experiments) conveyed a convincing novice persona and helped learners "develop a more accurate assessment of their own abilities" **[snippet]**; the protégé effect (students work harder for their agent than for themselves) is the long-standing Stanford AAA Lab result **[snippet]**.

**Why this matters here.** A teach-it-back mode is worth having — but as a **calibration instrument, not a retention booster**. Its value to primer is that the learner's explanation to a naive listener is *signal the Primer did not author*, which the feedback protocol explicitly says to prefer. Claiming learning gains from it would not survive the N=96 null result.

## 9. Simulated learners are now the standard way to test a tutor

Converging 2025–2026 work: TutorBench's profile-driven first-person student simulator **[verified]**; **VISTA**, a versatile interactive user-simulation toolkit for agent evaluation (arXiv:2606.11079) **[snippet]**; a benchmark for *controllable* simulation of imperfect students (arXiv:2605.25601) **[snippet]**; history-aware student profiles for tutoring dialogues (arXiv:2605.30051) **[snippet]**; "Simulated Students in Tutoring Dialogues" (ACL 2026) **[snippet]**; Agent4Edu (AAAI 2025) generating learner response data **[snippet, carried from the June artifact]**. The shared claim is that LLM-simulated students produce realistic confusion and error patterns usable for benchmarking teacher models, which is how the coverage problem gets solved without human subjects.

**Why this matters here.** primer has no engine test suite. `test_primer_state.py` covers the state layer (19 tests on scheduling, decay, triggers) and nothing covers the protocol — the part that actually determines lesson quality. Every protocol edit since Session 1 has shipped unverified. The public core's stated goal is community improvement, and there is currently no regression net for a contributor to land a change against.

## 10. Product landscape: Socratic study modes are table stakes; visuals are the differentiator

ChatGPT Study Mode, Gemini Guided Learning, and Claude Learning Mode all ship as of 2026 **[snippet]**. Reviewer consensus on how they differ: ChatGPT's is conversational and follows tangents; **Gemini's differentiator is structured staging plus visuals and diagrams**; Claude's is the most "teacher-like" in its written feedback. Google's LearnLM report (Nov 2025) describes an RCT with Eedi, 165 UK secondary students aged 13–15, where a human-expert-supervised LearnLM tutor edged text-based human-only tutoring on subsequent novel problem types (~66.2% success) **[snippet — the PDF would not extract; figures come from secondary coverage and must be re-verified before citing]**.

The Claude Code learning-skill niche has also filled in: `learn-faster-kit` (spaced repetition + personalized syllabi + progress tracking), `AI-learning-skill` (active recall, spaced repetition, Socratic dialogue, scaffolding), `fluent` (SM-2, adaptive difficulty, tracking, language-focused), `obsidian-learning-loop` (generates open questions, grades strictly, surfaces wiki gaps), alongside the already-catalogued `learning-opportunities` **[snippet]**.

**Why this matters here.** The answer-refusing Socratic loop is no longer a differentiator — three major vendors ship it and several Claude Code skills implement it. What remains genuinely uncommon is the combination the June artifact identified: a persistent, evidence-backed, hand-editable learner model with honest confidence, plus a durable artifact per session, plus class/instance privacy. The README's "every existing learning skill is session-scoped" framing is now too strong and needs a hedge. And the one feature reviewers single out as a differentiator elsewhere — visuals — is the thing primer's engine explicitly rules out.

---

## 11. Visual and multimedia learning — the evidence for a visual layer

**Diagrams pay off reliably; interactivity pays off selectively; decoration costs.**

- **Mayer meta-analysis** — "A meta-analysis of Richard Mayer's multimedia learning research: searching for boundary conditions of design principles across multiple media types," *Educational Research Review*, 2025 (S1747938X25000673) **[snippet]**. Largest effects: removing seductive detail, modality, personalization, the multimedia principle, sentence-level coherence, self-explanation. **Large, consistent effects for text + diagrams across factual, inferential, *and* transfer outcomes.** Medium effects: testing, scaffolding, cueing, embodiment. **Less consistent: animation, games, simulations** — smaller on factual, larger on inferential/transfer; **no significant effect for VR.**
- **Learning by drawing** — meta-analysis of 53 studies, 166 effects, 8,111 participants: **overall g = 0.69** across factual, inferential, and transfer outcomes; mechanisms are generation, comparison, and revision **[snippet]**. A separate meta-analysis found **no significant difference between technology-based and paper-and-pencil drawing** **[snippet]**, and prior knowledge plus spatial ability correlate with recall and transfer.
- **Interactive simulations** — PhET meta-analysis, 47 effect sizes from 20 studies (2018–2023), 4,563 students: **d ≈ 0.83** vs traditional approaches **[snippet]**. But head-to-head comparisons of a circuit simulation against static graphics and physical bulbs-and-wires found **no statistically significant difference between treatment groups** **[snippet]**. Read together: the simulation win is confounded with activity design, and the honest claim is much weaker than d = 0.83 suggests.

**AI-generated visuals break in specific, checkable ways.**

- **"Evaluating Interactivity: Toward Automated Assessment of AI-Generated Explorable Explanations"** — Wang, Wang & Wen, 2026, arXiv:2606.31012 **[partial]**. Proposes an FSM-based evaluation of interactivity across interaction correctness, state management, and educational clarity. Finding: **most AI-generated interactive explanations fail state management and respond incorrectly to user manipulation** — broken interactivity chains, incorrect state transitions, misaligned outputs, poor sequential handling. Text generation ability does not carry over to functional interactive systems.
- **MermaidSeqBench** — arXiv:2511.14967 **[snippet]**. Mermaid admits many semantically equivalent surface forms, so string matching is unreliable as a correctness check; they use a judge that normalizes node labels, extracts directed relations, and computes node/edge precision/recall/F1. **DiagramIR**, an IR-based automatic evaluation pipeline for educational diagrams, reports higher agreement with human raters than LLM-as-judge baselines **[snippet]**.
- Adjacent 2026 work confirms the direction of travel: agentic pipelines that plan → generate → review → refine interactive tutorial sites (LERN 2026), Transformer Explainer running a live GPT-2 in-browser (CHI 2026), EduIllustrate for scalable multimodal educational content (arXiv:2604.05005) **[snippet]**.

**The composite design rule this implies**, which is stronger than any single finding:

1. **Static diagrams are the default.** Text + diagrams is one of the largest, most consistent effects in the corpus, including on transfer. This is the reliable win and it is cheap.
2. **Interactivity is a targeted instrument, not an upgrade.** It earns its place where a concept has a parameter genuinely worth varying, and its measured benefit concentrates on inferential/transfer outcomes. It is also where AI generation demonstrably breaks, so it must be validated, not trusted.
3. **Decoration is a measured harm.** Removing seductive detail is among the *largest* effects in the meta-analysis. A visual that does not carry an invariant is worse than no visual.
4. **The learner should draw, not just look.** g = 0.69 sits with *learner-generated* representations, and the medium does not matter — so "predict what this diagram looks like / fill the blanked step / describe what changes if λ doubles" captures the effect without needing a drawing canvas. This is the productive-struggle non-negotiable expressed visually, and it is the single highest-value item in this section.

---

## 12. Cross-cutting takeaways

1. **The teacher must stop grading itself.** §2 (models confirm correct answers and fail on everything else) and §4 (adversarial oversight beats a bigger model; the Devil's Advocate outweighs fine-tuning) converge on separating the examiner from the tutor. This is the highest-leverage structural change available, and it hardens the weakness D-0015 already admits.
2. **Two non-negotiables are now testable, and untested.** Sycophancy has a benchmark shape (§1) whose measured Claude-model weak spot is the register primer deliberately runs; protocol quality has a simulated-learner methodology (§9). Neither has a test in the repo.
3. **Rubrics are not enough for prompt quality; grounding is.** §5 puts a number on it — rubric-only lands at 40–50%, grounded exemplars lift precision 56% → 78% — and primer already accumulates the corpus needed to do it.
4. **Adaptivity is the industry-wide gap, so the profile is the right bet** (§3) — but alternative framings score 32.8% and must be demanded explicitly rather than assumed.
5. **Two settled decisions have new counter-evidence:** SM-2 over FSRS (§6 — pretrained defaults remove the "no training data" objection) and "no images in v1" (§11 — text + diagrams is one of the largest consistent effects available).
6. **Three claims to design *against*:** "interactive beats static" (§11 — confounded, and AI-generated interactives fail state management), "a good rubric produces good prompts" (§5), and "teach-it-back raises test scores" (§8 — N=96 null).

*Weak-source caveats retained:* the LearnLM RCT figures (§10) are secondary-sourced and must be re-verified before citing; the Mayer, drawing, and PhET meta-analyses (§11) are search-snippet only and should be fetched before any of their numbers appear in a lesson or in `REQUIREMENTS.md`; §7's dependence findings are correlational.
