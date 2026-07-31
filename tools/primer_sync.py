#!/usr/bin/env python3
"""Commit and push the learner's private instance repo.

The instance holds the only copy of a lesson artifact and of the learner model. Leaving it
uncommitted at the end of a lesson puts an unrecoverable loss one crash away, and the
safety of the learner's own data should not depend on anyone remembering to ask. So this
runs automatically at Recap (`SKILL.md` lesson flow, final step) — not on request.

Three properties matter more than the convenience:

**It stages only what the engine owns** — `learner/` and `lessons/`. A blanket `add -A` in
someone's data repo would sweep up whatever else they happen to be editing and commit it
under a lesson's message.

**It never rewrites history and never forces.** On a rejected push it rebases once (the
other machine's commits are the learner's own work) and retries. If that fails it stops and
says so; a data repo is exactly where a clobbering fix is unacceptable.

**It fails loudly and separately from the lesson.** A failed sync must not look like a
successful one, because the whole point is knowing the data is stored. But it also must not
take the lesson down with it, so an unpushed commit is still a *committed* commit.

Python 3.11+, stdlib only, consistent with D-0018.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

# The directories the engine writes. Anything else in the learner's repo is theirs.
OWNED = ("learner", "lessons")


class SyncError(Exception):
    """A sync problem worth telling the learner about."""


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise SyncError(f"git {' '.join(args)} failed: "
                        f"{(proc.stderr or proc.stdout).strip()}")
    return proc


def is_repo(repo: Path) -> bool:
    return git(repo, "rev-parse", "--git-dir", check=False).returncode == 0


def has_remote(repo: Path) -> bool:
    return bool(git(repo, "remote", check=False).stdout.strip())


def pending(repo: Path) -> list[str]:
    """Paths with changes under the directories the engine owns."""
    out = git(repo, "status", "--porcelain", "--", *OWNED).stdout
    return [line[3:].strip() for line in out.splitlines() if line.strip()]


def default_message(repo: Path, changed: list[str]) -> str:
    """A message that says what moved, since this commit is written by a machine.

    Lesson artifacts are the headline; state files are the routine part. Naming the lesson
    makes `git log` in the instance readable as a learning history rather than a wall of
    identical "sync" commits.
    """
    lessons = sorted({Path(p).stem for p in changed
                      if p.startswith("lessons/") and p.endswith(".md")
                      and not p.endswith(".STATE.md") and "README" not in p})
    stamp = date.today().isoformat()
    if not lessons:
        return f"state: update learner model ({stamp})"
    if len(lessons) == 1:
        return f"lesson: {lessons[0]} + state"
    return f"lessons: {', '.join(lessons)} + state"


def sync(repo: Path, message: str | None = None, push: bool = True) -> list[str]:
    """Commit the engine-owned paths and push. Returns human-readable result lines."""
    if not is_repo(repo):
        return [f"not a git repo: {repo} — lessons are on disk but not version-controlled"]

    changed = pending(repo)
    if not changed:
        return ["nothing to sync — instance is already committed"]

    git(repo, "add", "--", *OWNED)
    # Re-check: `add` may have staged nothing if everything was already ignored.
    if not git(repo, "diff", "--cached", "--quiet", check=False).returncode:
        return ["nothing to sync — no staged changes after add"]

    git(repo, "commit", "-q", "-m", message or default_message(repo, changed))
    head = git(repo, "rev-parse", "--short", "HEAD").stdout.strip()
    lines = [f"committed {head}: {len(changed)} path(s)"]

    if not push:
        return lines + ["push skipped (--no-push)"]
    if not has_remote(repo):
        return lines + ["no remote configured — commit is local only"]

    branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if git(repo, "push", "origin", branch, check=False).returncode == 0:
        return lines + [f"pushed to origin/{branch}"]

    # Rejected: another machine got there first. The remote commits are the learner's own
    # work, so rebase onto them and retry once. Never force.
    rebase = git(repo, "pull", "--rebase", "origin", branch, check=False)
    if rebase.returncode != 0:
        git(repo, "rebase", "--abort", check=False)
        raise SyncError(
            f"commit {head} is safe locally, but the push was rejected and the rebase onto "
            f"origin/{branch} did not apply cleanly. Resolve by hand — this is a data repo "
            f"and nothing here will force-push over the other machine's work.")
    if git(repo, "push", "origin", branch, check=False).returncode != 0:
        raise SyncError(
            f"commit {head} is safe locally, but the push still failed after rebasing onto "
            f"origin/{branch}. Push by hand when the network or credentials allow.")
    return lines + [f"rebased onto origin/{branch} and pushed"]


def resolve_data_dir(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser()
    cfg = Path.home() / ".config" / "primer" / "config"
    if cfg.exists():
        for line in cfg.read_text().splitlines():
            if line.startswith("DATA_DIR="):
                return Path(line.split("=", 1)[1].strip()).expanduser()
    raise SyncError("no --data-dir given and no DATA_DIR in ~/.config/primer/config")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Commit and push the private primer instance (runs at Recap).")
    p.add_argument("--data-dir", default=None)
    p.add_argument("--message", default=None, help="override the generated commit message")
    p.add_argument("--no-push", action="store_true", help="commit only")
    args = p.parse_args(argv)
    try:
        for line in sync(resolve_data_dir(args.data_dir), args.message, not args.no_push):
            print(line)
    except SyncError as exc:
        # Non-zero so a caller notices, and phrased so the learner knows what is and is not
        # stored — a silent failure here is the one outcome the command exists to prevent.
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
