# Research Protocol — the source-discovery pass, as a procedure

Read this before the Deepen step's discovery pass. `primer/source-canon.md` holds the shared starter floor and the stale-criteria; this file is *how the pass runs*.

Currency is the top non-negotiable, and the pass that enforces it is mandatory every lesson. That only stays true if it's cheap. So the pass is a procedure with a memory, not a fresh improvisation each session: it reads what has already been vetted, sweeps narrowly for what hasn't, and writes its verdicts down.

## Contents

- The three states, and which one you're in
- Query templates by source class
- Vetting: the decision procedure
- Coverage floor
- Recording verdicts (and why it pays off)
- Claim-level provenance

---

## The three states, and which one you're in

Ask the ledger first. Never start from a blank sweep when the answer may already be recorded:

```bash
python3 ${CLAUDE_SKILL_DIR}/tools/primer_sources.py --data-dir "$DATA_DIR" sweep-check --domain <d>
```

| State | What it means | What the pass does |
|---|---|---|
| **No recorded sweep** | This domain has never been swept | **Full sweep** — all five source classes below, then `sweep-record` |
| **Sweep fresh** (inside the horizon) | The domain's landscape was mapped recently | **Narrow top-up** — `sources-floor --domain <d>` for the starting set, then search only for *this topic*'s specifics |
| **Sweep stale** (past the horizon) | The landscape has had time to move | **Full sweep** again, then `sweep-record` |

The narrow top-up is still mandatory. The horizon is the guardrail on the *cached sweep*, not permission to skip searching — a fresh domain sweep says nothing about a topic nobody has looked up yet.

**Run the sweep in a subagent.** It is verbose retrieval whose output matters and whose process the learner never needs to see, and doing it in the lesson thread spends the lesson's context on search results and puts search latency in the middle of teaching. Dispatch it with the topic, the domain, and the current floor; have it return a compact list — URL, tag, one-line why-load-bearing, and the specific claim it grounds. Nothing else.

## Query templates by source class

"Search for current material" leaves a strategy to be invented per topic. Use these five classes; they're what actually separates a current source from a popular one. Aim for one hit in at least the first two.

| Class | What to look for | Query shape |
|---|---|---|
| **Primary spec / official docs** | The thing itself, not a summary of it | `<topic> specification`, `<project> docs <subsystem>`, `site:docs.<project>.<tld> <topic>` |
| **Current practice** | What practitioners do *now*, with the tradeoff named | `<topic> in production`, `<topic> tradeoffs <current year>`, `<topic> postmortem` |
| **Maintained reference implementation** | Code that is kept alive, not a 2019 gist | `<topic> reference implementation`, recent commit activity, released versions |
| **Primary-source practitioner writing** | A named person with operational scars | known authors in the domain; their blog, not an aggregator's paraphrase |
| **Recent talk or paper** | Where the consensus is moving | `<topic> <conference> <year>`, `arxiv <topic>` for research-adjacent domains |

Two rules that matter more than the queries:

- **Prefer the primary over the paraphrase.** A blog summarizing a spec is a source about a source. Cite the spec and use the blog for the practitioner read.
- **Recency is not currency.** A new post repeating a superseded pattern is stale regardless of its date, and a 2019 spec that nothing has replaced is current. Judge against the stale-criteria, not the timestamp.

## Vetting: the decision procedure

For each candidate, in order. Stop at the first line that fires.

1. **Already in the ledger?** `sources-check --url <u>`. If the verdict is `dropped`, don't re-litigate it. If it's `cite`/`caveat` and fresh, reuse it — that's the saving — and **still `sources-add` it**, which is one call that refreshes `checked` and records the reliance. Skipping that is what would make `used` count recordings instead of lessons, and `sources-stale`'s "most-used first" ordering rests on it. If it's stale, re-validate now and re-add (which refreshes `checked`).
2. **Fails a stale-criterion?** (`primer/source-canon.md` — predates a known consensus shift, has a maintained successor, teaches a pattern the field cooled on, or makes version claims that can't be grounded.) → verdict **`dropped`**, recorded with the reason so the next lesson doesn't spend time on it again.
3. **Load-bearing for this lesson, and grounded?** → verdict **`cite`**, tag `verified` if it was actually fetched and read this session.
4. **Usable but limited?** (right on the concept, dated on specifics; vendor-authored; a single case study generalized too far) → verdict **`caveat`**, and *state the limitation in the lesson* — an unstated caveat is the same as no caveat.
5. **Couldn't be grounded, and the topic is version- or API-specific?** → do not cite it. If it's the only thing available, tag it **`from-training`** and say so out loud to the learner. These accumulate as a backlog, queryable with `sources-unverified`.

Tags are not decoration. `[verified via docs]` means *fetched and read in this session* — not "I'm confident about it." The whole tagging discipline is worthless the moment it starts meaning the latter.

## Coverage floor

Before Deepen proceeds, the pass must have produced **at least one primary source and one current-practice source** for the topic. If it hasn't, say so in the lesson rather than proceeding quietly — a thin sweep that goes unmentioned is how a lesson ends up grounded in the model's training data while wearing citations.

Prefer fewer, higher-quality sources over a long list. Three that carry the lesson beat nine that decorate it.

## Recording verdicts (and why it pays off)

Every candidate gets written down — including the rejects, which is the part that's easy to skip and expensive to lose:

```bash
python3 ${CLAUDE_SKILL_DIR}/tools/primer_sources.py --data-dir "$DATA_DIR" \
  sources-add --url <u> --domain <d> --tag verified --verdict cite --why "<one line>"
```

Two constraints worth knowing before a sweep writes twenty of these: **`--why` is capped at 400 characters and may not contain a `|`** (the ledger is pipe-delimited, one entry per line), and **`sweep-record --note` has the same 400-character cap.** Both reject with a specific message and a non-zero exit, so a `set -e` loop stops rather than skipping silently — but a loop that ignores exit codes will drop the entry, and the rejects are the entries most worth keeping.

Re-adding an existing URL is the normal case — it refreshes `checked`, bumps `used`, and keeps the original `seen`. A source used in five lessons with a stale `checked` is the first thing to re-verify.

At recap, promote what proved load-bearing:

```bash
… sources-promote --url <u>        # marks it as part of this domain's floor
```

**Promotion writes to the learner's ledger, not to the public core.** `primer/source-canon.md` is a shared starter pack in a repo the learner *pulls updates into*; writing per-learner promotions there would leak what they study and conflict on every pull. The ledger is the learner's own accreted floor, and `sources-floor --domain <d>` is what a future lesson reads as its starting set. Contributing a source upstream is a deliberate PR, not a side effect of a lesson. (D-0025.)

At deep recalibrate, the two backlogs become a queryable list instead of a remembered ritual:

```bash
… sources-stale        # past the freshness horizon, most-used first
… sources-unverified   # the [from-training, verify] backlog
```

## Claim-level provenance

A tag on a sentence is a note to a future reader who never comes back. Carry the mapping in the artifact's frontmatter so it survives the session:

```yaml
sources_consulted:
  - url: https://…
    tag: verified
    accessed: 2026-07-30
    grounds: "leader cannot commit without a majority quorum"   # the specific claim
  - url: https://…
    tag: from-training
    grounds: "the 2026 default is distroless"                   # outstanding — verify
```

The ledger tracks the URL and the verdict; the claim-to-source mapping lives here, in the artifact. So `sources-unverified` gives you the outstanding *sources* and the artifacts' `grounds` lines tell you which *claims* each one is holding up — that pairing is what makes the backlog closable instead of a list of links with no idea what depends on them.
