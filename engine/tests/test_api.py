"""Route tests. AI calls are monkeypatched with responses recorded from real Claude calls
(tests/fixtures/recorded_*.json), never invented ones."""

import base64
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
from redline import ai

FIX = Path(__file__).parent / "fixtures"
SAMPLES = Path(__file__).resolve().parents[2] / "web" / "public" / "samples"
client = TestClient(main.app)


def recorded(name):
    return json.loads((FIX / f"recorded_{name}.json").read_text(encoding="utf-8"))["response"]


@pytest.fixture
def ai_on(monkeypatch):
    monkeypatch.setattr(ai, "available", lambda: True)


def lines(*xs):
    return [{"id": f"l{i + 1}", "ascii": a} for i, a in enumerate(xs)]


NEG = lines("5 - 2(x - 3) = 1", "5 - 2x - 6 = 1", "-2x - 1 = 1", "-2x = 2", "x = -1")


def test_health():
    r = client.get("/api/health").json()
    assert r["status"] == "ok" and r["db"] == "disabled" and r["ai"] == "disabled"


@pytest.mark.parametrize("sample", ["negative-bracket", "moving-terms", "square-root"])
def test_transcribe_with_recorded_response(ai_on, monkeypatch, sample):
    monkeypatch.setattr(ai, "transcribe", lambda b, m: recorded(f"transcribe_{sample}"))
    img = base64.b64encode((SAMPLES / f"{sample}.jpg").read_bytes()).decode()
    r = client.post("/api/transcribe", json={"image_base64": img, "mime": "image/jpeg"})
    assert r.status_code == 200
    body = r.json()
    assert body["lines"] and all(ln["parse_ok"] for ln in body["lines"])
    assert all(0 <= v <= 1 for ln in body["lines"] for v in ln["box"])
    # The deliberate mistake is preserved, not corrected.
    v = client.post("/api/verify", json={"problem": body["problem"], "lines": body["lines"]}).json()
    assert v["first_error_id"] is not None and v["final_correct"] is False


def test_transcribe_without_key_is_503():
    img = base64.b64encode((SAMPLES / "square-root.jpg").read_bytes()).decode()
    r = client.post("/api/transcribe", json={"image_base64": img})
    assert r.status_code == 503 and r.json()["error"]["code"] == "ai_unavailable"


def test_transcribe_rejects_non_image(ai_on):
    r = client.post("/api/transcribe", json={"image_base64": base64.b64encode(b"hello").decode()})
    assert r.status_code == 415


def test_transcribe_bad_output_twice_is_502(ai_on, monkeypatch):
    def boom(b, m):
        raise ai.AIBadOutput("x")

    monkeypatch.setattr(ai, "transcribe", boom)
    img = base64.b64encode((SAMPLES / "square-root.jpg").read_bytes()).decode()
    assert client.post("/api/transcribe", json={"image_base64": img}).status_code == 502


def test_verify_verified_diagnosis_offline():
    r = client.post("/api/verify", json={"lines": NEG}).json()
    assert r["first_error_id"] == "l2"
    assert r["misconception"]["id"] == "NEG_DIST_FIRST_ONLY"
    assert r["misconception"]["evidence"] == "verified"
    assert r["final_correct"] is False and r["offline"] is False


def test_verify_never_sends_the_answer():
    raw = client.post("/api/verify", json={"lines": NEG}).text
    assert '"5"' not in raw and "x = 5" not in raw


def test_verify_ai_hypothesis_from_recorded_response(ai_on, monkeypatch):
    monkeypatch.setattr(ai, "hypothesize", lambda p, c: recorded("hypothesis"))
    r = client.post("/api/verify", json={"lines": lines("3x + 4 = 19", "x + 4 = 57")}).json()
    assert r["misconception"]["evidence"] == "ai_hypothesis"


def test_verify_offline_flag_when_ai_down():
    r = client.post("/api/verify", json={"lines": lines("3x + 4 = 19", "x + 4 = 57")}).json()
    assert r["misconception"] is None and r["offline"] is True


def test_verify_unsupported_scope():
    r = client.post("/api/verify", json={"lines": lines("x + y = 2")})
    assert r.status_code == 422 and r.json()["error"]["code"] == "unsupported_scope"


def test_verify_validation_limits():
    assert client.post("/api/verify", json={"lines": []}).status_code == 422
    assert client.post("/api/verify", json={"lines": lines(*["x=1"] * 21)}).status_code == 422


def hint_body(level, **kw):
    return {"lines": NEG, "error_line_id": "l2", "misconception_id": "NEG_DIST_FIRST_ONLY", "level": level} | kw


@pytest.mark.parametrize("level", [1, 2, 3])
def test_hint_template_when_ai_off(level):
    r = client.post("/api/hint", json=hint_body(level))
    assert r.status_code == 200
    h = r.json()
    assert h["source"] == "template" and h["guard"]["passed"]
    if level == 3:
        assert h["example"]["problem"] != "5 - 2(x - 3) = 1"


