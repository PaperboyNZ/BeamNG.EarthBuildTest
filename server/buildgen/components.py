"""Bounded, immutable construction templates stamped into existing mesh batches.

Keys contain geometry only. Position, wall orientation and paint stay per instance;
there are no new TSStatics or material instances. Facade callers normalize
subtraction roundoff at 1e-12 metres so identical dimensions reuse a template.
"""
from functools import lru_cache, cached_property
from dataclasses import dataclass
import math
import numpy as np

UV = ((0., 0.), (1., 0.), (1., 1.), (0., 1.))


@dataclass(frozen=True, eq=False)
class Template:
    point_rows: tuple
    uv_rows: tuple
    triangle_rows: tuple
    unique: tuple
    indices: tuple
    flat_uv: tuple
    flat_triangles: tuple

    @cached_property
    def points(self):
        rows=self.point_rows or tuple(self.unique[i] for i in self.indices)
        a=np.asarray(rows,np.float64);a.flags.writeable=False;return a

    @cached_property
    def uvs(self):
        a=np.asarray(self.uv_rows,np.float64);a.flags.writeable=False;return a

    @cached_property
    def triangles(self):
        a=np.asarray(self.triangle_rows,np.int64);a.flags.writeable=False;return a

    def __iter__(self):
        return iter((self.points, self.uvs, self.triangles))


def _template(points, uvs, triangles):
    points,uvs,triangles=tuple(map(tuple,points)),tuple(map(tuple,uvs)),tuple(map(tuple,triangles))
    lookup, unique, indices = {}, [], []
    for point in points:
        point = tuple(point)
        if point not in lookup:
            lookup[point] = len(unique)
            unique.append(point)
        indices.append(lookup[point])
    return Template(points,uvs,triangles,tuple(unique),tuple(indices),
                    tuple(v for uv in uvs for v in uv),tuple(i for t in triangles for i in t))


def _quads(faces, uvs=None):
    points, tex, tris = [], [], []
    for k,face in enumerate(faces):
        i = len(points)
        points.extend(face)
        tex.extend(UV if uvs is None else uvs[k])
        tris.extend(((i, i+1, i+2), (i, i+2, i+3)))
    return _template(points, tex, tris)


def _append(mesh, points, uvs, triangles, mat):
    n = len(points)
    mesh.P.extend(points.ravel())
    mesh.UV.extend(uvs.ravel())
    mesh.C.extend(tuple(mat[1])*n)
    mesh.T.extend((triangles+mesh.n).ravel())
    mesh.M.extend((mat[0],)*len(triangles))
    mesh.n += n


def _facade_layout(indices,uvs):
    triangles=tuple(t for i in range(0,len(indices),4) for t in ((i,i+1,i+2),(i,i+2,i+3)))
    return indices,tuple(uvs),triangles,tuple(v for uv in uvs for v in uv),tuple(i for t in triangles for i in t)


_SURROUND_LAYOUT=_facade_layout(
    (0,1,2,3,1,4,5,2,4,6,7,5,6,0,3,7,8,9,10,11,12,13,14,15,9,12,16,17,18,19,15,10),
    ((0.,0.),(1.,0.),(1.,.1),(0.,.1))*4+UV*4)
_SILL_LAYOUT=_facade_layout((0,1,2,3,1,0,4,5,2,1,5,6,3,2,6,7,0,3,7,4),UV*5)


def _instance_template(layout,points):
    indices,uvs,triangles,flat_uv,flat_triangles=layout
    return Template((),uvs,triangles,points,indices,flat_uv,flat_triangles)


@lru_cache(maxsize=256)
def surround(width, height, frame, reveal):
    """Four recess returns and four face strips, in their original draw order."""
    w,h,f,r=width,height,frame,reveal
    return _instance_template(_SURROUND_LAYOUT,(
        (0.,0.,0.),(w,0.,0.),(w,0.,-r),(0.,0.,-r),(w,h,0.),(w,h,-r),(0.,h,0.),(0.,h,-r),
        (-f,-f,.018),(0.,-f,.018),(0.,h+f,.018),(-f,h+f,.018),
        (w,-f,.018),(w+f,-f,.018),(w+f,h+f,.018),(w,h+f,.018),
        (w,0.,.018),(0.,0.,.018),(0.,h,.018),(w,h,.018)))


@lru_cache(maxsize=256)
def sill(width, depth, thickness):
    front = ((0., -thickness, depth), (width, -thickness, depth),
             (width, -.015, depth), (0., -.015, depth))
    back = ((0., -thickness, .018), (width, -thickness, .018),
            (width, 0., .018), (0., 0., .018))
    return _instance_template(_SILL_LAYOUT,front+back)


