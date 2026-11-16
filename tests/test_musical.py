import copy
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import mido
from musical import Brief, Note, accompany, read_notes, track_from_notes, repeated_motif
from score_notes import score_track_notes


def fixture(pitches=(72, 76, 79, 76, 77, 81, 84, 81, 79, 83, 86, 83, 72)):
    midi = mido.MidiFile(ticks_per_beat=480)
    midi.tracks.append(mido.MidiTrack([
        mido.MetaMessage("set_tempo", tempo=600000),
        mido.MetaMessage("time_signature", numerator=4, denominator=4),
        mido.MetaMessage("set_tempo", tempo=750000, time=3840)]))
    notes = [Note(i*480, (i+1)*480, pitch) for i, pitch in enumerate(pitches)]
    midi.tracks.append(track_from_notes(notes, 73, 0, "Original melody"))
    return midi


class MusicalTests(unittest.TestCase):
    def test_cli_accepts_type_zero_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory)/"source.mid"
            output = Path(directory)/"result.mid"
            source = mido.MidiFile(type=0)
            source.tracks.append(track_from_notes([Note(240, 960, 64)], 0, 0))
            source.save(original)
            before = original.read_bytes()
            command = [sys.executable, str(Path(__file__).resolve().parents[1]/"src"/"compose.py"), str(original), str(output)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(mido.MidiFile(output).type, 1)
            self.assertEqual(original.read_bytes(), before)
            output_before = output.read_bytes()
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(output.read_bytes(), output_before)

    def test_cli_refuses_occupied_channel(self):
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory)/"source.mid"
            output = Path(directory)/"result.mid"
            source = fixture()
            source.tracks.append(track_from_notes([Note(0, 480, 48)], 0, 2))
            source.save(original)
            result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1]/"src"/"compose.py"),
                                     str(original), str(output), "--single"], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())

    def test_score_track_extraction_uses_logical_track_and_resolution(self):
        note = SimpleNamespace(onset_ticks=12, duration_ticks=24, pitch=67, velocity=80)
        bar = SimpleNamespace(notes=[note], beat_length=3)
        score = SimpleNamespace(resolution=24, tracks=[SimpleNamespace(bars=[]),
                                                       SimpleNamespace(bars=[bar, bar])])
        self.assertEqual(score_track_notes(score, 1, 480), [(240, 720, 67, 80), (1680, 2160, 67, 80)])

    def test_source_unchanged_and_repeatable(self):
        midi = fixture()
        before = copy.deepcopy(midi.tracks)
        a, report = accompany(midi, Brief(tonic=0))
        b, _ = accompany(midi, Brief(tonic=0))
        self.assertEqual(a, b)
        self.assertEqual(midi.tracks, before)
        self.assertEqual([h["roman"] for h in report["harmony"]], ["I", "IV", "V", "I"])
        midi.tracks.append(a)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.mid"
            midi.save(path)
            loaded = mido.MidiFile(path)
            self.assertEqual([[m for m in t if m.type != "end_of_track"] for t in loaded.tracks[:2]], before)
            self.assertTrue(read_notes(loaded, 2))

    def test_invalid_briefs_rejected(self):
        for data in ({"voces": True}, {"voces": 9}, {"instrumento": 128},
                     {"registro": "low"}, {"beat_ticks": 0}, {"tonic": -1},
                     {"denominator": 3}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                Brief(**data)

    def test_empty_and_hanging_notes_rejected(self):
        with self.assertRaises(ValueError):
            accompany(mido.MidiFile())
        midi = mido.MidiFile()
        midi.tracks.append(mido.MidiTrack([mido.Message("note_on", note=60)]))
        with self.assertRaises(ValueError):
            read_notes(midi)

    def test_fifo_and_channel_identity_and_velocity_zero(self):
        midi = mido.MidiFile()
        midi.tracks.append(mido.MidiTrack([
            mido.Message("note_on", channel=0, note=60, velocity=50),
            mido.Message("note_on", channel=1, note=60, velocity=70),
            mido.Message("note_on", channel=0, note=60, velocity=60, time=10),
            mido.Message("note_on", channel=0, note=60, velocity=0, time=10),
            mido.Message("note_off", channel=0, note=60, time=10),
            mido.Message("note_off", channel=1, note=60, time=10)]))
        self.assertEqual([(n.start, n.end) for n in read_notes(midi, 0)], [(0, 20), (10, 30)])
        self.assertEqual(read_notes(midi, 1)[0].end, 40)

    def test_polyphony_range_and_harmonic_membership(self):
        for voices in range(1, 5):
            for spacing in ("cerrada", "abierta"):
                track, report = accompany(fixture(), Brief(tonic=0, voces=voices, disposicion=spacing))
                out = mido.MidiFile()
                out.tracks.append(track)
                notes = read_notes(out)
                self.assertTrue(all(48 <= n.pitch <= 71 and n.start < n.end for n in notes))
                for n in notes:
                    chord = next(h for h in report["harmony"] if h["start_tick"] <= n.start < h["end_tick"])
                    self.assertIn(n.pitch % 12, chord["pitch_classes"])
                self.assertLessEqual(max(sum(n.start <= t < n.end for n in notes)
                                         for t in {n.start for n in notes}), voices)

    def test_chromatic_melody_preserved(self):
        midi = fixture((72, 73, 74, 75, 76, 77, 78, 79))
        before = read_notes(midi, 0)
        accompany(midi, Brief(tonic=0))
        self.assertEqual(read_notes(midi, 0), before)

    def test_other_channels_do_not_contaminate_harmony(self):
        midi = fixture()
        _, expected = accompany(midi, Brief(tonic=0))
        midi.tracks.append(track_from_notes([Note(0, 6240, 66)], 0, 3))
        _, actual = accompany(midi, Brief(tonic=0))
        self.assertEqual(actual["harmony"], expected["harmony"])

    def test_minor_and_meters(self):
        for numerator, denominator in ((3, 4), (4, 4), (6, 8)):
            source = fixture((69, 72, 76, 69, 71, 74, 68, 69))
            source.tracks[0][1] = mido.MetaMessage("time_signature", numerator=numerator, denominator=denominator)
            track, report = accompany(source,
                                       Brief(tonic=9, mode="minor", numerator=numerator,
                                             denominator=denominator, downbeat=240))
            self.assertEqual(report["harmony"][0]["end_tick"], 240)
            self.assertEqual(report["harmony"][-1]["end_tick"], 3840)
            self.assertTrue(all(m.time >= 0 for m in track))

    def test_meter_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            accompany(fixture(), Brief(numerator=3))

    def test_free_harmony_follows_source_onsets_and_preserves_notes(self):
        midi = fixture()
        before = read_notes(midi, 0)
        _, report = accompany(midi, Brief(tonic=0, ritmo_armonico="libre", patron="sostenido", costo_cambio=1))
        self.assertTrue(all(h["start_tick"] in {n.start for n in before} for h in report["harmony"]))
        self.assertEqual(read_notes(midi, 0), before)
        self.assertGreater(len(report["harmony"]), 1)

    def test_repeated_phrase_keeps_harmony_under_rubato(self):
        pitches = [59, 64, 66, 64, 62, 61] * 2
        starts = [0, 600, 840, 1080, 1680, 1920, 2640, 3100, 3320, 3600, 4200, 4400]
        notes = [Note(t, starts[i+1] if i+1 < len(starts) else 5000, p)
                 for i, (t, p) in enumerate(zip(starts, pitches))]
        midi = mido.MidiFile()
        midi.tracks.append(track_from_notes(notes, 0, 0))
        _, report = accompany(midi, Brief(tonic=4, mode="dorian", ritmo_armonico="libre", costo_cambio=1))
        self.assertEqual(report["repeated_motif"]["starts"], [0, 6])
        first = [(starts.index(h["start_tick"]), h["roman"]) for h in report["harmony"] if h["start_tick"] < 2640]
        second = [(starts.index(h["start_tick"])-6, h["roman"]) for h in report["harmony"] if h["start_tick"] >= 2640]
        self.assertEqual(first, second)

    def test_explicit_modal_harmony_and_leading_silence(self):
        midi = mido.MidiFile()
        midi.tracks.append(track_from_notes([Note(480, 960, 64), Note(960, 1440, 61)], 0, 0))
        track, report = accompany(midi, Brief(tonic=4, mode="dorian", patron="sostenido",
                                             cambios=((480, "i"), (960, "IV"))))
        out = mido.MidiFile()
        out.tracks.append(track)
        self.assertEqual(min(n.start for n in read_notes(out)), 480)
        self.assertEqual(report["harmony"][1]["pitch_classes"], (9, 1, 4))
        with self.assertRaises(ValueError):
            accompany(midi, Brief(tonic=4, mode="dorian", cambios=((480, "nonsense"),)))
        with self.assertRaises(ValueError):
            Brief(cambios=((480, "i"), (240, "IV")))


if __name__ == "__main__":
    unittest.main()
