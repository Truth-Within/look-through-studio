# Downloadable builds — The Look Through Studio

| File | What it is | How to run |
|---|---|---|
| `LookThroughStudio-Linux-arm64` | Single-file Linux app (ARM64/aarch64, 37 MB) — starts the web UI and opens the browser | `chmod +x LookThroughStudio-Linux-arm64 && ./LookThroughStudio-Linux-arm64` → http://127.0.0.1:8080 |
| `LookThroughStudio.apk` | Android companion app (signed, 0.6 MB) — WebView client for the web UI | Install on Android → open it → tap **Auto-discover** (same Wi-Fi as the computer), or enter the computer's LAN IP, e.g. `192.168.1.70` port `8080` — **never** `127.0.0.1` (on the phone that is the phone itself). In the phone's Chrome, open `http://<computer-LAN-IP>:8080` |
| `LookThroughStudio-Windows.zip` | Windows package: full source + `START_WEB.bat` + `packaging\build_windows.bat` | Unzip on Windows → double-click `START_WEB.bat` (needs Python 3.10+ and ffmpeg), or run `packaging\build_windows.bat` to produce `dist\LookThroughStudio.exe` |

Notes
- The Linux binary is **ARM64** (built on this machine). On x86_64 Linux, run from
  source instead: `python3 webapp.py`, or build your own with `packaging/build_linux.sh`.
- A Windows `.exe` cannot be produced on Linux/ARM (no cross-compiler), so the
  Windows file ships as source + a one-command build script; to have the real
  `.exe` built automatically on `v*` tags, enable the CI workflow by copying
  `packaging/release-workflow.yml` to `.github/workflows/release.yml` on GitHub
  (web UI, or a token with the `workflow` scope).
- All three frontends talk to the same web UI: start it with `./start_web.sh`
  (binds `0.0.0.0`, so it answers on both http://127.0.0.1:8080 on the computer
  **and** http://\<LAN-IP\>:8080 from the phone). The server prints its LAN
  addresses at startup and answers UDP discovery probes on port 8081 (that is
  how the app's Auto-discover button finds it). The **Downloads** page is at
  http://127.0.0.1:8080/downloads/
- Phone won't connect? Checklist: server running (`./start_web.sh`, leave the
  terminal open) → phone and computer on the same Wi-Fi → use the computer's
  LAN IP, not 127.0.0.1 → firewall allows port 8080. The app shows this
  checklist on its error page.
- Renders require `ffmpeg` on PATH. The web UI checks and reports this at `/api/health`.

SHA-256 checksums: see `SHA256SUMS.txt`.
