"""Conservative automatic frontage grounds for commercial buildings.

The fitted envelope is a local visual/access treatment, never a parcel claim.
Everything is bounded by the source facade and observed ordinary street.
"""
from dataclasses import replace
import hashlib
import math
import os

import numpy as np
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from .access import Solid, basis
from .site_layout import Layout

MAX_DEPTH = 24.
CELL = 2.
MAX_PATCHES = 32
AUTO = 'automatic-frontage:'


def _shape(s):
    return Polygon([p[:2] for p in s.top])


def _key(spec):
    source = str(getattr(getattr(spec, 'evidence', None), 'source_id', '') or '')
    ring = tuple(map(tuple, np.round(np.asarray(spec.ring, float), 5)))
    return source, ring


def _owner(spec):
    return AUTO + hashlib.sha256(repr(_key(spec)).encode()).hexdigest()[:24]



def eligible(spec):
    """Whether a building is eligible for a default-on inferred frontage."""
    return (os.environ.get('BNE_BUILDING_PATHS', 'auto') != 'off'
            and spec.site is None and spec.inference is not None
            and spec.inference.use.value in ('commercial', 'industrial', 'mixed')
            and (spec.min_h or 0.) <= .5)


def _frontage_edge(spec, lines, offset):
    """Use an entrance when known, otherwise the closest usable street facade.

    An inferred service yard does not assert a missing door or a cadastral parcel.
    """
    if spec.door is not None:
        return spec.door[0]
    candidates = []
    ring = np.asarray(spec.ring, float)
    for edge, (a, c) in enumerate(zip(ring, np.roll(ring, -1, axis=0))):
        length = float(np.linalg.norm(c-a))
        if length < 5.: continue
        tangent = (c-a)/length
        depth = _road_depth(a, tangent, np.array([tangent[1], -tangent[0]]), length, lines, offset)
        if depth is not None: candidates.append((depth, -length, edge))
    return min(candidates)[2] if candidates else None

def _road_depth(origin, tangent, normal, length, lines, offset):
    from sitegen.commercial_access import BLOCKED_ROADS
    candidates = []
    for line in lines:
        if len(line) > 2 and line[2] in BLOCKED_ROADS:
            continue
        points = np.asarray(line[0], float)
        for a, b in zip(points[:-1, :2]-offset, points[1:, :2]-offset):
            v = b-a
            n = np.linalg.norm(v)
            if n < 1e-6 or abs(v@tangent/n) < .96:
                continue
            along = sorted(((a-origin)@tangent, (b-origin)@tangent))
            if min(length, along[1])-max(0., along[0]) < min(4., length*.5):
                continue
            d = float(((a+b)/2-origin)@normal)-float(line[1])
            if 1.7 < d <= MAX_DEPTH+3.:
                candidates.append(d)
    return min(candidates) if candidates else None


def _fit_rect(q, ground, offset, shared_plane=None):
    # Fit one plane to a 5x5 grid: no fake level slab over unknown/rough terrain.
    points = np.array([(1-v)*((1-u)*q[0]+u*q[1])+v*((1-u)*q[3]+u*q[2])
                       for v in np.linspace(0, 1, 5) for u in np.linspace(0, 1, 5)])
    try:
        z = np.asarray(ground(points+offset), float).reshape(-1)
    except (ValueError, TypeError, IndexError):
        return None
    if len(z) != len(points) or not np.isfinite(z).all():
        return None
    if shared_plane is not None:
        # Recheck every patch's own probes against the common frontage datum.
        # A shared plane never waives terrain/fill validation for a small patch.
        fill=np.c_[points,np.ones(len(points))]@shared_plane-z
        if np.linalg.norm(shared_plane[:2])>.10 or fill.min()<.004 or fill.max()>.16:return None
        heights=np.c_[q,np.ones(4)]@shared_plane
    else:
        centre = points.mean(axis=0)
        A = np.c_[points-centre, np.ones(len(points))]
        coeff = np.linalg.lstsq(A, z, rcond=None)[0]
        residual = z-A@coeff
        # A shallow offset above the highest residual keeps the entire slab grounded.
        lift = float(max(residual)+.025)
        if np.linalg.norm(coeff[:2]) > .10 or lift-float(min(residual)) > .16:
            return None
        heights = np.c_[q-centre, np.ones(4)]@coeff+lift
    top = np.c_[q, heights]
    if not Polygon(q).exterior.is_ccw:
        top = top[::-1]
    return tuple(tuple(map(float, p)) for p in top), float(z.min()-.1)



