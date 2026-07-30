# Source Canon — 2026-Current

**Currency is non-negotiable.** Wasting time learning a take the field has already moved past is a core failure mode for any technical learner (and an explicit fear for many). Every lesson must be grounded in current material.

This file is **not** the set of sources a lesson is permitted to cite. It is two things:

1. A **vetted floor** — sources already explored and confirmed load-bearing in 2026. Cite them freely; they are a shortcut for exploration already done. Their presence here does **not** mean they are the only good sources, and their absence does **not** mean a source is disallowed.
2. A **stale-list** — sources explicitly avoided. *This* is the currency guardrail, not the floor.

**Every lesson runs a source-discovery pass.** The floor is where a lesson *starts*, never where it *stops*. A closed allowlist would freeze knowledge at the moment the list was written — the opposite of the goal. **The pass is a procedure, not an improvisation: read `primer/research-protocol.md`** for the query templates by source class, the vetting decision procedure, the coverage floor, and how verdicts get recorded so the next lesson reuses them instead of re-judging.

This file is a living document, but **a lesson never writes to it** — it ships in the public core, a repo you pull updates into. Sources that prove load-bearing get promoted into the learner's own ledger (`$DATA_DIR/learner/source-ledger.md`), which is where a per-learner floor accretes from real use. See *Refreshing this file* and D-0025. Freshness of *this* file is checked against the ~3-month rule; ask `primer_sources.py sources-stale` rather than eyeballing dates.

---

## Vetted floor — starter pack (load-bearing in 2026)

> Cite freely. This is a starting set, not a permitted set. Always search beyond it (see *Source-discovery pass* below).
>
> **This floor is a domain *starter pack*, not a universal canon.** It currently covers the
> systems/backend/AI-agentic domains the public core shipped with — it is *not* the set of domains primer is
> for. A learner whose goal lies elsewhere (frontend, data, a new language, a non-software field) starts with
> an empty floor in that domain and grows it through the per-lesson discovery pass and promotion. The floor
> below is one example of an accreted floor, not a claim about what every learner should study.
>
> **Edition/date specifics carry the same tagging discipline as lesson claims.** Any entry asserting an
> edition, year, or version (`[edition — verify]` below) is the model's most hallucination-prone class; treat
> it as `[from-training, verify]` until grounded by the discovery pass or a freshness check. The currency
> guardrail is the stale-list and the discovery pass — not blind trust in the floor's own metadata.

### AI / Agentic Workflows

