#!/usr/bin/env python3
"""End-to-end: drive a real render through the web API (POST /api/jobs) and wait
for it to finish, proving the dashboard controls the pipeline. Uses the cached
demo-book job so it finishes in ~30s. Exits 1 on failure.

  python3 tests/web_e2e.py
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


def req(base, path, method="GET", body=None):
    r = urllib.request.Request(base + path, method=method,
                               data=json.dumps(body).encode() if body is not None else None,
                               headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            raw = resp.read()
            try:
                return resp.status, json.loads(raw or b"{}")
            except Exception:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def main():
    httpd = webapp.serve("127.0.0.1", 0)
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        s, b = req(base, "/api/jobs", "POST", {"demo": "book", "force": False})
        assert s == 202, (s, b)
        print("queued demo-book via web API:", b)
        status = None
        for i in range(40):
            time.sleep(5)
            s, d = req(base, "/api/jobs")
            job = next(j for j in d["jobs"] if j["name"] == "demo-book")
            if job["status"] != status:
                print(f"  t+{5 * (i + 1)}s  status={job['status']}")
                status = job["status"]
            if status in ("done", "failed"):
                break
        assert status == "done", f"job ended as {status}"
        s, d = req(base, "/api/jobs/demo-book")
        assert any(f["path"] == "video.mp4" for f in d["files"]), "no video.mp4"
        assert d["qc"]["main"]["pass"], "main QC failed"
        assert sum(1 for c in [d["qc"]["main"]] + d["qc"]["shorts"] if c["pass"]) == 1 + len(d["qc"]["shorts"])
        s, log = req(base, "/api/jobs/demo-book/log?tail=4000")
        assert b"[6/6]" in log or b"exports" in log, log[-300:]
        s, raw = req(base, "/files/demo-book/video.mp4")
        assert s == 200 and raw[:4] in (b"\x00\x00\x00 ", b"\x00\x00\x00\x18", b"\x00\x00\x00\x1c") or raw[4:8] == b"ftyp", \
            "video.mp4 is not an MP4"
        print("QC all pass, video.mp4 is a real MP4, log complete -> WEB E2E PASS")
    finally:
        httpd.shutdown()


if __name__ == "__main__":
    main()
