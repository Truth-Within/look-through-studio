"""A character's performance: a timeline of beats, evaluated at any time t (frame-rate independent)."""
import math

from engine import face as F
from engine import library as lib
from engine.skeleton import Pose, fk, lerp_pose, lowest, solve_limb


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def trapezoid(tn, r):
    """Fraction of distance covered at normalised time tn, with accel/decel ramps of fraction r."""
    tn = max(0.0, min(1.0, tn))
    if r <= 1e-6:
        return tn
    v = 1.0 / (1.0 - r)
    if tn < r:
        return 0.5 * v / r * tn * tn
    if tn <= 1 - r:
        return 0.5 * v * r + v * (tn - r)
    return 1.0 - 0.5 * v / r * (1 - tn) ** 2


class Beat:
    def __init__(self, name, t0, dur, key=None, fn=None, x1=None, path="hold", ramp=0.18, theta=None, turn=0.4,
                 blend=0.3, idle=True, ik=None, lock=False, support=0.0, tags=(), approx=False, planted=True):
        self.name, self.t0, self.dur = name, t0, max(dur, 0.01)
        self.key, self.fn, self.x1, self.path, self.ramp = key, fn, x1, path, ramp
        self.theta1, self.turn, self.blend, self.idle = theta, turn, blend, idle
        self.ik = ik or {}          # {"R": (spec, ramp_in_seconds)}
        self.lock, self.support, self.tags = lock, support, set(tags)
        self.approx, self.planted, self.seated = approx, planted, False
        self.from_pose = self.x0 = self.theta0 = self.support0 = self.lock_targets = None

    def path_xy(self, tau):
        if self.path == "hold" or self.x1 is None:
            return self.x0, 0.0
        tn = tau / self.dur
        f = trapezoid(tn, self.ramp) if self.path == "trap" else smooth(tn)
        return self.x0 + (self.x1 - self.x0) * f, abs(self.x1 - self.x0) * f


