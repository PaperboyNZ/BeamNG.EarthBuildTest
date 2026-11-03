"""Export accepted hard surfaces for order-independent natural-prop exclusion.

Coordinates are in the road content's frame, not building-local XY. Soft planted
cover is intentionally absent. This record does not own or modify physical meshes.
"""
import math
from shapely import make_valid
import numpy as np
from shapely.geometry import Polygon, LineString, box as shape_box

MAX_POLYGONS = 8192
MAX_VERTICES = 131072
SOFT = frozenset(('lawn_margin', 'garden_bed', 'gravel_margin',
                  'site_lawn_margin', 'site_garden_bed', 'site_gravel_margin'))


def collect(items=(), drives=(), walks=(), *, chunks=(), origin=(0., 0.), ground=None,
            frame=None, fuel_pads=(), bounds=None, mapped_polygons=(), clearance=()):
    """Versioned JSON data with exact polygon holes and finite height intervals."""
    origin = np.asarray(origin[:2], dtype=float)
    clip = shape_box(*bounds) if bounds is not None else None
    records = []
    vertices = 0
    overflow = False
    pending = []
    pending_vertices = 0

    def add(shape, z, kind):
        nonlocal vertices, overflow
        if shape.is_empty or not shape.is_valid:
            return
        if clip is not None:
            shape = shape.intersection(clip)
        parts = [shape] if shape.geom_type == 'Polygon' else getattr(shape, 'geoms', ())
        z = np.asarray(z, dtype=float).reshape(-1)
        known = bool(len(z) and np.isfinite(z).all())
        low, high = ((float(z.min())-.1, float(z.max())+.4) if known
                     else (-1000000., 1000000.))
        for p in parts:
            if p.geom_type != 'Polygon' or p.area <= 1e-8:
                continue
            rings = [list(p.exterior.coords)[:-1], *(list(r.coords)[:-1] for r in p.interiors)]
            count = sum(map(len, rings))
            if len(records) >= MAX_POLYGONS or vertices+count > MAX_VERTICES:
                overflow = True
                return
            records.append(dict(rings=[[[float(x),float(y)] for x,y in r] for r in rings],
                                min_z=low, max_z=high, kind=kind))
            if not known:
                records[-1]['unknown_height'] = True
            vertices += count

    def draped(shape, xy, kind):
        nonlocal overflow, pending_vertices
        if len(pending) >= MAX_POLYGONS or pending_vertices+len(xy)>MAX_VERTICES:
            overflow = True
        else:
            pending.append((shape, np.asarray(xy, dtype=float), kind))
            pending_vertices += len(xy)

    for spec, _, _ in items or ():
        access = getattr(spec, 'access', None)
        if access is not None:
            # Accepted physical paths, steps, drives, parking and paved margins.
            # Lawn/beds belong to access.landscape and are never blanket-masked.
            for solid in access.solids:
                if solid.kind in SOFT:
                    continue
                p = np.asarray(solid.top, dtype=float)
                add(Polygon(p[:,:2]+origin), p[:,2], 'hardscape')
            for solid in access.landscape:
                if solid.kind in ('paved_margin', 'site_paved_margin'):
                    p = np.asarray(solid.top, dtype=float)
                    add(Polygon(p[:,:2]+origin), p[:,2], 'pavement')
        garage = getattr(spec, 'garage_access', None)
        if garage is not None and garage.status == 'connected':
            for solid in garage.surfaces:
                p = np.asarray(solid.top, dtype=float)
                add(Polygon(p[:,:2]+origin), p[:,2], 'driveway')
    for drive in drives or ():
        if drive.get('bne_access_only'):
            continue  # the accepted garage's exact apron is already included
        nodes = np.asarray(drive.get('n', ()), dtype=float)
        width = float(drive.get('w', 0.))
        if nodes.ndim != 2 or len(nodes)<2 or not math.isfinite(width) or width<=0:
            continue
        # Each segment retains its local height range; no tall slope-wide mask.
        for a,c in zip(nodes,nodes[1:]):
            if np.linalg.norm(c[:2]-a[:2]) < 1e-7:
                continue
            p = LineString((a[:2],c[:2])).buffer(width/2, cap_style='flat', join_style='mitre')
            xy = np.asarray(p.exterior.coords)[:-1]
            draped(p, xy, 'driveway')
    if chunks:
        # Reuse the exact road-ribbon edge solver: lane widths, mitered joins and
        # raised deck heights match the actual renderer rather than class guesses.
        import roadmesh
        visible = [c for c in chunks if not c.get('tube_only')]
        for (left,right,_,_,_,fixed), _chunk in roadmesh.ribbon_pairs(visible):
            for i in range(len(left)-1):
                xy = np.array([left[i],left[i+1],right[i+1],right[i]])
                shape = Polygon(xy)
                if fixed is None:
                    draped(shape,xy,'road')
                else:
                    add(shape,np.asarray(fixed)[i:i+2],'road')
        for chunk in visible:
            if chunk.get('poly'):
                xy = np.asarray(chunk['poly'],dtype=float)[:,:2]
                draped(Polygon(xy),xy,'pavement')
    import sidewalks
    for walk in walks or ():
        if 'corner' in walk:
            corner = walk['corner']
            p = np.concatenate((np.asarray(corner['arc']),np.asarray(corner['outer'])))
            add(Polygon(p[:,:2]), p[:,2], 'footpath')
            continue
        width = float(walk.get('w', 2.5))
        curb, outward = sidewalks.run_geometry(walk['pts'], walk['side'], width)
        profile = sidewalks.profile(h=float(walk.get('curb_h',sidewalks.CURB_H)),w=width)
        # Include the visible sloping back skin beyond the nominal slab width.
        # Vehicle crossings lower the inner curb, leaving this outer extent.
        back = curb[:,:2]+outward*float(profile[:,0].max())
        for i in range(len(curb)-1):
            p = np.array([curb[i,:2],curb[i+1,:2],back[i+1],back[i]])
            z = curb[i:i+2,2,None]+profile[None,:,1]
            shape=make_valid(Polygon(p))
            for garden in walk.get('tree_gardens',()):
                hole=Polygon(np.asarray(garden['ring'])[:,:2])
                if hole.is_valid:shape=shape.difference(hole)
            add(shape, z, 'footpath')
    if frame is not None:
        for _, polygons in fuel_pads or ():
            for lat,lon in polygons:
                x,y,_ = frame.geodetic_to_enu(np.asarray(lat),np.asarray(lon),0.)
                xy = np.column_stack((x,y))
                draped(Polygon(xy),xy,'fuel')
    for kind, shape in mapped_polygons:
        if clip is not None:
            shape = shape.intersection(clip)
        parts = [shape] if shape.geom_type == 'Polygon' else getattr(shape,'geoms',())
        for p in parts:
            if p.geom_type != 'Polygon' or p.is_empty or not p.is_valid:
                continue
            xy = np.concatenate([np.asarray(p.exterior.coords)[:-1],
                                 *(np.asarray(r.coords)[:-1] for r in p.interiors)])
            draped(p,xy,kind)
    for shape in clearance:
        xy = np.asarray(shape.exterior.coords)[:-1]
        draped(shape,xy,'access')
    if pending:
        samples = np.concatenate([xy for _,xy,_ in pending])
        try:
            from .surfaces import terrain_sampler
            sampler = terrain_sampler(ground)
            heights = sampler(samples) if sampler is not None else np.full(len(samples),np.nan)
        except (OSError, ValueError, TypeError):
            heights = np.full(len(samples),np.nan)
        offset = 0
        for shape,xy,kind in pending:
            add(shape,heights[offset:offset+len(xy)],kind)
            offset += len(xy)
    if overflow:
        # Never silently truncate protection. Extreme optional vegetation is
        # deferred for this tile; the physical geometry is still complete.
        if bounds is None:
            shapes = [Polygon(r['rings'][0],r['rings'][1:]) for r in records]
            if shapes:
                bounds = (min(s.bounds[0] for s in shapes),min(s.bounds[1] for s in shapes),
                          max(s.bounds[2] for s in shapes),max(s.bounds[3] for s in shapes))
        if bounds is not None:
            x0,y0,x1,y1 = map(float,bounds)
            records = [dict(rings=[[[x0,y0],[x1,y0],[x1,y1],[x0,y1]]],
                            min_z=-1000000.,max_z=1000000.,kind='access' if clearance else 'hardscape',unknown_height=True)]
    return dict(v=1,polygons=records)
