"""Pinned, source-linked property evidence. No inferred cadastral boundaries."""
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
from .topology import Footprint


@dataclass(frozen=True, slots=True)
class Port:
    kind: str
    a: tuple
    b: tuple


@dataclass(frozen=True, slots=True)
class Site:
    id: str
    revision: str
    boundary: Footprint
    exclusions: tuple[Footprint, ...]
    ports: tuple[Port, ...]
    dock_rise: float | None = None
    owner_footprint: Footprint | None = None


@lru_cache(maxsize=1)
def catalogue():
    path=os.environ.get('BNE_BUILDING_SITES')
    if not path:
        return 'none',{}
    if Path(path).stat().st_size>16*1024*1024:
        raise ValueError('building sites catalogue exceeds 16 MiB')
    raw=Path(path).read_bytes()
    data=json.loads(raw)
    if data.get('type')!='FeatureCollection' or not isinstance(data.get('features'),list) or len(data['features'])>10000:
        raise ValueError('building sites require a bounded GeoJSON FeatureCollection')
    rows={}
    def polygon(g):
        if g.get('type')!='Polygon':
            raise ValueError('site boundaries/exclusions must be Polygon')
        rings=g['coordinates']
        if not isinstance(rings,list) or not rings or any(not isinstance(r,list) or len(r)<4 for r in rings):
            raise ValueError('site polygons require closed rings with at least four coordinates')
        if any(r[0]!=r[-1] for r in rings):
            raise ValueError('site polygon rings must be closed')
        if sum(map(len,rings))>128:
            raise ValueError('site polygon exceeds 128 coordinates')
        for ring in rings:
            for p in ring:
                if len(p)!=2 or not all(math.isfinite(v) for v in p) or not -180<=p[0]<=180 or not -85<=p[1]<=85:
                    raise ValueError('site polygons require finite WGS84 longitude/latitude')
        fp=Footprint(rings[0],tuple(rings[1:]))
        if max(x for x,y in fp.outer)-min(x for x,y in fp.outer)>1:
            raise ValueError('split oversized or dateline-spanning sites')
        return fp.shape()
    boundaries=[];identities=set()
    for feature in data['features']:
        p=feature['properties']
        for field in ('site_id','owner_id','source','release'):
            if not isinstance(p.get(field),str) or not p[field].strip():
                raise ValueError('missing site provenance: '+field)
        if p.get('obstacles_complete') is not True:
            raise ValueError('site requires a complete declared exclusion inventory')
        if p['owner_id'] in rows:
            raise ValueError('duplicate site owner')
        if p['site_id'] in identities:
            raise ValueError('duplicate site identity')
        identities.add(p['site_id'])
        boundaries.append(polygon(feature['geometry']))
        if len(p.get('exclusions',()))>32 or len(p.get('ports',()))>8:
            raise ValueError('site exceeds exclusion/port budget')
        for g in p.get('exclusions',()):
            polygon(g)
        for port in p.get('ports',()):
            if port.get('kind') not in ('service','parking','pedestrian') or len(port.get('coordinates',()))!=2:
                raise ValueError('site port requires a role and two measured endpoints')
            for q in port['coordinates']:
                if len(q)!=3 or not all(math.isfinite(v) for v in q) or not -180<=q[0]<=180 or not -85<=q[1]<=85:
                    raise ValueError('port endpoints require longitude, latitude, ellipsoidal elevation')
        rise=p.get('dock_rise')
        if rise is not None and (not isinstance(rise,(int,float)) or not .8<=rise<=1.5):
            raise ValueError('dock_rise must be 0.8–1.5 m above resolved building base')
        rows[p['owner_id']]=feature
    from shapely import STRtree
    index=STRtree(boundaries)
    for i,boundary in enumerate(boundaries):
        hits=index.query(boundary)
        if len(hits)>64:
            raise ValueError('site ownership overlap query exceeds budget')
        if any(j<i and boundary.intersection(boundaries[int(j)]).area>1e-16 for j in hits):
            raise ValueError('overlapping properties require one explicit site owner')
    return hashlib.sha256(raw).hexdigest(),rows


def project(owner, frame, x0=0., y0=0., owner_footprint=None):
    digest,rows=catalogue()
    feature=rows.get(str(owner))
    if feature is None:
        return None
    def xy(points):
        p=np.asarray(points,float)
        x,y,z=frame.geodetic_to_enu(p[:,1],p[:,0],p[:,2] if p.shape[1]==3 else np.zeros(len(p)))
        return np.column_stack((x-x0,y-y0,z))
    def fp(g):
        rings=[xy(r)[:,:2] for r in g['coordinates']]
        return Footprint(rings[0],tuple(rings[1:]))
    p=feature['properties']
    ports=[]
    for row in p.get('ports',()):
        a,b=xy(row['coordinates'])
        ports.append(Port(row['kind'],tuple(a),tuple(b)))
    boundary=fp(feature['geometry'])
    from shapely.geometry import Point
    for port in ports:
        if not 1.2<=math.dist(port.a[:2],port.b[:2])<=12.:
            raise ValueError('site port width must be 1.2–12 m')
        if any(boundary.shape().boundary.distance(Point(q[:2]))>.1 for q in (port.a,port.b)):
            raise ValueError('site port endpoints must lie on the supplied property boundary')
    return Site(p['site_id'],digest,boundary,tuple(fp(g) for g in p.get('exclusions',())),
                tuple(sorted(ports,key=lambda q:(q.kind,q.a,q.b))),p.get('dock_rise'),owner_footprint)


def project_record(owner, frame, x0=0., y0=0., owner_footprint=None):
    """Live compatibility boundary, after the unchanged catalogue/project checks.

    Catalogue owner IDs are explicit join keys, not newly inferred provider IDs.
    Original projected XY and measured XYZ remain in their declared frame.
    This route does not enable shared or multi-level site generation.
    """
    site = project(owner, frame, x0, y0, owner_footprint)
    if site is None:
        return None
    from sitegen.adapters import adapt_validated_legacy_site
    from sitegen.identity import GeographicFrame, SourceIdentity
    from sitegen.plan import EntityRef, FrameContext
    # The old catalogue permits identifiers outside the detached contract's text
    # budget/convention. Preserve that valid old site's geometry and diagnose the
    # unsupported migration rather than failing a whole physical tile.
    try:
        owner_identity = SourceIdentity('beamng-earth/site-catalogue-owner', str(owner))
        SourceIdentity('beamng-earth/site-catalogue', site.id)
    except ValueError as exc:
        import logging
        logging.getLogger(__name__).warning('Site record migration retained legacy input: %s', exc)
        return site
    context = FrameContext('legacy_projected_xy',
                           GeographicFrame(float(frame.lon0), float(frame.lat0), float(frame.h0)),
                           float(x0), float(y0))
    return adapt_validated_legacy_site(site,
        owner=EntityRef(owner_identity, 'building'),
        frame=context, source_namespace='beamng-earth/site-catalogue')
