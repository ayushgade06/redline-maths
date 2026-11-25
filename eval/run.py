"""Run the evaluation and publish the numbers.

    python eval/run.py              synthetic set (deterministic, no network) — CI runs this
    RUN_LIVE=1 python eval/run.py   also: live hint-leak test and sample-sheet transcription

Writes eval/results.md and web/public/eval.json. Live sections are kept from the previous
run unless RUN_LIVE=1 re-measures them, and always carry their measurement date.
"""

import datetime
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))
os.chdir(ROOT / "engine")  # so main.py's load_dotenv finds engine/.env
if os.getenv("RUN_LIVE") != "1":
    os.environ["ANTHROPIC_API_KEY"] = ""  # synthetic run must be offline and deterministic

import main  # noqa: E402
from redline import ai, guard  # noqa: E402
from redline.catalog import entry  # noqa: E402
from redline.verifier import verify_lines  # noqa: E402

OUT_JSON = ROOT / "web" / "public" / "eval.json"
OUT_MD = ROOT / "eval" / "results.md"
TODAY = datetime.date.today().isoformat()


def metric(label, hits, n, target=None, note=None):
    return {"label": label, "value": (hits / n) if n else None, "n": n, "target": target, "note": note}


def synthetic():
    """Offline by construction: executable rules only, no AI hypotheses, so CI gets identical numbers."""
    real_available, ai.available = ai.available, lambda: False
    try:
        return _synthetic()
    finally:
        ai.available = real_available


def _synthetic():
    path = ROOT / "eval" / "synthetic.json"
    if not path.exists():
        import generate

        generate.main()
    cases = json.loads(path.read_text(encoding="utf-8"))
    correct = [c for c in cases if c["first_error"] is None]
    errors = [c for c in cases if c["first_error"] is not None]
    false_alarms, located, named, verified, explained = 0, 0, 0, 0, 0
    per = defaultdict(lambda: [0, 0])
    failures = []
    for c in correct:
        r = verify_lines(None, c["lines"])
        if r.first_error_index is not None:
            false_alarms += 1
            failures.append({"kind": "False alarm", "lines": c["lines"], "expected": "no error", "got": f"line {r.first_error_index + 1}"})
    for c in errors:
        r = verify_lines(None, c["lines"])
        ok_loc = r.first_error_index == c["first_error"]
        located += ok_loc
        d, _ = main._diagnosis(r) if ok_loc else (None, False)
        per[c["misconception"]][1] += 1
        if d is not None:
            explained += 1
            verified += d.evidence == "verified"
        if d is not None and d.id == c["misconception"]:
            named += 1
            per[c["misconception"]][0] += 1
        elif not ok_loc:
            failures.append({"kind": "Wrong line", "lines": c["lines"], "expected": f"line {c['first_error'] + 1}",
                             "got": "none" if r.first_error_index is None else f"line {r.first_error_index + 1}"})
        else:
            failures.append({"kind": "Different misconception", "lines": c["lines"], "expected": c["misconception"],
                             "got": d.id if d else "unclassified"})
    n = len(errors)
    return {
        "n_cases": len(cases),
        "metrics": [
            metric("Wrong line found exactly", located, n, "≥ 95%"),
            metric("False alarms on correct solutions", false_alarms, len(correct), "≤ 5%"),
            metric("Misconception named as labelled", named, n, "≥ 85%",
                   "Several rules can produce the same line; a mismatch can still be a valid explanation."),
            metric("Error explained by some executable rule", explained, n, None, "Offline run: no AI hypotheses."),
            metric("Diagnoses that are verified (not AI guesses)", verified, max(explained, 1)),
        ],
        "by_misconception": [{"id": k, "name": entry(k)["name"], "n": v[1], "correct": v[0]} for k, v in sorted(per.items())],
    }, failures


