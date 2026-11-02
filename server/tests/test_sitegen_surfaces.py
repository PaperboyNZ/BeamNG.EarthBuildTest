"""Runtime sample reuse and optional groundcover coordination safety."""
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import pickle
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from shapely.geometry import Polygon

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import freeze_items, landscaping, sitework
from buildgen.access import AccessPlan, Solid
from buildgen.topology import Footprint
from sitegen.surfaces import (SharedTerrainSampler, SurfaceReservation,
                              contains_known_site, terrain_sampler)
from test_buildgen_facades import building
from test_buildgen_driveways import scene


def solid(kind,x,y,w=1.,d=1.,z=.02):
    return Solid(kind,((x,y,z),(x+w,y,z),(x+w,y+d,z),(x,y+d,z)),z-.1)


def owner(name,x=0.):
    s=building(fp=Footprint(((x,0),(x+10,0),(x+10,10),(x,10))),seed_id=name)
    s.access=AccessPlan(.06,None,(),landscape=())
    return s


class SamplerTests(unittest.TestCase):
    def test_exact_duplicates_share_one_observation_without_quantizing(self):
        calls=[]
        def provider(p):
            calls.append(p.copy())
            return p[:,0]+2*p[:,1]
        sample=SharedTerrainSampler(provider)
        points=[[1.,2.],[1.,2.],[1.+1e-10,2.],[0.,0.],[-0.,0.]]
        result=sample(points)
        self.assertEqual(len(calls),1)
        self.assertEqual(len(calls[0]),3)
        self.assertEqual(sample.sampled_points,3)
        self.assertEqual(sample.cached_points,3)
        np.testing.assert_array_equal(result,np.array(points)[:,0]+2*np.array(points)[:,1])
        np.testing.assert_array_equal(sample(points),result)
        self.assertEqual(len(calls),1)
        with self.assertRaises(ValueError):result.setflags(write=True)
        points[0][0]=99
        self.assertEqual(result[0],5.)

    def test_bounded_cache_keeps_batch_dedup_after_it_fills(self):
        calls=[]
        sample=SharedTerrainSampler(lambda p:(calls.append(len(p)) or np.zeros(len(p))),max_cached_points=1)
        sample([[0,0],[1,0],[1,0]])
        sample([[0,0],[1,0],[1,0]])
        self.assertEqual(calls,[2,1])
        self.assertEqual(sample.cached_points,1)
        self.assertIs(terrain_sampler(sample),sample)
        self.assertIsNone(terrain_sampler(None))

    def test_missing_or_failed_observations_are_not_retried_as_free_land(self):
        for provider in (lambda p:np.full(len(p),np.nan),lambda p:np.zeros(0)):
            sample=SharedTerrainSampler(provider)
            self.assertTrue(np.isnan(sample([[0,0],[0,0]])).all())
            self.assertTrue(np.isnan(sample([[0,0]])).all())
            self.assertEqual(sample.calls,1)
        def fail(p):raise OSError('missing source terrain')
        self.assertTrue(np.isnan(SharedTerrainSampler(fail)([[0,0]])).all())

    def test_query_bounds_and_coordinate_validation(self):
        sample=SharedTerrainSampler(lambda p:np.zeros(len(p)))
        for points in ([[float('nan'),0]],[[0,0,0]]):
            with self.assertRaises(ValueError):sample(points)
        self.assertEqual(len(sample(np.zeros((0,2)))),0)
        self.assertEqual(sample.calls,0)

    def test_dense_queries_preserve_every_point_with_bounded_callback_chunks(self):
        calls=[]
        def provider(p):
            calls.append(len(p))
            return p[:,0]*.001+p[:,1]
        sample=SharedTerrainSampler(provider)
        points=np.column_stack((np.arange(65543),np.ones(65543)))
        result=sample(points)
        np.testing.assert_array_equal(result,points[:,0]*.001+points[:,1])
        self.assertEqual(calls,[65536,7])
        self.assertLessEqual(sample.cached_points,8192)

    def test_detached_reservations_retain_source_holes(self):
        ring=[[0,0],[10,0],[10,10],[0,10]]
        hole=[[2,2],[3,2],[3,3],[2,3]]
        reservation=SurfaceReservation('local-owner','building',ring,[hole])
        ring[0][0]=100;hole[0][0]=100
        self.assertAlmostEqual(reservation.shape().area,99.)
        self.assertEqual(reservation,pickle.loads(pickle.dumps(reservation)))
        with self.assertRaises(FrozenInstanceError):reservation.kind='changed'


