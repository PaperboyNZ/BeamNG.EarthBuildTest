"""Deform existing sidewalk skins to corrected pavement boundary profiles.

No terrain is sampled here. Profiles come from the same clipped top polygons
which are published by clear_terrain. Matching uses original XYZ edges, never
material UVs; original triangle barycentric coordinates work for vertical caps.
"""
from collections import defaultdict

import numpy as np
from shapely import STRtree, linestrings, box


def _point(p):
    return tuple(float(c) for c in p)


def _edge(a, b):
    a, b = _point(a), _point(b)
    return _ordered_edge(a, b)


def _ordered_edge(a, b):
    """Order already-materialized exact Python coordinate keys."""
    return (a, b) if a < b else (b, a)


class BoundarySkin:
    """Original material-zero adjacency and exact shared top-edge evidence."""
    def __init__(self, points, triangles, uvs, materials, selected, tolerance=1e-7):
        self.p = points
        self.t = triangles
        self.uv = uvs
        self.tol = tolerance
        self.faces = np.flatnonzero(materials == 0)
        used_faces = np.concatenate((self.faces, np.asarray(selected, dtype=np.intp)))
        used_vertices = np.unique(triangles[used_faces])
        # tolist converts Float32/64 scalars to the same exact Python floats as
        # _point, once per referenced vertex; unused mesh prefixes get no tuple.
        self.point_keys = dict(zip(used_vertices, map(tuple, points[used_vertices].tolist())))
        self.edges = defaultdict(list)
        self.endpoints = defaultdict(set)
        for face in self.faces:
            ids = triangles[face]
            for j in range(3):
                a, b = self.point_keys[ids[j]], self.point_keys[ids[(j+1) % 3]]
                self.edges[_ordered_edge(a, b)].append(int(face))
                self.endpoints[a].add(int(face))
        edge_keys = tuple(self.edges)
        edge_points = np.asarray(edge_keys)
        tree = STRtree(linestrings(edge_points[:, :, :2])) if edge_keys else None
        self.shared = defaultdict(list)
        # At most255 top edges per tree query; pair arithmetic stays bounded
        # even where many collinear native/terrain subdivisions share a box.
        for start in range(0,len(selected),85):
            records=[]
            for face in selected[start:start+85]:
                ids=triangles[face]
                records.extend((int(face),_ordered_edge(self.point_keys[ids[j]],self.point_keys[ids[(j+1)%3]])) for j in range(3))
            keys=[key for face,key in records]
            matches=[[key] if key in self.edges else [] for key in keys]
            if tree is not None and keys:
                top=np.asarray(keys)
                lo,hi=np.minimum(top[:,0],top[:,1]),np.maximum(top[:,0],top[:,1])
                pairs=tree.query(box(lo[:,0]-tolerance,lo[:,1]-tolerance,
                                     hi[:,0]+tolerance,hi[:,1]+tolerance))
                # Array queries retain each scalar query's traversal order.
                # Keep that order through filtering and through the final
                # face/edge loop, including exact keys AND extended subedges.
                for first in range(0,pairs.shape[1],8192):
                    top_ids,candidate_ids=pairs[:,first:first+8192]
                    candidates=edge_points[candidate_ids]
                    c=candidates[:,0];cd=candidates[:,1]-c
                    length2=np.einsum('ij,ij->i',cd,cd)
                    valid=length2>1e-24
                    top_ids,candidate_ids=top_ids[valid],candidate_ids[valid]
                    c,cd,length2=c[valid],cd[valid],length2[valid]
                    ends=top[top_ids]
                    params=np.einsum('pij,pj->pi',ends-c[:,None],cd)/length2[:,None]
                    error=np.linalg.norm(ends-(c[:,None]+params[:,:,None]*cd[:,None]),axis=2)
                    overlap=np.minimum(1.,params.max(axis=1))-np.maximum(0.,params.min(axis=1))
                    accepted=(error.max(axis=1)<=tolerance)&(overlap*np.sqrt(length2)>tolerance)
                    for edge,index in zip(top_ids[accepted],candidate_ids[accepted]):
                        matches[int(edge)].append(edge_keys[int(index)])
            for (face,key),found in zip(records,matches):
                for match in found:
                    if match not in self.shared[face]:self.shared[face].append(match)
        self.profiles = {}
        self.raised = {}

    def collect(self, face, original, corrected):
        """Collect existing output vertices on a source face's shared XYZ edges."""
        for key in self.shared.get(int(face), ()):
            a, b = np.asarray(key)
            ab = b-a
            length2 = float(ab @ ab)
            if length2 <= 1e-24:
                continue
            t = (original-a) @ ab / length2
            projection = a+t[:, None]*ab
            collinear = np.linalg.norm(original-projection, axis=1) <= self.tol
            match = (t >= 0.) & (t <= 1.) & collinear
            profile = self.profiles.setdefault(key, [(0., a.copy()), (1., b.copy())])
            samples = list(zip(t[match], corrected[match]))
            # When the original skin endpoint is inside a longer top edge, take
            # its exact height from that already-published linear output edge.
            # This is clipping existing evidence, never another terrain sample.
            for j in range(len(original)):
                k=(j+1)%len(original)
                if not (collinear[j] and collinear[k]) or abs(t[k]-t[j])*np.sqrt(length2) <= self.tol:
                    continue
                for limit in (0.,1.):
                    if min(t[j],t[k]) <= limit <= max(t[j],t[k]):
                        fraction=(limit-t[j])/(t[k]-t[j])
                        samples.append((limit,corrected[j]+fraction*(corrected[k]-corrected[j])))
            for parameter, coord in samples:
                parameter = float(np.clip(parameter, 0., 1.))
                coord = coord.copy()
                # Correct all duplicates of an original endpoint, including M0
                # faces not themselves incident to a shared top edge.
                endpoint = 0 if parameter*np.sqrt(length2) <= self.tol else 1 if (1.-parameter)*np.sqrt(length2) <= self.tol else None
                if endpoint is not None:
                    parameter = float(endpoint)
                    coord[:2] = key[endpoint][:2]
                    if coord[2] > key[endpoint][2]+self.tol:
                        point = key[endpoint]
                        self.raised[point] = max(self.raised.get(point, point[2]), float(coord[2]))
                profile.append((parameter, coord))

    def _profile(self, key):
        a, b = np.asarray(key)
        length = np.linalg.norm(b-a)
        result = []
        for t, coord in sorted(self.profiles[key], key=lambda row: row[0]):
            if result and abs(t-result[-1][0])*length <= self.tol:
                # Multiple source triangles/positive-negative clips agree on the
                # upper envelope. Select its highest roundoff-equivalent copy.
                if coord[2] > result[-1][1][2]:
                    result[-1] = (result[-1][0], coord)
            else:
                result.append((t, coord))
        return result

    def rebuild(self):
        """Return (original M0 faces to remove, absolute replacement mesh)."""
        profiles = {}
        incident = set()
        for key in self.profiles:
            profile = self._profile(key)
            a, b = np.asarray(key)
            if any(p[2] > (a+t*(b-a))[2]+self.tol for t, p in profile):
                profiles[key] = profile
                incident.update(self.edges[key])
        for point in self.raised:
            incident.update(self.endpoints[point])
        if not incident:
            return np.empty(0, np.int64), None
        positions, textures, triangles = [], [], []
        for face in sorted(incident):
            ids = self.t[face]
            xyz, uv = self.p[ids], self.uv[ids]
            keys = [self.point_keys[index] for index in ids]
            moved = xyz.copy()
            for j in range(3):
                moved[j, 2] = self.raised.get(keys[j], xyz[j, 2])
            boundary, barys = [], []
            for j in range(3):
                k = (j+1) % 3
                key = _ordered_edge(keys[j], keys[k])
                profile = profiles.get(key)
                if profile is None:
                    samples = [(0., moved[j])]
                else:
                    forward = keys[j] == key[0]
                    samples = [(t if forward else 1.-t, p) for t,p in (profile if forward else reversed(profile))]
                    samples = samples[:-1]  # next original edge contributes its start
                for t, coord in samples:
                    bary = np.zeros(3)
                    bary[j], bary[k] = 1.-t, t
                    point = coord.copy()
                    if t == 0.:
                        point = moved[j].copy()
                    boundary.append(point)
                    barys.append(bary)
            # Fan in the original triangle's barycentric parameter plane. The
            # surface can be vertical in XY; none of these operations divide by
            # projected XY area. Only the shared edge deforms to the new profile.
            center = moved.mean(axis=0)
            base = len(positions)
            positions.append(center)
            textures.append(uv.mean(axis=0))
            positions.extend(boundary)
            textures.extend(np.asarray(barys) @ uv)
            for j in range(len(boundary)):
                k = (j+1) % len(boundary)
                if np.linalg.norm(np.cross(boundary[j]-center, boundary[k]-center)) <= 1e-12:
                    continue
                triangles.append((base, base+1+j, base+1+k))
        return np.asarray(sorted(incident), np.int64), (
            np.asarray(positions, np.float64), np.asarray(triangles, np.int64).reshape(-1, 3),
            np.asarray(textures, np.float64), np.zeros(len(triangles), np.int64))
