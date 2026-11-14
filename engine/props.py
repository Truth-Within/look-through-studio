"""Props with attachment points, states (open, page flip, bites...) and timed placement tracks."""
import math

from engine.draw import BLACK

WOOD, DARK, PAPER = (176, 128, 84), (122, 84, 56), (246, 241, 226)
SPECS = {}


def spec(name, grips=None, solid=None, seat=None, surface=None, hold="hand", behind=True):
    def deco(fn):
        SPECS[name] = dict(draw=fn, grips=grips or (lambda s: {}), solid=solid, seat=seat, surface=surface,
                           hold=hold, behind=behind)
        return fn
    return deco


class Xf:
    """Local prop coordinates (units of u, y up, origin = bottom centre) -> screen px."""

    def __init__(self, sx, sy, u, rot=0.0, flip=1):
        self.sx, self.sy, self.u, self.flip = sx, sy, u, flip
        self.c, self.s = math.cos(math.radians(rot)), math.sin(math.radians(rot))

    def __call__(self, dx, dy):
        x, y = dx * self.flip * self.u, -dy * self.u
        return (self.sx + x * self.c - y * self.s, self.sy + x * self.s + y * self.c)


def _w(T, u):
    return max(2.0, u * 0.05)


# ---------------------------------------------------------------- furniture
@spec("chair", grips=lambda s: {"back": (-0.58, 3.5)}, seat=1.55)
def _chair(L, T, s, u):
    ow = _w(T, u)
    for x in (-0.5, 0.5):
        L.cap(T(x, 0), T(x, 1.5), u * 0.14 + 2 * ow, BLACK)
        L.cap(T(x, 0), T(x, 1.5), u * 0.14, DARK)
    L.poly([T(-0.65, 3.8), T(-0.48, 3.8), T(-0.48, 1.7), T(-0.65, 1.7)], WOOD, BLACK, ow)
    L.poly([T(-0.65, 1.5), T(0.7, 1.5), T(0.7, 1.72), T(-0.65, 1.72)], WOOD, BLACK, ow)


@spec("desk", grips=lambda s: {"top_L": (-0.9, 2.6), "top_R": (-0.2, 2.6), "center": (0.0, 2.6)},
      solid=(-1.4, 1.4, 0.0, 2.6), surface=2.6)
def _desk(L, T, s, u):
    ow = _w(T, u)
    for x in (-1.25, 1.25):
        L.poly([T(x - 0.09, 0), T(x + 0.09, 0), T(x + 0.09, 2.4), T(x - 0.09, 2.4)], DARK, BLACK, ow)
    L.poly([T(-1.4, 2.6), T(1.4, 2.6), T(1.4, 2.35), T(-1.4, 2.35)], WOOD, BLACK, ow)
    L.poly([T(0.4, 2.35), T(1.15, 2.35), T(1.15, 1.7), T(0.4, 1.7)], DARK, BLACK, ow)


@spec("bed", solid=(-4.0, 4.0, 0.0, 1.45), surface=1.45, seat=1.45)
def _bed(L, T, s, u):
    ow = _w(T, u)
    L.poly([T(-4.1, 0), T(-3.9, 0), T(-3.9, 2.8), T(-4.1, 2.8)], DARK, BLACK, ow)
    L.poly([T(-4.0, 0.5), T(4.0, 0.5), T(4.0, 1.2), T(-4.0, 1.2)], DARK, BLACK, ow)
    L.poly([T(-4.0, 1.2), T(4.0, 1.2), T(4.0, 1.45), T(-4.0, 1.45)], (232, 230, 240), BLACK, ow)
    L.poly([T(-3.9, 1.45), T(-2.3, 1.45), T(-2.4, 1.85), T(-3.8, 1.85)], (250, 250, 255), BLACK, ow)
    L.poly([T(-0.4, 1.45), T(4.0, 1.45), T(4.0, 1.62), T(-0.4, 1.62)], (110, 150, 200), BLACK, ow)


