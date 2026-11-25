"""Render the synthetic sample worksheets.

These are NOT real handwriting: they are drawn with OFL handwriting fonts (Caveat,
Kalam) on a lined-paper background with per-line jitter, so the demo has reliable
inputs. They go through the real transcription pipeline like any photo.
Real handwritten photos belong in eval/photos/ (see eval/photos/README.md).

    python eval/make_samples.py   ->  web/public/samples/*.jpg + samples.json
"""

import json
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "public" / "samples"
FONTS = ROOT / "eval" / "fonts"

SAMPLES = [
    {
        "id": "negative-bracket",
        "title": "Linear · brackets",
        "font": "Caveat.ttf",
        "problem": "Solve  5 - 2(x - 3) = 1",
        "lines": ["5 - 2(x - 3) = 1", "5 - 2x - 6 = 1", "-2x - 1 = 1", "-2x = 2", "x = -1"],
        "expect": {"first_error": 1, "misconception": "NEG_DIST_FIRST_ONLY"},
    },
    {
        "id": "moving-terms",
        "title": "Linear · both sides",
        "font": "Kalam-Regular.ttf",
        "problem": "Solve  7x - 4 = 3x + 12",
        "lines": ["7x - 4 = 3x + 12", "7x - 3x = 12 - 4", "4x = 8", "x = 2"],
        "expect": {"first_error": 1, "misconception": "MOVE_NO_SIGN_FLIP"},
    },
    {
        "id": "square-root",
        "title": "Quadratic · square root",
        "font": "Caveat.ttf",
        "problem": "Solve  (x - 2)^2 = 9",
        "lines": ["(x - 2)^2 = 9", "x - 2 = 3", "x = 5"],
        "expect": {"first_error": 1, "misconception": "SQRT_LOST_NEG_ROOT"},
    },
]


def draw_math(d: ImageDraw.ImageDraw, x: float, y: float, text: str, font, small, ink):
    """Draw text, rendering ^n as a raised superscript like handwriting."""
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "^" and i + 1 < len(text):
            d.text((x, y - font.size * 0.28), text[i + 1], font=small, fill=ink)
            x += d.textlength(text[i + 1], font=small) + 2
            i += 2
            continue
        d.text((x, y), ch, font=font, fill=ink)
        x += d.textlength(ch, font=font)
        i += 1


def render(sample: dict, rng: random.Random) -> Image.Image:
    w, h = 1200, 300 + 130 * len(sample["lines"])
    img = Image.new("RGB", (w, h), (250, 247, 240))
    d = ImageDraw.Draw(img)
    for yy in range(140, h, 65):
        d.line([(0, yy), (w, yy)], fill=(198, 214, 232), width=2)
    d.line([(110, 0), (110, h)], fill=(232, 170, 170), width=2)
    font = ImageFont.truetype(str(FONTS / sample["font"]), 84)
    small = ImageFont.truetype(str(FONTS / sample["font"]), 54)
    head = ImageFont.truetype(str(FONTS / sample["font"]), 64)
    ink = (28, 42, 110)
    draw_math(d, 150, 40, sample["problem"], head, small, ink)
    y = 175
    for line in sample["lines"]:
        layer = Image.new("RGBA", (w, 160), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        draw_math(ld, 10, 30, line, font, small, ink + (255,))
        layer = layer.rotate(rng.uniform(-1.2, 1.2), resample=Image.BICUBIC)
        img.paste(layer, (150 + rng.randint(-8, 22), y - 40), layer)
        y += 130
    img = img.rotate(rng.uniform(-0.8, 0.8), resample=Image.BICUBIC, fillcolor=(250, 247, 240))
    return img.filter(ImageFilter.GaussianBlur(0.6))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(29)
    meta = []
    for s in SAMPLES:
        render(s, rng).save(OUT / f"{s['id']}.jpg", quality=88)
        meta.append({k: s[k] for k in ("id", "title", "problem", "lines", "expect")} | {"image": f"/samples/{s['id']}.jpg"})
    (OUT / "samples.json").write_text(json.dumps(meta, indent=2))
    print(f"wrote {len(meta)} samples to {OUT}")


if __name__ == "__main__":
    main()
