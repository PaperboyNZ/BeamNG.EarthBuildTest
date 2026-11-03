"""Sparse-data variety, contextual fit, terrain/party clearance and tier parity."""
from collections import Counter
from dataclasses import replace
from pathlib import Path
import pickle
import sys
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import commercial, commercial_forms as forms, facades, freeze_items
from buildgen.context import Context, Neighbour
from buildgen.evidence import normalise_attributes
from buildgen.topology import Footprint
from test_buildgen_facades import building


def neighbours(count, area, cls):
    return Context(neighbours=tuple(Neighbour(str(i),20.+i,area,
        normalise_attributes({'class':cls})) for i in range(count)))


def fixture(cls='industrial', seed='form', width=60., depth=25., height=6., floors=1,
            ctx=None, fp=None, ground=None, pid=None):
    s=building(width,depth,fp=fp,**{'class':cls,'height':height,'num_floors':floors,
        'roof_shape':'flat','facade_material':'concrete','seed_id':seed,'_context':ctx})
    if pid:
        from buildgen.presets import catalogue
        preset=next(p for p in catalogue() if p.id==pid)
        s.inference=replace(s.inference,selection=replace(s.inference.selection,preset=preset))
        s.windows=preset.windows;s.plain=not preset.windows
    ground=ground or (lambda p:np.zeros(len(p)))
    s.gring=ground(np.asarray(s.ring))
    lo,hi=float(s.gring.min()),float(s.gring.max())
    x,y=np.asarray(s.ring).min(axis=0)
    roads=[(np.array([(x-50,y-12),(x+width+50,y-12)]),3.,'residential',False)]
    b.doors([(s,lo,hi)],roads,0.,0.,ground=ground)
    if s.facades is None:s.facades=facades.plan(s,lo,hi)
    return s,lo,hi


