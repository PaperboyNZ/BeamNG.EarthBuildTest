"""Compact geometry, regional identity, physical ownership and scaling contracts."""
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
import json
import pickle
import sys
import unittest
from unittest.mock import patch
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import freeze_items, facades, minimum, quality
from buildgen.progressive import DETAIL
from buildgen.topology import Footprint
from test_buildgen_regions import building, architecture
from test_buildgen_regional_blocks import building as block


@contextmanager
def tier(name):
    token=DETAIL.set(name)
    try:yield
    finally:DETAIL.reset(token)


class MinimumTests(unittest.TestCase):
    def test_analytical_roofs_preserve_full_planes_coverage_and_height(self):
        from buildgen import roofs, minimum_roofs
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        for angle in (0.,.41,1.7):
            c,s=np.cos(angle),np.sin(angle)
            xy=np.array(((0,0),(17,0),(17,9),(0,9)))@np.array(((c,s),(-s,c)))+np.array((103.,-57.))
            fp=Footprint(tuple(map(tuple,xy)))
            for kind in ('gabled','hipped'):
                for variant in ('standard','shed','saltbox','gambrel','mansard','broad_eave','industrial_barrel'):
                    with self.subTest(angle=angle,kind=kind,variant=variant):
                        full=roofs._envelope(fp,kind,variant)
                        compact=minimum_roofs.envelope(fp,kind,variant)
                        self.assertIsNotNone(compact)
                        np.testing.assert_allclose(compact.planes,full.planes,atol=1e-10)
                        self.assertAlmostEqual(compact.peak,full.peak,places=7)
                        cover=unary_union([Polygon([p[:2] for p in tri]) for tri in compact.triangles])
                        self.assertLess(cover.symmetric_difference(fp.shape()).area,1e-7)
                        area=sum(Polygon([p[:2] for p in tri]).area for tri in compact.triangles)
                        self.assertAlmostEqual(area,fp.area,places=7)
        concave=Footprint(((0,0),(10,0),(10,5),(5,5),(5,10),(0,10)))
        self.assertIsNone(minimum_roofs.envelope(concave,'gabled','standard'))

    def test_all_regions_keep_identity_materials_roofs_and_valid_topology(self):
        signatures=set()
        for theme in architecture.catalogue():
            spec=building(theme)
            expected=(spec.seed,spec.roof,spec.roof_mat,spec.facade,spec.inference)
            with tier('minimum'),patch.object(facades,'plan',side_effect=AssertionError('full facade planner')):
                items=freeze_items([(spec,0.,0.)])
                restored=pickle.loads(pickle.dumps(items))
                mesh=b.build(restored);coll=b.collision_mesh(restored)
            frozen=items[0][0]
            self.assertEqual(expected,(frozen.seed,frozen.roof,frozen.roof_mat,frozen.facade,frozen.inference))
            self.assertIsNone(frozen.facades)
            for product in (mesh,coll):
                self.assertTrue(np.isfinite(product[0]).all(),theme)
                self.assertTrue(np.isfinite(product[1]).all(),theme)
                self.assertGreaterEqual(product[2].min(),0)
                self.assertLess(product[2].max(),len(product[0]))
            self.assertAlmostEqual(mesh[0][:,2].max(),coll[0][:,2].max(),places=5,msg=theme)
            signatures.add((spec.roof,spec.roof_mat,spec.facade))
        self.assertGreater(len(signatures),16)

    def test_upper_storey_geometry_cost_is_constant(self):
        meshes=[]
        for floors in (6,60,120):
            spec=block(floors=floors,facade_material='concrete')
            with tier('minimum'):meshes.append(b.build(freeze_items([(spec,0.,0.)])))
        # Midrise and tower inference may choose different ground-floor bays;
        # doubling a tower's storeys must not double its mesh work.
        self.assertEqual(len(meshes[1][0]),len(meshes[2][0]))
        self.assertLess(max(len(m[0]) for m in meshes),400)
        self.assertTrue(any(b.MATERIALS[i].startswith('bne_minimum_') for i in meshes[0][3]))

    def test_recess_and_courtyard_are_not_filled(self):
        fp=Footprint(((0,0),(30,0),(30,20),(0,20)),(((8,6),(8,14),(22,14),(22,6)),))
        spec=building('nz_temperate',fp=fp,roof_shape='flat')
        with tier('minimum'):
            items=freeze_items([(spec,0.,0.)]);mesh=b.collision_mesh(items)
        from shapely.geometry import Point,Polygon
        hole=Polygon(fp.holes[0])
        for tri in mesh[0][mesh[2]]:
            if np.ptp(tri[:,2])<1e-8 and tri[0,2]>1:
                self.assertFalse(hole.contains(Point(tri[:,:2].mean(0))))

    def test_removed_bays_never_leave_invisible_collision(self):
        spec=building('nz_temperate')
        with tier('minimum'),patch('buildgen.regional_facade_details.draw_collision_bays',side_effect=AssertionError('bay collision')),\
             patch('buildgen.regional_facade_details.bay_boxes',side_effect=AssertionError('bay occupancy')):
            items=freeze_items([(spec,0.,0.)])
            self.assertIsNotNone(b.collision_mesh(items));self.assertTrue(b.collider_boxes(items,0,0))

    def test_commercial_entrance_has_a_visible_stock_door(self):
        spec=block(floors=8,**{'class':'office'})
        spec.door=None
        line=[(np.array(((-10.,-8.),(50.,-8.))),3.,'residential',False)]
        with tier('minimum'),patch('buildgen.commercial.resolve',side_effect=AssertionError('detailed commercial plan')):
            rows=b.doors([(spec,0.,0.)],line,0,0,ground=lambda xy:np.zeros(len(xy)))
        self.assertTrue(any(row[0]==b.G_DOOR for row in rows))
        self.assertIsNotNone(spec.access)

    def test_minimum_is_a_separate_physical_policy_and_stable_ceiling(self):
        from types import SimpleNamespace
        with tier('minimum'):
            self.assertEqual(quality.site_level(),-1)
            self.assertEqual(quality.import_vertices(),20000)
        self.assertTrue(quality.needs_rebuild('ultra','minimum','minimum'))
        self.assertTrue(quality.needs_rebuild('minimum','low','low'))
        self.assertTrue(quality.needs_rebuild(None,'minimum','minimum'))
        for busy in (False,True):
            self.assertEqual(quality.adaptive_target(SimpleNamespace(),SimpleNamespace(building_quality='minimum'),100,busy=busy),'minimum')

    def test_shared_window_assets_have_masks_and_registered_materials(self):
        from PIL import Image
        root=Path(__file__).resolve().parents[2]/'mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth'
        materials=json.loads((root/'buildings.materials.json').read_text())
        for kind in ('sash','tall','wide','modern'):
            name='bne_minimum_'+kind
            self.assertIn(name,b.MATERIALS)
            self.assertTrue(materials[name]['alphaTest'])
            self.assertFalse(materials[name]['Stages'][0]['vertColor'])
            with Image.open(root/(name+'.png')) as image:
                alpha=np.asarray(image)[:,:,3]
                self.assertEqual(set(np.unique(alpha)),{0,255})
            self.assertTrue((root/(name+'.dds')).is_file())

    def test_distant_jobs_capture_quality_and_restore_worker_context(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from earthd import Connection
        import building_settings
        server=SimpleNamespace(build_far_geo=Mock(return_value='ready'))
        conn=SimpleNamespace(s=server,building_quality='minimum',roads=SimpleNamespace())
        callback=building_settings.run('v2',Connection.build_far_geo,conn,'bldfar')
        conn.building_quality='ultra'
        self.assertEqual(callback(1,2),'ready')
        server.build_far_geo.assert_called_once_with('bldfar',1,2,building_detail='minimum')
        with tier('high'):
            self.assertEqual(quality.run('minimum',DETAIL.get),'minimum')
            self.assertEqual(DETAIL.get(),'high')
            with self.assertRaises(ValueError):quality.run('minimum',lambda: (_ for _ in ()).throw(ValueError()))
            self.assertEqual(DETAIL.get(),'high')

    def test_far_paths_are_distinct_and_switch_queues_replacements(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from earthd import Connection
        import blockworker as bw
        with tier('minimum'):compact=bw.far_geo_names('bldfar','g1')
        with tier('full'):normal=bw.far_geo_names('bldfar','g1')
        self.assertNotEqual(compact,normal)
        far=Mock();sky=Mock()
        conn=SimpleNamespace(lod_scale=1.,tree_scale=1.,building_scale=1.,veg=SimpleNamespace(send_m=1300),
            bldfar=far,bldsky=sky,s=SimpleNamespace(base_px=2048),view_cap=None,active=None)
        Connection.set_graphics(conn,dict(buildingQuality='minimum'))
        Connection.set_graphics(conn,dict(buildingQuality='minimum'))
        far.change_generator.assert_called_once();sky.change_generator.assert_called_once()
        Connection.set_graphics(conn,dict(buildingQuality='ultra'))
        self.assertEqual(far.change_generator.call_count,2)


if __name__=='__main__':unittest.main()
