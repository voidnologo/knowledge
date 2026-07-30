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
- `recalibrate-check` — is a minor recalibrate due? (fires on 4+ misses or 8+ lessons since the last one).

`--on YYYY-MM-DD` overrides "today" (for testing or back-dating). `--data-dir` overrides the path otherwise
read from `~/.config/primer/config`.

Scheduler: **SM-2** (SuperMemo-2) — chosen over FSRS for transparency and zero training data (D-0020).

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
- `validate <view.html>` — re-check an existing page.
- `ascii <artifact.md> [--id ID]` — terminal rendering, for the live conversation.

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
