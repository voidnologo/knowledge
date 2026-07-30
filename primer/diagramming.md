# Diagramming — choosing, composing, and specifying figures

Read this when a lesson is about to carry a figure. `primer/visuals.md` is the short conventions file; this is the working reference: which form to reach for, how to compose it, and the exact spec format `tools/primer_view.py` consumes.

**You do not author SVG.** You write a figure *spec* — a small JSON block — and the template library renders it. Geometry, layout, theming, and accessibility are the template's job. Labels, values, and the invariant are yours.

## Contents

- Why a figure at all — and when not
- Choosing the form (selection table)
- The three composition rules
- The faded diagram (predict before reveal)
- Figure spec format — the six templates
- Explorables — spec format and the interaction contract
- Rendering and validating

---

## Why a figure at all — and when not

Text paired with diagrams is one of the largest and most consistent effects in the multimedia-learning literature — it holds for factual, inferential, *and* transfer outcomes. That is the reason figures are first-class here.

The same literature puts **removing seductive detail** among the largest effects measured. A figure that doesn't carry an invariant is not neutral; it costs the learner working memory and returns nothing. So the bar is not "would a picture be nice here" but:

> **Can I state, in one sentence, the invariant this figure makes visible — and is that sentence load-bearing for the lesson?**

If not, don't draw it. Specifically, do not draw:

- **Data that is rows and columns.** Use a table (this rule predates the visual layer and still holds).
- **A restatement of the prose.** If the figure and the paragraph make the same claim the same way, cut one.
- **Anything decorative.** Icons, mascots, gradients, "architecture-diagram-looking" boxes that carry no claim.
- **More than one claim.** Two invariants is two figures. A figure needing two captions is the tell.

## Choosing the form

| Form | Use it for | The invariant it makes visible | Reach for it when |
|---|---|---|---|
| `sequence` | Temporal ordering between participants | *What happens in which order, and what can interleave* | Protocol rounds, request flows, handshakes, "who waits on whom" |
| `state` | A lifecycle and its legal transitions | *Which transitions exist — and which the design forbids* | Replication state, leader/follower, connection lifecycle, saga status |
| `quorum` | A node set split by a boundary | *Which side can make progress* | Partitions, majority/minority, split-brain, replica placement |
| `layers` | A path through stacked components | *Where a boundary sits and what crosses it* | Request path, trust boundary, cache tiers, storage stack |
| `curve` | One input against one or two outputs | *The shape of the relationship, especially where it goes non-linear* | Utilization vs latency, batch size vs throughput, retry rate vs collapse |
| `timeline` | Concurrent actors over a shared axis | *What overlaps, and for how long* | Lock hold windows, GC pauses vs requests, deploy overlap, clock skew |
| **table** | Rows and columns | *Comparison across fixed axes* | Tradeoffs — always a table, never a diagram |
| **prose** | Everything else | — | The default. A figure is the exception you justify. |

Two notes on picking:

- **`curve` is under-used and carries the most weight in systems lessons.** Most "why does this fall over" invariants are the shape of a curve near its asymptote, and prose describes that badly.
- **If you're torn between `sequence` and `timeline`:** sequence answers *what order*, timeline answers *what overlaps*. If the lesson's invariant is about concurrency, it's a timeline.

## The three composition rules

**1. Label in place, not in a legend.** A legend forces the learner to hold a mapping in working memory while reading the figure — the split-attention cost. Put the label on the element. The templates do this by default; don't fight them by using bare ids as labels.

**2. Seven elements, then split.** Past roughly seven nodes/participants/states, the figure stops being read and starts being scanned. Split it into two figures with two invariants, or abstract a group into one labeled element.

**3. Fade figure density with depth, exactly as worked examples fade.** The expertise-reversal evidence applies to figures too: a fully-annotated diagram that helps a novice is redundant load for someone whose depth marker says they've built this. For a high-confidence marker in the domain, drop the annotations and keep the structure — or skip the figure and go straight to the `curve` that carries the tradeoff. When the markers are ambiguous, under-annotate; the learner can open the view page and ask.

## The faded diagram (predict before reveal)

**This is the default, not an option.** The measured effect for *learner-generated* representations is g ≈ 0.69, and it doesn't depend on the learner drawing on a canvas — it depends on them generating rather than receiving. A figure handed over complete is a figure received.

