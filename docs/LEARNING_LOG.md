# Learning log

> **Author:** these are notes from the build, written as prompts. The Learning & Growth criterion is judged on *your* reflection — rewrite each entry in your own words, keep what's true for you, and add what you actually struggled with.

## 2026-11-25 — `parse_expr` is `eval` with extra steps
SymPy's `parse_expr` turns the string into Python code and runs `eval` on it. Passing a learner's (or a model's) text straight in would let `__import__('os')` run. The fix is a gate *before* the parser: a character whitelist, a single variable, only `sqrt`, and caps on length, exponents, numbers and nesting — then `parse_expr` with a minimal namespace. Even model output goes through the same gate, which is what makes prompt injection in a photo harmless.

## 2026-11-25 — Equal expressions vs. equal solution sets
"Is this step correct?" means different things for expressions and equations. `2(x−3)` and `2x−6` are equal expressions. `2x = 16` and `x = 8` aren't equal expressions at all, but they have the same solution set — that's what a valid algebra step preserves. Comparing solution sets also gives a free classification: a smaller set means a lost root (dividing by x, forgetting ±), a bigger set means an extraneous root (squaring both sides).

## 2026-11-25 — SymPy quietly "fixes" mistakes
With `evaluate=False`, `-(x - 4)` was still expanded to `4 - x`, which would have hidden exactly the sign mistakes Redline is looking for. Writing it as `0 - (x - 4)` keeps the bracket. Lesson: a library's normalisation is great for checking correctness and terrible for diagnosing *how* someone went wrong.

## 2026-11-25 — Executable misconceptions
Instead of asking an LLM "what did the student do wrong?", encode common mistakes as buggy rewrite rules (`−k(a+b) → −ka + kb`), apply them to the previous line, and see if one reproduces the student's line. If it does, the diagnosis is a proof, not a guess (idea from MalruleLib, arXiv 2601.03217). The evaluation also showed where this breaks: a single changed number can be explained by several rules, so rules need a priority order and "arithmetic slip" has to be strict about what counts as a near miss.

## 2026-11-25 — Prompts aren't guarantees; code guards are
The hint prompt says "never reveal the answer" and the model is never given the answer — and still, in the live evaluation, 2 of 20 raw drafts leaked it (by working it out). The deterministic guard caught both. Measuring the pre-guard rate is what makes the guard's value visible.

## 2026-11-25 — Reading the API terms changed the audience
The original plan used Gemini, whose terms forbid apps likely to be used by under-18s; that's why Redline is scoped to adult learners with an 18+ gate. The build ended up on Claude because that's the key available, and the 18+ scope stayed.

## 2026-11-25 — The evaluation found real bugs
Generating errors automatically (every rule at every step) found two bugs the hand-written tests missed: a step collapsing to `3x = 3x` was only a warning, and the "divided by x" rule fired whenever one side was 0. Both fixed; localisation went from 98.1% to 100% on the synthetic set.
