"""Colour precedence, spatial sampling safety, stale evidence and cache identity."""
from pathlib import Path
from dataclasses import replace
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from shapely.geometry import Polygon, box
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
import revisit
from buildgen import roof_colours, ingest, BuildingPlan
from buildgen.context import Context
from buildgen.roof_sampling import sample, lab
from test_buildgen_inference import planned
from test_buildgen_context import geographic, rect


class Pixels:
    def __init__(self, data): self.data=data; self.count=0
    def pixels(self,source,z,x,y):
        self.count=len(x)
        return self.data[y,x]


class RoofColourTests(unittest.TestCase):
    def test_external_evidence_changes_generated_cache_identity(self):
        from buildgen import zones
        with patch.dict(os.environ,{'BNE_BUILDING_GENERATOR':'v2'}), patch.object(revisit,'_code',[]):
            keys=[]
            for roof,zone in (('roof1','zone1'),('roof2','zone1'),('roof2','zone2')):
                revisit._code.clear()
                with patch.object(roof_colours,'catalogue',return_value=(roof,{})), \
                     patch.object(zones,'catalogue',return_value=(zone,(),None)):
                    keys.append(revisit.code_key())
            self.assertEqual(len(set(keys)),3)

    def test_imagery_wins_and_raw_mapped_evidence_is_preserved(self):
        measured=roof_colours.Sample((.2,.3,.4),'fixture','geometry','image',1.)
        spec=planned({'class':'house','roof_color':'#ff0000'},Context(roof_colour=measured))
        self.assertEqual(spec.inference.roof_colour.value,measured.rgb)
        self.assertEqual(b.LOOKS[spec.roof_mat][1],measured.rgb)
        self.assertEqual(spec.evidence.get('roof_color').value,'#ff0000')
        self.assertEqual(BuildingPlan.from_spec(spec).inference.roof_colour,spec.inference.roof_colour)

    def test_mapped_then_palette_fallback(self):
        self.assertEqual(planned({'roof_color':'#123'}).inference.roof_colour.source,'mapped:roof_color')
        self.assertEqual(planned({'roof_color':'bogus'}).inference.roof_colour.source,'material_palette')

    def test_eroded_mask_excludes_yard_and_courtyard(self):
        data=np.full((64,64,3),(20,170,20),np.uint8)
        data[10:50,10:50]=(120,90,80)
        data[22:38,22:38]=(10,180,10)
        poly=Polygon([(10,10),(50,10),(50,50),(10,50)], [[(22,22),(38,22),(38,38),(22,38)]])
        result=sample(poly,1.,Pixels(data),'test',17)
        self.assertEqual(result['status'],'accepted')
        self.assertEqual(result['rgb'],[120.,90.,80.])

    def test_coarse_tiny_dark_green_and_mixed_are_rejected(self):
        p=box(2,2,50,50)
        self.assertEqual(sample(p,10.,Pixels(None),'test',14)['status'],'coarse_imagery')
        self.assertNotEqual(sample(box(1,1,3,3),1.,Pixels(None),'test',17)['status'],'accepted')
        for rgb in ((5,5,5),(10,190,10)):
            self.assertNotEqual(sample(p,1.,Pixels(np.full((64,64,3),rgb,dtype=np.uint8)),'test',17)['status'],'accepted')
        data=np.full((64,64,3),(200,50,40),np.uint8);data[:,25:]=(50,60,210)
        self.assertEqual(sample(p,1.,Pixels(data),'test',17)['status'],'mixed_colour')

    def test_reference_lab_and_bounded_pixel_work(self):
        np.testing.assert_allclose(lab([255,255,255]),[100,0,0],atol=1e-3)
        np.testing.assert_allclose(lab([0,0,0]),[0,0,0],atol=1e-6)
        pixels=Pixels(np.full((1024,1024,3),120,np.uint8))
        sample(box(0,0,1000,1000),1.,pixels,'test',17)
        self.assertLessEqual(pixels.count,4096)

    def test_catalogue_rejects_bad_quality_and_stale_geometry(self):
        f=geographic([[[rect(0,0,20,10)]]],['B1'])
        cc=ingest.components(f,0)
        row=dict(source_id='B1',geometry_digest=roof_colours.geometry_digest(cc),imagery_digest='hash',
                 source='fixture',mpp=1.,status='accepted',pixels=50,usable_share=.9,spread_de76_p80=4.,rgb=[100,110,120])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'roofs.json'
            path.write_text(json.dumps(dict(schema=1,method='eroded-roof-v1',records=[row])))
            with patch.dict(os.environ,{'BNE_BUILDING_ROOF_COLOURS':str(path)}):
                roof_colours.catalogue.cache_clear()
                try:
                    self.assertIsNotNone(roof_colours.query('B1',cc))
                    changed=geographic([[[rect(0,0,21,10)]]],['B1'])
                    self.assertIsNone(roof_colours.query('B1',ingest.components(changed,0)))
                finally: roof_colours.catalogue.cache_clear()
            row['mpp']=10.
            path.write_text(json.dumps(dict(schema=1,method='eroded-roof-v1',records=[row])))
            with self.assertRaises(ValueError):roof_colours.load(path)


if __name__=='__main__':unittest.main()
