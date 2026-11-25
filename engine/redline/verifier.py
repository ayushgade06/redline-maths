"""Step verifier: the only component that decides mathematical correctness.

For equations, a step is valid when it keeps the solution set over the reals.
For expressions, a step is valid when both sides are symbolically equal (numeric
spot-check fallback). The LLM is never consulted here.
"""

from __future__ import annotations

import random
import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field

from sympy import EmptySet, FiniteSet, Poly, PolynomialError, Rational, S, Union, simplify, solveset

from .safe_parse import ParsedLine, ParseError, detect_variable, parse_line

TIMEOUT_S = 3.0
MAX_DEGREE = 4
ERROR_STATUSES = {"invalid", "lost_solution"}

# ponytail: a Python thread can't be killed, so a timed-out SymPy call keeps running in
# the pool. Input caps in safe_parse bound the worst case; use a process pool if abused.
_pool = ThreadPoolExecutor(max_workers=8)


@dataclass
class LineResult:
    status: str
    detail: str = ""


@dataclass
class VerifyResult:
    variable: str
    lines: list[LineResult]
    first_error_index: int | None
    final_correct: bool | None
    scope_ok: bool
    # Server-only fields: never serialised to the client.
    parsed: list = field(default_factory=list, repr=False)
    base: ParsedLine | None = field(default=None, repr=False)
    correct_set: object = field(default=None, repr=False)


def _run(fn, *args):
    try:
        return _pool.submit(fn, *args).result(timeout=TIMEOUT_S)
    except FutureTimeout:
        return None


def solution_set(pl: ParsedLine):
    out = EmptySet
    for lhs, rhs in pl.eqs:
        out = Union(out, solveset(lhs - rhs, pl.var, S.Reals))
    return out


def _same(a, b) -> bool:
    try:
        d = a - b
        if d == 0 or simplify(d) == 0:
            return True
        return abs(complex(d.evalf())) < 1e-9
    except (TypeError, ValueError):
        return False


def _finite_subset(a: FiniteSet, b: FiniteSet) -> bool:
    return all(any(_same(x, y) for y in b) for x in a)


def compare_sets(a, b) -> str | None:
    """Relation of B (student's new line) to A (previous line)."""
    if isinstance(a, FiniteSet | type(EmptySet)) and isinstance(b, FiniteSet | type(EmptySet)):
        a_in_b = _finite_subset(a, b) if a else True
        b_in_a = _finite_subset(b, a) if b else True
    else:
        if a == b:
            return "equal"
        a_in_b, b_in_a = a.is_subset(b), b.is_subset(a)
        if a_in_b is None or b_in_a is None:
            return None
    if a_in_b and b_in_a:
        return "equal"
    if b_in_a:
        return "lost"
    if a_in_b:
        return "gained"
    return "different"


def expr_equivalent(a, b, var) -> bool | None:
    d = a - b
    try:
        if simplify(d) == 0:
            return True
    except (TypeError, ValueError):
        pass
    rng = random.Random(7)
    checked = 0
    for _ in range(20):
        r = Rational(rng.randint(-90, 90), rng.choice([1, 2, 3, 7, 10]))
        try:
            va, vb = complex(a.subs(var, r).evalf()), complex(b.subs(var, r).evalf())
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        if any(v != v or abs(v) == float("inf") or abs(v.imag) > 1e-12 for v in (va, vb)):
            continue  # pole or outside the real domain
        if abs(va - vb) > 1e-9 * max(1.0, abs(va)):
            return False
        checked += 1
        if checked >= 7:
            return True
    return None


