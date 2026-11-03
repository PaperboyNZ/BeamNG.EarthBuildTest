"""Actual commercial geometry, clearance, complete directories and freeze boundary."""
from dataclasses import replace
from pathlib import Path
import sys,unittest
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'server'));sys.path.insert(0,str(ROOT/'tools'))
from buildgen import property_assets as a,property_geometry as g
from buildgen import property_sign_text as text
from buildgen import property_palette as palette
from buildgen.plan import BuildingPlan
from sitegen import property_directories as pd,shared_courts as sc
from preview_commercial_stage_one import fixture,FAMILIES
from test_sitegen_shared_courts import fixture as court_fixture


class PropertyGeometryTests(unittest.TestCase):
    def test_batched_prism_preserves_shape_uv_and_winding(self):
        import buildings as b
        direct=a.Mesh();queued=b.Mesh();material=(0,(180,190,200,255))
        tangent=np.array((.6,.8))
        for mesh in (direct,queued):g.box(mesh,(13.,-9.),tangent,3.2,.35,2.1,2.9,material)
        p,uv,t,mi,col=queued.arrays()
        original=direct.arrays()
        np.testing.assert_allclose(p,original[0],atol=1e-10)
        np.testing.assert_array_equal(uv,original[1]);np.testing.assert_array_equal(t,original[2])

    def test_detail_setting_bounds_work_before_text_baking(self):
        from buildgen import quality
        from PIL import Image
        from io import BytesIO
        s=fixture(FAMILIES[0])[0][0][0]
        rows=tuple((replace(s,property_identity=dict(s.property_identity,display_name='Shop '+str(i),revision=str(i))),0.,0.) for i in range(40))
        for detail in ('minimum','very_low','low'):
            with patch.object(text,'prepare_fascia',side_effect=AssertionError('low detail baked text')):
                self.assertEqual(quality.run(detail,a.visuals,rows),((),()))
        for detail,count,width in (('medium',8,256),('high',16,512),('very_high',24,512),('ultra',32,1024)):
            meshes,boards=quality.run(detail,a.visuals,rows)
            self.assertEqual(len(boards),count)
            self.assertEqual({Image.open(BytesIO(board.png)).width for board in boards},{width})
        counts=[len(a.furniture_template('trolley_shelter',rank)[2]) for rank in (2,3,4,5)]
        self.assertEqual(counts,sorted(set(counts)))
        self.assertLess(counts[0],counts[-1]/5)
        self.assertIs(a.furniture_template('bench',3),a.furniture_template('bench',3))

    def test_sign_palette_tracks_region_and_facade_and_changes_asset_revision(self):
        import buildings as b
        original=fixture(FAMILIES[0])[0][0][0]
        colours=[];revisions=[]
        for region in ('nz_temperate','eu_atlantic','jp_temperate','tropical_humid'):
            environment=replace(original.inference.selection.environment,region=region)
            inference=replace(original.inference,selection=replace(original.inference.selection,environment=environment))
            s=replace(original,inference=inference)
            colour=palette.resolve(s);colours.append(colour)
            self.assertGreaterEqual(palette.contrast(colour[0],colour[1]),4.5)
            revisions.append(text.prepare_fascia('Example Market',palette=colour).revision)
        self.assertEqual(len(set(colours)),4);self.assertEqual(len(set(revisions)),4)
        changed=replace(original,facade=b.custom_look(b.PANEL,(.15,.25,.75)))
        self.assertNotEqual(palette.resolve(original),palette.resolve(changed))

    def test_all_six_families_keep_identity_through_freeze_and_fit_real_name(self):
        for row in FAMILIES:
            with self.subTest(row[0]):
                items,_=fixture(row);s=items[0][0]
                self.assertIsInstance(s,BuildingPlan)
                self.assertEqual(s.property_identity['kind'],row[0])
                meshes,boards=a.visuals(items)
                self.assertEqual(len(boards),1)
                self.assertEqual(len(meshes),1)
                p,uv,t,mi,mats,col=meshes[0]
                self.assertTrue(np.isfinite(p).all())
                self.assertTrue(np.all(np.linalg.norm(np.cross(p[t[:,1]]-p[t[:,0]],p[t[:,2]]-p[t[:,0]]),axis=1)>1e-9))
                self.assertEqual(mats[mi[0]],boards[0].material)
                # A named panel sits only in its reserved aperture-free band.
                c,u,n,width,z0,z1=g.sign_slot(s,0,0)
                self.assertAlmostEqual(p[:,2].min(),z0);self.assertAlmostEqual(p[:,2].max(),z1)
                self.assertLessEqual(uv[:,1].max(),boards[0].used_ratio)
                blank=replace(s,property_identity=None)
                self.assertEqual(a.visuals(((blank,0.,0.),)),((),()))

    def test_furniture_meshes_are_bounded_non_degenerate_and_closed_primitives(self):
        for kind in ('trolley_shelter','bench','bollard','bike_rack','service_cabinet','planter'):
            mesh=a.furniture(kind);p,uv,t,mi,mats,col=mesh.arrays()
            self.assertLess(len(t),2000);self.assertTrue(np.isfinite(p).all())
            areas=np.linalg.norm(np.cross(p[t[:,1]]-p[t[:,0]],p[t[:,2]]-p[t[:,0]]),axis=1)
            self.assertTrue((areas>1e-9).all(),kind)
            self.assertGreater(p[:,2].max(),.4)
        self.assertLess(len(a.trolley_shelter(detail=False).tris),len(a.trolley_shelter().tris))

    def court(self,tenants=2,position=(8,8)):
        tile,plan,items=court_fixture()
        court,why=sc.fit(plan,lambda lat,lon:np.full(np.shape(lat),20.))
        self.assertIsNone(why)
        key=pd.member_key(plan.evidence.ref)
        data=dict(site_id=key,address=dict(number='6',street='Main Road'),
            display=dict(position=position),tenants=[dict(identity='test:'+str(i),
                member=pd.member_key(plan.evidence.memberships[0].member),name='Tenant '+str(i+1),
                unit=str(i+1),association='supported') for i in range(tenants)])
        return tile,court,items,key,data

    def test_shared_directory_all_pages_and_exact_membership(self):
        tile,court,items,key,data=self.court(10)
        with patch.object(pd,'catalogue',return_value=('test',{key:data})):
            meshes,boards=a.visuals(items,(court,),tile.frame,(*tile.box[:2],0.))
        self.assertEqual(len(boards),2);self.assertEqual(len(meshes),1)
        source=sc.project_points(meshes[0][0]+(*tile.box[:2],0.),tile.frame,sc._frame(court.plan))
        self.assertGreater(source[:,0].min(),4.)
        self.assertLess(source[:,0].max(),12.)
        # A source hole and existing member footprints cannot host a sign.
        for position in ((0,0),(-40,0),('bad','data')):
            data['display']['position']=position
            with patch.object(pd,'catalogue',return_value=('test',{key:data})):
                self.assertEqual(a.visuals(items,(court,),tile.frame,(*tile.box[:2],0.)),((),()))

    def test_partial_directory_is_never_emitted(self):
        tile,court,items,key,data=self.court(32,position=(13,8))
        with patch.object(pd,'catalogue',return_value=('test',{key:data})):
            # Four boards do not fit on the declared court at this position.
            self.assertEqual(a.visuals(items,(court,),tile.frame,(*tile.box[:2],0.)),((),()))


if __name__=='__main__':unittest.main()