@spec("door", grips=lambda s: {"handle": (0.75 * math.cos(math.radians(72 * s.get("open", 0))) - 0.1, 3.3)},
      surface=None)
def _door(L, T, s, u):
    ow = _w(T, u)
    a = s.get("open", 0.0)
    L.poly([T(-1.0, 0), T(1.0, 0), T(1.0, 7.4), T(-1.0, 7.4)], (30, 30, 44), BLACK, ow)
    wid = 1.7 * math.cos(math.radians(72 * a))
    L.poly([T(-0.85, 0), T(-0.85 + wid, 0.0 + 0.1 * a), T(-0.85 + wid, 7.2 - 0.25 * a), T(-0.85, 7.3)], (150, 100, 66), BLACK, ow)
    L.circle(T(-0.85 + wid * 0.85, 3.3), u * 0.09, (240, 210, 90), BLACK, ow * 0.6)


@spec("ladder", solid=None)
def _ladder(L, T, s, u):
    ow = _w(T, u)
    for x in (-0.45, 0.45):
        L.cap(T(x, 0), T(x, 7.4), u * 0.13 + 2 * ow, BLACK)
        L.cap(T(x, 0), T(x, 7.4), u * 0.13, WOOD)
    for i in range(1, 11):
        L.cap(T(-0.45, i * 0.68), T(0.45, i * 0.68), u * 0.1 + 2 * ow, BLACK)
        L.cap(T(-0.45, i * 0.68), T(0.45, i * 0.68), u * 0.1, DARK)


@spec("board", grips=lambda s: {"point": (-0.6, 5.0)})
def _board(L, T, s, u):
    ow = _w(T, u)
    L.poly([T(-2.3, 3.0), T(2.3, 3.0), T(2.3, 6.4), T(-2.3, 6.4)], (250, 250, 252), BLACK, ow * 1.4)
    L.cap(T(-1.8, 5.7), T(0.4, 5.7), u * 0.06, (70, 110, 200))
    L.cap(T(-1.8, 5.1), T(1.4, 5.1), u * 0.06, (200, 80, 80))
    L.cap(T(-1.8, 4.5), T(-0.2, 4.5), u * 0.06, (70, 110, 200))
    L.cap(T(0, 3.0), T(0, 0), u * 0.1, DARK)


# ---------------------------------------------------------------- handheld
@spec("book", grips=lambda s: {"L": (-0.45 - 0.45 * s.get("open", 0), 0.0), "R": (0.45 + 0.45 * s.get("open", 0), 0.0),
                               "top": (0.0, 0.1)}, hold="anchor", behind=False)
def _book(L, T, s, u):
    ow = _w(T, u)
    o = s.get("open", 0.0)
    cover = (196, 72, 72)
    if o < 0.05:
        L.poly([T(-0.45, -0.6), T(0.45, -0.6), T(0.45, 0.6), T(-0.45, 0.6)], cover, BLACK, ow)
        L.cap(T(-0.34, -0.6), T(-0.34, 0.6), u * 0.04, (150, 50, 50))
        return
    wd = 0.9 * min(1.0, o)
    L.poly([T(-wd, -0.55), T(0, -0.62), T(0, 0.62), T(-wd, 0.55)], PAPER, BLACK, ow)
    L.poly([T(0, -0.62), T(wd, -0.55), T(wd, 0.55), T(0, 0.62)], PAPER, BLACK, ow)
    for k in range(3):
        L.cap(T(-wd * 0.8, 0.3 - 0.25 * k), T(-0.12, 0.3 - 0.25 * k), u * 0.025, (150, 150, 160))
        L.cap(T(0.12, 0.3 - 0.25 * k), T(wd * 0.8, 0.3 - 0.25 * k), u * 0.025, (150, 150, 160))
    f = s.get("flip", 0.0)
    if 0.0 < f < 1.0:  # a page turning over from right to left
        x = wd * math.cos(math.pi * f)
        L.poly([T(0, -0.6), T(x, -0.52 - 0.05 * math.sin(math.pi * f)), T(x, 0.52 + 0.1 * math.sin(math.pi * f)), T(0, 0.6)],
               (252, 249, 238), BLACK, ow * 0.8)


