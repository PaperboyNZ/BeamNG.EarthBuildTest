"""Captured sidewalk hole and unnecessary generation preparation regressions."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import parkinggrade
import sidewalks
from buildgen import ingest
from buildgen.topology import Footprint, component_key
from test_roads import FRAME


class CornerCoverageTests(unittest.TestCase):
    def test_captured_auckland_corner_has_visual_and_collision_coverage(self):
        c = json.loads((Path(__file__).parent/'fixtures/sidewalk_auckland_corner.json').read_text())['corner']
        arc, inward = np.asarray(c['arc']), np.asarray(c['inward'])
        outer = sidewalks.corner_outer(c)
        expected = Polygon(np.vstack((arc[:, :2]+inward*sidewalks.CURB_W, outer[:, :2])))
        for origin in ((0, 0, 0), (1234, -9876, 10)):
            b = sidewalks.Builder(origin, collision=True)
            b.add_corner(arc, inward, outer)
            for mesh, visual in ((b.arrays(), True), (b.col.arrays(), False)):
                p, t, _, m = mesh
                faces = (p+origin)[t[m == 1] if visual else t]
                coverage = unary_union([Polygon(q[:, :2]) for q in faces if Polygon(q[:, :2]).area > 1e-10])
                self.assertLess(expected.difference(coverage).area, 1e-8)

    def test_partial_native_triangulation_is_repaired(self):
        # Slab's third vertex is unused by the broken output; rear faces identify
        # its full vertex range, including that missing corner.
        p = np.array([[0,0,1], [3,0,1], [3,3,2], [0,3,1], [3,3,2], [0,3,1], [0,3,0]])
        mesh = p, np.array([[0,1,3], [4,5,6]]), p[:, :2].copy(), np.array([1,0])
        fixed = sidewalks.complete_corner_slab(mesh)
        faces = fixed[0][fixed[1][fixed[3] == 1]]
        self.assertAlmostEqual(unary_union([Polygon(q[:, :2]) for q in faces]).area, 9.)
        np.testing.assert_array_equal(fixed[0], p)


class TerrainClearanceTests(unittest.TestCase):
    def check_surface(self, builder, ground, exact=True):
        p,t,_,m = builder.arrays()
        triangles = (p+builder.origin)[t[np.isin(m,(1,2,3,4,6))]]
        edges = triangles[:,1:,:2]-triangles[:,:1,:2]
        self.assertTrue(np.all(np.abs(edges[:,0,0]*edges[:,1,1]-edges[:,0,1]*edges[:,1,0]) > 1e-12))
        weights = np.array([(i/12,j/12,1-(i+j)/12) for i in range(13) for j in range(13-i)])
        samples = np.einsum('wk,tkd->twd',weights,triangles).reshape(-1,3)
        self.assertGreaterEqual(float(np.min(samples[:,2]-ground(samples[:,0],samples[:,1]))),.009999)
        cp,ct,_,_ = builder.col.arrays()
        # A corrected slab uses exactly its visible geometry for collision.
        if exact:
            for triangle in p[t[np.isin(m,(1,2,3,4,6))]]:
                self.assertTrue(any(np.allclose(triangle,face,atol=1e-9) for face in cp[ct]))

    def test_run_transverse_slope_and_flat_control(self):
        curb=np.array([[0.,0.,0.],[20.,0.,0.]])
        outward=np.array([[0.,1.],[0.,1.]])
        plain=sidewalks.Builder((0,0,0),collision=True)
        flat=sidewalks.Builder((0,0,0),collision=True,ground=lambda x,y:x*0)
        for b in (plain,flat):b.add_run(curb,outward,2.5)
        for a,b in zip(plain.arrays(),flat.arrays()):np.testing.assert_array_equal(a,b)
        ground=lambda x,y:.1*y
        b=sidewalks.Builder((0,0,0),collision=True,ground=ground)
        b.add_run(curb,outward,2.5)
        self.check_surface(b,ground)
        p=b.arrays()[0]
        self.assertTrue(np.any(np.isclose(p[:,1],sidewalks.CURB_W)&np.isclose(p[:,2],sidewalks.CURB_H)))

    def test_descending_corner_clears_drawn_lattice(self):
        import grading, junctions, roadmesh, roads
        class Frame:
            def enu_to_geodetic(self,x,y,z):return y,x,z
            def geodetic_to_enu(self,a,b,h):return b,a,h
        spec=roads.Spec(10.,'paved',True,'secondary',False)
        lines=[np.array([[0.,0.,0.],[100.,0.,0.]]),np.array([[0.,0.,0.],[0.,100.,0.]])]
        for slope in (-.06,-.08,-.1):
            corner=junctions.find([(str(i),spec,line,0.) for i,line in enumerate(lines)],roads.has_sidewalks,None)[0][0]
            plans=[]
            for i,line in enumerate(lines):
                xy=line[:,:2]
                plan=grading.Plan(xy,slope*xy.sum(axis=1),spec.width/2+grading.shoulder(spec),road_half=spec.width/2)
                plan.rid=i;plans.append(plan)
            def drawn(a,b):return grading.grade_points(b,a,slope*(a+b),plans,grading.ROAD_LIFT)
            def ground(x,y):return roadmesh.drawn_ground(Frame(),drawn,np.c_[x,y],1/256)
            walk={'corner':corner}
            roads.drape_walks(None,None,[walk],ground)
            c=walk['corner']
            b=sidewalks.Builder((0,0,0),collision=True,ground=ground)
            b.add_corner(c['arc'],c['inward'],sidewalks.corner_outer(c))
            self.check_surface(b,ground,exact=slope < -.06)


class ParkingPreparationTests(unittest.TestCase):
    def grader(self, shapes):
        pg = parkinggrade.ParkingGrader(None, lambda a,b: np.sin(a*10000)*.1)
        pg.cells['cell'] = [(('lot', str(i), 0, s.wkb), FRAME, s) for i,s in enumerate(shapes)]
        return pg

    def test_remote_lots_never_prepare_or_evict_relevant_patch(self):
        pg = self.grader([box(0,0,20,20)] + [box(500+i*30,500,520+i*30,520) for i in range(537)])
        la,lo,_ = FRAME.enu_to_geodetic(np.array([10.]),np.array([10.]),0.)
        with patch.object(parkinggrade.mapcells, 'cells_for_points', return_value=['cell']), \
             patch.object(pg, '_protected', return_value=None) as protection:
            a = pg.apply(la,lo,np.zeros(1))
            b = pg.apply(la,lo,np.zeros(1))
        self.assertEqual(protection.call_count, 1)
        self.assertEqual(len(pg.cache), 1)
        np.testing.assert_array_equal(a,b)

    def test_filter_preserves_all_corrections_and_split_queries(self):
        shapes = [box(0,0,20,20),box(10,10,30,30),box(500,500,520,520)]
        pg = self.grader(shapes)
        x,y = np.meshgrid(np.arange(-5,36,2.),np.arange(-5,36,2.))
        la,lo,_ = FRAME.enu_to_geodetic(x.ravel(),y.ravel(),0.)
        base = np.zeros(len(la))
        with patch.object(parkinggrade.mapcells, 'cells_for_points', return_value=['cell']), \
             patch.object(parkinggrade.ParkingGrader, '_protected', return_value=None):
            actual = pg.apply(la,lo,base)
            with patch.object(parkinggrade,'affects_samples',return_value=True):
                expected = self.grader(shapes).apply(la,lo,base)
            split = np.r_[pg.apply(la[:100],lo[:100],base[:100]),pg.apply(la[100:],lo[100:],base[100:])]
        np.testing.assert_array_equal(actual,expected)
        np.testing.assert_array_equal(actual,split)


class CanonicalIdentityTests(unittest.TestCase):
    def test_validated_keys_preserve_winding_start_and_holes(self):
        outer = [(0,0),(20,0),(20,20),(0,20)]
        hole = [(3,3),(6,3),(6,6),(3,6)]
        for winding in (outer,outer[::-1],outer[2:]+outer[:2],outer+[outer[0]]):
            fp = Footprint(winding,(hole,))
            self.assertEqual(fp.component_key(),component_key([winding,hole]))

    def test_ingestion_validates_once_and_still_rejects_outside_holes(self):
        from buildgen import topology
        outer = [(0,0),(20,0),(20,20),(0,20)]
        f = SimpleNamespace(parts=lambda i:[[outer]],ids=['valid'])
        with patch.object(topology,'canonical_ring',wraps=topology.canonical_ring) as canonical:
            first = ingest.components(f,0)
            self.assertEqual(canonical.call_count,1)
            self.assertEqual(ingest.components(f,0),first)
            self.assertEqual(canonical.call_count,1)
        invalid = SimpleNamespace(parts=lambda i:[[outer,[(30,30),(40,30),(40,40),(30,40)]]],ids=['bad'])
        self.assertEqual(ingest.components(invalid,0),())


if __name__ == '__main__':
    unittest.main()
