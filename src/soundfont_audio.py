"""Offline FluidSynth rendering; no audio device, cloud, or Python native bindings."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import wave

import mido
from delivery import serialize_midi

ROOT = Path(__file__).resolve().parents[1]


def configuration():
    executable = os.environ.get('FLUIDSYNTH_BIN') or shutil.which('fluidsynth')
    if not executable:
        executable = next((str(p) for p in (ROOT/'.tools/fluidsynth').rglob('fluidsynth.exe')), None)
    font = os.environ.get('SOUNDFONT_PATH')
    if not font:
        font = next((str(ROOT/'assets/soundfonts'/name) for name in ('FluidR3_GM.sf2', 'GeneralUser-GS.sf2')
                     if (ROOT/'assets/soundfonts'/name).is_file()), None)
    if not executable or not Path(executable).is_file() or not font or not Path(font).is_file():
        raise ValueError('Falta FluidSynth o el SoundFont. Ejecutá python scripts/setup_audio.py o configurá FLUIDSYNTH_BIN y SOUNDFONT_PATH.')
    return Path(executable), Path(font)


def audio_status():
    try:
        executable, font = configuration()
        return {'available': True, 'font': font.name, 'renderer': executable.name}
    except ValueError as exc:
        return {'available': False, 'error': str(exc)}


def render(midi, output):
    """Render exact MIDI events/programs/controllers to stereo PCM with fixed gain.

    Uses separate temporary processes for deterministic controller state. No
    per-track/per-file normalization: preserve requested dynamic differences.
    """
    executable, font = configuration()
    duration = midi.length
    if duration <= 0 or duration > 600:
        raise ValueError('La escucha con SoundFont admite hasta 10 minutos por resultado; el MIDI se puede descargar igual.')
    output = Path(output)
    if output.exists():
        raise FileExistsError('El audio de salida ya existe')
    with tempfile.TemporaryDirectory(prefix='melody-audio-') as temporary:
        temp = Path(temporary)
        source, wave_path = temp/'input.mid', temp/'render.wav'
        source.write_bytes(serialize_midi(midi))
        command = [str(executable), '-niq', '-F', str(wave_path), '-T', 'wav', '-O', 's16',
                   '-r', '22050', '-g', '0.35', '-R', '1', '-C', '0',
                   '-o', 'synth.cpu-cores=1', '-o', 'synth.polyphony=256',
                   str(font), str(source)]
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        try:
            done = subprocess.run(command, capture_output=True, timeout=120, creationflags=flags)
        except subprocess.TimeoutExpired as exc:
            raise ValueError('La preparación del audio excedió dos minutos. Probá un fragmento más corto.') from exc
        if done.returncode or not wave_path.is_file():
            raise ValueError('FluidSynth no pudo preparar el audio. Revisá el SoundFont y la instalación.')
        with wave.open(str(wave_path), 'rb') as handle:
            if handle.getnchannels() != 2 or handle.getsampwidth() != 2 or handle.getnframes() == 0:
                raise ValueError('FluidSynth produjo un WAV no válido')
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('xb') as target:
            target.write(wave_path.read_bytes())
    return {'font': font.name, 'font_sha256': hashlib.sha256(font.read_bytes()).hexdigest(),
            'renderer_executable_sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
            'sample_rate': 22050, 'gain': 0.35}


class AudioCache:
    """Small on-disk session cache; caller holds a lock during reads/writes."""
    def __init__(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='melody-studio-audio-')
        self.directory = Path(self.temporary.name)

    def get(self, data, midi):
        executable, font = configuration()
        signature = repr([(p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in (executable, font)]).encode()
        key = hashlib.sha256(data+signature+b'22050-0.35-R1-C0-v1').hexdigest()
        path = self.directory/(key+'.wav')
        if not path.exists():
            render(midi, path)
            for old in sorted(self.directory.glob('*.wav'), key=lambda p: p.stat().st_mtime, reverse=True)[8:]:
                old.unlink()
        return key, path

    def close(self):
        self.temporary.cleanup()
