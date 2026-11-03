"""Landscape fit, shared collision, bounded detail and identity conventions."""
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np
from shapely.geometry import Polygon

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import landscaping,site_layout,sitework,access,freeze_items
from buildgen.environments import Environment
from test_buildgen_facades import building,road
from test_buildgen_sites import example


def fixture(seed='garden',material='wood',cls='house',environment='',climate='temperate_or_unknown'):
    s=building(20,14,**{'class':cls,'height':6.,'seed_id':seed,'facade_material':material})
    selection=replace(s.inference.selection,environment=Environment(environment),climate_response=climate)
    s.inference=replace(s.inference,selection=selection)
    calls=[]
    def ground(p):calls.append(len(p));return np.zeros(len(p))
    b.doors([(s,0.,0.)],road(),0,0,ground=ground)
    return s,calls


class LandscapeTests(unittest.TestCase):
    def test_visual_identities_guide_palette_and_industry_stays_sparse(self):
        variants=[dict(material='wood'),dict(material='brick'),dict(environment='city_centre'),
                  dict(environment='rural'),dict(climate='cold_climate'),dict(climate='solar_shading'),
                  dict(cls='supermarket'),dict(cls='warehouse')]
        profiles=[landscaping.treatment(fixture(**kw)[0]) for kw in variants]
        self.assertEqual(len({p.identity for p in profiles}),8)
        self.assertEqual(profiles[-1].plants,0)
        self.assertLess(profiles[-1].margin,min(p.margin for p in profiles[:-1]))

    def test_varied_frontages_stay_connected_bounded_and_clear(self):
        signatures=set();covers=set()
        for seed in range(16):
            s,calls=fixture(seed=seed)
            signatures.add(landscaping.margins(s))
            self.assertEqual(len(calls),1)
            self.assertLessEqual(sum(calls),140)
            self.assertLessEqual(len(s.access.landscape),12)
            for band in s.access.landscape:
                covers.add(band.kind)
                p=Polygon([q[:2] for q in band.top])
                self.assertLess(p.intersection(s.footprint.shape()).area,1e-7)
                for solid in s.access.solids:self.assertFalse(sitework._overlap(band,solid))
            for shoulder in (v for v in s.access.solids if v.kind=='paved_margin'):
                p=Polygon([q[:2] for q in shoulder.top])
                self.assertTrue(any(p.distance(Polygon([q[:2] for q in v.top]))<1e-7
                                    for v in s.access.solids if v.kind=='path'))
        self.assertGreater(len(signatures),12)
        self.assertIn('lawn_margin',covers);self.assertIn('garden_bed',covers)

    def test_decorative_landcover_and_bounded_plants_do_not_add_collision(self):
        s,_=fixture(material='brick')
        # At least one real accepted garden across deterministic variants.
        for seed in range(20):
            s,_=fixture(seed=seed,material='brick')
            if any(p.kind=='garden_bed' for p in s.access.landscape):break
        self.assertTrue(any(p.kind=='garden_bed' for p in s.access.landscape))
        near=b.Mesh();lite=b.Mesh()
        landscaping.draw(near,s,True);landscaping.draw(lite,s,False)
        self.assertEqual(len(near.arrays()[2]),2*len(s.access.landscape))
        for a,c in zip(near.arrays(),lite.arrays()):np.testing.assert_array_equal(a,c)
        for mesh in (near,lite):
            p,uv,t,*_=mesh.arrays()
            self.assertTrue(np.isfinite(p).all() and np.isfinite(uv).all())
            self.assertTrue((np.linalg.norm(np.cross(p[t[:,1]]-p[t[:,0]],p[t[:,2]]-p[t[:,0]]),axis=1)>1e-9).all())
        before=b.collision_mesh(freeze_items([(s,0.,0.)]))
        s.access=replace(s.access,landscape=())
        after=b.collision_mesh(freeze_items([(s,0.,0.)]))
        np.testing.assert_array_equal(before[0],after[0]);np.testing.assert_array_equal(before[2],after[2])

    def test_site_gardens_respect_boundary_and_paving_and_share_terrain_budget(self):
        s,lo,hi=example();s.inference=replace(s.inference,use=replace(s.inference.use,value='commercial'))
        calls=[]
        def ground(p):calls.append(len(p));return np.zeros(len(p))
        site_layout.resolve([(s,lo,hi)],ground,0,0)
        gardens=[v for v in s.access.landscape if v.kind.startswith('site_')]
        self.assertTrue(gardens)
        self.assertLessEqual(len(gardens),4);self.assertEqual(len(calls),1);self.assertLessEqual(calls[0],512)
        for band in gardens:
            self.assertTrue(s.site.boundary.shape().covers(Polygon([p[:2] for p in band.top])))
            self.assertFalse(any(sitework._overlap(band,p) for p in s.access.solids))
        before=s.access
        site_layout.resolve([(s,lo,hi)],ground,0,0)
        self.assertEqual(before,s.access)

    def test_disabled_paths_and_missing_terrain_do_not_create_landscape(self):
        with patch.dict(os.environ,{'BNE_BUILDING_PATHS':'off'}):
            self.assertFalse(fixture()[0].access.landscape)
        s=building()
        b.doors([(s,0.,0.)],road(),0,0,ground=lambda p:np.full(len(p),np.nan))
        self.assertFalse(s.access.landscape)

    def test_landscape_materials_are_registered_and_opaque(self):
        root=Path(__file__).resolve().parents[2]
        data=json.loads((root/'mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/buildings.materials.json').read_text())
        for mat in (b.LAWN,b.GARDEN,b.GRAVEL,b.FOLIAGE):
            self.assertIn(mat,b.MATERIALS);self.assertEqual(data[mat]['mapTo'],mat)
            self.assertFalse(data[mat]['translucent']);self.assertTrue(data[mat]['Stages'][0]['vertColor'])

    def test_driveway_updates_retain_only_unobstructed_landscape(self):
        from test_buildgen_driveways import scene
        any_landscape=False
        for seed in range(6):
            s=building(seed_id=seed,facade_material='wood')
            s,_,_,_,calls=scene(spec=s)
            self.assertEqual(len(calls),2)
            self.assertTrue(any(v.kind=='driveway' for v in s.access.solids))
            any_landscape|=bool(s.access.landscape)
            for band in s.access.landscape:
                self.assertFalse(any(sitework._overlap(band,p) for p in s.access.solids))
        self.assertTrue(any_landscape)


if __name__=='__main__':unittest.main()
