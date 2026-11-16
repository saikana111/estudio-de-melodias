"""Run the same dashboard service on a directory of MIDIs; keep per-file outcomes."""
import argparse
import io
import json
from pathlib import Path
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import mido
from generation import generate, inspect
from delivery import serialize_midi
from musical import read_notes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--song', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a new report path')
    results = []
    for path in sorted(p for p in args.directory.rglob('*') if p.suffix.lower() in ('.mid', '.midi')):
        entry = {'file': str(path.relative_to(args.directory))}
        start = time.perf_counter()
        try:
            raw = path.read_bytes()
            info = inspect(raw)
            output, report = generate(raw, {'mode': 'song' if args.song else 'ensemble'})
            loaded = mido.MidiFile(file=io.BytesIO(serialize_midi(output)))
            source = mido.MidiFile(file=io.BytesIO(raw))
            assert loaded.tracks[:len(source.tracks)] == source.tracks
            assert read_notes(loaded)
            entry.update(status='ok', melody_channel=report['request']['melody_channel'],
                         seconds=round(loaded.length, 2), channels=info['channels'])
        except ValueError as exc:
            entry.update(status='unsupported', reason=str(exc))
        except Exception as exc:
            entry.update(status='error', reason=str(exc))
        entry['runtime_seconds'] = round(time.perf_counter()-start, 3)
        results.append(entry)
    summary = {'mode': 'song' if args.song else 'ensemble', 'files': len(results),
               'ok': sum(r['status'] == 'ok' for r in results),
               'unsupported': sum(r['status'] == 'unsupported' for r in results),
               'errors': sum(r['status'] == 'error' for r in results),
               'scope': 'Structural compatibility, not listening quality', 'results': results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(summary, handle, indent=2)
    print(json.dumps({k: v for k, v in summary.items() if k != 'results'}))


if __name__ == '__main__':
    main()
