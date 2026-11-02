"""Audit same-shell regional variety and render actual generated sample meshes.

Colours approximate native materials; this is an offline diagnostic, not a game
screenshot. Optional --baseline points at saved regional_architecture.py and
facades.py files to compare aperture diversity before a change.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
import buildings as b
import buildgen
from buildgen import facades, freeze_items, regional_architecture as regional
from buildgen.context import Context
from buildgen.topology import Footprint
from building_preview import raster


def fixture(theme,index):
    example=regional.catalogue()[theme]['example']
    fp=Footprint(((0.,0.),(12.,0.),(12.,9.),(0.,9.)))
    attrs=dict(_footprint=fp,_context=Context(location=(example['lat'],example['lon'])),
               seed_id=f'diversity-{index}',**{'class':'house','height':8.,'num_floors':2,
               'roof_shape':'flat','facade_material':'render','facade_color':'#ccccbb'})
    spec=b.plan(np.asarray(fp.outer),attrs)
    spec.gring=np.zeros(4);spec.door=(0,2.3);spec.front=0
    return spec


def signature(layout):
    return tuple(tuple((o.kind,o.floor,*(round(v/.02) for v in
                 (o.left,o.right,o.bottom,o.top))) for o in e.openings) for e in layout.elevations)


def load_baseline(path,name):
    spec=importlib.util.spec_from_file_location('buildgen._baseline_'+name,path/(name+'.py'))
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'build/preset-diversity')
    parser.add_argument('--baseline',type=Path)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    baseline_regional=load_baseline(args.baseline,'regional_architecture') if args.baseline else None
    baseline_facades=load_baseline(args.baseline,'facades') if args.baseline else None
    if baseline_regional:baseline_regional.PATH=regional.PATH  # compare code with the same authored vocabulary
    records={}
    for theme in regional.catalogue():
        specs=[fixture(theme,i) for i in range(16)]
        layouts=[facades.plan(spec,0.,0.) for spec in specs]
        records[theme]={'buildings':16,'distinct_opening_geometry':len({signature(layout) for layout in layouts})}
        if baseline_facades:
            with patch.object(buildgen,'regional_architecture',baseline_regional):
                before=[baseline_facades.plan(spec,0.,0.) for spec in specs]
            records[theme]['baseline_distinct_opening_geometry']=len({signature(layout) for layout in before})
    themes=('nz_temperate','alpine','italy_regional','jp_temperate')
    font=ImageFont.truetype('arial.ttf',18)
    sheet=Image.new('RGB',(1600,64+len(themes)*340),'#edf1ee')
    draw=ImageDraw.Draw(sheet)
    draw.text((16,10),'Same region, same footprint, height, flat roof and observed wall colour; different building identities',font=font,fill='#243b33')
    draw.text((16,35),'Actual generated meshes with approximate materials. Offline preview, not BeamNG screenshots.',font=font,fill='#52665c')
    for row,theme in enumerate(themes):
        y=64+row*340
        draw.text((16,y+8),theme,font=font,fill='#243b33')
        for col in range(4):
            spec=fixture(theme,col);items=freeze_items([(spec,0.,0.)])
            mesh=b.build(items)
            sheet.paste(raster(mesh,[('door',2.3,0.,0.,0.,'',2.25,'')],[],400,290,b,
                               camera=(1.35,-2.,.75),tight=True),(col*400,y+36))
    sheet.save(args.out/'same-region-variation.png')
    report={'scope':'Same-shell aperture coordinates quantised to 2 cm; colours and pane variants excluded.',
            'regions':len(records),'buildings':16*len(records),
            'minimum_distinct_per_region':min(r['distinct_opening_geometry'] for r in records.values()),
            'maximum_distinct_per_region':max(r['distinct_opening_geometry'] for r in records.values()),
            'fixtures':records}
    if baseline_facades:
        report['baseline_distinct_per_region_range']=[min(r['baseline_distinct_opening_geometry'] for r in records.values()),
                                                     max(r['baseline_distinct_opening_geometry'] for r in records.values())]
    (args.out/'diversity.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='fixtures'},indent=2))


if __name__=='__main__':main()
