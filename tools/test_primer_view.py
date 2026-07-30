#!/usr/bin/env python3
"""Unit tests for primer_view. Stdlib unittest — run: python3 tools/test_primer_view.py

The validator tests matter most: they are the reason the Primer can hand a learner a
page without eyeballing it first. Each one breaks a good page in one specific way and
asserts the corresponding check fires.
"""
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import primer_view as pv

SEQUENCE = {
    "id": "raft-partition", "type": "sequence",
    "caption": "Leader isolated in a minority partition.",
    "invariant": "A leader without a majority cannot advance the commit index.",
    "blank": ["m3"], "reveal": "The majority-side ack; safety holds by refusing to commit.",
    "spec": {
        "participants": [{"id": "L", "label": "Leader"}, {"id": "F1", "label": "Follower"},
                         {"id": "F2", "label": "Follower (isolated)"}],
        "messages": [{"id": "m1", "from": "L", "to": "F1", "label": "AppendEntries"},
                     {"id": "m2", "from": "F1", "to": "L", "label": "ack", "dashed": True},
                     {"id": "m3", "from": "L", "to": "F2", "label": "AppendEntries",
                      "lost": True}],
        "notes": [{"id": "n1", "after": "m3", "over": "F2", "label": "timeout fires"}],
    },
}

STATE = {
    "id": "raft-roles", "type": "state", "caption": "Raft role lifecycle.",
    "invariant": "There is no path from follower to leader that skips an election.",
    "blank": ["t-illegal"],
    "reveal": "None — the transition does not exist; a follower must win an election.",
    "spec": {
        "states": [{"id": "f", "label": "Follower", "initial": True},
                   {"id": "c", "label": "Candidate"}, {"id": "l", "label": "Leader"}],
        "transitions": [{"id": "t1", "from": "f", "to": "c", "label": "election timeout"},
                        {"id": "t2", "from": "c", "to": "l", "label": "majority vote"}],
        "illegal": [{"id": "t-illegal", "from": "f", "to": "l", "label": "never"}],
    },
}

QUORUM = {
    "id": "split", "type": "quorum", "caption": "Five nodes, 2/3 split.",
    "invariant": "Only the side holding a majority can make progress.",
    "blank": ["progress"], "reveal": "The three-node side; the leader's side cannot.",
    "spec": {
        "nodes": [{"id": "a", "label": "n1", "leader": True}, {"id": "b", "label": "n2"},
                  {"id": "c", "label": "n3"}, {"id": "d", "label": "n4"},
                  {"id": "e", "label": "n5"}],
        "partition": [["a", "b"], ["c", "d", "e"]], "progress": "right",
    },
}

LAYERS = {
    "id": "path", "type": "layers", "caption": "Request path and trust boundary.",
    "invariant": "Authentication happens above the boundary, so the API must re-check.",
    "spec": {"layers": [{"label": "Client"}, {"label": "Edge"},
                        {"label": "API", "detail": "authn here"}, {"label": "Postgres"}],
             "boundary_after": 1, "boundary_label": "trust boundary"},
}

CURVE = {
    "id": "util", "type": "curve", "caption": "Latency against utilization.",
    "invariant": "Latency diverges as utilization approaches 1.",
    "blank": ["tail"], "reveal": "It goes to infinity — headroom is a latency decision.",
    "spec": {"x": {"label": "rho", "min": 0, "max": 1},
             "y": {"label": "latency", "min": 0, "max": 20},
             "series": [{"label": "M/M/1", "points": [[0, 1], [0.5, 2], [0.8, 5],
                                                      [0.9, 10], [0.95, 20]]}],
             "annotate": [{"x": 0.8, "label": "the knee"}]},
}

TIMELINE = {
    "id": "gc", "type": "timeline", "caption": "GC pause overlapping a request.",
    "invariant": "A stop-the-world pause lands inside the request, so p99 tracks GC.",
    "blank": ["s2"], "reveal": "It overlaps — the request pays the whole pause.",
    "spec": {"actors": [{"id": "req", "label": "request"}, {"id": "gc", "label": "GC"}],
             "spans": [{"id": "s1", "actor": "req", "start": 0, "end": 40, "label": "p50"},
                       {"id": "s2", "actor": "gc", "start": 25, "end": 70,
                        "label": "stop-the-world"}],
             "unit": "ms"},
}

