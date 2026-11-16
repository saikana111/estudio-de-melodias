"""Build versioned MIDI-first deliverables; refuse to overwrite existing results."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
import mido
from delivery import save_bundle
from ensemble import Ensemble, arrange
from musical import Brief
from song import Song, develop
from render_preview import render


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT/"test/0_melodia_original.mid")
    parser.add_argument("--output-dir", type=Path, default=ROOT/"artifacts/v0.2.0")
    parser.add_argument("--preview", action="store_true", help="Also render simple WAV listening previews")
    args = parser.parse_args()
    for name in ("accompaniment", "song"):
        for suffix in (".mid", ".analysis.json", ".wav"):
            if (args.output_dir/(name+suffix)).exists():
                parser.error("Output directory already contains results; choose a new --output-dir")
    load = lambda name: json.loads((ROOT/"examples"/name).read_text(encoding="utf-8"))
    brief, ensemble, song = Brief(**load("automatic-dorian.json")), Ensemble(**load("chamber.json")), Song(**load("song.json"))
    source = mido.MidiFile(args.source)
    outputs = [("accompaniment", *arrange(source, brief, ensemble=ensemble)),
               ("song", *develop(source, brief, ensemble=ensemble, song=song))]
    for name, result, report in outputs:
        output = args.output_dir/(name+".mid")
        save_bundle(result, report, output, args.source.read_bytes(), "ensemble" if name == "accompaniment" else "song")
        if args.preview:
            render(result, output.with_suffix(".wav"))
        # Verify the deliverable, not only the in-memory objects.
        loaded = mido.MidiFile(output)
        assert loaded.tracks[:len(source.tracks)] == source.tracks
        print(f"{output}: {loaded.length:.2f} seconds, {len(loaded.tracks)} tracks")


if __name__ == "__main__":
    main()
