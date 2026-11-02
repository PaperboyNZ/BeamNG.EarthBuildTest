"""Raised sidewalks with curbs as one mesh per road tile (docs/ARCHITECTURE.md "Raised sidewalks").

How West Coast USA does it (2026-10-11 study of its level files, after the user found our first
curbs "invisible" and plain): no MeshRoads anywhere. Each district's sidewalks are one modelled
mesh (64 `sidewalk_<district>.dae`, 231k triangles in all) with a curb profile textured from the
`curbs` trim sheet (8 horizontal bands: plain, red / yellow / white / green painted; in each band the
light upper part is the curb top and the darker lower part the face) and slab tops (`sidewalk1`,
a 4096 x 1024 sheet of 5 sidewalk strips with panel joints along them), plus a collision mesh. One
draw call per material per district instead of three per sidewalk piece.

Here: the sidewalk runs of a road tile (roads.build_tile, after the cuts at crossings) are swept
along a fixed profile into one shape (cdae.py). The profile, across from the curb
line (offset 0) outwards, heights above the road:
    face   (0, -SINK) -> (BATTER, h - NOSE)   curbs, the band's dark part
    nose   -> (NOSE_W, h)                     curbs, light
    top    -> (CURB_W, h)                     curbs, light
    slab   -> (W, h + W * CROSS_SLOPE)        tileable slabs (rising away from the road, as built)
    back   -> (W, -SINK)                      curbs, dark
with flat end caps (curbs). Heights follow the road's (graded) centreline z, carried by the runs.
Slabs, brick, grass and tactile pads receive metric surface UVs after assembly; only curbs use
a trim atlas. Surface coordinates follow the path's station and profile offset.
The mod shows it as a TSStatic that collides with its visible mesh. Pure functions; deterministic.
"""
import numpy as np

import cdae

CURB_H = 0.15           # m above the road (US curbs: 0.15)
SINK = 0.10             # m the faces reach below the road / ground
BACK_RUN = 2.0          # the slab's back falls to the ground at 1:2, not straight down: the ground behind a sidewalk is
                        # graded at road level (grading.SIDEWALK_MARGIN_M), so a vertical back was a ~20 cm ledge that
                        # caught a wheel leaving the sidewalk for the verge ("pulling the car down", user 2026-10-14)
BATTER = 0.02           # m the face leans back over its height
NOSE = 0.025            # m: the bevelled nose, down from the top ...
NOSE_W = 0.045          # ... and in from the face
CURB_W = 0.15           # m of curb top band
CROSS_SLOPE = 0.015     # sidewalk cross slope, rising away from the road
CURB_REPEAT_M = 9.0     # m of curb per texture width (3 joints of 3 m)
SLAB_REPEAT_M = 45.0    # m of sidewalk per texture width (4096 px, a 205 px strip ~ 2.25 m)
MATERIALS = ("curbs", "bne_sidewalk_slab", "tactile_indicator",  # loaded by roads.lua
             "bne_sidewalk_brick", "bne_land_lawn", "bne_sidewalk_utility", "bne_sidewalk_stone")
GRASS = 4
BRICK = 3
STONE = 6
BRICK_REPEAT_M = 1.2        # native sweep encoding, converted to path metres below
BRICK_TILE_M = 4.8          # herringbone sheet: approximately 0.20 x 0.10 m paving bricks
SLAB_TILE_M = (8.0, 4.0)    # slabs_large: 2048 x 1024, four by two square 2 m panels
GRASS_REPEAT_M = 3.0
STONE_TILE_M = (3.0, 1.5)   # Italy sidewalk tiles: 1024 x 512, six by three 0.5 m panels
UV_PHASE_M = 24.0          # common multiple of all surface repeats, including tactile 0.6 m


def path_station(point, path):
    """Stable station of a cut's start on its original curb line."""
    curb = np.asarray(path[0])[:, :2]
    delta = np.diff(curb, axis=0)
    lengths = np.linalg.norm(delta, axis=1)
    valid = np.flatnonzero(lengths > 1e-8)
    if not len(valid):
        return 0.
    fraction = np.clip(np.sum((np.asarray(point)[:2]-curb[:-1])*delta, axis=1)
                       / np.maximum(lengths**2, 1e-16), 0., 1.)
    distance = np.sum((curb[:-1]+fraction[:, None]*delta-np.asarray(point)[:2])**2, axis=1)
    i = valid[np.argmin(distance[valid])]
    phase = float(curb[0] @ (delta[valid[0]]/lengths[valid[0]])) % UV_PHASE_M
    return phase + np.sum(lengths[:i]) + fraction[i]*lengths[i]


