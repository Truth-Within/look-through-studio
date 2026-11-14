"""Stage: the world state for one video, target resolution, camera, and frame rendering."""
import math

from PIL import Image, ImageDraw

from engine import overlay
from engine.character import Appearance, draw_character
from engine.draw import Layer
from engine.props import SPECS, PropTrack, Xf
from pipeline import scenes

ZOOM = {"wide": 1.0, "medium": 1.22, "close": 1.75, "follow": 1.3, "two_shot": 1.15}
ANCHORS = {"chest_front": ("neck", 0.95, 0.85), "waist_front": ("hip", 0.85, -0.5), "overhead": ("head", 0.0, -2.0)}


def fwd_of(theta):
    return 1 if math.sin(math.radians(theta)) >= 0 else -1


class Stage:
    def __init__(self, size, cast):
        self.size = size
        self.W, self.H = size
        self.u = 0.08 * min(self.W, self.H)
        self.gy = scenes.ground_y(size)
        self.cast = cast                      # id -> Appearance
        self.builds = {i: a.build for i, a in cast.items()}
        self.perfs, self.props = {}, {}
        self.scene = "void"

    # ---------------------------------------------------------------- lookups
    def attach_point(self, actor, kind, name, t, pre):
        S = self.perfs[actor].solve(t, ik=not pre)
        pts, fwd = (S["pre"] if pre else S["pts"]), fwd_of(S["theta"])
        if kind == "hand":
            x, y = pts["hand_" + name]
        else:
            part, dx, dy = ANCHORS[name]
            x, y = pts[part][0] + dx * self.u * fwd, pts[part][1] + dy * self.u
        return x, y, fwd

    def prop_state(self, pid, t, pre=True):
        return self.props[pid].at(t, lambda a, k, n: self.attach_point(a, k, n, t, pre), self.u)

    def prop_point(self, pid, grip, t, pre=True):
        st = self.prop_state(pid, t, pre)
        return self.props[pid].grip_world(st, grip, self.u)

    def resolve(self, spec, actor_id, t, pre):
        """Turn an IK/look spec into a world (x, y) point."""
        if spec is None:
            return None
        kind, u = spec[0], self.u
        fwd = fwd_of(self.perfs[actor_id].solve(t, ik=False)["theta"]) if actor_id in self.perfs else 1
        if kind == "pt":
            return spec[1], spec[2]
        if kind == "body":
            p = pre[spec[1]]
            return p[0] + spec[2] * u * fwd, p[1] + spec[3] * u
        if kind == "prop":
            return self.prop_point(spec[1], spec[2], t)
        if kind == "actor":
            S = self.perfs[spec[1]].solve(t, ik=False)
            p, f2 = S["pre"][spec[2]], fwd_of(S["theta"])
            return p[0] + spec[3] * u * f2, p[1] + spec[4] * u
        if kind == "fn":
            return spec[1](t, pre, self, actor_id)
        return None

    # ---------------------------------------------------------------- state capture
    def end_state(self, T):
        actors = {}
        for i, perf in self.perfs.items():
            S = perf.solve(T, ik=True)
            actors[i] = {"x": S["x"], "theta": S["theta"], "pose": S["pose"].to_dict(), "support": S["support"],
                         "face": {k: v for k, v in perf.face_at(T).items()}}
        props = {}
        for pid, tr in self.props.items():
            ph = None
            for t0, p in tr.phases:
                if t0 <= T + 1e-9:
                    ph = p
            st = self.prop_state(pid, T, pre=False)
            d = {"type": tr.type, "facing": tr.facing, "state": tr.state_at(T)}
            if ph["kind"] in ("hand", "anchor"):
                d["phase"] = {k: v for k, v in ph.items() if not callable(v)}
            else:
                d["phase"] = {"kind": "free", "x": st["x"], "y": st["y"], "rot": st["rot"] if not callable(st["rot"]) else 0.0}
            props[pid] = d
        return {"actors": actors, "props": props, "scene": self.scene}

    # ---------------------------------------------------------------- camera
    def camera(self, shot, focus_ids, t, T):
        z = ZOOM.get(shot, 1.0)
        if shot in ("medium", "close") and T > 0:
            z *= 1 + 0.05 * min(1.0, t / T)  # slow push-in keeps shots alive
        xs, ys = [], []
        for lag in (0.0, 0.15, 0.3, 0.45):
            for i in focus_ids:
                if i in self.perfs:
                    S = self.perfs[i].solve(max(0.0, t - lag), ik=False)
                    xs.append(S["x"])
                    ys.append((S["pts"]["head"][1] * 0.6 + S["y"] * 0.4))
        fx = sum(xs) / len(xs) if xs else self.W / 2
        fy = sum(ys) / len(ys) if ys else self.H / 2
        if shot == "wide" or z <= 1.001:
            return 1.0, self.W / 2, self.H / 2
        fx = min(self.W - self.W / (2 * z), max(self.W / (2 * z), fx))
        fy = min(self.H - self.H / (2 * z), max(self.H / (2 * z), fy))
        return z, fx, fy

    # ---------------------------------------------------------------- rendering
    def render(self, t, frame_idx, shot, focus_ids, T, headline, caption, talking=(), icon=None, icon_actor=None, aa=2):
        W, H, u = self.W, self.H, self.u
        z, fx, fy = self.camera(shot, focus_ids, t, T)
        bg = scenes.background(self.scene, self.size)
        if z > 1.001:
            box = (fx - W / (2 * z), fy - H / (2 * z), fx + W / (2 * z), fy + H / (2 * z))
            img = bg.resize((W, H), Image.BILINEAR, box=box)
        else:
            img = bg.copy()
        scenes.animate(ImageDraw.Draw(img), self.scene, self.size, t)

        def S(p):
            return ((p[0] - fx) * z + W / 2, (p[1] - fy) * z + H / 2)

        us = u * z
        items_back, items_front, pts_all = [], [], []
        for pid, tr in self.props.items():
            st = tr.at(t, lambda a, k, n: self.attach_point(a, k, n, t, False), u)
            sx, sy = S((st["x"], st["y"]))
            items_back.append((pid, tr, st, sx, sy)) if SPECS[tr.type]["behind"] and st["kind"] == "free" else items_front.append((pid, tr, st, sx, sy))
            pts_all += [(sx - 4 * us, sy - 8 * us), (sx + 4 * us, sy + 2 * us)]
        sols = {}
        for i, perf in self.perfs.items():
            sol = perf.solve(t, ik=True)
            sols[i] = sol
            for p in sol["pts"].values():
                q = S(p)
                pts_all += [(q[0] - 2.4 * us, q[1] - 2.4 * us), (q[0] + 2.4 * us, q[1] + 2.4 * us)]
        if pts_all:
            box = (min(p[0] for p in pts_all), min(p[1] for p in pts_all), max(p[0] for p in pts_all), max(p[1] for p in pts_all))
            L = Layer(img, box, aa)

            def draw_prop(item):
                pid, tr, st, sx, sy = item
                rot = st["rot"]
                draw = SPECS[tr.type]["draw"]
                draw(L, Xf(sx, sy, us, rot, st["flip"]), st["state"], us)

            for item in items_back:
                draw_prop(item)
            for i, sol in sols.items():
                root = S((sol["x"], sol["y"]))
                flap = i in talking and (frame_idx // 2) % 2 == 0
                draw_character(L, sol["pose"], self.cast[i], root, us, sol["theta"], sol["face"], talk=flap, seed=hash(i) % 7, t=t)
            for item in items_front:
                draw_prop(item)
            L.finish()
        d = ImageDraw.Draw(img)
        if icon and icon != "none":
            a = icon_actor if icon_actor in sols else next(iter(sols), None)
            if a:
                hx, hy = S(sols[a]["pts"]["head"])
                overlay.draw_icon(d, icon, hx + 2.2 * us, hy - 1.2 * us, us, t)
        overlay.text_overlay(d, self.size, headline, caption)
        return img
