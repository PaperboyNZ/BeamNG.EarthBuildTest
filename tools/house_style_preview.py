"""Same-shell neighbourhood and five-family review; synthetic, not game lighting."""
import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server',type=Path,default=ROOT/'server')
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--families',action='store_true')
    args=parser.parse_args()
    sys.path.insert(0,str(args.server.resolve()))
    import buildings as b
    from buildgen import freeze_items
    from buildgen.context import Context
    from buildgen.topology import Footprint
    from building_preview import raster
    latlon=(-36.9141,174.90925)
    ctx=Context(location=latlon) if 'location' in Context.__dataclass_fields__ else Context()
    fp=Footprint(((0.,0.),(12.,0.),(12.,9.),(0.,9.)))
    seeds=['house-neighbourhood-'+str(i) for i in range(24)]
    if args.families:
        from buildgen import house_styles
        seeds=[]
        for family in house_styles.CONTEMPORARY:
            for i in range(10000):
                seed='house-neighbourhood-'+str(i)
                style=house_styles.select('nz_temperate',seed,'residential','house',2,8.,108.)
                if style.variant=='contemporary' and style.alternate==family:
                    seeds.append(seed);break
    width,height,columns=340,270,5 if args.families else 6
    canvas=Image.new('RGB',(columns*width,50+height*((len(seeds)+columns-1)//columns)),'#e8edf0')
    draw=ImageDraw.Draw(canvas)
    try:font=ImageFont.truetype('arial.ttf',15)
    except OSError:font=ImageFont.load_default()
    draw.text((15,12),'Same dimensions / actual generated meshes / approximate colours / not BeamNG lighting',font=font,fill='#203040')
    rows=[]
    for index,seed in enumerate(seeds):
        attrs=dict(seed_id=seed,_footprint=fp,_context=ctx,**{'class':'house','height':8.,'num_floors':2})
        spec=b.plan(np.asarray(fp.outer),attrs)
        spec.gring=np.zeros(len(fp.outer));spec.door=(0,2.3);spec.front=0
        item=freeze_items([(spec,0.,0.)]);mesh=b.build(item)
        style=getattr(spec.inference,'house_style',None)
        label=style.variant if style else 'previous recipe'
        if style and style.variant=='global':label+=' / '+style.profile
        if style and style.alternate:label+=' / '+style.alternate
        x,y=(index%columns)*width,50+(index//columns)*height
        canvas.paste(raster(mesh,[],[],width,225,b),(x,y))
        draw.text((x+9,y+227),label,font=font,fill='#203040')
        draw.text((x+9,y+248),spec.inference.facade.value+' / '+spec.roof,font=font,fill='#405060')
        h=hashlib.sha256()
        for field in (0,1,2,3,5):h.update(mesh[field].tobytes())
        rows.append(dict(seed=seed,style=asdict(style) if style else None,geography=spec.inference.selection.environment.region,
                         facade=spec.facade,roof=spec.roof,roof_material=spec.roof_mat,
                         roof_colour=b.LOOKS[spec.roof_mat][1],vertices=len(mesh[0]),triangles=len(mesh[2]),sha256=h.hexdigest()))
    args.out.parent.mkdir(parents=True,exist_ok=True);canvas.save(args.out)
    report=dict(scope='Synthetic identical shells at Auckland context; no map geometry or game texture/lighting acceptance',
                server=str(args.server),mixture=dict(Counter(r['style']['variant'] if r['style'] else 'previous' for r in rows)),
                roof_colours=len({tuple(r['roof_colour']) for r in rows}),fixtures=rows)
    args.out.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='fixtures'},indent=2))


if __name__=='__main__':main()
