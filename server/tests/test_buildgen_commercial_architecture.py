"""Built commercial compositions, fitting, topology and bounded optional detail."""
from dataclasses import replace
import math
from pathlib import Path
import pickle
import sys
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import commercial, facades, freeze_items
from buildgen.topology import Footprint


def fixture(material='brick', *, cls='office', width=30., depth=20., seed='composition',
            floors=3, height=12., roof='flat', fp=None, offset=(0.,0.)):
    fp=fp or Footprint(((0,0),(width,0),(width,depth),(0,depth)))
    if offset != (0.,0.):
        fp=fp.translated(*offset)
    attrs={'class':cls,'_footprint':fp,'height':height,'num_floors':floors,
           'seed_id':seed,'roof_shape':roof}
    if material is not None:
        attrs['facade_material']=material
    spec=b.plan(np.asarray(fp.outer),attrs)
    spec.gring=np.zeros(len(spec.ring))
    road=[(np.array([(-50.,-12.),(width+50.,-12.)])+offset,3.,'residential',False)]
    b.doors([(spec,0.,0.)],road,0.,0.,ground=lambda xy:np.zeros(len(xy)))
    return spec,road


class CommercialArchitectureTests(unittest.TestCase):
    def test_office_compositions_change_geometry_not_only_material(self):
        plans=[]
        layouts=[]
        for material,profile in (('brick','office_punched'),('concrete','office_ribbon'),('glass','office_curtain')):
            spec,_=fixture(material)
            self.assertEqual(commercial.office_profile(spec),profile)
            self.assertIn('ci_composition:'+profile,spec.facades.diagnostics)
            layouts.append(tuple((e.edge,tuple((o.left,o.right,o.bottom,o.top) for o in e.openings))
                                 for e in spec.facades.elevations))
            plans.append(freeze_items([(spec,0.,0.)]))
        self.assertEqual(len(set(layouts)),3)
        geometries=[b.build(plan)[0].tobytes() for plan in plans]
        self.assertEqual(len(set(geometries)),3)
        # These are visual grammars over one unchanged physical shell and entry.
        colliders=[b.collision_mesh(plan) for plan in plans]
        for collider in colliders[1:]:
            np.testing.assert_array_equal(collider[0],colliders[0][0])
            np.testing.assert_array_equal(collider[2],colliders[0][2])
        widths=[]
        for plan in plans:
            ops=[o for e in plan[0][0].facades.elevations for o in e.openings if o.floor==1]
            widths.append(np.median([o.right-o.left for o in ops]))
        self.assertLess(widths[0],2.)
        self.assertGreater(widths[1],5.)
        self.assertGreater(widths[2],3.)

    def test_style_prior_does_not_claim_an_observed_construction_era(self):
        for material in ('brick','concrete','glass',None):
            spec,_=fixture(material)
            self.assertIn('ci_style:weak_material_compatible_prior',spec.facades.diagnostics)
            self.assertIn('ci_era:unknown',spec.facades.diagnostics)
            if material:
                self.assertEqual(spec.inference.facade.status,'observed')
            else:
                self.assertEqual(spec.inference.facade.status,'fallback')
        tall,_=fixture('concrete',floors=commercial.MAX_OFFICE_FLOORS+1,height=52.)
        self.assertEqual(commercial.office_profile(tall),'')
        layout=facades.plan(tall,0.,0.)
        self.assertIn('city_family:office_panel',layout.diagnostics)
        self.assertEqual(len(tall.city.programme.datums),13)
        self.assertTrue(all(o.kind=='door' for e in layout.elevations for o in e.openings))

    def test_strip_frontage_is_fitted_and_does_not_invent_tenant_routes(self):
        strip,_=fixture('brick',cls='retail',width=60.,depth=20.,floors=1,height=6.)
        self.assertEqual(commercial.kind(strip),'ci_strip_shops')
        self.assertIn('ci_tenancy:inferred_closed_frontage_only',strip.facades.diagnostics)
        front=next(e for e in strip.facades.elevations if e.edge==strip.front and not e.boundary)
        shops=[o for o in front.openings if o.kind=='storefront']
        self.assertGreaterEqual(len(shops),5)
        self.assertEqual(sum(o.kind=='door' for e in strip.facades.elevations for o in e.openings),1)
        self.assertFalse(any(e.openings for e in strip.facades.elevations if e.edge!=strip.front))
        self.assertFalse(any(o.kind in ('service','staff_door','public_entry') for o in front.openings))
        self.assertFalse(any(s.kind=='ci_threshold' for s in strip.access.solids))
        # Multiple mapped storeys and small shops retain their established recipe.
        upper,_=fixture('brick',cls='retail',floors=2,height=7.)
        small,_=fixture('brick',cls='retail',width=10.,depth=10.,floors=1,height=4.)
        self.assertNotEqual(commercial.kind(upper),'ci_strip_shops')
        self.assertNotEqual(commercial.kind(small),'ci_strip_shops')

    def test_fitted_openings_and_source_roofs_over_shapes_and_seeds(self):
        shapes=(Footprint(((0,0),(30,0),(30,20),(0,20))),
                Footprint(((0,0),(40,0),(40,15),(25,15),(25,30),(0,30))),
                Footprint(((0,0),(30,0),(30,24),(0,24)),(((10,8),(20,8),(20,16),(10,16)),)))
        for material in ('brick','concrete','glass'):
            for seed,fp in enumerate(shapes):
                roof=('flat','gabled','hipped')[seed]
                with self.subTest(material=material,seed=seed):
                    spec,_=fixture(material,fp=fp,seed=str(seed),roof=roof)
                    self.assertEqual(spec.footprint,fp)
                    self.assertEqual(spec.roof,roof)
                    self.assertAlmostEqual(spec.height+spec.inference.roof_rise,12.)
                    for elevation in spec.facades.elevations:
                        self.assertLessEqual(len(elevation.openings),commercial.MAX_OPENINGS)
                        for i,op in enumerate(elevation.openings):
                            self.assertGreaterEqual(op.left,.45)
                            self.assertLessEqual(op.right,elevation.length-.45)
                            self.assertGreaterEqual(op.bottom,0.)
                            self.assertLessEqual(op.top,spec.height)
                            self.assertTrue(all(not op.overlaps(other,.15) for other in elevation.openings[i+1:]))
                    frozen=freeze_items([(spec,0.,0.)])
                    copied=pickle.loads(pickle.dumps(frozen))
                    self.assertEqual(copied[0][0].facades,spec.facades)
                    for mesh in (b.build(copied),b.build(copied,lite=True),b.collision_mesh(copied)):
                        self.assertTrue(np.isfinite(mesh[0]).all())
                        triangles=mesh[0][mesh[2]]
                        areas=np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]),axis=1)
                        self.assertTrue((areas>1e-9).all())
                    if fp.holes:
                        # The new grammar makes no courtyard access/opening claim.
                        self.assertTrue(all(not e.openings for e in spec.facades.elevations if e.boundary))
                        collision=b.collision_mesh(copied)
                        tri=collision[0][collision[2]]
                        horizontal=tri[np.ptp(tri[:,:,2],axis=1)<1e-6]
                        from shapely.geometry import Point,Polygon
                        inner=Polygon(fp.holes[0]).buffer(-.5)
                        self.assertFalse(any(inner.contains(Point(p[:2])) for p in horizontal.mean(axis=1)))

    def test_shared_wall_suppresses_office_windows_and_bands(self):
        for material in ('brick','concrete','glass'):
            spec,road=fixture(material)
            wall=Footprint(((0,20.001),(30,20.001),(30,21),(0,21)))
            neighbour=b.plan(np.asarray(wall.outer),{'class':'industrial','_footprint':wall,'height':12.,'seed_id':'wall'})
            commercial.resolve([(spec,0.,0.),(neighbour,0.,0.)],road,lambda xy:np.zeros(len(xy)),0.,0.)
            rear=next(e for e in spec.facades.elevations if not e.boundary and e.edge==2)
            self.assertFalse(rear.openings)
            self.assertFalse(commercial.bands(spec,rear))
            self.assertIn('ci_opening_omitted_obstruction',spec.facades.diagnostics)
            front=next(e for e in spec.facades.elevations if not e.boundary and e.edge==spec.front)
            self.assertTrue(front.openings)

    def test_optional_work_is_bounded_over_long_and_many_edged_sources(self):
        ring=tuple((300.*math.cos(a),300.*math.sin(a)) for a in np.linspace(0,2*math.pi,32,endpoint=False))
        fp=Footprint(ring)
        for polygon in (fp,Footprint(((0,0),(1000,0),(1000,500),(0,500)))):
            spec,road=fixture('glass',fp=polygon,floors=12,height=48.)
            layout=spec.facades or facades.plan(spec,0.,0.)
            count=sum(o.kind!='door' for e in layout.elevations for o in e.openings)
            self.assertLessEqual(count,commercial.MAX_ARCHITECTURE_OPENINGS)
            self.assertLessEqual(max(len(e.openings) for e in layout.elevations),commercial.MAX_OPENINGS)
            self.assertTrue(all(o.right-o.left<10. for e in layout.elevations for o in e.openings))
            calls=[]
            def ground(xy):
                calls.append(len(xy))
                return np.zeros(len(xy))
            commercial.resolve([(spec,0.,0.)],road,ground,0.,0.)
            self.assertEqual(len(calls),1)
            self.assertLessEqual(calls[0],commercial.MAX_ARCHITECTURE_OPENINGS*6)

    def test_replay_rebase_and_repeated_resolution_keep_layout(self):
        for cls,material,floors,height in (('office','brick',3,12.),('office','glass',3,12.),('retail','brick',1,6.)):
            original,road=fixture(material,cls=cls,floors=floors,height=height)
            expected,access=original.facades,original.access
            commercial.resolve([(original,0.,0.)],road,lambda xy:np.zeros(len(xy)),0.,0.)
            self.assertEqual(original.facades,expected)
            self.assertEqual(original.access,access)
            shifted,_=fixture(material,cls=cls,floors=floors,height=height,offset=(1234.,-567.))
            self.assertEqual(shifted.facades,original.facades)
            replay,_=fixture(material,cls=cls,floors=floors,height=height)
            self.assertEqual(replay.facades,original.facades)

    def test_major_bands_exist_in_both_visual_tiers_without_changing_collision(self):
        spec,_=fixture('concrete')
        frozen=freeze_items([(spec,0.,0.)])
        with_bands=[b.build(frozen,lite=lite) for lite in (False,True)]
        collider=b.collision_mesh(frozen)
        with patch.object(commercial,'bands',return_value=()):
            without_bands=[b.build(frozen,lite=lite) for lite in (False,True)]
            unbanded_collider=b.collision_mesh(frozen)
        for actual,control in zip(with_bands,without_bands):
            self.assertGreater(len(actual[0]),len(control[0]))
            np.testing.assert_allclose(actual[0].min(axis=0),control[0].min(axis=0))
            np.testing.assert_allclose(actual[0].max(axis=0),control[0].max(axis=0))
        np.testing.assert_array_equal(collider[0],unbanded_collider[0])
        np.testing.assert_array_equal(collider[2],unbanded_collider[2])


if __name__=='__main__':
    unittest.main()
