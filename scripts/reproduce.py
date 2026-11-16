"""Verify determinism against the delivered single-track MIDI and make an ensemble."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import mido
from musical import Brief, accompany
from ensemble import arrange
from render_preview import render


def midi_bytes(midi):
    output = io.BytesIO()
    midi.save(file=output)
    return output.getvalue()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def mido_source_revision():
    directory = Path(mido.__file__).resolve().parents[1]
    if not (directory/".git").exists():
        return None
    try:
        return subprocess.check_output(["git", "-c", f"safe.directory={directory.as_posix()}",
                                        "-C", str(directory), "rev-parse", "HEAD"], text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main():
    source_path = ROOT / "test/0_melodia_original.mid"
    brief_path = ROOT / "examples/automatic-dorian.json"
    source = mido.MidiFile(source_path)
    brief = Brief(**json.loads(brief_path.read_text(encoding="utf-8")))
    rendered = []
    for _ in range(2):
        result = deepcopy(source)
        track, _ = accompany(result, brief)
        result.tracks.append(track)
        rendered.append(midi_bytes(result))
    previous = (ROOT / "artifacts/original-melody/05-automatic-free-time.mid").read_bytes()
    assert rendered[0] == rendered[1] == previous, "Single-track reproduction differs"
    full, report = arrange(source, brief)
    repeated, _ = arrange(source, brief)
    assert midi_bytes(full) == midi_bytes(repeated), "Ensemble generation is not deterministic"
    out = ROOT / "artifacts/original-melody"
    full.save(out / "06-ensemble.mid")
    (out / "06-ensemble.analysis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    render(full, out / "06-ensemble.wav")
    manifest = {
        "python": platform.python_version(), "mido": mido.version.__version__,
        "mido_source_revision": mido_source_revision(),
        "source_sha256": digest(source_path.read_bytes()),
        "brief_sha256": digest(brief_path.read_bytes()),
        "code_sha256": {name: digest((ROOT/name).read_bytes()) for name in
                        ("src/musical.py", "src/ensemble.py", "scripts/render_preview.py")},
        "single_track_sha256": digest(rendered[0]), "ensemble_sha256": digest(midi_bytes(full)),
        "single_track_matches_delivered_bytes": True, "ensemble_repeat_matches_bytes": True,
        "scope": "Verified in this environment; cross-version/platform byte equality not promised.",
        "brief": report["brief"],
    }
    (out / "reproducibility.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
