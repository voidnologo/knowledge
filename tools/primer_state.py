#!/usr/bin/env python3
"""primer_state — deterministic bookkeeping for the primer learner model.

Why this exists: the feedback loop (primer/feedback-protocol.md) has mechanical
parts — spaced-repetition scheduling, confidence decay over time, and the
recalibration trigger — that are pure arithmetic over dates and counts. Doing
that in-context with the LLM is token-expensive and unreliable (models miscount
and mis-date). This module does it as code instead, and the skill calls it.

Source of truth stays the learner's markdown (so it git-syncs cleanly across
machines and stays hand-editable — DECISIONS D-0018/D-0020); this script reads
and rewrites those files deterministically. No database: at one-learner scale
parsing markdown is instant, and a binary SQLite file would break the
cross-machine git sync the private instance depends on.

Stdlib only — runs on any Python 3.11+ (mac/linux/windows) with nothing to install.
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

# --- SM-2 spaced-repetition constants -------------------------------------
# SuperMemo-2: the lightweight, transparent scheduler chosen over FSRS (D-0020)
# — few parameters, no training data needed, and at this scale the *habit*
# matters more than squeezing optimal intervals.
EF_DEFAULT = 2.5
EF_MIN = 1.3
FIRST_INTERVAL = 1   # days, after the first successful recall
SECOND_INTERVAL = 6  # days, after the second

# Quality scale (0–5) mapped from the grade the Primer assigns in conversation.
QUALITY = {"again": 1, "fail": 1, "hard": 3, "good": 4, "easy": 5}
PASS_THRESHOLD = 3  # quality < this is a lapse: reset reps and interval

# Confidence decay: a [high] marker untouched this long drifts toward [med] and
# is flagged for reprobe (forgetting-aware; feedback-protocol.md).
DECAY_THRESHOLD_DAYS = 35

# Evidence-triggered minor recalibrate (D-0017): fire on either threshold.
RECAL_MISS_THRESHOLD = 4
RECAL_LESSON_CAP = 8


# --- SM-2 scheduler --------------------------------------------------------
@dataclass(frozen=True)
class ReviewState:
    reps: int
    interval: int
    ef: float
    due: date


def sm2(reps: int, interval: int, ef: float, quality: int, today: date) -> ReviewState:
    """Advance one item's schedule by SM-2.

    A lapse (quality < PASS_THRESHOLD) resets the item to a 1-day interval;
    a success grows the interval by the ease factor.
    """
    ef = _adjust_ef(ef, quality)
    if quality < PASS_THRESHOLD:
        return ReviewState(0, FIRST_INTERVAL, ef, today + timedelta(days=FIRST_INTERVAL))
    new_interval = _next_interval(reps, interval, ef)
    return ReviewState(reps + 1, new_interval, ef, today + timedelta(days=new_interval))


def _adjust_ef(ef: float, quality: int) -> float:
    # Standard SM-2 ease update, clamped to a sane floor so hard items don't
    # collapse to daily forever.
    adjusted = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    return max(EF_MIN, round(adjusted, 2))


def _next_interval(reps: int, interval: int, ef: float) -> int:
    if reps == 0:
        return FIRST_INTERVAL
    if reps == 1:
        return SECOND_INTERVAL
    return max(1, round(interval * ef))


def quality_from_label(label: str) -> int:
    """Map a grade label ('again|hard|good|easy' or '0'–'5') to an SM-2 quality."""
    key = label.strip().lower()
    if key in QUALITY:
        return QUALITY[key]
    if key.isdigit() and 0 <= int(key) <= 5:
        return int(key)
    raise ValueError(f"unknown quality '{label}'; use {sorted(QUALITY)} or 0–5")


# --- Review-queue prompts --------------------------------------------------
PROMPT_RE = re.compile(
    r"^- due:(?P<due>\d{4}-\d{2}-\d{2}) \| int:(?P<int>\d+) \| ef:(?P<ef>[\d.]+) \| "
    r"reps:(?P<reps>\d+) \| (?P<domain>[^|]+?) \| Q:: (?P<q>.*?) \| A:: (?P<a>.*)$"
)


@dataclass(frozen=True)
class Prompt:
    due: date
    interval: int
    ef: float
    reps: int
    domain: str
    question: str
    answer: str


def parse_prompt(line: str) -> Prompt | None:
    m = PROMPT_RE.match(line.strip())
    if not m:
        return None
    return Prompt(
        due=date.fromisoformat(m["due"]),
        interval=int(m["int"]),
        ef=float(m["ef"]),
        reps=int(m["reps"]),
        domain=m["domain"].strip(),
        question=m["q"].strip(),
        answer=m["a"].strip(),
    )


def format_prompt(p: Prompt) -> str:
    return (
        f"- due:{p.due.isoformat()} | int:{p.interval} | ef:{p.ef:.2f} | "
        f"reps:{p.reps} | {p.domain} | Q:: {p.question} | A:: {p.answer}"
    )


def new_prompt(domain: str, question: str, answer: str, today: date) -> Prompt:
    # Freshly added: due at the next review (today), unseen.
    return Prompt(today, 0, EF_DEFAULT, 0, domain, question, answer)


def graded(p: Prompt, quality: int, today: date) -> Prompt:
    s = sm2(p.reps, p.interval, p.ef, quality, today)
    return Prompt(s.due, s.interval, s.ef, s.reps, p.domain, p.question, p.answer)


def find_prompts(lines: list[str]) -> list[tuple[int, Prompt]]:
    """All (line-index, Prompt) pairs in a review-queue file."""
    return [(i, p) for i, line in enumerate(lines) if (p := parse_prompt(line))]


def due_prompts(lines: list[str], today: date) -> list[tuple[int, Prompt]]:
    """Prompts whose next-due is on/before today, weakest-and-oldest first."""
    due = [(i, p) for i, p in find_prompts(lines) if p.due <= today]
    return sorted(due, key=lambda ip: (ip[1].due, ip[1].reps))


def _find_header(lines: list[str], header: str) -> int | None:
    for i, line in enumerate(lines):
        if line.strip() == f"## {header}":
            return i
    return None


def insert_prompt(lines: list[str], prompt: Prompt) -> list[str]:
    """Insert a new prompt under the '## Prompts' section (creating it if absent)."""
    header = _find_header(lines, "Prompts")
    if header is None:
        return lines + ["", "## Prompts", "", format_prompt(prompt)]
    at = header + 1
    # Skip blank lines and the '<prompts appended here>' placeholder.
    while at < len(lines) and (not lines[at].strip() or lines[at].strip().startswith("<")):
        at += 1
    return lines[:at] + [format_prompt(prompt)] + lines[at:]


# --- Depth-marker decay (topic-index.md) -----------------------------------
MARKER_RE = re.compile(
    r"^\| (?P<domain>[^|]+?) \| (?P<updated>\d{4}-\d{2}-\d{2}) \| (?P<depth>[^|]*?) \| "
    r"(?P<conf>low|med|high) \| (?P<evidence>.*?) \|$"
)


def decay_marker_line(line: str, today: date, threshold: int) -> tuple[str, str | None]:
    """Drift a stale [high] marker to [med] + flag reprobe. Returns (line, change-or-None).

    The 'updated' date is NOT bumped — the decay is the *absence* of fresh
    evidence, not new evidence.
    """
    m = MARKER_RE.match(line.strip())
    if not m or m["conf"] != "high":
        return line, None
    age = (today - date.fromisoformat(m["updated"])).days
    if age <= threshold:
        return line, None
    evidence = f"{m['evidence'].strip()} — decayed to med (untouched {age}d, reprobe)"
    new_line = (
        f"| {m['domain'].strip()} | {m['updated']} | {m['depth'].strip()} | "
        f"med | {evidence} |"
    )
    return new_line, f"{m['domain'].strip()}: high→med (untouched {age}d)"


def decay_markers(lines: list[str], today: date, threshold: int) -> tuple[list[str], list[str]]:
    out, changes = [], []
    for line in lines:
        new_line, change = decay_marker_line(line, today, threshold)
        out.append(new_line)
        if change:
            changes.append(change)
    return out, changes


# --- Recalibration trigger -------------------------------------------------
DATED_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2}) \| (?P<mode>[a-z-]+)?")

# The calibration log's third field is the miss-type; DATED_RE's `mode` group lands on the
# *domain* there, which is why counting dated lines counted every row including the ones
# the template invites you to write as annotations.
CALIB_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2}) \| (?P<domain>[^|]*) \| (?P<misstype>[^|]*) \|")

# The documented miss-type vocabulary. The trigger counts a row only if its miss-type
# *starts with* one of these tokens, so `too-advanced (intake mis-scope)` counts and
# `(mastery signal, not a miss)` does not. Keep this in agreement with the list in
# `templates/learner/calibration-log.md` — a token in one and not the other is the
# template-drift class that has now produced three separate bugs.
MISS_TYPES = frozenset({
    "too-basic", "too-advanced", "vocab-gap", "dead-analogy", "pacing",
    "struggle-mismatch", "retention-miss", "escape-hatch", "examiner-disagree",
    # Added after the first live runs surfaced signals with nowhere to be written:
    "register-miss",     # the voice/vocabulary fit is wrong — feedback-protocol's
                         # "style confirmation" signal, which had no token to record it
    "analogy-transfer",  # an analogy carried the structure across correctly and the
                         # magnitude or cost incorrectly; not dead-analogy, which is an
                         # analogy that failed to connect at all
})

# Written by `recalibrate-mark` so counting is positional within one file rather than a
# comparison between two files' dates. Must not appear in MISS_TYPES — it would count
# itself. See _misses_since.
RECAL_MARK_TYPE = "recalibrate-mark"


def _leading_token(misstype: str) -> str:
    """The bare token at the start of a miss-type cell, ignoring any parenthetical."""
    return re.match(r"[a-z-]*", misstype.strip()).group(0)


@dataclass(frozen=True)
class RecalDecision:
    fire: bool
    misses: int
    lessons: int
    reason: str


def _last_recalibrate(log_lines: list[str]) -> date | None:
    found = [
        date.fromisoformat(m["date"])
        for line in log_lines
        if (m := DATED_RE.match(line.strip())) and (m["mode"] or "").startswith("recalibrate")
    ]
    return max(found) if found else None


def _count_after(lines: list[str], since: date | None, mode: str | None = None) -> int:
    n = 0
    for line in lines:
        m = DATED_RE.match(line.strip())
        if not m:
            continue
        when = date.fromisoformat(m["date"])
        if since is not None and when <= since:
            continue
        if mode is not None and (m["mode"] or "") != mode:
            continue
        n += 1
    return n


def _misses_since(calib_lines: list[str], since: date | None) -> int:
    """Count real misses since the last recalibrate.

    Two things this gets right that counting dated lines did not:

    **What counts.** Only rows whose miss-type begins with a documented token. The template
    invites annotation rows — `(mastery signal, not a miss)`, `(intake floor-finding)` — and
    counting those inverted the signal for the strongest evidence class the log carries: a
    demonstration of mastery raised the apparent need to correct the model.

    **Where counting starts.** Positionally, from the last `recalibrate-mark` row if one
    exists. Comparing dates across two files meant every entry written on the same calendar
    day as a recalibrate was invisible to the next check — and a recalibrate runs at session
    start while the session's misses are logged at its end, so *the common case dropped a
    whole session*. Instances predating the marker fall back to the date, now strictly
    `<` rather than `<=`, which recovers the same-day entries for exactly that reason.
    """
    last_mark = max(
        (i for i, line in enumerate(calib_lines)
         if (m := CALIB_RE.match(line.strip()))
         and _leading_token(m["misstype"]) == RECAL_MARK_TYPE),
        default=None)
    n = 0
    for i, line in enumerate(calib_lines):
        m = CALIB_RE.match(line.strip())
        if not m or _leading_token(m["misstype"]) not in MISS_TYPES:
            continue
        if last_mark is not None:
            if i > last_mark:
                n += 1
        elif since is None or date.fromisoformat(m["date"]) >= since:
            n += 1
    return n


def recalibrate_check(
    log_lines: list[str],
    calib_lines: list[str],
    miss_threshold: int = RECAL_MISS_THRESHOLD,
    lesson_cap: int = RECAL_LESSON_CAP,
) -> RecalDecision:
    since = _last_recalibrate(log_lines)
    misses = _misses_since(calib_lines, since)
    lessons = _count_after(log_lines, since, mode="lesson")
    if misses >= miss_threshold:
        return RecalDecision(True, misses, lessons, f"{misses} misses ≥ {miss_threshold}")
    if lessons >= lesson_cap:
        return RecalDecision(True, misses, lessons, f"{lessons} lessons ≥ cap {lesson_cap}")
    return RecalDecision(False, misses, lessons, f"{misses} misses / {lessons} lessons — below thresholds")


# --- File / data-dir helpers (CLI side) ------------------------------------
def resolve_data_dir(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser()
    cfg = Path.home() / ".config" / "primer" / "config"
    if cfg.exists():
        for line in cfg.read_text().splitlines():
            if line.startswith("DATA_DIR="):
                return Path(line.split("=", 1)[1].strip()).expanduser()
    raise SystemExit("no --data-dir given and no DATA_DIR in ~/.config/primer/config")


def _read_lines(path: Path) -> list[str]:
    return path.read_text().splitlines() if path.exists() else []


def _write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n")


def _learner(data_dir: Path, name: str) -> Path:
    return data_dir / "learner" / name


# --- CLI commands ----------------------------------------------------------
def cmd_review_due(args: argparse.Namespace) -> int:
    path = _learner(resolve_data_dir(args.data_dir), "review-queue.md")
    today = _today(args)
    due = due_prompts(_read_lines(path), today)
    if args.limit:
        due = due[: args.limit]
    if not due:
        print("no prompts due")
        return 0
    for idx, (_, p) in enumerate(due):
        print(f"{idx}\t{p.domain}\t(due {p.due.isoformat()}, reps {p.reps})\tQ:: {p.question}")
    return 0


def cmd_review_grade(args: argparse.Namespace) -> int:
    path = _learner(resolve_data_dir(args.data_dir), "review-queue.md")
    today = _today(args)
    lines = _read_lines(path)
    due = due_prompts(lines, today)
    if args.index < 0 or args.index >= len(due):
        raise SystemExit(f"index {args.index} out of range (0–{len(due) - 1})")
    line_no, prompt = due[args.index]
    updated = graded(prompt, quality_from_label(args.quality), today)
    lines[line_no] = format_prompt(updated)
    _write_lines(path, lines)
    lapsed = quality_from_label(args.quality) < PASS_THRESHOLD
    print(f"{'lapse' if lapsed else 'ok'}: next due {updated.due.isoformat()} "
          f"(int {updated.interval}d, ef {updated.ef:.2f}, reps {updated.reps})")
    return 0


def cmd_review_add(args: argparse.Namespace) -> int:
    path = _learner(resolve_data_dir(args.data_dir), "review-queue.md")
    today = _today(args)
    lines = insert_prompt(_read_lines(path), new_prompt(args.domain, args.question, args.answer, today))
    _write_lines(path, lines)
    print(f"added prompt to {args.domain}, due {today.isoformat()}")
    return 0


def cmd_review_history(args: argparse.Namespace) -> int:
    path = _learner(resolve_data_dir(args.data_dir), "review-queue.md")
    lines = _read_lines(path)
    note = f" | {args.note}" if args.note else ""
    entry = f"- {_today(args).isoformat()} | {args.correct}/{args.total} correct{note}"
    header = _find_header(lines, "Review history")
    if header is None:
        lines += ["", "## Review history", "", entry]
    else:
        lines.insert(header + 1, entry)
    _write_lines(path, lines)
    print(f"recorded {args.correct}/{args.total}")
    return 0


def cmd_markers_decay(args: argparse.Namespace) -> int:
    path = _learner(resolve_data_dir(args.data_dir), "topic-index.md")
    today = _today(args)
    out, changes = decay_markers(_read_lines(path), today, args.days)
    if changes:
        _write_lines(path, out)
    for c in changes:
        print(c)
    if not changes:
        print("no markers decayed")
    return 0


def cmd_recalibrate_check(args: argparse.Namespace) -> int:
    data_dir = resolve_data_dir(args.data_dir)
    decision = recalibrate_check(
        _read_lines(_learner(data_dir, "log.md")),
        _read_lines(_learner(data_dir, "calibration-log.md")),
    )
    print(f"fire={'yes' if decision.fire else 'no'} | misses={decision.misses} "
          f"| lessons={decision.lessons} | {decision.reason}")
    return 0


def cmd_recalibrate_mark(args: argparse.Namespace) -> int:
    """Record that a minor recalibrate ran, so the next check counts from here.

    Writes into the calibration log rather than only `log.md` because that is the file the
    misses live in, and a positional marker inside one file is immune to the same-day
    ambiguity that comparing dates across two files created.
    """
    path = _learner(resolve_data_dir(args.data_dir), "calibration-log.md")
    note = args.note or "minor recalibrate ran — the next check counts from below this line"
    entry = (f"{_today(args).isoformat()} | (all) | {RECAL_MARK_TYPE} | "
             f"minor recalibrate | {note}")
    _write_lines(path, _read_lines(path) + [entry])
    print(f"marked: {entry}")
    return 0


# --- Escape-hatch trend (dependence signal) -------------------------------
# T7's "just show me" hatch is the right call — misaligned Socratic pressure causes
# overload — but a *rising* rate is precisely the AI-dependence signal the cognitive-
# offloading literature describes, and it was invisible: nothing counted it. It is logged
# as an ordinary calibration miss (a struggle-tolerance mismatch, which is what it is, and
# what minor recalibrate should act on) with a fixed type token so the rate is computable.
HATCH_TYPE = "escape-hatch"
# Enough lessons for a rate to mean something without averaging away a recent change.
HATCH_WINDOW = 10


@dataclass
class HatchTrend:
    domain: str
    hatches: int
    lessons: int

    @property
    def rate(self) -> float:
        return self.hatches / self.lessons if self.lessons else 0.0


def hatch_trend(calib_lines: list[str], log_lines: list[str],
                window: int = HATCH_WINDOW) -> list[HatchTrend]:
    """Escape-hatch uses per domain over the last `window` lessons.

    The denominator is lessons, not calendar time: a learner who takes a month off has not
    become more dependent, and a rate over days would say they had.
    """
    lesson_dates = sorted(_dated(log_lines, mode="lesson"))
    if not lesson_dates:
        return []
    since = lesson_dates[-window] if len(lesson_dates) >= window else lesson_dates[0]
    in_window = [d for d in lesson_dates if d >= since]
    counts: dict[str, int] = {}
    for line in calib_lines:
        parsed = _hatch_entry(line)
        if parsed is None:
            continue
        when, domain = parsed
        if when >= since:
            counts[domain] = counts.get(domain, 0) + 1
    trends = [HatchTrend(d, n, len(in_window)) for d, n in counts.items()]
    return sorted(trends, key=lambda t: (-t.rate, t.domain))


def _hatch_entry(line: str) -> tuple[date, str] | None:
    parts = [p.strip() for p in line.strip().lstrip("- ").split("|")]
    if len(parts) < 3 or parts[2] != HATCH_TYPE:
        return None
    try:
        return date.fromisoformat(parts[0]), parts[1]
    except ValueError:
        return None


def _dated(lines: list[str], mode: str | None = None) -> list[date]:
    out: list[date] = []
    for line in lines:
        m = DATED_RE.match(line.strip())
        if not m:
            continue
        if mode is not None and (m["mode"] or "") != mode:
            continue
        out.append(date.fromisoformat(m["date"]))
    return out


def cmd_hatch_log(args: argparse.Namespace) -> int:
    path = _learner(resolve_data_dir(args.data_dir), "calibration-log.md")
    note = args.note or "consider lowering the struggle-tolerance setting for this domain"
    entry = (f"{_today(args).isoformat()} | {args.domain} | {HATCH_TYPE} | "
             f"learner asked for the answer directly | {note}")
    _write_lines(path, _read_lines(path) + [entry])
    print(f"logged: {entry}")
    return 0


def cmd_hatch_trend(args: argparse.Namespace) -> int:
    data_dir = resolve_data_dir(args.data_dir)
    trends = hatch_trend(_read_lines(_learner(data_dir, "calibration-log.md")),
                         _read_lines(_learner(data_dir, "log.md")), args.window)
    if not trends:
        print("no escape-hatch uses recorded in the window")
        return 0
    for t in trends:
        print(f"{t.domain}\t{t.hatches}/{t.lessons} lessons\t{t.rate:.0%}")
    print("A rising rate is a dependence signal, not a failure — read it as the register "
          "being mis-set for this learner in this domain, and act at recalibrate.")
    return 0


def _today(args: argparse.Namespace) -> date:
    # --on lets tests and back-dating pin 'today'; otherwise the system date.
    return date.fromisoformat(args.on) if getattr(args, "on", None) else date.today()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="primer_state", description=__doc__)
    parser.add_argument("--data-dir", help="learner data root (else ~/.config/primer/config)")
    parser.add_argument("--on", help="treat this YYYY-MM-DD as 'today' (testing / back-dating)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("review-due", help="list prompts due for review")
    p.add_argument("--limit", type=int, default=0)
    p.set_defaults(func=cmd_review_due)

    p = sub.add_parser("review-grade", help="grade a due prompt by its index and reschedule")
    p.add_argument("--index", type=int, required=True)
    p.add_argument("--quality", required=True, help="again|hard|good|easy or 0–5")
    p.set_defaults(func=cmd_review_grade)

    p = sub.add_parser("review-add", help="add a new prompt to the queue")
    p.add_argument("--domain", required=True)
    p.add_argument("--question", required=True)
    p.add_argument("--answer", required=True)
    p.set_defaults(func=cmd_review_add)

    p = sub.add_parser("review-history", help="record a review session score")
    p.add_argument("--correct", type=int, required=True)
    p.add_argument("--total", type=int, required=True)
    p.add_argument("--note", default="")
    p.set_defaults(func=cmd_review_history)

    p = sub.add_parser("markers-decay", help="decay stale high-confidence depth markers")
    p.add_argument("--days", type=int, default=DECAY_THRESHOLD_DAYS)
    p.set_defaults(func=cmd_markers_decay)

    p = sub.add_parser("recalibrate-check", help="is a minor recalibrate due?")
    p.set_defaults(func=cmd_recalibrate_check)

    p = sub.add_parser("recalibrate-mark",
                       help="record that a minor recalibrate ran (resets the miss count)")
    p.add_argument("--note", default=None)
    p.set_defaults(func=cmd_recalibrate_mark)

    p = sub.add_parser("hatch-log", help="record a 'just show me' escape-hatch use")
    p.add_argument("--domain", required=True)
    p.add_argument("--note", default="")
    p.set_defaults(func=cmd_hatch_log)

    p = sub.add_parser("hatch-trend", help="escape-hatch rate per domain (dependence signal)")
    p.add_argument("--window", type=int, default=HATCH_WINDOW)
    p.set_defaults(func=cmd_hatch_trend)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
