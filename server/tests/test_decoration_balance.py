"""Coverage and safety regressions for the balanced roadside placement."""
import sys, unittest, copy
from pathlib import Path
import numpy as np
from shapely.geometry import Point, box
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import furniture,roadside_clearance as rc,sidewalks,streetplanters,roads
from test_furniture import road
from test_vegetation_surfaces import items,raster
import vegetation


def walk(width=3.5):
    return dict(fid='tree-street',pts=np.array([[0.,4.+width/2,0.],[100.,4.+width/2,0.]]),side=1,w=width)


def tree(x=50.):return ['deciduous',x,4.9,.15,25.,1.,8.,.3]
def flat(xy):return np.zeros(len(xy))


class BalanceTests(unittest.TestCase):
    def test_canopy_may_overhang_paving_but_trunk_may_not(self):
        chm=raster();mask=np.zeros(chm.data.shape,bool);mask[:,80:]=True
        source=items(((78,80),(80,80),(76,80)),groups=(vegetation.G_DECIDUOUS,),height=12.)
        self.assertEqual(len(vegetation._clear_surface_footprints(source,mask,chm)),2)
        self.assertEqual(len(vegetation._clear_surface_footprints(source,mask,chm,ground_only=False)),1)

    def test_wide_walk_gets_paired_planter_and_keeps_walking_strip(self):
        wk=walk();rows=rc.clear([tree()],walks=[wk],ground=flat,lines=[(np.array([[0,0],[100,0]]),4.,'residential')])
        self.assertEqual(len(rows),2)
        planter,plant=rows
        self.assertIn(planter[0],streetplanters.GROUPS);self.assertEqual(plant[0],'planted_tree')
        self.assertEqual(planter[8],plant[8]);self.assertAlmostEqual(plant[3]-planter[3],streetplanters.SOIL)
        self.assertLessEqual(planter[2]+.8,4+wk['w']-1.5)
        self.assertFalse(any(a.intersects(Point(*planter[1:3]).buffer(.8)) for a in rc.keepouts(walks=[wk])))
        # A second clearance pass must keep the same assembly, not duplicate it.
        self.assertEqual(rows,rc.clear(copy.deepcopy(rows),walks=[wk],ground=flat))

    def test_narrow_walk_places_uncontained_tree_beyond_back_skin(self):
        wk=walk(2.5);rows=rc.clear([tree()],walks=[wk],ground=flat)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0][0],'deciduous')
        from sitegen.hardscape import collect
        from shapely.geometry import Polygon
        footprint=Point(*rows[0][1:3]).buffer(.035*8+.25)
        masks=collect(walks=[wk])
        self.assertFalse(any(Polygon(p['rings'][0],p['rings'][1:]).intersects(footprint) for p in masks['polygons']))

    def test_no_ground_or_blocked_rear_never_licenses_bare_tree_on_path(self):
        self.assertEqual(rc.clear([tree()],walks=[walk(2.5)]),[])
        self.assertEqual(rc.clear([tree()],walks=[walk(2.5)],ground=flat,areas=[box(-1,4,101,30)]),[])

    def test_relocation_batches_terrain_for_all_supports(self):
        calls=[]
        def ground(xy):calls.append(len(xy));return np.zeros(len(xy))
        rows=rc.clear([tree(20),tree(40),tree(60),tree(80)],walks=[walk(2.5)],ground=ground)
        self.assertEqual(len(rows),4)
        self.assertEqual(len(calls),1)

    def test_invalid_curved_walk_quad_with_garden_does_not_abort_tile(self):
        from unittest.mock import patch
        from sitegen.hardscape import collect
        wk=walk(4.)
        wk['tree_gardens']=[dict(ring=[[0,0,0],[1,0,0],[1,1,0],[0,1,0]])]
        curb=np.array([[0.,0.,0.],[2.,0.,0.]])
        out=np.array([[1.,1.],[-1.,1.]]) # self-crossing rear skin
        with patch.object(sidewalks,'run_geometry',return_value=(curb,out)):
            masks=collect(walks=[wk])
        self.assertGreater(len(masks['polygons']),0)

    def test_full_width_driveway_rejects_planter(self):
        wk=walk();wk['driveways']=[(0.,100.)]
        rows=rc.clear([tree()],walks=[wk],ground=flat)
        self.assertFalse(any(r[0] in streetplanters.GROUPS for r in rows))

    def test_steep_walk_does_not_get_floating_planter(self):
        wk=walk();wk['pts'][1,2]=20
        self.assertFalse(any(r[0] in streetplanters.GROUPS for r in rc.clear([tree()],walks=[wk],ground=flat)))

    def test_finer_search_finds_small_gap_for_lamp_and_bin(self):
        # Only x=51 has enough clearance; the former 0/2/4/8/12 m probes miss it.
        wk=walk(3.5)
        areas=[box(-100,-100,50.3,100),box(51.7,-100,200,100)]
        for kind in ('streetlight','bin'):
            rows=rc.clear([[kind,50.,4.5,.15,0.,1.,1.,0.]],walks=[wk],areas=areas)
            self.assertEqual(len([r for r in rows if r[0]==kind]),1)
            self.assertAlmostEqual(rows[0][1],51.)

    def test_short_walk_without_lamp_station_does_not_suppress_road_fallback(self):
        r=road('short','residential',True,x0=0,x1=200,y=0)
        side=1 if furniture._h01('short','side')<.5 else -1
        wk=dict(fid='short',pts=np.array([[80.,side*5.25,0.],[82.,side*5.25,0.]]),side=side,w=2.5)
        rows=furniture.place([r],[wk],(-10,-20,210,20),buried=1.)
        self.assertGreater(sum(r[0]=='streetlight' for r in rows),2)

    def test_fenced_garden_cuts_both_pavement_and_collision(self):
        from shapely.geometry import Polygon
        from sitegen.hardscape import collect
        wk=walk(4.);wk['caps']=(True,True)
        rows=rc.clear([tree()],walks=[wk],ground=flat,lines=[(np.array([[0.,0.],[100.,0.]]),4.,'residential')])
        self.assertIn(rows[0][0],streetplanters.GARDENS)
        self.assertLessEqual(rows[0][6],.55);self.assertLessEqual(rows[1][6],6.5)
        raw=copy.deepcopy([wk]);streetplanters.attach([wk],rows,raw)
        self.assertEqual(wk['tree_gardens'],raw[0]['tree_gardens'])
        hole=Polygon(np.asarray(wk['tree_gardens'][0]['ring'])[:,:2])
        self.assertGreater(hole.area,.5)
        self.assertGreaterEqual(hole.bounds[1],4.3) # no intrusion into the driving lane
        self.assertLessEqual(hole.bounds[3],4+wk['w']-1.5)
        curb,out=sidewalks.run_geometry(wk['pts'],1,wk['w'])
        for ramps,drives,verge in (((),(),False),(((10,12),),(),False),((),((70,74),),True)):
            b=sidewalks.Builder((0,0,0),collision=True)
            b.add_run(curb,out,wk['w'],ramps=ramps,driveways=drives,verge=verge,gardens=wk['tree_gardens'])
            for P,T,UV,M in (b.arrays(),b.col.arrays()):
                self.assertTrue(np.isfinite(P).all());self.assertEqual(len(T),len(M))
                area=sum(Polygon(P[t,:2]).intersection(hole).area for t in T if Polygon(P[t,:2]).area>1e-10)
                self.assertLess(area,1e-7,'the opening must remove triangles, not paint over them')
                self.assertGreater(sum(Polygon(P[t,:2]).area for t in T),200)
        masks=collect(walks=[wk])
        self.assertFalse(any(Polygon(p['rings'][0],p['rings'][1:]).contains(hole.representative_point()) for p in masks['polygons']))
        # Removing the assembly also removes its cuts on the next build pass.
        streetplanters.attach([wk],[],raw);self.assertNotIn('tree_gardens',wk)

    def test_garden_cutouts_follow_skin_rebase_without_mutating_source(self):
        import blockworker,geodesy,geotiles
        wk=walk(4.);rows=rc.clear([tree()],walks=[wk],ground=flat);streetplanters.attach([wk],rows)
        original=np.array(wk['tree_gardens'][0]['ring'])
        source=geodesy.EnuFrame(39.29,-76.58);target=geodesy.EnuFrame(39.291,-76.579)
        rebased=blockworker._map_walks(source,target,[wk])
        np.testing.assert_allclose(rebased[0]['tree_gardens'][0]['ring'],geotiles.world_map(source,target,original))
        np.testing.assert_array_equal(wk['tree_gardens'][0]['ring'],original)

    def test_garden_assets_stay_inside_reserved_space(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
        from build_street_gardens import mesh
        for kind in streetplanters.GARDENS:
            P,T,M,C,CT=mesh(kind)
            self.assertLessEqual(np.linalg.norm(P[:,:2],axis=1).max(),streetplanters.GARDEN_RADIUS+1e-9)
            self.assertLessEqual(np.linalg.norm(C[:,:2],axis=1).max(),streetplanters.GARDEN_RADIUS+1e-9)
            self.assertAlmostEqual(P[:,2].max(),.51)
            self.assertLessEqual(len(T),420);self.assertLessEqual(len(CT),104)

    def test_planter_assets_fit_clearance_and_have_small_closed_collision(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
        from build_street_planters import mesh
        for kind in ('square','octagon','trough'):
            P,T,M,C,CT=mesh(kind)
            self.assertTrue(np.isfinite(P).all());self.assertLessEqual(np.linalg.norm(P[:,:2],axis=1).max(),streetplanters.RADIUS)
            self.assertLessEqual(len(T),120);self.assertLessEqual(len(CT),32)
            edges={}
            for tri in CT:
                for a,b in zip(tri,np.roll(tri,-1)):edges[tuple(sorted((a,b)))]=edges.get(tuple(sorted((a,b))),0)+1
            self.assertTrue(all(n==2 for n in edges.values()))

if __name__=='__main__':unittest.main()
