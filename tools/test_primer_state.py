#!/usr/bin/env python3
"""Unit tests for primer_state. Stdlib unittest — run: python3 tools/test_primer_state.py"""
import tempfile
import unittest
from datetime import date
from pathlib import Path

import primer_state as ps

TODAY = date(2026, 6, 16)


class TestSM2(unittest.TestCase):
    def test_first_success_is_one_day(self):
        s = ps.sm2(reps=0, interval=0, ef=2.5, quality=4, today=TODAY)
        self.assertEqual(s.reps, 1)
        self.assertEqual(s.interval, ps.FIRST_INTERVAL)
        self.assertEqual(s.due, date(2026, 6, 17))

    def test_second_success_is_six_days(self):
        s = ps.sm2(reps=1, interval=1, ef=2.5, quality=4, today=TODAY)
        self.assertEqual(s.reps, 2)
        self.assertEqual(s.interval, ps.SECOND_INTERVAL)

    def test_third_success_grows_by_ease(self):
        # reps>=2: interval = round(prev_interval * ef)
        s = ps.sm2(reps=2, interval=6, ef=2.5, quality=4, today=TODAY)
        self.assertEqual(s.interval, 15)  # round(6 * 2.5) before ef adjust; ef at q4 unchanged
        self.assertEqual(s.reps, 3)

    def test_lapse_resets(self):
        s = ps.sm2(reps=5, interval=100, ef=2.2, quality=1, today=TODAY)
        self.assertEqual(s.reps, 0)
        self.assertEqual(s.interval, ps.FIRST_INTERVAL)
        self.assertEqual(s.due, date(2026, 6, 17))

    def test_ease_floor(self):
        # Repeated hard grades must not drive ef below the floor.
        ef = 1.3
        for _ in range(5):
            ef = ps.sm2(reps=2, interval=6, ef=ef, quality=3, today=TODAY).ef
        self.assertGreaterEqual(ef, ps.EF_MIN)

    def test_quality_from_label(self):
        self.assertEqual(ps.quality_from_label("good"), 4)
        self.assertEqual(ps.quality_from_label("FAIL"), 1)
        self.assertEqual(ps.quality_from_label("5"), 5)
        with self.assertRaises(ValueError):
            ps.quality_from_label("nope")


class TestPromptRoundTrip(unittest.TestCase):
    def test_parse_format_roundtrip(self):
        line = ("- due:2026-06-20 | int:6 | ef:2.50 | reps:3 | distributed-systems "
                "| Q:: What does Raft guarantee? | A:: At most one leader per term.")
        p = ps.parse_prompt(line)
        self.assertIsNotNone(p)
        self.assertEqual(p.domain, "distributed-systems")
        self.assertEqual(p.reps, 3)
        self.assertEqual(ps.format_prompt(p), line)

    def test_non_prompt_line_ignored(self):
        self.assertIsNone(ps.parse_prompt("## Prompts"))
        self.assertIsNone(ps.parse_prompt("- 2026-06-16 | 5/7 correct"))

    def test_new_prompt_due_today_unseen(self):
        p = ps.new_prompt("docker", "Q?", "A.", TODAY)
        self.assertEqual(p.due, TODAY)
        self.assertEqual(p.reps, 0)
        self.assertEqual(p.ef, ps.EF_DEFAULT)


class TestQueueOps(unittest.TestCase):
    def setUp(self):
        self.lines = [
            "# Review Queue", "", "## Prompts", "",
            "- due:2026-06-10 | int:6 | ef:2.50 | reps:2 | docker | Q:: q-old | A:: a",
            "- due:2026-07-01 | int:30 | ef:2.50 | reps:4 | docker | Q:: q-future | A:: a",
            "", "## Review history", "",
        ]

    def test_due_excludes_future(self):
        due = ps.due_prompts(self.lines, TODAY)
        self.assertEqual(len(due), 1)
        self.assertEqual(due[0][1].question, "q-old")

    def test_insert_prompt_under_header(self):
        out = ps.insert_prompt(self.lines, ps.new_prompt("ai", "newq", "newa", TODAY))
        prompts = [p for _, p in ps.find_prompts(out)]
        self.assertIn("newq", [p.question for p in prompts])
        # placed in the Prompts section, before Review history
        self.assertLess(out.index(ps.format_prompt(ps.new_prompt("ai", "newq", "newa", TODAY))),
                        out.index("## Review history"))


