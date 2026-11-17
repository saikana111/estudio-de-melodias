"""Download pinned official SoundFont / Windows FluidSynth assets for local playback."""
import hashlib
import json
from pathlib import Path
import platform
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FONT_REV = '684543d5e5efaef08d02be50dcda8d552478fa60'
FONT_BASE = f'https://raw.githubusercontent.com/mrbumpy409/GeneralUser-GS/{FONT_REV}/'
FLUID_URL = 'https://github.com/FluidSynth/fluidsynth/releases/download/v2.6.2/fluidsynth-v2.6.2-win10-x64-cpp11.zip'
FLUID_SHA = '808295345d43c9c428f3fa87d29fbf97a9926f356df95559ff2689f3bd4072d7'


def fetch(url, path, expected=None):
    if path.exists():
        data = path.read_bytes()
    else:
        print('Downloading', path.name, flush=True)
        request = urllib.request.Request(url, headers={'User-Agent': 'Melody-Studio'})
        with urllib.request.urlopen(request, timeout=120) as response:
            data = response.read()
    digest = hashlib.sha256(data).hexdigest()
    if expected and digest != expected:
        raise ValueError(f'Checksum mismatch: {path.name}')
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(data)
    return digest


def main():
    folder = ROOT/'assets/soundfonts'
    font = folder/'GeneralUser-GS.sf2'
    digest = fetch(FONT_BASE+'GeneralUser-GS.sf2', font,
                   '9575028c7a1f589f5770fccc8cff2734566af40cd26ed836944e9a5152688cfe')
    fetch(FONT_BASE+'documentation/LICENSE.txt', folder/'GeneralUser-GS-LICENSE.txt')
    manifest = {'font': font.name, 'source': FONT_BASE+'GeneralUser-GS.sf2', 'sha256': digest}
    if platform.system() == 'Windows':
        if platform.machine().lower() not in ('amd64', 'x86_64'):
            raise ValueError('Install a FluidSynth binary for your architecture and set FLUIDSYNTH_BIN')
        archive = ROOT/'.tools/fluidsynth.zip'
        fetch(FLUID_URL, archive, FLUID_SHA)
        destination = (ROOT/'.tools/fluidsynth').resolve()
        with zipfile.ZipFile(archive) as zipped:
            for member in zipped.infolist():
                if not (destination/member.filename).resolve().is_relative_to(destination):
                    raise ValueError('Unsafe archive member')
            zipped.extractall(destination)
        manifest['renderer'] = {'source': FLUID_URL, 'sha256': FLUID_SHA}
    else:
        print('Install FluidSynth through your system package manager, or set FLUIDSYNTH_BIN.')
    (folder/'audio-assets.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
