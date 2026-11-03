"""192 regional generic-block variants, separate from designed commercial work.

Keep source shells/access intact. Compose plausible, mildly irregular groups of
windows rather than independent random apertures or uninterrupted glass sheets.
"""
from functools import lru_cache
import json
import math
from pathlib import Path

from . import materials
from .commercial_detail import Component, _wall_fragments

MAX_OPENINGS = 256
MAX_COMPONENTS = 96
MAX_PER_ELEVATION = 24
MAX_FLOORS = 48
PATH = Path(__file__).with_name('catalog')/'regional_blocks.json'


@lru_cache(maxsize=1)
def catalogue():
    data=json.loads(PATH.read_text(encoding='utf-8'))
    if data['schema']!=1:raise ValueError('Unsupported regional block catalogue')
    if len(data['regions'])!=64 or any(len(r)!=3 for r in data['regions'].values()):
        raise ValueError('Regional blocks require all 192 proposals')
    return data['regions']


def profile(spec):
    if getattr(spec, 'city', None) is not None:
        return None  # dedicated city descriptions have independent authoring
    from . import commercial
    import buildings as b
    if (spec.inference is None or spec.footprint is None or spec.plain or spec.windows is False
            or spec.deck or spec.church or spec.terminal or getattr(spec,'city',None) or spec.site is not None
            or spec.garage_access is not None or spec.garage_opening
            or not 1<=spec.floors<=MAX_FLOORS or spec.floor_h<2.2 or spec.roof!='flat'
            or (spec.min_h or 0.)>.5):return None
    if (spec.cls in b.HOUSE_CLASSES or spec.cls in b.INDUSTRIAL_CLASSES
            or spec.cls in b.CHURCH_CLASSES or spec.cls in b.BRIDGE_CLASSES
            or spec.cls in ('transportation','terminal','parking','parking_garage','garage','garages')):return None
    recipe=spec.inference.selection.preset.id
    if recipe.startswith('ci_') or commercial.office_profile(spec):return None
    if spec.inference.use.value not in ('residential','mixed','commercial','civic','unknown'):return None
    fp=spec.footprint
    if fp.holes or fp.vertex_count>8:return None
    area=fp.area
    # Admit small road-clearance bevels, but never simplify their actual outline.
    box=fp.shape().minimum_rotated_rectangle
    if area/box.area<.94:return None
    lengths=[math.dist(a,c) for a,c in zip(fp.outer,fp.outer[1:]+fp.outer[:1])]
    if area<250. and max(lengths)<18.:return None
    if min(box.exterior.length/2-max(lengths),max(lengths))<5.:return None
    rows=catalogue().get(spec.inference.selection.environment.region)
    if not rows:return None
    return rows[min(2,int(materials.unit(spec.seed,'regional-block-design-v1')*3))]


def value(spec,p,key,span):
    lo,hi=span
    return lo+(hi-lo)*materials.unit(spec.seed,(p['id'],key))


def reveal(spec,p):
    return min(spec.floor_h*.10,value(spec,p,'reveal',p['reveal']))


def frame(spec,p):
    return .075 if p['grammar'] in ('panel','ribbon') else .095


