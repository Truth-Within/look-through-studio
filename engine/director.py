"""The director turns a narration segment (cast, props, actions) into a performance plan."""
import json
import random

from engine import actions as AC
from engine import library as lib
from engine import quality
from engine.performance import Performance
from engine.props import PropTrack
from engine.skeleton import Pose
from engine.stage import Stage

DEFAULT_X = {1: [0.42], 2: [0.28, 0.72], 3: [0.2, 0.5, 0.8], 4: [0.15, 0.38, 0.62, 0.85]}
SHOTS = ("wide", "medium", "close", "follow", "two_shot")


class Plan:
    pass


def _theta(face, x, W):
    return {"right": 40, "left": -40, "viewer": 0, "away": 180}.get(face, 40 if x < W / 2 else -40)


def build(size, cast, prev, seg, seed, speed=1.0, blend_mult=1.0):
    st = Stage(size, cast)
    W, u, gy = st.W, st.u, st.gy
    rng = random.Random(seed)
    st.scene = seg.get("scene") or (prev or {}).get("scene", "void")
    same_scene = prev is not None and prev.get("scene") == st.scene
    pa = (prev or {}).get("actors", {})

    # --- who is on stage
    wanted = []
    for ch in seg.get("characters") or []:
        ch = {"id": ch} if isinstance(ch, str) else ch
        if ch["id"] in cast:
            wanted.append(ch)
    if not wanted:
        wanted = [{"id": i} for i in (pa or list(cast)[:1])]
    n = len(wanted)
    actors = {}
    for k, ch in enumerate(wanted):
        aid = ch["id"]
        s0 = pa.get(aid)
        slot = DEFAULT_X.get(n, DEFAULT_X[4])[min(k, 3)]
        if ch.get("x") is not None:
            x = float(ch["x"]) * W
        elif s0 and same_scene:
            x = s0["x"]
        else:
            x = slot * W
        if s0:
            pose, theta, support = Pose.from_dict(s0["pose"]), s0["theta"], s0["support"] if same_scene else 0.0
            if ch.get("x") is not None or not same_scene:
                pose, support = lib.named_pose("relaxed"), 0.0
        else:
            pose, theta, support = lib.named_pose("relaxed"), _theta(ch.get("facing"), x, W), 0.0
        if ch.get("facing") and not (s0 and same_scene and ch.get("x") is None):
            theta = _theta(ch["facing"], x, W)
        perf = Performance(aid, st, {"pose": pose, "x": x, "theta": theta, "support": support}, seed=rng.random() * 6)
        if s0 and "face" in s0:
            perf.face_keys = [(0.0, s0["face"], s0["face"], 0.0)]
        A = AC.Actor(aid, perf, x, theta, support)
        if s0 and same_scene:
            A.seat, A.lying = s0.get("seat"), s0.get("lying")
            A.holding = dict(s0.get("holding", {}))
        st.perfs[aid] = perf
        actors[aid] = A

    # --- props
    pp = (prev or {}).get("props", {})
    for pid, d in pp.items():
        ph = d["phase"]
        held = ph["kind"] in ("hand", "anchor") and ph.get("actor") in actors
        if not (same_scene or held):
            continue
        tr = PropTrack(pid, d["type"], 0, 0, d.get("facing", 1), d.get("state"))
        tr.phases = [(0.0, dict(ph))] if held or ph["kind"] == "free" else [(0.0, dict(ph))]
        st.props[pid] = tr
    for pr in seg.get("props") or []:
        pid, ptype = pr["id"], pr["type"]
        if ptype not in AC.SPECS:
            continue
        x = float(pr.get("x", 0.5)) * W
        y = gy
        on = pr.get("on")
        if on in st.props:
            ox = st.prop_state(on, 0.0)["x"]
            x = ox + float(pr.get("dx", 0.0)) * u
            y = gy - (AC.SPECS[st.props[on].type]["surface"] or 0) * u
        y -= AC.REST_H.get(ptype, 0.0) * u
        tr = PropTrack(pid, ptype, x, y, int(pr.get("facing", 1)) or 1, pr.get("state"))
        if pid in st.props and st.props[pid].phases[0][1]["kind"] in ("hand", "anchor") and pr.get("x") is None:
            continue
        st.props[pid] = tr
    for A in actors.values():
        for pid, mode in list(A.holding.items()):
            if pid not in st.props:
                del A.holding[pid]
            elif mode == "anchor":
                A.carry_ik = {"L": (("prop", pid, "L"), 0.3), "R": (("prop", pid, "R"), 0.3)}

    c = AC.Ctx(st, actors, rng)
    c.speed, c.blend_mult = speed, blend_mult
    notes = []
    default = next(iter(actors))
    for a in seg.get("actions") or []:
        aid = a.get("actor") or default
        if aid not in actors:
            notes.append(f"unknown actor '{aid}'")
            continue
        A, do = actors[aid], a.get("do", "stand")
        if a.get("wait"):
            A.t = max(A.t, max(x.t for x in actors.values()))
        fn = AC.ACT.get(do) or (AC.ACT["pose"] if lib.exists(do) else None)
        if fn is None:
            notes.append(f"unknown action '{do}'")
            continue
        a = dict(a, do=do, pose=a.get("pose") or (do if lib.exists(do) else None))
        try:
            fn(c, A, a)
        except Exception as e:  # a bad action must never kill the whole video
            notes.append(f"action '{do}' failed: {e}")
        if A.allow:
            A.sticky = set(A.allow)
        A.allow = set()
    return st, actors, c, notes


def plan_segment(size, cast, prev, seg, speech, fps, seed, pad=0.35):
    target = speech + pad
    speed, blend_mult, issues, notes = 1.0, 1.0, [], []
    for attempt in range(3):
        st, actors, c, notes = build(size, cast, prev, seg, seed, speed, blend_mult)
        nat = max([A.t for A in actors.values()] + [0.0])
        if nat > target * 1.25 and speed == 1.0 and attempt == 0:
            speed = min(1.7, nat / target)  # actions too long for the narration: perform them faster
            continue
        T = max(target, nat + 0.3)
        for A in actors.values():
            if A.t < T:
                AC.B(AC.Ctx(st, actors, c.rng), A, "idle", (T - A.t) * c.speed, pose=AC.stance(A))
        issues = quality.check(st, T, fps)
        if any(i["type"] == "abrupt_change" for i in issues) and blend_mult < 2.0:
            blend_mult = 2.0
            continue
        break
    plan = Plan()
    plan.stage, plan.T, plan.issues, plan.notes = st, T, issues, notes
    plan.shot = seg.get("camera") if seg.get("camera") in SHOTS else ("wide" if len(actors) > 2 else "medium")
    plan.focus = [i for i in (seg.get("focus") or []) if i in actors] or list(actors)
    plan.speaker = seg.get("speaker")
    end = st.end_state(T)
    for aid, A in actors.items():
        end["actors"][aid].update(seat=A.seat, lying=A.lying, holding=A.holding)
    plan.end_state = end
    return plan


def state_key(state):
    return json.dumps(state, sort_keys=True, default=str)
