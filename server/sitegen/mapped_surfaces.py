"""Bounded cached painted-surface polygons in the road content's current frame.

No map-data fetch, facility inference or geometry repair. ``surface.lots`` is the
existing non-waiting cached service; ``extra_pads`` supplies current runway pads.
"""
from itertools import islice

import numpy as np
from shapely.geometry import Polygon, box

MAX_TABLES = 64
MAX_FEATURES = 10000
MAX_POLYGONS = 2048
MAX_VERTICES = 131072
MAX_RING_VERTICES = 4096


class _Unresolved(ValueError):
    pass


def collect(frame,bounds,surface):
    """Return ``((kind, polygon), ...)`` in current-frame XY, clipped to bounds.

    Source hole handling follows current rendering: terrain/photo painters fill
    parking/plaza holes, so exclusions do too. A hole in the raised plaza skin
    still exposes paved terrain underneath, not confirmed green ground.
    Overflow or a failed/invalid relevant input returns one whole-bounds
    ``hardscape`` exclusion. An empty cached service result remains empty.
    ``frame`` uses geodesy.EnuFrame's latitude-first vector conversion API.
    """
    bounds=tuple(float(v) for v in bounds)
    if len(bounds)!=4 or not np.isfinite(bounds).all() or bounds[2]<=bounds[0] or bounds[3]<=bounds[1]:
        raise ValueError('mapped surfaces require finite ordered XY bounds')
    clip=box(*bounds)
    if surface is None:return ()
    import surface as surface_module
    result=[];seen=set();vertices=features=0

    def limited(values,limit):
        values=tuple(islice(iter(values),limit+1))
        if len(values)>limit:raise _Unresolved('mapped surface budget')
        return values

    def project(ring):
        nonlocal vertices
        points=np.asarray(limited(ring,MAX_RING_VERTICES),dtype=float)
        if points.ndim!=2 or points.shape[1]!=2 or len(points)<3 or not np.isfinite(points).all():
            raise _Unresolved('invalid mapped surface ring')
        vertices+=len(points)
        if vertices>MAX_VERTICES:raise _Unresolved('mapped surface vertex budget')
        if np.any(abs(points[:,0])>180) or np.any(abs(points[:,1])>90):
            raise _Unresolved('mapped surface source coordinates require longitude/latitude')
        x,y,_=frame.geodetic_to_enu(points[:,1],points[:,0],np.zeros(len(points)))
        xy=np.column_stack((x,y))
        if not np.isfinite(xy).all():raise _Unresolved('invalid projected surface')
        return xy

    def add(kind,outer,holes=()):
        shape=Polygon(project(outer),[project(h) for h in limited(holes,MAX_RING_VERTICES//3)])
        if shape.is_empty or not shape.is_valid:raise _Unresolved('invalid mapped surface polygon')
        if not shape.intersects(clip):return
        shape=shape.intersection(clip)
        pieces=(shape,) if shape.geom_type=='Polygon' else getattr(shape,'geoms',())
        for piece in pieces:
            if piece.geom_type!='Polygon' or piece.area<=1e-8:continue
            key=(kind,piece.wkb)
            if key in seen:continue
            if len(result)>=MAX_POLYGONS:raise _Unresolved('mapped surface polygon budget')
            seen.add(key);result.append((kind,piece))

    x0,y0,x1,y1=bounds
    x=np.array((x0,x1,x0,x1,(x0+x1)/2))
    y=np.array((y0,y0,y1,y1,(y0+y1)/2))
    try:
        lat,lon,_=frame.enu_to_geodetic(x,y,np.zeros(5))
        lat,lon=np.asarray(lat,float),np.asarray(lon,float)
        if not np.isfinite(lat).all() or not np.isfinite(lon).all():raise _Unresolved('invalid surface query')
        service=getattr(surface,'lots',None)
        tables=limited(service(lat,lon),MAX_TABLES) if callable(service) else ()
        for table in tables:
            if table is None:continue
            count=len(table.kind);features+=count
            if features>MAX_FEATURES:raise _Unresolved('mapped surface feature budget')
            parking=surface_module._parking(table)
            plazas=surface_module._plazas(table)
            yards=surface_module._yards(table)
            for selected,kind in ((parking,'parking'),(plazas,'plaza'),(yards,'yard')):
                if selected is None:continue
                for index in np.flatnonzero(np.asarray(selected,bool)&(table.kind==3)):
                    for part in limited(table.parts(int(index)),MAX_POLYGONS):
                        part=limited(part,MAX_RING_VERTICES//3)
                        if not part:raise _Unresolved('missing mapped surface ring')
                        # All existing ground painters draw outer rings only.
                        # Plaza mesh holes still expose that painted ground.
                        wire_kind={'parking':'parking','plaza':'pavement','yard':'hardscape'}[kind]
                        add(wire_kind,part[0])
        extra=getattr(surface,'extra_pads',None)
        if callable(extra):
            for latitudes,longitudes in limited(extra(lat,lon),MAX_POLYGONS):
                latitudes=limited(latitudes,MAX_RING_VERTICES)
                longitudes=limited(longitudes,MAX_RING_VERTICES)
                if len(latitudes)!=len(longitudes):raise _Unresolved('runway pad coordinate mismatch')
                add('road',np.column_stack((longitudes,latitudes)))
    except Exception:
        return (('hardscape',clip),)
    return tuple(result)
