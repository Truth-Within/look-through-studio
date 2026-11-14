"""Skeleton + pose library.

Angles are screen angles in degrees: 0 = straight down, +90 = toward screen-right,
-90 = toward screen-left, 180 = straight up. Each limb is (upper segment, lower segment).
"""
import math

BASE = dict(
    la=(-12, -6), ra=(12, 6),      # left / right arm: (upper arm, forearm)
    ll=(-8, -4), rl=(8, 4),        # left / right leg: (thigh, shin)
    torso=0.0, head=0.0,           # lean of torso / extra tilt of head
    rot=0.0, air=0.0,              # whole-body rotation about the hip / height off the ground (in u)
    spin=0.0, bounce=0.0,          # degrees of rotation per cycle / bounce height per footfall
    seat=0,                        # draw a stool under the hips
)

POSES = {}


def S(**kw):
    return kw


def static(name, **kw):
    POSES[name] = (None, [kw])


def cycle(name, period, *keys):
    POSES[name] = (period, list(keys))


# ---- neutral / attitude
static("stand")
static("relaxed", torso=3, head=4, ll=(-4, -2), rl=(14, 6), ra=(14, 8), la=(-8, -4))
static("hands_on_hips", la=(-55, 50), ra=(55, -50))
static("arms_crossed", la=(-10, 95), ra=(10, -95), head=3)
static("open_arms", la=(-105, -115), ra=(105, 115))
static("humble", la=(-5, 35), ra=(5, -35), head=8)
static("lean_in", torso=20, head=10, la=(-10, -8), ra=(10, 8), ll=(-6, -2), rl=(6, 2))

# ---- gestures
static("point_right", ra=(100, 100))
static("point_left", la=(-100, -100))
static("point_up", ra=(158, 170), head=-6)
cycle("wave", 0.7, S(ra=(125, 165)), S(ra=(125, 125)))
static("present", la=(-65, -100), ra=(65, 100), head=-4)
cycle("explain", 1.1, S(la=(-30, -100), ra=(30, 100), head=3), S(la=(-30, -125), ra=(30, 125), head=-3))
static("shrug", la=(-40, -100), ra=(40, 100), head=9)
static("stop", ra=(100, 176))
cycle("beckon", 0.8, S(ra=(75, 150)), S(ra=(75, 115)))
static("salute", ra=(95, -150))
cycle("clap", 0.5, S(la=(-25, 115), ra=(25, -115)), S(la=(-55, 70), ra=(55, -70)))

# ---- thinking
static("think", ra=(75, -130), la=(-15, 75), head=7)
cycle("scratch_head", 0.5, S(ra=(110, -160), head=6), S(ra=(110, -178), head=6))
static("facepalm", ra=(95, -140), head=18, torso=6)
static("hands_on_head", la=(-108, 150), ra=(108, -150), head=2)

# ---- emotion
static("hands_up", la=(-140, -170), ra=(140, 170), head=-5)
cycle("cheer", 0.6,
      S(la=(-135, -155), ra=(135, 155), ll=(-14, -8), rl=(14, 8), bounce=0.35),
      S(la=(-155, -170), ra=(155, 170), ll=(-14, -8), rl=(14, 8), bounce=0.35))
cycle("fist_pump", 0.7, S(ra=(150, 175), torso=-2), S(ra=(125, 160), torso=2))
static("flex", la=(-95, -172), ra=(95, 172), ll=(-20, -10), rl=(20, 10), head=-3)
static("sad_slump", torso=16, head=34, la=(-6, -2), ra=(6, 2), ll=(-5, -2), rl=(5, 2))
static("cry", la=(-120, 110), ra=(120, -110), head=10, torso=4)
static("angry", la=(-52, 15), ra=(52, -15), ll=(-22, -12), rl=(22, 12), head=-3)
static("scared", torso=14, head=-8, la=(-50, 150), ra=(50, -150), ll=(-26, 4), rl=(26, -4))
static("pray", la=(-25, 130), ra=(25, -130), head=10)
static("bow", torso=55, head=15, la=(-6, -2), ra=(6, 2))

