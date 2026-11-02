"""Shared composition changes cannot move access or physical source envelopes."""
from pathlib import Path
import pickle
import sys
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import freeze_items
from buildgen import programme
from test_buildgen_facades import building, road


CASES=(
    ('office_punched',{'class':'office','facade_material':'brick','height':12.,'num_floors':3}),
    ('office_ribbon',{'class':'office','facade_material':'concrete','height':12.,'num_floors':3}),
    ('office_curtain',{'class':'office','facade_material':'glass','height':12.,'num_floors':3}),
    ('strip',{'class':'retail','height':6.,'num_floors':1}),
    ('trade',{'class':'industrial','height':6.,'num_floors':1}),
    ('church',{'class':'church','height':15.,'num_floors':1,'_church_spire':'square_broach'}),
    ('terminal',{'class':'airport_terminal','height':12.,'num_floors':3}),
)


def scene(attrs,**extra):
    s=building(30.,20.,**dict(attrs,seed_id='foundation-integration',**extra))
    props=b.doors([(s,0.,0.)],road(),0.,0.,ground=lambda xy:np.zeros(len(xy)))
    return s,props,freeze_items([(s,0.,0.)])


class FoundationIntegrationTests(unittest.TestCase):
    def test_palette_only_changes_leave_ports_plans_and_mesh_geometry_fixed(self):
        for label,attrs in CASES:
            with self.subTest(label=label):
                a,props_a,items_a=scene(attrs,facade_color='#887766',roof_color='#554433')
                c,props_c,items_c=scene(attrs,facade_color='#ccbb99',roof_color='#334455')
                self.assertEqual(a.door,c.door)
                self.assertEqual(a.garage_opening,c.garage_opening)
                self.assertEqual(a.access,c.access)
                self.assertEqual(props_a,props_c)
                pa,pc=programme.derive(items_a[0][0]),programme.derive(items_c[0][0])
                self.assertEqual(pa.datums,pc.datums)
                self.assertEqual(pa.runs,pc.runs)
                for channel in programme.CHANNELS:
                    self.assertEqual(pa.seed(channel),pc.seed(channel))
                for emit in (b.build,lambda items:b.build(items,lite=True),b.collision_mesh):
                    left,right=emit(items_a),emit(items_c)
                    for index in (0,1,2):
                        np.testing.assert_array_equal(left[index],right[index])

    def test_source_floor_labels_never_raise_the_roof_or_create_basements(self):
        for label,attrs in CASES:
            with self.subTest(label=label):
                a,_,ia=scene(attrs)
                c,_,ic=scene(attrs,min_floor=6.,level=2.,num_floors_underground=3.)
                self.assertEqual((a.height,a.floor_h,a.floors,a.min_h),(c.height,c.floor_h,c.floors,c.min_h))
                self.assertEqual(programme.derive(ia[0][0]).datums,programme.derive(ic[0][0]).datums)
                for x,y in zip(b.collision_mesh(ia),b.collision_mesh(ic)):
                    np.testing.assert_array_equal(x,y)

    def test_worker_roundtrip_has_same_architecture_and_shared_geometry(self):
        for label,attrs in CASES:
            with self.subTest(label=label):
                _,_,original=scene(attrs)
                restored=pickle.loads(pickle.dumps(original))
                self.assertEqual(programme.derive(original[0][0]),programme.derive(restored[0][0]))
                for emit in (b.build,lambda items:b.build(items,lite=True),b.collision_mesh,b._sky_mesh):
                    for x,y in zip(emit(original),emit(restored)):
                        np.testing.assert_array_equal(x,y)


if __name__=='__main__':unittest.main()
