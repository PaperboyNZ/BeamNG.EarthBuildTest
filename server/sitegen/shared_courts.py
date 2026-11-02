"""Runtime boundary for explicit canonical courts and interface-led shared sites.

Interface-free courts keep their single-sector contract. Observed-interface
plans use the bounded shared-layout solver and canonical contact fragments.
Property ownership and membership always come from the supplied source records.
"""
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import logging
import math
import os
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

from buildgen.topology import Footprint, triangles
from .identity import canonical_json
from .plan import SiteGraph, SitePlan

MAX_BYTES = 1 << 20
MAX_SITES = 128
MAX_TILE_SITES = 8
MAX_RESOURCES = 8
MAX_MEMBERS = 32
MAX_VERTICES = 128
MAX_POINTS = 1024
MAX_TILE_POINTS = 2048
SPACING = 2.
MAX_GRADE = .05
MAX_FILL = .15
BUILDING_NAMESPACE = 'beamng-earth/source-building-id'


@dataclass(frozen=True, slots=True)
class FittedCourt:
    plan: SitePlan
    plane: tuple
    bottom: float
    terrain_points: int

    def __post_init__(self):
        if type(self.plan) is not SitePlan:
            raise TypeError('court requires immutable source records')
        plane = tuple(self.plane)
        if (len(plane) != 3 or any(type(v) not in (int, float) or not math.isfinite(v) for v in plane)
                or np.linalg.norm(plane[:2]) > MAX_GRADE
                or type(self.bottom) not in (int, float) or not math.isfinite(self.bottom) or type(self.terrain_points) is not int
                or not 3 <= self.terrain_points <= MAX_POINTS):
            raise ValueError('invalid accepted court dimensions')
        object.__setattr__(self, 'plane', tuple(map(float, plane)))
        object.__setattr__(self, 'bottom', float(self.bottom))
        if reason(self.plan) is not None:
            raise ValueError('unsupported accepted court contract')

    @property
    def revision(self):
        return hashlib.sha256(canonical_json(dict(plan=self.plan.to_dict(), plane=self.plane,
            bottom=self.bottom, terrain_points=self.terrain_points)).encode()).hexdigest()


def reason(plan):
    """Capability check; a declaration is not a fitted physical surface."""
    if plan.interfaces:
        from .shared_layouts import capability
        return capability(plan)
    e = plan.evidence
    if e.frame.kind != 'canonical_enu': return 'shared_court_requires_canonical_frame'
    if abs(e.frame.frame.latitude_e7) > 850_000_000: return 'shared_court_unsupported_latitude'
    if e.exclusions is None: return 'shared_court_unknown_exclusions'
    if e.association_extent is None: return 'shared_court_missing_association'
    if not e.memberships: return 'shared_court_missing_members'
    if len(e.memberships) > MAX_MEMBERS: return 'shared_court_membership_budget'
    if any(m.member.kind not in ('building', 'lot') or m.interval is not None for m in e.memberships):
        return 'shared_court_unsupported_membership'
    if any(m.member.kind == 'building' and m.member.identity.namespace != BUILDING_NAMESPACE for m in e.memberships):
        return 'shared_court_unsupported_building_identity'
    if not 1 <= len(plan.resources) <= MAX_RESOURCES: return 'shared_court_resource_budget'
    if (len(e.physical_extents) != len(plan.resources)
            or {r.identity for r in plan.resources} != {p.identity for p in e.physical_extents}):
        return 'shared_court_resource_extent_mismatch'
    members = {m.member for m in e.memberships}
    if any(r.kind != 'shared_circulation' or r.producer != e.ref or not r.consumers or len(r.consumers) > MAX_MEMBERS
           or not set(r.consumers) <= members for r in plan.resources):
        return 'shared_court_unsupported_resource'
    if plan.interfaces: return 'shared_court_interfaces_require_shared_solver'
    polygons = (e.association_extent, *e.exclusions, *(p.boundary for p in e.physical_extents))
    if sum(len(p.outer)+sum(map(len, p.holes)) for p in polygons) > MAX_VERTICES:
        return 'shared_court_vertex_budget'
    if any(abs(v) > 2048. for p in polygons for ring in (p.outer, *p.holes) for xy in ring for v in xy):
        return 'shared_court_spatial_budget'
    if any(p.interval is None or p.interval.basis != 'ellipsoidal_height'
           or p.interval.maximum-p.interval.minimum > 4. for p in e.physical_extents):
        return 'shared_court_requires_measured_ground_heights'
    return None


def shape(p):
    return Polygon(p.outer, p.holes)


