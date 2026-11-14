"""Action library. Complex acts are composed from simple beats, IK reaches, prop events and expressions."""
import math

from engine import motion
from engine.performance import Beat
from engine.props import SPECS
from engine.stage import fwd_of

REST_H = {"book": 0.6, "apple": 0.22, "phone": 0.26, "box": 0.55}
REACTIONS = {"surprise": "lean_back", "fear": "scared", "panic": "scared", "anger": "angry", "frustration": "hands_on_head",
             "sadness": "sad_slump", "grief": "cry", "confusion": "scratch_head", "laughter": "hands_on_hips",
             "excited": "cheer", "happy": "open_arms", "embarrassment": "hands_on_head", "realization": "point_up",
             "disgust": "lean_back", "determination": "flex", "skepticism": "arms_crossed", "curiosity": "lean_in",
             "anxiety": "scared", "fatigue": "sad_slump", "confidence": "hands_on_hips", "concentration": "think",
             "contemplation": "think", "amused": "hands_on_hips"}
ACT = {}
NOLOCK = ("jump", "dance", "hop", "kick", "punch", "cheer", "fall", "stumble", "crawl", "climb", "jacks", "cartwheel", "wave_off")


def act(*names):
    def deco(f):
        for n in names:
            ACT[n] = f
        return f
    return deco


class Actor:
    def __init__(self, aid, perf, x, theta, support=0.0):
        self.id, self.perf, self.x, self.theta, self.support, self.t = aid, perf, x, theta, support, 0.0
        self.seat = self.lying = None
        self.holding, self.carry_ik = {}, None
        self.allow, self.sticky = set(), set()


class Ctx:
    def __init__(self, stage, actors, rng):
        self.s, self.A, self.rng = stage, actors, rng
        self.u, self.W, self.gy = stage.u, stage.W, stage.gy
        self.speed, self.blend_mult = 1.0, 1.0

    def prop_xy(self, pid, t):
        st = self.s.prop_state(pid, t, pre=True)
        return st["x"], st["y"]

    def actor_x(self, aid, t):
        return self.s.perfs[aid].solve(max(0.0, t), ik=False)["x"]


# ------------------------------------------------------------------ helpers
def B(c, A, name, dur, pose=None, fn=None, **kw):
    dur = dur / c.speed
    kw["blend"] = kw.get("blend", 0.3) * c.blend_mult
    kw["tags"] = set(kw.get("tags", ())) | A.allow
    kw.setdefault("support", A.support)
    kw.setdefault("theta", A.theta)
    kw["tags"] = set(kw["tags"]) | A.sticky
    if ("lock" not in kw and kw.get("x1") is None and kw.get("support") == 0 and A.lying is None
            and not any(k in name for k in NOLOCK)):
        kw["lock"] = True  # planted feet stay planted while the upper body acts
    if A.carry_ik and "ik" not in kw:
        kw["ik"] = A.carry_ik
    if pose is not None and fn is None:
        fn = motion.named(pose, kw.pop("phase", 0.0))
    b = Beat(name, A.t, dur, fn=fn, **kw)
    b.seated = A.seat is not None
    A.perf.add(b)
    A.t += b.dur
    if b.x1 is not None:
        A.x = b.x1
    A.theta = b.theta1
    A.support = b.support(b.dur) if callable(b.support) else b.support
    return b


def stance(A):
    return "sit" if A.seat else ("lie_down" if A.lying else "relaxed")


def face_toward(c, A, x, view=38):
    d = 1 if x >= A.x else -1
    if abs(A.theta - view * d) > 8:
        B(c, A, "turn", 0.4, pose=stance(A), theta=view * d)


def target_x(c, A, a):
    tg = a.get("target")
    if a.get("x") is not None:
        return float(a["x"]) * c.W
    if tg in c.A:
        return c.actor_x(tg, A.t)
    if tg in c.s.props:
        return c.prop_xy(tg, A.t)[0]
    return A.x


def stand_if_needed(c, A):
    if A.lying:
        ACT["wake_up"](c, A, {"target": A.lying, "quick": True})
    if A.seat:
        ACT["stand_up"](c, A, {})


def go(c, A, kind, xd, gap=0.0, tags=()):
    u = c.u
    stand_if_needed(c, A)
    d = 1 if xd >= A.x else -1
    xd = min(max(xd - d * gap * u, 0.07 * c.W), 0.93 * c.W)
    D = abs(xd - A.x)
    if D < 0.25 * u:
        return
    d = 1 if xd > A.x else -1
    if abs(A.theta - 90 * d) > 15:
        B(c, A, "turn", 0.35, pose=stance(A), theta=90 * d)
    g = motion.GAITS[kind]
    T = max(0.7, D / (g["speed"] * u) / 0.82) * c.speed
    c0 = (g["duty"] / 2 - D / (g["S"] * u)) % 1.0
    var = 1 + 0.1 * (c.rng.random() - 0.5)
    limb = c.s.builds[A.id].get("limb", 1.0)
    B(c, A, f"{kind}_to", T, fn=lambda tau, dist: motion.gait_pose(kind, dist, c0, u, limb, var), x1=xd, path="trap",
      theta=90 * d, blend=0.25, idle=False, tags=tags)
    A.sticky = set()


def surface_of(c, pid, t):
    """id of the solid surface prop (desk...) an item sits on, if any."""
    x, y = c.prop_xy(pid, t)
    for q, Q in c.s.props.items():
        sp = SPECS[Q.type]
        if q != pid and sp["solid"] and sp["surface"]:
            qx = c.prop_xy(q, t)[0]
            if qx + sp["solid"][0] * c.u - 0.3 * c.u <= x <= qx + sp["solid"][1] * c.u + 0.3 * c.u and abs(y - (c.gy - sp["surface"] * c.u)) < 0.8 * c.u:
                return q
    return None


