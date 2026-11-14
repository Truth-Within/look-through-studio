# TECHNICAL ARCHITECTURE

Recommended implementation: Python 3.12+ backend (FastAPI, Pydantic, SQLAlchemy/SQLite initially), React + TypeScript frontend, background job queue, FFmpeg/ffprobe media engine, local filesystem asset store with content hashes and manifests. Use practical alternatives when repository constraints justify them. Keep frontend/backend clearly separated and provide one-command local startup with setup docs.

Pipeline modules: ingestion -> probe -> ASR/diarization -> semantic segmentation -> excerpt decision engine -> audio assembly -> narration alignment -> creative director -> shot planner -> illustration renderer -> animation/compositing -> music mixer -> final encoding -> QC -> still-frame curation -> publishing. Persist artifacts and state at every stage. Use versioned structured schemas and validation at each boundary.

Provider interface contracts: `transcribe(media, config)`, `analyze(transcript, context)`, `plan_shots(audio_timeline, style)`, `generate_image(shot, references)`, `generate_motion(shot, assets)`, `evaluate_visual(shot, render)`. Implement capability discovery, credential verification, per-stage provider selection, model selection, timeout/retry, budget, fallback, and provider health. Potential providers: faster-whisper/Whisper, Gemini, Anthropic, OpenAI, Ollama/OpenCode-compatible endpoints, ComfyUI image/video workflows, and other compliant image/video APIs. Do not assume a chat subscription includes API credits.

Animation: implement reliable local 2D/vector compositing for stick figures, articulated poses, face/expression library, motion paths, keyframes, camera pan/zoom/parallax, layers, light/color treatments, masks, and transitions. SVG/Lottie/Blender or a deterministic renderer may be used; FFmpeg handles compositing and encoding. AI imagery supplements—not replaces—coherent programmatic animation. Make all shots renderable in a no-paid-API demo mode using actual generated motion graphics.

Data model: SourceAsset, TranscriptSegment, ExcerptDecision, EditedAudioTimeline, Scene, Shot, VisualAsset, RenderJob, QualityFinding, ExportBundle, ProviderConfig, PublishRequest. Each shot references edited-audio time range, semantic objective, visual style, shot type, camera plan, animation plan, asset IDs, transition, and QC status.

YouTube: OAuth 2.0 installed/web flow, encrypted token storage, least privilege, token refresh, disconnect, privacy defaults to private, user confirmation before upload and especially public release. Handle quota and upload retries. Never hardcode channel ID.

Security: accept user-provided source files only within authorized access; validate types and size; prevent path traversal and shell injection; sanitize prompts, secrets and logs; store secrets in environment/keyring; support rights confirmation. Provide a content provenance trail and an editorial preview before publication.