def grid(spec,p,edge,length):
    """Aligned stacks with unequal room groups and modest inter-group gaps.

    Every floor uses this same lattice. Tall/wide buildings combine room bays
    into glazing groups before exhausting the building-wide aperture budget.
    """
    ring=spec.footprint.outer
    lengths=[math.dist(a,c) for a,c in zip(ring,ring[1:]+ring[:1])]
    usable=sum(l for l in lengths if l>=2.)
    capacity=max(1,int(MAX_OPENINGS/spec.floors*length/max(usable,1.))-1)
    count=max(1,min(capacity,int((length-1.4)/value(spec,p,'bay',p['bay']))))
    if length<2.:return ()
    group=max(2,int(value(spec,p,'group',p['groups'])+.5))
    # Small coherent differences in section spacing, never per-window jitter.
    weights=[1.+.16*(materials.unit(spec.seed,(p['id'],'room-group',edge,k//group))-.5)
             +(0.,.08,-.06)[k%3]
             +(.22 if k and k%group==0 else 0.) for k in range(count)]
    scale=(length-1.4)/sum(weights)
    cursor=.7;result=[]
    for k,w in enumerate(weights):
        bay=w*scale
        result.append((k,cursor,cursor+bay,k//group))
        cursor+=bay
    return tuple(result)


def openings(spec,p,boundary,edge,length,reserved,budget):
    from .facades import Opening
    if boundary:return tuple(reserved),'block_courtyard'
    front=spec.front if spec.front is not None else 0
    # Doorless secondary faces do not acquire invented service access.
    role='public' if edge==front else 'service' if edge==(front+len(spec.ring)//2)%len(spec.ring) else 'secondary'
    bays=grid(spec,p,edge,length)
    result=list(reserved)
    g=p['grammar'];office=spec.inference.facade.value=='glass' or spec.cls in ('office','commercial')
    for floor in range(int(spec.floors)):
        for k,left,right,section in bays:
            if len(result)-len(reserved)>=budget:return tuple(result),'block_'+role
            # An occasional solid circulation stack, not a checkerboard of holes.
            if len(bays)>=5 and k==len(bays)//2+(1 if edge%2 else -1):continue
            if role=='service' and len(bays)>=4 and k%4==3:continue
            bay=right-left
            local=materials.unit(spec.seed,(p['id'],'window-group',edge,section))
            width=(1.35+.40*local) if not office else (1.8+.5*local)
            if g in ('solid','masonry','arcade'):width*=.87
            if g in ('gallery','frame','screen'):width*=1.08
            if g=='ribbon':width*=1.30
            # Wide source bays fit grouped panes; never a huge single pane.
            cols=2 if width>1.8 else 1
            if bay>7.:
                width=min(5.2,bay*.55);cols=max(2,math.ceil(width/1.65))
            width=min(width,bay-.65)
            if width<.65:continue
            sill=min(.85,spec.floor_h*.27)
            h=min(1.55+.20*local,spec.floor_h-sill-.5)
            if g in ('masonry','terrace','arcade'):h=min(h+.18,spec.floor_h-sill-.5)
            if g=='ribbon':sill=min(1.,spec.floor_h*.30);h=min(1.4,spec.floor_h-sill-.5)
            if floor==spec.floors-1:
                # Top-floor glazing is slightly quieter, not a copy of each row.
                h*=.94;width*=.96
            storefront=bool(spec.shop and floor==0 and role=='public')
            if storefront:sill=.35;h=min(2.2,spec.floor_h-.8);width=min(width*1.15,bay-.65)
            if h<.65:continue
            centre=(left+right)/2
            op=Opening('storefront' if storefront else 'office' if office else 'window',floor,
                       centre-width/2,centre+width/2,floor*spec.floor_h+sill,
                       floor*spec.floor_h+sill+h,cols,int(local*3)%3)
            if op.right>length-.45 or op.left<.45:continue
            if not any(op.overlaps(other,.25+frame(spec,p)) for other in reserved):result.append(op)
    return tuple(result),'block_'+role


def wall_looks(spec,p):
    """Only fallback cladding is reinterpreted; mapped colour/material wins."""
    import buildings as b
    observed=spec.evidence.get('facade_color') if spec.evidence else None
    preserve=spec.inference.facade.status!='fallback' or (observed is not None and observed.status=='observed')
    if preserve:return spec.facade,spec.facade,spec.facade
    mapping={'brick':b.BRICK_WALL,'stone':b.STONE,'wood':b.SIDING,'render':b.STUCCO,'metal':b.METALWALL,'concrete':b.CONCRETE}
    def look(family,rgb):
        family=materials.wall_family(family, spec.inference.use.value)
        # Brick/stone textures already contain their base colour.
        tint=tuple(.76+.22*c for c in rgb) if family in ('brick','stone') else tuple(rgb)
        return b.custom_look(mapping[family],tint)
    jitter=value(spec,p,'wall-tint',(-.025,.025))
    rgb=tuple(max(.15,min(.94,c+jitter)) for c in p['wall_colour'])
    upper=look(p['wall_family'],rgb)
    lower=look(p['base_family'],p['base_colour'])
    alternate=look(p['wall_family'],tuple(max(.15,c*.88) for c in rgb))
    return lower,upper,alternate


def paint_cells(spec,p,elevation,cell,looks,section_width=None):
    """Base/body/crown and broad facade sections; identical in near and lite."""
    s0,s1,z0,z1=cell
    lower,upper,alternate=looks
    cuts=sorted({z0,z1,*[z for z in (spec.floor_h,spec.height-min(.65,spec.floor_h*.22)) if z0<z<z1]})
    if section_width is None:section_width=value(spec,p,'section-width',(9.,16.))
    xcuts=[s0]+[k*section_width for k in range(1,int(elevation.length/section_width)+1) if s0<k*section_width<s1]+[s1]
    for a,c in zip(xcuts,xcuts[1:]):
        section=int(((a+c)/2)/section_width)
        for lo,hi in zip(cuts,cuts[1:]):
            mat=lower if hi<=spec.floor_h else alternate if lo>=spec.height-.66 else upper
            if lo>=spec.floor_h and p['grammar'] in ('terrace','panel','timber') and section%3==1:mat=alternate
            yield a,c,lo,hi,mat


def components(spec,p,elevation,budget):
    if budget<=0 or elevation.boundary:return ()
    limit=min(MAX_PER_ELEVATION,budget);rows=[]
    g=p['grammar'];length=elevation.length
    def add(kind,l,r,lo,hi,material='trim',overlay=False,near=False):
        if len(rows)>=limit:return
        l=max(.12,l);r=min(length-.12,r);lo=max(.30,lo);hi=min(spec.height-.04,hi)
        if r-l<.025 or hi-lo<.025:return
        candidate=Component('block_'+kind,l,r,lo,hi,material,overlay,near)
        fragments=(candidate,) if overlay else _wall_fragments(candidate,elevation.openings)
        rows.extend(fragments[:limit-len(rows)])
    # Roof-edge and entrance hierarchy take priority over minor surface details.
    add('cap',.12,length-.12,spec.height-.18,spec.height-.04)
    if g in ('masonry','arcade','terrace'):
        add('cornice',.12,length-.12,spec.height-.47,spec.height-.31)
    elif g in ('timber','gallery','ribbon'):
        add('fascia',.12,length-.12,spec.height-.42,spec.height-.19,'accent')
    for op in elevation.openings:
        if op.kind!='door':continue
        add('entry_left',op.left-.27,op.left-.12,op.bottom,op.top+.24)
        add('entry_right',op.right+.12,op.right+.27,op.bottom,op.top+.24)
        add('entry_head',op.left-.27,op.right+.27,op.top+.12,op.top+.24)
    bays=grid(spec,p,elevation.edge,length)
    if g in ('frame','timber','arcade','panel','terrace'):
        for k,left,right,section in bays:
            if k and (k%max(2,int(sum(p['groups'])/2))):continue
            w=.10 if g=='panel' else .22
            add('pier',left-.28,left-.28+w,.3,spec.height-.48,'accent' if g in ('timber','panel') else 'trim')
    if g in ('gallery','ribbon','frame','timber','panel','arcade'):
        # Uniformly distribute bounded bands over tall volumes, not just the base.
        floors=list(range(1,int(spec.floors)))
        stride=max(1,math.ceil(len(floors)/7))
        for floor in floors[::stride]:
            add('band',.12,length-.12,floor*spec.floor_h-.24,floor*spec.floor_h-.07,
                'accent' if g in ('timber','ribbon') else 'trim')
    accepted=[o for o in elevation.openings if o.kind in ('window','office')]
    # Spread the optional screen/lintel detail over the elevation budget.
    stride=max(1,math.ceil(len(accepted)/4))
    for op in accepted[::stride]:
        if g=='screen':
            for fraction in (.22,.50,.78):
                centre=op.left+(op.right-op.left)*fraction
                add('screen',centre-.035,centre+.035,op.bottom+.08,op.top-.08,'accent',True)
        elif g=='gallery':
            # Opaque low window panels are not invented balcony platforms.
            add('lower_panel',op.left+.03,op.right-.03,op.bottom+.02,op.bottom+.24,'accent',True)
        elif g in ('masonry','terrace','arcade'):
            add('lintel',op.left-.13,op.right+.13,op.top+.12,op.top+.22)
    return tuple(rows)
