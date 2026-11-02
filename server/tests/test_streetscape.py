"""Regional curb seams, service fallbacks, real clearance and bounded geometry."""
import copy
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from shapely.geometry import Polygon, box

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import sidewalks as sw
import streetscape as sc
import vehicle_crossings as vc
import roadside_clearance as rc
import junctions
from buildgen import automatic_sites
from sitegen.commercial_access import propose_access, commit_access
from test_buildgen_commercial import fixture
from test_buildgen_automatic_sites import road, flat
from test_buildgen_driveways import walk


class StreetscapeTests(unittest.TestCase):
    def test_all_64_themes_have_a_small_stable_palette(self):
        path=Path(sc.__file__).parent/'buildgen/catalog/regional_profiles.json'
        self.assertEqual(set(json.loads(path.read_text())['profiles']),set(sc.THEMES))
        self.assertEqual(len(sc.STYLES),6)
        self.assertGreater(len({v.height for v in sc.STYLES.values()}),3)

    def test_geographic_styles_survive_rebase_metadata(self):
        import geodesy
        for lat,lon,style in ((-36.85,174.76,'precast_channel'),(51.5,-.12,'compact_precast'),
                              (59.91,10.75,'cold_climate'),(1.29,103.85,'deep_channel')):
            wk=walk();wk['fid']='street'
            sc.annotate([wk],geodesy.EnuFrame(lat,lon),road_classes={'street':'residential'})
            self.assertEqual(wk['curb_style'],style)
            self.assertEqual(wk['curb_h'],sc.STYLES[style].height)

    def test_clipping_cannot_reselect_a_road_profile(self):
        import geodesy
        for frame in (geodesy.EnuFrame(-36.85,174.76),geodesy.EnuFrame(51.5,-.12)):
            wk=walk();wk['fid']='same-source'
            sc.annotate([wk],frame,source_locations={'same-source':(-36.85,174.76)})
            self.assertEqual(wk['curb_style'],'precast_channel')

    def test_every_regional_height_matches_service_seam_and_collision(self):
        for name,style in sc.STYLES.items():
            item=fixture('industrial',40,20);item[0].door=None;item[0].access=None
            wk=walk();wk['curb_h']=style.height
            raw=copy.deepcopy([wk])
            records=automatic_sites.resolve([item],road(-12),0,0,ground=flat,walks=[wk],raw_walks=raw)
            self.assertEqual(len(records),1,name)
            self.assertEqual(raw[0]['driveways'],wk['driveways'])
            s0,s1,lip=wk['driveways'][0]
            curb,out=sw.run_geometry(wk['pts'],wk['side'],wk['w'])
            builder=sw.Builder((0,0,0),collision=True)
            builder.add_run(curb,out,wk['w'],style.height,driveways=wk['driveways'])
            P=builder.col.arrays()[0]
            self.assertTrue(np.isfinite(P).all())
            rear=style.height+wk['w']*sw.CROSS_SLOPE
            edges=[p for solid in item[0].access.solids if solid.kind=='site_driveway'
                   for p in solid.top if abs(p[1]+6.5)<1e-7]
            self.assertTrue(edges)
            np.testing.assert_allclose(np.asarray(edges)[:,2],rear)
            self.assertTrue(np.any(np.isclose(P[:,2],lip)))

    def test_small_yard_without_door_gets_one_owned_service_access(self):
        for cls in ('commercial','industrial','warehouse'):
            item=fixture(cls,40,20);spec=item[0];spec.door=None;spec.access=None
            wk=[walk()];raw=copy.deepcopy(wk)
            for _ in range(2):
                records=automatic_sites.resolve([item],road(-12),0,0,ground=flat,walks=wk,raw_walks=raw)
                self.assertEqual(len(records),1)
                self.assertEqual(spec.access.site_layout.connections,('service',))
                self.assertEqual(spec.access.site_layout.parking,0)
                self.assertEqual(len(wk[0]['driveways']),1)
            self.assertIsNone(spec.door)
            import buildings
            from buildgen import freeze_items
            self.assertTrue(freeze_items([item]))
            for mesh in (buildings.build([item]),buildings.build([item],lite=True),buildings.collision_mesh([item])):
                self.assertTrue(np.isfinite(mesh[0]).all())

    def test_unknown_ground_obstacles_and_motorway_never_get_fake_openings(self):
        for mode in ('terrain','blocked','motorway'):
            item=fixture('industrial',40,20);item[0].door=None;item[0].access=None
            wk=[walk()];roads=road(-12)
            if mode=='motorway':roads=[(*roads[0][:2],'motorway',False)]
            records=automatic_sites.resolve([item],roads,0,0,ground=(lambda p:np.full(len(p),np.nan))
                if mode=='terrain' else flat, walks=wk,
                obstacles=(box(-100,-20,100,0),) if mode=='blocked' else ())
            self.assertFalse(records)
            self.assertNotIn('driveways',wk[0])

    def test_verge_is_absent_on_vehicle_and_pedestrian_crossings(self):
        wk=walk();curb,out=sw.run_geometry(wk['pts'],1,2.5)
        b=sw.Builder((0,0,0),collision=True)
        b.add_run(curb,out,2.5,verge=True,driveways=[(30.,36.)],ramps=[(65.,68.)])
        P,T,UV,M=b.arrays()
        self.assertIn(sw.GRASS,M)
        centres=P[T[M==sw.GRASS]].mean(axis=1)
        self.assertTrue(np.all((centres[:,0] < -20.-vc.FLARE) | (centres[:,0] > -14.+vc.FLARE)))
        self.assertTrue(np.all((centres[:,0] < 15.-sw.RAMP_FLARE) | (centres[:,0] > 18.+sw.RAMP_FLARE)))
        self.assertTrue(np.all(centres[:,1] < -8.25+1e-6))
        # Curb texture stays on its trim sheet after grass UV conversion.
        self.assertTrue(np.all((UV[T[M==0],1]>=sw.V_BAND_LOW-1e-6)&(UV[T[M==0],1]<=1.)))
        self.assertLess(len(b.col.arrays()[1]),len(T))

    def test_narrow_vehicle_crossing_is_monotone_bounded_and_matches_rear(self):
        for w in (1.5,1.8,2.,2.4,2.5,4.):
            for style in sc.STYLES.values():
                p=vc.section(w,style.height,1.,.002)
                self.assertTrue((np.diff(p[:,0])>0).all())
                self.assertAlmostEqual(np.interp(w,p[:,0],p[:,1]),style.height+w*sw.CROSS_SLOPE)
                # The driving top has no vertical jump or reversed segment.
                top=p[(p[:,0]>=sw.CURB_W)&(p[:,0]<=w)]
                self.assertLess(np.max(abs(np.diff(top[:,1])/np.diff(top[:,0]))),.25)

    def test_corner_sagitta_is_small_even_at_tight_radius_and_count_is_bounded(self):
        for radius in (.2,.8,3.,6.,12.):
            arc,*_=junctions._piece(np.zeros(2),np.array([1.,0.]),3.,np.array([0.,1.]),3.,radius)
            chord=np.linalg.norm(np.diff(arc,axis=0),axis=1)
            error=radius-np.sqrt(radius**2-(chord/2)**2)
            self.assertLessEqual(error.max(),.008+1e-9)
            self.assertLessEqual(len(arc),97)

    def test_actual_tile_junction_uses_curvature_budget(self):
        import roads
        from test_roads import FRAME,features,flat as road_flat
        x=(120.,120.)
        f=features([[x,(300,120)],[x,(120,300)],[x,(-60,120)],[x,(120,-60)]],['residential']*4)
        walks=[]
        roads.build_tile(FRAME,0,0,[f],road_flat,lambda la,lo:np.ones(np.shape(la),bool),walks=walks)
        corners=[w['corner'] for w in walks if 'corner' in w]
        self.assertEqual(len(corners),4)
        for c in corners:
            self.assertGreaterEqual(len(c['arc']),12)
            self.assertLess(np.linalg.norm(np.diff(c['arc'][:,:2],axis=0),axis=1).max(),.44)

    def test_asymmetric_corner_outer_edge_matches_adjacent_walk_datums(self):
        arc=np.array([[0.,0.,0.],[1.,1.,0.],[2.,1.,0.]])
        corner=dict(arc=arc,inward=np.tile([0.,1.],(3,1)),
                    outer=[(2.,5.,0.),(1.,5.,0.),(0.,1.5,0.)],outer_widths=[4.,2.75,1.5])
        before=copy.deepcopy(corner)
        b=sw.Builder((0,0,0),collision=True)
        b.add_corner(arc,corner['inward'],sw.corner_outer(corner),h=.125)
        for mesh in (b.arrays(),b.col.arrays()):
            for point,width in ((corner['outer'][0],4.),(corner['outer'][-1],1.5)):
                expected=np.array([*point[:2],.125+width*sw.CROSS_SLOPE])
                self.assertLess(np.linalg.norm(mesh[0]-expected,axis=1).min(),1e-7)
        np.testing.assert_equal(corner['outer'],before['outer'])

    def test_corner_blocks_route_and_unrelated_corner_does_not_crash(self):
        from buildgen.garages import _walk_contact
        c=dict(corner=dict(arc=np.array([[-4,-4,0],[4,-4,0]]),outer=np.array([[4,-2,0],[-4,-2,0]])))
        args=(np.array([0.,0.]),np.array([1.,0.]),np.array([0.,1.]),np.array([0.,-9.]),4.)
        self.assertIsNone(_walk_contact(*args,[c],np.zeros(2)))
        c['corner']['arc'][:,0]+=50;c['corner']['outer'][:,0]+=50
        self.assertFalse(_walk_contact(*args,[c],np.zeros(2)))


