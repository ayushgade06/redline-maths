"""Targeted practice and parallel worked examples, one template per misconception.

Every template builds a problem with whole-number answers. The answer is never sent to
the client: /practice/check rebuilds the problem from its params and solves it.
"""

from __future__ import annotations

import random
import re

from .safe_parse import ParsedLine, parse_line
from .verifier import compare_sets, solution_set


def _nz(rng, lo, hi, avoid=()):
    while True:
        v = rng.randint(lo, hi)
        if v != 0 and v not in avoid:
            return v


# Each builder: rng -> (params, x0). `problem(params)` -> ASCII. `steps(params)` -> (wrong, right).
TEMPLATES = {
    "NEG_DIST_FIRST_ONLY": {
        "params": lambda r: {"a": r.randint(2, 12), "b": (b := r.randint(2, 6)), "c": _nz(r, 1, 9, (b,)), "x0": _nz(r, -6, 9)},
        "problem": lambda p: f"{p['a']} - {p['b']}(x - {p['c']}) = {p['a'] - p['b'] * (p['x0'] - p['c'])}",
        "steps": lambda p: (f"{p['a']} - {p['b']}x - {p['b'] * p['c']}", f"{p['a']} - {p['b']}x + {p['b'] * p['c']}"),
        "note": "the −{b} multiplies the −{c} too, and (−{b})·(−{c}) = +{bc}",
    },
    "DIST_FIRST_ONLY": {
        "params": lambda r: {"b": r.randint(2, 7), "c": r.randint(1, 9), "x0": _nz(r, -5, 9)},
        "problem": lambda p: f"{p['b']}(x + {p['c']}) = {p['b'] * (p['x0'] + p['c'])}",
        "steps": lambda p: (f"{p['b']}x + {p['c']}", f"{p['b']}x + {p['b'] * p['c']}"),
        "note": "the {b} multiplies both x and {c}",
    },
    "MOVE_NO_SIGN_FLIP": {
        "params": lambda r: {"a": r.randint(2, 9), "b": r.randint(2, 15), "x0": _nz(r, -6, 9)},
        "problem": lambda p: f"{p['a']}x + {p['b']} = {p['a'] * p['x0'] + p['b']}",
        "steps": lambda p: (
            f"{p['a']}x = {p['a'] * p['x0'] + p['b']} + {p['b']}",
            f"{p['a']}x = {p['a'] * p['x0'] + p['b']} - {p['b']}",
        ),
        "note": "subtracting {b} from both sides removes +{b} on the left",
    },
    "DIVIDE_ONE_TERM": {
        "params": lambda r: {"k": r.randint(2, 6), "m": r.randint(1, 8), "x0": _nz(r, -5, 9)},
        "problem": lambda p: f"{p['k']}x + {p['k'] * p['m']} = {p['k'] * (p['x0'] + p['m'])}",
        "steps": lambda p: (f"x + {p['k'] * p['m']} = {p['x0'] + p['m']}", f"x + {p['m']} = {p['x0'] + p['m']}"),
        "note": "dividing the left side by {k} divides both {k}x and {km}",
    },
    "SQUARE_OF_SUM": {
        "params": lambda r: {"a": r.randint(1, 7), "c": r.randint(2, 9)},
        "problem": lambda p: f"(x + {p['a']})^2 = {p['c'] ** 2}",
        "steps": lambda p: (f"x^2 + {p['a'] ** 2} = {p['c'] ** 2}", f"x^2 + {2 * p['a']}x + {p['a'] ** 2} = {p['c'] ** 2}"),
        "note": "(x + {a})² = (x + {a})(x + {a}) has a middle term {a2}x",
    },
    "COMBINE_UNLIKE": {
        "params": lambda r: {"a": r.randint(2, 9), "b": r.randint(2, 9), "x0": _nz(r, -5, 9)},
        "problem": lambda p: f"{p['a']}x + {p['b']} = {p['a'] * p['x0'] + p['b']}",
        "steps": lambda p: (f"{p['a'] + p['b']}x = {p['a'] * p['x0'] + p['b']}", f"{p['a']}x = {p['a'] * p['x0']}"),
        "note": "{a}x and {b} are unlike terms, so they can't be added",
    },
    "SQRT_LOST_NEG_ROOT": {
        "params": lambda r: {"c": r.randint(2, 12)},
        "problem": lambda p: f"x^2 = {p['c'] ** 2}",
        "steps": lambda p: (f"x = {p['c']}", f"x = {p['c']} or x = -{p['c']}"),
        "note": "both {c} and −{c} square to {c2}",
    },
    "DIV_BY_VARIABLE": {
        "params": lambda r: {"k": r.randint(2, 9)},
        "problem": lambda p: f"x^2 = {p['k']}x",
        "steps": lambda p: (f"x = {p['k']}", f"x(x - {p['k']}) = 0"),
        "note": "factor instead of dividing by x, so x = 0 isn't lost",
    },
    "ARITH_SLIP": {
        "params": lambda r: {"a": r.randint(2, 9), "b": r.randint(2, 15), "x0": _nz(r, -6, 9)},
        "problem": lambda p: f"{p['a']}x - {p['b']} = {p['a'] * p['x0'] - p['b']}",
        "steps": lambda p: (f"{p['a']}x = {p['a'] * p['x0'] + 1}", f"{p['a']}x = {p['a'] * p['x0']}"),
        "note": "{d} + {b} has to be recomputed carefully",
    },
    "TRANSPOSE_MULT_AS_ADD": {
        "params": lambda r: {"a": r.randint(2, 9), "x0": _nz(r, -6, 12)},
        "problem": lambda p: f"{p['a']}x = {p['a'] * p['x0']}",
        "steps": lambda p: (f"x = {p['a'] * p['x0']} - {p['a']}", f"x = {p['a'] * p['x0']}/{p['a']}"),
        "note": "x is multiplied by {a}, so divide by {a}",
    },
}


