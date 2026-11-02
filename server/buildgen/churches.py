"""Conservative church fabric: fitted facades and bounded decorated spires.

No name dispatch, religious symbols, site surfaces or new occupied footprint. The
caller stores adapt()'s frozen result as ``spec.church`` and dispatches draw()
before its ordinary visual/collision geometry branch.
"""
from dataclasses import dataclass
import math
from numbers import Real

import numpy as np

from . import materials, roofs, programme
from .facades import Opening, Elevation, FacadeLayout, wall_cells
from .topology import Footprint

VERSION = 1
FAMILIES = ('church_plain_chapel', 'church_parish_hall', 'church_modern_hall')
MAX_SOURCE_VERTICES = 128
MAX_OPENINGS = 192
_SUPPORTED_ROOFS = ('flat', 'gabled', 'hipped')
_CHURCH_TAGS = frozenset(('church','chapel','cathedral'))
SPIRE_KINDS = ('square_broach','octagonal_needle','short_pyramidal')


@dataclass(frozen=True, slots=True)
class ChurchSpire:
    kind: str
    footprint: Footprint
    centre: tuple
    direction: tuple
    base_height: float
    shoulder_height: float
    top_height: float

    def __post_init__(self):
        object.__setattr__(self,'centre',tuple(float(v) for v in self.centre))
        object.__setattr__(self,'direction',tuple(float(v) for v in self.direction))
        if self.kind not in SPIRE_KINDS or not isinstance(self.footprint,Footprint):
            raise ValueError('unsupported church spire descriptor')
        if len(self.centre)!=2 or len(self.direction)!=2 or not all(math.isfinite(v) for v in (*self.centre,*self.direction)):
            raise ValueError('church spire requires finite centre and axis')
        if not math.isclose(math.hypot(*self.direction),1.,abs_tol=1e-6):
            raise ValueError('church spire axis must be normalized')
        heights=(self.base_height,self.shoulder_height,self.top_height)
        if not all(math.isfinite(v) for v in heights) or not 0<self.base_height<self.shoulder_height<self.top_height:
            raise ValueError('church spire heights must increase within the source envelope')


@dataclass(frozen=True, slots=True)
class ChurchArchitecture:
    family: str
    current_use: str
    architectural_fabric: str
    accepted: bool
    total_height: float
    roof_rise: float
    vocabulary: str
    roof_material: str
    party_walls: tuple = ()
    diagnostics: tuple = ()
    spire: ChurchSpire | None = None
    version: int = VERSION

    def __post_init__(self):
        object.__setattr__(self, 'party_walls', tuple(tuple(p) for p in self.party_walls))
        object.__setattr__(self, 'diagnostics', tuple(self.diagnostics))
        if self.spire is not None and not isinstance(self.spire,ChurchSpire):
            raise ValueError('church architecture requires a frozen spire descriptor')


def _text(value):
    return value.strip().lower() if isinstance(value, str) else ''


def _finite(value):
    if isinstance(value, bool):return None
    try:result=float(value)
    except (TypeError, ValueError, OverflowError):return None
    return result if math.isfinite(result) else None


def _missing(value):
    if value is None or isinstance(value,str) and not value.strip():return True
    try:return isinstance(value,Real) and not isinstance(value,bool) and math.isnan(value)
    except OverflowError:return False