@spec("phone", grips=lambda s: {"grip": (0.0, -0.1)}, behind=False)
def _phone(L, T, s, u):
    ow = _w(T, u)
    L.poly([T(-0.14, -0.26), T(0.14, -0.26), T(0.14, 0.26), T(-0.14, 0.26)], (40, 44, 60), BLACK, ow)
    L.poly([T(-0.1, -0.2), T(0.1, -0.2), T(0.1, 0.2), T(-0.1, 0.2)], (130, 190, 240))


@spec("cup", grips=lambda s: {"grip": (0.2, 0.15)}, behind=False)
def _cup(L, T, s, u):
    ow = _w(T, u)
    L.ring(T(0.2, 0.17), u * 0.1, u * 0.1, BLACK, ow * 1.4)
    L.poly([T(-0.17, 0.0), T(0.17, 0.0), T(0.2, 0.38), T(-0.2, 0.38)], (240, 240, 245), BLACK, ow)
    L.poly([T(-0.17, 0.0), T(0.17, 0.0), T(0.18, 0.26 * (1 - s.get("drunk", 0.0)) + 0.01), T(-0.18, 0.26 * (1 - s.get("drunk", 0.0)) + 0.01)], (150, 96, 62))


@spec("apple", grips=lambda s: {"grip": (0.0, 0.0)}, behind=False)
def _apple(L, T, s, u):
    ow = _w(T, u)
    r = u * (0.22 - 0.04 * s.get("bite", 0.0))
    L.circle(T(0, 0.0), r, (214, 60, 60), BLACK, ow)
    L.cap(T(0, 0.2), T(0.04, 0.34), u * 0.04, DARK)
    L.ellipse(T(0.1, 0.32), u * 0.07, u * 0.04, (90, 170, 90))


@spec("ball", behind=False)
def _ball(L, T, s, u):
    ow = _w(T, u)
    L.circle(T(0, 0.4), u * 0.4, (240, 150, 60), BLACK, ow)
    L.cap(T(-0.4, 0.4), T(0.4, 0.4), u * 0.04, BLACK)


@spec("hammer", grips=lambda s: {"grip": (0.0, 0.0)}, behind=False)
def _hammer(L, T, s, u):
    ow = _w(T, u)
    L.cap(T(0, -0.1), T(0, 0.9), u * 0.1 + 2 * ow, BLACK)
    L.cap(T(0, -0.1), T(0, 0.9), u * 0.1, WOOD)
    L.poly([T(-0.28, 0.85), T(0.28, 0.85), T(0.28, 1.1), T(-0.28, 1.1)], (140, 146, 160), BLACK, ow)


@spec("box", grips=lambda s: {"L": (-0.65, 0.0), "R": (0.65, 0.0), "top": (0, 0.55)}, hold="anchor", behind=False)
def _box(L, T, s, u):
    ow = _w(T, u)
    L.poly([T(-0.65, -0.55), T(0.65, -0.55), T(0.65, 0.55), T(-0.65, 0.55)], (200, 160, 100), BLACK, ow)
    L.cap(T(-0.65, 0.25), T(0.65, 0.25), u * 0.05, (170, 130, 80))


@spec("laptop", grips=lambda s: {"keys_L": (-0.3, 0.15), "keys_R": (0.3, 0.15)})
def _laptop(L, T, s, u):
    ow = _w(T, u)
    L.poly([T(-0.8, 0), T(0.8, 0), T(0.8, 0.1), T(-0.8, 0.1)], (150, 156, 170), BLACK, ow)
    L.poly([T(-0.7, 0.1), T(-0.45, 1.2), T(0.35, 1.2), T(0.1, 0.1)][::-1][::-1], (60, 64, 80), BLACK, ow)
    L.poly([T(-0.55, 0.18), T(-0.4, 1.05), T(0.3, 1.05), T(0.05, 0.18)], (120, 190, 240))


