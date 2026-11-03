"""Offline commercial review sheet and bounded compile benchmark; no downloads."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
import buildings as b
from buildgen import freeze_items
from buildgen import commercial, commercial_detail
from buildgen.topology import Footprint
from building_preview import raster


COMPARISON = (
    ('Workshop / trade units', 'workshop', 'metal', 6., 1),
    ('Strip shop composition', 'retail', 'brick', 6., 1),
    ('Supermarket', 'supermarket', 'concrete', 6., 1),
    ('Office / punched masonry', 'office', 'brick', 12., 3),
    ('Office / horizontal ribbons', 'office', 'concrete', 12., 3),
    ('Office / vertical curtain bays', 'office', 'glass', 12., 3),
)


def mesh_hash(mesh):
    digest=hashlib.sha256()
    for value in mesh:
        if isinstance(value,np.ndarray):
            digest.update(str((value.dtype.str,value.shape)).encode())
            digest.update(value.tobytes())
        else:
            digest.update(json.dumps(value,sort_keys=True).encode())
    return digest.hexdigest()


def make(cls,width,depth,seed,shape='rect',*,height=6.,floors=1,material=None):
    ring=((0,0),(width,0),(width,depth),(0,depth)) if shape=='rect' else \
         ((0,0),(width,0),(width,depth*.55),(width*.7,depth*.55),(width*.7,depth),(0,depth))
    fp=Footprint(ring)
    spec=b.plan(np.asarray(fp.outer),{'class':cls,'num_floors':floors,'height':height,'_footprint':fp,
        'seed_id':seed,'roof_shape':'flat','facade_material':material or ('metal' if cls=='warehouse' else 'concrete')})
    spec.gring=np.zeros(len(spec.ring))
    roads=[(np.array([(-30.,-12.),(width+30.,-12.)]),3.,'service' if cls!='supermarket' else 'residential',False)]
    props=b.doors([(spec,0.,0.)],roads,0.,0.,ground=lambda xy:np.zeros(len(xy)))
    if spec.facades is None:
        from buildgen import facades
        spec.facades=facades.plan(spec,0.,0.)
    return spec,props


def comparison(out,repeats=5):
    """Equal-footprint control sheet; style labels are not observed building ages."""
    canvas=Image.new('RGB',(1500,850),(232,237,240))
    draw=ImageDraw.Draw(canvas)
    try:font=ImageFont.truetype('Arial.ttf',18)
    except OSError:font=ImageFont.load_default(size=18)
    draw.text((24,15),'Commercial architecture comparison - six generated envelopes',font=font,fill=(30,45,55))
    draw.text((24,43),'Material-compatible style priors; construction era unknown. Synthetic meshes; no game acceptance.',font=font,fill=(60,75,85))
    rows=[]
    for index,(label,cls,material,height,floors) in enumerate(COMPARISON):
        samples=[]
        for repeat in range(repeats+1):
            start=time.perf_counter()
            spec,props=make(cls,30.,20.,'comparison-'+str(index),height=height,floors=floors,material=material)
            planned=time.perf_counter()
            frozen=freeze_items([(spec,0.,0.)])
            near=b.build(frozen);lite=b.build(frozen,lite=True);collision=b.collision_mesh(frozen)
            end=time.perf_counter()
            samples.append(dict(plan_access_ms=(planned-start)*1000,compile_ms=(end-planned)*1000))
        x,y=(index%3)*500,85+(index//3)*380
        canvas.paste(raster(near,props,[],500,300,b),(x,y))
        draw.text((x+18,y+302),label,font=font,fill=(30,45,55))
        draw.text((x+18,y+329),f'{spec.inference.selection.preset.id} / {len(near[0])} vertices',font=font,fill=(60,75,85))
        rows.append(dict(label=label,preset=spec.inference.selection.preset.id,
                         input=dict(cls=cls,material=material,height=height,floors=floors,width=30.,depth=20.),
                         near_vertices=len(near[0]),near_triangles=len(near[2]),lite_vertices=len(lite[0]),
                         collision_vertices=len(collision[0]),layout=asdict(spec.facades),
                         details=asdict(commercial_detail.plan(spec,spec.facades,commercial.derive_programme(spec),commercial.detail_family(spec))),
                         mesh_sha256=dict(near=mesh_hash(near),lite=mesh_hash(lite),collision=mesh_hash(collision)),
                         first_pass=samples[0],warm={field:{'p50_ms':float(np.percentile([s[field] for s in samples[1:]],50)),
                                                          'p95_ms':float(np.percentile([s[field] for s in samples[1:]],95))}
                                                         for field in samples[0]}))
    out.parent.mkdir(parents=True,exist_ok=True)
    canvas.save(out)
    sources=('server/buildgen/commercial.py','server/buildgen/facades.py','server/buildgen/commercial_detail.py','server/buildgen/programme.py',
             'server/buildgen/catalog/commercial.json','tools/commercial_preview.py')
    report=dict(status='synthetic_not_game_acceptance',repeats=repeats,fixtures=rows,
                source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sources})
    out.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(out)
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,default=ROOT.parent/'artifacts/buildings-commercial-stage1.png')
    parser.add_argument('--comparison',action='store_true',help='six-building equal-footprint architecture comparison')
    parser.add_argument('--repeats',type=int,default=5,help='warm samples per comparison fixture')
    args=parser.parse_args()
    if args.comparison:
        if not 1<=args.repeats<=100:parser.error('--repeats must be within 1..100')
        comparison(args.out,args.repeats)
        return
    canvas=Image.new('RGB',(1500,1180),(232,237,240))
    draw=ImageDraw.Draw(canvas)
    def font_at(size):
        for name in ('Arial.ttf','DejaVuSans.ttf'):
            try:
                return ImageFont.truetype(name,size)
            except OSError:
                pass
        return ImageFont.load_default(size=size)
    font,small=font_at(20),font_at(16)
    draw.text((24,18),'Procedural commercial buildings — first stage',font=font,fill=(30,45,55))
    draw.text((24,48),'Generated meshes • approximate colours • no game textures or lighting • closed doors',font=small,fill=(60,75,85))
    rows=[]
    for j,cls in enumerate(('warehouse','supermarket','workshop')):
        for i,(width,depth,shape) in enumerate(((32,20,'rect'),(58,30,'rect'),(47,28,'ell'))):
            spec,props=make(cls,width,depth,f'{cls}-{i}',shape)
            frozen=freeze_items([(spec,0.,0.)])
            mesh=b.build(frozen)
            im=raster(mesh,props,[],500,295,b)
            canvas.paste(im,(i*500,85+j*355))
            count={k:sum(o.kind==k for e in spec.facades.elevations for o in e.openings)
                   for k in ('service','staff_door','office','storefront','public_entry')}
            draw.text((i*500+20,385+j*355),f'{cls.title()} • {width} × {depth} m • {shape}',font=small,fill=(30,45,55))
            draw.text((i*500+20,410+j*355),f"{count['service']} shutters / {count['staff_door']} extra staff entries",font=small,fill=(60,75,85))
            rows.append({'preset':spec.inference.selection.preset.id,'size':[width,depth],
                         'vertices':len(mesh[0]),'openings':count,'layout':asdict(spec.facades)})
    args.out.parent.mkdir(parents=True,exist_ok=True)
    canvas.save(args.out)
    planning,freezing,meshing=[],[],[]
    for i in range(90):
        t=time.perf_counter()
        spec,_=make(('warehouse','supermarket','workshop')[i%3],25+i%57,18+i%23,str(i))
        t1=time.perf_counter()
        frozen=freeze_items([(spec,0.,0.)])
        t2=time.perf_counter()
        b.build(frozen); b.build(frozen,lite=True); b.collision_mesh(frozen)
        t3=time.perf_counter()
        planning.append((t1-t)*1000);freezing.append((t2-t1)*1000);meshing.append((t3-t2)*1000)
    stats={k:{'p50_ms':float(np.percentile(v,50)),'p95_ms':float(np.percentile(v,95))}
           for k,v in [('plan_and_access',planning),('freeze',freezing),('near_lite_collision',meshing)]}
    report={'status':'synthetic_not_game_acceptance','sites':90,'benchmark':stats,'fixtures':rows}
    args.out.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(stats,indent=2))
    print(args.out)


if __name__=='__main__':
    main()
