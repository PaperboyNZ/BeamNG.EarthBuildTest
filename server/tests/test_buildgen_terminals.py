"""Retained semantic evidence and fitted closed terminal shells."""
from pathlib import Path
import pickle
import sys
import unittest

import numpy as np
from shapely.geometry import Polygon

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import freeze_items, terminals, programme
from buildgen.topology import Footprint


def fixture(cls='airport_terminal', fp=None, seed='terminal', **attrs):
    fp = fp or Footprint(((0, 0), (40, 0), (40, 24), (0, 24)))
    values = dict(height=8., num_floors=1, roof_shape='flat', seed_id=seed, _footprint=fp)
    values.update(attrs)
    values['class'] = cls
    spec = b.plan(np.asarray(fp.outer), values)
    spec.gring = np.zeros(len(spec.ring))
    lo = np.min(fp.outer, axis=0); hi = np.max(fp.outer, axis=0)
    roads = [(np.array([(lo[0]-100., lo[1]-9.), (hi[0]+100., lo[1]-9.)]), 3., 'residential', False)]
    b.doors([(spec, 0., 0.)], roads, 0., 0., ground=lambda xy: np.zeros(len(xy)))
    return spec


class TerminalTests(unittest.TestCase):
    def test_keyword_false_positives_keep_observed_ordinary_use(self):
        for cls, name, use in [('hotel', 'Terminal Hotel', 'commercial'),
                               ('shop', 'Concourse Coffee', 'commercial'),
                               ('retail', 'Concourse Coffee', 'commercial'),
                               ('freight_terminal', 'Air Freight Terminal', 'industrial')]:
            with self.subTest(cls=cls):
                s = fixture(cls, name=name)
                self.assertFalse(s.terminal['accepted'])
                self.assertEqual(s.inference.use.value, use)
                self.assertNotIn('specialised_structure_legacy_recipe', s.diagnostics)
                self.assertEqual(s.inference.height.value, 8.)

    def test_generic_terminal_and_other_modes_do_not_become_airport(self):
        for cls in ('terminal', 'passenger_terminal', 'bus_station', 'ferry_terminal', 'train_station'):
            s = fixture(cls, name='International Terminal')
            self.assertFalse(s.terminal['accepted'])
            self.assertEqual(s.terminal['transport_mode'], 'unknown')

    def test_explicit_airport_class_and_subtype_select_distinct_families(self):
        hall = fixture()
        concourse = fixture('terminal', subtype='airport_concourse',
                            fp=Footprint(((0, 0), (80, 0), (80, 12), (0, 12))))
        self.assertEqual(hall.terminal['family'], 'terminal_regional_hall')
        self.assertEqual(concourse.terminal['family'], 'terminal_linear_concourse')
        for s in (hall, concourse):
            s.facades = freeze_items([(s, 0., 0.)])[0][0].facades
            roles = {e.role for e in s.facades.elevations}
            self.assertIn('terminal_public', roles)
            self.assertIn('terminal_service', roles)
            self.assertLessEqual(sum(len(e.openings) for e in s.facades.elevations), terminals.MAX_OPENINGS)
            for e in s.facades.elevations:
                for i, op in enumerate(e.openings):
                    self.assertGreaterEqual(op.left, 0)
                    self.assertLessEqual(op.right, e.length)
                    self.assertFalse(any(op.overlaps(other, .01) for other in e.openings[i+1:]))
        self.assertIn('terminal_hall', {e.role for e in concourse.facades.elevations})

    def test_source_topology_height_and_closed_collision_across_matrix(self):
        shapes = [Footprint(((0, 0), (40, 0), (40, 24), (0, 24))),
                  Footprint(((0, 0), (40, 0), (40, 12), (24, 12), (24, 24), (0, 24))),
                  Footprint(((0, 0), (40, 0), (40, 24), (0, 24)),
                            (((12, 8), (12, 16), (24, 16), (24, 8)),))]
        for fp in shapes:
            for seed in ('a', 'b', 'c'):
                s = fixture(fp=fp, seed=seed)
                frozen = freeze_items([(s, 0., 0.)])
                self.assertEqual(s.footprint, fp)
                self.assertEqual(s.inference.height.value, 8.)
                for mesh in (b.build(frozen), b.build(frozen, lite=True), b.collision_mesh(frozen)):
                    self.assertTrue(np.isfinite(mesh[0]).all())
                    self.assertGreater(len(mesh[2]), 0)
                collision = b.collision_mesh(frozen)
                roof = collision[0][collision[2]]
                roof = roof[np.ptp(roof[:, :, 2], axis=1) < 1e-7]
                allowed = Polygon(fp.outer, fp.holes)
                self.assertTrue(all(allowed.buffer(1e-7).covers(Polygon(t[:, :2])) for t in roof))

    def test_rebase_seed_and_worker_metadata(self):
        a = fixture(seed='stable')
        shifted = a.footprint.translated(400, -220)
        c = fixture(fp=shifted, seed='stable')
        self.assertEqual(a.terminal, c.terminal)
        frozen = freeze_items([(a, 0., 0.)])
        translated = freeze_items([(c, 0., 0.)])
        self.assertEqual(frozen[0][0].facades, translated[0][0].facades)
        restored = pickle.loads(pickle.dumps(frozen))
        for left, right in zip(b.build(frozen)[:4], b.build(restored)[:4]):
            np.testing.assert_array_equal(left, right)
        with self.assertRaises(TypeError):
            restored[0][0].terminal['family'] = 'changed'

    def test_large_or_special_roof_assembly_is_diagnosed(self):
        for attrs in ({'roof_shape': 'dome'}, {'height': 50}, {'num_floors': 8}):
            s = fixture(**attrs)
            self.assertFalse(s.terminal['accepted'])
            self.assertTrue(any('deferred' in d or 'fallback' in d for d in s.terminal['diagnostics']))

    def test_infrastructure_name_never_overrides_structure(self):
        fp = Footprint(((0, 0), (40, 0), (40, 24), (0, 24)))
        self.assertIsNone(terminals.classify({'class': 'bridge', 'name': 'Terminal Bridge'}, fp))
        self.assertIsNone(terminals.classify({'garage': True, 'name': 'Terminal Parking'}, fp))

    def test_masonry_bridge_is_protected_and_generic_transport_is_not_a_garage(self):
        fp = Footprint(((0, 0), (40, 0), (40, 24), (0, 24)))
        s = b.plan(np.asarray(fp.outer), dict(_footprint=fp, height=8., num_floors=1,
                   bridge_masonry=True, **{'class':'airport_terminal'}))
        self.assertIsNone(s.terminal)
        self.assertEqual(s.cls, 'bridge_pier')
        s = fixture('transportation', subtype='airport_terminal')
        self.assertTrue(s.terminal['accepted'])

    def test_keyword_does_not_replace_supported_pyramid(self):
        fp = Footprint(((0, 0), (40, 0), (40, 24), (0, 24)))
        s = b.plan(np.asarray(fp.outer), dict(_footprint=fp, height=20., roof_height=18.,
                   roof_shape='pyramidal', name='Terminal Exhibition', **{'class':'museum'}))
        self.assertIsNone(s.terminal)
        self.assertEqual(s.cls, 'pyramid')
        self.assertEqual(s.roof, 'hipped')

    def test_complete_source_controls_fragment_admission(self):
        source = Footprint(((0, 0), (160, 0), (160, 80), (0, 80)))
        full = fixture(fp=source)
        fragment = fixture(_planning_footprint=source)
        self.assertFalse(full.terminal['accepted'])
        self.assertEqual(full.terminal, fragment.terminal)

    def test_collinear_terminal_facades_share_one_grid_and_floor_datums(self):
        full=Footprint(((0,0),(40,0),(40,24),(0,24)))
        sampled=Footprint(((0,0),(10,0),(25,0),(40,0),(40,24),(0,24)))
        plans=[]
        for fp,door in ((full,(0,20.)),(sampled,(1,10.))):
            s=b.plan(np.asarray(fp.outer),dict(_footprint=fp,height=12.,num_floors=3,
                     seed_id='shared-terminal',roof_shape='flat',**{'class':'airport_terminal'}))
            s.gring=np.zeros(len(s.ring));s.door=door;s.front=door[0]
            plans.append(freeze_items([(s,0.,0.)])[0][0])
        def apertures(plan):
            shared=programme.derive(plan)
            return {(shared.run(e.boundary,e.edge).start,shared.run(e.boundary,e.edge).end):
                    tuple((o.kind,o.floor,o.left,o.right,o.bottom,o.top) for o in e.openings)
                    for e in plan.facades.elevations}
        self.assertEqual(apertures(plans[0]),apertures(plans[1]))
        shared=programme.derive(plans[1])
        self.assertEqual(len(plans[1].facades.elevations),4)
        public=next(e for e in plans[1].facades.elevations if e.role=='terminal_public')
        upper={round((o.left+o.right)/2,8) for o in public.openings if o.floor==1}
        ground={round((o.left+o.right)/2,8) for o in public.openings if o.floor==0 and o.kind!='door'}
        self.assertTrue(ground<=upper)
        for opening in public.openings:
            if opening.kind!='door':self.assertLessEqual(opening.top,shared.datum(opening.floor).top)

    def test_disabled_optional_programme_keeps_existing_shell_route(self):
        s=fixture()
        self.assertIsNone(terminals.openings(s,0,0,40.,0.,0.,(),programme=False))


if __name__ == '__main__':
    unittest.main()