def host(plan):
    """One complete source association, one closed sector; never centroid clipping."""
    import geotiles
    e = plan.evidence
    if e.frame.kind != 'canonical_enu' or e.association_extent is None: return None
    frame = e.frame.frame
    vertices = (*e.association_extent.outer,
                *(p for h in e.association_extent.holes for p in h))
    owners = set()
    for x, y in vertices:
        lon, lat, _ = frame.enu_to_geodetic(x, y, 0.)
        owners.add(geotiles.tile_of(lat, lon))
        if len(owners) != 1: return None
    owner = next(iter(owners))
    # A conservative interior avoids bowed geographic cell edges and near-edge
    # ground/height projection uncertainty. No arbitrary tile fragment owns it.
    tile = geotiles.geobox(*owner)
    points = project_points([(x, y, 0.) for x, y in vertices], _frame(plan), tile.frame)
    x0, y0, x1, y1 = tile.inner
    if not (np.all(points[:, 0] > x0+.5) and np.all(points[:, 0] < x1-.5)
            and np.all(points[:, 1] > y0+.5) and np.all(points[:, 1] < y1-.5)):
        return None
    return owner


@lru_cache(maxsize=1)
def catalogue():
    path = os.environ.get('BNE_SHARED_SITE_RECORDS')
    if not path: return 'none', (), ()
    source = Path(path)
    if source.stat().st_size > MAX_BYTES: raise ValueError('shared site catalogue exceeds byte budget')
    with source.open('rb') as stream: raw = stream.read(MAX_BYTES+1)
    if len(raw) > MAX_BYTES: raise ValueError('shared site catalogue exceeds byte budget')
    value = json.loads(raw)
    # Bound site count before constructing/validating all detached polygons.
    root = value.get('record', {}) if isinstance(value, dict) else {}
    if not isinstance(root, dict): raise ValueError('shared site catalogue requires a SiteGraph envelope')
    sites = root.get('value', {}).get('sites') if isinstance(root, dict) and isinstance(root.get('value'), dict) else None
    if root.get('type') != 'SiteGraph' or not isinstance(sites, list) or len(sites) > MAX_SITES:
        raise ValueError('shared site catalogue requires a bounded SiteGraph')
    graph = SiteGraph.from_dict(value)
    accepted, diagnostics = [], []
    for plan in graph.sites:
        why = reason(plan)
        if plan.interfaces and not why:
            from .shared_layouts import sectors
            owners=sectors(plan)
            if not owners:why='shared_layout_sector_budget'
            else:
                accepted.extend((owner,plan) for owner in owners)
                continue
        owner = None if why else host(plan)
        if not why and owner is None: why = 'shared_court_cross_sector_requires_retention'
        if why: diagnostics.append((plan.evidence.identity, why))
        else: accepted.append((owner, plan))
    if diagnostics:
        from collections import Counter
        logging.getLogger(__name__).warning('Unsupported shared court records: %s', dict(Counter(why for _,why in diagnostics)))
    return hashlib.sha256(raw).hexdigest(), tuple(accepted), tuple(diagnostics)


def _samples(p):
    """Full polygon grid and dense boundary; reject oversized work before allocation."""
    polygon = shape(p)
    x0, y0, x1, y1 = polygon.bounds
    nx, ny = max(1, math.ceil((x1-x0)/SPACING)), max(1, math.ceil((y1-y0)/SPACING))
    if (nx+1)*(ny+1) > MAX_POINTS: return None
    points = set()
    for ring in (p.outer, *p.holes):
        for a, b in zip(ring, ring[1:]+ring[:1]):
            n = max(1, math.ceil(math.dist(a, b)/SPACING))
            if n+len(points) > MAX_POINTS: return None
            for t in np.linspace(0., 1., n+1):
                points.add(tuple(np.asarray(a)*(1-t)+np.asarray(b)*t))
    for x in np.linspace(x0, x1, nx+1):
        for y in np.linspace(y0, y1, ny+1):
            if polygon.covers(Point(x, y)): points.add((float(x), float(y)))
    if len(points) > MAX_POINTS: return None
    return tuple(sorted(points))


