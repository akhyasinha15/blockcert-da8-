#!/usr/bin/env python3
"""Render captured transcript text (docs/transcript/*.txt) as dark terminal-style PNGs.

The images contain exactly the text that was printed by the real run - nothing is edited
except line-wrapping and syntax colouring. Used to produce report figures.
"""
import re
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
BG, FG = (31, 33, 51), (216, 219, 232)
COL = {
    "prompt": (127, 184, 255),
    "ok": (95, 211, 141),
    "bad": (255, 107, 107),
    "event": (230, 192, 123),
    "note": (138, 147, 184),
    "bar": (42, 45, 68),
}
WRAP = 108
SCALE = 2
FS = 13 * SCALE


def colour(line: str):
    s = line.strip()
    if s.startswith("$"):
        return COL["prompt"]
    if s.startswith("#") or s.startswith("^"):
        return COL["note"]
    if "REVERTED" in s or s in ("false",) or s.startswith("reason"):
        return COL["bad"]
    if "SUCCESS" in s or s == "true":
        return COL["ok"]
    if s.startswith("event") or s.startswith("TamperAlert") or s.startswith("message"):
        return COL["event"]
    return FG


def render(lines, title, out: Path):
    font = ImageFont.truetype(FONT, FS)
    wrapped = []
    for ln in lines:
        indent = len(ln) - len(ln.lstrip())
        parts = textwrap.wrap(ln, WRAP, subsequent_indent=" " * (indent + 6), break_long_words=True,
                              drop_whitespace=False, replace_whitespace=False) or [""]
        c = colour(ln)
        for p in parts:
            wrapped.append((p, c))
    cw = font.getlength("M")
    lh = int(FS * 1.35)
    pad = 18 * SCALE
    bar = 26 * SCALE
    w = int(cw * WRAP + pad * 2 + cw * 2)
    h = bar + pad + lh * len(wrapped) + pad
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, bar], fill=COL["bar"])
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        r = 5 * SCALE
        cx = pad + i * 16 * SCALE
        d.ellipse([cx - r, bar // 2 - r, cx + r, bar // 2 + r], fill=c)
    tf = ImageFont.truetype(FONT, 11 * SCALE)
    d.text((w // 2, bar // 2), title, fill=COL["note"], font=tf, anchor="mm")
    y = bar + pad
    for text, c in wrapped:
        d.text((pad, y), text, fill=c, font=font)
        y += lh
    img.save(out)
    return img.size


if __name__ == "__main__":
    src, title, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    start = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    end = int(sys.argv[5]) if len(sys.argv) > 5 else None
    text = src.read_text().splitlines()
    text = [l for l in text if not l.startswith("# Step")]
    print(render(text[start:end], title, out))