def mouth():
    return ("body", "head", 0.7, 0.45)


# ------------------------------------------------------------------ posture / expression
@act("stand", "idle", "hold", "pose")
def a_stand(c, A, a):
    th = A.theta
    if not (A.seat or A.lying) and abs(math.sin(math.radians(A.theta))) > 0.9:
        th = 38 * fwd_of(A.theta)
    name = a.get("pose") or stance(A)
    B(c, A, "stand", a.get("duration", 1.0), pose=name, theta=th)


@act("express", "emote")
def a_express(c, A, a):
    A.perf.express(A.t, a.get("emotion", "neutral"))


@act("react")
def a_react(c, A, a):
    emo = a.get("emotion", "surprise")
    A.perf.express(A.t, emo, 0.2)
    pose = "sit" if A.seat else REACTIONS.get(emo, "shrug")
    B(c, A, "react", a.get("duration", 1.1), pose="sit_think" if A.seat and emo in ("concentration", "contemplation") else pose)


@act("look_at")
def a_look(c, A, a):
    tg = a.get("target")
    if tg in c.A:
        spec = ("actor", tg, "head", 0, 0)
    elif tg in c.s.props:
        spec = ("prop", tg, "top") if "top" in SPECS[c.s.props[tg].type]["grips"]({}) else ("fn", lambda t, pre, st, aid, p=tg: st.prop_point(p, "none", t))
    elif a.get("x") is not None:
        spec = ("pt", float(a["x"]) * c.W, c.gy - 5 * c.u)
    else:
        spec = None
    A.perf.look(A.t, spec)
    if a.get("duration"):
        A.t += 0.0


@act("turn_to", "turn")
def a_turn(c, A, a):
    tg = a.get("target", "")
    view = {"viewer": 0, "camera": 0, "away": 180}.get(tg)
    if view is None:
        view = 38 * (1 if target_x(c, A, a) >= A.x else -1)
    B(c, A, "turn", a.get("duration", 0.6), pose=stance(A), theta=view)


@act("wave")
def a_wave(c, A, a):
    if a.get("target") in c.A:
        face_toward(c, A, c.actor_x(a["target"], A.t))
    A.perf.express(A.t, a.get("emotion", "happy"))
    B(c, A, "wave", a.get("duration", 1.4), pose="wave")


@act("clap", "cheer", "dance", "jump", "flex", "salute", "pray", "bow", "shrug", "cross_arms", "think", "stretch",
     "stumble", "kick", "punch", "dance", "listen", "bend", "lean")
def a_pose_action(c, A, a):
    name = {"cross_arms": "arms_crossed", "listen": "listening", "bend": "bend_over", "lean": "lean_in", "think": "think"}.get(a["do"], a["do"])
    if a["do"] in ("jump", "dance", "kick", "punch", "cheer") or a["do"] == "clap":
        stand_if_needed(c, A)
    if a["do"] == "listen":
        A.perf.express(A.t, "concentration")
    if a["do"] == "think":
        A.perf.express(A.t, "contemplation")
    th = 38 * fwd_of(A.theta) if (abs(math.sin(math.radians(A.theta))) > 0.9 and not A.seat) else A.theta
    B(c, A, a["do"], a.get("duration", {"jump": 1.2, "dance": 3.0, "stumble": 1.0}.get(a["do"], 1.6)), pose=name, theta=th)


@act("hop")
def a_hop(c, A, a):
    stand_if_needed(c, A)
    B(c, A, "hop", a.get("duration", 1.6),
      fn=lambda tau, d: _hop(tau))


def _hop(tau):
    from engine import library as lib
    p = lib.named_pose("stand", 0)
    k = abs(math.sin(math.pi * tau / 0.5))
    p.air = 0.55 * k
    for s in "LR":
        p.J["thigh_" + s] = (-1 if s == "L" else 1) * 8 * (1 - k)
        p.J["shin_" + s] = (-1 if s == "L" else 1) * -12 * (1 - k)
    return p


# ------------------------------------------------------------------ locomotion
for _name, _kind in (("walk_to", "walk"), ("jog_to", "jog"), ("run_to", "run"), ("sprint_to", "sprint"), ("walk", "walk"),
                     ("run", "run"), ("go_to", "walk"), ("approach", "walk"), ("follow", "walk")):
    def _mk(kind):
        def f(c, A, a):
            tg = a.get("target")
            gap = 0.0
            if tg in c.A:
                gap = 2.8
            elif tg in c.s.props:
                sol = SPECS[c.s.props[tg].type]["solid"]
                gap = (sol[1] + 1.0) if sol else 1.6
            if a.get("x") is not None:
                gap = 0.0
            go(c, A, kind, target_x(c, A, a), gap=gap)
        return f
    ACT[_name] = _mk(_kind)


@act("crawl_to", "crawl")
def a_crawl(c, A, a):
    stand_if_needed(c, A)
    xd = min(max(target_x(c, A, a), 0.07 * c.W), 0.93 * c.W)
    d = 1 if xd >= A.x else -1
    D = abs(xd - A.x)
    if D < 0.3 * c.u:
        return
    B(c, A, "crawl_to", max(1.0, D / (0.9 * c.u)), fn=motion.cyclic_by_distance("crawl", 2.2, c.u), x1=xd, path="trap",
      theta=90 * d, idle=False, approx=True)