class SparseCommercialTests(unittest.TestCase):
    def test_broad_tags_reach_all_eight_compositions_without_zones(self):
        for cls,expected in [('commercial',forms.COMMERCIAL),('industrial',forms.INDUSTRIAL),('factory',forms.INDUSTRIAL)]:
            selected=set();signatures=set();old_layout=0
            for seed in range(64):
                s,_,_=fixture(cls,str(seed))
                selected.add(s.inference.selection.preset.id)
                front=next(e for e in s.facades.elevations if e.edge==s.front and not e.boundary)
                signature=tuple(sorted(Counter(o.kind for o in front.openings).items()))
                signatures.add(signature)
                old_layout+=signature==(('door',1),('service',1))
                self.assertEqual(s.inference.use.value,'industrial' if cls=='factory' else cls)
                self.assertIn('sparse_use_architecture_v1',s.inference.selection.reasons)
            self.assertEqual(selected,set(expected))
            self.assertGreaterEqual(len(signatures),4)
            self.assertEqual(old_layout,0)

    def test_no_specific_tags_uses_observed_land_use_or_neighbours(self):
        for use in ('industrial','commercial'):
            for ctx in (Context(land_use=((use,1.),)),neighbours(4,800.,use)):
                ids={fixture('yes',str(i),ctx=ctx)[0].inference.selection.preset.id for i in range(48)}
                expected=forms.INDUSTRIAL if use=='industrial' else forms.COMMERCIAL
                self.assertEqual(ids,set(expected))
        unknown=fixture('yes')[0]
        self.assertEqual(unknown.inference.use.value,'unknown')
        self.assertNotIn(unknown.inference.selection.preset.id,forms.IDS)
        conflict=fixture('yes',ctx=Context(land_use=(('industrial',1.),('residential',1.))))[0]
        self.assertEqual(conflict.inference.use.value,'unknown')

    def test_footprint_and_surroundings_change_weights_and_selected_population(self):
        compact=Footprint(((0,0),(12,0),(12,10),(0,10)))
        broad=Footprint(((0,0),(60,0),(60,25),(0,25)))
        w,_=forms.weights('industrial',('industrial',''),compact,1,6.)
        v,_=forms.weights('industrial',('industrial',''),broad,1,6.)
        self.assertGreater(w[forms.INDUSTRIAL[2]],v[forms.INDUSTRIAL[2]])
        self.assertGreater(v[forms.INDUSTRIAL[0]],w[forms.INDUSTRIAL[0]])
        sparse=neighbours(3,100.,'commercial');dense=neighbours(16,200.,'commercial')
        a,_=forms.weights('commercial',('commercial',''),broad,1,6.,sparse)
        z,_=forms.weights('commercial',('commercial',''),broad,1,6.,dense)
        self.assertGreater(z[forms.COMMERCIAL[2]],a[forms.COMMERCIAL[2]])
        populations=[Counter(fixture('commercial',str(i),ctx=ctx)[0].inference.selection.preset.id
                             for i in range(64)) for ctx in (sparse,dense)]
        self.assertGreater(populations[1][forms.COMMERCIAL[2]],populations[0][forms.COMMERCIAL[2]])
        low,_=forms.weights('industrial',('industrial',''),broad,1,3.)
        self.assertNotIn(forms.INDUSTRIAL[1],low)
        self.assertNotIn(forms.INDUSTRIAL[0],low)

    def test_specific_classes_and_mapped_envelopes_remain_authoritative(self):
        for cls,pid in [('warehouse','ci_logistics_hall'),('workshop','ci_trade_units'),
                        ('supermarket','ci_supermarket'),('retail','ci_strip_shops'),('office','office'),('hotel','hotel')]:
            s,_,_=fixture(cls)
            self.assertEqual(s.inference.selection.preset.id,pid)
        s,_,_=fixture('industrial',height=12.,floors=3)
        self.assertEqual((s.height,s.floors,s.roof),(12.,3,'flat'))
        self.assertEqual(s.inference.facade.value,'concrete')
        self.assertEqual(s.evidence.get('class').value,'industrial')

    def test_all_layouts_fit_narrow_collinear_irregular_and_courtyard_envelopes(self):
        shapes=[Footprint(((0,0),(8,0),(8,12),(0,12))),
                Footprint(((0,0),(15,0),(60,0),(60,25),(0,25))),
                Footprint(((0,0),(40,0),(40,12),(15,12),(15,30),(0,30))),
                Footprint(((0,0),(60,0),(60,40),(0,40)),(((15,12),(45,12),(45,28),(15,28)),))]
        for pid in forms.IDS:
            for fp in shapes:
                s,_,_=fixture('commercial' if pid in forms.COMMERCIAL else 'industrial',fp=fp,pid=pid)
                for e in s.facades.elevations:
                    for i,o in enumerate(e.openings):
                        self.assertGreaterEqual(o.left,.45)
                        self.assertLessEqual(o.right,e.length-.45)
                        self.assertGreater(o.top,o.bottom)
                        self.assertLessEqual(o.top,s.height)
                        self.assertTrue(all(not o.overlaps(p,.15) for p in e.openings[i+1:]))
                    if e.boundary:self.assertFalse(e.openings)

    def test_missing_terrain_grade_and_neighbour_walls_suppress_service_openings(self):
        for pid in forms.INDUSTRIAL[:3]:
            for ground in (lambda p:p[:,0]*.2,lambda p:np.full(len(p),np.nan)):
                s,_,_=fixture(pid=pid,ground=ground)
                self.assertFalse(any(o.kind=='service' for e in s.facades.elevations for o in e.openings))
            s,lo,hi=fixture(pid=pid)
            wall=building(fp=Footprint(((0,-1),(60,-1),(60,-.01),(0,-.01))),**{'class':'industrial','height':6.})
            commercial.resolve([(s,lo,hi),(wall,0.,0.)],[],lambda p:np.zeros(len(p)),0.,0.)
            self.assertFalse(any(o.kind=='service' for e in s.facades.elevations for o in e.openings))
        s=building(60,25,**{'class':'industrial','height':6.})
        layout=facades.plan(s,0.,0.)
        self.assertFalse(any(o.kind=='service' for e in layout.elevations for o in e.openings))

    def test_roundtrip_translation_meshes_and_collision_preserve_shared_plan(self):
        for pid in forms.IDS:
            cls='commercial' if pid in forms.COMMERCIAL else 'industrial'
            item=fixture(cls,pid=pid)
            s=item[0]
            shifted=fixture(cls,pid=pid,fp=s.footprint.translated(1000.,-500.))[0]
            self.assertEqual(s.inference.selection,shifted.inference.selection)
            self.assertEqual(s.facades,shifted.facades)
            frozen=pickle.loads(pickle.dumps(freeze_items([item])))
            self.assertEqual(frozen[0][0].facades,s.facades)
            for lite in (False,True):
                mesh=b.build(frozen,lite=lite)
                self.assertTrue(np.isfinite(mesh[0]).all())
                triangles=mesh[0][mesh[2]]
                area=np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]),axis=1)
                self.assertTrue((area>1e-9).all())
            self.assertTrue(np.isfinite(b.collision_mesh(frozen)[0]).all())

    def test_giant_and_many_storey_buildings_have_bounded_opening_work(self):
        for cls in ('commercial','industrial'):
            for floors in (1,12):
                for i in range(8):
                    s,_,_=fixture(cls,str(i),width=1000.,depth=400.,height=6.*floors,floors=floors)
                    total=sum(len(e.openings) for e in s.facades.elevations)
                    self.assertLessEqual(total,commercial.MAX_ARCHITECTURE_OPENINGS+1)
                    self.assertTrue(all(len(e.openings)<=commercial.MAX_OPENINGS for e in s.facades.elevations))

    def test_new_catalogue_and_solver_participate_in_cache_and_package_identity(self):
        import codefiles
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
        import package
        for name in ('buildgen/commercial_forms.py','buildgen/catalog/commercial_forms.json'):
            self.assertIn(name,codefiles.source_files(Path(__file__).resolve().parents[1]))
            self.assertIn('server/'+name,package.collect())


if __name__=='__main__':unittest.main()