def run_uvs(mesh, origin, piece, path):
    """Recover sweep stations in linear time from the native strip UVs.

    A tactile boundary can overwrite U on the neighbouring slab's vertex.
    Check both encodings against geometry before rescaling any material.
    """
    P, T, UV, M = mesh
    ids = np.unique(T[np.isin(M, (1, 2, BRICK))])
    UV = UV.copy()
    curb, outward = piece[1] - origin, piece[2]
    stations = np.r_[0., np.cumsum(np.linalg.norm(np.diff(curb[:, :2], axis=0), axis=1))]
    best = np.full(len(ids), np.inf)
    metric = np.zeros((len(ids), 2))
    for repeat in (SLAB_REPEAT_M if piece[8] == 1 else BRICK_REPEAT_M, TACTILE_REPEAT_M):
        s = np.clip(UV[ids, 0]*repeat, 0., stations[-1])
        centre = np.column_stack([np.interp(s, stations, curb[:, j]) for j in range(2)])
        n = np.column_stack([np.interp(s, stations, outward[:, j]) for j in range(2)])
        rel = P[ids, :2] - centre
        across = np.sum(rel*n, axis=1) / np.maximum(np.sum(n*n, axis=1), 1e-12)
        error = np.sum((rel-across[:, None]*n)**2, axis=1)
        take = error < best
        best[take] = error[take]
        metric[take] = np.c_[s[take], across[take]]
    metric[:, 0] += path_station(piece[1][0], path)
    UV[ids] = metric
    return P, T, UV, M


def corner_uvs(mesh, origin, path):
    """A regular paving grid aligned with the corner's incoming footpath.

    A junction fan has no single across-path station at its inside vertex.
    Projecting that fan onto arc length stretches and pinches the tiles, so
    use the incoming curb normal as a local planar frame for the whole corner.
    """
    P, T, UV, M = mesh
    vertices = np.unique(T[M == 1])
    UV = UV.copy()
    curb, outward = path
    if len(vertices) and len(curb) >= 2:
        normal = outward[0] / max(np.linalg.norm(outward[0]), 1e-12)
        tangent = np.array([normal[1], -normal[0]])
        if tangent @ (curb[1, :2]-curb[0, :2]) < 0:
            tangent = -tangent
        relative = P[vertices, :2] - (curb[0, :2]-np.asarray(origin)[:2])
        phase = float(curb[0, :2] @ tangent) % UV_PHASE_M
        UV[vertices] = np.c_[relative@tangent + phase, relative@normal]
    return P, T, UV, M


def surface_uvs(mesh):
    """Apply each surface material's metric mapping after all sidewalk pieces are assembled.

    Profile offsets also identify the planted verge before this step.
    Path metres keep paving aligned through bends and driveway cuts. Split only
    vertices used by different materials: a tactile edge must not
    change the adjoining pavement's UVs (or a pavement edge the curb's trim band).
    """
    P, T, UV, M = mesh
    if not len(T):
        return mesh
    source_uv = UV
    T, UV = T.copy(), UV.copy()
    owner = np.full(len(P), -1, np.int64)
    ps, uvs = [P], [UV]
    count = len(P)
    repeats = {1: SLAB_TILE_M, 2: TACTILE_REPEAT_M, BRICK: BRICK_TILE_M,
               GRASS: GRASS_REPEAT_M, STONE: STONE_TILE_M}
    for mat in np.unique(M):
        rows = M == mat
        vertices = np.unique(T[rows])
        shared = vertices[owner[vertices] >= 0]
        owner[vertices] = mat
        target = vertices.copy()
        if len(shared):
            remap = np.arange(len(P), dtype=np.int64)
            remap[shared] = count + np.arange(len(shared))
            T[rows] = remap[T[rows]]
            target = remap[vertices]
            ps.append(P[shared])
            uvs.append(UV[shared].copy())
            count += len(shared)
        if mat in repeats:
            repeat = np.asarray(repeats[mat], np.float64)
            mapped = source_uv[vertices] / repeat
            original = target < len(P)
            UV[target[original]] = mapped[original]
            if len(shared):
                uvs[-1][:] = mapped[~original]
    return (np.concatenate(ps) if len(ps) > 1 else P), T, (np.concatenate(uvs) if len(uvs) > 1 else UV), M

