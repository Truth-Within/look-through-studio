"""Hierarchical 2D skeleton: forward kinematics, joint limits, two-bone IK.

Angles are degrees, clockwise from straight UP, in a character-local frame where the character
faces +x. A joint *value* is a rotation relative to the parent bone's rest direction.
"""
import math

BONES = {
    # name: (parent, length in u, rest angle, min value, max value)
    "spine": (None, 1.2, 0, -35, 80),
    "chest": ("spine", 1.3, 0, -25, 60),
    "neck": ("chest", 0.3, 0, -40, 40),
    "head": ("neck", 0.85, 0, -60, 60),
}
for _s in "LR":
    BONES[f"uarm_{_s}"] = ("chest", 1.15, 180, -200, 200)
    BONES[f"farm_{_s}"] = (f"uarm_{_s}", 1.05, 0, -178, 178)
    BONES[f"thigh_{_s}"] = (None, 1.4, 180, -130, 130)
    BONES[f"shin_{_s}"] = (f"thigh_{_s}", 1.35, 0, -150, 150)
    BONES[f"foot_{_s}"] = (f"shin_{_s}", 0.55, -90, -60, 60)
ORDER = list(BONES)  # parents always precede children

# radius (in u) of each point, used for ground contact
RADIUS = {"hand": 0.12, "toe": 0.14, "heel": 0.14, "ankle": 0.14, "knee": 0.12, "hip": 0.15,
          "sh": 0.1, "elbow": 0.1, "waist": 0.2, "neck": 0.1}


def wrap180(a):
    return (a + 180.0) % 360.0 - 180.0


class Pose:
    """Joint values + whole-body rotation about the hip, lift off the ground, and foot flattening."""
    __slots__ = ("J", "rot", "air", "flat")

    def __init__(self, J=None, rot=0.0, air=0.0, flat=1.0):
        self.J = dict.fromkeys(BONES, 0.0)
        if J:
            self.J.update(J)
        self.rot, self.air, self.flat = float(rot), float(air), float(flat)

    def copy(self):
        return Pose(self.J, self.rot, self.air, self.flat)

    def to_dict(self):
        return {"J": {k: round(v, 3) for k, v in self.J.items()}, "rot": round(self.rot, 3),
                "air": round(self.air, 3), "flat": round(self.flat, 3)}

    @staticmethod
    def from_dict(d):
        return Pose(d["J"], d["rot"], d["air"], d["flat"])


def lerp_pose(a, b, k):
    return Pose({n: a.J[n] + (b.J[n] - a.J[n]) * k for n in BONES},
                a.rot + (b.rot - a.rot) * k, a.air + (b.air - a.air) * k, a.flat + (b.flat - a.flat) * k)


def _vec(phi, ln, u):
    r = math.radians(phi)
    return (math.sin(r) * ln * u, -math.cos(r) * ln * u)


def _add(p, q):
    return (p[0] + q[0], p[1] + q[1])


def fk(pose, u, theta=60.0, build=None, viol=None):
    """Forward kinematics. Returns (points, absolute angles). Points are px relative to the hip.

    theta is the heading: 0 = facing the viewer, +90 = facing right, -90 = facing left, 180 = back.
    """
    b = build or {}
    limb, torso, headk, width = b.get("limb", 1.0), b.get("torso", 1.0), b.get("head", 1.0), b.get("width", 1.0)
    c = math.cos(math.radians(theta))
    fwd = 1 if math.sin(math.radians(theta)) >= 0 else -1

    def length(name):
        ln = BONES[name][1]
        if name in ("spine", "chest"):
            return ln * torso
        if name in ("neck", "head"):
            return ln * headk
        return ln * limb

    ab = {}
    for name in ORDER:
        parent, _, rest, lo, hi = BONES[name]
        v = pose.J[name]
        if viol is not None and (v < lo - 2 or v > hi + 2):
            viol.append((name, round(v, 1)))
        v = min(hi, max(lo, v))
        base = pose.rot if parent is None else ab[parent]
        a = base + rest + v
        if name.startswith("foot"):
            flat = 90.0 + pose.rot + v
            a = a + (flat - a) * pose.flat
        ab[name] = a

    P = {"hip": (0.0, 0.0)}
    P["waist"] = _vec(ab["spine"], length("spine"), u)
    P["neck"] = _add(P["waist"], _vec(ab["chest"], length("chest"), u))
    P["head"] = _add(_add(P["neck"], _vec(ab["neck"], length("neck"), u)), _vec(ab["head"], length("head"), u))
    for s, sg in (("L", -1), ("R", 1)):
        lat = sg * (0.5 * c + 0.12 * (1 - abs(c))) * width
        sh = _add(P["neck"], _vec(ab["chest"] + 90, lat, u))
        P["sh_" + s] = sh
        P["elbow_" + s] = _add(sh, _vec(ab["uarm_" + s], length("uarm_" + s), u))
        P["hand_" + s] = _add(P["elbow_" + s], _vec(ab["farm_" + s], length("farm_" + s), u))
        hp = (sg * (0.28 * c + 0.06 * (1 - abs(c))) * width * u, 0.0)
        P["hip_" + s] = hp
        P["knee_" + s] = _add(hp, _vec(ab["thigh_" + s], length("thigh_" + s), u))
        P["ankle_" + s] = _add(P["knee_" + s], _vec(ab["shin_" + s], length("shin_" + s), u))
        P["toe_" + s] = _add(P["ankle_" + s], _vec(ab["foot_" + s], length("foot_" + s), u))
        P["heel_" + s] = _add(P["ankle_" + s], _vec(ab["foot_" + s], -0.12 * limb, u))
    if fwd < 0:
        P = {k: (-x, y) for k, (x, y) in P.items()}
    return P, ab


