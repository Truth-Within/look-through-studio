"""Screen-space text and icons (headline, captions, thought icons)."""
import math
from functools import lru_cache

from PIL import ImageFont

from config import ACCENT, BG, INK

_FONTS = ["DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
          "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


@lru_cache(maxsize=None)
def font(size):
    for name in _FONTS:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def wrap(d, text, fnt, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if not cur or d.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def text_overlay(d, size, headline, caption):
    W, H = size
    m = min(W, H)
    hs = int(0.075 * m)
    y = H * 0.05
    for ln in wrap(d, headline.upper(), font(hs), W * 0.9)[:2]:
        d.text((W / 2, y), ln, font=font(hs), fill=ACCENT, anchor="ma", stroke_width=4, stroke_fill=BG)
        y += hs * 1.2
    cs = int(0.045 * m)
    lines = wrap(d, caption, font(cs), W * 0.9)
    lh = cs * 1.3
    y = H * 0.96 - len(lines) * lh
    for ln in lines:
        d.text((W / 2, y), ln, font=font(cs), fill=INK, anchor="ma", stroke_width=3, stroke_fill=BG)
        y += lh


def draw_icon(d, kind, x, y, u, t=0.0):
    w = max(5, int(u * 0.12))
    pulse = 1 + 0.06 * math.sin(t * 2 * math.pi * 1.2)
    if kind == "question":
        d.text((x, y), "?", font=font(int(u * 3.0 * pulse)), fill=ACCENT, anchor="mm", stroke_width=3, stroke_fill=BG)
    elif kind == "exclaim":
        d.text((x, y), "!", font=font(int(u * 3.0 * pulse)), fill=ACCENT, anchor="mm", stroke_width=3, stroke_fill=BG)
    elif kind == "lightbulb":
        r = u * 0.8 * pulse
        d.ellipse([x - r, y - r, x + r, y + r], outline=ACCENT, width=w)
        d.rectangle([x - r * 0.45, y + r, x + r * 0.45, y + r * 1.5], outline=ACCENT, width=w)
        for deg in (200, 235, 270, 305, 340):
            a = math.radians(deg)
            d.line([x + math.cos(a) * r * 1.3, y + math.sin(a) * r * 1.3, x + math.cos(a) * r * 1.8, y + math.sin(a) * r * 1.8],
                   fill=ACCENT, width=w)
    elif kind == "heart":
        r = u * 0.5 * pulse
        d.ellipse([x - 2 * r * 0.55 - r * 0.5, y - r, x - r * 0.05, y + r * 0.1], fill=(230, 70, 90))
        d.ellipse([x + r * 0.05, y - r, x + 2 * r * 0.55 + r * 0.5, y + r * 0.1], fill=(230, 70, 90))
        d.polygon([(x - r * 1.05, y - r * 0.15), (x + r * 1.05, y - r * 0.15), (x, y + r * 1.2)], fill=(230, 70, 90))
