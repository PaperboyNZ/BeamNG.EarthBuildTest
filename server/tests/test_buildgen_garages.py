"""Playable garage interfaces: physical surfaces, body clearance and LOD parity."""
from dataclasses import FrozenInstanceError
import copy
import pickle
from pathlib import Path
import sys
import unittest

import numpy as np
from shapely.geometry import MultiPoint, Polygon

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
import sidewalks
import vehicle_crossings
from buildgen import freeze_items
from buildgen.garages import ramp_profile, vehicle_sweep, circulation, ROAD_LIP
from buildgen.topology import Footprint


def fixture(holes=(),offset=(0.,0.),ground=None,walk=False,obstacle=False):
    fp=Footprint(((0,0),(60,0),(60,40),(0,40)),holes)
    spec=b.plan(np.asarray(fp.outer),{'class':'parking','height':9.,'num_floors':3,'seed_id':'garage','_footprint':fp})
    items=[(spec,0.,0.)]
    if obstacle:
        other=Footprint(((49,-7),(59,-7),(59,-1),(49,-1)))
        s=b.plan(np.asarray(other.outer),{'class':'utility','height':3.,'_footprint':other})
        items.append((s,0.,0.))
    roads=[(np.array([[-50.,-12.],[120.,-12.]])+offset,4.,'residential',False)]
    walks=[]
    if walk:
        walks=[dict(pts=np.c_[np.array([[-50.,-6.75],[120.,-6.75]])+offset,np.zeros(2)],side=1,w=2.5,caps=(True,True))]
    raw=copy.deepcopy(walks)
    drives=b.garage_drives(items,roads,*offset,ground=ground or (lambda p:np.zeros(len(p))),walks=walks,raw_walks=raw)
    return spec,items,drives,walks,raw


def clipped_height(triangle,lo,hi):
    points=list(triangle)
    for z,sign in ((lo,1),(hi,-1)):
        output=[]
        for a,c in zip(points,points[1:]+points[:1]):
            ain,cin=(a[2]-z)*sign>=0,(c[2]-z)*sign>=0
            if ain:output.append(a)
            if ain!=cin:output.append(a+(c-a)*((z-a[2])/(c[2]-a[2])))
        points=output
        if not points:break
    return points


