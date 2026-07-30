#!/usr/bin/env python3
"""primer_sources — deterministic bookkeeping for the source-discovery pass.

Why this exists: currency is primer's top non-negotiable (GOALS.md) and it was the only
one with no code behind it. The per-lesson discovery pass (primer/research-protocol.md) is
mandatory, and it was specified entirely as prose — so it got reconstructed from scratch
every session, with hand-computed freshness dates and no memory of what had already been
vetted. Four costs: re-swept sources, re-judged verdicts, hand-done arithmetic the model
gets wrong, and `[from-training, verify]` tags nobody ever came back to.

This module makes the ledger queryable, which inverts the economics: the discovery pass
gets *cheaper* the more it runs, because a source vetted inside the freshness horizon is
reused rather than re-swept.

Source of truth stays the learner's markdown (D-0018/D-0020), and the ledger lives in the
private instance — never in the public core (see D-0025: the core's canon is a shared
starter pack, so a per-learner promotion there would leak what the learner studies and
conflict on every pull).

Stdlib only — runs on any Python 3.11+ (mac/linux/windows) with nothing to install.
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Callable

# Matches source-canon.md's "~3 months stale" rule, in one place instead of in prose.
FRESH_DAYS = 90
# Domain sweeps age faster than individual sources: a source stays true, but the *set* of
# what's current in a domain moves, so a sweep is stale sooner than the sources it found.
SWEEP_FRESH_DAYS = 60

TAGS = ("verified", "from-training")
VERDICTS = ("cite", "caveat", "dropped")

# Fields are pipe-delimited (matching review-queue.md), so a pipe or a newline inside a
# value would silently corrupt the line — and these values come from web pages and model
# output. Rejected loudly rather than escaped: an unparseable ledger is worse than a
# rejected add, and the caller can always rephrase a `why`.
FORBIDDEN = ("|", "\n", "\r")
MAX_FIELD = 400
# A ledger entry is something the learner may click. Only web and local schemes.
ALLOWED_SCHEMES = ("http://", "https://", "file://")

SOURCES_HEADING = "## Sources"
SWEEPS_HEADING = "## Domain sweeps"
PLACEHOLDER = "<sources appended here>"


class LedgerError(Exception):
    """An input would corrupt the ledger, or a lookup found nothing usable."""


@dataclass(frozen=True)
class Source:
    url: str
    domain: str
    tag: str
    verdict: str
    seen: date
    checked: date
    floor: bool
    used: int
    why: str

    def age(self, today: date) -> int:
        return (today - self.checked).days

    def is_stale(self, today: date, days: int = FRESH_DAYS) -> bool:
        return self.age(today) >= days

    def to_line(self) -> str:
        return (f"- url:{self.url} | domain:{self.domain} | tag:{self.tag} | "
                f"verdict:{self.verdict} | seen:{self.seen.isoformat()} | "
                f"checked:{self.checked.isoformat()} | "
                f"floor:{'yes' if self.floor else 'no'} | used:{self.used} | "
                f"why:{self.why}")


@dataclass(frozen=True)
class Sweep:
    domain: str
    swept: date
    note: str

    def to_line(self) -> str:
        return f"- domain:{self.domain} | swept:{self.swept.isoformat()} | note:{self.note}"


# --- Parsing ---------------------------------------------------------------


def _fields(line: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in line.lstrip("- ").split(" | "):
        key, _, value = part.partition(":")
        out[key.strip()] = value.strip()
    return out


def _date(value: str, what: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise LedgerError(f"{what} is not a YYYY-MM-DD date: {value!r}") from None


def parse_source(line: str) -> Source | None:
    """Parse one ledger line. Returns None for anything that isn't one (prose, headings)."""
    if not line.lstrip().startswith("- url:"):
        return None
    f = _fields(line)
    # `url:` splits on the first colon, so the scheme's own colon lands in the value.
    url = f.get("url", "")
    if url and not url.startswith(ALLOWED_SCHEMES):
        url = _reattach_scheme(line)
    return Source(
        url=url, domain=f.get("domain", ""), tag=f.get("tag", "verified"),
        verdict=f.get("verdict", "cite"),
        seen=_date(f.get("seen", "1970-01-01"), "seen"),
        checked=_date(f.get("checked", f.get("seen", "1970-01-01")), "checked"),
        floor=f.get("floor", "no") == "yes", used=int(f.get("used", "0") or 0),
        why=f.get("why", ""))


def _reattach_scheme(line: str) -> str:
    """Recover a URL whose scheme colon was eaten by the field split."""
    m = re.search(r"- url:(.*?)(?: \| |$)", line)
    return m.group(1).strip() if m else ""


