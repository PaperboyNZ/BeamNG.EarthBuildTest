"""Compact garage panels use shutter material without changing their interfaces."""
from contextlib import contextmanager
from pathlib import Path
import pickle
import sys
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import facades,freeze_items,materials
from buildgen.progressive import DETAIL
from test_buildgen_facades import building,road


@contextmanager
def minimum():
    token=DETAIL.set('minimum')
    try:yield
    finally:DETAIL.reset(token)


def garage_fixture(kind,seed='house',width=None):
    width=width if width is not None else (12. if kind=='house' else 5.4)
    if kind=='house':
        # Reuse the real inferred house/seed and road setback already exercised
        # by test_garage_entry_windows_and_driveway_form_one_layout (12m) and
        # test_front_fence_leaves_the_full_garage_driveway_clear (20m). A mapped
        # 3.2m TOTAL height can leave too little wall height under a pitched roof
        # for a door/garage; do not force an aperture onto that rejected form.
        spec=building(width,10.,seed_id=seed)
    else:
        spec=building(width,7.,**{'class':'garage','height':3.2,'num_floors':1,'seed_id':seed})
    spec.gring=np.zeros(len(spec.ring))
    b.doors([(spec,0.,0.)],road(),0.,0.,ground=lambda xy:np.zeros(len(xy)))
    return spec


def opening_quad(spec):
    edge,centre,width,height=spec.garage_opening
    ring=np.asarray(spec.footprint.outer)
    a,c=ring[edge],ring[(edge+1)%len(ring)]
    direction=(c-a)/np.linalg.norm(c-a)
    outward=np.array([direction[1],-direction[0]])
    base=b.base_z(spec,0.,0.)+(spec.min_h or 0.)
    z=spec.access.garage_z if spec.access and spec.access.garage_z is not None else base
    return np.array([np.r_[a+direction*along+outward*.02,level]
                     for along,level in ((centre-width/2,z),(centre+width/2,z),
                                         (centre+width/2,z+height),(centre-width/2,z+height))])


