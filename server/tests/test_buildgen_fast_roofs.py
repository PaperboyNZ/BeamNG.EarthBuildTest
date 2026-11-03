"""Regional silhouettes, exact occupied area, and stable accepted roof recipes."""
from dataclasses import replace
from pathlib import Path
import pickle
import sys
import unittest
from unittest.mock import patch
import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import fast_roofs as fast, roofs, quality, freeze_items, roof_edges
from buildgen.topology import Footprint
from test_buildgen_regions import building, architecture


def shapes():
    return (
        Footprint(((0,0),(18,0),(18,10),(0,10))),
        Footprint(((0,0),(18,1),(16,10),(2,9))),
        Footprint(((0,0),(18,0),(18,6),(7,6),(7,14),(0,14))),
        Footprint(((0,0),(18,0),(18,5),(12,5),(12,14),(6,14),(6,5),(0,5))),
        Footprint(((0,0),(18,0),(18,14),(12,14),(12,5),(6,5),(6,14),(0,14))),
        Footprint(((0,0),(18,0),(18,14),(0,14)),(((5,4),(5,10),(13,10),(13,4)),)),
        Footprint(((0,0),(18,0),(18,14),(0,14)),
                  (((2,2),(2,5),(5,5),(5,2)),((10,7),(10,12),(15,12),(15,7)))),
    )


