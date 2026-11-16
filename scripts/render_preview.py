"""Small additive synth for comparable previews, NOT a General MIDI renderer.

Uses the same timbre in every comparison, honors tempo events and note velocity.
No SoundFont, plugin or cloud service; programs/CC/pitch bends are not rendered.
"""
from array import array
from collections import defaultdict, deque
import math
import wave


def render(midi, path, sample_rate=22050):
    tick_seconds = 0.0
    active, notes = defaultdict(deque), []
    for msg in midi:  # mido converts deltas using the full tempo map; no sleep.
        tick_seconds += msg.time
        if msg.type not in ("note_on", "note_off"):
            continue
        key = (msg.channel, msg.note)
        if msg.type == "note_on" and msg.velocity:
            active[key].append((tick_seconds, msg.velocity))
        elif active[key]:
            start, velocity = active[key].popleft()
            notes.append((start, tick_seconds, msg.note, velocity, msg.channel))
    if any(active.values()):
        raise ValueError("Cannot preview hanging MIDI notes")
    duration = max((end for _, end, *_ in notes), default=0) + 0.3
    samples = array("f", [0]) * math.ceil(duration*sample_rate)
    for start, end, pitch, velocity, channel in notes:
        frequency = 440 * 2**((pitch-69)/12)
        count = int((end-start+0.12)*sample_rate)
        offset = int(start*sample_rate)
        gain = (velocity/127) * (0.23 if channel == 0 else 0.085)
        for i in range(count):
            t = i/sample_rate
            envelope = min(1, t/0.012) * math.exp(-0.35*t)
            if t > end-start:
                envelope *= max(0, 1-(t-(end-start))/0.12)
            angle = 2*math.pi*frequency*t
            sample = math.sin(angle) + 0.25*math.sin(2*angle) + 0.08*math.sin(3*angle)
            samples[offset+i] += gain*envelope*sample
    peak = max((abs(v) for v in samples), default=0)
    if peak > 1:
        raise ValueError(f"Preview clips: peak {peak}")
    pcm = array("h", (round(v*32767) for v in samples))
    import sys
    if sys.byteorder != "little":
        pcm.byteswap()
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm.tobytes())
