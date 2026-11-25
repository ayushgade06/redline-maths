"""Safe parser: Redline-grammar ASCII -> SymPy.

This is the security boundary. SymPy's parse_expr() calls eval() internally, so
nothing reaches it until the string has passed a strict character whitelist and
complexity caps. Only digits, one single-letter variable, + - * / ^ ( ) = , . and
the words `sqrt` / `or` survive.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sympy import Add, Float, Integer, Mul, Pow, Rational, Symbol, nan, sqrt, zoo
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

MAX_LEN = 120
MAX_INT = 10**6
MAX_EXP = 10
MAX_DEPTH = 6

_TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)
_GLOBALS = {
    "Integer": Integer,
    "Rational": Rational,
    "Float": Float,
    "Symbol": Symbol,
    "sqrt": sqrt,
    "Add": Add,
    "Mul": Mul,
    "Pow": Pow,
    "__builtins__": {},
}
_ALLOWED = re.compile(r"^[0-9a-z+\-*/^().=, ]+$")
_WORDS = re.compile(r"sqrt|\bor\b")


class ParseError(ValueError):
    """Line can't be parsed. `reason` is safe to show to the learner."""

    def __init__(self, reason: str, code: str = "unreadable"):
        super().__init__(reason)
        self.reason = reason
        self.code = code


@dataclass
class ParsedLine:
    kind: str  # "equation" | "expression"
    var: Symbol
    raw: list  # unevaluated: [(lhs, rhs), ...] for equations, [expr] for expressions
    text: str

    @property
    def eqs(self):
        """Evaluated (lhs, rhs) clauses. A line like `x=3 or x=-3` has two."""
        return [(lhs.doit(), rhs.doit()) for lhs, rhs in self.raw]

    @property
    def expr(self):
        return self.raw[0].doit()


def normalize(text: str) -> str:
    s = text.strip().lower()
    for a, b in {
        "−": "-",
        "–": "-",
        "—": "-",
        "×": "*",
        "·": "*",
        "÷": "/",
        "**": "^",
        "²": "^2",
        "³": "^3",
        "√": "sqrt",
        " ": " ",
        " ": " ",
    }.items():
        s = s.replace(a, b)
    s = re.sub(r"sqrt\s*(\d+|[a-z](?![a-z]))", r"sqrt(\1)", s)  # √16 -> sqrt(16)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _letters(s: str) -> set[str]:
    return set(re.findall(r"[a-z]", _WORDS.sub(" ", s)))


def detect_variable(lines: list[str]) -> str:
    """The one letter used across all lines. Raises ParseError(code=unsupported_scope) on >1."""
    letters: set[str] = set()
    for line in lines:
        letters |= _letters(normalize(line))
    if len(letters) > 1:
        raise ParseError(
            f"Redline checks single-variable algebra; found {', '.join(sorted(letters))}.",
            "unsupported_scope",
        )
    return letters.pop() if letters else "x"


def _expand_pm(s: str) -> str:
    """`x = ±3` / `x = +-3` -> `x = 3 or x = -3`."""
    s = s.replace("±", "+-")
    m = re.fullmatch(r"(.+?)=\s*\+-\s*(.+)", s)
    if m:
        return f"{m[1]}= {m[2]} or {m[1]}= -({m[2]})"
    return s


def _check_caps(s: str) -> None:
    if len(s) > MAX_LEN:
        raise ParseError(f"Line is too long (max {MAX_LEN} characters).")
    if not _ALLOWED.match(s):
        bad = sorted(set(re.sub(r"[0-9a-z+\-*/^().=, ]", "", s)))
        raise ParseError(f"Unsupported character(s): {' '.join(bad)}")
    for num in re.findall(r"\d+", s):
        if len(num) > 7 or int(num) > MAX_INT:
            raise ParseError("Numbers above 1,000,000 aren't supported.")
    depth = 0
    for ch in s:
        depth += ch == "("
        depth -= ch == ")"
        if depth > MAX_DEPTH:
            raise ParseError("Too many nested brackets.")
        if depth < 0:
            raise ParseError("Brackets don't match.")
    if depth != 0:
        raise ParseError("Brackets don't match.")


