#!/usr/bin/env python3
"""Tests for primer_sync.

Written from the promise the command makes (D-0029): the learner's lesson is stored, only
the engine's own paths are touched, and a failure is never mistaken for a success. Each test
builds a real git repo in a temp dir — the interesting behaviour is entirely in what git
does, so mocking it would test the mock.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import primer_sync as ps


def git(repo, *args, check=True):
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, check=check)


def make_repo(root: Path) -> Path:
    repo = root / "instance"
    (repo / "learner").mkdir(parents=True)
    (repo / "lessons" / "d").mkdir(parents=True)
    git(repo.parent, "init", "-q", "instance")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "t")
    git(repo, "config", "commit.gpgsign", "false")
    (repo / "README.md").write_text("instance\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "init")
    return repo


def make_remote(root: Path, repo: Path) -> Path:
    bare = root / "remote.git"
    git(root, "init", "-q", "--bare", "remote.git")
    git(repo, "remote", "add", "origin", str(bare))
    git(repo, "push", "-q", "-u", "origin", git(repo, "rev-parse", "--abbrev-ref",
                                                "HEAD").stdout.strip())
    return bare


class TestSync(unittest.TestCase):
    def test_a_lesson_and_its_state_are_committed_and_pushed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            repo = make_repo(root)
            make_remote(root, repo)
            (repo / "lessons" / "d" / "2026-07-31-a-topic.md").write_text("# lesson\n")
            (repo / "learner" / "log.md").write_text("entry\n")
            out = ps.sync(repo)
            self.assertTrue(any("committed" in line for line in out), out)
            self.assertTrue(any("pushed" in line for line in out), out)
            # The remote actually has it — the point of the command.
            branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
            remote_files = git(repo, "ls-tree", "-r", "--name-only",
                               f"origin/{branch}").stdout
            self.assertIn("lessons/d/2026-07-31-a-topic.md", remote_files)
            self.assertIn("learner/log.md", remote_files)

    def test_nothing_to_sync_is_reported_not_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            repo = make_repo(Path(d))
            out = ps.sync(repo, push=False)
            self.assertEqual(len(out), 1)
            self.assertIn("nothing to sync", out[0])

    def test_only_engine_owned_paths_are_committed(self):
        # A blanket `add -A` would sweep up whatever the learner happens to be editing.
        with tempfile.TemporaryDirectory() as d:
            repo = make_repo(Path(d))
            (repo / "learner" / "log.md").write_text("entry\n")
            (repo / "scratch.txt").write_text("my own notes, mid-edit\n")
            ps.sync(repo, push=False)
            committed = git(repo, "show", "--name-only", "--format=", "HEAD").stdout
            self.assertIn("learner/log.md", committed)
            self.assertNotIn("scratch.txt", committed)
            self.assertIn("scratch.txt", git(repo, "status", "--porcelain").stdout)

    def test_a_repo_with_no_remote_still_commits_and_says_so(self):
        with tempfile.TemporaryDirectory() as d:
            repo = make_repo(Path(d))
            (repo / "learner" / "log.md").write_text("entry\n")
            out = ps.sync(repo)
            self.assertTrue(any("committed" in line for line in out), out)
            self.assertTrue(any("no remote" in line for line in out), out)

    def test_a_non_repo_is_reported_rather_than_raising(self):
        # A learner who never ran git init should not have a lesson fail at Recap.
        with tempfile.TemporaryDirectory() as d:
            out = ps.sync(Path(d))
            self.assertIn("not a git repo", out[0])

    def test_a_diverged_remote_is_rebased_onto_not_forced_over(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            repo = make_repo(root)
            bare = make_remote(root, repo)
            # Another machine pushes first.
            other = root / "other"
            git(root, "clone", "-q", str(bare), "other")
            git(other, "config", "user.email", "t@example.com")
            git(other, "config", "user.name", "t")
            (other / "learner").mkdir(exist_ok=True)
            (other / "learner" / "profile.md").write_text("from the other machine\n")
            git(other, "add", "-A")
            git(other, "commit", "-q", "-m", "other machine")
            git(other, "push", "-q")

            (repo / "lessons" / "d" / "2026-07-31-mine.md").write_text("# mine\n")
            out = ps.sync(repo)
            self.assertTrue(any("rebased" in line for line in out), out)
            # Both survive. Nothing was clobbered.
            branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
            files = git(repo, "ls-tree", "-r", "--name-only", f"origin/{branch}").stdout
            self.assertIn("lessons/d/2026-07-31-mine.md", files)
            self.assertIn("learner/profile.md", files)

    def test_an_unpushable_remote_still_leaves_the_commit_and_raises(self):
        # The commit must survive a network failure — an unpushed commit is still stored.
        with tempfile.TemporaryDirectory() as d:
            repo = make_repo(Path(d))
            git(repo, "remote", "add", "origin", str(Path(d) / "does-not-exist.git"))
            (repo / "learner" / "log.md").write_text("entry\n")
            with self.assertRaises(ps.SyncError) as ctx:
                ps.sync(repo)
            self.assertIn("safe locally", str(ctx.exception))
            self.assertIn("learner/log.md",
                          git(repo, "show", "--name-only", "--format=", "HEAD").stdout)

    def test_the_message_names_the_lesson(self):
        # `git log` in the instance should read as a learning history.
        msg = ps.default_message(Path("."), ["lessons/d/2026-07-31-async-event-loop.md",
                                             "learner/log.md"])
        self.assertIn("2026-07-31-async-event-loop", msg)
        self.assertTrue(msg.startswith("lesson:"), msg)

    def test_a_state_only_change_gets_a_state_message(self):
        msg = ps.default_message(Path("."), ["learner/review-queue.md"])
        self.assertTrue(msg.startswith("state:"), msg)

    def test_state_sidecars_and_readmes_do_not_become_the_headline(self):
        msg = ps.default_message(Path("."), ["lessons/d/2026-07-31-x.STATE.md",
                                             "lessons/d/README.md", "learner/log.md"])
        self.assertTrue(msg.startswith("state:"), msg)

    def test_cli_exits_non_zero_when_the_push_fails(self):
        # A failed sync must not look like a successful one.
        with tempfile.TemporaryDirectory() as d:
            repo = make_repo(Path(d))
            git(repo, "remote", "add", "origin", str(Path(d) / "nope.git"))
            (repo / "learner" / "log.md").write_text("entry\n")
            self.assertEqual(ps.main(["--data-dir", str(repo)]), 1)

    def test_cli_exits_zero_on_a_clean_sync(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            repo = make_repo(root)
            make_remote(root, repo)
            (repo / "learner" / "log.md").write_text("entry\n")
            self.assertEqual(ps.main(["--data-dir", str(repo)]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=1)