def parse_sweep(line: str) -> Sweep | None:
    if not line.lstrip().startswith("- domain:"):
        return None
    f = _fields(line)
    return Sweep(domain=f.get("domain", ""), swept=_date(f.get("swept", "1970-01-01"),
                                                         "swept"), note=f.get("note", ""))


def _section_bounds(lines: list[str], heading: str) -> tuple[int, int]:
    """Index range of a section's body: (first line after the heading, end exclusive)."""
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == heading) + 1
    except StopIteration:
        raise LedgerError(f"ledger is missing its '{heading}' section — is this file "
                          f"scaffolded from templates/learner/source-ledger.md?") from None
    end = next((i for i in range(start, len(lines))
                if lines[i].startswith("## ")), len(lines))
    return start, end


def read_sources(lines: list[str]) -> list[Source]:
    start, end = _section_bounds(lines, SOURCES_HEADING)
    return [s for s in (parse_source(l) for l in lines[start:end]) if s]


def read_sweeps(lines: list[str]) -> list[Sweep]:
    start, end = _section_bounds(lines, SWEEPS_HEADING)
    return [s for s in (parse_sweep(l) for l in lines[start:end]) if s]


# --- Validation ------------------------------------------------------------


def clean(value: str, what: str) -> str:
    """Reject anything that would corrupt a pipe-delimited line, or is absurdly long."""
    text = (value or "").strip()
    if not text:
        raise LedgerError(f"{what} is required")
    bad = next((c for c in FORBIDDEN if c in text), None)
    if bad is not None:
        raise LedgerError(f"{what} may not contain {bad!r} — the ledger is "
                          f"pipe-delimited, one entry per line. Rephrase it.")
    if len(text) > MAX_FIELD:
        raise LedgerError(f"{what} is {len(text)} chars, over the {MAX_FIELD} limit")
    return text


def clean_url(value: str) -> str:
    url = clean(value, "url")
    if not url.startswith(ALLOWED_SCHEMES):
        raise LedgerError(f"url must start with one of {ALLOWED_SCHEMES}; got {url!r}")
    return url


def one_of(value: str, allowed: tuple[str, ...], what: str) -> str:
    if value not in allowed:
        raise LedgerError(f"{what} must be one of {allowed}; got {value!r}")
    return value


# --- Mutation --------------------------------------------------------------


def upsert_source(sources: list[Source], new: Source) -> tuple[list[Source], str]:
    """Add, or update the existing entry for the same URL.

    Re-adding is the common case — the same source turns up in a later lesson — so it
    refreshes `checked`, bumps `used`, and keeps the earliest `seen`. That accrual is the
    whole point: it's what makes a repeat sighting evidence rather than a duplicate.
    """
    for i, existing in enumerate(sources):
        if existing.url != new.url:
            continue
        merged = replace(new, seen=min(existing.seen, new.seen),
                         used=existing.used + 1,
                         floor=existing.floor or new.floor)
        return sources[:i] + [merged] + sources[i + 1:], "updated"
    return sources + [new], "added"


def upsert_sweep(sweeps: list[Sweep], new: Sweep) -> list[Sweep]:
    kept = [s for s in sweeps if s.domain != new.domain]
    return kept + [new]


def render(lines: list[str], sources: list[Source], sweeps: list[Sweep]) -> list[str]:
    """Rewrite both sections in place, leaving all surrounding prose untouched."""
    out = _replace_section(lines, SOURCES_HEADING,
                           [s.to_line() for s in sorted(sources, key=_source_key)],
                           _is_source_line)
    return _replace_section(out, SWEEPS_HEADING,
                            [s.to_line() for s in sorted(sweeps, key=lambda s: s.domain)],
                            _is_sweep_line)


def _source_key(s: Source) -> tuple[str, str]:
    return (s.domain, s.url)


def _is_source_line(line: str) -> bool:
    return line.lstrip().startswith("- url:")


def _is_sweep_line(line: str) -> bool:
    return line.lstrip().startswith("- domain:")


def _replace_section(lines: list[str], heading: str, body: list[str],
                     is_data: Callable[[str], bool]) -> list[str]:
    """Swap a section's data lines for `body`, keeping every other line in place.

    Only data lines and the template placeholder are removed — the section's explanatory
    prose and its format documentation are part of the file's value (this is an
    Open-Learner-Model file a human reads and hand-edits), so a rewrite must not eat them.
    """
    start, end = _section_bounds(lines, heading)
    kept = [l for l in lines[start:end]
            if not is_data(l) and l.strip() != PLACEHOLDER]
    # Data goes back where the section ends, just above its trailing `---` rule if it has
    # one, so appended entries don't drift past the separator over successive writes.
    cut = max((i for i, l in enumerate(kept) if l.strip() == "---"), default=len(kept))
    before = _trim_trailing_blanks(kept[:cut])
    after = kept[cut:]
    block = ([""] + body + [""]) if body else [""]
    return lines[:start] + before + block + after + lines[end:]


