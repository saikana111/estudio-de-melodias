"""Shared Gemini instructions and bounded, project-local dialogue context.

No SDK, credentials, audio dependencies or network required to load the skill.
"""
import json
from pathlib import Path

SKILL_PATH = Path(__file__).resolve().parents[1] / "skills" / "interpretar-emocion-musical" / "SKILL.md"


def load_emotion_skill(skill_path=SKILL_PATH):
    """Inline the complete local knowledge pack; Gemini needs no file/web tools.

    Sorted Markdown/JSON files in knowledge/ are picked up on application restart.
    Fail visibly on missing/invalid material instead of silently dropping guidance.
    """
    skill_path = Path(skill_path)
    text = skill_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"Falta la cabecera de la skill: {skill_path}")
    _, _, body = text.split("---", 2)
    if not body.strip():
        raise ValueError(f"Skill vacía: {skill_path}")
    knowledge = skill_path.parent / "knowledge"
    files = sorted(p for p in knowledge.rglob("*") if p.suffix in (".md", ".json"))
    if not files:
        raise ValueError(f"Falta la base de conocimiento: {knowledge}")
    sections = [body.strip()]
    for path in files:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            raise ValueError(f"Conocimiento vacío: {path}")
        if path.suffix == ".json":
            # Parse before sending; compact representation avoids formatting tokens.
            content = json.dumps(json.loads(content), ensure_ascii=False, separators=(",", ":"))
        sections.append(f"\n\n--- Material local: {path.relative_to(knowledge).as_posix()} ---\n{content}")
    return "\n".join(sections)


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
