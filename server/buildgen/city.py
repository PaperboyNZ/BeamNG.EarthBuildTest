"""Bounded city compositions derived from source envelopes and regional prose.

No imports of the existing regional style/roof/opening profiles. Repeated facade
runs retain coverage at every storey without storing a per-window Opening graph.
Physical access, roofs and collision remain owned by the existing generators.
"""
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path

from . import materials, programme

PATH = Path(__file__).with_name('catalog')/'city_regions.json'
MAX_RUNS = 64
MAX_COLUMNS = 48
MAX_PANES = 2048
MAX_DETAILS = 96


@lru_cache(maxsize=1)
def catalogue():
    data = json.loads(PATH.read_text(encoding='utf-8'))
    if data.get('schema') != 1 or len(data['regions']) != 64:
        raise ValueError('Invalid city descriptive catalogue')
    return data['regions']


@lru_cache(maxsize=1)
def identity():
    return hashlib.sha256(PATH.read_bytes()).hexdigest()


def candidate(resolution, cls):
    """First slice: closed flat-roof tall offices and actual multi-storey hotels.

    The height guard avoids low-building regional roof inference. Motel/hostel,
    generic commercial, specialist and unsupported pitched sources stay intact.
    """
    return bool(resolution and resolution.roof.value == 'flat'
                and resolution.body_height > 15.
                and ((cls == 'office' and 13 <= resolution.floors.value <= 120)
                     or (cls == 'hotel' and 5 <= resolution.floors.value <= 120)))


@dataclass(frozen=True, slots=True)
class Region:
    id: str
    source_digest: str
    cues: tuple[str, ...]
    status: str = 'text_based_proposal'

    def __post_init__(self):
        object.__setattr__(self, 'cues', tuple(self.cues))
        if any(type(value) is not str for value in (self.id,self.source_digest,self.status,*self.cues)):
            raise ValueError('City region values must be detached strings')


@dataclass(frozen=True, slots=True)
class Run:
    index: int
    columns: int
    margin: float
    pitch: float
    window_width: float


@dataclass(frozen=True, slots=True)
class Architecture:
    family: str
    region: Region
    expression: str
    programme: programme.Programme
    runs: tuple[Run, ...]
    mode: str
    glass: tuple[float, float, float]
    frame: tuple[float, float, float]
    spandrel: tuple[float, float, float]
    diagnostics: tuple[str, ...]
    version: int = 1

    def __post_init__(self):
        for name in ('runs','glass','frame','spandrel','diagnostics'):
            object.__setattr__(self,name,tuple(getattr(self,name)))
        if (not isinstance(self.region,Region) or not isinstance(self.programme,programme.Programme)
                or len(self.runs)>MAX_RUNS or len(self.runs)!=len(self.programme.runs)
                or not all(isinstance(run,Run) for run in self.runs)
                or self.mode not in ('modules','bands')):
            raise ValueError('Invalid bounded city architecture')
        for colour in (self.glass,self.frame,self.spandrel):
            if len(colour)!=3 or not all(math.isfinite(v) and 0<=v<=1 for v in colour):
                raise ValueError('City colour must be a finite RGB triple')


