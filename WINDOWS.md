# The Look Through Studio — Windows

Two ways to run it on Windows:

## Option A — run from source (no build, ~2 minutes)
1. Install **Python 3.10+** from https://www.python.org/downloads/ (tick "Add python.exe to PATH").
2. Install **ffmpeg** and put it on PATH: `winget install ffmpeg`
3. Double-click **`START_WEB.bat`** (or run `python webapp.py`) in this folder.
4. Open http://127.0.0.1:8080 — the full dashboard (start renders, watch logs,
   play videos, download artifacts, batch queue, and the `/downloads/` page).

Jobs are stored in `output\` next to this file.

## Option B — single desktop .exe
On a Windows machine, from this folder run:

```
packaging\build_windows.bat
```

This installs PyInstaller and builds **`dist\LookThroughStudio.exe`** — a single
file that starts the same web UI and opens your browser automatically.
Double-click it to use; no Python needed on the target machine (ffmpeg still
required on PATH for rendering).

> Why no .exe shipped here: executables are platform-specific, so a Windows .exe
> must be produced on Windows (PyInstaller cannot cross-compile from Linux/ARM).
> The GitHub Actions workflow in `packaging/release-workflow.yml` builds the
> .exe (plus the Linux binary and the APK) automatically on every `v*` tag —
> copy it to `.github/workflows/release.yml` on GitHub (web UI or a
> `workflow`-scoped token) to enable it.

## Files
- `webapp.py` — web dashboard server (stdlib only) + JSON API
- `web/` — dashboard single-page UI
- `main.py` / `batch.py` — CLI render / batch entry points
- `engine/`, `pipeline/` — animation engine and production stages
- `desktop/launcher.py` — entry point frozen into the .exe / Linux binary
- `packaging/` — PyInstaller specs, icons, build scripts
- `downloads/` (in the project root, one level up) — prebuilt Linux binary + APK