def _decimals_to_fractions(s: str) -> str:
    return re.sub(r"(\d+)\.(\d+)", lambda m: f"({int(m[1] + m[2])}/{10 ** len(m[2])})", s)


def _guard_tree(e) -> None:
    for node in (n for n in _walk(e) if isinstance(n, Pow)):
        exp = node.exp
        if any(isinstance(n, Pow) for n in _walk(exp)) or exp.free_symbols:
            raise ParseError("Exponents must be plain numbers (like x^2).")
        val = exp.doit()
        if not val.is_Rational or abs(val) > MAX_EXP:
            raise ParseError(f"Exponents must be whole numbers up to {MAX_EXP}.")


def _walk(e):
    yield e
    for a in e.args:
        yield from _walk(a)


def _parse_side(side: str, sym: Symbol):
    side = side.strip()
    if not side:
        raise ParseError("Something is missing on one side of '='.")
    # A leading unary minus on a bracket would be auto-distributed by SymPy even with
    # evaluate=False; prefixing 0 keeps -(a+b) intact so misconceptions stay visible.
    side = re.sub(r"(^|\()\s*-", r"\g<1>0-", side)
    try:
        e = parse_expr(
            side,
            local_dict={sym.name: sym},
            global_dict=_GLOBALS,
            transformations=_TRANSFORMS,
            evaluate=False,
        )
    except (SyntaxError, TypeError, ValueError, AttributeError, ZeroDivisionError, TokenError):
        raise ParseError("Couldn't read this line as math.") from None
    if e.free_symbols - {sym}:
        raise ParseError("Unexpected symbol in this line.")
    _guard_tree(e)
    if e.doit().has(zoo, nan):
        raise ParseError("This line divides by zero.")
    return e


try:  # tokenize errors surface as TokenError on unbalanced input
    from tokenize import TokenError
except ImportError:  # pragma: no cover
    TokenError = SyntaxError  # type: ignore


def parse_line(text: str, var: str | None = None) -> ParsedLine:
    s = _expand_pm(normalize(text))
    _check_caps(s)
    if "_" in s:
        raise ParseError("Unsupported character(s): _")
    var = var or detect_variable([s])
    if _letters(s) - {var}:
        raise ParseError("Only one variable is supported.", "unsupported_scope")
    if re.search(r"[a-z]{2,}", _WORDS.sub(" ", s)):
        raise ParseError("Only the function sqrt() is supported.")
    sym = Symbol(var, real=True)
    s = re.sub(r"\b0+(\d)", r"\1", _decimals_to_fractions(s))  # `007` is a Python SyntaxError
    clauses = [c.strip() for c in re.split(r"\bor\b|,", s) if c.strip()]
    if not clauses:
        raise ParseError("This line is empty.")
    # `x = 3, -3` -> `x = 3 or x = -3`
    head = clauses[0].split("=")
    if len(head) == 2 and head[0].strip() == var:
        clauses = [c if "=" in c else f"{var} = {c}" for c in clauses]
    raw = []
    kinds = set()
    for c in clauses:
        parts = c.split("=")
        if len(parts) > 2:
            raise ParseError("A step can contain only one '='.")
        if len(parts) == 2:
            kinds.add("equation")
            raw.append((_parse_side(parts[0], sym), _parse_side(parts[1], sym)))
        else:
            kinds.add("expression")
            raw.append(_parse_side(parts[0], sym))
    if len(kinds) > 1 or (kinds == {"expression"} and len(raw) > 1):
        raise ParseError("Mixes equations and expressions in one line.")
    return ParsedLine(kinds.pop(), sym, raw, text)
