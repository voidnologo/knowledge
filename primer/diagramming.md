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

**What blanking conceals depends on where the claim lives, and the two are not the same thing.** A blanked element's *label* is the obvious channel; for some forms the claim is carried by the drawing instead, and hiding the label there leaves the answer in plain sight. So each form defines what a blank actually removes:

| Form | Blanking | What it conceals |
|---|---|---|
| `sequence` | a message or note id | its **label**. The arrow, its direction, and its place in the order stay — you are asking *what this message is*, not whether one exists. |
| `state` | a transition or illegal-transition id | its **label**. The arc and its endpoints stay — you are asking *why this transition exists or is forbidden*. |
| `layers` | `"boundary"` | the boundary's **label**. Its position stays; if *where the boundary sits* is your claim, this form cannot blank it — restructure or ask in prose. |
| `quorum` | `"progress"` | which side is shaded **and** the "can make progress" caption — the whole claim, since the claim is the side. |
| `curve` | `"tail"` | the plotted **region** past the knee: the series is cut there and the area is drawn as unresolved. Position is the claim, so position is what goes. |
| `timeline` | a span id | the span's **position and extent**. The row renders as an unresolved field across the declared axis; the true offsets are never emitted. Requires a declared `axis` (see the `timeline` payload below). |

If you find yourself wanting to blank something the table says is not concealable, that is a signal the figure is the wrong form for the claim — not a signal to blank the nearest label and hope.

**A blank is only valid relative to what has already been said.** Re-check it against the conversation immediately before rendering: a spec authored ahead of its beat can have its answer given away by an intervening beat, at which point the `?` asks a question the learner has already been handed. Retarget onto something still unsaid, or drop the blank and show the figure whole. This is the figure-level version of the stale-sidecar problem, and pre-authored sets are where it bites.

**Both channels conceal identically, and that is a tested property**, not a convention: the terminal cannot spoil the page and the page cannot spoil the terminal. The regression that motivated writing it down is worth knowing, because it passed every check at the time — a blanked `timeline` span rendered its bar at true coordinates with a `?` where its label had been, so the learner read the answer off the geometry while `render` reported `faded-reveal integrity: passed`. That check verifies the reveal *text* is gated; it says nothing about a drawing that answers its own prediction. (D-0029.)
- **The caption must not answer the blank.** Nothing can check this for you — the caption is the one string shown above a blanked figure, so it is the remaining spoiler channel. "Leader isolated in a minority partition" is fine above a blanked ack; "Request path and trust boundary" is not fine above a blanked boundary label. Describe what the figure *is*, not what it *shows*.
- Ask for a *specific* prediction: "what message has to happen here for the commit to be safe?" beats "what goes here?".
- The `reveal` text is the answer *plus why* — one or two sentences. It is what the learner checks their prediction against, so it has to be falsifiable, not a restatement.

**The `invariant` is gated too, automatically.** For a blanked figure the invariant usually *is* the answer ("a leader that cannot reach a majority cannot advance the commit index" answers "what's missing here?"), so the generator moves it inside the gate alongside the reveal. Use the optional `predict` field for the line that shows *above* the figure — that's where the question goes. An unblanked figure shows its invariant normally.

The view page enforces the rest structurally: the reveal is hidden until the learner acts, and `primer_view.py validate` fails the page if the answer is reachable before the commit affordance. You cannot accidentally hand it over. **The blanked ASCII rendering honours the same blanks**, so the terminal can't spoil the page — and a `blank` id that matches nothing is a hard error in *both* channels, because a silent no-op there would hand over the answer.

One residual limit worth knowing: the reveal is in the page's DOM, so a browser's find-in-page expands closed `<details>`. This is inherent to a static local page. It's not a defence against a learner who wants the answer — it's a defence against *receiving* it without choosing to.

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
| `id` | yes | Unique within the lesson. `^[A-Za-z][A-Za-z0-9_-]{0,63}$` — it becomes a DOM id. |
| `type` | yes | One of `sequence` `state` `quorum` `layers` `curve` `timeline`. |
| `caption` | yes | One line, above the figure. Validator fails without it. |
| `invariant` | yes | The single claim the figure makes visible. Forces rule 1 on yourself. Gated when the figure is blanked. |
| `blank` | no | Element ids to blank in the faded variant. Omit only with reason. An id matching nothing is an error. |
| `reveal` | if `blank` | The answer plus why. Hidden until the learner commits. Rejected if nothing is blanked. |
| `predict` | no | The question shown above a blanked figure, in place of the gated invariant. |
| `spec` | yes | Type-specific payload, below. |

**Give every blankable element an `id`.** Messages, notes, transitions, illegal transitions, and spans are blankable *only* if they carry one, and the whole point is to blank the element carrying the invariant. Add ids as you author, not after.

**Labels have a budget: 34 characters.** Templates own geometry, so they also own the consequence — a longer label would be clipped by the viewBox and silently lost. The generator rejects it instead. If a label needs more room, it's usually two figures.

### `sequence`

```json
{
  "participants": [{"id": "L", "label": "Leader (term 4)"},
                   {"id": "F1", "label": "Follower"},
                   {"id": "F2", "label": "Follower (isolated)"}],
  "messages": [{"id": "m1", "from": "L", "to": "F1", "label": "AppendEntries"},
               {"id": "m2", "from": "F1", "to": "L", "label": "ack", "dashed": true},
               {"id": "m3", "from": "L", "to": "F2", "label": "AppendEntries", "lost": true}],
  "notes": [{"id": "n-timeout", "after": "m3", "over": "F2", "label": "timeout fires"}]
}
```

