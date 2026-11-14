# ACCEPTANCE TESTS AND RELEASE GATES

A. Import an actual test MP4; ffprobe returns duration, codecs and sample rate. Reject invalid input gracefully.
B. Transcribe and produce timestamps. When models unavailable, demo fixture must be clearly labeled and the pipeline must still execute without pretending transcription occurred.
C. Demonstrate ad/irrelevance classification, human-editable excerpt selection, semantic continuity checks, and accurate source-time mappings. Preserve meaningful context and original voices.
D. Produce playable edited audio; no clipping or accidental dead air. Compare actual duration to edit timeline.
E. Generate a validated time-coded storyboard and render multiple distinct animated shots using a working local visual renderer, not just still-image concatenation.
F. Export a playable full-length MP4 with nonzero video/audio streams, reasonable A/V sync, correct resolution, and nonblack frames. Validate via ffprobe and frame sampling.
G. Produce >=4 separate, playable vertical MP4 Shorts (1080x1920 default) with distinct coherent content, authentic source-audio provenance, cinematic visuals, audible dialogue, captions, correct aspect ratio, duration, and audio/video synchronization. Validate each with ffprobe and playback inspection; do not substitute PNG frames or crops of arbitrary main-video segments.
H. Music on/off works; custom uploaded music is optional; voice stays intelligible.
I. Provider settings are usable; unavailable credentials show honest errors; a local demo path works without paid APIs.
J. UI supports job creation, inspection, cancel/resume, preview, export, and error logs; no fake buttons or nonfunctional placeholders presented as complete.
K. YouTube OAuth integration is implemented with private default and explicit approval; live upload only when credentials and user authorization exist. Never claim upload without verification.
L. Automated tests pass, sample production is actually rendered, file paths are verified, and README contains exact install/run/test commands.

Report a pass/fail table, limitations, test commands, observed evidence, and final artifacts. Do not mark any gate as passed without proof. If a dependency prevents a gate, identify exact blocker and the best functional fallback.
