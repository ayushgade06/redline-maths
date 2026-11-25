# Progress

Status against the milestones in the project plan (§19; the plan itself is kept out of the public repo).

| Milestone | Status | Notes |
|---|---|---|
| M0 Repository foundation | ✅ | Monorepo, CI workflow (ruff, pytest, tsc, vitest, vite build, synthetic eval, bundle key scan), `.env.example` |
| M1 Safe parser | ✅ | 36 accept/reject cases incl. `__import__`, huge exponents, power towers, 200-char lines, two variables |
| M2 Step verifier | ✅ | Zero false alarms on 16 correct solutions; 33 seeded errors on the right line; lost/gained roots; p95 well under 300 ms |
| M3 Executable misconceptions | ✅ | 10 catalog rules + `EXTRANEOUS_ROOT`; ≥ 3 positives each, 6 negatives |
| M4 Engine API + AI integration | ✅ | Real Claude calls; 3 transcriptions + 1 hypothesis recorded as fixtures; offline behaviour without a key |
| M5 Hints + answer guard | ✅ | 12 leaks caught, 11 safe pass; regenerate-once → template; `/hint` never 5xx; live leak rate 10% → 0% after guard |
| M6 Frontend shell + design system | ✅ | Tokens (light/dark), components, routes, typed API client, 18+ gate with storage fallback |
| M7 Core flow UI | ✅ | Capture (photo/typed/samples) → review with boxes → results with red box + underline on the photo |
| M8 Hints, fix loop, practice | ✅ | Sequential hint ladder, 4 languages, fix-and-re-verify (with "remove lines below"), practice with SymPy checking |
| M9 Class insights | ✅ | Endpoints, dashboard, share flow; Neon Postgres in production (create → share → summary → 404 verified against the real database) |
| M10 Evaluation harness | ✅ | Synthetic 172 cases; live hint-leak (20) and sample sheets (3). Real photos still to add |
| M11 Deployment & hardening | ✅ | Live on Vercel (https://redline-maths.vercel.app): Vite frontend + FastAPI Python function via Vercel Services, security headers, Neon Postgres for class mode. Production sample flow verified in Chrome. Docker + Render blueprint kept as an alternative |
| M12 Polish, demo, submission | ⏳ | Screenshots, video and Devpost form are for the author; drafts in `docs/SUBMISSION.md` |

## Decisions and deviations

| Decision | Why |
|---|---|
| **Claude (Anthropic) instead of Gemini** for the in-product AI | The author supplied an Anthropic key; no Gemini key was available. Claude reads handwriting, returns line boxes accurately on the samples (all 3 sheets end-to-end correct) and supports structured JSON output. Model id is configurable (`AI_MODEL`), verified with `scripts/list_models.py` on 2026-11-25 (`claude-opus-5-5`). The 18+ gate and scope stay as planned. |
| **One Vercel project with Vercel Services** instead of two projects | Same origin for app and API (no CORS). The engine can also serve the built app itself (Docker/Render path). |
| **Box snapping** (`boxes.py`) | In production testing a Claude box came back half a line high, putting the red underline between lines. Boxes are now snapped to ink rows deterministically; a test proves shifted boxes snap to the same rows. |
| **Fonts self-hosted (Fontsource) instead of Google Fonts** | The Google-hosted variable Fraunces with SOFT/WONK axes froze the Chrome renderer in testing; self-hosting also removes a third-party request. |
| `/practice/check` takes `prompt_ascii` instead of params | The problem text fully defines the check; the answer is never sent to the client either way. |
| Test data as `tests/data/{correct,errors}.json` (two files instead of one per case) | Same content, fewer files. |
| `gained_solution` is a warning, not an error, when finitely many roots are added | Squaring is a legitimate step; keeping the extraneous root is flagged at the final answer instead. Collapsing to an identity is an error. |
| Sample sheets rendered with handwriting fonts | No author photos yet; they're labelled as such in the UI, README and eval. |

## Known issues

- Real handwritten photos not yet evaluated (`eval/photos/`).
- Rate limiting is per instance (in-memory).
- Render free tier sleeps when idle: warm the site before demos.
- Test suite takes ~10 s; most of it is SymPy work.