def _entry_steps(points, source_kind, ground, offset):
    """A short pedestrian stair continuation with a complete lower landing.

    An existing step flight already owns its upper landing; its final tread can
    continue into another tread. Other entry surfaces need a new upper landing.
    These are never car-access strips: the separate road connector serves cars.
    """
    from .access import LANDING,TREAD,MAX_RISE,MAX_STEPS
    start=points[:2]; end=points[[3,2]]
    length=float(np.linalg.norm(end[:,:2].mean(axis=0)-start[:,:2].mean(axis=0)))
    delta=end[:,2]-start[:,2]
    if delta.min() < -.01 and delta.max() > .01:return None
    risers=int(math.ceil(float(np.max(np.abs(delta)))/MAX_RISE))
    if not 1<=risers<=MAX_STEPS:return None
    upper=TREAD if source_kind=='step' else LANDING
    minimum=upper+max(0,risers-1)*TREAD+LANDING
    if length<minimum-1e-8:return None
    distances=[0.,upper,*[upper+i*TREAD for i in range(1,risers)],length]
    quads=[]; samples=[]; levels=[]
    for i,(lo,hi) in enumerate(zip(distances,distances[1:])):
        t0,t1=lo/length,hi/length
        edge0=start.copy() if lo==0. else start+(end-start)*t0
        edge1=end.copy() if hi==length else start+(end-start)*t1
        z=start[:,2]+delta*(i/risers)
        edge0[:,2]=z;edge1[:,2]=z
        q=np.array([edge0[0],edge0[1],edge1[1],edge1[0]])
        for u in np.linspace(0.,1.,5):
            for v in np.linspace(0.,1.,5):
                point=(1-v)*((1-u)*q[0]+u*q[1])+v*((1-u)*q[3]+u*q[2])
                samples.append(point[:2]);levels.append(point[2])
        if not Polygon(q[:,:2]).exterior.is_ccw:q=q[::-1]
        quads.append(q)
    try: terrain=np.asarray(ground(np.asarray(samples)+offset),float).reshape(-1)
    except (ValueError,TypeError,IndexError):return None
    if len(terrain)!=len(samples) or not np.isfinite(terrain).all():return None
    fill=np.asarray(levels)-terrain
    # Low stair foundations are allowed; unknown ground, cut-through terrain or
    # a retaining-wall-scale flight remains unresolved instead of floating.
    if fill.min()<.004 or fill.max()>.6:return None
    return tuple(Solid('site_walk' if i==len(quads)-1 else 'site_step',
                       tuple(tuple(map(float,p)) for p in q),float(terrain[i*25:(i+1)*25].min()-.1))
                 for i,q in enumerate(quads))


def _entry_link(spec, slabs, obstacles, ground, offset, tangent, normal, clip):
    """Bridge an existing entry edge to one paved edge, matching both datums."""
    axes = (tangent, normal)
    sources = [s for s in spec.access.solids if s.kind in ('path','path_link','path_landing','threshold','step')]
    def edges(solid):
        pts = np.asarray(solid.top, float)
        for p, q in zip(pts, np.roll(pts,-1,axis=0)):
            d = q[:2]-p[:2]
            length = np.linalg.norm(d)
            if length < .6: continue
            axis = int(abs(d@axes[1]) > abs(d@axes[0]))
            if abs(d@axes[axis])/length < .999: continue
            yield p,q,axis
    jobs=[]
    for source in sources:
        for p,q,axis in edges(source):
            direction=axes[axis]; across=axes[1-axis]
            for slab in slabs:
                for r,s,other_axis in edges(slab):
                    if other_axis != axis: continue
                    gap = float((r[:2]-p[:2])@across)
                    if not .001 < abs(gap) <= 3.1: continue
                    u0,u1=sorted((float(p[:2]@direction),float(q[:2]@direction)))
                    v0,v1=sorted((float(r[:2]@direction),float(s[:2]@direction)))
                    lo,hi=max(u0,v0),min(u1,v1)
                    if hi-lo < .6: continue
                    mid=(lo+hi)/2
                    width=min(1.2,hi-lo)
                    lo,hi=mid-width/2,mid+width/2
                    def point(a,b,u):
                        av,bv=float(a[:2]@direction),float(b[:2]@direction)
                        return a+(b-a)*((u-av)/(bv-av))
                    points=np.array([point(p,q,lo),point(p,q,hi),point(r,s,hi),point(r,s,lo)])
                    shape=Polygon(points[:,:2])
                    if not shape.is_valid or shape.area < .01: continue
                    if clip is not None and not clip.buffer(1e-7).covers(shape):continue
                    if any(shape.intersection(o).area > 1e-7 for o in obstacles):continue
                    if any(shape.intersection(_shape(o)).area > 1e-7 for o in slabs):continue
                    jobs.append((abs(gap), tuple(np.round(points[:,:2].ravel(),6)), points,source.kind))
    ranked=sorted(jobs,key=lambda x:x[:2])
    for _,_,points,_ in ranked:
        # Full patch probes use the same two-triangle interpolation as rendering.
        samples=[]; levels=[]
        for u in np.linspace(0.,1.,5):
            for v in np.linspace(0.,1.,5):
                q=((1-u)*points[0]+(u-v)*points[1]+v*points[2] if v<=u
                   else (1-v)*points[0]+u*points[2]+(v-u)*points[3])
                samples.append(q[:2]); levels.append(q[2])
        try: terrain=np.asarray(ground(np.asarray(samples)+offset),float).reshape(-1)
        except (ValueError,TypeError,IndexError): continue
        if len(terrain)!=25 or not np.isfinite(terrain).all():continue
        fill=np.asarray(levels)-terrain
        if np.min(fill)<.004 or np.max(fill)>.16: continue
        if any(abs(a[2]-b[2])/np.linalg.norm(a[:2]-b[:2])>.1
               for a,b in zip(points,np.roll(points,-1,axis=0))):continue
        if not Polygon(points[:,:2]).exterior.is_ccw:points=points[::-1]
        return (Solid('site_walk',tuple(tuple(map(float,p)) for p in points),float(terrain.min()-.1)),)
    for _,_,points,source_kind in ranked[:4]:
        steps=_entry_steps(points,source_kind,ground,offset)
        if steps is not None:return steps
    return None


