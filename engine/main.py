"""Redline engine: FastAPI app. Run with `uvicorn main:app --reload` from engine/."""

from __future__ import annotations

import base64
import binascii
import json
import logging
import os
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from redline import __version__, ai, boxes, db, guard, practice  # noqa: E402
from redline.catalog import CATALOG, entry  # noqa: E402
from redline.malrules import Diagnosis, diagnose  # noqa: E402
from redline.safe_parse import ParseError, detect_variable, normalize, parse_line  # noqa: E402
from redline.verifier import VerifyResult, verify_lines  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("redline")

MAX_BODY = 6_000_000
MAX_IMAGE = 4_000_000

app = FastAPI(title="Redline engine", version=__version__, docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class APIError(HTTPException):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(status, {"code": code, "message": message})


@app.exception_handler(HTTPException)
async def _http_error(_: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "error", "message": str(exc.detail)}
    return JSONResponse({"error": detail}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def _validation_error(_: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    where = ".".join(str(p) for p in first.get("loc", [])[1:])
    msg = f"{where}: {first.get('msg', 'invalid request')}" if where else "invalid request"
    return JSONResponse({"error": {"code": "invalid_request", "message": msg}}, status_code=422)


# ponytail: in-memory token buckets are per instance; move to Redis/Upstash if scaled out.
_RATES = {"transcribe": 6, "hint": 20, "default": 60}  # requests per minute per IP
_buckets: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0, 0.0])


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?")


def _allow(ip: str, group: str) -> bool:
    rate = _RATES.get(group, _RATES["default"])
    tokens, last = _buckets[(ip, group)]
    now = time.monotonic()
    tokens = rate if last == 0 else min(rate, tokens + (now - last) * rate / 60)
    if tokens < 1:
        _buckets[(ip, group)] = [tokens, now]
        return False
    _buckets[(ip, group)] = [tokens - 1, now]
    return True


SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; "
        "font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(self), microphone=(), geolocation=()",
    "X-Frame-Options": "DENY",
}


@app.middleware("http")
async def _guards_and_logging(request: Request, call_next):
    start = time.perf_counter()
    path = request.url.path
    if path.startswith("/api/") and request.method == "POST":
        if int(request.headers.get("content-length") or 0) > MAX_BODY:
            return JSONResponse({"error": {"code": "too_large", "message": "Request is too large."}}, status_code=413)
        group = path.split("/")[2] if path.count("/") >= 2 else "default"
        if not _allow(_client_ip(request), group if group in _RATES else "default"):
            return JSONResponse(
                {"error": {"code": "rate_limited", "message": "Too many requests — wait a minute."}}, status_code=429
            )
    response = await call_next(request)
    for k, v in SECURITY_HEADERS.items():
        if not (k == "Content-Security-Policy" and path == "/api/docs"):  # Swagger UI loads from a CDN
            response.headers.setdefault(k, v)
    if path.startswith("/api/"):
        # Never log images or line content: route, status, latency only.
        log.info(json.dumps({"route": path, "status": response.status_code, "ms": round((time.perf_counter() - start) * 1000)}))
    return response


# ---------- models ----------


class LineIn(BaseModel):
    id: str = Field(max_length=20)
    ascii: str = Field(max_length=160)


class VerifyIn(BaseModel):
    problem: str | None = Field(default=None, max_length=160)
    lines: list[LineIn] = Field(min_length=1, max_length=20)


class TranscribeIn(BaseModel):
    image_base64: str = Field(max_length=MAX_BODY)
    mime: Literal["image/jpeg", "image/png", "image/webp"] = "image/jpeg"


class HintIn(VerifyIn):
    error_line_id: str = Field(max_length=20)
    misconception_id: str = Field(max_length=40)
    level: Literal[1, 2, 3]
    lang: Literal["en", "hi", "mr", "es"] = "en"


class PracticeGenIn(BaseModel):
    misconception_id: str = Field(max_length=40)
    count: int = Field(default=2, ge=1, le=3)


class PracticeCheckIn(BaseModel):
    template_id: str = Field(max_length=40)
    prompt_ascii: str = Field(max_length=120)
    answer_ascii: str = Field(max_length=60)


class ClassIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class EventIn(BaseModel):
    misconception_id: str = Field(max_length=40)
    topic: str = Field(default="algebra", max_length=40)


# ---------- helpers ----------


def _verify(body: VerifyIn) -> VerifyResult:
    try:
        return verify_lines(body.problem, [ln.ascii for ln in body.lines])
    except ParseError as e:
        raise APIError(422, e.code, e.reason) from None


def _prev_index(res: VerifyResult, i: int):
    for j in range(i - 1, -1, -1):
        if res.parsed[j] is not None:
            return res.parsed[j]
    return res.base if res.base is not res.parsed[i] else None


