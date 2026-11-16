"""Reproduce MIDI corpus checks and small listening examples without cloud/hardware."""
import copy
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import mido
from musical import Brief, Note, accompany, read_notes, summarize, track_from_notes


def main():
    out = ROOT / "artifacts"
    out.mkdir(exist_ok=True)
    results = []
    paths = sorted(p for folder in ("midi", "proyectos", "pruebas_sonido")
                   for p in (ROOT / folder).glob("*.mid"))
    paths += sorted(ROOT.glob("resultado_limpio*.mid"))
    for path in paths:
        entry = {"file": path.relative_to(ROOT).as_posix()}
        try:
            source = mido.MidiFile(path)
            notes = read_notes(source, 0)
            snapshot = copy.deepcopy(source.tracks)
            start = time.perf_counter()
            track, report = accompany(source, Brief(), 0, 2)
            entry.update({"status": "ok", "seconds": round(time.perf_counter()-start, 4),
                          "notes": len(notes), "source_unchanged": snapshot == source.tracks,
                          "key_candidates": report["key_candidates"],
                          "harmony": [h["roman"] for h in report["harmony"]],
                          "overlapping_note_pairs": sum(a.end > b.start for a, b in zip(notes, notes[1:]))})
            if path.name == "grabacion_melodia_basic_pitch23.mid":
                source.tracks.append(track)
                source.save(out / "recording23-accompanied.mid")
                (out / "recording23.analysis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        except Exception as exc:
            entry.update({"status": "error", "error": str(exc)})
        results.append(entry)
    # Deliberately simple fixture with known C-F-G-C harmony, not a quality benchmark.
    melody = [72, 76, 79, 76, 77, 81, 84, 81, 79, 83, 86, 83, 72, 76, 79, 72]
    source = mido.MidiFile(ticks_per_beat=480)
    source.tracks.append(mido.MidiTrack([mido.MetaMessage("set_tempo", tempo=625000),
                                       mido.MetaMessage("time_signature", numerator=4, denominator=4)]))
    source.tracks.append(track_from_notes([Note(i*480, i*480+440, p) for i, p in enumerate(melody)], 73, 0, "Melody"))
    source.save(out / "demo-source.mid")
    for name, brief in (("chords", Brief(tonic=0)),
                        ("arpeggio", Brief(tonic=0, patron="arpegio", notas="cortas", espacio="poco")),
                        ("bass", Brief(tonic=0, voces=1, registro="grave", instrumento=33))):
        target = copy.deepcopy(source)
        track, report = accompany(target, brief)
        target.tracks.append(track)
        target.save(out / f"demo-{name}.mid")
        (out / f"demo-{name}.analysis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary = {"files": len(results), "passed": sum(r["status"] == "ok" for r in results),
               "meaning": "Structural checks only, not listening quality or transcription accuracy.",
               "results": results}
    (out / "corpus-evaluation.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}))


if __name__ == "__main__":
    main()
