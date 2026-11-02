"""Shared elevation frames preserve miter geometry and complete regional meshes."""
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import regional_architecture as regional
from test_buildgen_regions import building
from buildgen import regional_blocks as blocks
from test_buildgen_regional_blocks import variants

_paint_cells=blocks.paint_cells


def reference_paint(spec,p,elevation,cell,looks,section_width=None):
    return _paint_cells(spec,p,elevation,cell,looks)


def reference_frame(ring,edge,base):
    return lambda s,z,depth:regional.band_point(ring,edge,s,z,depth,base)


class BandFrameTests(unittest.TestCase):
    def test_endpoints_interiors_reentrant_and_near_reversal(self):
        rings=[((0.,0.),(12.,0.),(12.,8.),(0.,8.)),
               ((.01,2.),(7.,3.),(9.,12.),(5.,5.),(-3.,8.)),
               ((0.,0.),(12.,0.),(.1,.01),(0.,8.))]
        for ring in rings:
            for edge in range(len(ring)):
                length=math.dist(ring[edge],ring[(edge+1)%len(ring)])
                point=regional.band_frame(ring,edge,145.27)
                for s in (0.,1e-9,1e-7,length/3,length-1e-9,length):
                    for depth in (-.12,0.,.012,.12):
                        self.assertEqual(point(s,2.3,depth),regional.band_point(ring,edge,s,2.3,depth,145.27))

    def test_all_64_regions_near_and_lite_mesh_arrays_are_identical(self):
        for theme in regional.catalogue():
            items=[(building(theme),0.,0.)]
            for lite in (False,True):
                with self.subTest(theme=theme,lite=lite):
                    actual=b.build(items,lite=lite)
                    with patch.object(regional,'band_frame',reference_frame):expected=b.build(items,lite=lite)
                    for field in (0,1,2,3,5):np.testing.assert_array_equal(actual[field],expected[field])
                    self.assertEqual(actual[4],expected[4])

    def test_all_192_blocks_preserve_paint_and_geometry(self):
        for theme in blocks.catalogue():
            for spec in variants(theme):
                for lite in (False,True):
                    with self.subTest(theme=theme,lite=lite):
                        actual=b.build([(spec,0.,0.)],lite=lite)
                        with patch.object(blocks,'paint_cells',reference_paint):
                            expected=b.build([(spec,0.,0.)],lite=lite)
                        for field in (0,1,2,3,5):np.testing.assert_array_equal(actual[field],expected[field])
                        self.assertEqual(actual[4],expected[4])


if __name__=='__main__':unittest.main()
