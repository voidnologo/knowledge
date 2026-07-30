# Visuals — channels and conventions

Lessons are text-native, but visuals are first-class. Read this to know *where* a visual goes and what the rules are. For *which* form to choose, how to compose it, and the spec format, read `primer/diagramming.md`.

## Three channels, one source

A figure is authored **once**, as a spec in the lesson artifact (`<!--primer-figure ... -->`, see `diagramming.md`). It renders to three places:

| Channel | What it's for | How |
|---|---|---|
| **Terminal (ASCII)** | The live conversation — inline, where nothing else renders | `primer_view.py ascii --id <fig>`, or hand-drawn box-drawing for a quick sketch |
| **Artifact (markdown)** | Reading the lesson later, on GitHub or in an editor | Mermaid block, rendered natively by GitHub |
| **View page (HTML)** | The rich version — full-size SVG, the faded reveal, explorables | `primer_view.py render <artifact.md>`; learner clicks a `file://` link |

Never author the same figure twice by hand. If it needs to appear in two channels, it's one spec and two renderings.

## The view page

`$DATA_DIR/lessons/<domain>/<YYYY-MM-DD>-<slug>.view.html` — one self-contained file the learner opens locally by clicking a link the Primer prints in the terminal.

Non-negotiables it inherits:

- **Zero external requests.** Inline CSS, inline JS, inline SVG, `data:` URIs only. No CDN, no web fonts, no remote images, no analytics. It works offline, and opening it tells nobody. The validator enforces this — it is not a promise.
- **Private instance only.** The page lives beside the lesson, inside the learner's private data repo. It is never written to the public core, and it is never published. (Publishing a *sanitized* view is the same deliberate derivation step reserved for lessons themselves — opt-in, not default.)
- **Derived, not source.** The page is regenerated from the artifact, so markdown stays the source of truth. It's gitignored in the instance; the artifact syncs and the page rebuilds. (Contrast `.STATE.md`, which *is* checkpoint state and must sync.)
- **Theme-aware, and never color-only.** Light and dark both work; anything encoded in color is also encoded in shape, position, or label.

## ASCII, for the live session

Use Unicode box-drawing (`┌─┐│└┘├┤┬┴┼`, arrows `→ ← ↑ ↓`) — renders in any modern terminal and copies cleanly into markdown.

```
   ┌──────────┐  AppendEntries  ┌──────────┐
   │  Leader  │ ──────────────▶ │ Follower │
   └──────────┘  ◀── ack ────── └──────────┘
        │
        │ replicates to majority
        ▼
   commit index advances
```

Keep inline ASCII small — four or five elements. Anything bigger belongs on the view page; say so and hand over the link.

## Tables for tradeoffs

Tradeoff comparisons are tables, always. They render everywhere and grep cleanly. This is not a fallback; a table is the *right* form for rows-and-columns data, and drawing it instead is a downgrade.

| Pattern | Operational cost | Latency | Consistency | When to reach for it |
|---|---|---|---|---|
| Outbox | Low | Low | Eventual | Default. Use this first. |
| CDC | Medium | Low | Eventual | When you can't change app code. |
| Saga (orchestrated) | High | High | Eventual | True cross-service workflows. |

## Anti-patterns

- **Drawing what could be a table.** Rows and columns → table.
- **A figure without a caption, or without a stated invariant.** Every figure makes exactly one claim, and says it.
- **A decorative figure.** Removing seductive detail is one of the largest measured effects in multimedia learning — a figure that carries no invariant is a net cost, not a neutral addition.
- **Handing over a complete diagram.** The default is the faded variant: blank the causal step, ask for a prediction, then reveal. Learner-generated beats learner-shown (`diagramming.md`).
- **Describing a figure in prose instead of rendering it.** "Picture 40 finishing at 2s, 40 at 4s, 20 at 6s" is not the figure; it is the figure's absence with extra words. Render it (`primer_view.py ascii`) at the point the prose reaches it — see the four-step figure beat in `primer/lesson-protocol.md`.
- **Authoring the spec at Recap.** A figure whose spec is first written while assembling the artifact arrives after the reasoning it was meant to support, when the learner already has the answer. The spec's mid-lesson home is the `.STATE.md` sidecar for exactly this reason.
- **An explorable for engagement.** Interactivity earns its place only when a parameter's variation *is* the insight. Otherwise it's a toy that costs attention.
- **Decorative emoji.** Content-bearing marks (`✓ ✗ →`) are fine; smileys are not.
- **Generated raster images.** Still out of scope, and not for lack of capability: a diagram spec is inspectable, diffable, correctable, and regenerable, and a PNG is none of those. If a concept genuinely needs a photograph or a rendered artwork, link an authoritative external source instead.
