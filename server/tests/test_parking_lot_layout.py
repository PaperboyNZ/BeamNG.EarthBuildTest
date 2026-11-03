"""Exact scalar reference for vectorized/prepared stall geometry predicates."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
import shapely
from shapely.affinity import rotate, translate
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings
import parking


def scalar_layout(rings,blockers=()):
    """Independent pre-vectorization implementation; retain operation order."""
    def polygons(rings):
        return [p for r in rings if len(r)>=3
                for p in [Polygon(np.asarray(r)[:,:2]).buffer(0)] if not p.is_empty]
    shape=unary_union(polygons(rings))
    blocked=unary_union(polygons(blockers))
    parts=[shape] if shape.geom_type=='Polygon' else list(getattr(shape,'geoms',()))
    for area in sorted(parts,key=lambda p:(*p.bounds,p.area)):
        ring=np.asarray(area.exterior.coords)
        c,u,hl,hw=buildings.oriented_box(ring)
        v=np.array([-u[1],u[0]])
        count=int((2*hl-2*parking.LOT_MARGIN_M)//parking.LOT_SPOT_W_M)
        if count<1:continue
        along=(np.arange(count)-(count-1)/2)*parking.LOT_SPOT_W_M
        rows=parking._lot_rows(hw)
        paired={round(off+parking.LOT_SPOT_D_M,3) for off,nose in rows if nose>0}
        for off,nose in rows:
            centres=c+along[:,None]*u+(off-hw)*v
            hx,hy=u*parking.LOT_SPOT_W_M/2,v*parking.LOT_SPOT_D_M/2
            ok=np.array([area.covers(stall) and not blocked.intersects(stall)
                         for q in centres for stall in [Polygon([q-hx-hy,q+hx-hy,q+hx+hy,q-hx+hy])]])
            yield c,u,v,along,off,hw,nose,ok,round(off,3) not in paired


def ring(p):return np.asarray(p.exterior.coords)


class LotLayoutTests(unittest.TestCase):
    def assert_exact(self,rings,blockers=(),bounds=(-200.,-200.,200.,200.)):
        expected=list(scalar_layout(rings,blockers))
        actual=list(parking._lot_layout(rings,blockers))
        self.assertEqual(len(actual),len(expected))
        for expected_row,actual_row in zip(expected,actual):
            self.assertEqual(len(expected_row),len(actual_row))
            for a,b in zip(expected_row,actual_row):
                if isinstance(a,np.ndarray):
                    self.assertEqual(a.dtype,b.dtype)
                    self.assertEqual(a.shape,b.shape)
                    self.assertEqual(a.tobytes(),b.tobytes())
                else:self.assertEqual(a,b)
        def z_at(x,y):return 2.+.01*x+.02*y
        with patch.object(parking,'_lot_layout',side_effect=scalar_layout):
            spots=parking.lot_spots(rings,bounds,z_at,blockers)
            marks=parking.lot_markings(rings,bounds,z_at,blockers)
        self.assertEqual(parking.lot_spots(rings,bounds,z_at,blockers),spots)
        self.assertEqual(parking.lot_markings(rings,bounds,z_at,blockers),marks)
        return actual

    def test_overlap_holes_disjoint_slanted_and_rotated_lots(self):
        donut=[box(0,0,80,12),box(0,48,80,60),box(0,12,12,48),box(68,12,80,48)]
        slanted=Polygon(((0,0),(60,13),(56,53),(-4,40)))
        cases=[([box(0,0,60,40)],[]),
               ([box(0,0,60,40),box(25,0,80,50),box(0,0,60,40)],[box(25,-1,32,51)]),
               (donut,[box(25,25,30,30)]),
               ([slanted],[box(20,15,30,28)]),
               ([rotate(slanted,37,origin=(0,0))],[rotate(box(20,15,30,28),37,origin=(0,0))]),
               ([translate(slanted,-100,-80),box(120,100,170,130)],[box(-80,-65,-70,-60)])]
        for polygons,blocked in cases:
            with self.subTest(lots=len(polygons),blockers=len(blocked)):
                self.assert_exact(list(map(ring,polygons)),list(map(ring,blocked)))

    def test_empty_narrow_degenerate_and_small_rows(self):
        for rings in ([],[ring(box(0,0,1,1))],[ring(box(0,0,20,2))],
                      [np.array(((0,0),(10,0),(20,0),(0,0)))],
                      [ring(box(0,0,6,8))],[ring(box(0,0,9.4,8))]):
            with self.subTest(rings=repr(rings)):
                self.assert_exact(rings)

    def test_blocker_touch_and_nextafter_on_both_sides_of_stall_boundary(self):
        rings=[ring(box(0,0,60,40))]
        c,u,v,along,off,hw,_,_,_=next(scalar_layout(rings))
        q=c+along[0]*u+(off-hw)*v
        hx,hy=u*parking.LOT_SPOT_W_M/2,v*parking.LOT_SPOT_D_M/2
        corners=np.array([q-hx-hy,q+hx-hy,q+hx+hy,q-hx+hy])
        edge=corners[:,0].max()
        masks=[]
        for x in (np.nextafter(edge,-np.inf),edge,np.nextafter(edge,np.inf)):
            blocker=ring(box(x,corners[:,1].min()+.5,edge+.25,corners[:,1].max()-.5))
            masks.append(self.assert_exact(rings,[blocker])[0][7][0])
        self.assertEqual(masks,[False,False,True])

    def test_road_unpaved_and_hole_blockers_across_tile_boundaries(self):
        rings=[ring(box(-20,-20,80,80)),ring(box(60,0,150,60))]
        blockers=list(map(ring,[box(-25,19,155,25),box(40,25,60,60),box(3,-5,12,12)]))
        for bounds in ((-25.,-25.,50.,50.),(50.,-25.,125.,50.),(-100.,-100.,200.,200.)):
            self.assert_exact(rings,blockers,bounds)

    def test_dense_outputs_keep_original_spot_cap_and_every_marking(self):
        self.assert_exact([ring(box(0,0,150,150))],bounds=(-1.,-1.,151.,151.))
        rows=parking.lot_spots([ring(box(0,0,150,150))],(-1.,-1.,151.,151.),lambda x,y:x*0)
        self.assertEqual(len(rows),parking.LOT_MAX_PER_TILE)

    def test_large_rows_and_1024_boundary_keep_all_candidates_with_bounded_batches(self):
        original=shapely.polygons
        for count in (1023,1024,1025,2050):
            with self.subTest(stalls=count):
                rings=[ring(box(0,0,2*parking.LOT_MARGIN_M+count*parking.LOT_SPOT_W_M+.01,8))]
                blockers=[ring(box(100,1,110,7))]
                batches=[]
                def polygons(coords,*args,**kwargs):
                    if isinstance(coords,np.ndarray) and coords.ndim==3:
                        batches.append(len(coords))
                        self.assertLessEqual(len(coords),1024)
                    return original(coords,*args,**kwargs)
                with patch('shapely.polygons',side_effect=polygons):
                    rows=self.assert_exact(rings,blockers,bounds=(-1.,-1.,6000.,9.))
                self.assertEqual(len(rows),1)
                self.assertEqual(len(rows[0][3]),count)
                self.assertTrue(batches)
                if count<=1024:self.assertTrue(all(n==count for n in batches))
                else:
                    self.assertIn(1024,batches)
                    self.assertIn(count%1024,batches)


if __name__=='__main__':unittest.main()
