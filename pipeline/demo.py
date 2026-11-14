"""Offline helpers: demo stories (no API keys needed), a week of sample topics, and a showcase."""
import json

from engine import face as F
from engine import library as lib
from engine.character import OUTFITS
from pipeline import scenes

H = {"id": "hero", "outfit": "hoodie", "hair": "short", "hair_color": "brown", "skin": "light", "accessories": ["glasses"]}
S = {"id": "stranger", "outfit": "professional", "hair": "long", "hair_color": "blond", "skin": "tan", "accessories": ["tie"]}


def a(actor, do, **kw):
    return dict(actor=actor, do=do, **kw)


STORY = {
    "title": "What If Nobody Remembered You?",
    "description": "A short demo made by the stickman animation engine.",
    "tags": ["psychology", "identity", "demo"], "claims_to_verify": [],
    "cast": [H, S],
    "segments": [
        {"text": "Imagine waking up in a world where nobody remembers you.", "headline": "Imagine", "scene": "room", "camera": "wide",
         "characters": [{"id": "hero", "x": 0.3, "facing": "right"}],
         "props": [{"id": "bed1", "type": "bed", "x": 0.3, "facing": 1}, {"id": "door1", "type": "door", "x": 0.68}],
         "actions": [a("hero", "wake_up", target="bed1"), a("hero", "express", emotion="confusion")]},
        {"text": "You get up, and something feels wrong.", "headline": "Something is off", "scene": "room", "camera": "wide",
         "characters": [{"id": "hero"}], "icon": "question",
         "actions": [a("hero", "stand_up"), a("hero", "walk_to", target="door1"), a("hero", "open_door", target="door1")]},
        {"text": "Outside, the street is full of people, and you know none of them.", "headline": "Strangers", "scene": "city", "camera": "wide",
         "characters": [{"id": "hero", "x": 0.15, "facing": "right"}, {"id": "stranger", "x": 0.78, "facing": "left"}],
         "actions": [a("hero", "walk_to", x=0.4), a("hero", "look_at", target="stranger")]},
        {"text": "You smile and greet someone you were sure you knew.", "headline": "Hello?", "scene": "city", "camera": "two_shot",
         "characters": [{"id": "hero"}, {"id": "stranger"}],
         "actions": [a("hero", "greet", target="stranger"), a("stranger", "react", emotion="skepticism")]},
        {"text": "They look straight through you, and walk away.", "headline": "Nothing", "scene": "city", "camera": "two_shot",
         "characters": [{"id": "hero"}, {"id": "stranger"}], "icon": "exclaim",
         "actions": [a("stranger", "shrug"), a("stranger", "walk_to", x=0.95), a("hero", "react", emotion="sadness")]},
        {"text": "So how much of who you are depends on being remembered?", "headline": "Who are you?", "scene": "mind", "camera": "close",
         "characters": [{"id": "hero", "x": 0.45, "facing": "right"}], "icon": "question",
         "actions": [a("hero", "think", duration=2.4), a("hero", "express", emotion="contemplation")]},
        {"text": "Maybe more than we like to admit.", "headline": "Maybe", "scene": "sunrise", "camera": "medium",
         "characters": [{"id": "hero", "x": 0.45, "facing": "right"}],
         "actions": [a("hero", "express", emotion="realization"), a("hero", "sit_down"), a("hero", "meditate", duration=2.0)]},
    ],
}

BOOK = {
    "title": "The Book That Surprised Me",
    "description": "Demo of a continuous action sequence.", "tags": ["demo"], "claims_to_verify": [],
    "cast": [H],
    "segments": [
        {"text": "He walks to the desk, pulls out the chair, and sits down.", "headline": "The desk", "scene": "room", "camera": "wide",
         "characters": [{"id": "hero", "x": 0.12, "facing": "right"}],
         "props": [{"id": "desk1", "type": "desk", "x": 0.64}, {"id": "chair1", "type": "chair", "x": 0.557, "facing": 1},
                   {"id": "book1", "type": "book", "x": 0.64, "on": "desk1", "dx": -0.3}],
         "actions": [a("hero", "walk_to", target="chair1"), a("hero", "sit_on", target="chair1")]},
        {"text": "He picks up a book, opens it, and turns the page.", "headline": "The book", "scene": "room", "camera": "medium",
         "characters": [{"id": "hero"}],
         "actions": [a("hero", "pick_up", target="book1"), a("hero", "open_book"), a("hero", "turn_page")]},
        {"text": "And then he sees something that changes everything.", "headline": "Wait...", "scene": "room", "camera": "close",
         "characters": [{"id": "hero"}], "icon": "exclaim",
         "actions": [a("hero", "react", emotion="surprise")]},
    ],
}

DEMOS = {"story": STORY, "book": BOOK}

DEMO_TOPICS = [
    ("Why do we fear being alone?", "Evolutionary roots of loneliness"),
    ("Is free will an illusion?", "Two sides of the debate, no verdict"),
    ("What is the bystander effect?", "A famous case and what research actually shows"),
    ("Why do we dream?", "Main scientific theories and their limits"),
    ("Can you really change your habits?", "How habits form, in plain terms"),
    ("What did the Stoics teach about anger?", "Practical ideas from Seneca and Marcus Aurelius"),
    ("Why does time feel faster as we age?", "Theories of time perception"),
]


def script(name="story"):
    return json.loads(json.dumps(DEMOS.get(name if isinstance(name, str) else "story", STORY)))


def showcase():
    """One short segment per pose, each with a different outfit, scene and facial expression."""
    outfits = list(OUTFITS)
    cast = [{"id": f"c{i}", "outfit": o, "hair": ["short", "long", "spiky", "bun", "ponytail", "afro", "messy", "mohawk"][i % 8],
             "hair_color": ["brown", "black", "blond", "red"][i % 4], "skin": ["light", "tan", "brown", "dark"][i % 4]}
            for i, o in enumerate(outfits)]
    segs = []
    for i, n in enumerate(lib.POSE_NAMES):
        who = f"c{i % len(cast)}"
        segs.append({"text": n.replace("_", " "), "headline": n.replace("_", " "), "scene": scenes.SCENES[(i // 5) % len(scenes.SCENES)],
                     "camera": "medium", "characters": [{"id": who, "x": 0.45, "facing": "right"}],
                     "actions": [{"actor": who, "do": "express", "emotion": F.EXPRESSIONS[i % len(F.EXPRESSIONS)]},
                                 {"actor": who, "do": n, "duration": 1.4}]})
    return {"title": "Pose showcase", "description": "", "tags": [], "claims_to_verify": [], "contains_synthetic_media": False,
            "cast": cast, "segments": segs}