EXPLORABLE = {
    "id": "queue", "caption": "Queue wait against utilization.",
    "invariant": "Wait is not linear in load.",
    "predict": "At what utilization does wait double?",
    "contract": {"inputs": [{"id": "rho", "label": "rho", "min": 0.05, "max": 0.95,
                             "step": 0.01, "value": 0.5}],
                 "outputs": [{"id": "wait", "label": "queue wait", "decimals": 2},
                             {"id": "head", "label": "headroom", "decimals": 2}]},
    "formulas": {"wait": "rho / (1 - rho)", "head": "0.95 - rho"},
}

ALL_FIGURES = [SEQUENCE, STATE, QUORUM, LAYERS, CURVE, TIMELINE]


def artifact_text(*blocks: dict) -> str:
    """A minimal lesson artifact carrying the given spec blocks."""
    out = ["# Consensus without implementing Paxos", ""]
    for block in blocks:
        kind = "explorable" if "contract" in block else "figure"
        out.append(f"<!--primer-{kind}\n{json.dumps(block)}\n-->")
        out.append("")
    return "\n".join(out)


def good_page(*blocks: dict) -> str:
    blocks = blocks or (SEQUENCE,)
    return pv.build_page(artifact_text(*blocks), Path("2026-07-30-consensus.md")).html


class TestExtraction(unittest.TestCase):
    def test_extracts_both_kinds(self):
        blocks = pv.extract_blocks(artifact_text(SEQUENCE, EXPLORABLE))
        self.assertEqual([b.kind for b in blocks], ["figure", "explorable"])
        self.assertEqual(blocks[0].id, "raft-partition")

    def test_ignores_ordinary_markdown(self):
        self.assertEqual(pv.extract_blocks("# Title\n\nSome prose.\n"), [])

    def test_bad_json_is_a_spec_error(self):
        with self.assertRaises(pv.SpecError) as ctx:
            pv.extract_blocks("<!--primer-figure {not json} -->")
        self.assertIn("not valid JSON", str(ctx.exception))

    def test_empty_spec_fails_at_the_first_missing_field(self):
        blocks = pv.extract_blocks("<!--primer-figure {} -->")
        with self.assertRaises(pv.SpecError) as ctx:
            pv.figure_html(blocks[0].spec)
        self.assertIn("missing required field 'type'", str(ctx.exception))


class TestTemplates(unittest.TestCase):
    def test_every_form_emits_wellformed_svg(self):
        for spec in ALL_FIGURES:
            with self.subTest(form=spec["type"]):
                svg = pv.RENDERERS[spec["type"]](spec["spec"], set(spec.get("blank", [])),
                                                 spec["id"])
                ET.fromstring(svg)  # raises on malformed output

    def test_all_six_forms_are_covered_by_fixtures(self):
        self.assertEqual({s["type"] for s in ALL_FIGURES}, set(pv.FIGURE_TYPES))

    def test_blanked_message_label_is_replaced(self):
        svg = pv.render_sequence(SEQUENCE["spec"], {"m3"}, "f")
        self.assertIn(">?<", svg)
        # The blanked message's own label must not survive anywhere in the figure.
        self.assertEqual(svg.count("AppendEntries"), 1)

    def test_unblanked_figure_keeps_its_labels(self):
        svg = pv.render_sequence(SEQUENCE["spec"], set(), "f")
        self.assertEqual(svg.count("AppendEntries"), 2)

    def test_unknown_participant_is_a_spec_error(self):
        spec = json.loads(json.dumps(SEQUENCE["spec"]))
        spec["messages"][0]["to"] = "nope"
        with self.assertRaises(pv.SpecError) as ctx:
            pv.render_sequence(spec, set(), "f")
        self.assertIn("unknown participant", str(ctx.exception))

    def test_curve_needs_two_points(self):
        spec = json.loads(json.dumps(CURVE["spec"]))
        spec["series"][0]["points"] = [[0, 1]]
        with self.assertRaises(pv.SpecError):
            pv.render_curve(spec, set(), "f")

    def test_missing_required_field_is_a_spec_error(self):
        with self.assertRaises(pv.SpecError) as ctx:
            pv.render_layers({}, set(), "f")
        self.assertIn("missing required field 'layers'", str(ctx.exception))


