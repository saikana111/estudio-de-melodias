"""Offline contract checks; no claims about live Gemini interpretation quality."""
import ast
from contextlib import nullcontext
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import mido
from emotion_skill import EmotionContext, SKILL_PATH, load_emotion_skill
from ensemble import Ensemble, arrange
from musical import Brief, Note, read_notes, track_from_notes

ROOT = Path(__file__).resolve().parents[1]


class EmotionSkillTests(unittest.TestCase):
    def test_all_profiles_match_app_schema_and_generate_without_changing_melody(self):
        pack = json.loads((SKILL_PATH.parent / 'knowledge/02-perfiles.json').read_text(encoding='utf-8'))
        tree = ast.parse((ROOT / 'src/gem.py').read_text(encoding='utf-8'))
        schema = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Arreglo')
        fields = {n.target.id for n in schema.body if isinstance(n, ast.AnnAssign)}
        self.assertEqual(set(pack['base']), fields)
        ids = [p['id'] for p in pack['perfiles']]
        self.assertEqual(len(ids), len(set(ids)))
        loaded = load_emotion_skill()
        for profile in pack['perfiles']:
            with self.subTest(profile=profile['id']):
                self.assertTrue(set(profile['ajustes']) <= fields)
                self.assertIn(profile['criterio'], loaded)
                settings = pack['base'] | profile['ajustes']
                for tonic, mode, pitches in [(0, 'major', [60, 64, 67, 65, 62, 60]),
                                              (4, 'minor', [59, 64, 66, 64, 62, 61])]:
                    midi = mido.MidiFile(ticks_per_beat=480)
                    midi.tracks.append(track_from_notes([
                        Note(i*600, i*600+420, pitch, 90) for i, pitch in enumerate(pitches)], 0, 0))
                    before = read_notes(midi, 0)
                    output, report = arrange(midi, Brief(**settings, tonic=tonic, mode=mode,
                                                        ritmo_armonico='libre'),
                                             ensemble=Ensemble(harmony_program=settings['instrumento']))
                    self.assertEqual(read_notes(output, 0), before)
                    self.assertEqual(read_notes(midi, 0), before)
                    harmony = read_notes(output, report['parts'][0]['channel'])
                    self.assertTrue(harmony)
                    self.assertTrue(all(n.end > n.start and 0 < n.velocity <= 127 for n in harmony))

    def test_new_local_knowledge_is_inlined_without_tools_or_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill = root / 'SKILL.md'
            skill.write_text('---\nname: test\ndescription: test\n---\nUse local knowledge.', encoding='utf-8')
            knowledge = root / 'knowledge'
            knowledge.mkdir()
            (knowledge / 'rule.md').write_text('Keep dynamics fixed when changing tension.', encoding='utf-8')
            first = load_emotion_skill(skill)
            (knowledge / 'new.json').write_text('{"new_rule": "Respect the chosen instrument"}', encoding='utf-8')
            second = load_emotion_skill(skill)
            self.assertIn('Keep dynamics fixed', first)
            self.assertIn('Respect the chosen instrument', second)
            (knowledge / 'new.json').write_text('{broken', encoding='utf-8')
            with self.assertRaises(json.JSONDecodeError):
                load_emotion_skill(skill)

    def test_context_is_bounded_and_keeps_latest_correction(self):
        context = EmotionContext(max_chars=1000)
        for i in range(15):
            context.record(str(i) + "x" * 200, "y" * 200)
        context.record("Más tensión, sin subir volumen", "Conservo la intensidad")
        self.assertLessEqual(len(context.as_json()), 1000)
        self.assertEqual(json.loads(context.as_json())[-1]["usuario"],
                         "Más tensión, sin subir volumen")
        context.clear()
        self.assertEqual(context.as_json(), "[]")

    def gem_functions(self):
        # Execute the actual boundary functions without importing microphone/TTS SDKs.
        tree = ast.parse((ROOT / "src/gem.py").read_text(encoding="utf-8"))
        names = {"hablar_con_mi_gem", "pedir_arreglo_json", "reiniciar_contexto_musical"}
        functions = ast.Module(body=[n for n in tree.body
                                    if isinstance(n, ast.FunctionDef) and n.name in names],
                               type_ignores=[])
        calls = []
        config = {"instrumento": 0, "voces": 3, "notas": "largas",
                  "espacio": "medio", "registro": "medio", "intensidad": 56,
                  "patron": "sostenido", "actividad": 1, "articulacion": "legato"}
        def generate(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(text=json.dumps(config))
        def create(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(send_message=lambda message: SimpleNamespace(
                text="Probemos piano suave, manteniendo la esperanza."))
        def validate(text):
            data = json.loads(text)
            Brief(**data)  # Confirm the proposed fixture is executable by our engine.
            return SimpleNamespace(model_dump=lambda: data)
        skill = load_emotion_skill()
        ns = dict(client=SimpleNamespace(models=SimpleNamespace(generate_content=generate),
                                        chats=SimpleNamespace(create=create)),
                  types=SimpleNamespace(GenerateContentConfig=lambda **kw: kw),
                  MODELO="test-model", GUIA_EMOCIONAL=skill,
                  instrucciones_del_sistema="Conversación\n" + skill,
                  contexto_emocional=EmotionContext(), ultimo_arreglo=None,
                  Arreglo=SimpleNamespace(model_validate_json=validate),
                  cronometro=lambda _: nullcontext(), json=json)
        exec(compile(functions, str(ROOT / "src/gem.py"), "exec"), ns)
        ns["reiniciar_contexto_musical"]()
        return ns, calls

    def test_chat_and_planner_receive_skill_and_emotional_context(self):
        ns, calls = self.gem_functions()
        ns["hablar_con_mi_gem"]("Triste pero con esperanza, no cambies mi melodía")
        result = ns["pedir_arreglo_json"]("Sí, piano", "Nota 64, duración 480", "E minor")
        self.assertIn(ns["GUIA_EMOCIONAL"], calls[0]["config"]["system_instruction"])
        planner = calls[-1]
        self.assertEqual(planner["config"]["system_instruction"], ns["GUIA_EMOCIONAL"])
        self.assertIn("Triste pero con esperanza", planner["contents"])
        self.assertEqual(planner["config"]["response_schema"], ns["Arreglo"])
        self.assertEqual(ns["ultimo_arreglo"], result)
        ns["pedir_arreglo_json"]("Más tensión sin más volumen", "Nota 64", "E minor")
        self.assertIn('"intensidad": 56', calls[-1]["contents"])

    def test_project_reset_removes_dialogue_and_previous_arrangement(self):
        ns, _ = self.gem_functions()
        ns["hablar_con_mi_gem"]("Enojado y fuerte")
        ns["ultimo_arreglo"] = {"intensidad": 92}
        old_chat = ns["mi_chat_gemini"]
        ns["reiniciar_contexto_musical"]()
        self.assertIsNot(old_chat, ns["mi_chat_gemini"])
        self.assertIsNone(ns["ultimo_arreglo"])
        self.assertEqual(ns["contexto_emocional"].as_json(), "[]")


if __name__ == "__main__":
    unittest.main()
