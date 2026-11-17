import array
import base64
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
import mido
from delivery import serialize_midi
from musical import Note, track_from_notes
from soundfont_audio import audio_status, render


def sample(program=0):
    midi = mido.MidiFile()
    midi.tracks.append(track_from_notes([Note(0,480,60,80), Note(480,960,64,80)],program,0))
    return midi


@unittest.skipUnless(audio_status()['available'], 'Run scripts/setup_audio.py to test native SoundFont rendering')
class SoundFontTests(unittest.TestCase):
    def test_program_changes_produce_different_nonclipping_stereo_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            signals = []
            for program in (0, 48, 73):
                path = Path(directory)/f'{program}.wav'
                render(sample(program),path)
                with wave.open(str(path)) as wav:
                    self.assertEqual((wav.getnchannels(),wav.getframerate(),wav.getsampwidth()),(2,22050,2))
                    pcm=wav.readframes(wav.getnframes())
                    signal=array.array('h',pcm)
                    self.assertGreater(max(abs(x) for x in signal),100)
                    self.assertLess(max(abs(x) for x in signal),32767)
                    signals.append(pcm)
            self.assertEqual(len(set(signals)),3)

    def test_controller_events_and_source_not_modified(self):
        midi=sample(48)
        before=serialize_midi(midi)
        with tempfile.TemporaryDirectory() as directory:
            normal,muted=Path(directory)/'normal.wav',Path(directory)/'muted.wav'
            render(midi,normal)
            self.assertEqual(serialize_midi(midi),before)
            midi.tracks[0].insert(0,mido.Message('control_change',channel=0,control=7,value=0))
            render(midi,muted)
            with wave.open(str(normal)) as wav:
                a=array.array('h',wav.readframes(wav.getnframes()))
            with wave.open(str(muted)) as wav:
                b=array.array('h',wav.readframes(wav.getnframes()))
            self.assertGreater(sum(abs(x) for x in a),sum(abs(x) for x in b)*10)

    def test_http_render_cache_and_download(self):
        from dashboard import Handler, ThreadingHTTPServer
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url=f'http://127.0.0.1:{server.server_port}'
        try:
            urls=[]
            for _ in range(2):
                req=Request(url+'/api/render',data=json.dumps({'midi':base64.b64encode(serialize_midi(sample())).decode()}).encode(),headers={'Content-Type':'application/json'})
                with urlopen(req) as response: result=json.load(response)
                urls.append(result['url'])
            self.assertEqual(urls[0],urls[1])
            with urlopen(url+urls[0]) as response:
                self.assertEqual(response.headers['Content-Type'],'audio/wav')
                with wave.open(io.BytesIO(response.read())) as wav:self.assertGreater(wav.getnframes(),0)
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__ == '__main__':unittest.main()
