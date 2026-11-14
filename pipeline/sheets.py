"""Preview sheets: poses, facial expressions, outfits/views, and scenes."""
from PIL import Image, ImageDraw

import config
from config import BG, INK
from engine import face as F
from engine import library as lib
from engine import overlay
from engine.character import OUTFITS, Appearance, draw_character
from engine.draw import Layer
from engine.skeleton import fk, lowest
from pipeline import scenes

BASE = Appearance("hoodie", "short", "brown", "light", ["glasses"])


def _place(L, pose, app, cx, base_y, u, theta, face):
    P, _ = fk(pose, u, theta, app.build)
    draw_character(L, pose, app, (cx, base_y - lowest(P, u, app.build.get("head", 1.0))), u, theta, face)


def pose_sheet(path, cols=8, cell=(210, 260)):
    names = lib.POSE_NAMES
    rows = -(-len(names) // cols)
    img = Image.new("RGB", (cols * cell[0], rows * cell[1]), (206, 220, 232))
    L = Layer(img, (0, 0, img.width, img.height), 2)
    outfits = list(OUTFITS)
    for i, n in enumerate(names):
        x0, y0 = (i % cols) * cell[0], (i // cols) * cell[1]
        per = lib.period(n) or 1.0
        app = Appearance(outfits[i % len(outfits)], ["short", "long", "spiky", "bun", "ponytail"][i % 5], "brown", ["light", "tan", "brown"][i % 3])
        _place(L, lib.named_pose(n, 0.0 if n not in ("cartwheel",) else 0.25 * per), app, x0 + cell[0] * 0.45, y0 + cell[1] * 0.84, 24, 40, F.expression("happy"))
    L.finish()
    d = ImageDraw.Draw(img)
    for i, n in enumerate(names):
        d.text(((i % cols) * cell[0] + cell[0] / 2, (i // cols) * cell[1] + cell[1] - 6), n, font=overlay.font(15), fill=(30, 30, 40), anchor="md")
    img.save(path)
    return path


def expression_sheet(path, cols=7, cell=(190, 200)):
    names = F.EXPRESSIONS
    rows = -(-len(names) // cols)
    img = Image.new("RGB", (cols * cell[0], rows * cell[1]), (206, 220, 232))
    for i, n in enumerate(names):
        x0, y0 = (i % cols) * cell[0], (i // cols) * cell[1]
        L = Layer(img, (x0, y0, x0 + cell[0] - 1, y0 + cell[1] - 22), 2)  # one clipped layer per face
        u = 44
        pose = lib.named_pose("stand", 0)
        P, _ = fk(pose, u, 20, BASE.build)
        hx, hy = P["head"]
        draw_character(L, pose, BASE, (x0 + cell[0] / 2 - hx, y0 + cell[1] * 0.42 - hy), u, 20, F.expression(n))
        L.finish()
    d = ImageDraw.Draw(img)
    for i, n in enumerate(names):
        d.text(((i % cols) * cell[0] + cell[0] / 2, (i // cols) * cell[1] + cell[1] - 6), n, font=overlay.font(15), fill=(30, 30, 40), anchor="md")
    img.save(path)
    return path


def outfit_sheet(path, cell=(150, 250)):
    views = [0, 40, 90, 180]
    outs = [("casual", "short", "brown", []), ("hoodie", "spiky", "black", ["glasses"]), ("professional", "long", "blond", ["tie"]),
            ("prehistoric", "messy", "brown", ["beard"]), ("toga", "bun", "gray", ["laurel"]), ("medieval", "ponytail", "red", ["cap"]),
            ("fantasy", "long", "white", ["wizard_hat", "cape", "beard"]), ("sporty", "afro", "black", ["headband"])]
    img = Image.new("RGB", (cell[0] * len(views), cell[1] * len(outs)), (206, 220, 232))
    L = Layer(img, (0, 0, img.width, img.height), 2)
    for r, (o, h, hc, acc) in enumerate(outs):
        app = Appearance(o, h, hc, ["light", "tan", "brown", "dark"][r % 4], acc)
        for c, th in enumerate(views):
            _place(L, lib.named_pose("stand", 0), app, c * cell[0] + cell[0] / 2, r * cell[1] + cell[1] * 0.97, 24, th, F.expression("neutral"))
    L.finish()
    img.save(path)
    return path


def scene_sheet(path, cols=4, thumb=(400, 225)):
    names = scenes.SCENES
    rows = -(-len(names) // cols)
    img = Image.new("RGB", (cols * thumb[0], rows * thumb[1]), BG)
    for i, n in enumerate(names):
        bg = scenes.background(n, config.LANDSCAPE).copy()
        L = Layer(bg, (300, 100, 900, 700), 2)
        _place(L, lib.named_pose("stand", 0), BASE, 560, scenes.ground_y(config.LANDSCAPE), 58, 40, F.expression("happy"))
        L.finish()
        d = ImageDraw.Draw(bg)
        d.text((640, 40), n.upper(), font=overlay.font(54), fill=(255, 196, 61), anchor="mm", stroke_width=4, stroke_fill=BG)
        img.paste(bg.resize(thumb), ((i % cols) * thumb[0], (i // cols) * thumb[1]))
    img.save(path)
    return path