@spec("notebook", grips=lambda s: {"write": (0.1, 0.08)})
def _notebook(L, T, s, u):
    ow = _w(T, u)
    L.poly([T(-0.7, 0), T(0.7, 0), T(0.7, 0.07), T(-0.7, 0.07)], PAPER, BLACK, ow)
    L.cap(T(-0.5, 0.07), T(0.3, 0.07), u * 0.025, (90, 110, 200))


@spec("pot", grips=lambda s: {"handle_L": (-0.7, 0.55), "handle_R": (0.7, 0.55), "stir": (0.0, 0.8)}, behind=True)
def _pot(L, T, s, u):
    ow = _w(T, u)
    L.poly([T(-0.55, 0), T(0.55, 0), T(0.6, 0.8), T(-0.6, 0.8)], (130, 136, 150), BLACK, ow)
    for sg in (-1, 1):
        L.cap(T(sg * 0.6, 0.55), T(sg * 0.8, 0.55), u * 0.07, BLACK)
    L.poly([T(-0.5, 0.8), T(0.5, 0.8), T(0.4, 1.0), T(-0.4, 1.0)], (96, 150, 90))


PROP_TYPES = list(SPECS)


def grips(ptype, state):
    return SPECS[ptype]["grips"](state or {})


class PropTrack:
    """Where a prop is over time: free, in a hand, on a body anchor, or in flight (tween)."""

    def __init__(self, pid, ptype, x, y, facing=1, state=None, rot=0.0):
        self.id, self.type, self.facing = pid, ptype, facing
        self.base_state = {"open": 0.0, "flip": 0.0, "page": 0, "bite": 0.0, "drunk": 0.0, **(state or {})}
        self.phases = [(0.0, {"kind": "free", "x": x, "y": y, "rot": rot})]
        self.anims = []  # (t0, dur, key, v0, v1)

    def set_phase(self, t, **ph):
        self.phases = [p for p in self.phases if p[0] < t - 1e-6] + [(t, ph)]

    def anim(self, t0, dur, key, v0, v1):
        self.anims.append((t0, dur, key, v0, v1))

    def state_at(self, t):
        s = dict(self.base_state)
        for t0, dur, key, v0, v1 in sorted(self.anims, key=lambda a: a[0]):
            if t >= t0:
                k = max(0.0, min(1.0, (t - t0) / max(dur, 1e-6)))
                s[key] = v0 + (v1 - v0) * (k * k * (3 - 2 * k))
        return s

    def at(self, t, lookup, u):
        """World placement at time t. lookup(actor, kind, name) -> (x, y, fwd) of a hand or body anchor."""
        ph = None
        for t0, p in self.phases:
            if t0 <= t + 1e-9:
                ph, pt0 = p, t0
        kind = ph["kind"]
        if kind == "free":
            x, y, rot = ph["x"], ph["y"], ph.get("rot", 0.0)
        elif kind == "tween":
            k = max(0.0, min(1.0, (t - pt0) / max(ph["dur"], 1e-6)))
            e = k * k * (3 - 2 * k)
            fx, fy, fr = ph["frm"]
            tx, ty, tr = ph["to"]
            x, y, rot = fx + (tx - fx) * e, fy + (ty - fy) * e - ph.get("arc", 0.0) * math.sin(math.pi * k), fr + (tr - fr) * e
        else:
            hx, hy, fwd = lookup(ph["actor"], kind, ph.get("side") or ph.get("name"))
            off = ph.get("off", (0.0, 0.0))
            r = ph.get("rot", 0.0)
            r = r(t) if callable(r) else r
            x, y, rot = hx + off[0] * u * fwd, hy - off[1] * u, r * fwd
        flip = fwd if kind in ("hand", "anchor") else self.facing
        return {"x": x, "y": y, "rot": rot, "state": self.state_at(t), "kind": kind, "flip": flip}

    def grip_world(self, st, name, u):
        g = grips(self.type, st["state"]).get(name)
        if g is None:
            return st["x"], st["y"]
        T = Xf(st["x"], st["y"], u, st["rot"], st.get("flip", self.facing))
        return T(*g)