- **Anthropic — "Building Effective Agents"** — https://www.anthropic.com/research/building-effective-agents — Canonical taxonomy: workflows vs agents; chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer.
- **Anthropic Cookbook — patterns/agents** — https://github.com/anthropics/anthropic-cookbook/tree/main/patterns/agents — Reference implementations of the patterns above; minimal, no-framework code.
- **12-Factor Agents (Dex Horthy / HumanLayer)** — https://github.com/humanlayer/12-factor-agents — The "12-factor for LLM apps." Production checklist.
- **LangGraph** — https://langchain-ai.github.io/langgraph/ — Stateful graph orchestration. Reach for it when durable state demands it; not before.
- **Pydantic AI** — https://ai.pydantic.dev/ — FastAPI-style DX for agents; first-class MCP and structured output. Best fit for Python-heavy stacks.
- **Model Context Protocol (MCP)** — https://modelcontextprotocol.io/ — Tool-calling standard as of 2026. Read the spec, not blog summaries.
- **Chip Huyen — *AI Engineering* (O'Reilly, 2025)** `[edition — verify]` — https://www.oreilly.com/library/view/ai-engineering/9781098166298/ — Eval, RAG, deployment, cost — the systems-engineer view of LLM apps.
- **Hamel Husain on evals** — https://hamel.dev/ — "Your AI Product Needs Evals" is required reading.

### Distributed Systems

- **MIT 6.5840 (formerly 6.824)** — https://pdos.csail.mit.edu/6.824/ — The gold standard. Raft / Spinnaker / CRAQ labs in Go.
- **Designing Data-Intensive Applications, 2nd ed. (Kleppmann & Riccomini, 2026)** `[edition — verify]` — https://www.oreilly.com/library/view/designing-data-intensive-applications/9781098119058/ — Updated for cloud, streaming, modern storage. The book.
- **Jepsen analyses** — https://jepsen.io/analyses — Empirical consistency teardowns; how real systems fail in real ways.
- **aphyr/distsys-class** — https://github.com/aphyr/distsys-class — Practitioner counterpart to 6.5840.
- **Marc Brooker's blog** — https://brooker.co.za/blog/ — AWS principal engineer; current thinking on consensus, durability, formal methods in production.
- **theanalyst/awesome-distributed-systems** — https://github.com/theanalyst/awesome-distributed-systems — Maintained curation of papers, talks, tools.
- **jepsen-io/maelstrom** — https://github.com/jepsen-io/maelstrom — Workbench for writing toy Raft/CRDT impls and getting them checked.

### Event-Driven Architecture

- **microservices.io (Chris Richardson)** — https://microservices.io/patterns/ — Saga, outbox, event sourcing, CQRS. Actively maintained.
- **Oskar Dudycz — Event-Driven.io** — https://event-driven.io/ — Most prolific current voice on event sourcing pragmatics; "should you build it" essays are unusually honest.
- **Confluent — *Kafka: The Definitive Guide*, 2nd ed.** `[edition — verify]` — https://www.confluent.io/resources/kafka-the-definitive-guide/ — Updated for KRaft (no ZooKeeper).
- **Microsoft Azure Architecture Center — patterns** — https://learn.microsoft.com/azure/architecture/patterns/ — Vendor-neutral writeups of CQRS, event sourcing, outbox, saga with tradeoffs.
- **NATS JetStream docs** — https://docs.nats.io/nats-concepts/jetstream — Lightweight Kafka alternative.
- **Debezium docs** — https://debezium.io/documentation/ — CDC + outbox-pattern reference implementation.
- **Martin Fowler — Event Sourcing / CQRS** — https://martinfowler.com/eaaDev/EventSourcing.html — Foundational vocabulary; pair with Dudycz for 2026 reality.

### Docker / Containers

- **Docker official docs — Build with Docker** — https://docs.docker.com/build/ — BuildKit, cache mounts, multi-stage, bake. Source of truth.
- **Nigel Poulton — *Docker Deep Dive*, 2025 ed.** `[edition — verify]` — https://leanpub.com/dockerdeepdive — Updated yearly. Current edition adds Build Cloud, buildx, Model Runner.
- **Google distroless** — https://github.com/GoogleContainerTools/distroless — Canonical minimal runtime images; `:debug` variants for incident response.
- **Chainguard Images** — https://images.chainguard.dev/ — The 2025-26 distroless successor with continuous CVE patching.
- **wagoodman/dive** — https://github.com/wagoodman/dive — Layer-by-layer image inspection; teaches what your Dockerfile actually produces.
- **Docker Compose v2 docs** — https://docs.docker.com/compose/ — Compose v2 (Go rewrite) is the current one.

### Backend Systems Thinking

- **donnemartin/system-design-primer** — https://github.com/donnemartin/system-design-primer — Shared vocabulary for system design.
- **Google SRE Books (free)** — https://sre.google/books/ — *SRE*, *Workbook*, *Building Secure & Reliable Systems*. Canonical reliability/on-call/capacity-planning text.
- ***Software Engineering at Google* (Winters/Manshreck/Wright)** — https://abseil.io/resources/swe-book — Code-as-org-asset; Hyrum's Law; staff-IC mindset at scale.
- **Tanya Reilly — *The Staff Engineer's Path*** — https://www.oreilly.com/library/view/the-staff-engineers/9781098118723/ — The book on staff-level technical leadership.
- **Will Larson — *An Elegant Puzzle* + StaffEng.com** — https://staffeng.com/ — Career/scope/scale patterns.
- **The Pragmatic Engineer (Gergely Orosz)** — https://newsletter.pragmaticengineer.com/ — Current Big-Tech engineering practice.
- **High Scalability** — http://highscalability.com/ — Architecture deep-dives on real systems (Discord, Figma, Notion).
- **Marc Brooker + Cindy Sridharan blogs** — https://brooker.co.za/blog/, https://copyconstruct.medium.com/ — Distributed-systems reliability and observability thinking.

---

## Source-discovery pass (every lesson)

Before the Deepen body, the Primer spends real effort finding current sources on the *specific* topic — not just reaching into the floor above. The floor saves time on the broad strokes; the discovery pass catches what's newer, more specific, or has moved since the floor was last touched.

What the pass does:

1. **Search** for current material on the exact topic (official docs, recent talks/papers, maintained projects, primary-source blogs from credible practitioners).
2. **Vet** each candidate against the stale-criteria below. A source that fails is dropped, not cited.
3. **Cite** survivors in `sources_consulted` with `[verified via docs]` (fetched this session) or `[from-training, verify]` tags.
4. **Promote** any source that proved load-bearing into the learner's ledger at recap (`primer_sources.py sources-promote`). Not into this file — see above.

The pass is mandatory even for topics with strong floor coverage — the floor ages, and the field moves between sessions.

## Stale-criteria (how to vet a candidate)

A source is stale — and excluded regardless of where it was found — if any hold:

- It predates a known consensus shift in its domain (see *Cross-cutting shifts* below) and hasn't been updated past it.
- A maintained successor exists that the field has moved to (e.g., a 1st ed. when a current ed. ships; a site that's actively maintained vs. a frozen book).
- It teaches a pattern the field has explicitly cooled on (e.g., "event-source everything," Alpine-as-default).
- The author/version/RFC claims can't be grounded and the topic is version- or API-specific.

## Stale list (named instances to avoid)

- Pre-2024 LangChain monolith tutorials — superseded by Anthropic "Building Effective Agents" + LangGraph + Pydantic AI.
- Designing Data-Intensive Applications, 1st ed. (2017) — noticeably dated on cloud and streaming. Use 2nd ed.
- "Microservices Patterns" book (Richardson, 2018) — use the actively-maintained microservices.io site + Dudycz.
- Burns, "Designing Distributed Systems" (2018) — use Brooker + 6.5840 + Jepsen.
- Alpine-as-default Dockerfiles — distroless / Chainguard are the current default.
- Older Coursera "Cloud Computing Specialization" / Udemy distsys — replaced by 6.5840 + DDIA 2nd ed.
- "Use Paxos" content from before ~2020 — Raft + practical-Paxos variants are the current teaching path.
- "Event-source everything" content — the field has cooled. Outbox-first; sagas only for true cross-service workflows.

---

## Cross-cutting shifts to encode (2024–2026)

- **Agents:** consensus has moved from "use a framework" to "use simple, composable LLM-call patterns; reach for LangGraph/Pydantic AI when you need durable state." MCP is now the tool-calling standard — teach it at the same level as HTTP, not as an optional extra.
- **Distributed systems:** less "implement Paxos," more "understand replication / consistency / failure modes well enough to read a Jepsen report." Formal methods (TLA+, P) are entering practitioner mainstream via Brooker/AWS.
- **Event-driven:** outbox-first; sagas only for true cross-service workflows; full event sourcing only for audit/finance domains.
- **Containers:** distroless/Chainguard have displaced Alpine-as-default; BuildKit features (cache mounts, secrets, bake) are no longer optional.
- **Backend thinking:** the staff-engineer vocabulary (scope, leverage, glue work) has become standard; system design is increasingly *operational* (capacity, on-call, blast radius) rather than purely architectural.

---

## Refreshing this file

Two triggers keep the floor current:

**Per-lesson promotion (every session) goes to the learner's ledger, not to this file.** A source that proved load-bearing gets promoted at recap via `primer_sources.py sources-promote`, which marks it as floor in `$DATA_DIR/learner/source-ledger.md`. That ledger is the learner's own accreted floor, and `sources-floor --domain <d>` is what a future lesson reads as its starting set.

This file is **never written to by a lesson.** It ships in the public core — a repo the learner pulls updates into — so a per-learner promotion here would leak what they study and conflict on every pull. Contributing a source upstream is a deliberate PR. (D-0025; the pass itself is `primer/research-protocol.md`.)

**Periodic re-validation (`freshness_check` > ~3 months).** The skill should:

1. Spawn a research subagent to verify each domain's floor is still load-bearing.
2. Surface new sources that have entered lessons or conversation (high signal: new books, talks at major conferences, projects with rapid star growth).
3. Demote any floor entry that now fails the stale-criteria into the stale list.
4. Update this file and bump the date.

The deep `recalibrate` ritual (see `primer/feedback-protocol.md`) also flags floor entries that have gone stale.

Prefer fewer, higher-quality sources over comprehensive lists. When in doubt, cut.
