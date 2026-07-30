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

    def test_empty_spec_fails_with_an_actionable_message(self):
        blocks = pv.extract_blocks("<!--primer-figure {} -->")
        with self.assertRaises(pv.SpecError) as ctx:
            pv.figure_html(blocks[0].spec)
        self.assertIn("figure id", str(ctx.exception))

    def test_missing_type_is_named(self):
        with self.assertRaises(pv.SpecError) as ctx:
            pv.figure_html({"id": "x"})
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
        self.assertEqual(len(passed), 6)

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
        html = good_page(SEQUENCE).replace(
            "</head>", '<link rel="stylesheet" href="https://x.example/a.css"></head>')
        with self.assertRaises(pv.ValidationError):
            pv.validate_page(html)

    def test_catches_srcset_and_poster_and_object_data(self):
        for tag in ('<img srcset="https://x.example/p.png 1x">',
                    '<video poster="https://x.example/p.jpg"></video>',
                    '<object data="https://x.example/o.swf"></object>',
                    '<meta http-equiv="refresh" content="0;url=https://x.example/">'):
            with self.subTest(tag=tag):
                html = good_page(SEQUENCE).replace("</header>", f"</header>{tag}")
                with self.assertRaises(pv.ValidationError):
                    pv.validate_page(html)

    def test_catches_inline_event_handler(self):
        html = good_page(SEQUENCE).replace('<div class="wrap">',
                                           '<div class="wrap" onmouseover="x()">')
        with self.assertRaises(pv.ValidationError) as ctx:
            pv.validate_page(html)
        self.assertIn("event handler", str(ctx.exception))

    def test_catches_network_calls_in_script(self):
        for js in ("fetch('/x')", "new XMLHttpRequest()", "eval('x')",
                   "navigator.sendBeacon('/x')"):
            with self.subTest(js=js):
                html = good_page(SEQUENCE).replace("<script>", f"<script>{js};", 1)
                with self.assertRaises(pv.ValidationError):
                    pv.validate_page(html)

    def test_protocol_relative_css_url_is_caught(self):
        html = good_page(SEQUENCE).replace("<style>", "<style>a{background:url(//h/x)}", 1)
        with self.assertRaises(pv.ValidationError):
            pv.validate_page(html)

    def test_data_uri_is_allowed(self):
        html = good_page(SEQUENCE).replace(
            "</header>", '</header><img src="data:image/gif;base64,R0lGODlhAQABAAAAADs=">')
        pv.validate_page(html)  # data: is inline, not a network hop

    def test_prose_about_html_does_not_false_positive(self):
        # A lesson *about* HTML legitimately contains attribute-shaped text. The old
        # whole-document regex reported these as external references.
        for prose in ("The href='/next' attribute drives the redirect",
                      "Use @import sparingly", "src='x' is relative to the document",
                      "url(https://cdn.example/x) in CSS costs a round trip"):
            with self.subTest(prose=prose):
                pv.validate_page(good_page(dict(SEQUENCE, caption=prose)))

    def test_csp_meta_is_present_and_permitted(self):
        html = good_page(SEQUENCE)
        self.assertIn("Content-Security-Policy", html)
        self.assertIn("default-src 'none'", html)
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


