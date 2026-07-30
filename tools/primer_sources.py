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

# Fields are pipe-delimited (matching review-queue.md), so a pipe or a line break inside a
# value silently corrupts the line — and these values come from web pages and model output.
# Rejected loudly rather than escaped: an unparseable ledger is worse than a rejected add,
# and the caller can always rephrase a `why`.
#
# Enumerating bad characters does not work here. `str.splitlines()` — which is how the
# ledger is read — breaks on **eleven** code points, not two, so `\x0b \x0c \x1c \x1d \x1e
# \x85    ` all sailed through a `("|", "\n", "\r")` check while still splitting
# the line on the next read. That was a proven entry-forgery vector: a separator inside a
# `--why` value wrote one line and the next read saw two, with the forged entry inheriting
# the honest record's tail (fresh `checked`, `floor:yes`, `verdict:cite`). So the rule is
# inverted: a value must survive a splitlines() round trip and carry no control characters.
MAX_FIELD = 400
# URLs are legitimately long (doc anchors, archive links); prose fields are not.
MAX_URL = 2000
# A ledger entry is something the learner may click. Only web and local schemes — enforced
# on read as well as write, because a hand-edited or already-corrupted file reaches the
# same place and `javascript:` in a `sources_consulted` list is not acceptable.
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


SOURCE_KEYS = {"url", "domain", "tag", "verdict", "seen", "checked", "floor", "used", "why"}
SWEEP_KEYS = {"domain", "swept", "note"}


def parse_source(line: str, where: str = "") -> Source | None:
    """Parse one ledger line. Returns None for anything that isn't one (prose, headings).

    Every field is **required**, and a wrong key or value is an error rather than a
    default. Permissive defaults were actively harmful: `floor:Yes` parsed as False and
    the next write rewrote it to `floor:no`, silently erasing a promotion; a `tags:` typo
    parsed as `tag=verified`, laundering an ungrounded source into a verified one and
    dropping it from the verify backlog forever. The file is advertised as hand-editable,
    so a case slip must fail loudly, not rewrite the learner's model.
    """
    if not _is_source_line(line):
        return None
    f = _fields(line)
    _require_keys(f, SOURCE_KEYS, "source", where)
    seen = _date(f["seen"], f"seen{where}")
    checked = _date(f["checked"], f"checked{where}")
    _check_order(seen, checked, where)
    return Source(
        url=clean_url(f["url"]), domain=clean(f["domain"], f"domain{where}"),
        tag=one_of(f["tag"], TAGS, f"tag{where}"),
        verdict=one_of(f["verdict"], VERDICTS, f"verdict{where}"),
        seen=seen, checked=checked, floor=_flag(f["floor"], where),
        used=_count(f["used"], where), why=clean(f["why"], f"why{where}"))


def _require_keys(fields: dict[str, str], expected: set[str], kind: str,
                  where: str) -> None:
    missing = sorted(expected - set(fields))
    unknown = sorted(set(fields) - expected)
    if missing:
        raise LedgerError(f"{kind} line{where} is missing field(s) {missing}")
    if unknown:
        # Carrying an unknown key silently through a rewrite drops it; dropping a
        # hand-added annotation without saying so is worse than refusing to write.
        raise LedgerError(f"{kind} line{where} has unrecognized field(s) {unknown} — "
                          f"remove them or add support before the next write drops them")


def _flag(value: str, where: str) -> bool:
    if value.lower() not in ("yes", "no"):
        raise LedgerError(f"floor{where} must be 'yes' or 'no'; got {value!r}")
    return value.lower() == "yes"


def _count(value: str, where: str) -> int:
    # `isdigit()` alone is True for Arabic-Indic and other non-ASCII digits, and `int()`
    # refuses strings over 4300 digits — both surfaced as tracebacks rather than errors.
    if not (value.isascii() and value.isdigit()) or len(value) > 9:
        raise LedgerError(f"used{where} must be a plain non-negative integer (max 9 "
                          f"digits); got {value!r}")
    return int(value)


def _check_order(seen: date, checked: date, where: str) -> None:
    if checked < seen:
        raise LedgerError(f"line{where}: checked ({checked}) is before seen ({seen})")


def _check_not_future(when: date, what: str, today: date) -> date:
    """A future date makes an entry permanently fresh — it silently switches off the
    freshness guardrail for that source, which is what this module exists to enforce."""
    if when > today:
        raise LedgerError(f"{what} is in the future ({when}); today is {today}")
    return when


def parse_sweep(line: str, where: str = "") -> Sweep | None:
    if not _is_sweep_line(line):
        return None
    f = _fields(line)
    _require_keys(f, SWEEP_KEYS, "sweep", where)
    return Sweep(domain=clean(f["domain"], f"domain{where}"),
                 swept=_date(f["swept"], f"swept{where}"),
                 note=clean(f["note"], f"note{where}"))