@act("climb")
def a_climb(c, A, a):
    pid = a.get("target")
    stand_if_needed(c, A)
    if pid in c.s.props:
        go(c, A, "walk", c.prop_xy(pid, A.t)[0] - 0.0)
    rise = min(float(a.get("height", 2.0)), (c.gy - 8.0 * c.u) / c.u) * c.u
    d = fwd_of(A.theta)
    from engine import library as lib
    dur = a.get("duration", 3.5)
    B(c, A, "climb", dur, fn=lambda tau, dist: lib.named_pose("climb", tau), support=lambda tau, r=rise, T=dur: r * (tau / T),
      theta=90 * d, idle=False, approx=True, tags=(pid,) if pid else ())


@act("fall")
def a_fall(c, A, a):
    stand_if_needed(c, A)
    A.perf.express(A.t, "surprise", 0.15)
    B(c, A, "stumble", 0.5, pose="stumble")
    from engine import library as lib

    def fall_fn(tau, dist):
        p = lib.named_pose("lie_down", tau)
        k = min(1.0, tau / 0.9)
        p.rot = 90 * (k * k * (3 - 2 * k))
        p.air = 0.5 * math.sin(math.pi * min(1.0, tau / 0.9))
        return p
    B(c, A, "fall", 1.0, fn=fall_fn, blend=0.2, idle=False)
    A.lying = "ground"
    A.perf.express(A.t, "sadness")


@act("get_up", "recover")
def a_get_up(c, A, a):
    if A.lying == "ground":
        B(c, A, "get_up", 0.9, pose="crouch_low", blend=0.7)
        A.lying = None
    stand_if_needed(c, A)
    B(c, A, "stand", 0.8, pose="relaxed")


# ------------------------------------------------------------------ sitting, lying, kneeling
@act("sit_down", "sit_on", "sit")
def a_sit(c, A, a):
    if A.seat:
        return
    u = c.u
    P = c.s.props.get(a.get("target"))
    if A.lying:
        ACT["wake_up"](c, A, {"target": A.lying, "quick": True, "sit_only": True})
        if P is None or P.type == "bed":
            return
    if P is not None:
        px, _ = c.prop_xy(P.id, A.t)
        d = P.facing
        seat_x = px + (3.0 * u * d if P.type == "bed" else 0.0)
        if P.type == "chair":
            for q in c.s.props.values():
                sol = SPECS[q.type]["solid"]
                qx = c.prop_xy(q.id, A.t)[0]
                if sol and SPECS[q.type]["surface"] and qx + sol[0] * u - 0.3 * u < seat_x + d * 1.3 * u < qx + sol[1] * u + 0.3 * u:
                    ACT["pull_chair"](c, A, {"target": P.id})
                    px = c.prop_xy(P.id, A.t)[0]
                    seat_x = px
                    break
        go(c, A, "walk", seat_x + d * 1.3 * u)
        if abs(A.theta - 90 * d) > 5:
            B(c, A, "turn", 0.3, pose="relaxed", theta=90 * d)
        B(c, A, "sit_down", a.get("duration", 1.1), pose="sit", x1=seat_x, path="ease", lock=True, theta=90 * d,
          tags=(P.id,), blend=0.8)
        A.seat = P.id
    else:
        d = fwd_of(A.theta)
        stand_if_needed(c, A)
        B(c, A, "sit_floor", a.get("duration", 1.2), pose="sit_floor", lock=True, theta=90 * d, blend=0.9)
        A.seat = "floor"


@act("stand_up")
def a_stand_up(c, A, a):
    if A.lying:
        ACT["wake_up"](c, A, {"target": A.lying, "quick": True, "sit_only": True})
    if not A.seat:
        return
    d = fwd_of(A.theta)
    B(c, A, "stand_up", a.get("duration", 1.0), pose="relaxed", x1=A.x + (1.3 * c.u * d if A.seat != "floor" else 2.2 * c.u * d),
      path="ease", lock=True, theta=90 * d, blend=0.8, tags=(A.seat,))
    A.seat = None


@act("squat", "crouch")
def a_squat(c, A, a):
    stand_if_needed(c, A)
    B(c, A, a["do"], a.get("duration", 1.5), pose="squat" if a["do"] == "squat" else "crouch_low", lock=True, blend=0.6)


@act("kneel")
def a_kneel(c, A, a):
    stand_if_needed(c, A)
    B(c, A, "kneel", a.get("duration", 1.6), pose="kneel", blend=0.7)


@act("lie_down", "sleep")
def a_lie(c, A, a):
    P = c.s.props.get(a.get("target"))
    if P is None:
        stand_if_needed(c, A)
        B(c, A, "lie_down", 1.2, pose="lie_down", blend=0.9)
        A.lying = "ground"
        return
    u, d = c.u, P.facing
    px, _ = c.prop_xy(P.id, A.t)
    if not A.seat:
        ACT["sit_down"](c, A, {"target": P.id})
    top = 1.45 * u

    def lie(tau, dist, tt=A.t):
        from engine import library as lib
        p = lib.named_pose("lie_down", tau)
        p.rot = -90
        return p
    B(c, A, "lie_back", a.get("duration", 1.4), fn=lie, x1=px + 0.8 * u * d, path="ease", support=top, theta=90 * d,
      blend=0.9, tags=(P.id,))
    A.seat, A.lying = None, P.id
    A.perf.express(A.t, "sleepy", 0.6)


