import base64
import io
import json
from pathlib import Path
import random
import sys
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
import mido
from dashboard import Handler, ThreadingHTTPServer
from delivery import serialize_midi
from generation import generate, inspect, preview_notes
from musical import Note, SCALES, read_notes, track_from_notes


def varied_seed(index):
    rng = random.Random(index)
    tonic, mode = index % 12, list(SCALES)[index % 4]
    channel = [0, 3, 7, 12][index % 4]
    ppq = [96, 240, 480, 960][index % 4]
    numerator, denominator = [(3, 4), (4, 4), (6, 8)][index % 3]
    midi = mido.MidiFile(ticks_per_beat=ppq)
    midi.tracks.append(mido.MidiTrack([mido.MetaMessage('set_tempo', tempo=400000+index*7000),
        mido.MetaMessage('time_signature', numerator=numerator, denominator=denominator)]))
    notes, cursor = [], ppq//2
    for i in range(8+index % 9):
        length = rng.choice([ppq//2, ppq, ppq*2])
        pitch = 60+tonic+rng.choice(SCALES[mode])
        notes.append(Note(cursor, cursor+length, pitch, rng.randint(60, 110), channel))
        cursor += length+rng.choice([0, ppq//4, ppq//2])
    midi.tracks.append(track_from_notes(notes, index % 80, channel, 'Independent seed'))
    return midi, {'tonic': tonic, 'mode': mode}, channel


class GenerationTests(unittest.TestCase):
    def test_varied_inputs_both_modes_preserve_source_and_roundtrip(self):
        # 24 independent seeds; random generation is only test input construction.
        for index in range(24):
            source, brief, channel = varied_seed(index)
            raw = serialize_midi(source)
            source = mido.MidiFile(file=io.BytesIO(raw))  # Compare actual uploaded events, including end-of-track.
            info = inspect(raw)
            self.assertEqual(info['suggested_channel'], channel)
            for mode in ('ensemble', 'song'):
                with self.subTest(seed=index, mode=mode):
                    output, report = generate(raw, {'mode': mode, 'brief': brief})
                    loaded = mido.MidiFile(file=io.BytesIO(serialize_midi(output)))
                    self.assertEqual(loaded.tracks[:len(source.tracks)], source.tracks)
                    self.assertTrue(read_notes(loaded))
                    self.assertEqual(report['request']['melody_channel'], channel)
                    self.assertTrue(all(n[1] > 0 for n in preview_notes(loaded)))
                    if mode == 'song':
                        self.assertGreater(loaded.length, source.length)

    def test_default_is_ensemble_and_reproducible(self):
        raw = serialize_midi(varied_seed(3)[0])
        a, report = generate(raw)
        b, _ = generate(raw)
        self.assertEqual(report['request']['mode'], 'ensemble')
        self.assertNotIn('sections', report)
        self.assertEqual(serialize_midi(a), serialize_midi(b))

    def test_invalid_input_and_settings(self):
        raw = serialize_midi(varied_seed(0)[0])
        for data, settings in [(b'not midi', {}), (raw, {'mode': 'unknown'}),
                               (raw, {'melody_channel': 9}), (raw, {'brief': []}),
                               (raw, {'unexpected': True})]:
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                generate(data, settings)

    def test_http_inspect_generate_and_origin_protection(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f'http://127.0.0.1:{server.server_port}'
        payload = {'midi': base64.b64encode(serialize_midi(varied_seed(2)[0])).decode()}
        try:
            with urlopen(url) as response:
                page = response.read().decode('utf-8')
                self.assertIn('Estudio de melodías', page)
                self.assertIn('lang="es"', page)
            for endpoint in ('inspect', 'generate'):
                req = Request(url+'/api/'+endpoint, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
                with urlopen(req) as response:
                    result = json.load(response)
                if endpoint == 'generate':
                    self.assertEqual(result['report']['generation_mode'], 'ensemble')
                    self.assertTrue(read_notes(mido.MidiFile(file=io.BytesIO(base64.b64decode(result['midi'])))))
                else:
                    self.assertEqual(result['suggested_channel'], 7)
            req = Request(url+'/api/generate', data=json.dumps(payload).encode(), headers={'Origin': 'https://outside.example'})
            with self.assertRaises(HTTPError) as error:
                urlopen(req)
            self.assertEqual(error.exception.code, 403)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
