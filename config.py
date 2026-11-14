"""Central settings. Override any of them in .env"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

TTS_VOICE = os.getenv("TTS_VOICE", "en-US-GuyNeural")
TTS_RATE = os.getenv("TTS_RATE", "-5%")

FPS = int(os.getenv("FPS", "24"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))
YT_PRIVACY = os.getenv("YT_PRIVACY", "private")  # keep private until you've reviewed it

# Batch mode
TIMEZONE = os.getenv("TIMEZONE", "Africa/Kampala")  # IANA name, used for publish times
PUBLISH_TIME = os.getenv("PUBLISH_TIME", "18:00")   # local time each scheduled video goes public
QUEUE_FILE = Path(os.getenv("QUEUE_FILE", "queue.json"))

LANDSCAPE = (1920, 1080)   # main video: 16:9 1080p H.264/AAC
SHORTS = (1080, 1920)      # 9:16 and <= 180s => YouTube treats it as a Short
SEGMENT_PAD_SEC = 0.35  # silence after each narration line

# Colours (flat 2D look)
BG = (18, 21, 31)
INK = (240, 236, 226)
ACCENT = (255, 196, 61)
MUTED = (70, 76, 96)

CHANNELS = {
    "human": (
        "The Human Question: psychology and philosophy for curious adults. Warm, reflective, "
        "plainspoken. Poses one big question, explores it from 2-3 angles, and ends with "
        "something the viewer can take away."
    ),
    "unveiled": (
        "The Unveiled Reality: hidden history, esoteric ideas and little-known science. "
        "Intriguing but intellectually honest: clearly separate documented fact from "
        "tradition, legend and speculation."
    ),
}
