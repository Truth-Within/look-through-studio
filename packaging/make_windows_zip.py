#!/usr/bin/env python3
"""Rebuild downloads/LookThroughStudio-Windows.zip from the current source tree.

The zip is the Windows deliverable: full runnable source + START_WEB.bat +
packaging\\build_windows.bat (one command on Windows -> dist\\LookThroughStudio.exe).
Run from the project root:  python3 packaging/make_windows_zip.py
"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "downloads" / "LookThroughStudio-Windows.zip"

TOP_FILES = ["webapp.py", "config.py", "main.py", "batch.py", "requirements.txt",
             ".env.example", "README.md", "WINDOWS.md", "START_WEB.bat", "start_web.sh"]
DIRS = ["web", "desktop", "engine", "pipeline", "tests", "packaging", ".github"]
SKIP_DIRS = {"__pycache__", "build", ".gradle", "output", "downloads", "dist", "attachments", ".git"}


def main():
    files = [ROOT / f for f in TOP_FILES if (ROOT / f).exists()]
    for d in DIRS:
        base = ROOT / d
        if base.is_dir():
            files += [p for p in sorted(base.rglob("*"))
                      if p.is_file() and not any(s in p.parts for s in SKIP_DIRS)]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.relative_to(ROOT).as_posix())
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {len(files)} files)")


if __name__ == "__main__":
    main()