class TestHostileStrings(unittest.TestCase):
    """Spec strings are model-authored and can carry markup. None may reach the DOM."""

    def test_caption_containing_a_comment_terminator_cannot_break_the_manifest(self):
        # `-->` is Mermaid edge syntax, so a lesson about diagrams may well contain it.
        html = good_page(dict(SEQUENCE, caption="The A --> B replication edge"))
        self.assertEqual(html.count("-->"), 1)
        pv.validate_page(html)

    def test_script_in_a_caption_is_escaped_not_executed(self):
        hostile = "x --><script>fetch('https://evil.example/')</script><!-- y"
        html = good_page(dict(SEQUENCE, caption=hostile))
        self.assertNotIn("<script>fetch", html)
        self.assertIn("&lt;script&gt;", html)
        pv.validate_page(html)

    def test_hostile_reveal_and_invariant_are_escaped(self):
        for key in ("reveal", "invariant"):
            with self.subTest(key=key):
                html = good_page(dict(SEQUENCE, **{key: '--><img src="https://e/x">'}))
                self.assertEqual(html.count("-->"), 1)
                pv.validate_page(html)

    def test_hostile_slider_bounds_are_rejected_as_non_numeric(self):
        for field, hostile in (("min", '0" onfocus="fetch(1)" x="'),
                               ("max", '1"><img srcset="https://e/p.png 1x'),
                               ("step", "x"), ("value", "{}")):
            with self.subTest(field=field):
                spec = json.loads(json.dumps(EXPLORABLE))
                spec["contract"]["inputs"][0][field] = hostile
                with self.assertRaises(pv.SpecError) as ctx:
                    pv.compile_explorable(spec)
                self.assertIn("must be a number", str(ctx.exception))

    def test_ids_must_match_a_safe_character_set(self):
        for bad in ("rho\nx", 'a"b', "a b", "1abc", "", "a" * 65, None, 42, "a--></b>"):
            with self.subTest(bad=bad):
                with self.assertRaises(pv.SpecError):
                    pv.figure_html(dict(SEQUENCE, id=bad))

    def test_input_ids_may_not_contain_hyphens(self):
        # A hyphen would tokenize as subtraction inside a formula.
        spec = json.loads(json.dumps(EXPLORABLE))
        spec["contract"]["inputs"][0]["id"] = "rho-bar"
        spec["formulas"] = {"wait": "1", "head": "1"}
        with self.assertRaises(pv.SpecError):
            pv.compile_explorable(spec)

    def test_output_ids_may_contain_hyphens(self):
        spec = json.loads(json.dumps(EXPLORABLE))
        spec["contract"]["outputs"][1]["id"] = "latency-p99"
        spec["formulas"] = {"wait": "rho", "latency-p99": "1 - rho"}
        pv.compile_explorable(spec)


class TestFormulaGrammar(unittest.TestCase):
    """A legal token sequence is not necessarily legal arithmetic."""

    def test_rejects_comment_injection(self):
        # `1/*2` compiled to `1/*2`, which opens a JS comment and swallowed the
        # statements after it — the whole explorable silently stopped updating.
        with self.assertRaises(pv.SpecError):
            pv.compile_formula("1/*2", {"rho"}, "wait")

    def test_rejects_unbalanced_and_stray_tokens(self):
        for expr in ("(", ")", ",", "1 2", "rho rho", "1+", "*2", "(1", "1)"):
            with self.subTest(expr=expr):
                with self.assertRaises(pv.SpecError):
                    pv.compile_formula(expr, {"rho"}, "wait")

    def test_rejects_regex_literal_smuggled_into_a_call(self):
        with self.assertRaises(pv.SpecError):
            pv.compile_formula("min(/1/,2)", {"rho"}, "wait")

    def test_enforces_arity(self):
        for expr in ("min(1)", "max(1,2,3)", "sqrt(1,2)", "pow(2)"):
            with self.subTest(expr=expr):
                with self.assertRaises(pv.SpecError) as ctx:
                    pv.compile_formula(expr, {"rho"}, "wait")
                self.assertIn("argument", str(ctx.exception))

    def test_function_without_parens_is_rejected(self):
        with self.assertRaises(pv.SpecError) as ctx:
            pv.compile_formula("sqrt", {"rho"}, "wait")
        self.assertIn("needs parentheses", str(ctx.exception))

    def test_subtraction_between_two_inputs_parses(self):
        js = pv.compile_formula("rho-n", {"rho", "n"}, "wait")
        self.assertEqual(js, 'v["rho"]-v["n"]')

    def test_accepts_real_expressions(self):
        cases = {
            "rho / (1 - rho)": 'v["rho"]/(1-v["rho"])',
            "-rho + 1": '(-v["rho"])+1',
            "pow(2, rho)": 'Math.pow(2,v["rho"])',
            "max(rho, 0.1) / min(1, 2)": 'Math.max(v["rho"],0.1)/Math.min(1,2)',
            "1-2-3": "1-2-3",
            "1/(2/3)": "1/(2/3)",
            "2*(3+4)": "2*(3+4)",
        }
        for expr, expected in cases.items():
            with self.subTest(expr=expr):
                self.assertEqual(pv.compile_formula(expr, {"rho", "n"}, "w"), expected)

    def test_unary_is_parenthesized_so_signs_cannot_fuse(self):
        # Bare concatenation produced JS `--`/`++`: `1 - -2` became `1--2` (a SyntaxError
        # that kills the whole script block) and `- -rho` became `--v["rho"]` — valid
        # pre-decrement, which returns the wrong value AND mutates the shared input
        # object, corrupting every output computed after it.
        self.assertEqual(pv.compile_formula("1--2", {"rho"}, "w"), "1-(-2)")
        self.assertEqual(pv.compile_formula("- -rho", {"rho"}, "w"), '(-(-v["rho"]))')
        for expr in ("1--2", "1 - -2", "1 ++ 2", "- -rho", "rho---rho", "rho - -0.05"):
            with self.subTest(expr=expr):
                js = pv.compile_formula(expr, {"rho"}, "w")
                self.assertNotIn("--", js, f"{expr!r} emitted decrement: {js}")
                self.assertNotIn("++", js, f"{expr!r} emitted increment: {js}")

    def test_emitted_js_is_syntactically_valid_where_node_is_available(self):
        import shutil
        import subprocess
        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        for expr in ("1--2", "- -rho", "rho---rho", "rho / (1 - rho)", "1 ++ 2",
                     "pow(2, rho)", "max(rho, 0.1) / min(1, 2)"):
            with self.subTest(expr=expr):
                js = pv.compile_formula(expr, {"rho"}, "w")
                probe = (f'var v={{"rho":0.5}};var before=v.rho;'
                         f'var out=({js});'
                         f'if(v.rho!==before)throw new Error("formula mutated its input");'
                         f'if(typeof out!=="number"||!isFinite(out))'
                         f'throw new Error("not a finite number: "+out);')
                r = subprocess.run([node, "-e", probe], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, f"{expr!r} -> {js}\n{r.stderr}")


