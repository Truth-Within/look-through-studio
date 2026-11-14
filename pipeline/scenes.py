"""Flat 2D background scenes. Static art is cached per (scene, size); a few scenes animate."""
import math
import random
from functools import lru_cache

from PIL import Image, ImageDraw

from config import BG, MUTED

SCENES = ["void", "room", "night_sky", "city", "forest", "mountains", "ocean", "desert",
          "space", "library", "cave", "temple", "mind", "sunrise"]

SCENE_GUIDE = (
    "void=plain dark (abstract ideas); room=cosy bedroom (personal, everyday life); "
    "night_sky=moon and stars (wonder, sleep, mystery); city=night skyline (society, modern life); "
    "forest=pine forest (nature, instinct, fear); mountains=sunset peaks (challenge, journey); "
    "ocean=sea and beach (depth, calm); desert=dunes and pyramids (ancient history); "
    "space=planets (cosmos, science); library=bookshelves (knowledge, study); "
    "cave=crystals (hidden, unconscious); temple=columns (philosophy, antiquity, ritual); "
    "mind=neural network (psychology, thoughts); sunrise=hills at dawn (hope, endings)"
)


def ground_y(size):
    W, H = size
    return H * (0.78 if W > H else 0.68)


def _mix(c1, c2, k):
    return tuple(int(a + (b - a) * k) for a, b in zip(c1, c2))


def _grad(d, W, y0, y1, c0, c1):
    y0, y1 = int(y0), int(y1)
    for y in range(y0, y1):
        d.line([(0, y), (W, y)], fill=_mix(c0, c1, (y - y0) / max(1, y1 - y0 - 1)))


def _circle(d, x, y, r, fill):
    d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def _hills(d, W, gy, base, amp, color, ph, freq=0.006):
    pts = [(0, gy)] + [(x, base - amp * (0.5 + 0.5 * math.sin(x * freq + ph)) - 0.3 * amp * math.sin(x * freq * 2.7 + ph))
                       for x in range(0, W + 16, 16)] + [(W, gy)]
    d.polygon(pts, fill=color)


def _peaks(d, W, gy, base, amp, color, r):
    pts, x = [(0, gy), (0, base)], 0
    while x < W + 80:
        x += r.randint(60, 140)
        pts.append((x, base - amp * (0.35 + 0.65 * r.random())))
        x += r.randint(40, 100)
        pts.append((x, base - amp * 0.1 * r.random()))
    pts.append((x, gy))
    d.polygon(pts, fill=color)


def _pines(d, W, gy, base, hmin, hmax, color, r):
    x = -30
    while x < W + 30:
        w, h = r.randint(50, 90), r.randint(hmin, hmax)
        cx = x + w / 2
        d.rectangle([cx - 4, base - 12, cx + 4, base + 4], fill=color)
        for i in range(3):
            top = base - h + i * h * 0.25
            half = w * (0.30 + 0.10 * i)
            d.polygon([(cx, top), (cx - half, top + h * 0.45), (cx + half, top + h * 0.45)], fill=color)
        x += r.randint(30, 70)
    d.rectangle([0, base, W, gy], fill=color)


# ------------------------------------------------------------------ scenes
def s_void(d, W, H, gy, r):
    d.rectangle([0, 0, W, H], fill=BG)
    d.line([(W * 0.12, gy), (W * 0.88, gy)], fill=MUTED, width=4)


def s_room(d, W, H, gy, r):
    d.rectangle([0, 0, W, gy], fill=(40, 46, 72))
    d.rectangle([0, gy, W, H], fill=(28, 31, 48))
    d.rectangle([0, gy - 10, W, gy], fill=(62, 68, 98))
    wx, wy, ww, wh = W * 0.70, H * 0.10, W * 0.20, H * 0.34
    d.rectangle([wx, wy, wx + ww, wy + wh], fill=(18, 26, 58), outline=(96, 104, 138), width=6)
    d.line([(wx + ww / 2, wy), (wx + ww / 2, wy + wh)], fill=(96, 104, 138), width=5)
    d.line([(wx, wy + wh / 2), (wx + ww, wy + wh / 2)], fill=(96, 104, 138), width=5)
    _circle(d, wx + ww * 0.28, wy + wh * 0.28, ww * 0.07, (240, 235, 200))
    fx, fy, fw, fh = W * 0.07, H * 0.13, W * 0.13, H * 0.22
    d.rectangle([fx, fy, fx + fw, fy + fh], fill=(54, 62, 96), outline=(130, 106, 72), width=7)
    d.polygon([(fx + fw * 0.1, fy + fh * 0.85), (fx + fw * 0.45, fy + fh * 0.4), (fx + fw * 0.9, fy + fh * 0.85)], fill=(80, 96, 140))
    d.ellipse([W * 0.16, gy - H * 0.03, W * 0.68, gy + H * 0.07], fill=(48, 42, 78))