`dashed` for replies, `lost` for a message that doesn't arrive (drawn cut). Participants render left to right in array order — put the actor whose behaviour is the invariant on the left.

### `state`

```json
{
  "states": [{"id": "f", "label": "Follower", "initial": true},
             {"id": "c", "label": "Candidate"},
             {"id": "l", "label": "Leader"}],
  "transitions": [{"id": "t-timeout", "from": "f", "to": "c", "label": "election timeout"},
                  {"id": "t-elected", "from": "c", "to": "l", "label": "majority vote"}],
  "illegal": [{"id": "t-skip", "from": "f", "to": "l", "label": "never — no election"}]
}
```

`illegal` transitions render struck-through. They are usually the invariant — what the design *forbids* is more instructive than what it permits — so they are usually what you blank. Self-transitions (`from` == `to`) draw as a loop above the box.

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

Provide 5–9 points; they render as a polyline (no smoothing), so put points where the curve actually bends. At most 2 series — a third is rejected, not dropped. Annotate the knee — that's where the lesson is. If you're blanking, blank the region past the knee and ask the learner to predict the shape.

### `timeline`

```json
{
  "actors": [{"id": "req", "label": "request"}, {"id": "gc", "label": "GC pause"}],
  "spans": [{"id": "s-req", "actor": "req", "start": 0, "end": 40, "label": "p50 path"},
            {"id": "s-gc", "actor": "gc", "start": 25, "end": 70, "label": "stop-the-world"}],
  "axis": {"min": 0, "max": 120},
  "unit": "ms"
}
```

Overlap is the point. If nothing overlaps, this should have been a `sequence`.

`axis` is optional and **required whenever a span is blanked**. Without it the axis is derived as exactly the hull of the spans — which is precisely wide enough for the true answer and no wider, so the bounds hand over the position you were asking the learner to predict. At the limit it is total: a blanked span on a 0–2000 axis has nowhere to sit but on top of the other one, which *is* the prediction. Declare a range with room for the wrong answer as well as the right one, and the generator will reject a span that falls outside it.

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
- **Every declared input must be read by some formula.** A slider that moves and changes nothing is precisely the failure the contract exists to prevent.
- Formulas are **parsed as arithmetic**, not merely filtered for allowed characters: numbers, declared input ids, `+ - * / ( ) ,` and `min max abs sqrt exp log pow` with correct arity. A malformed expression is rejected rather than emitted, so no arbitrary JS reaches the page.
- **Input ids may not contain hyphens** — `a-b` is subtraction. Use `queue_depth`, not `queue-depth`. Output ids may contain hyphens.
- Slider bounds must be numbers and `max` must exceed `min`; `decimals` is 0–8.
- `predict` is required. An explorable without a prediction beat is a toy. The `invariant` is gated behind the same commit affordance as a blanked figure's reveal.
- Two inputs maximum. Three sliders is a parameter-fitting exercise, not a lesson.

## Rendering and validating

```bash
python3 ${CLAUDE_SKILL_DIR}/tools/primer_view.py templates          # list forms + spec schema
python3 ${CLAUDE_SKILL_DIR}/tools/primer_view.py render <artifact.md>   # write + validate <slug>.view.html
python3 ${CLAUDE_SKILL_DIR}/tools/primer_view.py render <artifact.md> --open   # …and open it
python3 ${CLAUDE_SKILL_DIR}/tools/primer_view.py render <artifact.md> --upto <fig-id>  # mid-lesson: stop at this beat
python3 ${CLAUDE_SKILL_DIR}/tools/primer_view.py render <artifact.md> --only <fig-id>  # …or just these (repeatable)
python3 ${CLAUDE_SKILL_DIR}/tools/primer_view.py ascii <artifact.md> --id <fig-id>   # terminal rendering
python3 ${CLAUDE_SKILL_DIR}/tools/primer_view.py validate <view.html>  # re-check an existing page
```

**Use `--upto` for any page-only figure delivered mid-lesson.** The page is per-file while `ascii --id` is per-figure, so a bare `render` at beat 2 also publishes beat 5's caption and `predict` line — and those are shown ungated by design, so the reveal gate is no defence. `--upto` is what lets every spec live in the sidecar from the start, which is what keeps `.STATE.md` a complete cross-machine checkpoint.

`render` validates before it reports success and exits non-zero with a specific message on failure. **Fix and re-run; never show the learner a page that failed validation.** The checks are: XML well-formedness, zero external requests, a caption on every figure, contract satisfaction, and faded-reveal integrity (the answer is not reachable before the learner commits).

`ascii` gives the in-terminal rendering for the forms that support it (`sequence`, `layers`, `quorum`, `timeline`) so the same single spec serves both the live conversation and the page. Author the spec once. `curve` and `state` say plainly that they render on the page only, and keep their caption in the message so the learner knows what they are being sent to.

The terminal renderings are **diagrams, not lists**: `sequence` draws real lifelines with the arrow between its two columns and the label to the right, and `timeline` positions spans on a shared axis. A form whose ASCII output would be rows and columns wearing arrows should be a table instead — the first version of the `sequence` renderer printed a participant header over a flat list of `from ──label──▶ to` rows, which promised lanes it never drew, and a learner spotted it immediately.
