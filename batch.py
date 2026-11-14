#!/usr/bin/env python3
"""Queue a week of videos, render them unattended, and schedule their release.

  python batch.py plan "psychology of habits"   # LLM picks 7 topics -> queue.json
  python batch.py plan --topics-file topics.txt # or bring your own (one topic per line)
  python batch.py status
  python batch.py run --scripts-only            # write all scripts first, so you can review them
  python batch.py run --upload                  # render + upload privately, scheduled
"""
import argparse
import sys
import time
from datetime import date

import config
from pipeline import batchq, planner
from pipeline.produce import produce, slugify

STATUS_ICON = {"pending": "·", "scripted": "S", "rendered": "R", "uploaded": "✓", "failed": "✗", "running": "…"}


def cmd_plan(a):
    items = [] if a.replace else batchq.load()
    if a.topics_file:
        lines = [l.strip() for l in open(a.topics_file, encoding="utf-8") if l.strip() and not l.startswith("#")]
        ideas = [(l.split("|")[0].strip(), l.split("|")[1].strip() if "|" in l else "") for l in lines]
    else:
        ideas = planner.plan(a.theme, a.days, a.channel, use_demo=a.demo)
    start = date.fromisoformat(a.start) if a.start else batchq.next_start(items)
    items = batchq.build(ideas, a.channel, a.format, a.minutes, start, a.time or config.PUBLISH_TIME, items)
    batchq.save(items)
    print(f"Queued {len(ideas)} videos in {config.QUEUE_FILE} (times in {config.TIMEZONE}).")
    cmd_status(a)


def cmd_status(a):
    items = batchq.load()
    if not items:
        print("Queue is empty. Run: python batch.py plan")
        return
    for i in items:
        kind = "short" if i["shorts"] else "long "
        print(f" {STATUS_ICON.get(i['status'], '?')} #{i['id']:<3} {i['publish_at'][:16].replace('T', ' ')}  {kind}  {i['topic'][:56]}"
              + (f"  [{i['error'][:50]}]" if i.get("error") else ""))
    print("\n · pending  S scripted  R rendered  ✓ uploaded  ✗ failed")


def _wanted(item, a):
    ok = {"pending", "scripted", "running"}
    if a.upload:
        ok.add("rendered")
    if a.retry_failed:
        ok.add("failed")
    return item["status"] in ok


def cmd_run(a):
    items = batchq.load()
    todo = [i for i in items if _wanted(i, a)]
    if a.limit:
        todo = todo[: a.limit]
    if not todo:
        print("Nothing to do. (Use --upload to upload rendered videos, --retry-failed to retry failures.)")
        return
    for n, item in enumerate(todo, 1):
        print(f"\n=== {n}/{len(todo)}  #{item['id']}  {item['topic']} ===")
        item["status"], item["error"] = "running", None
        batchq.save(items)
        schedule = None
        if a.upload:
            if batchq.is_future(item["publish_at"]):
                schedule = batchq.to_utc_z(item["publish_at"])
            else:
                print("  publish time already passed: uploading as private without a schedule")
        try:
            res = produce(
                item["topic"], channel=item["channel"], minutes=item["minutes"], shorts=item["shorts"],
                demo_mode="story" if a.demo else False, yes=True, force=a.force, upload=a.upload, publish_at=schedule,
                notes=item.get("notes", ""), workname=f"{item['id']:02d}-{slugify(item['topic'])}",
                stop_after="script" if a.scripts_only else None,
            )
            if a.scripts_only:
                item["status"] = "scripted"
            else:
                item.update(status="uploaded" if a.upload else "rendered", video=str(res["video"]), url=res["url"])
        except KeyboardInterrupt:
            item["status"] = "pending"
            batchq.save(items)
            sys.exit("\nInterrupted. Run again to resume where it stopped.")
        except Exception as e:  # keep the rest of the week going
            item.update(status="failed", error=str(e).replace("\n", " "))
            print(f"  FAILED: {e}")
        batchq.save(items)
        if n < len(todo) and not a.demo:
            time.sleep(a.pause)
    print()
    cmd_status(a)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("plan", help="create or extend the queue")
    pl.add_argument("theme", nargs="?", help='optional theme, e.g. "stoicism"')
    pl.add_argument("--days", type=int, default=7)
    pl.add_argument("--channel", choices=list(config.CHANNELS), default="human")
    pl.add_argument("--format", choices=["long", "shorts", "mix"], default="long", help="mix alternates long/short")
    pl.add_argument("--minutes", type=float, default=3.0)
    pl.add_argument("--start", help="first publish date YYYY-MM-DD (default: tomorrow / day after queue end)")
    pl.add_argument("--time", help="local publish time HH:MM (default from .env)")
    pl.add_argument("--topics-file", help="text file, one topic per line, optional 'topic | angle'")
    pl.add_argument("--replace", action="store_true", help="discard the existing queue first")
    pl.add_argument("--demo", action="store_true", help="use built-in topics, no API key")
    pl.set_defaults(fn=cmd_plan)

    sub.add_parser("status", help="show the queue").set_defaults(fn=cmd_status)

    r = sub.add_parser("run", help="process pending videos in order")
    r.add_argument("--upload", action="store_true", help="upload as private + scheduled")
    r.add_argument("--scripts-only", action="store_true", help="only write scripts, so you can edit them first")
    r.add_argument("--limit", type=int, help="process at most N videos")
    r.add_argument("--retry-failed", action="store_true")
    r.add_argument("--force", action="store_true", help="ignore cached files")
    r.add_argument("--pause", type=float, default=5.0, help="seconds between videos (API politeness)")
    r.add_argument("--demo", action="store_true", help="built-in script + silent audio, no API keys")
    r.set_defaults(fn=cmd_run)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