class FurnitureClearanceTests(unittest.TestCase):
    @staticmethod
    def row(kind,x,y):return [kind,x,y,0.,0.,1.,1.,0.]

    def test_narrow_walk_preserves_lamp_and_offset_lenses_as_one_assembly(self):
        import furniture
        wk=walk();wk['w']=2.;wk['driveways']=[(45.,51.)]
        curb,out=sw.run_geometry(wk['pts'],1,2.)
        base=(curb[0]+curb[-1])/2;base[:2]+=out[0]*.5
        post=['streetlight',*map(float,base),0.,1.,9.,0.]
        rows=[post]+furniture.lamp_lenses([post]);notes={}
        kept=rc.clear(rows,walks=[wk],ground=flat,diagnostics=notes)
        self.assertEqual([r[0] for r in kept],['streetlight','lamplens','lampglow'])
        self.assertEqual(notes['moved'],1)
        self.assertTrue(all(r[8]['root']==kept[0][1:4] for r in kept))
        expected=furniture.lamp_lenses([kept[0]])
        for actual,reference in zip(kept[1:],expected):self.assertEqual(actual[:8],reference)
        for choice in kept[0][8]['choices']:
            from shapely.geometry import Point
            xy=np.array(kept[0][1:3])+choice[:2]
            self.assertFalse(any(a.intersects(Point(*xy).buffer(.45)) for a in rc.keepouts(walks=[wk])))

    def test_unplaceable_post_never_leaves_offset_accessories(self):
        import furniture
        post=['streetlight',0.,0.,0.,0.,1.,9.,0.]
        rows=[post]+furniture.lamp_lenses([post])
        self.assertEqual(rc.clear(rows,areas=[box(-1,-1,1,1)]),[])

    def test_relocation_preserves_mixed_furniture_without_entering_buildings(self):
        from types import SimpleNamespace
        wk=walk();wk['driveways']=[(45.,51.)]
        rows=[self.row('bin',-2,-8.3),self.row('hydrant',2,-8.55),self.row('bench',10,-6.9)]
        building=SimpleNamespace(ring=np.array([[-4,-5],[4,-5],[4,10],[-4,10]]),access=None,garage_access=None)
        kept=rc.clear(rows,walks=[wk],items=[(building,0,0)],ground=flat)
        self.assertEqual(len(kept),3)
        for r in kept:
            from shapely.geometry import Point
            self.assertFalse(Polygon(building.ring).intersects(Point(*r[1:3]).buffer(rc.RADII[r[0]]+.15)))

    def test_full_prop_envelope_clears_driveway_flares_and_pedestrian_strip(self):
        wk=walk();wk['driveways']=[(45.,51.)];wk['ramps']=[(70.,73.)]
        rows=[self.row('bin',-5.-vc.FLARE-.2,-8.6),self.row('hydrant',-2.,-8.6),
              self.row('bench',-15.,-6.9),self.row('bin',21.,-8.5),
              self.row('hydrant',-30.,-8.6),self.row('door',-2.,-8.6)]
        kept=rc.clear(rows,walks=[wk],ground=flat)
        self.assertEqual(len(kept),len(rows))
        self.assertIn(rows[-1],kept)
        for row in kept:
            if row[0]=='door':continue
            self.assertFalse(any(p.intersects(__import__('shapely').geometry.Point(*row[1:3]).buffer(rc.RADII[row[0]]+.15)) for p in rc.keepouts(walks=[wk])))

    def test_late_committed_routes_win_and_local_building_paths_translate(self):
        from buildgen.access import AccessPlan,Solid
        from types import SimpleNamespace
        s=SimpleNamespace(access=AccessPlan(0,None,(Solid('path',((0,0,0),(2,0,0),(2,8,0),(0,8,0)),-.1),)),garage_access=None)
        rows=[self.row('bin',1001,2004),self.row('hydrant',1010,2010)]
        self.assertEqual(rc.clear(rows,items=[(s,0,0)],origin=(1000,2000)),rows[1:])

    def test_mapped_paths_service_roads_and_crosswalks_reserve_full_width(self):
        lines=[(np.array([[0.,0.],[20.,0.]]),1.,'path'),(np.array([[0.,10.],[20.,10.]]),3.,'service')]
        chunks=[dict(m='crossing_white',w=3.,n=[[30.,0.,0.],[30.,10.,0.]])]
        rows=[self.row('bin',5.,1.5),self.row('hydrant',5.,12.9),self.row('bench',31.7,5.),self.row('hydrant',50.,50.)]
        self.assertEqual(rc.clear(rows,lines=lines,chunks=chunks),rows[-1:])

    def test_removed_pole_cannot_leave_attached_lights_or_floating_wires(self):
        rows=[self.row(k,0.,0.) for k in ('pole','polelamp','lamplens','lampglow')]
        rows.append(self.row('pole',20.,20.))
        wires=[np.array([[1.,0.,9.],[20.,20.,9.]]),np.array([[20.,20.,9.],[40.,20.,9.]])]
        drive=dict(w=4.,n=[[-2,0,0],[2,0,0]])
        self.assertEqual(rc.clear(rows,drives=[drive],wires=wires),rows[-1:])
        self.assertEqual(len(wires),1)
        np.testing.assert_allclose(wires[0][0],[20,20,9])

    def test_access_masks_export_for_late_neighbour_arrivals(self):
        from sitegen.hardscape import collect
        wk=walk();wk['driveways']=[(45.,51.)]
        areas=rc.keepouts(walks=[wk])
        payload=collect(clearance=areas,ground=flat,bounds=(-50,-12,50,0))
        self.assertTrue(payload['polygons'])
        self.assertTrue(all(p['kind']=='access' for p in payload['polygons']))
        for record in payload['polygons']:
            self.assertLessEqual(record['min_z'],0.)
            self.assertGreaterEqual(record['max_z'],.18+2.5*sw.CROSS_SLOPE)
        # The verge beside an ordinary curb is not a blanket furniture ban.
        from shapely.geometry import Point
        self.assertFalse(any(Polygon(p['rings'][0]).covers(Point(-30,-8.6)) for p in payload['polygons']))


if __name__=='__main__':unittest.main()
