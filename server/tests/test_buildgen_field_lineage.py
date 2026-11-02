"""Retained source level labels survive cache, ingest and worker boundaries."""
from dataclasses import FrozenInstanceError
import io
import os
from pathlib import Path
import pickle
import sys
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
import mapgeom
import overture
from buildgen import freeze_items
from buildgen.evidence import normalise_attributes
from test_buildgen_topology import FlatFrame, features, rect


def cached(feature):
    data=io.BytesIO()
    np.savez_compressed(data,**feature.to_arrays('f.'))
    data.seek(0)
    with np.load(data,allow_pickle=False) as archive:
        return mapgeom.Features.from_arrays(feature.layer,dict(archive),'f.')


class FieldLineageTests(unittest.TestCase):
    def tile(self,layers,**kwargs):
        with patch.dict(os.environ,{'BNE_BUILDING_GENERATOR':'v2'}):
            return b.tile_buildings(FlatFrame(),0.,0.,256.,256.,layers,
                                    lambda lat,lon:np.zeros(np.shape(lat)),**kwargs)

    def test_fields_already_have_numeric_feed_projections(self):
        for key in ('min_floor','num_floors_underground','level'):
            self.assertIn(key,overture.LAYERS['buildings']['float'])
            self.assertIn(key,overture.LAYERS['buildings']['cols'])
        self.assertIn('min_floor',overture.LAYERS['building_parts']['float'])

    def test_labels_survive_actual_cache_tile_and_frozen_worker_path(self):
        source=features([[(rect(10,10,20,15),)]],height=[12.],num_floors=[3.],
                        min_floor=[4.],num_floors_underground=[2.],level=[1.],
                        src_record=['way/verified-fixture'],**{'class':['office']})
        restored=cached(source)
        items=self.tile([restored])
        self.assertEqual(len(items),1)
        plan=pickle.loads(pickle.dumps(freeze_items(items)))[0][0]
        for key,value in (('min_floor',4.),('num_floors_underground',2.),('level',1.)):
            observed=plan.evidence.get(key)
            self.assertEqual((observed.status,observed.value,observed.source),
                             ('observed',value,'OpenStreetMap'))
        self.assertEqual(plan.evidence.source_record,'way/verified-fixture')
        self.assertEqual((plan.height,plan.floors),(12.,3))
        restored.attrs['min_floor'][0]=90.
        self.assertEqual(plan.evidence.get('min_floor').value,4.)
        with self.assertRaises(FrozenInstanceError):
            plan.evidence.get('level').value=99.

    def test_part_level_provenance_is_its_own_not_parent_label(self):
        parent=features([[(rect(0,0,60,60),)]],ids=['parent'],height=[20.],min_floor=[0.])
        part=features([[(rect(10,10,20,15),)]],ids=['part'],height=[20.],min_height=[8.],
                      num_floors=[3.],min_floor=[2.],building_id=['parent'])
        items=self.tile([cached(parent)],part_layers=[cached(part)])
        self.assertEqual(len(items),1)
        spec=items[0][0]
        self.assertEqual((spec.evidence.source_id,spec.evidence.parent_id),('part','parent'))
        self.assertEqual(spec.evidence.get('min_floor').value,2.)
        self.assertEqual(spec.evidence.get('level').status,'unknown')
        self.assertEqual((spec.height,spec.min_h),(12.,8.))

    def test_signed_labels_zero_count_and_unknown_remain_distinct(self):
        evidence=normalise_attributes({'min_floor':-1,'level':-.5,'num_floors_underground':0})
        self.assertEqual(evidence.get('min_floor').value,-1.)
        self.assertEqual(evidence.get('level').status,'observed')
        self.assertEqual(evidence.get('num_floors_underground').status,'observed')
        for value in (None,np.nan,''):
            self.assertEqual(normalise_attributes({'level':value}).get('level').status,'unknown')
        for value in (-1,float('inf'),'several',True):
            self.assertEqual(normalise_attributes({'num_floors_underground':value})
                             .get('num_floors_underground').status,'invalid')

    def test_old_cache_missing_fields_and_collapsed_booleans_are_not_observations(self):
        source=features([[(rect(10,10,20,15),)]],height=[12.])
        source.attrs['has_parts']=mapgeom.bool_column([None])
        source.attrs['is_underground']=mapgeom.bool_column([None])
        spec=self.tile([cached(source)])[0][0]
        for key in ('min_floor','num_floors_underground','level'):
            self.assertEqual(spec.evidence.get(key).status,'unknown')
        # Legacy bool columns conflate a missing observation with false. Do not
        # claim that they are known negatives until presence is retained upstream.
        for field in ('has_parts','is_underground'):
            observation=spec.evidence.get(field)
            self.assertEqual(observation.status,'unknown')
            self.assertIsNone(observation.value)
            self.assertIn('legacy cache',observation.reason)

    def test_level_metadata_does_not_create_new_physical_floor_geometry(self):
        source=features([[(rect(10,10,20,15),)]],height=[12.],num_floors=[3.],**{'class':['office']})
        before=self.tile([source])
        source.attrs.update(min_floor=np.array([5.]),level=np.array([2.]),
                            num_floors_underground=np.array([3.]))
        after=self.tile([source])
        for emitter in (b.build,b.collision_mesh,b._sky_mesh):
            for a,c in zip(emitter(before),emitter(after)):
                np.testing.assert_array_equal(a,c)


if __name__=='__main__':unittest.main()
