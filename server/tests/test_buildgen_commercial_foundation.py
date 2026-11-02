"""Shared collinear grids and bounded accepted commercial facade detail."""
from dataclasses import FrozenInstanceError
from pathlib import Path
import pickle
import sys
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import commercial, commercial_detail, facades, freeze_items, programme
from buildgen.topology import Footprint
from test_buildgen_commercial_architecture import fixture


FAMILIES=(('office','brick',3,12.),('office','concrete',3,12.),('office','glass',3,12.),
          ('retail','brick',1,6.),('workshop','metal',1,6.),('warehouse','metal',1,6.),
          ('supermarket','concrete',1,6.))


def planned(cls,material,floors,height,fp,seed='foundation'):
    s=b.plan(np.asarray(fp.outer),{'class':cls,'_footprint':fp,'num_floors':floors,'height':height,
                                  'roof_shape':'flat','facade_material':material,'seed_id':seed})
    s.gring=np.zeros(len(s.ring))
    return s


def set_world_door(spec,point):
    point=np.asarray(point)
    for edge,(a,c) in enumerate(zip(spec.ring,np.roll(spec.ring,-1,axis=0))):
        d=c-a;length=np.linalg.norm(d);along=float((point-a)@d/length)
        if -.000001<=along<=length+.000001 and np.linalg.norm(point-a-d*along/length)<1e-6:
            spec.front=edge;spec.door=(edge,along);return
    raise AssertionError('door outside source outline')


