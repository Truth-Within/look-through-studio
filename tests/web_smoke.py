#!/usr/bin/env python3
"""Smoke test for webapp.py: starts the server on an ephemeral port and checks
every API route plus HTTP Range file serving. Exits 1 on any failure.

  python3 tests/web_smoke.py
"""
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import webapp  # noqa: E402

FAIL = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAIL.append(name)


def req(base, path, method="GET", body=None, headers=None):
    r = urllib.request.Request(base + path, method=method,
                               data=json.dumps(body).encode() if body is not None else None,
                               headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(r, timeout=15) as resp:
            return resp.status, resp.headers, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


def main():
    httpd = webapp.serve("127.0.0.1", 0)
    port = httpd.server_address[1]
    base = f"http://127.0.0.1:{port}"
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.3)
    try:
        s, h, b = req(base, "/")
        check("GET / serves dashboard", s == 200 and b"Look Through Studio" in b)

        s, h, b = req(base, "/api/health")
        check("GET /api/health", s == 200 and json.loads(b)["ok"] is True)

        s, h, b = req(base, "/api/config")
        cfg = json.loads(b)
        check("GET /api/config has channels+fps", s == 200 and "human" in cfg["channels"] and cfg["fps"] == 24)

        s, h, b = req(base, "/api/jobs")
        jobs = json.loads(b)["jobs"]
        names = [j["name"] for j in jobs]
        check("GET /api/jobs lists demo jobs", s == 200 and "demo-story" in names, str(names))
        demo = next((j for j in jobs if j["name"] == "demo-story"), None)
        check("demo-story marked done with QC", demo and demo["status"] == "done" and demo["qc_pass"] is True,
              str(demo))

        s, h, b = req(base, "/api/jobs/demo-story")
        d = json.loads(b)
        check("GET /api/jobs/demo-story detail", s == 200 and d["metadata"]["title"] and any(
            f["path"] == "video.mp4" for f in d["files"]))

        s, h, b = req(base, "/api/jobs/demo-story/log?tail=200")
        check("GET log route (empty ok)", s == 200)

        s, h, b = req(base, "/files/demo-story/video.mp4", headers={"Range": "bytes=0-1023"})
        check("Range request -> 206 + Content-Range", s == 206 and "bytes 0-1023/" in h.get("Content-Range", ""),
              f"status={s} cr={h.get('Content-Range')}")
        check("Range body is 1024 bytes", len(b) == 1024, f"got {len(b)}")

        s, h, b = req(base, "/files/demo-story/video.mp4")
        check("Full file served as video/mp4", s == 200 and h.get("Content-Type") == "video/mp4"
              and int(h.get("Content-Length", 0)) == len(b))

        s, h, b = req(base, "/files/../config.py")
        check("path traversal blocked", s == 404, f"status={s}")

        s, h, b = req(base, "/files/demo-story/thumbnail.png?download=1")
        check("download adds Content-Disposition", s == 200 and "attachment" in h.get("Content-Disposition", ""))

        s, h, b = req(base, "/api/queue")
        check("GET /api/queue", s == 200 and "items" in json.loads(b))

        # start a job that fails fast (no API keys, not demo) then clean up
        s, h, b = req(base, "/api/jobs", method="POST",
                      body={"topic": "web-smoke-test-xyz", "channel": "human"})
        check("POST /api/jobs accepted", s == 202 and json.loads(b)["name"] == "web-smoke-test-xyz", f"s={s} b={b[:200]}")
        time.sleep(3)
        s, h, b = req(base, "/api/jobs/web-smoke-test-xyz/log?tail=500")
        check("job log is being written", s == 200 and len(b) > 0, b[:200].decode(errors="replace"))
        s, h, b = req(base, "/api/jobs/web-smoke-test-xyz/stop", method="POST")
        check("POST stop", s == 200)
        time.sleep(1)
        s, h, b = req(base, "/api/jobs", method="DELETE", )
        # delete needs the path form:
        s, h, b = req(base, "/api/jobs/web-smoke-test-xyz", method="DELETE")
        # may 409 if still cancelling; wait and retry once
        if s == 409:
            time.sleep(6)
            s, h, b = req(base, "/api/jobs/web-smoke-test-xyz", method="DELETE")
        check("DELETE job", s == 200, f"s={s} b={b[:200]}")

        s, h, b = req(base, "/api/jobs", method="POST", body={"channel": "human"})
        check("POST without topic/demo -> 400", s == 400, f"s={s}")

        s, h, b = req(base, "/api/jobs/no-such-job")
        check("unknown job -> 404", s == 404)

        s, h, b = req(base, "/api/nonexistent")
        check("unknown route -> 404", s == 404)
    finally:
        httpd.shutdown()

    print()
    if FAIL:
        print(f"{len(FAIL)} FAILING: {FAIL}")
        sys.exit(1)
    print("ALL WEB SMOKE TESTS PASS")


if __name__ == "__main__":
    main()
