"""Automatic animation quality checks. Returns a list of issues; the director can retry with smoother blends."""
import math

from engine.props import SPECS

JOINT_STEP_LIMIT = 70.0      # degrees per frame (at 12 fps) before a pose change counts as abrupt
SLIDE_PER_FRAME = 0.045      # planted foot may move at most this many u per frame
REACH_TOL = 0.55             # hand must be within this many u of the grip it should hold


def _agg(issues, kind, actor, t, detail, count, min_count=1, severity="warn"):
    if count >= min_count:
        issues.append({"type": kind, "actor": actor, "t": round(t, 2), "frames": count, "severity": severity, "detail": detail})


def check(stage, T, fps, beats_by_actor=None):
    u, gy, W, H = stage.u, stage.gy, stage.W, stage.H
    n = int(T * fps) + 1
    issues = []
    for aid, perf in stage.perfs.items():
        c = dict(viol=[0, 0.0, ""], ik=[0, 0.0, ""], oof=[0, 0.0, ""], abrupt=[0, 0.0, ""], slide=[0, 0.0, ""],
                 coll=[0, 0.0, ""], reach=[0, 0.0, ""])
        prev = None
        planted_frames = 0

        def hit(k, t, d=""):
            if c[k][0] == 0:
                c[k][1], c[k][2] = t, d
            c[k][0] += 1

        for i in range(n):
            t = i / fps
            S = perf.solve(t)
            fl = S["flags"]
            if fl["viol"]:
                hit("viol", t, ", ".join(f"{b}={v}" for b, v in fl["viol"][:3]))
            if fl["ik_fail"]:
                hit("ik", t, ",".join(fl["ik_fail"]))
            if S["x"] < 0.03 * W or S["x"] > 0.97 * W or S["pts"]["head"][1] < 0:
                hit("oof", t, f"x={S['x']:.0f}")
            beat = next((b for b in reversed(perf.beats) if b.t0 <= t + 1e-9), None)
            planted = {}
            for s in "LR":
                ax, ay = S["pts"]["ankle_" + s]
                if ay + 0.14 * u >= gy - S["support"] - 0.12 * u and S["pose"].air < 0.05 and beat is not None and not beat.approx and abs(S["pose"].rot) < 30:
                    planted[s] = ax
            if prev is not None:
                dj = max(abs(S["pose"].J[b] - prev["pose"].J[b]) for b in S["pose"].J)
                dj = max(dj, abs(S["pose"].rot - prev["pose"].rot) / 2)
                if dj > JOINT_STEP_LIMIT * (12.0 / fps) and not (beat and beat.name in ("fall", "jump", "stumble")):
                    hit("abrupt", t, f"{dj:.0f} deg in one frame")
                if abs(S["x"] - prev["x"]) > 1.6 * u * (12.0 / fps):
                    hit("abrupt", t, "root jumped")
                for s, ax in planted.items():
                    if s in prev["planted"]:
                        planted_frames += 1
                        if abs(ax - prev["planted"][s]) > SLIDE_PER_FRAME * u * (12.0 / fps) * (1 if beat and beat.name.endswith("_to") else 1.6):
                            hit("slide", t, f"foot {s} moved {abs(ax - prev['planted'][s]) / u:.2f}u")
            S["planted"] = planted
            prev = {"pose": S["pose"], "x": S["x"], "planted": planted}
            # collisions with solid furniture
            tags = beat.tags if beat else set()
            for pid, tr in stage.props.items():
                sp = SPECS[tr.type]
                if not sp["solid"] or pid in tags or S["support"] > 0 or (beat is not None and beat.seated and sp["surface"] and sp["seat"] is None) or (aid in getattr(stage, "ignore_collide", ())):
                    continue
                st = stage.prop_state(pid, t, pre=False)
                if st["kind"] != "free":
                    continue
                x0, x1, _, top = sp["solid"]
                lo, hi = sorted((st["x"] + x0 * u * tr.facing, st["x"] + x1 * u * tr.facing))
                for part in ("hip", "knee_L", "knee_R", "ankle_L", "ankle_R", "waist"):
                    px, py = S["pts"][part]
                    if lo + 0.2 * u < px < hi - 0.2 * u and py > gy - top * u + 0.2 * u:
                        hit("coll", t, f"{part} inside {pid}")
                        break
            # hands that should be on a held prop
            if beat is not None:
                for side, (spec, _) in beat.ik.items():
                    if spec[0] == "prop":
                        gx, gy2 = stage.prop_point(spec[1], spec[2], t, pre=False)
                        hx, hy = S["pts"]["hand_" + side]
                        if S["tau"] > 0.6 and math.hypot(gx - hx, gy2 - hy) > REACH_TOL * u:
                            hit("reach", t, f"hand {side} {math.hypot(gx - hx, gy2 - hy) / u:.1f}u from {spec[1]}.{spec[2]}")
        names = {"viol": ("broken_joint", "joint beyond its limit"), "ik": ("limb_unreachable", "limb cannot reach its target"),
                 "oof": ("out_of_frame", "character leaves the frame"), "abrupt": ("abrupt_change", "pose changes too fast"),
                 "slide": ("foot_sliding", "planted foot slides"), "coll": ("collision", "passes through an object"),
                 "reach": ("detached_prop", "hand is not on the prop")}
        mins = {"viol": 3, "ik": 3, "oof": 1, "abrupt": 1, "slide": max(4, planted_frames // 8), "coll": 2, "reach": 3}
        for k, (kind, text) in names.items():
            cnt, t0, d = c[k]
            _agg(issues, kind, aid, t0, f"{text}: {d}", cnt, mins[k], "error" if k in ("coll", "oof", "reach") else "warn")
        # repetition: the same beat three times in a row
        run, last = 0, None
        for b in perf.beats:
            if b.name == last and b.name not in ("hold", "wait", "stand", "asleep", "idle"):
                run += 1
                if run == 2:
                    _agg(issues, "repetitive", aid, b.t0, f"'{b.name}' repeated 3+ times", 1)
            else:
                run = 0
            last = b.name
    return issues
