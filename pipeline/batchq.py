"""queue.json: load/save and weekly scheduling."""
import json
import os
from datetime import date, datetime, timedelta, timezone

try:  # Python 3.9+
    from zoneinfo import ZoneInfo
except ImportError:  # Python 3.8 fallback
    import pytz

    def ZoneInfo(name):  # minimal stand-in with the same call signature
        return pytz.timezone(name)

import config


def load():
    if not config.QUEUE_FILE.exists():
        return []
    return json.loads(config.QUEUE_FILE.read_text())


def save(items):
    tmp = config.QUEUE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, indent=2, ensure_ascii=False))
    os.replace(tmp, config.QUEUE_FILE)  # atomic: a crash never leaves a half-written queue


def local_slot(day, hhmm):
    hh, mm = (int(x) for x in hhmm.split(":"))
    return datetime(day.year, day.month, day.day, hh, mm, tzinfo=ZoneInfo(config.TIMEZONE))


def to_utc_z(local_iso):
    """Local ISO string -> the UTC RFC 3339 format YouTube's publishAt wants."""
    return datetime.fromisoformat(local_iso).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def next_start(items):
    """Day after the last scheduled item, else tomorrow (in the configured timezone)."""
    if items:
        last = max(datetime.fromisoformat(i["publish_at"]).date() for i in items)
        return last + timedelta(days=1)
    return datetime.now(ZoneInfo(config.TIMEZONE)).date() + timedelta(days=1)


def build(ideas, channel, fmt, minutes, start, hhmm, items):
    """Append one entry per idea, one per day, and return the new list."""
    next_id = max((i["id"] for i in items), default=0) + 1
    out = list(items)
    for n, (topic, angle) in enumerate(ideas):
        shorts = fmt == "shorts" or (fmt == "mix" and n % 2 == 1)
        out.append({
            "id": next_id + n, "topic": topic, "notes": angle, "channel": channel,
            "shorts": shorts, "minutes": minutes if not shorts else None,
            "publish_at": local_slot(start + timedelta(days=n), hhmm).isoformat(),
            "status": "pending", "video": None, "url": None, "error": None,
        })
    return out


def is_future(local_iso, minutes=15):
    return datetime.fromisoformat(local_iso) > datetime.now(timezone.utc) + timedelta(minutes=minutes)
