"""Reusable construction geometry: orientation, seams, paint and cache limits."""
import math
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import components as c


def reference_beam(mesh, a, end, radius, mat, sides=8):
    a, end = np.asarray(a, float), np.asarray(end, float)
    d = end-a
    length = float(np.linalg.norm(d))
    if length < 1e-7:
        return
    d /= length
    ref = np.array([0., 0., 1.]) if abs(d[2]) < .9 else np.array([1., 0., 0.])
    u = np.cross(d, ref); u /= np.linalg.norm(u)
    v = np.cross(d, u)
    ring = [radius*(u*math.cos(i*2*math.pi/sides)+v*math.sin(i*2*math.pi/sides)) for i in range(sides)]
    for i, p in enumerate(ring):
        q = ring[(i+1)%sides]
        mesh.quad(a+p, a+q, end+q, end+p, *c.UV, mat)
        mesh.tri(a, a+q, a+p, (.5,.5), (1.,1.), (0.,0.), mat)
        mesh.tri(end, end+p, end+q, (.5,.5), (0.,0.), (1.,1.), mat)


class ComponentsTest(unittest.TestCase):
    def compare(self, a, expected):
        aa, bb = a.arrays(), expected.arrays()
        np.testing.assert_allclose(aa[0], bb[0], atol=2e-10, rtol=0)
        np.testing.assert_allclose(aa[1], bb[1], atol=2e-10, rtol=0)
        for k in (2,3,4):
            np.testing.assert_array_equal(aa[k], bb[k])

    def test_pipe_directions_caps_and_prior_mesh_offset(self):
        rng = np.random.default_rng(71)
        for d in [(0.,0.,0.), (0.,0.,3.), (0.,0.,-3.), (3.,0.,0.), *rng.normal(size=(50,3))]:
            for sides in (6,8):
                a, old = b.Mesh(), b.Mesh()
                start = np.array([1000., -2000., 7.])
                for m in (a,old):
                    m.tri((0,0,0),(1,0,0),(0,1,0),(0,0),(1,0),(0,1),(2,(1,2,3,255)))
                c.beam(a,start,start+d,.04,(3,(40,50,60,255)),sides)
                reference_beam(old,start,start+d,.04,(3,(40,50,60,255)),sides)
                self.compare(a,old)

    def test_surround_preserves_reveal_and_affine_uvs(self):
        for angle in (0., .47, 2.8):
            ax,ay,dx,dy,base = 45.,-90.,math.cos(angle),math.sin(angle),11.
            x0,x1,z0,z1,frame,reveal,run = 2.3,4.2,1.1,3.4,.065,.09,17.
            def at(s,z,depth=0.):return (ax+dx*s+dy*depth,ay+dy*s-dx*depth,base+z)
            a,old=b.Mesh(),b.Mesh();mat=(3,(34,54,75,255))
            c.facade(a,c.surround(x1-x0,z1-z0,frame,reveal),(ax,ay),(dx,dy),base,x0,z0,mat,(run,2.4,3.))
            corners=((x0,z0),(x1,z0),(x1,z1),(x0,z1))
            for p,q in zip(corners,corners[1:]+corners[:1]):
                old.quad(at(*p),at(*q),at(*q,-reveal),at(*p,-reveal),(0,0),(1,0),(1,.1),(0,.1),mat)
            for l,r,lo,hi in ((x0-frame,x0,z0-frame,z1+frame),(x1,x1+frame,z0-frame,z1+frame),
                               (x0,x1,z0-frame,z0),(x0,x1,z1,z1+frame)):
                old.quad(at(l,lo,.018),at(r,lo,.018),at(r,hi,.018),at(l,hi,.018),
                         ((run+l)/2.4,lo/3),((run+r)/2.4,lo/3),((run+r)/2.4,hi/3),((run+l)/2.4,hi/3),mat)
            self.compare(a,old)

    def test_sill_closed_returns_and_paint_independence(self):
        template=c.sill(2.,.12,.07)
        for paint in ((20,50,90,255),(230,220,200,255)):
            m=b.Mesh();c.facade(m,template,(0,0),(1,0),0.,0.,0.,(3,paint))
            self.assertEqual(m.n,20)
            self.assertEqual(len(m.T),30)
            self.assertEqual(set(map(tuple,m.arrays()[4])),{paint})
        self.assertIs(template,c.sill(2.,.12,.07))
        for a in template:
            self.assertFalse(a.flags.writeable)

    def test_cache_capacity_and_clear(self):
        c.clear()
        for i in range(300):c.surround(1.+i/1000,2.,.06,.09);c.sill(1.+i/1000,.12,.07)
        for i in range(40):c.pipe(.01+i/1000,8)
        for info in c.cache_info().values():self.assertLessEqual(info['currsize'],info['maxsize'])
        c.clear()
        self.assertTrue(all(v['currsize']==0 for v in c.cache_info().values()))


if __name__ == '__main__':unittest.main()
