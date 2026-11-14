"""Character appearance (outfits, hair, accessories, proportions) and rendering."""
import math

from engine import face as F
from engine.draw import BLACK, hull
from engine.skeleton import fk

SKIN = {"light": (255, 224, 196), "tan": (232, 186, 144), "brown": (182, 128, 90), "dark": (124, 84, 60)}
HAIR_COL = {"black": (34, 32, 38), "brown": (98, 64, 42), "blond": (232, 200, 112), "red": (178, 74, 44),
            "gray": (170, 170, 178), "white": (240, 240, 240), "blue": (62, 112, 192), "green": (62, 150, 102)}

OUTFITS = {
    "casual": dict(top=(226, 96, 88), sleeves="short", bottom=(64, 92, 152), kind="pants", shoes=(240, 240, 240)),
    "hoodie": dict(top=(92, 112, 164), sleeves="long", bottom=(52, 58, 84), kind="pants", shoes=(228, 228, 228), hood=True),
    "professional": dict(top=(244, 244, 248), sleeves="long", bottom=(46, 50, 68), kind="pants", shoes=(32, 32, 38),
                         tie=(192, 52, 62), jacket=(46, 50, 68)),
    "prehistoric": dict(top=(152, 106, 66), sleeves="none", bottom=(152, 106, 66), kind="fur", shoes=None),
    "toga": dict(top=(240, 236, 224), sleeves="none", bottom=(240, 236, 224), kind="robe", shoes=(150, 112, 72)),
    "medieval": dict(top=(142, 62, 62), sleeves="long", bottom=(82, 72, 62), kind="tunic", shoes=(72, 52, 42), belt=(62, 42, 32)),
    "fantasy": dict(top=(92, 62, 152), sleeves="long", bottom=(92, 62, 152), kind="robe", shoes=(62, 42, 92), belt=(230, 190, 70)),
    "sporty": dict(top=(60, 170, 120), sleeves="short", bottom=(40, 50, 70), kind="shorts", shoes=(250, 250, 250)),
}
HAIRSTYLES = ["short", "long", "ponytail", "bun", "spiky", "afro", "mohawk", "messy", "bald"]
ACCESSORIES = ["glasses", "cap", "top_hat", "wizard_hat", "crown", "laurel", "beard", "mustache", "backpack",
               "scarf", "tie", "cape", "headband"]
BUILDS = {"average": dict(head=1.12), "tall": dict(limb=1.12, torso=1.05, head=1.05), "short": dict(limb=0.9, torso=0.92, head=1.18),
          "stocky": dict(width=1.25, thick=1.25, head=1.12), "slim": dict(width=0.85, thick=0.8, head=1.12), "child": dict(limb=0.72, torso=0.75, head=1.35)}


class Appearance:
    def __init__(self, outfit="casual", hair="short", hair_color="brown", skin="light", accessories=(), build="average",
                 top=None, bottom=None):
        self.outfit = dict(OUTFITS.get(outfit, OUTFITS["casual"]))
        if top:
            self.outfit["top"] = tuple(top)
        if bottom:
            self.outfit["bottom"] = tuple(bottom)
        self.name = outfit
        self.hair = hair if hair in HAIRSTYLES else "short"
        self.hair_col = HAIR_COL.get(hair_color, HAIR_COL["brown"])
        self.skin = SKIN.get(skin, SKIN["light"])
        self.acc = [a for a in accessories if a in ACCESSORIES]
        if self.outfit.get("hood") and "hood" not in self.acc:
            pass
        self.build = dict(BUILDS.get(build, {}))

    @staticmethod
    def from_dict(d):
        return Appearance(d.get("outfit", "casual"), d.get("hair", "short"), d.get("hair_color", "brown"),
                          d.get("skin", "light"), d.get("accessories", ()), d.get("build", "average"))


def _rot(p, c, deg):
    a = math.radians(deg)
    x, y = p[0] - c[0], p[1] - c[1]
    return (c[0] + x * math.cos(a) - y * math.sin(a), c[1] + x * math.sin(a) + y * math.cos(a))


