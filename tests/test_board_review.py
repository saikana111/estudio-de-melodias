import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import mido
from musical import Note, track_from_notes
from revision_musical import guardar_midi


class BoardReview(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name)
        names = "grabar convertir correccion reproducir esp32 proyectos sugerencia asistente".split()
        with patch.dict(sys.modules, {n: MagicMock() for n in names}):
            spec = importlib.util.spec_from_file_location("board_flow", Path(__file__).resolve().parents[1]/"src/main.py")
            self.app = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.app)
        a = self.app
        a.nombre = "obra"
        a.proyectos.CARPETA = tmp.name
        a.proyectos.guardar.side_effect = lambda midi, name: guardar_midi(midi, self.folder/(name+".mid"))
        a.proyecto = mido.MidiFile()
        self.full = mido.MidiFile()
        for ch, program, name in [(0, 27, "Teclado"), (2, 27, "Sugerencia IA - Armonia"),
                                  (3, 34, "Sugerencia IA - Bajo"), (9, 0, "Sugerencia IA - Bateria")]:
            track = track_from_notes([Note(100, 500, 60, 80)], program, ch, name)
            self.full.tracks.append(track)
        a.proyecto.tracks.append(self.full.tracks[0])

    def names(self):
        return [t.name for t in mido.MidiFile(self.folder/"obra.mid").tracks]

    def chat(self, message, action, names=(), delta=0):
        self.app.gem.transcribir.return_value = message
        self.app.gem.decision_voz.return_value = dict(accion=action, pistas=list(names),
            cambio_velocity=delta, formato="ensamble", respuesta="¿Te referís al bajo?")
        self.app.procesar_chat()
        self.assertEqual(self.app.gem.decision_voz.call_args.args[0]["mensaje"], message)
        self.app.esp32.esperar_si_no.assert_not_called()

    def test_accept_revise_skip_and_remove(self):
        a = self.app
        a.revisar_borrador(self.full, "ensamble")
        self.assertEqual(len(a.proyecto.tracks), 1)
        self.chat("Esa viola queda bárbara, dejémosla", "guardar")
        self.assertEqual(self.names(), ["Teclado", "Sugerencia IA - Armonia"])
        self.assertEqual(len(mido.MidiFile(self.folder/"borradores"/"obra.mid").tracks), 4)
        self.chat("El grave me tapa lo que canté", "dinamica", ["Sugerencia IA - Bajo"], -12)
        self.assertEqual(len(a.proyecto.tracks), 2)
        self.chat("Ahora sí quedó como quería", "guardar")
        self.assertEqual(next(m.velocity for m in a.proyecto.tracks[-1] if m.type=="note_on"),68)
        self.chat("Mejor sin esos golpes", "descartar")
        self.chat("Sacaría las cuerdas eléctricas", "quitar", ["Sugerencia IA - Armonia"])
        self.chat("Dejala así", "guardar")
        self.assertEqual(self.names(), ["Teclado", "Sugerencia IA - Bajo"])
        self.assertEqual(a.proyecto.tracks[0], self.full.tracks[0])

    def test_edit_full_song_and_clarify_without_saving(self):
        a = self.app
        self.full.tracks.append(mido.MidiTrack([mido.MetaMessage("track_name", name="Sugerencia IA - Secciones"),
                                               mido.MetaMessage("marker", text="Coda")]))
        a.revisar_borrador(self.full, "cancion")
        self.chat("Mmm, ese del fondo...", "aclarar")
        self.assertEqual(len(a.proyecto.tracks), 1)
        self.chat("El bajo. Quedaría mejor sin él", "quitar", ["Sugerencia IA - Bajo"])
        self.chat("Esto era lo que tenía en mente", "guardar")
        self.assertNotIn("Sugerencia IA - Bajo", self.names())
        self.assertIn("Sugerencia IA - Secciones", self.names())
        self.assertIn("Sugerencia IA - Bateria", self.names())
