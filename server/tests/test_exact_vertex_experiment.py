"""Candidate files preserve every final vertex record and first-use ordering."""
from pathlib import Path
import sys,unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'server'),str(ROOT/'tools')]
import cdae
from experiment_exact_vertices import compact,rows


class ExactVertexExperimentTests(unittest.TestCase):
    def test_complete_records_materials_lods_and_collision_are_preserved(self):
        p=np.array([[0.,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,0],[1,1,0],[0,1,0]])
        triangles=np.array([[4,5,6],[0,1,2],[0,2,3]])
        uv=p[:,:2].copy();uv2=uv*.23;colors=np.full((len(p),4),255,np.uint8)
        # Equal position, distinct colour and UV must remain separate vertices.
        colors[4,0]=100;uv[5,0]+=.05
        for collision in (False,True):
            data=cdae.encode(p,triangles,uvs=uv,uvs2=uv2,colors=colors,material=['a','b'],
                tri_materials=np.array([1,0,1]),collision_only=collision,
                lods=[(200,dict(positions=p,tris=triangles,uvs=uv,uvs2=uv2,colors=colors,tri_materials=np.array([1,0,1])))])
            candidate,saved=compact(data);before=cdae.decode(data);after=cdae.decode(candidate)
            for field in ('names','details','bounds','materials','objects','nodes'):self.assertEqual(before[field],after[field])
            for old,new in zip(before['meshes'],after['meshes']):
                if old['type']==4:self.assertEqual(old,new);continue
                fields,records=rows(old);other,shared=rows(new);self.assertEqual(fields,other)
                indices=np.frombuffer(old['indices'][2],'<u4');mapped=np.frombuffer(new['indices'][2],'<u4')
                np.testing.assert_array_equal(records[indices],shared[mapped])
                self.assertEqual(old['primitives'],new['primitives'])
                order=list(dict.fromkeys(mapped.tolist()))
                self.assertEqual(order,list(range(len(shared))))
            self.assertGreater(saved,0)


if __name__=='__main__':unittest.main()
