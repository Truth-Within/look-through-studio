"""QC gate for a rendered file: ffprobe structure, black frames, silent audio, sampled frame brightness."""
import json
import re
import subprocess
import tempfile
from pathlib import Path


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def _run_filter(path, vf):
    r = subprocess.run(["ffmpeg", "-i", str(path), "-vf", vf, "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    return r.stderr


def _audio_level(path):
    r = subprocess.run(["ffmpeg", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"mean_volume: ([-\d.]+) dB", r.stderr)
    mx = re.search(r"max_volume: ([-\d.]+) dB", r.stderr)
    return (float(m.group(1)) if m else None, float(mx.group(1)) if mx else None)


def _frame_means(path, duration, n=5):
    """Mean luma of n evenly spaced frames (raw gray output, no temp files)."""
    means = []
    for k in range(1, n + 1):
        t = duration * k / (n + 1)
        r = subprocess.run(
            ["ffmpeg", "-ss", f"{t:.2f}", "-i", str(path), "-frames:v", "1",
             "-f", "rawvideo", "-pix_fmt", "gray", "-"],
            capture_output=True, check=True)
        buf = r.stdout
        if buf:
            means.append(sum(buf) / len(buf))
    return means


def check_video(path, label="", expect_size=None, require_audio=True, black_thresh=0.10, min_mean=8.0):
    path = Path(path)
    checks = {}
    checks["exists"] = path.exists() and path.stat().st_size > 10_000
    if not checks["exists"]:
        return {"label": label, "file": str(path), "pass": False,
                "checks": checks, "error": "missing or empty file"}
    try:
        p = probe(path)
    except Exception as e:
        return {"label": label, "file": str(path), "pass": False,
                "checks": checks, "error": f"ffprobe failed: {e}"}
    v = next((s for s in p["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in p["streams"] if s["codec_type"] == "audio"), None)
    dur = float(p["format"]["duration"])
    checks["video_stream_h264"] = bool(v and v["codec_name"] == "h264")
    checks["audio_stream_aac"] = bool(a and a["codec_name"] == "aac")
    checks["duration_positive"] = dur > 0.5
    if expect_size and v:
        checks["resolution"] = (v["width"], v["height"]) == tuple(expect_size)
    else:
        checks["resolution"] = bool(v and v["width"] > 0)
    checks["fps"] = bool(v and v.get("r_frame_rate", "0/0") not in ("0/0",))
    # black frames (>=0.2s of near-black counts as a defect)
    err = _run_filter(path, "blackdetect=d=0.2:pix_th=0.10")
    n_black = len(re.findall(r"black_start", err))
    checks["no_black_frames"] = n_black == 0
    # sampled frames must not be blank
    means = _frame_means(path, dur)
    checks["frames_nonblank"] = bool(means) and min(means) > min_mean
    if require_audio and a:
        mean_db, max_db = _audio_level(path)
        checks["audio_not_silent"] = mean_db is not None and mean_db > -80
        audio_info = {"mean_db": mean_db, "max_db": max_db}
    else:
        checks["audio_not_silent"] = None  # skipped (demo silence)
        audio_info = {"note": "audio check skipped (demo/silent mode)"}
    return {"label": label, "file": str(path), "duration": round(dur, 2),
            "size": [v["width"], v["height"]] if v else None,
            "fps": v.get("r_frame_rate") if v else None,
            "black_segments": n_black, "frame_means": [round(m, 1) for m in means],
            "audio": audio_info, "checks": checks,
            "pass": all(x for x in checks.values() if x is not None)}
