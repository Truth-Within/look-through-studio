#!/usr/bin/env python3
"""Web dashboard for The Look Through Studio.

Serves a single-page UI plus a JSON API on top of main.py / batch.py:

  GET  /                     dashboard (web/index.html)
  GET  /api/health           {"ok": true, "engine": ...}
  GET  /api/config           channels, defaults, engine version, ffmpeg presence
  GET  /api/jobs             every job in output/ + live status of running renders
  POST /api/jobs             start a render   {topic|demo, channel, minutes, shorts, ...}
  GET  /api/jobs/<name>      metadata + qc + quality + file listing
  GET  /api/jobs/<name>/log  tail of the render log (?tail=N chars)
  POST /api/jobs/<name>/stop cancel a queued/running render
  DELETE /api/jobs/<name>    delete a job directory (not while running)
  GET  /api/queue            batch queue (queue.json) + batch-run status
  POST /api/queue/plan       queue a week of videos {theme|topics[], days, channel, format, ...}
  POST /api/queue/run        run the queue in the background {demo, upload, limit, ...}
  GET  /files/<job>/<path>   serve an artifact (supports HTTP Range for video seek)
  GET  /downloads/           list downloadable app builds (Linux binary, APK, Windows pkg)
  GET  /downloads/<file>     download one build file (attachment, Range supported)

Stdlib only, so it runs anywhere the pipeline runs:

  python3 webapp.py               # http://127.0.0.1:8080 AND http://<LAN-IP>:8080 (phone-ready)
  python3 webapp.py --port 9000   # custom port
  python3 webapp.py --host 127.0.0.1   # local only

  The server also answers UDP discovery probes on port 8081, so the Android
  app's "Auto-discover" button can find this machine on the Wi-Fi by itself.
"""
import argparse
import json
import mimetypes
import os
import queue
import shutil
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

import config
from engine import VERSION as ENGINE_VERSION
from pipeline import batchq, planner
from pipeline.produce import slugify

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
OUT = config.OUTPUT_DIR.resolve()
OUT.mkdir(parents=True, exist_ok=True)
DL = ROOT / "downloads"
DL.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- runtime state
_lock = threading.Lock()
_jobs = {}            # name -> {"proc", "status", "log", "args", "started"}
_work_q = queue.Queue()
_batch = {"proc": None, "status": "idle", "log": OUT / ".batch.log", "started": None}


def _set_job(name, **kw):
    with _lock:
        _jobs.setdefault(name, {"proc": None, "status": "queued", "log": str(OUT / name / ".web.log"),
                                "args": [], "started": None})
        _jobs[name].update(kw)


def _get_job(name):
    with _lock:
        return _jobs.get(name)


def _cli_cmd(script, args):
    """Full command line to run a CLI script. Frozen desktop builds re-enter the
    binary in --worker mode (desktop/launcher.py), scripts use the .py file."""
    if getattr(sys, "frozen", False):
        return [sys.executable, "--worker", script, *args]
    return [sys.executable, str(ROOT / script), *args]


def _build_cmd(body):
    """Translate a JSON request body into main.py arguments -> (job name, args)."""
    args = ["-y"]
    topic = (body.get("topic") or "").strip()
    demo = body.get("demo") or None          # "story" | "book" | None
    if demo and demo not in ("story", "book"):
        raise ValueError("demo must be 'story' or 'book'")
    if demo:
        args += ["--demo", demo]
        name = f"demo-{demo}"
    elif topic:
        args.append(topic)
        name = slugify(topic)
    elif body.get("showcase"):
        args.append("--showcase")
        name = "showcase"
    else:
        raise ValueError("give a topic, or demo='story'/'book', or showcase=true")
    if body.get("channel") in config.CHANNELS:
        args += ["--channel", body["channel"]]
    if body.get("minutes"):
        args += ["--minutes", str(body["minutes"])]
    if body.get("shorts"):
        args.append("--shorts")
    if body.get("no_shorts"):
        args.append("--no-shorts")
    if body.get("force"):
        args.append("--force")
    if body.get("upload"):
        args.append("--upload")
    if body.get("regen"):
        args += ["--regen", str(body["regen"])]
    return name, args


def _worker():
    """One render at a time; subprocesses so Stop can really kill them."""
    while True:
        name, args = _work_q.get()
        job = _get_job(name)
        if job and job["status"] == "cancelled":
            continue
        log_path = OUT / name / ".web.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        _set_job(name, status="running", started=time.time(), args=args)
        env = dict(os.environ, PYTHONUNBUFFERED="1")
        cmd = _cli_cmd("main.py", args)
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')}  {' '.join(cmd)} =====\n")
            log.flush()
            proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT, env=env)
            _set_job(name, proc=proc)
            rc = proc.wait()
        status = "done" if rc == 0 else "failed"
        if _get_job(name) and _get_job(name)["status"] == "running":
            _set_job(name, status=status, proc=None)


