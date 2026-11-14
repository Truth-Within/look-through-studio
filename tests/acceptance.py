#!/usr/bin/env python3
"""Acceptance gates (05_QA_ACCEPTANCE.md) against a produced job directory.

Usage:  python3 tests/acceptance.py [output/<job>] [--expect-shorts]
Exit code 0 = all gates pass. Prints a PASS/FAIL table with evidence."""
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from pipeline import qc

ROOT = Path(__file__).resolve().parent.parent


def parse_srt(path):
    text = Path(path).read_text(encoding="utf-8")
    cues = re.findall(r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})", text)
    return cues


def main():
    work = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else ROOT / config.OUTPUT_DIR / "demo-story"
    work = work.resolve()
    gates = []

    def gate(name, ok, evidence=""):
        gates.append((name, bool(ok), evidence))
        print(f"  {'PASS' if ok else 'FAIL'}  {name}  {evidence}")

    print(f"Acceptance gates for {work}\n")

    # F: main video
    video = work / "video.mp4"
    r = qc.check_video(video, label="main", expect_size=config.SHORTS if "--shorts" in sys.argv else config.LANDSCAPE,
                       require_audio=False)
    gate("F main MP4: h264+aac, 16:9/9:16, >0.5s, non-black frames", r["pass"],
         f"{r.get('size')} {r.get('duration')}s black={r['black_segments']} means={r['frame_means']}")

    # G: >=4 shorts
    shorts_dir = work / "shorts"
    short_files = sorted(shorts_dir.glob("short_*.mp4")) if shorts_dir.exists() else []
    gate("G >=4 short MP4s exist", len(short_files) >= 4, f"{len(short_files)} files")
    for sf in short_files[:6]:
        rs = qc.check_video(sf, label=sf.name, expect_size=config.SHORTS, require_audio=False)
        gate(f"G {sf.name}: 1080x1920 h264+aac, 9:16, non-black, <=180s",
             rs["pass"] and rs["duration"] <= 180, f"{rs.get('size')} {rs.get('duration')}s")
        gate(f"G {sf.name}: has .srt with cues", (shorts_dir / (sf.stem + ".srt")).exists()
             and len(parse_srt(shorts_dir / (sf.stem + ".srt"))) > 0)

    # captions for main
    srt, vtt = work / "captions.srt", work / "captions.vtt"
    gate("E/D captions.srt + captions.vtt with cues", srt.exists() and vtt.exists() and len(parse_srt(srt)) >= 1,
         f"{len(parse_srt(srt)) if srt.exists() else 0} cues")

    # metadata / manifest / provenance / qc
    meta = work / "metadata.json"
    gate("metadata.json (title, shorts list, claims)", meta.exists() and "shorts" in json.loads(meta.read_text()),
         f"{len(json.loads(meta.read_text()).get('shorts', []))} shorts listed" if meta.exists() else "missing")
    man = work / "manifest.json"
    ok_man = False
    if man.exists():
        data = json.loads(man.read_text())
        entry = next((f for f in data["files"] if f["path"] == "video.mp4"), None)
        ok_man = entry is not None and hashlib.sha256((work / "video.mp4").read_bytes()).hexdigest() == entry["sha256"]
    gate("manifest.json with verifiable sha256", ok_man)
    gate("edit_decisions.json provenance", (work / "edit_decisions.json").exists())
    qcr = work / "qc_report.json"
    gate("qc_report.json all pass", qcr.exists() and all(c["pass"] for c in
         [json.loads(qcr.read_text())["main"]] + json.loads(qcr.read_text())["shorts"]))
    gate("quality.json (per-scene animation QC)", (work / "quality.json").exists())
    gate("thumbnail.png", (work / "thumbnail.png").exists())

    n_fail = sum(1 for _, ok, _ in gates if not ok)
    print(f"\n{len(gates)} gates, {n_fail} failing -> {'ALL PASS' if n_fail == 0 else 'FAILURES PRESENT'}")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
