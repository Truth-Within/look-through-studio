# Technical Environment, Model Selection, and Cost Policy

## Target machine
Fedora Linux; Lenovo ThinkPad T14 Gen 2 Intel, 11th-gen Core i7, 16 GB RAM, 1 TB SSD. Do not assume NVIDIA CUDA or a powerful discrete GPU. Use Python virtual environments and Fedora-compatible commands.

## Existing work to preserve
Previous experiments used ~/Downloads/youtube-studio-stage1, FastAPI/Uvicorn at 127.0.0.1:8000, FFmpeg, Python, n8n, Ollama, and files including app/main.py, character_v2.py, and main_ollama.py. These are historical context, not proof that the files are attached or currently functional. Inspect current copies before editing. Never overwrite without backup/version control.

## Audio decision
Kokoro TTS Balanced at speed 1.0 was preferred for natural sound; the 'Heart' voice was favored. Piper sounded distorted in prior tests. Some playback issues were player/device-dependent. Validate exported WAV audio, not just live playback. Maintain consistent loudness and timing.

## Preferred components
- Python + FastAPI + Pydantic for backend and structured interfaces.
- FFmpeg for audio/video encoding and validation.
- Ollama with a locally runnable model for ideation, writing, and structured planning when feasible.
- Kokoro TTS for narration.
- SVG/2D skeletal renderer and inverse kinematics for character animation.
- SQLite for initial job state; PostgreSQL only if needed later.
- n8n for scheduling/orchestration where it adds value.
- Official YouTube Data API with OAuth for private uploads.
- Local browser-based dashboard; lightweight frontend.

## Model routing
Use deterministic code for timing, rendering, transformations, and validation. Use local LLMs for feasible planning tasks; optional low-cost cloud models for difficult reasoning if explicitly enabled. Never require a paid key for basic operation. Compare actual quality, latency, memory, context limits, and cost before choosing a model.

## Cost controls
Track provider, model, input/output tokens, estimated charge, per-job spend, monthly caps, and free-tier usage. Cache source research, TTS, animation primitives, and reusable assets. Batch work and skip unchanged stages. Fail safely if spending limits are reached. Free tiers and provider prices can change: verify them before making current cost claims.

## Security and operations
Keep keys in environment variables or a secrets store; never commit credentials. Use idempotent jobs, bounded retries, logs, resource limits, and safe file paths. Private uploads only. No copyrighted assets without appropriate rights.
