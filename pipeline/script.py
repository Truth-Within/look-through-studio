"""Stage 1: topic -> a directed script (cast, scenes, props, actions) for the animation engine."""
import config
from engine import actions as AC
from engine import face as F
from engine import library as lib
from engine.character import ACCESSORIES, BUILDS, HAIR_COL, HAIRSTYLES, OUTFITS, SKIN
from engine.props import PROP_TYPES
from pipeline import llm, scenes

CAMERAS = ["wide", "medium", "close", "follow", "two_shot"]
ICONS = ["none", "question", "exclaim", "lightbulb", "heart"]
FACINGS = ["left", "right", "viewer", "away"]
ACTION_NAMES = sorted(set(AC.NAMES) | set(lib.POSE_NAMES))

ACTION_GUIDE = """\
  locomotion: walk_to, jog_to, run_to, sprint_to (target=prop/character id, or x), jump, hop, crawl_to, climb (target=ladder), dance, fall, get_up, stumble, turn_to (target)
  postures: sit_down/sit_on (target=chair/bed), stand_up, squat, crouch, kneel, lie_down (target=bed), wake_up (target=bed), bend, lean, stretch
  upper body: point_at (target), wave, clap, reach_for (target), push/pull (target prop), throw (target prop, x), catch, carry/lift (target prop), hug (with), cross_arms, shrug, bow, salute, pray, flex, think
  objects: pick_up (target), put_down (on=desk id), pull_chair (target chair), open_book, turn_page, read, write, type, use_phone, eat, drink, cook, open_door (target door), use_tool (hammer)
  social: greet (target character), shake_hands (with), hand_over (target prop, with), argue (with), teach (target board), listen, help (with)
  feelings: express (emotion), react (emotion: also moves the body), look_at (target)
  any pose name also works as "do" (e.g. facepalm, hands_on_hips, cheer)"""

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING"},
        "description": {"type": "STRING"},
        "tags": {"type": "ARRAY", "items": {"type": "STRING"}},
        "claims_to_verify": {"type": "ARRAY", "items": {"type": "STRING"}},
        "cast": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "id": {"type": "STRING"}, "outfit": {"type": "STRING", "enum": list(OUTFITS)},
            "hair": {"type": "STRING", "enum": HAIRSTYLES}, "hair_color": {"type": "STRING", "enum": list(HAIR_COL)},
            "skin": {"type": "STRING", "enum": list(SKIN)}, "build": {"type": "STRING", "enum": list(BUILDS)},
            "accessories": {"type": "ARRAY", "items": {"type": "STRING", "enum": ACCESSORIES}}},
            "required": ["id", "outfit", "hair"]}},
        "segments": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "text": {"type": "STRING"}, "headline": {"type": "STRING"},
            "scene": {"type": "STRING", "enum": scenes.SCENES}, "camera": {"type": "STRING", "enum": CAMERAS},
            "speaker": {"type": "STRING"}, "icon": {"type": "STRING", "enum": ICONS},
            "characters": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
                "id": {"type": "STRING"}, "x": {"type": "NUMBER"}, "facing": {"type": "STRING", "enum": FACINGS}},
                "required": ["id"]}},
            "props": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
                "id": {"type": "STRING"}, "type": {"type": "STRING", "enum": PROP_TYPES}, "x": {"type": "NUMBER"},
                "on": {"type": "STRING"}, "dx": {"type": "NUMBER"}, "facing": {"type": "INTEGER"}},
                "required": ["id", "type"]}},
            "actions": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
                "actor": {"type": "STRING"}, "do": {"type": "STRING", "enum": ACTION_NAMES},
                "target": {"type": "STRING"}, "x": {"type": "NUMBER"}, "with": {"type": "STRING"},
                "emotion": {"type": "STRING", "enum": F.EXPRESSIONS}, "duration": {"type": "NUMBER"}},
                "required": ["actor", "do"]}}},
            "required": ["text", "headline", "scene", "characters", "actions"]}},
    },
    "required": ["title", "description", "tags", "claims_to_verify", "cast", "segments"],
}

SHAPE_HINT = (
    'Return ONLY JSON: {"title","description","tags":[],"claims_to_verify":[],"cast":[{"id","outfit","hair","hair_color","skin","build",'
    '"accessories":[]}],"segments":[{"text","headline","scene","camera","speaker","icon","characters":[{"id","x","facing"}],'
    '"props":[{"id","type","x","on","dx","facing"}],"actions":[{"actor","do","target","x","with","emotion","duration"}]}]}. '
    f"scene in {scenes.SCENES}; camera in {CAMERAS}; prop type in {PROP_TYPES}; outfit in {list(OUTFITS)}; "
    f"hair in {HAIRSTYLES}; emotion in {F.EXPRESSIONS}; do in {ACTION_NAMES}."
)