def adapt(spec, attrs, footprint):
    """Adapt confirmed church fabric; accepted cases mutate only building style.

    ``_church_family`` is an explicit curated/test composition request, not a
    production feed observation. Modern composition is not a construction date.
    Unsupported confirmed fabric returns accepted=False plus a fallback reason;
    an unrelated/name-only/generic religious feature returns None.
    """
    import buildings as b
    from .specialized import select
    if not isinstance(footprint, Footprint):return None
    if not any(_text(attrs.get(field)) in _CHURCH_TAGS for field in ('class','subtype','building')):
        return None
    selected=select(attrs, footprint.area)
    if selected.architectural_fabric!='church':return None
    reasons=['church_fabric_confirmed', 'current_use_recorded_separately', 'source_or_diagnosed_style_prior_for_spire']
    def decline(reason):
        source_height=_finite(attrs.get('height'))
        declared_height=source_height if source_height is not None and source_height>0 else float(spec.height or 0.)
        return ChurchArchitecture('legacy_fallback', selected.facility_use, 'church', False,
                                  declared_height, 0., 'unchanged', 'unchanged',
                                  diagnostics=tuple(reasons+[reason, 'church_phase1_legacy_fallback']))
    source_footprint=attrs.get('_planning_footprint')
    if source_footprint is not None and (not isinstance(source_footprint,Footprint) or source_footprint!=footprint):
        return decline('church_infrastructure_cut_source_envelope_unsupported')
    if selected.ambiguous:return decline('church_conflicting_semantics')
    if _text(attrs.get('class'))=='cathedral' or _text(attrs.get('building'))=='cathedral':
        return decline('church_landmark_composition_unsupported')
    if attrs.get('_part') or attrs.get('parent_id') or attrs.get('tower') or attrs.get('building:part'):
        return decline('church_mapped_part_assembly_unsupported')
    if footprint.vertex_count>MAX_SOURCE_VERTICES or len(footprint.holes)>8 or not 20<=footprint.area<=2500:
        return decline('church_phase1_footprint_budget')
    minimum=_finite(attrs.get('min_height'))
    if not _missing(attrs.get('min_height')) and (minimum is None or minimum<0):
        return decline('church_invalid_minimum_height')
    if (spec.min_h or 0.)>0 or minimum and minimum>0 or spec.deck or spec.portal:
        return decline('church_elevated_or_playable_topology_unsupported')
    floors=_finite(attrs.get('num_floors'))
    if not _missing(attrs.get('num_floors')) and (floors is None or floors!=1):
        return decline('church_multiple_storeys_unsupported')
    if any(not _missing(attrs.get(k)) for k in ('roof_direction','roof_orientation')):
        return decline('church_mapped_roof_alignment_unsupported')
    roof=_text(attrs.get('roof_shape')) or spec.roof or 'gabled'
    if roof not in _SUPPORTED_ROOFS:return decline('church_mapped_roof_unsupported')
    if roof!='flat' and not roofs.supported(footprint):return decline('church_roof_complexity_budget')
    family=_text(attrs.get('_church_family'))
    if family and family not in FAMILIES:return decline('church_unknown_curated_family')
    if family:reasons.append('curated_composition_request_not_source_era')
    else:
        subtype=_text(attrs.get('subtype'))
        family='church_modern_hall' if subtype in ('modern_church','modern_hall') else \
               'church_parish_hall' if subtype in ('parish_church','parish_hall') else 'church_plain_chapel'
        reasons.append('observed_subtype_composition' if subtype in ('modern_church','modern_hall','parish_church','parish_hall')
                       else 'plain_chapel_conservative_composition_prior')
    mapped_total=_finite(attrs.get('height'))
    mapped_rise=_finite(attrs.get('roof_height'))
    if not _missing(attrs.get('height')) and (mapped_total is None or mapped_total<=0):
        return decline('church_invalid_mapped_height')
    if not _missing(attrs.get('roof_height')) and (mapped_rise is None or mapped_rise<0):
        return decline('church_invalid_mapped_roof_height')
    _,_,_,half_width=b.oriented_box(np.asarray(footprint.outer))
    if roof=='flat':
        if mapped_rise:return decline('church_flat_roof_height_conflict')
        rise=0.
    elif mapped_rise is not None:
        if mapped_rise<=0:return decline('church_pitched_roof_height_conflict')
        rise=mapped_rise
    else:
        rise=half_width*math.tan(math.radians(b.roof_pitch(spec)))
        if mapped_total is not None:rise=min(rise, mapped_total*.35, max(0.,mapped_total-2.8))
        reasons.append('church_roof_rise_style_prior')
    total=mapped_total if mapped_total is not None else float(spec.height)+rise
    body=total-rise
    if not 2.8<=body<=14 or not body<=total<=20 or (roof!='flat' and rise<.1):
        return decline('church_height_envelope_unsupported')
    blocked=[];party_walls=attrs.get('_party_walls') or ()
    if not isinstance(party_walls,(tuple,list)) or len(party_walls)>MAX_SOURCE_VERTICES:
        return decline('church_party_wall_context_budget')
    for item in party_walls:
        if not isinstance(item,(tuple,list)) or len(item)!=2 or any(type(v) is not int for v in item):
            return decline('church_invalid_party_wall_context')
        boundary,edge=item
        rings=(footprint.outer,*footprint.holes)
        if not 0<=boundary<len(rings) or not 0<=edge<len(rings[boundary]):
            return decline('church_invalid_party_wall_context')
        blocked.append((boundary,edge))
    aliases={'timber':'wood','wood':'wood','weatherboard':'wood','brick':'brick','stone':'stone',
             'render':'render','plaster':'render','stucco':'render','concrete':'concrete','metal':'metal'}
    observed=_text(attrs.get('facade_material'))
    vocabulary=aliases.get(observed) if observed else None
    if observed and vocabulary is None:return decline('church_mapped_facade_material_unsupported')
    if vocabulary is None:
        vocabulary={'church_plain_chapel':'wood','church_parish_hall':'brick','church_modern_hall':'render'}[family]
        reasons.append('church_material_vocabulary_style_prior')
    kind={'wood':b.SIDING,'brick':b.BRICK_WALL,'stone':b.STONE,'render':b.STUCCO,
          'concrete':b.CONCRETE,'metal':b.METALWALL}[vocabulary]
    colour=b.parse_color(attrs.get('facade_color'))
    if colour is not None:facade=b.custom_look(kind,colour)
    elif vocabulary=='brick':facade=('bne_brick_red','bne_brick_dark','bne_brick_tan')[min(2,int(programme.legacy_seed(spec,'vocabulary','church-brick')*3))]
    elif vocabulary=='stone':facade=f'{kind}|{min(len(b.WALL_TINTS[kind])-1,int(programme.legacy_seed(spec,"vocabulary","church-stone")*len(b.WALL_TINTS[kind])))}'
    else:facade=b.custom_look(kind,materials.colour(spec.seed,vocabulary))
    from .inference import ROOF_ALIASES
    supported_covers={'metal':b.ROOF_METAL,'copper':b.ROOF_METAL,'tile':b.ROOF_SLATE,'slate':b.ROOF_SLATE,
                      'shingle':b.ROOF_SHINGLE,'membrane':b.ROOF_FLAT}
    mapped_cover=_text(attrs.get('roof_material'))
    cover='membrane' if roof=='flat' else 'metal'
    if not _missing(attrs.get('roof_material')):
        cover=ROOF_ALIASES.get(mapped_cover,mapped_cover if mapped_cover in supported_covers else None)
        if cover not in supported_covers:return decline('church_mapped_roof_material_unsupported')
    cover_kind=supported_covers[cover]
    roof_colour=b.parse_color(attrs.get('roof_color'))
    if roof_colour is not None:roof_mat=b.custom_look(cover_kind,roof_colour)
    elif cover=='copper':roof_mat=b.custom_look(cover_kind,b.COLOR_NAMES['copper'])
    else:roof_mat=f'{cover_kind}|{min(len(b.ROOF_TINTS[cover_kind])-1,int(programme.legacy_seed(spec,"vocabulary","church-roof-cover")*len(b.ROOF_TINTS[cover_kind])))}'
    spire,body,spire_reasons=_fit_spire(spec,attrs,footprint,family,selected.facility_use,total,body,rise,mapped_rise)
    reasons.extend(spire_reasons)
    spec.footprint=footprint;spec.ring=np.asarray(footprint.outer,np.float64)
    spec.height=body;spec.floor_h=body;spec.floors=1;spec.roof=roof
    spec.pitch=math.degrees(math.atan2(rise,half_width)) if rise else 0.
    spec.facade=facade;spec.wall=facade;spec.roof_mat=roof_mat
    spec.steeple=False;spec.porch=False;spec.shop=False;spec.sign=None;spec.plain=False;spec.windows=True
    spec.inference=None;spec.facades=None;spec.garage_opening=None
    if family=='church_modern_hall':reasons.append('modern_composition_is_not_observed_construction_era')
    if selected.facility_use not in ('church','religious','unknown'):reasons.append('converted_fabric_no_active_worship_identity')
    return ChurchArchitecture(family,selected.facility_use,'church',True,total,rise,vocabulary,cover,
                              tuple(sorted(set(blocked))),tuple(reasons),spire)


