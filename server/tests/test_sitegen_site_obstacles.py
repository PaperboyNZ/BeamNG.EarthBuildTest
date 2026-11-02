"""Site exclusions preserve map geometry and never fetch missing layers."""
from pathlib import Path
import os
import copy
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import geodesy
import mapgeom
from sitegen import site_obstacles


class SiteObstacleTests(unittest.TestCase):
    def setUp(self):
        self.frame = geodesy.EnuFrame(-43.5, 172.6)
        self.bounds = (100., 200., 140., 240.)

    def ring(self, xy):
        p = np.array(xy, float)
        lat, lon, _ = self.frame.enu_to_geodetic(p[:, 0], p[:, 1], np.zeros(len(p)))
        return np.column_stack((lon, lat))

    def test_lower_policies_skip_eligible_frontage_inventory_before_any_work(self):
        from buildgen import automatic_sites, quality
        class Eligible:
            access=object();site=None;door=(0,0);min_h=0
            inference=SimpleNamespace(use=SimpleNamespace(value='commercial'))
        spec=Eligible()
        with patch.dict(os.environ,{'BNE_BUILDING_PATHS':'auto'}):
            self.assertTrue(automatic_sites.eligible(spec))
            for detail in ('minimum','very_low','low'):
                with self.subTest(detail=detail), \
                     patch.object(automatic_sites,'eligible',side_effect=AssertionError('eligibility scan')), \
                     patch.object(site_obstacles,'cached_water',side_effect=AssertionError('water inventory')), \
                     patch.object(site_obstacles,'collect',side_effect=AssertionError('hazard inventory')):
                    self.assertEqual(quality.run(detail,site_obstacles.for_items,
                        [(spec,0,0)],object(),self.frame,self.bounds,keys=range(65)),())

    def test_complete_site_policies_keep_full_eligible_frontage_inventory(self):
        from buildgen import quality
        class Eligible:
            access=object();site=None;door=(0,0);min_h=0
            inference=SimpleNamespace(use=SimpleNamespace(value='commercial'))
        water=object();cell=object();result=(Point(2,3).buffer(1.),)
        chunks=[object()];drives=[object()];pads=[object()];surface=object()
        for detail in ('medium','high','very_high','ultra'):
            with self.subTest(detail=detail), patch.dict(os.environ,{'BNE_BUILDING_PATHS':'auto'}), \
                 patch.object(site_obstacles,'cached_water',return_value=(water,)) as cached, \
                 patch.object(site_obstacles,'collect',return_value=result) as collect:
                got=quality.run(detail,site_obstacles.for_items,[(Eligible(),0,0)],None,
                    self.frame,self.bounds,keys=('key',),cells=(cell,),chunks=chunks,
                    drives=drives,fuel_pads=pads,surface=surface)
                self.assertIs(got,result)
                cached.assert_called_once_with(None,('key',))
                collect.assert_called_once_with(self.frame,self.bounds,chunks=chunks,
                    fuel_pads=pads,surface=surface,cells=(cell,water),drives=drives)

    def test_inventory_gate_preserves_accepted_lower_policy_frontage(self):
        from buildgen import automatic_sites,quality
        from test_buildgen_commercial import fixture
        from test_buildgen_automatic_sites import road,flat
        with patch.dict(os.environ,{'BNE_BUILDING_PATHS':'auto'}):
            item=quality.run('medium',fixture,'supermarket',40,20)
            quality.run('medium',automatic_sites.resolve,[item],road(),0,0,ground=flat)
            spec=item[0];accepted=spec.access
            self.assertIsNotNone(accepted.site_layout)
            self.assertTrue(any(s.kind.startswith('site_') for s in accepted.solids))
            walks=[dict(pts=[[0.,-20.,0.],[50.,-20.,0.]],side=1,w=2.5)]
            original_walks=copy.deepcopy(walks)
            retained=automatic_sites._retained_records([item],walks,0,0)
            for detail in ('minimum','very_low','low'):
                with self.subTest(detail=detail), \
                     patch.object(site_obstacles,'cached_water',side_effect=AssertionError('water inventory')), \
                     patch.object(site_obstacles,'collect',side_effect=AssertionError('hazard inventory')), \
                     patch.object(automatic_sites,'_resolve_staged',side_effect=AssertionError('replacement planning')):
                    obstacles=quality.run(detail,site_obstacles.for_items,[item],None,self.frame,self.bounds)
                    result=quality.run(detail,automatic_sites.resolve,[item],road(),0,0,
                        ground=lambda p:self.fail('ground query'),walks=walks,obstacles=obstacles)
                    self.assertEqual(result,retained)
                    self.assertIs(spec.access,accepted)
                    self.assertEqual(walks,original_walks)

    def test_water_hole_and_rail_use_frame_then_tile_origin(self):
        outer = self.ring([(102,202),(118,202),(118,218),(102,218),(102,202)])
        hole = self.ring([(106,206),(114,206),(114,214),(106,214),(106,206)])
        line = self.ring([(125,202),(125,218)])
        water = mapgeom.build('water', np.array(['water']), [(mapgeom.POLYGON, [[outer, hole]])])
        rail = mapgeom.build('roads', np.array(['rail']), [(mapgeom.LINE, [[line]])])
        rail.attrs['subtype'] = np.array(['rail'])
        got = site_obstacles.collect(self.frame, self.bounds, cells=[SimpleNamespace(layers={'water':water, 'roads':rail})])
        self.assertTrue(any(p.covers(Point(3,3)) for p in got))
        self.assertFalse(any(p.covers(Point(10,10)) for p in got))
        self.assertTrue(any(p.covers(Point(25,10)) for p in got))
        self.assertFalse(any(p.covers(Point(35,10)) for p in got))

    def test_road_fuel_and_mapped_surfaces_are_clipped_local(self):
        import roadmesh
        from sitegen import mapped_surfaces
        from shapely.geometry import box
        left = np.array([[95.,205.],[110.,205.]])
        right = np.array([[95.,209.],[110.,209.]])
        chunk = {'n': [[95,207,0],[110,207,0]], 'w':4}
        fuel = self.ring([(130,230),(145,230),(145,245),(130,245),(130,230)])
        with patch.object(roadmesh, 'ribbon_pairs', return_value=[((left,right,None,None,None,None),chunk)]), \
             patch.object(mapped_surfaces, 'collect', return_value=(('parking', box(115,220,120,225)),)):
            got = site_obstacles.collect(self.frame, self.bounds, chunks=[chunk],
                fuel_pads=[('fuel', [(fuel[:,1],fuel[:,0])])])
        for point in [(2,7),(17,22),(35,35)]:
            self.assertTrue(any(p.covers(Point(*point)) for p in got), point)
        self.assertTrue(all(0 <= v <= 40 for p in got for v in p.bounds))

    def test_real_polygon_only_road_chunk_is_not_tile_fallback(self):
        chunk = {'n': [], 'w': 0.0, 'poly': [[102,202],[110,202],[110,210],[102,210]]}
        got = site_obstacles.collect(self.frame, self.bounds, chunks=[chunk])
        self.assertTrue(any(p.covers(Point(5,5)) for p in got))
        self.assertFalse(any(p.covers(Point(35,35)) for p in got))

    def test_invalid_or_over_budget_fails_closed(self):
        bad = {'n': [[0, float('nan'), 0],[1,2,0]], 'w':4}
        self.assertEqual(site_obstacles.collect(self.frame, self.bounds, chunks=[bad])[0].bounds, (0,0,40,40))
        with patch.object(site_obstacles, 'MAX_INPUTS', 0):
            self.assertEqual(site_obstacles.collect(self.frame, self.bounds, cells=[None])[0].bounds, (0,0,40,40))
        with self.assertRaises(ValueError):
            site_obstacles.collect(self.frame, (0,0,0,1))

    def test_cached_water_memory_disk_missing_and_no_network(self):
        import mapdata
        outer=self.ring([(102,202),(118,202),(118,218),(102,218),(102,202)])
        memory=mapgeom.build('water',np.array(['memory']),[(mapgeom.POLYGON,[[outer]])])
        disk=mapgeom.build('water',np.array(['disk']),[(mapgeom.POLYGON,[[outer]])])
        tmp_root=Path(__file__).resolve().parents[2]/'build'/'tmp'
        tmp_root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp_root) as tmp:
            root=Path(tmp)
            arrays=disk.to_arrays('');arrays['provenance']=np.array('{}')
            np.savez_compressed(root/'disk.npz',**arrays)
            np.savez_compressed(root/'missing.npz',provenance=np.array('{}'),missing=np.array(True))
            calls=[]
            data=SimpleNamespace(_mem_lock=threading.Lock(),_mem={(str('memory'),'water'):(memory,None,0)},
                path=lambda key,layer:root/(str(key)+'.npz'),
                cell=lambda *a,**k:self.fail('network-capable cell called'))
            def load(path):
                calls.append(path.name)
                return mapdata.MapData._load(data,path)
            data._load=load
            got=site_obstacles.cached_water(data,['memory','disk','missing','absent'])
            self.assertEqual([str(x.ids[0]) for x in got],['memory','disk'])
            self.assertEqual(calls,['disk.npz','missing.npz','absent.npz'])

    def test_cached_water_budget_counts_misses_and_memory_hits(self):
        data=SimpleNamespace(_mem_lock=threading.Lock(),_mem={},path=lambda key,layer:key,
            _load=lambda path:None,cell=lambda *a,**k:self.fail('network-capable cell called'))
        self.assertEqual(site_obstacles.cached_water(data,range(64)),())
        with self.assertRaisesRegex(ValueError,'water cell budget'):
            site_obstacles.cached_water(data,range(65))
        data._mem={(str(i),'water'):(None,None,0) for i in range(65)}
        with self.assertRaisesRegex(ValueError,'water cell budget'):
            site_obstacles.cached_water(data,range(65))
        # A denied oversized inventory fails closed without invoking a map fetch.
        class Eligible:
            access=object(); site=None; door=(0,0); min_h=0
            inference=SimpleNamespace(use=SimpleNamespace(value='commercial'))
        got=site_obstacles.for_items([(Eligible(),0,0)],data,self.frame,self.bounds,keys=range(65))
        self.assertEqual(got[0].bounds,(0,0,40,40))

    def test_empty_cached_sources_do_not_invent_obstacles(self):
        self.assertEqual(site_obstacles.collect(self.frame, self.bounds), ())


if __name__ == '__main__':
    unittest.main()
