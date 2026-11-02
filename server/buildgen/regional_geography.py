"""Offline, indexed theme routing from bundled administrative/locality polygons."""
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path

PATH = Path(__file__).with_name('catalog') / 'regional_geography.json'


@dataclass(frozen=True, slots=True)
class Location:
    theme: str = ''
    source: str = ''
    locality: str = ''
    method: str = 'unresolved'
    jurisdiction: str = ''


@lru_cache(maxsize=1)
def identity():
    return hashlib.sha256(PATH.read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def _index():
    from shapely import STRtree
    from shapely.geometry import shape
    data=json.loads(PATH.read_bytes())
    if data.get('schema') != 1:
        raise ValueError('Unsupported regional geography schema')
    polygons,metadata=[],[]
    for feature in data['features']:
        geometry=shape(feature['geometry'])
        if not geometry.is_valid:
            raise ValueError('Invalid regional routing polygon')
        for polygon in (geometry.geoms if geometry.geom_type=='MultiPolygon' else (geometry,)):
            polygons.append(polygon)
            metadata.append(feature['properties'])
    return STRtree(polygons),tuple(metadata)


@lru_cache(maxsize=8192)
def locate(lat, lon):
    """Highest-specificity containing polygon; ambiguity never picks by order.

    A 500 m shoreline allowance covers generalized coastlines and small reclaimed
    areas. It cannot bridge an ocean or choose between differently themed shores.
    Inputs are exact, not rounded cell centres, so tile boundaries do not select
    a different theme. +/-180 longitude and polar locations are supported.
    """
    from shapely.geometry import Point,box
    if not isinstance(lat,(int,float)) or not isinstance(lon,(int,float)) or not math.isfinite(lat+lon) or not -90<=lat<=90:
        return Location()
    lon=(lon+180)%360-180
    tree, metadata=_index()
    points=[Point(lon,lat)]
    if lon==-180:points.append(Point(180,lat))
    hits={int(i) for point in points for i in tree.query(point,predicate='intersects')}
    method='polygon'
    if not hits:
        # Candidates within 500 m in a local tangent approximation. Geography
        # records remain immutable, and no per-building polygon transformation.
        dy=500/111320
        dx=dy/max(.02,math.cos(math.radians(lat)))
        for query_lon in (lon,lon-360,lon+360):
            point=Point(query_lon,lat)
            for i in tree.query(box(query_lon-dx,lat-dy,query_lon+dx,lat+dy)):
                from shapely.ops import clip_by_rect
                from shapely.affinity import scale
                clipped=clip_by_rect(tree.geometries[int(i)],query_lon-dx,lat-dy,query_lon+dx,lat+dy)
                metric=scale(clipped,xfact=1/dx,yfact=1/dy,origin=(query_lon,lat))
                if not metric.is_empty and metric.distance(point)<=1:
                    hits.add(int(i))
        method='shoreline_500m'
    if not hits:return Location()
    if method=='shoreline_500m':
        # Discard a country's broad default when its provincial refinement is
        # available, but never let another country's high-priority record win
        # merely because it has more administrative detail.
        by_country={}
        for i in hits:
            p=metadata[i]
            by_country.setdefault(p['jurisdiction'],[]).append(p)
        winners=[]
        for candidates in by_country.values():
            priority=max(p['priority'] for p in candidates)
            winners.extend(p for p in candidates if p['priority']==priority)
        if len({p['theme'] for p in winners})!=1:return Location(method='ambiguous_shoreline')
        winner=min(winners,key=lambda p:(p['source'],p['name']))
        return Location(winner['theme'],winner['source'],winner['name'],method,winner['jurisdiction'])
    priority=max(metadata[i]['priority'] for i in hits)
    winners=[metadata[i] for i in hits if metadata[i]['priority']==priority]
    if len({p['theme'] for p in winners})!=1:return Location(method='ambiguous_boundary')
    winner=min(winners,key=lambda p:(p['source'],p['name']))
    return Location(winner['theme'],winner['source'],winner['name'],method,winner['jurisdiction'])