class TestDecay(unittest.TestCase):
    def test_stale_high_decays(self):
        line = "| dist | 2026-01-01 | solid on raft | high | lesson 2026-01-01 |"
        new_line, change = ps.decay_marker_line(line, TODAY, ps.DECAY_THRESHOLD_DAYS)
        self.assertIn("| med |", new_line)
        self.assertIn("reprobe", new_line)
        self.assertIsNotNone(change)
        # 'updated' date must not be bumped — decay is absence of evidence.
        self.assertIn("2026-01-01", new_line)

    def test_recent_high_unchanged(self):
        line = "| dist | 2026-06-10 | x | high | y |"
        new_line, change = ps.decay_marker_line(line, TODAY, ps.DECAY_THRESHOLD_DAYS)
        self.assertEqual(new_line, line)
        self.assertIsNone(change)

    def test_low_confidence_untouched(self):
        line = "| dist | 2026-01-01 | x | low | y |"
        _, change = ps.decay_marker_line(line, TODAY, ps.DECAY_THRESHOLD_DAYS)
        self.assertIsNone(change)


class TestRecalibrate(unittest.TestCase):
    def test_fires_on_misses(self):
        calib = [f"2026-06-1{i} | dist | too-advanced | x | y" for i in range(4)]
        d = ps.recalibrate_check(log_lines=[], calib_lines=calib)
        self.assertTrue(d.fire)
        self.assertEqual(d.misses, 4)

    def test_fires_on_lesson_cap(self):
        log = [f"2026-06-{10 + i:02d} | lesson | 60m | x" for i in range(8)]
        d = ps.recalibrate_check(log_lines=log, calib_lines=[])
        self.assertTrue(d.fire)
        self.assertEqual(d.lessons, 8)

    def test_below_thresholds_no_fire(self):
        log = ["2026-06-11 | lesson | 60m | x", "2026-06-12 | lesson | 60m | x"]
        calib = ["2026-06-11 | dist | pacing | x | y"]
        d = ps.recalibrate_check(log_lines=log, calib_lines=calib)
        self.assertFalse(d.fire)

    def test_counts_only_after_last_recalibrate(self):
        log = [
            "2026-06-01 | lesson | 60m | x",
            "2026-06-05 | recalibrate-minor | 3m | reset",
            "2026-06-10 | lesson | 60m | x",
        ]
        calib = ["2026-06-02 | d | x | y | z", "2026-06-11 | d | x | y | z"]
        d = ps.recalibrate_check(log_lines=log, calib_lines=calib)
        self.assertEqual(d.lessons, 1)  # only the 06-10 lesson, after the recalibrate
        self.assertEqual(d.misses, 1)   # only the 06-11 miss


class TestCLI(unittest.TestCase):
    """End-to-end: grade a due prompt through the CLI and confirm it reschedules."""
    def test_grade_reschedules_in_file(self):
        with tempfile.TemporaryDirectory() as d:
            data = Path(d)
            (data / "learner").mkdir()
            q = data / "learner" / "review-queue.md"
            q.write_text(
                "# Review Queue\n\n## Prompts\n\n"
                "- due:2026-06-10 | int:6 | ef:2.50 | reps:2 | docker | Q:: q | A:: a\n\n"
                "## Review history\n\n"
            )
            rc = ps.main(["--data-dir", str(data), "--on", "2026-06-16",
                          "review-grade", "--index", "0", "--quality", "good"])
            self.assertEqual(rc, 0)
            after = ps.due_prompts(q.read_text().splitlines(), date(2026, 7, 1))
            self.assertEqual(len(after), 1)
            self.assertGreater(after[0][1].interval, 6)   # interval grew
            self.assertEqual(after[0][1].reps, 3)