def lowest(P, u, headk=1.0):
    """Largest y (px) any body part reaches, including its radius."""
    low = P["head"][1] + 0.9 * u * headk
    for k, (_, y) in P.items():
        r = RADIUS.get(k.split("_")[0], 0.1)
        low = max(low, y + r * u)
    return low


def ik2(origin, target, l1, l2, bend):
    """Analytic two-bone IK in the local frame. bend=+1 puts the joint on the clockwise side
    (elbows point backwards), bend=-1 on the counter-clockwise side (knees point forwards)."""
    dx, dy = target[0] - origin[0], target[1] - origin[1]
    d = math.hypot(dx, dy)
    lo = max(abs(l1 - l2) + 1e-3, math.sqrt(l1 * l1 + l2 * l2 - 2 * l1 * l2 * math.cos(math.radians(32))))
    hi = l1 + l2 - 1e-3
    tol = 0.05 * (l1 + l2)
    ok = lo - tol <= d <= hi + tol
    dc = min(hi, max(lo, d))
    if d > 1e-6:
        target = (origin[0] + dx / d * dc, origin[1] + dy / d * dc)
    d = dc
    cos_a = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)
    A = math.degrees(math.acos(max(-1.0, min(1.0, cos_a))))
    p1 = math.degrees(math.atan2(dx, -dy)) + bend * A
    e = (origin[0] + math.sin(math.radians(p1)) * l1, origin[1] - math.cos(math.radians(p1)) * l1)
    p2 = math.degrees(math.atan2(target[0] - e[0], -(target[1] - e[1])))
    return p1, p2, ok


def solve_limb(pose, u, theta, build, root, side, kind, target_world, weight=1.0):
    """Overwrite the arm ('arm') or leg ('leg') joint values so the hand/ankle reaches target_world.

    Returns True if the target was reachable. weight < 1 blends the IK result with the existing pose.
    """
    P, ab = fk(pose, u, theta, build)
    fwd = 1 if math.sin(math.radians(theta)) >= 0 else -1
    limb = (build or {}).get("limb", 1.0)
    if kind == "arm":
        o_name, up, lo_, bend = "sh_" + side, "uarm_" + side, "farm_" + side, 1
    else:
        o_name, up, lo_, bend = "hip_" + side, "thigh_" + side, "shin_" + side, -1
    o = (P[o_name][0] * fwd, P[o_name][1])  # back into the right-facing local frame
    t = ((target_world[0] - root[0]) * fwd, target_world[1] - root[1])
    l1, l2 = BONES[up][1] * limb * u, BONES[lo_][1] * limb * u
    o = (o[0], o[1])
    p1, p2, ok = ik2(o, t, l1, l2, bend)
    parent_up = pose.rot if BONES[up][0] is None else ab[BONES[up][0]]
    v1 = wrap180(p1 - parent_up - BONES[up][2])
    v2 = wrap180(p2 - p1 - BONES[lo_][2])
    pose.J[up] += (v1 - pose.J[up]) * weight
    pose.J[lo_] += (v2 - pose.J[lo_]) * weight
    return ok
