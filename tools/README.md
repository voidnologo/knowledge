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

`render` validates before reporting success and exits non-zero with the specific problem. Five checks:
figure well-formedness (each SVG parses as XML), no external requests (nothing on the page phones
home), caption coverage, contract satisfaction (every declared input is listened to, every declared
output is written), and faded-reveal integrity (a blanked figure's answer is unreachable until the
learner commits). **Never show the learner a page that failed validation** — fix the spec and re-run.

Blanks are honoured in the ASCII rendering too, so the terminal can't spoil what the page gates.

See `primer/diagramming.md` for the spec format and how to choose a form.
