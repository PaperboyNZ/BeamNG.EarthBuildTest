"""Bounded job-local samples and detached planar reservations for legacy sites.

These frame-local helpers do not establish canonical identity or streaming owners.
"""
from dataclasses import dataclass
from itertools import islice
import math

import numpy as np
from buildgen.topology import MAX_VERTICES

MAX_CACHED_POINTS = 8192
MAX_QUERY_POINTS = 65536
MAX_RESERVATIONS = 8192


class SharedTerrainSampler:
    """Reuse exact XY observations across one planning pass, including failures.

    No rounding/quantization, interpolation, persistent storage or global cache.
    The callback and its coordinate frame must remain fixed for this instance.
    """
    def __init__(self, ground, max_cached_points=MAX_CACHED_POINTS):
        if not callable(ground):
            raise TypeError("terrain sampler requires a callback")
        if type(max_cached_points) is not int or not 0 <= max_cached_points <= MAX_CACHED_POINTS:
            raise ValueError("terrain cache exceeds the job-local point budget")
        self.ground = ground
        self.max_cached_points = max_cached_points
        self._cache = {}
        self.calls = self.sampled_points = self.cache_hits = 0

    def __call__(self, points):
        xy = np.asarray(points, dtype=float)
        if xy.ndim != 2 or xy.shape[1] != 2:
            raise ValueError("terrain query requires finite XY pairs")
        values=np.empty(len(xy),dtype=float)
        for start in range(0,len(xy),MAX_QUERY_POINTS):
            chunk=xy[start:start+MAX_QUERY_POINTS]
            if not np.isfinite(chunk).all():
                raise ValueError("terrain query requires finite XY pairs")
            values[start:start+len(chunk)]=self._sample_chunk(chunk)
        # Even setflags(write=True) cannot mutate the detached returned samples.
        return np.frombuffer(values.tobytes(), dtype=float)

    def _sample_chunk(self,xy):
        keys = [tuple(p) for p in xy]
        missing = dict.fromkeys(key for key in keys if key not in self._cache)
        self.cache_hits += len(keys) - len(missing)
        fresh = {}
        if missing:
            query = np.asarray(tuple(missing), dtype=float)
            self.calls += 1
            self.sampled_points += len(query)
            try:
                heights = np.asarray(self.ground(query), dtype=float).reshape(-1)
                if len(heights) != len(query):
                    raise ValueError("terrain callback returned the wrong sample count")
            except (OSError, ValueError):
                heights = np.full(len(query), np.nan)
            fresh = dict(zip(missing, map(float, heights)))
            for key, height in fresh.items():
                if len(self._cache) < self.max_cached_points:
                    self._cache[key] = height
        return np.asarray([self._cache[k] if k in self._cache else fresh[k] for k in keys], dtype=float)

    @property
    def cached_points(self):
        return len(self._cache)


def terrain_sampler(ground):
    """Wrap once at the runtime planning boundary; preserve None and wrappers."""
    return ground if ground is None or isinstance(ground, SharedTerrainSampler) else SharedTerrainSampler(ground)


@dataclass(frozen=True, slots=True)
class SurfaceReservation:
    owner: str
    kind: str
    outer: tuple
    holes: tuple = ()

    def __post_init__(self):
        if type(self.owner) is not str or not self.owner or len(self.owner) > 1024:
            raise ValueError("reservation requires a bounded local owner label")
        if type(self.kind) is not str or not self.kind or len(self.kind) > 64:
            raise ValueError("reservation requires a bounded semantic kind")
        def ring(values):
            values=tuple(islice(iter(values),MAX_VERTICES+2))
            if len(values)>MAX_VERTICES+1:raise ValueError('reservation exceeds vertex budget')
            result=[]
            for point in values:
                pair=tuple(islice(iter(point),3))
                if len(pair)!=2:raise ValueError('reservation requires XY coordinate pairs')
                p=tuple(float(v)+0. for v in pair)
                if not all(math.isfinite(v) for v in p):raise ValueError('reservation requires finite coordinates')
                result.append(p)
            if len(result)>1 and result[0]==result[-1]:result.pop()
            if len(result)<3:raise ValueError('reservation requires a polygon ring')
            return tuple(result)
        outer=ring(self.outer)
        holes=[];count=len(outer)
        for hole in self.holes:
            h=ring(hole);count+=len(h)
            if count>MAX_VERTICES:raise ValueError('reservation exceeds vertex budget')
            holes.append(h)
        holes=tuple(holes)
        object.__setattr__(self,"outer",outer)
        object.__setattr__(self,"holes",holes)
        shape=self.shape()
        if shape.is_empty or not shape.is_valid or shape.area<=0:raise ValueError('invalid reservation polygon')

    def shape(self):
        from shapely.geometry import Polygon
        return Polygon(self.outer,self.holes)


def overlaps(a, b, tolerance=1e-7):
    """Contact at an edge is allowed; positive planar area is a reservation hit."""
    return a.intersection(b).area > tolerance


def contains_known_site(spec, shape):
    """No site keeps existing narrow-frontage behavior; unknown inventory fails."""
    site = getattr(spec, "site", None)
    if site is None:
        return True
    exclusions = getattr(site, "exclusions", None)
    boundary = getattr(site, "boundary", None)
    if exclusions is None or boundary is None:
        return False
    return boundary.shape().covers(shape) and not any(overlaps(shape, fp.shape()) for fp in exclusions)