class Head3D:
    """Orthographic head: (f forward, l lateral, h up) in units of the head radius -> screen px."""

    def __init__(self, c, r, theta, roll):
        t = math.radians(theta)
        self.c, self.r, self.st, self.ct, self.roll = c, r, math.sin(t), math.cos(t), roll

    def at(self, f, l, h):
        x = (f * self.st - l * self.ct) * self.r
        y = -h * self.r
        return _rot((self.c[0] + x, self.c[1] + y), self.c, self.roll)

    def depth(self, f, l):
        return f * self.ct + l * self.st


def _skull(hd, hmin, scale=1.07, n=20, hs=(0.0, 0.4, 0.75, 1.0)):
    """Points on a spherical cap (elevation >= hmin) of the head."""
    pts = [hd.at(0, 0, scale)]
    for i in range(n):
        az = 2 * math.pi * i / n
        for k in hs:
            h = hmin + (1.0 - hmin) * k
            rr = math.sqrt(max(0.0, 1 - h * h)) * scale
            pts.append(hd.at(rr * math.cos(az), rr * math.sin(az), h * scale))
    return pts


def _back_points(hd, hmin=-0.35, scale=1.07):
    pts = []
    for i in range(14):
        az = math.pi / 2 + math.pi * i / 13  # back half of the head (f <= 0)
        for h in (hmin, 0.2, 0.7):
            rr = math.sqrt(max(0.0, 1 - h * h)) * scale
            pts.append(hd.at(rr * math.cos(az), rr * math.sin(az), h * scale))
    return pts


def _side_view(hd):
    return abs(hd.st) > 0.35 or hd.ct < -0.2


def _draw_hair(L, hd, app, ow, back):
    col, st = app.hair_col, app.hair
    if st == "bald":
        return
    if back:
        if st == "long":
            L.poly(hull([hd.at(-0.9, l, h) for l in (-1.05, 0, 1.05) for h in (0.6, -2.0)] + [hd.at(-0.2, l, 0.3) for l in (-1.1, 1.1)]), col, BLACK, ow)
        elif st == "afro":
            L.poly(hull([hd.at(1.45 * math.cos(a), 1.45 * math.sin(a), 0.2) for a in [i * 0.4 for i in range(16)]]), col, BLACK, ow)
        elif st == "ponytail":
            L.ellipse(hd.at(-1.25, 0, 0.1), hd.r * 0.28, hd.r * 0.7, col, BLACK, ow)
        elif st == "bun":
            L.circle(hd.at(-0.55, 0, 1.25), hd.r * 0.36, col, BLACK, ow)
        return
    if st == "mohawk":
        pts = [hd.at(f, l, 0.75 if abs(f) > 0.8 else 1.35) for f in (-0.9, -0.4, 0.1, 0.6, 0.9) for l in (-0.14, 0.14)]
        L.poly(hull(pts), col, BLACK, ow)
        return
    pts = _skull(hd, 0.5 if st != "long" else 0.45)
    if _side_view(hd):
        pts += _back_points(hd, -0.35 if st in ("long", "afro") else 0.0)
    if st == "afro":
        pts = _skull(hd, 0.35, 1.2) + (_back_points(hd, -0.2, 1.2) if _side_view(hd) else [])
    L.poly(hull(pts), col, BLACK, ow)
    if st in ("spiky", "messy"):
        for f, l in ((0.5, 0.0), (0.0, 0.5), (0.0, -0.5), (-0.5, 0.0), (0.0, 0.0)):
            L.poly([hd.at(f + 0.25, l, 0.95), hd.at(f - 0.25, l, 0.95), hd.at(f, l + (0.25 if st == "spiky" else 0.0), 1.6)], col, BLACK, ow * 0.8)