class FastRoofTests(unittest.TestCase):
    def test_every_profile_covers_rotated_concave_and_courtyard_shapes(self):
        for n,original in enumerate(shapes()):
            for angle in (0.,.41,1.7):
                c,s=np.cos(angle),np.sin(angle)
                def rotate(ring):return tuple((103.+c*x-s*y,-57.+s*x+c*y) for x,y in ring)
                fp=Footprint(rotate(original.outer),tuple(rotate(h) for h in original.holes))
                for kind in ('gabled','hipped'):
                    for variant in sorted(fast.VARIANTS):
                        with self.subTest(shape=n,angle=angle,kind=kind,variant=variant):
                            with patch.object(Footprint,'half',side_effect=AssertionError('GEOS clipping')):
                                roof=fast.envelope(fp,kind,variant)
                            faces=[Polygon([p[:2] for p in t]) for t in roof.triangles]
                            cover=unary_union(faces)
                            self.assertLess(cover.symmetric_difference(fp.shape()).area,1e-7)
                            self.assertAlmostEqual(sum(f.area for f in faces),fp.area,places=7)
                            xyz=np.asarray(roof.triangles)
                            self.assertTrue(np.isfinite(xyz).all())
                            self.assertAlmostEqual(xyz[:,:,2].max(),1.)
                            self.assertGreaterEqual(xyz[:,:,2].min(),0.)
                            for tri,i in zip(roof.triangles,roof.triangle_planes):
                                a,b,h=roof.planes[i]
                                for x,y,z in tri:
                                    self.assertAlmostEqual(z,(a*(x-roof.centre[0])+b*(y-roof.centre[1])+h)/roof.peak,places=7)
                            # Walls terminate on the same surface, including hole rings.
                            self.assertAlmostEqual(sum(v-u for u,v in roof.wall_u),fp.shape().length)
                            for p,q in roof.boundary:
                                mid=tuple((a+b)/2 for a,b in zip(p,q))
                                self.assertAlmostEqual(mid[2],max(0.,roof_edges.height(roof,mid)),places=7)

    def test_rectangular_profiles_match_detailed_surface(self):
        fp=shapes()[0]
        for variant in sorted(fast.VARIANTS):
            for kind in ('gabled','hipped'):
                fast_roof=fast.envelope(fp,kind,variant)
                detailed=roofs._envelope(fp,kind,variant)
                for t in fast_roof.triangles:
                    for p in (*t,tuple(np.mean(t,axis=0))):
                        self.assertAlmostEqual(p[2],roof_edges.height(detailed,p),places=7,msg=variant)

    def test_cached_streams_match_scalar_roof_drawing_and_append_offsets(self):
        for fp in (shapes()[0],shapes()[2],shapes()[5]):
            spec=quality.run('minimum',building,'nz_temperate',fp=fp,roof_shape='hipped',roof_height=2.)
            for variant in sorted(fast.VARIANTS):
                spec.inference=replace(spec.inference,roof_variant=variant)
                for top in (-19.,0.,73.25):
                    actual=b.Mesh();expected=b.Mesh();mats=b._Looks(spec.seed)
                    for mesh in (actual,expected):
                        mesh.tri((0,0,0),(1,0,0),(0,1,0),*((0,0),)*3,mats[spec.roof_mat])
                    roofs.draw(actual,spec,top,mats)
                    roofs._draw(expected,spec,top,mats)
                    for a,w in zip(actual.arrays(),expected.arrays()):
                        np.testing.assert_array_equal(a,w)

    def test_envelope_cache_bounds_retained_geometry(self):
        fast.envelope.cache_clear()
        for i in range(1100):fast.envelope(shapes()[0].translated(i*20.,0.),'gabled')
        size=fast.envelope.cache_info()
        self.assertLessEqual(size['entries'],1024)
        self.assertLessEqual(size['vertices'],8192)
        self.assertLessEqual(size['triangles'],16384)

    def test_low_tiers_plan_varied_regional_roofs_without_detailed_solver(self):
        variants=set()
        with patch.object(roofs,'_envelope',side_effect=AssertionError('detailed solver')):
            for tier in ('minimum','very_low','low'):
                for theme in architecture.catalogue():
                    for fp in (shapes()[0],shapes()[2],shapes()[5]):
                        spec=quality.run(tier,building,theme,fp=fp,seed='fast-'+theme)
                        if spec.roof=='flat':continue
                        self.assertEqual(spec.inference.roof_solver,'fast')
                        self.assertGreater(spec.inference.roof_rise,0.)
                        variants.add(spec.inference.roof_variant)
                        self.assertEqual(spec.footprint,fp)
        self.assertGreaterEqual(len(variants),2)
        # Exercise every selectable regional recipe, independently of the small
        # fixture sample's deterministic style probabilities.
        from buildgen.house_styles import HouseStyle
        with patch('buildgen.house_styles.select',return_value=HouseStyle('regional','nz_temperate')), \
             patch('buildgen.architectural_modifiers.select',return_value=()), \
             patch.object(roofs,'_envelope',side_effect=AssertionError('detailed solver')):
            for variant in sorted(fast.VARIANTS-{'standard','industrial_barrel'}):
                with patch('buildgen.residential.roof_options',return_value=((variant,1),)):
                    for fp in (shapes()[0],shapes()[2],shapes()[5]):
                        spec=quality.run('minimum',building,'nz_temperate',fp=fp)
                        self.assertEqual(spec.inference.roof_variant,variant)
                        self.assertGreater(spec.inference.roof_rise,0.)

    def test_accepted_recipe_survives_pickle_and_quality_switches(self):
        # A detailed joined hip must not silently become a clipped box hip on downgrade.
        for planned in ('full','minimum'):
            spec=quality.run(planned,building,'nz_temperate',fp=shapes()[2],roof_shape='hipped')
            items=quality.run(planned,freeze_items,[(spec,0.,0.)])
            frozen=pickle.loads(pickle.dumps(items))[0][0]
            expected=quality.run(planned,roofs.for_spec,frozen)
            collision=quality.run(planned,b.collision_mesh,items)
            for rendered in ('minimum','very_low','low','full'):
                self.assertEqual(quality.run(rendered,roofs.for_spec,frozen),expected)
                for actual,want in zip(quality.run(rendered,b.collision_mesh,items),collision):
                    np.testing.assert_array_equal(actual,want)

    def test_explicit_height_and_outline_share_surface_and_wall_boundary(self):
        fp=shapes()[0]
        spec=quality.run('minimum',building,'nz_temperate',fp=fp,roof_shape='hipped',roof_height=2.)
        spec.roof_outline=fp
        spec.footprint=Footprint(((1,1),(17,1),(17,9),(1,9)))
        spec.ring=np.asarray(spec.footprint.outer)
        wall=roofs.for_spec(spec);surface=roof_edges.for_spec(spec)
        self.assertAlmostEqual(spec.height+spec.inference.roof_rise,8.)
        for p,q in wall.boundary:
            self.assertAlmostEqual(p[2],roof_edges.height(surface,p))
            self.assertAlmostEqual(q[2],roof_edges.height(surface,q))
        self.assertAlmostEqual(sum(Polygon([p[:2] for p in t]).area for t in wall.triangles),spec.footprint.area)

    def test_explicit_flat_roof_and_complexity_limits_remain_authoritative(self):
        spec=quality.run('minimum',building,'nz_temperate',fp=shapes()[2],roof_shape='flat')
        self.assertEqual(spec.roof,'flat')
        angles=np.linspace(0.,2*np.pi,260,endpoint=False)
        fp=Footprint(tuple((10*np.cos(a),10*np.sin(a)) for a in angles))
        spec=quality.run('minimum',building,'nz_temperate',fp=fp,roof_shape='gabled')
        self.assertEqual(spec.roof,'flat')


if __name__=='__main__':unittest.main()
