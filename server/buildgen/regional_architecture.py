"""Image-informed regional defaults and bounded facade components.

Parameters are authored visual interpretations, not surveyed measurements or
claims about individual buildings. Source materials, heights, roof forms and
access constraints remain authoritative. No imported landmark or sacred forms.
"""
from dataclasses import replace
from functools import lru_cache
import json
import hashlib
from pathlib import Path

from . import materials, house_styles

PATH = Path(__file__).with_name('catalog')/'regional_profiles.json'
MAX_COMPONENTS = 96
MAX_PER_ELEVATION = 24
MAX_CANOPIES = 16
MAX_ARCHES = 32


@lru_cache(maxsize=1)
def identity():
    return hashlib.sha256(PATH.read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def catalogue():
    data=json.loads(PATH.read_bytes())
    if data.get('schema') != 1:
        raise ValueError('Unsupported regional architecture schema')
    return data['profiles']


def profile(theme):
    if not theme:return None
    from .environments import catalogue as environments
    if environments()['regions'].get(theme,{}).get('status') not in ('active','pilot','adapter_ready'):
        return None
    return catalogue().get(theme)


def base_profile(spec):
    """Read-only family selection without resolving per-building decoration."""
    if not spec.inference or spec.plain or spec.floors>12 or spec.deck or spec.church or spec.terminal:
        return None
    if spec.inference.use.value not in ('residential','mixed','commercial','civic','unknown'):
        return None
    style=spec.inference.house_style
    p=house_styles.contemporary_profile(style) if style.variant=='contemporary' else \
        profile(house_styles.profile_region(spec.inference))
    if p is None and style.variant=='contemporary':
        p=profile(spec.inference.selection.environment.region)
    from . import residential
    from . import architectural_modifiers
    return architectural_modifiers.profile(spec, residential.adjust_profile(spec,p))


def for_spec(spec):
    p=base_profile(spec)
    if not p:return None
    # A catalogue row is a local vocabulary, not a finished building. Resolve a
    # detached copy from source identity so workers/LODs share the same choices
    # and a neighbouring building never mutates the cached regional defaults.
    p=dict(p)
    for key,span in (('window_width',(.88,1.12)),('bay',(.90,1.12)),
                     ('window_height',(.92,1.08)),('frame',(.88,1.12)),
                     ('reveal',(.85,1.15)),('facade_depth',(.85,1.15))):
        if key in p:p[key]*=dimension(spec,key,*span)
    p['sill']+=dimension(spec,'sill',-.08,.08)
    # Optional decoration is selected for the whole building, never independently
    # per window. Structural grammar and its connected beams/piers stay intact.
    expression=variation(spec)
    probability=.95 if expression=='local_detail' else .72 if expression=='ordinary' else .40
    p['details']=[detail for detail in p['details']
                  if materials.unit(spec.seed,('regional-detail-v1',detail))<probability]
    return p


def dimension(spec,channel,lo,hi):
    return lo+(hi-lo)*materials.unit(spec.seed,('regional-dimension-v1',channel))


def opening_centres(spec,boundary,edge,lo,hi,count,width,frame):
    """Coherent room bays with safe piers; the same lattice on every storey.

    Allocate only spare wall width. Symmetric or paired room groups change the
    composition without per-window noise, extra apertures or door movement.
    """
    if count<=0:return []
    gap=.25+2*frame
    spare=hi-lo-count*width-2*frame-(count-1)*gap
    if spare<0:
        return [lo+(hi-lo)*(k+.5)/count for k in range(count)]
    channel=('regional-room-bays-v1',boundary,edge,count)
    paired=materials.unit(spec.seed,(channel,'composition'))<.5
    weights=[.55+materials.unit(spec.seed,(channel,min(k,count-k) if paired else k//2))
             for k in range(count+1)]
    scale=spare/sum(weights)
    cursor=lo+frame+weights[0]*scale
    centres=[]
    for k in range(count):
        centres.append(cursor+width/2)
        cursor+=width+gap+weights[k+1]*scale
    return centres


def variation(spec):
    """A stable contemporary/ordinary/detailed interpretation, not an era claim."""
    if spec.inference and spec.inference.house_style.variant=='contemporary':
        return 'contemporary'
    u=materials.unit(spec.seed,'regional-expression-v1')
    return 'contemporary' if u<.20 else 'local_detail' if u>.70 else 'ordinary'


def window_parameters(spec, width, bay):
    p=for_spec(spec)
    if not p or spec.inference.facade.value=='glass':return width,bay,None
    variant=variation(spec)
    width=p['window_width']*(1.12 if variant=='contemporary' else 1.)
    bay=p['bay']
    pattern=p.get('opening_pattern','regular')
    grammar=p.get('massing_grammar','')
    if pattern=='grouped':width*=1.70;bay*=1.5
    elif pattern=='horizontal':width*=1.65;bay*=1.4
    elif pattern=='vertical':width*=.88;bay*=.95
    if grammar in ('arcaded_front','stone_loggia') and pattern!='vertical':
        bay=max(3.,bay);width=min(2.4,bay-.85)
    if spec.floors>=4:
        width=min(2.8,width*1.08)
        bay=max(width+.8,bay)
    # A regional rhythm is not permission to tile every available wall metre.
    # Keep substantial wall piers, especially around wide grouped windows.
    bay=max(bay*1.20,width+1.65,3.4)
    return width,bay,p


def glazing_share(p,front=False):
    if front and p.get('residential_structure'):
        from .residential import catalogue
        row=catalogue()['families'][p['residential_structure']]
        if row['mode'] in ('gallery','loggia','courtyard','lattice','hall','screen') and not row.get('privacy'):
            # A shaded room aperture includes solid parapets, screens and
            # piers; it is not an equally large unshaded glazing panel.
            return .70
    grammar=p.get('massing_grammar','')
    if front:
        if grammar in ('earthen_recess','compact_courtyard','arctic_modular'):return .24
        if grammar in ('arcaded_front','stone_loggia'):return .34
        return .30
    if grammar in ('earthen_recess','compact_courtyard','arctic_modular'):return .15
    if grammar in ('arcaded_front','stone_loggia'):return .24
    return .20


def window_vertical(spec,p,sill,height):
    if not p:return sill,height
    pattern=p.get('opening_pattern','regular');grammar=p.get('massing_grammar','')
    if pattern=='vertical':sill=.55;height=2.25*dimension(spec,'window_height',.92,1.08)
    elif pattern=='horizontal':sill=1.0;height=1.15*dimension(spec,'window_height',.92,1.08)
    if grammar in ('arcaded_front','stone_loggia') and pattern!='vertical':
        sill=.40;height=(spec.floor_h-.85)*dimension(spec,'window_height',.92,1.)
    return sill,min(height,spec.floor_h-sill-.35)


def wall_materials(spec,p,mats,body):
    """Material zones are fallback composition, never mapped cladding overrides."""
    import buildings as b
    if not p or spec.inference.facade.status!='fallback':return body,body
    colour=spec.evidence.get('facade_color') if spec.evidence else None
    if colour is not None and colour.status=='observed':return body,body
    if 'half_timber' in spec.inference.modifiers:return body,body
    mapping={'wood':b.SIDING,'render':b.STUCCO,'brick':b.BRICK_WALL,'stone':b.STONE,
             'concrete':b.CONCRETE,'metal':b.METALWALL}
    result=[]
    for key in ('base_material','upper_material'):
        family=materials.wall_family(p.get(key), spec.inference.use.value)
        if family not in mapping:result.append(body);continue
        rgb=tuple(p.get('timber_colour',p['accent'])) if family=='wood' and p.get('massing_grammar') in ('alpine_timber','east_asian_timber') else \
            (.92,.91,.88) if family in ('stone','brick','concrete') else wall_colour(
                house_styles.profile_region(spec.inference),family,spec.seed,
                materials.colour(spec.seed,family) or tuple(p['colours'][0]),
                broaden=spec.inference.house_style.variant!='unmixed')
        result.append(mats[b.custom_look(mapping[family],rgb)])
    return tuple(result)


def wall_colour(theme, family, identity, fallback, broaden=False):
    if broaden and house_styles.broad_palette(identity,'wall'):
        return fallback
    p=profile(theme)
    if p and (family in ('render','wood','metal') or family in p.get('material_colours',{})):
        colours=p.get('material_colours',{}).get(family,p['colours'])
        return tuple(colours[min(int(materials.unit(identity,'regional-wall-paint-v1')*len(colours)),len(colours)-1)])
    return fallback


def roof_colour(theme, family, identity, broaden=False):
    if broaden and house_styles.broad_palette(identity,'roof'):
        return None
    p=profile(theme)
    colours=p.get('roof_colours',{}).get(family) if p else None
    if not colours:return None
    return tuple(colours[min(int(materials.unit(identity,'regional-roof-tint-v1')*len(colours)),len(colours)-1)])


def roof_default(theme, use, low, identity, fallback):
    p=profile(theme)
    if not p or not low or use not in ('residential','mixed','commercial','civic','unknown'):
        return fallback
    return materials.choose(identity,'regional-roof-form-v1',p['roof_shapes'])


def pitch_default(theme, identity, fallback):
    p=profile(theme)
    if not p:return fallback
    lo,hi=p['pitch']
    return lo+(hi-lo)*materials.unit(identity,'regional-pitch-v1')


def components(spec, elevation, p, budget):
    """Shutters/bands occupy clear wall; glazing bars stay inside window panes.

    Components are shallow closed strips in the existing facade renderer. Their
    count is capped across a whole building and no detail introduces new access.
    """
    from .commercial_detail import Component, _wall_fragments
    if not p or budget<=0 or elevation.boundary or not (elevation.role=='generic' or elevation.role.startswith('dwelling:')):return ()
    details=set(p['details'])
    if variation(spec)=='contemporary':details-={'sash','timber_bands'}
    if spec.inference.facade.value not in ('wood','render'):
        details.discard('timber_bands')
    result=[]
    limit=min(MAX_PER_ELEVATION,budget)
    def add(kind,left,right,bottom,top,material='trim',overlay=False,near_only=False):
        if len(result)>=limit:return
        margin=0. if kind in ('deep_beam','upper_cornice','floor_band','corner_board') else .15
        left=max(margin,left);right=min(elevation.length-margin,right)
        bottom=max(.35,bottom);top=min(spec.height-.12,top)
        if right-left<.025 or top-bottom<.025:return
        c=Component(kind,left,right,bottom,top,material,overlay,near_only)
        fragments=(c,) if overlay else _wall_fragments(c,elevation.openings)
        result.extend(fragments[:limit-len(result)])
    grammar=p.get('massing_grammar','')
    # Large compositional elements are admitted before small decorative strips.
    # Every element fits on the existing wall and is clipped around access.
    # Siding uses narrow painted corner boards, not false veranda posts through
    # the middle of a wall. Restrict this vocabulary to modest timber houses;
    # a rectangular footprint gives both faces a clean joined corner. A board
    # must remain continuous rather than being clipped into stubs by an opening.
    if (grammar in ('timber_veranda','alpine_timber','east_asian_timber') and spec.inference.facade.value=='wood'
            and spec.inference.use.value=='residential' and spec.floors<=3
            and spec.height<=11.5 and spec.footprint.is_rectangle()):
        width=max(.09,min(.16,elevation.length*.012,spec.floor_h*.045))
        for left,right in ((0.,width),(elevation.length-width,elevation.length)):
            if not any(o.left<right+.06 and o.right>left-.06 for o in elevation.openings):
                add('corner_board',left,right,.35,spec.height-.12,'trim')
    # Window gaps do not establish a structural frame. Inferring posts there
    # produced irregular dark lines, including on Alpine/East Asian houses.
    # Projecting porch assemblies keep their real supports; flat walls do not.
    if grammar in ('timber_veranda','alpine_timber','east_asian_timber','urban_shophouse','panel_modern','arctic_modular','brick_pattern'):
        for floor in range(1,min(int(spec.floors)+1,9)):
            z=min(spec.height-.20,floor*spec.floor_h)
            add('deep_beam',0.,elevation.length,z-.10,z+.10,'trim' if grammar in ('brick_pattern','timber_veranda') else 'wall_trim')
    if grammar in ('masonry_terrace','render_shutters','earthen_recess','stone_loggia','arcaded_front','compact_courtyard'):
        add('upper_cornice',0.,elevation.length,spec.height-.30,spec.height-.15)
    if p.get('recess_panels') and elevation.edge==spec.front:
        # Opaque recessed lower panels suggest closed loggia/veranda bays. They
        # are window composition, not walkable or projected balconies.
        for op in elevation.openings:
            if op.kind=='window' and op.floor>0:
                add('recess_panel',op.left+.03,op.right-.03,op.bottom+.03,op.bottom+min(.45,(op.top-op.bottom)*.27),'accent',True)
    if ('floor_bands' in details or 'timber_bands' in details) and grammar not in (
            'timber_veranda','alpine_timber','east_asian_timber','urban_shophouse','panel_modern','arctic_modular','brick_pattern'):
        for floor in range(1,min(int(spec.floors),8)):
            z=floor*spec.floor_h
            add('floor_band',0.,elevation.length,z-.06,z+.06,
                'wall_trim' if 'timber_bands' in details else 'trim')
    windows=[op for op in elevation.openings if op.kind=='window']
    # Admit a detail across the whole elevation before adding another layer.
    # A per-window loop used up the budget downstairs and left upper bays bare.
    families=[('shutters',2),('screens',2),('sash',1),('lintels',1),('mullion',1)]
    for feature,cost in families:
        enabled=feature in details or feature=='mullion' and 'sash' in details and variation(spec)=='local_detail'
        if not enabled or cost*len(windows)>limit-len(result):continue
        for op in windows:
            l,r,z0,z1=op.left,op.right,op.bottom,op.top
            if feature=='shutters':
                width=min(.55,(r-l)*.42)
                add('shutter',l-.14-width,l-.14,z0,z1,'accent')
                add('shutter',r+.14,r+.14+width,z0,z1,'accent')
            elif feature=='lintels':
                # Curved heads already have a frame; a second flat lintel
                # touches their crown and muddies the arch silhouette.
                if aperture_shape(spec,p,elevation,op)=='rectangular':
                    add('lintel',l-.12,r+.12,z1+.13,z1+.22)
            elif feature=='sash':
                mid=(z0+z1)/2
                add('sash',l+.07,r-.07,mid-.025,mid+.025,overlay=True,near_only=True)
            elif feature=='mullion':
                mid=(l+r)/2
                add('mullion',mid-.022,mid+.022,z0+.07,z1-.07,overlay=True,near_only=True)
            elif feature=='screens':
                for fraction in (1/3,2/3):
                    x=l+(r-l)*fraction
                    add('screen',x-.025,x+.025,z0+.1,z1-.1,'accent',True,True)
    return tuple(result)


def band_frame(ring,edge,base):
    """Solve an elevation's trim frame once, shared by all its strip vertices.

    Job-local closure: no global geometry cache or retained footprint working
    set. Keep the original NumPy operation order for identical mesh coordinates.
    """
    import numpy as np
    a=np.asarray(ring[edge],dtype=float);c=np.asarray(ring[(edge+1)%len(ring)],dtype=float)
    d=c-a;length=float(np.linalg.norm(d));d/=length
    n=np.array([d[1],-d[0]])
    def miter(index):
        p=np.asarray(ring[index],dtype=float);before=p-np.asarray(ring[index-1]);after=np.asarray(ring[(index+1)%len(ring)])-p
        before/=np.linalg.norm(before);after/=np.linalg.norm(after)
        n0=np.array([before[1],-before[0]]);n1=np.array([after[1],-after[0]])
        den=1.+float(n0@n1)
        return (p,n0+n1,den) if den>.2 else None
    start,end=miter(edge),miter((edge+1)%len(ring))
    def point(s,z,depth):
        corner=start if abs(s)<1e-8 else end if abs(s-length)<1e-8 else None
        xy=corner[0]+corner[1]*depth/corner[2] if corner else a+d*s+n*depth
        return (float(xy[0]),float(xy[1]),base+z)
    return point


def band_point(ring,edge,s,z,depth,base):
    """Isolated roof/coping endpoints need only the selected corner's miter."""
    import numpy as np
    a=np.asarray(ring[edge],dtype=float);c=np.asarray(ring[(edge+1)%len(ring)],dtype=float)
    d=c-a;length=float(np.linalg.norm(d));d/=length
    n=np.array([d[1],-d[0]])
    xy=a+d*s+n*depth
    index=edge if abs(s)<1e-8 else (edge+1)%len(ring) if abs(s-length)<1e-8 else None
    if index is not None:
        p=np.asarray(ring[index],dtype=float);before=p-np.asarray(ring[index-1]);after=np.asarray(ring[(index+1)%len(ring)])-p
        before/=np.linalg.norm(before);after/=np.linalg.norm(after)
        n0=np.array([before[1],-before[0]]);n1=np.array([after[1],-after[0]])
        den=1.+float(n0@n1)
        if den>.2:xy=p+(n0+n1)*depth/den
    return (float(xy[0]),float(xy[1]),base+z)


def aperture_shape(spec,p,elevation,opening):
    if not p or opening.kind!='window' or not (elevation.role=='generic' or elevation.role.startswith('dwelling:')):return 'rectangular'
    scope=p.get('arch_scope','all')
    if scope in ('front','front_ground') and (elevation.boundary or elevation.edge!=spec.front):return 'rectangular'
    if scope=='front_ground' and opening.floor:return 'rectangular'
    if opening.assembly:
        if opening.assembly!='gallery':return 'rectangular'
        from .residential import for_spec
        row=for_spec(spec)
        return row.get('arch','rectangular') if row else 'rectangular'
    return p.get('opening_shape','rectangular')


def coping(mesh,spec,top,mats):
    """A shallow joined cap; earth/render parapets continue the wall material."""
    p=for_spec(spec)
    if not p or spec.inference.house_style.variant=='contemporary':return False
    import math
    import buildings as b
    grammar=p['massing_grammar']
    earthy=grammar in ('earthen_recess','compact_courtyard')
    _,wall=wall_materials(spec,p,mats,mats[spec.facade])
    mat=wall if earthy else mats[b.custom_look(b.PANEL,tuple(p['trim']))]
    depth=.06 if earthy else .12
    low,high=top-.18,top+.12
    ring=spec.footprint.outer
    uv=((0.,0.),(1.,0.),(1.,.1),(0.,.1))
    for edge,(a,c) in enumerate(zip(ring,ring[1:]+ring[:1])):
        length=math.dist(a,c)
        a0=band_point(ring,edge,0.,low,depth,0.)
        c0=band_point(ring,edge,length,low,depth,0.)
        a1=(*a0[:2],high);c1=(*c0[:2],high)
        mesh.quad(a0,c0,c1,a1,*uv,mat)
        mesh.quad((*a,high),a1,c1,(*c,high),*uv,mat)
        mesh.quad((*a,low),(*c,low),c0,a0,*uv,mat)
        mesh.quad((*c,top),(*a,top),(*a,high),(*c,high),*uv,mat)
    return True
