"""Typed streams retain snapshots and component order across bounded flushes."""
from pathlib import Path
import sys,unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import components
from buildgen.typed_mesh import Stream


class TypedMeshTests(unittest.TestCase):
    def test_exported_snapshot_survives_append_and_scattered_write(self):
        stream=Stream('d',np.float64);stream.extend([1.,2.,3.]);old=stream.view()
        stream.extend(np.array([4.,5.]));stream.write(np.array([0,4]),np.array([9.,8.]))
        np.testing.assert_array_equal(old,[1.,2.,3.])
        np.testing.assert_array_equal(stream.view(),[9.,2.,3.,4.,8.])
        same=Stream('d',np.float64);same.extend([9.,2.,3.,4.,8.])
        self.assertEqual(stream,same)
        same.append(10.);self.assertNotEqual(stream,same)

    def test_more_than_one_batch_preserves_interleaved_geometry_and_uvs(self):
        mesh=b.Mesh();template=components.surround(1.3,1.8,.06,.15);mat=(2,(20,30,40,255))
        for i in range(600):
            components.facade(mesh,template,(10.,-20.),(.8,.6),3.,i*.05,1.,mat,(17.,2.4,3.))
            mesh.tri((i,0,0),(i+1,0,0),(i,1,0),(0,0),(1,0),(0,1),mat)
        p,uv,t,materials,col=mesh.arrays()
        self.assertFalse(mesh.component_jobs)
        stride=len(template.indices)+3
        for i in (0,255,256,511,599):
            np.testing.assert_array_equal(p[i*stride+len(template.indices)],(i,0.,0.))
            np.testing.assert_array_equal(uv[i*stride:i*stride+16],template.uvs[:16])
        self.assertEqual(len(p),600*stride)
        self.assertLess(t.max(),len(p))
        self.assertTrue(p.flags.c_contiguous and uv.flags.c_contiguous)


if __name__=='__main__':unittest.main()
