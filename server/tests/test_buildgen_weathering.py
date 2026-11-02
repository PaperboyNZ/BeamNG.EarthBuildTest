"""Aging must be stable across LOD/rebase and leave physics/topology unchanged."""
from pathlib import Path
import json
import io
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
import cdae
from buildgen import weathering,progressive
import test_buildgen_progressive as fixtures


class WeatheringTests(unittest.TestCase):
    def test_shipped_detail_texture_uses_supported_rgb_dds_with_complete_mips(self):
        from PIL import Image
        root=Path(__file__).resolve().parents[2]
        sys.path.insert(0,str(root/'tools'))
        import build_weathering
        pixels=build_weathering.texture()
        data=build_weathering.encode(pixels)
        path=root/'mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/bne_weathering.dds'
        self.assertEqual(data,path.read_bytes(),'asset must match its reproducible generator')
        known=(root/'mod/beamng_earth/art/beamngEarth/detail_ground.dds').read_bytes()
        self.assertEqual(data[76:108],known[76:108],'match the engine-tested RGB pixel format, not terrain DX10')
        self.assertEqual(struct.unpack_from('<I',data,28)[0],9)
        np.testing.assert_array_equal(np.asarray(Image.open(io.BytesIO(data)))[:,:,:3],pixels)
        offset=128;level=pixels
        while True:
            count=len(level)**2*4
            rgba=np.frombuffer(data[offset:offset+count],np.uint8).reshape(len(level),len(level),4)
            np.testing.assert_array_equal(rgba[:,:,:3],level)
            self.assertTrue(np.all(rgba[:,:,3]==255))
            offset+=count
            if len(level)==1:break
            level=np.rint(level.reshape(len(level)//2,2,len(level)//2,2,3).mean((1,3))).astype(np.uint8)
        self.assertEqual(offset,len(data),'no missing or surplus mip bytes')

    def test_buildings_have_stable_varied_aging(self):
        values=[weathering.strength(i/32) for i in range(32)]
        self.assertLess(min(values),.25)
        self.assertGreater(max(values),.85)
        self.assertEqual(values,[weathering.strength(i/32) for i in range(32)])
        self.assertTrue(all(.06<=v<=1 for v in values))

    def test_aging_changes_only_vertex_rgb_not_geometry_uv_or_alpha(self):
        item=fixtures.ProgressiveTests().items(1)
        with patch.object(weathering,'apply',side_effect=lambda p,c,*args:c):fresh=b.build(item)
        aged=b.build(item)
        for i in range(5):
            if isinstance(fresh[i],np.ndarray):np.testing.assert_array_equal(fresh[i],aged[i])
            else:self.assertEqual(fresh[i],aged[i])
        np.testing.assert_array_equal(fresh[5][:,3],aged[5][:,3])
        self.assertLess(aged[5][:,:3].mean(),fresh[5][:,:3].mean())

    def test_same_surface_point_has_same_tone_and_detail_uv_at_any_lod(self):
        p=np.array([[0.,0.,0.],[8.,0.,0.],[8.,0.,8.],[0.,0.,8.]])
        tris=np.array([[0,1,2],[0,2,3]])
        c=np.full((4,4),240,np.uint8);c[:,3]=255
        mat=np.full(2,b.MATERIALS.index(b.STUCCO))
        result=weathering.apply(p,c,tris,mat,[(0,.765,0.,8.)])
        shifted=p+np.array([1000,2000,50])
        np.testing.assert_array_equal(result,weathering.apply(shifted,c,tris,mat,[(0,.765,50.,8.)]))
        self.assertLess(result[0,0],result[3,0])
        np.testing.assert_allclose(weathering.uv(p,tris),p[:,[0,2]]/6.)

    def test_native_lods_encode_shared_detail_uv_and_collision_omits_it(self):
        item=fixtures.ProgressiveTests().items(1)
        mesh=b.build_parts(item,with_lod=True)[0]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'aged.cdae';b.write(str(path),mesh)
            data=cdae.read(path)
            for lod in data['meshes']:
                self.assertEqual(lod['tverts2'][0],lod['verts'][0])
            b.write(str(path),b.collision_mesh(item),collision_only=True)
            for lod in cdae.read(path)['meshes']:
                self.assertEqual(lod.get('tverts2',(0,))[0],0)
        self.assertTrue(np.isfinite(progressive.shell(item)[0]).all())

    def test_material_palette_stays_shared_and_windows_stay_unstained(self):
        root=Path(__file__).resolve().parents[2]
        mats=json.loads((root/'mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/buildings.materials.json').read_text())
        aged=[m for m in mats.values() if m['Stages'][0].get('detailMap','').endswith('bne_weathering.dds')]
        self.assertGreaterEqual(len(aged),8)
        for m in aged:
            self.assertEqual(m['Stages'][0]['detailMapUseUV'],1)
            self.assertFalse(m.get('translucent',False))
        for name in (b.OFFICE,b.SHOP,b.FACADE):self.assertNotIn('detailMap',mats[name]['Stages'][0])


if __name__=='__main__':unittest.main()
