#!/usr/bin/env python3
"""Render a primer lesson artifact's figure specs into a self-contained local view page.

Python 3.11+, stdlib only (D-0018/D-0020: deterministic work is code, and primer never
requires an install). The lesson's markdown stays the source of truth; this page is a
derived build product and is regenerable at any time.

Why a template library rather than model-authored SVG: authoring geometry mid-lesson is
slow at the worst moment, burns context that should be teaching, and is where malformed
output comes from. The model supplies labels and values; templates supply geometry.

Why generated interaction wiring rather than model-authored JS: AI-generated interactives
measurably fail at state management (broken chains, outputs that don't track inputs).
Compiling a declared formula makes the interaction contract structurally true instead of
hopefully true.

Commands:
  templates                      list forms and their spec schema
  render   <artifact.md> [--open]  write + validate <stem>.view.html
  validate <view.html>           re-check an existing page
  ascii    <artifact.md> --id ID  terminal rendering of one figure
"""

import argparse
import json
import re
import sys
import webbrowser
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

FIGURE_TYPES = ("sequence", "state", "quorum", "layers", "curve", "timeline")

# Functions a declared formula may call. Everything else is rejected, so no
# arbitrary expression from a spec can reach the page as executable JavaScript.
ALLOWED_FUNCS = {"min": "Math.min", "max": "Math.max", "abs": "Math.abs",
                 "sqrt": "Math.sqrt", "exp": "Math.exp", "log": "Math.log",
                 "pow": "Math.pow"}

BLOCK_RE = re.compile(r"<!--primer-(figure|explorable)\s*(\{.*?\})\s*-->", re.DOTALL)
TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


class SpecError(Exception):
    """A figure or explorable spec is unusable. Message names the spec and the problem."""


class ValidationError(Exception):
    """A generated page failed a validation check. Message names the check and the figure."""


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


@dataclass
class Block:
    kind: str  # "figure" | "explorable"
    spec: dict[str, Any]

    @property
    def id(self) -> str:
        return str(self.spec.get("id", "<no-id>"))


def extract_blocks(markdown: str) -> list[Block]:
    """Pull figure/explorable specs out of a lesson artifact.

    Specs live in HTML comments so they are invisible in rendered markdown, greppable,
    hand-editable, and parseable without a YAML dependency.
    """
    blocks: list[Block] = []
    for kind, payload in BLOCK_RE.findall(markdown):
        try:
            spec = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise SpecError(f"primer-{kind} block is not valid JSON: {exc}") from exc
        blocks.append(Block(kind=kind, spec=spec))
    return blocks


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------


def esc(text: Any) -> str:
    """Escape for XML text and attribute values.

    Single quotes are escaped too, so that inert prose in a caption (a lesson *about*
    HTML will contain `src='x'`) cannot look like a live attribute to the
    external-reference scan.
    """
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;"))