def _trim_trailing_blanks(lines: list[str]) -> list[str]:
    end = len(lines)
    while end and not lines[end - 1].strip():
        end -= 1
    return lines[:end]


# --- Queries ---------------------------------------------------------------


def stale_sources(sources: list[Source], today: date, days: int) -> list[Source]:
    candidates = [s for s in sources if s.verdict != "dropped"
                  and s.is_stale(today, days)]
    return sorted(candidates, key=lambda s: (-s.used, s.checked))


def unverified(sources: list[Source]) -> list[Source]:
    return sorted((s for s in sources if s.tag == "from-training"
                   and s.verdict != "dropped"), key=lambda s: s.seen)


def floor_for(sources: list[Source], domain: str | None) -> list[Source]:
    return sorted((s for s in sources if s.floor and s.verdict != "dropped"
                   and (domain is None or s.domain == domain)),
                  key=lambda s: (-s.used, s.url))


def sweep_due(sweeps: list[Sweep], domain: str, today: date, days: int) -> tuple[bool, str]:
    for s in sweeps:
        if s.domain != domain:
            continue
        age = (today - s.swept).days
        if age >= days:
            return True, f"last full sweep {age}d ago (horizon {days}d) — run a full sweep"
        return False, (f"last full sweep {age}d ago (horizon {days}d) — read the ledger "
                       f"and do a narrow top-up for this topic")
    return True, f"no recorded sweep for '{domain}' — run a full sweep"


# --- File helpers ----------------------------------------------------------


