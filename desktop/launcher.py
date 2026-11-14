#!/usr/bin/env python3
"""Desktop launcher for The Look Through Studio.

Starts the local web server (webapp.py) and opens the dashboard in the default
browser. This is the entry point that gets frozen into the Linux binary and the
Windows .exe by the PyInstaller specs in packaging/.

  python3 desktop/launcher.py                 # http://127.0.0.1:8080
  python3 desktop/launcher.py --port 9000 --no-browser

Frozen builds store jobs in ~/LookThroughStudio/ (OUTPUT_DIR/QUEUE_FILE are set
before config is imported). `--worker` is an internal mode used by webapp to
spawn renders as child processes of the frozen binary.
"""
import argparse
import importlib
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


def resource_root():
    if getattr(sys, "frozen", False):          # PyInstaller onefile/onedir
        return Path(sys._MEIPASS)              # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


ROOT = resource_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main():
    p = argparse.ArgumentParser(description="The Look Through Studio — desktop launcher")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--no-browser", action="store_true", help="don't open a browser (headless use)")
    p.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)  # internal: re-enter frozen binary
    p.add_argument("rest", nargs=argparse.REMAINDER)
    a = p.parse_args()

    if a.worker:  # webapp spawns: <binary> --worker main.py <args...>
        script = a.rest[0]
        sys.argv = [script] + a.rest[1:]
        os.chdir(str(ROOT))
        importlib.import_module(Path(script).stem).main()
        return

    if getattr(sys, "frozen", False):
        data = Path.home() / "LookThroughStudio"
        data.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("OUTPUT_DIR", str(data / "output"))
        os.environ.setdefault("QUEUE_FILE", str(data / "queue.json"))

    os.chdir(str(ROOT))
    import webapp

    httpd = webapp.serve(a.host, a.port)
    shown_host = "127.0.0.1" if a.host in ("0.0.0.0", "", "::") else a.host
    url = f"http://{shown_host}:{a.port}"
    print(f"The Look Through Studio is running -> {url}", flush=True)
    print(f"jobs are written to {os.environ.get('OUTPUT_DIR', 'output')}  (Ctrl+C to stop)", flush=True)
    if not a.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