def fit(plan, elev, *, obstacles=(), point_budget=MAX_POINTS):
    """Fit a common plane to measured ground, atomically for all site resources.

    elev accepts WGS84 latitude/longitude arrays and returns ellipsoidal heights.
    Obstacles are complete physical polygons in the canonical site's XY frame.
    The sampling envelope is authored gameplay capability, not a design standard.
    """
    why = reason(plan)
    if why: return None, why
    if elev is None: return None, 'shared_court_missing_terrain'
    if type(point_budget) is not int or not 0 <= point_budget <= MAX_TILE_POINTS:
        raise ValueError('invalid shared court terrain budget')
    e = plan.evidence
    boundary = shape(e.association_extent)
    extents = tuple(e.physical_extents)
    surfaces = [shape(p.boundary) for p in extents]
    exclusions = [shape(p) for p in e.exclusions]
    if any(not boundary.covers(p) for p in surfaces): return None, 'shared_court_outside_association'
    if any(a.intersection(b).area > 1e-7 for i, a in enumerate(surfaces) for b in surfaces[i+1:]):
        return None, 'shared_court_duplicate_physical_owner'
    if any(a.intersection(b).area > 1e-7 for a in surfaces for b in (*exclusions, *obstacles)):
        return None, 'shared_court_physical_conflict'
    groups = [_samples(p.boundary) for p in extents]
    if any(p is None for p in groups): return None, 'shared_court_terrain_budget'
    points = sorted({p for group in groups for p in group})
    if len(points) > min(point_budget, MAX_POINTS): return None, 'shared_court_terrain_budget'
    import geodesy
    descriptor = e.frame.frame.as_geographic_frame()
    frame = geodesy.EnuFrame(descriptor.latitude, descriptor.longitude, descriptor.height)
    xy = np.asarray(points, float)
    lat, lon, _ = frame.enu_to_geodetic(xy[:, 0], xy[:, 1], np.zeros(len(xy)))
    try:
        heights = np.asarray(elev(lat, lon), float).reshape(-1)
        if len(heights) != len(xy) or not np.isfinite(heights).all():
            return None, 'shared_court_missing_terrain'
    except (OSError, ValueError, TypeError):
        return None, 'shared_court_missing_terrain'
    index = {p: i for i, p in enumerate(points)}
    for extent, group in zip(extents, groups):
        h = heights[[index[p] for p in group]]
        if h.min() < extent.interval.minimum-.02 or h.max() > extent.interval.maximum+.02:
            return None, 'shared_court_ground_height_conflict'
    z = frame.geodetic_to_enu(lat, lon, heights)[2]
    matrix = np.c_[xy, np.ones(len(xy))]
    plane, _, rank, _ = np.linalg.lstsq(matrix, z, rcond=None)
    if rank != 3 or np.linalg.norm(plane[:2]) > MAX_GRADE:
        return None, 'shared_court_grade'
    plane[2] += .03+float(np.max(z-matrix@plane))
    fill = matrix@plane-z
    if fill.max() > MAX_FILL or fill.min() < .029999:
        return None, 'shared_court_grading'
    return FittedCourt(plan, tuple(map(float, plane)), float(z.min()-.1), len(points)), None


def _frame(plan):
    import geodesy
    f = plan.evidence.frame.frame.as_geographic_frame()
    return geodesy.EnuFrame(f.latitude, f.longitude, f.height)


def project_points(points, source, target, origin=(0., 0., 0.)):
    p = np.asarray(points, float)
    lat, lon, h = source.enu_to_geodetic(p[:, 0], p[:, 1], p[:, 2])
    return np.column_stack(target.geodetic_to_enu(lat, lon, h))-np.asarray(origin)


def compile(courts, target, origin=(0., 0., 0.)):
    """Closed court meshes, using the same accepted plane for visual and contact."""
    from . import shared_layouts
    layouts=[c for c in courts if isinstance(c,shared_layouts.SharedLayout)]
    if layouts:
        result=compile(tuple(c for c in courts if not isinstance(c,shared_layouts.SharedLayout)),target,origin)
        for layout in layouts:result=combine(result,shared_layouts.compile(layout,target,origin))
        return result
    import roadmesh
    P, T, UV = [], [], []
    for court in courts:
        source = _frame(court.plan)
        def emit(points):
            i = len(P)
            P.extend(project_points(points, source, target, origin))
            UV.extend((x/4., y/4.) for x, y, _ in points)
            T.append((i, i+1, i+2))
        def top(x, y):
            a, b, c = court.plane
            return (x, y, a*x+b*y+c)
        for extent in court.plan.evidence.physical_extents:
            polygon = extent.boundary
            for tri in triangles(Footprint(polygon.outer, polygon.holes)):
                emit([top(x, y) for x, y in tri])
                emit([(x, y, court.bottom) for x, y in tri[::-1]])
            for ring in (polygon.outer, *polygon.holes):
                for a, b in zip(ring, ring[1:]+ring[:1]):
                    A, B = top(*a), top(*b)
                    lo_a, lo_b = (*a, court.bottom), (*b, court.bottom)
                    emit([lo_a, lo_b, B]); emit([lo_a, B, A])
    if not P: return None
    return np.asarray(P), np.asarray(T, np.int64), np.asarray(UV), [roadmesh.DECK_SIDE], np.zeros(len(T), np.int64)