def s_night_sky(d, W, H, gy, r):
    _grad(d, W, 0, gy, (8, 10, 32), (46, 32, 86))
    _circle(d, W * 0.78, H * 0.2, H * 0.07, (240, 235, 200))
    _circle(d, W * 0.78 + H * 0.025, H * 0.2 - H * 0.015, H * 0.06, (22, 20, 56))
    _hills(d, W, gy, gy - H * 0.04, H * 0.12, (20, 22, 48), 1.0)
    d.rectangle([0, gy, W, H], fill=(14, 16, 30))


def s_city(d, W, H, gy, r):
    _grad(d, W, 0, gy, (18, 20, 48), (88, 58, 98))
    for col, wcol, hmax, lit in (((30, 32, 62), (78, 78, 120), 0.5, 0.25), ((20, 22, 44), (255, 214, 120), 0.36, 0.4)):
        x = -20
        while x < W:
            bw, bh = r.randint(60, 130), int(H * r.uniform(0.15, hmax))
            d.rectangle([x, gy - bh, x + bw, gy], fill=col)
            for wy in range(int(gy - bh + 14), int(gy - 10), 26):
                for wx in range(x + 10, x + bw - 14, 22):
                    if r.random() < lit:
                        d.rectangle([wx, wy, wx + 9, wy + 13], fill=wcol)
            x += bw + r.randint(0, 14)
    d.rectangle([0, gy, W, H], fill=(26, 28, 40))
    for x in range(0, W, 90):
        d.rectangle([x, gy + H * 0.07, x + 44, gy + H * 0.07 + 5], fill=(120, 120, 92))


def s_forest(d, W, H, gy, r):
    _grad(d, W, 0, gy, (22, 44, 58), (74, 112, 104))
    _circle(d, W * 0.75, H * 0.16, H * 0.05, (214, 224, 200))
    _pines(d, W, gy, gy - H * 0.04, int(H * 0.30), int(H * 0.42), (30, 66, 64), r)
    _pines(d, W, gy, gy + H * 0.0, int(H * 0.22), int(H * 0.34), (22, 50, 50), r)
    d.rectangle([0, gy, W, H], fill=(20, 36, 34))


def s_mountains(d, W, H, gy, r):
    _grad(d, W, 0, gy, (50, 60, 112), (238, 150, 112))
    _circle(d, W * 0.70, gy - H * 0.26, H * 0.07, (255, 224, 164))
    _peaks(d, W, gy, gy - H * 0.10, H * 0.42, (118, 100, 150), r)
    _peaks(d, W, gy, gy - H * 0.02, H * 0.32, (76, 74, 124), r)
    _peaks(d, W, gy, gy + H * 0.0, H * 0.18, (46, 50, 86), r)
    d.rectangle([0, gy, W, H], fill=(30, 34, 54))


def s_ocean(d, W, H, gy, r):
    hy = gy - H * 0.28
    _grad(d, W, 0, hy, (30, 60, 112), (152, 192, 216))
    _grad(d, W, hy, gy, (30, 88, 142), (18, 58, 108))
    _circle(d, W * 0.72, hy - H * 0.07, H * 0.06, (255, 236, 192))
    for i in range(7):
        y = hy + 6 + i * 12
        d.line([(W * 0.72 - (40 - i * 4), y), (W * 0.72 + (40 - i * 4), y)], fill=(255, 236, 192), width=4)
    d.rectangle([0, gy, W, H], fill=(124, 106, 82))
    d.line([(0, gy), (W, gy)], fill=(190, 210, 224), width=5)


def s_desert(d, W, H, gy, r):
    _grad(d, W, 0, gy, (58, 56, 118), (240, 172, 112))
    _circle(d, W * 0.22, gy - H * 0.30, H * 0.07, (255, 226, 172))
    for px, s in ((W * 0.62, 1.0), (W * 0.80, 0.7), (W * 0.48, 0.5)):
        d.polygon([(px - H * 0.22 * s, gy - H * 0.04), (px, gy - H * 0.04 - H * 0.26 * s), (px + H * 0.22 * s, gy - H * 0.04)], fill=(150, 100, 92))
    _hills(d, W, gy, gy - H * 0.02, H * 0.07, (196, 134, 84), 0.5, 0.004)
    d.rectangle([0, gy, W, H], fill=(158, 110, 70))