@act("wake_up")
def a_wake(c, A, a):
    P = c.s.props.get(a.get("target")) or next((p for p in c.s.props.values() if p.type == "bed"), None)
    if P is None:
        return
    u, d = c.u, P.facing
    px, _ = c.prop_xy(P.id, A.t)
    top = 1.45 * u

    def lie(tau, dist):
        from engine import library as lib
        p = lib.named_pose("lie_down", tau)
        p.rot = -90
        return p
    if not A.lying:
        A.perf.express(A.t, "sleepy", 0.01)
        B(c, A, "asleep", 0.05, fn=lie, x1=px + 0.8 * u * d, path="ease", support=top, theta=90 * d, blend=0.01, tags=(P.id,))
        A.lying = P.id
    if not a.get("quick"):
        B(c, A, "asleep", a.get("sleep", 0.9), fn=lie, support=top, blend=0.01, tags=(P.id,))
        A.perf.express(A.t, "confusion", 0.5)

    def sit_up(tau, dist):
        from engine import library as lib
        p = lib.named_pose("sit_floor", tau)
        return p
    B(c, A, "sit_up", 1.0 if not a.get("quick") else 0.7, pose="sit_floor", support=top, theta=90 * d, blend=0.9, tags=(P.id,))
    A.lying, A.seat = None, "bed_long"
    if a.get("sit_only"):
        # swing legs off the end of the bed and sit on the edge
        B(c, A, "sit_edge", 0.9, pose="sit", x1=px + 3.0 * u * d, path="ease", support=lambda tau, T=0.9: top * (1 - min(1.0, tau / T)),
          theta=90 * d, blend=0.8, tags=(P.id,))
        A.seat = P.id
        return
    if not a.get("quick"):
        A.perf.look(A.t, ("pt", c.W * (0.5 + 0.3 * d), c.gy - 4 * u))
        B(c, A, "look_around", 0.9, pose="listening", support=top, blend=0.5, tags=(P.id,))
        A.perf.look(A.t, None)
        B(c, A, "sit_edge", 0.9, pose="sit", x1=px + 3.0 * u * d, path="ease", support=lambda tau, T=0.9: top * (1 - min(1.0, tau / T)),
          theta=90 * d, blend=0.8, tags=(P.id,))
        A.seat = P.id


# ------------------------------------------------------------------ hands & objects
def _grip_name(ptype, prefer=("grip", "R", "top", "handle", "write", "back")):
    g = SPECS[ptype]["grips"]({})
    for n in prefer:
        if n in g:
            return n
    return next(iter(g), "none")


@act("point_at")
def a_point(c, A, a):
    tx = target_x(c, A, a)
    ty = c.gy - 4.5 * c.u
    if a.get("target") in c.s.props:
        ty = c.prop_xy(a["target"], A.t)[1] - 1.5 * c.u
    face_toward(c, A, tx, 45)
    d = 1 if tx >= A.x else -1
    side = "R" if d > 0 else "L"
    sh = "sh_" + side

    def tgt(t, pre, st, aid):
        dx, dy = tx - pre[sh][0], ty - pre[sh][1]
        n = math.hypot(dx, dy) or 1
        return pre[sh][0] + dx / n * 2.0 * st.u, pre[sh][1] + dy / n * 2.0 * st.u
    A.perf.look(A.t, ("pt", tx, ty))
    B(c, A, "point", a.get("duration", 1.5), pose=stance(A), ik={side: (("fn", tgt), 0.4)})
    A.perf.look(A.t, None)


@act("reach_for", "reach")
def a_reach(c, A, a):
    tg = a.get("target")
    if tg in c.s.props:
        px = c.prop_xy(tg, A.t)[0]
        if not A.seat and abs(px - A.x) > 1.8 * c.u:
            go(c, A, "walk", px, gap=1.4)
        spec = ("prop", tg, _grip_name(c.s.props[tg].type))
    elif tg in c.A:
        spec = ("actor", tg, "hand_R", 0, 0)
    else:
        spec = ("pt", target_x(c, A, a), c.gy - 5.5 * c.u)
    face_toward(c, A, spec[1] if isinstance(spec[1], float) else target_x(c, A, a), 50)
    side = "R"
    B(c, A, "reach", a.get("duration", 1.2), pose=stance(A), ik={side: (spec, 0.4)})


def _surface_dest(c, A, a):
    u = c.u
    on = a.get("on")
    if on in c.s.props:
        S = c.s.props[on]
        sx, _ = c.prop_xy(on, A.t)
        h = (SPECS[S.type]["surface"] or 0.0) * u
        return sx + float(a.get("dx", 0.0)) * u, c.gy - h
    best = None
    for pid, P in c.s.props.items():
        if SPECS[P.type]["surface"] and SPECS[P.type]["solid"] and abs(c.prop_xy(pid, A.t)[0] - A.x) < 3.2 * u:
            best = pid
            break
    if best:
        sx, _ = c.prop_xy(best, A.t)
        P = c.s.props[best]
        return sx + float(a.get("dx", -0.3)) * u * P.facing, c.gy - SPECS[P.type]["surface"] * u
    return A.x + 1.2 * u * fwd_of(A.theta), c.gy


