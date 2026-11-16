"""Acceptance/rejection integration with mocked hardware, speech and playback."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from test_song import seed, BRIEF
from project_arrangement import candidate
from delivery import serialize_midi


class SuggestionUiTests(unittest.TestCase):
    def load_ui(self, directory, accepted):
        mocks = {name: MagicMock() for name in ("music21", "acompanante", "esp32", "gem", "proyectos", "reproducir")}
        mocks["proyectos"].CARPETA = directory
        mocks["esp32"].esperar_si_no.return_value = accepted
        with patch.dict(sys.modules, mocks):
            spec = importlib.util.spec_from_file_location("suggestion_under_test", Path(__file__).resolve().parents[1]/"src/sugerencia.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        return module, mocks

    def test_reject_does_not_change_or_save_project(self):
        with tempfile.TemporaryDirectory() as directory:
            ui, mocks = self.load_ui(directory, False)
            project = seed()
            before = serialize_midi(project)
            preview, report = candidate(project, BRIEF)
            self.assertFalse(ui.proponer_ensamble(preview, report, project, "test"))
            self.assertEqual(serialize_midi(project), before)
            mocks["proyectos"].guardar.assert_not_called()
            self.assertFalse(list(Path(directory).iterdir()))

    def test_accept_commits_whole_group_and_report(self):
        with tempfile.TemporaryDirectory() as directory:
            ui, mocks = self.load_ui(directory, True)
            project = seed()
            preview, report = candidate(project, BRIEF)
            self.assertTrue(ui.proponer_ensamble(preview, report, project, "test"))
            self.assertEqual(project.tracks, preview.tracks)
            mocks["proyectos"].guardar.assert_called_once_with(project, "test")
            self.assertTrue((Path(directory)/"test.arrangement.json").exists())


if __name__ == "__main__":
    unittest.main()
