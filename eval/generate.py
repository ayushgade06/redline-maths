"""Build the synthetic evaluation set from eval/seeds.json.

For every correct seed solution, every step k and every misconception that applies to
line k-1, write an erroneous solution: lines 1..k-1, the buggy line k, then a final line
with the buggy line's own solution. Labels: first_error = k, misconception = rule.
Deterministic (no randomness).

    python eval/generate.py   ->  eval/synthetic.json
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))

from sympy import Add, Pow, sqrt  # noqa: E402

from redline.malrules import _equation_candidates, to_ascii  # noqa: E402
from redline.safe_parse import ParseError, parse_line  # noqa: E402
from redline.verifier import compare_sets, solution_set  # noqa: E402


def clause_ascii(lhs, rhs) -> str:
    return f"{to_ascii(lhs)} = {to_ascii(rhs)}"


def answer_line(pl) -> str | None:
    s = solution_set(pl)
    if not s.is_FiniteSet or len(s) == 0 or len(s) > 2:
        return None
    return " or ".join(f"x = {to_ascii(v)}" for v in sorted(s, key=float))


def buggy_lines(prev, correct_next: str):
    """Yield (rule, buggy_ascii) for line k given line k-1."""
    seen = set()
    for rule, cand, _node, _corr in _equation_candidates(prev):
        if rule in seen:
            continue
        text = " or ".join(clause_ascii(lhs, rhs) for lhs, rhs in cand)
        yield rule, text
        seen.add(rule)
    lhs, rhs = prev.eqs[0]
    for sq, other in ((lhs, rhs), (rhs, lhs)):
        if isinstance(sq, Pow) and sq.exp == 2 and prev.var not in other.free_symbols and other.is_positive:
            yield "SQRT_LOST_NEG_ROOT", f"{to_ascii(sq.base)} = {to_ascii(sqrt(other))}"
    x = prev.var
    if all(e.is_polynomial(x) for e in (lhs, rhs)):
        terms = Add.make_args((lhs - rhs).expand())
        if len(terms) == 2 and all(t.has(x) and t.as_coeff_exponent(x)[1] >= 1 for t in terms):
            a, b = terms  # a + b = 0 with both terms divisible by x
            yield "DIV_BY_VARIABLE", f"{to_ascii((a / x).expand())} = {to_ascii((-b / x).expand())}"
    m = re.search(r"\d+", correct_next)
    if m and int(m.group()) >= 2:
        yield "ARITH_SLIP", correct_next[: m.start()] + str(int(m.group()) + 1) + correct_next[m.end() :]


def main():
    seeds = json.loads((ROOT / "eval" / "seeds.json").read_text(encoding="utf-8"))
    cases = []
    for seed in seeds:
        lines = seed["lines"]
        cases.append({"seed": seed["id"], "lines": lines, "first_error": None, "misconception": None})
        for k in range(1, len(lines)):
            prev = parse_line(lines[k - 1], "x")
            if prev.kind != "equation":
                continue
            correct_set = solution_set(parse_line(lines[k], "x"))
            for rule, bug in buggy_lines(prev, lines[k]):
                try:
                    pl = parse_line(bug, "x")
                except ParseError:
                    continue
                if compare_sets(correct_set, solution_set(pl)) == "equal":
                    continue  # the "bug" happens to be harmless here
                final = answer_line(pl)
                tail = [final] if final and final.replace(" ", "") != bug.replace(" ", "") else []
                cases.append({"seed": seed["id"], "lines": lines[:k] + [bug] + tail, "first_error": k, "misconception": rule})
    out = ROOT / "eval" / "synthetic.json"
    out.write_text(json.dumps(cases, indent=1), encoding="utf-8")
    n_err = sum(c["first_error"] is not None for c in cases)
    print(f"wrote {len(cases)} cases ({n_err} with a seeded error) to {out}")


if __name__ == "__main__":
    main()