def _diagnosis(res: VerifyResult) -> tuple[Diagnosis | None, bool]:
    """(diagnosis, offline). Deterministic rules first; the LLM only as a labelled fallback."""
    i = res.first_error_index
    if i is None:
        return None, False
    if res.lines[i].detail == "keeps_extraneous":
        return Diagnosis("EXTRANEOUS_ROOT", "verified"), False
    curr, prev = res.parsed[i], _prev_index(res, i)
    if curr is None or prev is None:
        return None, False
    d = diagnose(prev, curr)
    if d is not None:
        return d, False
    if not ai.available():
        return None, True
    try:
        h = ai.hypothesize(prev.text, curr.text)
    except ai.AIUnavailable:
        return None, True
    except ai.AIBadOutput:
        return None, False
    return Diagnosis(h["id"], "ai_hypothesis", rationale=h["rationale"]), False


def _misconception_json(d: Diagnosis | None):
    if d is None:
        return None
    e = entry(d.id)
    return {
        "id": d.id,
        "name": e["name"],
        "description": e["description"],
        "concept": e["concept"],
        "evidence": d.evidence,
        "rationale": d.rationale,
        "focus": d.focus,
        "practice": d.id in practice.TEMPLATES,
    }


# ---------- routes ----------


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": __version__,
        "model": ai.MODEL,
        "ai": "ok" if ai.available() else "disabled",
        "db": db.health(),
    }


@app.post("/api/transcribe")
def transcribe(body: TranscribeIn):
    try:
        raw = base64.b64decode(body.image_base64.split(",")[-1], validate=True)
    except (binascii.Error, ValueError):
        raise APIError(415, "image_invalid", "That file isn't a readable image.") from None
    if len(raw) > MAX_IMAGE:
        raise APIError(413, "image_invalid", "Use a JPG/PNG under 4 MB.")
    if not (raw[:3] == b"\xff\xd8\xff" or raw[:8] == b"\x89PNG\r\n\x1a\n" or raw[8:12] == b"WEBP"):
        raise APIError(415, "image_invalid", "Use a JPG, PNG or WebP photo.")
    if not ai.available():
        raise APIError(503, "ai_unavailable", "Handwriting reading is unavailable right now. Type your steps instead.")
    out = None
    for attempt in range(2):
        try:
            out = ai.transcribe(raw, body.mime)
            break
        except ai.AIUnavailable:
            raise APIError(
                503, "ai_unavailable", "Handwriting reading is unavailable right now. Type your steps instead."
            ) from None
        except ai.AIBadOutput:
            if attempt:
                raise APIError(502, "ai_bad_output", "Couldn't read that photo. Try again or type your steps.") from None

    texts = [normalize(str(ln.get("ascii", ""))) for ln in out["lines"]]
    try:
        var = detect_variable(texts)
    except ParseError:
        var = None
    lines = []
    for ln, text in zip(out["lines"], texts, strict=True):
        if not text or len(lines) >= 20:
            continue
        box = [min(1000, max(0, int(v))) / 1000 for v in (ln.get("box_2d") or [])[:4]]
        if len(box) != 4 or box[0] >= box[2] or box[1] >= box[3]:
            box = None
        item = {
            "id": f"l{len(lines) + 1}",
            "ascii": text[:160],
            "box": box,
            "confidence": ln.get("confidence", "medium"),
            "parse_ok": True,
        }
        try:
            parse_line(text, var)
        except ParseError as e:
            item.update(parse_ok=False, parse_error=e.reason)
        lines.append(item)
    for item, snapped in zip(lines, boxes.snap(raw, [ln["box"] for ln in lines]), strict=True):
        item["box"] = snapped
    problem = out.get("problem")
    return {
        "problem": normalize(problem)[:160] if problem else None,
        "variable": var or "x",
        "lines": lines,
        "notes": out.get("notes"),
    }


@app.post("/api/verify")
def verify(body: VerifyIn):
    res = _verify(body)
    d, offline = _diagnosis(res)
    ids = [ln.id for ln in body.lines]
    return {
        "variable": res.variable,
        "lines": [{"id": ids[i], "status": r.status, "detail": r.detail} for i, r in enumerate(res.lines)],
        "first_error_id": ids[res.first_error_index] if res.first_error_index is not None else None,
        "final_correct": res.final_correct,
        "misconception": _misconception_json(d),
        "scope_ok": res.scope_ok,
        "offline": offline,
    }


def _template_hint(mid: str, level: int, line_no: int, focus: str | None, example: dict | None) -> str:
    e = entry(mid)
    if level == 3:
        if example:
            return (
                f"Here's the same kind of slip in a different problem. In `{example['problem']}`, writing "
                f"`{example['wrong']}` is the mistake; the correct step is `{example['right']}`, because "
                f"{example['note']}. Now look at line {line_no} again with that in mind."
            )
        return f"{e['concept']} Now apply that idea to line {line_no} yourself."
    return e["hints"][level].format(line=line_no, focus=f"`{focus}`" if focus else "that part")