def _draw_hat(L, hd, app, ow):
    top = hd.at(0, 0, 0.88)
    r = hd.r
    roll = hd.roll

    def R(dx, dy):
        return _rot((top[0] + dx * r, top[1] + dy * r), top, roll)

    for a in app.acc:
        if a == "cap":
            L.poly(hull(_skull(hd, 0.4, 1.13) + (_back_points(hd, 0.1, 1.13) if _side_view(hd) else [])), (200, 60, 60), BLACK, ow)
            L.poly(hull([hd.at(0.95, -0.75, 0.45), hd.at(0.95, 0.75, 0.45), hd.at(1.55, 0.5, 0.4), hd.at(1.55, -0.5, 0.4)]),
                   (170, 44, 44), BLACK, ow * 0.8)
        elif a == "top_hat":
            L.poly([R(-0.85, 0.12), R(0.85, 0.12), R(0.85, -0.06), R(-0.85, -0.06)], (30, 30, 40), BLACK, ow)
            L.poly([R(-0.55, 0.0), R(0.55, 0.0), R(0.5, -1.1), R(-0.5, -1.1)], (36, 36, 48), BLACK, ow)
        elif a == "wizard_hat":
            L.poly([R(-1.15, 0.12), R(1.15, 0.12), R(0.2, -0.1), R(0.5, -1.6), R(-0.3, -1.9), R(-0.55, -0.1)], (90, 60, 150), BLACK, ow)
        elif a == "crown":
            pts = [R(-0.7, 0.05)]
            for i in range(5):
                pts += [R(-0.7 + 0.35 * i, -0.55), R(-0.52 + 0.35 * i, -0.2)]
            pts += [R(0.7, 0.05)]
            L.poly(pts, (240, 200, 60), BLACK, ow * 0.8)
        elif a == "laurel":
            for s in (-1, 1):
                for i in range(4):
                    L.ellipse(R(s * (0.55 + 0.2 * i), 0.1 + 0.18 * i), r * 0.15, r * 0.08, (96, 150, 80), BLACK, ow * 0.5)
        elif a == "headband":
            L.line([hd.at(f, l, 0.45) for f in (0.7, 0) for l in (-1, 0, 1)][:0] or [hd.at(0.95 * math.cos(t), 0.95 * math.sin(t), 0.45) for t in [i * 0.4 for i in range(16)]], max(2, r * 0.14), (220, 60, 70))


