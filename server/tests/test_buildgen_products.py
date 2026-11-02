"""A lite/full upgrade reuses accepted physics and never re-enters tile planning."""
from pathlib import Path
import json,os,sys,tempfile,types,unittest
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b,blockworker as bw,geotiles,inputwatch
from buildgen import freeze_items,products
from buildgen.progressive import DETAIL
from productcache import Store
from test_buildgen_regions import building


class IndependentProductsTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'BNE_BUILDING_GENERATOR':'v2'});self.env.start();self.addCleanup(self.env.stop)
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.root=Path(self.folder.name);self.cache=self.root/'cache'
        self.worker=patch.object(bw,'_s',types.SimpleNamespace(cache_dir=str(self.cache),md=types.SimpleNamespace(versions=lambda:{'buildings':'fixture1'})))
        self.worker.start();self.addCleanup(self.worker.stop)
        self.gx,self.gy=geotiles.tile_of(-36.91493,174.9094);self.tile=geotiles.geobox(self.gx,self.gy)
        self.plans=freeze_items([(building('jp_temperate'),0.,0.)])
        self.source=self.root/'source-revision';self.source.write_text('r1')
        self.watched=inputwatch.snapshot({'files':{str(self.source)},'overflow':False})
        dep=bw._geo_content_key(self.tile.key,15,True,False,False,False,0.,None,None,building_detail='accepted-plan-v1')
        self.key,self.dependencies=products.address(self.tile,dep)

    def parts(self,detail):
        P=bw._Parts();P.plans=self.plans
        P.chunks=[];P.ctx=[];P.walks_raw=[];P.dmesh=P.tmesh=P.rmesh=None
        P.props=[];P.wires=[];P.park=[];P.fuel=[];P.fuel_pads=[]
        P.guardrail_rows=[];P.garage_sound=[];P.wells=[];P.vegetation_exclusions=[]
        token=DETAIL.set(detail)
        try:P.bld=b.road_tile(self.tile.frame,self.tile,None,None,None,items=self.plans)
        finally:DETAIL.reset(token)
        return P

    def retain_lite(self):
        out=self.root/'lite';out.mkdir();P=self.parts('lite')
        path,n,info=bw._write_geo_content(str(out),'/lite',self.tile,P)
        self.assertTrue(products.retain(bw,self.tile,self.key,self.dependencies,P,str(out),'/lite',n,info,self.watched))
        return out,json.loads((out/bw.geo_names(self.tile.key)['json']).read_text())

    def test_runtime_upgrade_skips_combined_pipeline_and_preserves_physical_identity(self):
        before_dir,before=self.retain_lite();out=self.root/'full';out.mkdir()
        with patch.object(bw,'_tile_parts',side_effect=AssertionError('replanned combined tile')),\
             patch.object(bw,'_frame_grader',side_effect=AssertionError('terrain replanned')),\
             patch.object(b,'collision_mesh',side_effect=AssertionError('rebuilt collision')),\
             patch.object(b,'doors',side_effect=AssertionError('rebuilt access')):
            token=DETAIL.set('full')
            try:result=bw._geo_content(self.gx,self.gy,15,str(out),'/full',True,False,False,False,0.,None,None)
            finally:DETAIL.reset(token)
        after=json.loads((out/bw.geo_names(self.tile.key)['json']).read_text())
        self.assertEqual(after['physicalHash'],before['physicalHash'])
        self.assertEqual(after['sectorManifest']['physical'],before['sectorManifest']['physical'])
        self.assertNotEqual(after['sectorManifest']['visual']['revision'],before['sectorManifest']['visual']['revision'])
        self.assertEqual(after['sectorManifest']['visual']['depends_on'],before['physicalHash'])
        self.assertEqual(after['buildingDetail'],'full')
        self.assertNotEqual(after['h'],before['h'])
        for what in before['buildingChunks']['collision']:
            name=bw.geo_names(self.tile.key,parts={what:{}})[what]
            self.assertEqual((out/name).read_bytes(),(before_dir/name).read_bytes())
        fresh_dir=self.root/'fresh';fresh_dir.mkdir()
        bw._write_geo_content(str(fresh_dir),'/fresh',self.tile,self.parts('full'))
        for what in after['buildingChunks']['visual']:
            name=bw.geo_names(self.tile.key,parts={what:{}})[what]
            self.assertEqual((out/name).read_bytes(),(fresh_dir/name).read_bytes())
        # A later worker/process visit restores the independently cached visuals.
        again=self.root/'again';again.mkdir()
        with patch.object(b,'visual_products',side_effect=AssertionError('recompiled cached visuals')):
            self.assertIsNotNone(products.refine(bw,self.tile,self.key,str(again),'/again','full'))

    def test_changed_terrain_or_street_source_invalidates_the_plan(self):
        self.retain_lite();self.source.write_text('new source revision')
        self.assertIsNone(products.refine(bw,self.tile,self.key,str(self.root),'/test','full'))
        with patch('revisit.code_key',return_value='new-generator-revision'):
            other,_=products.address(self.tile,'changed street/access/material revisions')
        self.assertNotEqual(other,self.key)

    def test_lazy_feed_revision_is_retained_after_source_resolution(self):
        parts=self.parts('lite');version={'revision':None}
        def planning(*args,**kwargs):
            version['revision']='manifest-discovered-during-planning'
            return parts
        lite=self.root/'cold';lite.mkdir();full=self.root/'upgraded';full.mkdir()
        with patch.object(bw._s.md,'versions',side_effect=lambda:dict(version)),\
             patch.object(bw,'_frame_grader',return_value=None),patch('revisit.ON',False):
            token=DETAIL.set('lite')
            try:
                with patch.object(bw,'_tile_parts',side_effect=planning):
                    bw._geo_content(self.gx,self.gy,15,str(lite),'/cold',True,False,False,False,0.,None,None)
            finally:DETAIL.reset(token)
            with patch.object(bw,'_tile_parts',side_effect=AssertionError('discovered revision was lost')):
                self.assertIsNotNone(bw._geo_content(self.gx,self.gy,15,str(full),'/full',True,False,False,False,0.,None,None))

    def test_failed_visual_upgrade_preserves_previous_complete_publication(self):
        before_dir,before=self.retain_lite()
        meta=before_dir/bw.geo_names(self.tile.key)['json'];accepted=meta.read_bytes()
        collision={n:p.read_bytes() for n,p in ((name,before_dir/name) for name in bw.geo_names(self.tile.key).values()) if p.exists() and 'bldcol' in n}
        with patch.object(b,'visual_products',side_effect=RuntimeError('worker failed')):
            with self.assertRaises(RuntimeError):products.refine(bw,self.tile,self.key,str(before_dir),'/lite','full')
        self.assertEqual(meta.read_bytes(),accepted)
        for name,data in collision.items():self.assertEqual((before_dir/name).read_bytes(),data)
        self.assertEqual(Store(str(self.cache)).load('physical',self.key).status,'ready')


if __name__=='__main__':unittest.main()
