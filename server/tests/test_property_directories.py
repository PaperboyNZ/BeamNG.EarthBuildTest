import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sitegen import property_directories as d
from buildgen import property_sign_text as text
from buildgen import property_fonts as fonts

def ref(kind, key):
    return NS(kind=kind, identity=NS(namespace='source', feature_id=key))

def site():
    return NS(evidence=NS(ref=ref('site','s'), memberships=tuple(NS(member=ref('building',str(i))) for i in range(3))))

def data():
    return dict(site_id='source:s',address=dict(number='14',street='Main Street'),tenants=[
        dict(identity='id2',member='source:1',name='Café',unit='10',association='verified'),
        dict(identity='id1',member='source:2',name='商店',unit='2',association='supported')])

class DirectoryTests(unittest.TestCase):
    def tearDown(self): d.catalogue.cache_clear()
    def test_complete_members_and_natural_order(self):
        plan=d.plan(site(),data())
        self.assertEqual([t.identity for t in plan.tenants],['id1','id2'])
        self.assertEqual(plan.boards[0][0].name,'商店')
        self.assertEqual(plan.digest,d.plan(site(),data()).digest)
    def test_rejects_conflicts_foreign_and_overflow(self):
        v=data();v['tenants'].append(dict(v['tenants'][0],name='Different'))
        with self.assertRaises(ValueError): d.plan(site(),v)
        v=data();v['tenants'][0]['member']='source:foreign'
        with self.assertRaises(ValueError): d.plan(site(),v)
        v=data();v['tenants']*=17
        with self.assertRaises(ValueError): d.plan(site(),v)
        v=data();v['address']['number']=''
        with self.assertRaises(ValueError): d.plan(site(),v)
    def test_boards_cached_and_material(self):
        p=d.plan(site(),data()); first=text.prepare(p); second=text.prepare(p)
        self.assertIs(first,second)
        self.assertTrue(first[0].png.startswith(b'\x89PNG'))
        self.assertEqual(first[0].material_definition('/level')['Stages'][0]['baseColorMap'],'/level/'+first[0].filename)
        self.assertGreater(first[0].used_ratio,0)
    def test_international_shaping_and_roles(self):
        from PIL import features
        if not features.check('raqm'): self.skipTest('RAQM was loaded before FriBidi in this process')
        for value in ('مخبز السلام', 'नमस्ते दुकान', '商店 Tokyo', 'Cafe متجر'):
            self.assertTrue(text.prepare_fascia(value).png.startswith(b'\x89PNG'))
        self.assertNotEqual(text.prepare_fascia('Farm Shop',style='artisan').revision,
                            text.prepare_fascia('Farm Shop',style='trade').revision)
        self.assertTrue(fonts.resolve('商店','clinical','ja').endswith('NotoSansCJKjp.otf'))
        self.assertTrue(fonts.resolve('商店','clinical','zh-Hant').endswith('NotoSansCJKtc.otf'))
        with self.assertRaises(fonts.TextUnavailable): text.prepare_fascia('\U0010ffff')
        self.assertTrue(fonts.resolve('नमस्ते','clinical').endswith('NotoSansDevanagari.ttf'))
        self.assertTrue(fonts.resolve('Կենտրոն','artisan_bold').endswith('NotoSerifArmenian-Bold.ttf'))
        self.assertTrue(fonts.resolve('Market','noto_serif_italic').endswith('NotoSerif-Italic.ttf'))
        self.assertTrue(fonts.resolve('متجر','arabic_kufi_bold').endswith('NotoKufiArabic-Bold.ttf'))
    def test_explicit_tenant_typography_changes_revision(self):
        a=data(); b=data(); b['tenants'][0]['typography_role']='artisan'
        self.assertNotEqual(d.plan(site(),a).digest,d.plan(site(),b).digest)
        self.assertEqual(d.plan(site(),b).tenants[1].typography_role,'artisan')
        b['tenants'][0]['typography_role']='unknown'
        with self.assertRaises(ValueError): d.plan(site(),b)
    def test_fascia_aspect_and_cluster_boundaries(self):
        from io import BytesIO
        from PIL import Image
        default=text.prepare_fascia('Business')
        wide=text.prepare_fascia('Business',aspect=20)
        self.assertEqual((default.physical_width,default.physical_height),(4.,1.))
        self.assertEqual((wide.physical_width,wide.physical_height),(20.,1.))
        self.assertNotEqual(default.revision,wide.revision)
        self.assertEqual(Image.open(BytesIO(wide.png)).size,(1024,64))
        self.assertAlmostEqual(wide.used_ratio,51/64)
        self.assertEqual(text._clusters('a\u0301b\u200dc'),['a\u0301','b\u200dc'])
        for invalid in (1,25,float('nan'),True):
            with self.assertRaises(ValueError): text.prepare_fascia('Business',aspect=invalid)
    def test_palette_changes_both_text_products(self):
        p=((20,40,50),(255,255,255),(190,130,70))
        q=((40,70,40),(255,255,255),(230,210,100))
        self.assertNotEqual(text.prepare_fascia('Market',palette=p).revision,text.prepare_fascia('Market',palette=q).revision)
        self.assertNotEqual(text.prepare(d.plan(site(),data()),palette=p)[0].revision,text.prepare(d.plan(site(),data()),palette=q)[0].revision)
        with self.assertRaises(ValueError): text.prepare_fascia('Market',palette=((300,0,0),(0,0,0),(0,0,0)))
    def test_resolution_changes_pixels_not_source_or_physical_size(self):
        from io import BytesIO
        from PIL import Image
        source=data(); original=json.dumps(source,sort_keys=True)
        p=d.plan(site(),source)
        normal=text.prepare(p)[0]; small=text.prepare(p,pixel_width=256)[0]
        self.assertEqual(Image.open(BytesIO(small.png)).width,256)
        self.assertEqual(Image.open(BytesIO(normal.png)).width,512)
        self.assertEqual((small.physical_width,small.physical_height),(normal.physical_width,normal.physical_height))
        self.assertNotEqual(small.revision,normal.revision)
        large_f=text.prepare_fascia('Market',aspect=20)
        small_f=text.prepare_fascia('Market',aspect=20,pixel_width=256)
        self.assertEqual(Image.open(BytesIO(small_f.png)).width,256)
        self.assertEqual((large_f.physical_width,large_f.physical_height),(small_f.physical_width,small_f.physical_height))
        self.assertNotEqual(large_f.revision,small_f.revision)
        self.assertEqual(json.dumps(source,sort_keys=True),original)
        with self.assertRaises(ValueError): text.prepare(p,pixel_width=128)
    def test_broader_script_families_and_fail_closed_vertical(self):
        from PIL import features
        if not features.check('raqm'): self.skipTest('RAQM unavailable')
        for sample,family in [('தமிழ்','Tamil'),('తెలుగు','Telugu'),('ગુજરાતી','Gujarati'),
                              ('ಕನ್ನಡ','Kannada'),('മലയാളം','Malayalam'),('ਪੰਜਾਬੀ','Gurmukhi'),
                              ('ଓଡ଼ିଆ','Oriya'),('සිංහල','Sinhala'),('မြန်မာ','Myanmar'),
                              ('ភាសាខ្មែរ','Khmer'),('བོད་ཡིག','Tibetan'),('አማርኛ','Ethiopic'),
                              ('ܫܠܡܐ','Syriac'),('ދިވެހި','Thaana'),('ᏣᎳᎩ','Cherokee'),
                              ('ᐃᓄᒃ','CanadianAboriginal'),('ⵜⴰⵎⴰⵣⵉⵖⵜ','Tifinagh'),('ꆈꌠ','Yi'),('ꕙꔤ','Vai')]:
            with self.subTest(family=family):
                self.assertIn(family,fonts.resolve(sample))
                self.assertTrue(text.prepare_fascia(sample).png.startswith(b'\x89PNG'))
        with self.assertRaises(fonts.TextUnavailable): fonts.resolve('ᠮᠣᠩᠭᠣᠯ')
    def test_catalogue_is_pinned(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as tmp:
            p=Path(tmp)/'data.json';p.write_text(json.dumps(dict(version=1,sites=[data()])),encoding='utf8')
            with patch.dict(os.environ,{'BNE_PROPERTY_IDENTITIES':str(p)}):
                self.assertEqual(d.for_plan(site()).site_id,'source:s')
                p.write_text('{}',encoding='utf8')
                with self.assertRaises(RuntimeError): d.watch()
    def test_500_record_preparation(self):
        start=time.perf_counter()
        for i in range(500):
            p=d.plan(site(),data())
            text.prepare(p)
        self.assertEqual(len(p.tenants),2)
        print('500 plan + warm text preparations: %.3fs' % (time.perf_counter()-start))

if __name__=='__main__': unittest.main()
