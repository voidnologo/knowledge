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



class TestSeparatorForgery(unittest.TestCase):
    """The assertion that would have caught the entry-forgery exploit: write a value,
    re-read the file, and require the entry count to be unchanged.

    `str.splitlines()` breaks on eleven code points. A `FORBIDDEN` list of ("|","\\n","\\r")
    let eight through, and a separator inside a `--why` or `--url` value wrote one line
    that the next read saw as two — the forged entry inheriting the honest record's tail
    (fresh `checked`, `floor:yes`, `verdict:cite`), landing it in the floor a future lesson
    reads as its citation set.
    """

    BREAKERS = ["\n", "\r", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85",
                " ", " "]

    def test_every_splitlines_breaker_is_rejected(self):
        for ch in self.BREAKERS:
            with self.subTest(char=repr(ch)):
                with self.assertRaises(ps.LedgerError):
                    ps.clean(f"before{ch}after", "why")

    def test_no_breaker_can_forge_an_entry_through_why(self):
        for ch in self.BREAKERS:
            with self.subTest(char=repr(ch)):
                with tempfile.TemporaryDirectory() as tmp:
                    root = fresh_ledger(tmp)
                    run(root, *ADD)
                    payload = f"legit{ch}- url:https://evil.test/floor"
                    rc = run(root, "sources-add", "--url", "https://b.dev",
                             "--domain", "d", "--why", payload)
                    self.assertEqual(rc, 1)
                    lines = (root / "learner" / "source-ledger.md").read_text().splitlines()
                    urls = [s.url for s in ps.read_sources(lines)]
                    self.assertEqual(urls, ["https://jepsen.io/analyses"])

    def test_no_breaker_can_forge_an_entry_through_url(self):
        for ch in self.BREAKERS:
            with self.subTest(char=repr(ch)):
                with self.assertRaises(ps.LedgerError):
                    ps.clean_url(f"https://ok.test/a{ch}- url:https://evil.test/floor")

    def test_no_breaker_can_forge_a_heading(self):
        # A forged `## Domain sweeps` bound _section_bounds to an empty section and
        # orphaned the real one, erasing the whole cached-sweep layer.
        with tempfile.TemporaryDirectory() as tmp:
            root = fresh_ledger(tmp)
            run(root, "sweep-record", "--domain", "d")
            rc = run(root, "sources-add", "--url", "https://b.dev", "--domain", "d",
                     "--why", "note ## Domain sweeps")
            self.assertEqual(rc, 1)
            lines = (root / "learner" / "source-ledger.md").read_text().splitlines()
            self.assertEqual([s.domain for s in ps.read_sweeps(lines)], ["d"])

    def test_control_characters_are_rejected(self):
        for ch, why in (("\t", "forges output columns"), ("\x1b", "terminal escapes"),
                        ("\x00", "makes the ledger binary to git")):
            with self.subTest(char=repr(ch), why=why):
                with self.assertRaises(ps.LedgerError):
                    ps.clean(f"a{ch}b", "why")

    def test_duplicate_heading_is_refused_rather_than_losing_half_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fresh_ledger(tmp)
            path = root / "learner" / "source-ledger.md"
            path.write_text(path.read_text() + "\n## Sources\n\n---\n")
            with self.assertRaises(ps.LedgerError) as ctx:
                ps.read_sources(path.read_text().splitlines())
            self.assertIn("headings", str(ctx.exception))

    def test_scheme_is_enforced_on_the_read_path_too(self):
        # clean_url ran only on write, so a hand-edited or already-corrupted ledger could
        # serve a javascript: URL into sources_consulted.
        line = ("- url:javascript:alert(1) | domain:d | tag:verified | verdict:cite | "
                "seen:2026-01-01 | checked:2026-01-01 | floor:no | used:1 | why:w")
        with self.assertRaises(ps.LedgerError):
            ps.parse_source(line)


