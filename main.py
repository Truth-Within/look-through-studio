#!/usr/bin/env python3
"""topic -> script -> voice -> stickman video -> (optional) YouTube upload.

For a whole week of videos, see batch.py.
"""
import argparse
import shutil
import sys

import config
from pipeline import sheets
from pipeline.produce import produce


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("topic", nargs="?", help='e.g. "Why do we fear being alone?"')
    p.add_argument("--channel", choices=list(config.CHANNELS), default="human")
    p.add_argument("--minutes", type=float, help="target length (default 3, or 0.7 for --shorts)")
    p.add_argument("--shorts", action="store_true", help="vertical 9:16 main video for YouTube Shorts")
    p.add_argument("--no-shorts", action="store_true", help="skip the shorts pack (every job otherwise renders >=4 9:16 shorts)")
    p.add_argument("--demo", nargs="?", const="story", choices=["story", "book"], help="no API keys: built-in story + silent audio")
    p.add_argument("--showcase", action="store_true", help="render a video that shows every pose, outfit and expression")
    p.add_argument("--sheets", action="store_true", help="write pose/expression/outfit/scene preview PNGs, then exit")
    p.add_argument("--regen", help="re-render only these scene numbers (comma separated, 1-based), e.g. --regen 3,5")
    p.add_argument("--upload", action="store_true", help="upload to YouTube when finished")
    p.add_argument("-y", "--yes", action="store_true", help="skip the script review pause")
    p.add_argument("--force", action="store_true", help="regenerate everything, ignoring cache")
    a = p.parse_args()

    if a.sheets:
        config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        for fn, name in ((sheets.pose_sheet, "pose_sheet"), (sheets.expression_sheet, "expression_sheet"),
                         (sheets.outfit_sheet, "outfit_sheet"), (sheets.scene_sheet, "scene_sheet")):
            print(fn(config.OUTPUT_DIR / f"{name}.png"))
        return
    if not (a.topic or a.demo or a.showcase):
        p.error("give a topic, or use --demo / --showcase")
    if not shutil.which("ffmpeg"):
        sys.exit("FFmpeg not found. Install it first (see README).")

    topic = "showcase" if a.showcase else (a.topic or f"demo-{a.demo}")
    regen = {int(x) - 1 for x in a.regen.split(",")} if a.regen else None
    produce(topic, channel=a.channel, minutes=a.minutes, shorts=a.shorts, demo_mode=a.demo,
            showcase=a.showcase, yes=a.yes, force=a.force, upload=a.upload, regen=regen,
            no_shorts=a.no_shorts)


if __name__ == "__main__":
    main()
