#!/usr/bin/env python3
"""Unit tests for primer_update. Run: python3 tools/test_primer_update.py

The migration tests matter most: an engine release that adds a state file must not leave
an existing instance broken, and must never overwrite the learner's own data.
"""
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import primer_update as pu

TODAY = date(2026, 7, 30)


def instance(tmp: str, *, learner: bool = True) -> Path:
    root = Path(tmp) / "primer-data"
    if learner:
        (root / "learner").mkdir(parents=True)
    else:
        root.mkdir(parents=True)
    return root


class TestVersion(unittest.TestCase):
    def test_version_file_ships_and_is_parseable(self):
        self.assertTrue(pu.VERSION_FILE.exists(), "core needs a VERSION file")
        self.assertRegex(pu.local_version(), r"^\d+\.\d+\.\d+")

    def test_core_root_points_at_the_repo(self):
        self.assertTrue((pu.CORE_ROOT / "SKILL.md").exists())
        self.assertTrue(pu.TEMPLATE_DIR.is_dir())


class TestMigration(unittest.TestCase):
    def test_adds_state_files_the_instance_predates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = instance(tmp)
            done = pu.migrate_instance(root)
            for template in pu.TEMPLATE_DIR.glob("*.md"):
                self.assertTrue((root / "learner" / template.name).exists(), template.name)
            self.assertTrue(any("source-ledger.md" in d for d in done),
                            "the ledger added by the research layer must be migrated in")

    def test_never_overwrites_existing_learner_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = instance(tmp)
            mine = root / "learner" / "profile.md"
            mine.write_text("# my real profile\nhard-won content\n", encoding="utf-8")
            pu.migrate_instance(root)
            self.assertIn("hard-won content", mine.read_text(encoding="utf-8"))

    def test_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = instance(tmp)
            pu.migrate_instance(root)
            self.assertEqual(pu.migrate_instance(root), [])

    def test_appends_the_gitignore_rule_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = instance(tmp)
            (root / ".gitignore").write_text(".DS_Store\n", encoding="utf-8")
            pu.migrate_instance(root)
            pu.migrate_instance(root)
            text = (root / ".gitignore").read_text(encoding="utf-8")
            self.assertEqual(text.count("lessons/**/*.view.html"), 1)
            self.assertIn(".DS_Store", text)

    def test_creates_the_gitignore_when_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = instance(tmp)
            pu.migrate_instance(root)
            self.assertIn("view.html", (root / ".gitignore").read_text(encoding="utf-8"))

    def test_state_md_is_never_gitignored(self):
        # It is checkpoint state and must cross machines (D-0021).
        self.assertNotIn("STATE.md", " ".join(r for r, _ in pu.GITIGNORE_RULES))

    def test_a_non_instance_directory_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = instance(tmp, learner=False)
            with self.assertRaises(pu.UpdateError) as ctx:
                pu.migrate_instance(root)
            self.assertIn("init-instance.sh", str(ctx.exception))


class TestCheckCache(unittest.TestCase):
    def test_fresh_within_the_ttl(self):
        self.assertTrue(pu.cache_is_fresh({"checked": TODAY.isoformat()}, TODAY))

    def test_stale_past_the_ttl(self):
        old = (TODAY - timedelta(days=pu.CHECK_TTL_DAYS)).isoformat()
        self.assertFalse(pu.cache_is_fresh({"checked": old}, TODAY))

    def test_missing_or_corrupt_stamp_is_stale(self):
        for cache in ({}, {"checked": ""}, {"checked": "not-a-date"}):
            with self.subTest(cache=cache):
                self.assertFalse(pu.cache_is_fresh(cache, TODAY))

    def test_cached_count_tolerates_junk(self):
        self.assertIsNone(pu._cached_count({"behind": "lots"}))
        self.assertIsNone(pu._cached_count({}))
        self.assertEqual(pu._cached_count({"behind": "3"}), 3)


class TestCheckOutput(unittest.TestCase):
    """The notice is injected ahead of a lesson, so it must never fail or get chatty."""

    def setUp(self):
        self._behind = pu.behind_count

    def tearDown(self):
        pu.behind_count = self._behind

    def _check(self, count, detail="stub", quiet=True):
        pu.behind_count = lambda today, force: (count, detail)
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = pu.main(["check", "--quiet"] if quiet else ["check"])
        return rc, buf.getvalue()

    def test_quiet_says_nothing_when_up_to_date(self):
        self.assertEqual(self._check(0), (0, ""))

    def test_quiet_says_nothing_when_it_cannot_tell(self):
        # Offline must read as "don't know" and stay silent — never as up-to-date, and
        # never as an error in front of a learner.
        self.assertEqual(self._check(None, "offline"), (0, ""))

    def test_quiet_announces_an_available_update(self):
        rc, out = self._check(3)
        self.assertEqual(rc, 0)
        self.assertIn("3 update(s) available", out)
        self.assertIn("/primer update", out)

    def test_verbose_always_reports_something(self):
        for count in (0, 2, None):
            with self.subTest(count=count):
                rc, out = self._check(count, quiet=False)
                self.assertEqual(rc, 0)
                self.assertTrue(out.strip())

    def test_an_update_error_during_check_still_exits_zero(self):
        def boom(today, force):
            raise pu.UpdateError("git is not installed")
        pu.behind_count = boom
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(pu.main(["check", "--quiet"]), 0)
        self.assertEqual(buf.getvalue(), "")


class TestCli(unittest.TestCase):
    def test_status_runs_against_an_instance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = instance(tmp)
            self.assertEqual(pu.main(["--data-dir", str(root), "status"]), 0)

    def test_migrate_reports_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = instance(tmp)
            self.assertEqual(pu.main(["--data-dir", str(root), "migrate"]), 0)
            self.assertEqual(pu.main(["--data-dir", str(root), "migrate"]), 0)

    def test_migrate_without_an_instance_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = instance(tmp, learner=False)
            self.assertEqual(pu.main(["--data-dir", str(root), "migrate"]), 1)

    def test_apply_instance_only_does_not_touch_the_core(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = instance(tmp)
            # Redirect the check cache: a test must not write into the real ~/.config.
            original = pu.CHECK_CACHE
            pu.CHECK_CACHE = Path(tmp) / "update-check.json"
            try:
                self.assertEqual(
                    pu.main(["--data-dir", str(root), "apply", "--instance-only"]), 0)
            finally:
                pu.CHECK_CACHE = original
            self.assertTrue((root / "learner" / "source-ledger.md").exists())


if __name__ == "__main__":
    unittest.main(verbosity=1)
