"""Executable misconceptions.

Each rewrite rule applies a known *buggy* transformation to the previous line. If one
of those buggy successors has exactly the student's solution set (or is the same
expression), the diagnosis is proven: we can reproduce the mistake. Relation
detectors cover errors that are visible only in how the solution set changed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import islice

from sympy import Add, Integer, Mul, Pow, S, Symbol, gcd, preorder_traversal, sign, solve, solveset, sqrt

from .safe_parse import ParsedLine
from .verifier import _run, compare_sets, expr_equivalent, solution_set

MAX_CANDIDATES = 200


@dataclass
class Diagnosis:
    id: str
    evidence: str  # "verified" | "ai_hypothesis"
    focus: str | None = None  # ASCII fragment of the student's previous line
    rationale: str | None = None
    correct_fragment: object = None  # server-only: what the fragment should become (guard input)


def to_ascii(e) -> str:
    s = str(e)
    s = re.sub(r"(?<![\d.])1\*", "", s)
    s = re.sub(r"(^|\()0 - ", r"\1-", s)
    s = s.replace(" + 0", "").replace("**", "^").replace("+ -", "- ")
    s = re.sub(r"(\d)\*([a-z(])", r"\1\2", s)
    s = re.sub(r"\)\*\(", ")(", s)
    return s


def _factors(m: Mul) -> list:
    out = []
    for a in m.args:
        out.extend(_factors(a) if isinstance(a, Mul) else [a])
    return out


def _side_candidates(side, var):
    """Yield (rule, buggy_side, focus_node, correct_value) for subtrees of one side."""
    for node in preorder_traversal(side):
        if isinstance(node, Mul):
            fs = _factors(node)
            adds = [f for f in fs if isinstance(f, Add)]
            if len(adds) == 1:
                add = adds[0]
                k = Mul(*[f for f in fs if f is not add]).doit()
                terms = [t.doit() for t in Add.make_args(add)]
                if len(terms) >= 2 and k != 1:
                    correct = (k * add.doit()).expand()
                    if k.is_number and k.is_negative:
                        bug = k * terms[0] - k * Add(*terms[1:])
                        yield "NEG_DIST_FIRST_ONLY", side.xreplace({node: bug}), node, correct
                    for j in range(len(terms)):
                        bug = k * terms[j] + Add(*(terms[:j] + terms[j + 1 :]))
                        yield "DIST_FIRST_ONLY", side.xreplace({node: bug}), node, correct
        if isinstance(node, Pow) and node.exp == 2 and isinstance(node.base, Add):
            terms = [t.doit() for t in Add.make_args(node.base)]
            correct = node.doit().expand()
            for bug in {Add(*[t**2 for t in terms]), Add(*[sign(t.as_coeff_Mul()[0]) * t**2 for t in terms])}:
                yield "SQUARE_OF_SUM", side.xreplace({node: bug}), node, correct


def _term_merges(side, var):
    terms = list(Add.make_args(side.doit()))
    for i in range(len(terms)):
        for j in range(i + 1, len(terms)):
            ci, di = terms[i].as_coeff_exponent(var)
            cj, dj = terms[j].as_coeff_exponent(var)
            if di == dj or not (ci.is_number and cj.is_number):
                continue
            rest = Add(*(terms[:i] + terms[i + 1 : j] + terms[j + 1 :]))
            for d in {max(di, dj), min(di, dj)}:
                if d != 0:
                    yield rest + (ci + cj) * var**d


def _equation_candidates(pl: ParsedLine):
    var = pl.var
    for ci, (l_raw, r_raw) in enumerate(pl.raw):

        def with_clause(lhs, rhs, ci=ci):
            return [(lhs, rhs) if i == ci else c for i, c in enumerate(pl.raw)]

        for side_i, side in enumerate((l_raw, r_raw)):
            for rule, bug, node, corr in _side_candidates(side, var):
                new = (bug, r_raw) if side_i == 0 else (l_raw, bug)
                yield rule, with_clause(*new), node, corr
        lhs, rhs = l_raw.doit(), r_raw.doit()
        # Squaring both sides of a sqrt equation, squaring the other side term by term.
        for s, o, flip in ((lhs, rhs, False), (rhs, lhs, True)):
            if s.has(Pow) and any(isinstance(n, Pow) and n.exp == Integer(1) / 2 for n in preorder_traversal(s)):
                terms = Add.make_args(o)
                if len(terms) >= 2:
                    for bug in {Add(*[t**2 for t in terms]), Add(*[sign(t.as_coeff_Mul()[0]) * t**2 for t in terms])}:
                        sq = (s**2).expand()
                        yield "SQUARE_OF_SUM", with_clause(*((bug, sq) if flip else (sq, bug))), o, (o**2).expand()
        for t in Add.make_args(lhs):
            if len(Add.make_args(lhs)) > 1:
                yield "MOVE_NO_SIGN_FLIP", with_clause(lhs - t, rhs + t), t, None
        for t in Add.make_args(rhs):
            if len(Add.make_args(rhs)) > 1:
                yield "MOVE_NO_SIGN_FLIP", with_clause(lhs + t, rhs - t), t, None
        ks = set()  # students divide by the coefficient of the variable
        for e in (lhs, rhs):
            for t in Add.make_args(e):
                c, rest = t.as_coeff_Mul()
                if var in rest.free_symbols and c.is_Integer and 2 <= abs(c) <= 12:
                    ks.add(abs(c))
        for k in ks:
            for s_i, (s, o) in enumerate(((lhs, rhs), (rhs, lhs))):
                terms = Add.make_args(s)
                if len(terms) < 2:
                    continue
                for j, t in enumerate(terms):
                    bug = t / k + Add(*(terms[:j] + terms[j + 1 :]))
                    pair = (bug, o / k) if s_i == 0 else (o / k, bug)
                    yield "DIVIDE_ONE_TERM", with_clause(*pair), s, None
        for s_i, s in enumerate((lhs, rhs)):
            for merged in _term_merges(s, var):
                yield "COMBINE_UNLIKE", with_clause(*((merged, rhs) if s_i == 0 else (lhs, merged))), s, None
        for s, o in ((lhs, rhs), (rhs, lhs)):
            c, rest = s.as_coeff_Mul()
            if rest == var and c.is_number and c not in (0, 1):
                yield "TRANSPOSE_MULT_AS_ADD", with_clause(var, o - c), s, None


def _expression_candidates(pl: ParsedLine):
    yield from _side_candidates(pl.raw[0], pl.var)
    for merged in _term_merges(pl.raw[0], pl.var):
        yield "COMBINE_UNLIKE", merged, pl.raw[0], None


PRIORITY = [
    "NEG_DIST_FIRST_ONLY",
    "SQUARE_OF_SUM",
    "MOVE_NO_SIGN_FLIP",
    "COMBINE_UNLIKE",
    "DIST_FIRST_ONLY",
    "DIVIDE_ONE_TERM",
    "TRANSPOSE_MULT_AS_ADD",
]


def _match_rewrite(prev: ParsedLine, curr: ParsedLine) -> Diagnosis | None:
    gen = _equation_candidates(prev) if prev.kind == "equation" else _expression_candidates(prev)
    cands = sorted(islice(gen, MAX_CANDIDATES), key=lambda c: PRIORITY.index(c[0]))
    target = solution_set(curr) if curr.kind == "equation" else None
    for rule, cand, node, corr in cands:
        try:
            if curr.kind == "equation":
                ok = compare_sets(solution_set(ParsedLine("equation", prev.var, cand, "")), target) == "equal"
            else:
                ok = expr_equivalent(cand.doit(), curr.expr, prev.var) is True
        except (TypeError, ValueError, NotImplementedError, ZeroDivisionError):
            continue
        if ok:
            return Diagnosis(rule, "verified", to_ascii(node), correct_fragment=corr)
    return None


def _match_relation(prev: ParsedLine, curr: ParsedLine) -> Diagnosis | None:
    if prev.kind != "equation" or curr.kind != "equation":
        return None
    sa, sb = solution_set(prev), solution_set(curr)
    if compare_sets(sa, sb) != "lost" or not sa.is_FiniteSet:
        return None
    missing = [m for m in sa if not any((m - k).simplify() == 0 for k in sb)]
    if missing and all(m != 0 and any((m + k).simplify() == 0 for k in sb) for m in missing):
        return Diagnosis("SQRT_LOST_NEG_ROOT", "verified")
    lhs, rhs = prev.eqs[0]
    for sq, other in ((lhs, rhs), (rhs, lhs)):  # (B)^2 = c  ->  only one of B = ±sqrt(c) kept
        if isinstance(sq, Pow) and sq.exp == 2 and prev.var not in other.free_symbols:
            branches = [solveset(sq.base - s_ * sqrt(other), prev.var, S.Reals) for s_ in (1, -1)]
            if any(compare_sets(br, sb) == "equal" for br in branches):
                return Diagnosis("SQRT_LOST_NEG_ROOT", "verified", to_ascii(sq))
    polys = lhs != 0 and rhs != 0 and lhs.is_polynomial(prev.var) and rhs.is_polynomial(prev.var)
    shared = gcd(lhs, rhs) if polys else 1  # gcd(p, 0) = p would fake a shared factor
    if 0 in missing or (shared != 1 and prev.var in shared.free_symbols):
        return Diagnosis("DIV_BY_VARIABLE", "verified")
    return None


def _match_slip(prev: ParsedLine, curr: ParsedLine) -> Diagnosis | None:
    c = Symbol("c_slip")
    ints = sorted({abs(int(a)) for side in _sides(curr) for a in side.atoms(Integer) if a != 0})[:8]
    for v in ints:
        swapped = [tuple(s.xreplace({Integer(v): c, Integer(-v): -c}) for s in cl) for cl in _clauses(curr)]
        if curr.kind == "equation":
            sa = solution_set(prev)
            if not sa.is_FiniteSet or len(sa) == 0:
                return None
            r = next(iter(sa))
            lhs, rhs = swapped[0]
            sols = solve((lhs - rhs).doit().subs(curr.var, r), c)
        else:
            probe = Integer(3)
            sols = solve((swapped[0][0] - prev.expr).doit().subs(curr.var, probe), c)
        for s in sols:
            if not (s.is_Integer and s != v and _slip_like(int(s), v)):
                continue
            fixed = [tuple(x.subs(c, s) for x in cl) for cl in swapped]
            if curr.kind == "equation":
                ok = compare_sets(solution_set(prev), solution_set(ParsedLine("equation", curr.var, fixed, ""))) == "equal"
            else:
                ok = expr_equivalent(fixed[0][0].doit(), prev.expr, curr.var) is True
            if ok:
                return Diagnosis("ARITH_SLIP", "verified")
    return None


def _slip_like(right: int, written: int) -> bool:
    """A slip is a near miss: sign flip, off by one or two, or one digit wrong in a multi-digit number."""
    if right == -written or abs(right - written) <= 2:
        return True
    a, b = str(abs(right)), str(abs(written))
    return len(a) == len(b) > 1 and sum(x != y for x, y in zip(a, b, strict=True)) == 1


def _clauses(pl: ParsedLine):
    return pl.raw if pl.kind == "equation" else [(pl.raw[0],)]


def _sides(pl: ParsedLine):
    for cl in _clauses(pl):
        yield from cl


def diagnose(prev: ParsedLine, curr: ParsedLine) -> Diagnosis | None:
    """Deterministic diagnosis of an erroneous step, or None if no rule reproduces it."""
    if prev.kind != curr.kind:
        return None

    def _all():
        return _match_relation(prev, curr) or _match_rewrite(prev, curr) or _match_slip(prev, curr)

    return _run(_all)
