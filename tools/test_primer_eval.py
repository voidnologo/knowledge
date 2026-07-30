#!/usr/bin/env python3
"""Unit tests for primer_eval. Run: python3 tools/test_primer_eval.py

The load-bearing assertions: an unrun trap must never score as a pass (that would
understate the failure rate this eval exists to measure), and scoring must stay
pressure-resolved rather than collapsing to one number.
"""
import json
import tempfile
import unittest
from pathlib import Path

import primer_eval as pe


def results_file(tmp: str, rows: list[dict]) -> Path:
    path = Path(tmp) / "results.json"
    path.write_text(json.dumps({"results": rows}), encoding="utf-8")
    return path


class TestTrapSet(unittest.TestCase):
    def test_the_shipped_set_loads(self):
        traps = pe.load_traps()
        self.assertGreaterEqual(len(traps), 12)

    def test_all_three_pressure_modes_are_covered(self):
        modes = {t.pressure for t in pe.load_traps().values()}
        self.assertEqual(modes, {"context-switch", "authority", "social-affective"})

    def test_low_confidence_context_switch_is_represented(self):
        # The measured weak point for Claude models, and the shape primer's register
        # invites — the set is useless if it doesn't probe there.
        traps = pe.load_traps().values()
        weak = [t for t in traps if t.pressure == "context-switch" and t.confidence == 1]
        self.assertGreaterEqual(len(weak), 3)

    def test_more_than_one_domain(self):
        self.assertGreater(len({t.domain for t in pe.load_traps().values()}), 3)

    def test_malformed_trap_sets_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, payload in (
                ("not json", "{nope"),
                ("no traps", json.dumps({"traps": []})),
                ("trap not an object", json.dumps({"traps": ["x"]})),
                ("missing fields", json.dumps({"traps": [{"id": "a"}]})),
                ("bad pressure", json.dumps({
                    "pressure_modes": {"authority": ""},
                    "traps": [{"id": "a", "domain": "d", "misconception": "m",
                               "correct": "c", "frame": "f", "pressure": "nope",
                               "confidence": 1}]})),
                ("bad confidence", json.dumps({
                    "traps": [{"id": "a", "domain": "d", "misconception": "m",
                               "correct": "c", "frame": "f", "pressure": "authority",
                               "confidence": 9}]})),
            ):
                with self.subTest(case=name):
                    path = Path(tmp) / "t.json"
                    path.write_text(payload, encoding="utf-8")
                    with self.assertRaises(pe.EvalError):
                        pe.load_traps(path)

    def test_duplicate_ids_are_refused(self):
        trap = {"id": "a", "domain": "d", "misconception": "m", "correct": "c",
                "frame": "f", "pressure": "authority", "confidence": 1}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.json"
            path.write_text(json.dumps({"traps": [trap, dict(trap)]}), encoding="utf-8")
            with self.assertRaises(pe.EvalError) as ctx:
                pe.load_traps(path)
            self.assertIn("duplicate", str(ctx.exception))

    def test_missing_file_is_reported(self):
        with self.assertRaises(pe.EvalError):
            pe.load_traps(Path("/nonexistent/traps.json"))


class TestResults(unittest.TestCase):
    def setUp(self):
        self.traps = pe.load_traps()
        self.ids = list(self.traps)

    def test_unrun_traps_must_not_be_scored_as_passes(self):
        # The whole point: `held: null` is not "it held".
        with tempfile.TemporaryDirectory() as tmp:
            path = results_file(tmp, [{"trap": self.ids[0], "held": None}])
            with self.assertRaises(pe.EvalError) as ctx:
                pe.load_results(path, self.traps)
            self.assertIn("understate", str(ctx.exception))

    def test_unknown_trap_id_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = results_file(tmp, [{"trap": "ghost", "held": True}])
            with self.assertRaises(pe.EvalError):
                pe.load_results(path, self.traps)

    def test_empty_results_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = results_file(tmp, [])
            with self.assertRaises(pe.EvalError):
                pe.load_results(path, self.traps)

    def test_a_bare_array_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.json"
            path.write_text(json.dumps([{"trap": self.ids[0], "held": True}]),
                            encoding="utf-8")
            self.assertEqual(len(pe.load_results(path, self.traps)), 1)


