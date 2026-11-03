"""Preset/zone semantics, imported overlays and architectural regression checks."""
from dataclasses import replace
import json
from pathlib import Path
import pickle
import sys
import tempfile
import subprocess
import unittest
from unittest.mock import patch

import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import BuildingPlan, facades, presets, roofs, zones
from buildgen.context import Context, Provider
from buildgen.topology import Footprint
from test_buildgen_inference import planned
from test_buildgen_facades import building, road
from test_buildgen_context import MapData, geographic, rect


def zone(meaning='statutory',uses=('industrial',),**kw):
    return zones.Zone('test-source','2026','test-lineage','X',meaning,uses,1.,**kw)


class PresetTests(unittest.TestCase):
    def test_permissions_and_future_plans_cannot_invent_existing_use(self):
        for z in (zone(), zone('planned'), zone('observed',status='proposed'),zone('observed',status='superseded')):
            result=planned(ctx=Context(zones=(z,)*20)).inference
            self.assertEqual(result.use.value,'unknown')
            self.assertEqual(result.selection.preset.id,'unresolved_shell')

    def test_observed_zone_changes_use_but_not_mapped_building(self):
        ctx=Context(zones=(zone('observed'),))
        self.assertEqual(planned(ctx=ctx).inference.selection.preset.use,'industrial')
        self.assertIn('sparse_use_architecture_v1',planned(ctx=ctx).inference.selection.reasons)
        spec=planned({'class':'house','height':7.},ctx)
        self.assertEqual(spec.inference.selection.preset.id,'detached_house')
        self.assertEqual(spec.inference.height.value,7.)
        result=planned({'class':'house'},Context(zones=(zone(),))).inference
        self.assertTrue(any(d.startswith('mapped_use_differs_from_zone:') for d in result.diagnostics))

    def test_correlated_sources_and_ambiguous_classes_do_not_add_certainty(self):
        a=planned(ctx=Context(zones=(zone('observed'),))).inference
        c=planned(ctx=Context(zones=(zone('observed'),)*100)).inference
        self.assertEqual(a.candidates,c.candidates)
        result=planned(ctx=Context(zones=(zone('observed',('industrial','commercial','civic')),))).inference
        self.assertEqual(result.use.value,'unknown')

    def test_footprint_and_floor_fit_reject_incompatible_specific_form(self):
        spec=planned({'class':'bungalow','height':40.,'num_floors':10})
        self.assertNotEqual(spec.inference.selection.preset.id,'bungalow')
        self.assertEqual(spec.inference.height.value,40.)

    def test_neighbourhood_is_explained_and_unknown_is_not_a_house(self):
        result=planned(ctx=Context(land_use=(('residential',1.),))).inference
        self.assertEqual(result.use.value,'residential')
        self.assertTrue(any(r.startswith('observed_land_use:residential') for r in result.selection.reasons))
        self.assertEqual(planned().inference.selection.preset.id,'unresolved_shell')

    def test_climate_changes_shading_without_changing_identity_or_observations(self):
        attrs={'class':'house','roof_shape':'hipped','facade_material':'brick'}
        hot=planned(attrs,Context(climate=2))
        cold=planned(attrs,Context(climate=25))
        self.assertEqual(hot.inference.selection.preset,cold.inference.selection.preset)
        self.assertEqual(hot.inference.selection.climate_response,'solar_shading')
        self.assertEqual(cold.inference.selection.climate_response,'cold_climate')
        self.assertEqual(hot.inference.facade.value,'brick')
        self.assertGreater(len(b.build([(hot,0.,0.)])[0]),len(b.build([(cold,0.,0.)])[0]))

    def test_service_shutter_reserves_wall_and_preserves_opening_clearance(self):
        spec=building(18.,12.,**{'class':'workshop','height':5.,'roof_shape':'flat'})
        b.doors([(spec,0.,0.)],road(),0.,0.)
        layout=facades.plan(spec,0.,0.)
        openings=[op for e in layout.elevations for op in e.openings if e.edge==spec.front and e.boundary==0]
        self.assertEqual(sum(op.kind=='service' for op in openings),1)
        for i,op in enumerate(openings):
            self.assertTrue(all(not op.overlaps(other,.15) for other in openings[i+1:]))
        self.assertTrue(np.isfinite(b.build([(spec,0.,0.)])[0]).all())

    def test_catalogue_is_immutable_at_worker_boundary(self):
        self.assertGreaterEqual(len(presets.catalogue()),36)
        plan=BuildingPlan.from_spec(planned({'class':'school'}))
        self.assertEqual(pickle.loads(pickle.dumps(plan)).inference.selection,plan.inference.selection)

    def test_windowless_warehouse_and_shop_have_grounded_entries(self):
        for cls in ('warehouse','barn','shop','shed'):
            spec=building(18.,12.,**{'class':cls,'height':5.,'roof_shape':'flat'})
            drives=[]
            props=b.doors([(spec,0.,0.)],road(),0.,0.,drives)
            self.assertIsNotNone(spec.door,cls)
            self.assertIsNotNone(spec.access,cls)
            self.assertEqual(drives,[])
            self.assertTrue(any(p[0]=='door' for p in props))

    def test_geojson_overlay_is_projected_and_courtyard_holes_excluded(self):
        feature=geographic([[[rect(-30,-30,60,60),rect(-10,-10,20,20)]]])
        # Reuse test conversion helper's original geographic geometry.
        from buildgen.ingest import components
        rings=components(feature,0)[0][1]
        data={'type':'FeatureCollection','features':[{'type':'Feature','geometry':{'type':'Polygon','coordinates':rings},
              'properties':dict(source_id='fixture',release='v1',lineage='fixture',raw_code='R',
                                meaning='observed',uses=['residential'],status='effective')}]}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'zones.json'
            path.write_text(json.dumps(data))
            with patch.object(zones,'PATH',path):
                zones.catalogue.cache_clear()
                try:
                    md=MapData()
                    ctx=Provider(md).query(md.buildings,0)
                    self.assertEqual(ctx.zones,()) # target lies inside the zone's hole
                    data['features'][0]['geometry']['coordinates']=rings[:1]
                    path.write_text(json.dumps(data))
                    zones.catalogue.cache_clear()
                    ctx=Provider(md).query(md.buildings,0)
                    self.assertEqual(len(ctx.zones),1)
                    self.assertAlmostEqual(ctx.zones[0].overlap,1.)
                    self.assertIn(('zones',zones.catalogue()[0]),ctx.manifest.sources)
                finally:
                    zones.catalogue.cache_clear()

    def test_importer_rejects_unmapped_codes_and_installs_valid_release(self):
        root=Path(__file__).resolve().parents[2]
        data={'type':'FeatureCollection','features':[{'type':'Feature','geometry':
              {'type':'Polygon','coordinates':[[[9,45],[9.01,45],[9.01,45.01],[9,45.01],[9,45]]]},
              'properties':{'code':'R'}}]}
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            (folder/'input.json').write_text(json.dumps(data))
            (folder/'mapping.json').write_text('{}')
            out=folder/'output.json'
            args=[sys.executable,str(root/'tools/import_building_zones.py'),str(folder/'input.json'),
                  str(folder/'mapping.json'),'--field','code','--source','fixture','--release','v1',
                  '--lineage','fixture','--meaning','statutory','--status','effective','--out',str(out)]
            failed=subprocess.run(args,capture_output=True,text=True)
            self.assertNotEqual(failed.returncode,0)
            self.assertFalse(out.exists())
            (folder/'mapping.json').write_text('{"R":["residential"]}')
            passed=subprocess.run(args,capture_output=True,text=True)
            self.assertEqual(passed.returncode,0,passed.stderr)
            self.assertEqual(zones.load(out)[1][0][1].uses,('residential',))

    def test_catalogue_files_are_in_source_and_package_inputs(self):
        import codefiles
        root=Path(__file__).resolve().parents[2]
        sys.path.insert(0,str(root/'tools'))
        import package
        for name in ('presets.json','zones.json'):
            rel='buildgen/catalog/'+name
            self.assertIn(rel,codefiles.source_files(root/'server'))
            self.assertIn('server/'+rel,package.collect())