class TestNonFinite(unittest.TestCase):
    """float() accepts nan/inf, and every ordering guard is a comparison — NaN slips past."""

    def test_non_finite_slider_bounds_rejected(self):
        for field, value in (("min", "nan"), ("max", "inf"), ("max", "1e400"),
                             ("step", "nan"), ("value", "-inf")):
            with self.subTest(field=field, value=value):
                spec = json.loads(json.dumps(EXPLORABLE))
                spec["contract"]["inputs"][0][field] = value
                with self.assertRaises(pv.SpecError) as ctx:
                    pv.compile_explorable(spec)
                self.assertIn("finite", str(ctx.exception))

    def test_non_finite_axis_rejected_rather_than_rendering_nan(self):
        for axis, field in (("x", "min"), ("y", "max")):
            with self.subTest(axis=axis, field=field):
                spec = json.loads(json.dumps(CURVE))
                spec["spec"][axis][field] = "nan"
                with self.assertRaises(pv.SpecError):
                    pv.figure_html(spec)

    def test_non_finite_timeline_bound_rejected(self):
        spec = json.loads(json.dumps(TIMELINE))
        spec["spec"]["spans"][0]["end"] = "inf"
        with self.assertRaises(pv.SpecError):
            pv.figure_html(spec)

    def test_no_nan_reaches_a_rendered_page(self):
        self.assertNotIn("nan", good_page(*ALL_FIGURES, EXPLORABLE).lower())


class TestNetworkScanPrecision(unittest.TestCase):
    """The scan must not blame a network call that doesn't exist."""

    def test_output_ids_named_after_network_apis_are_allowed(self):
        for oid in ("WebSocket_ms", "eventsource_lag", "xmlhttprequest_cost", "fetch_ms",
                    "worker_count"):
            with self.subTest(oid=oid):
                spec = json.loads(json.dumps(EXPLORABLE))
                spec["contract"]["outputs"][1]["id"] = oid
                spec["formulas"] = {"wait": "rho", oid: "1 - rho"}
                pv.validate_page(good_page(spec))

    def test_real_network_calls_are_still_caught(self):
        for js in ("fetch('/x')", "new XMLHttpRequest()", "new WebSocket('/x')",
                   "new EventSource('/x')", "navigator.sendBeacon('/x')",
                   "new Worker('w.js')", "eval('x')", "import('/m.js')"):
            with self.subTest(js=js):
                html = good_page(SEQUENCE).replace("<script>", f"<script>{js};", 1)
                with self.assertRaises(pv.ValidationError):
                    pv.validate_page(html)