class GarageTests(unittest.TestCase):
    def test_lane_width_not_overwritten_by_bridge_clearance(self):
        self.assertGreaterEqual(b.DECK_LANE_M,3.6)
        self.assertEqual(b.DECK_ROAD_INSET_M,1.)

    def test_road_to_portal_is_a_collision_surface_with_exact_shared_heights(self):
        spec,items,drives,_,_=fixture()
        a=spec.garage_access
        self.assertEqual(a.status,'connected',a.diagnostics)
        self.assertEqual(len(drives),1)
        self.assertTrue(drives[0]['bne_access_only'])
        self.assertAlmostEqual(drives[0]['n'][-1][1],-8.)
        points=np.array([p for s in a.surfaces for p in s.top])
        self.assertTrue(np.allclose(points[points[:,1]==-8.,2],ROAD_LIP))
        self.assertTrue(np.allclose(points[points[:,1]==0.,2],.03))
        near=b.build(freeze_items(items));lite=b.build(freeze_items(items),lite=True);col=b.collision_mesh(freeze_items(items))
        np.testing.assert_array_equal(near[0],lite[0])
        np.testing.assert_array_equal(near[0],col[0])
        np.testing.assert_array_equal(near[2],col[2])
        for p in points:
            self.assertLess(np.linalg.norm(col[0]-p,axis=1).min(),1e-9)
        for solid in a.surfaces:
            p=np.asarray(solid.top)
            self.assertGreater(np.cross(p[1]-p[0],p[2]-p[0])[2],0.)
        self.assertLessEqual(a.terrain_points,4*116)

    def test_dropped_kerb_matches_apron_and_keeps_pedestrian_ramps(self):
        spec,items,drives,walks,raw=fixture(walk=True)
        self.assertEqual(spec.garage_access.status,'connected',spec.garage_access.diagnostics)
        self.assertEqual(walks[0]['driveways'],raw[0]['driveways'])
        self.assertAlmostEqual(walks[0]['driveways'][0][2],ROAD_LIP)
        p=np.array([p for s in spec.garage_access.surfaces for p in s.top])
        boundary=p[np.isclose(p[:,1],-5.5)]
        self.assertTrue(len(boundary)>0)
        self.assertTrue(np.allclose(boundary[:,2],sidewalks.CURB_H+2.5*sidewalks.CROSS_SLOPE))
        prof=vehicle_crossings.section(2.5,sidewalks.CURB_H,1.,ROAD_LIP)
        self.assertAlmostEqual(np.interp(sidewalks.CURB_W,prof[:,0],prof[:,1]),ROAD_LIP)
        builder=sidewalks.Builder((0,0,0),collision=True)
        curb,out=sidewalks.run_geometry(walks[0]['pts'],1,2.5)
        builder.add_run(curb,out,2.5,driveways=walks[0]['driveways'])
        physical=builder.col.arrays()[0]
        for point in boundary:
            # The constant full-width crossing plane contains each apron endpoint;
            # its vertices extend 0.1 m beyond the apron as lateral clearance.
            self.assertTrue(np.any(np.isclose(physical[:,1],point[1])&np.isclose(physical[:,2],point[2])))
        old=walks[0]['driveways'][0]
        walks[0].pop('driveways');walks[0]['ramps']=[(old[0]-1,old[1]+1)]
        b.garage_drives(items,[(np.array([[-50.,-12.],[120.,-12.]]),4.)],0,0,
                        ground=lambda p:np.zeros(len(p)),walks=walks)
        self.assertEqual(spec.garage_access.status,'rejected')
        self.assertNotIn('driveways',walks[0])

    def test_ramp_grade_transitions_and_u_turn_envelopes_fit(self):
        spec,*_=fixture()
        plan=b.deck_plan(spec,0,0)
        _,_,rise,(_,a,u,n,s0,s1)=plan
        stations,z,grade=ramp_profile(s1-s0,rise)
        self.assertEqual(z[0],0.)
        self.assertEqual(z[-1],rise)
        self.assertLessEqual(grade,b.DECK_SLOPE)
        slopes=np.diff(z)/np.diff(stations)
        self.assertLess(abs(slopes[0]),.01)
        self.assertLess(abs(slopes[-1]),.01)
        well,turns=circulation(plan)
        shape=spec.footprint.shape()
        for turn in turns:self.assertTrue(shape.covers(turn))
        self.assertGreaterEqual((b.DECK_LANE_M+b.DECK_RAMP_GAP_M)/2,5.)

    def test_emitted_structure_does_not_block_ground_route(self):
        spec,items,*_=fixture()
        mesh=b.collision_mesh(freeze_items(items));triangles=mesh[0][mesh[2]]
        # Ground route ends 3 m into the eased ramp. Check the flat section and
        # every actual vertical/sloping obstacle, including columns, skin/tower.
        _,_,_,(_,a,u,n,s0,s1)=b.deck_plan(spec,0,0)
        normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
        wall=abs(normals[:,2])<.5*np.maximum(np.linalg.norm(normals,axis=1),1e-12)
        relevant=triangles[wall&(triangles[:,:,2].max(1)>.23)&(triangles[:,:,2].min(1)<2.23)]
        polygons=[]
        for tri in relevant:
            clipped=clipped_height(tri,.23,2.23)
            if clipped:polygons.append(MultiPoint(np.asarray(clipped)[:,:2]).convex_hull)
        route=np.array(spec.garage_access.route)
        sweep=vehicle_sweep(route)
        for poly in polygons:
            self.assertTrue(sweep.intersection(poly).is_empty,poly.wkt)

    def test_holes_are_preserved_and_bad_layouts_never_get_a_drive(self):
        hole=((25,28),(35,28),(35,36),(25,36))
        spec,items,*_=fixture(holes=(hole,))
        mesh=b.collision_mesh(freeze_items(items))
        p=mesh[0][mesh[2]]
        for tri in p[np.ptp(p[:,:,2],axis=1)<1e-8]:
            self.assertLess(Polygon(tri[:,:2]).intersection(Polygon(hole)).area,1e-7)
        spec,items,drives,*_=fixture(holes=(((1,1),(15,1),(15,20),(1,20)),))
        if b.deck_plan(spec,0,0) is None:
            self.assertEqual(drives,[])

    def test_upper_level_u_turns_are_clear_in_the_actual_collider(self):
        spec,items,*_=fixture()
        plan=b.deck_plan(spec,0,0)
        _,floors,storey,_=plan
        _,turns=circulation(plan)
        mesh=b.collision_mesh(freeze_items(items));triangles=mesh[0][mesh[2]]
        normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
        wall=abs(normals[:,2])<.5*np.maximum(np.linalg.norm(normals,axis=1),1e-12)
        for level in range(1,floors):
            low=.03+level*storey+.2;high=low+2.
            for tri in triangles[wall&(triangles[:,:,2].max(1)>low)&(triangles[:,:,2].min(1)<high)]:
                clipped=clipped_height(tri,low,high)
                if clipped:
                    poly=MultiPoint(np.asarray(clipped)[:,:2]).convex_hull
                    self.assertTrue(turns[level%2].intersection(poly).is_empty,(level,poly.wkt))

    def test_missing_terrain_obstacles_and_rough_ground_do_not_emit_false_access(self):
        for kw in (dict(ground=lambda p:np.full(len(p),np.nan)),dict(obstacle=True),
                   dict(ground=lambda p:np.sin(p[:,1])*2)):
            spec,_,drives,walks,_=fixture(**kw)
            self.assertEqual(spec.garage_access.status,'rejected',kw)
            self.assertEqual(drives,[])
            self.assertEqual(spec.garage_access.surfaces,())
            self.assertFalse(any(w.get('driveways') for w in walks))

    def test_worker_round_trip_and_rebase_preserve_access(self):
        spec,items,*_=fixture()
        shifted,*_=fixture(offset=(1000.,-2000.))
        self.assertEqual(spec.garage_access,shifted.garage_access)
        frozen=freeze_items(items)[0][0]
        restored=pickle.loads(pickle.dumps(frozen))
        self.assertEqual(restored.garage_access,spec.garage_access)
        with self.assertRaises(FrozenInstanceError):restored.garage_access.status='broken'
        a=b.collision_mesh([(frozen,0,0)]);c=b.collision_mesh([(restored,0,0)])
        np.testing.assert_array_equal(a[0],c[0])

    def test_replanning_replaces_owned_cuts_and_preserves_other_crossings(self):
        spec,items,drives,walks,raw=fixture(walk=True)
        before=spec.garage_access
        foreign=(10.,15.)
        for w in (walks[0],raw[0]):w['driveways'].append(foreign)
        roads=[(np.array([[-50.,-12.],[120.,-12.]]),4.)]
        after=b.garage_drives(items,roads,0,0,ground=lambda p:np.zeros(len(p)),walks=walks,raw_walks=raw)
        self.assertEqual(before,spec.garage_access)
        self.assertEqual(drives,after)
        self.assertEqual(len(walks[0]['driveways']),2)
        b.garage_drives(items,roads,0,0,ground=lambda p:np.full(len(p),np.nan),walks=walks,raw_walks=raw)
        self.assertEqual(walks[0]['driveways'],[foreign])
        self.assertEqual(raw[0]['driveways'],[foreign])
        self.assertEqual(spec.garage_access.surfaces,())

    def test_interior_buildings_and_low_overhangs_block_the_complete_route(self):
        for ring,min_h in ((((24,21),(27,21),(27,24),(24,24)),0.),
                           (((51,-7),(59,-7),(59,-1),(51,-1)),1.)):
            spec,items,*_=fixture()
            fp=Footprint(ring)
            obstacle=b.plan(np.asarray(fp.outer),{'class':'utility','height':3.,'_footprint':fp})
            obstacle.min_h=min_h
            items.append((obstacle,0.,0.))
            drives=b.garage_drives(items,[(np.array([[-50.,-12.],[120.,-12.]]),4.)],0,0,
                                    ground=lambda p:np.zeros(len(p)))
            self.assertEqual(drives,[])
            self.assertEqual(spec.garage_access.status,'rejected')

    def test_nonplanar_road_mouth_cannot_be_hidden_by_fill_allowance(self):
        spec,items,*_=fixture()
        x=spec.garage_access.portal[0]
        ground=lambda p:-.2*np.exp(-((p[:,0]-x)/.8)**2)
        drives=b.garage_drives(items,[(np.array([[-50.,-12.],[120.,-12.]]),4.)],0,0,ground=ground)
        self.assertEqual(drives,[])
        self.assertIn('garage_road_contact_nonplanar',spec.garage_access.diagnostics)


if __name__=='__main__':unittest.main()