def _draw_face(L, hd, app, fp, ow, talk):
    r = hd.r
    skin_d = tuple(max(0, c - 40) for c in app.skin)
    if hd.depth(1, 0) < -0.15 and abs(hd.st) < 0.8:  # back of head: no features
        return
    lw = max(2.0, r * 0.1)
    near = 1 if hd.st >= 0 else -1
    eyes = []
    for sg in (1, -1):
        l = sg * 0.42
        if abs(hd.st) > 0.8 and hd.depth(0, l) < 0:
            continue
        if hd.depth(0.82, l) < 0.02:
            continue
        eyes.append((sg, hd.at(0.82, l, 0.14)))
    if fp["blush"] > 0.05:
        for sg in (1, -1):
            if hd.depth(0.7, sg * 0.6) > 0.1:
                L.ellipse(hd.at(0.7, sg * 0.62, -0.28), r * 0.2, r * 0.11, (255, 150, 150))
    foreshort = max(0.45, abs(hd.ct) * 0.6 + 0.4)
    for sg, c in eyes:
        e = fp["eye"]
        er = r * 0.17
        if e < 0.25:
            sag = 0.5 if fp["smile"] > 0.2 else 0.0
            L.line([_rot((c[0] - er, c[1]), c, hd.roll), _rot((c[0], c[1] + er * sag * (1 if fp["smile"] > 0.2 else -1)), c, hd.roll),
                    _rot((c[0] + er, c[1]), c, hd.roll)], lw, BLACK)
        else:
            ry = er * min(1.5, 0.35 + 0.65 * e)
            L.ellipse(c, er * foreshort, ry, (255, 255, 255), BLACK, max(1.0, lw * 0.6))
            pr = er * 0.5
            L.circle((c[0] + fp["px"] * er * 0.4 + near * (hd.st * er * 0.3), c[1] + fp["py"] * ry * 0.4), pr, BLACK)
            if fp["lid"] > 0.05:
                L.poly([(c[0] - er * foreshort - 1, c[1] - ry - 1), (c[0] + er * foreshort + 1, c[1] - ry - 1),
                        (c[0] + er * foreshort + 1, c[1] - ry + 2 * ry * fp["lid"]), (c[0] - er * foreshort - 1, c[1] - ry + 2 * ry * fp["lid"])], app.skin, BLACK, 1)
        brow_h = fp["browL"] if sg == 1 else fp["browR"]
        inner = _rot((c[0] - sg * hd.ct * -1 * 0 + (-sg) * er * 0.2 * -1, c[1]), c, 0)
        y0 = c[1] - r * (0.34 + 0.16 * brow_h)
        t = fp["tilt"]
        p_in = (c[0] + sg * 0 - (er * 0.6) * (-1 if sg == 1 else 1) * 0 + (hd.st * 0) + (-sg * er * 1.0) * (-1) * 0, y0)
        # inner end is toward the nose (center), outer toward the ear
        cx_face = hd.at(0.9, 0, 0.14)[0]
        side = 1 if c[0] >= cx_face else -1
        p_in = (c[0] - side * er * 0.9 * foreshort, y0 + r * 0.1 * t)
        p_out = (c[0] + side * er * 1.15 * foreshort, y0 - r * 0.1 * t)
        L.line([_rot(p_in, hd.c, hd.roll), _rot(p_out, hd.c, hd.roll)], lw * 1.1, BLACK)
        if fp["tear"] > 0.2:
            L.ellipse((c[0], c[1] + r * 0.32), r * 0.05, r * 0.11, (120, 190, 255))
    mc = hd.at(0.92, 0, -0.45)
    mwid = r * 0.3 * fp["mw"] * max(0.45, abs(hd.ct))
    sm = fp["smile"]
    op = max(fp["open"], 0.9 if talk else 0.0)
    pts = [(mc[0] + mwid * (2 * i / 6 - 1), mc[1] - r * 0.1 * sm * (1 - (2 * i / 6 - 1) ** 2) * -1 * -1 + r * 0.14 * sm * (1 - (2 * i / 6 - 1) ** 2) * 0) for i in range(7)]
    pts = [(mc[0] + mwid * (2 * i / 6 - 1), mc[1] + r * 0.16 * sm * (1 - (2 * i / 6 - 1) ** 2) - r * 0.07 * sm) for i in range(7)]
    if op > 0.12:
        h = r * 0.34 * op
        L.ellipse((mc[0], mc[1] + h * 0.3), max(mwid * 0.8, r * 0.07), h, (88, 30, 44), BLACK, max(1.0, lw * 0.5))
    else:
        L.line([_rot(p, hd.c, hd.roll) for p in pts], lw, BLACK)
    if abs(hd.st) > 0.55 and hd.depth(1, 0) > 0.2:
        n = hd.at(1.12, 0, -0.1)
        L.poly([hd.at(1.0, 0, 0.12), n, hd.at(1.0, 0, -0.2)], app.skin, BLACK, max(1.0, lw * 0.5))
    if fp["sweat"] > 0.2:
        s = hd.at(0.4, 0.9 * near, 0.85)
        L.poly([(s[0], s[1] - r * 0.14), (s[0] - r * 0.08, s[1] + r * 0.04), (s[0] + r * 0.08, s[1] + r * 0.04)], (130, 200, 255), BLACK, 1)
        L.circle((s[0], s[1] + r * 0.04), r * 0.08, (130, 200, 255))


