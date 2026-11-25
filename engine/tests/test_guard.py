import pytest
from sympy import FiniteSet, Integer, Symbol

from redline.catalog import CATALOG
from redline.guard import check
from redline.practice import TEMPLATES, parallel_example
from redline.verifier import verify_lines

x = Symbol("x", real=True)
# Problem: 5 - 2(x-3) = 1  (answer x = 5); fragment -2(x-3) should become -2x + 6.
CORRECT = FiniteSet(Integer(5))
FRAGMENT = -2 * x + 6

LEAKS = [
    "So x = 5.",
    "The answer is 5",
    "x is 5",
    "You should get `-2x = -10`",
    "It should be -2x + 6, not -2x - 6.",
    "Then 11 - 2x = 1 gives the result",
    "x equals 5",
    "The solution is 5.",
    "which gives -2x=-10",
    "Write 5 - 2x + 6 = 1 instead",
    "x=5",
    "the value of x comes out to 5",
]

SAFE = [
    "Look at line 2. Check the sign of each term from -2(x - 3).",
    "A negative factor multiplies every term inside the bracket.",
    "Example: in 12 - 4(x - 7) = 16, -4 times -7 is +28, so 12 - 4x + 28 = 16.",
    "Check line 3 again.",
    "Count the terms in the bracket: there are 2.",
    "Your line 2 has 5 - 2x - 6 = 1; revisit the -6.",
    "Think about what (-2)(-3) equals.",
    "Re-read step 2, the second term.",
    "Multiply each term: x and 3.",
    "In 7 - 3(x - 2), the -3 hits both terms.",
    "-k(a - b) = -ka + kb, because a negative times a negative is positive.",
]


@pytest.mark.parametrize("text", LEAKS)
def test_leaks_are_caught(text):
    assert check(text, "x", CORRECT, FRAGMENT) is False


@pytest.mark.parametrize("text", SAFE)
def test_safe_hints_pass(text):
    assert check(text, "x", CORRECT, FRAGMENT) is True


@pytest.mark.parametrize("mid", list(CATALOG))
@pytest.mark.parametrize("level", [1, 2])
def test_template_hints_never_leak(mid, level):
    text = CATALOG[mid]["hints"][level].format(line=2, focus="`-2(x - 3)`")
    assert check(text, "x", CORRECT, FRAGMENT)


@pytest.mark.parametrize("mid", list(TEMPLATES))
def test_parallel_example_uses_different_numbers_and_answer(mid):
    lines = ["5 - 2(x - 3) = 1", "5 - 2x - 6 = 1"]
    roots = set(verify_lines(None, lines).correct_set)
    for seed in range(3):
        ex = parallel_example(mid, roots, " ".join(lines), seed=seed)
        assert set(verify_lines(None, [ex["problem"]]).correct_set or []) & roots == set()
        text = f"In `{ex['problem']}`, `{ex['wrong']}` is wrong; `{ex['right']}` is right, because {ex['note']}."
        assert check(text, "x", CORRECT, FRAGMENT)
