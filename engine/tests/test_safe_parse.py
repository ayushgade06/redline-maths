import pytest

from redline.safe_parse import ParseError, detect_variable, parse_line

ACCEPT = [
    ("2(x-3)=10", "equation"),
    ("-2(x+1) + 4 = 3x", "equation"),
    ("x/3 + 1/2 = 5/6", "equation"),
    ("(x+3)^2 = 16", "equation"),
    ("sqrt(x+1)=3", "equation"),
    ("x = ±3", "equation"),
    ("x = 3 or x = -3", "equation"),
    ("x = 3, -3", "equation"),
    ("0.5x = 2", "equation"),
    ("−(x−4) = 2", "equation"),
    ("2x² = 8", "equation"),
    ("3 × 4 ÷ 2 = x", "equation"),
    ("x**2 = 4", "equation"),
    ("3(x+2) - 2(x-1)", "expression"),
    ("x(x - 3) = 0", "equation"),
    ("√16 = x", "equation"),
    ("007x = 14", "equation"),
    ("X + 1 = 2", "equation"),
]

REJECT = [
    "__import__('os')",
    "x**99999",
    "lambda",
    "2^2^2^2^2",
    "x" * 200,
    "a=b=c",
    "x = 1 = 2",
    "x^x = 4",
    "sin(x) = 1",
    "(((((((x))))))) = 1",
    "1234567x = 1",
    "x =",
    "2(x = 3",
    "x^(1/3) = 2",
    "1/0 = x",
    "exec('x')",
    "x; import os",
    "x = {1}",
]


@pytest.mark.parametrize("text,kind", ACCEPT)
def test_accepts(text, kind):
    assert parse_line(text).kind == kind


@pytest.mark.parametrize("text", REJECT)
def test_rejects(text):
    with pytest.raises(ParseError):
        parse_line(text)


def test_multi_variable_is_unsupported_scope():
    with pytest.raises(ParseError) as e:
        detect_variable(["y + x = 2"])
    assert e.value.code == "unsupported_scope"


def test_keeps_structure_of_negative_bracket():
    # A leading -( ) must stay unexpanded so misconceptions remain detectable.
    from redline.malrules import to_ascii

    lhs, _ = parse_line("-(x - 4) = 2").raw[0]
    assert to_ascii(lhs) == "-(x - 4)"


def test_plus_minus_expands_to_two_clauses():
    assert len(parse_line("x = ±3").eqs) == 2


def test_decimal_becomes_exact_fraction():
    ((lhs, _),) = parse_line("0.25x = 1").eqs
    assert str(lhs) == "x/4"
