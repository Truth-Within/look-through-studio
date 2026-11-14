"""Ask the LLM for a week of distinct video topics."""
import config
from pipeline import demo, llm

SCHEMA = {
    "type": "OBJECT",
    "properties": {"ideas": {"type": "ARRAY", "items": {
        "type": "OBJECT",
        "properties": {"topic": {"type": "STRING"}, "angle": {"type": "STRING"}},
        "required": ["topic", "angle"]}}},
    "required": ["ideas"],
}
SHAPE_HINT = 'Return ONLY JSON: {"ideas": [{"topic": str, "angle": str}]}'

SYSTEM = """You are the content planner for a faceless YouTube channel.
CHANNEL: {tone}

Plan exactly {n} distinct video topics for one week.
- Each "topic" is a specific, curiosity-driven title-style question or claim (max 80 characters).
- Vary the approach across the week: history, a famous experiment, a thought experiment, everyday life, a common myth.
- Only choose topics that can be covered accurately without inventing statistics, studies or quotes.
- "angle" is one sentence on how the video should treat the topic.
"""


def plan(theme, n, channel, use_demo=False):
    """Returns a list of (topic, angle)."""
    if use_demo:
        return (demo.DEMO_TOPICS * 3)[:n]
    user = f"Give me {n} topics" + (f" around the theme: {theme}" if theme else " that fit the channel")
    data = llm.json_call(SYSTEM.format(tone=config.CHANNELS[channel], n=n), user, SCHEMA, SHAPE_HINT)
    ideas = [(i["topic"].strip(), i.get("angle", "").strip()) for i in data["ideas"] if i.get("topic", "").strip()]
    if not ideas:
        raise RuntimeError("Planner returned no topics")
    return ideas[:n]
