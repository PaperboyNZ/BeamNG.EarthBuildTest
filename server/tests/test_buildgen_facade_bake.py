"""Distant cards cannot fill openings or consume roofs and projections."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np

sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[2]/'tools')]
import buildings as b
from buildgen import facade_bake as bake,freeze_items
from buildgen.topology import Footprint
from test_buildgen_regions import building


def solid(material,uv,tint,jac):
    return {k:np.full((len(uv),3),128,np.uint8) for k in bake.CHANNELS}


class FacadeBakeTest(unittest.TestCase):
    def fixture(self,fp=None):
        kw={} if fp is None else dict(fp=fp)
        # These lab tests exercise flat-card eligibility. New deep structural
        # apertures have their own rejection regression below.
        with patch('buildgen.residential.for_spec',return_value=None):
            item=freeze_items([(building('nz_temperate',**kw),0.,0.)])[0]
            return item,b.build([item],lite=True)

    def test_structural_recesses_are_not_closed_by_cards(self):
        item=freeze_items([(building('jp_temperate'),0.,0.)])[0]
        mesh=b.build([item],lite=True)
        cards,notes=bake.cards(mesh,*item,solid)
        self.assertTrue(any(o.assembly for e in item[0].facades.elevations for o in e.openings))
        self.assertLess(len(cards),4)
        self.assertTrue(any('open_surface_retained' in note for note in notes))

    def test_roof_and_unselected_attributes_survive_exactly(self):
        item,mesh=self.fixture()
        cards,notes=bake.cards(mesh,*item,solid)
        self.assertEqual(len(cards),4)
        placements={c.signature:('test_atlas',((0,0),(1,0),(1,1),(0,1))) for c in cards}
        result=bake.assemble(mesh,cards,placements)
        keep=np.ones(len(mesh[2]),bool)
        for c in cards:keep[c.source_triangles]=False
        n=int(keep.sum())
        for field in (0,1,5):
            np.testing.assert_array_equal(result[field][result[2][:n]],mesh[field][mesh[2][keep]])
        np.testing.assert_array_equal(result[3][:n],mesh[3][keep])
        self.assertEqual(float(result[0][:,2].max()),float(mesh[0][:,2].max()))

    def test_courtyard_boundaries_remain_separate(self):
        fp=Footprint(((0,0),(24,0),(24,22),(0,22)),(((8,6),(16,6),(16,16),(8,16)),))
        item,mesh=self.fixture(fp)
        cards,_=bake.cards(mesh,*item,solid)
        self.assertEqual(len(cards),8)
        # Every card follows one original wall edge, never a roof over the court.
        for card in cards:
            self.assertEqual(card.points[0,2],card.points[1,2])
            self.assertEqual(card.points[2,2],card.points[3,2])
            np.testing.assert_array_equal(card.points[0,:2],card.points[3,:2])

    def test_narrow_opening_is_not_closed_by_a_card(self):
        item,mesh=self.fixture()
        cards,_=bake.cards(mesh,*item,solid)
        victim=cards[0].source_triangles
        # Removing the base wall leaves only separated window/trim overlays.
        keep=np.ones(len(mesh[2]),bool);keep[victim]=False
        broken=(mesh[0],mesh[1],mesh[2][keep],mesh[3][keep],mesh[4],mesh[5])
        actual,_=bake.cards(broken,*item,solid)
        self.assertEqual(len(actual),3)

    def test_resolution_budget_and_missing_material_fail_closed(self):
        item,mesh=self.fixture()
        cards,notes=bake.cards(mesh,*item,solid,max_side=8)
        self.assertFalse(cards);self.assertTrue(notes)
        def missing(*args):raise FileNotFoundError('fixture texture')
        cards,notes=bake.cards(mesh,*item,missing)
        self.assertFalse(cards);self.assertTrue(all('material_retained' in x for x in notes))

    def test_shadow_split_preserves_visible_geometry_and_adds_only_aliases(self):
        from building_render_lab import shadow_candidate
        item,_=self.fixture()
        near,hybrid,casters,aliases=shadow_candidate([item])
        for k in (0,1,2,5):np.testing.assert_array_equal(near[k],hybrid[k])
        self.assertLess(len(casters[2]),len(near[2]))
        resolved=[aliases.get(hybrid[4][i],hybrid[4][i]) for i in hybrid[3]]
        self.assertEqual(resolved,[near[4][i] for i in near[3]])


if __name__=='__main__':unittest.main()
