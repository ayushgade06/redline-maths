# Redline evaluation results

Generated 2026-11-25T17:23:07+00:00 by `eval/run.py`. Numbers are as measured.

## Synthetic error set (172 solutions)

| Measure | Result | Cases | Target |
|---|---:|---:|---|
| Wrong line found exactly | 100.0% | 157 | ≥ 95% |
| False alarms on correct solutions | 0.0% | 15 | ≤ 5% |
| Misconception named as labelled | 91.7% | 157 | ≥ 85% |
| Error explained by some executable rule | 93.6% | 157 |  |
| Diagnoses that are verified (not AI guesses) | 100.0% | 147 |  |

### By misconception

| Misconception | Named correctly | Cases |
|---|---:|---:|
| Arithmetic slip | 32 | 43 |
| Combined unlike terms | 26 | 26 |
| Multiplied only the first term in the bracket | 8 | 9 |
| Divided only one term by a number | 24 | 25 |
| Divided by an expression that could be zero | 3 | 3 |
| Moved a term across '=' without changing its sign | 29 | 29 |
| Negative distributed to only the first term | 3 | 3 |
| Forgot the ± when taking a square root | 2 | 2 |
| Squared a sum term by term | 1 | 1 |
| Undid multiplication by subtracting | 16 | 16 |

## Hint answer leaks (live, 2026-11-25, 20 hints)

| Measure | Result | Cases | Target |
|---|---:|---:|---|
| Hints leaking the answer before the guard | 10.0% | 20 |  |
| Hints leaking the answer after the guard | 0.0% | 20 | 0% |

## Sample sheets (live, 2026-11-25)

Synthetic sample sheets rendered in handwriting fonts — not real handwriting. Real-photo results to be added.

| Measure | Result | Cases | Target |
|---|---:|---:|---|
| Lines transcribed exactly | 100.0% | 12 |  |
| Right line and misconception, end to end | 100.0% | 3 |  |

## Failure examples

- **Different misconception** — `5 - 2(x - 3) = 1 → 6 - 2x + 6 = 1 → x = 11/2`: expected ARITH_SLIP, got unclassified
- **Different misconception** — `4x + 9 = 2x + 1 → 4x + 9/2 = x + 1/2 → x = -4/3`: expected DIVIDE_ONE_TERM, got MOVE_NO_SIGN_FLIP
- **Different misconception** — `6 - (x + 2) = 3x → 8 - x = 3x → x = 2`: expected DIST_FIRST_ONLY, got NEG_DIST_FIRST_ONLY
- **Different misconception** — `-3(x - 2) + 4 = 1 → -4x + 6 + 4 = 1 → x = 9/4`: expected ARITH_SLIP, got unclassified
- **Different misconception** — `5x + 3 = 2(x + 6) → 6x + 3 = 2x + 12 → x = 9/4`: expected ARITH_SLIP, got DIST_FIRST_ONLY
- **Different misconception** — `(x + 1)/4 = (x - 2)/3 → 4(x + 1) = 4(x - 2)`: expected ARITH_SLIP, got unclassified
- **Different misconception** — `(x + 1)/4 = (x - 2)/3 → 3(x + 1) = 4(x - 2) → 4x + 3 = 4x - 8`: expected ARITH_SLIP, got unclassified
- **Different misconception** — `(x + 3)^2 = 16 → x + 4 = ±4 → x = -8 or x = 0`: expected ARITH_SLIP, got unclassified
- **Different misconception** — `x^2 - 5x + 6 = 0 → (x - 3)(x - 3) = 0 → x = 3`: expected ARITH_SLIP, got unclassified
- **Different misconception** — `x^2 - 5x + 6 = 0 → (x - 2)(x - 3) = 0 → x = 3 or x = 3 → x = 3`: expected ARITH_SLIP, got unclassified
- **Different misconception** — `x^2 = 4x → x^3 - 4x = 0`: expected ARITH_SLIP, got unclassified
- **Different misconception** — `x^2 = 4x → x^2 - 4x = 0 → x(x - 5) = 0 → x = 0 or x = 5`: expected ARITH_SLIP, got unclassified