@act("pick_up", "grab", "carry", "lift")
def a_pick_up(c, A, a):
    pid = a.get("target")
    P = c.s.props.get(pid)
    if P is None or pid in A.holding:
        return
    u = c.u
    px, py = c.prop_xy(pid, A.t)
    sf = surface_of(c, pid, A.t)
    if sf:
        A.allow.add(sf)
    on_surface = sf is not None
    low = (c.gy - py) < 1.2 * u and not A.seat
    if not A.seat and abs(px - A.x) > (1.3 if on_surface else 1.0) * u:
        go(c, A, "walk", px, gap=2.4 if low else (1.1 if on_surface else 1.3))
    face_toward(c, A, px, 55)
    anchor = SPECS[P.type]["hold"] == "anchor" or a["do"] in ("carry", "lift")
    grip = _grip_name(P.type) if not anchor else ("R" if "R" in SPECS[P.type]["grips"]({}) else _grip_name(P.type))
    B(c, A, "reach", 0.8, pose="pickup_low" if low else ("desk_lean" if (on_surface and not A.seat) else stance(A)),
      ik={"R": (("prop", pid, grip), 0.4)}, tags=(pid,))
    P.set_phase(A.t, kind="hand", actor=A.id, side="R", off=(0.0, 0.0))
    if not anchor:
        B(c, A, "lift", 0.5, pose=stance(A), ik={"R": (("body", "sh_R", 0.5, 1.9), 0.4)})
        A.holding[pid] = "hand"
        return
    B(c, A, "raise", 0.6, pose=stance(A), ik={"R": (("body", "neck", 0.95, 0.85), 0.35)})
    P.set_phase(A.t, kind="anchor", actor=A.id, name="chest_front", off=(0.0, 0.0), rot=0.0)
    A.holding[pid] = "anchor"
    A.carry_ik = {"L": (("prop", pid, "L"), 0.3), "R": (("prop", pid, "R"), 0.3)}
    if a["do"] == "lift":
        P.set_phase(A.t, kind="anchor", actor=A.id, name="overhead", off=(0.0, 0.0), rot=0.0)
        A.carry_ik = {"L": (("prop", pid, "L"), 0.3), "R": (("prop", pid, "R"), 0.3)}
        B(c, A, "lift_up", 0.9, pose="lift_overhead")


@act("put_down", "place", "drop")
def a_put_down(c, A, a):
    pid = a.get("target") or next(iter(A.holding), None)
    P = c.s.props.get(pid)
    if P is None or pid not in A.holding:
        return
    u = c.u
    dx, dy = _surface_dest(c, A, a)
    ydest = dy - REST_H.get(P.type, 0.0) * u
    A.carry_ik = None
    sf = surface_of(c, pid, A.t) or next((q for q, Q in c.s.props.items() if SPECS[Q.type]["solid"] and SPECS[Q.type]["surface"] and abs(c.prop_xy(q, A.t)[0] - dx) < 2 * u), None)
    if sf:
        A.allow.add(sf)
    floor = (c.gy - dy) < 1.2 * u and not A.seat
    if not A.seat and abs(dx - A.x) > (2.6 if floor else 1.5) * u:
        go(c, A, "walk", dx, gap=2.4 if floor else 1.2)
    B(c, A, "lower", 0.8, pose="pickup_low" if floor else ("desk_lean" if (sf and not A.seat) else stance(A)), ik={"R": (("pt", dx, dy - 0.3 * u), 0.3)})
    tr = A.t - 0.3
    st = c.s.prop_state(pid, tr, pre=False)
    P.set_phase(tr, kind="tween", frm=(st["x"], st["y"], 0.0), to=(dx, ydest, 0.0), dur=0.3, arc=0.0)
    del A.holding[pid]
    B(c, A, "release", 0.4, pose=stance(A))


@act("open_book")
def a_open_book(c, A, a):
    pid = a.get("target") or next((p for p in A.holding if c.s.props[p].type == "book"), None)
    if pid is None:
        return
    if pid not in A.holding:
        a_pick_up(c, A, {"do": "pick_up", "target": pid})
    A.perf.express(A.t, "curiosity", 0.3)
    c.s.props[pid].anim(A.t + 0.1, 0.8, "open", 0.0, 1.0)
    A.perf.look(A.t, ("prop", pid, "top"))
    B(c, A, "open_book", a.get("duration", 1.2), pose="hold_chest" if not A.seat else "sit_think")


@act("turn_page")
def a_turn_page(c, A, a):
    pid = a.get("target") or next((p for p in A.holding if c.s.props[p].type == "book"), None)
    if pid is None:
        return
    P = c.s.props[pid]
    t0 = A.t
    P.anim(t0 + 0.2, 0.6, "flip", 0.0, 1.0)
    P.anim(t0 + 0.85, 0.01, "flip", 1.0, 0.0)

    def hand(t, pre, st, aid, p=pid, t0=t0):
        k = max(0.0, min(1.0, (t - t0 - 0.2) / 0.6))
        x1, y1 = st.prop_point(p, "R", t)
        x0, y0 = st.prop_point(p, "L", t)
        return x1 + (x0 - x1) * k * 0.9, y1 - 0.5 * st.u * math.sin(math.pi * k)
    ik = dict(A.carry_ik or {})
    ik["R"] = (("fn", hand), 0.2)
    B(c, A, "turn_page", a.get("duration", 1.1), pose="hold_chest" if not A.seat else "sit_think", ik=ik)


@act("read")
def a_read(c, A, a):
    pid = a.get("target") or next((p for p in A.holding if c.s.props[p].type == "book"), None)
    if pid is None:
        return
    P = c.s.props[pid]
    if pid not in A.holding:
        a_pick_up(c, A, {"do": "pick_up", "target": pid})
    if P.state_at(A.t + 0.01)["open"] < 0.5:
        a_open_book(c, A, {"target": pid})
    A.perf.express(A.t, a.get("emotion", "concentration"))
    A.perf.look(A.t, ("fn", lambda t, pre, st, aid, p=pid: (st.prop_point(p, "top", t)[0] + 0.6 * st.u * math.sin(t * 2.2), st.prop_point(p, "top", t)[1])))
    B(c, A, "read", a.get("duration", 2.5), pose="sit_think" if A.seat else "hold_chest")
    A.perf.look(A.t, None)


