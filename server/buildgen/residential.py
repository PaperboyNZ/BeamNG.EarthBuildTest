"""Geographic dwelling structures fitted to source volumes and accepted access.

These are alternative local visual priors, not inferred ethnicity, construction
dates or surveyed floor plans. Recesses remain closed render assemblies; mapped
courtyards, physical envelopes and entrances remain authoritative.
"""
from dataclasses import replace
from functools import lru_cache
import json
import math
from pathlib import Path
from . import materials

PATH=Path(__file__).with_name('catalog')/'residential_structures.json'
MAX_ASSEMBLIES=24
MAX_SCREEN_BARS=48


@lru_cache(maxsize=1)
def catalogue():
    data=json.loads(PATH.read_bytes())
    if data.get('schema')!=1:raise ValueError('unsupported dwelling structure schema')
    return data


def selection(resolution,cls='',part=False,area=0.):
    if (part or resolution.use.value not in ('residential','unknown') or
            resolution.floors.value>4 or resolution.height.value>18. or area>1000. or
            cls not in ('','house','residential','detached','semidetached_house','bungalow','terrace','town_house','cabin','apartments')):
        return None
    region=resolution.selection.environment.region
    choices=catalogue()['regions'].get(region)
    if not choices:return None
    # Geographic structure is independent of the older colour/style mixture.
    # Contemporary or borrowed cladding cannot turn a local home into a foreign
    # generic suburban plan. Keep the same geography through all representations.
    return choices


def for_spec(spec):
    if (spec.inference is None or spec.plain or spec.deck or spec.church or spec.terminal or
            getattr(spec,'city',None) is not None or spec.footprint is None):return None
    choices=selection(spec.inference,spec.cls or '',area=spec.footprint.area)
    if not choices:return None
    key=getattr(spec.inference,'dwelling_structure','') or materials.choose(spec.seed,'dwelling-structure-v1',choices)
    row=catalogue()['families'][key]
    # A tall villa should retain its local modern composition rather than
    # acquiring a single-storey timber hall on every level.
    if spec.floors>row.get('max_floors',4):
        row=catalogue()['families'][row.get('tall_fallback','local_modern')]
        key=row['id']
    return dict(row,id=key,region=spec.inference.selection.environment.region)


def roof_options(region,identity,floors):
    import buildings as b
    choices=catalogue()['regions'].get(region)
    if not choices:return None
    key=materials.choose(b._hash01(identity,'v2_appearance'),'dwelling-structure-v1',choices)
    row=catalogue()['families'][key]
    if floors>row.get('max_floors',4):row=catalogue()['families'][row.get('tall_fallback','local_modern')]
    return row.get('roof_variants')


def resolve_id(region,identity,floors,use,cls,height,area,part=False):
    if (part or use not in ('residential','unknown') or floors>4 or height>18. or area>1000. or
            cls not in ('','house','residential','detached','semidetached_house','bungalow','terrace','town_house','cabin','apartments')):
        return ''
    import buildings as b
    choices=catalogue()['regions'].get(region)
    if not choices:return ''
    key=materials.choose(b._hash01(identity,'v2_appearance'),'dwelling-structure-v1',choices)
    row=catalogue()['families'][key]
    return row.get('tall_fallback','local_modern') if floors>row.get('max_floors',4) else key


def adjust_profile(spec,p):
    row=for_spec(spec)
    if row is None or p is None:return p
    p=dict(p)
    # Retain each of the 64 local profiles' dimensions within the structural
    # family, rather than flattening them into a new continent-wide template.
    p['window_width']=row['window_width']*(.75+.25*p.get('window_width',1.2)/1.2)
    p['bay']=row['bay']*(.8+.2*p.get('bay',3.)/3.)
    p['window_height']=row.get('window_height',1.6)*(.8+.2*p.get('window_height',1.5)/1.5)
    p['sill']=.6*row.get('sill',.65)+.4*p.get('sill',.65)
    p['opening_pattern']=row.get('pattern',p.get('opening_pattern','grouped'))
    p['reveal']=p['facade_depth']=.8*row['depth']+.2*p.get('facade_depth',.1)
    # Structural assemblies provide their own connected screens/frames.
    p['details']=[x for x in p['details'] if x not in ('screens','sash','mullion')]
    p['residential_structure']=row['id']
    p['massing_grammar']=row.get('edge_family',p.get('massing_grammar','plain_modern'))
    return p


