"""Answer-leak guard: a deterministic check on every hint before it reaches the learner.

Prompting the model "don't reveal the answer" is not a guarantee, so this code checks
the generated text. A hint leaks if it contains:
  1. an equation with the same solution set as the problem (e.g. `x = 4`, or a
     correct next line like `2x = 8`);
  2. a phrase giving a root ("x is 4", "the answer is 4");
  3. the corrected version of the fragment the student got wrong (e.g. `-2x + 6`).
"""

from __future__ import annotations

import re

from .safe_parse import ParseError, normalize, parse_line
from .verifier import _run, compare_sets, expr_equivalent, solution_set

_PHRASE = (
    r"(?:\b{v}\b|answer|solution|result|value)\s*(?:is|=|equals|should be|must be|will be|would be|"
    r"comes out (?:to|as)|works out (?:to|as)|of)\s*(-?\s*\d+(?:\s*/\s*\d+)?)"
)


def _spans(text: str, var: str) -> list[str]:
    t = normalize(text)
    spans = re.findall(r"`([^`]{1,120})`", t)
    allowed = rf"[0-9{var}+\-*/^().=√± ]"
    for run in re.findall(rf"{allowed}+", re.sub(r"`[^`]*`", " ", t)):
        run = run.strip(" .=")
        if re.search(r"\d", run) and re.search(rf"[{var}=+\-*/^]", run):
            spans.append(run)
    return spans


def _numbers_from_roots(correct_set) -> set:
    try:
        return {r for r in correct_set} if correct_set is not None and correct_set.is_FiniteSet else set()
    except (AttributeError, TypeError):
        return set()


def check(text: str, var: str, correct_set=None, correct_fragment=None) -> bool:
    """True when the hint is safe (no leak)."""
    result = _run(_check, text, var, correct_set, correct_fragment)
    return bool(result)  # a timeout counts as unsafe


def _check(text, var, correct_set, correct_fragment) -> bool:
    roots = _numbers_from_roots(correct_set)
    for m in re.finditer(_PHRASE.format(v=re.escape(var)), normalize(text), re.I):
        try:
            val = parse_line(m[1].replace(" ", ""), var).expr
        except ParseError:
            continue
        if any((val - r).simplify() == 0 for r in roots):
            return False
    for span in _spans(text, var):
        try:
            pl = parse_line(span, var)
        except ParseError:
            continue
        if pl.kind == "equation" and correct_set is not None and len(roots) > 0:
            if pl.var in {s for lhs, rhs in pl.eqs for s in (lhs - rhs).free_symbols}:
                if compare_sets(correct_set, solution_set(pl)) == "equal":
                    return False
        # An unexpanded bracket is the student's own starting point, not the fix.
        if pl.kind == "expression" and correct_fragment is not None and "(" not in span:
            if pl.var in pl.expr.free_symbols or not getattr(correct_fragment, "free_symbols", None):
                if expr_equivalent(pl.expr, correct_fragment, pl.var) is True:
                    return False
    return True