class TestBlanking(unittest.TestCase):
    def test_blankable_ids_per_form(self):
        self.assertEqual(pv.blankable_ids(SEQUENCE), {"m1", "m2", "m3", "n1"})
        self.assertEqual(pv.blankable_ids(STATE), {"t1", "t2", "t-illegal"})
        self.assertEqual(pv.blankable_ids(QUORUM), {"progress"})
        self.assertEqual(pv.blankable_ids(LAYERS), {"boundary"})
        self.assertEqual(pv.blankable_ids(CURVE), {"tail"})
        self.assertEqual(pv.blankable_ids(TIMELINE), {"s1", "s2"})

    def test_unknown_blank_id_is_rejected_not_ignored(self):
        spec = dict(SEQUENCE, blank=["typo"])
        with self.assertRaises(pv.SpecError) as ctx:
            pv.figure_html(spec)
        self.assertIn("match nothing blankable", str(ctx.exception))

    def test_blank_without_reveal_is_rejected(self):
        spec = {k: v for k, v in SEQUENCE.items() if k != "reveal"}
        with self.assertRaises(pv.SpecError) as ctx:
            pv.figure_html(spec)
        self.assertIn("'reveal'", str(ctx.exception))

    def test_unknown_type_is_rejected(self):
        with self.assertRaises(pv.SpecError) as ctx:
            pv.figure_html(dict(SEQUENCE, type="pie-chart"))
        self.assertIn("unknown type", str(ctx.exception))


class TestFormulas(unittest.TestCase):
    def test_compiles_inputs_and_functions(self):
        js = pv.compile_formula("max(rho, 0.1) / (1 - rho)", {"rho"}, "wait")
        self.assertEqual(js, 'Math.max(v["rho"],0.1)/(1-v["rho"])')

    def test_rejects_unknown_name(self):
        with self.assertRaises(pv.SpecError) as ctx:
            pv.compile_formula("rho * fetch", {"rho"}, "wait")
        self.assertIn("unknown name 'fetch'", str(ctx.exception))

    def test_rejects_arbitrary_js(self):
        for hostile in ("window.location", "eval(1)", "this", "a=>1"):
            with self.subTest(expr=hostile):
                with self.assertRaises(pv.SpecError):
                    pv.compile_formula(hostile, {"rho"}, "wait")

    def test_rejects_power_operator_with_a_hint(self):
        with self.assertRaises(pv.SpecError) as ctx:
            pv.compile_formula("rho ** 2", {"rho"}, "wait")
        self.assertIn("pow(a,b)", str(ctx.exception))

    def test_rejects_empty(self):
        with self.assertRaises(pv.SpecError):
            pv.compile_formula("   ", {"rho"}, "wait")


class TestExplorableContract(unittest.TestCase):
    def test_compiles(self):
        compiled = pv.compile_explorable(EXPLORABLE)
        self.assertEqual(set(compiled["js"]), {"wait", "head"})

    def test_output_without_formula_is_rejected(self):
        spec = json.loads(json.dumps(EXPLORABLE))
        del spec["formulas"]["head"]
        with self.assertRaises(pv.SpecError) as ctx:
            pv.compile_explorable(spec)
        self.assertIn("without a formula", str(ctx.exception))

    def test_formula_for_undeclared_output_is_rejected(self):
        spec = json.loads(json.dumps(EXPLORABLE))
        spec["formulas"]["ghost"] = "rho"
        with self.assertRaises(pv.SpecError) as ctx:
            pv.compile_explorable(spec)
        self.assertIn("undeclared outputs", str(ctx.exception))

    def test_three_inputs_rejected(self):
        spec = json.loads(json.dumps(EXPLORABLE))
        spec["contract"]["inputs"] += [{"id": "b", "label": "b"}, {"id": "c", "label": "c"}]
        with self.assertRaises(pv.SpecError) as ctx:
            pv.compile_explorable(spec)
        self.assertIn("at most 2 inputs", str(ctx.exception))

    def test_missing_predict_rejected(self):
        spec = {k: v for k, v in EXPLORABLE.items() if k != "predict"}
        with self.assertRaises(pv.SpecError):
            pv.compile_explorable(spec)


