# Architecture

## Shape

One FastAPI service (`engine/`) owns all math and AI logic. On Vercel, `vercel.json` (Vercel Services) serves the Vite build as the frontend and runs the engine as a Python function (`api/index.py`) behind `/api/*` — one origin, no CORS. In Docker, the engine serves `web/dist` itself. In development, Vite serves the app on :5173 and proxies `/api` to the engine.

```
engine/
  main.py                 routes, validation, rate limit, error mapping, security headers, static serving
  redline/safe_parse.py   whitelist + caps → SymPy (the security boundary)
  redline/verifier.py     solution-set equivalence per step, final-answer check, timeouts
  redline/malrules.py     executable misconceptions (rewrite rules + relation detectors)
  redline/catalog.py      misconception names, explanations, template hints
  redline/guard.py        deterministic answer-leak guard
  redline/practice.py     targeted practice + parallel worked examples
  redline/ai.py           the only module that calls the LLM (Claude, structured outputs)
  redline/boxes.py        snaps model line boxes to ink rows in the photo (Pillow)
  redline/db.py           optional class mode (Postgres)
web/src/
  pages/Check.tsx         capture → review → results → fix → practice
  components/Hints.tsx    hint ladder with guard chips
  lib/api.ts              typed client, engine error shape → friendly messages
  lib/math.ts             ASCII grammar → LaTeX for KaTeX (display only)
eval/                     seeds, generator, runner, results
```

## The verifier

For a transition A → B in variable x over ℝ:

- **Equations:** `S_A = solveset(A.lhs − A.rhs)` (union over `or` clauses), likewise `S_B`. Equal → valid. `S_B ⊂ S_A` → lost solution (error). `S_A ⊂ S_B` with finitely many extra values → gained solution (warning: squaring/multiplying can do this legitimately). Infinite extra values (e.g. collapsing to `3x = 3x`) or otherwise different → invalid.
- **Expressions:** `simplify(A − B) == 0`, else 7 numeric samples at random rationals (fixed seed, poles skipped).
- **Kinds differ** (equation ↔ expression): a new segment, not judged.
- **Final answer:** when the last line isolates the variable, its solution set is compared with the problem's. If every step followed but the answer is wrong (an extraneous root kept), the last line is flagged.
- Each transition runs under a 3 s timeout in a thread pool. Python threads can't be killed, so the parser's caps (length 120, exponents ≤ 10, integers ≤ 10⁶, nesting ≤ 6, degree ≤ 4 for scope) bound the worst case.

The correct solution set stays on the server. It's used for the final verdict and the guard, and is never serialised.

## Executable misconceptions

`malrules.py` generates buggy successors of the previous line:

| Rule | Rewrite |
|---|---|
| `NEG_DIST_FIRST_ONLY` | `−k(a + b) → −ka + kb` on any subtree (unary minus kept unexpanded by the parser) |
| `DIST_FIRST_ONLY` | `k(a + b) → ka + b` (each term position) |
| `MOVE_NO_SIGN_FLIP` | move a term across `=` keeping its sign |
| `DIVIDE_ONE_TERM` | divide a side by the variable's coefficient, but only one term |
| `SQUARE_OF_SUM` | `(a + b)² → a² + b²` (and sign-kept variant); squaring a sqrt equation term by term |
| `COMBINE_UNLIKE` | merge terms of different degree |
| `TRANSPOSE_MULT_AS_ADD` | `kx = R → x = R − k` |

…plus relation detectors: `SQRT_LOST_NEG_ROOT` (one branch of `B² = c` kept), `DIV_BY_VARIABLE` (lost root 0 or a shared factor), `ARITH_SLIP` (changing one integer by a near-miss amount makes the step valid), and `EXTRANEOUS_ROOT` (from the final-answer check). Candidates are capped at 200 and tried in a fixed priority order. A candidate whose solution set equals the learner's line is a **verified** diagnosis; it also yields the *focus* (the learner's own fragment, safe to show) and the *correct fragment* (server-only, a guard input).

## The answer guard

A hint is rejected if any of these hold:
1. A math span parses as an equation whose solution set equals the problem's.
2. A phrase like "x is 4", "the answer is 4" names a root.
3. An expanded expression span equals the corrected fragment (e.g. `−2x + 6`).

On rejection the hint is regenerated once with a stricter instruction, then replaced by the catalog template. Templates are unit-tested to pass. The L3 worked example is generated from the practice template with resampled numbers until its answer differs from the learner's and its numbers overlap as little as possible.

## Failure handling

| Failure | Engine | UI |
|---|---|---|
| No key / quota / network | 503 `ai_unavailable` on transcribe; verify sets `offline`; hint falls back to template | Offline banner; typed path; samples fall back to their typed lines (labelled) |
| Malformed model output | retry once → 502 `ai_bad_output` | "Couldn't read that photo" + type instead |
| Unparseable line | `unreadable` + reason | amber "?" and edit prompt |
| SymPy timeout | `undetermined` | "Couldn't verify automatically" (never blames the learner) |
| Two variables | 422 `unsupported_scope` | explains the supported scope |
| Rate limit | 429 | "wait a moment" |