class CommercialFoundationTests(unittest.TestCase):
    def test_collinear_densification_keeps_rendered_facade_and_accepted_door(self):
        dense=Footprint(((0,0),(7.3,0),(14.8,0),(27.4,0),(30,0),(30,8),(30,20),
                         (12,20),(0,20),(0,13)))
        for cls,material,floors,height in FAMILIES:
            with self.subTest(cls=cls,material=material):
                original,roads=fixture(material,cls=cls,floors=floors,height=height,seed='foundation')
                a=original.ring[original.door[0]];c=original.ring[(original.door[0]+1)%len(original.ring)]
                portal=a+(c-a)*original.door[1]/np.linalg.norm(c-a)
                split=planned(cls,material,floors,height,dense)
                set_world_door(split,portal)
                accepted=split.door
                split.access=original.access
                commercial.resolve([(split,0.,0.)],roads,lambda xy:np.zeros(len(xy)),0.,0.)
                self.assertEqual(split.door,accepted)
                normalized=[]
                for s in (original,split):
                    pg=programme.derive(s)
                    normalized.append(tuple((pg.run(e.boundary,e.edge).start,pg.run(e.boundary,e.edge).end,
                                             e.openings,e.role) for e in s.facades.elevations))
                self.assertEqual(normalized[0],normalized[1])
                # Exercise the real shared renderer, not only grid descriptors.
                for lite in (False,True):
                    meshes=[]
                    for s in (original,split):
                        mesh=b.Mesh();facades.draw(mesh,s,0.,0.,-3.,lite=lite);meshes.append(mesh.arrays())
                    for first,second in zip(meshes[0][:4],meshes[1][:4]):
                        np.testing.assert_allclose(first,second,rtol=0,atol=1e-6)

    def test_office_floor_grids_align_through_actual_entry_fragments(self):
        for material in ('brick','concrete','glass'):
            s,_=fixture(material)
            pg=programme.derive(s)
            for elevation in s.facades.elevations:
                lattice=commercial.office_grid(s,pg.run(elevation.boundary,elevation.edge),pg)
                for op in elevation.openings:
                    if op.kind=='door':continue
                    nominal=next(bay for bay in lattice.bays if bay.index==op.variant)
                    self.assertGreaterEqual(op.left,nominal.left-1e-9)
                    self.assertLessEqual(op.right,nominal.right+1e-9)
                    if op.floor>0:
                        self.assertAlmostEqual(op.left,nominal.left)
                        self.assertAlmostEqual(op.right,nominal.right)
            self.assertIn('architecture_programme_shared_runs_v1',s.facades.diagnostics)

    def test_corner_entry_gate_aligns_facade_threshold_and_stock_door(self):
        fp=Footprint(((0,0),(27,0),(30,0),(30,20),(0,20)))
        roads=[(np.array([(27.,-12.),(40.,-12.)]),3.,'residential',False)]
        for along,wide in ((1.8,False),(.2,True)):
            with self.subTest(along=along):
                s=planned('supermarket','concrete',1,6.,fp)
                s.front=1;s.door=(1,along)
                before=s.door
                props=b.doors([(s,0.,0.)],roads,0.,0.,ground=lambda xy:np.zeros(len(xy)))
                self.assertEqual(s.door[0],before[0])
                self.assertAlmostEqual(s.door[1],before[1],places=12)
                self.assertEqual(commercial.can_public_entry(s),wide)
                openings=[o for e in s.facades.elevations for o in e.openings]
                self.assertEqual(any(o.kind=='public_entry' for o in openings),wide)
                self.assertEqual(any(p[0]=='door' for p in props),not wide)
                threshold=next(v for v in s.access.solids if v.kind=='threshold')
                width=np.linalg.norm(np.subtract(threshold.top[0][:2],threshold.top[3][:2]))
                self.assertAlmostEqual(width,3.6 if wide else 1.4)
                for op in openings:
                    self.assertGreaterEqual(op.left,.45)
                    self.assertLessEqual(op.right,30.-.45)

    def test_optional_programme_failure_preserves_generic_geometry_and_door(self):
        s,_=fixture('concrete',cls='supermarket',floors=1,height=6.)
        with patch.object(programme,'derive',side_effect=ValueError('bounded source descriptor rejected')):
            self.assertFalse(commercial.can_public_entry(s))
            self.assertEqual(commercial.entry_width(s),1.4)
            layout=facades.plan(s,0.,0.)
            self.assertIn('architecture_programme_existing_geometry_fallback',layout.diagnostics)
            self.assertTrue(any(o.kind=='door' for e in layout.elevations for o in e.openings))
            self.assertFalse(any(o.kind=='public_entry' for e in layout.elevations for o in e.openings))
            mesh=b.Mesh();facades.draw(mesh,s,0.,0.,-3.)
            self.assertTrue(np.isfinite(mesh.arrays()[0]).all())

    def test_programme_is_derived_once_per_facade_plan(self):
        for cls,material,floors,height in FAMILIES:
            s,_=fixture(material,cls=cls,floors=floors,height=height)
            with patch.object(programme,'derive',wraps=programme.derive) as derive:
                facades.plan(s,0.,0.)
                self.assertEqual(derive.call_count,1)

    def test_detail_envelopes_clear_accepted_openings_and_remain_bounded(self):
        for cls,material,floors,height in FAMILIES:
            s,_=fixture(material,cls=cls,floors=floors,height=height)
            detail=commercial_detail.plan(s,s.facades,programme.derive(s),commercial.detail_family(s))
            self.assertLessEqual(sum(len(e.components) for e in detail.elevations),commercial_detail.MAX_COMPONENTS)
            self.assertEqual(detail,pickle.loads(pickle.dumps(detail)))
            with self.assertRaises(FrozenInstanceError):detail.diagnostics=()
            for e in detail.elevations:
                elevation=next(x for x in s.facades.elevations if x.boundary==e.boundary and x.edge==e.edge)
                self.assertLessEqual(len(e.components),commercial_detail.MAX_PER_ELEVATION)
                for c in e.components:
                    self.assertGreaterEqual(c.left,.025)
                    self.assertLessEqual(c.right,elevation.length-.025)
                    self.assertGreaterEqual(c.bottom,0.)
                    self.assertLessEqual(c.top,s.height)
                    self.assertGreater(c.right,c.left)
                    self.assertGreater(c.top,c.bottom)
                    panel=facades.Opening(c.kind,0,c.left,c.right,c.bottom,c.top)
                    if not c.overlay:
                        self.assertTrue(all(not panel.overlaps(o,.079) for o in elevation.openings))
                    else:
                        self.assertTrue(c.near_only)
                        self.assertTrue(any(o.kind in ('office','storefront') and o.left<c.left<c.right<o.right
                                            and o.bottom<c.bottom<c.top<o.top for o in elevation.openings))

    def test_visible_details_preserve_collision_and_tier_envelope(self):
        for cls,material,floors,height in FAMILIES:
            s,_=fixture(material,cls=cls,floors=floors,height=height)
            frozen=freeze_items([(s,0.,0.)])
            actual=[b.build(frozen,lite=lite) for lite in (False,True)]
            collision=b.collision_mesh(frozen)
            with patch.object(commercial_detail,'plan',return_value=commercial_detail.DetailPlan(())):
                controls=[b.build(frozen,lite=lite) for lite in (False,True)]
                control_collision=b.collision_mesh(frozen)
            for mesh,control in zip(actual,controls):
                self.assertGreater(len(mesh[0]),len(control[0]))
                np.testing.assert_allclose(mesh[0].min(axis=0),control[0].min(axis=0))
                np.testing.assert_allclose(mesh[0].max(axis=0),control[0].max(axis=0))
            np.testing.assert_array_equal(collision[0],control_collision[0])
            np.testing.assert_array_equal(collision[2],control_collision[2])

    def test_obstructed_and_courtyard_runs_get_no_unproved_structural_detail(self):
        s,roads=fixture('concrete')
        fp=Footprint(((12,-.25),(18,-.25),(18,-.001),(12,-.001)))
        neighbour=planned('industrial','concrete',1,20.,fp)
        commercial.resolve([(s,0.,0.),(neighbour,0.,0.)],roads,lambda xy:np.zeros(len(xy)),0.,0.)
        detail=commercial_detail.plan(s,s.facades,programme.derive(s),commercial.detail_family(s))
        self.assertIn('ci_obstruction_run:0:0',s.facades.diagnostics)
        self.assertFalse(detail.elevation(0,0))
        self.assertIn('commercial_detail_omitted_obstructed_run',detail.diagnostics)
        self.assertTrue(detail.elevation(0,2))
        court=Footprint(((0,0),(30,0),(30,24),(0,24)),(((10,8),(20,8),(20,16),(10,16)),))
        s,_=fixture('brick',fp=court)
        detail=commercial_detail.plan(s,s.facades,programme.derive(s),commercial.detail_family(s))
        self.assertTrue(all(e.boundary==0 for e in detail.elevations))
        blocked=programme.derive(s,party_walls=((0,0),))
        openings,role=commercial.openings(s,0,0,30.,0.,0.,(),programme=blocked)
        self.assertEqual((openings,role),((),'party_wall'))


if __name__=='__main__':unittest.main()
