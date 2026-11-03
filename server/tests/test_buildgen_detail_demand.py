"""FOV/resolution, hysteresis, free camera and stale-camera demand."""
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from buildgen import detail_demand as d


class DetailDemandTests(unittest.TestCase):
    def test_projected_feature_size_depends_on_camera_and_resolution(self):
        self.assertTrue(d.wanted(100,height=1080))
        self.assertFalse(d.wanted(300,height=1080))
        self.assertTrue(d.wanted(300,height=2160))
        self.assertTrue(d.wanted(300,height=1080,fov=20))
        self.assertFalse(d.wanted(300,height=1080,fov=100))
        self.assertAlmostEqual(d.pixels(100,height=2160),2*d.pixels(100,height=1080))

    def test_hysteresis_speed_reversal_and_explicit_distance_reach(self):
        self.assertTrue(d.wanted(300,previous=True,height=1080))
        self.assertFalse(d.wanted(300,previous=False,height=1080))
        self.assertFalse(d.wanted(50,fast=True))
        self.assertTrue(d.wanted(50,fast=True,free_camera=True))
        self.assertTrue(d.wanted(50,fast=False))
        self.assertFalse(d.wanted(500,fov=10,height=4000,reach=350))
        self.assertTrue(d.wanted(375,previous=True,fov=10,height=4000,reach=350))
        self.assertFalse(d.wanted(410,previous=True,fov=10,height=4000,reach=350))

    def test_invalid_or_previous_anchor_camera_keeps_legacy_policy(self):
        for cam in ({'x':0,'y':0,'h':float('nan')},{'x':False,'y':0},{'x':0,'y':0,'fovDeg':180},None):
            self.assertIsNone(d.camera(cam,2,2))
        good={'x':2.,'y':3.,'z':4.,'h':2160,'fovDeg':70}
        self.assertIsNone(d.camera(good,2,1))
        self.assertEqual(d.camera(good,2,2),(2.,3.,4.,70,2160))

    def test_existing_scheduler_uses_projection_and_free_camera_for_new_optional_work(self):
        from types import SimpleNamespace
        from concurrent.futures import Future
        from unittest.mock import patch
        import tempfile,roads,geodesy,geotiles
        key=geotiles.tile_of(0,0);frame=geodesy.EnuFrame(0,0)
        tracker=roads.GeoTracker();submitted=[]
        def submit(pool,fn,*args):
            f=Future();submitted.append((fn,f));return f
        loop=SimpleNamespace(run_in_executor=submit)
        with tempfile.TemporaryDirectory() as folder,patch.object(roads,'geo_wanted',return_value={key:0}),\
             patch.object(geotiles,'quad_dist',return_value=300.),\
             patch.object(geotiles,'tiles_near',return_value=[(*key,0)]):
            conn=SimpleNamespace(building_quality='adaptive',building_progress=True,send=lambda m:None,
                cam={'x':0.,'y':0.,'z':0.,'fovDeg':65.,'h':1080.},cam_aid=1,s=SimpleNamespace(out_dir=folder))
            def pose(speed=0,view=None):
                tracker.on_pose(conn,1,0,0,loop,lambda *a,**kw:None,vel=(speed,0),view=view,frame=frame)
            try:
                pose();self.assertEqual(submitted[-1][0].keywords['building_detail'],'lite')
                submitted[-1][1].set_result(dict(content=('/lite',0,{'h':'lite','parts':{},'buildingDetail':'lite'},[])))
                tracker.skins.add(key);tracker.need[(key,1)]={}
                conn.cam['h']=2160.;pose()
                self.assertEqual(submitted[-1][0].keywords['building_detail'],'full')
                conn.cam['h']=1080.;pose()
                self.assertTrue(tracker.building_demand[key],'retain detail in pixel hysteresis band')
                submitted[-1][1].set_result(dict(content=('/full',0,{'h':'full','parts':{},'buildingDetail':'full'},[])))
                tracker.info[key]['buildingDetail']='lite';conn.cam['h']=2160.
                pose(67.,view=(1000.,0.))
                self.assertEqual(submitted[-1][0].keywords['building_detail'],'full','free camera demand survives fast driving elsewhere')
            finally:tracker.close()


if __name__=='__main__':unittest.main()