class TestContractGuards(unittest.TestCase):
    def test_unused_input_is_rejected(self):
        spec = json.loads(json.dumps(EXPLORABLE))
        spec["contract"]["inputs"].append({"id": "n", "label": "replicas", "min": 1,
                                           "max": 5, "step": 1, "value": 3})
        with self.assertRaises(pv.SpecError) as ctx:
            pv.compile_explorable(spec)
        self.assertIn("no formula reads", str(ctx.exception))

    def test_decimals_must_be_in_range(self):
        for bad in (200, -1, 9):
            with self.subTest(decimals=bad):
                spec = json.loads(json.dumps(EXPLORABLE))
                spec["contract"]["outputs"][0]["decimals"] = bad
                with self.assertRaises(pv.SpecError) as ctx:
                    pv.compile_explorable(spec)
                self.assertIn("decimals", str(ctx.exception))

    def test_max_must_exceed_min(self):
        spec = json.loads(json.dumps(EXPLORABLE))
        spec["contract"]["inputs"][0]["max"] = 0.05
        with self.assertRaises(pv.SpecError):
            pv.compile_explorable(spec)

    def test_duplicate_ids_are_rejected(self):
        with self.assertRaises(pv.SpecError) as ctx:
            pv.build_page(artifact_text(SEQUENCE, SEQUENCE), Path("l.md"))
        self.assertIn("duplicate figure id", str(ctx.exception))


class TestRevealGating(unittest.TestCase):
    def test_invariant_is_gated_for_a_blanked_figure(self):
        # The invariant is the figure's one claim, so ungated it pre-announces the answer.
        html = good_page(SEQUENCE)
        region = pv._figure_region(html, "raft-partition")
        gated = pv._closed_details_body(region, "raft-partition")
        self.assertIn(pv.esc(SEQUENCE["invariant"]), gated)
        self.assertEqual(region.count(pv.esc(SEQUENCE["invariant"])), 1)

    def test_invariant_is_visible_for_an_unblanked_figure(self):
        html = good_page(LAYERS)
        region = pv._figure_region(html, "path")
        self.assertIn(pv.esc(LAYERS["invariant"]), region)
        self.assertNotIn("<details", region)

    def test_explorable_invariant_is_gated_and_predict_is_not(self):
        html = good_page(EXPLORABLE)
        region = pv._figure_region(html, "queue")
        gated = pv._closed_details_body(region, "queue")
        self.assertIn(pv.esc(EXPLORABLE["invariant"]), gated)
        self.assertNotIn(pv.esc(EXPLORABLE["predict"]), gated)

    def test_predict_line_renders_above_a_blanked_figure(self):
        spec = dict(SEQUENCE, predict="What message has to happen here?")
        region = pv._figure_region(good_page(spec), "raft-partition")
        self.assertNotIn(pv.esc(spec["predict"]),
                         pv._closed_details_body(region, "raft-partition"))

    def test_gate_check_survives_a_tampered_manifest(self):
        # `validate` is a standalone re-check of an existing page, so the check cannot key
        # off the manifest's own `blank` field — that field is editable.
        html = good_page(SEQUENCE).replace('"blank":["m3"]', '"blank":[]')
        pv.validate_page(html)  # still gated, so still valid
        ungated = html.replace(
            '<details><summary>I have committed to a prediction — reveal</summary>\n', "")
        with self.assertRaises(pv.ValidationError):
            pv.validate_page(ungated)

    def test_reveal_without_a_blank_is_rejected(self):
        with self.assertRaises(pv.SpecError) as ctx:
            pv.figure_html(dict(LAYERS, reveal="an answer to nothing"))
        self.assertIn("nothing is blanked", str(ctx.exception))

    def test_render_writes_nothing_when_validation_fails(self):
        # Guarantee: the learner is told the output path is safe to click, so a page that
        # failed validation must never exist there — nor destroy a valid earlier one.
        original = pv.validate_page
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "l.md"
            artifact.write_text(artifact_text(SEQUENCE), encoding="utf-8")
            page = Path(tmp) / "l.view.html"
            self.assertEqual(pv.main(["render", str(artifact)]), 0)
            good = page.read_text(encoding="utf-8")
            pv.validate_page = lambda html: (_ for _ in ()).throw(
                pv.ValidationError("synthetic failure"))
            try:
                self.assertEqual(pv.main(["render", str(artifact)]), 1)
            finally:
                pv.validate_page = original
            self.assertEqual(page.read_text(encoding="utf-8"), good)