class TestStrictParsing(unittest.TestCase):
    """Permissive defaults rewrote the ledger: `floor:Yes` became `floor:no`, erasing a
    promotion; a `tags:` typo became `tag:verified`, laundering an ungrounded source."""

    GOOD = ("- url:https://a.dev | domain:d | tag:from-training | verdict:caveat | "
            "seen:2026-01-01 | checked:2026-07-01 | floor:yes | used:3 | why:w")

    def test_the_good_line_parses(self):
        src = ps.parse_source(self.GOOD)
        self.assertEqual((src.tag, src.verdict, src.floor, src.used),
                         ("from-training", "caveat", True, 3))

    def test_floor_is_case_insensitive_but_bounded(self):
        self.assertTrue(ps.parse_source(self.GOOD.replace("floor:yes", "floor:YES")).floor)
        for bad in ("floor:true", "floor:y", "floor:maybe", "floor:"):
            with self.subTest(value=bad):
                with self.assertRaises(ps.LedgerError):
                    ps.parse_source(self.GOOD.replace("floor:yes", bad))

    def test_typoed_or_unknown_keys_are_refused(self):
        for bad in ("tags:from-training", "verdic:caveat", "why:w | reviewer:caleb"):
            with self.subTest(field=bad):
                mangled = self.GOOD.replace("tag:from-training", "tags:from-training") \
                    if bad.startswith("tags") else self.GOOD
                if bad.startswith("verdic"):
                    mangled = self.GOOD.replace("verdict:caveat", "verdic:caveat")
                if bad.startswith("why"):
                    mangled = self.GOOD + " | reviewer:caleb"
                with self.assertRaises(ps.LedgerError):
                    ps.parse_source(mangled)

    def test_bad_enum_values_are_refused(self):
        for field, bad in (("tag:from-training", "tag:trustme"),
                           ("verdict:caveat", "verdict:probably")):
            with self.subTest(bad=bad):
                with self.assertRaises(ps.LedgerError):
                    ps.parse_source(self.GOOD.replace(field, bad))

    def test_used_must_be_a_plain_non_negative_integer(self):
        for bad in ("used:three", "used:-3", "used:1_000", "used:٣", "used:",
                    "used:" + "9" * 4400):
            with self.subTest(bad=bad):
                with self.assertRaises(ps.LedgerError):
                    ps.parse_source(self.GOOD.replace("used:3", bad))

    def test_checked_before_seen_is_refused(self):
        with self.assertRaises(ps.LedgerError):
            ps.parse_source(self.GOOD.replace("checked:2026-07-01", "checked:2025-01-01"))

    def test_future_on_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fresh_ledger(tmp)
            rc = ps.main(["--data-dir", str(root), "--on", "2099-01-01", *ADD])
            self.assertEqual(rc, 1)

    def test_parse_errors_name_the_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fresh_ledger(tmp)
            run(root, *ADD)
            path = root / "learner" / "source-ledger.md"
            path.write_text(path.read_text().replace("checked:2026-07-30",
                                                     "checked:31-12-2026"))
            with self.assertRaises(ps.LedgerError) as ctx:
                ps.read_sources(path.read_text().splitlines())
            self.assertIn("line ", str(ctx.exception))


class TestProsePreservation(unittest.TestCase):
    def test_fenced_format_documentation_is_not_parsed_as_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fresh_ledger(tmp)
            path = root / "learner" / "source-ledger.md"
            path.write_text(path.read_text().replace(
                "<sources appended here>",
                "My notes: a.dev is the one I keep coming back to.\n\n"
                "```\n- url:<url> | domain:<d> | example only\n```\n"))
            run(root, *ADD)
            after = path.read_text()
            self.assertIn("```", after)
            self.assertIn("- url:<url> | domain:<d> | example only", after)
            self.assertIn("My notes: a.dev", after)
            urls = [s.url for s in ps.read_sources(after.splitlines())]
            self.assertEqual(urls, ["https://jepsen.io/analyses"])

    def test_indented_bullet_is_prose_not_data(self):
        line = "  - url:https://a.dev | domain:d"
        self.assertIsNone(ps.parse_source(line))

    def test_domain_sweeps_prose_survives_a_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fresh_ledger(tmp)
            path = root / "learner" / "source-ledger.md"
            run(root, *ADD)
            after = path.read_text()
            for marker in ("Format: `- domain:", "*narrow* top-up", "## Domain sweeps"):
                self.assertIn(marker, after, marker)

    def test_curated_trailing_note_keeps_its_position(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fresh_ledger(tmp)
            path = root / "learner" / "source-ledger.md"
            path.write_text(path.read_text().replace(
                "<sources appended here>", "<sources appended here>\n\nTrailing note."))
            for i in range(3):
                run(root, "sources-add", "--url", f"https://a{i}.dev", "--domain", "d",
                    "--why", "w")
            body = path.read_text().split("\n## Sources\n")[1].split("\n## Domain sweeps\n")[0]
            self.assertLess(body.index("https://a0.dev"), body.index("Trailing note."))

    def test_repeated_writes_are_structurally_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fresh_ledger(tmp)
            path = root / "learner" / "source-ledger.md"
            shapes = set()
            for i in range(20):
                run(root, "sources-add", "--url", f"https://a{i}.dev", "--domain",
                    f"d{i % 3}", "--why", "w")
                text = path.read_text()
                shapes.add(tuple(l for l in text.splitlines()
                                 if not l.startswith("- url:")))
            self.assertEqual(len(shapes), 1, "non-data shape drifted across writes")
            self.assertEqual(len(ps.read_sources(path.read_text().splitlines())), 20)


class TestCrossDomain(unittest.TestCase):
    def test_the_same_url_can_belong_to_two_domains(self):
        # A spec or a Jepsen report is legitimately cited from two domains; URL-only
        # identity removed it from the first domain's floor on the second citation.
        with tempfile.TemporaryDirectory() as tmp:
            root = fresh_ledger(tmp)
            run(root, "sources-add", "--url", "https://a.dev", "--domain",
                "distributed-systems", "--why", "consensus", "--floor")
            run(root, "sources-add", "--url", "https://a.dev", "--domain", "containers",
                "--why", "image layers", "--floor")
            lines = (root / "learner" / "source-ledger.md").read_text().splitlines()
            sources = ps.read_sources(lines)
            self.assertEqual(len(sources), 2)
            self.assertEqual(len(ps.floor_for(sources, "distributed-systems")), 1)
            self.assertEqual(len(ps.floor_for(sources, "containers")), 1)

    def test_floor_with_dropped_verdict_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fresh_ledger(tmp)
            rc = run(root, "sources-add", "--url", "https://a.dev", "--domain", "d",
                     "--verdict", "dropped", "--why", "superseded", "--floor")
            self.assertEqual(rc, 1)

if __name__ == "__main__":
    unittest.main(verbosity=1)