def combine(a, b):
    if a is None: return b
    if b is None: return a
    return (np.concatenate((a[0], b[0])), np.concatenate((a[1], b[1]+len(a[0]))),
            np.concatenate((a[2], b[2])), [*a[3], *b[3]], np.concatenate((a[4], b[4]+len(a[3]))))


def build_tile(tile, frame, elev, *, items=(), obstacles=(), origin=(0., 0., 0.)):
    """Fit complete source sites; emit only their canonically owned contact."""
    import inputwatch
    path = os.environ.get('BNE_SHARED_SITE_RECORDS')
    if path: inputwatch.paths((path,))
    if not hasattr(tile, 'key'): return (), ()
    digest, entries, _ = catalogue()
    if path:
        with Path(path).open('rb') as stream: current = stream.read(MAX_BYTES+1)
        if len(current) > MAX_BYTES or hashlib.sha256(current).hexdigest() != digest:
            # Configuration is pinned into the process's generator identity.
            # A changed/deleted catalogue fails the new build, preserving any
            # accepted resident physics, until restart chooses the new identity.
            raise RuntimeError('Shared site catalogue changed; restart the server before rebuilding')
    selected = [plan for owner, plan in entries if tile.key == f'g17_{owner[0]}_{owner[1]}']
    if len(selected) > MAX_TILE_SITES: raise RuntimeError('shared_court_tile_budget')
    # Stable ordering makes conflict outcomes independent of record/source order.
    selected.sort(key=lambda p: (p.evidence.identity.namespace, p.evidence.identity.feature_id))
    accepted, notes = [], []
    from . import shared_layouts
    remaining = shared_layouts.MAX_PROBES if any(p.interfaces for p in selected) else MAX_TILE_POINTS
    for plan in selected:
        source = _frame(plan)
        physical = []
        # Host-frame physical masks carry their complete height intervals. Use a
        # conservative swept outline; a projected box cannot license free ground.
        for record in obstacles:
            ring = record['rings'][0]
            projections = []
            for z in (record['min_z'], record['max_z']):
                xyz = [(x, y, z) for x, y in ring]
                projections.append(Polygon(project_points(xyz, frame, source)[:, :2]))
            physical.append(unary_union(projections).convex_hull)
        member_shapes = {}
        for spec, _, _ in items or ():
            fp = getattr(spec, 'footprint', None)
            if fp is None:
                # An older/specialist solid without a detached footprint still
                # blocks its whole ring. Unknown holes never license pavement.
                try: fp = Footprint(spec.ring)
                except (AttributeError, ValueError, TypeError) as exc:
                    raise RuntimeError('shared_court_unknown_building_obstacle') from exc
            def ring(values):
                return project_points([(x+origin[0], y+origin[1], 0.) for x, y in values], frame, source)[:, :2]
            poly = Polygon(ring(fp.outer), [ring(h) for h in fp.holes])
            physical.append(poly)
            evidence = getattr(spec, 'evidence', None)
            if evidence is not None and evidence.source_id:
                member_shapes.setdefault(evidence.source_id, []).append(poly)
            # Soft landscaping is also reserved; a late optional court cannot
            # pave over the accepted garden/path programme of a member building.
            for solid in getattr(getattr(spec, 'access', None), 'landscape', ()):
                xyz = [(x+origin[0], y+origin[1], z) for x, y, z in solid.top]
                physical.append(Polygon(project_points(xyz, frame, source)[:, :2]))
        if plan.interfaces:
            # Fit the complete source plan identically in every participating
            # sector. Local obstacles can reject a proposal, never change its
            # geometry or create a different height solution on the other side.
            layout,why=shared_layouts.fit(plan,elev,point_budget=remaining)
            if layout is None:
                notes.append(why);continue
            fragment=shared_layouts.partition(layout,tile.gx,tile.gy)
            surfaces=unary_union([Polygon(np.asarray(s.top)[:,:2]) for s in fragment.surfaces])
            if any(surfaces.intersection(p).area>1e-5 for p in physical):
                notes.append('shared_layout_existing_physical_conflict');continue
            for old in accepted:
                _,_,old_masks=metadata((old,),source)
                if any(surfaces.intersection(Polygon(m['rings'][0],m['rings'][1:])).area>1e-5 for m in old_masks):
                    notes.append('shared_layout_duplicate_physical_owner');break
            else:
                accepted.append(fragment);remaining-=layout.terrain_points
            continue
        boundary = shape(plan.evidence.association_extent).buffer(.001)
        if any(m.member.kind == 'building' and (m.member.identity.feature_id not in member_shapes or
               not boundary.covers(unary_union(member_shapes[m.member.identity.feature_id]))) for m in plan.evidence.memberships):
            notes.append('shared_court_unresolved_member'); continue
        # Previously accepted sites retain their actual plane heights during
        # projection; lower-priority sites cannot claim the same ground.
        for old in accepted:
            if isinstance(old,shared_layouts.SharedLayout):
                _,_,old_masks=metadata((old,),source)
                physical.extend(Polygon(m['rings'][0],m['rings'][1:]) for m in old_masks)
                continue
            for extent in old.plan.evidence.physical_extents:
                p = extent.boundary
                xyz = [(x, y, old.plane[0]*x+old.plane[1]*y+old.plane[2]) for x, y in p.outer]
                physical.append(Polygon(project_points(xyz, _frame(old.plan), source)[:, :2]))
        court, why = fit(plan, elev, obstacles=physical, point_budget=min(remaining,MAX_TILE_POINTS))
        if court is None: notes.append(why)
        else:
            accepted.append(court); remaining -= court.terrain_points
    if notes:
        # Opted-in, supported records declare physical resources. Omission is
        # not an acceptable replacement for a previously resident court. Fail
        # the whole proposed content, leaving M2's accepted state in place.
        raise RuntimeError('shared_court_unresolved: '+','.join(sorted(set(notes))))
    return tuple(accepted), ()