class TestScoring(unittest.TestCase):
    def setUp(self):
        self.traps = pe.load_traps()

    def outcomes(self, spec: dict[str, bool]) -> list[pe.Outcome]:
        return [pe.Outcome(trap=self.traps[tid], held=held, note="")
                for tid, held in spec.items()]

    def test_rate_counts_capitulations_not_passes(self):
        by_mode = {t.pressure: t.id for t in self.traps.values()}
        outcomes = self.outcomes({by_mode["authority"]: False,
                                  by_mode["context-switch"]: True})
        overall = pe.score(outcomes)["overall"][0]
        self.assertEqual((overall.failed, overall.total), (1, 2))
        self.assertAlmostEqual(overall.rate, 0.5)

    def test_pressure_modes_are_reported_separately(self):
        cs = [t.id for t in self.traps.values() if t.pressure == "context-switch"][:2]
        auth = [t.id for t in self.traps.values() if t.pressure == "authority"][:2]
        outcomes = self.outcomes({cs[0]: False, cs[1]: False,
                                  auth[0]: True, auth[1]: True})
        groups = pe.score(outcomes)
        modes = {c.label: c.rate for c in groups["by pressure mode"]}
        self.assertAlmostEqual(modes["context-switch"], 1.0)
        self.assertAlmostEqual(modes["authority"], 0.0)
        # An aggregate of 50% would hide a mode failing every time.
        self.assertAlmostEqual(groups["overall"][0].rate, 0.5)

    def test_confidence_is_a_reporting_axis(self):
        low = [t.id for t in self.traps.values() if t.confidence == 1][:2]
        outcomes = self.outcomes({low[0]: False, low[1]: False})
        labels = [c.label for c in pe.score(outcomes)["by learner confidence"]]
        self.assertIn("confidence 1", labels)

    def test_worst_cell_sorts_first(self):
        cs = [t.id for t in self.traps.values() if t.pressure == "context-switch"][:1]
        auth = [t.id for t in self.traps.values() if t.pressure == "authority"][:1]
        outcomes = self.outcomes({cs[0]: False, auth[0]: True})
        self.assertEqual(pe.score(outcomes)["by pressure mode"][0].label, "context-switch")

    def test_thin_cells_are_flagged(self):
        one = list(self.traps)[0]
        cell = pe.score(self.outcomes({one: False}))["overall"][0]
        self.assertTrue(cell.thin)
        self.assertIn("thin", cell.line())

    def test_coverage_gaps_are_named_rather_than_silent(self):
        one = list(self.traps)[0]
        gaps = pe.coverage_gaps(self.traps, self.outcomes({one: True}))
        self.assertTrue(gaps)
        self.assertIn("not run", gaps[0])

    def test_no_gaps_when_everything_ran(self):
        all_held = {tid: True for tid in self.traps}
        self.assertEqual(pe.coverage_gaps(self.traps, self.outcomes(all_held)), [])


class TestCli(unittest.TestCase):
    def test_list_and_template_run(self):
        self.assertEqual(pe.main(["list"]), 0)
        self.assertEqual(pe.main(["list", "--pressure", "context-switch"]), 0)
        self.assertEqual(pe.main(["list", "--domain", "nope"]), 0)
        self.assertEqual(pe.main(["template"]), 0)

    def test_template_output_is_a_valid_shape_for_score(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            pe.main(["template"])
        data = json.loads(buf.getvalue())
        rows = [dict(r, held=True) for r in data["results"]]
        with tempfile.TemporaryDirectory() as tmp:
            path = results_file(tmp, rows)
            self.assertEqual(pe.main(["score", str(path)]), 0)

    def test_score_of_a_bad_file_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.json"
            path.write_text("{nope", encoding="utf-8")
            self.assertEqual(pe.main(["score", str(path)]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=1)
