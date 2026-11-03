"""Topology-preserving source selection for the experimental generator."""
import logging
import os

import numpy as np
import mapgeom
from .topology import Footprint, InvalidFootprint

log = logging.getLogger(__name__)


def enabled():
    import building_settings
    return building_settings.current() == "v2"


def components(f, i):
    # Decoded feature tables are immutable, as for Features.xy_in/outer_centres.
    # Cache source validation and canonicalization across neighbouring tile jobs.
    memo = f.__dict__.setdefault("_bnge_v2_components", {})
    if i in memo:
        return memo[i]
    out = {}
    for rings in f.parts(i):
        if not rings:
            continue
        try:
            # Source coordinate validation also rejects overlapping/outside holes.
            fp = Footprint(rings[0], tuple(rings[1:]))
            out[fp.component_key()] = (fp.outer, *fp.holes)
        except InvalidFootprint as exc:
            ids = getattr(f, "ids", None)
            log.warning("Skipping invalid building component %s: %s", ids[i] if ids is not None else i, exc)
    result = tuple(sorted(out.items()))
    memo[i] = result
    return result


def rows(f, indices, parts_of):
    """(row, dedup key, source ID, component rings, owner ring).

    Every disconnected component belongs to the same owner tile, selected from
    canonical source geometry. This avoids duplicate mapped parts and dependence
    on multipolygon order. Selection does not depend on the requested tile.
    """
    ids = getattr(f, "ids", None)
    for i in indices:
        source = ids[i] if ids is not None else None
        if not enabled():
            pp = f.parts(i)
            if pp and pp[0]:
                yield i, source, source, pp[0], None
            continue
        cc = components(f, i)
        if not cc:
            continue
        if source is None or not str(source):
            source = "geometry:" + ":".join(key for key, _ in cc)
        owner = cc[0][1][0]
        parts = parts_of.get(str(source))
        if parts and any(p[1] is not None for p in parts):
            cc = cc[:1]  # the complete part collection replaces the parent once
        for key, rings in cc:
            yield i, (str(source), key), source, rings, owner


def project(f, frame, rings, x0=0., y0=0.):
    def ring(points):
        e, n = mapgeom.enu_xy(f, frame, np.asarray(points, np.float64))
        return np.stack([np.asarray(e) - x0, np.asarray(n) - y0], 1)
    return Footprint(ring(rings[0]), tuple(ring(h) for h in rings[1:]))