def live_hints(n_target=20):
    """Generate real hints for real error cases and measure leaks before and after the guard."""
    cases = [c for c in json.loads((ROOT / "eval" / "synthetic.json").read_text(encoding="utf-8")) if c["first_error"]]
    picked, seen = [], set()
    for c in cases:  # spread across misconceptions
        if c["misconception"] not in seen or len(picked) < n_target // 2:
            picked.append(c)
            seen.add(c["misconception"])
        if len(picked) >= n_target // 3 + 1:
            break
    pre_leaks = post_leaks = total = 0
    for c in picked:
        r = verify_lines(None, c["lines"])
        prev, curr = r.parsed[c["first_error"] - 1], r.parsed[c["first_error"]]
        d = main.diagnose(prev, curr)
        frag = d.correct_fragment if d else None
        for level in (1, 2, 3):
            if total >= n_target:
                break
            body = main.HintIn(lines=[{"id": f"l{i}", "ascii": a} for i, a in enumerate(c["lines"])],
                               error_line_id=f"l{c['first_error']}", misconception_id=c["misconception"], level=level)
            # Raw draft (pre-guard) for the leak rate, then the full route (post-guard).
            facts = {"line_number": c["first_error"] + 1, "previous_line": prev.text, "learner_line": curr.text,
                     "misconception": {k: entry(c["misconception"])[k] for k in ("name", "description", "concept")}}
            try:
                draft = ai.hint(level, facts, "en")
            except (ai.AIUnavailable, ai.AIBadOutput):
                continue
            pre_leaks += not guard.check(draft, r.variable, r.correct_set, frag)
            final = main.hint(body)["text"]
            post_leaks += not guard.check(final, r.variable, r.correct_set, frag)
            total += 1
    return {"date": TODAY, "n": total, "metrics": [
        metric("Hints leaking the answer before the guard", pre_leaks, total),
        metric("Hints leaking the answer after the guard", post_leaks, total, "0%"),
    ]}


def live_sheets():
    """Transcribe the bundled sample sheets live and check the pipeline end to end."""
    import base64

    from fastapi.testclient import TestClient

    client = TestClient(main.app)
    meta = json.loads((ROOT / "web" / "public" / "samples" / "samples.json").read_text(encoding="utf-8"))
    exact = total_lines = e2e = 0
    for s in meta:
        img = base64.b64encode((ROOT / "web" / "public" / s["image"].lstrip("/")).read_bytes()).decode()
        t = client.post("/api/transcribe", json={"image_base64": img, "mime": "image/jpeg"}).json()
        got = [ln["ascii"].replace(" ", "") for ln in t.get("lines", [])]
        want = [x.replace(" ", "") for x in s["lines"]]
        total_lines += len(want)
        exact += sum(g == w for g, w in zip(got, want, strict=False))
        v = client.post("/api/verify", json={"problem": t.get("problem"), "lines": t.get("lines", [])}).json()
        ids = [ln["id"] for ln in t.get("lines", [])]
        idx = ids.index(v["first_error_id"]) if v.get("first_error_id") in ids else None
        e2e += idx == s["expect"]["first_error"] and (v.get("misconception") or {}).get("id") == s["expect"]["misconception"]
    return {"date": TODAY, "n_photos": len(meta), "note": "Synthetic sample sheets rendered in handwriting fonts — not real handwriting. Real-photo results to be added.",
            "metrics": [metric("Lines transcribed exactly", exact, total_lines),
                        metric("Right line and misconception, end to end", e2e, len(meta))]}


def main_():
    previous = json.loads(OUT_JSON.read_text(encoding="utf-8")) if OUT_JSON.exists() else {}
    syn, failures = synthetic()
    live = os.getenv("RUN_LIVE") == "1" and ai.available()
    hints = live_hints() if live else previous.get("hints")
    photos = live_sheets() if live else previous.get("photos")
    data = {"generated_at": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
            "synthetic": syn, "hints": hints, "photos": photos, "failures": failures[:12]}
    OUT_JSON.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")

    def table(ms):
        rows = ["| Measure | Result | Cases | Target |", "|---|---:|---:|---|"]
        rows += [f"| {m['label']} | {'—' if m['value'] is None else f'{m['value'] * 100:.1f}%'} | {m['n']} | {m['target'] or ''} |" for m in ms]
        return "\n".join(rows)

    md = [f"# Redline evaluation results\n\nGenerated {data['generated_at']} by `eval/run.py`. Numbers are as measured.\n",
          f"## Synthetic error set ({syn['n_cases']} solutions)\n", table(syn["metrics"]), "\n### By misconception\n",
          "| Misconception | Named correctly | Cases |", "|---|---:|---:|"]
    md += [f"| {b['name']} | {b['correct']} | {b['n']} |" for b in syn["by_misconception"]]
    if hints:
        md += [f"\n## Hint answer leaks (live, {hints['date']}, {hints['n']} hints)\n", table(hints["metrics"])]
    if photos:
        md += [f"\n## Sample sheets (live, {photos['date']})\n", photos["note"] + "\n", table(photos["metrics"])]
    md += ["\n## Failure examples\n"] + [f"- **{f['kind']}** — `{' → '.join(f['lines'])}`: expected {f['expected']}, got {f['got']}" for f in failures[:12]]
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    for m in syn["metrics"]:
        print(f"{m['label']}: {m['value'] if m['value'] is None else round(m['value'] * 100, 1)}% (n={m['n']})")
    if hints:
        print("hints:", [(m["label"], m["value"]) for m in hints["metrics"]])
    if photos:
        print("sheets:", [(m["label"], m["value"]) for m in photos["metrics"]])


if __name__ == "__main__":
    main_()