# curbs sheet (1024 x 512, 8 bands of 64 px; Collada v up, so band 0 is v in [7/8, 1]):
# rows 0-40 of a band are the light curb top, 40-64 the darker face
V_BAND_TOP, V_LIGHT_LOW, V_BAND_LOW = 1.0 - 1 / 512, 1.0 - 40 / 512, 1.0 - 63 / 512
# sidewalk1 sheet: strip 0 (the top row) across the slab
V_SLAB_IN, V_SLAB_OUT = 1.0 - 0.195, 1.0 - 0.005


def _normals_2d(xy):
    """Unit left normals at each point of a polyline (mitred like roads.offset_polyline, clamped)."""
    if len(xy) < 2:
        return np.zeros((len(xy), 2))
    d = np.diff(xy, axis=0)
    L = np.hypot(d[:, 0], d[:, 1])
    if np.any(L < 1e-8):
        keep = np.r_[True, L >= 1e-8]
        return _normals_2d(xy[keep])[np.cumsum(keep) - 1]
    L[L == 0] = 1.0
    t = d / L[:, None]
    nseg = np.stack([-t[:, 1], t[:, 0]], axis=1)
    n = np.empty((len(xy), 2))
    n[0], n[-1] = nseg[0], nseg[-1]
    if len(xy) > 2:
        m = nseg[:-1] + nseg[1:]
        ml = np.hypot(m[:, 0], m[:, 1])
        ml[ml < 1e-9] = 1.0
        m = m / ml[:, None]
        cos = np.clip((m * nseg[1:]).sum(1), 0.5, 1.0)          # miter at most 2x
        n[1:-1] = m / cos[:, None]
    return n


RAMP_RUN = 1.8          # m over which a curb ramp's slab climbs back to the sidewalk (1:12)
RAMP_FLARE = 0.6        # m of curb sloping down on each side of a ramp
RAMP_H = 0.01           # m: the curb at a ramp (flush with the gutter)
TACTILE_REPEAT_M = 0.6  # m per tactile pad texture repeat
PAD_W = 0.6             # m of a ramp's slope from the curb that is the tactile pad (US: 2 ft of domes)


def profile(h=CURB_H, w=2.5, hr=None):
    """(The reference the Rust sweep follows, earthfast sidewalks.rs profile: tests pin its shape.) The cross-section points (offset from the curb line outwards, height above the road): face
    bottom, face top, nose end, curb top end, ramp end, slab outer top, back bottom (BACK_RUN out). hr: the curb's
    height (h, or lower at a curb ramp: the slab then climbs from hr at the curb top to h at
    RAMP_RUN)."""
    hr = h if hr is None else hr
    f = hr / h if h > 0 else 0.0
    # a band narrower than RAMP_RUN (a median's 0.3-0.6 m, an island's 1.2 m) ends its ramp inside it: past its outer
    # edge the profile folded back over itself, and the folded collision caught wheels ("the median eats tires",
    # GitHub #55; a truck held on an island band in Bodø, 2026-10-20)
    rr = max(CURB_W + NARROW_EDGE_M, min(RAMP_RUN, w - NARROW_EDGE_M))
    zr = h + rr * CROSS_SLOPE
    xp = CURB_W + min(PAD_W, (rr - CURB_W) / 2)
    zp = hr + (zr - hr) * (xp - CURB_W) / (rr - CURB_W)    # on the ramp's slope, PAD_W past the curb top
    top = h + w * CROSS_SLOPE
    return np.array([[0.0, -SINK], [BATTER * f, hr - NOSE * f], [NOSE_W * f, hr], [CURB_W, hr],
                     [xp, zp], [rr, zr], [w, top], [w + BACK_RUN * (top + SINK), -SINK]])


