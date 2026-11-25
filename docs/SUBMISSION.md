# Submission kit (STEM2Connect AI Hackathon 2026)

Deadline: **Sun Nov 29, 11:59 PM EST = Mon Nov 30, 10:29 AM IST**. Internal target: submitted by **Sun Nov 29, 11:00 PM IST**.

## One-liners

- **Name:** Redline
- **Tagline:** Finds the exact line where your math went wrong. Won't give you the answer.
- **Track:** Education
- **Short description (≤ 200 chars):** Snap your handwritten algebra. Redline proves which line is wrong with a math engine, names the mistake, and coaches you with hints that code-checks never reveal the answer.

## Devpost text (draft — personalise the bracketed parts)

**Inspiration**
AI made getting answers free and learning optional. In a 2025 field experiment with about 1,000 high-school students, those who practised with unrestricted GPT-4 scored 17% lower on the exam without it than students who never had it (Bastani et al., PNAS 2025). [Author: one or two true sentences about a time you couldn't find where your own algebra went wrong.]

**What it does**
- Reads a photo of your handwritten working, line by line, and shows where each line is on the photo.
- Lets you confirm the reading, so it never blames you for a misread.
- Proves which line is wrong with SymPy — the AI never decides correctness.
- Names the misconception: verified when an executable rule reproduces your line, otherwise a labelled AI hypothesis.
- Coaches with three hints that a code guard checks for answers, then re-verifies your fix and gives targeted practice. Instructors can see which mistakes their class shares, anonymously.

**How we built it**
FastAPI + SymPy engine, React/Vite/Tailwind/KaTeX front end, one Docker service. A whitelist parser feeds a solution-set verifier; ten misconceptions are buggy rewrite rules; a deterministic guard scans every hint. Claude (Anthropic) does three narrow jobs with structured outputs: transcription with line boxes, labelled hypotheses, and hint wording. An evaluation harness generates 157 seeded errors from 15 hand-written solutions and measures localisation, false alarms, diagnosis accuracy and hint leakage.

**How we used AI**
1. *In the product:* Claude reads handwriting (with bounding boxes), suggests misconceptions only when no rule matches (labelled "AI hypothesis"), and words hints. It never sees the answer, and code checks every hint.
2. *To build it:* Claude Code as a coding assistant — scaffolding, most of the engine and UI code, tests, evaluation scripts, doc drafts, bug fixing. [Author: what you designed, wrote, reviewed and tested yourself.] Full detail in `AI_DISCLOSURE.md`.

**Challenges**
Safe parsing (SymPy's parser uses `eval`); SymPy auto-expanding the very sign errors we needed to see; extraneous vs lost roots; making "arithmetic slip" strict enough not to swallow real misconceptions; guard false positives (the learner's own bracket looks like the corrected term); a browser freeze traced to a variable web font.

**Accomplishments**
100% of seeded errors found on the exact line, 0% false alarms, 91.7% of misconceptions named as labelled (offline, rules only). Live: 10% of raw hint drafts leaked the answer and the guard caught all of them (0% after). Works from a phone photo, in four languages.

**What we learned**
See `docs/LEARNING_LOG.md` — [author: summarise your 3–4 lessons in your own words].

**What's next**
Real-photo evaluation; safeguards and a provider suitable for under-18s; inequalities and systems; a classroom pilot.

**Pre-existing work:** None — built Nov 25–29, 2026.

## Demo video (target 3:30–4:30, hard max 6:00)

| Time | Show | Say (in your own words) |
|---|---|---|
| 0:00–0:20 | A handwritten page; the red underline draws under line 2 | "This is my algebra. Somewhere in here I made a mistake. Watch Redline find it — and refuse to give me the answer." |
| 0:20–0:50 | Title + PNAS finding | The 17% finding; answer machines make learning optional; learners need *where*, not the answer. |
| 0:50–2:20 | Live on the production URL: upload photo → review (fix one character) → red box on the photo, "Verified diagnosis" → hints 1–3 with "Answer guard passed" → fix the line → "All steps verified" → one practice problem | "The AI read my handwriting, but the math engine decided it was wrong." |
| 2:20–3:10 | How it works page: pipeline + evaluation table | "The LLM perceives and explains; SymPy judges; code enforces the pedagogy." Read 2–3 numbers, including the 10% → 0% leak result and one failure. |
| 3:10–3:35 | Instructor dashboard (if deployed with a database) | Anonymous class misconceptions; re-teach suggestions. |
| 3:35–4:10 | Learning | Solution sets vs expressions; `parse_expr` is `eval`; prompts aren't guarantees; API terms shaped the audience. |
| 4:10–4:30 | Next steps + close | "Redline finds your mistake, and leaves the learning to you." |

Tips: open the site a minute before recording (free hosting sleeps); 1080p; browser zoom 125%; captions on; one clean take plus a backup.

## Screenshots (1200×800 cover + 5)

1. Landing hero (worked sheet with the red underline)
2. Review screen: photo with numbered boxes + editable lines
3. Results: red box + underline on the photo, verified diagnosis card
4. Hint ladder with three hints and guard chips (one in Hindi)
5. How it works: pipeline + evaluation table
6. (Optional) Instructor dashboard

Save to `docs/screenshots/` and reference `results-desktop.jpg` from the README.

## Final checklist

- [ ] Production URL works in incognito on phone and desktop; sample flow 5/5
- [ ] Typed fallback works with AI disabled
- [ ] Public GitHub repo with README, LICENSE, AI_DISCLOSURE.md, LEARNING_LOG.md (in your words), eval/results.md
- [ ] Video ≤ 6:00, public or unlisted on YouTube, captions on, link tested logged-out
- [ ] Devpost: problem, solution, AI use, learnings, next steps; **track: Education**; AI tool disclosure; pre-existing work statement; repo + video + live links
- [ ] 18+ scope and privacy explained
- [ ] Submitted before Sun Nov 29, 11:00 PM IST; page shows "Submitted"