def _fit_spire(spec,attrs,footprint,family,current_use,total,body,rise,mapped_rise):
    """At most one source-contained roof tower, fitted inside the total height.

    This procedural option is an explicit user-authorized style prior. It never
    claims mapped tower evidence, changes a measured roof-height span, or grows
    the occupied source footprint. Mapped part assemblies remain unsupported.
    """
    import buildings as b
    requested=_text(attrs.get('_church_spire'))
    if requested=='none':return None,body,('church_spire_explicitly_omitted',)
    curated_extent=attrs.get('_church_tower_footprint')
    explicit=requested in SPIRE_KINDS or requested=='auto' or curated_extent is not None
    if requested and requested not in (*SPIRE_KINDS,'auto'):
        return None,body,('church_spire_unknown_request_omitted',)
    if not explicit and (current_use!='church' or programme.legacy_seed(spec,'structure','church-spire-presence-v1')>=.28):
        return None,body,()
    if mapped_rise is not None:
        return None,body,('church_spire_omitted_preserve_mapped_roof_height',)
    kind=requested if requested in SPIRE_KINDS else SPIRE_KINDS[
        min(2,int(programme.legacy_seed(spec,'structure','church-spire-kind-v1')*3))]
    tip_height={'square_broach':2.3,'octagonal_needle':2.9,'short_pyramidal':1.35}[kind]
    fitted_body=total-rise-tip_height-1.1
    if not 3.4<=fitted_body<=14:
        return None,body,('church_spire_omitted_height_clearance',)
    centre,u,half_length,half_width=b.oriented_box(np.asarray(footprint.outer))
    v=np.array((-u[1],u[0]))
    reserved_half=min(1.6,max(1.2,math.sqrt(footprint.area)*.055))
    candidates=[centre+u*half_length*s+v*half_width*t for s,t in (
        (.55,.5),(-.55,.5),(.55,-.5),(-.55,-.5),(.55,0),(-.55,0),(0,.5),(0,-.5),(0,0))]
    if curated_extent is not None:
        if not isinstance(curated_extent,Footprint) or not curated_extent.is_rectangle():
            return None,body,('church_spire_omitted_invalid_curated_extent',)
        centre,u,hl,hw=b.oriented_box(np.asarray(curated_extent.outer));v=np.array((-u[1],u[0]))
        reserved_half=min(hl,hw,1.6)
        if reserved_half<.7:return None,body,('church_spire_omitted_narrow_curated_extent',)
        candidates=[centre]
    accepted=None
    shape=footprint.shape()
    for point in candidates:
        proposed=Footprint(tuple(tuple(point+u*s*reserved_half+v*t*reserved_half)
                                for s,t in ((-1,-1),(1,-1),(1,1),(-1,1))))
        occupied=proposed.shape()
        if not shape.covers(occupied) or shape.boundary.distance(occupied)<.3:continue
        if curated_extent is not None and not curated_extent.shape().buffer(1e-7).covers(occupied):continue
        accepted=(point,proposed);break
    if accepted is None:return None,body,('church_spire_omitted_no_solid_roof_reservation',)
    point,reservation=accepted
    spire=ChurchSpire(kind,reservation,tuple(map(float,point)),tuple(map(float,u)),
                      fitted_body,total-tip_height,total)
    reason='church_spire_curated_style' if explicit else 'church_spire_procedural_style_prior'
    return spire,fitted_body,(reason,'church_spire_height_reserved_inside_source_total',
                             'church_spire_not_mapped_tower_evidence')


