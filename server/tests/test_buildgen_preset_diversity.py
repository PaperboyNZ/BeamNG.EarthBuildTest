"""Same-shell neighbourhoods must vary in geometry, not just paint or glass."""
import copy
import pickle
import unittest

import numpy as np

from test_buildgen_regions import building
from test_buildgen_facades import building as generic_building
from test_buildgen_regional_blocks import building as block_building, fingerprint
import buildings as b
from buildgen import facades, freeze_items, regional_architecture as regional, regional_blocks as blocks
from buildgen.topology import Footprint


def signature(layout):
    # Two-centimetre quantisation: microscopic noise and random pane colours do
    # not qualify as a distinct architectural composition.
    return tuple((e.boundary,e.edge,tuple((o.kind,o.floor,*(
        round(v/.02) for v in (o.left,o.right,o.bottom,o.top)))
        for o in e.openings)) for e in layout.elevations)


def centres(layout):
    return tuple(tuple(round((o.left+o.right)/.04) for o in e.openings
                       if o.kind=='window' and o.floor==1) for e in layout.elevations)


class PresetDiversityTests(unittest.TestCase):
    def assert_safe(self,spec,layout):
        for e in layout.elevations:
            for i,op in enumerate(e.openings):
                self.assertGreaterEqual(op.left,facades.CORNER_MARGIN-1e-8)
                self.assertLessEqual(op.right,e.length-facades.CORNER_MARGIN+1e-8)
                self.assertGreaterEqual(op.bottom,0.)
                self.assertLessEqual(op.top,spec.height)
                self.assertFalse(any(op.overlaps(other,.08) for other in e.openings[i+1:]))
            for floor in range(int(spec.floors)):
                windows=[o for o in e.openings if o.kind=='window' and o.floor==floor]
                if windows:
                    self.assertEqual(len({round(o.top,8) for o in windows}),1)

    def test_every_region_varies_same_shells_even_with_identical_observed_materials(self):
        catalogue=copy.deepcopy(regional.catalogue())
        for theme in catalogue:
            shapes=set();rhythms=set()
            for i in range(16):
                spec=building(theme,seed=f'diversity-{i}',roof_shape='flat',
                              facade_material='render',facade_color='#ccccbb')
                before=(spec.footprint,spec.height,spec.floors,spec.roof,spec.facade,spec.door)
                layout=facades.plan(spec,0.,0.)
                with self.subTest(theme=theme,seed=i):
                    self.assert_safe(spec,layout)
                    self.assertEqual(layout,facades.plan(spec,0.,0.))
                    self.assertEqual(before,(spec.footprint,spec.height,spec.floors,spec.roof,spec.facade,spec.door))
                    self.assertEqual(spec.facade,b.custom_look(b.STUCCO,b.parse_color('#ccccbb')))
                shapes.add(signature(layout));rhythms.add(centres(layout))
            with self.subTest(theme=theme):
                self.assertGreaterEqual(len(shapes),15)
                self.assertGreaterEqual(len(rhythms),12)
        self.assertEqual(catalogue,regional.catalogue())

    def test_each_of_the_192_block_presets_varies_within_its_own_design(self):
        for theme,rows in blocks.catalogue().items():
            shapes={p['id']:set() for p in rows}
            for i in range(80):
                spec=block_building(theme,seed=f'diversity-block-{i}')
                p=blocks.profile(spec)
                shapes[p['id']].add(signature(facades.plan(spec,0.,0.)))
                if all(len(values)>=8 for values in shapes.values()):break
            for preset,values in shapes.items():
                with self.subTest(preset=preset):self.assertGreaterEqual(len(values),8)

    def test_unlocated_generic_preset_varies_without_changing_preset_or_source(self):
        shapes=set();presets=set()
        for i in range(16):
            spec=generic_building(seed_id=f'generic-diversity-{i}',height=8.,num_floors=2,
                                  roof_shape='flat',facade_material='render',facade_color='#ccccbb')
            spec.front=0;spec.door=(0,2.3)
            presets.add(spec.inference.selection.preset.id)
            layout=facades.plan(spec,0.,0.);self.assert_safe(spec,layout)
            shapes.add(signature(layout))
        self.assertEqual(len(presets),1)
        self.assertGreaterEqual(len(shapes),15)

    def test_varied_bays_keep_clearances_on_narrow_irregular_and_garage_frontages(self):
        footprints=(Footprint(((0.,0.),(5.,0.),(5.,15.),(0.,15.))),
                    Footprint(((0.,0.),(14.,0.),(14.,7.),(7.,7.),(7.,12.),(0.,12.))))
        for theme in regional.catalogue():
            for index in range(4):
                for fp in footprints:
                    spec=building(theme,fp=fp,seed=f'clearance-{index}',height=6.,num_floors=2)
                    if fp is footprints[1]:spec.garage_opening=(0,8.,4.8,2.3)
                    with self.subTest(theme=theme,seed=index,width=fp.outer[1][0]):
                        self.assert_safe(spec,facades.plan(spec,0.,0.))

    def test_fallback_wall_zones_use_more_than_the_first_regional_paint(self):
        colours=set()
        for i in range(32):
            spec=building('italy_regional',seed=f'paint-{i}')
            if spec.inference.house_style.variant!='regional':
                continue  # this assertion isolates regional wall-zone palettes
            p=regional.for_spec(spec)
            # Inspect the ordinary fallback render zones, independent of which
            # cladding family this particular source identity inferred.
            p=dict(p,base_material='render',upper_material='render')
            mats=b._Looks(spec.seed)
            colours.add(regional.wall_materials(spec,p,mats,mats[spec.facade])[1])
        self.assertGreaterEqual(len(colours),3)

    def test_reloads_translation_and_mesh_tiers_do_not_reroll_architecture(self):
        for theme in ('nz_temperate','alpine','italy_regional','jp_temperate'):
            for i in range(3):
                spec=building(theme,seed=f'stable-diversity-{i}')
                moved=building(theme,seed=f'stable-diversity-{i}',fp=spec.footprint.translated(1000,-300))
                item=freeze_items([(spec,0.,0.)])[0]
                reloaded=pickle.loads(pickle.dumps(item))
                self.assertEqual(item[0].facades,facades.plan(moved,0.,0.))
                self.assertEqual(regional.for_spec(spec),regional.for_spec(reloaded[0]))
                for lite in (False,True):
                    mesh=b.build([item],lite=lite)
                    self.assertTrue(np.isfinite(mesh[0]).all())
                    self.assertEqual(fingerprint(mesh),fingerprint(b.build([reloaded],lite=lite)))
                self.assertEqual(fingerprint(b.collision_mesh([item])),fingerprint(b.collision_mesh([reloaded])))


if __name__=='__main__':unittest.main()
