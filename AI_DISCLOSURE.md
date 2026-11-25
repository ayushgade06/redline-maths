# AI disclosure

The hackathon rules allow AI coding assistants with disclosure and attribution. This file states what AI did in this project.

## AI inside the product

| Where | Model | What it does | What it never does |
|---|---|---|---|
| `engine/redline/ai.py` → `transcribe()` | Anthropic Claude (`claude-opus-5-5`, set by `AI_MODEL`) | Reads a photo of handwritten algebra; returns each line in a strict ASCII grammar with a bounding box and a confidence | Correct, solve or judge anything. Its output is re-validated by `safe_parse.py` and confirmed by the learner. |
| `hypothesize()` | same | When no executable rule explains a wrong step, suggests a catalog misconception, shown as **AI hypothesis** | Decide that the step is wrong (the verifier already proved that). |
| `hint()` | same | Words the three hint levels from verified facts | See the answer: the engine never passes the correct answer or corrected line. Every hint is checked by `guard.py`. |

Correctness, diagnosis (when verified), practice answers and the answer guard are deterministic code (SymPy + Python).

## AI used to build the product

**Claude Code** (Anthropic's coding agent) was used as a coding assistant during the hackathon (Nov 25–29, 2026). It:

- scaffolded the repository, engine and web app from the author's project plan (kept out of the repo);
- wrote most of the code in `engine/` and `web/`, the tests, the evaluation scripts and the first drafts of the docs;
- ran the tests, the evaluation and browser checks, and fixed the bugs they found.

**What the author did:** chose the problem and wrote the project plan (idea, scope, architecture, milestones); directed the build; reviewed the code and behaviour; _[author: list what you personally wrote, changed, tested on your phone, and decided — be specific and honest]_.

Recorded test fixtures in `engine/tests/fixtures/recorded_*.json` are real Claude responses, captured on 2026-11-25; none are invented.
