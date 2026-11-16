import copy
import io
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
import mido
from ensemble import Ensemble, arrange
from musical import Brief, Note, read_notes, track_from_notes


def source():
    midi = mido.MidiFile()
    midi.tracks.append(mido.MidiTrack([mido.MetaMessage("set_tempo", tempo=650000)]))
    midi.tracks.append(track_from_notes([Note(480, 960, 64), Note(1440, 1920, 67),
                                        Note(2400, 2880, 71), Note(3000, 3600, 64)], 0, 0))
    return midi


def to_bytes(midi):
    data = io.BytesIO()
    midi.save(file=data)
    return data.getvalue()


class EnsembleTests(unittest.TestCase):
    def test_repeatable_preserves_source_and_metadata(self):
        original = source()
        before = to_bytes(original)
        result, report = arrange(original, Brief(tonic=4, mode="minor", patron="sostenido"))
        repeated, _ = arrange(original, Brief(tonic=4, mode="minor", patron="sostenido"))
        self.assertEqual(to_bytes(result), to_bytes(repeated))
        self.assertEqual(to_bytes(original), before)
        loaded = mido.MidiFile(file=io.BytesIO(to_bytes(result)))
        self.assertEqual(read_notes(loaded, 0), read_notes(original, 0))
        self.assertEqual(result.tracks[:len(original.tracks)], original.tracks)
        self.assertEqual(len(report["parts"]), 3)

    def test_roles_share_harmony_and_responses_only_in_rests(self):
        result, report = arrange(source(), Brief(tonic=4, mode="minor", patron="sostenido"))
        parts = {p["role"]: p["channel"] for p in report["parts"]}
        melody = read_notes(result, 0)
        for answer in read_notes(result, parts["response"]):
            self.assertFalse(any(answer.start < n.end and answer.end > n.start for n in melody))
        bass = read_notes(result, parts["bass"])
        for note, chord in zip(bass, report["harmony"]):
            self.assertEqual(note.pitch % 12, chord["pitch_classes"][0])
            self.assertLessEqual(note.pitch+5, min(chord["voicing"]))

    def test_existing_channels_untouched(self):
        original = source()
        original.tracks.append(track_from_notes([Note(0, 480, 48)], 0, 1))
        result, report = arrange(original)
        self.assertNotIn(1, [p["channel"] for p in report["parts"]])
        self.assertEqual(result.tracks[:len(original.tracks)], original.tracks)

    def test_exhausted_channels_rejected(self):
        original = source()
        for channel in range(1, 16):
            original.tracks.append(mido.MidiTrack([mido.Message("program_change", channel=channel)]))
        with self.assertRaises(ValueError):
            arrange(original)

    def test_responses_can_be_disabled(self):
        _, report = arrange(source(), ensemble=Ensemble(responses=False))
        self.assertEqual([p["role"] for p in report["parts"]], ["harmony", "bass"])


if __name__ == "__main__":
    unittest.main()
