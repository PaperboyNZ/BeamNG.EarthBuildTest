"""Driveway/kerb continuity, bounded work and optional pedestrian branches."""
from pathlib import Path
import copy
import os
import sys
import unittest
from unittest.mock import patch
import numpy as np
from shapely.geometry import Polygon
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
import sidewalks
import vehicle_crossings
from buildgen import BuildingPlan
from buildgen import driveways
from buildgen.diagnostics import DrivewayAudit
from buildgen.site_data import Site
from buildgen.access import AccessPlan,patch as access_patch
from buildgen.topology import Footprint
from test_buildgen_facades import building,road


def walk(dense=False,width=2.5,offset=(0.,0.)):
    xs=np.arange(-50.,51.) if dense else np.array([-50.,50.])
    xy=np.column_stack((xs,np.full(len(xs),-9.+width/2)))+offset
    return dict(pts=np.c_[xy,np.zeros(len(xs))],side=1,w=width,caps=(True,True))


def scene(walks=True,ground=None,dense=False,offset=(0.,0.),spec=None):
    spec=spec or building()
    streets=[(np.asarray(p)+offset,*rest) for p,*rest in road()]
    wk=[walk(dense,offset=offset)] if walks else []
    raw=copy.deepcopy(wk);drives=[];calls=[]
    def terrain(xy):
        calls.append(len(xy))
        return ground(xy-np.asarray(offset)) if ground else np.zeros(len(xy))
    b.doors([(spec,0.,0.)],streets,*offset,drives,ground=terrain,walks=wk,raw_walks=raw)
    return spec,wk,raw,drives,calls


class DrivewayTests(unittest.TestCase):
    def test_garage_and_footpath_connections_and_single_extra_batch(self):
        spec,wk,raw,drives,calls=scene()
        panels=[s for s in spec.access.solids if s.kind=='driveway']
        self.assertEqual(len(panels),8)
        self.assertEqual(len(calls),2)
        self.assertLessEqual(calls[-1],4*37)
        self.assertAlmostEqual(panels[0].top[0][2],spec.access.garage_z)
        self.assertAlmostEqual(panels[-1].top[1][1],-6.5)
        self.assertAlmostEqual(panels[-1].top[1][2],.15+2.5*.015)
        for a,c in zip(panels,panels[1:]):
            np.testing.assert_allclose(a.top[1],c.top[0])
            np.testing.assert_allclose(a.top[2],c.top[3])
        self.assertEqual(wk[0]['driveways'],raw[0]['driveways'])
        self.assertTrue(all(d.get('bne_access_only') for d in drives))
        self.assertEqual(BuildingPlan.from_spec(spec).access,spec.access)

    def test_no_footpath_drive_reaches_road_edge(self):
        spec,*_=scene(walks=False)
        end=[s for s in spec.access.solids if s.kind=='driveway'][-1]
        self.assertAlmostEqual(end.top[1][1],-9.)
        self.assertAlmostEqual(end.top[1][2],.01)

    def test_landing_link_is_optional_and_has_clear_interfaces(self):
        spec,*_=scene()
        self.assertTrue(any(s.kind=='path_link' for s in spec.access.solids))
        self.assertFalse(any(s.kind=='path' for s in spec.access.solids))
        with patch.dict(os.environ,{'BNE_BUILDING_PATHS':'off'}):
            spec,*_=scene()
        self.assertTrue(any(s.kind=='driveway' for s in spec.access.solids))
        self.assertFalse(any(s.kind.startswith('path') for s in spec.access.solids))

    def test_steep_missing_and_obstructed_routes_do_not_cut_kerb(self):
        for terrain in (lambda xy:np.full(len(xy),np.nan),lambda xy:-xy[:,1]*.5):
            spec,wk,_,drives,_=scene(ground=terrain)
            self.assertFalse(any(s.kind=='driveway' for s in spec.access.solids))
            self.assertNotIn('driveways',wk[0])
            self.assertEqual(drives,[])
        spec=building()
        obstacle=building(fp=Footprint(((0,-5),(14,-5),(14,-3),(0,-3))))
        wk=[walk()]
        b.doors([(spec,0.,0.),(obstacle,0.,0.)],road(),0.,0.,[],ground=lambda xy:np.zeros(len(xy)),walks=wk)
        self.assertFalse(any(s.kind=='driveway' for s in spec.access.solids))

    def test_dense_collinear_walk_and_translated_frame_agree(self):
        a=scene()[0].access
        for spec,*_ in (scene(dense=True),scene(offset=(1000.,-2000.))):
            self.assertEqual(spec.access,a)

    def test_existing_pedestrian_ramp_and_narrow_walk_are_preserved(self):
        for wk in (walk(width=1.2),dict(walk(),ramps=[(48.,60.)])):
            spec=building()
            b.doors([(spec,0.,0.)],road(),0.,0.,[],ground=lambda xy:np.zeros(len(xy)),walks=[wk])
            self.assertFalse(any(s.kind=='driveway' for s in spec.access.solids))
            self.assertNotIn('driveways',wk)

    def test_rear_walking_strip_keeps_crossfall_without_tactile_driveway(self):
        p=vehicle_crossings.section(2.5,.15,1.)
        rear=p[(p[:,0]>=1.3)&(p[:,0]<=2.5)]
        np.testing.assert_allclose(rear[:,1],.15+rear[:,0]*.015)
        self.assertAlmostEqual(np.interp(.15,p[:,0],p[:,1]),.01)
        builder=sidewalks.Builder((0,0,0),collision=True)
        wk=walk();curb,out=sidewalks.run_geometry(wk['pts'],wk['side'],wk['w'])
        builder.add_run(curb,out,2.5,driveways=[(45.,50.)])
        full,collision=builder.arrays(),builder.col.arrays()
        self.assertTrue(np.isfinite(full[0]).all())
        self.assertNotIn(2,full[3])
        self.assertLessEqual(len(builder.vehicle_meshes[0][0]),160)
        self.assertLessEqual(len(builder.vehicle_meshes[0][1]),280)
        for point in builder.vehicle_meshes[0][0]:
            self.assertLess(np.linalg.norm(collision[0]-point,axis=1).min(),1e-6)