def layout(spec,gmin,gmax):
    """Fitted bays, reserved actual doorway, and explicit opaque shared walls."""
    import buildings as b
    architecture=spec.church
    resolved=programme.derive(spec)
    floor=resolved.datum(0)
    width,bay,sill,height,columns={
        'church_plain_chapel':(.95,3.4,.85,1.65,2),
        'church_parish_hall':(1.05,3.1,1.0,3.2,1),
        'church_modern_hall':(2.8,4.6,.65,2.2,3)}[architecture.family]
    sill+=floor.bottom
    height=min(height,floor.top-sill-.4)
    trim=b.custom_look(b.PANEL,(.84,.83,.77) if architecture.family=='church_parish_hall' else (.92,.93,.90))
    plinth=b.custom_look(b.PANEL,(.40,.43,.43))
    elevations=[];used=0
    base=b.base_z(spec,gmin,gmax)+(spec.min_h or 0.)
    for run in resolved.runs:
        boundary,edge,length=run.boundary,run.edge,run.length;openings=[]
        if run.party_wall:
            elevations.append(Elevation(boundary,edge,length,(),'party_wall'));continue
        member=run.member(spec.door[0]) if boundary==0 and spec.door else None
        if member is not None:
            z=(spec.access.door_z if spec.access is not None else
               b.door_ground(spec,spec.door[0],spec.door[1],gmax)+(b.STOOP_H if spec.stoop else 0.))-base
            centre=member.start+spec.door[1]
            left,right=centre-.625,centre+.625
            if left>=.45 and right<=length-.45 and z+2.25<=floor.top-.15:
                openings.append(Opening('door',0,left,right,z,z+2.25))
        reserved=tuple((op.left,op.right) for op in openings)
        grid=programme.fit_grid(length,bay,width,margin=.55,reserved=reserved,gap=.35,
                                max_bays=min(16,MAX_OPENINGS-used),mode='fill')
        if height>=.7:
            for module in grid.bays:
                variant=min(2,int(programme.legacy_seed(spec,'vocabulary',('church-pane',boundary,run.edge,module.index))*3))
                openings.append(Opening('church_window',0,module.left,module.right,sill,sill+height,columns,variant))
                used+=1
        elevations.append(Elevation(boundary,edge,length,tuple(openings),architecture.family))
    return FacadeLayout(tuple(elevations),materials.wall_scale(architecture.vocabulary),trim,plinth,trim)