class TestHatchTrend(unittest.TestCase):
    """The escape hatch is right to have; an unnoticed *rise* in its use is the problem."""

    LOG = [f"2026-07-{d:02d} | lesson | 60m | a lesson" for d in range(10, 22)]

    def hatch(self, day: int, domain: str) -> str:
        return (f"2026-07-{day:02d} | {domain} | {ps.HATCH_TYPE} | "
                f"learner asked for the answer directly | note")

    def test_no_hatches_is_no_trend(self):
        self.assertEqual(ps.hatch_trend([], self.LOG), [])

    def test_rate_is_per_lesson_not_per_day(self):
        # A learner who takes a month off has not become more dependent.
        calib = [self.hatch(20, "docker"), self.hatch(21, "docker")]
        trends = ps.hatch_trend(calib, self.LOG, window=10)
        self.assertEqual((trends[0].domain, trends[0].hatches), ("docker", 2))
        self.assertEqual(trends[0].lessons, 10)
        self.assertAlmostEqual(trends[0].rate, 0.2)

    def test_window_excludes_older_uses(self):
        calib = [self.hatch(10, "docker"), self.hatch(21, "docker")]
        trends = ps.hatch_trend(calib, self.LOG, window=3)
        self.assertEqual(trends[0].hatches, 1)

    def test_sorted_by_rate_then_domain(self):
        calib = [self.hatch(20, "docker"), self.hatch(21, "docker"),
                 self.hatch(21, "consensus")]
        trends = ps.hatch_trend(calib, self.LOG, window=10)
        self.assertEqual([t.domain for t in trends], ["docker", "consensus"])

    def test_other_miss_types_are_not_counted(self):
        other = "2026-07-21 | docker | vocabulary-gap | used a term early | define first"
        self.assertEqual(ps.hatch_trend([other], self.LOG), [])

    def test_malformed_lines_are_ignored(self):
        for bad in ("", "not a log line", f"nodate | d | {ps.HATCH_TYPE} | x | y",
                    f"2026-07-21 | {ps.HATCH_TYPE}"):
            with self.subTest(line=bad):
                self.assertEqual(ps.hatch_trend([bad], self.LOG), [])

    def test_zero_lessons_does_not_divide_by_zero(self):
        self.assertEqual(ps.hatch_trend([self.hatch(21, "d")], []), [])

    def test_hatch_use_counts_toward_the_recalibrate_trigger(self):
        # Repeated hatch use means the register is mis-set, which is exactly what the
        # minor recalibrate exists to correct — so it should fire it.
        calib = [self.hatch(18 + i, "docker") for i in range(4)]
        decision = ps.recalibrate_check(self.LOG, calib)
        self.assertTrue(decision.fire)

    def test_log_then_trend_round_trips_through_the_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            learner = Path(tmp) / "learner"
            learner.mkdir(parents=True)
            (learner / "calibration-log.md").write_text("# Calibration log\n")
            (learner / "log.md").write_text("\n".join(self.LOG) + "\n")
            argv = ["--data-dir", tmp, "--on", "2026-07-21"]
            self.assertEqual(ps.main([*argv, "hatch-log", "--domain", "docker"]), 0)
            self.assertEqual(ps.main([*argv, "hatch-trend"]), 0)
            calib = (learner / "calibration-log.md").read_text().splitlines()
            self.assertEqual(len(ps.hatch_trend(calib, self.LOG)), 1)