def fallback_scene(*,offset=(0.,0.),reverse=False,dense=False,terrain_failure=False,source_hole=False,obstacle=False):
    spec=building();items=[(spec,0.,0.)]
    # One independently observed obstacle at the nearest route's outer edge.
    if obstacle:
        other=building(fp=Footprint(((5.0,-6.2),(6.2,-6.2),(6.2,-5.2),(5.0,-5.2))),**{'class':'utility'})
        other.inference=None;other.plain=True
        items.append((other,0.,0.))
    if source_hole:
        boundary=Footprint(((-5,-14),(20,-14),(20,15),(-5,15)),
                           (((5.,-6.2),(6.2,-6.2),(6.2,-5.2),(5.,-5.2)),))
        spec.site=Site('known','fixture',boundary,(),())
    xs=np.arange(-50.,101.) if dense else np.array((-50.,100.))
    points=np.column_stack((xs,np.full(len(xs),-12.)))+offset
    if reverse:points=points[::-1]
    streets=[(points,3.,'residential',False)]
    wk=walk(offset=offset)
    if reverse:wk=dict(wk,pts=wk['pts'][::-1],side=-1)
    unrelated=dict(pts=np.array(((-40.,20.,0.),(60.,20.,0.)))+[offset[0],offset[1],0.],side=1,w=2.5,caps=(True,True))
    walks=[unrelated,wk] if reverse else [wk,unrelated]
    raw=copy.deepcopy(walks);drives=[];calls=[];audit=DrivewayAudit()
    def ground(xy):
        calls.append(len(xy));local=xy-offset
        if terrain_failure:return np.full(len(xy),np.nan)
        return np.where((abs(local[:,0]-5.6)<.3)&(local[:,1]<-5.9),.6,0.) if not (source_hole or obstacle) else np.zeros(len(xy))
    b.doors(items,streets,*offset,drives,ground=ground,walks=walks,raw_walks=raw,driveway_audit=audit)
    return spec,items,streets,walks,raw,drives,calls,audit


