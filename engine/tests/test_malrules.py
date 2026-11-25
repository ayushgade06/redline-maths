import json
from pathlib import Path

import pytest

import main
from redline.catalog import CATALOG
from redline.malrules import diagnose
from redline.safe_parse import parse_line
from redline.verifier import verify_lines

ERRORS = json.loads((Path(__file__).parent / "data" / "errors.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", ERRORS, ids=lambda c: f"{c['misconception']}: {' | '.join(c['lines'][:2])}")
def test_diagnosis_matches_label(case):
    d, offline = main._diagnosis(verify_lines(None, case["lines"]))
    assert d is not None and d.id == case["misconception"]
    assert d.evidence == "verified"


def test_every_rule_has_three_positive_cases():
    counts = {k: 0 for k in CATALOG}
    for c in ERRORS:
        counts[c["misconception"]] += 1
    missing = {k: n for k, n in counts.items() if n < 3 and k != "EXTRANEOUS_ROOT"}
    assert not missing


NEGATIVES = [
    ("2x + 3 = 11", "x = 100"),
    ("x + 1 = 5", "x = -40"),
    ("3x + 4 = 19", "x + 4 = 57"),
    ("5 - 2(x - 3) = 1", "x = 1000"),
    ("x^2 = 9", "x = 17"),
    ("2(x + 1) = 8", "7x = 3"),
]


@pytest.mark.parametrize("prev,curr", NEGATIVES)
def test_unrelated_errors_do_not_match_spuriously(prev, curr):
    assert diagnose(parse_line(prev), parse_line(curr)) is None


def test_focus_points_at_the_students_bracket():
    d = diagnose(parse_line("5 - 2(x - 3) = 1"), parse_line("5 - 2x - 6 = 1"))
    assert d.focus == "-2(x - 3)"
    assert str(d.correct_fragment) == "6 - 2*x"
