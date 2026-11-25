"""Snap the model's line boxes to the actual ink rows in the photo.

Vision models place boxes approximately; a box half a line off puts the red underline
on the wrong handwriting. This is deterministic image processing: per box, project dark
pixels onto rows within the box's horizontal span, find ink bands, and move the box to
the nearest unused band (top to bottom), tightening x to the ink in that band.
"""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps

WORK_W = 600  # analysis width; boxes are fractions so resolution doesn't matter


def _ink_mask(img: Image.Image):
    g = ImageOps.grayscale(img)
    if g.width > WORK_W:
        g = g.resize((WORK_W, max(1, round(g.height * WORK_W / g.width))))
    px = g.load()
    w, h = g.size
    hist, seen, paper = g.histogram(), 0, 255
    for level, n in enumerate(hist):  # median brightness ≈ the paper
        seen += n
        if seen >= w * h / 2:
            paper = level
            break
    cut = paper - 70  # ruled lines and margins are light; pen ink is much darker
    return [[px[x, y] < cut for x in range(w)] for y in range(h)], w, h


def _bands(rows: list[int], h: int) -> list[tuple[int, int]]:
    if not rows or max(rows) == 0:
        return []
    thr = max(2, 0.12 * max(rows))
    out, start = [], None
    for y, c in enumerate(rows + [0]):
        if c >= thr and start is None:
            start = y
        elif c < thr and start is not None:
            out.append([start, y - 1])
            start = None
    merged: list[list[int]] = []
    gap = max(2, round(0.012 * h))  # join superscripts / dots to their line
    for b in out:
        if merged and b[0] - merged[-1][1] <= gap:
            merged[-1][1] = b[1]
        else:
            merged.append(b)
    return [(a, b) for a, b in merged if b - a >= max(3, round(0.012 * h))]


def snap(image_bytes: bytes, boxes: list[list[float] | None]) -> list[list[float] | None]:
    try:
        img = Image.open(BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)
        mask, w, h = _ink_mask(img)
    except Exception:  # noqa: BLE001 - never fail a transcription over box polish
        return boxes
    out: list[list[float] | None] = []
    floor = -1  # each line must sit below the previous one
    for box in boxes:
        if not box:
            out.append(box)
            continue
        y0, x0, y1, x1 = box
        pad = 0.04
        cx0, cx1 = max(0, int((x0 - pad) * w)), min(w, int((x1 + pad) * w) + 1)
        rows = [sum(r[cx0:cx1]) for r in mask]
        center, height = (y0 + y1) / 2 * h, max(1.0, (y1 - y0) * h)
        cands = [b for b in _bands(rows, h) if b[0] > floor and abs((b[0] + b[1]) / 2 - center) <= 1.6 * height]
        if not cands:
            out.append(box)
            continue
        a, b = min(cands, key=lambda b: abs((b[0] + b[1]) / 2 - center))
        cols = [x for x in range(cx0, cx1) if any(mask[y][x] for y in range(a, b + 1))]
        nx0, nx1 = (cols[0] / w, (cols[-1] + 1) / w) if cols else (x0, x1)
        out.append([round(a / h, 4), round(nx0, 4), round((b + 1) / h, 4), round(nx1, 4)])
        floor = b
    return out
