"""Offline church mesh review: same source envelopes, three fitted compositions.

No downloads or game assets. Legacy controls replay the old church recipe and
nonrectangular fallback; they are not screenshots from a historical executable.
"""
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
from buildgen import churches, freeze_items, programme
from buildgen.evidence import normalise_attributes
from buildgen.topology import Footprint
from building_preview import raster


def shapes():
    return (('Rectangle',Footprint(((0,0),(18,0),(18,10),(0,10)))),
            ('Mapped L',Footprint(((0,0),(22,0),(22,8),(14,8),(14,15),(0,15)))),
            ('Source courtyard',Footprint(((0,0),(24,0),(24,18),(0,18)),
                                        (((8,6),(16,6),(16,12),(8,12)),))))


def make(family,fp,seed,matched=False,legacy=False,spire=None):
    attrs={'class':'church','height':15. if spire else 9.,'num_floors':1,'roof_shape':'gabled',
           'roof_height':np.nan if spire else 2.,'_footprint':fp,'seed_id':seed,'_church_family':family,
           '_church_spire':spire or 'none'}
    if matched:attrs.update(facade_material='render',facade_color='#d5d1c8')
    if legacy:
        spec=b._legacy_plan(np.asarray(fp.outer),attrs)
        spec.footprint=fp;spec.evidence=normalise_attributes(attrs);spec.diagnostics=()
        if not fp.is_rectangle():spec.roof='flat';spec.steeple=False;spec.porch=False
    else:spec=b.plan(np.asarray(fp.outer),attrs)
    spec.gring=np.zeros(len(spec.ring))
    roads=[(np.array([(-30.,-10.),(60.,-10.)]),3.,'residential',False)]
    props=b.doors([(spec,0.,0.)],roads,0.,0.,ground=lambda xy:np.zeros(len(xy)))
    return spec,props


def fingerprint(mesh):
    digest=hashlib.sha256()
    for value in (mesh[0],mesh[2],mesh[3],mesh[5]):digest.update(np.ascontiguousarray(value).tobytes())
    return digest.hexdigest()


def font(size):
    for name in ('Arial.ttf','DejaVuSans.ttf'):
        try:return ImageFont.truetype(name,size)
        except OSError:pass
    return ImageFont.load_default(size=size)


