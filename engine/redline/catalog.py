"""Misconception catalog: names, explanations and answer-free template hints.

Template placeholders: {line} = 1-based line number of the wrong step, {prev} = the
line before it, {focus} = the part of the previous line the rule acted on (the
student's own writing, so it is never a leak).
"""

CATALOG: dict[str, dict] = {
    "NEG_DIST_FIRST_ONLY": {
        "name": "Negative distributed to only the first term",
        "description": "When a negative number multiplies a bracket, the sign changes every term inside — not just the first.",
        "concept": "A minus in front of a bracket multiplies each term: −k(a + b) = −ka − kb, and −k(a − b) = −ka + kb.",
        "hints": {
            1: "Look at how {focus} was expanded on the way to line {line}. Check the sign of each term that came out of the bracket.",
            2: "A negative factor in front of a bracket multiplies every term inside it, so every term's sign is affected — not only the first one.",
        },
    },
    "DIST_FIRST_ONLY": {
        "name": "Multiplied only the first term in the bracket",
        "description": "The number outside a bracket has to multiply every term inside it.",
        "concept": "Distribution: k(a + b) = ka + kb. Every term inside the bracket gets multiplied by k.",
        "hints": {
            1: "In line {line}, look again at how {focus} was expanded. Did every term inside the bracket get multiplied?",
            2: "The factor outside a bracket multiplies each term inside, one by one. Count the terms inside and make sure each one was multiplied.",
        },
    },
    "MOVE_NO_SIGN_FLIP": {
        "name": "Moved a term across '=' without changing its sign",
        "description": "Moving a term to the other side really means subtracting (or adding) it on both sides, which flips its sign.",
        "concept": "If a term is added on one side, you remove it by subtracting it from both sides — so it appears with the opposite sign on the other side.",
        "hints": {
            1: "Compare line {line} with the line before it. Which term moved to the other side of '=', and what sign does it have now?",
            2: "'Moving' a term is shorthand for doing the same operation to both sides. Adding becomes subtracting on the other side, and subtracting becomes adding.",
        },
    },
    "DIVIDE_ONE_TERM": {
        "name": "Divided only one term by a number",
        "description": "When you divide one side of an equation, every term on that side must be divided.",
        "concept": "(a + b) / k = a/k + b/k. Dividing a side means dividing each term on it.",
        "hints": {
            1: "In line {line} something was divided. Check that every term on each side was divided by the same number.",
            2: "Dividing a whole side by a number divides each term on that side. If one term was left alone, the two sides are no longer balanced.",
        },
    },
    "SQUARE_OF_SUM": {
        "name": "Squared a sum term by term",
        "description": "(a + b)² is not a² + b². Squaring a sum produces a middle term 2ab.",
        "concept": "(a + b)² = (a + b)(a + b) = a² + 2ab + b². Squaring each term separately drops the 2ab.",
        "hints": {
            1: "Look at a squared bracket on the way to line {line}. Write the square out as the bracket multiplied by itself.",
            2: "Squaring a sum means multiplying the bracket by itself. Expanding (a + b)(a + b) gives four products, two of which combine into a middle term.",
        },
    },
    "COMBINE_UNLIKE": {
        "name": "Combined unlike terms",
        "description": "Only like terms (same variable, same power) can be added together. 3x + 2 can't become 5x.",
        "concept": "Like terms share exactly the same variable part: 3x and 2x combine to 5x, but 3x and 2 (or x² and x) stay separate.",
        "hints": {
            1: "In line {line}, two terms were merged. Check that they have exactly the same variable part.",
            2: "You can only add coefficients when the variable parts match exactly. A number and an x-term, or an x² and an x, have to stay as separate terms.",
        },
    },
    "SQRT_LOST_NEG_ROOT": {
        "name": "Forgot the ± when taking a square root",
        "description": "Taking the square root of both sides gives two possibilities: positive and negative.",
        "concept": "If y² = 9, then y = 3 or y = −3, because both square to 9. Square-rooting an equation needs ±.",
        "hints": {
            1: "Line {line} took a square root. How many numbers square to give the value on the other side?",
            2: "Both a positive and a negative number have the same square. When you undo a square, keep both possibilities with ±.",
        },
    },
    "DIV_BY_VARIABLE": {
        "name": "Divided by an expression that could be zero",
        "description": "Dividing both sides by the variable (or a bracket containing it) throws away the solution that makes it zero.",
        "concept": "Instead of dividing by x, move everything to one side and factor: x² = kx → x² − kx = 0 → x(x − k) = 0.",
        "hints": {
            1: "In line {line} both sides were divided by something containing the variable. What if that thing equals zero?",
            2: "You can't divide by something that might be zero. Bring every term to one side and factor instead, so no solution gets lost.",
        },
    },
    "ARITH_SLIP": {
        "name": "Arithmetic slip",
        "description": "The method is fine, but one number came out wrong.",
        "concept": "The step uses the right idea; one calculation (an addition, subtraction, multiplication or division) went wrong.",
        "hints": {
            1: "The method in line {line} is right, but recheck the arithmetic in that step, one number at a time.",
            2: "Redo just the calculation from the previous line on scrap paper, slowly, and compare each number with what you wrote.",
        },
    },
    "TRANSPOSE_MULT_AS_ADD": {
        "name": "Undid multiplication by subtracting",
        "description": "To undo 'times k' you divide by k; subtracting k undoes addition, not multiplication.",
        "concept": "Each operation has an inverse: + undoes −, and ÷ undoes ×. In kx = c, x is multiplied by k, so divide both sides by k.",
        "hints": {
            1: "In line {line}, think about how the number next to the variable is attached to it. Is it added, or multiplied?",
            2: "A number written right next to a variable multiplies it. The inverse of multiplying is dividing, so that's the operation to use on both sides.",
        },
    },
}

CATALOG["EXTRANEOUS_ROOT"] = {
    "name": "Kept an extraneous solution",
    "description": "Squaring both sides (or clearing a denominator) can create values that don't solve the original equation. They have to be checked and rejected.",
    "concept": "After squaring or multiplying by an expression with the variable, substitute every candidate back into the ORIGINAL equation and discard the ones that fail.",
    "hints": {
        1: "Every step after the first one followed correctly, but check each value in line {line} by substituting it into the original equation.",
        2: "Squaring both sides can turn a false statement into a true one (−3 ≠ 3, but 9 = 9). That's why candidates from a squared equation must be checked in the original.",
    },
}

OTHER = {
    "name": "Unclassified error",
    "description": "This step changes the answer, but it doesn't match a known misconception pattern.",
    "concept": "Compare the two lines carefully, one operation at a time.",
    "hints": {
        1: "Line {line} doesn't follow from the line before it. Redo that single step carefully.",
        2: "Each step must keep the equation balanced: whatever you do to one side, do to the other side, to every term.",
    },
}


def entry(mid: str) -> dict:
    return CATALOG.get(mid, OTHER)