@app.post("/api/hint")
def hint(body: HintIn):
    if body.misconception_id not in CATALOG and body.misconception_id != "OTHER":
        raise APIError(422, "unknown_misconception", "Unknown misconception id.")
    res = _verify(body)
    ids = [ln.id for ln in body.lines]
    if body.error_line_id not in ids:
        raise APIError(422, "invalid_request", "error_line_id is not one of the lines.")
    i = ids.index(body.error_line_id)
    curr, prev = res.parsed[i], _prev_index(res, i)
    d = diagnose(prev, curr) if (curr is not None and prev is not None) else None
    focus = d.focus if d and d.id == body.misconception_id else None
    fragment = d.correct_fragment if d and d.id == body.misconception_id else None
    mid = body.misconception_id
    roots = set(res.correct_set) if res.correct_set is not None and res.correct_set.is_FiniteSet else set()
    example = None
    if body.level == 3 and mid in practice.TEMPLATES:
        example = practice.parallel_example(mid, roots, " ".join(ln.ascii for ln in body.lines) + (body.problem or ""))
    e = entry(mid)
    facts = {
        "line_number": i + 1,
        "previous_line": prev.text if prev else None,
        "learner_line": body.lines[i].ascii,
        "misconception": {"name": e["name"], "description": e["description"], "concept": e["concept"]},
        "focus_in_previous_line": focus,
    }
    if example:
        facts["worked_example_with_different_numbers"] = example

    regenerated = False
    text, source = None, "template"
    if ai.available():
        for strict in (False, True):
            try:
                draft = ai.hint(body.level, facts, body.lang, strict=strict)
            except (ai.AIUnavailable, ai.AIBadOutput):
                break
            if guard.check(draft, res.variable, res.correct_set, fragment):
                text, source = draft, "ai"
                break
            regenerated = True
            log.info(json.dumps({"event": "guard_blocked", "level": body.level, "strict": strict}))
    if text is None:
        text = _template_hint(mid, body.level, i + 1, focus, example)
        if not guard.check(text, res.variable, res.correct_set, fragment):  # templates are tested; belt and braces
            text = f"Look closely at line {i + 1} and compare it with the line before, one term at a time."
    return {
        "text": text,
        "level": body.level,
        "source": source,
        "guard": {"passed": True, "regenerated": regenerated},
        "example": example,
    }


@app.post("/api/practice/generate")
def practice_generate(body: PracticeGenIn):
    if body.misconception_id not in practice.TEMPLATES:
        raise APIError(404, "unknown_misconception", "No practice set for this misconception.")
    return {"problems": practice.generate(body.misconception_id, body.count)}


@app.post("/api/practice/check")
def practice_check(body: PracticeCheckIn):
    if body.template_id not in practice.TEMPLATES:
        raise APIError(404, "unknown_misconception", "Unknown practice template.")
    try:
        ok = practice.check(body.prompt_ascii, body.answer_ascii)
    except ParseError as e:
        return {"correct": False, "feedback_code": "unreadable", "message": e.reason}
    return {"correct": ok, "feedback_code": "correct" if ok else "incorrect"}


_CODE = re.compile(r"^[A-Z2-9]{6}$")


def _db(fn, *args):
    try:
        return fn(*args)
    except db.DBUnavailable:
        raise APIError(503, "db_unavailable", "Class mode is unavailable right now.") from None


@app.post("/api/class")
def create_class(body: ClassIn):
    code = _db(db.create_class, body.name.strip())
    return {"code": code, "dashboard_path": f"/class/{code}"}


@app.post("/api/class/{code}/events")
def class_event(code: str, body: EventIn):
    code = code.upper()
    if not _CODE.match(code):
        raise APIError(404, "class_not_found", "No class with that code.")
    if body.misconception_id not in CATALOG:
        raise APIError(422, "unknown_misconception", "Unknown misconception id.")
    if not _db(db.add_event, code, body.misconception_id, body.topic):
        raise APIError(404, "class_not_found", "No class with that code.")
    return {"ok": True}


@app.get("/api/class/{code}/summary")
def class_summary(code: str):
    code = code.upper()
    name = _db(db.class_name, code) if _CODE.match(code) else None
    if name is None:
        raise APIError(404, "class_not_found", "No class with that code.")
    total, rows = _db(db.summary, code)
    counts = [{"misconception_id": m, "name": entry(m)["name"], "count": n} for m, n in rows]
    suggestions = [
        {"misconception_id": c["misconception_id"], "name": c["name"], "concept": entry(c["misconception_id"])["concept"]}
        for c in counts[:3]
    ]
    return {"name": name, "total": total, "window_days": 14, "counts": counts, "suggestions": suggestions}


@app.api_route("/api/{rest:path}", methods=["GET", "POST"])
def api_not_found(rest: str):
    raise APIError(404, "not_found", "Unknown API route.")


# ---------- static web app (single-service deploys) ----------

STATIC = Path(os.getenv("STATIC_DIR", Path(__file__).resolve().parent.parent / "web" / "dist"))

if STATIC.is_dir():

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = (STATIC / path).resolve()
        if path and f.is_file() and STATIC.resolve() in f.parents:
            headers = {"Cache-Control": "public, max-age=31536000, immutable"} if path.startswith("assets/") else {}
            return FileResponse(f, headers=headers)
        return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})