def _trim_beds(beds, link, origin, tangent, normal):
    """Keep rectangular planted fragments clear of the accepted entry link."""
    from shapely.affinity import affine_transform
    transform=[*tangent,*normal,-origin@tangent,-origin@normal]
    link_local=affine_transform(_shape(link),transform)
    result=[]
    for bed in beds:
        shape=affine_transform(_shape(bed),transform)
        overlap=shape.intersection(link_local)
        if overlap.area < 1e-7:
            result.append(bed); continue
        x0,y0,x1,y1=shape.bounds
        a,b,c,d=overlap.bounds
        xs=sorted(set((x0,max(x0,a),min(x1,c),x1)))
        ys=sorted(set((y0,max(y0,b),min(y1,d),y1)))
        top=np.asarray(bed.top,float)
        plane=np.linalg.lstsq(np.c_[top[:,:2],np.ones(len(top))],top[:,2],rcond=None)[0]
        for lo,hi in zip(xs,xs[1:]):
            # Merge consecutive clear cells within each strip.
            start=None
            for k,(near,far) in enumerate(zip(ys,ys[1:])):
                cell=box(lo,near,hi,far)
                clear=cell.area>.01 and shape.buffer(1e-8).covers(cell) and cell.intersection(link_local).area<1e-7
                if clear and start is None:start=near
                if start is not None and (not clear or k==len(ys)-2):
                    end=far if clear else near
                    if (hi-lo)*(end-start)>.01:
                        xy=np.array([origin+tangent*x+normal*y for x,y in
                                     ((lo,start),(hi,start),(hi,end),(lo,end))])
                        z=np.c_[xy,np.ones(4)]@plane
                        points=np.c_[xy,z]
                        if not Polygon(xy).exterior.is_ccw:points=points[::-1]
                        result.append(Solid(bed.kind,tuple(tuple(map(float,p)) for p in points),bed.bottom))
                    start=None
    return result

