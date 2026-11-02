"""Engineering-inspired appearance constraints; no code-compliance claims."""
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
import pickle
import numpy as np
from shapely.geometry import Polygon,LineString

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import access,details,facades,sitework,freeze_items
from buildgen.topology import Footprint
from test_buildgen_facades import building,road


def resolved(ground=None,offset=(0.,0.),**attrs):
    spec=building(**attrs)
    sampler=Mock(side_effect=ground or (lambda xy:np.zeros(len(xy))))
    lines=[(p+offset,*rest) for p,*rest in road()]
    b.doors([(spec,0.,0.)],lines,*offset,[],ground=sampler)
    return spec,sampler


class SiteworkTest(unittest.TestCase):
    def test_flat_frontage_has_connected_graded_path_with_single_sample_batch(self):
        spec,sampler=resolved()
        self.assertEqual(sampler.call_count,1)
        path=[s for s in spec.access.solids if s.kind=='path']
        self.assertGreaterEqual(len(path),2)
        self.assertLess(len(path),5) # flat terrain sampling is simplified for mesh export
        landing=next(s for s in spec.access.solids if s.kind=='threshold')
        self.assertAlmostEqual(path[0].top[0][2],landing.top[1][2])
        self.assertLess(landing.top[1][2],landing.top[0][2])
        for i,s in enumerate(path):
            p=np.asarray(s.top)
            for a,c in ((0,1),(3,2)):
                grade=abs(p[c,2]-p[a,2])/np.linalg.norm(p[c,:2]-p[a,:2])
                self.assertLessEqual(grade,sitework.MAX_GRADE+1e-7)
            cross=abs(p[3,2]-p[0,2])/np.linalg.norm(p[3,:2]-p[0,:2])
            self.assertLessEqual(cross,.02)
            if i:
                np.testing.assert_allclose(path[i-1].top[1],s.top[0])
                np.testing.assert_allclose(path[i-1].top[2],s.top[3])
            self.assertLess(Polygon(p[:,:2]).intersection(spec.footprint.shape()).area,1e-7)
            corridor=LineString(road()[0][0]).buffer(road()[0][1]+.25)
            self.assertLess(Polygon(p[:,:2]).intersection(corridor).area,1e-7)
        self.assertTrue(spec.access.landscape)

    def test_steep_or_missing_terrain_does_not_invent_earthworks(self):
        for terrain in (lambda xy:-.25*xy[:,1],lambda xy:np.full(len(xy),np.nan)):
            spec,_=resolved(terrain)
            self.assertFalse(any(s.kind=='path' for s in spec.access.solids))
            self.assertTrue(any('path_omitted' in d for d in spec.access.diagnostics))

    def test_path_does_not_cross_neighbor_or_driveway_apron(self):
        spec,_=resolved()
        for path in (s for s in spec.access.solids if s.kind=='path'):
            for apron in (s for s in spec.access.solids if s.kind=='apron'):
                self.assertFalse(sitework._overlap(path,apron))
        along=spec.door[1]
        obstacle=building(fp=Footprint(((along-.9,-5),(along+.9,-5),(along+.9,-3),(along-.9,-3))))
        spec.access=None
        b.doors([(spec,0.,0.),(obstacle,0.,0.)],road(),0.,0.,ground=lambda xy:np.zeros(len(xy)))
        self.assertFalse(any(s.kind=='path' for s in spec.access.solids))
        self.assertIn('front_path_omitted_obstruction',spec.access.diagnostics)

    def test_anchor_offset_does_not_change_local_path_geometry(self):
        a,_=resolved()
        c,sampler=resolved(offset=(100.,200.))
        self.assertEqual(a.access,c.access)
        self.assertGreater(sampler.call_args.args[0][:,0].min(),100.)

    def test_access_shell_stays_identical_in_collision_and_lite(self):
        spec,_=resolved()
        plan=freeze_items([(spec,0.,0.)])[0][0]
        self.assertEqual(pickle.loads(pickle.dumps(plan)).access,plan.access)
        # Decorative groundcover now persists at lite LOD, but does not create
        # a new physics surface. Compare the shared physical shell separately.
        meshes=[]
        for collision in (False,True):
            m=b.Mesh(); access.draw(m,plan,collision); meshes.append(m.arrays())
        np.testing.assert_array_equal(meshes[0][0][:len(meshes[1][0])],meshes[1][0])
        np.testing.assert_array_equal(meshes[0][2][:len(meshes[1][2])],meshes[1][2])
        self.assertEqual(len(meshes[0][2])-len(meshes[1][2]),2*len(plan.access.landscape))
        m=b.Mesh(); access.draw(m,plan,detail=True)
        self.assertGreater(len(m.arrays()[0]),len(meshes[0][0]))

    def test_flat_apron_falls_away_and_adverse_fall_is_reported(self):
        spec,_=resolved()
        apron=next(s for s in spec.access.solids if s.kind=='apron')
        self.assertLess(apron.top[1][2],apron.top[0][2])
        spec,_=resolved(lambda xy:-.1*xy[:,1])
        self.assertIn('garage_apron_adverse_fall_drainage_unresolved',spec.access.diagnostics)