class MinimumGarageTests(unittest.TestCase):
    def test_house_and_standalone_shutter_faces_survive_freeze_and_pickle(self):
        cases=(('house','house',12.),('house','house',20.),
               ('garage','compact-garage-a',5.4),('garage','compact-garage-b',5.4))
        for kind,seed,width in cases:
            with self.subTest(kind=kind,seed=seed,width=width),minimum(), \
                 patch.object(facades,'plan',side_effect=AssertionError('full facade planner')):
                spec=garage_fixture(kind,seed,width)
                self.assertIsNotNone(spec.garage_opening)
                if kind=='garage':self.assertEqual(spec.inference.selection.preset.id,'garage_outbuilding')
                else:
                    self.assertIsNotNone(spec.door)
                    self.assertGreater(abs(spec.door[1]-spec.garage_opening[1]),spec.garage_opening[2]/2+.85)
                interfaces=(spec.door,spec.garage_opening,spec.access)
                expected=opening_quad(spec)
                restored=pickle.loads(pickle.dumps(freeze_items([(spec,0.,0.)])))
                frozen=restored[0][0]
                self.assertIsNone(frozen.facades)
                self.assertEqual(interfaces,(frozen.door,frozen.garage_opening,frozen.access))
                for lite in (False,True):
                    with patch.object(materials,'garage_colour',wraps=materials.garage_colour) as paint:
                        product=b.build(restored,lite=lite)
                    positions,uv,triangles,mats,*_=product
                    corners=np.linalg.norm(positions[:,None,:]-expected[None,:,:],axis=2)<1e-7
                    self.assertTrue(corners.any(axis=0).all(),'garage corners moved')
                    garage_vertices=corners.any(axis=1)
                    garage_faces=np.flatnonzero(garage_vertices[triangles].all(axis=1))
                    self.assertEqual(len(garage_faces),2,'expected the existing single garage quad')
                    np.testing.assert_array_equal(mats[garage_faces],np.full(2,b.MATERIALS.index(b.SHUTTER)))
                    # Keep the negative control about the actual material:
                    # the original renderer must fail above on FACADE, not
                    # first on the newly introduced helper's call count.
                    paint.assert_called_once_with(frozen.seed)
                    for index,wanted in enumerate(((0.,0.),(1.,0.),(1.,1.),(0.,1.))):
                        for vertex in np.flatnonzero(corners[:,index]):
                            np.testing.assert_array_equal(uv[vertex],wanted)
                    # The render operation must not rewrite physical access,
                    # entrance anchors or the accepted garage aperture.
                    self.assertEqual(interfaces,(frozen.door,frozen.garage_opening,frozen.access))

    def test_house_windows_keep_atlas_region_and_clear_door_garage_reservations(self):
        with minimum(),patch.object(facades,'plan',side_effect=AssertionError('full facade planner')):
            spec=garage_fixture('house','house',20.)
            items=pickle.loads(pickle.dumps(freeze_items([(spec,0.,0.)])))
            positions,uv,triangles,mats,*_=b.build(items)
            spec=items[0][0]
        self.assertIsNotNone(spec.door);self.assertIsNotNone(spec.garage_opening)
        ring=np.asarray(spec.footprint.outer);windows=0
        u0,u1,v0,v1=b.WIN_UV
        for face,material in zip(triangles,mats):
            if material!=b.MATERIALS.index(b.FACADE):continue
            points=positions[face]
            for edge,(a,c) in enumerate(zip(ring,np.roll(ring,-1,axis=0))):
                direction=(c-a)/np.linalg.norm(c-a);outward=np.array([direction[1],-direction[0]])
                local=points[:,:2]-a
                if not np.allclose(local@outward,.018,rtol=0,atol=1e-8):continue
                along=local@direction
                if along.min()<0 or along.max()>np.linalg.norm(c-a):continue
                windows+=1
                self.assertTrue(((uv[face,0]>=u0-1e-12)&(uv[face,0]<=u1+1e-12)).all())
                self.assertTrue(((uv[face,1]>=v0-1e-12)&(uv[face,1]<=v1+1e-12)).all())
                reservations=[]
                if edge==spec.door[0]:
                    z=spec.access.door_z if spec.access else 0.
                    reservations.append((spec.door[1]-.85,spec.door[1]+.85,z,z+2.4))
                if edge==spec.garage_opening[0]:
                    _,centre,width,height=spec.garage_opening
                    z=spec.access.garage_z if spec.access and spec.access.garage_z is not None else b.base_z(spec,0.,0.)
                    reservations.append((centre-width/2-.2,centre+width/2+.2,z,z+height+.2))
                for left,right,bottom,top in reservations:
                    self.assertFalse(along.min()<right and along.max()>left and points[:,2].min()<top and points[:,2].max()>bottom,
                                     'window overlaps a reserved entrance/garage interval')
        self.assertGreater(windows,0,'house fixture must contain actual atlas windows')

    def test_no_garage_never_selects_garage_paint(self):
        with minimum(),patch.object(facades,'plan',side_effect=AssertionError('full facade planner')):
            spec=building(seed_id='no-garage')
            self.assertIsNone(spec.garage_opening)
            items=pickle.loads(pickle.dumps(freeze_items([(spec,0.,0.)])))
            with patch.object(materials,'garage_colour',side_effect=AssertionError('unused garage paint')):
                self.assertIsNotNone(b.build(items))

    def test_full_facade_paint_tokens_equal_the_original_seeded_palette(self):
        # Frozen pre-fix recipe: preserve its exact channel, ordering and weights.
        old_palette=(((.86,.87,.84),4),((.35,.38,.39),3),((.52,.44,.36),2),((.52,.21,.16),1))
        for seed in range(32):
            spec=building(seed_id=seed)
            expected=materials.choose(spec.seed,'garage-paint',old_palette)
            self.assertEqual(materials.garage_colour(spec.seed),expected)
            layout=facades.plan(spec,0.,0.)
            self.assertEqual(layout.garage,b.custom_look(b.SHUTTER,expected))


if __name__=='__main__':unittest.main()
