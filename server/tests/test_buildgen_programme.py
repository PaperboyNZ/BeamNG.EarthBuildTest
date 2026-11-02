"""Shared programme contracts constrain composition without inventing evidence."""
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import pickle
import sys
import unittest

import numpy as np
from shapely.geometry import LineString
from shapely.ops import unary_union

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import freeze_items, materials, programme
from buildgen.topology import Footprint


RECT=Footprint(((0,0),(24,0),(24,12),(0,12)))
SPLIT=Footprint(((0,0),(7,0),(15,0),(24,0),(24,12),(0,12)))


def spec(fp=RECT,**extra):
    attrs={'class':'office','height':12.,'num_floors':3,'roof_shape':'flat',
           'seed_id':'programme-owner','_footprint':fp}
    attrs.update(extra)
    return b.plan(np.asarray(fp.outer),attrs)


class ProgrammeTests(unittest.TestCase):
    def test_floor_datums_follow_actual_body_and_never_allocate_source_labels(self):
        original=spec()
        labelled=spec(min_floor=-2.,level=5.,num_floors_underground=3.)
        a,c=programme.derive(original),programme.derive(labelled)
        self.assertEqual([(d.bottom,d.top) for d in a.datums],[(0.,4.),(4.,8.),(8.,12.)])
        self.assertEqual(a.datums,c.datums)
        values={p.field:p for p in c.source_levels}
        self.assertEqual(values['min_floor'].value,-2.)
        self.assertEqual(values['level'].value,5.)
        self.assertEqual(values['num_floors_underground'].status,'observed')

    def test_clipped_floor_datums_stop_at_source_wall_top(self):
        resolved=freeze_items([(spec(),0.,0.)])[0][0]
        inconsistent=replace(resolved,height=5.5,floors=3,floor_h=3.)
        result=programme.derive(inconsistent)
        self.assertEqual([(d.bottom,d.top) for d in result.datums],[(0.,3.),(3.,5.5)])
        self.assertIn('resolved_floor_datums_clipped_to_actual_body',result.diagnostics)

    def test_church_spire_reservation_is_outside_floor_datums(self):
        church=spec(**{'class':'church','height':15.,'num_floors':1,'roof_shape':'gabled',
                       'roof_height':np.nan,'_church_spire':'square_broach'})
        self.assertIsNotNone(church.church.spire)
        result=programme.derive(church)
        self.assertEqual(result.datums[-1].top,church.height)
        self.assertLess(result.datums[-1].top,church.church.total_height)

    def test_era_structure_and_condition_remain_explicit_unknowns(self):
        result=programme.derive(spec(facade_material='stone',start_date='1890',building_age='historic'))
        self.assertEqual(result.function.value,'commercial')
        for fact in (result.structure,result.era,result.condition):
            self.assertIsNone(fact.value)
            self.assertEqual(fact.status,'unknown')
            self.assertIn('not_retained',fact.source)
        self.assertEqual(result.vocabulary.value,'stone')

    def test_semantic_channels_are_independent_and_legacy_bridge_is_exact(self):
        original=spec();result=programme.derive(original)
        channels=[result.seed(channel) for channel in programme.CHANNELS]
        self.assertEqual(len(set(channels)),5)
        self.assertEqual(result.seed('structure','bay'),programme.seed(original,'structure','bay'))
        self.assertNotEqual(result.seed('structure','bay'),result.seed('vocabulary','bay'))
        self.assertEqual(programme.legacy_seed(original,'structure','terminal-bay'),materials.unit(original.seed,'terminal-bay'))
        for channel in ('era','condition'):
            self.assertEqual(result.seed(channel),programme.derive(spec(facade_color='#987654')).seed(channel))

    def test_collinear_samples_merge_without_restarting_run_origin(self):
        a,c=programme.derive(spec()),programme.derive(spec(SPLIT))
        self.assertEqual([(r.start,r.end,r.length) for r in a.runs],[(r.start,r.end,r.length) for r in c.runs])
        bottom=c.run(0,0)
        self.assertIs(bottom,c.run(0,1));self.assertIs(bottom,c.run(0,2))
        self.assertEqual([(m.edge,m.start,m.end) for m in bottom.members],[(0,0.,7.),(1,7.,15.),(2,15.,24.)])
        self.assertEqual(bottom.locate(7.),(1,0.))
        self.assertEqual(bottom.locate(24.),(2,9.))

    def test_party_wall_boundary_is_a_real_grid_break(self):
        source=spec(SPLIT)
        result=programme.derive(source,party_walls=((0,1),))
        self.assertEqual(len(result.runs),6)
        self.assertTrue(result.run(0,1).party_wall)
        self.assertNotEqual(result.run(0,0),result.run(0,1))
        self.assertNotEqual(result.run(0,1),result.run(0,2))

    def test_omit_reservations_keep_one_complete_lattice(self):
        whole=programme.fit_grid(30.,4.,2.,margin=1.,gap=.3,mode='centered',reserved_mode='omit')
        blocked=programme.fit_grid(30.,4.,2.,margin=1.,gap=.3,mode='centered',reserved_mode='omit',reserved=((12.,17.),))
        self.assertTrue(blocked.bays)
        self.assertLess(len(blocked.bays),len(whole.bays))
        by_index={bay.index:bay for bay in whole.bays}
        self.assertTrue(all(bay==by_index[bay.index] for bay in blocked.bays))
        self.assertTrue(all(bay.right<=11.7 or bay.left>=17.3 for bay in blocked.bays))

    def test_free_span_reflow_respects_reservations_and_total_bay_cap(self):
        grid=programme.fit_grid(40.,3.,1.4,reserved=((8.,11.),(20.,22.),(32.,35.)),max_bays=1)
        self.assertEqual(len(grid.bays),1)
        capped=programme.fit_grid(1000.,1.,1.,gap=0.,max_bays=programme.MAX_BAYS)
        self.assertEqual(len(capped.bays),programme.MAX_BAYS)
        for bay in grid.bays:
            self.assertFalse(any(bay.left<high+.24 and bay.right>low-.24 for low,high in ((8,11),(20,22),(32,35))))

    def test_projected_members_reconstruct_whole_bays_without_phase_loss(self):
        run=programme.derive(spec(SPLIT)).run(0,0)
        grid=programme.fit_grid(run.length,4.,2.4,margin=.6,max_bays=12)
        reconstructed={}
        for member in run.members:
            projected=programme.project_grid(grid,run,member.edge)
            for bay in projected.bays:
                reconstructed.setdefault(bay.index,[]).append(LineString(((bay.left+member.start,0),(bay.right+member.start,0))))
        for bay in grid.bays:
            united=unary_union(reconstructed[bay.index])
            self.assertAlmostEqual(united.length,bay.right-bay.left)
            self.assertEqual(united.bounds,(bay.left,0.,bay.right,0.))

    def test_records_detach_mutable_inputs_and_roundtrip_as_pure_data(self):
        bays=[programme.Bay(0,1.,2.)]
        grid=programme.BayGrid(4.,bays)
        bays.clear();self.assertEqual(len(grid.bays),1)
        result=programme.derive(spec())
        restored=pickle.loads(pickle.dumps(result))
        self.assertEqual(result,restored)
        with self.assertRaises(FrozenInstanceError):restored.era.status='observed'
        from dataclasses import asdict
        json.dumps(asdict(result),allow_nan=False)

    def test_long_source_identity_is_bounded_without_losing_geometry(self):
        source=spec(seed_id='long-source-'+'x'*4096)
        result=programme.derive(source)
        self.assertEqual(result.identity[0][0],'hashed_source_id')
        self.assertLess(len(repr(result.identity)),150)
        self.assertEqual(result,programme.derive(pickle.loads(pickle.dumps(freeze_items([(source,0.,0.)])[0][0]))))
        self.assertTrue(np.isfinite(b.build(freeze_items([(source,0.,0.)]))[0]).all())

    def test_unsupported_inputs_are_rejected_without_unbounded_records(self):
        for kwargs in ({'length':float('nan')},{'max_bays':programme.MAX_BAYS+1},{'reserved':[(1.,2.)]*(programme.MAX_BAYS+1)},
                       {'reserved':((3.,1.),)},{'bay':False}):
            params=dict(length=20.,bay=3.,width=1.2);params.update(kwargs)
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):programme.fit_grid(**params)
        with self.assertRaises(ValueError):programme.seed(spec(),'structure',object())
        with self.assertRaises(ValueError):programme.derive(replace(freeze_items([(spec(),0.,0.)])[0][0],floors=121))


if __name__=='__main__':unittest.main()