def _draw_beard(L, hd, app, ow):
    if "beard" in app.acc and hd.depth(1, 0) > -0.1:
        pts = [hd.at(f, l, h) for f in (0.1, 0.75) for l in (-0.88, 0.88) for h in (-0.05,)]
        for i in range(9):
            t = -1 + i / 4
            pts += [hd.at(0.1 + 0.65 * (1 - abs(t)), 0.88 * t, -0.05 - 1.12 * math.sqrt(max(0.0, 1 - 0.7 * t * t)))]
        L.poly(hull(pts), app.hair_col, BLACK, ow)


def _accessories_front(L, hd, app, ow):
    r = hd.r
    lw = max(2.0, r * 0.08)
    if "glasses" in app.acc and hd.depth(1, 0) > 0.0:
        centers = [hd.at(0.85, sg * 0.42, 0.14) for sg in (1, -1) if hd.depth(0.85, sg * 0.42) > 0.02]
        for c in centers:
            L.ring(c, r * 0.26 * max(0.5, abs(hd.ct)), r * 0.26, BLACK, lw * 0.8)
        if len(centers) == 2:
            L.line(centers, lw, BLACK)
    if "mustache" in app.acc and hd.depth(1, 0) > 0.15:
        L.poly(hull([hd.at(0.95, l, h) for l in (-0.4, 0.4) for h in (-0.28, -0.4)]), app.hair_col, BLACK, ow * 0.6)