def sheet(out,legacy=False):
    height=1270 if legacy else 1645
    canvas=Image.new('RGB',(1800,height),(232,237,240));draw=ImageDraw.Draw(canvas)
    title='Legacy church recipe replay' if legacy else 'Church fabric — three fitted building compositions'
    draw.text((25,18),title,font=font(26),fill=(30,45,55))
    subtitle='Legacy controls: 9 m supplied total / 2 m mapped roof • old automatic tower and nonrectangular flat-fallback behavior' if legacy else \
             'Composition controls: 9 m total / 2 m mapped roof • decorated spires: 15 m total / unknown roof height • near plus lite inset'
    draw.text((25,53),subtitle,
              font=font(17),fill=(55,70,80))
    draw.text((25,79),'Left column shares outline, material and seed. Other columns exercise mapped concavity and a courtyard; approximate colours, no game lighting.',
              font=font(16),fill=(55,70,80))
    rows=[];cases=[]
    for row,family in enumerate(churches.FAMILIES):
        for column,(label,fp) in enumerate(shapes()):cases.append((row,column,family,label,fp,None))
    if not legacy:
        for column,kind in enumerate(churches.SPIRE_KINDS):
            cases.append((3,column,churches.FAMILIES[1],kind.replace('_',' ').title(),shapes()[0][1],kind))
    for row,column,family,label,fp,spire_kind in cases:
        spec,props=make(family,fp,f'church-control-{column}',matched=column==0,legacy=legacy,spire=spire_kind)
        frozen=freeze_items([(spec,0.,0.)])
        start=time.perf_counter();near=b.build(frozen);lite=b.build(frozen,lite=True);collision=b.collision_mesh(frozen)
        elapsed=(time.perf_counter()-start)*1000
        image=raster(near,props,[],600,290,b)
        inset=raster(lite,[],[],190,135,b)
        x,y=column*600,115+row*375
        canvas.paste(image,(x,y));canvas.paste(inset,(x+400,y+150))
        draw.rectangle((x+400,y+150,x+589,y+284),outline=(140,155,160),width=1)
        draw.text((x+408,y+154),'LITE',font=font(12),fill=(50,60,65))
        if spire_kind:
            # Inspect actual upper-tower triangles with a ground plane at
            # roof level; this reveals fitted louvers/cornices at useful size.
            minimum=spec.church.spire.shoulder_height-1.0
            selected=near[2][np.min(near[0][near[2],2],axis=1)>=minimum]
            indices,faces=np.unique(selected,return_inverse=True)
            enlarged=(near[0][indices]-np.array([*spec.church.spire.centre,minimum]))*6.
            detail=(enlarged,near[1][indices],faces.reshape(-1,3),
                    near[3][np.min(near[0][near[2],2],axis=1)>=minimum],near[4],near[5][indices])
            zoom=raster(detail,[],[],190,135,b)
            canvas.paste(zoom,(x+10,y+150));draw.rectangle((x+10,y+150,x+199,y+284),outline=(140,155,160))
            draw.text((x+18,y+154),'BELFRY DETAIL',font=font(12),fill=(50,60,65))
        family_label=family.removeprefix('church_').replace('_',' ').title()
        draw.text((x+18,y+296),f'{family_label} / {label}',font=font(20),fill=(30,45,55))
        draw.text((x+18,y+325),f'Near {len(near[0]):,} vertices • collision {len(collision[2]):,} triangles • top {near[0][:,2].max():.2f} m',
                  font=font(15),fill=(60,75,85))
        architecture=spec.church
        shared=programme.derive(frozen[0][0]) if architecture is not None and architecture.accepted else None
        if shared is not None:
            draw.text((x+18,y+346),f'Shared runs {len(shared.runs)} / floor datums {len(shared.datums)} / era {shared.era.status}',
                      font=font(13),fill=(60,75,85))
        rows.append(dict(family=family,label=label,source_id=f'church-control-{column}',
                         footprint=asdict(fp),source_total_height=15. if spire_kind else 9.,
                         source_roof_height=None if spire_kind else 2.,
                         rendered_top=float(near[0][:,2].max()),near_vertices=len(near[0]),
                         lite_vertices=len(lite[0]),collision_triangles=len(collision[2]),
                         near_fingerprint=fingerprint(near),lite_fingerprint=fingerprint(lite),
                         collision_fingerprint=fingerprint(collision),compile_ms=elapsed,
                         architecture=asdict(architecture) if architecture else None,
                         programme=asdict(shared) if shared is not None else None,
                         semantic_seed_channels={channel:shared.seed(channel) for channel in programme.CHANNELS} if shared else None,
                         facade_layout=asdict(churches.layout(spec,0.,0.)) if architecture and architecture.accepted else None))
    footer='Legacy recipe replay only. Includes old automatic tower silhouettes; no historical executable capture or BeamNG acceptance claim.' if legacy else \
           'Synthetic review only. Source-contained spires are labelled style priors; no churchyard, parking, mapped part assembly, regional pack or BeamNG acceptance claim.'
    draw.text((25,height-30),footer,
              font=font(15),fill=(60,75,85))
    out.parent.mkdir(parents=True,exist_ok=True);canvas.save(out)
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'build/church-stage1/church-review.png')
    args=parser.parse_args()
    before=args.out.with_name('church-before.png')
    before_rows=sheet(before,legacy=True)
    rows=sheet(args.out)
    sources={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in (
        ROOT/'server/buildgen/churches.py',ROOT/'server/buildgen/programme.py',ROOT/'server/buildgen/roofs.py',ROOT/'server/buildgen/facades.py',
        ROOT/'server/buildings.py',ROOT/'server/buildgen/plan.py',Path(__file__))}
    report=dict(status='synthetic_mesh_review_not_game_acceptance',sources=sources,fixtures=rows,
                legacy_recipe_replay=before_rows,before_image=str(before.resolve()),review_image=str(args.out.resolve()))
    args.out.with_suffix('.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({'review':str(args.out.resolve()),'legacy_control':str(before.resolve()),'fixtures':len(rows)},indent=2))


if __name__=='__main__':main()
