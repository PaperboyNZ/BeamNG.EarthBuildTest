"""Commercial fit, evidence, terrain, determinism and shared-engine regressions."""
import hashlib
import json
from pathlib import Path
import pickle
import sys
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import commercial, facades, freeze_items, presets
from buildgen.topology import Footprint
from test_buildgen_facades import building, road


def fixture(cls='warehouse',width=60.,depth=25.,seed='commercial',ground=None,fp=None):
    s=building(width,depth,fp=fp,**{'class':cls,'height':6.,'roof_shape':'flat',
                                  'seed_id':seed,'facade_material':'concrete'})
    g=ground or (lambda xy:np.zeros(len(xy)))
    s.gring=g(np.asarray(s.ring))
    low,high=float(s.gring.min()),float(s.gring.max())
    streets=[(np.array([(-50.,-12.),(width+50.,-12.)]),3.,'residential',False)]
    b.doors([(s,low,high)],streets,0.,0.,ground=g)
    return s,low,high


class CommercialTests(unittest.TestCase):
    def test_specific_classes_select_dedicated_presets_not_generic_land_use(self):
        for cls,pid in [('warehouse','ci_logistics_hall'),('supermarket','ci_supermarket'),('workshop','ci_trade_units')]:
            self.assertEqual(fixture(cls)[0].inference.selection.preset.id,pid)
        for cls in ('industrial','commercial','hangar','mall'):
            self.assertNotIn(fixture(cls)[0].inference.selection.preset.id,commercial.IDS)
        self.assertEqual(fixture('workshop',12,10)[0].inference.selection.preset.id,'workshop')

    def test_function_is_legible_on_same_footprint(self):
        counts={}
        for cls in ('warehouse','supermarket','workshop'):
            s,_,_=fixture(cls)
            ops=[o for e in s.facades.elevations for o in e.openings]
            counts[cls]={k:sum(o.kind==k for o in ops) for k in ('service','staff_door','storefront','office')}
            self.assertTrue(all(not e.openings for e in s.facades.elevations if e.edge!=s.front))
        self.assertGreater(counts['warehouse']['service'],2)
        self.assertGreater(counts['warehouse']['office'],0)
        self.assertGreaterEqual(counts['supermarket']['storefront'],2)
        self.assertEqual(counts['supermarket']['service'],0)
        self.assertGreater(counts['workshop']['staff_door'],1)
        self.assertGreater(counts['workshop']['service'],1)

    def test_dimensions_fit_and_no_openings_overlap_over_varied_widths_and_seeds(self):
        signatures=set()
        for width in (14.,27.,45.,80.,1000.):
            for seed in range(4):
                for cls in ('warehouse','supermarket','workshop'):
                    s,_,_=fixture(cls,width,25,seed=str(seed))
                    for e in s.facades.elevations:
                        self.assertLessEqual(len(e.openings),commercial.MAX_OPENINGS)
                        for i,o in enumerate(e.openings):
                            self.assertGreaterEqual(o.left,.45)
                            self.assertLessEqual(o.right,e.length-.45)
                            self.assertGreater(o.top,o.bottom)
                            self.assertLessEqual(o.top,s.height)
                            self.assertTrue(all(not o.overlaps(p,.15) for p in e.openings[i+1:]))
                    if width==80. and cls=='warehouse':
                        signatures.add(repr(s.facades.elevations))
        self.assertGreater(len(signatures),2)

    def test_steep_or_missing_terrain_omits_service_openings(self):
        for ground in (lambda xy:xy[:,0]*.2,lambda xy:np.full(len(xy),np.nan)):
            s=building(60,25,**{'class':'warehouse','height':6,'seed_id':'steep','roof_shape':'flat'})
            b.doors([(s,0.,0.)],road(),0.,0.,ground=ground)
            self.assertFalse(any(o.kind=='service' for e in s.facades.elevations for o in e.openings))
            self.assertTrue(s.facades.diagnostics)

    def test_neighbour_suppresses_hidden_openings(self):
        s,low,high=fixture()
        wall=Footprint(((0,-1),(60,-1),(60,-.01),(0,-.01)))
        neighbour=building(fp=wall,**{'class':'industrial','height':6})
        commercial.resolve([(s,low,high),(neighbour,0.,0.)],road(),lambda xy:np.zeros(len(xy)),0.,0.)
        self.assertFalse(any(o.kind=='service' for e in s.facades.elevations for o in e.openings))
        self.assertIn('ci_opening_omitted_obstruction',s.facades.diagnostics)

    def test_terrain_work_is_one_batch_bounded_by_openings(self):
        s,low,high=fixture('workshop',1000,100)
        calls=[]
        def ground(xy):
            calls.append(len(xy))
            return np.zeros(len(xy))
        commercial.resolve([(s,low,high)],road(),ground,0.,0.)
        self.assertEqual(len(calls),1)
        self.assertLessEqual(calls[0],commercial.MAX_OPENINGS*6)

    def test_roundtrip_and_mesh_tiers_preserve_layout_and_shell(self):
        for cls in ('warehouse','supermarket','workshop'):
            item=fixture(cls)
            frozen=freeze_items([item])
            copied=pickle.loads(pickle.dumps(frozen))
            self.assertEqual(frozen[0][0].facades,copied[0][0].facades)
            for lite in (False,True):
                mesh=b.build(copied,lite=lite)
                self.assertTrue(np.isfinite(mesh[0]).all())
                triangles=mesh[0][mesh[2]]
                self.assertTrue((np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]),axis=1)>1e-9).all())
            collision=b.collision_mesh(copied)
            self.assertTrue(np.isfinite(collision[0]).all())
            self.assertEqual(item[0].footprint,frozen[0][0].footprint)

    def test_no_frontage_no_invented_loading(self):
        s=building(60,25,**{'class':'warehouse','height':6,'roof_shape':'flat'})
        layout=facades.plan(s,0.,0.)
        self.assertFalse(any(e.openings for e in layout.elevations))

    def test_repeated_resolution_does_not_accumulate_or_hide_thresholds(self):
        s,lo,hi=fixture('workshop')
        facade,access=s.facades,s.access
        commercial.resolve([(s,lo,hi)],road(),lambda xy:np.zeros(len(xy)),0.,0.)
        self.assertEqual(s.facades,facade)
        self.assertEqual(s.access,access)

    def test_supermarket_has_mesh_entry_and_matching_wide_threshold(self):
        s,_,_=fixture('supermarket')
        entry=next(o for e in s.facades.elevations for o in e.openings if o.kind=='public_entry')
        threshold=next(v for v in s.access.solids if v.kind=='threshold')
        self.assertAlmostEqual(entry.right-entry.left,3.2)
        self.assertGreater(np.linalg.norm(np.subtract(threshold.top[0][:2],threshold.top[3][:2])),3.2)
        props=b.doors([(s,0.,0.)],road(),0.,0.,ground=lambda xy:np.zeros(len(xy)))
        self.assertFalse(any(p[0]=='door' for p in props))

    def test_translation_keeps_relative_appearance(self):
        original,_,_=fixture('workshop')
        offset=np.array([1234.,-500.])
        fp=original.footprint.translated(*offset)
        shifted=building(fp=fp,**{'class':'workshop','height':6.,'roof_shape':'flat',
                                'seed_id':'commercial','facade_material':'concrete'})
        shifted.gring=np.zeros(len(shifted.ring))
        streets=[(line[0]+offset,*line[1:]) for line in road()]
        b.doors([(shifted,0.,0.)],streets,0.,0.,ground=lambda xy:np.zeros(len(xy)))
        self.assertEqual(shifted.facades,original.facades)

    def test_new_catalogue_and_module_ship_and_invalidate_source_hash(self):
        import codefiles
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
        import package
        for rel in ('buildgen/commercial.py','buildgen/catalog/commercial.json'):
            self.assertIn(rel,codefiles.source_files(Path(__file__).resolve().parents[1]))
            self.assertIn('server/'+rel,package.collect())


if __name__=='__main__':
    unittest.main()