def compose(spec,elevation):
    row=for_spec(spec)
    if row is None or elevation.length<2.8:return elevation
    from .facades import Opening
    ring=spec.footprint.outer
    front=spec.front
    if front is None:
        front=max(range(len(ring)),key=lambda i:math.dist(ring[i],ring[(i+1)%len(ring)]))
    inward=elevation.boundary>0
    principal=inward or elevation.edge==front
    retained=[o for o in elevation.openings if o.kind!='window']
    windows=[o for o in elevation.openings if o.kind=='window']
    if not windows or spec.windows is False:return elevation
    mode=row['mode'];result=list(retained)
    from .regional_architecture import catalogue as regional_catalogue
    local=regional_catalogue().get(row['region'],{})
    for floor in range(int(spec.floors)):
        original=[o for o in windows if o.floor==floor]
        if not original:continue
        if row.get('privacy') and not inward:
            # Deep high-level street slots; existing courtyard faces retain
            # room-sized apertures. No courtyard is invented from a style prior.
            for o in original[::2]:
                centre=(o.left+o.right)/2
                width_factor=.85+.3*materials.unit(spec.seed,('privacy-slot-width',elevation.boundary,elevation.edge))
                w=min(.85,max(.40,.65*local.get('window_width',1.2)/1.2)*width_factor,o.right-o.left)
                spare=max(0.,o.right-o.left-w)
                centre+=min(.6,spare*.4)*(2*materials.unit(spec.seed,('privacy-room-position',elevation.boundary,elevation.edge))-1)
                bottom=floor*spec.floor_h+min(1.5,spec.floor_h*.5)
                slot_height=.70+.25*materials.unit(spec.seed,('privacy-slot-height',elevation.boundary,elevation.edge))
                result.append(replace(o,left=centre-w/2,right=centre+w/2,bottom=bottom,
                                      top=min((floor+1)*spec.floor_h-.45,bottom+slot_height),depth=row['depth']))
            continue
        if not principal or mode in ('compact','frame','villa','terrace'):
            for i,o in enumerate(original):
                # Regional modern homes keep asymmetrical room groupings,
                # rather than a universal repeated Western sash lattice.
                assembly=('lattice' if mode=='lattice' else 'paired' if mode in ('villa','compact') else '')
                depth=row['depth']
                if principal and mode=='villa' and i%2:
                    # A distinct recessed utility/gallery bay interrupts the
                    # broad sliding-window rooms in modern Korean villa fronts.
                    assembly='gallery';depth=max(.65,depth)
                result.append(replace(o,depth=depth,assembly=assembly))
            continue
        # Fit whole shaded room bays inside clear spans between accepted doors
        # and garages. End piers remain solid, connected to the roof/storeys.
        lo,hi=.55,elevation.length-.55
        spans=[]
        for op in sorted(retained,key=lambda o:o.left):
            if op.floor!=floor and op.top<=floor*spec.floor_h:continue
            if op.bottom>=(floor+1)*spec.floor_h:continue
            if op.left-.35>lo:spans.append((lo,min(hi,op.left-.35)))
            lo=max(lo,op.right+.35)
        if lo<hi:spans.append((lo,hi))
        for lo,hi in spans:
            if hi-lo<1.7:continue
            rhythm=.9+.2*materials.unit(spec.seed,('dwelling-room-count',elevation.boundary,elevation.edge))
            count=max(1,min(4,math.ceil((hi-lo)/(row.get('module',4.5)*rhythm))))
            weights=[.8+.4*materials.unit(spec.seed,('dwelling-room-width',elevation.boundary,elevation.edge,i)) for i in range(count)]
            scale=(hi-lo)/sum(weights);cursor=lo
            for i in range(count):
                left=cursor+.10;cursor+=weights[i]*scale;right=cursor-.10
                bottom=floor*spec.floor_h+row.get('sill',.40)
                top=min((floor+1)*spec.floor_h-.40,spec.height-.30)
                if row['id']=='japanese_machiya' and floor:
                    # Low upper lattice rooms differ from the tall ground-floor
                    # street screen. The source storey/roof heights stay fixed.
                    bottom=floor*spec.floor_h+1.05
                    top=min(top,bottom+1.05)
                if top-bottom<.8:continue
                assembly=('breeze' if mode=='screen' else 'lattice' if mode in ('lattice','hall') else 'gallery')
                op=Opening('window',floor,left,right,bottom,top,max(2,min(6,round((right-left)/.75))),
                           original[0].variant,row['depth'],assembly)
                if not any(op.overlaps(other,.18) for other in result):result.append(op)
    # A building-wide cap is applied in plan(); each elevation also stays small.
    return replace(elevation,openings=tuple(sorted(result,key=lambda o:(o.floor,o.left,o.bottom))),
                   role='dwelling:'+row['id'])


