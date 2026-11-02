"""Small, detached road-access proposals for the automatic commercial frontage.

The dimensions below are conservative authored gameplay envelopes, not regional
design standards. A proposal fits the whole receiving pavement and connector
before it can own a curb cut. The caller emits the immutable Solid tops in all
visual/collision variants and commits only after the rest of its site succeeds.
"""
from dataclasses import dataclass
import math

import numpy as np
from shapely.geometry import LineString, Polygon, Point, box

from buildgen.access import Solid

MAX_LENGTH = 24.
MAX_GRADE = .15
MAX_FILL = .6
MAX_CANDIDATES = 4
MAX_ROAD_SEGMENTS = 64
SECTIONS = 33
ROAD_LIP = .002
OWNER_FIELD = 'commercial_driveway_owners'
BLOCKED_ROADS = frozenset(('motorway', 'motorway_link', 'trunk', 'trunk_link',
                           'primary_link', 'secondary_link', 'footway', 'path',
                           'cycleway', 'steps', 'pedestrian', 'bridleway'))


@dataclass(frozen=True, slots=True)
class AccessProposal:
    owner: str
    surfaces: tuple[Solid, ...]
    receiving: tuple[Solid, ...]
    ring: tuple
    route: tuple
    width: float
    crossing: tuple | None
    walk_signature: tuple | None
    offset: tuple
    terrain_points: int

    @property
    def outline(self):
        return Polygon(self.ring)

    def parking_record(self):
        return dict(m='road_asphalt_2lane', w=self.width, tl=11., p=19,
                    bne_access_only=True, bne_commercial_access=True,
                    bne_commercial_owner=self.owner,
                    n=[[p[0]+self.offset[0], p[1]+self.offset[1], 0.] for p in self.route])


def _signature(walk):
    pts = np.asarray(walk.get('pts', ()), float)
    return (tuple(map(tuple, pts)), walk.get('side'), float(walk.get('w', 2.5)),
            bool('corner' in walk), bool(walk.get('median')),
            tuple(tuple(row) for row in walk.get('ramps', ())), float(walk.get('curb_h', .15)))


def _planar_signature(signature):
    return (tuple(tuple(point[:2]) for point in signature[0]), *signature[1:])


def _without_owned(walk, owner):
    result = dict(walk)
    remaining = list(walk.get('driveways', ()))
    for row in walk.get(OWNER_FIELD, {}).get(owner, ()):
        index = next((i for i, value in enumerate(remaining) if tuple(value) == tuple(row)), None)
        if index is not None:
            remaining.pop(index)
    result['driveways'] = remaining
    return result


def _crossing_free(walk, interval):
    import vehicle_crossings as vc
    import sidewalks as sw
    lo, hi = interval[:2]
    # Both cuts own their flare; pedestrian ramp flares are protected too.
    return (not any(b+sw.RAMP_FLARE >= lo-vc.FLARE and a-sw.RAMP_FLARE <= hi+vc.FLARE
                    for a, b in walk.get('ramps', ()))
            and not any(row[1]+vc.FLARE >= lo-vc.FLARE and row[0]-vc.FLARE <= hi+vc.FLARE
                        for row in walk.get('driveways', ())))


def _receiver_samples(receiving):
    """Full-area probes on the emitted triangles, including width-edge probes."""
    points, heights = [], []
    if len(receiving) > 32:
        return None
    for solid in receiving:
        p = np.asarray(solid.top, float)
        if p.shape != (4, 3) or not np.isfinite(p).all():
            return None
        shape = Polygon(p[:, :2])
        if not shape.is_valid or shape.area < .01:
            return None
        for u in np.linspace(0., 1., 5):
            for v in np.linspace(0., 1., 5):
                q = ((1-u)*p[0]+(u-v)*p[1]+v*p[2] if v <= u
                     else (1-v)*p[0]+u*p[2]+(v-u)*p[3])
                points.append(q[:2]); heights.append(q[2])
        lengths = np.linalg.norm(np.roll(p[:, :2], -1, axis=0)-p[:, :2], axis=1)
        if np.any(abs(np.roll(p[:, 2], -1)-p[:, 2]) > MAX_GRADE*lengths+1e-8):
            return None
        for indices in ((0, 1, 2), (0, 2, 3)):
            tri = p[list(indices)]
            matrix = tri[1:, :2]-tri[0, :2]
            if abs(np.linalg.det(matrix)) < 1e-10:
                return None
            if np.linalg.norm(np.linalg.solve(matrix, tri[1:, 2]-tri[0, 2])) > MAX_GRADE:
                return None
    return np.asarray(points).reshape(-1, 2), np.asarray(heights)