# ---- movement (walk/run face screen-right)
cycle("walk", 0.9,
      S(torso=4, ll=(-22, -38), rl=(24, 14), la=(20, 40), ra=(-20, -26), bounce=0.06),
      S(torso=4, ll=(24, 14), rl=(-22, -38), la=(-20, -26), ra=(20, 40), bounce=0.06))
cycle("run", 0.55,
      S(torso=16, ll=(-38, -110), rl=(72, 8), la=(52, 150), ra=(-45, -75), bounce=0.4),
      S(torso=16, ll=(72, 8), rl=(-38, -110), la=(-45, -75), ra=(52, 150), bounce=0.4))
cycle("jump", 1.2,
      S(ll=(-30, 8), rl=(30, -8), la=(-35, -60), ra=(35, 60), torso=4),
      S(la=(-160, -172), ra=(160, 172), ll=(-8, -12), rl=(8, 12), air=1.6))
cycle("jumping_jacks", 0.8, S(),
      S(la=(-140, -160), ra=(140, 160), ll=(-28, -26), rl=(28, 26), air=0.25))
cycle("dance", 0.9,
      S(la=(-140, -160), ra=(40, 60), ll=(-24, -12), rl=(10, 6), torso=-8, head=-8, bounce=0.2),
      S(la=(-40, -60), ra=(140, 160), ll=(-10, -6), rl=(24, 12), torso=8, head=8, bounce=0.2))
cycle("kick", 1.0,
      S(rl=(65, -8), la=(-60, -70), ra=(45, 30), torso=-4),
      S(rl=(88, 88), la=(-60, -70), ra=(45, 30), torso=-8))
cycle("punch", 0.8,
      S(ra=(70, -120), la=(-35, 150), ll=(-22, -12), rl=(22, 12), torso=6),
      S(ra=(92, 92), la=(-35, 150), ll=(-22, -12), rl=(22, 12), torso=10))
cycle("cartwheel", 1.6,
      S(spin=360, la=(-140, -150), ra=(140, 150), ll=(-30, -28), rl=(30, 28), air=0.6))

# ---- postures
static("sit", seat=1, ll=(80, 4), rl=(84, 6), la=(25, 70), ra=(35, 75), torso=2)
static("sit_think", seat=1, ll=(80, 4), rl=(84, 6), ra=(75, -130), la=(15, 75), head=7, torso=3)
static("kneel", ll=(5, -88), rl=(85, 5), ra=(70, 165))
static("crouch", ll=(-60, -2), rl=(60, 2), la=(-30, -5), ra=(30, 5), torso=6)
static("lie_down", rot=90, la=(-12, -6), ra=(12, 6), ll=(-4, -2), rl=(4, 2))
cycle("handstand", 1.6,
      S(rot=176, la=(-160, -172), ra=(160, 172), ll=(-6, -4), rl=(6, 4)),
      S(rot=184, la=(-160, -172), ra=(160, 172), ll=(-6, -4), rl=(6, 4)))
static("tree", ll=(0, 0), rl=(80, -50), la=(-148, -168), ra=(148, 168))
static("meditate", ll=(-80, 95), rl=(80, -95), la=(-10, 40), ra=(10, -40))
static("reach_up", la=(-160, -172), ra=(160, 172), head=-10)

ALIASES = {"point": "point_right", "greet": "wave", "idle": "stand", "think_hard": "think"}

GROUPS = {
    "neutral": ["stand", "relaxed", "hands_on_hips", "arms_crossed", "open_arms", "humble", "lean_in"],
    "gesture": ["point_right", "point_left", "point_up", "wave", "present", "explain", "shrug",
                "stop", "beckon", "salute", "clap"],
    "thinking": ["think", "scratch_head", "sit_think", "facepalm", "hands_on_head"],
    "emotion": ["cheer", "hands_up", "fist_pump", "flex", "sad_slump", "cry", "angry", "scared", "pray", "bow"],
    "movement": ["walk", "run", "jump", "jumping_jacks", "dance", "kick", "punch", "cartwheel"],
    "posture": ["sit", "kneel", "crouch", "lie_down", "handstand", "tree", "meditate", "reach_up"],
}
POSE_NAMES = [n for g in GROUPS.values() for n in g]
assert set(POSE_NAMES) == set(POSES), set(POSES) ^ set(POSE_NAMES)

