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
    def test_packed_map_keeps_both_sources_and_complete_alpha_mips(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
        import build_weathering
        packed=build_weathering.packed_texture()
        np.testing.assert_array_equal(packed[:,:,:3],build_weathering.texture())
        np.testing.assert_array_equal(packed[:,:,3],build_weathering.streak_texture()[:,:,1])
        root=Path(__file__).resolve().parents[2]
        data=(root/'mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/bne_weathering_blend.dds').read_bytes()
        self.assertEqual(data,build_weathering.encode(packed))
        level=packed;offset=128
        while True:
            count=len(level)**2*4
            actual=np.frombuffer(data[offset:offset+count],np.uint8).reshape(level.shape)
            np.testing.assert_array_equal(actual,level)
            offset+=count
            if len(level)==1:break
            level=np.rint(level.reshape(len(level)//2,2,len(level)//2,2,4).mean((1,3))).astype(np.uint8)
        self.assertEqual(offset,len(data))

    def test_roof_control_is_per_building_affine_and_excludes_roof_slopes(self):
        def control(p,c,t,ranges):
            with patch.object(weathering,'strength',return_value=0.):
                return weathering.apply(p,c,t,np.full(len(t),b.MATERIALS.index(b.STUCCO)),ranges)
        p=np.array([[0,0,0],[8,0,0],[8,0,8],[0,0,8]],float)
        t=np.array([[0,1,2],[0,2,3]])
        c=np.full((4,4),220,np.uint8)
        got=control(p,c,t,[(0,.7,0.,8.)])
        np.testing.assert_array_equal(got[:,3],[0,0,255,255])
        np.testing.assert_array_equal(got[:,:3],c[:,:3])
        # Two unrelated building bases/heights sharing the same combined mesh.
        q=p*np.array([1,1,2])+[20,0,50]
        combined=control(np.vstack((p,q)),np.vstack((c,c)),
            np.vstack((t,t+4)),[(0,.7,0.,8.),(4,.1,50.,16.)])
        np.testing.assert_array_equal(combined[:4],combined[4:])
        halfway=p.copy();halfway[2:,2]=4
        middle=control(halfway,c,t,[(0,.7,0.,8.)])
        np.testing.assert_allclose(middle[2:,3],got[2:,3]/2,atol=.5)
        roof=np.array([[0,0,8],[8,0,8],[8,8,12],[0,8,12]],float)
        self.assertTrue(np.all(control(roof,c,t,[(0,.7,0.,8.)])[:,3]==0))

    def test_organic_map_is_lighter_and_has_no_dominant_streak_direction(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
        import build_weathering
        p=build_weathering.texture()[:,:,1].astype(float)/255.
        self.assertGreater(p.mean(),.42)
        self.assertLess(p.mean(),.48)
        self.assertGreater(p.std(),.025)
        dx=np.abs(p-np.roll(p,1,axis=1)).mean()
        dy=np.abs(p-np.roll(p,1,axis=0)).mean()
        self.assertLess(max(dx,dy)/min(dx,dy),1.6)
        for axis in (0,1):
            seam=np.abs(np.take(p,0,axis)-np.take(p,-1,axis)).mean()
            self.assertLess(seam,2*max(dx,dy))

    def test_climate_exposure_survives_plan_freezing(self):
        from buildgen.context import Context
        from buildgen import freeze_items
        from buildgen.topology import Footprint
        fp=Footprint(((0.,0.),(12.,0.),(12.,9.),(0.,9.)))
        values=[]
        for climate in (1,4,15):
            context=Context(climate=climate,location=(-36.,174.))
            spec=b.plan(np.asarray(fp.outer),{'_footprint':fp,'_context':context,'seed_id':'same','class':'house'})
            frozen=freeze_items([(spec,0.,0.)])[0][0]
            self.assertEqual(frozen.weather_exposure,weathering.exposure(context))
            values.append(frozen.weather_exposure[0])
        self.assertGreater(values[0],values[1])
        self.assertGreater(values[2],values[1])
        self.assertEqual(weathering.exposure(),(1.,0.))

    def test_deposits_favour_damp_shade_lower_walls_and_shallow_roofs(self):
        def tone(p,exposure=(1.,1.)):
            c=np.full((4,4),240,np.uint8);c[:,3]=255
            t=np.array([[0,1,2],[0,2,3]])
            return weathering.apply(np.asarray(p,float),c,t,
                np.full(2,b.MATERIALS.index(b.STUCCO)),[(0,.765,0.,8.,exposure)])[:,:3].mean(axis=1)
        # Winding gives a north-facing wall, then the same face facing south.
        p=[[8,0,0],[0,0,0],[0,0,8],[8,0,8]]
        north=tone(p);south=tone(p,(1.,-1.))
        self.assertLess(north.mean(),south.mean())
        self.assertLess(north[:2].mean(),north[2:].mean())
        self.assertLess(tone(p,(1.22,1.)).mean(),tone(p,(.65,1.)).mean())
        flat=[[0,0,8],[8,0,8],[8,8,8],[0,8,8]]
        slope=[[0,0,8],[8,0,8],[8,8,16],[0,8,16]]
        self.assertLess(tone(flat).mean(),tone(slope).mean())
        # New neutral mean darkening stays below the old uniform .22-.42 wash.
        self.assertGreater(tone(p,(1.,0.)).mean(),240*(1-weathering.strength(.765)*.32*.9533))

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
        values=[weathering.strength(i/256) for i in range(256)]
        self.assertLess(min(values),.25)
        self.assertGreater(max(values),.85)
        self.assertEqual(values,[weathering.strength(i/256) for i in range(256)])
        self.assertTrue(all(.18<=v<=1 for v in values))
        self.assertGreater(np.median(values),.65)

    def test_stains_raise_roughness_and_all_opaque_surfaces_have_normals(self):
        root=Path(__file__).resolve().parents[2]
        sys.path.insert(0,str(root/'tools'))
        import build_weathering
        pixels=build_weathering.texture()
        rough=build_weathering.roughness(pixels)
        art=root/'mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth'
        self.assertEqual(build_weathering.encode(rough),
                         (art/'bne_weathering_roughness.data.dds').read_bytes())
        self.assertGreaterEqual(rough.min()/255.,.83)
        self.assertLessEqual(rough.max()/255.,1.)
        self.assertLess(np.corrcoef(pixels[:,:,1].ravel(),rough[:,:,0].ravel())[0,1],-.98)
        mats=json.loads((art/'buildings.materials.json').read_text())
        mats.update(json.loads((art/'architectural_details.materials.json').read_text()))
        for name,material in mats.items():
            s=material['Stages'][0]
            if not s.get('detailMap','').endswith('bne_weathering_blend.dds'):continue
            with self.subTest(material=name):
                self.assertTrue(s.get('normalMap'))
                self.assertGreater(s['normalMapStrength'],0.)
                if '_roof_' not in name:
                    self.assertLessEqual(s['normalMapStrength'],1.)
                self.assertTrue(s['roughnessMap'].endswith('bne_weathering_roughness.data.dds'))
                self.assertEqual(s['roughnessMapUseUV'],s['detailMapUseUV'])
                self.assertGreaterEqual(rough.min()/255.*s['roughnessFactor'],.80)
                self.assertNotIn('metallicMap',s)
                self.assertLessEqual(s['metallicFactor'],.1)

    def test_aging_changes_only_vertex_colour_and_stain_control_not_geometry_or_uv(self):
        item=fixtures.ProgressiveTests().items(1)
        with patch.object(weathering,'apply',side_effect=lambda p,c,*args:c):fresh=b.build(item)
        aged=b.build(item)
        for i in range(5):
            if isinstance(fresh[i],np.ndarray):np.testing.assert_array_equal(fresh[i],aged[i])
            else:self.assertEqual(fresh[i],aged[i])
        self.assertTrue(np.any(aged[5][:,3]!=fresh[5][:,3]))
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
                alpha=np.frombuffer(lod['colors'][2],np.uint8).reshape(-1,4)[:,3]
                self.assertEqual(alpha.min(),0)
                self.assertEqual(alpha.max(),255)
            b.write(str(path),b.collision_mesh(item),collision_only=True)
            for lod in cdae.read(path)['meshes']:
                self.assertEqual(lod.get('tverts2',(0,))[0],0)
        self.assertTrue(np.isfinite(progressive.shell(item)[0]).all())

    def test_material_palette_stays_shared_and_windows_stay_unstained(self):
        root=Path(__file__).resolve().parents[2]
        mats=json.loads((root/'mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/buildings.materials.json').read_text())
        aged=[m for m in mats.values() if m['Stages'][0].get('detailMap','').endswith('bne_weathering_blend.dds')]
        self.assertGreaterEqual(len(aged),8)
        for m in aged:
            self.assertEqual(m['Stages'][0]['detailMapUseUV'],1)
            self.assertEqual(m['Stages'][0]['detailScale'],[-1.03125,1])
            self.assertFalse(m.get('translucent',False))
        for name in (b.OFFICE,b.SHOP,b.FACADE):self.assertNotIn('detailMap',mats[name]['Stages'][0])


if __name__=='__main__':unittest.main()