SYSTEM = """You are the writer AND director of a faceless YouTube channel animated by a procedural 2D stickman engine.
CHANNEL: {tone}

WRITING
- About {words} words of narration, in segments of 1-2 short sentences (max 28 words each). Segment 1 is a hook.
- "text" is spoken English only: no stage directions, emojis, markdown or URLs.
- Never invent studies, quotes, statistics or experts. List every claim a human should double-check in "claims_to_verify".
- title <= 70 characters; description 2-3 sentences, no hashtags; 8-12 tags. "headline" is a 1-4 word on-screen keyword.

DIRECTING - the characters must ACT OUT the narration, not stand beside it.
- cast: 1-4 recurring characters (id, outfit, hair, hair_color, skin, build, accessories). Outfits: {outfits}. Use historical or
  prehistoric outfits when the topic calls for it. Reuse the same ids in every segment for continuity.
- Each segment lists "characters" on stage (id, x between 0.1 and 0.9, facing left/right/viewer), the "scene" background
  (keep it for 2-5 segments; change when the topic shifts), a "camera" (wide, medium, close, follow, two_shot) and an "icon".
  Scenes: {scene_guide}.
- "props": objects needed in this segment ({prop_types}). Give each an id, an x, and "on" (a desk id) for items on a desk.
  Reuse an id to keep the same object; objects persist while the scene stays the same.
- "actions": an ordered list performing the narration. Each has actor, do, and optional target / x / with / emotion / duration.
{action_guide}
- Emotions for express/react: {emotions}.
- Be physically logical: walk to a chair before sitting, pick up a book before opening it, stand up before walking, open the
  door before walking through. 2-6 actions per segment, never the same action three times in a row, show feelings with
  react/express. Set "speaker" only when a character is talking. Targets must be ids of props or characters on stage.
- Character x positions: keep them apart (at least 0.25) unless they hug or shake hands.
"""


def _normalise(s):
    cast = [c for c in s.get("cast", []) if c.get("id")]
    if not cast:
        cast = [{"id": "hero", "outfit": "hoodie", "hair": "short"}]
    ids = {c["id"] for c in cast}
    segs = [x for x in s.get("segments", []) if str(x.get("text", "")).strip()]
    if not segs:
        raise ValueError("Model returned no usable segments")
    last_scene = "void"
    for x in segs:
        x["text"], x["headline"] = x["text"].strip(), str(x.get("headline", "")).strip()
        x["scene"] = x.get("scene") if x.get("scene") in scenes.SCENES else last_scene
        last_scene = x["scene"]
        x["camera"] = x.get("camera") if x.get("camera") in CAMERAS else "medium"
        x["icon"] = x.get("icon") if x.get("icon") in ICONS else "none"
        chars = [c for c in x.get("characters", []) if c.get("id") in ids]
        x["characters"] = chars or [{"id": cast[0]["id"]}]
        on = {c["id"] for c in x["characters"]}
        x["actions"] = [a for a in x.get("actions", []) if a.get("actor") in on and a.get("do")]
        if x.get("speaker") not in on:
            x.pop("speaker", None)
    s.update(cast=cast, segments=segs)
    s.setdefault("tags", [])
    s.setdefault("claims_to_verify", [])
    s["contains_synthetic_media"] = False  # stylised cartoon + generic TTS voice
    return s


def upgrade(script):
    """Turn an older pose/mood/prop script into the cast/actions format so cached scripts keep working."""
    if script.get("cast"):
        return script
    script["cast"] = [{"id": "hero", "outfit": "hoodie", "hair": "short", "hair_color": "brown", "accessories": ["glasses"]}]
    for seg in script["segments"]:
        if "actions" in seg:
            continue
        seg["characters"] = [{"id": "hero", "x": 0.42}]
        acts = []
        if seg.get("mood") and seg["mood"] not in ("neutral",):
            acts.append({"actor": "hero", "do": "express", "emotion": seg["mood"]})
        acts.append({"actor": "hero", "do": seg.get("pose", "stand"), "duration": 1.6})
        seg["actions"] = acts
        if seg.get("prop") in ICONS:
            seg["icon"] = seg["prop"]
    return script


def generate(topic, minutes, channel, notes=""):
    system = SYSTEM.format(
        tone=config.CHANNELS[channel], words=int(minutes * 150), outfits=", ".join(OUTFITS), scene_guide=scenes.SCENE_GUIDE,
        prop_types=", ".join(PROP_TYPES), action_guide=ACTION_GUIDE, emotions=", ".join(F.EXPRESSIONS))
    user = f"Write and direct a video about: {topic}"
    if notes:
        user += f"\nAngle to take: {notes}"
    return _normalise(llm.json_call(system, user, SCHEMA, SHAPE_HINT))