def draw_character(L, pose, app, root, u, theta, face, talk=False, seed=0, t=0.0):
    """Draw one character with its hip at screen position `root`. Returns the screen points."""
    build = app.build
    P, ab = fk(pose, u, theta, build)
    fwd = 1 if math.sin(math.radians(theta)) >= 0 else -1
    S = {k: (root[0] + x, root[1] + y) for k, (x, y) in P.items()}
    o = app.outfit
    skin, ow = app.skin, max(2.0, u * 0.06)
    thick = build.get("thick", 1.0)
    wl = 0.27 * u * thick
    c = math.cos(math.radians(theta))
    tw = u * (0.9 + 0.3 * abs(c)) * thick
    kind = o["kind"]
    top, bottom = o["top"], o["bottom"]
    fp = dict(face)
    fp["eye"] = fp["eye"] * F.blink(t, seed)

    def chain(segs):
        for a, b, w, _ in segs:
            L.cap(S[a], S[b], w + 2 * ow, BLACK)
        for a, b, w, col in segs:
            L.cap(S[a], S[b], w, col)

    def arm(s):
        sl = o["sleeves"]
        up = top if sl in ("short", "long") else skin
        lo = top if sl == "long" else skin
        chain([("sh_" + s, "elbow_" + s, wl, up), ("elbow_" + s, "hand_" + s, wl * 0.92, lo)])
        L.circle(S["hand_" + s], wl * 0.62, skin, BLACK, ow)

    def leg(s):
        thigh = bottom if kind in ("pants", "shorts", "tunic") else skin
        shin = bottom if kind == "pants" else skin
        wl2 = wl * 1.1
        chain([("hip_" + s, "knee_" + s, wl2, thigh), ("knee_" + s, "ankle_" + s, wl2 * 0.95, shin)])
        sc = o.get("shoes")
        if sc is not None:
            L.cap(S["heel_" + s], S["toe_" + s], wl * 1.25 + 2 * ow, BLACK)
            L.cap(S["heel_" + s], S["toe_" + s], wl * 1.25, sc)
        else:
            L.cap(S["heel_" + s], S["toe_" + s], wl * 1.1 + 2 * ow, BLACK)
            L.cap(S["heel_" + s], S["toe_" + s], wl * 1.1, skin)

    hr = 0.9 * u * build.get("head", 1.0)
    hd = Head3D(S["head"], hr, theta, ab["head"] * fwd)
    far, near = ("L", "R") if fwd > 0 else ("R", "L")

    if "cape" in app.acc or kind == "robe" and o is OUTFITS["fantasy"]:
        L.poly([S["sh_L"], S["sh_R"], (S["hip"][0] + fwd * -1.1 * u, S["hip"][1] + 2.4 * u), (S["hip"][0] + fwd * 0.3 * u, S["hip"][1] + 2.6 * u)], (176, 44, 60), BLACK, ow)
    if "backpack" in app.acc:
        c0 = ((S["neck"][0] + S["hip"][0]) / 2 - fwd * 0.55 * u * (1 - 0.5 * abs(c)), (S["neck"][1] + S["hip"][1]) / 2)
        L.ellipse(c0, 0.45 * u, 0.7 * u, (210, 150, 60), BLACK, ow)
    _draw_hair(L, hd, app, ow, back=True)
    leg(far)
    arm(far)

    # torso
    L.cap(S["hip"], S["neck"], tw + 2 * ow, BLACK)
    L.cap(S["hip"], S["neck"], tw, top)
    if "jacket" in o:
        L.cap(S["hip"], S["neck"], tw * 0.98 + 2 * ow, BLACK)
        L.cap(S["hip"], S["neck"], tw * 0.98, o["jacket"])
        L.cap(S["waist"], S["neck"], tw * 0.28, top)
    if "tie" in o or "tie" in app.acc:
        L.poly([S["neck"], (S["neck"][0] - 0.12 * u, S["neck"][1] + 0.35 * u), (S["neck"][0], S["neck"][1] + 1.2 * u),
                (S["neck"][0] + 0.12 * u, S["neck"][1] + 0.35 * u)], o.get("tie", (190, 50, 60)), BLACK, ow * 0.6)
    if "belt" in o:
        L.cap((S["hip"][0] - tw * 0.5, S["hip"][1] - 0.15 * u), (S["hip"][0] + tw * 0.5, S["hip"][1] - 0.15 * u), 0.18 * u, o["belt"])
    if kind in ("robe", "tunic", "fur"):
        hem_y = S["hip"][1] + (2.4 if kind == "robe" else 1.0) * u * build.get("limb", 1.0)
        a0, a1 = (S["hip"][0] - tw * 0.7, S["hip"][1] - 0.2 * u), (S["hip"][0] + tw * 0.7, S["hip"][1] - 0.2 * u)
        if kind == "fur":
            zig = [(a1[0] + 0.25 * u, hem_y - 0.1 * u)] + [(a1[0] - (a1[0] - a0[0] + 0.5 * u) * i / 5 + 0.25 * u, hem_y + (0.28 * u if i % 2 else -0.05 * u)) for i in range(6)]
            L.poly([a0, a1] + zig, bottom, BLACK, ow)
        else:
            flare = 0.5 if kind == "robe" else 0.3
            L.poly([a0, a1, (a1[0] + flare * u, hem_y), (a0[0] - flare * u, hem_y)], bottom, BLACK, ow)
    if "scarf" in app.acc:
        L.cap((S["neck"][0] - 0.3 * u, S["neck"][1] + 0.05 * u), (S["neck"][0] + 0.3 * u, S["neck"][1] + 0.05 * u), 0.3 * u, (220, 80, 80))
    if o.get("hood"):
        L.poly([(S["neck"][0] - 0.45 * u, S["neck"][1] - 0.1 * u), (S["neck"][0] + 0.45 * u, S["neck"][1] - 0.1 * u),
                (S["neck"][0], S["neck"][1] + 0.5 * u)], top, BLACK, ow * 0.7)

    leg(near)
    arm(near)
    L.cap(S["neck"], S["head"], 0.3 * u, BLACK)
    L.cap(S["neck"], S["head"], 0.3 * u - 2 * ow * 0.0, skin)
    L.circle(S["head"], hr, skin, BLACK, ow * 1.3)
    _draw_hair(L, hd, app, ow, back=False)
    _draw_beard(L, hd, app, ow)
    _draw_face(L, hd, app, fp, ow, talk)
    _accessories_front(L, hd, app, ow)
    _draw_hat(L, hd, app, ow)
    return S