class RankedDrivewayTests(unittest.TestCase):
    def test_nearest_grading_rejection_tries_second_complete_route_in_one_batch(self):
        spec,_,_,walks,raw,drives,calls,audit=fallback_scene()
        self.assertIn('driveway_candidate_1_rejected_grading',spec.access.diagnostics)
        self.assertIn('driveway_candidate_2_selected',spec.access.diagnostics)
        self.assertIn('driveway_connected',spec.access.diagnostics)
        self.assertEqual(len(calls),2)
        self.assertLessEqual(calls[-1],4*37)
        self.assertEqual(len(drives),1)
        self.assertEqual(sum(len(w.get('driveways',())) for w in walks),1)
        self.assertEqual([w.get('driveways') for w in walks],[w.get('driveways') for w in raw])
        self.assertEqual(audit.snapshot()['counts']['outcomes'],{'driveway_connected':1})
        self.assertEqual(audit.snapshot()['counts']['candidates']['selected_rank_2'],1)

    def test_nearest_obstacle_or_source_hole_tries_a_clear_alternative(self):
        for options in (dict(obstacle=True),dict(source_hole=True)):
            spec,*_=fallback_scene(**options)
            self.assertIn('driveway_candidate_1_rejected_obstruction',spec.access.diagnostics)
            self.assertIn('driveway_candidate_2_selected',spec.access.diagnostics)
            if spec.site is not None:
                for solid in spec.access.solids:
                    if solid.kind=='driveway':self.assertTrue(spec.site.boundary.shape().covers(Polygon([p[:2] for p in solid.top])))

    def test_fallback_rebase_reversed_street_order_and_dense_collinear_roads(self):
        expected=fallback_scene()[0].access
        for options in (dict(offset=(1000.,-2000.)),dict(reverse=True),dict(dense=True),dict(reverse=True,dense=True)):
            spec,*_=fallback_scene(**options)
            self.assertEqual(spec.access,expected,options)

    def test_unknown_terrain_does_not_drop_a_curb_or_claim_crossing_only(self):
        spec,_,_,walks,raw,drives,_,audit=fallback_scene(terrain_failure=True)
        self.assertFalse(any(s.kind=='driveway' for s in spec.access.solids))
        self.assertFalse(any(w.get('driveways') for w in (*walks,*raw)))
        self.assertFalse(drives)
        self.assertNotIn('crossing_only',spec.access.diagnostics)
        self.assertEqual(sum(audit.snapshot()['counts']['outcomes'].values()),1)
        self.assertEqual(audit.snapshot()['crossing_only_feasibility'],'not_evaluated')

    def test_failed_replan_preserves_previous_physical_route_cuts_and_records(self):
        spec,items,streets,walks,raw,drives,_,_=fallback_scene()
        physical=spec.access.solids;landscape=spec.access.landscape
        cuts=copy.deepcopy(walks);rawcuts=copy.deepcopy(raw);records=copy.deepcopy(drives)
        audit=DrivewayAudit()
        for _ in range(2):
            driveways.resolve(items,streets,walks,raw,lambda p:np.full(len(p),np.nan),0,0,drives,audit=audit)
            self.assertEqual(spec.access.solids,physical)
            self.assertEqual(spec.access.landscape,landscape)
            self.assertEqual(drives,records)
            for actual,old in zip(walks,cuts):self.assertEqual(actual.get('driveways'),old.get('driveways'))
            for actual,old in zip(raw,rawcuts):self.assertEqual(actual.get('driveways'),old.get('driveways'))
        self.assertIn('driveway_replan_retained_previous',spec.access.diagnostics)
        self.assertEqual(audit.snapshot()['counts']['outcomes'],{'driveway_replan_retained_previous':2})

    def test_repeated_success_does_not_duplicate_owned_curbs_or_drive_records(self):
        spec,items,streets,walks,raw,drives,_,_=fallback_scene()
        ground=lambda xy:np.where((abs(xy[:,0]-5.6)<.3)&(xy[:,1]<-5.9),.6,0.)
        before=spec.access
        driveways.resolve(items,streets,walks,raw,ground,0,0,drives)
        self.assertEqual(spec.access,before)
        self.assertEqual(len(drives),1)
        self.assertEqual(sum(len(w.get('driveways',())) for w in walks),1)

    def test_over_budget_road_inventory_is_declined_independent_of_source_order(self):
        def run(reverse):
            spec=building();roads=[]
            for i in range(65):
                roads.append((np.array(((-20.,-12.-i*.02),(20.,-12.-i*.02))),3.,'residential',False))
            if reverse:roads.reverse()
            audit=DrivewayAudit();walks=[]
            b.doors([(spec,0,0)],roads,0,0,[],ground=lambda p:np.zeros(len(p)),walks=walks,driveway_audit=audit)
            return spec.access,audit.snapshot()
        first,a=run(False);second,c=run(True)
        self.assertEqual(first,second)
        self.assertEqual(a,c)
        self.assertIn('driveway_omitted_road_query_budget',first.diagnostics)
        self.assertFalse(any(s.kind=='driveway' for s in first.solids))

    def test_invalid_legacy_obstacle_is_diagnosed_without_aborting_other_geometry(self):
        spec=building();other=building()
        other.footprint=None;other.ring=np.array(((20,0),(22,2),(20,2),(22,0)),float)
        other.inference=None;other.plain=True
        b.doors([(spec,0,0),(other,0,0)],road(),0,0,[],ground=lambda p:np.zeros(len(p)),walks=[walk()])
        self.assertFalse(any(s.kind=='driveway' for s in spec.access.solids))
        self.assertTrue(any('unknown_obstacle_inventory' in note for note in spec.access.diagnostics))

    def test_controlled_roads_and_unknown_site_inventory_do_not_gain_inferred_access(self):
        for controlled in (True,False):
            spec=building()
            streets=[(np.array(((-50.,-12.),(100.,-12.))),3.,'motorway' if controlled else 'residential',False)]
            if not controlled:
                from types import SimpleNamespace
                spec.site=SimpleNamespace(boundary=Footprint(((-5,-20),(20,-20),(20,15),(-5,15))),exclusions=None)
            wk=[walk()];drives=[]
            b.doors([(spec,0,0)],streets,0,0,drives,ground=lambda p:np.zeros(len(p)),walks=wk)
            self.assertFalse(any(s.kind=='driveway' for s in spec.access.solids))
            self.assertNotIn('driveways',wk[0])

    def test_surviving_green_beds_do_not_overlap_the_chosen_fallback(self):
        spec,*_=fallback_scene()
        paths=[Polygon([p[:2] for p in s.top]) for s in spec.access.solids]
        for bed in spec.access.landscape:
            shape=Polygon([p[:2] for p in bed.top])
            self.assertTrue(all(shape.intersection(p).area<1e-7 for p in paths))

    def test_same_source_components_own_separate_routes_cuts_and_records(self):
        def planned(reverse=False,translation=(0.,0.)):
            specs=[]
            for x in (0.,24.):
                fp=Footprint(((x,0),(x+12,0),(x+12,10),(x,10))).translated(*translation)
                specs.append(building(fp=fp,seed_id='same-source-components'))
            self.assertEqual(specs[0].seed,specs[1].seed)
            self.assertEqual(specs[0].evidence.source_id,specs[1].evidence.source_id)
            wk=walk();wk['pts']=wk['pts']+[translation[0],translation[1],0.]
            streets=[(np.asarray(points)+translation,*rest) for points,*rest in road()]
            items=[(s,0.,0.) for s in specs]
            if reverse:items.reverse()
            raw=copy.deepcopy([wk]);drives=[]
            b.doors(items,streets,0,0,drives,ground=lambda xy:np.zeros(len(xy)),walks=[wk],raw_walks=raw)
            self.assertEqual(len(drives),2)
            self.assertEqual(len(wk.get('driveways',())),2)
            owners={d['bne_building_owner'] for d in drives}
            self.assertEqual(len(owners),2)
            self.assertEqual(set(wk['building_driveway_owners']),owners)
            before=[s.access for s in specs]
            driveways.resolve(items,streets,[wk],raw,lambda p:np.zeros(len(p)),0,0,drives)
            self.assertEqual(len(drives),2)
            self.assertEqual(len(wk['driveways']),2)
            self.assertEqual([s.access for s in specs],before)
            return owners,tuple(sorted(wk['driveways']))
        self.assertEqual(planned(),planned(True))
        first,_=planned();translated,_=planned(translation=(1000.,-2000.))
        self.assertEqual(first,translated)

    def test_commit_pass_protects_both_neighboring_flared_mouths(self):
        specs=[]
        for x in (0.,4.5):
            s=building(fp=Footprint(((x,0),(x+3.6,0),(x+3.6,10),(x,10))),seed_id=str(x))
            s.door=(0,1.8);s.garage_opening=(0,1.8,3.,2.4)
            apron=access_patch(s,0,1.8,3.3,0.,2.5,(.06,.02,.02,.06),-.1,'apron')
            s.access=AccessPlan(.06,.06,(apron,))
            specs.append(s)
        wk=walk();raw=copy.deepcopy([wk]);drives=[]
        driveways.resolve([(s,0,0) for s in specs],road(),[wk],raw,lambda p:np.zeros(len(p)),0,0,drives)
        intervals=sorted(wk.get('driveways',()))
        self.assertGreaterEqual(len(intervals),1)
        for first,second in zip(intervals,intervals[1:]):
            self.assertLess(first[1]+vehicle_crossings.FLARE,second[0]-vehicle_crossings.FLARE)
        self.assertTrue(any(any('neighbour_crossing_conflict' in note for note in s.access.diagnostics) for s in specs))

    def test_partial_same_source_replan_replaces_only_installed_component(self):
        from sitegen.portals import installed_owner
        for reverse in (False,True):
            specs=[building(fp=Footprint(((x,0),(x+20,0),(x+20,10),(x,10))),
                            seed_id='partial-components') for x in (0.,32.)]
            wk=walk();wk['pts'][-1,0]=150.
            raw=copy.deepcopy([wk]);drives=[]
            items=[(s,0.,0.) for s in specs]
            b.doors(items[::-1] if reverse else items,road(),0,0,drives,
                    ground=lambda p:np.zeros(len(p)),walks=[wk],raw_walks=raw)
            a,c=specs;owner_a,owner_c=map(installed_owner,specs)
            self.assertEqual(len(drives),2)
            a_cut=copy.deepcopy(wk['building_driveway_owners'][owner_a])
            old_c_cut=copy.deepcopy(wk['building_driveway_owners'][owner_c])
            a_record=copy.deepcopy(next(d for d in drives if d['bne_building_owner']==owner_a))
            # Entrance refitting must carry the installed local owner token even
            # when the sibling is absent from this invocation.
            b.doors([(c,0.,0.)],road(),0,0,drives,ground=lambda p:np.zeros(len(p)),
                    walks=[wk],raw_walks=raw)
            self.assertEqual(installed_owner(c),owner_c)
            edge,along,width,height=c.garage_opening
            c.garage_opening=(edge,16.95 if along<10 else 3.05,width,height)
            apron=access_patch(c,edge,c.garage_opening[1],width+.3,0.,2.5,
                               (.06,.02,.02,.06),-.1,'apron')
            c.access=AccessPlan(.06,.06,(apron,),diagnostics=c.access.diagnostics)
            driveways.resolve([(c,0.,0.)],road(),[wk],raw,lambda p:np.zeros(len(p)),0,0,drives)
            self.assertEqual(installed_owner(c),owner_c)
            self.assertEqual(wk['building_driveway_owners'][owner_a],a_cut)
            self.assertNotEqual(wk['building_driveway_owners'][owner_c],old_c_cut)
            self.assertEqual(next(d for d in drives if d['bne_building_owner']==owner_a),a_record)
            self.assertEqual(len(drives),2)
            self.assertEqual(len(wk['driveways']),2)

    def test_fresh_partial_component_cannot_claim_installed_sibling_owner(self):
        from sitegen.portals import installed_owner
        a=building(width=20,seed_id='fresh-partial-components')
        wk=walk();wk['pts'][-1,0]=150.
        raw=copy.deepcopy([wk]);drives=[]
        b.doors([(a,0.,0.)],road(),0,0,drives,ground=lambda p:np.zeros(len(p)),
                walks=[wk],raw_walks=raw)
        owner_a=installed_owner(a)
        a_cut=copy.deepcopy(wk['building_driveway_owners'][owner_a])
        a_record=copy.deepcopy(drives[0])
        c=building(fp=Footprint(((32,0),(52,0),(52,10),(32,10))),seed_id='fresh-partial-components')
        self.assertIsNone(installed_owner(c))
        b.doors([(c,0.,0.)],road(),0,0,drives,ground=lambda p:np.zeros(len(p)),
                walks=[wk],raw_walks=raw)
        self.assertNotEqual(installed_owner(c),owner_a)
        self.assertEqual(wk['building_driveway_owners'][owner_a],a_cut)
        self.assertEqual(next(d for d in drives if d['bne_building_owner']==owner_a),a_record)
        self.assertEqual(len(drives),2)
        self.assertEqual(len(wk['driveways']),2)


if __name__=='__main__':unittest.main()
