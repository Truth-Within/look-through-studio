# Stickman YouTube Pipeline

Topic in, finished stickman video out. Every stage runs on a free tier or locally.

```
topic -> Gemini (script) -> edge-tts (voice) -> Pillow (scene + posed stickman)
      -> FFmpeg (MP4) -> YouTube Data API (optional, scheduled upload)
```

## Setup

1. Python 3.8+ (3.10+ recommended) and **FFmpeg with the H.264 encoder** (`sudo apt install ffmpeg`, `brew install ffmpeg`, or `winget install ffmpeg`).
   On **Fedora** the default `ffmpeg-free` package has no H.264 (libx264) encoder: enable RPM Fusion, then `sudo dnf swap ffmpeg-free ffmpeg --allowerasing`.
   On a machine where apt is unavailable, a static build works too:
   `curl -L -o /tmp/ff.tar.xz https://github.com/FFmpeg-Builds/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linuxarm64-gpl.tar.xz && tar -xf /tmp/ff.tar.xz -C /tmp && cp /tmp/ffmpeg-master-latest-linuxarm64-gpl/bin/{ffmpeg,ffprobe} /usr/local/bin/`
2. `pip install -r requirements.txt`
3. `cp .env.example .env` and paste a free Gemini key from https://aistudio.google.com/apikey
   (Python 3.8 note: `backports.zoneinfo` isn't needed — `pipeline/batchq.py` falls back to `pytz`, which is in requirements.txt)

## Try it with no keys

```
python3 main.py --demo            # full sample job: main video + >=4 Shorts + captions + QC (silent audio)
python3 main.py --sheets          # writes output/pose_sheet.png, expression/outfit/scene sheets
python3 main.py --showcase        # video that steps through every pose and scene
python3 tests/run_battery.py      # regression check of every action (exit 1 on hard failures)
python3 tests/acceptance.py output/demo-story   # acceptance gates on a produced job
```

## One video

```
python main.py "Why do we fear being alone?"
python main.py "The bystander effect" --minutes 5
python main.py "What is the Overview Effect?" --shorts
python main.py "Hermetic principles" --channel unveiled
```

The script is saved to `output/<topic>/script.json`. The program pauses so you can fix it and
fact-check the `claims_to_verify` list (skip with `-y`). Every stage caches its result; `--force` redoes all.

## Deliverables per job

Every run of `main.py` / `batch.py run` writes into `output/<job>/`:

| File | What |
|---|---|
| `video.mp4` | main video (1920x1080 H.264/AAC by default; 1080x1920 with `--shorts`) |
| `shorts/short_01.mp4` ... | **at least four** standalone 9:16 Shorts, each its own arc with hook, captions, QC (skip with `--no-shorts`) |
| `shorts/short_XX.srt` / `.vtt` / `.qc.json` | per-Short captions and scene-quality report |
| `captions.srt` / `captions.vtt` | main-video captions, timed from the actual rendered scene durations |
| `quality.json` | per-scene animation quality report (sliding feet, collisions, ...) |
| `qc_report.json` | machine gates: ffprobe streams/resolution, black frames, audio level, frame brightness |
| `metadata.json` | title, description, tags, claims_to_verify, per-short titles/descriptions |
| `edit_decisions.json` | provenance: every kept segment mapped to its time range |
| `manifest.json` | every artifact with byte size + sha256 |
| `thumbnail.png`, `script.json`, `audio/`, `segments/` | thumbnail, reviewed script, per-line audio, per-scene clips (cache) |

## A week of videos (batch mode)

```
python batch.py plan "psychology of habits"          # LLM picks 7 topics, one per day -> queue.json
python batch.py plan --topics-file topics.txt        # or your own list ("topic | angle" per line)
python batch.py plan --format mix                    # alternate long videos and Shorts
python batch.py status
python batch.py run --scripts-only                   # write all 7 scripts, then edit output/*/script.json
python batch.py run                                  # render everything (resumable)
python batch.py run --upload                         # upload as private, scheduled to go public
```

- Publish times use `TIMEZONE` and `PUBLISH_TIME` from `.env` (default Africa/Kampala, 18:00). Change them there or per plan with `--time`.
- `queue.json` is plain JSON. Edit topics, dates or `status` by hand. `plan` appends after the last scheduled day; `--replace` starts over.
- A failed video is marked `failed` and the rest continue. `run --retry-failed` retries. Ctrl+C is safe: run again to resume.
- Scheduled uploads are private until their time, so you can review each one in YouTube Studio first.
- `--demo` works on `plan` and `run` too, to test the queue without keys.

## Web dashboard, desktop apps & Android app

The studio also runs as a web app, a desktop app and a phone app — all on top of the same CLI:

```
./start_web.sh                                # binds 0.0.0.0 -> http://127.0.0.1:8080 AND http://<LAN-IP>:8080
python3 webapp.py --port 8080                 # same (0.0.0.0 is the default)
python3 webapp.py --host 127.0.0.1            # local only
python3 desktop/launcher.py                   # desktop: local server + opens your browser
```

The server must be running for the port to answer — start it with one of the commands above
(and keep that terminal open), then open http://127.0.0.1:8080 . It prints its LAN addresses at
startup (e.g. `LAN: http://192.168.1.70:8080`) and answers UDP discovery probes on port 8081,
which is how the phone app's **Auto-discover** button finds it. Prebuilt app packages
(Linux binary, APK, Windows package) are downloadable in-browser at
**http://127.0.0.1:8080/downloads/** and on disk in `downloads/` (with `SHA256SUMS.txt`).

### Using it from your phone (the common "it doesn't connect" fix)

1. On the computer run `./start_web.sh` and **leave the terminal open** — nothing listens on
   8080 until then. It binds `0.0.0.0`, so the phone can reach it.
2. Phone and computer must be on the **same Wi-Fi**.
3. In the Android app: open → **Auto-discover** → Save (or type the computer's **LAN IP**,
   e.g. `192.168.1.70`, port `8080`). **Never `127.0.0.1` on the phone — that is the phone
   itself**, which is why `http://127.0.0.1:8080` in the phone's Chrome always fails. In Chrome
   use `http://<computer-LAN-IP>:8080` (shown in the server's startup log).
4. If the computer has a firewall, allow incoming port `8080`.
5. The app's error page shows this same checklist with the exact URL it tried.

The dashboard (stdlib-only, no extra dependencies) lets you start renders (topic / channel /
minutes / demo / shorts / force / upload), watch live logs, play the main video and every Short
in-page, read `qc_report.json` + `metadata.json`, download any artifact, delete jobs, and
plan/run the weekly batch queue. The JSON API behind it: `GET /api/jobs`, `POST /api/jobs`,
`POST /api/jobs/<name>/stop`, `GET /api/queue`, `POST /api/queue/plan|run`,
`GET /files/<job>/<path>` (HTTP Range supported, so video seeking works),
`GET /downloads/` + `GET /downloads/<file>` (app builds, served as attachments).

| Artifact | How to get it |
|---|---|
| **Linux desktop app** | `bash packaging/build_linux.sh` → `dist/lookthrough-studio` (PyInstaller single-file; verified booted on this aarch64 machine: `/api/health` OK, dashboard HTTP 200). Menu entry: `bash packaging/install_linux.sh` (`packaging/lookthrough-studio.desktop`). Stores jobs in `~/LookThroughStudio/` |
| **Windows .exe** | on a Windows machine: `packaging\build_windows.bat` → `dist\LookThroughStudio.exe` (PyInstaller spec `packaging/studio-windows.spec`). Or enable CI auto-builds — copy `packaging/release-workflow.yml` to `.github/workflows/release.yml` on GitHub (via the web UI, or push with a token that has the `workflow` scope) and push a `v*` tag: CI then builds the .exe, the Linux binary and the APK. Needs ffmpeg on PATH (`winget install ffmpeg`). A Windows .exe cannot be cross-compiled from Linux/ARM, so the ready-to-go Windows file is `downloads/LookThroughStudio-Windows.zip` (source + `START_WEB.bat` to run instantly, + `build_windows.bat` to produce the .exe in one command) |
| **Android APK** | `cd android && gradle --offline :app:assembleRelease` → `android/app/build/outputs/apk/release/app-release.apk`, also copied to `dist/LookThroughStudio.apk` + `downloads/LookThroughStudio.apk` (signed; `apksigner verify` passes). Install on a phone, open it, tap **Auto-discover** (UDP 8081 beacon) or enter the computer's LAN IP — see the phone checklist above. Full remote control: start renders, watch the queue, play videos/shorts fullscreen, download files. If the page can't load, the app shows an in-app error page explaining the causes. Zero-dependency Kotlin (plain `Activity` + `WebView`), so it builds fully offline |

Tests: `python3 tests/web_smoke.py` (19 API + file-serving checks incl. Range requests and path-traversal
blocking) and `python3 tests/web_e2e.py` (drives a full demo render through `POST /api/jobs` and checks
QC + the MP4). The desktop launcher doubles as the frozen binary's `--worker` mode, which is how the
packaged apps spawn renders as killable child processes.

## The animation engine

Characters act out the narration instead of standing beside captions. The script now contains a **cast** (outfit, hair,
accessories, build), and each scene lists **props**, a **camera**, and an ordered list of **actions** (walk to the desk, pull out
the chair, sit, pick up the book, open it, turn the page, react with surprise). Details, vocabulary and how to extend it are in
[ENGINE.md](ENGINE.md).

- 70 poses, about 95 actions, 25 parametric facial expressions, 16 props, 14 scenes
- 8 outfits (modern, hoodie, professional, prehistoric, toga, medieval, fantasy, sporty), 9 hairstyles, 13 accessories
- front, three-quarter, side, back and in-between views
- IK hands and feet, planted feet that do not slide, prop attachment points, collision checks
- an automatic quality report per scene: `output/<video>/quality.json`
- scene-level caching: edit one scene and only the affected scenes re-render; `--regen 3,5` forces specific ones

```
python3 main.py --demo              # 7-scene story: "What if nobody remembered you?" + shorts pack
python3 main.py --demo book         # the desk / chair / book sequence
python3 main.py --sheets            # pose, expression, outfit and scene preview PNGs
python3 main.py --showcase          # a video stepping through every pose with different outfits and faces
python3 main.py "topic" --regen 3   # re-render only scene 3 (1-based)
python3 tests/run_battery.py        # regression check of every action
python3 tests/acceptance.py output/demo-story   # QA gates F/G + exports on a finished job
```

## Files

| File | Job |
|---|---|
| `main.py` | One video (main + shorts pack) |
| `batch.py` | Weekly queue: plan, status, run |
| `config.py` | Settings, colours, channel tone prompts |
| `pipeline/script.py`, `llm.py` | Gemini JSON-schema calls, Groq fallback, backoff |
| `pipeline/planner.py`, `batchq.py` | Topic planning, queue file, schedule maths |
| `pipeline/voice.py` | edge-tts, one audio file per line |
| `pipeline/shorts.py` | picks >=4 arcs and renders each as a standalone 9:16 Short |
| `pipeline/captions.py` | SRT/VTT from real scene durations |
| `pipeline/qc.py` | ffprobe / black-frame / audio-level gates -> qc_report.json |
| `pipeline/produce.py` | orchestrates one job and writes all exports |
| `engine/` | The animation engine (see ENGINE.md) |
| `pipeline/scenes.py`, `poses.py` | Backgrounds; base pose data |
| `pipeline/render.py` | Pipes frames into FFmpeg |
| `pipeline/upload.py` | Resumable YouTube upload with optional `publishAt` |
| `webapp.py` + `web/` | Web dashboard + JSON API (jobs, queue, logs, Range file serving, `/downloads/` app builds) |
| `start_web.sh` / `START_WEB.bat` | One-command start of the web UI (Linux/macOS / Windows) |
| `downloads/` | Prebuilt packages, tracked in this repo and also served at `/downloads/`: Linux ARM64 binary, signed APK, Windows zip + `SHA256SUMS.txt` |
| `desktop/launcher.py` | Desktop launcher (entry point for the PyInstaller builds) |
| `packaging/` | PyInstaller specs, `build_linux.sh` / `build_windows.bat`, `.desktop` entry, icons, `make_icons.py` |
| `android/` | Kotlin companion APK (WebView client for the web UI + server settings/test screen) |
| `tests/` | `run_battery.py` (engine regression), `acceptance.py` (release gates), `web_smoke.py`, `web_e2e.py` |

## Uploading

1. Google Cloud Console: create a project, enable **YouTube Data API v3**.
2. Create an OAuth client of type **Desktop app**, save it as `client_secret.json` in this folder.
3. `python3 main.py "topic" --upload` (a browser opens once to log in). Main video **and every Short** are uploaded, all private/scheduled.

Uploads default to private (`YT_PRIVACY`). Google may keep uploads from unaudited API projects private
until the project passes a compliance audit, so test one video before relying on a weekly schedule.

## Verified evidence (offline demo, no API keys)

On this machine (Ubuntu 20.04 aarch64, Python 3.8, static ffmpeg with libx264):

```
python3 main.py --demo -y          # ~1m45s: main 1920x1080@24 video (30s) + 4 Shorts + all exports
python3 tests/run_battery.py       # 12 scenarios, 0 crashes, 0 hard quality failures
python3 tests/acceptance.py output/demo-story   # 17 gates, 0 failing -> ALL PASS
```

Observed artifacts in `output/demo-story/`: `video.mp4` (h264 1920x1080 + aac, 30.02s, 0 black segments),
`shorts/short_01..04.mp4` (each h264 1080x1920 + aac, 8.1s/9.6s/8.1s/3.5s, each with `.srt`/`.vtt`/`.qc.json`),
`captions.srt` (7 cues), `quality.json`, `qc_report.json` (all pass), `metadata.json`, `edit_decisions.json`,
`manifest.json` (sha256 per file), `thumbnail.png`. Real narration (edge-tts, no key) verified separately;
script generation needs `GEMINI_API_KEY`/`GROQ_API_KEY` — without them use `--demo`.

Known limitations: the demo story's `wake_up` beat trips a collision warning in `quality.json`;
YouTube upload is implemented but can only be exercised with real OAuth credentials (`client_secret.json`)
— never claimed as working without them. The Windows .exe is built by `packaging/build_windows.bat` on a
Windows machine or by the release workflow (PyInstaller cannot cross-compile, so it is not produced on this
Linux box); the Linux binary and the signed APK in `dist/` were built here.

## Notes

- `edge-tts` uses an unofficial Microsoft endpoint and can be throttled. If it breaks, replace `_speak` in `voice.py`.
- `containsSyntheticMedia` is `false` because this is a stylised cartoon with a generic voice. Set it to `true` if you add realistic imagery or a cloned voice.
- Free-tier limits and YouTube policy change often. Check them before relying on any number here.
- Fully automated, repetitive channels risk demonetisation as "mass-produced content". Keep the script review step, even in batch mode (`run --scripts-only`).
