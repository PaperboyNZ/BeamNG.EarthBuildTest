"""Actual frontage generation over rotated/sloping/offset synthetic terrain."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import numpy as np
from shapely.geometry import Polygon

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
import buildings as b
from buildgen import freeze_items
from buildgen.topology import Footprint


def scene(name,angle=0.,origin=(0.,0.),datum=0.,slope=(0.,0.),rough=0.):
    angle=np.deg2rad(angle)
    rotation=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
    offset=np.asarray(origin,float)
    transform=lambda xy:np.asarray(xy)@rotation.T
    def ground(xy):
        local=(np.asarray(xy)-offset)@rotation
        return datum+local@np.asarray(slope)+rough*np.sin(local[:,0]/8.)
    fp=Footprint(tuple(map(tuple,transform(((30,40),(74,40),(74,64),(30,64))))))
    spec=b.plan(np.asarray(fp.outer),dict(_footprint=fp,seed_id='terrain-check',
        **{'class':'supermarket'},height=6.,num_floors=1,roof_shape='flat',facade_material='concrete'))
    spec.gring=ground(np.asarray(fp.outer)+offset)
    item=(spec,float(min(spec.gring)),float(max(spec.gring)))
    road=transform(((-50.,15.),(150.,15.)))+offset
    lines=[(road,3.,'residential',False)]
    xy=transform(((-50.,19.25),(150.,19.25)))+offset
    walks=[dict(pts=np.c_[xy,ground(xy)],side=1,w=2.5)]
    raw=[dict(pts=w['pts'].copy(),side=w['side'],w=w['w']) for w in walks]
    b.doors([item],lines,*origin,ground=ground,walks=walks,raw_walks=raw)
    b.garage_drives([item],lines,*origin,ground=ground,walks=walks,raw_walks=raw)
    props=b.landscape_props([item],*origin)
    frozen=freeze_items([item])
    for mesh in (b.build(frozen),b.build(frozen,lite=True),b.collision_mesh(frozen)):
        assert mesh is not None and np.isfinite(mesh[0]).all(),name
    shape=lambda solid:Polygon([p[:2] for p in solid.top])
    beds=[s for s in spec.access.landscape if s.kind=='site_garden_bed']
    solids=spec.access.solids
    overlap=max((shape(a).intersection(shape(c)).area for a in beds for c in solids),default=0.)
    assert overlap<1e-7,name
    layout=spec.access.site_layout
    return dict(name=name,angle_deg=round(float(np.rad2deg(angle)),3),origin=list(origin),datum=datum,
        slope=list(slope),roughness=rough,bed_m2=round(sum(shape(s).area for s in beds),3),
        curbs=sum(s.kind=='site_curb' for s in solids),parking=layout.parking,
        native_props=dict(sorted(Counter(row[0] for row in props).items())),
        cuts=len(walks[0].get('driveways',())),raw_cuts=len(raw[0].get('driveways',())),
        bed_overlap_m2=round(overlap,9),diagnostics=list(layout.diagnostics))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'build/site-refinement/terrain.json')
    args=parser.parse_args()
    cases=[scene('flat'),scene('slope',slope=(.006,.02)),
        scene('offset_slope',origin=(1000.,-2000.),datum=137.,slope=(.006,.02)),
        scene('rotated_slope',angle=31.,origin=(1000.,-2000.),datum=-32.,slope=(.006,.02)),
        scene('gentle_rough',angle=-23.,datum=213.,slope=(.005,.01),rough=.008),
        scene('steep_suppressed',slope=(0.,.12))]
    for row in cases:
        assert row['cuts']==row['raw_cuts'],row['name']
    for row in cases[:-1]:
        assert row['parking']>0 and row['cuts']==1,row['name']
        assert 'automatic_entry_link_unresolved' not in row['diagnostics'],row['name']
        assert row['native_props'].get('site_shrub',0)>0,row['name']
    assert cases[-1]['parking']==0 and cases[-1]['curbs']==0
    for row in cases[2:4]:
        for key in ('parking','curbs','bed_m2','native_props','diagnostics'):
            assert row[key]==cases[1][key],(row['name'],key)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(dict(scope='synthetic runtime geometry, not game acceptance',cases=cases),
                                   indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(cases,indent=2))


if __name__=='__main__':main()
