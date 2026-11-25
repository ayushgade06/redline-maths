# Testing

## Automated

| Layer | Command | What it covers |
|---|---|---|
| Engine | `cd engine && pytest -q` | 226 tests: parser accept/reject (incl. injection strings), 16 correct solutions with zero false alarms, 33 seeded errors on the exact line, every misconception ≥ 3 positive cases + 6 negative cases, guard (12 leaks caught, 11 safe hints pass, all templates pass), API routes with recorded Claude fixtures, offline paths, rate limit |
| Live (opt-in) | `RUN_LIVE=1 pytest -q -k live` | real transcription of a sample sheet → verify → Hindi L3 hint |
| Web | `cd web && npm test` | ASCII→LaTeX, image fit and box scaling, gate storage with broken localStorage, API error mapping, hint unlock order |
| Build | `npx tsc --noEmit && npx vite build`, `ruff check . && ruff format --check .` | types, bundle, lint |
| Evaluation | `python eval/run.py` (+ `RUN_LIVE=1`) | see `eval/results.md` |
| Security | CI greps `web/dist` for `sk-ant-` / `ANTHROPIC_API_KEY` | no key in the client bundle |

## Manual end-to-end script (run on production before recording)

| # | Step | Expected |
|---|---|---|
| 1 | Open the site in a private window | Landing renders; worked sheet shows the red underline under line 2 |
| 2 | Click **Try a sample** | 18+ gate appears; Continue stays disabled until both boxes are ticked |
| 3 | Accept the gate | "Reading your handwriting…" then the review screen within ~10 s; numbered boxes sit on each line |
| 4 | Click **Looks right — check my steps** | Results: line 2 boxed + underlined in red on the photo; "Verified diagnosis — Negative distributed to only the first term" |
| 5 | Click **Get a nudge**, **Explain the idea**, **Show a similar example** | Three hints, each with "Answer guard passed"; the example uses different numbers; no hint contains `x = 5` |
| 6 | Switch language to हिन्दी, open a new check, request a hint | Hint in Hindi, math in KaTeX |
| 7 | **Fix this line** → `5 - 2x + 6 = 1` with "Remove the lines below" ticked → Re-check | "Every step so far follows"; photo shows the fixed line as "edited" |
| 8 | **Add next step** `11 - 2x = 1`, `-2x = -10`, `x = 5` | "All 5 steps verified"; practice panel appears |
| 9 | Answer a practice problem right, then wrong | "Correct" / "Not yet" |
| 10 | **Type steps**: `x^2 = 9`, `x = 3` | Line 2 "Loses a solution", verified "Forgot the ± when taking a square root" |
| 11 | Type `x + y = 2` | Banner: single-variable algebra only |
| 12 | Upload a real photo from a phone camera (Android/iOS) | Photo downscaled, transcribed, boxes aligned |
| 13 | Stop the AI (unset key on a test deploy) and use **Type steps** | Offline banner; verification works; hints show "Built-in hint" |
| 14 | (Class mode) For instructors → create class → share a diagnosis from results → open dashboard | Counts and re-teach suggestions update within 30 s; invalid code shows "No class with code …" |
| 15 | Keyboard only: Tab through the gate, capture, results, hints | Visible focus everywhere; all actions reachable |
| 16 | 360 px wide | No horizontal scroll; tap targets ≥ 44 px |

## Results log

| Date | Where | Result |
|---|---|---|
| 2026-11-25 | Local (Chrome, desktop 1536 px + 375 px iframes) | Steps 1–5, 7–9 pass on the negative-bracket sample with live Claude; no horizontal scroll at 360–375 px on landing, check and how-it-works; light and dark themes checked |
| 2026-11-25 | Production (redline-maths.vercel.app, Chrome desktop) | Health ok (AI + DB); gate → moving-terms sample → review → results with verified MOVE_NO_SIGN_FLIP diagnosis; no console errors. Found a misplaced box (model half a line off) → added box snapping |
| _pending_ | Real phone camera | Step 12 |