class Performance:
    def __init__(self, actor_id, world, init, seed=0):
        """init: dict(pose=Pose, x=px, theta=deg, support=px) describing the state at t=0."""
        self.id, self.world, self.seed = actor_id, world, seed
        self.init = init
        self.beats, self.t_end = [], 0.0
        self.face_keys = [(0.0, F.expression("neutral"), F.expression("neutral"), 0.0)]
        self.look_keys = []  # (t, spec or None)
        self.cache = {}

    # ---------------------------------------------------------------- planning
    def add(self, b):
        if b.t0 > self.t_end + 1e-6:
            self.add(Beat("hold", self.t_end, b.t0 - self.t_end, fn=lambda tau, d, p=self.state_at(self.t_end)["pose"]: p.copy(),
                          blend=0.01))
        self.cache.clear()
        st = self.state_at(b.t0)
        b.from_pose, b.x0, b.theta0, b.support0 = st["pose"].copy(), st["x"], st["theta"], st["support"]
        if b.theta1 is None:
            b.theta1 = st["theta"]
        if b.lock:
            u, gy = self.world.u, self.world.gy
            on_ground = all(abs(gy - st["support"] - 0.14 * u - st["pts"]["ankle_" + s][1]) < 0.3 * u for s in "LR")
            if not on_ground or abs(st["pose"].rot) > 30:
                b.lock = False  # feet are off the ground (lying, jumping...): nothing to plant
        if b.lock:
            b.lock_targets = {s: (st["pts"]["ankle_" + s][0], gy - st["support"] - 0.14 * u) for s in "LR"}
        self.beats.append(b)
        self.t_end = max(self.t_end, b.t0 + b.dur)
        self.cache.clear()

    def express(self, t, name, trans=0.35):
        prev = self.face_at(t)
        self.face_keys = [k for k in self.face_keys if k[0] < t - 1e-6] + [(t, prev, F.expression(name), trans)]
        self.cache.clear()

    def look(self, t, spec):
        self.look_keys = [k for k in self.look_keys if k[0] < t - 1e-6] + [(t, spec)]
        self.cache.clear()

    # ---------------------------------------------------------------- evaluation
    def state_at(self, t):
        return self.solve(t, ik=True) if self.beats else self._initial()

    def _initial(self):
        w, i = self.world, self.init
        pose, x, theta = i["pose"].copy(), i["x"], i["theta"]
        return self._finish(pose, x, theta, i.get("support", 0.0), None, 0.0, 0.0, ik=False, beat=None)

    def face_at(self, t):
        cur = self.face_keys[0][2]
        for t0, frm, to, tr in self.face_keys:
            if t0 <= t:
                cur = F.lerp(frm, to, F.smooth((t - t0) / tr) if tr > 0 else 1.0)
        return cur

    def solve(self, t, ik=True):
        key = (round(t, 5), ik)
        if key in self.cache:
            return self.cache[key]
        if not self.beats:
            r = self._initial()
            self.cache[key] = r
            return r
        b = self.beats[0]
        for cand in self.beats:
            if cand.t0 <= t + 1e-9:
                b = cand
        tau = max(0.0, min(t - b.t0, b.dur))
        x, dist = b.path_xy(tau)
        k = smooth(tau / max(b.blend, 1e-6))
        raw = b.fn(tau, dist) if b.fn else b.key
        pose = lerp_pose(b.from_pose, raw, k)
        theta = b.theta0 + (b.theta1 - b.theta0) * smooth(tau / max(min(b.turn, b.dur), 1e-6))
        sup = b.support(tau) if callable(b.support) else b.support
        sup = b.support0 + (sup - b.support0) * smooth(tau / max(b.blend, 1e-6))
        if b.idle:
            self._idle(pose, t)
        r = self._finish(pose, x, theta, sup, b, tau, t, ik=ik, beat=b)
        self.cache[key] = r
        return r

    def _idle(self, pose, t):
        s, J = self.seed, pose.J
        J["chest"] += 1.1 * math.sin(2 * math.pi * t / 3.7 + s)
        J["spine"] += 0.7 * math.sin(2 * math.pi * t / 5.3 + 1.3 * s)
        J["head"] += 1.4 * math.sin(2 * math.pi * t / 4.1 + 2 * s) + 0.7 * math.sin(2 * math.pi * t / 1.7 + s)

    def _finish(self, pose, x, theta, support, b, tau, t, ik, beat):
        w = self.world
        u, gy = w.u, w.gy
        build = w.builds[self.id]
        face = self.face_at(t)
        pose.J["head"] += face["post_head"]
        pose.J["spine"] += face["post_spine"] * 0.6
        pose.J["chest"] += face["post_spine"] * 0.4
        look = None
        for t0, spec in self.look_keys:
            if t0 <= t:
                look = spec
        viol = []
        P, _ = fk(pose, u, theta, build, viol)
        hk = build.get("head", 1.0)
        y = gy - support - pose.air * u - lowest(P, u, hk)
        flags = {"ik_fail": [], "viol": viol, "beat": beat.name if beat else "init"}
        if beat is not None and beat.lock and beat.lock_targets:
            for s, (tx, ty) in beat.lock_targets.items():
                if not solve_limb(pose, u, theta, build, (x, y), s, "leg", (tx, ty - support * 0)):
                    flags["ik_fail"].append("leg_" + s)
            P, _ = fk(pose, u, theta, build)
        pre = {k: (x + px, y + py) for k, (px, py) in P.items()}
        if look is not None and ik:
            tgt = w.resolve(look, self.id, t, pre)
            if tgt:
                fwd = 1 if math.sin(math.radians(theta)) >= 0 else -1
                pose.J["head"] += max(-1, min(1, (tgt[1] - pre["head"][1]) / (3 * u))) * 16
                face = dict(face)
                face["px"] = max(-1, min(1, (tgt[0] - pre["head"][0]) * fwd / (4 * u))) * 0.9
                face["py"] = max(-1, min(1, (tgt[1] - pre["head"][1]) / (3 * u))) * 0.8
        if beat is not None and ik and beat.ik:
            for s, (spec, ramp) in beat.ik.items():
                tgt = w.resolve(spec, self.id, t, pre)
                if tgt is None:
                    continue
                wgt = smooth(tau / max(ramp, 1e-6))
                if not solve_limb(pose, u, theta, build, (x, y), s, "arm", tgt, wgt) and wgt > 0.95:
                    flags["ik_fail"].append("arm_" + s)
            P, _ = fk(pose, u, theta, build)
        pts = {k: (x + px, y + py) for k, (px, py) in P.items()}
        return {"pose": pose, "x": x, "y": y, "theta": theta, "pts": pts, "pre": pre, "face": face,
                "support": support, "flags": flags, "tau": tau}
