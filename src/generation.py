"""Shared, hardware-free generation service for local UI and integrations."""
from dataclasses import asdict
import io
import mido
from ensemble import Ensemble, arrange
from musical import Brief, read_notes, key_candidates
from song import Song, develop

MAX_BYTES = 2_000_000


def load(data):
    if not isinstance(data, bytes) or not 0 < len(data) <= MAX_BYTES:
        raise ValueError("Upload a MIDI file smaller than 2 MB")
    try:
        midi = mido.MidiFile(file=io.BytesIO(data))
        notes = read_notes(midi)
    except (EOFError, OSError, KeyError, IndexError) as exc:
        raise ValueError("Could not read this MIDI file") from exc
    if not notes:
        raise ValueError("No pitched notes found; percussion-only MIDI is not supported")
    if len(notes) > 4096 or midi.length > 600:
        raise ValueError("Use an excerpt of at most 10 minutes and 4096 notes")
    return midi, notes


def inspect(data):
    midi, notes = load(data)
    channels = []
    for channel in sorted({n.channel for n in notes}):
        selected = [n for n in notes if n.channel == channel]
        channels.append({"channel": channel, "notes": len(selected),
                         "range": [min(n.pitch for n in selected), max(n.pitch for n in selected)],
                         "keys": key_candidates(selected)[:3]})
    return {"channels": channels, "seconds": round(midi.length, 2),
            "tracks": len(midi.tracks), "ppq": midi.ticks_per_beat,
            "suggested_channel": max(channels, key=lambda c: c['notes'])['channel'],
            "meters": sorted({(m.numerator, m.denominator) for t in midi.tracks for m in t if m.type == 'time_signature'})}


def generate(data, settings=None):
    settings = settings or {}
    if not isinstance(settings, dict) or set(settings)-{'mode', 'melody_channel', 'brief', 'ensemble', 'song'}:
        raise ValueError("Unknown generation settings")
    source, notes = load(data)
    mode = settings.get('mode', 'ensemble')
    if mode not in ('ensemble', 'song'):
        raise ValueError("Choose ensemble or song")
    channel = settings.get('melody_channel', inspect(data)['suggested_channel'])
    if type(channel) is not int or channel not in {n.channel for n in notes}:
        raise ValueError("Choose a channel containing pitched notes")
    selected = [n for n in notes if n.channel == channel]
    if len(selected) > 256:
        raise ValueError("Select a melody excerpt with at most 256 notes (64 for longer song)")
    if mode == 'song' and settings.get('song') is None:
        song_data = {}
    else:
        song_data = settings.get('song', {})
    if any(not isinstance(v, dict) for v in (settings.get('brief', {}), settings.get('ensemble', {}), song_data)):
        raise ValueError("Musical settings must be JSON objects")
    brief_data = {'patron': 'sostenido', 'ritmo_armonico': 'libre', **settings.get('brief', {})}
    meters = {(m.numerator, m.denominator) for t in source.tracks for m in t if m.type == 'time_signature'}
    if len(meters) > 1:
        raise ValueError("Changing meter is not supported; select a constant-meter excerpt")
    if meters:
        numerator, denominator = next(iter(meters))
        brief_data.setdefault('numerator', numerator)
        brief_data.setdefault('denominator', denominator)
    try:
        brief, ensemble, song = Brief(**brief_data), Ensemble(**settings.get('ensemble', {})), Song(**song_data)
    except TypeError as exc:
        raise ValueError(f"Invalid configuration: {exc}") from exc
    result, report = (develop(source, brief, channel, ensemble, song) if mode == 'song'
                      else arrange(source, brief, channel, ensemble))
    if len({n.channel for n in notes}) > 1:
        report['warnings'].append('Other source parts are preserved, but their harmony is not reconciled with the new ensemble.')
    report['request'] = {'mode': mode, 'melody_channel': channel,
                         'brief': asdict(brief), 'ensemble': asdict(ensemble), 'song': asdict(song)}
    return result, report


def preview_notes(midi):
    """Seconds-based browser preview honoring tempo changes; no instrument synthesis."""
    from collections import defaultdict, deque
    active, result, time = defaultdict(deque), [], 0
    for msg in midi:
        time += msg.time
        if msg.type not in ('note_on', 'note_off') or msg.channel == 9:
            continue
        key = (msg.channel, msg.note)
        if msg.type == 'note_on' and msg.velocity:
            active[key].append((time, msg.velocity))
        elif active[key]:
            start, velocity = active[key].popleft()
            result.append([round(start, 5), round(time-start, 5), msg.note, velocity, msg.channel])
    return result