class CoordinationTests(unittest.TestCase):
    def test_other_owner_parking_and_access_win_over_groundcover(self):
        a,c=owner('a'),owner('c',30)
        original=solid('site_parking',12,-5,6,5)
        c.access=replace(c.access,solids=(original,solid('driveway',20,-5,4,5)))
        a.access=replace(a.access,landscape=(solid('garden_bed',13,-3),solid('lawn_margin',21,-3),solid('gravel_margin',25,-3)))
        before=c.access.solids
        sitework.coordinate([(a,0,0),(c,0,0)])
        self.assertEqual(len(a.access.landscape),1)
        self.assertEqual(a.access.landscape[0].kind,'gravel_margin')
        self.assertEqual(c.access.solids,before)
        self.assertIn('landscape_omitted_shared_reservation',a.access.diagnostics)

    def test_garage_apron_and_buildings_without_access_are_reserved(self):
        a,c=owner('garden'),owner('plain',30)
        c.access=None
        a.access=replace(a.access,landscape=(solid('garden_bed',31,2),solid('lawn_margin',12,-3)))
        c.footprint=None
        c.garage_access=SimpleNamespace(status='connected',surfaces=(solid('garage_apron',11,-4,3,3),))
        sitework.coordinate([(a,0,0),(c,0,0)])
        self.assertEqual(a.access.landscape,())

    def test_membership_extent_holes_exclusions_and_unknown_inventory(self):
        s=owner('site')
        boundary=Footprint(((-5,-10),(20,-10),(20,15),(-5,15)),(((12,-5),(15,-5),(15,-2),(12,-2)),))
        exclusion=Footprint(((16,-5),(18,-5),(18,-2),(16,-2)))
        s.site=SimpleNamespace(boundary=boundary,exclusions=(exclusion,))
        s.access=replace(s.access,landscape=(solid('garden_bed',12.5,-4),solid('lawn_margin',16.2,-4),solid('gravel_margin',10.5,-8)))
        sitework.coordinate([(s,0,0)])
        self.assertEqual(len(s.access.landscape),1)
        self.assertFalse(contains_known_site(s,Polygon(((13,-4),(14,-4),(14,-3),(13,-3)))))
        s.site=SimpleNamespace(boundary=boundary,exclusions=None)
        sitework.coordinate([(s,0,0)])
        self.assertEqual(s.access.landscape,())

    def test_repeated_and_reversed_planning_preserve_outputs_and_physical_solids(self):
        def setup(reverse=False):
            a,c=owner('a'),owner('c',30)
            a.access=replace(a.access,solids=(solid('path',15,-5,1,4),),landscape=(solid('garden_bed',12,-4,2,2),))
            c.access=replace(c.access,landscape=(solid('lawn_margin',13,-4,2,2),))
            items=[(a,0,0),(c,0,0)]
            if reverse:items.reverse()
            physical=tuple((s,s.access.solids) for s,_,_ in items)
            reservations=sitework.coordinate(items)
            result=(a.access,c.access)
            self.assertEqual(sitework.coordinate(items),reservations)
            self.assertEqual(result,(a.access,c.access))
            for s,solids in physical:self.assertEqual(s.access.solids,solids)
            return result
        self.assertEqual(setup(),setup(True))

    def test_competing_groundcover_priority_survives_scene_translation(self):
        def planned(offset):
            a,c=owner('a'),owner('c',30)
            bands=(solid('garden_bed',12,-4,2,2),solid('lawn_margin',13,-4,2,2))
            for spec,band in zip((a,c),bands):
                spec.ring=np.asarray(spec.ring)+offset
                spec.footprint=spec.footprint.translated(*offset)
                top=tuple((x+offset[0],y+offset[1],z) for x,y,z in band.top)
                spec.access=replace(spec.access,landscape=(replace(band,top=top),))
            sitework.coordinate([(a,0,0),(c,0,0)])
            return bool(a.access.landscape),bool(c.access.landscape)
        expected=planned((0.,0.))
        self.assertEqual(sum(expected),1)
        for offset in ((1000.,-2000.),(-10000.,40000.)):
            self.assertEqual(planned(offset),expected)

    def test_missing_and_steep_groundcover_fail_without_removing_routes(self):
        s=owner('steep')
        bad=solid('garden_bed',12,-4)
        bad=replace(bad,top=((12,-4,.02),(13,-4,.7),(13,-3,.7),(12,-3,.02)))
        s.access=replace(s.access,solids=(solid('path',10,-4),),landscape=(bad,replace(bad,top=((12,-4,float('nan')),)*4)))
        route=s.access.solids
        sitework.coordinate([(s,0,0)])
        self.assertEqual(s.access.landscape,())
        self.assertEqual(s.access.solids,route)

    def test_reservation_overflow_suppresses_only_optional_groundcover(self):
        s=owner('bounded')
        s.access=replace(s.access,solids=(solid('path',10,-4),),landscape=(solid('garden_bed',12,-4),))
        physical=s.access.solids
        with patch('sitegen.surfaces.MAX_RESERVATIONS',1):
            reservations=sitework.coordinate([(s,0,0)])
        self.assertEqual(len(reservations),1)
        self.assertEqual(s.access.solids,physical)
        self.assertFalse(s.access.landscape)
        self.assertIn('site_coordination_reservation_budget',s.access.diagnostics)

    def test_unsupported_legacy_obstacle_does_not_abort_physical_generation(self):
        s,c=owner('garden'),owner('legacy',30)
        c.footprint=None
        c.ring=np.array(((30,0),(32,2),(30,2),(32,0)),float)
        s.access=replace(s.access,solids=(solid('path',10,-4),),landscape=(solid('garden_bed',12,-4),))
        physical=s.access.solids
        sitework.coordinate([(s,0,0),(c,0,0)])
        self.assertEqual(s.access.solids,physical)
        self.assertFalse(s.access.landscape)
        self.assertIn('site_coordination_obstacle_unresolved',s.access.diagnostics)

    def test_runtime_sample_reuse_preserves_geometry_rebase_and_worker_boundary(self):
        with patch('sitegen.surfaces.terrain_sampler',side_effect=lambda ground:ground):
            baseline=scene()[0]
        actual=scene()[0]
        self.assertEqual(actual.access,baseline.access)
        shifted=scene(offset=(1000.,-2000.))[0]
        self.assertEqual(actual.access,shifted.access)
        for a,c in zip(b.collision_mesh(freeze_items([(baseline,0,0)])),b.collision_mesh(freeze_items([(actual,0,0)]))):
            if isinstance(a,np.ndarray):np.testing.assert_array_equal(a,c)
        frozen=freeze_items([(actual,0,0)])
        self.assertEqual(frozen[0][0].access,pickle.loads(pickle.dumps(frozen))[0][0].access)

    def test_paved_shoulders_retain_exact_adjacent_path_heights(self):
        from test_buildgen_landscaping import fixture
        checked=0
        for seed in range(16):
            s,_=fixture(seed=seed,material='brick')
            paths=[v for v in s.access.solids if v.kind=='path']
            for shoulder in (v for v in s.access.solids if v.kind=='paved_margin'):
                common=[(a,c) for a in shoulder.top for path in paths for c in path.top
                        if np.linalg.norm(np.asarray(a[:2])-c[:2])<1e-10]
                self.assertGreaterEqual(len(common),2)
                for a,c in common:self.assertAlmostEqual(a[2],c[2],places=12)
                checked+=1
        self.assertGreater(checked,0)


if __name__=='__main__':unittest.main()