def _profile(op,arched):
    left,right,bottom,top=op.left,op.right,op.bottom,op.top
    if not arched:return ((left,bottom),(right,bottom),(right,top),(left,top))
    radius=(right-left)/2;spring=top-radius;centre=(left+right)/2
    return ((left,bottom),(right,bottom),*tuple((centre+radius*math.cos(i*math.pi/8),
            spring+radius*math.sin(i*math.pi/8)) for i in range(9)))


def _walls(mesh,spec,gmin,gmax,bottom,lite):
    import buildings as b
    planned=layout(spec,gmin,gmax);mats=b._Looks(spec.seed)
    resolved=programme.derive(spec)
    body,trim,plinth=mats[spec.facade],mats[planned.trim],mats[planned.plinth]
    base=b.base_z(spec,gmin,gmax)+(spec.min_h or 0.)
    for elevation in planned.elevations:
        run=resolved.run(elevation.boundary,elevation.edge)
        a,c=np.asarray(run.start),np.asarray(run.end)
        d=(c-a)/elevation.length;outside=np.array((d[1],-d[0]))
        def at(s,z,depth=0.):return (*tuple(a+d*s+outside*depth),base+z)
        def quad(l,r,lo,hi,material,depth=0.):
            if r-l<1e-8 or hi-lo<1e-8:return
            uv=((l/3,lo/3),(r/3,lo/3),(r/3,hi/3),(l/3,hi/3))
            mesh.quad(at(l,lo,depth),at(r,lo,depth),at(r,hi,depth),at(l,hi,depth),*uv,material)
        for left,right,low,high in wall_cells(elevation.length,bottom-base,spec.height,elevation.openings):
            cuts=sorted({low,high,max(low,min(high,.28)),max(low,min(high,spec.height-.14))})
            for z0,z1 in zip(cuts,cuts[1:]):
                mat=plinth if z1<=.28 else trim if z0>=spec.height-.14 else body
                quad(left,right,z0,z1,mat)
        for op in elevation.openings:
            arched=spec.church.family=='church_parish_hall' and op.kind!='door'
            profile=_profile(op,arched)
            glass=(.20,.27,.30) if op.kind=='door' else ((.23,.31,.35),(.28,.34,.30),(.25,.29,.37))[op.variant]
            if spec.church.current_use not in ('church','religious'):glass=(.25,.30,.32)
            pane=mats[b.custom_look(b.PANEL,glass)]
            depth=0. if lite else -.06
            centre=(sum(p[0] for p in profile)/len(profile),sum(p[1] for p in profile)/len(profile))
            for p,q in zip(profile,profile[1:]+profile[:1]):
                mesh.tri(at(*centre,depth),at(*p,depth),at(*q,depth),
                         (0.,0.),(0.,1.),(1.,1.),pane)
                if not lite:
                    mesh.quad(at(*p),at(*q),at(*q,depth),at(*p,depth),
                              (0.,0.),(1.,0.),(1.,.1),(0.,.1),trim)
            if arched:
                arc=profile[2:]
                for p,q in zip(arc,arc[1:]):
                    mesh.quad(at(*q),at(*p),at(p[0],op.top),at(q[0],op.top),
                              (0.,0.),(1.,0.),(1.,1.),(0.,1.),body)
            # The frame stays inside the fitted opening envelope and source XY.
            frame=.045 if lite else .065
            quad(op.left,op.left+frame,op.bottom,op.top,trim)
            quad(op.right-frame,op.right,op.bottom,op.top,trim)
            quad(op.left,op.right,op.bottom,op.bottom+frame,trim)
            if not arched:quad(op.left,op.right,op.top-frame,op.top,trim)
            if not lite or spec.church.family=='church_modern_hall':
                for k in range(1,op.columns):
                    x=op.left+(op.right-op.left)*k/op.columns
                    quad(x-.025,x+.025,op.bottom,op.top,trim)
            if spec.church.family=='church_modern_hall' and op.kind=='door':
                # Flush broad surround; no projected porch or new collision.
                quad(op.left-.18,op.right+.18,op.top+.07,min(spec.height-.18,op.top+.28),trim)


