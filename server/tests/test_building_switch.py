"""Live mode changes retain the world and reject superseded building jobs."""
from concurrent.futures import Future, ThreadPoolExecutor, ProcessPoolExecutor
from pathlib import Path
import sys
import threading
import tempfile
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import building_settings as modes
import blockworker
import earthd
import revisit
import roads
import vegetation
from buildgen import ingest


def process_mode():
    return modes.current(), ingest.enabled(), os.getpid()


class LiveBuildingSwitchTests(unittest.TestCase):
    def setUp(self):
        self.default = patch.object(modes, '_default', 'v2')
        self.default.start()
        self.addCleanup(self.default.stop)

    def connection(self):
        c = SimpleNamespace(active=7, road_geo=True, building_chunks_supported=True,
                            building_progress_supported=True, building_progress=True)
        c.messages = []
        c.send = c.messages.append
        c.roads = roads.GeoTracker()
        c.roads.aid = 7
        c.bldfar = vegetation.Tracker(kind='bldfar', geo=True)
        c.bldsky = vegetation.Tracker(kind='bldsky', geo=True)
        c.brfar = vegetation.Tracker(kind='brfar', geo=True)
        c.veg = vegetation.Tracker(geo=True)
        c.s = SimpleNamespace(connections=[c], anchors={7: object()}, out_dir=None,
                              mapdata=object(), imagery=object(), dem=object())
        return c

    def test_round_trip_preserves_world_and_resident_tiles(self):
        c = self.connection()
        key = (65536, 65536)
        c.roads.sent.add(key); c.roads.skins.add(key)
        c.roads.info[key] = {'h': 'accepted'}
        c.bldfar.sent.add(key); c.bldsky.sent.add(key)
        c.veg.sent.add(key); c.brfar.sent.add(key)
        before = (c.s.anchors, c.s.mapdata, c.s.imagery, c.s.dem, c.veg, c.brfar)
        for value in ('legacy', 'v2', 'legacy'):
            self.assertTrue(earthd.Connection.change_building_generator(c, value))
            self.assertEqual(modes.current(), value)
            self.assertEqual(c.active, 7)
            self.assertEqual(before, (c.s.anchors, c.s.mapdata, c.s.imagery, c.s.dem, c.veg, c.brfar))
            self.assertEqual(c.roads.sent, {key})
            self.assertEqual(c.roads.skins, {key})
            self.assertEqual(c.roads.info[key]['h'], 'accepted')
            self.assertIn(key, c.roads.regenerate)
            self.assertIn(key, c.bldfar.refinements)
            self.assertEqual(c.veg.generation_epoch, 0)
            self.assertEqual(c.brfar.generation_epoch, 0)
            self.assertEqual(c.building_progress, value == 'v2')
        self.assertTrue(all(m['type'] == 'building_generator' for m in c.messages))

    def test_invalid_or_incompatible_request_preserves_mode_and_world(self):
        c = self.connection()
        self.assertFalse(earthd.Connection.change_building_generator(c, 'wrong'))
        c.road_geo = False
        self.assertFalse(earthd.Connection.change_building_generator(c, 'legacy'))
        self.assertEqual(modes.current(), 'v2')
        self.assertEqual(c.roads.generation_epoch, 0)
        self.assertEqual(c.active, 7)

    def test_late_near_job_cannot_replace_current_generation(self):
        c = self.connection(); key = (65536, 65536)
        future = Future(); c.roads.futs[key] = future; c.roads.building.add(key)
        epoch = c.roads.generation_epoch
        earthd.Connection.change_building_generator(c, 'legacy')
        future.set_result({'content': ('/old.json', 0, {'h': 'old', 'parts': {}}, [])})
        c.roads._built(c, 7, key, future, True, True, 'auto', generation_epoch=epoch)
        self.assertNotIn(key, c.roads.building)
        self.assertNotIn(key, c.roads.info)
        self.assertIn(key, c.roads.regenerate)
        self.assertFalse(any(m['type'] == 'roads_tile' for m in c.messages))

    def test_active_peer_without_building_chunks_blocks_live_switch(self):
        c = self.connection()
        peer = self.connection()
        peer.building_chunks_supported = False
        c.s.connections.append(peer)
        self.assertFalse(earthd.Connection.change_building_generator(c, 'legacy'))
        self.assertEqual(modes.current(), 'v2')
        self.assertEqual(c.roads.generation_epoch, 0)
        self.assertEqual(peer.roads.generation_epoch, 0)
        self.assertIn('older mod', c.messages[-1]['error'])

    def test_inactive_older_peer_does_not_block_live_switch(self):
        c = self.connection()
        peer = self.connection()
        peer.active = None
        peer.building_chunks_supported = False
        c.s.connections.append(peer)
        self.assertTrue(earthd.Connection.change_building_generator(c, 'legacy'))
        self.assertEqual(modes.current(), 'legacy')

    def test_late_far_job_cannot_replace_current_generation(self):
        c = self.connection(); key = (65536, 65536)
        future = Future(); c.bldfar.futs[key] = future; c.bldfar.building.add(key)
        c.bldfar.sent.add(key)
        epoch = c.bldfar.generation_epoch
        earthd.Connection.change_building_generator(c, 'legacy')
        future.set_result(('/old.json', 0, (0, 0), 0, {}))
        c.bldfar._built_geo(c, key, future, epoch)
        self.assertIn(key, c.bldfar.sent)
        self.assertIn(key, c.bldfar.refinements)
        self.assertNotIn(key, c.bldfar.building)
        self.assertFalse(any(m['type'] == 'bldfar_tile' for m in c.messages))

    def test_worker_modes_are_isolated_even_during_concurrent_builds(self):
        barrier = threading.Barrier(2)
        def work():
            before = ingest.enabled()
            barrier.wait(timeout=5)
            return before, ingest.enabled()
        with ThreadPoolExecutor(2) as pool:
            simple = pool.submit(modes.run, 'legacy', work)
            advanced = pool.submit(modes.run, 'v2', work)
            self.assertEqual(simple.result(), (False, False))
            self.assertEqual(advanced.result(), (True, True))
        self.assertEqual(modes.current(), 'v2')

    def test_existing_worker_process_switches_modes_without_restart(self):
        import multiprocessing
        with ProcessPoolExecutor(1, mp_context=multiprocessing.get_context('spawn')) as pool:
            rows = [pool.submit(modes.run, mode, process_mode).result(timeout=30)
                    for mode in ('legacy', 'v2', 'legacy')]
        self.assertEqual([r[:2] for r in rows], [('legacy', False), ('v2', True), ('legacy', False)])
        self.assertEqual(len({r[2] for r in rows}), 1)

    def test_road_worker_keeps_mode_and_progress_with_running_timeout(self):
        from unittest.mock import Mock
        result = {'content': None}
        future = Future(); future.set_result(result)
        pool = SimpleNamespace(submit=Mock(return_value=future))
        anchor = SimpleNamespace(lat=1., lon=2., zooms=(15,))
        server = SimpleNamespace(anchors={7: anchor}, mapdata=True, road_pool=pool,
            geo_rules=lambda *args: (False, False, 0., None, 'NZ', 15),
            out_dir='unused', vfs_dir='/test', sidewalks=True, near_visual='detail',
            buildings=True, gas_stations=False, anchor_q=lambda a: 0.)
        with patch.object(earthd.poolsmod, 'result_running', wraps=earthd.poolsmod.result_running) as wait:
            got = modes.run('legacy', earthd.Server.build_roads_geo, server, 7, 1, 2,
                            progress_token='progress', building_detail='fast', building_view={'x': 1})
        self.assertIs(got, result)
        args = pool.submit.call_args.args
        self.assertEqual(args[:3], (modes.run, 'legacy', blockworker.roads_geo))
        self.assertEqual(args[-3:], ('progress', 'fast', {'x': 1}))
        self.assertIs(wait.call_args.args[0], future)
        self.assertEqual(wait.call_args.args[1], earthd.ROAD_TILE_TIMEOUT_S)

    def test_area_prebuild_keeps_optional_admission_and_low_priority(self):
        from unittest.mock import Mock
        future = Future(); future.set_result('cached')
        pool = SimpleNamespace(submit=Mock(), submit_low=Mock(return_value=future))
        server = SimpleNamespace(mapdata=True, road_pool=pool, cache_dir='unused',
            geo_rules=lambda *args: (False, False, 0., None, 'NZ', 15),
            buildings=True, gas_stations=False)
        with patch.object(revisit, 'ON', True):
            got = modes.run('legacy', earthd.Server.prebuild_geo, server, 1, 2)
        self.assertEqual(got, 'cached')
        pool.submit.assert_not_called()
        self.assertEqual(pool.submit_low.call_args.args[:3],
                         (modes.prebuild, 'legacy', blockworker.prebuild_geo))
        self.assertTrue(pool.submit_low.call_args.args[0].__name__.startswith('prebuild'))

    def test_only_building_dependent_cache_keys_change(self):
        for kind in ('roads', 'roadsg', 'bldfar', 'bldsky', 'fargeo', 'far', 'plans', 'brfar'):
            a = modes.run('legacy', revisit.key, kind, 'same-input')
            b = modes.run('v2', revisit.key, kind, 'same-input')
            if kind in ('roads', 'roadsg', 'bldfar', 'bldsky'):
                self.assertNotEqual(a, b, kind)
            else:
                self.assertEqual(a, b, kind)
        key = 'g17_65536_65536'
        self.assertNotEqual(modes.run('legacy', blockworker.geo_names, key), modes.run('v2', blockworker.geo_names, key))
        for kind in ('bldfar', 'bldsky', 'brfar'):
            a = modes.run('legacy', blockworker.far_geo_names, kind, key)
            b = modes.run('v2', blockworker.far_geo_names, kind, key)
            self.assertEqual(a == b, kind == 'brfar')

    def test_compiled_geometry_round_trip_reuses_each_modes_cache(self):
        import numpy as np
        import buildings
        import geotiles
        from test_buildgen_topology import FlatFrame, features, rect
        layer = features([[(rect(10, 10, 35, 35), (rect(20, 20, 10, 10))),
                           (rect(60, 10, 15, 15),)]], height=[8.], **{'class': ['apartments']})
        tile = geotiles.geobox(65536, 65536)
        compiled = []
        def parts(*args, **kwargs):
            compiled.append(modes.current())
            items = buildings.tile_buildings(FlatFrame(), 0, 0, 100, 100, [layer],
                                            lambda la, lo: np.zeros(np.shape(la)))
            mesh = buildings.road_tile(None, 0, 0, None, None, items=items)
            return SimpleNamespace(chunks=[], ctx=[], walks_raw=[], plans=(), fuel_pads=[],
                dmesh=None, tmesh=None, rmesh=None, bld=mesh, props=[], wires=[], park=[],
                fuel=[], guardrail_rows=[], garage_sound=[], wells=[], vegetation_exclusions=[])
        with tempfile.TemporaryDirectory() as folder:
            cache = str(Path(folder) / 'cache'); out = Path(folder) / 'out'; out.mkdir()
            worker = SimpleNamespace(cache_dir=cache, md=SimpleNamespace(versions=lambda: {'buildings': 'fixture'}))
            try:
                with patch.object(blockworker, '_s', worker), patch.object(blockworker, '_frame_grader', return_value=None), \
                     patch.object(blockworker, '_tile_parts', side_effect=parts), patch.object(revisit, 'ON', True):
                    results = []
                    for mode in ('legacy', 'v2', 'legacy', 'v2'):
                        result = modes.run(mode, blockworker._geo_content, 65536, 65536, 15, str(out), '/test',
                                           True, False, False, False, 0., None, None)
                        data = json.loads((out / Path(result[0]).name).read_text())
                        results.append(data)
                    self.assertEqual(compiled, ['legacy', 'v2'])
                    self.assertNotEqual(results[0]['h'], results[1]['h'])
                    self.assertEqual(results[0], results[2])
                    self.assertEqual(results[1], results[3])
                    self.assertNotIn('buildingChunks', results[0])
                    self.assertTrue(results[1]['buildingChunks']['visual'])
            finally:
                descriptor = revisit._where.pop(cache, None)
                if descriptor is not None:os.close(descriptor)


if __name__ == '__main__':
    unittest.main()