def _batch_worker(cmd):
    log_path = _batch["log"]
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')}  {' '.join(cmd)} =====\n")
        log.flush()
        proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT,
                                env=dict(os.environ, PYTHONUNBUFFERED="1"))
        with _lock:
            _batch.update(proc=proc, status="running", started=time.time())
        rc = proc.wait()
    with _lock:
        _batch.update(proc=None, status="done" if rc == 0 else "failed")


threading.Thread(target=_worker, daemon=True).start()


# ---------------------------------------------------------------- job scanning
def _qc_pass(work):
    qc = work / "qc_report.json"
    if not qc.exists():
        return None
    try:
        r = json.loads(qc.read_text())
        checks = [r["main"]] + r.get("shorts", [])
        return all(c["pass"] for c in checks)
    except Exception:
        return None


def scan_jobs():
    jobs = []
    for d in sorted(OUT.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not d.is_dir() or d.name.startswith("."):
            continue
        meta_path = d / "metadata.json"
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        live = _get_job(d.name) or {}
        video = d / "video.mp4"
        jobs.append({
            "name": d.name,
            "title": meta.get("title") or d.name,
            "topic": meta.get("topic") or d.name,
            "status": live.get("status") or ("done" if video.exists() else "incomplete"),
            "duration_sec": meta.get("duration_sec"),
            "resolution": meta.get("resolution"),
            "n_shorts": len(meta.get("shorts", [])) if meta else len(list((d / "shorts").glob("*.mp4"))) if (d / "shorts").exists() else 0,
            "qc_pass": _qc_pass(d),
            "demo": meta.get("demo_mode", False),
            "has_video": video.exists(),
            "thumbnail": f"/files/{d.name}/thumbnail.png" if (d / "thumbnail.png").exists() else None,
            "updated": d.stat().st_mtime,
        })
    return jobs


def job_detail(name):
    work = (OUT / name).resolve()
    if not str(work).startswith(str(OUT)) or not work.is_dir():
        return None
    meta = json.loads((work / "metadata.json").read_text()) if (work / "metadata.json").exists() else {}
    qc = json.loads((work / "qc_report.json").read_text()) if (work / "qc_report.json").exists() else None
    quality = json.loads((work / "quality.json").read_text()) if (work / "quality.json").exists() else None
    files = []
    for p in sorted(work.rglob("*")):
        if p.is_file() and p.name != ".web.log":
            files.append({"path": str(p.relative_to(work)), "bytes": p.stat().st_size,
                          "url": f"/files/{name}/{p.relative_to(work)}"})
    live = _get_job(name) or {}
    return {"name": name, "status": live.get("status") or ("done" if (work / "video.mp4").exists() else "incomplete"),
            "metadata": meta, "qc": qc, "quality": quality, "files": files,
            "log_url": f"/api/jobs/{name}/log"}


def log_tail(name, tail=4000):
    p = OUT / name / ".web.log"
    if not p.exists():
        return ""
    data = p.read_text(errors="replace")
    return data[-tail:]


# ---------------------------------------------------------------- HTTP layer
MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css",
        ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml", ".json": "application/json",
        ".mp4": "video/mp4", ".srt": "text/srt; charset=utf-8", ".vtt": "text/vtt; charset=utf-8",
        ".txt": "text/plain; charset=utf-8", ".md": "text/markdown; charset=utf-8"}