def draw_opening(mesh,spec,op,at,quad,body,trim,window,lite=False,elevation=None):
    """Closed shaded rooms with actual depth, not dark panels painted on walls."""
    if not op.assembly:return False
    from .facades import FRAME
    x0,x1,z0,z1=op.left,op.right,op.bottom,op.top
    depth=float(op.depth or .25);w=x1-x0;h=z1-z0
    back=-depth
    row=for_spec(spec)
    timber=bool(row and row['id'] in ('japanese_machiya','japanese_engawa','korean_maru','chinese_courtyard'))
    structure=trim
    if timber:
        import buildings as b
        # Existing timber material and stable family-specific structural finish;
        # this is the gallery frame, separate from mapped wall cladding.
        rgb=(.24,.15,.10) if row['id']=='korean_maru' else (.20,.18,.13)
        structure=b._Looks(spec.seed)[b.custom_look(b.SIDING,rgb)]
    # Back glazing and its closed lower wall, floor, ceiling and jambs.
    panel=.40 if op.assembly=='gallery' else .12
    quad(x0,x1,z0,z0+panel,body,back)
    u0,u1,v0,v1=__import__('buildings').WIN_UV
    quad(x0,x1,z0+panel,z1,window,back,((u0,v0),(u1,v0),(u1,v1),(u0,v1)))
    uv=((0.,0.),(w,0.),(w,depth),(0.,depth))
    faces=[(at(x0,z0),at(x1,z0),at(x1,z0,back),at(x0,z0,back)),
           (at(x0,z1,back),at(x1,z1,back),at(x1,z1),at(x0,z1)),
           (at(x0,z0,back),at(x0,z1,back),at(x0,z1),at(x0,z0)),
           (at(x1,z0),at(x1,z1),at(x1,z1,back),at(x1,z0,back))]
    for face in faces:mesh.quad(*face,*uv,body)
    def bar(a,c,lo,hi,material=trim,d=.025):
        # A closed box section gives screens and rails real oblique silhouettes.
        if c-a<=0 or hi-lo<=0:return
        quad(a,c,lo,hi,material,d)
        if not lite:
            corners=((a,lo),(c,lo),(c,hi),(a,hi))
            for p,q in zip(corners,corners[1:]+corners[:1]):
                mesh.quad(at(*p,d),at(*q,d),at(*q,d-.045),at(*p,d-.045),
                          (0,0),(1,0),(1,.1),(0,.1),material)
    bar(x0-.055,x1+.055,z0-.07,z0,structure)
    bar(x0-.055,x1+.055,z1,z1+.07,structure)
    bar(x0-.055,x0,z0,z1,structure);bar(x1,x1+.055,z0,z1,structure)
    if timber and op.assembly in ('gallery','lattice'):
        # Front-plane timber posts and a deep head beam expose the shaded
        # gallery as a connected assembly from the street and grazing views.
        for x in (x0+.065,x1-.065):bar(x-.055,x+.055,z0,z1,structure,.035)
        bar(x0,x1,z1-.13,z1,structure,.045)
    if op.assembly=='gallery':
        # A waist-high closed parapet stays inside the existing solid physical
        # envelope. This is not advertised as a traversable balcony.
        rail=min(z1-.45,z0+.75)
        bar(x0,x1,z0,rail,body,.015)
        bar(x0,x1,rail,rail+.055,structure)
        n=min(6,max(1,int(w/1.1)))
        for i in range(1,n):
            x=x0+w*i/n;bar(x-.035,x+.035,rail+.055,z1,structure,.025 if timber else back+.025)
        if row and row.get('arch') and elevation is not None:
            from . import regional_architecture as regional
            shape=regional.aperture_shape(spec,regional.for_spec(spec),elevation,op)
            from .regional_openings import draw_arch
            if shape!='rectangular':draw_arch(mesh,op,at,body,trim,depth,.065,shape,lite=False)
    elif op.assembly=='breeze':
        columns=min(8,max(3,round(w/.42)));rows=min(5,max(2,round(h/.42)))
        for i in range(1,columns):
            x=x0+w*i/columns;bar(x-.045,x+.045,z0,z1,body)
        for i in range(1,rows):
            z=z0+h*i/rows;bar(x0,x1,z-.045,z+.045,body)
    elif op.assembly=='lattice':
        columns=min(12,max(3,round(w/.35)))
        for i in range(1,columns):
            x=x0+w*i/columns;bar(x-.018,x+.018,z0,z1,structure,back+.06)
        for fraction in (.33,.66):
            z=z0+h*fraction;bar(x0,x1,z-.018,z+.018,structure,back+.06)
    elif op.assembly=='paired':
        x=(x0+x1)/2;bar(x-.045,x+.045,z0,z1,trim,back+.05)
    return True


def frame_components(spec,elevation,row):
    if row is None or row['mode']!='frame' or elevation.boundary:return ()
    from .commercial_detail import Component,_wall_fragments
    result=[];length=elevation.length
    for floor in range(1,min(4,int(spec.floors)+1)):
        z=min(spec.height-.15,floor*spec.floor_h)
        result.extend(_wall_fragments(Component('dwelling_frame',0.,length,z-.14,z,'trim'),elevation.openings))
    n=max(1,min(5,round(length/3.5)))
    for i in range(n+1):
        x=length*i/n;left=max(0.,x-.11);right=min(length,x+.11)
        result.extend(_wall_fragments(Component('dwelling_frame',left,right,.05,spec.height-.15,'trim'),elevation.openings))
    return tuple(result[:28])