def s_space(d, W, H, gy, r):
    d.rectangle([0, 0, W, H], fill=(6, 8, 22))
    px, py, pr = W * 0.78, H * 0.28, H * 0.15
    _circle(d, px, py, pr, (116, 78, 148))
    d.ellipse([px - pr * 1.6, py - pr * 0.3, px + pr * 1.6, py + pr * 0.3], outline=(200, 170, 220), width=6)
    _circle(d, px, py, pr * 0.0 + 1, (116, 78, 148))
    _circle(d, W * 0.12, H * 0.2, H * 0.03, (170, 170, 190))
    d.rectangle([0, gy, W, H], fill=(38, 40, 60))
    for _ in range(7):
        cx, cy, cr = r.randint(0, W), r.randint(int(gy + 10), H - 10), r.randint(20, 60)
        d.ellipse([cx - cr, cy - cr * 0.3, cx + cr, cy + cr * 0.3], fill=(26, 28, 46))


def s_library(d, W, H, gy, r):
    d.rectangle([0, 0, W, gy], fill=(58, 42, 36))
    shelf_h = int(H * 0.15)
    palette = [(120, 60, 60), (70, 90, 130), (90, 120, 80), (150, 120, 70), (100, 70, 120), (60, 100, 110)]
    for sy in range(int(H * 0.04), int(gy - shelf_h * 0.8), int(H * 0.19)):
        x = 0
        while x < W:
            bw, bh = r.randint(16, 34), int(shelf_h * r.uniform(0.6, 0.95))
            d.rectangle([x, sy + shelf_h - bh, x + bw, sy + shelf_h], fill=r.choice(palette))
            x += bw + 2
        d.rectangle([0, sy + shelf_h, W, sy + shelf_h + 9], fill=(92, 62, 44))
    d.rectangle([0, gy, W, H], fill=(44, 30, 26))
    for y in range(int(gy + 20), H, 34):
        d.line([(0, y), (W, y)], fill=(36, 24, 20), width=3)


def s_cave(d, W, H, gy, r):
    d.rectangle([0, 0, W, H], fill=(20, 17, 28))
    x = -20
    while x < W:
        w, h = r.randint(40, 100), r.randint(int(H * 0.08), int(H * 0.28))
        d.polygon([(x, 0), (x + w, 0), (x + w / 2, h)], fill=(34, 28, 44))
        x += w - r.randint(0, 20)
    d.rectangle([0, gy, W, H], fill=(36, 30, 46))
    x = 0
    while x < W:
        w, h = r.randint(30, 70), r.randint(int(H * 0.03), int(H * 0.12))
        d.polygon([(x, gy), (x + w, gy), (x + w / 2, gy - h)], fill=(36, 30, 46))
        x += w + r.randint(20, 80)
    for cx, col in ((W * 0.12, (88, 200, 220)), (W * 0.86, (210, 100, 190)), (W * 0.93, (88, 200, 220))):
        d.polygon([(cx - 14, gy), (cx, gy - H * 0.14), (cx + 14, gy)], fill=col)
        d.polygon([(cx + 10, gy), (cx + 26, gy - H * 0.08), (cx + 40, gy)], fill=col)


def s_temple(d, W, H, gy, r):
    _grad(d, W, 0, gy, (46, 36, 84), (210, 140, 128))
    _circle(d, W * 0.5, gy - H * 0.10, H * 0.09, (250, 206, 150))
    stone, shade = (168, 158, 156), (128, 120, 122)
    top, step = H * 0.20, H * 0.05
    d.rectangle([W * 0.02, top - H * 0.05, W * 0.98, top], fill=stone)
    d.polygon([(W * 0.02, top - H * 0.05), (W * 0.5, top - H * 0.17), (W * 0.98, top - H * 0.05)], fill=shade)
    cw = W * 0.05
    for i in range(5):
        x = W * (0.10 + 0.18 * i)
        d.rectangle([x, top, x + cw, gy - step * 2], fill=stone)
        d.rectangle([x + cw * 0.65, top, x + cw, gy - step * 2], fill=shade)
        d.rectangle([x - cw * 0.2, top, x + cw * 1.2, top + H * 0.02], fill=stone)
        d.rectangle([x - cw * 0.2, gy - step * 2 - H * 0.02, x + cw * 1.2, gy - step * 2], fill=stone)
    d.rectangle([W * 0.0, gy - step * 2, W, gy - step], fill=(120, 112, 118))
    d.rectangle([0, gy - step, W, gy], fill=(104, 96, 104))
    d.rectangle([0, gy, W, H], fill=(80, 72, 88))


