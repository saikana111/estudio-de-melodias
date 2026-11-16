"""MIDI-first output bundles with provenance and non-overwriting writes."""
import hashlib
import io
import json
from pathlib import Path
import platform

import mido

ENGINE_VERSION = "0.2.0"


def serialize_midi(midi):
    output = io.BytesIO()
    midi.save(file=output)
    return output.getvalue()


def save_bundle(midi, report, output, source_bytes, mode):
    """Write MIDI + JSON. Validate/serialize first; roll back only our new files."""
    output = Path(output)
    if output.suffix.lower() not in (".mid", ".midi"):
        raise ValueError("Output must have a .mid or .midi extension")
    sidecar = output.with_suffix(".analysis.json")
    if output.exists() or sidecar.exists():
        raise FileExistsError("Choose a new output path; existing MIDI/report files are never overwritten")
    midi_data = serialize_midi(midi)
    details = dict(report)
    details.update(schema_version=1, engine_version=ENGINE_VERSION, generation_mode=mode)
    details["provenance"] = {
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "output_sha256": hashlib.sha256(midi_data).hexdigest(),
        "python": platform.python_version(), "mido_reported_version": mido.version.__version__,
        "implementation_sha256": {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                  for name in ("musical.py", "ensemble.py", "song.py", "delivery.py")},
    }
    json_data = json.dumps(details, indent=2, ensure_ascii=False).encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    created = []
    try:
        for path, data in ((output, midi_data), (sidecar, json_data)):
            with path.open("xb") as handle:
                created.append(path)
                handle.write(data)
    except Exception:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise
    return sidecar
