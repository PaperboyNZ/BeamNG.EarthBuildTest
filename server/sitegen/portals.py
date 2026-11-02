"""Detached frame-local street proposals; no persistent identity or emission."""
from dataclasses import dataclass
import math

import numpy as np

VERSION=1
MAX_CANDIDATES=4
OWNER_TOKEN_PREFIX='driveway_owner_token:'


def installed_owner(spec):
    """Existing field preserves a local installed resource token without schema changes."""
    access=getattr(spec,'access',None)
    return next((note[len(OWNER_TOKEN_PREFIX):] for note in access.diagnostics
                 if note.startswith(OWNER_TOKEN_PREFIX)),None) if access is not None else None


def simplified_lines(lines):
    """Planning-only removal of redundant nodes; retain all per-line evidence.

    Full coordinate dimensions participate, so a supplied height/grade break is
    not flattened. The source renderer still receives its original geometry.
    """
    import sidewalks
    result=[]
    for line in lines:
        points=np.asarray(line[0],dtype=float)
        if points.size==0:continue
        if points.ndim!=2 or points.shape[1]<2:raise ValueError('street line requires coordinates')
        if len(points)<2:continue
        kept=points[sidewalks.simplify(points,tol=1e-6)]
        detached=np.frombuffer(kept.tobytes(),dtype=float).reshape(kept.shape)
        result.append((detached,*line[1:]))
    return tuple(result)


def _finite(value):
    if isinstance(value,bool) or not isinstance(value,(int,float,np.number)) or not math.isfinite(value):
        raise ValueError('street proposals require finite numeric values')
    return float(value)+0.


def _freeze(value):
    if isinstance(value,np.ndarray):return _freeze(value.tolist())
    if isinstance(value,(tuple,list)):return tuple(_freeze(v) for v in value)
    if value is None:return None
    if isinstance(value,(int,np.integer)) and not isinstance(value,bool):return int(value)
    return _finite(value)


@dataclass(frozen=True,slots=True)
class StreetPortal:
    kind: str
    end: tuple
    tangent: tuple
    width: float
    distance: float
    height: float | None = None
    crossfall: float = 0.
    crossing: tuple | None = None
    rear: tuple = ()

    def __post_init__(self):
        if self.kind not in ('sidewalk','road'):raise ValueError('unsupported street interface')
        for name in ('end','tangent'):
            values=tuple(round(_finite(v),9) for v in getattr(self,name))
            if len(values)!=2:raise ValueError('street interface requires XY vectors')
            object.__setattr__(self,name,values)
        for name in ('width','distance','crossfall'):
            object.__setattr__(self,name,round(_finite(getattr(self,name)),12 if name=='crossfall' else 9))
        if self.width<=0 or self.distance<=0:raise ValueError('street interface requires positive dimensions')
        if abs(math.hypot(*self.tangent)-1)>1e-7:raise ValueError('street tangent must be normalized')
        if self.height is not None:object.__setattr__(self,'height',round(_finite(self.height),9))
        if self.crossing is not None:
            values=tuple(self.crossing)
            if len(values)!=3 or type(values[0]) is not int or values[0]<0:raise ValueError('invalid sidewalk reference')
            object.__setattr__(self,'crossing',(values[0],_finite(values[1]),_finite(values[2])))
        rear=tuple(tuple(round(_finite(v),9) for v in p) for p in self.rear)
        if rear and (not 3<=len(rear)<=17 or any(len(p)!=3 for p in rear)):
            raise ValueError('curved portal requires bounded rear XYZ samples')
        object.__setattr__(self,'rear',rear)

    @property
    def rank_key(self):
        # Geometry is a local deterministic ordering key, never a cache identity.
        return (self.kind!='sidewalk',round(self.distance,9),tuple(round(v,9) for v in self.end),
                tuple(round(v,9) for v in self.tangent),round(self.width,9),
                (self.height is None,0. if self.height is None else round(self.height,9)),round(self.crossfall,9))


def ranked(proposals):
    retained=[]
    for proposal in proposals:
        if type(proposal) is not StreetPortal:raise TypeError('expected detached StreetPortal')
        # Different caller-local crossing references are not deduplicated merely
        # because endpoints coincide; their source restrictions may differ.
        if proposal in retained:continue
        retained.append(proposal)
        retained.sort(key=lambda p:(p.rank_key,p.crossing or ()))
        del retained[MAX_CANDIDATES:]
    return tuple(retained)


@dataclass(frozen=True,slots=True)
class RouteProposal:
    portal: StreetPortal
    sections: tuple
    branch: tuple | None = None
    mode: str = 'connected'

    def __post_init__(self):
        if type(self.portal) is not StreetPortal:raise TypeError('route requires a street proposal')
        points=np.asarray(self.sections,float)
        if points.ndim!=3 or points.shape[2]!=2 or not 3<=points.shape[1]<=17 or not 2<=len(points)<=33 or not np.isfinite(points).all():
            raise ValueError('route requires bounded left/centre/right XY sections')
        if self.mode not in ('connected','crossing_only'):raise ValueError('unsupported route mode')
        object.__setattr__(self,'sections',_freeze(points))
        object.__setattr__(self,'branch',_freeze(self.branch))