@act("write")
def a_write(c, A, a):
    pid = a.get("target") or next((k for k, p in c.s.props.items() if p.type == "notebook"), None)
    if pid is None:
        return
    px = c.prop_xy(pid, A.t)[0]
    sf = surface_of(c, pid, A.t)
    if sf:
        A.allow.add(sf)
    if not A.seat and abs(px - A.x) > 1.6 * c.u:
        go(c, A, "walk", px, gap=1.2)

    def scribble(t, pre, st, aid, p=pid):
        x, y = st.prop_point(p, "write", t)
        return x + 0.35 * st.u * math.sin(t * 7), y - 0.06 * st.u * abs(math.sin(t * 14))
    A.perf.express(A.t, "concentration")
    A.perf.look(A.t, ("prop", pid, "write"))
    B(c, A, "write", a.get("duration", 3.0), pose="sit_think" if A.seat else "desk_lean", ik={"R": (("fn", scribble), 0.4)}, tags=(pid,))
    A.perf.look(A.t, None)


@act("type")
def a_type(c, A, a):
    pid = a.get("target") or next((k for k, p in c.s.props.items() if p.type == "laptop"), None)
    if pid is None:
        return
    px = c.prop_xy(pid, A.t)[0]
    sf = surface_of(c, pid, A.t)
    if sf:
        A.allow.add(sf)
    if not A.seat and abs(px - A.x) > 1.6 * c.u:
        go(c, A, "walk", px, gap=1.2)

    def key(side):
        def f(t, pre, st, aid, p=pid, s=side):
            x, y = st.prop_point(p, "keys_" + s, t)
            return x, y - 0.12 * st.u * abs(math.sin(t * (8 if s == "L" else 6.3)))
        return f
    A.perf.express(A.t, "concentration")
    A.perf.look(A.t, ("prop", pid, "keys_L"))
    B(c, A, "type", a.get("duration", 3.0), pose="sit_think" if A.seat else "desk_lean",
      ik={"L": (("fn", key("L")), 0.4), "R": (("fn", key("R")), 0.4)}, tags=(pid,))
    A.perf.look(A.t, None)


def _to_mouth_cycle(c, A, pid, label, dur, key, n=2, tilt=False):
    for i in range(n):
        B(c, A, label, dur / n * 0.55, pose=stance(A), ik={"R": (mouth(), 0.25)})
        c.s.props[pid].anim(A.t - 0.2, 0.3, key, i / n, (i + 1) / n)
        B(c, A, label + "_down", dur / n * 0.45, pose=stance(A), ik={"R": (("body", "sh_R", 0.5, 1.9), 0.25)})


@act("eat", "drink")
def a_eat(c, A, a):
    want = "apple" if a["do"] == "eat" else "cup"
    pid = a.get("target") or next((k for k, p in c.s.props.items() if p.type == want), None)
    if pid is None:
        return
    if pid not in A.holding:
        a_pick_up(c, A, {"do": "pick_up", "target": pid})
    A.perf.express(A.t, "happy", 0.4)
    _to_mouth_cycle(c, A, pid, a["do"], a.get("duration", 3.0), "bite" if want == "apple" else "drunk")


@act("use_phone", "phone")
def a_phone(c, A, a):
    pid = a.get("target") or next((k for k, p in c.s.props.items() if p.type == "phone"), None)
    if pid is None:
        return
    if pid not in A.holding:
        a_pick_up(c, A, {"do": "pick_up", "target": pid})
    A.perf.express(A.t, a.get("emotion", "concentration"))
    B(c, A, "phone_up", 0.6, pose=stance(A), ik={"R": (("body", "head", 0.65, 0.2), 0.3)})
    B(c, A, "use_phone", a.get("duration", 2.5), pose="listening" if not A.seat else "sit_think", ik={"R": (("body", "head", 0.65, 0.2), 0.1)})


@act("cook")
def a_cook(c, A, a):
    pid = a.get("target") or next((k for k, p in c.s.props.items() if p.type == "pot"), None)
    if pid is None:
        return
    px = c.prop_xy(pid, A.t)[0]
    sf = surface_of(c, pid, A.t)
    if sf:
        A.allow.add(sf)
    if abs(px - A.x) > 1.6 * c.u:
        go(c, A, "walk", px, gap=1.2)

    def stir(t, pre, st, aid, p=pid):
        x, y = st.prop_point(p, "stir", t)
        return x + 0.3 * st.u * math.cos(t * 5), y + 0.12 * st.u * math.sin(t * 5)
    A.perf.express(A.t, "concentration")
    B(c, A, "cook", a.get("duration", 3.0), pose="desk_lean",
      ik={"R": (("fn", stir), 0.4), "L": (("prop", pid, "handle_L"), 0.4)}, tags=(pid,))


@act("open_door")
def a_open_door(c, A, a):
    pid = a.get("target") or next((k for k, p in c.s.props.items() if p.type == "door"), None)
    if pid is None:
        return
    px = c.prop_xy(pid, A.t)[0]
    d = 1 if px >= A.x else -1
    go(c, A, "walk", px, gap=0.6)
    c.s.props[pid].anim(A.t + 0.5, 1.0, "open", 0.0, 1.0)
    B(c, A, "open_door", a.get("duration", 1.6), pose="stand", ik={"R": (("prop", pid, "handle"), 0.4)}, tags=(pid,))