def plan(spec, party_walls=()):
    if (not candidate(spec.inference, spec.cls) or spec.footprint is None or
            spec.deck or spec.plain or spec.windows is False or spec.church or spec.terminal):
        return None
    try:
        shared = programme.derive(spec, party_walls=party_walls)
    except ValueError:
        return None
    if len(shared.runs) > MAX_RUNS:
        return None
    material = spec.inference.facade.value
    hotel = spec.cls == 'hotel'
    family = ('hotel_masonry' if material in ('brick', 'stone') else 'hotel_contemporary') if hotel else (
        'office_curtain' if material == 'glass' else
        'office_panel' if material in ('concrete', 'metal') else 'office_masonry')
    region_id = spec.inference.selection.environment.region
    text = catalogue().get(region_id)
    cues = tuple(text['cues']) if text and text['city_applicable'] else ()
    region = Region(region_id, text['source_digest'] if text else '', cues,
                    'text_based_proposal' if text and text['city_applicable'] else 'neutral_fallback')
    expression = 'local' if shared.seed('vocabulary', 'city-expression-v1') > .55 else 'restrained'
    # These are new city fitting defaults, not residential profile dimensions.
    nominal = 3.5 if hotel else 4.2 if family == 'office_panel' else 3.6
    nominal *= .94 + .12*shared.seed('structure', 'city-bay-v1')
    ratio = .92 if family == 'office_curtain' else .85 if family == 'office_panel' else .54 if hotel else .61
    if expression == 'local' and 'recess' in cues:
        ratio = max(.45, ratio-.06)
    runs = []
    count = 0
    for run in shared.runs:
        available = max(0., run.length-1.2)
        columns = max(0, int(available/nominal))
        pitch = available/columns if columns else nominal
        runs.append(Run(run.index, columns, .6, pitch, pitch*ratio))
        if not run.party_wall:
            count += columns*len(shared.datums)
    # Full textured rows replace pane detail on oversized sources; no blank
    # upper floors, stretched bays or truncated mapped members to satisfy a cap.
    mode = 'bands' if count > MAX_PANES or any(r.columns > MAX_COLUMNS for r in runs) else 'modules'
    glass = materials.choose(spec.seed, 'city-glass-v1', (
        ((.78, .86, .91), 3), ((.70, .82, .84), 2), ((.83, .81, .76), 1)))
    frame = (.26, .29, .30) if expression == 'restrained' else (.57, .59, .59)
    spandrel = (.54, .57, .59) if family == 'office_curtain' else (.71, .71, .68)
    notes = ('city_family:'+family, 'city_region:'+region_id,
             'city_region_basis:descriptive_text', 'city_era:unknown', 'city_facade_mode:'+mode)
    return Architecture(family, region, expression, shared, tuple(runs), mode,
                        glass, frame, spandrel, notes)


def layout(spec, gmin, gmax):
    """Only physical entry reservations are explicit; upper rows stay compact."""
    import buildings as b
    from .facades import FacadeLayout, Elevation, Opening, DOOR_WIDTH, DOOR_HEIGHT
    arch = spec.city
    base = b.base_z(spec, gmin, gmax)+(spec.min_h or 0.)
    elevations = []
    for run in arch.programme.runs:
        ops = ()
        member = run.member(spec.door[0]) if spec.door and run.boundary == 0 else None
        if member is not None and not run.party_wall:
            z = spec.access.door_z-base if spec.access else (
                b.door_ground(spec, spec.door[0], spec.door[1], gmax)-base if spec.stoop else gmax-base)
            if spec.access is None and spec.stoop:
                z += b.STOOP_H
            anchor = member.start+spec.door[1]
            ops = (Opening('door', 0, anchor-DOOR_WIDTH/2, anchor+DOOR_WIDTH/2, z, z+DOOR_HEIGHT),)
        elevations.append(Elevation(run.boundary, run.edge, run.length, ops, 'city_'+arch.family))
    return FacadeLayout(tuple(elevations), materials.wall_scale(spec.inference.facade.value),
                        b.custom_look(b.PANEL, arch.frame), b.custom_look(b.PANEL, (.51,.52,.51)),
                        b.SHUTTER, arch.diagnostics)


