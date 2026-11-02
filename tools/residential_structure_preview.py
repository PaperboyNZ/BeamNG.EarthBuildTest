"""Production structural comparison, including mapped-like polygons and courts."""
from pathlib import Path
from dataclasses import replace
import argparse,json,sys
import numpy as np
from PIL import Image,ImageDraw
from building_preview import raster


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--server',type=Path,default=Path(__file__).resolve().parents[1]/'server')
    parser.add_argument('--region',default='')
    args=parser.parse_args()
    sys.path.insert(0,str(args.server.resolve()))
    import buildings as b
    from buildgen import freeze_items,regional_architecture as regional
    from buildgen.context import Context
    from buildgen import residential,house_styles
    from buildgen.topology import Footprint
    families=residential.catalogue()['families']
    rows=[]
    for region,choices in residential.catalogue()['regions'].items():
        if args.region and args.region!=region:continue
        for family,_ in choices:
            if not args.region and family in [r[1] for r in rows]:continue
            rows.append((region,family))
    width=1500;cellw=500;cellh=430
    canvas=Image.new('RGB',(width,cellh*((len(rows)+2)//3)),'#e8edf0');draw=ImageDraw.Draw(canvas)
    report=[]
    from unittest.mock import patch
    for i,(region,family) in enumerate(rows):
        location=regional.catalogue()[region]['example']
        fp=Footprint(((0,0),(12,0),(12.003,9),(0,9)))
        options=[[family,1]]
        with patch.dict(residential.catalogue()['regions'],{region:options}),patch.object(house_styles,'select',return_value=house_styles.HouseStyle('regional',region)):
            spec=b.plan(np.asarray(fp.outer),dict(seed_id='dwelling-review-'+family,_footprint=fp,
                   _context=Context(location=(location['lat'],location['lon'])),height=8.,num_floors=2,
                   **{'class':'house'}))
            spec.gring=np.zeros(len(fp.outer));spec.front=0;spec.door=(0,1.8)
            items=freeze_items([(spec,0.,0.)]);mesh=b.build(items);lite=b.build(items,lite=True)
            x,y=(i%3)*cellw,(i//3)*cellh
            canvas.paste(raster(mesh,[],[],cellw,365,b,tight=True,camera=(1.35,-2.,.8)),(x,y))
            draw.text((x+12,y+371),region+' / '+family,fill='#1d2933')
            draw.text((x+12,y+392),f'{spec.roof} / {spec.inference.roof_variant} / '+str(len(mesh[0]))+' close vertices',fill='#43515c')
            report.append(dict(region=region,family=family,roof=spec.roof,roof_variant=spec.inference.roof_variant,
                               near_vertices=len(mesh[0]),lite_vertices=len(lite[0]),
                               assemblies=[o.assembly for e in items[0][0].facades.elevations for o in e.openings if o.assembly]))
    args.out.parent.mkdir(parents=True,exist_ok=True);canvas.save(args.out)
    args.out.with_suffix('.json').write_text(json.dumps(dict(scope='Synthetic production geometry, not native lighting',fixtures=report),indent=2)+'\n')
    print(args.out)


if __name__=='__main__':main()