def test_hint_leak_regenerates_then_falls_back(ai_on, monkeypatch):
    calls = []

    def leaky(level, facts, lang, strict=False):
        calls.append(strict)
        return "Easy: x = 5."

    monkeypatch.setattr(ai, "hint", leaky)
    h = client.post("/api/hint", json=hint_body(1)).json()
    assert calls == [False, True]
    assert h["source"] == "template" and h["guard"]["regenerated"] is True and "x = 5" not in h["text"]


def test_hint_regenerated_clean_draft_is_used(ai_on, monkeypatch):
    monkeypatch.setattr(
        ai,
        "hint",
        lambda level, facts, lang, strict=False: (
            "Check the sign of the second term in line 2." if strict else "It should be -2x + 6."
        ),
    )
    h = client.post("/api/hint", json=hint_body(1)).json()
    assert h["source"] == "ai" and h["guard"]["regenerated"] is True


def test_hint_never_5xx_when_ai_fails(ai_on, monkeypatch):
    def down(*a, **k):
        raise ai.AIUnavailable("x")

    monkeypatch.setattr(ai, "hint", down)
    r = client.post("/api/hint", json=hint_body(2))
    assert r.status_code == 200 and r.json()["source"] == "template"


def test_hint_facts_never_include_the_answer(ai_on, monkeypatch):
    seen = {}
    monkeypatch.setattr(ai, "hint", lambda level, facts, lang, strict=False: seen.setdefault("f", facts) and "ok line 2")
    client.post("/api/hint", json=hint_body(3))
    blob = json.dumps(seen["f"])
    assert "x = 5" not in blob and "-2x + 6" not in blob


def test_hint_unknown_misconception():
    assert client.post("/api/hint", json=hint_body(1, misconception_id="NOPE")).status_code == 422


def test_practice_generate_and_check():
    probs = client.post("/api/practice/generate", json={"misconception_id": "MOVE_NO_SIGN_FLIP", "count": 2}).json()["problems"]
    assert len(probs) == 2 and "x0" not in probs[0]["params"]
    p = probs[0]["params"]
    answer = (eval_rhs := int(probs[0]["prompt_ascii"].split("=")[1])) and (eval_rhs - p["b"]) // p["a"]
    ok = client.post(
        "/api/practice/check",
        json={"template_id": "MOVE_NO_SIGN_FLIP", "prompt_ascii": probs[0]["prompt_ascii"], "answer_ascii": f"x = {answer}"},
    ).json()
    bad = client.post(
        "/api/practice/check",
        json={"template_id": "MOVE_NO_SIGN_FLIP", "prompt_ascii": probs[0]["prompt_ascii"], "answer_ascii": f"x = {answer + 1}"},
    ).json()
    assert ok["correct"] is True and bad["correct"] is False


def test_practice_unknown_is_404():
    assert client.post("/api/practice/generate", json={"misconception_id": "NOPE"}).status_code == 404


def test_class_mode_disabled_without_db():
    assert client.post("/api/class", json={"name": "Algebra 101"}).status_code == 503


def test_error_shape_for_unknown_route():
    r = client.get("/api/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


def test_rate_limit(monkeypatch):
    monkeypatch.setattr(main, "_buckets", main.defaultdict(lambda: [0.0, 0.0]))
    codes = [client.post("/api/hint", json=hint_body(1), headers={"x-forwarded-for": "9.9.9.9"}).status_code for _ in range(22)]
    assert codes.count(429) >= 1


@pytest.mark.skipif(os.getenv("RUN_LIVE") != "1", reason="opt-in live test: RUN_LIVE=1")
def test_live_transcribe_and_hint():
    img = base64.b64encode((SAMPLES / "negative-bracket.jpg").read_bytes()).decode()
    t = client.post("/api/transcribe", json={"image_base64": img}).json()
    v = client.post("/api/verify", json={"problem": t["problem"], "lines": t["lines"]}).json()
    assert v["misconception"]["id"] == "NEG_DIST_FIRST_ONLY"
    h = client.post(
        "/api/hint",
        json={
            "lines": t["lines"],
            "problem": t["problem"],
            "error_line_id": v["first_error_id"],
            "misconception_id": "NEG_DIST_FIRST_ONLY",
            "level": 3,
            "lang": "hi",
        },
    ).json()
    assert h["guard"]["passed"]


def test_boxes_snap_to_ink_rows_even_when_the_model_is_off():
    from redline.boxes import snap

    img = (SAMPLES / "moving-terms.jpg").read_bytes()
    good = [[v / 1000 for v in ln["box_2d"]] for ln in recorded("transcribe_moving-terms")["lines"]]
    shifted = [[b[0] - 0.045, b[1], b[2] - 0.045, b[3]] for b in good]  # half a line too high
    assert snap(img, shifted) == snap(img, good)