def _problem_line(mid: str, params: dict) -> ParsedLine:
    return parse_line(TEMPLATES[mid]["problem"](params), "x")


def _roots(mid: str, params: dict) -> set:
    return set(solution_set(_problem_line(mid, params)))


def generate(mid: str, count: int, avoid_roots=(), seed: int | None = None) -> list[dict]:
    rng = random.Random(seed)
    avoid = set(avoid_roots)
    out = []
    while len(out) < count:
        p = TEMPLATES[mid]["params"](rng)
        if _roots(mid, p) & avoid:
            continue
        prob = TEMPLATES[mid]["problem"](p)
        if any(o["prompt_ascii"] == prob for o in out):
            continue
        out.append({"template_id": mid, "params": {k: v for k, v in p.items() if k != "x0"}, "prompt_ascii": prob})
    return out


def check(prompt_ascii: str, answer_ascii: str) -> bool:
    """True when the answer's solution set equals the problem's."""
    problem = parse_line(prompt_ascii, "x")
    ans = answer_ascii.strip()
    if "=" not in ans:
        ans = " or ".join(f"x = {a}" for a in ans.replace(" or ", ",").split(",") if a.strip())
    return compare_sets(solution_set(problem), solution_set(parse_line(ans, "x"))) == "equal"


def _ints(text: str) -> set[int]:
    return {int(n) for n in re.findall(r"\d+", text) if int(n) >= 2}


def parallel_example(mid: str, avoid_roots=(), avoid_text: str = "", seed: int | None = None) -> dict:
    """A worked example of the same mistake on a *different* problem: different answer
    and, as far as possible, none of the student's numbers."""
    rng = random.Random(seed)
    avoid, theirs = set(avoid_roots), _ints(avoid_text)
    t = TEMPLATES[mid]
    best, best_overlap = None, None
    for _ in range(80):
        p = t["params"](rng)
        if _roots(mid, p) & avoid:
            continue
        overlap = len(_ints(t["problem"](p)) & theirs)
        if best is None or overlap < best_overlap:
            best, best_overlap = p, overlap
        if overlap == 0:
            break
    p = best
    wrong, right = t["steps"](p)
    fill = dict(p)
    fill.update(
        bc=p.get("b", 0) * p.get("c", 0),
        km=p.get("k", 0) * p.get("m", 0),
        a2=2 * p.get("a", 0),
        c2=p.get("c", 0) ** 2,
        d=p.get("a", 0) * p.get("x0", 0) - p.get("b", 0),
    )
    return {"problem": t["problem"](p), "wrong": wrong, "right": right, "note": t["note"].format(**fill)}
