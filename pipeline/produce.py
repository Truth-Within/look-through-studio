"""One video, start to finish. Used by main.py and batch.py.

Every job produces: video.mp4 (main), shorts/short_01..NN.mp4 (>=4 vertical 9:16),
captions.srt/.vtt (+ per-short), quality.json, qc_report.json, metadata.json,
edit_decisions.json, manifest.json, thumbnail.png."""
import hashlib
import json
import re
import sys
from pathlib import Path

import config
from engine.character import Appearance
from engine.thumbnail import make_thumbnail
from pipeline import captions, demo, qc, render, script as script_mod, shorts as shorts_mod, voice


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "video"


def _manifest(work):
    files = []
    for p in sorted(Path(work).rglob("*")):
        if p.is_file():
            files.append({"path": str(p.relative_to(work)), "bytes": p.stat().st_size,
                          "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    return {"files": files}


def _edit_decisions(script, cap_items, demo_mode):
    """Provenance: this pipeline renders an original LLM/demo script (no source-audio
    excerpts are cut), so every kept segment maps 1:1 to a scene of script.json."""
    return {
        "source": "built-in demo script (offline)" if demo_mode else "LLM-generated script (see script.json)",
        "policy": "no source-audio excerpts are spliced; narration is synthesized per segment",
        "segments": [
            {"index": i + 1, "text": text, "start_sec": round(s, 3), "end_sec": round(e, 3), "kept": True}
            for i, (s, e, text) in enumerate(cap_items)
        ],
    }


def produce(topic, *, channel="human", minutes=None, shorts=False, demo_mode=False, showcase=False,
            yes=True, force=False, upload=False, publish_at=None, notes="", workname=None, stop_after=None,
            regen=None, no_shorts=False):
    """Returns {"script", "video", "thumbnail", "url", "shorts"}. stop_after="script" stops once script.json exists."""
    minutes = minutes or (0.7 if shorts else 3.0)
    size = config.SHORTS if shorts else config.LANDSCAPE
    work = config.OUTPUT_DIR / (workname or slugify(topic))
    work.mkdir(parents=True, exist_ok=True)
    script_path = work / "script.json"
    demo_mode = demo_mode or showcase

    print("[1/6] script")
    if script_path.exists() and not force:
        print("  using cached script.json")
        script = script_mod.upgrade(json.loads(script_path.read_text()))
    else:
        if showcase:
            script = demo.showcase()
        elif demo_mode:
            script = demo.script(demo_mode)
        else:
            script = script_mod.generate(topic, minutes, channel, notes)
        script_path.write_text(json.dumps(script, indent=2, ensure_ascii=False))

    if script["claims_to_verify"]:
        print("\n  Fact-check these before publishing:")
        for c in script["claims_to_verify"]:
            print(f"   - {c}")
    if not (demo_mode or yes) and sys.stdin.isatty():
        input(f"\n  Edit {script_path} if needed, then press Enter to continue... ")
        script = script_mod.upgrade(json.loads(script_path.read_text()))
    if stop_after == "script":
        return {"script": script, "video": None, "thumbnail": None, "url": None, "shorts": []}

    print("[2/6] voice")
    audio = voice.synthesize(script, work / "audio", demo=demo_mode, force=force)

    print("[3/6] thumbnail")
    thumb = make_thumbnail(script["title"], work / "thumbnail.png", script["segments"][0].get("scene", "void"),
                           Appearance.from_dict(script["cast"][0]))

    print("[4/6] video")
    video, report = render.render_video(script, audio, work, size, only=regen, force=force)
    n_issues = sum(len(r["issues"]) for r in report)
    print(f"  quality report: {n_issues} issue(s), saved to {work / 'quality.json'}")
    length = voice.duration(video)
    print(f"  {video} ({length:.0f}s)")
    if shorts and length > 180:
        print("  WARNING: over 180s, YouTube won't treat this as a Short. Use fewer minutes.")
    cap_items = captions.from_scene_dir(script, work / "segments", voice.duration)
    captions.write_pair(work / "captions", cap_items)
    print(f"  captions: {work / 'captions.srt'} ({len(cap_items)} cues)")

    if no_shorts:
        print("[5/6] shorts pack skipped (--no-shorts)")
        shorts_list = []
    else:
        print("[5/6] shorts pack (>=4 vertical 9:16 videos)")
        shorts_list = shorts_mod.make_shorts(script, audio, work, force=force)

    print("[6/6] exports (qc, metadata, manifest)")
    qc_report = {
        "main": qc.check_video(video, label="main", expect_size=size, require_audio=not demo_mode),
        "shorts": [qc.check_video(s["file"], label=f"short_{i + 1:02d}", expect_size=config.SHORTS,
                                  require_audio=not demo_mode)
                   for i, s in enumerate(shorts_list)],
    }
    (work / "qc_report.json").write_text(json.dumps(qc_report, indent=2))
    n_fail = sum(1 for c in [qc_report["main"]] + qc_report["shorts"] if not c["pass"])
    print(f"  qc_report.json: {'ALL PASS' if n_fail == 0 else str(n_fail) + ' FAILING'}")

    metadata = {
        "title": script["title"], "description": script["description"], "tags": script.get("tags", []),
        "claims_to_verify": script.get("claims_to_verify", []),
        "contains_synthetic_media": bool(script.get("contains_synthetic_media", False)),
        "channel": channel, "demo_mode": bool(demo_mode), "topic": topic,
        "resolution": list(size), "fps": config.FPS, "duration_sec": round(length, 2),
        "video": str(video), "thumbnail": str(thumb),
        "captions": [str(work / "captions.srt"), str(work / "captions.vtt")],
        "shorts": [{k: s[k] for k in ("file", "title", "description", "hashtags", "duration", "segments")}
                   for s in shorts_list],
    }
    if len(shorts_list) < 4:
        metadata["shorts_limitation"] = (
            f"only {len(shorts_list)} short(s) produced: the script has fewer than 4 segments; "
            "add more narration or source material for a full 4-shorts pack")
    (work / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
    (work / "edit_decisions.json").write_text(json.dumps(_edit_decisions(script, cap_items, demo_mode),
                                                         indent=2, ensure_ascii=False))
    (work / "manifest.json").write_text(json.dumps(_manifest(work), indent=2))

    url = None
    if upload:
        from pipeline import upload as up
        print("[upload] main video")
        url = up.upload(video, script, thumb, shorts, config.YT_PRIVACY, publish_at)
        print("  ", url)
        for s in shorts_list:
            sub = {"title": s["title"], "description": s["description"], "tags": script.get("tags", [])}
            print(f"[upload] {Path(s['file']).name}")
            up.upload(s["file"], sub, None, True, config.YT_PRIVACY, publish_at)
    else:
        print("[upload] skipped (add --upload)")
    return {"script": script, "video": video, "thumbnail": thumb, "url": url, "shorts": shorts_list}
