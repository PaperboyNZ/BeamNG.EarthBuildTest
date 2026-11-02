"""Texture-based distant apertures retain footprints, roofs and physics."""
from pathlib import Path
import sys,unittest
from dataclasses import replace
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import facades,freeze_items,regional_architecture as regional,quality,progressive
from test_buildgen_regions import building


class TextureLodTests(unittest.TestCase):
    def test_distant_deep_windows_use_atlas_planes_without_changing_close_mesh(self):
        spec=freeze_items([(building('nz_temperate'),0.,0.)])[0][0]
        opening=facades.Opening('window',0,3.,5.,1.,2.4,depth=.6)
        spec=replace(spec,facades=replace(spec.facades,elevations=(facades.Elevation(0,0,12.,(opening,)),)))
        meshes=[]
        with patch.object(regional,'for_spec',return_value=None),patch.object(regional,'aperture_shape',return_value='rectangular'):
            for textured in (False,True):
                m=b.Mesh();facades.draw(m,spec,0.,0.,-.5,lite=True,textured=textured);meshes.append(m.arrays())
        old,new=meshes;glass=b._Looks(spec.seed)['bne_bld_fac_white'][0]
        a=np.unique(old[2][old[3]==glass]);c=np.unique(new[2][new[3]==glass])
        np.testing.assert_array_equal(old[1][a],new[1][c])
        np.testing.assert_array_equal(old[0][a][:,[0,2]],new[0][c][:,[0,2]])
        self.assertLess(len(new[2]),len(old[2]))
        self.assertTrue(np.allclose(new[0][c,1],-.02))

    def test_far_texture_mode_keeps_roof_and_collision(self):
        items=freeze_items([(building('nz_temperate'),0.,0.)])
        close=b.build(items);old=b.build(items,lite=True);new=b.build(items,lite=True,texture_facades=True)
        roof={b.MATERIALS.index(m) for m in (b.ROOF_METAL,b.ROOF_SLATE,b.ROOF_SHINGLE)}
        def roofs(m):return m[0][m[2][np.isin(m[3],list(roof))]]
        np.testing.assert_array_equal(roofs(old),roofs(new))
        again=b.build(items)
        for field in (0,1,2,3,5):np.testing.assert_array_equal(close[field],again[field])
        self.assertLess(len(new[2]),len(old[2]))

    def test_detailed_import_budgets_shrink_and_minimum_stays_bounded(self):
        budgets=[];groups=[]
        for name in quality.NAMES:
            token=progressive.DETAIL.set(name)
            try:
                if name == 'minimum':
                    # Minimum publishes one compact representation, not a large
                    # tile batch of the existing detailed compiler's products.
                    self.assertLessEqual(quality.import_vertices(),20000)
                    self.assertGreater(quality.import_vertices(),0)
                else:budgets.append(quality.import_vertices())
                groups.append(quality.current().group_size)
                if quality.current().rank>=2:self.assertGreater(quality.import_vertices(1),quality.import_vertices(2))
            finally:progressive.DETAIL.reset(token)
        self.assertEqual(budgets,sorted(budgets,reverse=True))
        self.assertEqual(groups,sorted(groups,reverse=True))

    def test_view_order_prioritizes_front_without_changing_partition_ids(self):
        from test_buildgen_progressive import ProgressiveTests
        items=ProgressiveTests().items(12)
        publisher=progressive.Publisher('unused','/vfs',None,'a'*32,view=(110.,5.,1.,0.))
        groups=publisher.partition(items)
        ids=[i for i,_ in publisher.view_order(groups)]
        self.assertEqual(sorted(ids),list(range(len(groups))))
        publisher.view=(110.,5.,-1.,0.)
        other=[i for i,_ in publisher.view_order(groups)]
        self.assertNotEqual(ids,other)
        self.assertEqual(publisher.partition(items),groups)

    def test_priority_hint_uses_tile_local_coordinates_and_direction(self):
        import geotiles
        tile=geotiles.geobox(*geotiles.tile_of(-43.53,172.63))
        frame=tile.frame
        hint=progressive.local_view(frame,tile,30.,40.,dict(fx=1.,fy=0.))
        np.testing.assert_allclose(hint,(30.-tile.box[0],40.-tile.box[1],1.,0.),atol=.001)
        self.assertIsNone(progressive.local_view(frame,tile,0.,0.,dict(fx=float('nan'),fy=0.)))


if __name__=='__main__':unittest.main()