class TestPageBuild(unittest.TestCase):
    def test_builds_and_validates_every_form(self):
        html = good_page(*ALL_FIGURES, EXPLORABLE)
        passed = pv.validate_page(html)
        self.assertEqual(len(passed), 5)

    def test_manifest_lists_every_block(self):
        page = pv.build_page(artifact_text(SEQUENCE, EXPLORABLE), Path("l.md"))
        ids = [f["id"] for f in page.manifest["figures"]]
        self.assertEqual(ids, ["raft-partition", "queue"])

    def test_manifest_does_not_carry_the_answer(self):
        html = good_page(SEQUENCE)
        manifest = pv._read_manifest(html)
        self.assertNotIn("reveal", manifest["figures"][0])
        self.assertNotIn("refusing to commit", json.dumps(manifest))

    def test_no_blocks_is_an_error(self):
        with self.assertRaises(pv.SpecError) as ctx:
            pv.build_page("# Just prose\n", Path("l.md"))
        self.assertIn("nothing to render", str(ctx.exception))

    def test_title_comes_from_the_artifact_heading(self):
        html = good_page(SEQUENCE)
        self.assertIn("Consensus without implementing Paxos", html)

    def test_two_explorables_both_validate(self):
        second = json.loads(json.dumps(EXPLORABLE))
        second["id"] = "queue2"
        pv.validate_page(good_page(EXPLORABLE, second))


class TestValidator(unittest.TestCase):
    """Each test breaks a good page in one way and asserts the right check fires."""

    def test_rejects_page_without_manifest(self):
        with self.assertRaises(pv.ValidationError) as ctx:
            pv.validate_page("<html><body>hand-written</body></html>")
        self.assertIn("no pv-manifest", str(ctx.exception))

    def test_catches_malformed_svg(self):
        html = good_page(SEQUENCE).replace("</svg>", "", 1)
        with self.assertRaises(pv.ValidationError) as ctx:
            pv.validate_page(html)
        self.assertIn("well-formedness", str(ctx.exception))

    def test_catches_external_script(self):
        html = good_page(SEQUENCE).replace(
            "</head>", '<script src="https://cdn.example.com/mermaid.js"></script></head>')
        with self.assertRaises(pv.ValidationError) as ctx:
            pv.validate_page(html)
        self.assertIn("external", str(ctx.exception))

    def test_catches_external_stylesheet(self):
        html = good_page(SEQUENCE).replace("</head>", '<link rel="stylesheet"></head>')
        with self.assertRaises(pv.ValidationError):
            pv.validate_page(html)

    def test_catches_remote_font_import(self):
        html = good_page(SEQUENCE).replace("<style>", "<style>@import 'x';", 1)
        with self.assertRaises(pv.ValidationError):
            pv.validate_page(html)

    def test_svg_namespace_is_not_flagged_as_external(self):
        pv.validate_page(good_page(SEQUENCE))  # xmlns is a URI, not a fetch

    def test_catches_missing_caption(self):
        html = good_page(SEQUENCE).replace(
            "<figcaption>Leader isolated in a minority partition.</figcaption>",
            "<figcaption></figcaption>")
        with self.assertRaises(pv.ValidationError) as ctx:
            pv.validate_page(html)
        self.assertIn("caption", str(ctx.exception))

    def test_catches_details_left_open(self):
        html = good_page(SEQUENCE).replace("<details>", "<details open>", 1)
        with self.assertRaises(pv.ValidationError) as ctx:
            pv.validate_page(html)
        self.assertIn("marked open", str(ctx.exception))

    def test_catches_reveal_moved_outside_the_gate(self):
        html = good_page(SEQUENCE)
        html = html.replace('<details><summary>I have committed to a prediction'
                            ' — reveal</summary>\n', "")
        html = html.replace("</details>\n", "", 1)
        with self.assertRaises(pv.ValidationError) as ctx:
            pv.validate_page(html)
        self.assertIn("figure 'raft-partition'", str(ctx.exception))

    def test_catches_reveal_duplicated_outside_the_gate(self):
        html = good_page(SEQUENCE).replace(
            '<div class="fig-body">',
            '<p class="reveal">spoiler</p><div class="fig-body">', 1)
        with self.assertRaises(pv.ValidationError) as ctx:
            pv.validate_page(html)
        self.assertIn("outside the gate", str(ctx.exception))

    def test_catches_unwired_input(self):
        html = good_page(EXPLORABLE).replace(
            'document.getElementById("in-queue-rho").addEventListener("input", u);', "")
        with self.assertRaises(pv.ValidationError) as ctx:
            pv.validate_page(html)
        self.assertIn("never listened to", str(ctx.exception))

    def test_catches_unwritten_output(self):
        html = good_page(EXPLORABLE).replace(
            'document.getElementById("out-queue-head").textContent =', "var unused =")
        with self.assertRaises(pv.ValidationError) as ctx:
            pv.validate_page(html)
        self.assertIn("never written", str(ctx.exception))

    def test_catches_missing_readout_element(self):
        html = good_page(EXPLORABLE).replace('id="out-queue-wait"', 'id="typo"')
        with self.assertRaises(pv.ValidationError) as ctx:
            pv.validate_page(html)
        self.assertIn("no readout", str(ctx.exception))

    def test_catches_explorable_widget_left_ungated(self):
        html = good_page(EXPLORABLE)
        html = html.replace('<details><summary>I have made my prediction'
                            ' — show the model</summary>\n', "")
        with self.assertRaises(pv.ValidationError):
            pv.validate_page(html)


