"""Coordinated chamber arrangement of an immutable melody.

One harmonic plan drives bass and strings. A flute answers only during melody
rests. This is a deterministic arrangement preset, not unrestricted orchestration.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
import statistics

from musical import Brief, Note, accompany, read_notes, track_from_notes, expressive_velocity, articulated_end, expression_controls, add_controls


@dataclass(frozen=True)
class Ensemble:
    bass_program: int = 43       # General MIDI contrabass (zero-based)
    harmony_program: int = 48    # string ensemble
    response_program: int = 73   # flute
    responses: bool = True
    reserved_channels: tuple = ()

    def __post_init__(self):
        for program in (self.bass_program, self.harmony_program, self.response_program):
            if type(program) is not int or not 0 <= program <= 127:
                raise ValueError("Programs must be MIDI integers 0..127")
        if type(self.responses) is not bool:
            raise ValueError("responses must be boolean")
        if not isinstance(self.reserved_channels, (tuple, list)) or any(
                type(c) is not int or not 0 <= c <= 15 for c in self.reserved_channels):
            raise ValueError("reserved_channels must contain channel integers 0..15")


def _bass(harmony, channel, brief):
    """Root bass, separated from the lowest string voice, minimizing octave leaps."""
    notes, previous = [], 36
    for chord in harmony:
        root = chord["pitch_classes"][0]
        ceiling = min(47, min(chord["voicing"])-5)
        options = [p for p in range(28, ceiling+1) if p % 12 == root]
        if not options:
            raise ValueError("No room below the harmony for bass; choose a higher harmony register")
        pitch = min(options, key=lambda p: (abs(p-previous), abs(p-36), p))
        start, end = chord["start_tick"], chord["end_tick"]
        velocity = expressive_velocity(brief, start, harmony[0]["start_tick"], harmony[-1]["end_tick"], "bass")
        notes.append(Note(start, articulated_end(start, end, brief.articulacion), pitch, velocity, channel))
        previous = pitch
    return notes


def _responses(melody, harmony, channel, brief):
    """Project a two-note melodic contour onto the preceding chord during rests.

    Timing subdivides an observed rest, not an invented pulse. No response before
    the first melody note, after its end, or on top of a sounding melody note.
    """
    minimum_gap = max(1, round(statistics.median(n.end-n.start for n in melody)*0.4))
    result, sounding_until = [], melody[0].end
    for i, note in enumerate(melody[1:], 1):
        gap = note.start-sounding_until
        changes_inside_gap = any(sounding_until < h["start_tick"] < note.start for h in harmony)
        if gap >= minimum_gap and not changes_inside_gap:
            chord = next((h for h in reversed(harmony) if h["start_tick"] < sounding_until), None)
            if chord:
                options = [p for p in range(60, 84) if p % 12 in chord["pitch_classes"]]
                fragment = melody[max(0, i-2):i]
                if len(fragment) == 1:
                    fragment = fragment*2
                first = min(options, key=lambda p: (abs(p-fragment[0].pitch-12), p))
                direction = fragment[1].pitch-fragment[0].pitch
                eligible = [p for p in options if (p-first)*direction > 0] if direction else [first]
                second = min(eligible or options, key=lambda p: (abs(p-(first+direction)), p))
                margin = max(1, gap//12)
                unit = max(1, (gap-2*margin)//2)
                for j, pitch in enumerate((first, second)):
                    start = sounding_until+margin+j*unit
                    end = min(note.start-margin, start+max(1, round(unit*0.8)))
                    if start < end:
                        velocity = expressive_velocity(brief, start, melody[0].start, max(n.end for n in melody), "response")
                        result.append(Note(start, articulated_end(start, end, brief.articulacion), pitch, velocity, channel))
        sounding_until = max(sounding_until, note.end)
    return result


def arrange(midi, brief=None, melody_channel=0, ensemble=None):
    """Return a NEW MIDI and an auditable report. Never mutate source tracks."""
    ensemble = ensemble or Ensemble()
    brief = brief or Brief(patron="sostenido", ritmo_armonico="libre")
    occupied = {m.channel for t in midi.tracks for m in t if hasattr(m, "channel")}
    free = [c for c in range(16) if c != 9 and c not in occupied and c != melody_channel
            and c not in ensemble.reserved_channels]
    needed = 3 if ensemble.responses else 2
    if len(free) < needed:
        raise ValueError(f"Ensemble requires {needed} unused non-drum MIDI channels")
    harmony_channel, bass_channel = free[:2]
    harmony_brief = replace(brief, instrumento=ensemble.harmony_program)
    # Enforce room for the bass DURING voicing search, not after selecting a
    # locally attractive inversion that makes the full ensemble impossible.
    harmony_track, report = accompany(midi, harmony_brief, melody_channel, harmony_channel,
                                      voicing_filter=lambda chord, v: any(
                                          p % 12 == chord.root and p+5 <= min(v) for p in range(28, 48)))
    harmony_track.name = "Strings - shared harmony" if ensemble.harmony_program == 48 else "Harmony - shared chords"
    melody = read_notes(midi, melody_channel)
    bass_notes = _bass(report["harmony"], bass_channel, brief)
    tracks = [harmony_track, track_from_notes(bass_notes, ensemble.bass_program, bass_channel, "Bass - harmonic roots")]
    parts = [{"role": "harmony", "channel": harmony_channel, "program": ensemble.harmony_program},
             {"role": "bass", "channel": bass_channel, "program": ensemble.bass_program}]
    if ensemble.responses:
        response_channel = free[2]
        response_notes = _responses(melody, report["harmony"], response_channel, brief)
        if response_notes:
            tracks.append(track_from_notes(response_notes, ensemble.response_program, response_channel, "Flute - answers in rests"))
            parts.append({"role": "response", "channel": response_channel, "program": ensemble.response_program})
    # Harmony already carries its envelope from accompany(); bass and responses
    # share the same time curve without touching source controller messages.
    for i, part in enumerate(parts[1:], 1):
        tracks[i] = add_controls(tracks[i], expression_controls(brief, report['harmony'][0]['start_tick'],
                                  report['harmony'][-1]['end_tick'], part['channel']))
    result = deepcopy(midi)
    result.type = 1
    result.tracks.extend(tracks)
    del result.merged_track  # Mido may have cached the source timeline during inspection.
    report["ensemble"] = asdict(ensemble)
    report["parts"] = parts
    report["source_tracks_preserved"] = result.tracks[:len(midi.tracks)] == midi.tracks
    report["generated_notes"] = sum(len(read_notes(result, p["channel"])) for p in parts)
    report["limitations"] = [
        "Fixed chamber preset; not a learned orchestration or a full song-development model.",
        "Bass/string separation and melody-rest responses are enforced; strict counterpoint is not.",
        "Existing non-melody parts are preserved but not musically reconciled with new parts.",
        "Instrument programs are editable; instrument-specific articulation/fingering is not modelled.",
    ]
    return result, report
