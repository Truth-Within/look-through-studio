# Autonomous Production Workflow and Data Contracts

## End-to-end sequence
1. Scheduler or user request creates a job.
2. Idea agent proposes/ranks topics; user-supplied topic bypasses discovery.
3. Research agent gathers sources, claim notes, and uncertainties.
4. Script agent writes narrative with source traceability.
5. Editorial validation checks structure, claims, originality, and duration.
6. Storyboard agent divides script into timed scenes with exact narration excerpts.
7. TTS agent produces audio and alignment/timestamps.
8. Visual director creates character/prop/background/action plans.
9. Animation renderer generates scene clips; infographics and diagrams as needed.
10. Editor assembles scenes, audio, subtitles, music, transitions.
11. QA checks audio, video, text, timing, source/asset issues.
12. Defective components are regenerated selectively.
13. Metadata agent generates thumbnail, title, description, chapters, hashtags, sources.
14. Publisher uploads PRIVATE via YouTube API, then awaits explicit human approval.

## Agent design
'Agents' are logical responsibilities, not necessarily separate paid API calls. Prefer a shared model, validated schemas, deterministic transforms, and clear stage boundaries. Preserve reproducibility: record prompts, model versions, asset IDs, and seeds when available.

## Job structure
Store job_id, topic, status, settings, budget, created_at, updated_at, source manifest, script version, narration files, scene manifests, rendered clips, final video, metadata, QA report, and upload status. Maintain state in SQLite and assets under organized job directories.

## Scene schema concept
scene_id; exact_script_excerpt; start_ms; end_ms; characters [{id, rig, pose, expression, actions}]; props; background; camera; text; audio_alignment; asset_refs; render_status; qa_issues. Define and validate the exact schema in code.

## Scheduling
Initial production goal: 2 long videos + 3 Shorts per week. Queue jobs and avoid overwhelming local CPU/RAM. Allow pause, resume, cancel, rerun stage, and regenerate scene.

## QA and recovery
Check missing files, ffprobe duration, blank frames, clipped text, silence, volume spikes, subtitle mismatch, out-of-range joints, wrong aspect ratio, and duplicate uploads. Research/factual QA should expose uncertainty and allow human review. Save checkpoints so power loss or failure does not restart the entire pipeline.

## Publishing safety
YouTube upload privacy=private. Public release requires explicit user action. Track upload IDs and retries to prevent duplicate publishing. Never silently change publishing policy.