def _curbed_beds(beds, origin, tangent, normal, openings=()):
    """A joined curb ring and its matching soft interior share one fitted datum.

    Automatic beds are facade-aligned rectangles. Keep every block inside that
    already validated footprint: neither adjoining pavement nor planted cover
    may overlap the raised curb. The two long blocks own the corner squares;
    side blocks meet them at exact shared ends instead of leaving corner gaps.
    """
    from sitegen.commercial_access import perimeter_curbs
    width=.15
    interiors=[];curbs=[]
    for bed in beds:
        top=np.asarray(bed.top,float)
        uv=np.c_[(top[:,:2]-origin)@tangent,(top[:,:2]-origin)@normal]
        lo,near=uv.min(axis=0); hi,far=uv.max(axis=0)
        if min(hi-lo,far-near)<2*width+.6:
            interiors.append(bed);continue
        if abs(Polygon(uv).area-(hi-lo)*(far-near))>1e-6:
            interiors.append(bed);continue
        plane=np.linalg.lstsq(np.c_[top[:,:2],np.ones(4)],top[:,2],rcond=None)[0]
        if np.max(np.abs(np.c_[top[:,:2],np.ones(4)]@plane-top[:,2]))>1e-6:
            interiors.append(bed);continue
        def point(x,y):
            q=origin+tangent*x+normal*y
            return tuple(map(float,(*q,(*q,1.)@plane)))
        edges=[(point(lo,near+width/2),point(hi,near+width/2)),
               (point(lo,far-width/2),point(hi,far-width/2)),
               (point(lo+width/2,near+width),point(lo+width/2,far-width)),
               (point(hi-width/2,near+width),point(hi-width/2,far-width))]
        blocks=perimeter_curbs(edges,openings,width=width,base_plane=plane)
        if not blocks:
            interiors.append(bed);continue
        inner=tuple(point(x,y) for x,y in ((lo+width,near+width),(hi-width,near+width),
                                         (hi-width,far-width),(lo+width,far-width)))
        if not Polygon([p[:2] for p in inner]).exterior.is_ccw:inner=inner[::-1]
        interiors.append(replace(bed,top=inner))
        curbs.extend(blocks)
    return interiors,curbs


