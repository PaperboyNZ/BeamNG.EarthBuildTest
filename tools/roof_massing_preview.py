"""Offline production comparison of inferred joined-wing residential roofs."""
from pathlib import Path
import json,sys
from unittest.mock import patch
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'server'),str(ROOT/'server/tests')]
from building_preview import raster
from test_buildgen_residential_structures import building
import buildings as b
from buildgen import residential


def main():
    out=ROOT/'build/world-architecture-programme/joined-roof-massing.png'
    canvas=Image.new('RGB',(1500,440),'#e8edf0');draw=ImageDraw.Draw(canvas);rows=[]
    for i,variant in enumerate(('standard','flared_hip','cross_gable')):
        recipe=dict(residential.catalogue()['families']['japanese_engawa'],roof_variants=[[variant,1]])
        with patch.dict(residential.catalogue()['families'],{'japanese_engawa':recipe}):
            spec,frozen,near,lite,col=building('jp_temperate','japanese_engawa',roof_height=2.5,roof_shape=None,height=9.)
            canvas.paste(raster(near,[],[],500,375,b,tight=True,camera=(1.35,-2.,.8)),(i*500,0))
            draw.text((i*500+15,383),'Same source footprint and height / '+variant,fill='#1d2933')
            draw.text((i*500+15,404),f'{len(near[0])} near vertices / {len(lite[0])} middle vertices',fill='#43515c')
            assert spec.inference.roof_variant==variant
            rows.append(dict(variant=variant,total_height=spec.height+spec.inference.roof_rise,roof_strategy=spec.inference.roof_variant,
                             close_vertices=len(near[0]),middle_vertices=len(lite[0])))
    out.parent.mkdir(parents=True,exist_ok=True);canvas.save(out)
    out.with_suffix('.json').write_text(json.dumps(dict(scope='Forced inferred production roof choices; offline raster, not game lighting; identical footprint/height',fixtures=rows),indent=2)+'\n')
    print(out)


if __name__=='__main__':main()