class TestSpecTypeErrors(unittest.TestCase):
    """A malformed spec must surface as SpecError, never as a traceback out of the CLI."""

    CASES = [
        ("curve axis without min/max", CURVE, lambda s: s["spec"].__setitem__("x", {"label": "t"})),
        ("curve non-numeric axis", CURVE, lambda s: s["spec"]["x"].update({"min": "a"})),
        ("curve non-numeric points", CURVE,
         lambda s: s["spec"]["series"][0].__setitem__("points", [["a", "b"], [1, 2]])),
        ("curve three series", CURVE, lambda s: s["spec"]["series"].extend(
            [{"label": "b", "points": [[0, 1], [1, 2]]},
             {"label": "c", "points": [[0, 1], [1, 2]]}])),
        ("curve knee before the data", CURVE,
         lambda s: s["spec"].__setitem__("annotate", [{"x": -5, "label": "knee"}])),
        ("sequence message without from", SEQUENCE,
         lambda s: s["spec"]["messages"][0].pop("from")),
        ("sequence participants as strings", SEQUENCE,
         lambda s: s["spec"].__setitem__("participants", ["L", "F1"])),
        ("quorum nodes as strings", QUORUM, lambda s: s["spec"].__setitem__("nodes", ["a"])),
        ("quorum empty group", QUORUM, lambda s: s["spec"].__setitem__("partition", [[]])),
        ("layers boundary out of range", LAYERS,
         lambda s: s["spec"].__setitem__("boundary_after", "one")),
        ("layers boundary past the end", LAYERS,
         lambda s: s["spec"].__setitem__("boundary_after", 99)),
        ("state transitions as a dict", STATE,
         lambda s: s["spec"].__setitem__("transitions", {"a": 1})),
        ("state transition without to", STATE,
         lambda s: s["spec"]["transitions"][0].pop("to")),
        ("timeline span without start", TIMELINE,
         lambda s: s["spec"]["spans"][0].pop("start")),
        ("timeline non-numeric start", TIMELINE,
         lambda s: s["spec"]["spans"][0].__setitem__("start", "soon")),
        ("spec payload not an object", SEQUENCE, lambda s: s.__setitem__("spec", [1, 2])),
        ("label over the budget", SEQUENCE,
         lambda s: s["spec"]["messages"][0].__setitem__("label", "x" * 80)),
    ]

    def test_all_surface_as_spec_errors(self):
        for name, base, mutate in self.CASES:
            with self.subTest(case=name):
                spec = json.loads(json.dumps(base))
                mutate(spec)
                with self.assertRaises(pv.SpecError):
                    pv.figure_html(spec)

    def test_cli_never_prints_a_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i, (name, base, mutate) in enumerate(self.CASES):
                with self.subTest(case=name):
                    spec = json.loads(json.dumps(base))
                    mutate(spec)
                    artifact = Path(tmp) / f"a{i}.md"
                    artifact.write_text(artifact_text(spec), encoding="utf-8")
                    self.assertEqual(pv.main(["render", str(artifact)]), 1)