NARROW_EDGE_M = 0.05    # m a narrow band's ramp end stays inside its outer edge (profile)


# strips: (from profile point, to point, material index, v at from, v at to); material 1 on the
# ramp strip is replaced by 2 (tactile) where the curb is lowered
_SL = (RAMP_RUN - CURB_W) / (2.5 - CURB_W)
_SP = PAD_W / (2.5 - CURB_W)
V_SLAB_MID = V_SLAB_IN + _SL * (V_SLAB_OUT - V_SLAB_IN)
V_SLAB_PAD = V_SLAB_IN + _SP * (V_SLAB_OUT - V_SLAB_IN)
STRIPS = ((0, 1, 0, V_BAND_LOW, V_LIGHT_LOW), (1, 2, 0, V_LIGHT_LOW, V_BAND_TOP - 0.02),
          (2, 3, 0, V_BAND_TOP - 0.02, V_BAND_TOP), (3, 4, 1, V_SLAB_IN, V_SLAB_PAD),
          (4, 5, 1, V_SLAB_PAD, V_SLAB_MID), (5, 6, 1, V_SLAB_MID, V_SLAB_OUT), (6, 7, 0, V_LIGHT_LOW, V_BAND_LOW))
CURB_STRIPS = STRIPS[:3]


# The lean collision mesh (Builder(collision=True), written as the tile's "walkcol"): the drawn mesh's 8-point profile
# and 0.5 m ramp steps cost the game's collision rebuild ~7 ms of ~12 in Fells Point (2026-10-16: 31 tiles, 245k
# triangles). Physics gets the face, the curb top to the ramp run, the slab and the back (profile points LEAN) at the
# points that matter: a run's points within LEAN_TOL_M of the line between their neighbours kept (Douglas-Peucker,
# the curb height counted too, so ramps keep their shape).
LEAN = (0, 2, 5, 6, 7)
LEAN_STRIPS = tuple((i, i + 1, 0, 0.0, 0.0) for i in range(len(LEAN) - 1))
LEAN_TOL_M = 0.03


