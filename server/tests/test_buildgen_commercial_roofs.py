"""Roof evidence, watertight coverage, support, tier parity and hard budgets."""
from dataclasses import replace
from pathlib import Path
import pickle
import sys
import unittest
from unittest.mock import patch

import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import buildings as b
import cdae
from buildgen import commercial_roofs as cr, freeze_items, roofs, roof_edges, materials
from buildgen.geometry import sky_vertex_count
from buildgen.topology import Footprint
from test_buildgen_facades import building
from building_fixtures import transform


def fixture(form=None, **attrs):
    values = dict(height=9., num_floors=1, seed_id='commercial-roof', **{'class': 'industrial'})
    values.update(attrs)
    choose = materials.choose
    def select(identity, channel, options):
        return form if form is not None and channel == 'ci-roof-form-v1' else choose(identity, channel, options)
    with patch.object(materials, 'choose', side_effect=select):
        return building(60., 25., **values)


class CommercialRoofsTest(unittest.TestCase):
    def test_generic_population_reaches_five_forms_and_bounded_heights(self):
        for cls in ('industrial', 'commercial', 'factory'):
            forms = set()
            for seed in range(160):
                s = fixture(seed_id=str(seed), **{'class': cls})
                forms.add(s.roof if s.roof == 'flat' else s.inference.roof_variant)
                self.assertLessEqual(s.inference.roof_rise, 2.8)
                self.assertAlmostEqual(s.height + s.inference.roof_rise, 9.)
            self.assertEqual(forms, {'flat', 'standard', 'shed', 'saltbox', 'industrial_barrel'})

    def test_mapped_roofs_materials_heights_and_parts_win(self):
        for kind in ('flat', 'gabled', 'hipped'):
            s = fixture('industrial_barrel', roof_shape=kind, roof_material='slate', roof_height=1.4)
            self.assertEqual((s.roof, s.inference.roof_variant), (kind, 'standard'))
            self.assertEqual(s.inference.roof_material.value, 'slate')
            if kind != 'flat': self.assertEqual(s.inference.roof_rise, 1.4)
        s = fixture('shed', _part=True, roof_shape='flat')
        self.assertEqual(cr.plan(s), ())
        for cls in ('house', 'office', 'warehouse', 'church', 'hangar'):
            s = fixture(**{'class': cls})
            self.assertNotEqual(s.inference.roof.source if s.inference else '', 'sparse_use_roof_prior_v1')
            self.assertFalse(cr.eligible(s))

    def test_unsuitable_footprints_and_tall_blocks_do_not_get_hall_roofs(self):
        for s in (fixture(height=30., num_floors=8),
                  fixture(fp=Footprint(((0,0),(30,0),(30,8),(8,8),(8,30),(0,30))))):
            self.assertNotEqual(s.inference.roof.source, 'sparse_use_roof_prior_v1')

    def test_barrel_coverage_planes_and_uv_export_after_transform(self):
        outer = ((0.,0.),(60.,0.),(59.6,25.),(.2,25.))
        for angle, offset in ((0.,(0.,0.)), (37.,(8100.,-6300.))):
            fp = Footprint(transform(outer,angle,1.,offset))
            s = fixture('industrial_barrel', fp=fp)
            roof = roofs.for_spec(s)
            pieces = [Polygon([p[:2] for p in t]) for t in roof.triangles]
            self.assertLess(unary_union(pieces).symmetric_difference(fp.shape()).area, 1e-6)
            self.assertAlmostEqual(sum(p.area for p in pieces), fp.area, places=5)
            self.assertEqual(len(set(roof.triangle_planes)), 6)
            self.assertLessEqual(len(roof.triangles), 24)
            for t,pid in zip(roof.triangles,roof.triangle_planes):
                ax,ay,z = roof.planes[pid]
                for x,y,h in t:
                    self.assertAlmostEqual(h, ((x-roof.centre[0])*ax+(y-roof.centre[1])*ay+z)/roof.peak)
            mesh = b.Mesh(); roofs.draw(mesh,s,s.height,b._Looks(s.seed),overhang=True)
            p,uv,t,mid,colors = mesh.arrays()
            data = cdae.decode(cdae.encode(p,t,uvs=uv,material=list(b.MATERIALS),tri_materials=mid,colors=colors))
            for compiled in data['meshes']:
                arrays = cdae.mesh_arrays(compiled)
                for key in ('verts','tverts','norms','tangents'):
                    self.assertTrue(np.isfinite(arrays[key]).all())

    def test_roof_shell_agrees_across_lods_collision_and_sky(self):
        for form in ('standard','shed','saltbox','industrial_barrel'):
            s = fixture(form)
            items = freeze_items([(s,0.,0.)])
            with patch.object(cr, 'draw'):
                for mesh in (b.build(items), b.build(items,lite=True), b.collision_mesh(items), b._sky_mesh(items)):
                    self.assertAlmostEqual(float(mesh[0][:,2].max()),9.,places=5)
                    self.assertTrue(np.isfinite(mesh[0]).all())
            sky = b._sky_mesh(items)
            self.assertEqual(len(sky[0]), sky_vertex_count(items[0][0]))

    def test_detail_containment_spacing_and_surface_support(self):
        courtyard = Footprint(((0,0),(60,0),(60,40),(0,40)),
                              (((20,10),(20,30),(40,30),(40,10)),))
        for form in ('flat','standard','shed','saltbox','industrial_barrel'):
            for fp in (None,courtyard):
                for seed in range(8):
                    s = fixture(form, fp=fp, seed_id=str(seed))
                    details = cr.plan(s)
                    self.assertLessEqual(len(details),cr.MAX_DETAILS)
                    shapes = [Polygon(d.corners) for d in details]
                    for shape in shapes:
                        self.assertTrue(s.footprint.shape().buffer(-cr.EDGE_SETBACK+.000001,join_style=2).covers(shape))
                    for i,a in enumerate(shapes):
                        for z in shapes[i+1:]:self.assertGreaterEqual(a.distance(z),cr.GAP)
                    roof = roof_edges.for_spec(s) if s.roof != 'flat' else None
                    for detail in details:
                        for xy,lo,hi in zip(detail.corners,detail.bottom,detail.top):
                            z = roof_edges.height(roof,xy)*s.inference.roof_rise if roof else 0.
                            self.assertAlmostEqual(lo,z-.025)
                            self.assertGreater(hi,z)

    def test_details_have_fixed_cost_and_survive_frozen_plan(self):
        kinds = set()
        for seed in range(24):
            s = fixture('flat',seed_id=str(seed))
            frozen = pickle.loads(pickle.dumps(freeze_items([(s,0.,0.)])))[0][0]
            self.assertEqual(cr.plan(s),cr.plan(frozen))
            kinds.update(d.kind for d in cr.plan(s))
            for lite in (False,True):
                mesh=b.Mesh();cr.draw(mesh,s,s.height,b._Looks(s.seed),lite=lite)
                p,uv,t,_,_=mesh.arrays()
                self.assertLessEqual(len(t),20 if lite else 128)
                self.assertTrue(np.isfinite(p).all() and np.isfinite(uv).all())
                if lite:
                    self.assertEqual(len(t),sum(10 if d.kind=='hvac' else 2 if d.kind in ('solar','rooflight') else 0 for d in cr.plan(s)))
        self.assertEqual(kinds,{'hvac','duct','vent','hatch','solar','rooflight'})
        self.assertEqual(cr._plan.cache_info().maxsize,512)

    def test_no_legacy_duplicates_or_detail_collision(self):
        s = fixture('flat')
        with patch.object(b,'_clutter') as legacy:
            b.build([(s,0.,0.)])
            legacy.assert_not_called()
        with patch.object(cr,'draw') as draw:
            b.collision_mesh(freeze_items([(s,0.,0.)])); b._sky_mesh(freeze_items([(s,0.,0.)]))
            draw.assert_not_called()


if __name__ == '__main__':
    unittest.main()