def _resolve_staged(items, lines, x0, y0, *, ground, walks=(), raw_walks=None, bounds=None, obstacles=()):
    """Install finite, non-overlapping inferred frontages and return road exclusions."""
    from sitegen.commercial_access import propose_access, commit_access
    offset = np.array([x0, y0], float)
    records = []
    if os.environ.get('BNE_BUILDING_PATHS', 'auto') == 'off':
        return records
    # Retire this adapter's old sidewalk cuts before rebuilding.
    old_owners = {s.access.site_layout.site_id for s, _, _ in items
                  if s.access and s.access.site_layout and s.access.site_layout.site_id.startswith(AUTO)}
    for collection in (walks, raw_walks if raw_walks is not walks else None):
        for walk in collection or ():
            owners = dict(walk.get('commercial_driveway_owners', {}))
            remaining = list(walk.get('driveways', ()))
            for owner in old_owners:
                for row in owners.pop(owner, ()):
                    match = next((i for i, value in enumerate(remaining) if tuple(value) == tuple(row)), None)
                    if match is not None: remaining.pop(match)
            if remaining: walk['driveways'] = remaining
            else: walk.pop('driveways', None)
            if owners: walk['commercial_driveway_owners'] = owners
            else: walk.pop('commercial_driveway_owners', None)
    # Strip only surfaces previously owned by this adapter. Surveyed layouts and
    # primary access remain untouched across repeated resolves.
    for s, _, _ in items:
        if s.access and s.access.site_layout and s.access.site_layout.site_id.startswith(AUTO):
            s.access = replace(s.access, solids=tuple(v for v in s.access.solids if not v.kind.startswith('site_')),
                               landscape=tuple(v for v in s.access.landscape if not v.kind.startswith('site_')),
                               site_layout=None)
    occupied = []
    for s, _, _ in items:
        occupied.append(s.footprint.shape() if s.footprint is not None else Polygon(s.ring))
        if s.access:
            occupied.extend(_shape(v) for v in s.access.solids)
        ga = getattr(s, 'garage_access', None)
        if ga:
            occupied.extend(_shape(v) for v in ga.surfaces)
    for obj in obstacles:
        shape = obj if hasattr(obj, 'intersection') else None
        if shape is not None and not shape.is_empty:
            occupied.append(shape)
    scene_obstacles = list(occupied)
    for line in lines:
        p = np.asarray(line[0], float)
        if len(p) >= 2:
            occupied.append(LineString(p[:, :2]-offset).buffer(float(line[1])+.08, cap_style=2))
    for walk in walks or ():
        p = np.asarray(walk.get('pts', ()), float)
        if len(p) >= 2:
            occupied.append(LineString(p[:, :2]-offset).buffer(float(walk.get('w', 2.5))/2+.08, cap_style=2))
    clip = None
    if bounds is not None:
        lo = np.asarray(bounds[:2], float)-offset
        hi = np.asarray(bounds[2:], float)-offset
        clip = box(lo[0], lo[1], hi[0], hi[1])

    for spec, _, _ in sorted(items, key=lambda item: _key(item[0])):
        if not eligible(spec):
            continue
        if spec.access is None:
            from .access import AccessPlan
            spec.access = AccessPlan(float(np.min(spec.gring)) if spec.gring is not None else 0., None, ())
        owner = _owner(spec)
        notes = []
        def finish(note):
            spec.access = replace(spec.access, site_layout=Layout(owner, '1', diagnostics=(note,)))
        if ground is None:
            finish('automatic_missing_terrain'); continue
        edge = _frontage_edge(spec, lines, offset)
        if edge is None:
            finish('automatic_no_compatible_road'); continue
        a, c = np.asarray(spec.ring[edge], float), np.asarray(spec.ring[(edge+1) % len(spec.ring)], float)
        length = float(np.linalg.norm(c-a))
        if length < 5.:
            finish('automatic_frontage_too_narrow'); continue
        tangent = (c-a)/length
        normal = np.array([tangent[1], -tangent[0]])
        depth = _road_depth(a, tangent, normal, length, lines, offset)
        if depth is None:
            finish('automatic_no_compatible_road'); continue
        # Reserve enough transition behind the actual nearby sidewalk to
        # meet its raised outer edge at a drivable grade. On shallow frontages,
        # sidewalk polygons themselves determine the available walk width.
        frontage = Polygon([a,a+tangent*length,a+tangent*length+normal*depth,a+normal*depth])
        walk_widths = []
        near_walk = depth
        from shapely.affinity import affine_transform
        for walk in walks or ():
            pts=np.asarray(walk.get('pts',()),float)
            width=float(walk.get('w',2.5))
            if len(pts)<2: continue
            line=LineString(pts[:,:2]-offset)
            if line.distance(frontage) > width: continue
            walk_widths.append(width)
            intersection=line.buffer(width/2+.08,cap_style=2).intersection(frontage)
            if not intersection.is_empty:
                local=affine_transform(intersection,[*tangent,*normal,-a@tangent,-a@normal])
                near_walk=min(near_walk,local.bounds[1])
        reserve = 3.5 + max(0.,max(walk_widths,default=.5)-.5)
        depth = min(MAX_DEPTH, depth-(reserve if depth >= 10. else .18), near_walk-(2.2 if depth >= 8. else .02))
        if depth < 1.25:
            finish('automatic_setback_too_shallow'); continue
        # Integer cells prevent clipping across source polygons; merge horizontal
        # runs and identical adjacent runs into inexpensive convex rectangles.
        nx = min(40, max(1, int((length-1.)/CELL)))
        ny = min(12, max(1, int((depth-.5)/CELL)))
        xs = np.linspace(.5, length-.5, nx+1)
        ys = np.linspace(.5, depth, ny+1)
        if depth >= 8. and ny >= 2:
            # Allow a genuine stock shrub's complete canopy and clearance.
            # Keep the same outer extent and cell budget; only move this split.
            ys = np.r_[.5, np.linspace(3.1, depth, ny)]
        local_obstacles = [p for p in occupied if p.distance(Polygon([a,a+tangent*length,
                            a+tangent*length+normal*depth,a+normal*depth])) < .01]
        union = unary_union(local_obstacles) if local_obstacles else Polygon()
        def quad(x0, x1, y0, y1):
            return np.array([a+tangent*x0+normal*y0, a+tangent*x1+normal*y0,
                             a+tangent*x1+normal*y1, a+tangent*x0+normal*y1])
        # Tiny terrain ripples must not give neighboring pieces independently
        # lifted datums and force an otherwise usable centre slab to disappear.
        # Prefer one validated plane, then verify each accepted patch against it.
        shared_fit=_fit_rect(quad(xs[0],xs[-1],ys[0],ys[-1]),ground,offset)
        shared_plane=None
        if shared_fit is not None:
            top=np.asarray(shared_fit[0])
            shared_plane=np.linalg.lstsq(np.c_[top[:,:2],np.ones(4)],top[:,2],rcond=None)[0]
        grid = np.zeros((ny, nx), bool)
        for j in range(ny):
            for i in range(nx):
                shape = Polygon(quad(xs[i],xs[i+1],ys[j],ys[j+1]))
                grid[j,i] = (clip is None or clip.buffer(1e-7).covers(shape)) and shape.intersection(union).area < 1e-7
        runs = []
        for i in range(nx):
            j = 0
            while j < ny:
                if not grid[j,i]: j += 1; continue
                k = j+1
                while k < ny and grid[k,i]: k += 1
                match = next ( (r for r in runs if r[2] == j and r[3] == k and r[1] == i), None)
                if match is not None: match[1] = i+1
                else: runs.append([i,i+1,j,k])
                j = k
        runs.sort(key=lambda r: (-(xs[r[1]]-xs[r[0]])*(ys[r[3]]-ys[r[2]]),r))
        if len(runs) > MAX_PATCHES:
            notes.append('automatic_patch_budget'); runs = runs[:MAX_PATCHES]
        slabs=[]; beds=[]
        for i,k,j,l in runs:
            # A broad planted row on substantial spans; the rest is paved.
            parts = []
            if j == 0 and k-i >= 3 and l-j >= 2 and ys[l]-ys[j] >= 8.5:
                parts.append(('site_garden_bed',quad(xs[i],xs[k],ys[j]+.16,ys[j+1])))
                j += 1
            if l > j:
                parts.append(('site_service',quad(xs[i],xs[k],ys[j],ys[l])))
            for kind,q in parts:
                fitted = _fit_rect(q, ground, offset, shared_plane)
                if fitted is None:
                    notes.append('automatic_missing_or_rough_terrain'); continue
                solid = Solid(kind, *fitted)
                # Adjacent independently sampled planes must meet without a lip.
                # Reject a conflicting patch rather than invent earthworks.
                conflict = False
                for other in (*slabs, *beds, *spec.access.solids):
                    shared = _shape(solid).boundary.intersection(_shape(other).boundary)
                    if shared.length < .05:
                        continue
                    coords = list(shared.geoms) if hasattr(shared, 'geoms') else [shared]
                    aa = np.asarray(solid.top, float); bb = np.asarray(other.top, float)
                    pa = np.linalg.lstsq(np.c_[aa[:,:2],np.ones(len(aa))],aa[:,2],rcond=None)[0]
                    pb = np.linalg.lstsq(np.c_[bb[:,:2],np.ones(len(bb))],bb[:,2],rcond=None)[0]
                    for segment in coords:
                        if not hasattr(segment, 'coords') or len(segment.coords) < 2: continue
                        for point in segment.coords:
                            if abs(np.dot(pa-pb, [point[0],point[1],1.])) > .005:
                                conflict = True; break
                        if conflict: break
                    if conflict: break
                if conflict:
                    notes.append('automatic_surface_seam_conflict'); continue
                (beds if kind == 'site_garden_bed' else slabs).append(solid)
        if not slabs:
            finish(notes[0] if notes else 'automatic_obstructed'); continue
        links = _entry_link(spec, slabs, local_obstacles, ground, offset, tangent, normal, clip)
        if links is not None:
            for link in links:beds = _trim_beds(beds, link, a, tangent, normal)
            slabs.extend(links)
            if any(link.kind=='site_step' for link in links):notes.append('automatic_pedestrian_steps')
        else:
            notes.append('automatic_entry_link_unresolved')
        # Only call a parking area connected when its slab is in the same
        # touching component as the actual entrance link.
        reachable = {id(link) for link in links or ()}
        changed = True
        while changed:
            changed = False
            for candidate in slabs:
                if id(candidate) in reachable: continue
                # Interpolated rotated edges can differ by a few ulps after a
                # frame shift. Sub-micron XY roundoff is not a physical gap.
                if any(_shape(candidate).boundary.intersection(_shape(other).boundary.buffer(1e-7)).length > .05
                       for other in slabs if id(other) in reachable):
                    reachable.add(id(candidate)); changed = True
        parking = 0; marks = []; connections=[]; proposal = None
        # A parking row requires a real six-metre aisle and five-metre stalls,
        # and a verified road connector from the outer edge of its receiving slab.
        for idx, slab in enumerate(slabs):
            if slab.kind != 'site_service': continue
            p = np.asarray(slab.top)
            uv = np.c_[(p[:,:2]-a)@tangent,(p[:,:2]-a)@normal]
            lo,hi = uv[:,0].min(),uv[:,0].max()
            near,far = uv[:,1].min(),uv[:,1].max()
            if id(slab) not in reachable or hi-lo < 7.5 or far-near < 11.2: continue
            z = lambda x,y: float(np.linalg.lstsq(np.c_[uv,np.ones(4)],p[:,2],rcond=None)[0] @ [x,y,1.])
            mouth_lo = (lo+hi)/2-3.; mouth_hi = mouth_lo+6.
            source = (tuple((* (a+tangent*mouth_lo+normal*far),z(mouth_lo,far))),
                      tuple((* (a+tangent*mouth_hi+normal*far),z(mouth_hi,far))))
            proposal = propose_access(source, lines, walks, ground, x0, y0, owner=owner,
                                      receiving=(slab,), obstacles=scene_obstacles, bounds=bounds)
            if proposal is None: continue
            if not commit_access(proposal, walks, raw_walks, records):
                proposal = None; continue
            slabs[idx] = replace(slab, kind='site_parking')
            parking = min(12, int((hi-lo)/2.7))
            for v in np.linspace(lo, lo+parking*2.7, parking+1):
                u0,u1=near,near+5.2
                marks.append((tuple((* (a+tangent*v+normal*u0),z(v,u0)+.006)),
                              tuple((* (a+tangent*v+normal*u1),z(v,u1)+.006))))
            slabs.extend(proposal.surfaces); connections.append('parking'); break
        if parking == 0:
            notes.append('automatic_parking_no_connected_fit')
        if proposal is None:
            # A service entrance needs a receiving yard, not eleven metres of
            # marked parking or an already-resolved pedestrian entrance. Try a
            # bounded set of mouth positions; never drop an entire frontage.
            attempts = 0
            for slab in tuple(slabs):
                if slab.kind != 'site_service': continue
                p = np.asarray(slab.top)
                uv = np.c_[(p[:,:2]-a)@tangent, (p[:,:2]-a)@normal]
                lo, near = uv.min(axis=0); hi, far = uv.max(axis=0)
                width = min(7. if spec.inference.use.value == 'industrial' else 5., hi-lo-.6)
                if width < 3.5 or far-near < 3.5: continue
                plane = np.linalg.lstsq(np.c_[uv,np.ones(4)],p[:,2],rcond=None)[0]
                for middle in dict.fromkeys(((lo+hi)/2, lo+width/2+.3, hi-width/2-.3)):
                    if attempts >= 6: break
                    attempts += 1
                    source = [(* (a+tangent*u+normal*far), float(plane@[u,far,1.]))
                              for u in (middle-width/2,middle+width/2)]
                    proposal = propose_access(source, lines, walks, ground, x0, y0, owner=owner,
                        receiving=(slab,), obstacles=(*scene_obstacles,
                        *(_shape(v) for v in (*slabs,*beds) if v is not slab)), bounds=bounds)
                    if proposal is not None and commit_access(proposal, walks, raw_walks, records):
                        slabs.extend(proposal.surfaces)
                        connections.append('service')
                        notes.append('automatic_service_access')
                        break
                    proposal = None
                if proposal is not None or attempts >= 6: break
            if proposal is None: notes.append('automatic_service_access_no_safe_fit')
        # Curb the actual bed/pavement boundary as well as its ends. Paving is
        # adjacent, while traversable entry links require a clear curb opening.
        routes=(*spec.access.solids,*(s for s in slabs if s.kind in ('site_walk','site_step','site_driveway')))
        beds,curbs=_curbed_beds(beds,a,tangent,normal,tuple(_shape(s) for s in routes))
        all_new = slabs+curbs
        shapes = [_shape(v) for v in all_new+beds]
        occupied.extend(shapes)
        scene_obstacles.extend(shapes)
        notes.extend((f'automatic_paved_m2={sum(_shape(v).area for v in slabs):.1f}',
                      f'automatic_bed_m2={sum(_shape(v).area for v in beds):.1f}',
                      f'automatic_parking={parking}',f'automatic_curbs={len(curbs)}'))
        layout=Layout(owner,'1',parking=parking,terrain_points=25*(1+len(slabs)+len(beds)),
                      connections=tuple(connections),diagnostics=tuple(sorted(set(notes))),markings=tuple(marks))
        spec.access=replace(spec.access,solids=spec.access.solids+tuple(all_new),
                            landscape=spec.access.landscape+tuple(beds),site_layout=layout)
    return records


