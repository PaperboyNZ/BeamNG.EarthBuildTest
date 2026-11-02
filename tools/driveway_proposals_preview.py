"""Actual runtime ranked-driveway fixtures, footprint sheet and old/new geometry delta."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
import buildings as b
from buildgen import driveways,freeze_items
from buildgen.diagnostics import DrivewayAudit
from buildgen.topology import Footprint
from generation_baseline import building,road,walk,access_case


def fixture(case):
    spec=building();items=[(spec,0.,0.)]
    if case=='obstacle':
        other=building(cls='utility')
        fp=Footprint(((5.,-6.2),(6.2,-6.2),(6.2,-5.2),(5.,-5.2)))
        other.ring=np.asarray(fp.outer);other.footprint=fp;other.inference=None;other.plain=True
        items.append((other,0.,0.))
    calls=[]
    def ground(points):
        calls.append(len(points))
        if case=='missing':return np.full(len(points),np.nan)
        if case=='terrain':return np.where((abs(points[:,0]-5.6)<.3)&(points[:,1]<-5.9),.6,0.)
        return np.zeros(len(points))
    walks=[walk()];drives=[];audit=DrivewayAudit()
    started=time.perf_counter()
    b.doors(items,road(),0.,0.,drives,ground=ground,walks=walks,driveway_audit=audit)
    elapsed=(time.perf_counter()-started)*1000
    mesh=b.collision_mesh(freeze_items(items))
    return spec,items,walks,drives,calls,audit,mesh,elapsed


def comparison(original,current):
    a,c=original[6],current[6]
    return dict(**mesh_delta(a,c),
                original_connected=any(s.kind=='driveway' for s in original[0].access.solids),
                current_connected=any(s.kind=='driveway' for s in current[0].access.solids),
                original_points=sum(original[4]),current_points=sum(current[4]))


def mesh_delta(a,c):
    same_vertices=a[0].shape==c[0].shape
    return dict(original_vertices=len(a[0]),current_vertices=len(c[0]),
                original_triangles=len(a[2]),current_triangles=len(c[2]),
                triangle_indices_equal=bool(np.array_equal(a[2],c[2])),
                max_coordinate_delta_m=float(np.max(abs(a[0]-c[0]))) if same_vertices else None)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'build/architecture-foundations/driveway-proposals.png')
    args=parser.parse_args();args.out.parent.mkdir(parents=True,exist_ok=True)
    path=ROOT/'build/architecture-foundations/original/driveways.py'
    module_spec=importlib.util.spec_from_file_location('buildgen._driveways_reference',path)
    original=importlib.util.module_from_spec(module_spec);sys.modules[module_spec.name]=original
    module_spec.loader.exec_module(original)
    canvas=Image.new('RGB',(1200,1100),'#edf1f0');draw=ImageDraw.Draw(canvas)
    try:font=ImageFont.truetype('Arial.ttf',18);small=ImageFont.truetype('Arial.ttf',15)
    except OSError:font=ImageFont.load_default(size=18);small=ImageFont.load_default(size=15)
    draw.text((24,16),'Ranked complete driveway proposals / actual runtime synthetic fixtures',font=font,fill='#233d45')
    draw.text((24,45),'One terrain batch; at most four options; no curb drop until the complete route fits',font=small,fill='#53666b')
    report=[]
    cases=(('clear','Clear nearest route'),('obstacle','Nearest footprint blocked / fallback'),
           ('terrain','Nearest grade fails / fallback'),('missing','Unknown terrain / no curb drop'))
    for index,(case,label) in enumerate(cases):
        with patch.object(driveways,'resolve',original.resolve):reference=fixture(case)
        current=fixture(case)
        spec,items,walks,drives,calls,audit,_,elapsed=current
        ox,oy=(index%2)*600,80+(index//2)*500
        draw.rounded_rectangle((ox+12,oy+8,ox+588,oy+486),12,fill='white')
        draw.text((ox+28,oy+21),label,font=font,fill='#233d45')
        def point(p):return (ox+36+(p[0]+5)*22,oy+72+(11-p[1])*13)
        def polygon(points,fill,outline=None):draw.polygon([point(p) for p in points],fill=fill,outline=outline)
        polygon(((-5,-13),(18,-13),(18,11),(-5,11)),'#d7e2cc')
        polygon(((-5,-13),(18,-13),(18,-9),(-5,-9)),'#7f898d')
        polygon(((-5,-9),(18,-9),(18,-5.925),(-5,-5.925)),'#c6c9c5')
        for item,_,_ in items:polygon(item.footprint.outer,'#aaa99f','#676c6b')
        for band in spec.access.landscape:
            polygon(band.top,'#8caf70' if 'lawn' in band.kind else '#987c5d')
        for solid in spec.access.solids:
            polygon(solid.top,'#62aebe' if solid.kind=='driveway' else '#cfb991' if solid.kind=='threshold' else '#dde2d7')
        if case=='terrain':polygon(((5.3,-7.6),(5.9,-7.6),(5.9,-5.9),(5.3,-5.9)),'#ce6e69')
        draw.line((point((-5,-9)),point((18,-9))),fill='#a7554b',width=3)
        for lo,hi,*_ in walks[0].get('driveways',()):
            draw.line((point((lo-50,-9)),point((hi-50,-9))),fill='#168491',width=5)
        notes=[n for n in spec.access.diagnostics if n.startswith('driveway_candidate_')]
        selected=next((n for n in notes if n.endswith('_selected')),'No accepted route')
        draw.text((ox+28,oy+397),selected.replace('driveway_','').replace('_',' '),font=small,fill='#233d45')
        draw.text((ox+28,oy+423),f'{len(drives)} drive / {sum(len(w.get("driveways",())) for w in walks)} curb cut / {len(calls)} terrain callbacks',font=small,fill='#53666b')
        draw.text((ox+28,oy+449),f'{sum(calls)} source points; independent crossing-only gate remains open',font=small,fill='#53666b')
        report.append(dict(case=case,diagnostics=notes,final_outcomes=audit.snapshot()['counts']['outcomes'],
                           candidate_counts=audit.snapshot()['counts']['candidates'],terrain_callbacks=calls,
                           access_ms=elapsed,comparison=comparison(reference,current)))
    canvas.save(args.out)
    # Warm paired measurements are instrumentation, not statistical/game gates.
    timings={}
    for label,resolver in (('original',original.resolve),('ranked',driveways.resolve)):
        values=[]
        with patch.object(driveways,'resolve',resolver):
            for i in range(30):values.append(fixture('clear')[7])
        timings[label]=dict(p50_ms=float(np.percentile(values,50)),p95_ms=float(np.percentile(values,95)))
    matrix=[]
    collision=b.collision_mesh
    for case in ('connected','no_footpath','no_garage','narrow','pedestrian_ramp','obstructed','missing_terrain','steep','no_roads'):
        meshes=[];results=[]
        for resolver in (original.resolve,driveways.resolve):
            def capture(items):
                mesh=collision(items);meshes.append(mesh);return mesh
            with patch.object(driveways,'resolve',resolver),patch.object(b,'collision_mesh',side_effect=capture):
                results.append(access_case(case))
        matrix.append(dict(case=case,**mesh_delta(*meshes),
                           original_crossings=results[0]['emitted_crossings'],current_crossings=results[1]['emitted_crossings'],
                           original_points=results[0]['terrain_points'],current_points=results[1]['terrain_points']))
    result=dict(status='synthetic_not_game_acceptance',max_candidates=4,length_limit_m=18.,grade_limit=.15,
                independent_crossing_only='not_validated',fixtures=report,baseline_access_matrix=matrix,warm_clear_30=timings)
    args.out.with_suffix('.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2));print(args.out)


if __name__=='__main__':main()