MOODS = ["neutral", "happy", "sad", "angry", "surprised", "scared", "calm"]


def _full(partial):
    return {**BASE, **partial}


def _lerp(a, b, k):
    if isinstance(a, tuple):
        return tuple(x + (y - x) * k for x, y in zip(a, b))
    return a + (b - a) * k


def blend(a, b, k):
    out = {}
    for key in a:
        out[key] = (b[key] if k > 0.5 else a[key]) if key == "seat" else _lerp(a[key], b[key], k)
    return out


def pose_params(name, t):
    """Joint parameters for pose `name` at time `t` seconds."""
    period, keys = POSES.get(ALIASES.get(name, name), POSES["stand"])
    if period is None:
        P = _full(keys[0])
        sway = math.sin(t * 2 * math.pi * 0.6)
        P["la"] = (P["la"][0] - 2.5 * sway, P["la"][1] - 2.5 * sway)
        P["ra"] = (P["ra"][0] + 2.5 * sway, P["ra"][1] + 2.5 * sway)
        P["torso"] += 0.8 * sway
        phase = 0.0
    else:
        phase = (t / period) % 1.0
        n = len(keys)
        if n == 1:
            P = _full(keys[0])
        else:
            pos = phase * n
            i = int(pos) % n
            ease = 0.5 - 0.5 * math.cos(math.pi * (pos - int(pos)))
            P = blend(_full(keys[i]), _full(keys[(i + 1) % n]), ease)
    P["rot"] += P["spin"] * phase
    P["air"] += P["bounce"] * abs(math.sin(2 * math.pi * phase))
    return P


def layout(P, u, cx, base_y):
    """Forward kinematics. Returns joint positions (screen px) and total head angle."""
    def seg(o, a, ln):
        a = math.radians(a)
        return (o[0] + math.sin(a) * ln * u, o[1] + math.cos(a) * ln * u)

    t = math.radians(P["torso"])
    ha = math.radians(P["torso"] + P["head"])
    sh = (math.sin(t) * 2.5 * u, -math.cos(t) * 2.5 * u)
    side = (math.cos(t) * 0.5 * u, math.sin(t) * 0.5 * u)  # half shoulder width, along the shoulder line
    pts = {
        "hip": (0.0, 0.0),
        "sh": sh,
        "head": (sh[0] + math.sin(ha) * 1.15 * u, sh[1] - math.cos(ha) * 1.15 * u),
        "l_sh": (sh[0] - side[0], sh[1] - side[1]),
        "r_sh": (sh[0] + side[0], sh[1] + side[1]),
        "l_hip": (-0.28 * u, 0.0),
        "r_hip": (0.28 * u, 0.0),
    }
    for s, key in (("l", "la"), ("r", "ra")):
        e = seg(pts[s + "_sh"], P[key][0], 1.15)
        pts[s + "_elbow"], pts[s + "_hand"] = e, seg(e, P[key][1], 1.05)
    for s, key in (("l", "ll"), ("r", "rl")):
        k = seg(pts[s + "_hip"], P[key][0], 1.4)
        pts[s + "_knee"], pts[s + "_foot"] = k, seg(k, P[key][1], 1.35)

    rr = math.radians(P["rot"])
    c, sn = math.cos(rr), math.sin(rr)
    pts = {k: (x * c - y * sn, x * sn + y * c) for k, (x, y) in pts.items()}

    low = max(max(y for k, (_, y) in pts.items() if k != "head"), pts["head"][1] + 0.9 * u)
    dy = base_y - P["air"] * u - low
    return {k: (x + cx, y + dy) for k, (x, y) in pts.items()}, P["torso"] + P["head"] + P["rot"]