def extend_masks(existing, masks, bounds):
    """Keep the existing vegetation exclusion budget; overflow protects all ground."""
    from . import hardscape
    rows = [*existing['polygons'], *masks]
    count = sum(sum(map(len, r['rings'])) for r in rows)
    if len(rows) > hardscape.MAX_POLYGONS or count > hardscape.MAX_VERTICES:
        x0, y0, x1, y1 = bounds
        rows = [dict(rings=[[[x0,y0],[x1,y0],[x1,y1],[x0,y1]]], min_z=-1000000.,
                     max_z=1000000., kind='hardscape', unknown_height=True)]
    return dict(v=1, polygons=rows)


def metadata(courts, target):
    """Exact provenance and host-frame contact masks alongside the compiled mesh."""
    sites, boxes, masks = [], [], []
    for court in courts:
        from . import shared_layouts
        if isinstance(court,shared_layouts.SharedLayout):
            s,b,m=shared_layouts.metadata(court,target)
            sites.extend(s);boxes.extend(b);masks.extend(m)
            continue
        source = _frame(court.plan)
        e = court.plan.evidence
        sites.append(dict(identity=e.identity.to_dict(), frame=e.frame.frame.to_dict(), revision=court.revision,
                          source_plan_sha256=hashlib.sha256(court.plan.to_json().encode()).hexdigest(),
                          resources=[dict(identity=r.identity, kind=r.kind, producer=r.producer.to_dict(),
                                          consumers=[c.to_dict() for c in r.consumers], retention=r.retention)
                                     for r in court.plan.resources]))
        for extent in e.physical_extents:
            def top(ring):
                return project_points([(x, y, court.plane[0]*x+court.plane[1]*y+court.plane[2]) for x, y in ring], source, target)
            p = extent.boundary
            rings = [top(r) for r in (p.outer, *p.holes)]
            low = project_points([(x, y, court.bottom) for x, y in p.outer], source, target)
            zmin, zmax = float(low[:, 2].min()), float(rings[0][:, 2].max())
            xy = rings[0][:, :2]
            plain = [[[float(x), float(y)] for x, y, _ in r] for r in rings]
            boxes.append([float(xy[:, 0].min()), float(xy[:, 1].min()), zmin,
                          float(xy[:, 0].max()), float(xy[:, 1].max()), zmax, plain])
            masks.append(dict(rings=plain, min_z=zmin-.1, max_z=zmax+.4, kind='hardscape'))
    return sites, boxes, masks


def managed(spec):
    """Explicit shared membership supersedes optional per-building frontage work."""
    if not os.environ.get('BNE_SHARED_SITE_RECORDS'):return False
    source=getattr(getattr(spec,'evidence',None),'source_id',None)
    if not source:return False
    return any(plan.interfaces and any(m.member.kind=='building' and
               m.member.identity.namespace==BUILDING_NAMESPACE and m.member.identity.feature_id==str(source)
               for m in plan.evidence.memberships) for _,plan in catalogue()[1])