class Handler(BaseHTTPRequestHandler):
    server_version = "LookThroughStudio/1.0"

    def log_message(self, *a):  # quiet
        pass

    # -- helpers
    def _send(self, body, status=200, ctype="application/json", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, obj, status=200):
        self._send(obj, status)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return {}

    def _serve_file(self, path, download=False, base=OUT):
        path = path.resolve()
        if not str(path).startswith(str(base.resolve())) or not path.is_file():
            return self._json({"error": "not found"}, 404)
        size = path.stat().st_size
        ctype = MIME.get(path.suffix.lower()) or mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        extra = {"Accept-Ranges": "bytes"}
        if download:
            extra["Content-Disposition"] = f'attachment; filename="{path.name}"'
        rng = self.headers.get("Range")
        if rng and rng.startswith("bytes="):
            try:
                start_s, end_s = rng[6:].split("-", 1)
                start = int(start_s) if start_s else max(0, size - int(end_s))
                end = int(end_s) if end_s else size - 1
                end = min(end, size - 1)
            except ValueError:
                return self._json({"error": "bad range"}, 416)
            with open(path, "rb") as f:
                f.seek(start)
                data = f.read(end - start + 1)
            extra["Content-Range"] = f"bytes {start}-{end}/{size}"
            self._send(data, 206, ctype, extra)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(size))
        self.send_header("Accept-Ranges", "bytes")
        for k, v in extra.items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            with open(path, "rb") as f:
                shutil.copyfileobj(f, self.wfile)

    # -- routing
    def do_GET(self):
        u = urlparse(self.path)
        path = unquote(u.path)
        q = parse_qs(u.query)
        try:
            if path == "/" or path == "/index.html":
                return self._serve_file(WEB_DIR / "index.html", base=WEB_DIR)
            if path == "/favicon.ico":
                return self._send(b"", 204, "image/x-icon")
            if path.startswith("/static/"):
                p = (WEB_DIR / path[len("/static/"):]).resolve()
                if str(p).startswith(str(WEB_DIR.resolve())) and p.is_file():
                    return self._serve_file(p, base=WEB_DIR)
                return self._json({"error": "not found"}, 404)
            if path == "/api/health":
                return self._json({"ok": True, "engine": ENGINE_VERSION, "ffmpeg": bool(shutil.which("ffmpeg")),
                                   "time": time.time()})
            if path == "/api/config":
                return self._json({"channels": config.CHANNELS, "fps": config.FPS,
                                   "landscape": list(config.LANDSCAPE), "shorts": list(config.SHORTS),
                                   "engine": ENGINE_VERSION, "output_dir": str(config.OUTPUT_DIR)})
            if path == "/api/jobs":
                return self._json({"jobs": scan_jobs()})
            if path.startswith("/api/jobs/"):
                parts = path.split("/")
                name = parts[3]
                if len(parts) == 5 and parts[4] == "log":
                    tail = int(q.get("tail", ["4000"])[0])
                    return self._send(log_tail(name, tail), 200, "text/plain; charset=utf-8")
                d = job_detail(name)
                return self._json(d) if d else self._json({"error": "no such job"}, 404)
            if path == "/api/queue":
                with _lock:
                    b = {k: (str(v) if isinstance(v, Path) else v) for k, v in _batch.items()}
                    b["proc"] = None
                return self._json({"items": batchq.load(), "batch": b})
            if path == "/api/batch-log":
                p = _batch["log"]
                return self._send(p.read_text(errors="replace")[-int(q.get("tail", ["4000"])[0]):] if p.exists() else "",
                                  200, "text/plain; charset=utf-8")
            if path.startswith("/files/"):
                rest = path[len("/files/"):]
                return self._serve_file(OUT / rest, download=q.get("download", ["0"])[0] == "1")
            if path in ("/downloads", "/downloads/"):
                items = sorted(p for p in DL.iterdir() if p.is_file() and p.name != "index.html")
                rows = "".join(
                    f'<li><a href="/downloads/{p.name}">{p.name}</a> '
                    f'<small>({p.stat().st_size / 1e6:.1f} MB)</small></li>' for p in items)
                body = (f"<h1>Look Through Studio — downloads</h1><ul>{rows}</ul>"
                        f"<p><a href='/'>&larr; back to dashboard</a></p>").encode()
                return self._send(body, 200, "text/html; charset=utf-8")
            if path.startswith("/downloads/"):
                rest = path[len("/downloads/"):]
                return self._serve_file(DL / rest, download=True, base=DL)
            return self._json({"error": "not found", "path": path}, 404)
        except BrokenPipeError:
            pass
        except Exception as e:
            return self._json({"error": str(e)}, 500)

    def do_HEAD(self):
        self.do_GET()

    def do_POST(self):
        u = urlparse(self.path)
        path = unquote(u.path)
        try:
            if path == "/api/jobs":
                body = self._body()
                name, args = _build_cmd(body)
                existing = _get_job(name)
                if existing and existing["status"] in ("queued", "running"):
                    return self._json({"error": f"job '{name}' is already {existing['status']}"}, 409)
                _set_job(name, status="queued", proc=None)
                _work_q.put((name, args))
                return self._json({"ok": True, "name": name, "status": "queued"}, 202)
            if path.startswith("/api/jobs/") and path.endswith("/stop"):
                name = path.split("/")[3]
                job = _get_job(name)
                if not job:
                    return self._json({"error": "no such running job"}, 404)
                if job["status"] == "queued":
                    _set_job(name, status="cancelled")
                elif job["proc"]:
                    job["proc"].terminate()
                    _set_job(name, status="cancelling")
                    def _kill(p=job["proc"]):
                        time.sleep(5)
                        if p.poll() is None:
                            p.kill()
                    threading.Thread(target=_kill, daemon=True).start()
                return self._json({"ok": True, "name": name})
            if path == "/api/queue/plan":
                body = self._body()
                ideas = [(t.split("|")[0].strip(), t.split("|")[1].strip() if "|" in t else "")
                         for t in body.get("topics") or [] if t.strip()]
                if not ideas:
                    ideas = planner.plan(body.get("theme") or "general", int(body.get("days", 7)),
                                         body.get("channel", "human"), use_demo=bool(body.get("demo")))
                from datetime import date
                start = date.fromisoformat(body["start"]) if body.get("start") else batchq.next_start(batchq.load())
                items = batchq.build(ideas, body.get("channel", "human"), body.get("format", "long"),
                                     float(body.get("minutes", 3.0)), start,
                                     body.get("time") or config.PUBLISH_TIME, batchq.load() if not body.get("replace") else [])
                batchq.save(items)
                return self._json({"ok": True, "queued": len(ideas), "items": items})
            if path == "/api/queue/run":
                body = self._body()
                with _lock:
                    if _batch["status"] == "running":
                        return self._json({"error": "a batch run is already going"}, 409)
                cmd = _cli_cmd("batch.py", ["run"] )
                if body.get("upload"):
                    cmd.append("--upload")
                if body.get("scripts_only"):
                    cmd.append("--scripts-only")
                if body.get("retry_failed"):
                    cmd.append("--retry-failed")
                if body.get("force"):
                    cmd.append("--force")
                if body.get("demo"):
                    cmd.append("--demo")
                if body.get("limit"):
                    cmd += ["--limit", str(body["limit"])]
                with _lock:
                    _batch.update(status="starting", proc=None, started=time.time())
                threading.Thread(target=_batch_worker, args=(cmd,), daemon=True).start()
                return self._json({"ok": True, "cmd": cmd}, 202)
            return self._json({"error": "not found", "path": path}, 404)
        except ValueError as e:
            return self._json({"error": str(e)}, 400)
        except Exception as e:
            return self._json({"error": str(e)}, 500)

    def do_DELETE(self):
        u = urlparse(self.path)
        path = unquote(u.path)
        try:
            if path.startswith("/api/jobs/"):
                name = path.split("/")[3]
                job = _get_job(name)
                if job and job["status"] in ("queued", "running", "cancelling"):
                    return self._json({"error": "stop the job first"}, 409)
                work = (OUT / name).resolve()
                if str(work).startswith(str(OUT)) and work.is_dir():
                    shutil.rmtree(work)
                    with _lock:
                        _jobs.pop(name, None)
                    return self._json({"ok": True, "deleted": name})
                return self._json({"error": "no such job"}, 404)
            return self._json({"error": "not found"}, 404)
        except Exception as e:
            return self._json({"error": str(e)}, 500)