@act("use_tool", "hammer")
def a_tool(c, A, a):
    pid = a.get("target") or next((k for k, p in c.s.props.items() if p.type == "hammer"), None)
    if pid is None:
        return
    if pid not in A.holding:
        a_pick_up(c, A, {"do": "pick_up", "target": pid})
    t0 = A.t

    def swing(t, pre, st, aid):
        k = abs(math.sin((t - t0) * 4.2))
        return pre["sh_R"][0] + 1.0 * st.u, pre["sh_R"][1] - 1.5 * st.u + 2.2 * st.u * k
    c.s.props[pid].phases[-1][1]["rot"] = lambda t, t0=t0: -50 + 100 * abs(math.sin((t - t0) * 4.2))
    A.perf.express(A.t, "determination")
    B(c, A, "use_tool", a.get("duration", 2.5), pose="stand", ik={"R": (("fn", swing), 0.3)})


@act("pull_chair")
def a_pull_chair(c, A, a):
    pid = a.get("target") or next((k for k, p in c.s.props.items() if p.type == "chair"), None)
    if pid is None:
        return
    P = c.s.props[pid]
    u, d = c.u, P.facing
    px, py = c.prop_xy(pid, A.t)
    if abs(A.x - (px - d * 1.1 * u)) > 0.7 * u:
        go(c, A, "walk", px - d * 1.1 * u)
    if abs(A.theta - 60 * d) > 8:
        B(c, A, "turn", 0.3, pose="relaxed", theta=60 * d)
    B(c, A, "reach", 0.5, pose="relaxed", ik={"R": (("prop", pid, "back"), 0.3)}, tags=(pid,))
    t0 = A.t
    P.set_phase(t0, kind="tween", frm=(px, py, 0.0), to=(px - 0.9 * u * d, py, 0.0), dur=0.8, arc=0.0)
    B(c, A, "pull_chair", 0.9, pose="lean_back", ik={"R": (("prop", pid, "back"), 0.1)}, tags=(pid,))
    B(c, A, "settle", 0.3, pose="relaxed")


def _move_prop(c, A, a, sign):
    pid = a.get("target")
    P = c.s.props.get(pid)
    if P is None:
        return
    u = c.u
    px, py = c.prop_xy(pid, A.t)
    d = 1 if a.get("x") is None else (1 if float(a["x"]) * c.W >= px else -1)
    d = d * sign
    start = px - d * (3.0 if (c.gy - py) < 2.2 * u else 1.9) * u
    go(c, A, "walk", start)
    if abs(A.theta - 90 * d) > 5:
        B(c, A, "turn", 0.3, pose="relaxed", theta=90 * d)
    shift = 1.6 * u * d
    dur = a.get("duration", 2.0)
    t0 = A.t
    P.set_phase(t0 + 0.4, kind="tween", frm=(px, py, 0.0), to=(px + shift, py, 0.0), dur=dur - 0.4, arc=0.0)

    def handp(t, pre, st, aid, p=pid):
        x, y = st.prop_state(p, t)["x"], st.prop_state(p, t)["y"]
        return x - d * 0.75 * u, y - 0.9 * u
    B(c, A, "push" if sign > 0 else "pull", dur, pose="pickup_low" if (c.gy - py) < 2.2 * u else "lean_in", ik={"R": (("fn", handp), 0.3), "L": (("fn", handp), 0.3)},
      x1=A.x + shift, path="ease", ramp=0.0, tags=(pid,), blend=0.4, idle=False)


@act("push")
def a_push(c, A, a):
    _move_prop(c, A, a, 1)


@act("pull")
def a_pull(c, A, a):
    _move_prop(c, A, a, 1)


@act("throw")
def a_throw(c, A, a):
    pid = a.get("target") or next(iter(A.holding), None)
    P = c.s.props.get(pid)
    if P is None:
        return
    if pid not in A.holding:
        a_pick_up(c, A, {"do": "pick_up", "target": pid})
    u = c.u
    dest = float(a["x"]) * c.W if a.get("x") is not None else A.x + 6 * u * fwd_of(A.theta)
    d = 1 if dest >= A.x else -1
    face_toward(c, A, dest, 70)
    B(c, A, "wind_up", 0.5, pose="stand", ik={"R": (("body", "sh_R", -1.0, -1.2), 0.3)})
    B(c, A, "throw", 0.3, pose="stand", ik={"R": (("body", "sh_R", 2.0, -0.6), 0.1)})
    t_rel = A.t - 0.05
    st = c.s.prop_state(pid, t_rel, pre=False)
    tgt = a.get("target2")
    P.set_phase(t_rel, kind="tween", frm=(st["x"], st["y"], 0.0), to=(dest, c.gy - REST_H.get(P.type, 0.0) * u, 0.0), dur=0.8, arc=2.4 * u)
    del A.holding[pid]
    B(c, A, "follow_through", 0.5, pose="stand")


@act("catch")
def a_catch(c, A, a):
    pid = a.get("target")
    P = c.s.props.get(pid)
    if P is None:
        return
    px, py = c.prop_xy(pid, A.t)
    B(c, A, "catch", 0.8, pose="stand", ik={"R": (("pt", px, py - 0.2 * c.u), 0.3)})
    P.set_phase(A.t, kind="hand", actor=A.id, side="R", off=(0.0, 0.0))
    A.holding[pid] = "hand"


# ------------------------------------------------------------------ social
def _partner(c, A, a):
    other = a.get("with") or a.get("target")
    return c.A.get(other)


def _meet(c, A, O, gap):
    """Walk A next to O (if far) and face each other."""
    d = 1 if O.x >= A.x else -1
    if abs(O.x - A.x) > gap * c.u * 1.35:
        go(c, A, "walk", O.x - d * gap * c.u)
    face_toward(c, A, O.x, 40)


def _sync(A, O):
    t = max(A.t, O.t)
    A.t = O.t = t


