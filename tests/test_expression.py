from dataclasses import replace
import io
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
import mido
from delivery import serialize_midi
from ensemble import arrange
from musical import Brief, Note, read_notes, track_from_notes
from song import Song, develop


def source():
    midi = mido.MidiFile()
    midi.tracks.append(track_from_notes([Note(i*480, i*480+360, 60, 90) for i in range(16)], 0, 0))
    return midi


class ExpressionTests(unittest.TestCase):
    def test_legacy_defaults_keep_delivered_midi(self):
        import json
        root = Path(__file__).resolve().parents[1]
        midi = mido.MidiFile(root/'test/0_melodia_original.mid')
        brief = Brief(**json.loads((root/'examples/automatic-dorian.json').read_text()))
        output, _ = arrange(midi, brief)
        self.assertEqual(serialize_midi(output), (root/'artifacts/v0.2.0/accompaniment.mid').read_bytes())

    def test_intensity_balance_and_curve_change_actual_velocities(self):
        brief = Brief(tonic=0, patron='sostenido', ritmo_armonico='compases', intensidad=80,
                      curva_dinamica='crescendo', balance_bajo=-25)
        midi = source()
        before = serialize_midi(midi)
        result, report = arrange(midi, brief)
        harmony = read_notes(result, report['parts'][0]['channel'])
        bass = read_notes(result, report['parts'][1]['channel'])
        self.assertLess(harmony[0].velocity, harmony[-1].velocity)
        self.assertEqual(harmony[0].velocity-bass[0].velocity, 25)
        self.assertEqual(serialize_midi(midi), before)
        self.assertEqual(result.tracks[:len(midi.tracks)], midi.tracks)
        cc = [m.value for t in result.tracks[len(midi.tracks):] for m in t if m.type == 'control_change' and m.control == 11]
        self.assertIn(76, cc)
        self.assertIn(112, cc)
        self.assertEqual(cc[-1],127)

    def test_activity_and_articulation_change_notes_without_overlap(self):
        brief = Brief(tonic=0, patron='sostenido')
        a, report = arrange(source(), brief)
        b, _ = arrange(source(), replace(brief, actividad=3))
        c, _ = arrange(source(), replace(brief, actividad=3, articulacion='staccato'))
        channel = report['parts'][0]['channel']
        original, active, short = [read_notes(m, channel) for m in (a,b,c)]
        self.assertGreater(len(active), len(original))
        self.assertEqual(len(active), len(short))
        self.assertTrue(all(s.end-s.start < n.end-n.start for s,n in zip(short,active)))
        for pitch in {n.pitch for n in active}:
            same = [n for n in active if n.pitch == pitch]
            self.assertTrue(all(n.end <= next_note.start for n,next_note in zip(same,same[1:])))
        self.assertEqual(read_notes(c, 0), read_notes(source(), 0))

    def test_harmonic_profile_changes_search_in_both_rhythm_modes(self):
        for rhythm in ('libre', 'compases'):
            base = Brief(tonic=0, patron='sostenido', ritmo_armonico=rhythm, costo_cambio=.1)
            _, settled = arrange(source(), replace(base, perfil_armonico='reposado'))
            _, rising = arrange(source(), replace(base, perfil_armonico='creciente'))
            self.assertNotEqual([h['roman'] for h in settled['harmony']], [h['roman'] for h in rising['harmony']])
            self.assertGreater(rising['harmony'][-1]['functional_tension'], settled['harmony'][-1]['functional_tension'])

    def test_section_overrides_apply_and_theme_matches(self):
        midi = source()
        brief = Brief(tonic=0, patron='sostenido', ritmo_armonico='libre')
        song = Song(sections=('theme','variation','coda'), expresion_secciones={
            'variation': {'intensidad': 95, 'actividad': 2}, 'coda': {'intensidad': 40, 'curva_dinamica': 'diminuendo'}})
        result, report = develop(midi, brief, song=song)
        theme, theme_report = arrange(midi, brief)
        channel = report['parts'][0]['channel']
        opening = [n for n in read_notes(result,channel) if n.start < report['sections'][0]['end_tick']]
        self.assertEqual(opening, read_notes(theme,theme_report['parts'][0]['channel']))
        self.assertEqual(report['sections'][1]['expression']['intensidad'],95)
        self.assertEqual(report['sections'][2]['expression']['intensidad'],40)
        variation = [n.velocity for n in read_notes(result,channel) if report['sections'][1]['start_tick'] <= n.start < report['sections'][1]['end_tick']]
        coda = [n.velocity for n in read_notes(result,channel) if n.start >= report['sections'][2]['start_tick']]
        self.assertGreater(min(variation),max(coda))
        read_notes(mido.MidiFile(file=io.BytesIO(serialize_midi(result))))

    def test_invalid_expression_rejected(self):
        for values in ({'intensidad':128},{'actividad':0},{'actividad':True},{'balance_bajo':-100},
                       {'curva_dinamica':'happy'},{'articulacion':'unknown'},{'perfil_armonico':'sad'}):
            with self.subTest(values=values), self.assertRaises(ValueError): Brief(**values)
        with self.assertRaises(ValueError):
            Song(expresion_secciones={'theme':{'intensidad':50}})


if __name__ == '__main__': unittest.main()
