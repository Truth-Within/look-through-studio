# PRODUCT REQUIREMENTS

## User journey
1. Import local source video, inspect metadata and playback, select language and topic if desired.
2. Transcribe with word-level or segment-level timestamps and confidence; diarize if useful.
3. Detect introductions, advertisements, sponsor reads, irrelevant digressions, repetition, and coherent topic-bearing excerpts. Produce editable keep/drop decisions and reasons.
4. Assemble original audio excerpts in coherent sequence with intelligible cuts, controlled silence, crossfades only where appropriate, loudness normalization, noise reduction, and no synthetic speech substitution by default.
5. Analyze the final edited narration semantically, identify concepts, emotional beats, entities, transitions, and visual opportunities. Produce a time-coded shot plan with explicit narration-to-shot traceability.
6. Generate consistent illustrations and cinematic motion, with default stick-figure visual grammar and topic-adaptive alternatives. Maintain character and prop continuity across shots.
7. Add optional user-supplied licensed music with automatic ducking, fades, loudness control, and preview.
8. Render full production with synchronized audio, transitions, captions, and optional opening/closing cards.
9. Export final video, at least four compelling PNG frames actually extracted from different moments of final render, editable metadata, caption file, audio master, QC report, and edit decision list.
10. Provide secure YouTube OAuth connection, upload preview, title/description/tags/privacy/schedule settings; only publish after explicit approval.

## UI
Project dashboard, import wizard, source preview, transcript with synchronized waveform and excerpt markers, audio edit timeline, storyboard and shot inspector, visual style chooser, AI provider configuration, music mixer, preview renderer, full render queue, job logs, QC panel, asset gallery, export center, YouTube connection/publish center. Autosave, resume, rerun failed stage, and regenerate one shot without restarting whole job.

## Deliverables
`final_video.mp4`, `shorts/short_01.mp4` through `shorts/short_04.mp4` (minimum), per-output captions and metadata, `edited_voice.wav`, `captions.srt`, `captions.vtt`, `thumbnail_candidates/`, `edit_decisions.json`, `shot_plan.json`, `qc_report.json`, `metadata.json`, `manifest.json`. Four actual SHORT VIDEOS are mandatory; still images do not count.

## Output defaults
16:9, 1920x1080, H.264/AAC MP4, 24 or 30 fps selectable, 4K optional if the pipeline genuinely supports it. Respect input and output duration; no hardcoded duration. Main video: 16:9, 1920x1080. Shorts: 9:16, 1080x1920, individually edited and rendered, generally 20–60 seconds by default (configurable; no hardcoded limit). Select four distinct, self-contained high-impact moments; write opening hooks using authentic audio, maintain meaning, create vertically composed scene plans, generate or recompose cinematic visuals for portrait orientation, mix music optionally, add safe-area-aware captions, and test every Short separately. Never merely crop random sections from the main render.

## Nonfunctional
Recoverable jobs, clear logs, deterministic manifest, file validation, disk quota warnings, accessible UI, secure uploads, sandboxed processing, provider rate limits, credential protection, cancellation, progress and cost estimates, no unlicensed asset downloading.
