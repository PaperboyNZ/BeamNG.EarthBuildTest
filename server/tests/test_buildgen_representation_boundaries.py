"""Generic eligibility fallbacks keep all apertures with bounded shallow cost."""
from pathlib import Path
import sys,unittest
from unittest.mock import patch
import numpy as np
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[2]/'tools')]
import buildings as b
from buildgen import facades,freeze_items
from benchmark_representation_boundaries import fixtures


class RepresentationBoundaryTests(unittest.TestCase):
    def test_fallback_preserves_plans_bounds_and_physics_with_lower_cost(self):
        counts={}
        for name,spec in fixtures():
            items=freeze_items([(spec,0.,0.)]);plan=items[0][0].facades
            physical=b.collision_mesh(items)
            with patch.object(facades,'shallow_openings',return_value=frozenset()):reference=b.build(items)
            after=b.build(items);counts[name]=len(after[0])
            self.assertEqual(items[0][0].facades,plan)
            np.testing.assert_allclose(after[0].min(axis=0),reference[0].min(axis=0),atol=1e-10)
            np.testing.assert_allclose(after[0].max(axis=0),reference[0].max(axis=0),atol=1e-10)
            for field in (0,1,2,3,5):np.testing.assert_array_equal(physical[field],b.collision_mesh(items)[field])
            if name in ('fallback49','courtyard48','complex49','generic_glass80'):
                self.assertLess(len(after[0]),len(reference[0])*.65,name)
                # Every accepted upper pane still has its four glass vertices.
                # This catches a budget that silently drops rows or windows.
                for elevation in plan.elevations:
                    shallow=facades.shallow_openings(items[0][0],elevation,None,None,False)
                    for op in shallow:
                        self.assertGreaterEqual(np.count_nonzero(np.isclose(after[0][:,2],op.top,atol=1e-8)),2)
                    if shallow:
                        op=next(iter(shallow));ring=items[0][0].footprint.outer
                        if elevation.boundary:ring=items[0][0].footprint.holes[elevation.boundary-1]
                        a=np.array(ring[elevation.edge]);direction=(np.array(ring[(elevation.edge+1)%len(ring)])-a)/elevation.length
                        xy=a+direction*op.left+np.array([direction[1],-direction[0]])*(-(op.depth or facades.REVEAL))
                        self.assertLess(np.linalg.norm(after[0]-(*xy,op.top),axis=1).min(),1e-6)
            else:self.assertEqual(len(after[0]),len(reference[0]))
        # The old fallback has 1,764 apertures versus 193 for the designed block.
        # Retaining every accepted recess explains the remaining near-tier cost;
        # its increase is now bounded, rather than the former 4.8x jump.
        self.assertLess(counts['fallback49']/counts['block48'],2.5)

    def test_street_rows_and_explicit_deep_assemblies_are_never_flattened(self):
        from dataclasses import replace
        _,spec=next((n,s) for n,s in fixtures() if n=='fallback49')
        plan=freeze_items([(spec,0.,0.)])[0][0].facades;elevation=plan.elevations[0]
        upper=next(op for op in elevation.openings if op.floor==3)
        protected=(replace(upper,depth=.5),replace(upper,assembly='gallery'))
        modified=replace(elevation,openings=elevation.openings+protected)
        chosen=facades.shallow_openings(spec,modified,None,None,False)
        self.assertTrue(chosen)
        self.assertTrue(all(op.floor>=2 for op in chosen))
        self.assertFalse(any(op in chosen for op in protected))


if __name__=='__main__':unittest.main()
