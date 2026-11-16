import io
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
import mido
from delivery import save_bundle, serialize_midi
from ensemble import Ensemble, arrange
from musical import Brief, Note, read_notes, track_from_notes
from project_arrangement import candidate
from song import Song, develop


def seed():
    result = mido.MidiFile()
    pitches = [59, 64, 66, 64, 62, 61, 59, 59, 64, 66, 64, 62, 61]
    starts = [1907, 3814, 4183, 4660, 5843, 6233, 7852, 8531, 10137, 10527, 10961, 12068, 12502]
    ends = [3177, 4161, 4628, 5856, 6233, 7169, 8531, 9367, 10584, 10961, 12089, 12502, 13796]
    result.tracks.append(track_from_notes([Note(a, b, p, 90) for a, b, p in zip(starts, ends, pitches)], 0, 0, "Melodia"))
    return result


BRIEF = Brief(tonic=4, mode="dorian", registro="grave", disposicion="abierta",
              patron="sostenido", ritmo_armonico="libre", costo_cambio=1)


class SongTests(unittest.TestCase):
    def test_source_preserved_sections_developed_and_cadence_resolves(self):
        source = seed()
        before = serialize_midi(source)
        result, report = develop(source, BRIEF)
        self.assertEqual(before, serialize_midi(source))
        self.assertEqual(result.tracks[:len(source.tracks)], source.tracks)
        loaded = mido.MidiFile(file=io.BytesIO(serialize_midi(result)))
        melody = read_notes(loaded, 0)
        original = read_notes(source, 0)
        self.assertEqual([n for n in melody if n.start < 13796], original)
        self.assertEqual([s["kind"] for s in report["sections"]], ["theme", "variation", "contrast", "return", "coda"])
        self.assertGreater(report["sections"][1]["melody_note_count"], len(original))
        self.assertGreater(report["duration_seconds"], source.length*3)
        self.assertEqual(melody[-1].pitch % 12, 4)
        self.assertEqual(report["sections"][-1]["harmony"][-1]["roman"], "i")
        self.assertTrue(all(n.start < n.end for n in read_notes(loaded)))
        markers = [m for t in loaded.tracks for m in t if m.type == "marker"]
        self.assertEqual(len(markers), 5)

    def test_theme_accompaniment_matches_accepted_engine(self):
        source = seed()
        original, original_report = arrange(source, BRIEF)
        song, report = develop(source, BRIEF)
        for part in original_report["parts"]:
            channel = next(p["channel"] for p in report["parts"] if p["role"] == part["role"])
            self.assertEqual([n for n in read_notes(song, channel) if n.start < 13796],
                             read_notes(original, part["channel"]))

    def test_song_is_deterministic_and_return_preserves_relative_timing(self):
        a, report = develop(seed(), BRIEF)
        b, _ = develop(seed(), BRIEF)
        self.assertEqual(serialize_midi(a), serialize_midi(b))
        section = next(s for s in report["sections"] if s["kind"] == "return")
        notes = [n for n in read_notes(a, 0) if section["start_tick"] <= n.start < section["end_tick"]]
        original = read_notes(seed(), 0)
        self.assertEqual([(n.start-section["start_tick"], n.end-n.start, n.pitch) for n in notes],
                         [(n.start-original[0].start, n.end-n.start, n.pitch) for n in original])

    def test_tempo_changes_rejected_but_accompaniment_accepts(self):
        source = seed()
        source.tracks.append(mido.MidiTrack([mido.MetaMessage("set_tempo", tempo=700000, time=1000)]))
        with self.assertRaises(ValueError):
            develop(source, BRIEF)
        arrange(source, BRIEF)

    def test_short_form_and_reserved_channels(self):
        result, report = develop(seed(), BRIEF, ensemble=Ensemble(reserved_channels=(1, 2)),
                                 song=Song(sections=("theme", "coda")))
        self.assertEqual(len(report["sections"]), 2)
        self.assertTrue(all(p["channel"] not in (1, 2, 9) for p in report["parts"]))

    def test_invalid_song_config(self):
        for data in ({"sections": ["theme", "unknown", "coda"]}, {"contrast_rate": float("nan")},
                     {"contrast_steps": True}, {"sections": ["variation", "coda"]}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                Song(**data)

    def test_bundle_preserves_existing_files_and_hashes(self):
        import hashlib
        import json
        source = seed()
        result, report = develop(source, BRIEF, song=Song(sections=("theme", "coda")))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/"song.mid"
            sidecar = save_bundle(result, report, output, serialize_midi(source), "song")
            details = json.loads(sidecar.read_text(encoding="utf-8"))
            self.assertEqual(details["provenance"]["output_sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
            self.assertEqual(details["schema_version"], 1)
            original_bytes = output.read_bytes()
            with self.assertRaises(FileExistsError):
                save_bundle(source, report, output, b"", "song")
            self.assertEqual(output.read_bytes(), original_bytes)

    def test_app_adapter_preview_is_nonmutating_and_replaces_group(self):
        source = seed()
        before = serialize_midi(source)
        preview, report = candidate(source, BRIEF)
        self.assertEqual(before, serialize_midi(source))
        self.assertTrue(all(p["channel"] not in (0, 1, 9) for p in report["parts"]))
        replacement, _ = candidate(preview, BRIEF)
        self.assertEqual(len(replacement.tracks), len(preview.tracks))
        self.assertEqual(read_notes(replacement, 0), read_notes(source, 0))


if __name__ == "__main__":
    unittest.main()
