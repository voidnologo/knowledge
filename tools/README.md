# tools

Helper scripts for primer. All are self-contained (no third-party installs).

| Script | What it does |
|--------|--------------|
| `install.sh` | Symlinks this repo into `~/.claude/skills/primer`. |
| `init-instance.sh` | Scaffolds the private data repo, writes the per-machine pointer (`~/.config/primer/config`), prints the git/gh commands to push it private. |
| `primer_state.py` | **Deterministic learner-model bookkeeping** — the parts of the feedback loop that are pure arithmetic over dates/counts (so the LLM doesn't do them in-context). |
| `test_primer_state.py` | Unit tests for `primer_state.py`. Run: `python3 tools/test_primer_state.py`. |
| `primer_view.py` | **Figure templates + the local view page** — renders a lesson artifact's figure specs into a self-contained HTML page, and validates it before the learner sees it. |
| `test_primer_view.py` | Unit tests for `primer_view.py`. Run: `python3 tools/test_primer_view.py`. |
| `primer_sources.py` | **The source ledger** — what has been vetted, what has gone stale, what still needs grounding. Makes the mandatory discovery pass cheaper the more it runs. |
| `test_primer_sources.py` | Unit tests for `primer_sources.py`. Run: `python3 tools/test_primer_sources.py`. |
| `primer_update.py` | **Self-update** — check for a newer engine, fast-forward it, and migrate the learner's instance (add state files a newer engine expects). |
| `test_primer_update.py` | Unit tests for `primer_update.py`. Run: `python3 tools/test_primer_update.py`. |
| `primer_eval.py` | **Sycophancy eval scorer** — pressure-resolved failure rates over the trap set in `evals/sycophancy/`. Tests a non-negotiable that used to be untested. |
| `test_primer_eval.py` | Unit tests for `primer_eval.py`. Run: `python3 tools/test_primer_eval.py`. |

## `primer_state.py`

Python 3.11+ stdlib only — runs on mac/linux/windows with nothing to install. It reads and rewrites the
learner's **markdown** state files (the source of truth; D-0018/D-0020), so state stays hand-editable and
git-syncs cleanly across machines. No database.

```
python3 tools/primer_state.py --data-dir "$DATA_DIR" <command>
```

Commands:

- `review-due [--limit N]` — list prompts due today (SM-2 schedule), weakest/oldest first.
- `review-grade --index <i> --quality again|hard|good|easy` — grade a due prompt and reschedule it.
- `review-add --domain D --question Q --answer A` — add a new prompt (initial schedule, due today).
- `review-history --correct N --total M [--note ...]` — record a review session's score.
- `markers-decay [--days N]` — drift stale `[high]` depth markers to `[med]` + flag reprobe (forgetting-aware).
- `recalibrate-check` — is a minor recalibrate due? (fires on 4+ misses or 8+ lessons since the last one). Counts only rows whose miss-type begins with a documented token, so annotation rows like `(mastery signal, not a miss)` don't inflate it; `MISS_TYPES` and the template's list are asserted equal by a test.
- `recalibrate-mark [--note ...]` — record that a minor recalibrate ran. Writes a positional marker into `calibration-log.md`; everything below the last marker is what the next check counts. Run it at the end of every minor recalibrate — without it, counting falls back to comparing dates, and a recalibrate at session start hides every miss logged later the same day.
- `hatch-log --domain D [--note ...]` — record a "just show me" escape-hatch use.
- `hatch-trend [--window N]` — escape-hatch rate per domain over the last N lessons. The hatch is right to offer; a rising rate is the dependence signal, and it was invisible until counted.

`--on YYYY-MM-DD` overrides "today" (for testing or back-dating). `--data-dir` overrides the path otherwise
read from `~/.config/primer/config`.

Scheduler: **SM-2** (SuperMemo-2) — chosen over FSRS for transparency and zero training data (D-0020).

## `primer_sync.py`

Python 3.11+ stdlib only. Commits and pushes the learner's private instance repo. **Runs
automatically at the end of every lesson** (`SKILL.md` lesson flow, final step) — it is part
of finishing a lesson, not something the learner asks for. The instance holds the only copy
of the artifact and of the learner model, so an uncommitted instance is an unrecoverable
loss one crash away.

```
python3 tools/primer_sync.py [--data-dir D] [--message M] [--no-push]
```

Three properties that matter more than the convenience:

- **Stages only `learner/` and `lessons/`.** A blanket `add -A` in someone's data repo would
  sweep up whatever else they are editing and commit it under a lesson's message.
- **Never rewrites history and never forces.** On a rejected push it rebases once — the
  remote commits are the same learner's work from another machine — and retries. If that
  fails it stops and says so. A data repo is exactly where a clobbering fix is unacceptable.
- **Fails loudly, and separately from the lesson.** Non-zero exit with a message naming what
  is and is not stored. The commit survives a failed push, so the work is never lost, only
  un-mirrored.

Applies to the **instance only**. The public core is never auto-pushed; engine changes go
through a branch and a PR.

## `primer_view.py`

Python 3.11+ stdlib only. Turns the figure specs embedded in a lesson artifact into
`<slug>.view.html` — one self-contained local page the learner opens by clicking a `file://` link.
The artifact stays the source of truth; the page is a derived build product and is regenerable.

```
python3 tools/primer_view.py <command>
```

Commands:

- `templates` — list the six figure forms and their full spec schema. Read this before authoring a spec.
- `render <artifact.md> [--open]` — write and validate `<stem>.view.html`; prints the `file://` URL.
- `render <artifact.md> --upto ID` / `--only ID` — render a subset. **Use `--upto` for any page-only figure delivered mid-lesson**: the page is per-file while `ascii --id` is per-figure, so a bare `render` at beat 2 also publishes beat 5's caption and `predict` line, and those are ungated by design. `--upto` is what lets every spec live in the sidecar from the start, keeping `.STATE.md` a complete cross-machine checkpoint.
- `validate <view.html>` — re-check an existing page.
- `ascii <artifact.md> [--id ID]` — terminal rendering, for the live conversation. Supports `sequence`, `layers`, `quorum`, `timeline`; `curve` and `state` report that they are page-only and keep their caption in the message.

Two design choices worth knowing:

**The model writes specs, not geometry.** Six parameterized templates (`sequence` `state` `quorum`
`layers` `curve` `timeline`) own layout, theming, and accessibility. Authoring SVG mid-lesson is slow
at the worst moment and is where malformed output comes from.

**The model writes formulas, not JavaScript.** An explorable declares a contract (inputs → outputs)
plus one restricted arithmetic formula per output; the wiring is generated. AI-generated interactives
measurably fail at state management, so the contract is made structurally true rather than trusted.

`render` validates **before writing**, and exits non-zero with the specific problem — the output path
is deterministic and the learner is told to click it, so a page that failed validation must never
exist there, nor destroy a valid earlier one. Six checks:

1. **comment integrity** — exactly one comment terminator (the manifest's). A spec string containing
   `-->` would otherwise close the manifest comment and expose the rest to the HTML parser.
2. **figure well-formedness** — each generated SVG parses as XML; a malformed figure renders blank.
3. **no external requests** — scanned per tag attribute (so `srcset`, `poster`, `data`, and
   `http-equiv=refresh` are caught), plus `@import`/remote `url()` in styles and `fetch`/`eval`/
   `XMLHttpRequest` in scripts, plus any inline `on*` handler. A `Content-Security-Policy` meta tag
   backs it at runtime, because a regex over generated markup can be outrun and a browser policy
   can't. `data:` and `file:` are local and permitted.
4. **caption coverage** — every figure has a caption, and it reached the document.
5. **contract satisfaction** — every declared input has a control and a listener; every declared
   output has a readout and an assignment.
6. **faded-reveal integrity** — a blanked figure's answer sits inside that figure's own closed
   `<details>` and nowhere else, checked structurally per figure.

**Never show the learner a page that failed validation** — fix the spec and re-run.

Spec strings are model-authored, so they are treated as untrusted: ids are constrained to a safe
character set, slider bounds are coerced to numbers, and formulas are *parsed as arithmetic* rather
than filtered for allowed characters (a legal token sequence can still be illegal JavaScript —
`1/*2` opens a comment, a lone `(` kills the script block).

Blanks are honoured in the ASCII rendering too, and an unknown `blank` id is a hard error there as
well — that channel is what the learner sees *during* the prediction beat, before the page exists.

See `primer/diagramming.md` for the spec format and how to choose a form.

## `primer_sources.py`

Python 3.11+ stdlib only. Owns the deterministic half of the source-discovery pass
(`primer/research-protocol.md`), against `$DATA_DIR/learner/source-ledger.md`.

```
python3 tools/primer_sources.py --data-dir "$DATA_DIR" <command>
```

Commands:

- `sources-add --url U --domain D [--tag verified|from-training] [--verdict cite|caveat|dropped] --why "..." [--floor]` — record a vetted source. Idempotent per URL: re-adding refreshes `checked`, bumps `used`, keeps the original `seen`.
- `sources-check --url U [--days N]` — already vetted? what verdict? still fresh? **Ask this before sweeping.**
- `sources-stale [--days N]` — entries past the freshness horizon (default 90d, matching the canon's ~3-month rule), most-used first.
- `sources-unverified` — the `[from-training, verify]` backlog.
- `sources-floor [--domain D]` — the learner's accreted floor: a lesson's starting set.
- `sources-promote --url U` — mark a source as floor.
- `sweep-record --domain D [--note ...]` / `sweep-check --domain D [--days N]` — when the domain last had a full sweep, and whether a narrow top-up will do.

`--on YYYY-MM-DD` overrides "today". `--data-dir` overrides the path otherwise read from
`~/.config/primer/config`.

**Why it exists.** Currency is primer's top non-negotiable and was the only one with no code
behind it: the mandatory per-lesson pass was pure prose, so it got reconstructed from scratch
every session with hand-computed dates and no memory of prior verdicts. The ledger inverts the
economics — a source vetted inside the horizon is reused, not re-swept — which is what makes
"every lesson runs the pass" sustainable rather than something that quietly degrades.

**Promotion writes here, not to the public core.** `primer/source-canon.md` ships in a repo the
learner pulls updates into, so a per-learner promotion there would leak what they study and
conflict on every pull. The ledger is the learner's own floor (D-0025).

Values come from web pages and model output, so they are treated as untrusted: the file is
pipe-delimited, and a `|`, newline, non-`http(s)`/`file` scheme, or over-long field is rejected
with an actionable message rather than escaped into a line that would corrupt the ledger.

## `primer_eval.py`

Python 3.11+ stdlib only. Scores the pedagogical-sycophancy eval against the trap set in
`evals/sycophancy/traps.json`.

```
python3 tools/primer_eval.py list [--pressure MODE] [--domain D]   # traps to run
python3 tools/primer_eval.py template > results.json               # blank results file
python3 tools/primer_eval.py score results.json                    # pressure-resolved rates
```

Division of labour: *running* a trap needs a live tutor and a judgement call, so an agent or
a human does that and records `held: true|false`. *Scoring* is arithmetic, so it runs here.

Two properties worth knowing. **An unrun trap is refused, not counted as a pass** — `held:
null` raises, because scoring it as a pass would understate the very rate the eval exists to
measure, and coverage gaps are printed by name. And **it never collapses to one number**:
rates come out by pressure mode, by learner confidence, and by domain × mode, because the
finding that motivates the eval is that aggregates hide where the failure lives (two models
with the same ~14% overall failed on opposite modes; single cells spiked past 30%).

Why this eval and not another: "hold correct positions under pushback" is a non-negotiable
in `GOALS.md`, and the measured weak mode for Claude models — context-switch frame attacks,
worst at *low* learner confidence — is exactly what primer's senior-peer register invites and
what its low-confidence markers describe. See `primer/anti-patterns.md` #1 for the
counter-moves and `primer/examiner-protocol.md` for the related separation of judgment.
