"""Shared Gemini instructions and bounded, project-local dialogue context.

No SDK, credentials, audio dependencies or network required to load the skill.
"""
import json
from pathlib import Path

SKILL_PATH = Path(__file__).resolve().parents[1] / "skills" / "interpretar-emocion-musical" / "SKILL.md"


def load_emotion_skill():
    text = SKILL_PATH.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"Falta la cabecera de la skill: {SKILL_PATH}")
    _, _, body = text.split("---", 2)
    if not body.strip():
        raise ValueError(f"Skill vacía: {SKILL_PATH}")
    return body.strip()


class EmotionContext:
    """Recent successful exchanges, not permanent memory or inferred psychology."""

    def __init__(self, max_chars=24000):
        self.max_chars = max_chars
        self.turns = []

    def record(self, user, assistant):
        # Bound individual exchanges as well as total context. Keep roles explicit.
        limit = self.max_chars // 4
        self.turns.append({"usuario": user[-limit:], "asistente": assistant[-limit:]})
        while len(self.turns) > 1 and len(self.as_json()) > self.max_chars:
            self.turns.pop(0)

    def as_json(self):
        return json.dumps(self.turns, ensure_ascii=False)

    def clear(self):
        self.turns.clear()
