"""Dense building shapes must survive the engine's 16-bit draw indices."""
from pathlib import Path
import struct,sys,unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cdae


class VertexLimitTests(unittest.TestCase):
    def fixture(self):
        n=66003
        p=np.zeros((n,3));p[:,0]=np.arange(n)//3
        p[1::3,1]=1;p[2::3,2]=1
        t=np.arange(n).reshape(-1,3)
        uv=np.arange(n*2,dtype=float).reshape(-1,2)/n
        colors=np.tile([120,80,40,255],(n,1)).astype(np.uint8)
        normals=np.tile([1.,0.,0.],(n,1))
        return p,t,dict(uvs=uv,uvs2=uv*.2,colors=colors,normals=normals,
                       material=['unused','wall','roof'],tri_materials=np.arange(len(t))%2+1)

    def check_meshes(self,shape):
        for mesh in shape['meshes']:
            if mesh['type']==4:continue
            a=cdae.mesh_arrays(mesh)
            self.assertLessEqual(len(a['verts']),cdae.MAX_MESH_VERTS)
            self.assertLess(int(a['indices'].max()),65536)
        count,_,raw=shape['objects']
        self.assertEqual(count,struct.unpack('<i',shape['subShapeNumObjects'][2])[0])
        for i in range(count):
            name,nmesh,start,*_=struct.unpack_from('<6i',raw,i*24)
            self.assertLess(name,len(shape['names']))
            self.assertLessEqual(start+nmesh,len(shape['meshes']))
        n,size,raw=shape['details']
        for i in range(n):self.assertLess(struct.unpack_from('<i',raw,i*size)[0],len(shape['names']))

    def test_dense_export_preserves_positions_materials_and_attributes(self):
        p,t,kw=self.fixture()
        shape=cdae.decode(cdae.encode(p,t,**kw));self.check_meshes(shape)
        self.assertGreater(len(shape['meshes']),1)
        order=np.argsort(kw['tri_materials'],kind='stable');expected=t[order,::-1]
        out={name:[] for name in ('verts','tverts','tverts2','norms','colors','material')}
        for mesh in shape['meshes']:
            a=cdae.mesh_arrays(mesh);tri=a['indices'].reshape(-1,3)
            a['colors']=np.frombuffer(mesh['colors'][2],np.uint8).reshape(-1,4)
            for name in out:
                if name!='material':out[name].append(a[name][tri])
            material=np.empty(len(tri),np.int64)
            for start,count,flags in a['primitives']:material[start//3:(start+count)//3]=(flags&cdae.PRIM_MATERIAL_MASK)+1
            out['material'].append(material)
        values={'verts':p,'norms':kw['normals'],'colors':kw['colors']}
        for name,original in values.items():np.testing.assert_array_equal(np.concatenate(out[name]),original[expected])
        for name,key in (('tverts','uvs'),('tverts2','uvs2')):
            value=kw[key].astype(np.float32).copy();value[:,1]=np.float32(1)-value[:,1]
            np.testing.assert_array_equal(np.concatenate(out[name]),value[expected])
        np.testing.assert_array_equal(np.concatenate(out['material']),kw['tri_materials'][order])

    def test_dense_lod_and_collision_only_have_valid_object_detail_tables(self):
        p,t,kw=self.fixture()
        lod=dict(positions=p,tris=t,**{k:v for k,v in kw.items() if k!='material'})
        shape=cdae.decode(cdae.encode(p[:3],[[0,1,2]],material=kw['material'],tri_materials=[1],lods=[(300,lod)]))
        self.check_meshes(shape)
        self.assertGreater(shape['objects'][0],1)
        self.assertIn(4,[m['type'] for m in shape['meshes']])
        for only in (False,True):
            args=dict(collision_only=True) if only else dict(collisions=[(p,t,kw['tri_materials'])])
            shape=cdae.decode(cdae.encode(p,t,**kw,**args));self.check_meshes(shape)
            self.assertIn('Collision-1',shape['names'])

    def test_native_placement_preserves_every_split_object(self):
        import fast
        fast.require(104,'cdae_shear')
        p,t,kw=self.fixture()
        blob=cdae.encode(p,t,**kw)
        before=cdae.decode(blob)
        count,_,_,_=fast._ef.cdae_zstats(blob)
        self.assertEqual(count,sum(len(cdae.mesh_arrays(m)['verts']) for m in before['meshes']))
        shifted=cdae.decode(fast._ef.cdae_shear(blob,0.,.01,-.02,0.,0.))
        self.check_meshes(shifted)
        self.assertEqual(len(before['meshes']),len(shifted['meshes']))
        for a,b in zip(before['meshes'],shifted['meshes']):
            original=cdae.mesh_arrays(a);moved=cdae.mesh_arrays(b)
            expected=original['verts'].copy()
            expected[:,0]+=expected[:,2]*.01
            expected[:,1]-=expected[:,2]*.02
            np.testing.assert_allclose(moved['verts'],expected,atol=.003)
            np.testing.assert_array_equal(original['indices'],moved['indices'])


if __name__=='__main__':unittest.main()
