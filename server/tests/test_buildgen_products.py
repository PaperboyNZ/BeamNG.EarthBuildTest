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

    def test_named_assets_survive_visual_refinement_and_relocation(self):
        from buildgen import property_assets
        class Board:
            material='bne_fascia_123_face'
            filename='bne_fascia_123.png'
            png=b'fixture-image'
            def material_definition(self, directory):
                return {'name':self.material, 'mapTo':self.material,
                        'Stages':[{'baseColorMap':directory+'/'+self.filename}]}
        extra=b.visual_products(self.plans)[0][0]
        with patch.object(property_assets,'visuals',return_value=((extra,),(Board(),))):
            before_dir,before=self.retain_lite()
            out=self.root/'named-full';out.mkdir()
            self.assertIsNotNone(products.refine(bw,self.tile,self.key,str(out),'/full','full'))
            after=json.loads((out/bw.geo_names(self.tile.key)['json']).read_text())
            self.assertEqual(before['physicalHash'],after['physicalHash'])
            self.assertGreaterEqual(len(after['buildingChunks']['visual']),2)
            self.assertEqual(after['propertyMaterials']['names'],['bne_fascia_123_face'])
            self.assertEqual((out/'bne_fascia_123.png').read_bytes(),b'fixture-image')
            self.assertIn('/full/bne_fascia_123.png', (out/Path(after['propertyMaterials']['path']).name).read_text())
            again=self.root/'named-again';again.mkdir()
            with patch.object(property_assets,'visuals',side_effect=AssertionError('visual cache missed')):
                self.assertIsNotNone(products.refine(bw,self.tile,self.key,str(again),'/again','full'))
            restored=json.loads((again/bw.geo_names(self.tile.key)['json']).read_text())
            material=(again/Path(restored['propertyMaterials']['path']).name).read_text()
            self.assertIn('/again/bne_fascia_123.png',material)
            self.assertNotIn('/full/',material)

    def test_normal_revisit_restores_named_assets_in_new_session(self):
        from buildgen import property_assets
        import revisit
        self.addCleanup(revisit.close, str(self.cache))
        class Board:
            material='bne_fascia_789_face'; filename='bne_fascia_789.png'; png=b'revisit-image'
            def material_definition(self, directory):
                return {'name':self.material, 'mapTo':self.material,
                        'Stages':[{'baseColorMap':directory+'/'+self.filename}]}
        extra=b.visual_products(self.plans)[0][0]
        parts=self.parts('lite')
        first=self.root/'revisit-first';first.mkdir()
        second=self.root/'revisit-second';second.mkdir()
        with patch.object(property_assets,'visuals',return_value=((extra,),(Board(),))), \
             patch.object(bw,'_frame_grader',return_value=None), \
             patch.object(bw,'_tile_parts',return_value=parts), \
             patch('revisit.ON',True):
            token=DETAIL.set('lite')
            try:
                bw._geo_content(self.gx,self.gy,15,str(first),'/first',True,False,False,False,0.,None,None)
                with patch.object(bw,'_tile_parts',side_effect=AssertionError('revisit cache missed')), \
                     patch('buildgen.products.refine',side_effect=AssertionError('not a revisit hit')):
                    bw._geo_content(self.gx,self.gy,15,str(second),'/second',True,False,False,False,0.,None,None)
            finally:DETAIL.reset(token)
        data=json.loads((second/bw.geo_names(self.tile.key)['json']).read_text())
        self.assertEqual((second/'bne_fascia_789.png').read_bytes(),b'revisit-image')
        definition=(second/Path(data['propertyMaterials']['path']).name).read_text()
        self.assertIn('/second/bne_fascia_789.png',definition)
        self.assertNotIn('/first/',definition)

    def test_optional_chunk_joins_existing_progress_group(self):
        from buildgen import property_assets
        class Board:
            material='bne_fascia_789_face'; filename='bne_fascia_789.png'; png=b'fixture'
            def material_definition(self,directory):
                return {'name':self.material,'Stages':[{'baseColorMap':directory+'/'+self.filename}]}
        parts=self.parts('lite')
        original=parts.bld[0] if isinstance(parts.bld[0],list) else [parts.bld[0]]
        names=['bld' if n==0 else f'bld{n+1}' for n in range(len(original))]
        parts.bld=(original,parts.bld[1],parts.bld[2],[{'group':'0','visual':names}],{})
        out=self.root/'grouped';out.mkdir()
        with patch.object(property_assets,'visuals',return_value=((original[0],),(Board(),))):
            bw._write_geo_content(str(out),'/grouped',self.tile,parts)
        data=json.loads((out/bw.geo_names(self.tile.key)['json']).read_text())
        extra='bld' if not original else f'bld{len(original)+1}'
        self.assertIn(extra,data['buildingGroups'][0]['visual'])
        self.assertEqual(data['propertyMaterials']['parts'],[extra])

    def test_directory_catalogue_content_changes_revisit_key(self):
        import revisit
        from sitegen import property_directories
        source=self.root/'directories.json'
        source.write_text('{"version":1,"sites":[]}')
        property_directories.catalogue.cache_clear()
        self.addCleanup(property_directories.catalogue.cache_clear)
        with patch.dict(os.environ, {'BNE_PROPERTY_IDENTITIES':str(source)}):
            first=revisit.key('roadsg', 'fixture')
            source.write_text('{"version":1,"sites":[],"revision":2}')
            # A new worker loads the changed pinned catalogue; simulate its cache.
            property_directories.catalogue.cache_clear()
            second=revisit.key('roadsg', 'fixture')
        self.assertNotEqual(first,second)

    def test_optional_property_failure_does_not_block_building_tile(self):
        from buildgen import property_assets
        with patch.object(property_assets,'visuals',side_effect=ValueError('bad optional text')):
            _,data=self.retain_lite()
        self.assertTrue(data['buildingChunks']['visual'])
        self.assertNotIn('propertyMaterials',data)

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