def _shared_source(source, receiving, cover):
    edge = LineString(source[:, :2])
    if not cover.boundary.buffer(1e-6).covers(edge):
        return False
    for t in np.linspace(0., 1., 5):
        point = source[0]*(1-t)+source[1]*t
        matches = []
        for solid in receiving:
            p = np.asarray(solid.top, float)
            for indices in ((0, 1, 2), (0, 2, 3)):
                triangle = p[list(indices)]
                matrix = np.c_[triangle[1, :2]-triangle[0, :2], triangle[2, :2]-triangle[0, :2]]
                if abs(np.linalg.det(matrix)) < 1e-10:
                    continue
                u, v = np.linalg.solve(matrix, point[:2]-triangle[0, :2])
                if min(u, v, 1-u-v) >= -1e-7:
                    matches.append(triangle[0, 2]+u*(triangle[1, 2]-triangle[0, 2])
                                   +v*(triangle[2, 2]-triangle[0, 2]))
        if not matches or max(abs(z-point[2]) for z in matches) > 1e-6:
            return False
    return True


def propose_access(source_edge, lines, walks, ground, x0, y0, *, owner,
                   receiving=(), obstacles=(), bounds=None):
    """Return one frozen access, without mutating scene dictionaries.

    source_edge: two LOCAL XYZ points across the already fitted aisle mouth.
    lines/walk pts/terrain/bounds: global road frame. obstacles: LOCAL polygons
    excluding the caller's receiving pavement. receiving: accepted paved quads
    whose complete bounded grid must fit in the same single terrain batch.
    """
    from buildgen.garages import _walk_contact
    from sitegen.portals import simplified_lines
    if ground is None or not isinstance(owner, str) or not owner:
        return None
    source = np.asarray(source_edge, float)
    if source.shape != (2, 3) or not np.isfinite(source).all():
        return None
    offset = np.asarray([x0, y0], float)
    delta = source[1, :2]-source[0, :2]
    width = float(np.linalg.norm(delta))
    if not 3. <= width <= 8. or abs(source[1, 2]-source[0, 2])/width > .02+1e-9:
        return None
    tangent = delta/width
    portal = source[:, :2].mean(axis=0)
    receiving = tuple(receiving)
    receiver = _receiver_samples(receiving)
    if receiver is None:
        return None
    receiver_xy, receiver_z = receiver
    # Any supplied receiving area must actually share the full source edge;
    # disconnected successful pavement is not proof of a working route.
    cover = None
    if receiving:
        from shapely.ops import unary_union
        cover = unary_union([Polygon(np.asarray(s.top)[:, :2]) for s in receiving])
        if not _shared_source(source, receiving, cover):
            return None
    planning_walks = [_without_owned(w, owner) for w in walks]
    obstacles = tuple(obstacles)
    candidates = []
    nearby = []
    for line in simplified_lines(lines):
        points = np.asarray(line[0], float)[:, :2]-offset
        half = float(line[1])
        if not math.isfinite(half) or half <= 0:
            continue
        for a, c in zip(points[:-1], points[1:]):
            if LineString([a, c]).distance(Point(portal)) <= MAX_LENGTH+half:
                nearby.append((a, c, half, line))
    if len(nearby) > MAX_ROAD_SEGMENTS:
        return None
    for a, c, half, line in nearby:
        if len(line) > 2 and line[2] in BLOCKED_ROADS:
            continue
        v = c-a; length = float(np.linalg.norm(v))
        if length < width+1. or abs(v@tangent/length) < .999:
            continue
        along = float((portal-a)@v/length)
        if not width/2+.6 <= along <= length-width/2-.6:
            continue
        centre = a+v*(along/length)
        outward = portal-centre
        distance = float(np.linalg.norm(outward))
        if distance <= half:
            continue
        normal = outward/distance
        road_end = centre+normal*half
        distance -= half
        if not 1. <= distance <= MAX_LENGTH or abs(normal@tangent) > .045:
            continue
        mouth = Polygon([source[0, :2], source[1, :2],
                         road_end+tangent*width/2, road_end-tangent*width/2])
        if not mouth.is_valid or mouth.area <= .1:
            continue
        if cover is not None and mouth.intersection(cover).area > 1e-7:
            continue
        if bounds is not None and not box(*(np.asarray(bounds)-np.tile(offset, 2))).covers(mouth):
            continue
        if any(mouth.intersection(p).area > 1e-7 for p in obstacles):
            continue
        # Do not traverse another road to reach the selected one, including
        # controlled carriageways which are never direct-access candidates.
        if any(mouth.intersection(LineString([ra, rb]).buffer(hw, cap_style=2)).area > 1e-6
               for ra, rb, hw, other in nearby if not (ra is a and rb is c)):
            continue
        contact = _walk_contact(portal, tangent, normal, road_end, width, planning_walks, offset)
        if contact is None:
            continue
        if contact is not False and not _crossing_free(planning_walks[contact[0]], contact[3]):
            continue
        end = road_end if contact is False else contact[1]
        run = float((portal-end)@normal)
        if run < 1.:
            continue
        candidates.append((distance, tuple(road_end), end, run, normal, road_end, mouth, contact))
    candidates.sort(key=lambda row: row[:2])
    candidates = candidates[:MAX_CANDIDATES]
    if not candidates:
        return None
    # All alternatives and the receiving pavement are sampled once. Each route
    # has 33 sections across FIVE width probes (edges, quarters and centre).
    xyrows = []
    t = np.linspace(0., 1., SECTIONS)
    across = np.linspace(-width/2, width/2, 5)
    for _, _, end, run, normal, road_end, mouth, contact in candidates:
        centres = end+(portal-end)*t[:, None]
        xyrows.append(centres[:, None, :]+across[None, :, None]*tangent)
    batch = np.vstack([receiver_xy, *[xy.reshape(-1, 2) for xy in xyrows]])
    terrain = np.asarray(ground(batch+offset), float)
    if terrain.shape != (len(batch),):
        return None
    received = terrain[:len(receiver_xy)]
    if (not np.isfinite(received).all() or np.any(receiver_z-received < -1e-6)
            or np.any(receiver_z-received > MAX_FILL)):
        return None
    for ci, ((_, _, end, run, normal, road_end, mouth, contact), xy) in enumerate(zip(candidates, xyrows)):
        start = len(receiver_xy)+ci*SECTIONS*5
        sampled = terrain[start:start+SECTIONS*5].reshape(SECTIONS, 5)
        if not np.isfinite(sampled).all():
            continue
        z0 = sampled[0, [0, -1]]+ROAD_LIP if contact is False else contact[2]
        # A straight width edge must match the whole road interface, not just
        # its two convenient corners. Existing sidewalk contact is similarly
        # checked by _walk_contact against all its source height breaks.
        if contact is False and np.max(abs(np.linspace(*z0, 5)-sampled[0]-ROAD_LIP)) > .005:
            continue
        z1 = source[:, 2]
        g0 = 0. if contact is False else .015
        z = ((2*t**3-3*t**2+1)[:, None]*z0
             +(t**3-2*t**2+t)[:, None]*run*g0
             +(-2*t**3+3*t**2)[:, None]*z1)
        surface = z[:, :1]+(z[:, 1:]-z[:, :1])*np.linspace(0., 1., 5)
        fill = surface-sampled
        if (np.max(abs(np.diff(z, axis=0)))/(run/(SECTIONS-1)) > MAX_GRADE
                or np.max(abs(z[:, 1]-z[:, 0]))/width > .02+1e-9
                or np.min(fill) < -1e-6 or np.max(fill) > MAX_FILL):
            continue
        solids = []
        for j in range(SECTIONS-1):
            top = np.array([np.r_[xy[j, 0], z[j, 0]], np.r_[xy[j+1, 0], z[j+1, 0]],
                            np.r_[xy[j+1, -1], z[j+1, 1]], np.r_[xy[j, -1], z[j, 1]]])
            area = np.sum(top[:, 0]*np.roll(top[:, 1], -1)-top[:, 1]*np.roll(top[:, 0], -1))
            if area < 0:
                top = top[::-1]
            solids.append(Solid('site_driveway', tuple(map(tuple, top)), float(sampled[j:j+2].min()-.1)))
        crossing = None if contact is False else (contact[0], *map(float, contact[3]))
        signature = None if contact is False else _signature(walks[contact[0]])
        return AccessProposal(owner, tuple(solids), receiving,
                              tuple(map(tuple, np.asarray(mouth.exterior.coords)[:-1])),
                              tuple(map(tuple, np.vstack((portal, end, road_end)))), width,
                              crossing, signature, tuple(offset), len(batch))
    return None