@act("greet")
def a_greet(c, A, a):
    O = _partner(c, A, a)
    if O is None:
        return a_wave(c, A, a)
    _meet(c, A, O, 3.0)
    _sync(A, O)
    face_toward(c, O, A.x, 40)
    A.perf.express(A.t, "happy")
    B(c, A, "greet", 1.4, pose="wave")
    B(c, O, "greet_back", 1.4, pose=a.get("reply", "stand") if a.get("reply") else "stand")


@act("shake_hands")
def a_shake(c, A, a):
    O = _partner(c, A, a)
    if O is None:
        return
    _meet(c, A, O, 2.7)
    _sync(A, O)
    face_toward(c, O, A.x, 45)
    t0 = A.t
    mx = lambda: (A.x + O.x) / 2

    def meet(t, pre, st, aid, t0=t0, A=A, O=O):
        return ((st.perfs[A.id].solve(t0, ik=False)["x"] + st.perfs[O.id].solve(t0, ik=False)["x"]) / 2,
                st.gy - 3.9 * st.u + 0.3 * st.u * math.sin((t - t0) * 9))
    A.perf.express(A.t, "confidence")
    O.perf.express(O.t, "happy")
    B(c, A, "shake_hands", 1.8, pose="stand", ik={"R": (("fn", meet), 0.4)})
    B(c, O, "shake_hands", 1.8, pose="stand", ik={"R": (("fn", meet), 0.4)})


@act("hug")
def a_hug(c, A, a):
    O = _partner(c, A, a)
    if O is None:
        return
    _meet(c, A, O, 1.5)
    _sync(A, O)
    face_toward(c, O, A.x, 60)
    for X, Y in ((A, O), (O, A)):
        X.perf.express(X.t, "happy")
        B(c, X, "hug", 2.0, pose="hug_pose", ik={"R": (("actor", Y.id, "neck", -0.4, 0.3), 0.5), "L": (("actor", Y.id, "waist", -0.2, 0.0), 0.5)},
          tags=(Y.id,))


@act("hand_over", "give")
def a_hand_over(c, A, a):
    O = c.A.get(a.get("with"))
    pid = a.get("target") or next(iter(A.holding), None)
    P = c.s.props.get(pid)
    if O is None or P is None:
        return
    if pid not in A.holding:
        a_pick_up(c, A, {"do": "pick_up", "target": pid})
    _meet(c, A, O, 2.7)
    _sync(A, O)
    face_toward(c, O, A.x, 50)
    t0 = A.t

    def mid(t, pre, st, aid, t0=t0):
        return ((st.perfs[A.id].solve(t0, ik=False)["x"] + st.perfs[O.id].solve(t0, ik=False)["x"]) / 2, st.gy - 3.9 * st.u)
    A.carry_ik = None
    B(c, A, "offer", 1.0, pose="stand", ik={"R": (("fn", mid), 0.4)})
    B(c, O, "receive", 1.0, pose="stand", ik={"R": (("fn", mid), 0.4)})
    P.set_phase(t0 + 0.9, kind="hand", actor=O.id, side="R", off=(0.0, 0.0))
    del A.holding[pid]
    O.holding[pid] = "hand"
    O.perf.express(t0 + 0.9, "happy")
    B(c, A, "retract", 0.6, pose="stand")
    B(c, O, "retract", 0.6, pose="stand")


@act("argue")
def a_argue(c, A, a):
    O = _partner(c, A, a)
    if O is None:
        return
    _meet(c, A, O, 3.2)
    _sync(A, O)
    face_toward(c, O, A.x, 45)
    A.perf.express(A.t, "anger")
    O.perf.express(O.t, "frustration")
    seq = [("explain", "angry"), ("angry", "explain")]
    for i in range(2):
        B(c, A, "argue", 1.0, pose=seq[i][0])
        B(c, O, "argue", 1.0, pose=seq[i][1])


@act("teach", "explain", "present")
def a_teach(c, A, a):
    pid = a.get("target")
    if pid in c.s.props:
        px = c.prop_xy(pid, A.t)[0]
        go(c, A, "walk", px, gap=2.6)
        ACT["point_at"](c, A, {"do": "point_at", "target": pid, "duration": 1.4})
    A.perf.express(A.t, "confidence")
    B(c, A, "teach", a.get("duration", 2.0), pose="explain", theta=38 * fwd_of(A.theta))


@act("help")
def a_help(c, A, a):
    O = _partner(c, A, a)
    if O is None:
        return
    _meet(c, A, O, 2.6)
    _sync(A, O)
    A.perf.express(A.t, "confidence")
    t0 = A.t

    def hand(t, pre, st, aid, t0=t0):
        return (st.perfs[O.id].solve(t0, ik=False)["pts"]["hand_R"][0] if O.lying else st.perfs[O.id].solve(t, ik=False)["pre"]["hand_R"][0],
                st.gy - 3.0 * st.u)
    B(c, A, "offer_hand", 1.2, pose="stand", ik={"R": (("fn", hand), 0.4)})
    if O.lying:
        O.lying = None
        B(c, O, "get_help", 1.2, pose="relaxed", ik={"R": (("fn", hand), 0.4)})
    else:
        B(c, O, "accept", 1.2, pose="stand", ik={"R": (("fn", hand), 0.4)})
    O.perf.express(O.t - 0.8, "happy")
    B(c, A, "retract", 0.5, pose="stand")
    B(c, O, "retract", 0.5, pose="stand")


@act("wait", "pause")
def a_wait(c, A, a):
    A.t += float(a.get("duration", 1.0))


NAMES = sorted(ACT)
