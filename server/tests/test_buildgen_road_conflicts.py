"""Ground-level street clearance is a geometry trim, never a fabricated lift."""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch
import numpy as np
from shapely.geometry import Polygon, box
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import freeze_items
from buildgen.road_conflicts import filter_items, source_items, CLEARANCE
from buildgen.topology import Footprint
from test_buildgen_facades import building


def flat(p):return np.zeros(len(p))
def road(y=1.,width=6.,offset=(0,0)):
    p=np.array([[-50,y,0],[100,y,0]],float);p[:,:2]+=offset
    return ('street',SimpleNamespace(cls='residential',width=width),p,None)
def item(fp=None,**attrs):
    spec=building(12,10,fp=fp,**attrs);spec.gring=flat(spec.ring)
    return spec,0.,0.


class RoadBuildingClipTests(unittest.TestCase):
    def test_ground_body_trimmed_behind_actual_sidewalk(self):
        original=item();notes=[]
        walk=dict(pts=np.array([[-50,5.25,0],[100,5.25,0]]),w=2.5,side=1)
        kept=filter_items([original],roads=[road()],walks=[walk],ground=flat,diagnostics=notes)
        self.assertEqual(len(kept),1);spec,lo,hi=kept[0]
        import sidewalks
        back=4.+sidewalks.profile(w=2.5)[:,0].max()
        self.assertGreaterEqual(min(spec.ring[:,1]),back+CLEARANCE-1e-8)
        self.assertAlmostEqual(spec.footprint.area,12*(10-back-CLEARANCE))
        self.assertTrue(original[0].footprint.shape().covers(spec.footprint.shape()))
        self.assertEqual(original[0].ring[:,1].min(),0.)
        self.assertIn('footprint_clipped_clear_of_street',spec.diagnostics)
        self.assertEqual(spec.height,original[0].height)
        self.assertEqual(spec.seed,original[0].seed)
        self.assertEqual(spec.facade,original[0].facade)
        self.assertIs(spec.inference,original[0].inference)
        self.assertEqual(spec.min_h,0.)
        self.assertEqual(notes[0]['reason'],'footprint_clipped_clear_of_street')
        for mesh in (b.build(freeze_items(kept)),b.build(freeze_items(kept),lite=True),b.collision_mesh(freeze_items(kept))):
            self.assertTrue(np.isfinite(mesh[0]).all())
            # Footprint and collision remain beyond the same actual sidewalk.
        self.assertGreaterEqual(b.collision_mesh(freeze_items(kept))[0][:,1].min(),back-1e-6)

    def test_new_doors_and_access_follow_trimmed_front(self):
        original=item(**{'class':'retail'})
        b.doors([original],[(road()[2][:,:2],3.,'residential',False)],0,0,ground=flat)
        kept=filter_items([original],roads=[road()],ground=flat)
        spec=kept[0][0]
        self.assertIsNone(spec.facades);self.assertIsNone(spec.access);self.assertIsNone(spec.door)
        b.doors(kept,[(road()[2][:,:2],3.,'residential',False)],0,0,ground=flat)
        self.assertIsNotNone(spec.access)
        self.assertGreaterEqual(spec.ring[:,1].min(),4.35-1e-8)

    def test_no_road_mesh_required_for_terrain_painted_streets(self):
        kept=filter_items([item()],chunks=[],roads=[road()],ground=flat)
        self.assertEqual(len(kept),1)
        self.assertAlmostEqual(kept[0][0].ring[:,1].min(),4.35)
        source=source_items([item()],[(road()[2][:,:2],3.,'residential',False)],flat)
        self.assertEqual(source[0][0].footprint,kept[0][0].footprint)

    def test_nonzero_frame_origin_and_height_offsets(self):
        first=filter_items([item()],roads=[road()],ground=flat)[0][0]
        origin=np.array([10000.,-20000.]);seen=[]
        def terrain(p):seen.extend(p.tolist());return np.full(len(p),37.)
        source=item();source=(source[0],37.,37.)
        second=filter_items([source],roads=[road(offset=origin)],origin=origin,ground=terrain)[0]
        self.assertEqual(first.footprint,second[0].footprint)
        self.assertEqual(second[1:],(37.,37.))
        self.assertTrue(all(9990<x<10020 and -20001<y<-19980 for x,y in seen))

    def test_explicit_elevated_parts_and_portals_unchanged(self):
        for field,value in (('min_h',5.5),('portal',True),('cls','bridge_structure'),('cls','toll_booth')):
            source=item();setattr(source[0],field,value)
            kept=filter_items([source],roads=[road()],ground=flat)
            self.assertIs(kept[0],source)

    def test_grade_separated_fixed_bridge_and_tunnel_preserved(self):
        source=item(height=5.)
        for z in (-8.,12.):
            chunk=dict(n=[[-50,1,z],[100,1,z]],w=6,m='road_asphalt_2lane',deck=True,fixed=True)
            kept=filter_items([source],[chunk],ground=flat)
            self.assertIs(kept[0],source)
        crossing=dict(n=[[-50,1,2],[100,1,2]],w=6,m='road_asphalt_2lane',deck=True,fixed=True)
        self.assertLess(filter_items([source],[crossing],ground=flat)[0][0].footprint.area,source[0].footprint.area)

    def test_courtyard_road_does_not_fill_or_cut_its_hole(self):
        fp=Footprint(((0,0),(20,0),(20,20),(0,20)),(((3,3),(3,17),(17,17),(17,3)),))
        source=item(fp)
        inside=('street',SimpleNamespace(cls='residential',width=3.),np.array([[6,10,0],[14,10,0]]),None)
        kept=filter_items([source],roads=[inside],ground=flat)
        self.assertIs(kept[0],source)
        exterior=filter_items([source],roads=[road(y=-1,width=4)],ground=flat)[0][0]
        self.assertEqual(len(exterior.footprint.holes),1)

    def test_polygon_only_junction_and_curved_ribbon(self):
        source=item()
        polygon=dict(n=[],w=0,m='road_asphalt_2lane',poly=[[-2,-2],[6,-2],[6,3],[-2,3]])
        kept=filter_items([source],[polygon],ground=flat)
        self.assertEqual(len(kept),1)
        self.assertLess(kept[0][0].footprint.shape().intersection(box(-2,-2,6,3).buffer(CLEARANCE)).area,1e-7)
        curve=dict(n=[[-10,1,0],[4,1,0],[4,15,0]],w=3,m='road_asphalt_2lane')
        self.assertTrue(filter_items([source],[curve],ground=flat))

    def test_consumed_and_thin_residuals_omitted(self):
        for width in (20.,16.):
            notes=[];self.assertEqual(filter_items([item()],roads=[road(width=width)],ground=flat,diagnostics=notes),[])
            self.assertEqual(notes[0]['reason'],'road_clip_no_usable_footprint')

    def test_service_aisles_and_painted_lines_do_not_trim_buildings(self):
        internal=road();internal[1].cls='service'
        source=item()
        self.assertIs(filter_items([source],roads=[internal],ground=flat)[0],source)
        mark=dict(n=[[-10,1,0],[30,1,0]],w=4,m='line_white')
        self.assertIs(filter_items([source],[mark],ground=flat)[0],source)

    def test_clipping_idempotent_and_road_order_independent(self):
        roads=[road(),road(y=20,width=2)]
        a=filter_items([item()],roads=roads,ground=flat)
        c=filter_items([item()],roads=roads[::-1],ground=flat)
        self.assertEqual(a[0][0].footprint,c[0][0].footprint)
        self.assertIs(filter_items(a,roads=roads,ground=flat)[0],a[0])

    def test_grounded_parking_garage_is_trimmed_and_refitted(self):
        spec=building(60,40,**{'class':'parking','height':9.,'num_floors':3,'seed_id':'road-garage'})
        spec.gring=flat(spec.ring)
        self.assertTrue(spec.deck)
        kept=filter_items([(spec,0,0)],roads=[road()],ground=flat)
        self.assertEqual(len(kept),1)
        self.assertLess(kept[0][0].footprint.area,spec.footprint.area)
        self.assertTrue(kept[0][0].deck)
        self.assertIsNotNone(b.deck_plan(*kept[0]))
        mesh=b.collision_mesh(freeze_items(kept))
        self.assertTrue(np.isfinite(mesh[0]).all())
        self.assertGreaterEqual(mesh[0][:,1].min(),4.35-1e-6)

    def test_church_spire_and_source_identity_survive_refitting(self):
        from test_buildgen_churches import make
        fp=Footprint(((0,0),(30,0),(30,20),(0,20)))
        spec,attrs=make(fp=fp,height=18.,roof_height=None,_church_spire='auto')
        kept=filter_items([(spec,0,0)],roads=[road()],ground=flat)
        self.assertEqual(len(kept),1)
        clipped=kept[0][0]
        self.assertEqual(clipped.evidence,spec.evidence)
        self.assertEqual(clipped.seed,spec.seed)
        self.assertEqual(clipped.church.total_height,spec.church.total_height)
        self.assertIsNotNone(clipped.church.spire)
        self.assertTrue(np.isfinite(b.build(freeze_items(kept))[0]).all())

    def test_sidewalk_corner_outer_fan_is_reserved(self):
        corner={'corner':{'arc':[[2,2,0],[6,2,0],[6,5,0]],'outer':[[2,5,0]]}}
        source=item()
        kept=filter_items([source],walks=[corner],ground=flat)
        self.assertEqual(len(kept),1)
        reserved=Polygon([[2,2],[6,2],[6,5],[2,5]]).buffer(CLEARANCE,join_style='mitre')
        self.assertLess(kept[0][0].footprint.shape().intersection(reserved).area,1e-7)

    def test_many_physical_ribbon_cells_share_one_terrain_probe_batch(self):
        calls=[]
        def terrain(p):calls.append(len(p));return np.zeros(len(p))
        nodes=np.c_[np.arange(-10,30,.5),np.ones(80),np.zeros(80)]
        chunk=dict(n=nodes.tolist(),w=6,m='road_asphalt_2lane')
        kept=filter_items([item()],[chunk],ground=terrain)
        self.assertEqual(len(kept),1)
        self.assertEqual(len(calls),2)  # one road-height batch, one clipped corner batch
        self.assertGreater(calls[0],1)
        self.assertLess(calls[0],100)

    def test_legacy_body_uses_new_clipped_polygon_in_every_representation(self):
        legacy=b.plan(np.array([[0,0],[12,0],[12,10],[0,10]]),{'class':'house','height':8.,'roof_shape':'gabled'})
        self.assertIsNone(legacy.footprint)
        kept=filter_items([(legacy,0,0)],roads=[road()],ground=flat)
        self.assertEqual(len(kept),1)
        clipped=kept[0][0]
        self.assertIsNone(clipped.inference)
        self.assertIsNotNone(clipped.footprint)
        self.assertEqual(clipped.height,legacy.height)
        for mesh in (b.build(kept),b.build(kept,lite=True),b.collision_mesh(kept)):
            self.assertTrue(np.isfinite(mesh[0]).all())
            self.assertGreaterEqual(mesh[0][:,1].min(),4.-1e-6)

    def test_clipped_plan_pickle_and_progressive_stages_share_geometry(self):
        import pickle
        from buildgen import progressive
        kept=filter_items([item()],roads=[road()],ground=flat)
        b.doors(kept,[(road()[2][:,:2],3.,'residential',False)],0,0,ground=flat)
        frozen=freeze_items(kept);restored=pickle.loads(pickle.dumps(frozen))
        for first,second in zip(b.build(frozen),b.build(restored)):
            np.testing.assert_array_equal(first,second)
        shell=progressive.shell(kept)
        self.assertGreaterEqual(shell[0][:,1].min(),4.-1e-6)  # roof overhang may reach the street edge
        events=[];publisher=progressive.Publisher('unused','/vfs',None,'c'*32)
        with patch.object(publisher,'publish',side_effect=lambda g,s,m,names=None:events.append(s)):
            publisher.shells(kept);meshes,groups=publisher.build(kept)
        self.assertEqual(events,[0,1,2])
        self.assertTrue(all(np.isfinite(m[0]).all() for m in meshes))

    def test_small_minimum_height_cannot_bypass_street_clearance(self):
        for minimum in (.51,2.,5.49):
            for elevation in (0.,37.):
                spec=item(height=8.)[0];spec.min_h=minimum
                kept=filter_items([(spec,elevation,elevation)],roads=[road()],
                                  ground=lambda p:np.full(len(p),elevation))
                self.assertEqual(len(kept),1)
                self.assertLess(kept[0][0].footprint.area,spec.footprint.area)
                self.assertEqual(kept[0][0].min_h,minimum)
                self.assertEqual(kept[0][0].height,spec.height)
        for elevation in (0.,37.):
            spec=item(height=8.)[0];spec.min_h=5.5;original=(spec,elevation,elevation)
            kept=source_items([original],[(road()[2][:,:2],3.,'residential',False)],
                              lambda p:np.full(len(p),elevation))
            self.assertIs(kept[0],original)

    def test_sidewalk_only_canopy_uses_pedestrian_not_road_headroom(self):
        spec=item(height=4.)[0];spec.min_h=3.
        original=(spec,0.,0.)
        walk=dict(pts=np.array([[-50,5.25,0],[100,5.25,0]]),w=2.5,side=1)
        self.assertIs(filter_items([original],walks=[walk],ground=flat)[0],original)
        spec.min_h=2.
        self.assertLess(filter_items([original],walks=[walk],ground=flat)[0][0].footprint.area,spec.footprint.area)

    def test_unknown_elevation_does_not_invent_a_grade_conflict(self):
        source=item()
        self.assertIs(filter_items([source],roads=[road()],ground=lambda p:np.full(len(p),np.nan))[0],source)
        with patch('buildgen.road_conflicts.MAX_ROADS',0):
            notes=[];self.assertIs(filter_items([source],roads=[road()],ground=flat,diagnostics=notes)[0],source)
            self.assertEqual(notes[0]['reason'],'road_clip_inventory_unresolved')

if __name__=='__main__':unittest.main()
