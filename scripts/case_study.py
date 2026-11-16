"""Reproduce accompaniment alternatives for the supplied 13-note melody.

The reviewed landmarks are hypotheses for THIS performance, not an automatic
beat detector. Source notes and timing remain untouched in each MIDI.
"""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import mido
from musical import Brief, accompany, read_notes, summarize
from render_preview import render


def main():
    path = ROOT / "test" / "0_melodia_original.mid"
    source = mido.MidiFile(path)
    out = ROOT / "artifacts" / "original-melody"
    out.mkdir(parents=True, exist_ok=True)
    summary = summarize(source, 0)
    (out / "source-analysis.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    render(source, out / "00-original.wav")
    for name, mode, tonic, changes in (
        ("01-e-dorian", "dorian", 4, ((1907, "i"), (5843, "IV"), (7852, "v"),
                                      (8531, "i"), (12068, "IV"))),
        ("02-e-mixolydian", "mixolydian", 4, ((1907, "I"), (5843, "IV"), (7852, "v"),
                                              (8531, "I"), (12068, "IV"))),
        ("03-b-minor", "minor", 11, ((1907, "i"), (3814, "iv"), (5843, "VII"),
                                    (7852, "i"), (10137, "iv"), (12068, "VII"))),
    ):
        brief = Brief(tonic=tonic, mode=mode, registro="grave", disposicion="abierta",
                      patron="sostenido", cambios=changes)
        result = copy.deepcopy(source)
        track, report = accompany(result, brief)
        result.tracks.append(track)
        result.save(out / f"{name}.mid")
        reloaded = mido.MidiFile(out / f"{name}.mid")
        assert reloaded.tracks[:len(source.tracks)] == source.tracks
        assert read_notes(reloaded, 0) == read_notes(source, 0)
        report["source_preservation_verified_after_save"] = True
        report["landmarks"] = "Hand-reviewed hypotheses for this recording; not inferred tempo or definitive harmony."
        (out / f"{name}.analysis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        (out / f"{name}.brief.json").write_text(json.dumps(report["brief"], indent=2), encoding="utf-8")
        render(reloaded, out / f"{name}.wav")
    print(f"Three alternatives, original preview and decision reports: {out}")
    automatic_brief = Brief(tonic=4, mode="dorian", registro="grave", disposicion="abierta",
                            patron="sostenido", ritmo_armonico="libre", costo_cambio=1)
    result = copy.deepcopy(source)
    track, report = accompany(result, automatic_brief)
    result.tracks.append(track)
    result.save(out / "05-automatic-free-time.mid")
    assert read_notes(mido.MidiFile(out / "05-automatic-free-time.mid"), 0) == read_notes(source, 0)
    report["landmarks"] = "Automatically chosen chord boundaries; E Dorian is an explicit hypothesis."
    (out / "05-automatic-free-time.analysis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    render(result, out / "05-automatic-free-time.wav")
    print("Automatic free-time harmony:", [(h["start_tick"], h["roman"]) for h in report["harmony"]])


if __name__ == "__main__":
    main()