class TestAscii(unittest.TestCase):
    def test_renders_the_four_supported_forms(self):
        for spec in (SEQUENCE, LAYERS, QUORUM, TIMELINE):
            with self.subTest(form=spec["type"]):
                out = pv.ascii_figure(spec)
                self.assertTrue(out.strip())
                self.assertNotIn("view page only", out)

    def test_unsupported_forms_say_so_rather_than_failing(self):
        out = pv.ascii_figure(CURVE)
        self.assertIn("view page only", out)

    def test_sequence_marks_a_lost_message(self):
        self.assertIn("╳", pv.ascii_figure(SEQUENCE))

    def test_blanks_are_honoured_so_the_terminal_does_not_spoil_the_page(self):
        # The blanked m3 label must not reach the terminal; the unblanked m1 must.
        out = pv.ascii_figure(SEQUENCE)
        self.assertEqual(out.count("AppendEntries"), 1)
        self.assertIn("?", out)

    def test_timeline_blank_hides_the_span_label(self):
        out = pv.ascii_figure(TIMELINE)
        self.assertNotIn("stop-the-world", out)
        self.assertIn("p50", out)

    def test_layers_blank_hides_the_boundary_label(self):
        blanked = pv.ascii_figure(dict(LAYERS, blank=["boundary"],
                                       reveal="the trust boundary"))
        self.assertNotIn("trust boundary", blanked)
        self.assertIn("trust boundary", pv.ascii_figure(LAYERS))

    def test_quorum_progress_blank_withholds_the_verdict(self):
        self.assertNotIn("can make progress", pv.ascii_figure(QUORUM))
        unblanked = pv.ascii_figure({k: v for k, v in QUORUM.items() if k != "blank"})
        self.assertIn("can make progress", unblanked)


class TestCli(unittest.TestCase):
    def test_render_writes_and_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "2026-07-30-consensus.md"
            artifact.write_text(artifact_text(*ALL_FIGURES, EXPLORABLE), encoding="utf-8")
            self.assertEqual(pv.main(["render", str(artifact)]), 0)
            page = Path(tmp) / "2026-07-30-consensus.view.html"
            self.assertTrue(page.exists())
            self.assertEqual(pv.main(["validate", str(page)]), 0)

    def test_render_of_a_bad_spec_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "bad.md"
            artifact.write_text(artifact_text(dict(SEQUENCE, blank=["nope"])),
                               encoding="utf-8")
            self.assertEqual(pv.main(["render", str(artifact)]), 1)
            self.assertFalse((Path(tmp) / "bad.view.html").exists())

    def test_ascii_by_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "l.md"
            artifact.write_text(artifact_text(SEQUENCE, LAYERS), encoding="utf-8")
            self.assertEqual(pv.main(["ascii", str(artifact), "--id", "path"]), 0)
            self.assertEqual(pv.main(["ascii", str(artifact), "--id", "ghost"]), 2)

    def test_templates_lists_every_form(self):
        self.assertEqual(pv.main(["templates"]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=1)
