# primer

A personal, Primer-style learning system — an adaptive tutor that runs interactive lessons calibrated to *you* and gets sharper the more you use it.

> **New here?** [Launch the 10-minute pitch deck](https://voidnologo.com/primer/pitch/primer-pitch.html) — it walks through the motivation, what it is, and how it works. Add [`?print-pdf`](https://voidnologo.com/primer/pitch/primer-pitch.html?print-pdf) to export a PDF. Source lives at `docs/pitch/primer-pitch.html`.

## What's a "Primer"?

In Neal Stephenson's *The Diamond Age*, the *Young Lady's Illustrated Primer* is the book you wish you'd had as a kid. It starts with a grandfather who wants something *more* for his granddaughter — who sees the makings of someone remarkable in her and sets out to give her every chance to become it. So he commissions a marvel, a book made possible only by technology just dreamed into being: it talks back, notices who's reading it, and reshapes itself to fit them. A copy finds its way to Nell, a young girl it was never made for — and it works just as beautifully for her. That's the heart of it: a book like this could do this for *anyone*.

It meets her exactly where she is, and grows right along with her. It pays attention to what lights her up — the questions she keeps asking, the things she's already quick at — and teaches through a fairy tale she can step straight into: Princess Nell, adventuring through a world of puzzles, locked doors, and clever escapes. Reading first, then logic, then honest-to-goodness computation (a Turing machine smuggled in as an enchanted castle), then how to hold her own, and finally the best part of all — how to *think* for herself. Never a lecture. Never pitched over her head or beneath it. Always just a step past what she can already do, so there's always something exciting to reach for.

Year by year, the Primer helps an ordinary kid grow into one of the most capable, quick-witted people in her world. The magic was never really the nanotech. It's that the Primer is a *relationship*, not a syllabus — patient, genuinely curious about its reader, and built around exactly one person.

That's the north star, pointed at a smaller but stubbornly real problem: staying sharp in a field that reinvents itself every eighteen months. This won't spin you a fairy tale — but the part that *is* reproducible, it chases hard. A tutor that genuinely knows you: where you actually are, what you're reaching for, the way you like to be talked to. One that teaches when *you* tug on a thread, not when a curriculum decides it's time. And one whose lessons are yours to keep — they live in your own repo, they outlast the session, and the picture it holds of you gets a little truer, and a little more capable, every time you show up.

## What this is

Implemented as a Claude Code skill, primer runs narrative, calibrated lessons against a persistent, evidence-backed learner profile and captures every session as a durable markdown artifact. It works for any learner and any goal — system design, MCP and AI-assisted development, picking up a new language, distributed systems. The intake interview discovers your ability and decomposes *your* goal; it doesn't assume a curriculum.

## Class and instance

primer is split in two:

- **This repo — the public core ("the class").** The engine: the skill, the protocols (`primer/`), and the instance templates. It holds **zero** personal data — including no lessons. Clone it and pull updates as the community improves it.
- **Your private data repo ("the instance").** Your profile, depth markers, calibration log, and lessons. Private, and git-synced across your machines. Created from the core by `init`.

This is why your data can be rich (real stack, real goals) without ever leaking: it lives only in your private repo. **Lessons are personal too** — they're calibrated to you, so they live in the private instance alongside the profile. Publishing a lesson is a deliberate, separate step (a derivation skill that turns a personal lesson into a sanitized public artifact is planned), never the default.

## Install & first run

```bash
git clone <this repo>
cd primer
./tools/install.sh          # symlinks the repo as the `primer` skill
```

Then, in any Claude Code session:

```
/primer init                # one-time: scaffold your private data repo + intake interview
```

`init` walks you through `tools/init-instance.sh` (scaffolds your data repo locally and prints the `git`/`gh` commands to push it private), then runs the cold-start interview to build your first profile. After that:

```
/primer <topic>             # run a lesson
/primer index               # show your topic map
```

### Second machine

Clone your private data repo, then point that machine at it:

```bash
./tools/init-instance.sh <path-to-your-data-repo-clone>
```

It detects the existing instance and only writes that machine's pointer (`~/.config/primer/config`).

### Privacy hardening (recommended)

primer never auto-reads a work codebase — but that is an instruction the model follows, not a wall. For
defense in depth, add a deny rule to your **global** Claude Code settings (`~/.claude/settings.json`) so the
tools physically can't read proprietary paths during a session. Adjust the paths to your machine:

```jsonc
{
  "permissions": {
    "deny": [
      "Read(//Users/you/Work/**)",
      "Edit(//Users/you/Work/**)",
      "Bash(cat //Users/you/Work/**)"
    ]
  }
}
```

This is belt-and-suspenders on top of the skill's own rule (the engine still redirects work-specific
scenarios to canonical analogs). Stack-aware framing comes from your profile and what you say in the
conversation, never from reading the code.

## Subcommands

- `/primer init` — first-time setup: intake interview, builds your profile
- `/primer <topic>` — start an interactive lesson
- `/primer next` — suggest 2–3 best-next lessons
- `/primer recalibrate` — deep profile review (the minor one runs automatically every 5 lessons)
- `/primer review` — interleaved spaced-retrieval warm-up from prior lessons
- `/primer resume` — pick up an in-progress lesson
- `/primer view [lesson]` — open a lesson's visual page (figures, faded reveals, explorables)
- `/primer index` — show topic-index tree with status
- `/primer profile` — show or update your profile
- `/primer suggest <goal>` — propose a multi-lesson track for a stated goal

## Design principles

The full set and the engineering rationale live in [`docs/engineering/GOALS.md`](docs/engineering/GOALS.md) and [`docs/engineering/DECISIONS.md`](docs/engineering/DECISIONS.md). The most load-bearing:

- **Personal, calibrated, evidence-backed.** Depth markers carry confidence + evidence; the system knows what it has *seen* you do vs. what it *assumed*. Intake discovers ability and goal; the feedback cycle keeps the profile true.
- **Senior peer, not teacher.** Lessons read like a senior engineer talking to a colleague (register is calibrated per learner). No motivational fluff.
- **Productive struggle over fluent answers.** Every lesson forces prediction or critique before the explanation lands. Figures work the same way: you get the diagram with the causal step blanked, and the answer stays behind a gate until you've committed to a prediction.
- **Currency is non-negotiable.** The canon (`primer/source-canon.md`) is a *vetted floor*, not a ceiling — every lesson searches for current sources beyond it; a stale-list is the guardrail.
- **Private by architecture, never proprietary.** All personal data — profile *and* lessons — lives only in your private instance; the skill never auto-reads a work codebase. Publishing a lesson is a deliberate future derivation step, not a default.

## Developing primer

Engineering happens against the north star in [`docs/engineering/`](docs/engineering/) using the `session-start` / `session-end` skills, which track the *why* (decisions, tradeoffs) alongside git's *what*. See [`REQUIREMENTS.md`](REQUIREMENTS.md) for the original design contract (historical; the living design record is now `docs/engineering/` + `primer/`).

## Contributing

The public core is the reusable part. Other learners clone it and bring their own private instance — fork or PR improvements to the engine; never commit personal data here.

## License

MIT — see [`LICENSE`](LICENSE).