def _accepted_automatic(access):
    layout = getattr(access, 'site_layout', None)
    return bool(layout is not None and layout.site_id.startswith(AUTO)
                and any(s.kind.startswith('site_') for s in (*access.solids, *access.landscape)))


def _replaces_automatic(previous, replacement):
    if not _accepted_automatic(replacement):
        return False
    before, after = previous.site_layout, replacement.site_layout
    if before.site_id != after.site_id or not set(before.connections).issubset(after.connections):
        return False
    # Losing a previously usable parking entrance is a failed replacement even
    # when some decorative pavement still fits beside the failed connector.
    if before.parking and (not after.parking or not any(s.kind == 'site_driveway' for s in replacement.solids)):
        return False
    if (any(s.kind == 'site_walk' for s in previous.solids)
            and not any(s.kind == 'site_walk' for s in replacement.solids)):
        return False
    return True


def _retained_records(items, walks, x0, y0):
    """Recover exclusions from installed immutable strips and exact owned cuts."""
    from shapely.geometry import Point
    import sidewalks
    offset = np.array([x0, y0], float)
    records = []
    for spec, _, _ in items:
        access = spec.access
        if not _accepted_automatic(access):
            continue
        owner = access.site_layout.site_id
        strips = [s for s in access.solids if s.kind == 'site_driveway']
        if not strips:
            continue
        sections = {}; widths = []
        for solid in strips:
            p = np.asarray(solid.top, float)[:, :2]
            # Each of the bounded strip panels is shorter than its full width.
            # The two long opposite edges are the exact cross sections shared
            # with the next panel; only the terminal sections occur once.
            lengths = np.linalg.norm(np.roll(p, -1, axis=0)-p, axis=1)
            index = int(np.argmax(lengths))
            widths.append(float(lengths[index]))
            for j in (index, (index+2) % 4):
                centre = (p[j]+p[(j+1) % 4])/2
                key = tuple(np.round(centre, 8))
                count, _ = sections.get(key, (0, centre))
                sections[key] = (count+1, centre)
        ends = [point for count, point in sections.values() if count == 1]
        if len(ends) != 2:
            # Installed helper strips are connected and always have two ends;
            # malformed imported geometry cannot establish a new mouth guess.
            continue
        road = None
        for walk in walks or ():
            intervals = walk.get('commercial_driveway_owners', {}).get(owner, ())
            if not intervals:
                continue
            curb, _ = sidewalks.run_geometry(walk['pts'], walk['side'], walk.get('w', 2.5))
            arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(curb[:, :2], axis=0), axis=1))]
            station = float((intervals[0][0]+intervals[0][1])/2)
            road = np.array([np.interp(station, arc, curb[:, j]) for j in (0, 1)])-offset
            break
        if road is not None:
            rear = min(range(2), key=lambda i: np.linalg.norm(ends[i]-road))
        else:
            footprint = spec.footprint.shape() if spec.footprint is not None else Polygon(spec.ring)
            rear = max(range(2), key=lambda i: footprint.distance(Point(ends[i])))
            road = ends[rear]
        route = np.vstack((ends[1-rear], ends[rear], road))+offset
        records.append(dict(m='road_asphalt_2lane', w=float(np.median(widths)), tl=11., p=19,
                            bne_access_only=True, bne_commercial_access=True,
                            bne_commercial_owner=owner,
                            n=[[*map(float, point), 0.] for point in route]))
    return records


