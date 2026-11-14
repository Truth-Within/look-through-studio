"""Named poses. The 49 hand-authored poses from pipeline/poses.py are converted into joint space."""
from engine.skeleton import Pose
from pipeline import poses as legacy

# a few extra poses authored in the same screen-angle format (0 down, +90 right, 180 up)
legacy.static("bend_over", torso=70, head=20, la=(-4, 0), ra=(4, 0), ll=(-6, -2), rl=(6, 2))
legacy.static("lean_back", torso=-14, head=-10, la=(-14, -8), ra=(14, 8))
legacy.static("stretch", la=(-165, -178), ra=(165, 178), torso=-10, head=-12, ll=(-12, -8), rl=(12, 8))
legacy.static("squat", ll=(-82, -3), rl=(82, 3), la=(-40, 60), ra=(40, -60), torso=12)
legacy.static("sit_floor", ll=(78, 85), rl=(70, 80), la=(-20, 55), ra=(25, 60), torso=-3, head=0)
legacy.static("listening", head=12, torso=3, la=(-14, 40), ra=(14, -40))
legacy.static("hold_chest", la=(-30, 110), ra=(30, -110), head=14, torso=4)
legacy.static("lift_overhead", la=(-150, -170), ra=(150, 170), torso=-6, ll=(-14, -8), rl=(14, 8))
legacy.static("crouch_low", ll=(-70, -5), rl=(70, 5), la=(-20, 20), ra=(20, -20), torso=20, head=8)
legacy.static("pickup_low", ll=(-86, -2), rl=(86, 2), la=(-6, -2), ra=(8, 2), torso=78, head=28)
legacy.static("desk_lean", ll=(-14, -4), rl=(14, 4), torso=38, head=14, la=(-10, -4), ra=(10, 4))
legacy.static("hug_pose", torso=8, head=8, la=(-14, -8), ra=(14, 8))
legacy.static("stumble", torso=-18, head=-14, la=(-110, -120), ra=(100, 130), ll=(-20, -8), rl=(34, 16))
legacy.cycle("crawl", 1.0,
             legacy.S(rot=78, la=(-10, -20), ra=(24, 6), ll=(-8, -70), rl=(20, 4), torso=-6, head=-20),
             legacy.S(rot=78, la=(24, 6), ra=(-10, -20), ll=(20, 4), rl=(-8, -70), torso=-6, head=-20))
legacy.cycle("climb", 1.2,
             legacy.S(la=(-170, -176), ra=(120, 160), ll=(-20, -40), rl=(35, -5), torso=4, head=-20),
             legacy.S(la=(-120, -160), ra=(170, 176), ll=(35, -5), rl=(-20, -40), torso=4, head=-20))
legacy.GROUPS["posture"] += ["desk_lean", "hug_pose", "pickup_low", "bend_over", "lean_back", "stretch", "squat", "sit_floor", "listening", "hold_chest",
                             "lift_overhead", "crouch_low"]
legacy.GROUPS["movement"] += ["stumble", "crawl", "climb"]
legacy.POSE_NAMES[:] = [n for g in legacy.GROUPS.values() for n in g]

POSE_NAMES = legacy.POSE_NAMES


def from_legacy(P):
    """Convert a legacy absolute-angle pose dict into a joint-space Pose."""
    T = P["torso"]
    J = {"spine": T * 0.5, "chest": T * 0.5, "head": P["head"]}
    for s, key in (("L", "la"), ("R", "ra")):
        up, lo = P[key]
        J["uarm_" + s] = -up - T
        J["farm_" + s] = up - lo
    for s, key in (("L", "ll"), ("R", "rl")):
        th, sh = P[key]
        J["thigh_" + s] = -th
        J["shin_" + s] = th - sh
    from engine.skeleton import wrap180
    return Pose({k: wrap180(v) for k, v in J.items()}, rot=P["rot"], air=P["air"])


def named_pose(name, t=0.0):
    """Pose `name` at time t seconds (cycles animate, static poses get a tiny idle sway)."""
    return from_legacy(legacy.pose_params(name, t))


def period(name):
    return legacy.POSES.get(legacy.ALIASES.get(name, name), legacy.POSES["stand"])[0]


def exists(name):
    return legacy.ALIASES.get(name, name) in legacy.POSES
