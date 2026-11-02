"""All 192 block designs: composition, clearance, determinism and exclusions."""
from dataclasses import replace
from pathlib import Path
import json
import math
import pickle
import sys
import unittest
from unittest.mock import patch

import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import freeze_items
from buildgen import facades, regional_blocks as blocks
from buildgen.context import Context
from buildgen.topology import Footprint
from buildgen.zones import Zone


def building(theme='nz_temperate',seed='block',width=36.,depth=24.,floors=6,**extra):
    fp=extra.pop('_footprint',Footprint(((0.,0.),(width,0.),(width,depth),(0.,depth))))
    zone=Zone('block-test','v1','test','R','statutory',('residential','commercial','civic','unknown'),1.,region=theme)
    attrs=dict(_footprint=fp,_context=Context(zones=(zone,)),seed_id=seed,
               **{'class':'apartments','height':floors*3.,'num_floors':floors,'roof_shape':'flat'})
    attrs.update(extra)
    spec=b.plan(np.asarray(fp.outer),attrs)
    spec.gring=np.zeros(len(spec.ring));spec.front=0;spec.door=(0,5.1)
    return spec


def variants(theme):
    found={}
    for i in range(64):
        spec=building(theme,f'block-variant-{i}')
        p=blocks.profile(spec)
        if p:found.setdefault(p['id'],spec)
        if len(found)==3:return [found[p['id']] for p in blocks.catalogue()[theme]]
    raise AssertionError(f'Not all variants selectable: {theme}: {list(found)}')


def fingerprint(mesh):
    import hashlib
    h=hashlib.sha256()
    for i in (0,1,2,3,5):h.update(np.asarray(mesh[i]).tobytes())
    return h.hexdigest()