def _section_bounds(lines: list[str], heading: str) -> tuple[int, int]:
    """Index range of a section's body: (first line after the heading, end exclusive)."""
    matches = [i for i, line in enumerate(lines) if line.strip() == heading]
    if not matches:
        raise LedgerError(f"ledger is missing its '{heading}' section — is this file "
                          f"scaffolded from templates/learner/source-ledger.md?")
    if len(matches) > 1:
        # Binding to the first would orphan everything under the second: its prose, its
        # format docs, and its records, all invisible to every command.
        raise LedgerError(f"ledger has {len(matches)} '{heading}' headings (lines "
                          f"{[i + 1 for i in matches]}) — one section must own the data; "
                          f"merge them before the next write ignores half the file")
    start = matches[0] + 1
    end = next((i for i in range(start, len(lines))
                if lines[i].startswith("## ")), len(lines))
    return start, end


def _data_lines(lines: list[str], heading: str) -> list[tuple[int, str]]:
    """A section's data lines with 1-based file line numbers, skipping fenced blocks.

    Fence-aware because the natural way to document the line format is a fenced example,
    and a doc line lifted out of its fence became a live ledger entry with url='<url>'.
    """
    start, end = _section_bounds(lines, heading)
    out: list[tuple[int, str]] = []
    fenced = False
    for i in range(start, end):
        if _is_fence(lines[i]):
            fenced = not fenced
            continue
        if not fenced:
            out.append((i + 1, lines[i]))
    return out


