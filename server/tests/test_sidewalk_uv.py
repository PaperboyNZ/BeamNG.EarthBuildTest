"""Texture/material contracts on generated surfaces, including mixed-material seams."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'server'))
import cdae
import sidewalks as sw


class SidewalkUVTest(unittest.TestCase):
    def run_mesh(self, width=2.5, **kwargs):
        b = sw.Builder((0, 0, 0), collision=True)
        b.add_run(np.array([[0., 0., 0.], [13., 0., 0.], [20., 7., 0.]]),
                  np.array([[0., 1.], [-.4, 1.], [-1., 1.]]), width, **kwargs)
        return b

    def assert_mapping(self, mesh, origin=(0, 0, 0)):
        P, T, UV, M = mesh
        self.assertTrue(np.isfinite(UV).all())
        repeats = {1: sw.SLAB_TILE_M, 2: sw.TACTILE_REPEAT_M,
                   sw.BRICK: sw.BRICK_TILE_M, sw.GRASS: sw.GRASS_REPEAT_M, sw.STONE: sw.STONE_TILE_M}
        used = {}
        for mat in np.unique(M):
            vertices = np.unique(T[M == mat])
            for other in used.values():
                self.assertEqual(len(np.intersect1d(vertices, other)), 0, 'material seam shares UVs')
            used[mat] = vertices
            if mat in repeats:
                repeat = np.asarray(repeats[mat])
                expected = (P[vertices, :2] + np.asarray(origin)[:2]) / repeat
                delta = UV[vertices] - expected
                np.testing.assert_allclose(delta, np.broadcast_to(-np.floor(np.asarray(origin)[:2] / repeat), delta.shape),
                                           atol=1e-9)
            elif mat == 0:
                self.assertTrue((UV[vertices, 1] >= sw.V_BAND_LOW - 1e-9).all())
                self.assertTrue((UV[vertices, 1] <= sw.V_BAND_TOP + 1e-9).all())

    def test_metric_scale_on_narrow_wide_and_bent_walks(self):
        for width in (.3, .6, 1.2, 2.5, 4., 7.):
            with self.subTest(width=width):
                self.assert_mapping(self.run_mesh(width).arrays())

    def test_tactile_transition_does_not_stretch_adjacent_slab(self):
        b = self.run_mesh(ramps=[(5., 7.)])
        self.assertIn(2, b.arrays()[3])
        self.assert_mapping(b.arrays())

    def test_verge_and_driveway_keep_the_same_pavement_scale(self):
        b = self.run_mesh(verge=True, driveways=[(6., 9.)])
        mesh = b.arrays()
        self.assertIn(sw.GRASS, mesh[3])
        self.assert_mapping(mesh)

    def test_brick_and_driveway_keep_the_same_paver_scale(self):
        b = self.run_mesh(slab=sw.BRICK, driveways=[(6., 9.)])
        self.assert_mapping(b.arrays())

    def test_corner_uses_same_mapping_as_runs(self):
        b = self.run_mesh()
        t = np.linspace(0, np.pi / 2, 12)
        arc = np.c_[5 * np.cos(t), 5 * np.sin(t), np.zeros(len(t))]
        b.add_corner(arc, -arc[:, :2] / 5, [[0, 2.5, 0], [0, 0, 0], [2.5, 0, 0]])
        self.assert_mapping(b.arrays())

    def test_tile_origins_keep_same_phase_and_float_precision(self):
        curb = np.array([[100001., 200003., 10.], [100021., 200003., 10.]])
        meshes = []
        for origin in ((100000., 200000., 0.), (99997., 199997., 3.)):
            b = sw.Builder(origin)
            b.add_run(curb, np.tile([0., 1.], (2, 1)), 2.5)
            mesh = b.arrays()
            self.assert_mapping(mesh, origin)
            meshes.append(mesh[2][np.unique(mesh[1][mesh[3] == 1])])
        delta = meshes[0] - meshes[1]
        np.testing.assert_allclose(delta, np.round(delta), atol=1e-9)
        self.assertLess(np.abs(meshes).max(), 10)

    def test_uv_assignment_preserves_triangle_positions_and_collision(self):
        b = self.run_mesh(ramps=[(5., 7.)], driveways=[(12., 14.)])
        b._defer_surface_uvs = True
        raw = b._build()
        mapped = sw.surface_uvs(raw[0], b.origin)
        np.testing.assert_array_equal(mapped[0][mapped[1]], raw[0][0][raw[0][1]])
        np.testing.assert_array_equal(mapped[3], raw[0][3])
        for before, after in zip(raw[1], b.col.arrays()):
            np.testing.assert_array_equal(before, after)

    def test_shape_roundtrip_and_material_assets(self):
        b = self.run_mesh(verge=True, driveways=[(6., 9.)])
        with tempfile.TemporaryDirectory() as d:
            path = str(Path(d) / 'walk.cdae')
            b.write(path)
            shape = cdae.read(path)
        names = {m['name'] for m in shape['materials']}
        self.assertIn('bne_sidewalk_slab', names)
        self.assertNotIn('sidewalk1', names)
        asset = ROOT / 'mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/sidewalk.materials.json'
        material = json.loads(asset.read_text())['bne_sidewalk_slab']
        self.assertEqual(material['mapTo'], sw.MATERIALS[1])
        self.assertIn('/slabs_large/', material['Stages'][0]['baseColorMap'])
        roads = (ROOT / 'mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua').read_text()
        self.assertIn('/beamngEarth/sidewalk.materials.json', roads)


if __name__ == '__main__':
    unittest.main()
