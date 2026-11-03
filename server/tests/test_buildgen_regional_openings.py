import math
import unittest
from types import SimpleNamespace
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('regional_openings', Path(__file__).parents[1] / 'buildgen' / 'regional_openings.py')
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
draw_arch=module.draw_arch

class Mesh:
    def __init__(self): self.faces=[]
    def quad(self,*args): self.faces.append((args[:4],args[-1]))
    def tri(self,*args): self.faces.append((args[:3],args[-1]))

def at(s,z,d): return (s,d,z)

class ArchTests(unittest.TestCase):
    def test_bounded_clear_and_lite_mask(self):
        for shape in ('arched','segmental'):
            for lite in (False,True):
                mesh=Mesh(); opening=SimpleNamespace(left=2.,right=4.,bottom=1.,top=3.)
                draw_arch(mesh,opening,at,'wall','trim',.12,.08,shape,lite)
                self.assertLessEqual(len(mesh.faces),40)
                for points,material in mesh.faces:
                    for x,y,z in points:
                        self.assertTrue(all(math.isfinite(v) for v in (x,y,z)))
                        self.assertTrue(1.92-1e-9<=x<=4.08+1e-9 and .92-1e-9<=z<=3.08+1e-9)
                        self.assertTrue(-.12-1e-9<=y<=.027+1e-9)
                    xs=[p[0] for p in points]; zs=[p[2] for p in points]
                    self.assertFalse(min(xs)<3.<max(xs) and min(zs)<1.8<max(zs))
                fronts=[p[1] for pts,mat in mesh.faces if mat=='wall' for p in pts if p[1]>=0]
                self.assertTrue(fronts); self.assertGreaterEqual(min(fronts),.025 if lite else 0.)
    def test_invalid(self):
        o=SimpleNamespace(left=0,right=1,bottom=0,top=2)
        with self.assertRaises(ValueError): draw_arch(Mesh(),o,at,'w','t',.1,.05,'pointed')
        with self.assertRaises(ValueError): draw_arch(Mesh(),o,at,'w','t',-.1,.05)

if __name__=='__main__': unittest.main()