def commit_access(proposal, walks, raw_walks=None, drives=None):
    """Commit only a still-valid proposal; failure leaves every collection intact.

    Replacements remove only this owner's prior intervals. Raw sidewalk cuts
    mirror its XY run rather than an index: roads copies raw runs before draping
    heights, so raw Z is intentionally allowed to differ from actual walk Z.
    """
    if not isinstance(proposal, AccessProposal):
        return False
    collections = [walks]
    if raw_walks is not None and raw_walks is not walks:
        collections.append(raw_walks)
    targets = []
    if proposal.crossing is not None:
        wi, *interval = proposal.crossing
        interval = tuple(interval)
        for ci, collection in enumerate(collections):
            expected = proposal.walk_signature if ci == 0 else _planar_signature(proposal.walk_signature)
            matches = [w for w in collection if
                       (_signature(w) if ci == 0 else _planar_signature(_signature(w))) == expected]
            if len(matches) != 1:
                return False
            walk = matches[0]
            if not _crossing_free(_without_owned(walk, proposal.owner), interval):
                return False
            targets.append(walk)
    # Build all new dictionaries before publishing any mutation.
    updates = []
    for collection in collections:
        for walk in collection:
            owners = dict(walk.get(OWNER_FIELD, {}))
            old = owners.pop(proposal.owner, ())
            remaining = list(walk.get('driveways', ()))
            for row in old:
                index = next((i for i, value in enumerate(remaining) if tuple(value) == tuple(row)), None)
                if index is not None:
                    remaining.pop(index)
            if any(walk is target for target in targets):
                remaining.append(interval)
                owners[proposal.owner] = (interval,)
            updates.append((walk, remaining, owners))
    record = proposal.parking_record()
    kept = None if drives is None else [r for r in drives if r.get('bne_commercial_owner') != proposal.owner]
    for walk, remaining, owners in updates:
        if remaining:
            walk['driveways'] = remaining
        else:
            walk.pop('driveways', None)
        if owners:
            walk[OWNER_FIELD] = owners
        else:
            walk.pop(OWNER_FIELD, None)
    if drives is not None:
        drives[:] = [*kept, record]
    return True


