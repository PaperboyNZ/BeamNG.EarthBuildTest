"""Cheap profile detail, separate from the physically rounded plan outline.

Very Low/Low retain the native single-bevel profile, with no smoothing pass or
added profile triangles. Medium and higher add curved profile detail. Straight
paths gain no stations. The physical rounded XY outline is a separate recipe.
"""
from functools import lru_cache
import numpy as np

REVISION = 'tiered-nose-v3-native-4-6'


def enabled(quality):
    return quality != 'minimum'


def spans(quality):
    return 1 if quality in ('very_low', 'low') else 4 if quality == 'medium' else 6


@lru_cache(maxsize=3)
def _template(count):
    return np.linspace(0., 1., count+1)[None, :, None]


def _nose(mesh, bottom, low, high, low_uv, high_uv, rows, count, endpoint_ids):
    p, t, uv, m = mesh
    stations = len(low)
    if stations < 2 or not len(rows):
        return mesh, None
    rise = high[:, 2]-low[:, 2]
    face_rise = low[:, 2]-bottom[:, 2]
    control = low+(low-bottom)*(rise/np.maximum(face_rise, 1e-9))[:, None]
    control[:, 2] = high[:, 2]
    a = _template(count)
    curve = (1.-a)**2*low[:, None]+2*a*(1.-a)*control[:, None]+a*a*high[:, None]
    texture = (1.-a)*low_uv[:, None]+a*high_uv[:, None]
    # Reuse native endpoints and append only the intermediate profile samples.
    # No superseded strip vertices or later whole-mesh compaction are needed.
    ring = np.empty((stations, count+1), np.int64)
    ring[:, 0], ring[:, -1] = endpoint_ids[:, 0], endpoint_ids[:, 1]
    ring[:, 1:-1] = np.arange(stations*(count-1)).reshape(stations, count-1)+len(p)
    aa, bb, cc, dd = ring[:-1, :-1], ring[1:, :-1], ring[1:, 1:], ring[:-1, 1:]
    faces = np.stack((np.stack((aa, bb, cc), -1), np.stack((aa, cc, dd), -1)), -2).reshape(-1, 3)
    vertices = np.vstack((p, curve[:, 1:-1].reshape(-1, 3)))
    old = p[t[rows]]
    reference = np.cross(old[:, 1]-old[:, 0], old[:, 2]-old[:, 0]).sum(axis=0)
    q = vertices[faces]
    normal = np.cross(q[:, 1]-q[:, 0], q[:, 2]-q[:, 0]).sum(axis=0)
    if normal@reference < 0:
        faces = faces[:, ::-1]
    keep = np.ones(len(t), bool)
    keep[rows] = False
    return (vertices, np.vstack((t[keep], faces)), np.vstack((uv, texture[:, 1:-1].reshape(-1, 2))),
            np.r_[m[keep], np.zeros(len(faces), np.int64)]), curve


def native_visual(mesh, piece, origin, quality='high'):
    """Run after native corner repairs, before surface UV conversion."""
    import sidewalks as sw
    from vehicle_crossings import combine
    p, t, uv, m = mesh
    if not len(t) or spans(quality) == 1:
        return mesh
    count = spans(quality)
    k = int(np.flatnonzero(np.abs(uv[:, 1]-sw.V_BAND_LOW) > 1e-10)[0])
    rows = np.flatnonzero(np.all((t >= 2*k) & (t < 4*k), axis=1))
    result, curve = _nose(mesh, p[:k], p[k:2*k], p[3*k:4*k],
                          uv[2*k:3*k], uv[3*k:4*k], rows, count,
                          np.c_[2*k+np.arange(k), 3*k+np.arange(k)])
    if curve is None or piece[0] != 0:
        return result
    # Fill the tiny crescent between the old cap chamfer and the profile
    # curve. The cap itself already follows the rounded physical XY outline.
    patches = []
    cap_offset = 14*k
    for end, cap in enumerate(piece[7]):
        if not cap:
            continue
        index = 0 if end == 0 else k-1
        cap_p, cap_uv = p[cap_offset:cap_offset+8], uv[cap_offset:cap_offset+8]
        cap_offset += 8
        q = curve[index]
        across = np.linalg.norm(q[:, :2]-cap_p[0, :2], axis=1)
        width = np.linalg.norm(cap_p[2, :2]-cap_p[1, :2])
        frac = (across-np.linalg.norm(cap_p[1, :2]-cap_p[0, :2]))/max(width, 1e-12)
        tex = cap_uv[1]+frac[:, None]*(cap_uv[2]-cap_uv[1])
        tex[:, 1] = cap_uv[1, 1]+(q[:, 2]-cap_p[1, 2])/max(cap_p[2, 2]-cap_p[1, 2], 1e-12)*(cap_uv[2, 1]-cap_uv[1, 1])
        faces = np.array([[0, j, j+1] for j in range(1, count)], np.int64)
        tangent = piece[1][1 if end == 0 else -1]-piece[1][0 if end == 0 else -2]
        want = tangent*(-1 if end == 0 else 1)
        normal = np.cross(q[faces[:, 1]]-q[faces[:, 0]], q[faces[:, 2]]-q[faces[:, 0]])
        reverse = normal@want < 0
        faces[reverse] = faces[reverse, ::-1]
        patches.append((q, faces, tex, np.zeros(len(faces), np.int64)))
    return combine(result, patches)


def vehicle_visual(mesh, positions, cols, stations, endpoint_ids, quality='high'):
    """Same small direct profile on driveway shoulders, with whole-mesh fallback."""
    import sidewalks as sw
    import sidewalk_outline as outline
    if spans(quality) == 1:
        return mesh
    p, t, uv, m = mesh
    count = len(positions)//cols
    if count > outline.limits(quality)[0] or not np.isfinite(positions).all():
        return mesh
    indices = np.arange(count)*cols
    nose = (m == 0) & np.all(np.isclose(uv[t, 1], sw.V_LIGHT_LOW) |
                            np.isclose(uv[t, 1], sw.V_BAND_TOP-.02), axis=1)
    rows = np.flatnonzero(nose)
    low_uv = np.c_[stations/sw.CURB_REPEAT_M, np.full(count, sw.V_LIGHT_LOW)]
    high_uv = low_uv.copy()
    high_uv[:, 1] = sw.V_BAND_TOP-.02
    return _nose(mesh, positions[indices], positions[indices+1], positions[indices+2],
                 low_uv, high_uv, rows, spans(quality), endpoint_ids)[0]