def refit(spec, previous):
    """Rebuild shape-bound runs after street/sidewalk clipping.

    Retain party labels only on surviving parts of their original wall segments;
    newly cut road-facing edges are not inherited party walls by array index.
    """
    if previous is None:
        return None
    blocked = []
    for boundary,ring in enumerate((spec.footprint.outer,*spec.footprint.holes)):
        for edge,(a,c) in enumerate(zip(ring,ring[1:]+ring[:1])):
            for old in previous.programme.runs:
                if not old.party_wall:
                    continue
                dx,dy = old.end[0]-old.start[0],old.end[1]-old.start[1]
                def on(point):
                    x,y = point[0]-old.start[0],point[1]-old.start[1]
                    t = (x*dx+y*dy)/(old.length*old.length)
                    return abs(x*dy-y*dx)/old.length < 1e-7 and -1e-8 <= t <= 1.+1e-8
                if on(a) and on(c):
                    blocked.append((boundary,edge))
                    break
    return plan(spec,tuple(blocked))


def draw(mesh, spec, gmin, gmax, bottom, lite=False):
    """Compose source walls as complete row bands/piers and separate glass.

    Near has bounded shallow reveals on low rows; lite retains matching pane
    positions and major materials. All surfaces stay at/inside the source wall.
    """
    import buildings as b
    from .facades import wall_cells
    # Each pane in a row clips against identical accepted door reservations.
    # Reuse that sweep within this building; never retain plans globally.
    arch = spec.city
    layout_ = spec.facades or layout(spec, gmin, gmax)
    elevations = {(e.boundary,e.edge):e for e in layout_.elevations}
    base = b.base_z(spec,gmin,gmax)+(spec.min_h or 0.)
    mats = b._Looks(spec.seed)
    frame = mats[layout_.trim]
    body = mats[spec.facade] if spec.inference.facade.value != 'glass' else mats[b.custom_look(b.PANEL, arch.spandrel)]
    glass = mats[spec.facade] if spec.inference.facade.value == 'glass' else mats[b.custom_look(b.OFFICE, arch.glass)]
    detail_budget = MAX_DETAILS
    hotel = arch.family.startswith('hotel')
    ribbon = arch.family in ('office_curtain', 'office_panel')
    for desc, run in zip(arch.runs, arch.programme.runs):
        elevation = elevations[(run.boundary,run.edge)]
        ax,ay = run.start
        dx,dy = ((run.end[0]-ax)/run.length, (run.end[1]-ay)/run.length)
        def at(s,z,depth=0.):
            return (ax+dx*s+dy*depth,ay+dy*s-dx*depth,base+z)
        def quad(l,r,lo,hi,mat,depth=0.,uv=None):
            if r-l <= 1e-8 or hi-lo <= 1e-8:
                return
            su,sv = layout_.wall_scale
            coords = uv or ((l/su,lo/sv),(r/su,lo/sv),(r/su,hi/sv),(l/su,hi/sv))
            mesh.quad(at(l,lo,depth),at(r,lo,depth),at(r,hi,depth),at(l,hi,depth),*coords,mat)
        if run.party_wall or desc.columns == 0:
            quad(0.,run.length,bottom-base,spec.height,body)
            continue
        # Source skirt and corner closure are always present.
        quad(0.,run.length,bottom-base,0.,mats[layout_.plinth])
        left,right = desc.margin,run.length-desc.margin
        quad(0.,left,0.,spec.height,body)
        quad(right,run.length,0.,spec.height,body)
        if lite:
            # Opaque shared backing replaces per-row wall fragments. Pane rows,
            # pier masks and floor bands retain their exact architectural grid;
            # a few millimetres of ordering avoids coplanar depth fighting.
            quad(left,right,0.,spec.height,body)
        for datum in arch.programme.datums:
            z0,z1 = datum.bottom,datum.top
            sill = .22 if arch.family == 'office_curtain' else .80 if hotel else .85
            head = .28 if arch.family == 'office_curtain' else .55
            lo,hi = z0+min(sill,datum.height*.28),z1-min(head,datum.height*.22)
            if datum.index == 0:
                lo = z0+.18
                hi = z1-.35
            # One row is fitted around the accepted door, including raised
            # thresholds extending past the first nominal floor datum.
            reserved = tuple(op for op in elevation.openings if op.bottom < z1 and op.top > z0)
            pane_cells = tuple(wall_cells(run.length,lo,hi,reserved))
            if not lite:
                for l,r,a,c in wall_cells(run.length,z0,lo,reserved):
                    quad(max(left,l),min(right,r),a,c,body)
                for l,r,a,c in wall_cells(run.length,hi,z1,reserved):
                    quad(max(left,l),min(right,r),a,c,body)
            if arch.mode == 'bands' or lite:
                spans = ((left,right),)
            else:
                spans = tuple((left+(i+.5)*desc.pitch-desc.window_width/2,
                               left+(i+.5)*desc.pitch+desc.window_width/2) for i in range(desc.columns))
            cursor = left
            for l,r in spans:
                if not lite:
                    for a,c,low,high in pane_cells:
                        quad(max(cursor,a),min(l,c),low,high,body)
                # Door reservation clips each pane, never its physical route.
                for a,c,low,high in pane_cells:
                    a,c = max(l,a),min(r,c)
                    if c-a <= 1e-8:
                        continue
                    # Stock office atlas band; whole modules repeat horizontally.
                    repeats = max(1.,(c-a)/max(desc.pitch,1.))/5.
                    uv = ((.003,.753),(.003+repeats,.753),(.003+repeats,.997),(.003,.997))
                    depth = .002 if lite else -.07 if datum.index < 2 and detail_budget >= 4 else 0.
                    quad(a,c,low,high,glass,depth,uv)
                    if (not lite and arch.expression == 'local' and 'screen' in arch.region.cues
                            and datum.index < 3 and detail_budget > (4 if depth else 0) and c-a > 1.):
                        centre = (a+c)/2
                        quad(centre-.035,centre+.035,low,high,frame,.002)
                        detail_budget -= 1
                    if depth and not lite:
                        corners = ((a,low),(c,low),(c,high),(a,high))
                        for p,q in zip(corners,corners[1:]+corners[:1]):
                            mesh.quad(at(*p),at(*q),at(*q,depth),at(*p,depth),
                                      (0.,0.),(1.,0.),(1.,1.),(0.,1.),frame)
                        detail_budget -= 4
                cursor = r
            if not lite:
                for a,c,low,high in pane_cells:
                    quad(max(cursor,a),min(right,c),low,high,body)
            # Floor division occupies solid wall, no collision projection.
            band = .12 if ribbon else .07
            if arch.expression == 'local' and 'horizontal' in arch.region.cues:
                band = min(.22,head*.6)
            for a,c,low,high in wall_cells(run.length,z1-band,z1,reserved):
                quad(max(left,a),min(right,c),low,high,frame,.004 if lite else .002)
        if lite and arch.mode == 'modules':
            # Full-height pier masks preserve the exact near aperture widths
            # with O(columns + floors) quads rather than O(columns * floors).
            cursor = left
            pier_cells=tuple(wall_cells(run.length,0.,spec.height,elevation.openings))
            for i in range(desc.columns):
                l = left+(i+.5)*desc.pitch-desc.window_width/2
                r = l+desc.window_width
                for a,c,low,high in pier_cells:
                    quad(max(cursor,a),min(l,c),low,high,body,.003)
                cursor = r
            for a,c,low,high in pier_cells:
                quad(max(cursor,a),min(right,c),low,high,body,.003)
        # Closed backing preserves the opaque shell behind the existing door
        # prop, including its frame clearance, in both representations.
        for op in elevation.openings:
            quad(op.left,op.right,op.bottom,op.top,frame,.002)
        # Roof termination stays below the mapped height, including its collision.
        quad(0.,run.length,spec.height-.16,spec.height,frame,.002)


def landscape_tint(spec, default):
    """Only colour of already accepted paving; never move paths, beds or plants."""
    arch = getattr(spec, 'city', None)
    if arch is None:
        return default
    if arch.family in ('office_masonry', 'hotel_masonry'):
        return (.73,.71,.66)
    return (.68,.70,.70)