def _nodes(W, H):
    r = random.Random("mind")
    return [(r.uniform(0.03, 0.97) * W, r.uniform(0.04, 0.72) * H, r.uniform(0, 6.28)) for _ in range(40)]


def s_mind(d, W, H, gy, r):
    _grad(d, W, 0, H, (14, 12, 38), (34, 20, 64))
    for k in range(1, 6):
        rad = H * 0.13 * k
        d.ellipse([W * 0.42 - rad, H * 0.40 - rad, W * 0.42 + rad, H * 0.40 + rad], outline=(40, 34, 86), width=3)
    nodes = _nodes(W, H)
    for i, (x1, y1, _) in enumerate(nodes):
        for x2, y2, _ in nodes[i + 1:]:
            if (x1 - x2) ** 2 + (y1 - y2) ** 2 < (0.2 * W) ** 2:
                d.line([(x1, y1), (x2, y2)], fill=(66, 56, 124), width=2)
    d.line([(W * 0.12, gy), (W * 0.88, gy)], fill=(100, 88, 160), width=4)


def s_sunrise(d, W, H, gy, r):
    _grad(d, W, 0, gy, (36, 44, 96), (250, 176, 120))
    _circle(d, W * 0.66, gy - H * 0.10, H * 0.12, (255, 214, 140))
    _hills(d, W, gy, gy - H * 0.06, H * 0.10, (96, 110, 126), 0.8)
    _hills(d, W, gy, gy - H * 0.02, H * 0.07, (62, 100, 86), 2.4, 0.008)
    d.rectangle([0, gy, W, H], fill=(46, 80, 64))


_BUILD = {n: globals()["s_" + n] for n in SCENES}
_CLOUDS = {"sunrise": (255, 214, 190), "mountains": (240, 180, 160), "ocean": (214, 228, 240), "desert": (255, 214, 170)}


@lru_cache(maxsize=32)
def background(scene, size):
    """Cached static background (treat as read-only; .copy() before drawing)."""
    W, H = size
    gy = int(ground_y(size))
    img = Image.new("RGB", size, BG)
    _BUILD.get(scene, s_void)(ImageDraw.Draw(img), W, H, gy, random.Random(scene))
    ov = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).rectangle([0, int(gy + H * 0.02), W, H], fill=(8, 10, 18, 120))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


@lru_cache(maxsize=8)
def _stars(scene, size):
    W, H = size
    r = random.Random("stars" + scene)
    return [(r.uniform(0, W), r.uniform(0, ground_y(size) * 0.92), r.uniform(1.5, 3.2), r.uniform(0, 6.28)) for _ in range(70)]


def animate(d, scene, size, t):
    """Per-frame moving details drawn over the cached background."""
    W, H = size
    gy = ground_y(size)
    if scene in ("night_sky", "space"):
        for x, y, rad, ph in _stars(scene, size):
            k = 0.5 + 0.5 * math.sin(t * 2.2 + ph)
            _circle(d, x, y, rad, _mix((50, 54, 90), (255, 255, 235), k))
    elif scene == "ocean":
        hy = gy - H * 0.28
        for i in range(10):
            y = hy + 14 + (i * 0.1) ** 1.3 * (gy - hy - 20)
            x = ((i * 137 + t * (18 + i * 3)) % (W + 160)) - 80
            d.line([(x, y), (x + 40 + i * 5, y)], fill=(200, 226, 240), width=3)
    elif scene == "mind":
        for x, y, ph in _nodes(W, H):
            _circle(d, x, y, 5 + 3 * math.sin(t * 2.5 + ph), (180, 160, 255))
    elif scene == "cave":
        for cx, col in ((W * 0.12, (88, 200, 220)), (W * 0.86, (210, 100, 190))):
            glow = 14 + 6 * math.sin(t * 2.0 + cx)
            d.ellipse([cx - glow, gy - H * 0.06 - glow, cx + glow, gy - H * 0.06 + glow], outline=col, width=3)
    if scene in _CLOUDS:
        for i, (cy, sc, sp) in enumerate(((0.12, 1.0, 10), (0.22, 0.7, 6), (0.08, 0.5, 14))):
            cx = ((i * 0.37 * W + t * sp) % (W + 400)) - 200
            y, w = H * cy, H * 0.07 * sc
            for dx, dr in ((-1.2, 0.8), (0, 1.1), (1.2, 0.8)):
                _circle(d, cx + dx * w, y, w * dr, _CLOUDS[scene])
