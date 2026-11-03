"""Hard surfaces protect natural props; accepted green patches remain available."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from shapely.geometry import Point, Polygon

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sitegen import hardscape
from buildgen.access import Solid, AccessPlan


def solid(kind, x=0., y=0., z=2.):
    return Solid(kind, ((x,y,z),(x+2,y,z),(x+2,y+2,z),(x,y+2,z)), z-.1)


class HardscapeTests(unittest.TestCase):
    def test_physical_surfaces_export_but_green_patches_remain_soft(self):
        access=AccessPlan(2.,None,(solid('path'),solid('parking',4)),(),
                          (solid('garden_bed',8),solid('lawn_margin',12)))
        s=SimpleNamespace(access=access,garage_access=None)
        data=hardscape.collect([(s,0,0)],origin=(100,200))
        shapes=[Polygon(r['rings'][0],r['rings'][1:]) for r in data['polygons']]
        self.assertEqual(len(shapes),2)
        self.assertTrue(any(p.covers(Point(101,201)) for p in shapes))
        self.assertFalse(any(p.covers(Point(109,201)) or p.covers(Point(113,201)) for p in shapes))
        self.assertTrue(all(r['min_z']<=2<=r['max_z'] for r in data['polygons']))

    def test_garage_apron_without_pedestrian_access_is_protected(self):
        s=SimpleNamespace(access=None,garage_access=SimpleNamespace(status='connected',surfaces=(solid('apron'),)))
        self.assertEqual(hardscape.collect([(s,0,0)])['polygons'][0]['kind'],'driveway')

    def test_mapped_paving_retains_plantable_garden_hole_after_clipping(self):
        shape=Polygon([(0,0),(20,0),(20,20),(0,20)],
                      [[(5,5),(15,5),(15,15),(5,15)]])
        data=hardscape.collect(mapped_polygons=[('parking',shape)],bounds=(2,2,18,18),
                               ground=lambda xy:np.ones(len(xy))*4)
        record=data['polygons'][0]
        actual=Polygon(record['rings'][0],record['rings'][1:])
        self.assertEqual(actual.bounds,(2,2,18,18))
        self.assertFalse(actual.covers(Point(10,10)))
        self.assertTrue(actual.covers(Point(3,3)))
        self.assertLessEqual(record['min_z'],4)
        self.assertGreaterEqual(record['max_z'],4)

    def test_mapped_services_export_only_client_supported_hard_surface_kinds(self):
        import geodesy
        from sitegen import mapped_surfaces
        from test_sitegen_mapped_surfaces import features
        frame=geodesy.EnuFrame(-43.5,172.6)
        tables=[features(frame,cls,subtype='pedestrian' if cls=='plaza' else '')
                for cls in ('parking','plaza','substation')]
        ring=tables[0].parts(0)[0][0]
        service=SimpleNamespace(lots=lambda *args:tables,
                                extra_pads=lambda *args:[(ring[:,1],ring[:,0])])
        shapes=mapped_surfaces.collect(frame,(-10,-10,30,30),service)
        data=hardscape.collect(mapped_polygons=shapes,ground=lambda xy:np.zeros(len(xy)))
        self.assertEqual(len(data['polygons']),4)
        for p in data['polygons']:
            self.assertIn(p['kind'],('pavement','driveway','parking','footpath','road','fuel','hardscape'))

    def test_driveway_and_full_sidewalk_width_heights(self):
        drive=dict(n=[[0,0,0],[10,0,0]],w=4.)
        walk=dict(pts=np.array([[0,5,2],[10,5,3]]),side=1,w=3.)
        data=hardscape.collect(drives=[drive],walks=[walk],ground=lambda xy:xy[:,0]*.1+2)
        shapes=[Polygon(r['rings'][0]) for r in data['polygons']]
        self.assertTrue(any(p.covers(Point(5,1.9)) for p in shapes))
        self.assertTrue(any(p.covers(Point(5,6.4)) for p in shapes))
        self.assertTrue(all(r['min_z']<=2 and r['max_z']>=3 for r in data['polygons']))

    def test_sidewalk_mask_includes_drawn_sloping_back_skin(self):
        import sidewalks
        walk=dict(pts=np.array([[0,5,2],[10,5,3]]),side=1,w=2.5)
        curb,out=sidewalks.run_geometry(walk['pts'],walk['side'],walk['w'])
        profile=sidewalks.profile(w=walk['w'])
        back=(curb[0,:2]+curb[1,:2])/2+out[0]*(profile[:,0].max()-.01)
        data=hardscape.collect(walks=[walk])
        self.assertTrue(any(Polygon(p['rings'][0]).covers(Point(back)) for p in data['polygons']))

    def test_unknown_ground_keeps_conservative_mask_not_free_paving(self):
        data=hardscape.collect(drives=[dict(n=[[0,0,0],[10,0,0]],w=3)],
                               ground=lambda xy:np.full(len(xy),np.nan))
        self.assertEqual(data['polygons'][0]['min_z'],-1000000.)

    def test_drawn_road_ribbons_are_protected_in_one_ground_batch(self):
        calls=[]
        def ground(xy):calls.append(xy.copy());return np.ones(len(xy))*5.
        chunks=[dict(n=[[0,0,0],[10,0,0],[20,4,0]],w=8.,m='road_asphalt_2lane',tl=11,p=19)]
        data=hardscape.collect(chunks=chunks,ground=ground)
        self.assertEqual(len(calls),1)
        self.assertTrue(any(Polygon(p['rings'][0]).covers(Point(4,3.8)) for p in data['polygons']))
        self.assertTrue(all(p['min_z']<=5<=p['max_z'] for p in data['polygons']))

    def test_mask_is_clipped_and_budget_never_silently_truncates(self):
        s=SimpleNamespace(access=AccessPlan(2.,None,(solid('path'),solid('path',4)),()),garage_access=None)
        with patch.object(hardscape,'MAX_POLYGONS',1):
            data=hardscape.collect([(s,0,0)],bounds=(0,0,8,8))
        self.assertEqual(len(data['polygons']),1)
        self.assertTrue(Polygon(data['polygons'][0]['rings'][0]).covers(Point(5,1)))
        self.assertEqual(Polygon(data['polygons'][0]['rings'][0]).bounds,(0,0,8,8))

    def test_anchor_and_geotile_manifests_retain_exclusions(self):
        import roads, blockworker, geotiles
        data=hardscape.collect(drives=[dict(n=[[0,0,0],[10,0,0]],w=3)])
        with tempfile.TemporaryDirectory() as folder:
            roads.write_tile(folder,'/vfs',1,0,0,[],vegetation_exclusions=data)
            self.assertEqual(json.loads((Path(folder)/'roads_1_0_0.json').read_text())['vegetationExclusions'],data)
            tile=geotiles.geobox(65536,65536)
            p=SimpleNamespace(chunks=[],walks_raw=[],ctx=[],dmesh=None,bld=None,props=None,wires=None,
                park=None,tmesh=None,fuel=None,rmesh=None,guardrail_rows=None,garage_sound=(),wells=(),
                vegetation_exclusions=data)
            blockworker._write_geo_content(folder,'/vfs',tile,p)
            exported=json.loads((Path(folder)/blockworker.geo_names(tile.key)['json']).read_text())
            self.assertEqual(exported['vegetationExclusions'],data)
            self.assertEqual(exported['frame'],list(geotiles.centre(65536,65536)))

    def test_native_green_decoration_stays_inside_accepted_patch(self):
        from buildgen import landscaping
        from test_buildgen_visible_landscaping import example
        for cover in ('site_lawn_margin','site_garden_bed'):
            spec=example(kind=cover)
            rows=landscaping.native_props(spec)
            self.assertTrue(rows)
            boundary=Polygon([p[:2] for p in spec.access.landscape[0].top])
            for row in rows:
                self.assertGreaterEqual(boundary.boundary.distance(Point(row[1:3])),
                                        landscaping.native_radius(row[0],row[6]))
            self.assertEqual(hardscape.collect([(spec,0,0)])['polygons'],[])

    def test_both_green_cover_types_receive_native_bushes_and_rocks(self):
        from buildgen import landscaping
        from test_buildgen_visible_landscaping import example
        for cover in ('site_lawn_margin','site_garden_bed'):
            groups=set()
            for seed in range(16):groups.update(r[0] for r in landscaping.native_props(example(kind=cover,seed=seed)))
            self.assertEqual(groups,{'site_shrub','site_rock'})


if __name__=='__main__':unittest.main()
