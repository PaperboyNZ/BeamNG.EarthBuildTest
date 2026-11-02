"""Render representative style/form combinations using production geometry."""
from pathlib import Path
from dataclasses import replace,asdict
import argparse,json,sys
import numpy as np
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import buildings as b
from buildgen import freeze_items,roof_edges,roof_outline,regional_architecture,house_styles
from buildgen.context import Context
from buildgen.topology import Footprint
from building_preview import raster


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    cases=[('nz_temperate','gabled','standard','wood'),
           ('us_northeast','gabled','gambrel','wood'),
           ('france_regional','hipped','mansard','render'),
           ('jp_temperate','gabled','broad_eave','wood'),
           ('eu_mediterranean','hipped','standard','render'),
           ('alpine','gabled','standard','wood'),
           ('us_northeast','gabled','saltbox','wood'),
           ('au_southeast','gabled','shed','wood'),
           ('maghreb','flat','standard','render')]
    canvas=Image.new('RGB',(1500,1260),'#e8edf0');draw=ImageDraw.Draw(canvas);report=[]
    for i,(key,kind,variant,facade) in enumerate(cases):
        fp=Footprint(((0.,0.),(12.,0.),(12.,9.),(0.,9.)))
        e=regional_architecture.catalogue()[key]['example']
        spec=b.plan(np.asarray(fp.outer),dict(seed_id='roof-edge-review-'+key,_footprint=fp,
                    _context=Context(location=(e['lat'],e['lon'])),height=8.,num_floors=2,
                    roof_shape=kind,roof_height=2.5 if kind!='flat' else 0.,facade_material=facade,**{'class':'house'}))
        spec.inference=replace(spec.inference,roof_variant=variant,house_style=house_styles.HouseStyle('regional',key))
        roof_outline.fit(spec,imagery=True)
        spec.gring=np.zeros(4);spec.front=0
        items=freeze_items([(spec,0.,0.)]);mesh=b.build(items);lite=b.build(items,lite=True)
        x,y=i%3*500,i//3*420
        canvas.paste(raster(mesh,[],[],500,365,b,tight=True,camera=(1.35,-2.,.9)),(x,y))
        t=roof_edges.treatment(spec)
        draw.text((x+15,y+370),f'{key} / {kind if variant=="standard" else variant}',fill='#1d2933')
        draw.text((x+15,y+390),f'eave {t.eave:.2f} m / rake {t.rake:.2f} m / edge {t.depth:.2f} m' if kind!='flat' else 'Shallow wall-coloured parapet and coping',fill='#43515c')
        report.append(dict(style=key,shape=kind,variant=variant,treatment=asdict(t),
                           source_area=fp.area,wall_area=spec.footprint.area,
                           near_triangles=len(mesh[2]),lite_triangles=len(lite[2])))
    args.out.parent.mkdir(parents=True,exist_ok=True);canvas.save(args.out)
    args.out.with_suffix('.json').write_text(json.dumps(dict(fixtures=report,scope='Production geometry raster; not native game lighting'),indent=2)+'\n')
    print(args.out)


if __name__=='__main__':main()
