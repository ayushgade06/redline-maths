import json
import time
from pathlib import Path

import pytest

from redline.verifier import verify_lines

DATA = Path(__file__).parent / "data"
CORRECT = json.loads((DATA / "correct.json").read_text(encoding="utf-8"))
ERRORS = json.loads((DATA / "errors.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CORRECT, ids=lambda c: c["lines"][0])
def test_no_false_alarms_on_correct_work(case):
    r = verify_lines(None, case["lines"])
    assert r.first_error_index is None, [x.status for x in r.lines]
    assert all(x.status in {"start", "valid"} for x in r.lines)
    if case["topic"] != "simplify":
        assert r.final_correct is True


@pytest.mark.parametrize("case", ERRORS, ids=lambda c: " | ".join(c["lines"][:2]))
def test_seeded_error_found_on_the_right_line(case):
    r = verify_lines(None, case["lines"])
    assert r.first_error_index == case["first_error"]
    assert r.lines[case["first_error"]].status == case["status"]
    assert r.final_correct in (False, None)


def test_lost_root_from_sqrt():
    assert verify_lines(None, ["x^2 = 9", "x = 3"]).lines[1].status == "lost_solution"


def test_dividing_by_x_loses_zero():
    assert verify_lines(None, ["x^2 = 2x", "x = 2"]).lines[1].status == "lost_solution"


def test_squaring_gains_extraneous_root():
    r = verify_lines(None, ["sqrt(x+1) = x - 1", "x + 1 = (x-1)^2"])
    assert r.lines[1].status == "gained_solution"
    assert r.first_error_index is None  # a warning, not an error, until the root is kept


def test_extraneous_root_kept_in_final_answer():
    r = verify_lines(None, ["sqrt(x+1) = x - 1", "x + 1 = x^2 - 2x + 1", "x^2 - 3x = 0", "x = 0 or x = 3"])
    assert r.first_error_index == 3 and r.lines[3].detail == "keeps_extraneous"


def test_unreadable_line_is_skipped_not_blamed():
    r = verify_lines(None, ["2x + 3 = 11", "2x = ???", "x = 4"])
    assert r.lines[1].status == "unreadable"
    assert r.lines[2].status == "valid"
    assert r.first_error_index is None


def test_problem_statement_drives_final_answer():
    r = verify_lines("Solve (x+3)^2 = 16", ["x + 3 = 4", "x = 1"])
    assert r.lines[0].status == "lost_solution"
    assert r.final_correct is False


def test_identity_is_valid():
    assert verify_lines(None, ["2x + 2 = 2(x + 1)", "2x + 2 = 2x + 2"]).lines[1].status == "valid"


def test_unfinished_work_has_no_verdict():
    assert verify_lines(None, ["2x + 3 = 11", "2x = 8"]).final_correct is None


def test_errors_after_the_first_follow_the_students_line():
    r = verify_lines(None, ["5 - 2(x-3) = 1", "5 - 2x - 6 = 1", "-2x - 1 = 1"])
    assert [x.status for x in r.lines] == ["start", "invalid", "valid"]


def test_expression_chain_error():
    r = verify_lines(None, ["3(x+2) - 2(x-1)", "3x + 6 - 2x - 2"])
    assert r.lines[1].status == "invalid"


def test_segment_break_between_kinds():
    assert verify_lines(None, ["2x + 3", "2x + 3 = 5"]).lines[1].status == "segment_break"


def test_scope_degree_cap():
    assert verify_lines(None, ["x^5 = 32", "x = 2"]).scope_ok is False


def test_verifier_is_fast():
    times = []
    for case in CORRECT + ERRORS:
        t = time.perf_counter()
        verify_lines(None, case["lines"])
        times.append((time.perf_counter() - t) / max(1, len(case["lines"]) - 1))
    times.sort()
    p95 = times[int(len(times) * 0.95) - 1]
    print(f"verifier p95 per transition: {p95 * 1000:.0f} ms")
    assert p95 < 0.3


def test_collapsing_to_an_identity_is_an_error():
    r = verify_lines(None, ["6 - (x + 2) = 3x", "3x = 3x"])
    assert r.lines[1].status == "invalid" and r.first_error_index == 1


def test_restating_the_problem_is_the_starting_line():
    r = verify_lines("Solve (x-2)^2 = 9", ["(x-2)^2 = 9", "x - 2 = 3"])
    assert [x.status for x in r.lines] == ["start", "lost_solution"]
