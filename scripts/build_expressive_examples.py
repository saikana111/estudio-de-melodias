"""Reproduce expressive MIDI plus actual SoundFont audio, without cloud/hardware."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import mido
from musical import Brief
from ensemble import arrange
from song import Song, develop
from delivery import save_bundle
from soundfont_audio import render


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'test/0_melodia_original.mid')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'artifacts/v0.3.0')
    args=parser.parse_args()
    brief=Brief(**json.loads((ROOT/'examples/expressive-dorian.json').read_text()))
    song=Song(**json.loads((ROOT/'examples/expressive-song.json').read_text()))
    source=mido.MidiFile(args.source)
    variants=[('ensamble-expresivo','ensemble',brief,None),
              ('ensamble-activo','ensemble',replace(brief,actividad=3,articulacion='staccato',
                  intensidad=76,curva_dinamica='crescendo',perfil_armonico='arco'),None),
              ('pieza-desarrollada','song',brief,song)]
    for name,*_ in variants:
        if any((args.output_dir/(name+suffix)).exists() for suffix in ('.mid','.wav','.analysis.json')):
            parser.error('Choose a new output directory; examples are never overwritten')
    for name,mode,settings,form in variants:
        result,report=develop(source,settings,song=form) if form else arrange(source,settings)
        path=args.output_dir/(name+'.mid')
        report['audio']=render(result,path.with_suffix('.wav'))
        save_bundle(result,report,path,args.source.read_bytes(),mode)
        loaded=mido.MidiFile(path)
        assert loaded.tracks[:len(source.tracks)]==source.tracks
        print(name,round(result.length,2),'seconds')


if __name__=='__main__':main()