@lru_cache(maxsize=512)
def _oriented(template,dx,dy,su,sv):
    points=tuple((dx*s+dy*d,dy*s-dx*d,z) for s,z,d in template.unique)
    uv=tuple((s/su,z/sv) for s,z,_ in template.unique) if su is not None else ()
    return points,uv


def facade(mesh, template, origin, direction, base, along, height, mat, wall_uv=None):
    if hasattr(mesh,'queue_facade'):
        mesh.queue_facade(template,origin,direction,base,along,height,mat,wall_uv)
        return
    ax, ay = origin
    dx, dy = direction
    # Small windows are below numpy's useful batch size. Transform shared
    # corners once using scalars, then expand the original hard-edge vertices.
    su,sv=wall_uv[1:] if wall_uv is not None else (None,None)
    offsets,uv_offsets=_oriented(template,dx,dy,su,sv)
    ox,oy,oz=ax+dx*along,ay+dy*along,base+height
    points=[(ox+x,oy+y,oz+z) for x,y,z in offsets]
    mesh.P.extend([v for i in template.indices for v in points[i]])
    if wall_uv is not None:
        run, su, sv = wall_uv
        u0,v0=(run+along)/su,height/sv
        uv = [(u0+u,v0+v) for u,v in uv_offsets]
        mesh.UV.extend(template.flat_uv[:32])
        mesh.UV.extend([v for i in template.indices[16:] for v in uv[i]])
    else:
        mesh.UV.extend(template.flat_uv)
    n = len(template.indices)
    mesh.C.extend(tuple(mat[1])*n)
    mesh.T.extend([i+mesh.n for i in template.flat_triangles])
    mesh.M.extend((mat[0],)*len(template.triangle_rows))
    mesh.n += n


@lru_cache(maxsize=32)
def pipe(radius, sides):
    """Unit-length capped pipe; radial dimensions are exact, length is stamped."""
    if not 3 <= sides <= 32 or not math.isfinite(radius) or radius <= 0:
        raise ValueError('invalid pipe profile')
    ring = [(radius*math.cos(i*2*math.pi/sides), radius*math.sin(i*2*math.pi/sides))
            for i in range(sides)]
    points, uv, tris = [], [], []
    for i in range(sides):
        p, q = ring[i], ring[(i+1)%sides]
        k = len(points)
        points.extend(((*p, 0.), (*q, 0.), (*q, 1.), (*p, 1.),
                       (0., 0., 0.), (*q, 0.), (*p, 0.),
                       (0., 0., 1.), (*p, 1.), (*q, 1.)))
        uv.extend((*UV, (.5, .5), (1., 1.), (0., 0.), (.5, .5), (0., 0.), (1., 1.)))
        tris.extend(((k, k+1, k+2), (k, k+2, k+3), (k+4, k+5, k+6), (k+7, k+8, k+9)))
    return _template(points, uv, tris)


def beam(mesh, a, c, radius, mat, sides=8):
    a, c = np.asarray(a, float), np.asarray(c, float)
    delta = c-a
    length = float(np.linalg.norm(delta))
    if length < 1e-7:
        return
    d = delta/length
    # Two 3-element cross products dominated the many tiny pipe/bracket calls.
    # Keep the same reference axis and handedness without numpy's axis dispatch.
    x,y,z=map(float,d)
    ux,uy,uz=(y,-x,0.) if abs(z)<.9 else (0.,z,-y)
    norm=math.sqrt(ux*ux+uy*uy+uz*uz)
    ux,uy,uz=ux/norm,uy/norm,uz/norm
    u=np.array((ux,uy,uz));v=np.array((y*uz-z*uy,z*ux-x*uz,x*uy-y*ux))
    p, uv, triangles = pipe(radius, sides)
    # Preserve independent side/cap vertices so hard edges and cap UVs survive.
    offsets = p[:, :1]*u+p[:, 1:2]*v
    points = np.where(p[:, 2:3] == 0., a, c)+offsets
    _append(mesh, points, uv, triangles, mat)


def cache_info():
    result = {}
    for name, fn in (('surround', surround), ('sill', sill), ('pipe', pipe), ('oriented',_oriented)):
        result[name] = fn.cache_info()._asdict()
    return result


def clear():
    for fn in (surround, sill, pipe, _oriented):
        fn.cache_clear()
