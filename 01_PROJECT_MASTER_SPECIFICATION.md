# The Human Question — Master Project Specification

## Vision
Build a modular, affordable, autonomous AI production studio for original educational YouTube documentaries and Shorts. The signature format is expressive 2D stickman animation, not a static slideshow. The studio must research topics, verify facts, write engaging scripts, direct character performances, synthesize narration, render synchronized animation, perform quality checks, generate metadata, and upload privately for human approval.

## Content identity
Channel: The Human Question. Themes: human psychology, evolution, biology, history, ancient civilizations, science, philosophy, technology, belief, and human behavior. Voice: calm, intelligent, curious, slightly eerie when appropriate, natural and conversational. Explain surprising questions about why the world and humans are the way they are.

## Main objective
Generate publishable-quality videos with minimal intervention and minimal recurring cost, while preserving editorial accuracy, originality, consistent characters, and human approval before public publication.

## Goals
1. Research credible sources and avoid invented citations.
2. Produce compelling, accurate documentary scripts and Shorts.
3. Convert each script into a timed, machine-readable storyboard.
4. Render consistent, expressive, moving stickman characters.
5. Use Kokoro TTS or another affordable local narration engine.
6. Synchronize speech, character motion, expressions, on-screen text, subtitles, and backgrounds.
7. Generate diagrams, infographics, timelines, props, and environments relevant to narration.
8. Produce complete 16:9 long-form and 9:16 Shorts.
9. Create thumbnail, title, description, source list, chapters where appropriate, and tags.
10. Run automated quality checks and selectively re-render bad scenes.
11. Upload via official YouTube API as private; wait for explicit approval to publish.
12. Support two long-form videos and three Shorts per week as an initial target.
13. Keep modules replaceable, observable, testable, and recoverable after interruptions.

## Video lengths
Long-form presets: 5–6, 8–10, and 12–15 minutes, plus custom. Shorts: configurable vertical duration. Actual number of scenes is determined by narration and visual needs, not a mandatory fixed image count.

## Product capabilities
- Idea discovery and user-supplied topics
- Source-backed research and claim checking
- Script and storyboard generation
- Character identity and asset library
- Animation and scene composition
- Natural TTS with timing
- Music/SFX with appropriate licensing
- Video editing, captions, thumbnails
- Quality control and scene-level repair
- Private YouTube uploads and approval
- Local dashboard for jobs, previews, costs, settings, and approvals

## Non-negotiable constraints
Free/open-source/local-first; no assumed GPU; preserve existing working code; don't invent evidence or claim untested code works; no unauthorized public uploads; comply with copyright, source licensing, and YouTube rules. Work incrementally and verify every milestone.

## Definition of done
A topic can become a researched, narrated, animated, edited, technically checked video uploaded privately, with a clear approval workflow. Each step is traceable and rerunnable without regenerating everything.