class DetailTest(unittest.TestCase):
    def finite_mesh(self,m):
        p,uv,t,*_=m.arrays()
        self.assertTrue(np.isfinite(p).all() and np.isfinite(uv).all())
        self.assertTrue(np.all(np.linalg.norm(np.cross(p[t[:,1]]-p[t[:,0]],p[t[:,2]]-p[t[:,0]]),axis=1)>1e-9))
        return p

    def test_gutters_pipes_and_corner_boards_are_finite_and_below_mapped_top(self):
        for roof in ('gabled','hipped'):
            spec,_=resolved(roof_shape=roof,facade_material='wood',height=7.)
            m=b.Mesh(); details.rainwater(m,spec,spec.height,b._Looks(spec.seed),0.,0.)
            p=self.finite_mesh(m)
            self.assertGreater(len(p),100)
            self.assertLess(p[:,2].max(),spec.inference.height.value)
            m=b.Mesh(); details.corners(m,spec,0.,facades.plan(spec,0.,0.),b._Looks(spec.seed))
            self.assertGreater(len(self.finite_mesh(m)),20)

    def test_straight_eaves_do_not_spawn_gutters_at_triangulation_cuts(self):
        from buildgen import roofs
        spec=building(roof_shape='hipped')
        fp=roofs.expanded_rectangle(spec.footprint,b.EAVE_M)
        roof=roofs.envelope(fp,spec.roof)
        self.assertGreater(len(roof.boundary),4)
        self.assertEqual(len(details.eave_runs(roof)),4)

    def test_close_detail_remains_bounded_and_paving_faces_are_valid(self):
        spec,_=resolved()
        m=b.Mesh(); access.draw(m,spec,detail=True)
        self.finite_mesh(m)
        self.assertLess(len(b.build([(spec,0.,0.)])[0]),5000)
        self.assertLess(len(b.build([(spec,0.,0.)],lite=True)[0]),600)

    def test_caps_and_valleys_follow_roof_planes_without_covering_courtyard(self):
        fp=Footprint(((0,0),(30,0),(30,24),(0,24)),(((8,8),(22,8),(22,16),(8,16)),))
        spec=building(fp=fp,roof_shape='hipped',height=7.)
        seams=details.roof_seams(spec,spec.height)
        self.assertTrue(any(kind=='ridge_cap' for kind,_ in seams))
        for _,panels in seams:
            for p in panels:
                self.assertLessEqual(max(q[2] for q in p),7.+1e-7)
                self.assertLess(Polygon([q[:2] for q in p]).difference(fp.shape()).area,1e-7)
        m=b.Mesh(); details.roof_caps(m,spec,spec.height,b._Looks(spec.seed))
        self.finite_mesh(m)


if __name__=='__main__':
    unittest.main()