def _is_fence(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("```") or stripped.startswith("~~~")


def read_sources(lines: list[str]) -> list[Source]:
    return [s for s in (parse_source(text, f" (line {n})")
                        for n, text in _data_lines(lines, SOURCES_HEADING)) if s]


def read_sweeps(lines: list[str]) -> list[Sweep]:
    return [s for s in (parse_sweep(text, f" (line {n})")
                        for n, text in _data_lines(lines, SWEEPS_HEADING)) if s]


# --- Validation ------------------------------------------------------------


def clean(value: str, what: str, limit: int = MAX_FIELD) -> str:
    """Reject anything that would corrupt a pipe-delimited line, or is absurdly long."""
    text = (value or "").strip()
    if not text:
        raise LedgerError(f"{what} is required")
    _reject_line_breaks(text, what)
    _reject_control_chars(text, what)
    if "|" in text:
        raise LedgerError(f"{what} may not contain '|' — the ledger is pipe-delimited, "
                          f"one entry per line. Rephrase it.")
    if len(text) > limit:
        raise LedgerError(f"{what} is {len(text)} chars, over the {limit} limit")
    return text


def _reject_line_breaks(text: str, what: str) -> None:
    """Anything `splitlines()` would break on, not just \\n and \\r."""
    if len(text.splitlines()) > 1 or text != "".join(text.splitlines()):
        raise LedgerError(f"{what} may not contain a line break (including the exotic "
                          f"ones: vertical tab, form feed, U+2028, U+2029) — one ledger "
                          f"entry is one line, and a break here forges a second entry")


def _reject_control_chars(text: str, what: str) -> None:
    """Tabs forge output columns; ESC lets a web-sourced value drive the terminal; NUL
    turns the ledger into a binary blob git can no longer merge."""
    bad = next((c for c in text if ord(c) < 0x20 or ord(c) == 0x7F), None)
    if bad is not None:
        raise LedgerError(f"{what} may not contain control characters (found "
                          f"{bad!r}) — they corrupt the ledger's display and its diffs")


def clean_url(value: str) -> str:
    url = clean(value, "url", MAX_URL)
    if not url.startswith(ALLOWED_SCHEMES):
        raise LedgerError(f"url must start with one of {ALLOWED_SCHEMES}; got {url!r}")
    return url


def one_of(value: str, allowed: tuple[str, ...], what: str) -> str:
    if value not in allowed:
        raise LedgerError(f"{what} must be one of {allowed}; got {value!r}")
    return value


# --- Mutation --------------------------------------------------------------


def upsert_source(sources: list[Source], new: Source) -> tuple[list[Source], str]:
    """Add, or update the existing entry for the same (url, domain).

    Re-adding is the common case — the same source turns up in a later lesson — so it
    refreshes `checked`, bumps `used`, and keeps the earliest `seen`. That accrual is the
    whole point: it's what makes a repeat sighting evidence rather than a duplicate.

    Identity is **(url, domain)**, not url alone. A spec or a Jepsen report is legitimately
    cited from two domains, and URL-only identity meant the second citation overwrote the
    first record's domain wholesale — silently removing the source from the first domain's
    accreted floor, which is the one thing the floor exists to remember.
    """
    for i, existing in enumerate(sources):
        if (existing.url, existing.domain) != (new.url, new.domain):
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


# Unindented only: an indented "- url:" is a nested list item in someone's prose, not a
# record, and treating it as data both mangles the prose and invents an entry.
def _is_source_line(line: str) -> bool:
    return line.startswith("- url:")


def _is_sweep_line(line: str) -> bool:
    return line.startswith("- domain:")


def _replace_section(lines: list[str], heading: str, body: list[str],
                     is_data: Callable[[str], bool]) -> list[str]:
    """Swap a section's data lines for `body`, keeping every other line in place.

    Only data lines and the template placeholder are removed — the section's explanatory
    prose and its format documentation are part of the file's value (this is an
    Open-Learner-Model file a human reads and hand-edits), so a rewrite must not eat them.
    """
    start, end = _section_bounds(lines, heading)
    body_lines = lines[start:end]
    # Fence-aware, for the same reason the parser is: the natural way to document the line
    # format is a fenced example, and treating a doc line as data both lifts it out of its
    # fence and turns it into a live entry.
    replaceable = _replaceable_flags(body_lines, is_data)
    # Where the data currently sits, so a curated section keeps its narrative order
    # instead of having trailing notes hoisted above the records on every write.
    anchor = next((i for i, flag in enumerate(replaceable) if flag), None)
    kept = [line for line, flag in zip(body_lines, replaceable) if not flag]
    if anchor is not None:
        cut = sum(1 for flag in replaceable[:anchor] if not flag)
    else:
        # No data yet: fall back to just above the section's trailing `---` rule.
        cut = max((i for i, line in enumerate(kept) if line.strip() == "---"),
                  default=len(kept))
    before = _trim_blanks(kept[:cut], trailing=True)
    after = _trim_blanks(kept[cut:], trailing=False)
    block = ([""] + body + [""]) if body else [""]
    return lines[:start] + before + block + after + lines[end:]


def _replaceable_flags(body: list[str], is_data: Callable[[str], bool]) -> list[bool]:
    """Per-line: is this a data line (or the placeholder) that a rewrite should replace?"""
    flags: list[bool] = []
    fenced = False
    for line in body:
        if _is_fence(line):
            fenced = not fenced
            flags.append(False)
            continue
        flags.append(not fenced and (is_data(line) or line.strip() == PLACEHOLDER))
    return flags


def _trim_blanks(lines: list[str], trailing: bool) -> list[str]:
    """Strip blank lines from one end, so the inserted block's own spacing is the only
    spacing and successive writes don't accumulate empty lines."""
    if trailing:
        end = len(lines)
        while end and not lines[end - 1].strip():
            end -= 1
        return lines[:end]
    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    return lines[start:]


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
    raise LedgerError("no --data-dir given and no DATA_DIR in "
                      "~/.config/primer/config — pass --data-dir or run "
                      "tools/init-instance.sh")


def ledger_path(args: argparse.Namespace) -> Path:
    return resolve_data_dir(args.data_dir) / "learner" / "source-ledger.md"


def _read(path: Path) -> list[str]:
    if not path.exists():
        raise LedgerError(f"no ledger at {path} — scaffold it from "
                          f"templates/learner/source-ledger.md (or run init-instance.sh)")
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise LedgerError(f"{path} is not valid UTF-8 ({exc}) — an editor probably saved "
                          f"it in a legacy encoding; re-save it as UTF-8") from None


def _write(path: Path, lines: list[str]) -> None:
    """Write via a temp file and rename.

    Two reasons this is not `write_text`. Explicit utf-8, because the locale default is
    cp1252 on a stock Windows box and an arrow in a `why` field would raise. And atomicity,
    because `write_text` opens with 'w' — it *truncates before it encodes*, so a failed
    write emptied the ledger, which is the only copy of the learner's accreted floor.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(path)


def _today(args: argparse.Namespace) -> date:
    if not getattr(args, "on", None):
        return date.today()
    when = _date(args.on, "--on")
    return _check_not_future(when, "--on", date.today())


def _show(sources: list[Source], today: date) -> None:
    for s in sources:
        flag = " [floor]" if s.floor else ""
        print(f"{s.domain}\t{s.verdict}\t{s.tag}\tchecked {s.age(today)}d ago\t"
              f"used {s.used}{flag}\t{s.url}\t{s.why}")


# --- CLI -------------------------------------------------------------------


def cmd_add(args: argparse.Namespace) -> int:
    path = ledger_path(args)
    lines = _read(path)
    today = _today(args)
    verdict = one_of(args.verdict, VERDICTS, "verdict")
    if args.floor and verdict == "dropped":
        # Same guard as `sources-promote`: a source that failed the stale-criteria has no
        # business in the floor a future lesson reads as its starting set.
        raise LedgerError("--floor with --verdict dropped: a dropped source cannot be "
                          "part of the floor")
    source = Source(url=clean_url(args.url), domain=clean(args.domain, "domain"),
                    tag=one_of(args.tag, TAGS, "tag"), verdict=verdict,
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
        print(f"no sources at or past the {args.days}d horizon")
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
    except ValueError as exc:
        # Residual coercion failures from a hand-edited ledger. Reported as a ledger
        # problem rather than a traceback, since that is what it always is.
        print(f"error: ledger could not be parsed ({type(exc).__name__}: {exc})")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
