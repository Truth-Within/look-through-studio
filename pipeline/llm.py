"""Shared JSON-mode LLM calls: Gemini first, Groq as fallback, backoff on 429/5xx."""
import json
import random
import time

import requests

import config


def post(url, headers, payload, tries=5):
    for attempt in range(tries):
        r = requests.post(url, headers=headers, json=payload, timeout=120)
        if r.status_code in (429, 500, 502, 503, 504):
            delay = 2 * 2**attempt + random.random()
            print(f"  API busy ({r.status_code}); retrying in {delay:.1f}s")
            time.sleep(delay)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"API still failing after {tries} tries: {url}")


def _gemini(system, user, schema):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema, "temperature": 0.8},
    }
    data = post(url, {"x-goog-api-key": config.GEMINI_API_KEY}, payload)
    return json.loads(data["candidates"][0]["content"]["parts"][0]["text"])


def _groq(system, user, shape_hint):
    payload = {
        "model": config.GROQ_MODEL,
        "messages": [{"role": "system", "content": system + "\n\n" + shape_hint},
                     {"role": "user", "content": user}],
        "response_format": {"type": "json_object"},
        "temperature": 0.8,
    }
    data = post("https://api.groq.com/openai/v1/chat/completions",
                {"Authorization": f"Bearer {config.GROQ_API_KEY}"}, payload)
    return json.loads(data["choices"][0]["message"]["content"])


def json_call(system, user, schema, shape_hint):
    errors = []
    for name, key, fn in (
        ("Gemini", config.GEMINI_API_KEY, lambda: _gemini(system, user, schema)),
        ("Groq", config.GROQ_API_KEY, lambda: _groq(system, user, shape_hint)),
    ):
        if not key:
            continue
        try:
            print(f"  asking {name}...")
            return fn()
        except Exception as e:
            errors.append(f"{name}: {e}")
            print(f"  {name} failed: {e}")
    if errors:
        raise RuntimeError("No LLM provider worked. " + " | ".join(errors))
    raise RuntimeError("Set GEMINI_API_KEY (or GROQ_API_KEY) in .env, or use --demo.")