def _lan_ips():
    """Best-effort list of this machine's non-loopback IPv4 addresses."""
    ips = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.append(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    try:  # enumerate every interface (picks up secondary NICs/VPNs too)
        out = subprocess.check_output(["ip", "addr", "show"], timeout=5).decode()
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == "inet":
                ip = parts[1].split("/")[0]
                if not ip.startswith("127.") and ip not in ips:
                    ips.append(ip)
    except Exception:
        pass
    try:  # hostname -I lists all local IPv4 addresses
        for ip in subprocess.check_output(["hostname", "-I"], timeout=5).decode().split():
            if not ip.startswith("127.") and ":" not in ip and ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    return ips


def discovery_beacon(port, discover_port=8081, stop=None):
    """Answer UDP discovery probes so the Android app can find this server
    automatically. Any datagram sent to <broadcast>:8081 gets a JSON reply:
    {"app": "lookthrough-studio", "port": 8080, "ips": [...]}"""
    payload = json.dumps({"app": "lookthrough-studio", "name": "Look Through Studio",
                          "port": port, "ips": _lan_ips()}).encode()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("", discover_port))
        s.settimeout(0.5)
        while stop is None or not stop.is_set():
            try:
                data, addr = s.recvfrom(1024)
            except socket.timeout:
                continue
            except OSError:
                break
            if b"lookthrough" in data.lower():
                try:
                    s.sendto(payload, addr)
                except OSError:
                    pass
        s.close()
    except OSError:
        pass  # discovery is best-effort; the HTTP server still works


def serve(host="0.0.0.0", port=8080):
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.daemon_threads = True
    return httpd


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--host", default="0.0.0.0",
                   help="bind address; default 0.0.0.0 so the phone app on the LAN can connect too")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--no-discover", action="store_true", help="disable the UDP discovery beacon (port 8081)")
    a = p.parse_args()
    httpd = serve(a.host, a.port)
    if not a.no_discover:
        threading.Thread(target=discovery_beacon, args=(a.port,), daemon=True).start()
    print("Look Through Studio web UI:", flush=True)
    print(f"  local : http://127.0.0.1:{a.port}", flush=True)
    for ip in _lan_ips():
        print(f"  LAN   : http://{ip}:{a.port}   <- use this address on your phone", flush=True)
    print(f"  jobs live in {OUT}   (Ctrl+C to stop)", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