def draw(mesh,spec,gmin,gmax,lite=False,collision=False):
    """Draw an accepted complete church envelope; return False for fallback."""
    import buildings as b
    architecture=getattr(spec,'church',None)
    if architecture is None or not architecture.accepted:return False
    fp=spec.footprint;mats=b._Looks(spec.seed)
    base=b.base_z(spec,gmin,gmax)+(spec.min_h or 0.)
    bottom=gmin-(b.FOUNDATION_M if collision else b.SKIRT_LITE_M if lite else b.SKIRT_M)
    top=base+spec.height
    if collision:
        token=(b.MATERIALS.index(b.PANEL),(128,128,128,255))
        for ring in (fp.outer,*fp.holes):
            for a,c in zip(ring,ring[1:]+ring[:1]):
                mesh.quad((*a,bottom),(*c,bottom),(*c,top),(*a,top),*((0.,0.),)*4,token)
    else:_walls(mesh,spec,gmin,gmax,bottom,lite)
    draw_roof(mesh,spec,top,mats,detail=not lite and not collision)
    if spec.access is not None:
        from .access import draw as draw_access
        draw_access(mesh,spec,collision,detail=not lite)
    return True


def draw_roof(mesh,spec,top,mats,detail=False):
    """Shared exact envelope for visual, collision and skyline material maps."""
    import buildings as b
    fp=spec.footprint
    if spec.roof=='flat':
        from .geometry import horizontal
        horizontal(mesh,fp,top,mats[spec.roof_mat],b.ROOF_UV_M)
    else:
        envelope=roofs.envelope(fp,spec.roof);rise=spec.church.roof_rise
        su,sv=materials.roof_scale(spec.church.roof_material)
        for tri in envelope.triangles:
            mesh.tri(*[(x,y,top+z*rise) for x,y,z in tri],
                     *[(x/su,y/sv) for x,y,z in tri],mats[spec.roof_mat])
        for p,q in envelope.boundary:
            if max(p[2],q[2])<1e-8:continue
            a,c=(*p[:2],top),(*q[:2],top)
            ap,cp=(*p[:2],top+p[2]*rise),(*q[:2],top+q[2]*rise)
            if p[2]<1e-8:mesh.tri(a,c,cp,(0.,0.),(1.,0.),(1.,1.),mats[spec.facade])
            elif q[2]<1e-8:mesh.tri(a,c,ap,(0.,0.),(1.,0.),(0.,1.),mats[spec.facade])
            else:mesh.quad(a,c,cp,ap,(0.,0.),(1.,0.),(1.,1.),(0.,1.),mats[spec.facade])
    if spec.church.spire is not None:
        _draw_spire(mesh,spec,top-spec.height,mats,detail)


