"""Grounds demand remains independent of building presentation and worker reuse."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import blockworker as bw
from buildgen import grounds_quality as grounds, quality, products
from buildgen.progressive import DETAIL, ACTIVE
import geotiles
import tempfile
from pathlib import Path
import json
import test_buildgen_products as fixtures


class GroundsQualityTests(unittest.TestCase):
    def test_explicit_grounds_policy_survives_every_building_quality(self):
        for name in quality.NAMES:
            levels=[]
            for building in quality.NAMES:
                levels.append(grounds.run(name,quality.run,building,quality.site_level))
            self.assertEqual(levels,[grounds.run(name,grounds.site_level)]*len(quality.NAMES))

    def test_worker_captures_independent_quality_and_restores_context_after_failure(self):
        tile=geotiles.geobox(*geotiles.tile_of(0.,0.)); seen=[]
        def build(*args):
            seen.append((grounds.current(),DETAIL.get()))
            raise RuntimeError('worker failure')
        with patch.object(bw,'_geo_content',side_effect=build),\
             patch.object(bw,'_s',SimpleNamespace(md=None)):
            with self.assertRaises(RuntimeError):
                bw.roads_geo(1,0.,0.,15,tile.gx,tile.gy,15,'.','/fixture',True,0.,True,False,False,None,False,
                             skin=False,building_detail='minimum',grounds_quality='ultra')
        self.assertEqual(seen,[('ultra','minimum')])
        self.assertIsNone(grounds.CURRENT.get())
        self.assertEqual(DETAIL.get(),'full')
        self.assertIsNone(ACTIVE.get())

    def test_grounds_recipes_have_distinct_road_visual_cache_identity(self):
        with patch.object(bw,'_s',SimpleNamespace(md=None)):
            keys=[grounds.run(n,bw._geo_content_key,'tile',15,True,False,False,False,0.,None,None,md={})
                  for n in quality.NAMES]
        self.assertEqual(len(set(keys)),len(quality.NAMES))

    def test_grounds_change_queues_complete_transaction_and_building_change_does_not_change_grounds(self):
        from earthd import Connection
        calls=[]
        conn=SimpleNamespace(lod_scale=1.,tree_scale=1.,building_scale=1.,veg=SimpleNamespace(send_m=1300),
            bldfar=SimpleNamespace(send_m=1600),s=SimpleNamespace(base_px=2048),view_cap=None,active=None,
            roads=SimpleNamespace(change_generator=lambda c:calls.append(c.grounds_quality)))
        Connection.set_graphics(conn,dict(buildingQuality='high',groundsQuality='low'))
        Connection.set_graphics(conn,dict(buildingQuality='minimum'))
        self.assertEqual(conn.grounds_quality,'low')
        self.assertFalse(calls)
        Connection.set_graphics(conn,dict(groundsQuality='ultra'))
        self.assertEqual(calls,['ultra'])
        Connection.set_graphics(conn,dict(groundsQuality='ultra'))
        self.assertEqual(calls,['ultra'])
        Connection.set_graphics(conn,dict(groundsQuality='invalid'))
        self.assertEqual(conn.grounds_quality,'ultra')

    def test_ground_context_restores_after_invalid_value(self):
        with self.assertRaises(ValueError):grounds.run('invalid',lambda:None)
        self.assertIsNone(grounds.CURRENT.get())

    def test_simple_worker_submission_ignores_saved_advanced_grounds_choice(self):
        from concurrent.futures import Future
        from earthd import Server
        import building_settings
        captured=[]
        class Pool:
            def submit(self,*args,**kwargs):
                captured.append(kwargs);future=Future();future.set_result(None);return future
        server=SimpleNamespace(anchors={1:SimpleNamespace(lat=0.,lon=0.,zooms=[15])},mapdata=object(),
            road_pool=Pool(),geo_rules=lambda *a:(False,False,0.,None,None,15),out_dir='.',vfs_dir='/fixture',
            sidewalks=True,near_visual='detail',buildings=True,gas_stations=False)
        for mode in ('legacy','v2'):
            building_settings.run(mode,Server.build_roads_geo,server,1,0,0,skin=False,grounds_quality='ultra')
        self.assertEqual([c['grounds_quality'] for c in captured],['minimum','ultra'])

    def test_recipe_revisions_change_road_cache_identity(self):
        import sidewalk_outline,sidewalk_rounding
        args=('tile',15,True,False,False,False,0.,None,None)
        with patch.object(bw,'_s',SimpleNamespace(md=None)):
            first=grounds.run('low',bw._geo_content_key,*args,md={})
            with patch.object(sidewalk_outline,'REVISION','new-outline'):
                self.assertNotEqual(first,grounds.run('low',bw._geo_content_key,*args,md={}))
            with patch.object(sidewalk_rounding,'REVISION','new-nose'):
                self.assertNotEqual(first,grounds.run('low',bw._geo_content_key,*args,md={}))

    def test_every_building_ceiling_reuses_physics_with_an_independent_fixed_grounds_policy(self):
        fixture=fixtures.IndependentProductsTests()
        grounds.run('ultra',fixture.setUp);self.addCleanup(fixture.doCleanups)
        before_dir,before=grounds.run('ultra',fixture.retain_lite)
        for name in quality.NAMES:
            out=fixture.root/('fixed-grounds-'+name);out.mkdir()
            with patch.object(bw,'_tile_parts',side_effect=AssertionError('replanned physical surfaces')),\
                 patch.object(bw,'_frame_grader',side_effect=AssertionError('replanned terrain')):
                result=grounds.run('ultra',quality.run,name,bw._geo_content,
                    fixture.gx,fixture.gy,15,str(out),'/fixed',True,False,False,False,0.,None,None)
            self.assertIsNotNone(result)
            after=json.loads((out/bw.geo_names(fixture.tile.key)['json']).read_text())
            self.assertEqual(after['physicalHash'],before['physicalHash'])
            self.assertEqual(after['sectorManifest']['physical'],before['sectorManifest']['physical'])
            for what in before['buildingChunks']['collision']:
                filename=bw.geo_names(fixture.tile.key,parts={what:{}})[what]
                self.assertEqual((before_dir/filename).read_bytes(),(out/filename).read_bytes())