class RegionalBlockTests(unittest.TestCase):
    def test_catalogue_covers_exactly_the_approved_192_proposals(self):
        proposals=json.loads((Path(__file__).resolve().parents[2]/'docs/regional-block-proposals.json').read_text(encoding='utf-8'))
        self.assertEqual(set(blocks.catalogue()),{r['id'] for r in proposals['regions']})
        self.assertEqual({p['id'] for rows in blocks.catalogue().values() for p in rows},
                         {p['id'] for r in proposals['regions'] for p in r['proposals']})

    def test_all_192_select_compile_and_have_distinct_meshes(self):
        signatures=set()
        for theme in blocks.catalogue():
            for spec in variants(theme):
                p=blocks.profile(spec)
                with self.subTest(proposal=p['id']):
                    item=freeze_items([(spec,0.,0.)])[0]
                    self.assertIn('regional_block:'+p['id'],item[0].facades.diagnostics)
                    self.assertEqual(item[0].facades,pickle.loads(pickle.dumps(item[0])).facades)
                    for lite in (False,True):
                        mesh=b.build([item],lite=lite)
                        self.assertTrue(np.isfinite(mesh[0]).all())
                        self.assertTrue(np.isfinite(mesh[1]).all())
                        self.assertLess(int(mesh[2].max()),len(mesh[0]))
                        if not lite:signatures.add(fingerprint(mesh))
                    old_collision=fingerprint(b.collision_mesh([item]))
                    with patch.object(blocks,'profile',return_value=None):
                        self.assertEqual(old_collision,fingerprint(b.collision_mesh([item])))
        self.assertEqual(len(signatures),192)

    def test_windows_are_proportional_irregular_grouped_and_clear_of_entries(self):
        for theme in blocks.catalogue():
            for spec in variants(theme):
                p=blocks.profile(spec);layout=facades.plan(spec,0.,0.)
                total=0;components=0
                for e in layout.elevations:
                    windows=[o for o in e.openings if o.kind in ('window','office','storefront')]
                    total+=len(windows)
                    for i,o in enumerate(e.openings):
                        self.assertGreaterEqual(o.left,.45)
                        self.assertLessEqual(o.right,e.length-.45)
                        self.assertLessEqual(o.top,spec.height)
                        self.assertFalse(any(o.overlaps(other,.08) for other in e.openings[i+1:]))
                    for o in windows:
                        self.assertLessEqual((o.right-o.left)/o.columns,1.9)
                        self.assertLessEqual(o.top-o.bottom,spec.floor_h*.68)
                    if windows:
                        # Typical opening area stays restrained, not an all-glass wall.
                        ratio=sum((o.right-o.left)*(o.top-o.bottom) for o in windows)/(e.length*spec.height)
                        self.assertLess(ratio,.40)
                    first=[o for o in windows if o.floor==1]
                    second=[o for o in windows if o.floor==2]
                    self.assertEqual([(o.left,o.right) for o in first],[(o.left,o.right) for o in second])
                    if len(first)>3:
                        centres=[(o.left+o.right)/2 for o in first]
                        gaps=[c-a for a,c in zip(centres,centres[1:])]
                        self.assertGreater(max(gaps)-min(gaps),.05)
                    rows=blocks.components(spec,p,e,blocks.MAX_COMPONENTS-components)
                    components+=len(rows)
                    self.assertLessEqual(len(rows),blocks.MAX_PER_ELEVATION)
                    for row in rows:
                        if not row.overlay:
                            detail=facades.Opening('detail',0,row.left,row.right,row.bottom,row.top)
                            self.assertFalse(any(detail.overlaps(o) for o in e.openings))
                self.assertLessEqual(total,blocks.MAX_OPENINGS)
                self.assertLessEqual(components,blocks.MAX_COMPONENTS)

    def test_designed_commercial_sites_and_specialists_are_excluded(self):
        for cls in ('office','retail','supermarket','workshop','warehouse','factory','house','church','parking','transportation'):
            spec=building(floors=3 if cls=='office' else 1,**{'class':cls})
            self.assertIsNone(blocks.profile(spec),cls)
            before=freeze_items([(spec,0.,0.)])
            with patch.object(blocks,'profile',return_value=None):
                prior=freeze_items([(spec,0.,0.)])
                near=fingerprint(b.build(prior));lite=fingerprint(b.build(prior,lite=True))
            self.assertEqual(near,fingerprint(b.build(before)),cls)
            self.assertEqual(lite,fingerprint(b.build(before,lite=True)),cls)
        spec=building();self.assertIsNotNone(blocks.profile(spec))
        for name in ('site','terminal','garage_access'):
            s=building();setattr(s,name,{'accepted':True})
            self.assertIsNone(blocks.profile(s),name)

    def test_other_outlines_roofs_small_buildings_and_missing_theme_keep_old_route(self):
        cases=[dict(theme=''),dict(width=12.,depth=10.),dict(roof_shape='gabled'),dict(floors=49),
               dict(_footprint=Footprint(((0,0),(36,0),(36,12),(16,12),(16,24),(0,24)))),
               dict(_footprint=Footprint(((0,0),(36,0),(36,24),(0,24)),(((5,5),(5,10),(10,10),(10,5)),)))]
        for args in cases:self.assertIsNone(blocks.profile(building(**args)),args)

    def test_source_material_colour_height_and_door_remain_authoritative(self):
        for mat in ('brick','stone','wood','metal','concrete','glass'):
            spec=building(facade_material=mat,facade_color='#778899')
            p=blocks.profile(spec)
            self.assertIsNotNone(p)
            self.assertEqual(blocks.wall_looks(spec,p),(spec.facade,)*3)
            before=(spec.height,spec.floors,spec.roof,spec.door,spec.footprint)
            b.build(freeze_items([(spec,0.,0.)]))
            self.assertEqual(before,(spec.height,spec.floors,spec.roof,spec.door,spec.footprint))

    def test_translation_pickle_and_tiers_do_not_reroll_variant(self):
        a=building(seed='stable');p=blocks.profile(a)
        shifted=a.footprint.translated(1000,-300)
        c=building(seed='stable',_footprint=shifted)
        self.assertEqual(p,blocks.profile(c))
        self.assertEqual(facades.plan(a,0,0),facades.plan(c,0,0))
        self.assertEqual(p,blocks.profile(freeze_items([(a,0.,0.)])[0][0]))

    def test_tall_wide_short_storeys_and_bevelled_road_clips_have_bounded_geometry(self):
        bevel=Footprint(((0,2),(2,0),(36,0),(36,24),(0,24)))
        for args in (dict(width=200,depth=100,floors=48),dict(height=13.8,floors=6),dict(_footprint=bevel)):
            s=building(**args);p=blocks.profile(s)
            self.assertIsNotNone(p)
            layout=facades.plan(s,0,0)
            self.assertLessEqual(sum(o.kind!='door' for e in layout.elevations for o in e.openings),blocks.MAX_OPENINGS)
            for lite in (False,True):self.assertTrue(np.isfinite(b.build([(s,0.,0.)],lite=lite)[0]).all())


if __name__=='__main__':unittest.main()