class TestTemplateFormatsMatchTheParsers(unittest.TestCase):
    """The templates document formats that this module parses. Drift between them breaks
    the state layer for NEW instances only — the worst place for it, because the
    maintainer's own instance keeps working and never surfaces the bug.

    This is exactly what happened: templates/learner/log.md documented the second field as
    `<domain>` while DATED_RE keys on a `<mode>` token, so a fresh instance would have had
    a recalibrate trigger that silently never fired and an escape-hatch trend with no
    denominator.
    """

    TEMPLATES = Path(__file__).resolve().parent.parent / "templates" / "learner"

    def template(self, name: str) -> str:
        path = self.TEMPLATES / name
        self.assertTrue(path.exists(), f"missing template {name}")
        return path.read_text()

    def test_log_documents_a_mode_field_not_a_domain(self):
        text = self.template("log.md")
        self.assertIn("<mode>", text)
        self.assertNotRegex(text, r"Format:.*\| <domain> \|")

    def test_log_names_every_mode_token_the_code_keys_on(self):
        text = self.template("log.md")
        # `lesson` is what recalibrate-check and hatch-trend count; the recalibrate tokens
        # are what reset the counting window.
        for token in ("`lesson`", "recalibrate-minor"):
            self.assertIn(token, text, f"log.md must document the {token} mode")

    def test_the_logs_own_example_line_parses_as_a_lesson(self):
        example = self.example_line(self.template("log.md"), "lesson |")
        m = ps.DATED_RE.match(example)
        self.assertIsNotNone(m, f"log.md's example does not parse: {example!r}")
        self.assertEqual(m["mode"], "lesson")

    def test_the_logs_example_counts_toward_the_recalibrate_trigger(self):
        example = self.example_line(self.template("log.md"), "lesson |")
        self.assertEqual(ps._count_after([example], None, mode="lesson"), 1)

    def test_review_queue_example_parses_with_the_prompt_regex(self):
        text = self.template("review-queue.md")
        # The template documents the shape with placeholders; build a concrete line from
        # the same field order and assert the parser accepts it.
        line = ("- due:2026-07-30 | int:6 | ef:2.50 | reps:2 | distributed-systems | "
                "Q:: what is the safety property? | A:: at most one entry per index")
        self.assertIn("due:<YYYY-MM-DD>", text)
        self.assertIsNotNone(ps.parse_prompt(line))

    def test_topic_index_example_marker_row_parses(self):
        text = self.template("topic-index.md")
        rows = [l.strip() for l in text.splitlines()
                if l.strip().startswith("|") and "low" in l and "---" not in l]
        self.assertTrue(rows, "topic-index.md should document an example marker row")
        concrete = rows[0].replace("<domain>", "docker").replace("<date>", "2026-07-30") \
            .replace("<one-line depth>", "builds multi-stage images")
        self.assertIsNotNone(ps.MARKER_RE.match(concrete),
                             f"documented marker row does not parse: {concrete!r}")

    def test_calibration_log_documents_every_token_the_code_writes(self):
        # Wave B added HATCH_TYPE to the code and to feedback-protocol.md but not to this
        # template's miss-type list — the same drift class as the log.md <mode> bug, so it
        # gets the same kind of test rather than a one-off fix.
        text = self.template("calibration-log.md")
        self.assertIn(ps.HATCH_TYPE, text,
                      "calibration-log.md must document the token hatch-log writes")
        self.assertIn("examiner-disagree", text,
                      "calibration-log.md must document the examiner's token")

    def test_calibration_log_field_order_matches_the_hatch_parser(self):
        text = self.template("calibration-log.md")
        self.assertIn("<date> | <domain> | <miss-type>", text)
        entry = f"2026-07-30 | docker | {ps.HATCH_TYPE} | asked outright | lower tolerance"
        self.assertEqual(ps._hatch_entry(entry), (date(2026, 7, 30), "docker"))

    def test_every_template_the_code_reads_exists(self):
        for name in ("log.md", "calibration-log.md", "review-queue.md", "topic-index.md"):
            with self.subTest(template=name):
                self.assertTrue((self.TEMPLATES / name).exists())

    @staticmethod
    def example_line(text: str, contains: str) -> str:
        for line in text.splitlines():
            stripped = line.strip().strip("`")
            if contains in stripped and stripped[:4].isdigit():
                return stripped
        raise AssertionError(f"no example line containing {contains!r}")



if __name__ == "__main__":
    unittest.main(verbosity=2)
