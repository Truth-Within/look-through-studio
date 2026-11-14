"""Parametric facial expression system. A face is a dict of continuous parameters, not a fixed sprite."""
import math

DEFAULT = dict(
    eye=1.0, px=0.0, py=0.0,       # eye openness, pupil offset
    browL=0.0, browR=0.0, tilt=0.0,  # eyebrow heights, tilt (+ = angry, - = sad)
    open=0.0, smile=0.0, mw=1.0,   # mouth openness, curve (+ smile / - frown), width
    blush=0.0, tear=0.0, sweat=0.0, lid=0.0,
    post_head=0.0, post_spine=0.0,  # posture offsets (degrees) applied to the skeleton
)

EXPR = {
    "neutral": {},
    "happy": dict(smile=0.7, eye=0.9, browL=0.2, browR=0.2),
    "excited": dict(smile=1.0, open=0.6, eye=1.25, browL=0.6, browR=0.6, post_spine=-4),
    "amused": dict(smile=0.8, eye=0.75, browL=0.3, browR=-0.1, tilt=-0.1),
    "laughter": dict(smile=1.0, open=1.0, eye=0.2, browL=0.4, browR=0.4, post_head=-8),
    "sadness": dict(smile=-0.7, eye=0.85, tilt=-0.6, browL=0.2, browR=0.2, py=0.3, post_head=14, post_spine=8),
    "grief": dict(smile=-1.0, open=0.3, eye=0.6, tilt=-0.9, tear=1.0, py=0.4, post_head=20, post_spine=14),
    "anger": dict(smile=-0.6, eye=0.8, tilt=0.9, browL=-0.3, browR=-0.3, open=0.15, post_head=-4),
    "frustration": dict(smile=-0.5, eye=0.7, tilt=0.6, browL=-0.2, browR=-0.2, open=0.1, post_head=8, post_spine=4),
    "fear": dict(smile=-0.4, eye=1.35, tilt=-0.7, browL=0.9, browR=0.9, open=0.4, post_spine=8),
    "anxiety": dict(smile=-0.3, eye=1.2, tilt=-0.5, browL=0.6, browR=0.6, sweat=1.0, px=0.3, post_spine=6),
    "panic": dict(smile=-0.5, eye=1.5, tilt=-0.8, browL=1.0, browR=1.0, open=0.9, sweat=1.0, post_spine=10),
    "surprise": dict(eye=1.4, browL=1.0, browR=1.0, open=0.7, mw=0.6, post_spine=-6),
    "curiosity": dict(eye=1.1, browL=0.7, browR=0.1, smile=0.15, px=0.4, py=-0.2, post_head=10),
    "confusion": dict(eye=1.0, browL=0.8, browR=-0.3, smile=-0.2, mw=0.8, post_head=12),
    "skepticism": dict(eye=0.7, browL=0.9, browR=-0.4, smile=-0.15, lid=0.3),
    "concentration": dict(eye=0.75, browL=-0.3, browR=-0.3, tilt=0.4, mw=0.7, post_head=8),
    "contemplation": dict(eye=0.85, py=-0.5, px=0.3, browL=0.2, browR=0.4, post_head=-6),
    "embarrassment": dict(eye=0.8, smile=0.25, blush=1.0, py=0.5, tilt=-0.3, post_head=12, sweat=0.3),
    "disgust": dict(eye=0.6, browL=-0.5, browR=-0.5, tilt=0.5, smile=-0.8, mw=0.8, lid=0.2, post_head=-10),
    "fatigue": dict(eye=0.5, lid=0.7, smile=-0.2, browL=-0.2, browR=-0.2, post_head=18, post_spine=12),
    "confidence": dict(eye=0.95, smile=0.45, browL=0.2, browR=0.2, post_head=-6, post_spine=-4),
    "determination": dict(eye=0.9, tilt=0.6, smile=0.1, browL=-0.2, browR=-0.2, mw=0.9, post_spine=4),
    "realization": dict(eye=1.3, browL=0.9, browR=0.9, open=0.4, smile=0.2, post_head=-8),
    "sleepy": dict(eye=0.05, smile=0.1, post_head=10),
    "calm": dict(eye=0.12, smile=0.4),
}
EXPRESSIONS = list(EXPR)
ALIAS = {"scared": "fear", "angry": "anger", "sad": "sadness", "surprised": "surprise", "confused": "confusion",
         "joy": "happy", "laugh": "laughter", "worried": "anxiety", "tired": "fatigue", "shy": "embarrassment",
         "thinking": "contemplation", "proud": "confidence", "nervous": "anxiety", "shocked": "surprise"}


def expression(name):
    name = ALIAS.get(name, name)
    return {**DEFAULT, **EXPR.get(name, {})}


def lerp(a, b, k):
    return {key: a[key] + (b[key] - a[key]) * k for key in DEFAULT}


def blink(t, seed=0):
    """Eye-openness multiplier: a quick blink every ~4 seconds (different rhythm per character)."""
    ph = (t + seed * 1.37) % (3.6 + (seed % 5) * 0.37)
    return abs(ph - 0.08) / 0.08 if ph < 0.16 else 1.0


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)