def perimeter_curbs(edges, openings=(), *, height=.12, width=.15, base_plane=None):
    """Physical edge blocks, clipped around walking/driving route polygons.

    Caller selects pavement/bed perimeter edges. XY openings should represent
    the complete traversable route; half-curb width plus .1m is reserved around
    each opening so a curb corner cannot project into the route. An optional
    accepted ``base_plane=(dx,dy,z0)`` carries the surface's transverse grade
    across the complete curb width, rather than flattening each end face.
    """
    from shapely.ops import unary_union
    if not .04 <= height <= .25 or not .08 <= width <= .3:
        return ()
    plane=None if base_plane is None else np.asarray(base_plane,float)
    if plane is not None and (plane.shape!=(3,) or not np.isfinite(plane).all()):
        return ()
    openings = tuple(openings)
    clear = unary_union(openings).buffer(width/2+.1) if openings else None
    solids = []
    for edge in tuple(edges)[:256]:
        p = np.asarray(edge, float)
        if p.shape != (2, 3) or not np.isfinite(p).all():
            continue
        if plane is not None and np.max(np.abs(np.c_[p[:,:2],np.ones(2)]@plane-p[:,2]))>.005:
            continue
        line = LineString(p[:, :2])
        if line.length < .1:
            continue
        remain = line if clear is None else line.difference(clear)
        parts = (remain,) if remain.geom_type == 'LineString' else getattr(remain, 'geoms', ())
        direction = (p[1, :2]-p[0, :2])/line.length
        normal = np.array([-direction[1], direction[0]])*width/2
        for part in parts:
            if part.geom_type != 'LineString' or part.length < .25:
                continue
            a, c = np.asarray(part.coords)[[0, -1]]
            za, zc = [float(np.interp(line.project(Point(q)), [0., line.length], p[:, 2])) for q in (a, c)]
            xy=np.array((a-normal,c-normal,c+normal,a+normal))
            base=np.array((za,zc,zc,za)) if plane is None else np.c_[xy,np.ones(4)]@plane
            top=tuple(tuple(map(float,(*q,z+height))) for q,z in zip(xy,base))
            solids.append(Solid('site_curb', top, float(base.min()-.04)))
    return tuple(solids)
