"""Compare production roofs on imperfect and real mapped outlines (offline)."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageDraw
from building_preview import raster


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--server',type=Path,default=Path(__file__).resolve().parents[1]/'server')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    sys.path.insert(0,str(args.server.resolve()))
    import buildings as b
    from buildgen import freeze_items,roof_edges
    from buildgen.topology import Footprint
    fixture=Path(__file__).resolve().parents[1]/'server/tests/fixtures/real_roof_outlines.json'
    rows=json.loads(fixture.read_text())['fixtures']
    cases=[('Imperfect quadrilateral',Footprint(((0,0),(12,0),(12.001,9),(0,9)))),
           ('L-shaped home',Footprint(((0,0),(14,0),(14,5),(6,5),(6,12),(0,12)))),
           ('Mapped Auckland home',Footprint(rows[0]['outer'],rows[0]['holes']))]
    canvas=Image.new('RGB',(1440,440),'#e8edf0');draw=ImageDraw.Draw(canvas)
    report=[]
    for i,(name,fp) in enumerate(cases):
        spec=b.plan(np.asarray(fp.outer),dict(seed_id='roof-compare-'+str(i),_footprint=fp,
                      height=6.,num_floors=1,roof_shape='hipped',roof_height=2.,facade_material='wood',**{'class':'house'}),
                      lat=-36.91493,lon=174.90940)
        spec.front=0;spec.gring=np.zeros(len(fp.outer))
        items=freeze_items([(spec,0.,0.)]);mesh=b.build(items)
        canvas.paste(raster(mesh,[],[],480,375,b,tight=True,camera=(1.35,-2.,.7)),(i*480,0))
        t=roof_edges.treatment(spec)
        draw.text((i*480+15,380),name,fill='#1d2933')
        draw.text((i*480+15,401),f'Eave: {t.eave:.3f} m / rake: {t.rake:.3f} m',fill='#43515c')
        report.append(dict(name=name,eave=t.eave,rake=t.rake,vertices=len(mesh[0])))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    canvas.save(args.out)
    args.out.with_suffix('.json').write_text(json.dumps(dict(server=str(args.server),fixtures=report,scope='Synthetic production geometry raster; not a native game screenshot'),indent=2)+'\n')
    print(args.out)


if __name__=='__main__':main()
