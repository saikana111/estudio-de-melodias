"""Performance instructions for the original interactive ensemble route."""
from collections import defaultdict
from bisect import bisect_right

import mido

from musical import Note, read_notes, track_from_notes


def strum(track, ppq):
    """Spread simultaneous attacks while preserving releases and expression CCs."""
    events, attacks, releases = [], defaultdict(list), defaultdict(list)
    tick = 0
    for msg in track:
        tick += msg.time
        index = len(events)
        events.append((tick, index, msg))
        if msg.type == "note_on" and msg.velocity:
            attacks[tick].append(index)
        elif msg.type == "note_off" or msg.type == "note_on":
            releases[msg.note].append(tick)
    onsets = list(attacks)
    for stroke, start in enumerate(onsets):
        indices = attacks[start]
        if len(indices) < 2:
            continue
        end = min(releases[events[i][2].note][bisect_right(releases[events[i][2].note], start)]
                  for i in indices)
        if stroke + 1 < len(onsets):
            end = min(end, onsets[stroke + 1])
        step = min(max(1, ppq // 64), (end - start - 1) // (len(indices) - 1))
        for order, i in enumerate(sorted(indices, key=lambda j: events[j][2].note, reverse=bool(stroke % 2))):
            msg = events[i][2]
            events[i] = (start + order * step, i, msg.copy(velocity=max(1, msg.velocity - order * 2)))
    result = mido.MidiTrack()
    previous = 0
    for tick, _, msg in sorted(events):
        result.append(msg.copy(time=tick-previous))
        previous = tick
    return result


def perform(source, output, report, brief, channel, drums, guitar):
    part = report["parts"][0]
    if guitar and not brief.rasgueo and 24 <= part["program"] <= 31:
        idx = len(source.tracks)
        output.tracks[idx] = strum(output.tracks[idx], output.ticks_per_beat)
    if drums != "ninguna":
        if any(getattr(m, "channel", None) == 9 for t in source.tracks for m in t):
            report["warnings"].append("Se conserva la percusión existente.")
        else:
            melody = read_notes(source, channel)
            first, last = melody[0].start, max(n.end for n in melody)
            beat = brief.beat_ticks or output.ticks_per_beat
            hits = []
            if drums == "acentos":
                for i, h in enumerate(report["harmony"]):
                    hits.append((h["start_tick"], 36 if i % 2 == 0 else 38, 0))
            else:
                if any((m.numerator,m.denominator) != (4,4) for t in source.tracks for m in t if m.type == "time_signature"):
                    raise ValueError("El patrón de batería requiere 4/4.")
                origin = brief.downbeat
                for i in range(max(0, (first-origin)*2//beat), (last-origin)*2//beat+1):
                    tick = origin + i*beat//2
                    if first <= tick < last:
                        hits.append((tick, 42, -16 if i%2 else -10))
                        if i%2 == 0:
                            hits.append((tick, 36 if i%4 == 0 else 38, 0))
                            if drums == "house" and i%4 == 2:
                                hits.append((tick, 36, -2))
            notes = [Note(t, min(last,t+max(1,beat//8)), pitch,
                          max(1,brief.intensidad+accent), 9) for t,pitch,accent in hits if t < last]
            if notes:
                output.tracks.append(track_from_notes(notes, 0, 9, "Bateria"))
                report["parts"].append({"role":"drums","channel":9,"program":0})
                report["generated_notes"] += len(notes)
    del output.merged_track
