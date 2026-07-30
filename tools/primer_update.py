#!/usr/bin/env python3
"""primer_update — check for a newer core, install it, and migrate the instance.

The audience constraint drives the whole design: a primer learner is not necessarily
someone who knows what `git pull --ff-only` does, or that a new engine release may need
a new state file in their data repo. So updating has to be one verb that does both halves
and explains itself, and *noticing* an update has to happen without being asked.

Two halves, because a core update alone can leave a broken instance:

1. **Core** — the engine (this repo, symlinked into ~/.claude/skills/primer). Updated with
   a fast-forward pull. Refuses rather than guesses when the checkout has local commits or
   uncommitted edits: a contributor's work is not ours to discard.
2. **Instance** — the learner's private data repo. Engine releases add state files
   (`source-ledger.md` arrived with the research layer) and gitignore rules. Migration only
   *adds* what's missing and never touches existing content, so it is safe to re-run.

The notice is delivered by SKILL.md's `!`…`` dynamic-context injection rather than a
settings.json hook: a hook is an extra install step for a non-technical user and would run
in every session, primer or not. This way the check rides the moment the learner is already
using primer, and the result is cached so it costs one network call a day at most.

Stdlib only — Python 3.11+, no installs.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

CORE_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = CORE_ROOT / "VERSION"
TEMPLATE_DIR = CORE_ROOT / "templates" / "learner"
CONFIG_DIR = Path.home() / ".config" / "primer"
CHECK_CACHE = CONFIG_DIR / "update-check.json"
# One network call a day is plenty for a project that ships in waves, and it keeps the
# per-invocation cost of the notice at a file read.
CHECK_TTL_DAYS = 1
# Short, because this runs in front of a lesson. A slow network must not delay teaching.
NET_TIMEOUT = 6

# Instance gitignore rules the engine expects. Appended if absent, never rewritten —
# `.STATE.md` is deliberately NOT here (it must sync across machines; D-0021).
GITIGNORE_RULES = [
    ("lessons/**/*.view.html",
     "Derived: regenerated from the lesson artifact by primer_view.py"),
]


class UpdateError(Exception):
    """Something the caller can act on: a dirty checkout, a missing instance, no git."""


def run_git(args: list[str], timeout: int = NET_TIMEOUT) -> tuple[int, str]:
    if not shutil.which("git"):
        raise UpdateError("git is not installed — primer's core is a git checkout, so "
                          "updates need it. Install git, then run /primer update again.")
    try:
        proc = subprocess.run(["git", "-C", str(CORE_ROOT), *args],
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def local_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() \
        else "unknown"


def is_git_checkout() -> bool:
    return (CORE_ROOT / ".git").exists()


# --- Checking --------------------------------------------------------------


def read_cache() -> dict[str, str]:
    if not CHECK_CACHE.exists():
        return {}
    try:
        data = json.loads(CHECK_CACHE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def write_cache(data: dict[str, str]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CHECK_CACHE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    tmp.replace(CHECK_CACHE)


def cache_is_fresh(cache: dict[str, str], today: date) -> bool:
    stamp = cache.get("checked")
    if not stamp:
        return False
    try:
        return (today - date.fromisoformat(stamp)).days < CHECK_TTL_DAYS
    except ValueError:
        return False


def behind_count(today: date, force: bool) -> tuple[int | None, str]:
    """How many upstream commits the core is behind. None when it can't be determined.

    Cached, because this runs ahead of every lesson. `None` is a first-class answer: being
    offline, or on a fork, must read as "don't know" and stay silent, never as "up to date"
    and never as an error in front of a learner.
    """
    cache = read_cache()
    if not force and cache_is_fresh(cache, today):
        return _cached_count(cache), cache.get("detail", "cached")
    if not is_git_checkout():
        return None, "core is not a git checkout"
    code, _ = run_git(["fetch", "--quiet", "origin"])
    if code != 0:
        return None, "could not reach the remote (offline?)"
    code, out = run_git(["rev-list", "--count", "HEAD..@{upstream}"], timeout=10)
    if code != 0 or not out.strip().isdigit():
        detail = "no upstream branch configured" if code != 0 else f"unexpected: {out}"
        return None, detail
    count = int(out.strip())
    write_cache({"checked": today.isoformat(), "behind": str(count),
                 "version": local_version(), "detail": "checked"})
    return count, "checked"


def _cached_count(cache: dict[str, str]) -> int | None:
    raw = cache.get("behind", "")
    return int(raw) if raw.isdigit() else None


# --- Instance migration ----------------------------------------------------


def resolve_data_dir(arg: str | None) -> Path | None:
    if arg:
        return Path(arg).expanduser()
    cfg = CONFIG_DIR / "config"
    if not cfg.exists():
        return None
    for line in cfg.read_text(encoding="utf-8").splitlines():
        if line.startswith("DATA_DIR="):
            return Path(line.split("=", 1)[1].strip()).expanduser()
    return None


def migrate_instance(data_dir: Path) -> list[str]:
    """Add anything a newer engine expects. Only ever adds; safe to re-run."""
    learner = data_dir / "learner"
    if not learner.is_dir():
        raise UpdateError(f"{data_dir} does not look like a primer instance (no learner/ "
                          f"directory) — run tools/init-instance.sh first")
    done = _copy_missing_templates(learner)
    done += _append_gitignore_rules(data_dir)
    return done


def _copy_missing_templates(learner: Path) -> list[str]:
    """Copy state files the engine expects but this instance predates.

    Never overwrites: an existing file holds the learner's own data, and the template is
    an empty scaffold. Silently clobbering it would destroy the only copy.
    """
    done: list[str] = []
    for template in sorted(TEMPLATE_DIR.glob("*.md")):
        target = learner / template.name
        if target.exists():
            continue
        shutil.copyfile(template, target)
        done.append(f"added learner/{template.name} (new in this version)")
    return done


def _append_gitignore_rules(data_dir: Path) -> list[str]:
    path = data_dir / ".gitignore"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    additions = [(rule, why) for rule, why in GITIGNORE_RULES if rule not in existing]
    if not additions:
        return []
    block = "".join(f"\n# {why}\n{rule}\n" for rule, why in additions)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(block)
    return [f"gitignored {rule}" for rule, _ in additions]


# --- Commands --------------------------------------------------------------


def cmd_check(args: argparse.Namespace) -> int:
    """Print a one-line notice when an update is waiting; otherwise print nothing.

    Always exits 0. This is injected into SKILL.md ahead of a lesson, so a failure here
    must never surface as a broken skill invocation.
    """
    try:
        count, detail = behind_count(date.today(), args.force)
    except UpdateError as exc:
        count, detail = None, str(exc)
    if args.quiet:
        if count:
            print(f"primer: {count} update(s) available — run `/primer update` to install "
                  f"(engine v{local_version()})")
        return 0
    if count is None:
        print(f"could not determine: {detail} (engine v{local_version()})")
        return 0
    state = f"{count} update(s) available" if count else "up to date"
    print(f"{state} — engine v{local_version()} ({detail})")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    before = local_version()
    changes = _update_core() if not args.instance_only else ["skipped core (--instance-only)"]
    data_dir = resolve_data_dir(args.data_dir)
    if data_dir is None:
        changes.append("no instance configured yet — nothing to migrate")
    else:
        migrated = migrate_instance(data_dir)
        changes += migrated or [f"instance at {data_dir} already current"]
    write_cache({"checked": date.today().isoformat(), "behind": "0",
                 "version": local_version(), "detail": "just updated"})
    after = local_version()
    print(f"primer {before} -> {after}" if before != after else f"primer v{after}")
    for line in changes:
        print(f"  - {line}")
    return 0


def _update_core() -> list[str]:
    if not is_git_checkout():
        raise UpdateError(
            "the core isn't a git checkout, so it can't self-update. Re-install with:\n"
            "  git clone https://github.com/voidnologo/primer && cd primer && "
            "./tools/install.sh\n"
            "Your lessons and profile live in a separate private repo and are untouched.")
    code, dirty = run_git(["status", "--porcelain"])
    if code == 0 and dirty:
        raise UpdateError(
            f"the core checkout has uncommitted changes, so a pull could lose them:\n"
            f"{dirty}\nCommit or stash them first, then run /primer update again.")
    code, out = run_git(["pull", "--ff-only", "--quiet"], timeout=30)
    if code != 0:
        raise UpdateError(
            f"could not fast-forward the core: {out}\nThis usually means local commits "
            f"have diverged from upstream. `git -C {CORE_ROOT} log --oneline @{{upstream}}..HEAD` "
            f"shows them; merge or reset by hand, then run /primer update again.")
    return ["updated the engine (fast-forward pull)"]


def cmd_migrate(args: argparse.Namespace) -> int:
    data_dir = resolve_data_dir(args.data_dir)
    if data_dir is None:
        raise UpdateError("no instance configured — run tools/init-instance.sh first")
    done = migrate_instance(data_dir)
    print("\n".join(f"  - {d}" for d in done) if done
          else f"instance at {data_dir} already current")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    data_dir = resolve_data_dir(args.data_dir)
    print(f"engine version : {local_version()}")
    print(f"engine path    : {CORE_ROOT}")
    print(f"git checkout   : {'yes' if is_git_checkout() else 'no'}")
    print(f"instance       : {data_dir or 'not configured'}")
    if data_dir and (data_dir / "learner").is_dir():
        missing = [t.name for t in sorted(TEMPLATE_DIR.glob("*.md"))
                   if not (data_dir / "learner" / t.name).exists()]
        print(f"missing state  : {', '.join(missing) if missing else 'none'}")
    cache = read_cache()
    print(f"last check     : {cache.get('checked', 'never')}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="primer_update.py",
        description="Check for a newer primer core, install it, and migrate the instance.")
    parser.add_argument("--data-dir", default=None,
                        help="instance root (default: DATA_DIR from ~/.config/primer/config)")
    subs = parser.add_subparsers(dest="cmd", required=True)

    check = subs.add_parser("check", help="is an update available? (cached, always exits 0)")
    check.add_argument("--quiet", action="store_true",
                       help="print only when an update is available (for SKILL.md injection)")
    check.add_argument("--force", action="store_true", help="ignore the cache")
    check.set_defaults(func=cmd_check)

    apply_cmd = subs.add_parser("apply", help="update the core and migrate the instance")
    apply_cmd.add_argument("--instance-only", action="store_true",
                           help="skip the core pull; migrate the instance only")
    apply_cmd.set_defaults(func=cmd_apply)

    subs.add_parser("migrate", help="add state files a newer engine expects").set_defaults(
        func=cmd_migrate)
    subs.add_parser("status", help="versions, paths, and what the instance is missing") \
        .set_defaults(func=cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except UpdateError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