class TestGeometryEdgeCases(unittest.TestCase):
    def test_single_element_figures_render(self):
        cases = [
            dict(SEQUENCE, blank=[], reveal=None, spec={
                "participants": [{"id": "L", "label": "Leader"}],
                "messages": [{"id": "m1", "from": "L", "to": "L", "label": "self"}]}),
            dict(LAYERS, spec={"layers": [{"label": "only"}]}),
            dict(QUORUM, blank=[], reveal=None,
                 spec={"nodes": [{"id": "a", "label": "n1"}], "partition": [["a"]]}),
        ]
        for spec in cases:
            with self.subTest(form=spec["type"]):
                clean = {k: v for k, v in spec.items() if v is not None}
                ET.fromstring(pv.RENDERERS[clean["type"]](clean["spec"], set(),
                                                          clean["id"]))

    def test_self_transition_does_not_draw_through_the_state_box(self):
        spec = json.loads(json.dumps(STATE))
        spec["spec"]["transitions"] = [{"id": "t1", "from": "f", "to": "f",
                                        "label": "heartbeat"}]
        spec["spec"]["illegal"] = []
        spec["blank"] = ["t1"]
        svg = pv.render_state(spec["spec"], {"t1"}, "s")
        ET.fromstring(svg)
        self.assertIn("<path", svg)  # a loop arc, not a straight line across the box

    def test_identical_timeline_bounds_do_not_divide_by_zero(self):
        spec = json.loads(json.dumps(TIMELINE))
        spec["spec"]["spans"] = [{"id": "s1", "actor": "req", "start": 5, "end": 5,
                                  "label": "instant"}]
        ET.fromstring(pv.render_timeline(spec["spec"], set(), "t"))

    def test_numeric_labels_are_coerced_rather_than_crashing(self):
        spec = json.loads(json.dumps(SEQUENCE))
        spec["spec"]["notes"][0]["label"] = 42
        svg = pv.render_sequence(spec["spec"], set(spec["blank"]), "f")
        ET.fromstring(svg)
        self.assertIn("42", svg)

    def test_reversed_timeline_span_has_positive_width(self):
        spec = json.loads(json.dumps(TIMELINE))
        spec["spec"]["spans"][0].update({"start": 40, "end": 0})
        svg = pv.render_timeline(spec["spec"], set(), "t")
        ET.fromstring(svg)
        self.assertNotIn('width="-', svg)


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

    def test_unknown_blank_id_is_rejected_on_the_ascii_path_too(self):
        # This is the channel the learner sees *during* the prediction beat, so a silent
        # no-op here hands over the answer before the page is ever rendered.
        with self.assertRaises(pv.SpecError):
            pv.ascii_figure(dict(SEQUENCE, blank=["m33"]))

    def test_ascii_rejects_everything_render_rejects(self):
        # The terminal comes first (Deepen), the page second (Recap) — so a spec error
        # that only `render` catches would surface after the learner saw the figure.
        cases = [
            ("over-budget label", SEQUENCE,
             lambda s: s["spec"]["messages"][0].__setitem__("label", "x" * 80)),
            ("three curve series", CURVE, lambda s: s["spec"]["series"].extend(
                [{"label": "b", "points": [[0, 1], [1, 2]]},
                 {"label": "c", "points": [[0, 1], [1, 2]]}])),
            ("reversed axis", CURVE, lambda s: s["spec"]["x"].update({"min": 5, "max": 1})),
            ("mistyped messages", SEQUENCE,
             lambda s: s["spec"].__setitem__("messages", {"m1": {}})),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for i, (name, base, mutate) in enumerate(cases):
                with self.subTest(case=name):
                    spec = json.loads(json.dumps(base))
                    mutate(spec)
                    artifact = Path(tmp) / f"a{i}.md"
                    artifact.write_text(artifact_text(spec), encoding="utf-8")
                    self.assertEqual(pv.main(["ascii", str(artifact)]), 1, name)

    def test_mistyped_collection_names_itself_not_the_blank_id(self):
        spec = json.loads(json.dumps(SEQUENCE))
        spec["spec"]["messages"] = {"m1": {"from": "L", "to": "F1"}}
        with self.assertRaises(pv.SpecError) as ctx:
            pv.figure_html(spec)
        self.assertIn("'messages' must be a list of objects", str(ctx.exception))

    def test_non_string_element_id_is_named(self):
        spec = json.loads(json.dumps(SEQUENCE))
        spec["spec"]["messages"][2]["id"] = 3
        spec["blank"] = ["m1"]
        with self.assertRaises(pv.SpecError) as ctx:
            pv.figure_html(spec)
        self.assertIn("non-string id", str(ctx.exception))

    def test_over_budget_labels_are_caught_on_every_channel(self):
        for name, base, mutate in [
            ("boundary_label", LAYERS,
             lambda s: s["spec"].__setitem__("boundary_label", "y" * 40)),
            ("timeline unit", TIMELINE, lambda s: s["spec"].__setitem__("unit", "z" * 40)),
            ("blanked label", SEQUENCE,
             lambda s: s["spec"]["messages"][2].__setitem__("label", "w" * 40)),
        ]:
            with self.subTest(case=name):
                spec = json.loads(json.dumps(base))
                mutate(spec)
                with self.assertRaises(pv.SpecError):
                    pv.figure_html(spec)

    def test_layers_boundary_below_the_last_layer_is_drawn(self):
        spec = dict(LAYERS, spec={**LAYERS["spec"], "boundary_after": 3})
        self.assertIn("trust boundary", pv.ascii_figure(spec))

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
