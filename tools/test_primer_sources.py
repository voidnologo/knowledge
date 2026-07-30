#!/usr/bin/env python3
"""Unit tests for primer_sources. Stdlib unittest — run: python3 tools/test_primer_sources.py

Hostile-input tests are here from the first commit, not bolted on after a review. The Wave A
lesson: values that come from web pages and model output will contain delimiters, and 56
passing tests were consistent with six exploitable holes because nothing adversarial was
tried. Ledger values are pipe-delimited, so a stray '|' or newline is the whole attack.
"""
import tempfile
import unittest
from datetime import date
from pathlib import Path

import primer_sources as ps

TODAY = date(2026, 7, 30)
TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "learner" / "source-ledger.md"


def fresh_ledger(tmp: str) -> Path:
    """An instance scaffolded from the real template, so the tests exercise the shipped shape."""
    root = Path(tmp)
    (root / "learner").mkdir(parents=True, exist_ok=True)
    path = root / "learner" / "source-ledger.md"
    path.write_text(TEMPLATE.read_text())
    return root


def run(root: Path, *argv: str) -> int:
    return ps.main(["--data-dir", str(root), "--on", TODAY.isoformat(), *argv])


ADD = ("sources-add", "--url", "https://jepsen.io/analyses", "--domain",
       "distributed-systems", "--why", "empirical consistency teardowns")


class TestParsing(unittest.TestCase):
    def test_round_trips_a_line(self):
        src = ps.Source(url="https://x.dev/a?b=1#c", domain="d", tag="verified",
                        verdict="cite", seen=date(2026, 1, 1), checked=TODAY,
                        floor=True, used=3, why="because")
        again = ps.parse_source(src.to_line())
        self.assertEqual(again, src)

    def test_url_scheme_colon_survives_the_field_split(self):
        line = "- url:https://a.dev/x | domain:d | tag:verified | verdict:cite | " \
               "seen:2026-01-01 | checked:2026-01-01 | floor:no | used:1 | why:w"
        self.assertEqual(ps.parse_source(line).url, "https://a.dev/x")

    def test_ignores_prose_and_headings(self):
        for line in ("## Sources", "", "some prose about url: things", "---",
                     "<sources appended here>"):
            self.assertIsNone(ps.parse_source(line))

    def test_missing_section_is_an_actionable_error(self):
        with self.assertRaises(ps.LedgerError) as ctx:
            ps.read_sources(["# Not a ledger", "just prose"])
        self.assertIn("scaffolded from", str(ctx.exception))

    def test_bad_date_is_reported_not_crashed(self):
        line = "- url:https://a.dev | domain:d | tag:verified | verdict:cite | " \
               "seen:not-a-date | checked:2026-01-01 | floor:no | used:1 | why:w"
        with self.assertRaises(ps.LedgerError):
            ps.parse_source(line)


class TestHostileInput(unittest.TestCase):
    """Values come from web pages and model output. A delimiter must never get through."""

    def test_pipe_in_any_field_is_rejected(self):
        for field, value in (("why", "a | b"), ("domain", "dist|sys")):
            with self.subTest(field=field):
                with self.assertRaises(ps.LedgerError) as ctx:
                    ps.clean(value, field)
                self.assertIn("pipe-delimited", str(ctx.exception))

    def test_newline_is_rejected(self):
        for value in ("a\nb", "a\rb", "a\r\nb"):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ps.LedgerError):
                    ps.clean(value, "why")

    def test_url_with_a_pipe_is_rejected(self):
        with self.assertRaises(ps.LedgerError):
            ps.clean_url("https://a.dev/x|y")

    def test_non_web_schemes_are_rejected(self):
        for url in ("javascript:alert(1)", "data:text/html,<script>x</script>",
                    "ftp://a.dev/x", "a.dev/x", "//a.dev/x"):
            with self.subTest(url=url):
                with self.assertRaises(ps.LedgerError) as ctx:
                    ps.clean_url(url)
                self.assertIn("must start with", str(ctx.exception))

    def test_overlong_field_is_rejected(self):
        with self.assertRaises(ps.LedgerError):
            ps.clean("x" * (ps.MAX_FIELD + 1), "why")

    def test_empty_required_field_is_rejected(self):
        for value in ("", "   ", None):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ps.LedgerError):
                    ps.clean(value, "domain")

    def test_bad_enum_values_are_rejected(self):
        with self.assertRaises(ps.LedgerError):
            ps.one_of("probably", ps.VERDICTS, "verdict")

    def test_hostile_why_cannot_corrupt_the_file_via_the_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fresh_ledger(tmp)
            self.assertEqual(run(root, *ADD), 0)
            rc = run(root, "sources-add", "--url", "https://b.dev", "--domain", "d",
                     "--why", "sneaky | url:https://evil.dev | verdict:cite")
            self.assertEqual(rc, 1)
            lines = (root / "learner" / "source-ledger.md").read_text().splitlines()
            self.assertEqual(len(ps.read_sources(lines)), 1)