def resolve_data_dir(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser()
    cfg = Path.home() / ".config" / "primer" / "config"
    if cfg.exists():
        for line in cfg.read_text().splitlines():
            if line.startswith("DATA_DIR="):
                return Path(line.split("=", 1)[1].strip()).expanduser()
    raise SystemExit("no --data-dir given and no DATA_DIR in ~/.config/primer/config")


def ledger_path(args: argparse.Namespace) -> Path:
    return resolve_data_dir(args.data_dir) / "learner" / "source-ledger.md"


def _read(path: Path) -> list[str]:
    if not path.exists():
        raise LedgerError(f"no ledger at {path} — scaffold it from "
                          f"templates/learner/source-ledger.md (or run init-instance.sh)")
    return path.read_text().splitlines()


def _write(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n")


def _today(args: argparse.Namespace) -> date:
    return _date(args.on, "--on") if getattr(args, "on", None) else date.today()


def _show(sources: list[Source], today: date) -> None:
    for s in sources:
        flag = " [floor]" if s.floor else ""
        print(f"{s.domain}\t{s.verdict}\t{s.tag}\tchecked {s.age(today)}d ago\t"
              f"used {s.used}{flag}\t{s.url}")


# --- CLI -------------------------------------------------------------------


def cmd_add(args: argparse.Namespace) -> int:
    path = ledger_path(args)
    lines = _read(path)
    today = _today(args)
    source = Source(url=clean_url(args.url), domain=clean(args.domain, "domain"),
                    tag=one_of(args.tag, TAGS, "tag"),
                    verdict=one_of(args.verdict, VERDICTS, "verdict"),
                    seen=today, checked=today, floor=args.floor, used=1,
                    why=clean(args.why, "why"))
    sources, action = upsert_source(read_sources(lines), source)
    _write(path, render(lines, sources, read_sweeps(lines)))
    print(f"{action}: {source.url} ({source.domain}, {source.verdict})")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    lines = _read(ledger_path(args))
    today = _today(args)
    url = clean_url(args.url)
    match = next((s for s in read_sources(lines) if s.url == url), None)
    if match is None:
        print(f"unknown: {url} — not yet vetted, run the discovery pass on it")
        return 0
    state = "stale" if match.is_stale(today, args.days) else "fresh"
    print(f"{state}: verdict {match.verdict}, tag {match.tag}, checked "
          f"{match.age(today)}d ago, used in {match.used} lesson(s) — {match.why}")
    return 0


def cmd_stale(args: argparse.Namespace) -> int:
    today = _today(args)
    found = stale_sources(read_sources(_read(ledger_path(args))), today, args.days)
    if not found:
        print(f"no sources older than {args.days}d")
        return 0
    print(f"{len(found)} source(s) past the {args.days}d freshness horizon, "
          f"most-used first:")
    _show(found, today)
    return 0


def cmd_unverified(args: argparse.Namespace) -> int:
    today = _today(args)
    found = unverified(read_sources(_read(ledger_path(args))))
    if not found:
        print("no from-training sources outstanding")
        return 0
    print(f"{len(found)} source(s) tagged from-training and never grounded:")
    _show(found, today)
    return 0


def cmd_floor(args: argparse.Namespace) -> int:
    today = _today(args)
    found = floor_for(read_sources(_read(ledger_path(args))), args.domain)
    if not found:
        scope = f" for '{args.domain}'" if args.domain else ""
        print(f"no accreted floor{scope} yet — the discovery pass builds it")
        return 0
    _show(found, today)
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    path = ledger_path(args)
    lines = _read(path)
    url = clean_url(args.url)
    sources = read_sources(lines)
    match = next((s for s in sources if s.url == url), None)
    if match is None:
        raise LedgerError(f"{url} is not in the ledger — add it first")
    if match.verdict == "dropped":
        raise LedgerError(f"{url} was dropped for failing the stale-criteria; "
                          f"re-add it with a fresh verdict before promoting")
    updated = [replace(s, floor=True) if s.url == url else s for s in sources]
    _write(path, render(lines, updated, read_sweeps(lines)))
    print(f"promoted to the floor: {url}")
    return 0


def cmd_sweep_record(args: argparse.Namespace) -> int:
    path = ledger_path(args)
    lines = _read(path)
    sweep = Sweep(domain=clean(args.domain, "domain"), swept=_today(args),
                  note=clean(args.note or "full discovery sweep", "note"))
    sweeps = upsert_sweep(read_sweeps(lines), sweep)
    _write(path, render(lines, read_sources(lines), sweeps))
    print(f"recorded sweep: {sweep.domain} on {sweep.swept.isoformat()}")
    return 0


def cmd_sweep_check(args: argparse.Namespace) -> int:
    lines = _read(ledger_path(args))
    due, why = sweep_due(read_sweeps(lines), clean(args.domain, "domain"),
                         _today(args), args.days)
    print(f"{'due' if due else 'fresh'}: {why}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="primer_sources.py",
        description="Deterministic bookkeeping for the source-discovery pass: what has "
                    "been vetted, what has gone stale, and what still needs grounding.")
    parser.add_argument("--data-dir", default=None,
                        help="instance root (default: DATA_DIR from ~/.config/primer/config)")
    parser.add_argument("--on", default=None, metavar="YYYY-MM-DD",
                        help="override today (for testing or back-dating)")
    subs = parser.add_subparsers(dest="cmd", required=True)

    add = subs.add_parser("sources-add", help="record a vetted source (idempotent per URL)")
    add.add_argument("--url", required=True)
    add.add_argument("--domain", required=True)
    add.add_argument("--tag", default="verified", choices=TAGS)
    add.add_argument("--verdict", default="cite", choices=VERDICTS)
    add.add_argument("--why", required=True, help="one line: why it is load-bearing")
    add.add_argument("--floor", action="store_true", help="also mark it as floor")
    add.set_defaults(func=cmd_add)

    check = subs.add_parser("sources-check", help="already vetted? what verdict? still fresh?")
    check.add_argument("--url", required=True)
    check.add_argument("--days", type=int, default=FRESH_DAYS)
    check.set_defaults(func=cmd_check)

    stale = subs.add_parser("sources-stale", help="entries past the freshness horizon")
    stale.add_argument("--days", type=int, default=FRESH_DAYS)
    stale.set_defaults(func=cmd_stale)

    subs.add_parser("sources-unverified",
                    help="the [from-training, verify] backlog").set_defaults(
        func=cmd_unverified)

    floor = subs.add_parser("sources-floor", help="the learner's accreted floor")
    floor.add_argument("--domain", default=None)
    floor.set_defaults(func=cmd_floor)

    promote = subs.add_parser("sources-promote", help="mark a source as floor")
    promote.add_argument("--url", required=True)
    promote.set_defaults(func=cmd_promote)

    rec = subs.add_parser("sweep-record", help="record a full discovery sweep for a domain")
    rec.add_argument("--domain", required=True)
    rec.add_argument("--note", default=None)
    rec.set_defaults(func=cmd_sweep_record)

    swc = subs.add_parser("sweep-check", help="is the domain's cached sweep stale?")
    swc.add_argument("--domain", required=True)
    swc.add_argument("--days", type=int, default=SWEEP_FRESH_DAYS)
    swc.set_defaults(func=cmd_sweep_check)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except LedgerError as exc:
        print(f"error: {exc}")
        return 1
    except OSError as exc:
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
