"""Complete building mesh sets survive serialization, caching and chunk limits."""
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

import numpy as np

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import buildings as b
import blockworker
import cdae
import geotiles
import roads
from test_buildgen_topology import courtyard, planned


class ChunkTest(unittest.TestCase):
    def setUp(self):
        patch = mock.patch.dict(os.environ, {"BNE_BUILDING_GENERATOR": "v2"})
        patch.start()
        self.addCleanup(patch.stop)
        self.item = (planned(courtyard()), 0., 0.)
        self.mesh = b.build([self.item])

    def test_oversized_single_building_preserves_triangles_and_attributes(self):
        limit = 60
        chunks = b.build_parts([self.item], max_verts=limit, with_lod=True)
        self.assertGreater(len(chunks), 4)
        self.assertTrue(all(len(m[0]) <= limit for m in chunks))
        original = self.mesh
        for field in (0, 1, 5):
            rebuilt = np.concatenate([m[field][m[2]] for m in chunks])
            np.testing.assert_array_equal(rebuilt, original[field][original[2]])
        np.testing.assert_array_equal(np.concatenate([m[3] for m in chunks]), original[3])
        for m in chunks:
            self.assertGreaterEqual(int(m[2].min()), 0)
            self.assertLess(int(m[2].max()), len(m[0]))

    def test_near_tile_uses_smaller_import_chunks_without_losing_geometry(self):
        items = [self.item] * 50
        result = b.road_tile(None, 0, 0, None, None, items=items)
        chunks = result[0]
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(mesh[0]) <= b.V2_IMPORT_VERTS for mesh in chunks))
        self.assertEqual(sum(len(mesh[2]) for mesh in chunks), len(self.mesh[2])*50)

    def test_transport_writes_every_visual_and_collision_chunk(self):
        collision = b.collision_mesh([self.item])
        # Force the collision budget lower to exercise the actual writer's split.
        original_split = b.split_mesh
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(b, "split_mesh", side_effect=lambda m: original_split(m, 24)):
            roads.write_tile(tmp, "/vfs", 1, 0, 0, [], bld=([self.mesh] * 7, [], collision))
            data = json.loads((Path(tmp) / "roads_1_0_0.json").read_text())
            manifest = data["buildingChunks"]
            self.assertEqual(len(manifest["visual"]), 7)
            self.assertGreater(len(manifest["collision"]), 1)
            files = roads.shape_files(1, 0, 0, data=data)
            for what in roads.building_chunk_names(data):
                path = Path(tmp) / files[what]
                self.assertTrue(path.is_file(), what)
                self.assertEqual(data[what]["shape"], "/vfs/" + path.name)
                self.assertGreater(len(cdae.decode(path.read_bytes())["meshes"]), 0)

    def test_geotile_content_names_and_exact_variants_include_later_chunks(self):
        collision = b.collision_mesh([self.item])
        tile = geotiles.geobox(*geotiles.tile_of(39.28, -76.59))
        parts = types.SimpleNamespace(chunks=[], ctx={}, walks_raw=[], dmesh=None,
                                      bld=([self.mesh] * 6, [], collision), props=None, wires=None, park=None,
                                      tmesh=None, fuel=None, rmesh=None, guardrail_rows=(), garage_sound=(), wells=())
        with tempfile.TemporaryDirectory() as tmp:
            path, _, info = blockworker._write_geo_content(tmp, "/vfs", tile, parts)
            self.assertIn("bld6", info["parts"])
            self.assertFalse(info["parts"]["bld6"]["col"])
            self.assertTrue(info["parts"]["bldcol"]["col"])
            data = json.loads((Path(tmp) / Path(path).name).read_text())
            names = blockworker.geo_names(tile.key, parts=info["parts"])
            for what in roads.building_chunk_names(data):
                self.assertTrue((Path(tmp) / names[what]).is_file())
                self.assertEqual(data[what]["shape"], "/vfs/" + names[what])
            exact = blockworker._geo_exact(2, 39.29, -76.58, tile.gx, tile.gy, tmp, "/vfs", {"bld6": info["parts"]["bld6"]})
            self.assertIn("bld6", exact)
            self.assertTrue((Path(tmp) / Path(exact["bld6"]).name).is_file())

    def test_old_mod_is_blocked_before_v2_tiles_can_be_requested(self):
        import earthd
        connection = types.SimpleNamespace(status=mock.Mock())
        earthd.Connection.dispatch(connection, {"type": "hello", "buildingChunks": 0})
        self.assertTrue(connection.building_chunks_blocked)
        earthd.Connection.dispatch(connection, {"type": "pose"})
        self.assertEqual(connection.status.call_count, 2)
        self.assertIn("matching mod", connection.status.call_args.args[0])

    def test_manifest_rejects_duplicate_or_missing_chunks(self):
        for names in (["bld", "bld"], ["bld", "bld7"], ["../bld"]):
            data = {"buildingChunks": {"v": roads.BUILDING_CHUNKS, "visual": names, "collision": []},
                    "bld": {"shape": "bld.cdae"}}
            with self.assertRaises(ValueError):
                roads.building_chunk_names(data)


if __name__ == "__main__":
    unittest.main()