class TestUpsert(unittest.TestCase):
    def test_add_then_readd_accrues_rather_than_duplicating(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fresh_ledger(tmp)
            run(root, *ADD)
            run(root, *ADD)
            sources = ps.read_sources((root / "learner" / "source-ledger.md")
                                      .read_text().splitlines())
            self.assertEqual(len(sources), 1)
            self.assertEqual(sources[0].used, 2)

    def test_readd_keeps_the_earliest_seen_and_refreshes_checked(self):
        old = ps.Source(url="https://a.dev", domain="d", tag="verified", verdict="cite",
                        seen=date(2026, 1, 1), checked=date(2026, 1, 1), floor=False,
                        used=4, why="w")
        new = ps.replace(old, seen=TODAY, checked=TODAY, used=1)
        merged, action = ps.upsert_source([old], new)
        self.assertEqual(action, "updated")
        self.assertEqual(merged[0].seen, date(2026, 1, 1))
        self.assertEqual(merged[0].checked, TODAY)
        self.assertEqual(merged[0].used, 5)

    def test_readd_does_not_demote_a_floor_source(self):
        old = ps.Source(url="https://a.dev", domain="d", tag="verified", verdict="cite",
                        seen=TODAY, checked=TODAY, floor=True, used=1, why="w")
        merged, _ = ps.upsert_source([old], ps.replace(old, floor=False))
        self.assertTrue(merged[0].floor)

    def test_rewrite_preserves_surrounding_prose(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fresh_ledger(tmp)
            path = root / "learner" / "source-ledger.md"
            before = path.read_text()
            run(root, *ADD)
            after = path.read_text()
            for marker in ("# Source Ledger", "accreted floor", "## Domain sweeps",
                           "Format: `- domain:"):
                self.assertIn(marker, after, marker)
            self.assertIn("jepsen.io", after)
            self.assertNotIn(ps.PLACEHOLDER, after.split("## Domain sweeps")[0])
            self.assertNotEqual(before, after)

    def test_sections_do_not_bleed_into_each_other(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fresh_ledger(tmp)
            run(root, *ADD)
            run(root, "sweep-record", "--domain", "distributed-systems")
            lines = (root / "learner" / "source-ledger.md").read_text().splitlines()
            self.assertEqual(len(ps.read_sources(lines)), 1)
            self.assertEqual(len(ps.read_sweeps(lines)), 1)
            # A sweep line must not be parsed as a source, nor vice versa.
            self.assertEqual([s.domain for s in ps.read_sweeps(lines)],
                             ["distributed-systems"])

    def test_many_adds_stay_parseable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fresh_ledger(tmp)
            for i in range(12):
                run(root, "sources-add", "--url", f"https://a{i}.dev/x",
                    "--domain", f"d{i % 3}", "--why", f"reason {i}")
            lines = (root / "learner" / "source-ledger.md").read_text().splitlines()
            self.assertEqual(len(ps.read_sources(lines)), 12)


class TestQueries(unittest.TestCase):
    def setUp(self):
        mk = lambda url, **kw: ps.Source(
            url=url, domain=kw.get("domain", "d"), tag=kw.get("tag", "verified"),
            verdict=kw.get("verdict", "cite"), seen=date(2026, 1, 1),
            checked=kw.get("checked", TODAY), floor=kw.get("floor", False),
            used=kw.get("used", 1), why="w")
        self.sources = [
            mk("https://fresh.dev"),
            mk("https://old.dev", checked=date(2026, 1, 1), used=7),
            mk("https://older.dev", checked=date(2025, 12, 1), used=2),
            mk("https://dropped.dev", checked=date(2025, 1, 1), verdict="dropped"),
            mk("https://ungrounded.dev", tag="from-training"),
            mk("https://floor.dev", floor=True, used=5),
            mk("https://otherfloor.dev", floor=True, domain="other"),
        ]

    def test_stale_excludes_dropped_and_orders_by_use(self):
        found = ps.stale_sources(self.sources, TODAY, ps.FRESH_DAYS)
        self.assertEqual([s.url for s in found],
                         ["https://old.dev", "https://older.dev"])

    def test_fresh_source_is_not_stale(self):
        self.assertFalse(self.sources[0].is_stale(TODAY))

    def test_unverified_lists_only_from_training(self):
        self.assertEqual([s.url for s in ps.unverified(self.sources)],
                         ["https://ungrounded.dev"])

    def test_floor_filters_by_domain(self):
        self.assertEqual([s.url for s in ps.floor_for(self.sources, "d")],
                         ["https://floor.dev"])
        self.assertEqual(len(ps.floor_for(self.sources, None)), 2)

    def test_sweep_due_when_never_swept(self):
        due, why = ps.sweep_due([], "distributed-systems", TODAY, 60)
        self.assertTrue(due)
        self.assertIn("no recorded sweep", why)

    def test_sweep_fresh_says_to_do_a_narrow_top_up(self):
        sweeps = [ps.Sweep(domain="d", swept=date(2026, 7, 20), note="n")]
        due, why = ps.sweep_due(sweeps, "d", TODAY, 60)
        self.assertFalse(due)
        self.assertIn("narrow top-up", why)

    def test_sweep_due_past_the_horizon(self):
        sweeps = [ps.Sweep(domain="d", swept=date(2026, 1, 1), note="n")]
        due, _ = ps.sweep_due(sweeps, "d", TODAY, 60)
        self.assertTrue(due)


class TestCli(unittest.TestCase):
    def test_check_reports_unknown_then_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fresh_ledger(tmp)
            self.assertEqual(run(root, "sources-check", "--url",
                                 "https://jepsen.io/analyses"), 0)
            run(root, *ADD)
            self.assertEqual(run(root, "sources-check", "--url",
                                 "https://jepsen.io/analyses"), 0)

    def test_promote_then_floor_lists_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fresh_ledger(tmp)
            run(root, *ADD)
            self.assertEqual(run(root, "sources-promote", "--url",
                                 "https://jepsen.io/analyses"), 0)
            sources = ps.read_sources((root / "learner" / "source-ledger.md")
                                      .read_text().splitlines())
            self.assertTrue(sources[0].floor)

    def test_promote_unknown_url_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fresh_ledger(tmp)
            self.assertEqual(run(root, "sources-promote", "--url", "https://nope.dev"), 1)

    def test_promote_refuses_a_dropped_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fresh_ledger(tmp)
            run(root, "sources-add", "--url", "https://stale.dev", "--domain", "d",
                "--verdict", "dropped", "--why", "superseded by the 2nd edition")
            self.assertEqual(run(root, "sources-promote", "--url", "https://stale.dev"), 1)

    def test_stale_and_unverified_and_floor_run_clean_on_an_empty_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fresh_ledger(tmp)
            for cmd in ("sources-stale", "sources-unverified", "sources-floor"):
                with self.subTest(cmd=cmd):
                    self.assertEqual(run(root, cmd), 0)

    def test_stale_finds_a_backdated_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fresh_ledger(tmp)
            ps.main(["--data-dir", str(root), "--on", "2026-01-01", *ADD])
            self.assertEqual(run(root, "sources-stale"), 0)
            lines = (root / "learner" / "source-ledger.md").read_text().splitlines()
            self.assertEqual(len(ps.stale_sources(ps.read_sources(lines), TODAY, 90)), 1)

    def test_missing_ledger_is_an_actionable_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "learner").mkdir()
            self.assertEqual(run(root, "sources-stale"), 1)

    def test_sweep_record_then_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fresh_ledger(tmp)
            self.assertEqual(run(root, "sweep-check", "--domain", "docker"), 0)
            self.assertEqual(run(root, "sweep-record", "--domain", "docker"), 0)
            lines = (root / "learner" / "source-ledger.md").read_text().splitlines()
            due, _ = ps.sweep_due(ps.read_sweeps(lines), "docker", TODAY, 60)
            self.assertFalse(due)

    def test_bad_url_via_cli_exits_nonzero_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fresh_ledger(tmp)
            path = root / "learner" / "source-ledger.md"
            before = path.read_text()
            self.assertEqual(run(root, "sources-add", "--url", "javascript:alert(1)",
                                 "--domain", "d", "--why", "w"), 1)
            self.assertEqual(path.read_text(), before)


if __name__ == "__main__":
    unittest.main(verbosity=1)