def spire_vertex_count(spec):
    """Additional skyline envelope vertices, without allocating mesh geometry."""
    spire=getattr(getattr(spec,'church',None),'spire',None)
    if spire is None:return 0
    return {'square_broach':104,'octagonal_needle':120,'short_pyramidal':60}[spire.kind]


def _draw_spire(mesh,spec,base,mats,detail):
    import buildings as b
    spire=spec.church.spire
    centre=np.asarray(spire.centre);u=np.asarray(spire.direction);v=np.array((-u[1],u[0]))
    half=math.dist(spire.footprint.outer[0],spire.footprint.outer[1])/2
    sides=8 if spire.kind=='octagonal_needle' else 4
    square=((-1.,-1.),(1.,-1.),(1.,1.),(-1.,1.))
    octagon=tuple((math.cos(-3*math.pi/4+i*math.pi/4),math.sin(-3*math.pi/4+i*math.pi/4)) for i in range(8))
    outline=octagon if sides==8 else square
    def ring(points,radius,z):
        return [(*tuple(centre+u*x*half*radius+v*y*half*radius),base+z) for x,y in points]
    wall,roof=mats[spec.facade],mats[spec.roof_mat]
    uv=((0.,0.),(1.,0.),(1.,1.),(0.,1.))
    levels=((spire.base_height,.78),(spire.shoulder_height-.16,.78),
            (spire.shoulder_height-.16,1.),(spire.shoulder_height,1.))
    for (z0,r0),(z1,r1) in zip(levels,levels[1:]):
        lower,upper=ring(outline,r0,z0),ring(outline,r1,z1)
        for i in range(sides):
            j=(i+1)%sides
            mesh.quad(lower[i],lower[j],upper[j],upper[i],*uv,wall)
    if spire.kind=='square_broach':
        square_eight=((-1.,-1.),(0.,-1.),(1.,-1.),(1.,0.),(1.,1.),(0.,1.),(-1.,1.),(-1.,0.))
        shoulder=ring(square_eight,1.,spire.shoulder_height)
        neck=ring(octagon,.68,spire.shoulder_height+(spire.top_height-spire.shoulder_height)*.2)
        for i in range(8):
            j=(i+1)%8
            mesh.quad(shoulder[i],shoulder[j],neck[j],neck[i],*uv,roof)
        points=neck
    else:points=ring(outline,1.,spire.shoulder_height)
    apex=(*spire.centre,base+spire.top_height)
    for p,q in zip(points,points[1:]+points[:1]):mesh.tri(p,q,apex,(0.,0.),(1.,0.),(.5,1.),roof)
    if detail:
        # Closed dark belfry panels and six fitted louver slats per face. All
        # detail stays well inside the reserved cornice footprint; no new symbol.
        dark=mats[b.custom_look(b.PANEL,(.13,.18,.19))]
        light=mats[b.custom_look(b.PANEL,(.64,.65,.61))]
        shaft=ring(outline,.78,0.)
        for a,c in zip(shaft,shaft[1:]+shaft[:1]):
            a,c=np.asarray(a[:2]),np.asarray(c[:2]);delta=c-a;length=float(np.linalg.norm(delta))
            direction=delta/length;outside=np.array((direction[1],-direction[0]))
            margin=min(.16,length*.22)
            def pane(z0,z1,depth,material):
                left=a+direction*margin+outside*depth;right=c-direction*margin+outside*depth
                mesh.quad((*left,base+z0),(*right,base+z0),(*right,base+z1),(*left,base+z1),*uv,material)
            low,high=spire.shoulder_height-.87,spire.shoulder_height-.26
            pane(low,high,.006,dark)
            for i in range(6):
                z=low+(high-low)*(i+.45)/6
                pane(z,z+.035,.012,light)
