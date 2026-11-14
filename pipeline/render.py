"""Stage 4: plan every scene with the animation engine, render only the scenes that changed, join with FFmpeg."""
import hashlib
import json
import math
import subprocess

import config
import engine
from engine import director
from engine.character import Appearance
from pipeline import voice


def _key(*parts):
    return hashlib.sha1(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:10]


def _render_scene(plan, seg, audio, out, size, fps, speech):
    n = math.ceil(plan.T * fps)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{size[0]}x{size[1]}", "-framerate", str(fps), "-i", "-",
        "-i", str(audio), "-af", "apad",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(fps),
        "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
        "-shortest", str(out),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for k in range(n):
        t = k / fps
        talking = {plan.speaker} if plan.speaker and t < speech else ()
        img = plan.stage.render(t, k, plan.shot, plan.focus, plan.T, seg.get("headline", ""), seg.get("text", ""), talking,
                                seg.get("icon"), plan.focus[0])
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed while rendering a scene")


def render_video(script, audio_paths, workdir, size, fps=config.FPS, only=None, force=False):
    """Returns (video path, quality report). Scenes whose content and starting state are unchanged are reused from cache;
    `only` (a set of scene numbers) forces just those scenes to be re-rendered."""
    cast = {c["id"]: Appearance.from_dict(c) for c in script["cast"]}
    seg_dir = workdir / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)
    state, parts, report = None, [], []
    segs = script["segments"]
    for i, (seg, audio) in enumerate(zip(segs, audio_paths)):
        speech = voice.duration(audio)
        plan = director.plan_segment(size, cast, state, seg, speech, fps, seed=i * 7919 + 13)
        key = _key(seg, director.state_key(state), script["cast"], engine.VERSION, fps, size, round(speech, 2))
        out = seg_dir / f"scene_{i:02d}_{key}.mp4"
        report.append({"scene": i, "seconds": round(plan.T, 1), "notes": plan.notes, "issues": plan.issues})
        if out.exists() and not force and not (only and i in only):
            print(f"  scene {i + 1}/{len(segs)}: cached")
        else:
            print(f"  scene {i + 1}/{len(segs)}: rendering {plan.T:.1f}s")
            _render_scene(plan, seg, audio, out, size, fps, speech)
        for issue in plan.issues:
            print(f"    ! {issue['type']} ({issue['actor']}, t={issue['t']}s): {issue['detail']}")
        for note in plan.notes:
            print(f"    ! {note}")
        state = plan.end_state
        parts.append(out)

    listfile = workdir / "concat.txt"
    listfile.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in parts))
    final = workdir / "video.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listfile),
                    "-c", "copy", "-movflags", "+faststart", str(final)], check=True)
    (workdir / "quality.json").write_text(json.dumps(report, indent=2))
    return final, report
