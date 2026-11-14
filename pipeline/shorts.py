"""Shorts pack: every job also renders >=4 standalone 9:16 vertical videos.

Each short is a *contiguous arc* of the main script (hook -> development -> payoff),
re-planned and rendered natively at 1080x1920 (not cropped from the main video),
with its own hook title, caption files and QC report."""
import json
import os
from pathlib import Path

import config
from pipeline import captions, render, voice


def pick_groups(durations, n=4):
    """Split segment indices into min(n, len) contiguous, duration-balanced groups."""
    m = len(durations)
    k = min(n, m)
    if k <= 0:
        return []
    if k == 1:
        return [list(range(m))]
    target = sum(durations) / k
    groups, cur, cur_len = [], [], 0.0
    for i, d in enumerate(durations):
        cur.append(i)
        cur_len += d
        left = m - i - 1
        if len(groups) < k - 1 and cur_len >= target and left >= (k - 1 - len(groups)):
            groups.append(cur)
            cur, cur_len = [], 0.0
    if cur:
        groups.append(cur)
    while len(groups) < k:  # safety: split the largest group
        big = max(range(len(groups)), key=lambda g: len(groups[g]))
        if len(groups[big]) < 2:
            break
        g = groups[big]
        groups[big] = g[: len(g) // 2]
        groups.append(g[len(g) // 2:])
    return groups


def _hook(script, idxs):
    seg = script["segments"][idxs[0]]
    hook = (seg.get("headline") or " ".join(seg.get("text", "").split()[:8])).strip()
    return hook[:80] or script["title"][:80]


def short_script(script, idxs):
    return {
        "title": _hook(script, idxs),
        "description": (script.get("description", "") + "\n\n#Shorts").strip(),
        "tags": list(script.get("tags", [])) + ["Shorts"],
        "claims_to_verify": script.get("claims_to_verify", []),
        "contains_synthetic_media": script.get("contains_synthetic_media", False),
        "cast": script["cast"],
        "segments": [script["segments"][i] for i in idxs],
    }


def make_shorts(script, audio_paths, work, n=4, force=False, size=None, fps=None):
    """Render shorts/short_01.mp4 ... (+ .srt/.vtt/.qc.json per short). Returns a list of dicts."""
    size = size or config.SHORTS
    fps = fps or config.FPS
    sdir_root = Path(work) / "shorts"
    sdir_root.mkdir(parents=True, exist_ok=True)
    durations = [voice.duration(a) for a in audio_paths]
    groups = pick_groups(durations, n)
    results, limited = [], len(groups) < n
    for gi, idxs in enumerate(groups, 1):
        name = f"short_{gi:02d}"
        sub = short_script(script, idxs)
        sdir = sdir_root / name
        audio_sub = [audio_paths[i] for i in idxs]
        print(f"  {name}: segments {idxs[0] + 1}-{idxs[-1] + 1} of {len(script['segments'])}, hook \"{sub['title']}\"")
        video, report = render.render_video(sub, audio_sub, sdir, size, force=force, fps=fps)
        final = sdir_root / f"{name}.mp4"
        os.replace(video, final)
        os.replace(sdir / "quality.json", sdir_root / f"{name}.qc.json")
        caps = captions.from_scene_dir(sub, sdir / "segments", voice.duration)
        captions.write_pair(sdir_root / name, caps)
        total = sum(e - s for s, e, _ in caps)
        results.append({
            "file": str(final), "title": sub["title"], "description": sub["description"],
            "hashtags": ["#Shorts"], "duration": round(total, 2), "segments": [i + 1 for i in idxs],
            "captions": [str(sdir_root / f"{name}.srt"), str(sdir_root / f"{name}.vtt")],
            "qc": str(sdir_root / f"{name}.qc.json"),
        })
    if limited:
        print(f"  NOTE: only {len(groups)} short(s) produced - the script has fewer than {n} segments. "
              f"Recorded as a limitation in metadata.json.")
    return results
