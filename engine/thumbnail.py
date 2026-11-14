"""Thumbnail: scene backdrop, big title, and the first character reacting."""
import math

from PIL import Image

from engine import face as F
from engine import library as lib
from engine import overlay
from engine.character import Appearance, draw_character
from engine.draw import Layer
from engine.skeleton import fk, lowest
from pipeline import scenes


def make_thumbnail(title, path, scene="void", appearance=None, size=(1280, 720)):
    from PIL import ImageDraw
    W, H = size
    img = scenes.background(scene, size).copy()
    d = ImageDraw.Draw(img)
    fs = 110
    while fs > 40:
        lines = overlay.wrap(d, title.upper(), overlay.font(fs), W * 0.58)
        if len(lines) <= 4 and len(lines) * fs * 1.15 < H * 0.8:
            break
        fs -= 6
    y = (H - len(lines) * fs * 1.15) / 2
    for i, ln in enumerate(lines):
        d.text((W * 0.05, y), ln, font=overlay.font(fs), fill=(255, 196, 61) if i == 0 else (240, 236, 226), anchor="la",
               stroke_width=7, stroke_fill=(18, 21, 31))
        y += fs * 1.15
    app = appearance or Appearance()
    u = 0.095 * H
    pose = lib.named_pose("point_up", 0.0)
    P, _ = fk(pose, u, 35, app.build)
    gy = scenes.ground_y(size)
    root = (W * 0.76, gy - lowest(P, u, app.build.get("head", 1.0)))
    L = Layer(img, (W * 0.5, 0, W, H), 2)
    draw_character(L, pose, app, root, u, 35, F.expression("surprise"))
    L.finish()
    overlay.draw_icon(ImageDraw.Draw(img), "question", W * 0.76 + 2.6 * u, gy - 6.6 * u, u)
    img.save(path)
    return path
