"""Stage 2: narration text -> one audio file per segment (edge-tts, no key needed)."""
import asyncio
import subprocess

import config


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


async def _speak(text, path):
    import edge_tts  # lazy so --demo works without it

    for attempt in range(3):
        try:
            await edge_tts.Communicate(text, config.TTS_VOICE, rate=config.TTS_RATE).save(str(path))
            return
        except Exception as e:
            print(f"  TTS retry {attempt + 1}: {e}")
            await asyncio.sleep(2 * (attempt + 1))
    raise RuntimeError("edge-tts failed 3 times (service may be throttling you)")


def _silence(text, path):
    secs = max(1.5, len(text.split()) / 2.6)  # ~156 wpm
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", "anullsrc=r=24000:cl=mono", "-t", f"{secs:.2f}", str(path)],
        check=True,
    )


def synthesize(script, outdir, demo=False, force=False):
    outdir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, seg in enumerate(script["segments"]):
        path = outdir / f"seg_{i:02d}.{'wav' if demo else 'mp3'}"
        if force or not path.exists():
            print(f"  voice {i + 1}/{len(script['segments'])}")
            if demo:
                _silence(seg["text"], path)
            else:
                asyncio.run(_speak(seg["text"], path))
        paths.append(path)
    return paths
