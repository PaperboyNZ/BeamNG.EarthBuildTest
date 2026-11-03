"""Stock landscaping placements stay inside accepted soft surfaces."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np
from shapely.geometry import Point, Polygon
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import landscaping
from buildgen.access import AccessPlan, Solid
from test_buildgen_facades import building


def example(kind='site_garden_bed',width=3.,length=30.,seed='native',cls='supermarket'):
    spec=building(30,16,**{'class':cls,'height':6.,'seed_id':seed})
    p=((0,-10,0),(length,-10,0),(length,-10+width,0),(0,-10+width,0))
    spec.access=AccessPlan(0.,None,(),landscape=(Solid(kind,p,-.1),))
    return spec


class NativeLandscapingTests(unittest.TestCase):
    def test_rows_exactly_match_original_across_width_seed_and_support_cases(self):
        # Keep a fixed pre-optimization oracle rather than importing another
        # checkout, whose source and imports could silently change underneath us.
        namespace=dict(vars(landscaping))
        reference=Path(__file__).with_name('fixtures')/'native_props_before_performance.txt'
        exec(compile(reference.read_text(encoding='utf-8'),str(reference),'exec'),namespace)
        original=namespace['native_props']
        for width in (1.,1.2511,1.2512,1.3,2.,3.,6.,8.):
            for seed in range(6):
                for terrain in ('flat','slope','steep','twisted'):
                    spec=example(width=width,seed=str(seed));band=spec.access.landscape[0]
                    top=np.array(band.top,float)
                    if terrain=='slope':top[:,2]=.03*top[:,0]
                    elif terrain=='steep':top[:,2]=.1*top[:,0]
                    elif terrain=='twisted':top[:,2]=(.0,.3,.05,-.1)
                    spec.access=replace(spec.access,landscape=(replace(band,top=tuple(map(tuple,top))),))
                    with self.subTest(width=width,seed=seed,terrain=terrain):
                        self.assertEqual(original(spec),landscaping.native_props(spec))
        # A failed narrow bed must preserve allowances and output ordering for
        # later beds, including the 48-plant total and per-bed limits.
        for seed in range(6):
            spec=example(width=1.2511,seed=str(seed));narrow=spec.access.landscape[0]
            broad=replace(narrow,top=((0,-30,0),(30,-30,0),(30,-24,0),(0,-24,0)))
            for beds in ((narrow,broad),(broad,narrow),(narrow,broad,narrow,broad)):
                spec.access=replace(spec.access,landscape=beds)
                self.assertEqual(original(spec,123.,-456.),landscaping.native_props(spec,123.,-456.))

    def test_only_exact_horizontal_valid_contained_footprints_bypass_support_solver(self):
        spec=example(width=6.)
        with patch.object(landscaping,'_support_range',side_effect=AssertionError('flat solver')):
            self.assertTrue(landscaping.native_props(spec))
            # Candidates outside the accepted footprint cannot use a known
            # horizontal datum to manufacture a supported plant.
            with patch.object(landscaping,'_point',return_value=np.array([100.,100.,0.])):
                self.assertEqual(landscaping.native_props(spec),[])
            bad=((0,-12,0),(30,-12,0),(1,-10,0),(0,-6,0))
            spec.access=replace(spec.access,landscape=(Solid('site_garden_bed',bad,-1.),))
            self.assertEqual(landscaping.native_props(spec),[])
        for heights in ((0.,.9,.9,0.),(0.,.3,.05,-.1),(1.,1.,np.nextafter(1.,2.),1.)):
            spec=example(width=6.);band=spec.access.landscape[0]
            top=tuple((x,y,z) for (x,y,_),z in zip(band.top,heights))
            spec.access=replace(spec.access,landscape=(replace(band,top=top),))
            with patch.object(landscaping,'_support_range',wraps=landscaping._support_range) as solver:
                self.assertTrue(landscaping.native_props(spec))
                self.assertGreater(solver.call_count,0)
        # The general helper has no native_props containment precondition.
        # A horizontal patch cannot support a circle entirely outside it.
        p=np.array(example(width=6.).access.landscape[0].top,float)
        self.assertIsNone(landscaping._support_range(p,(100.,100.),.5))

    def test_impossible_beds_do_not_generate_candidates(self):
        with patch.object(landscaping,'_point',side_effect=AssertionError('impossible candidate')):
            self.assertEqual(landscaping.native_props(example(width=1.)),[])

    def test_span_rejection_preserves_thresholds_and_later_bed_budgets(self):
        # Disable only the conservative span rejection for a reference run;
        # keep the exact native-size/support and placement tests unchanged.
        broad=Solid('site_garden_bed',((0,-30,0),(30,-30,0),(30,-24,0),(0,-24,0)),-.1)
        for width in (.24,.5,.9,1.,1.24,1.2511,1.2512,1.3,2.,3.,6.):
            for seed in range(6):
                spec=example(width=width,seed=str(seed));narrow=spec.access.landscape[0]
                for bands in ((narrow,),(narrow,broad),(broad,narrow),(narrow,broad,narrow,broad)):
                    spec.access=replace(spec.access,landscape=bands)
                    actual=landscaping.native_props(spec)
                    with patch.object(landscaping.np,'ptp',return_value=float('inf')):
                        self.assertEqual(actual,landscaping.native_props(spec),(width,seed))

    def test_both_soft_covers_receive_real_asset_groups(self):
        for kind in ('site_garden_bed','site_lawn_margin'):
            spec=example(kind=kind)
            rows=landscaping.native_props(spec)
            self.assertEqual({r[0] for r in rows},{'site_shrub','site_rock'})
            self.assertGreater(len(rows),5)
            self.assertLessEqual(len(rows),landscaping.MAX_SITE_PLANTS)
            self.assertEqual(rows,b.landscape_props([(spec,0,0)],0,0))

    def test_full_native_envelopes_fit_skew_and_sloped_beds(self):
        spec=example()
        for points in (((0,-10,0),(30,-10,0),(28,-7,0),(-2,-7,0)),
                       ((0,-10,-1),(30,-10,2),(30,-7,2.3),(0,-7,-.7))):
            for top in (points,points[::-1]):
                spec.access=replace(spec.access,landscape=(Solid('site_garden_bed',top,-2),))
                rows=landscaping.native_props(spec)
                self.assertTrue(rows)
                boundary=Polygon([p[:2] for p in top])
                for row in rows:
                    self.assertTrue(np.isfinite(row[1:]).all())
                    centre=Point(row[1:3])
                    self.assertTrue(boundary.covers(centre))
                    self.assertGreaterEqual(boundary.boundary.distance(centre),landscaping.native_radius(row[0],row[6]))
                    radius,nominal,zmin=landscaping.NATIVE_ASSETS[row[0]]
                    foot=row[3]+zmin*(row[6]/nominal)
                    expected=0 if points[0][2]==0 else .1*row[1]+.1*row[2]
                    drop=0. if points[0][2]==0 else np.sqrt(.02)*radius*(row[6]/nominal)
                    self.assertAlmostEqual(foot,expected-drop-.018,places=6)

    def test_hardscape_and_native_minimum_size_are_respected(self):
        spec=example()
        blocker=Solid('site_walk',((10,-11,0),(15,-11,0),(15,-6,0),(10,-6,0)),-.2)
        spec.access=replace(spec.access,solids=(blocker,))
        hard=Polygon([p[:2] for p in blocker.top])
        rows=landscaping.native_props(spec)
        self.assertTrue(rows)
        for row in rows:
            self.assertGreater(hard.distance(Point(row[1:3])),landscaping.native_radius(row[0],row[6]))
        self.assertEqual(landscaping.native_props(example(width=1.)),[])
        self.assertEqual(landscaping.native_props(example(kind='site_paved_margin')),[])

    def test_only_cover_geometry_in_both_building_lods(self):
        spec=example()
        outputs=[]
        for detail in (True,False):
            mesh=b.Mesh();landscaping.draw(mesh,spec,detail)
            arrays=mesh.arrays();outputs.append(arrays)
            self.assertEqual(len(arrays[2]),2)
            self.assertNotIn(b.MATERIALS.index(b.FOLIAGE),arrays[3])
            self.assertNotIn(b.MATERIALS.index(b.STONE),arrays[3])
        for a,c in zip(*outputs):np.testing.assert_array_equal(a,c)

    def test_determinism_rebase_variation_and_no_collision_mesh_additions(self):
        spec=example();rows=landscaping.native_props(spec)
        self.assertEqual(rows,landscaping.native_props(spec))
        self.assertNotEqual(rows,landscaping.native_props(example(seed='different')))
        shifted=landscaping.native_props(spec,1000,-2000)
        for row,moved in zip(rows,shifted):
            self.assertEqual(row[0],moved[0]);self.assertEqual(row[3:],moved[3:])
            np.testing.assert_allclose(np.array(moved[1:3])-row[1:3],[1000,-2000])
        before=b.collision_mesh([(spec,0,0)])
        spec.access=replace(spec.access,landscape=())
        after=b.collision_mesh([(spec,0,0)])
        for a,c in zip(before,after):np.testing.assert_array_equal(a,c)

    def test_budget_and_explicit_industrial_beds(self):
        spec=example(cls='workshop',length=100.)
        self.assertTrue(landscaping.native_props(spec))
        band=spec.access.landscape[0]
        beds=tuple(replace(band,top=tuple((x,y-5*k,z) for x,y,z in band.top)) for k in range(16))
        spec.access=replace(spec.access,landscape=beds)
        rows=landscaping.native_props(spec)
        self.assertLessEqual(len(rows),landscaping.MAX_SITE_PLANTS)
        self.assertGreater(len(rows),20)
        self.assertEqual(landscaping.native_props(example(cls='workshop',kind='garden_bed')),[])

    def test_organic_spacing_uses_bed_width_without_overlapping_native_envelopes(self):
        spec=example(width=8.)
        rows=landscaping.native_props(spec)
        self.assertGreater(len(rows),15)
        self.assertGreater(np.ptp([r[2] for r in rows]),4.)
        self.assertGreater(np.std(np.diff(sorted(r[1] for r in rows))),.2)
        for i,row in enumerate(rows):
            radius=landscaping.native_radius(row[0],row[6])
            for other in rows[i+1:]:
                self.assertGreaterEqual(np.linalg.norm(np.array(row[1:3])-other[1:3]),
                                        radius+landscaping.native_radius(other[0],other[6]))
        # Irregular strip planting, not the former nearly-perfect straight row.
        narrow=landscaping.native_props(example(width=3.))
        self.assertGreater(np.ptp([r[2] for r in narrow]),.4)
        self.assertGreater(np.std(np.diff(sorted(r[1] for r in narrow))),.2)

    def test_twisted_terrain_uses_rendered_triangles_and_entire_native_support(self):
        spec=example(width=6.)
        top=((0,-12,110.),(30,-12,110.3),(28,-6,110.05),(-2,-6,109.9))
        spec.access=replace(spec.access,landscape=(Solid('site_garden_bed',top,109.),))
        mesh=b.Mesh();landscaping.draw(mesh,spec,True)
        positions,_,triangles,*_=mesh.arrays()
        rows=landscaping.native_props(spec)
        self.assertGreater(len(rows),10)
        def surface_height(q):
            for tri in positions[triangles]:
                # Independent barycentric interpolation of actual emitted faces.
                weights=np.linalg.solve(np.vstack((tri[:,:2].T,np.ones(3))),np.r_[q,1.])
                if weights.min()>=-1e-6:return float(weights@tri[:,2])
            self.fail('native envelope escaped rendered cover')
        for row in rows:
            radius,nominal,zmin=landscaping.NATIVE_ASSETS[row[0]]
            physical=radius*row[6]/nominal
            foot=row[3]+zmin*row[6]/nominal
            probes=[surface_height(np.array(row[1:3])+physical*r*np.array([np.cos(a),np.sin(a)]))
                    for r in (0.,.5,1.) for a in np.linspace(0,2*np.pi,80,endpoint=False)]
            self.assertLessEqual(foot,min(probes)+1e-4)
            self.assertAlmostEqual(foot,min(probes)-.018,delta=.001)
            self.assertLessEqual(max(probes)-foot,min(.28,row[6]*.4)+.019)

    def test_ground_and_frame_offsets_preserve_placements_and_support(self):
        spec=example(width=6.);original=landscaping.native_props(spec)
        # Translate both the bed and building frame; elevation offset must shift
        # every asset origin exactly without changing its selection or scale.
        shift=np.array([12345.,-6789.,83.7])
        band=spec.access.landscape[0]
        spec.access=replace(spec.access,landscape=(replace(band,
            top=tuple(tuple(np.array(p)+shift) for p in band.top),bottom=band.bottom+shift[2]),))
        moved=landscaping.native_props(spec)
        self.assertEqual(len(original),len(moved))
        for a,c in zip(original,moved):
            self.assertEqual(a[0],c[0])
            np.testing.assert_allclose(np.array(c[1:4])-a[1:4],shift,atol=1e-8)
            np.testing.assert_allclose(a[4:],c[4:],atol=1e-9)

    def test_rotated_skewed_beds_and_unsupported_shapes_fail_safely(self):
        spec=example(width=6.)
        points=np.array(((0,-12,0),(30,-12,0),(28,-6,0),(-2,-6,0)),float)
        angle=.73;rotation=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
        points[:,:2]=points[:,:2]@rotation.T+np.array([100,-120])
        points[:,2]=1.+.03*points[:,0]-.02*points[:,1]
        spec.access=replace(spec.access,landscape=(Solid('site_garden_bed',tuple(map(tuple,points)),-10.),))
        rows=landscaping.native_props(spec)
        self.assertGreater(len(rows),10)
        boundary=Polygon(points[:,:2])
        for row in rows:
            self.assertGreaterEqual(boundary.boundary.distance(Point(row[1:3])),
                                    landscaping.native_radius(row[0],row[6]))
        for bad in (((0,-12,0),(30,-12,0),(1,-10,0),(0,-6,0)),
                    ((0,-12,0),(30,-12,0),(30,-6,float('nan')),(0,-6,0))):
            spec.access=replace(spec.access,landscape=(Solid('site_garden_bed',bad,-1.),))
            self.assertEqual(landscaping.native_props(spec),[])

    def test_missing_access_or_legacy_inference_is_empty(self):
        spec=example();spec.access=None
        self.assertEqual(landscaping.native_props(spec),[])
        spec=example();spec.inference=None
        self.assertEqual(landscaping.native_props(spec),[])


if __name__=='__main__':unittest.main()
