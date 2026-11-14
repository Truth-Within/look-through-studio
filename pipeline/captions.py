"""Caption files (SRT + VTT) built from the *actual* rendered scene durations,
so burned-in text and the sidecar files can never drift apart."""
from pathlib import Path


def _ts(t, sep):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def write(path, items, fmt):
    """items: list of (start_sec, end_sec, text). fmt: 'srt' or 'vtt'."""
    path = Path(path)
    lines = []
    if fmt == "vtt":
        lines.append("WEBVTT\n")
    for i, (start, end, text) in enumerate(items, 1):
        text = " ".join(str(text).split())
        if fmt == "srt":
            lines.append(f"{i}\n{_ts(start, ',')} --> {_ts(end, ',')}\n{text}\n")
        else:
            lines.append(f"{_ts(start, '.')} --> {_ts(end, '.')}\n{text}\n")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_pair(base, items):
    """Write base.srt and base.vtt; returns both paths."""
    base = Path(base)
    return write(base.with_suffix(".srt"), items, "srt"), write(base.with_suffix(".vtt"), items, "vtt")


def from_scene_dir(script, seg_dir, voice_duration):
    """Caption items (start, end, text) using the real duration of each rendered scene clip."""
    scenes = sorted(Path(seg_dir).glob("scene_*.mp4"))
    items, t = [], 0.0
    for seg, sc in zip(script["segments"], scenes):
        d = voice_duration(sc)
        items.append((t, t + d, seg.get("text", "")))
        t += d
    return items
