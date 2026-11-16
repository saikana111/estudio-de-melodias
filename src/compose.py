"""Offline CLI: python src/compose.py input.mid output.mid --brief brief.json."""
import argparse
import json
from pathlib import Path

import mido
from musical import Brief, accompany
from delivery import save_bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--brief", type=Path)
    parser.add_argument("--melody-channel", type=int, default=0)
    parser.add_argument("--output-channel", type=int, default=2)
    parser.add_argument("--ensemble", choices=["chamber"], help="Shared harmony, bass and responses; assigns free channels")
    parser.add_argument("--single", action="store_true", help="Legacy single-part accompaniment instead of the default ensemble")
    parser.add_argument("--ensemble-config", type=Path, help="JSON instrument/response settings")
    parser.add_argument("--song", action="store_true", help="Develop seed into theme, variation, contrast, return and coda")
    parser.add_argument("--song-config", type=Path, help="JSON section/development settings; requires --song")
    args = parser.parse_args()
    if args.single and (args.song or args.ensemble):
        parser.error("--single cannot be combined with --song or --ensemble")
    if not args.single:
        args.ensemble = args.ensemble or "chamber"
    report_path = args.output.with_suffix(".analysis.json")
    if args.output.resolve() == args.input.resolve() or args.output.exists() or report_path.exists():
        parser.error("Choose a new output path; source and existing results are never overwritten")
    if args.song_config and not args.song:
        parser.error("--song-config requires --song")
    if args.ensemble_config and not (args.ensemble or args.song):
        parser.error("--ensemble-config requires --ensemble chamber or --song")
    try:
        source_bytes = args.input.read_bytes()
        source = mido.MidiFile(args.input)
        data = json.loads(args.brief.read_text(encoding="utf-8")) if args.brief else {}
        ensemble_data = json.loads(args.ensemble_config.read_text(encoding="utf-8")) if args.ensemble_config else {}
        song_data = json.loads(args.song_config.read_text(encoding="utf-8")) if args.song_config else {}
    except (OSError, ValueError, EOFError) as exc:
        parser.error(str(exc))
    if not all(isinstance(d, dict) for d in (data, ensemble_data, song_data)):
        parser.error("Configuration files must contain JSON objects")
    meters = {(m.numerator, m.denominator) for t in source.tracks for m in t if m.type == "time_signature"}
    if len(meters) > 1:
        parser.error("Changing meter is not supported by this baseline")
    if meters:
        numerator, denominator = next(iter(meters))
        data.setdefault("numerator", numerator)
        data.setdefault("denominator", denominator)
    if not (args.ensemble or args.song) and any(getattr(m, "channel", None) == args.output_channel for t in source.tracks for m in t):
        parser.error("Output channel is occupied; choose another --output-channel")
    try:
        if args.song or args.ensemble:
            from ensemble import Ensemble, arrange
            data.setdefault("patron", "sostenido")
            data.setdefault("ritmo_armonico", "libre")
            if args.song:
                from song import Song, develop
                source, report = develop(source, Brief(**data), args.melody_channel,
                                         Ensemble(**ensemble_data), Song(**song_data))
            else:
                source, report = arrange(source, Brief(**data), args.melody_channel, Ensemble(**ensemble_data))
        else:
            track, report = accompany(source, Brief(**data), args.melody_channel, args.output_channel)
            source.tracks.append(track)
    except (ValueError, TypeError) as exc:
        parser.error(str(exc))
    source.type = 1  # A type-0 source becomes a synchronous multitrack file.
    try:
        report_path = save_bundle(source, report, args.output, source_bytes,
                                  "song" if args.song else "ensemble" if args.ensemble else "single")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"MIDI: {args.output}\nDecisions: {report_path}")
    for warning in report["warnings"]:
        print(f"NOTE: {warning}")


if __name__ == "__main__":
    main()