So: blank the element that carries the invariant, ask the learner to fill it, then reveal.

- Blank **the causal step**, not a cosmetic detail. In a sequence, blank the message whose absence breaks safety. In a `curve`, blank the region past the knee. In a `state` diagram, blank the transition the design forbids.
- Blank **exactly one thing** (occasionally two if they're the same claim). Blanking three turns a prediction into a guessing game.
- Ask for a *specific* prediction: "what message has to happen here for the commit to be safe?" beats "what goes here?".
- The `reveal` text is the answer *plus why* — one or two sentences. It is what the learner checks their prediction against, so it has to be falsifiable, not a restatement.

The view page enforces this structurally: the reveal is hidden until the learner acts, and `primer_view.py validate` fails the page if the answer is visible before the commit affordance. You cannot accidentally hand it over.

For a learner whose profile shows low productive-struggle tolerance, still emit the blank — but say the answer immediately after they engage, rather than waiting them out. Same as the `just show me` rule in `lesson-protocol.md`.

## Figure spec format

Figure specs live in the lesson artifact as HTML comment blocks. They are invisible in rendered markdown, greppable, hand-editable, and stdlib-parseable — so the artifact stays the single source of truth and the page is always regenerable from it.

```
<!--primer-figure
{
  "id": "raft-minority-partition",
  "type": "sequence",
  "caption": "Raft replication with the leader isolated in a minority partition.",
  "invariant": "A leader that cannot reach a majority cannot advance the commit index.",
  "blank": ["m3"],
  "reveal": "The majority-side ack. Without acks from a majority, the leader holds the entry uncommitted — safety is preserved by refusing to commit, not by detecting the partition.",
  "spec": { }
}
-->
```

Common fields, every type:

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Slug, unique within the lesson. Used for the page anchor. |
| `type` | yes | One of `sequence` `state` `quorum` `layers` `curve` `timeline`. |
| `caption` | yes | One line, above the figure. Validator fails without it. |
| `invariant` | yes | The single claim the figure makes visible. Forces rule 1 on yourself. |
| `blank` | no | Element ids to blank in the faded variant. Omit only with reason. |
| `reveal` | if `blank` | The answer plus why. Hidden until the learner commits. |
| `spec` | yes | Type-specific payload, below. |

### `sequence`

```json
{
  "participants": [{"id": "L", "label": "Leader (term 4)"},
                   {"id": "F1", "label": "Follower"},
                   {"id": "F2", "label": "Follower (isolated)"}],
  "messages": [{"id": "m1", "from": "L", "to": "F1", "label": "AppendEntries"},
               {"id": "m2", "from": "F1", "to": "L", "label": "ack", "dashed": true},
               {"id": "m3", "from": "L", "to": "F2", "label": "AppendEntries", "lost": true}],
  "notes": [{"after": "m3", "over": "F2", "label": "election timeout fires"}]
}
```

`dashed` for replies, `lost` for a message that doesn't arrive (drawn cut). Participants render left to right in array order — put the actor whose behaviour is the invariant on the left.

### `state`

```json
{
  "states": [{"id": "f", "label": "Follower", "initial": true},
             {"id": "c", "label": "Candidate"},
             {"id": "l", "label": "Leader"}],
  "transitions": [{"from": "f", "to": "c", "label": "election timeout"},
                  {"from": "c", "to": "l", "label": "majority vote"}],
  "illegal": [{"from": "f", "to": "l", "label": "never — no election"}]
}
```

`illegal` transitions render struck-through. They are usually the invariant: what the design *forbids* is more instructive than what it permits.

### `quorum`

```json
{
  "nodes": [{"id": "a", "label": "n1", "leader": true}, {"id": "b", "label": "n2"},
            {"id": "c", "label": "n3"}, {"id": "d", "label": "n4"}, {"id": "e", "label": "n5"}],
  "partition": [["a", "b"], ["c", "d", "e"]],
  "progress": "right"
}
```

`partition` is the split (2+ groups). `progress` names which side can make progress (`left`/`right`/`none`) and shades it. The leader deliberately sits on the minority side in most useful versions of this figure.

### `layers`

```json
{
  "layers": [{"label": "Client"}, {"label": "Edge / TLS termination"},
             {"label": "API", "detail": "authn happens here"}, {"label": "Postgres"}],
  "boundary_after": 1,
  "boundary_label": "trust boundary"
}
```

Top-to-bottom in array order. `boundary_after` draws the line below that index — the boundary is usually the invariant.

### `curve`

```json
{
  "x": {"label": "utilization ρ", "min": 0, "max": 1},
  "y": {"label": "latency (× service time)", "min": 0, "max": 20},
  "series": [{"label": "M/M/1 queueing", "points": [[0,1],[0.5,2],[0.8,5],[0.9,10],[0.95,20]]}],
  "annotate": [{"x": 0.8, "label": "the knee"}]
}
```

Provide 5–9 points; the template smooths. Annotate the knee — that's where the lesson is. If you're blanking, blank the region past the knee and ask the learner to predict the shape.

### `timeline`

```json
{
  "actors": [{"id": "req", "label": "request"}, {"id": "gc", "label": "GC pause"}],
  "spans": [{"actor": "req", "start": 0, "end": 40, "label": "p50 path"},
            {"actor": "gc", "start": 25, "end": 70, "label": "stop-the-world"}],
  "unit": "ms"
}
```

Overlap is the point. If nothing overlaps, this should have been a `sequence`.

## Explorables — spec format and the interaction contract

Interactivity is **not** an upgrade over a static figure. The evidence is inconsistent — smaller effects on factual outcomes, larger on inferential/transfer — and head-to-head comparisons against static graphics often show no difference. Separately, AI-generated interactives measurably fail at state management: broken interaction chains, outputs that don't track inputs.

So an explorable earns its place on one test: **is there a parameter whose variation *is* the insight?** Utilization, quorum size, retry rate, batch size, cache hit rate — yes. Anything you'd be tempted to make draggable "for engagement" — no.

**You do not write the JavaScript.** You declare a contract and a formula per output; the generator compiles the wiring. This is deliberate: hand-written event handlers are exactly where the state-management failures live, and generated wiring makes the contract structurally true rather than hopefully true.

```
<!--primer-explorable
{
  "id": "utilization-latency",
  "caption": "Queueing latency as utilization approaches 1.",
  "invariant": "Latency is not linear in load — it diverges as ρ → 1, so headroom is a latency decision.",
  "predict": "Before you touch the slider: at what utilization does latency double? Sketch the shape.",
  "contract": {
    "inputs":  [{"id": "rho", "label": "utilization ρ", "min": 0.05, "max": 0.95, "step": 0.01, "value": 0.5}],
    "outputs": [{"id": "wait", "label": "queue wait (× service time)", "decimals": 2},
                {"id": "headroom", "label": "headroom to ρ=0.95", "decimals": 2}]
  },
  "formulas": {"wait": "rho / (1 - rho)", "headroom": "0.95 - rho"}
}
-->
```

Rules the generator enforces:

- Every `formulas` key must be a declared output id; every declared output must have a formula. No orphans in either direction.
- Formulas are restricted arithmetic over input ids: `+ - * / ( )`, numbers, and `min max abs sqrt exp log pow`. Anything else fails validation. No arbitrary JS reaches the page.
- `predict` is required. An explorable without a prediction beat is a toy.
- Two inputs maximum. Three sliders is a parameter-fitting exercise, not a lesson.

## Rendering and validating

```bash
python3 ${CLAUDE_SKILL_DIR}/tools/primer_view.py templates          # list forms + spec schema
python3 ${CLAUDE_SKILL_DIR}/tools/primer_view.py render <artifact.md>   # write + validate <slug>.view.html
python3 ${CLAUDE_SKILL_DIR}/tools/primer_view.py render <artifact.md> --open   # …and open it
python3 ${CLAUDE_SKILL_DIR}/tools/primer_view.py ascii <artifact.md> --id <fig-id>   # terminal rendering
python3 ${CLAUDE_SKILL_DIR}/tools/primer_view.py validate <view.html>  # re-check an existing page
```

`render` validates before it reports success and exits non-zero with a specific message on failure. **Fix and re-run; never show the learner a page that failed validation.** The checks are: XML well-formedness, zero external requests, a caption on every figure, contract satisfaction, and faded-reveal integrity (the answer is not reachable before the learner commits).

`ascii` gives the in-terminal rendering for the forms that support it (`sequence`, `layers`, `quorum`, `timeline`) so the same single spec serves both the live conversation and the page. Author the spec once.