def classify(prev: ParsedLine, curr: ParsedLine) -> LineResult:
    if prev.kind != curr.kind:
        return LineResult("segment_break", "segment_break")
    if curr.kind == "expression":
        eq = _run(expr_equivalent, prev.expr, curr.expr, curr.var)
        if eq is None:
            return LineResult("undetermined", "timeout")
        return LineResult("valid", "equivalent") if eq else LineResult("invalid", "not_equivalent")

    def _cmp():
        sb = solution_set(curr)
        rel = compare_sets(solution_set(prev), sb)
        # Squaring can add a few extraneous roots (a warning); turning the equation into an
        # identity like 3x = 3x adds infinitely many, which is simply wrong.
        if rel == "gained" and not sb.is_FiniteSet:
            return "different"
        return rel

    rel = _run(_cmp)
    return {
        "equal": LineResult("valid", "equivalent"),
        "lost": LineResult("lost_solution", "lost_solution"),
        "gained": LineResult("gained_solution", "gained_solution"),
        "different": LineResult("invalid", "solution_set_changed"),
        None: LineResult("undetermined", "timeout"),
    }[rel]


def is_solved(pl: ParsedLine) -> bool:
    """Every clause isolates the variable: `x = 4`, `x = 3 or x = -3`, `4 = x`."""
    if pl.kind != "equation":
        return False
    for lhs, rhs in pl.eqs:
        if not ((lhs == pl.var and pl.var not in rhs.free_symbols) or (rhs == pl.var and pl.var not in lhs.free_symbols)):
            return False
    return True


def _within_scope(pl: ParsedLine) -> bool:
    exprs = [lhs - rhs for lhs, rhs in pl.eqs] if pl.kind == "equation" else [pl.expr]
    for e in exprs:
        try:
            num = e.as_numer_denom()[0].expand()
            if Poly(num, pl.var).degree() > MAX_DEGREE:
                return False
        except PolynomialError:
            continue  # sqrt etc.: not a polynomial, still in scope
    return True


_PROBLEM_WORDS = re.compile(r"^\s*(solve|simplify|evaluate|find)\b[^:0-9(]*:?|\bfor\s+[a-z]\s*\.?\s*$", re.I)


def clean_problem(problem: str | None) -> str | None:
    if not problem:
        return None
    p = _PROBLEM_WORDS.sub("", problem).strip().rstrip(".")
    return p or None


def verify_lines(problem: str | None, lines: list[str]) -> VerifyResult:
    problem = clean_problem(problem)
    var = detect_variable(([problem] if problem else []) + lines)  # may raise unsupported_scope

    base: ParsedLine | None = None
    if problem:
        try:
            base = parse_line(problem, var)
        except ParseError:
            base = None

    results: list[LineResult] = []
    parsed: list[ParsedLine | None] = []
    prev = base
    for text in lines:
        try:
            pl = parse_line(text, var)
        except ParseError as e:
            if e.code == "unsupported_scope":
                raise
            results.append(LineResult("unreadable", e.reason))
            parsed.append(None)
            continue
        parsed.append(pl)
        restates = prev is base and base is not None and text.replace(" ", "") == problem.replace(" ", "")
        results.append(LineResult("start", "start") if prev is None or restates else classify(prev, pl))
        prev = pl

    if base is None:
        base = next((p for p in parsed if p is not None), None)

    first_error = next((i for i, r in enumerate(results) if r.status in ERROR_STATUSES), None)

    final_correct = None
    correct_set = None
    last_i = max((i for i, p in enumerate(parsed) if p is not None), default=None)
    if base is not None and base.kind == "equation":
        correct_set = _run(solution_set, base)
    if last_i is not None and base is not None:
        last = parsed[last_i]
        if base.kind == "equation" and is_solved(last) and correct_set is not None:
            rel = _run(lambda: compare_sets(correct_set, solution_set(last)))
            final_correct = None if rel is None else rel == "equal"
        elif base.kind == "expression" and last.kind == "expression" and last_i > 0:
            eq = _run(expr_equivalent, base.expr, last.expr, base.var)
            final_correct = eq
    if first_error is None and final_correct is False and last_i is not None:
        # Every step followed from the one before, yet the answer is wrong: typically an
        # extraneous root from squaring/multiplying that was never checked.
        gained = any(r.status == "gained_solution" for r in results)
        results[last_i] = LineResult("invalid", "keeps_extraneous" if gained else "final_answer_mismatch")
        first_error = last_i

    scope_ok = all(_within_scope(p) for p in [base, *parsed] if p is not None)
    return VerifyResult(var, results, first_error, final_correct, scope_ok, parsed, base, correct_set)