def simplify(pts, tol=LEAN_TOL_M):
    """Indices of the points (k, d) Douglas-Peucker keeps at tolerance tol (both ends always). Pure."""
    pts = np.asarray(pts, np.float64)
    k = len(pts)
    if k <= 2:
        return np.arange(k)
    keep = np.zeros(k, bool)
    keep[0] = keep[-1] = True
    stack = [(0, k - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        seg = pts[b] - pts[a]
        rel = pts[a + 1:b] - pts[a]
        L2 = float(seg @ seg)
        if L2 > 0:
            t = np.clip(rel @ seg / L2, 0.0, 1.0)
            d = rel - t[:, None] * seg
        else:
            d = rel
        d2 = (d * d).sum(1)
        i = int(np.argmax(d2))
        if d2[i] > tol * tol:
            m = a + 1 + i
            keep[m] = True
            stack.append((a, m))
            stack.append((m, b))
    return np.nonzero(keep)[0]


class Builder:
    """Accumulates sidewalk runs and corners into one mesh (positions relative to `origin`), swept in Rust
    (earthfast.sidewalk_mesh: the profile, ramps, tactile pads, caps and corner slabs, in the old Python's arithmetic
    and order) when its arrays are asked for; collision: the lean collision mesh beside it (self.col.arrays())."""

    def __init__(self, origin, collision=False):
        self.origin = np.asarray(origin, np.float64)
        self.pieces = []            # (kind, points, dirs, outer, ramps, width, height, caps, slab)
        self.surface_paths = []     # original run retained across driveway/verge splits
        self._built = None          # the Rust meshes once built (full, lean)
        self.vehicle_meshes = []
        self.vehicle_visuals = []
        self.verge_builder = None
        self._defer_surface_uvs = False  # internal verge batch still needs profile-offset UVs
        self.col = _Lean(self) if collision else None

    def add_run(self, curb, toward_out, w, h=CURB_H, caps=(True, True), ramps=(), slab=1, driveways=(), verge=False,
                texture_path=None):
        """One sidewalk run: curb (k, 3) the curb line (z = the road there), toward_out (k, 2) unit
        vectors from the curb outwards (scaled by the miter), w its width; caps: end caps at the
        (start, end) (not where the run goes on in the next tile or meets a corner piece); ramps:
        curb ramps [(s0, s1)] in arc length along the curb."""
        curb = np.asarray(curb, np.float64)
        if len(curb) < 2:
            return
        toward_out = np.asarray(toward_out, np.float64)
        keep = np.r_[True, np.linalg.norm(np.diff(curb[:, :2], axis=0), axis=1) >= 1e-8]
        curb, toward_out = curb[keep], toward_out[keep]
        if len(curb) < 2:
            return
        texture_path = (curb, toward_out) if texture_path is None else texture_path
        if driveways:
            import vehicle_crossings
            if w >= vehicle_crossings.MIN_WIDTH:
                vehicle_crossings.add(self,curb,toward_out,w,h,caps,ramps,slab,driveways,verge=verge,
                                      texture_path=texture_path)
                return
        if verge and w >= 2.4 and not ramps and slab == 1:
            # A second bounded native batch gives offset-based UVs for the
            # planted strip. Geometry/collision still use the same native sweep.
            if self.verge_builder is None:
                self.verge_builder = Builder(self.origin, collision=self.col is not None)
                self.verge_builder._defer_surface_uvs = True
            self.verge_builder.add_run(curb,toward_out,w,h,caps,slab=BRICK,texture_path=texture_path)
            self._built = None
            return
        self.pieces.append((0, curb[:, :3], np.asarray(toward_out, np.float64)[:, :2], None, list(ramps), float(w),
                            float(h), (bool(caps[0]), bool(caps[1])), int(slab)))
        self.surface_paths.append(texture_path)
        self._built = None

    def add_corner(self, arc, inward, outer, h=CURB_H, ramps=(), slab=1):
        """A corner piece: the curb along the polyline arc (k, 3) (a curb return, with the straight
        runs and tapers of curb extensions; inward: unit vectors toward the sidewalk), the slab from
        the curb top to the outer corner points [(x, y, z) ...] (from the second sidewalk's end round
        to the first's), and the back faces along the outer edges. ramps: [(s0, s1)] arc lengths
        where the curb is lowered (the slab then slopes up from it toward the outer corner)."""
        self.pieces.append((1, np.asarray(arc, np.float64)[:, :3], np.asarray(inward, np.float64)[:, :2],
                            np.asarray(outer, np.float64).reshape(-1, 3), list(ramps), 2.5, float(h), (False, False),
                            int(slab)))
        self.surface_paths.append((self.pieces[-1][1], self.pieces[-1][2]))
        self._built = None

    def empty(self):
        return not self.pieces and not self.vehicle_meshes and self.verge_builder is None

    def _build(self):
        if self._built is None:
            ps = self.pieces
            # Retain each piece's path while mapping its native geometry. The
            # native ABI has no per-piece vertex offsets, so map before combining.
            from vehicle_crossings import combine
            batches = []
            for piece, path in zip(ps, self.surface_paths):
                finish = piece[8]
                visual, collision = native_mesh([piece], self.origin, self.col is not None)
                visual = (run_uvs(visual, self.origin, piece, path) if piece[0] == 0
                          else corner_uvs(visual, self.origin, path))
                P, T, UV, M = visual
                if finish != 1:
                    M = np.where((M == 1) | (M == BRICK), finish, M)
                batches.append(((P, T, UV, M), collision))
            if not batches:
                batches.append(native_mesh([], self.origin, self.col is not None))
            self._built = (combine(batches[0][0], [b[0] for b in batches[1:]]),
                           combine(batches[0][1], [b[1] for b in batches[1:]]))
            extra = list(self.vehicle_visuals)
            if not self._defer_surface_uvs:
                from sidewalk_details import meshes
                extra.extend(meshes(ps, self.origin))
            collision_extra = list(self.vehicle_meshes)
            if self.verge_builder is not None:
                P,T,UV,M = (a.copy() for a in self.verge_builder.arrays())
                # The first slab strip is 0.6 m wide (CURB_W .. CURB_W+PAD_W).
                # The remaining >=1.65 m stays paved, including every crossing.
                planted = (M == BRICK) & (UV[T,1].max(axis=1) <= CURB_W+PAD_W+1e-8)
                M[M == BRICK] = 1
                M[planted] = GRASS
                extra.append((P,T,UV,M))
                if self.col is not None:
                    collision_extra.append(self.verge_builder.col.arrays())
            if extra:
                from vehicle_crossings import combine
                visual, collision = self._built
                self._built=(combine(visual,extra),
                             combine(collision,collision_extra) if self.col is not None else collision)
            if not self._defer_surface_uvs:
                visual, collision = self._built
                self._built = surface_uvs(visual), collision
        return self._built

    def arrays(self):
        P, T, UV, M = self._build()[0]
        return P, T, UV, M

    def write(self, path):
        P, T, UV, M = self.arrays()
        return cdae.write(path, P, T, uvs=UV, material=list(MATERIALS), tri_materials=M, object_name="walk")

    def write_collision(self, path):
        """The lean collision mesh (Builder(collision=True)) as a never-drawn collision shape."""
        P, T, UV, M = self.col.arrays()
        return cdae.write(path, P, T, uvs=UV, material=MATERIALS[0], collision_only=True)


class _Lean:
    """A Builder's lean collision mesh (the same pieces: earthfast.sidewalk_mesh's second mesh)."""

    def __init__(self, b):
        self.b = b

    def arrays(self):
        P, T, UV, M = self.b._build()[1]
        return P, T, UV, M

    def empty(self):
        return self.b.empty()


def corner_outer(corner):
    """Offset the native 2.5 m outer datum to each actual adjoining walk width.

    Kept separate from draped source Z so repeat builds/rebases cannot add the
    correction twice. This fixes small ledges on wide or asymmetric footpaths.
    """
    outer=np.asarray(corner['outer'],np.float64).copy()
    widths=corner.get('outer_widths')
    if widths is not None:
        outer[:,2]+=(np.asarray(widths)-2.5)*CROSS_SLOPE
    return outer


def slab_material(walk):
    return STONE if walk.get('pavement') == 'stone' else BRICK if walk.get('brick') else 1


def native_mesh(ps, origin, collision):
    """One native geometry batch; material-specific surface UVs follow assembly."""
    import fast
    fast.require(104, 'sidewalk_mesh')
    kind = np.array([p[0] for p in ps], np.int64)
    pts = np.ascontiguousarray(np.concatenate([p[1] for p in ps]) if ps else np.zeros((0, 3)))
    dirs = np.ascontiguousarray(np.concatenate([p[2] for p in ps]) if ps else np.zeros((0, 2)))
    off = np.r_[0, np.cumsum([len(p[1]) for p in ps])].astype(np.int64)
    outs = [p[3] if p[3] is not None else np.zeros((0, 3)) for p in ps]
    outer = np.ascontiguousarray(np.concatenate(outs) if ps else np.zeros((0, 3)))
    ooff = np.r_[0, np.cumsum([len(o) for o in outs])].astype(np.int64)
    rs = [np.asarray(p[4], np.float64).reshape(-1, 2) for p in ps]
    ramps = np.ascontiguousarray(np.concatenate(rs) if ps else np.zeros((0, 2)))
    roff = np.r_[0, np.cumsum([len(r) for r in rs])].astype(np.int64)
    return fast._ef.sidewalk_mesh(kind, pts, dirs, off, outer, ooff, ramps, roff,
        np.array([p[5] for p in ps], np.float64), np.array([p[6] for p in ps], np.float64),
        np.array([p[7] for p in ps], bool).reshape(-1, 2),
        np.array([BRICK if p[8] != 1 else 1 for p in ps], np.int64),
        tuple(float(v) for v in origin), collision)


def run_geometry(walk_line, side, w):
    """The curb line and outward vectors of a sidewalk run given its centreline (k, 3) and the side of
    the road it is on (+1: the road's left, as roads.offset_polyline). Pure."""
    xy = np.asarray(walk_line, np.float64)[:, :2]
    n = _normals_2d(xy)
    out = n * side                      # left of the road's direction is +n for side +1
    curb = np.array(walk_line, np.float64)
    curb[:, :2] = xy - out * (w / 2)
    return curb, out