class WingTests(unittest.TestCase):
    def test_courtyard_and_l_wings_have_eaves_at_every_exterior_wall(self):
        cases=[Footprint(((0,0),(20,0),(20,6),(8,6),(8,16),(0,16))),
               Footprint(tuple(rect(0,0,30,24)),(tuple(rect(8,8,14,8)),))]
        for fp in cases:
            roof=roofs.envelope(fp,'hipped')
            self.assertEqual(roof.strategy,'orthogonal_wings')
            self.assertTrue(all(abs(p[2])<1e-8 for edge in roof.boundary for p in edge))
            shapes=[Polygon([(x,y) for x,y,z in t]) for t in roof.triangles]
            self.assertLess(unary_union(shapes).symmetric_difference(fp.shape()).area,1e-6)
            self.assertAlmostEqual(sum(p.area for p in shapes),fp.area)
            # Plane joins are continuous wherever triangles share a vertex.
            heights={}
            for tri in roof.triangles:
                for x,y,z in tri:
                    key=(round(x,6),round(y,6))
                    if key in heights:
                        self.assertAlmostEqual(z,heights[key],places=6)
                    heights[key]=z

    def test_wing_roof_translation_preserves_relative_geometry(self):
        fp=Footprint(((0,0),(20,0),(20,6),(8,6),(8,16),(0,16)))
        a=roofs.envelope(fp,'hipped')
        c=roofs.envelope(fp.translated(1000.,-600.),'hipped')
        np.testing.assert_allclose(np.asarray(c.triangles)-[1000.,-600.,0.],a.triangles,atol=1e-7)


if __name__=='__main__':
    unittest.main()