def resolve(items, lines, x0, y0, *, ground, walks=(), raw_walks=None, bounds=None, obstacles=()):
    """Publish a complete regeneration, preserving installed sites on failure.

    The geometry core may eagerly retire its own surfaces/cuts inside a detached
    batch. If any previously accepted owner loses its usable replacement, none
    of that batch is published: new sites cannot overlap retained old geometry.
    """
    import copy
    items = tuple(items)
    if os.environ.get('BNE_BUILDING_PATHS', 'auto') == 'off':
        return []
    walks = () if walks is None else walks
    staged_walks, staged_raw = copy.deepcopy((walks, raw_walks))
    copies = {}
    staged_items = []
    for spec, low, high in items:
        staged = copies.setdefault(id(spec), copy.copy(spec))
        staged_items.append((staged, low, high))
    previous = [(spec, copies[id(spec)]) for spec, _, _ in items if _accepted_automatic(spec.access)]
    records = _resolve_staged(staged_items, lines, x0, y0, ground=ground,
                              walks=staged_walks, raw_walks=staged_raw, bounds=bounds, obstacles=obstacles)
    if any(not _replaces_automatic(spec.access, staged.access) for spec, staged in previous):
        # AccessPlan and Layout are immutable; only diagnostics change while
        # every accepted top, marking, source seam and owned curb stays installed.
        for spec, _ in previous:
            layout = spec.access.site_layout
            notes = tuple(sorted(set((*layout.diagnostics, 'automatic_replan_retained_previous'))))
            spec.access = replace(spec.access, site_layout=replace(layout, diagnostics=notes))
        return _retained_records(items, walks, x0, y0)
    for spec, _, _ in items:
        spec.access = copies[id(spec)].access
    collections = [(walks, staged_walks)]
    if raw_walks is not None and raw_walks is not walks:
        collections.append((raw_walks, staged_raw))
    for original, staged in collections:
        for actual, replacement in zip(original, staged):
            actual.clear()
            actual.update(replacement)
    return records
