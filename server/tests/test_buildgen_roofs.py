"""Complex roof coverage, physical mapping and LOD/export regression fixtures."""
from pathlib import Path
from itertools import product
import sys
import unittest

import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import buildings as b
import cdae
from buildgen import roofs, materials, freeze_items
from buildgen.topology import Footprint
from building_fixtures import complex_roofs, transform
from test_buildgen_facades import building


class ComplexRoofTest(unittest.TestCase):
    def cases(self):
        for label, outer, holes in complex_roofs():
            for angle, size, offset in ((0., 1., (0., 0.)), (37., .4, (8100., -6300.)),
                                         (-83., 2.3, (-400., 900.))):
                fp = Footprint(transform(outer, angle, size, offset),
                               tuple(transform(h, angle, size, offset) for h in holes))
                for kind in ("gabled", "hipped"):
                    yield label, angle, fp, kind

    def test_complex_roofs_cover_occupied_area_and_preserve_all_voids(self):
        for name, angle, fp, kind in self.cases():
            with self.subTest(shape=name, angle=angle, roof=kind):
                roof = roofs.envelope(fp, kind)
                pieces = [Polygon([p[:2] for p in tri]) for tri in roof.triangles]
                union = unary_union(pieces)
                self.assertLess(union.symmetric_difference(fp.shape()).area, 1e-6)
                self.assertAlmostEqual(sum(p.area for p in pieces), fp.area, places=6)
                self.assertAlmostEqual(max(p[2] for t in roof.triangles for p in t), 1.)

    def test_complex_roof_mapping_keeps_scale_orientation_and_seams(self):
        for name, angle, fp, kind in self.cases():
            for family, rise in product(("metal", "slate", "shingle"), (.75, 3., 6.)):
                with self.subTest(shape=name, angle=angle, roof=kind, covering=family, rise=rise):
                    spec = building(fp=fp, roof_shape=kind, roof_material=family, height=10., roof_height=rise)
                    mesh = b.Mesh(); roofs.draw(mesh, spec, spec.height, b._Looks(spec.seed))
                    p, uv, tris, _, _ = mesh.arrays()
                    roof = roofs.envelope(fp, kind)
                    self.assertTrue(np.isfinite(p).all() and np.isfinite(uv).all())
                    shared = {}
                    for tri, plane in zip(tris, roof.triangle_planes):
                        positions, tex = p[tri], uv[tri]
                        real = np.linalg.norm(positions - np.roll(positions, 1, axis=0), axis=1)
                        mapped = np.linalg.norm((tex - np.roll(tex, 1, axis=0))*materials.roof_scale(family), axis=1)
                        np.testing.assert_allclose(real, mapped, atol=3e-5)
                        for i, j in ((0, 1), (1, 2), (2, 0)):
                            self.assertGreaterEqual((positions[i, 2]-positions[j, 2])*(tex[i, 1]-tex[j, 1]), -1e-7)
                        for xyz, st in zip(positions, tex):
                            key = (plane, *np.round(xyz, 6))
                            if key in shared:
                                np.testing.assert_allclose(st, shared[key], atol=1e-6)
                            shared[key] = st

    def test_complex_roof_tops_agree_in_near_lite_collision_and_skyline(self):
        for name, outer, holes in complex_roofs():
            for kind in ("gabled", "hipped"):
                with self.subTest(shape=name, roof=kind):
                    fp = Footprint(outer, holes)
                    spec = building(fp=fp, height=9., roof_height=2.5, roof_shape=kind)
                    items = freeze_items([(spec, 0., 0.)])
                    for mesh in (b.build(items), b.build(items, lite=True), b.collision_mesh(items), b._sky_mesh(items)):
                        self.assertTrue(np.isfinite(mesh[0]).all() and np.isfinite(mesh[1]).all())
                        self.assertAlmostEqual(float(mesh[0][:, 2].max()), 9.)

    def test_complex_roof_export_has_finite_orthogonal_shading_vectors(self):
        for name, outer, holes in complex_roofs():
            for kind in ("gabled", "hipped"):
                with self.subTest(shape=name, roof=kind):
                    spec = building(fp=Footprint(outer, holes), roof_shape=kind, roof_material="metal")
                    mesh = b.Mesh(); roofs.draw(mesh, spec, spec.height, b._Looks(spec.seed))
                    p, uv, tri, mid, colours = mesh.arrays()
                    data = cdae.decode(cdae.encode(p, tri, uvs=uv, material=list(b.MATERIALS), tri_materials=mid, colors=colours))
                    for compiled in data["meshes"]:
                        arrays = cdae.mesh_arrays(compiled)
                        for key in ("verts", "tverts", "norms", "tangents"):
                            self.assertTrue(np.isfinite(arrays[key]).all(), key)
                        tangent = arrays["tangents"][:, :3]
                        np.testing.assert_allclose(np.linalg.norm(tangent, axis=1), 1., atol=1e-5)
                        np.testing.assert_allclose((tangent*arrays["norms"]).sum(1), 0., atol=1e-5)


if __name__ == "__main__":
    unittest.main()