def svg_open(width: float, height: float, label: str) -> str:
    # role/aria-label rather than a <title> child: screen readers get the caption's
    # invariant, which is the content, not a redundant figure name.
    return (f'<svg class="pv-svg" viewBox="0 0 {width:g} {height:g}" '
            f'width="100%" height="auto" preserveAspectRatio="xMidYMid meet" '
            f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{esc(label)}">')


def box(x: float, y: float, w: float, h: float, cls: str = "") -> str:
    return (f'<rect class="pv-box {cls}" x="{x:g}" y="{y:g}" width="{w:g}" '
            f'height="{h:g}" rx="6"/>')


def text(x: float, y: float, s: str, cls: str = "", anchor: str = "middle") -> str:
    return (f'<text class="pv-t {cls}" x="{x:g}" y="{y:g}" '
            f'text-anchor="{anchor}">{esc(s)}</text>')


def line(x1: float, y1: float, x2: float, y2: float, cls: str = "") -> str:
    return (f'<line class="pv-l {cls}" x1="{x1:g}" y1="{y1:g}" '
            f'x2="{x2:g}" y2="{y2:g}"/>')


def arrow(x1: float, y1: float, x2: float, y2: float, cls: str = "") -> str:
    return (f'<line class="pv-l pv-arrow {cls}" x1="{x1:g}" y1="{y1:g}" '
            f'x2="{x2:g}" y2="{y2:g}" marker-end="url(#pv-head)"/>')


def path(d: str, cls: str = "", marker: bool = True) -> str:
    tip = ' marker-end="url(#pv-head)"' if marker else ""
    return f'<path class="pv-l {cls}" d="{d}"{tip} fill="none"/>'


# The arrowhead marker is defined once per page (below) and referenced by every figure;
# repeating the <defs> per <svg> would put duplicate ids in the document.
ARROW_DEFS = ""
ARROW_DEFS_PAGE = ('<svg width="0" height="0" aria-hidden="true" '
                   'xmlns="http://www.w3.org/2000/svg"><defs>'
                   '<marker id="pv-head" viewBox="0 0 10 10" refX="9" refY="5" '
                   'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                   '<path class="pv-head" d="M 0 0 L 10 5 L 0 10 z"/></marker>'
                   '</defs></svg>')

# Defence in depth for "the page makes no external requests": a regex over generated
# markup can be outrun, a browser-enforced policy cannot. `data:` images are allowed
# because the design permits inlined assets; everything else is denied outright.
CSP = ("default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
       "img-src data:; form-action 'none'; base-uri 'none'")


def require(spec: dict[str, Any], key: str, kind: str, fig: str) -> Any:
    value = spec.get(key)
    if value in (None, "", [], {}):
        raise SpecError(f"{kind} '{fig}': missing required field '{key}'")
    return value


# Ids reach HTML attributes, SVG anchors, and (for explorables) generated JavaScript
# string literals. Constraining the character set at spec load is what makes those
# interpolations safe by construction rather than by escaping discipline downstream.
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
# Formula-referencable names additionally exclude '-', so `a-b` tokenizes as subtraction
# rather than as one identifier.
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")


def check_id(value: Any, what: str, fig: str, pattern: re.Pattern[str] = ID_RE) -> str:
    hint = "letters, digits, '_'" + ("" if pattern is NAME_RE else ", '-'")
    if not isinstance(value, str) or not pattern.match(value):
        raise SpecError(f"'{fig}': {what} must start with a letter and use only {hint} "
                        f"(max 64 chars); got {value!r}")
    return value


def num(spec: dict[str, Any], key: str, default: Any, what: str, fig: str) -> float:
    """Read a numeric spec field. Specs are model-authored, so the type is not a given."""
    raw = spec.get(key, default)
    try:
        return float(raw)
    except (TypeError, ValueError):
        raise SpecError(f"'{fig}': {what} field '{key}' must be a number; "
                        f"got {raw!r}") from None


def obj_list(spec: dict[str, Any], key: str, kind: str, fig: str) -> list[dict[str, Any]]:
    """Read a required list-of-objects spec field, with the type checked up front."""
    return _typed_list(require(spec, key, kind, fig), key, kind, fig)


def opt_obj_list(spec: dict[str, Any], key: str, kind: str,
                 fig: str) -> list[dict[str, Any]]:
    """Same, for an optional field. A wrong type is reported rather than filtered away —
    silently dropping malformed entries loses figure content without telling anyone."""
    if key not in spec:
        return []
    return _typed_list(spec[key], key, kind, fig)


def _typed_list(value: Any, key: str, kind: str, fig: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise SpecError(f"{kind} '{fig}': '{key}' must be a list of objects; "
                        f"got {type(value).__name__}")
    bad = next((i for i in value if not isinstance(i, dict)), None)
    if bad is not None:
        raise SpecError(f"{kind} '{fig}': every entry in '{key}' must be an object with "
                        f"its own fields; found {bad!r}")
    return value


def req_key(item: dict[str, Any], key: str, kind: str, fig: str) -> Any:
    if key not in item:
        raise SpecError(f"{kind} '{fig}': an entry is missing required key '{key}': {item}")
    return item[key]


# ---------------------------------------------------------------------------
# Figure templates. Each returns (svg, blankable_ids).
# ---------------------------------------------------------------------------

QMARK = "?"

# Templates own geometry, which means they also own the label budget: these dimensions are
# fixed, so a label past the budget would be clipped by the viewBox and silently lost.
MAX_LABEL = 34
LANE_W, LANE_TOP_H, MSG_PITCH = 170.0, 40.0, 46.0


def _plain_label(value: Any, what: str, fig: str) -> str:
    label = str(value)
    if len(label) > MAX_LABEL:
        raise SpecError(f"'{fig}': {what} label is {len(label)} chars, over the "
                        f"{MAX_LABEL}-char budget for this form — it would be clipped by "
                        f"the viewBox and silently lost. Shorten it, or split the figure.")
    return label


def _label_text(item: dict[str, Any], blanks: set[str], what: str, fig: str) -> str:
    """A blankable element's visible label: `?` when blanked, budget-checked otherwise."""
    if item.get("id") in blanks:
        return QMARK
    return _plain_label(item.get("label", ""), what, fig)


def render_sequence(spec: dict[str, Any], blanks: set[str], fig: str) -> str:
    parts = obj_list(spec, "participants", "sequence", fig)
    msgs = obj_list(spec, "messages", "sequence", fig)
    notes = opt_obj_list(spec, "notes", "sequence", fig)
    width = max(len(parts) * LANE_W, 320.0)
    first_y = LANE_TOP_H + 52
    height = first_y + len(msgs) * MSG_PITCH + 30

    def cx(pid: Any) -> float:
        for i, p in enumerate(parts):
            if p.get("id") == pid:
                return LANE_W / 2 + i * LANE_W
        raise SpecError(f"sequence '{fig}': references unknown participant '{pid}'")

    out = [svg_open(width, height, spec.get("invariant", fig)), ARROW_DEFS]
    for i, p in enumerate(parts):
        x = LANE_W / 2 + i * LANE_W
        out.append(box(x - LANE_W / 2 + 12, 8, LANE_W - 24, LANE_TOP_H - 8))
        out.append(text(x, 8 + (LANE_TOP_H - 8) / 2 + 5,
                        _plain_label(p.get("label", p.get("id", "?")), "participant", fig)))
        out.append(line(x, LANE_TOP_H + 6, x, height - 14, "pv-lifeline"))

    for j, m in enumerate(msgs):
        y = first_y + j * MSG_PITCH
        blanked = m.get("id") in blanks
        cls = " ".join(c for c in ("pv-dash" if m.get("dashed") else "",
                                  "pv-blank" if blanked else "") if c)
        x1 = cx(req_key(m, "from", "sequence", fig))
        x2 = cx(req_key(m, "to", "sequence", fig))
        out.append(_sequence_message(x1, x2, y, _label_text(m, blanks, "message", fig),
                                    cls, bool(m.get("lost"))))

    for n in notes:
        y = first_y + _note_offset(msgs, n) * MSG_PITCH - 30
        out.append(_sequence_note(cx(req_key(n, "over", "sequence", fig)), y,
                                  _label_text(n, blanks, "note", fig)))

    out.append("</svg>")
    return "\n".join(out)


def _sequence_message(x1: float, x2: float, y: float, label: str, cls: str,
                      lost: bool) -> str:
    """A message arrow, or a cut arrow when the message never arrives."""
    if not lost:
        return arrow(x1, y, x2, y, cls) + text((x1 + x2) / 2, y - 8, label, "pv-sm")
    stop = x1 + (x2 - x1) * 0.62
    cut = "".join([line(stop + 6, y - 8, stop + 18, y + 8, "pv-cut"),
                   line(stop + 18, y - 8, stop + 6, y + 8, "pv-cut")])
    return (arrow(x1, y, stop, y, f"{cls} pv-dash") + cut
            + text((x1 + stop) / 2, y - 8, label, "pv-sm"))


def _note_offset(msgs: list[dict[str, Any]], note: dict[str, Any]) -> int:
    after = note.get("after")
    for j, m in enumerate(msgs):
        if m.get("id") == after:
            return j + 1
    return len(msgs)


def _sequence_note(x: float, y: float, label: str) -> str:
    w = max(90.0, 7.4 * len(label) + 18)
    return (f'<rect class="pv-box pv-note" x="{x - w / 2:g}" y="{y - 15:g}" '
            f'width="{w:g}" height="24" rx="3"/>' + text(x, y + 2, label, "pv-sm"))


def render_state(spec: dict[str, Any], blanks: set[str], fig: str) -> str:
    states = obj_list(spec, "states", "state", fig)
    trans = opt_obj_list(spec, "transitions", "state", fig)
    illegal = opt_obj_list(spec, "illegal", "state", fig)
    sw, gap, bh = 150.0, 40.0, 48.0
    width = max(len(states) * (sw + gap) + gap, 340.0)
    mid = 140.0
    height = mid + bh / 2 + 90

    def idx(sid: str) -> int:
        for i, s in enumerate(states):
            if s.get("id") == sid:
                return i
        raise SpecError(f"state '{fig}': transition references unknown state '{sid}'")

    def cx(sid: str) -> float:
        return gap + idx(sid) * (sw + gap) + sw / 2

    out = [svg_open(width, height, spec.get("invariant", fig)), ARROW_DEFS]
    for i, s in enumerate(states):
        x = gap + i * (sw + gap)
        cls = "pv-initial" if s.get("initial") else ""
        out.append(box(x, mid - bh / 2, sw, bh, cls))
        out.append(text(x + sw / 2, mid + 5,
                        _plain_label(s.get("label", s.get("id", "?")), "state", fig)))

    for t, below in [(t, False) for t in trans] + [(t, True) for t in illegal]:
        cls = "pv-illegal " if below else ""
        cls += "pv-blank" if t.get("id") in blanks else ""
        out.append(_state_edge(cx(req_key(t, "from", "state", fig)),
                               cx(req_key(t, "to", "state", fig)), mid, bh, sw,
                               _label_text(t, blanks, "transition", fig),
                               cls.strip(), below=below))
    out.append("</svg>")
    return "\n".join(out)


def _state_edge(x1: float, x2: float, mid: float, bh: float, sw: float, label: str,
                cls: str, below: bool) -> str:
    """Straight arrow between neighbours; an arc otherwise so edges don't cross boxes."""
    if x1 == x2:
        # A self-transition (retry, heartbeat, re-election) is common in the lifecycles
        # this form is for. Drawn as a loop above the box; a straight arrow would run
        # through the state it belongs to.
        top = mid - bh / 2
        d = (f"M {x1 - 26:g} {top:g} C {x1 - 34:g} {top - 46:g} "
             f"{x1 + 34:g} {top - 46:g} {x1 + 26:g} {top:g}")
        return path(d, cls) + text(x1, top - 40, label, "pv-sm")
    adjacent = abs(x2 - x1) < sw * 1.6
    if adjacent and not below:
        edge = (sw / 2) * (1 if x2 > x1 else -1)
        return (arrow(x1 + edge, mid, x2 - edge, mid, cls)
                + text((x1 + x2) / 2, mid - 12, label, "pv-sm"))
    sign = 1 if below else -1
    y0 = mid + sign * bh / 2
    apex = y0 + sign * 58
    d = f"M {x1:g} {y0:g} Q {(x1 + x2) / 2:g} {apex + sign * 20:g} {x2:g} {y0:g}"
    strike = ""
    if "pv-illegal" in cls:
        strike = line((x1 + x2) / 2 - 12, apex + 6, (x1 + x2) / 2 + 12, apex - 6, "pv-cut")
    return path(d, cls) + text((x1 + x2) / 2, apex + sign * 14, label, "pv-sm") + strike


def render_quorum(spec: dict[str, Any], blanks: set[str], fig: str) -> str:
    nodes = obj_list(spec, "nodes", "quorum", fig)
    groups = require(spec, "partition", "quorum", fig)
    if not isinstance(groups, list) or not all(isinstance(g, list) and g for g in groups):
        raise SpecError(f"quorum '{fig}': 'partition' must be a list of non-empty lists "
                        f"of node ids")
    by_id = {n.get("id"): n for n in nodes}
    for g in groups:
        unknown = [n for n in g if n not in by_id]
        if unknown:
            raise SpecError(f"quorum '{fig}': partition references unknown nodes {unknown}")
    step, pad, split = 78.0, 26.0, 56.0
    widths = [len(g) * step + pad for g in groups]
    width = sum(widths) + split * (len(groups) - 1) + 20
    height = 200.0
    progress = spec.get("progress", "none")
    blanked = "progress" in blanks

    out = [svg_open(width, height, spec.get("invariant", fig)), ARROW_DEFS]
    x = 10.0
    for gi, group in enumerate(groups):
        wins = _group_wins(progress, gi, len(groups))
        shade = "" if blanked else ("pv-shade" if wins else "pv-shade-off")
        out.append(f'<rect class="pv-group {shade}" x="{x:g}" y="26" '
                   f'width="{widths[gi]:g}" height="118" rx="10"/>')
        out.append(text(x + widths[gi] / 2, 166,
                        QMARK if blanked else _progress_label(wins, progress), "pv-sm"))
        out.extend(_quorum_nodes(group, by_id, x + pad / 2, step, fig))
        x += widths[gi]
        if gi < len(groups) - 1:
            out.append(line(x + split / 2, 12, x + split / 2, height - 46, "pv-partition"))
            out.append(text(x + split / 2, height - 30, "partition", "pv-sm"))
            x += split
    out.append("</svg>")
    return "\n".join(out)


def _group_wins(progress: str, gi: int, total: int) -> bool:
    if progress == "left":
        return gi == 0
    if progress == "right":
        return gi == total - 1
    return False


def _progress_label(wins: bool, progress: str) -> str:
    if progress == "none":
        return "no progress"
    return "can make progress" if wins else "cannot make progress"


def _quorum_nodes(group: list[str], by_id: dict[Any, Any], x0: float,
                  step: float, fig: str) -> list[str]:
    out: list[str] = []
    for i, nid in enumerate(group):
        node = by_id[nid]
        cx = x0 + step / 2 + i * step
        leader = node.get("leader")
        out.append(f'<circle class="pv-node" cx="{cx:g}" cy="76" r="27"/>')
        if leader:
            out.append(f'<circle class="pv-node pv-leader-ring" cx="{cx:g}" cy="76" r="33"/>')
        out.append(text(cx, 81, _plain_label(node.get("label", nid), "node", fig)))
        if leader:
            out.append(text(cx, 128, "leader", "pv-sm"))
    return out


def render_layers(spec: dict[str, Any], blanks: set[str], fig: str) -> str:
    layers = obj_list(spec, "layers", "layers", fig)
    bw, bh, gap, left = 430.0, 54.0, 14.0, 46.0
    width = left + bw + 20
    height = 20 + len(layers) * (bh + gap) + 24
    out = [svg_open(width, height, spec.get("invariant", fig)), ARROW_DEFS]
    out.append(arrow(left / 2, 24, left / 2, height - 34, "pv-dash"))
    out.append(text(left / 2, height - 16, "path", "pv-sm"))

    for i, layer in enumerate(layers):
        y = 20 + i * (bh + gap)
        out.append(box(left, y, bw, bh))
        out.append(text(left + 16, y + bh / 2 + 5,
                        _plain_label(layer.get("label", "?"), "layer", fig), "", "start"))
        if layer.get("detail"):
            out.append(text(left + bw - 16, y + bh / 2 + 5,
                            _plain_label(layer["detail"], "layer detail", fig),
                            "pv-sm", "end"))

    after = spec.get("boundary_after")
    if after is not None:
        idx = int(num(spec, "boundary_after", 0, "layers", fig))
        if not 0 <= idx < len(layers):
            raise SpecError(f"layers '{fig}': boundary_after must index a layer "
                            f"(0–{len(layers) - 1}); got {after!r}")
        blanked = "boundary" in blanks
        y = 20 + (idx + 1) * (bh + gap) - gap / 2
        out.append(line(left - 16, y, left + bw + 8, y, "pv-partition"))
        label = QMARK if blanked else spec.get("boundary_label", "boundary")
        out.append(text(left + bw + 4, y - 7, label, "pv-sm", "end"))
    out.append("</svg>")
    return "\n".join(out)


def render_curve(spec: dict[str, Any], blanks: set[str], fig: str) -> str:
    xa = _axis(spec, "x", fig)
    ya = _axis(spec, "y", fig)
    series = obj_list(spec, "series", "curve", fig)
    if len(series) > 2:
        raise SpecError(f"curve '{fig}': at most 2 series — a third would be silently "
                        f"dropped. Split the figure, or drop a series.")
    ml, mr, mt, mb = 62.0, 24.0, 18.0, 46.0
    pw, ph = 380.0, 226.0
    width, height = ml + pw + mr, mt + ph + mb
    cut = _curve_cut(spec, xa, series, fig) if "tail" in blanks else None

    def px(v: float) -> float:
        span = xa["max"] - xa["min"] or 1.0
        return ml + (float(v) - xa["min"]) / span * pw

    def py(v: float) -> float:
        span = ya["max"] - ya["min"] or 1.0
        return mt + ph - (float(v) - ya["min"]) / span * ph

    out = [svg_open(width, height, spec.get("invariant", fig)), ARROW_DEFS]
    out.append(line(ml, mt, ml, mt + ph, "pv-axis"))
    out.append(line(ml, mt + ph, ml + pw, mt + ph, "pv-axis"))
    out.append(text(ml + pw / 2, height - 12, xa.get("label", "x"), "pv-sm"))
    out.append(f'<text class="pv-t pv-sm" x="14" y="{mt + ph / 2:g}" text-anchor="middle" '
               f'transform="rotate(-90 14 {mt + ph / 2:g})">{esc(ya.get("label", "y"))}</text>')
    out.append(text(ml, mt + ph + 18, f'{xa["min"]:g}', "pv-sm"))
    out.append(text(ml + pw, mt + ph + 18, f'{xa["max"]:g}', "pv-sm"))
    out.append(text(ml - 8, mt + ph + 4, f'{ya["min"]:g}', "pv-sm", "end"))
    out.append(text(ml - 8, mt + 10, f'{ya["max"]:g}', "pv-sm", "end"))

    for si, s in enumerate(series):
        pts = _points(s, fig)
        kept = [p for p in pts if cut is None or p[0] <= cut]
        # Style by dash pattern, never by colour alone.
        cls = "pv-series" + (" pv-dash" if si else "")
        d = "M " + " L ".join(f"{px(a):g} {py(b):g}" for a, b in kept)
        out.append(path(d, cls, marker=False))
        out.append(text(px(kept[-1][0]) - 6, py(kept[-1][1]) - 10,
                        _plain_label(s.get("label", ""), "series", fig), "pv-sm", "end"))

    if cut is not None:
        out.append(f'<rect class="pv-blank-region" x="{px(cut):g}" y="{mt:g}" '
                   f'width="{ml + pw - px(cut):g}" height="{ph:g}"/>')
        out.append(text((px(cut) + ml + pw) / 2, mt + ph / 2, QMARK, "pv-qmark"))
    for a in opt_obj_list(spec, "annotate", "curve", fig):
        ax = px(num(a, "x", 0, "annotate", fig))
        out.append(line(ax, mt, ax, mt + ph, "pv-partition"))
        out.append(text(ax, mt - 4, _plain_label(a.get("label", ""), "annotation", fig),
                        "pv-sm"))
    out.append("</svg>")
    return "\n".join(out)


def _axis(spec: dict[str, Any], key: str, fig: str) -> dict[str, Any]:
    axis = require(spec, key, "curve", fig)
    if not isinstance(axis, dict):
        raise SpecError(f"curve '{fig}': axis '{key}' must be an object with label/min/max")
    lo = num(axis, "min", None, f"axis '{key}'", fig)
    hi = num(axis, "max", None, f"axis '{key}'", fig)
    if hi <= lo:
        raise SpecError(f"curve '{fig}': axis '{key}' has max <= min")
    return {"label": _plain_label(axis.get("label", key), f"axis '{key}'", fig),
            "min": lo, "max": hi}


def _points(series: dict[str, Any], fig: str) -> list[tuple[float, float]]:
    raw = series.get("points", [])
    if not isinstance(raw, list) or len(raw) < 2:
        raise SpecError(f"curve '{fig}': series '{series.get('label')}' needs 2+ points")
    try:
        pts = [(float(p[0]), float(p[1])) for p in raw]
    except (TypeError, ValueError, IndexError, KeyError):
        raise SpecError(f"curve '{fig}': series '{series.get('label')}' points must be "
                        f"[[x, y], …] with numeric x and y") from None
    return sorted(pts)


def _curve_cut(spec: dict[str, Any], xa: dict[str, Any],
               series: list[dict[str, Any]], fig: str) -> float:
    """Blank from the annotated knee if there is one, else the last 30% of the x range.

    Bounded against the data: a knee outside the plotted points would leave a series with
    fewer than two points, which renders an empty path that still parses as valid XML —
    a figure that silently shows nothing.
    """
    notes = opt_obj_list(spec, "annotate", "curve", fig)
    cut = (num(notes[0], "x", 0, "annotate", fig) if notes
           else xa["min"] + (xa["max"] - xa["min"]) * 0.7)
    for s in series:
        if len([p for p in _points(s, fig) if p[0] <= cut]) < 2:
            raise SpecError(f"curve '{fig}': blanking the tail at x={cut:g} leaves series "
                            f"'{s.get('label')}' with fewer than 2 visible points — move "
                            f"the annotation inside the plotted range, or add points")
    return cut


def render_timeline(spec: dict[str, Any], blanks: set[str], fig: str) -> str:
    actors = obj_list(spec, "actors", "timeline", fig)
    spans = obj_list(spec, "spans", "timeline", fig)
    ml, mr, mt = 130.0, 24.0, 16.0
    row, pw = 46.0, 380.0
    height = mt + len(actors) * row + 48
    width = ml + pw + mr
    lo = min(num(s, "start", None, "span", fig) for s in spans)
    hi = max(num(s, "end", None, "span", fig) for s in spans)
    span = (hi - lo) or 1.0

    def rowy(aid: Any) -> float:
        for i, a in enumerate(actors):
            if a.get("id") == aid:
                return mt + i * row
        raise SpecError(f"timeline '{fig}': span references unknown actor '{aid}'")

    out = [svg_open(width, height, spec.get("invariant", fig)), ARROW_DEFS]
    for i, a in enumerate(actors):
        y = mt + i * row
        out.append(text(ml - 12, y + row / 2 + 5,
                        _plain_label(a.get("label", a.get("id", "?")), "actor", fig),
                        "pv-sm", "end"))
        out.append(line(ml, y + row / 2, ml + pw, y + row / 2, "pv-lifeline"))

    for s in spans:
        y = rowy(req_key(s, "actor", "timeline", fig)) + row / 2 - 12
        x1 = ml + (num(s, "start", None, "span", fig) - lo) / span * pw
        x2 = ml + (num(s, "end", None, "span", fig) - lo) / span * pw
        cls = "pv-blank" if s.get("id") in blanks else ""
        out.append(f'<rect class="pv-span {cls}" x="{min(x1, x2):g}" y="{y:g}" '
                   f'width="{max(abs(x2 - x1), 3):g}" height="24" rx="4"/>')
        out.append(text((x1 + x2) / 2, y + 17, _label_text(s, blanks, "span", fig), "pv-sm"))

    axis_y = height - 30
    out.append(line(ml, axis_y, ml + pw, axis_y, "pv-axis"))
    unit = spec.get("unit", "")
    out.append(text(ml, axis_y + 16, f"{lo:g}", "pv-sm"))
    out.append(text(ml + pw, axis_y + 16, f"{hi:g} {unit}".strip(), "pv-sm"))
    out.append("</svg>")
    return "\n".join(out)


RENDERERS: dict[str, Callable[[dict[str, Any], set[str], str], str]] = {
    "sequence": render_sequence, "state": render_state, "quorum": render_quorum,
    "layers": render_layers, "curve": render_curve, "timeline": render_timeline,
}


# ---------------------------------------------------------------------------
# Blankable-id discovery. An unknown id in `blank` is an error, not a no-op:
# silently failing to blank hands the learner the answer.
# ---------------------------------------------------------------------------


def _ids_of(spec: dict[str, Any], *keys: str) -> set[str]:
    """Ids of the listed element collections, tolerant of a malformed spec.

    This runs before the renderers' type checks (blanks are validated first so a mistyped
    blank id is reported ahead of any geometry work), so it cannot assume list-of-dict.
    """
    found: set[str] = set()
    for key in keys:
        value = spec.get(key, [])
        if not isinstance(value, list):
            continue
        found |= {i["id"] for i in value
                  if isinstance(i, dict) and isinstance(i.get("id"), str)}
    return found


def blankable_ids(block: dict[str, Any]) -> set[str]:
    """Which ids a figure's `blank` list may name. Takes the whole block, not the payload."""
    kind = block.get("type")
    spec = block.get("spec", {})
    if not isinstance(spec, dict):
        return set()
    if kind == "sequence":
        return _ids_of(spec, "messages", "notes")
    if kind == "state":
        return _ids_of(spec, "transitions", "illegal")
    if kind == "timeline":
        return _ids_of(spec, "spans")
    if kind == "quorum":
        return {"progress"}
    if kind == "layers":
        return {"boundary"}
    if kind == "curve":
        return {"tail"}
    return set()


# ---------------------------------------------------------------------------
# Explorables: formula compilation
# ---------------------------------------------------------------------------

TOKEN_RE = re.compile(r"\s*(?:(?P<num>\d+(?:\.\d+)?)|(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
                      r"|(?P<op>\*\*|[-+*/(),]))")

# Arity per whitelisted function, so a malformed call is rejected rather than emitted.
FUNC_ARITY = {"min": 2, "max": 2, "pow": 2, "abs": 1, "sqrt": 1, "exp": 1, "log": 1}


def compile_formula(expr: str, inputs: set[str], out_id: str) -> str:
    """Compile a restricted arithmetic expression over input ids into JS.

    Checking the token *alphabet* is not enough: a sequence of individually-legal tokens
    can still form JavaScript that isn't arithmetic. `1/*2` opens a JS comment and
    swallows the statements after it; a lone `(` is a SyntaxError that kills the whole
    script block; `min(/1/,2)` smuggles in a regex literal. So this parses a grammar and
    emits from the parse, which makes the output arithmetic-over-declared-inputs by
    construction rather than by hoping the token filter was sufficient.
    """
    tokens = _tokenize(expr, out_id)
    if not tokens:
        raise SpecError(f"explorable output '{out_id}': empty formula")
    parser = _Parser(tokens, inputs, out_id)
    js = parser.expression()
    parser.expect_end()
    return js


def _tokenize(expr: str, out_id: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    pos = 0
    while pos < len(expr):
        m = TOKEN_RE.match(expr, pos)
        if not m or m.end() == pos:
            raise SpecError(f"explorable output '{out_id}': cannot parse formula at "
                            f"{expr[pos:pos + 12]!r}")
        pos = m.end()
        kind = next(k for k in ("num", "name", "op") if m.group(k) is not None)
        if m.group(kind) == "**":
            raise SpecError(f"explorable output '{out_id}': use pow(a,b), not '**'")
        tokens.append((kind, m.group(kind)))
    return tokens


class _Parser:
    """Recursive descent: expr := term (('+'|'-') term)*, term := factor (('*'|'/') …)*."""

    def __init__(self, tokens: list[tuple[str, str]], inputs: set[str], out_id: str):
        self.tokens = tokens
        self.inputs = inputs
        self.out_id = out_id
        self.pos = 0

    def fail(self, problem: str) -> None:
        seen = self.tokens[self.pos][1] if self.pos < len(self.tokens) else "end of formula"
        raise SpecError(f"explorable output '{self.out_id}': {problem} (at {seen!r})")

    def peek(self) -> tuple[str, str] | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def take_op(self, *ops: str) -> str | None:
        token = self.peek()
        if token and token[0] == "op" and token[1] in ops:
            self.pos += 1
            return token[1]
        return None

    def expect_end(self) -> None:
        if self.peek() is not None:
            self.fail("trailing tokens after a complete expression")

    def expression(self) -> str:
        js = self.term()
        while (op := self.take_op("+", "-")):
            js += op + self.term()
        return js

    def term(self) -> str:
        js = self.factor()
        while (op := self.take_op("*", "/")):
            js += op + self.factor()
        return js

    def factor(self) -> str:
        op = self.take_op("+", "-")
        return op + self.factor() if op else self.primary()

    def primary(self) -> str:
        token = self.peek()
        if token is None or (token[0] == "op" and token[1] != "("):
            self.fail("expected a number, an input, or '('")
            raise AssertionError("unreachable")  # fail() always raises
        self.pos += 1
        if token[0] == "num":
            return token[1]
        if token[0] == "name":
            return self.name(token[1])
        js = self.expression()
        if not self.take_op(")"):
            self.fail("unbalanced parenthesis")
        return f"({js})"

    def name(self, name: str) -> str:
        if name in self.inputs:
            return f'v["{name}"]'
        if name not in ALLOWED_FUNCS:
            self.fail(f"unknown name '{name}' — not a declared input and not one of "
                      f"{sorted(ALLOWED_FUNCS)}")
        return self.call(name)

    def call(self, name: str) -> str:
        if not self.take_op("("):
            self.fail(f"'{name}' is a function and needs parentheses")
        args = [self.expression()]
        while self.take_op(","):
            args.append(self.expression())
        if not self.take_op(")"):
            self.fail(f"unbalanced parenthesis in {name}(...)")
        if len(args) != FUNC_ARITY[name]:
            self.fail(f"{name}() takes {FUNC_ARITY[name]} argument(s), got {len(args)}")
        return f"{ALLOWED_FUNCS[name]}({','.join(args)})"


MAX_DECIMALS = 8  # Number.prototype.toFixed accepts 0–100; 8 is past any useful readout.
INPUT_REF_RE = re.compile(r'v\["([^"]+)"\]')


def compile_explorable(spec: dict[str, Any]) -> dict[str, Any]:
    fig = check_id(spec.get("id"), "explorable id", str(spec.get("id", "<no-id>")))
    for key in ("caption", "invariant", "predict", "contract", "formulas"):
        require(spec, key, "explorable", fig)
    contract = spec["contract"]
    ins = obj_list(contract, "inputs", "explorable", fig)
    outs = obj_list(contract, "outputs", "explorable", fig)
    if len(ins) > 2:
        raise SpecError(f"explorable '{fig}': at most 2 inputs (three sliders is a "
                        f"parameter-fitting exercise, not a lesson)")
    # Input ids land in generated JS as object keys, and are referenced by formulas, so
    # they get the stricter no-hyphen name rule.
    in_ids = {check_id(req_key(i, "id", "explorable", fig), "input id", fig, NAME_RE)
              for i in ins}
    out_ids = [check_id(req_key(o, "id", "explorable", fig), "output id", fig) for o in outs]
    formulas = require(spec, "formulas", "explorable", fig)
    if not isinstance(formulas, dict):
        raise SpecError(f"explorable '{fig}': 'formulas' must be an object mapping "
                        f"output id to expression")
    _check_contract_closed(fig, out_ids, formulas)
    compiled = {oid: compile_formula(str(formulas[oid]), in_ids, oid) for oid in out_ids}
    _check_inputs_used(fig, in_ids, compiled)
    return {"inputs": [_norm_input(i, fig) for i in ins],
            "outputs": [_norm_output(o, fig) for o in outs], "js": compiled}


def _check_contract_closed(fig: str, out_ids: list[str], formulas: dict[str, str]) -> None:
    """No orphans in either direction — every output has a formula and vice versa."""
    missing = [o for o in out_ids if o not in formulas]
    extra = [k for k in formulas if k not in out_ids]
    if missing:
        raise SpecError(f"explorable '{fig}': outputs without a formula: {missing}")
    if extra:
        raise SpecError(f"explorable '{fig}': formulas for undeclared outputs: {extra}")


def _check_inputs_used(fig: str, in_ids: set[str], compiled: dict[str, str]) -> None:
    """A slider no formula reads is the 'output doesn't track input' failure, inverted."""
    read = {name for js in compiled.values() for name in INPUT_REF_RE.findall(js)}
    unused = sorted(in_ids - read)
    if unused:
        raise SpecError(f"explorable '{fig}': declared inputs that no formula reads: "
                        f"{unused} — a control that changes nothing is the failure the "
                        f"contract exists to prevent")


def _norm_input(spec: dict[str, Any], fig: str) -> dict[str, Any]:
    """Coerce the slider bounds to numbers. Unchecked, a string flows into an HTML
    attribute and can inject arbitrary attributes, including event handlers."""
    lo = num(spec, "min", 0, "input", fig)
    hi = num(spec, "max", 1, "input", fig)
    if hi <= lo:
        raise SpecError(f"explorable '{fig}': input '{spec['id']}' has max <= min")
    return {"id": spec["id"], "label": str(req_key(spec, "label", "explorable", fig)),
            "min": lo, "max": hi, "step": num(spec, "step", 0.01, "input", fig),
            "value": min(max(num(spec, "value", lo, "input", fig), lo), hi)}


def _norm_output(spec: dict[str, Any], fig: str) -> dict[str, Any]:
    decimals = int(num(spec, "decimals", 2, "output", fig))
    if not 0 <= decimals <= MAX_DECIMALS:
        raise SpecError(f"explorable '{fig}': output '{spec['id']}' decimals must be "
                        f"0–{MAX_DECIMALS}; got {decimals}")
    return {"id": spec["id"], "label": str(req_key(spec, "label", "explorable", fig)),
            "decimals": decimals}


# ---------------------------------------------------------------------------
# ASCII rendering — same spec serves the live terminal
# ---------------------------------------------------------------------------


def ascii_figure(block: dict[str, Any]) -> str:
    """Terminal rendering of a figure block. Takes the whole block, not the payload.

    Blanks are honoured here too. The terminal is where the live conversation happens,
    so an ASCII rendering that showed a label the view page gates would hand over the
    answer the learner is supposed to predict.
    """
    kind = block.get("type")
    fig = str(block.get("id", "<no-id>"))
    blanks = set(block.get("blank", []))
    # The same check `figure_html` runs. Without it a mistyped blank id is a silent no-op
    # here, and this is the channel the learner sees *during* the prediction beat — the
    # page is rendered at Recap, after. A silent miss hands over the answer.
    _check_blanks(fig, blanks, block)
    renderer = {"sequence": _ascii_sequence, "layers": _ascii_layers,
                "quorum": _ascii_quorum, "timeline": _ascii_timeline}.get(str(kind))
    if renderer is None:
        return (f"[{kind} figures render on the view page only — "
                f"caption: {block.get('caption', '')}]")
    return renderer(block.get("spec", {}), blanks)


def _label(item: dict[str, Any], blanks: set[str]) -> str:
    return QMARK if item.get("id") in blanks else str(item.get("label", ""))


def _ascii_sequence(spec: dict[str, Any], blanks: set[str]) -> str:
    labels = {p["id"]: p.get("label", p["id"]) for p in spec.get("participants", [])}
    rows = ["  " + "   ".join(labels.values()), ""]
    for m in spec.get("messages", []):
        mark = "╳" if m.get("lost") else "▶"
        rows.append(f"  {labels.get(m['from'], m['from'])} ──{_label(m, blanks)}──{mark} "
                    f"{labels.get(m['to'], m['to'])}")
    for n in spec.get("notes", []):
        rows.append(f"    note over {labels.get(n['over'], n['over'])}: "
                    f"{_label(n, blanks)}")
    return "\n".join(rows)


def _ascii_layers(spec: dict[str, Any], blanks: set[str]) -> str:
    after = spec.get("boundary_after")
    boundary = QMARK if "boundary" in blanks else spec.get("boundary_label", "boundary")
    rows: list[str] = []
    layers = spec.get("layers", [])
    for i, layer in enumerate(layers):
        rows.append(f"    {layer.get('label', '?')}")
        on_boundary = after is not None and i == int(after)
        if i == len(layers) - 1:
            # A boundary below the last layer still has to be drawn — otherwise a figure
            # whose blanked element *is* that boundary shows the learner nothing.
            if on_boundary:
                rows.append(f"  ╌╌╌ {boundary} ╌╌╌")
            break
        rows.append(f"  ╌╌╌ {boundary} ╌╌╌" if on_boundary else "      │")
    return "\n".join(rows)


def _ascii_quorum(spec: dict[str, Any], blanks: set[str]) -> str:
    labels = {n["id"]: n.get("label", n["id"]) for n in spec.get("nodes", [])}
    groups = [" ".join(f"({labels.get(n, n)})" for n in g)
              for g in spec.get("partition", [])]
    rows = ["  " + "   ┊   ".join(groups)]
    if "progress" not in blanks and spec.get("progress", "none") != "none":
        side = spec["progress"]
        rows.append(f"  ({side} side holds the majority and can make progress)")
    return "\n".join(rows)


BAR_W = 40


def _ascii_timeline(spec: dict[str, Any], blanks: set[str]) -> str:
    spans = spec.get("spans", [])
    if not spans:
        return ""
    lo = min(float(s["start"]) for s in spans)
    hi = max(float(s["end"]) for s in spans)
    scale = (hi - lo) or 1.0
    rows = [_timeline_row(a, spans, lo, scale, blanks) for a in spec.get("actors", [])]
    axis = f"{lo:g}".ljust(BAR_W - len(f"{hi:g}")) + f"{hi:g}"
    rows.append(f"  {'':>14} └{axis} {spec.get('unit', '')}".rstrip())
    return "\n".join(rows)


def _timeline_row(actor: dict[str, Any], spans: list[dict[str, Any]], lo: float,
                  scale: float, blanks: set[str]) -> str:
    bar = [" "] * BAR_W
    labels: list[str] = []
    for s in (s for s in spans if s["actor"] == actor["id"]):
        i1 = int((float(s["start"]) - lo) / scale * (BAR_W - 1))
        i2 = max(int((float(s["end"]) - lo) / scale * (BAR_W - 1)), i1 + 1)
        for i in range(i1, min(i2 + 1, BAR_W)):
            bar[i] = "█"
        labels.append(_label(s, blanks))
    name = str(actor.get("label", actor["id"]))[:14]
    return f"  {name:>14} │{''.join(bar)}│ {', '.join(l for l in labels if l)}".rstrip()


# ---------------------------------------------------------------------------
# Page assembly
# ---------------------------------------------------------------------------

PAGE_CSS = """
:root{--bg:#fbfbfa;--fg:#1c1b19;--mut:#6b6862;--acc:#8a5a1f;--box:#ffffff;
--shade:rgba(138,90,31,.13);--line:#c9c5bd}
@media (prefers-color-scheme:dark){:root{--bg:#131313;--fg:#e8e6e1;--mut:#9d9a93;
--acc:#d9a45b;--box:#1d1d1c;--shade:rgba(217,164,91,.16);--line:#3a3936}}
:root[data-theme=dark]{--bg:#131313;--fg:#e8e6e1;--mut:#9d9a93;--acc:#d9a45b;
--box:#1d1d1c;--shade:rgba(217,164,91,.16);--line:#3a3936}
:root[data-theme=light]{--bg:#fbfbfa;--fg:#1c1b19;--mut:#6b6862;--acc:#8a5a1f;
--box:#ffffff;--shade:rgba(138,90,31,.13);--line:#c9c5bd}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:16px/1.6 ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}
.wrap{max-width:56rem;margin:0 auto;padding:2.5rem 1.25rem 5rem}
header{border-bottom:1px solid var(--line);padding-bottom:1.25rem;margin-bottom:2.5rem}
h1{font-size:1.6rem;line-height:1.25;margin:0 0 .35rem}
.meta{color:var(--mut);font-size:.85rem}
figure{margin:0 0 3rem;border:1px solid var(--line);border-radius:10px;
background:var(--box);overflow:hidden}
figcaption{padding:.9rem 1.1rem .2rem;font-weight:600;font-size:.98rem}
.inv{padding:0 1.1rem .9rem;color:var(--mut);font-size:.87rem;font-style:italic}
.fig-body{padding:.4rem 1.1rem 1.1rem;overflow-x:auto}
.pv-svg{display:block;max-width:100%;height:auto}
.predict{margin:0;padding:.85rem 1.1rem;background:var(--shade);
border-top:1px solid var(--line);font-size:.92rem}
details{border-top:1px solid var(--line)}
summary{padding:.8rem 1.1rem;cursor:pointer;font-size:.9rem;color:var(--acc);
font-weight:600}
.reveal{padding:0 1.1rem 1.1rem;font-size:.93rem}
.ctl{display:flex;flex-wrap:wrap;gap:1.25rem;padding:1.1rem}
.ctl label{display:block;font-size:.85rem;color:var(--mut);margin-bottom:.3rem}
.ctl input[type=range]{width:15rem;accent-color:var(--acc)}
.outs{display:flex;flex-wrap:wrap;gap:1.75rem;padding:0 1.1rem 1.2rem}
.out b{display:block;font-size:1.35rem;font-variant-numeric:tabular-nums}
.out span{font-size:.8rem;color:var(--mut)}
.pv-box{fill:var(--box);stroke:var(--fg);stroke-width:1.5}
.pv-note{fill:var(--shade);stroke:var(--line)}
.pv-initial{stroke-width:3}
.pv-t{fill:var(--fg);font:13px ui-sans-serif,system-ui,sans-serif}
.pv-sm{font-size:11.5px;fill:var(--mut)}
.pv-qmark{font-size:30px;font-weight:700;fill:var(--acc)}
.pv-l{stroke:var(--fg);stroke-width:1.5}
.pv-head{fill:var(--fg)}
.pv-lifeline{stroke:var(--line);stroke-dasharray:3 4}
.pv-axis{stroke:var(--mut);stroke-width:1.25}
.pv-partition{stroke:var(--acc);stroke-width:1.75;stroke-dasharray:7 5}
.pv-dash{stroke-dasharray:6 4}
.pv-cut{stroke:var(--acc);stroke-width:2.25}
.pv-illegal{stroke:var(--mut);stroke-dasharray:4 4}
.pv-series{stroke:var(--acc);stroke-width:2.5}
.pv-node{fill:var(--box);stroke:var(--fg);stroke-width:1.5}
.pv-leader-ring{fill:none;stroke-dasharray:4 3}
.pv-group{fill:none;stroke:var(--line);stroke-width:1.25}
.pv-shade{fill:var(--shade)}
.pv-shade-off{fill:none;stroke-dasharray:5 5}
.pv-arrow{stroke-linecap:round}
.pv-span{fill:var(--shade);stroke:var(--fg);stroke-width:1.25}
.pv-blank{stroke:var(--acc);stroke-width:2.5;stroke-dasharray:5 4}
.pv-blank-region{fill:var(--shade);stroke:var(--acc);stroke-dasharray:5 4}
.theme{position:fixed;top:.75rem;right:.75rem;background:var(--box);color:var(--fg);
border:1px solid var(--line);border-radius:6px;padding:.35rem .6rem;font-size:.8rem;
cursor:pointer}
"""

THEME_JS = """
(function(){var b=document.getElementById('theme');if(!b)return;
b.addEventListener('click',function(){var r=document.documentElement;
var d=r.getAttribute('data-theme');var m=window.matchMedia('(prefers-color-scheme:dark)');
var cur=d||(m.matches?'dark':'light');r.setAttribute('data-theme',cur==='dark'?'light':'dark');});})();
"""


def explorable_js(fig: str, compiled: dict[str, Any]) -> str:
    """Generated wiring. Every declared input is read; every declared output is written."""
    reads = ", ".join(f'"{i["id"]}": Number(document.getElementById("in-{fig}-{i["id"]}").value)'
                      for i in compiled["inputs"])
    sets: list[str] = []
    for out in compiled["outputs"]:
        oid = out["id"]
        dec = int(out.get("decimals", 2))
        sets.append(f'document.getElementById("out-{fig}-{oid}").textContent = '
                    f'({compiled["js"][oid]}).toFixed({dec});')
    listeners = "\n".join(
        f'document.getElementById("in-{fig}-{i["id"]}").addEventListener("input", u);'
        for i in compiled["inputs"])
    echoes = "\n".join(
        f'document.getElementById("echo-{fig}-{i["id"]}").textContent = '
        f'document.getElementById("in-{fig}-{i["id"]}").value;'
        for i in compiled["inputs"])
    return (f'(function(){{\nfunction u(){{\nvar v = {{{reads}}};\n'
            + "\n".join(sets) + "\n" + echoes + "\n}\n" + listeners + "\nu();\n})();\n")


def figure_html(spec: dict[str, Any]) -> str:
    fig = check_id(spec.get("id"), "figure id", str(spec.get("id", "<no-id>")))
    kind = str(require(spec, "type", "figure", fig))
    if kind not in RENDERERS:
        raise SpecError(f"figure '{fig}': unknown type '{kind}' "
                        f"(expected one of {', '.join(FIGURE_TYPES)})")
    caption = require(spec, "caption", "figure", fig)
    invariant = require(spec, "invariant", "figure", fig)
    payload = require(spec, "spec", "figure", fig)
    if not isinstance(payload, dict):
        raise SpecError(f"figure '{fig}': 'spec' must be an object")
    blanks = set(spec.get("blank", []))
    _check_blanks(fig, blanks, spec)
    if spec.get("reveal") and not blanks:
        raise SpecError(f"figure '{fig}': has a 'reveal' but nothing is blanked — either "
                        f"blank the element carrying the invariant or drop the reveal")
    # Reveal is required before any geometry work, so a spec missing it reports that
    # rather than whatever the renderer trips over first.
    gated = _gate_html(require(spec, "reveal", "figure", fig), invariant) if blanks else ""
    # The invariant is the figure's one claim, so for a blanked figure it usually *is* the
    # answer. Ungated, it pre-announces what the learner was asked to predict — so it moves
    # inside the gate, and the optional `predict` line takes its place above the figure.
    prompt = (f'<p class="predict">{esc(spec["predict"])}</p>\n'
              if blanks and spec.get("predict") else "")
    visible_inv = "" if blanks else f'<p class="inv">{esc(invariant)}</p>\n'
    svg = RENDERERS[kind](payload, blanks, fig)
    return (f'<figure id="fig-{fig}">\n<figcaption>{esc(caption)}</figcaption>\n'
            f'{visible_inv}<div class="fig-body">{svg}</div>\n{prompt}{gated}</figure>\n')


def _check_blanks(fig: str, blanks: set[str], spec: dict[str, Any]) -> None:
    allowed = blankable_ids(spec)
    unknown = sorted(blanks - allowed)
    if unknown:
        raise SpecError(f"figure '{fig}': blank ids {unknown} match nothing blankable "
                        f"(allowed: {sorted(allowed) or 'none — add ids to the elements'})."
                        f" A silent no-op here would hand the learner the answer.")


def _gate_html(reveal: str, invariant: str) -> str:
    return ('<details><summary>I have committed to a prediction — reveal</summary>\n'
            f'<p class="reveal">{esc(reveal)}</p>\n'
            f'<p class="inv">{esc(invariant)}</p>\n</details>\n')


def explorable_html(spec: dict[str, Any]) -> tuple[str, str]:
    fig = str(spec.get("id", "<no-id>"))
    compiled = compile_explorable(spec)
    ctl = "\n".join(_input_html(fig, i) for i in compiled["inputs"])
    outs = "\n".join(
        f'<div class="out"><b id="out-{esc(fig)}-{esc(o["id"])}">—</b>'
        f'<span>{esc(o["label"])}</span></div>' for o in compiled["outputs"])
    body = (f'<div class="ctl">{ctl}</div>\n<div class="outs">{outs}</div>\n')
    # Invariant inside the gate for the same reason as a blanked figure: it states the
    # shape the learner is being asked to predict.
    html = (f'<figure id="fig-{fig}">\n'
            f'<figcaption>{esc(spec["caption"])}</figcaption>\n'
            f'<p class="predict">{esc(spec["predict"])}</p>\n'
            f'<details><summary>I have made my prediction — show the model</summary>\n'
            f'{body}<p class="inv">{esc(spec["invariant"])}</p>\n</details>\n</figure>\n')
    return html, explorable_js(fig, compiled)


def _input_html(fig: str, spec: dict[str, Any]) -> str:
    """Slider markup. Bounds are floats by the time they get here (`_norm_input`), so the
    `:g` formatting cannot emit anything that escapes the attribute."""
    iid = spec["id"]
    return (f'<div><label for="in-{fig}-{iid}">{esc(spec["label"])} '
            f'(<span id="echo-{fig}-{iid}"></span>)</label>'
            f'<input type="range" id="in-{fig}-{iid}" '
            f'min="{spec["min"]:g}" max="{spec["max"]:g}" '
            f'step="{spec["step"]:g}" value="{spec["value"]:g}">'
            f'</div>')


@dataclass
class Page:
    html: str
    manifest: dict[str, Any] = field(default_factory=dict)


def build_page(markdown: str, artifact: Path) -> Page:
    blocks = extract_blocks(markdown)
    if not blocks:
        raise SpecError(f"{artifact.name}: no primer-figure or primer-explorable blocks "
                        f"found — nothing to render")
    title_match = TITLE_RE.search(markdown)
    title = title_match.group(1) if title_match else artifact.stem
    figures: list[str] = []
    scripts: list[str] = []
    manifest: dict[str, Any] = {"artifact": artifact.name, "figures": []}

    seen: set[str] = set()
    for block in blocks:
        _check_unique(block, seen)
        if block.kind == "figure":
            figures.append(figure_html(block.spec))
            manifest["figures"].append(_figure_manifest(block.spec))
            continue
        html, js = explorable_html(block.spec)
        figures.append(html)
        scripts.append(js)
        manifest["figures"].append(_explorable_manifest(block.spec))

    doc = (f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
           f'<meta http-equiv="Content-Security-Policy" content="{CSP}">\n'
           f'<meta name="viewport" content="width=device-width,initial-scale=1">\n'
           f'<title>{esc(title)} — primer</title>\n<style>{PAGE_CSS}</style>\n</head>\n'
           f'<body>\n<button class="theme" id="theme">theme</button>\n'
           f'{ARROW_DEFS_PAGE}\n<div class="wrap">\n'
           f'<header>\n<h1>{esc(title)}</h1>\n'
           f'<p class="meta">Figures for <code>{esc(artifact.name)}</code>. '
           f'Generated locally; nothing on this page leaves your machine.</p>\n</header>\n'
           f'{"".join(figures)}</div>\n'
           f'<!--pv-manifest {_manifest_comment(manifest)}-->\n'
           f'<script>{THEME_JS}{"".join(scripts)}</script>\n</body>\n</html>\n')
    return Page(html=doc, manifest=manifest)


def _check_unique(block: Block, seen: set[str]) -> None:
    """Duplicate ids give two elements the same anchor; getElementById silently wins the
    first, so the second figure's wiring would be dead but validated."""
    if block.id in seen:
        raise SpecError(f"duplicate figure id '{block.id}' — ids must be unique per lesson")
    seen.add(block.id)


def _manifest_comment(manifest: dict[str, Any]) -> str:
    """Serialize the manifest so it cannot terminate its own HTML comment.

    `json.dumps` leaves `<` and `-->` intact, so a caption containing `-->` (Mermaid edge
    syntax — a plausible thing to write *about*) would close the comment early and expose
    everything after it to the HTML parser. Both replacements stay valid JSON.
    """
    payload = json.dumps(manifest, separators=(",", ":"))
    return payload.replace("<", "\\u003c").replace("--", "\\u002d\\u002d")


def _figure_manifest(spec: dict[str, Any]) -> dict[str, Any]:
    # The reveal *text* is deliberately not recorded here. The manifest is a plain
    # comment in the page, and a learner reading source shouldn't find the answer
    # sitting in JSON next to the figure it belongs to.
    return {"id": spec.get("id"), "kind": "figure", "caption": spec.get("caption", ""),
            "blank": list(spec.get("blank", []))}


def _explorable_manifest(spec: dict[str, Any]) -> dict[str, Any]:
    contract = spec.get("contract", {})
    return {"id": spec.get("id"), "kind": "explorable", "caption": spec.get("caption", ""),
            "inputs": [i["id"] for i in contract.get("inputs", [])],
            "outputs": [o["id"] for o in contract.get("outputs", [])]}


# ---------------------------------------------------------------------------
# Validation. Runs against the manifest the page carries, so `validate` works
# standalone on any generated page.
# ---------------------------------------------------------------------------

MANIFEST_RE = re.compile(r"<!--pv-manifest (\{.*?\})-->", re.DOTALL)
SVG_RE = re.compile(r"<svg\b.*?</svg>", re.DOTALL)
DETAILS_RE = re.compile(r"<details(?P<attrs>[^>]*)>(?P<body>.*?)</details>", re.DOTALL)

TAG_RE = re.compile(r"<[a-zA-Z][^>]*>")
ATTR_RE = re.compile(r"""([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)""")
STYLE_RE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.DOTALL)
SCRIPT_RE = re.compile(r"<script\b[^>]*>(.*?)</script>", re.DOTALL)
# Attributes that can cause a fetch. Scanning by attribute name rather than by a
# `src=`-shaped pattern is what catches `srcset`, `poster`, `data`, and friends.
URL_ATTRS = {"src", "srcset", "href", "xlink:href", "data", "poster", "action",
             "formaction", "background", "cite", "codebase", "longdesc", "profile",
             "manifest", "ping", "usemap"}
# Schemes that stay on the machine. Anything else in a URL attribute is a network hop.
LOCAL_URL_RE = re.compile(r"^\s*(?:#|data:|file:)", re.IGNORECASE)
# Network APIs. A CSP blocks these at runtime, but failing the build is a clearer signal.
JS_NETWORK_RE = re.compile(r"\bfetch\s*\(|XMLHttpRequest|\bimport\s*\(|sendBeacon"
                           r"|new\s+Worker|EventSource|WebSocket|\beval\s*\(",
                           re.IGNORECASE)
CSS_NETWORK_RE = re.compile(r"@import|url\(\s*['\"]?(?!data:)[a-zA-Z0-9+.-]*:?//",
                            re.IGNORECASE)


def validate_page(html: str) -> list[str]:
    """Return the list of checks that passed; raise ValidationError on the first failure."""
    manifest = _read_manifest(html)
    checks = [
        ("comment integrity", lambda: _check_comment_integrity(html)),
        ("figure well-formedness", lambda: _check_wellformed(html, manifest)),
        ("no external requests", lambda: _check_no_external(html)),
        ("caption coverage", lambda: _check_captions(html, manifest)),
        ("contract satisfaction", lambda: _check_contracts(html, manifest)),
        ("faded-reveal integrity", lambda: _check_reveals(html, manifest)),
    ]
    passed: list[str] = []
    for name, check in checks:
        check()
        passed.append(name)
    return passed


def _read_manifest(html: str) -> dict[str, Any]:
    m = MANIFEST_RE.search(html)
    if not m:
        raise ValidationError("no pv-manifest comment — page was not produced by "
                              "primer_view.py render, so it cannot be validated")
    return json.loads(m.group(1))


def _check_comment_integrity(html: str) -> None:
    """The page must contain exactly one comment terminator: the manifest's own.

    A spec string containing `-->` would otherwise close the manifest comment early and
    hand the rest of it to the HTML parser. `_manifest_comment` escapes it at generation;
    this is the check that the escaping actually held.
    """
    count = html.count("-->")
    if count != 1:
        raise ValidationError(f"comment integrity: found {count} comment terminators, "
                              f"expected exactly 1 (the manifest) — a spec string has "
                              f"escaped into markup")


def _check_wellformed(html: str, manifest: dict[str, Any]) -> None:
    """Every generated SVG must parse as XML — a broken figure renders blank otherwise."""
    blocks = SVG_RE.findall(html)
    has_figure = any(f.get("kind") != "explorable" for f in manifest.get("figures", []))
    if not blocks and has_figure:
        raise ValidationError("figure well-formedness: no <svg> blocks found")
    for i, block in enumerate(blocks):
        try:
            ET.fromstring(block)
        except ET.ParseError as exc:
            raise ValidationError(f"figure well-formedness: svg #{i + 1} does not "
                                  f"parse: {exc}") from exc


def _check_no_external(html: str) -> None:
    """The page must be fully self-contained.

    Scanned per *tag attribute* rather than with a `src=`-shaped regex over the whole
    document. That matters in both directions: the old shape missed `srcset`, `poster`,
    `data`, and `http-equiv=refresh`, and it false-positived on inert prose (a lesson
    *about* HTML legitimately contains `src='x'` in a caption).
    """
    _check_tags(html)
    for css in STYLE_RE.findall(html):
        if CSS_NETWORK_RE.search(css):
            raise ValidationError("no external requests: a <style> block imports or "
                                  "fetches a remote resource")
    for js in SCRIPT_RE.findall(html):
        hit = JS_NETWORK_RE.search(js)
        if hit:
            raise ValidationError(f"no external requests: a <script> block uses "
                                  f"'{hit.group(0).strip()}' — the page must not reach "
                                  f"the network or evaluate dynamic code")


def _check_tags(html: str) -> None:
    for tag in TAG_RE.findall(html):
        for name, raw in ATTR_RE.findall(tag):
            _check_attr(name.lower(), raw.strip("\"'"), tag)


def _check_attr(name: str, value: str, tag: str) -> None:
    if name.startswith("on"):
        raise ValidationError(f"no external requests: inline event handler '{name}' in "
                              f"{tag[:70]!r} — all behaviour must come from the generated "
                              f"script block")
    if name == "http-equiv" and value != "Content-Security-Policy":
        raise ValidationError(f"no external requests: unexpected http-equiv '{value}' "
                              f"(a meta refresh can navigate off the page)")
    if name in URL_ATTRS and not LOCAL_URL_RE.match(value):
        raise ValidationError(f"no external requests: attribute '{name}={value[:40]}' "
                              f"points outside the page — only '#', 'data:', and 'file:' "
                              f"are local")


def _check_captions(html: str, manifest: dict[str, Any]) -> None:
    for fig in manifest.get("figures", []):
        anchor = f'id="fig-{fig["id"]}"'
        if anchor not in html:
            raise ValidationError(f"caption coverage: figure '{fig['id']}' is in the "
                                  f"manifest but not in the document")
        if not fig.get("caption"):
            raise ValidationError(f"caption coverage: figure '{fig['id']}' has no caption")
        if f"<figcaption>{esc(fig['caption'])}</figcaption>" not in html:
            raise ValidationError(f"caption coverage: figure '{fig['id']}' caption is "
                                  f"missing from the rendered document")


def _check_contracts(html: str, manifest: dict[str, Any]) -> None:
    for fig in (f for f in manifest.get("figures", []) if f.get("kind") == "explorable"):
        fid = fig["id"]
        for iid in fig.get("inputs", []):
            _require_in_page(html, f'id="in-{fid}-{iid}"', fid,
                             f"declared input '{iid}' has no control")
            _require_in_page(html, f'getElementById("in-{fid}-{iid}").addEventListener',
                             fid, f"declared input '{iid}' is never listened to")
        for oid in fig.get("outputs", []):
            _require_in_page(html, f'id="out-{fid}-{oid}"', fid,
                             f"declared output '{oid}' has no readout")
            _require_in_page(html, f'getElementById("out-{fid}-{oid}").textContent =',
                             fid, f"declared output '{oid}' is never written")


def _require_in_page(html: str, needle: str, fid: str, problem: str) -> None:
    if needle not in html:
        raise ValidationError(f"contract satisfaction: explorable '{fid}': {problem}")


def _check_reveals(html: str, manifest: dict[str, Any]) -> None:
    """A blanked figure's answer must be unreachable until the learner commits.

    Checked structurally, per figure — the answer must sit inside that figure's own
    closed <details> and nowhere else in the figure. Text matching would be fooled by
    two figures sharing a phrase, and would miss an answer duplicated outside the gate.
    """
    for fig in manifest.get("figures", []):
        fid = str(fig["id"])
        region = _figure_region(html, fid)
        explorable = fig.get("kind") == "explorable"
        # An unblanked figure has nothing to gate. `diagramming.md` pushes hard toward
        # blanking, but a pure orientation figure legitimately has no prediction to make,
        # so this is a check on gating being *effective*, not on it being present.
        if not explorable and not fig.get("blank"):
            continue
        gated = _closed_details_body(region, fid)
        needle = '<div class="ctl">' if explorable else '<p class="reveal">'
        _assert_gated(region, gated, fid, needle, "the model" if explorable else "the answer")


def _figure_region(html: str, fid: str) -> str:
    m = re.search(rf'<figure id="fig-{re.escape(fid)}">(.*?)</figure>', html, re.DOTALL)
    if not m:
        raise ValidationError(f"faded-reveal integrity: figure '{fid}' is in the manifest "
                              f"but has no <figure> element in the document")
    return m.group(1)


def _closed_details_body(region: str, fid: str) -> str:
    m = DETAILS_RE.search(region)
    if not m:
        raise ValidationError(f"faded-reveal integrity: figure '{fid}' needs a <details> "
                              f"gate so the learner predicts before seeing the answer")
    if re.search(r"\bopen\b", m.group("attrs")):
        raise ValidationError(f"faded-reveal integrity: figure '{fid}': the <details> is "
                              f"marked open, so the answer is visible without predicting")
    return m.group("body")


def _assert_gated(region: str, gated: str, fid: str, needle: str, what: str) -> None:
    if needle not in region:
        raise ValidationError(f"faded-reveal integrity: figure '{fid}': {what} is missing "
                              f"from the figure")
    if needle not in gated:
        raise ValidationError(f"faded-reveal integrity: figure '{fid}': {what} is outside "
                              f"the closed <details> — the learner can see it without "
                              f"predicting first")
    if region.count(needle) != gated.count(needle):
        raise ValidationError(f"faded-reveal integrity: figure '{fid}': {what} also "
                              f"appears outside the gate, so gating it achieves nothing")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

SCHEMA_HELP = """Figure spec blocks live in the lesson artifact as HTML comments:

  <!--primer-figure
  {"id":"...","type":"sequence","caption":"...","invariant":"...",
   "blank":["m3"],"reveal":"the answer plus why","spec":{...}}
  -->

Common fields: id, type, caption, invariant (all required); blank + reveal (blank
requires reveal, and reveal requires blank); optional predict (shown above a blanked
figure, since the invariant is gated with the reveal); spec (type-specific).

Ids match ^[A-Za-z][A-Za-z0-9_-]{0,63}$. Labels are capped at 34 chars (past that they
would be clipped by the viewBox). Only elements carrying an "id" are blankable, and a
blank id that matches nothing is an error in both the page and the ASCII channel.

  sequence  spec.participants[{id,label}], spec.messages[{id,from,to,label,dashed?,lost?}],
            spec.notes[{id?,after,over,label}]                 blankable: message/note ids
  state     spec.states[{id,label,initial?}], spec.transitions[{id?,from,to,label}],
            spec.illegal[{id?,from,to,label}]                  blankable: transition ids
  quorum    spec.nodes[{id,label,leader?}], spec.partition[[ids],[ids]],
            spec.progress left|right|none                      blankable: "progress"
  layers    spec.layers[{label,detail?}], spec.boundary_after, spec.boundary_label
                                                               blankable: "boundary"
  curve     spec.x{label,min,max}, spec.y{label,min,max},
            spec.series[{label,points[[x,y]...]}], spec.annotate[{x,label}]
                                                               blankable: "tail"
  timeline  spec.actors[{id,label}], spec.spans[{id?,actor,start,end,label}], spec.unit
                                                               blankable: span ids

Explorables declare a contract; the wiring is generated, never hand-written:

  <!--primer-explorable
  {"id":"...","caption":"...","invariant":"...","predict":"...",
   "contract":{"inputs":[{"id":"rho","label":"...","min":0.05,"max":0.95,"step":0.01,
                          "value":0.5}],
               "outputs":[{"id":"wait","label":"...","decimals":2}]},
   "formulas":{"wait":"rho / (1 - rho)"}}
  -->

Formulas are PARSED as arithmetic, not merely filtered: numbers, declared input ids,
+ - * / ( ) , and min max abs sqrt exp log pow with correct arity (min/max/pow take 2).
Max 2 inputs, each of which some formula must read. Every output needs exactly one
formula and vice versa. Input ids may not contain "-" (a-b is subtraction); output ids
may. Slider bounds must be numeric with max > min; decimals is 0-8.
"""


def cmd_templates(_: argparse.Namespace) -> int:
    print(f"Figure forms: {', '.join(FIGURE_TYPES)}\n")
    print(SCHEMA_HELP)
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    artifact = Path(args.artifact)
    page = build_page(artifact.read_text(encoding="utf-8"), artifact)
    # Validate *before* writing. The output path is deterministic and the learner is told
    # to click it, so writing first would leave an invalid page — or destroy a valid
    # earlier one — at exactly the path the engine promises is safe to open.
    passed = validate_page(page.html)
    out = artifact.with_name(artifact.stem + ".view.html")
    out.write_text(page.html, encoding="utf-8")
    print(f"ok: {out} ({len(page.manifest['figures'])} figures)")
    print("    checks passed: " + ", ".join(passed))
    print(f"    open: {out.resolve().as_uri()}")
    if args.open:
        webbrowser.open(out.resolve().as_uri())
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    html = Path(args.page).read_text(encoding="utf-8")
    passed = validate_page(html)
    print("ok: " + ", ".join(passed))
    return 0


def cmd_ascii(args: argparse.Namespace) -> int:
    artifact = Path(args.artifact)
    blocks = extract_blocks(artifact.read_text(encoding="utf-8"))
    wanted = [b for b in blocks if b.id == args.id] if args.id else blocks
    if not wanted:
        print(f"error: no figure with id '{args.id}' in {artifact.name}", file=sys.stderr)
        return 2
    for block in wanted:
        print(f"{block.spec.get('caption', '')}\n")
        if block.kind != "figure":
            print(f"[explorable '{block.id}' has no terminal rendering — it needs the "
                  f"view page. Prediction prompt: {block.spec.get('predict', '')}]\n")
            continue
        print(ascii_figure(block.spec))
        print()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="primer_view.py",
        description="Render a lesson artifact's figure specs into a self-contained "
                    "local view page.")
    subs = parser.add_subparsers(dest="cmd", required=True)

    subs.add_parser("templates", help="list figure forms and their spec schema") \
        .set_defaults(func=cmd_templates)

    p_render = subs.add_parser("render", help="write and validate <stem>.view.html")
    p_render.add_argument("artifact")
    p_render.add_argument("--open", action="store_true", help="open the page after writing")
    p_render.set_defaults(func=cmd_render)

    p_val = subs.add_parser("validate", help="re-check an existing view page")
    p_val.add_argument("page")
    p_val.set_defaults(func=cmd_validate)

    p_ascii = subs.add_parser("ascii", help="terminal rendering of a figure")
    p_ascii.add_argument("artifact")
    p_ascii.add_argument("--id", default="", help="figure id (default: all)")
    p_ascii.set_defaults(func=cmd_ascii)

    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (SpecError, ValidationError) as exc:
        # Deliberate: fail loudly with the specific problem so the caller fixes the spec
        # and re-runs, rather than showing the learner a broken or spoiled page.
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        # Specs are model-authored, so a shape this code didn't anticipate is a spec
        # problem, not a crash to show the learner. Report it as one and exit non-zero
        # rather than printing a traceback.
        print(f"error: internal failure while rendering ({type(exc).__name__}: {exc}). "
              f"This is a malformed spec the validator did not name — check the figure "
              f"spec against `primer_view.py templates`.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
