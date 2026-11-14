"""Procedural gaits (distance-driven so planted feet never slide), plus easy beat helpers."""
import math

from engine import library as lib
from engine.skeleton import Pose, ik2, wrap180

GAITS = {
    "walk": dict(S=4.4, duty=0.62, lift=0.40, lean=3, arm=30, elbow=16, speed=3.6, air=0.0),
    "jog": dict(S=5.6, duty=0.46, lift=0.65, lean=8, arm=40, elbow=70, speed=5.5, air=0.10),
    "run": dict(S=7.0, duty=0.38, lift=0.95, lean=14, arm=52, elbow=90, speed=8.0, air=0.26),
    "sprint": dict(S=8.4, duty=0.32, lift=1.15, lean=22, arm=62, elbow=96, speed=11.0, air=0.38),
}


def _ease(w):
    return w * w * (3 - 2 * w)


def gait_pose(kind, dist_px, c0, u, limb=1.0, var=1.0):
    """Pose of a gait cycle after travelling dist_px (character-local frame, facing +x)."""
    g = GAITS[kind]
    l1, l2 = 1.4 * limb * u, 1.35 * limb * u
    c = c0 + dist_px / (g["S"] * u)
    d = g["duty"]
    hh = (l1 + l2) * (0.84 + 0.02 * abs(math.sin(2 * math.pi * c)))
    J = {}
    air = 0.0
    for s, off in (("L", 0.0), ("R", 0.5)):
        p = (c + off) % 1.0
        half = 0.5 * g["S"] * d * u
        if p < d:
            fx, lift = half * (1 - 2 * p / d), 0.0
        else:
            w = (p - d) / (1 - d)
            fx, lift = -half + 2 * half * _ease(w), g["lift"] * u * math.sin(math.pi * w)
        p1, p2, _ = ik2((0.0, 0.0), (fx, hh - lift), l1, l2, -1)
        J["thigh_" + s] = wrap180(p1 - 180)
        J["shin_" + s] = wrap180(p2 - p1)
        fp = (c + (0.5 if s == "L" else 0.0)) % 1.0  # arm swings against the same-side leg
        swing = -g["arm"] * var * math.cos(2 * math.pi * ((c + off) % 1.0))
        J["uarm_" + s] = -swing
        J["farm_" + s] = -(g["elbow"] * (0.6 + 0.4 * max(0.0, swing / g["arm"])))
    if g["air"] > 0 and d < 0.5:
        p0 = c % 1.0
        for a, b in ((d, 0.5), (0.5 + d, 1.0)):
            if a <= p0 < b:
                air = g["air"] * math.sin(math.pi * (p0 - a) / (b - a))
    J["spine"], J["chest"] = g["lean"] * 0.5, g["lean"] * 0.5
    J["head"] = -g["lean"] * 0.6
    return Pose(J, air=air * 2.5)


def named(name, offset=0.0):
    return lambda tau, dist: lib.named_pose(name, tau + offset)


def cyclic_by_distance(name, S_u, u):
    per = lib.period(name) or 1.0
    return lambda tau, dist: lib.named_pose(name, (dist / (S_u * u)) * per)
