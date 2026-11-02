"""Regional structure must change geometry while retaining evidence and access."""
from collections import Counter
from dataclasses import replace
from pathlib import Path
import json,pickle,sys,unittest
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import residential,regional_architecture as regional,house_styles,freeze_items,facades,roofs,roof_edges
from buildgen.topology import Footprint
from buildgen.context import Context

FP=Footprint(((0,0),(12,0),(12.003,9),(0,9)))


def building(region,family,fp=FP,**attrs):
    location=regional.catalogue()[region]['example']
    values=dict(seed_id='dwelling-test-'+family,_footprint=fp,
                _context=Context(location=(location['lat'],location['lon'])),height=8.,num_floors=2,
                **{'class':'house'})
    values.update(attrs)
    with patch.dict(residential.catalogue()['regions'],{region:[[family,1]]}),patch.object(house_styles,'select',return_value=house_styles.HouseStyle('regional',region)):
        spec=b.plan(np.asarray(fp.outer),values)
        spec.gring=np.zeros(len(fp.outer));spec.front=0;spec.door=(0,1.6)
        frozen=freeze_items([(spec,0.,0.)])
        near=b.build(frozen);lite=b.build(frozen,lite=True);collision=b.collision_mesh(frozen)
        return spec,frozen,near,lite,collision


class ResidentialStructureTests(unittest.TestCase):
    def test_every_family_compiles_actual_depth_and_matching_lod_apertures(self):
        seen=set();signatures=set()
        for region,options in residential.catalogue()['regions'].items():
            for family,_ in options:
                if family in seen:continue
                seen.add(family)
                with self.subTest(family=family):
                    spec,frozen,near,lite,col=building(region,family)
                    layout=frozen[0][0].facades
                    self.assertIn('dwelling_structure:'+family,layout.diagnostics)
                    assemblies=[o for e in layout.elevations for o in e.openings if o.assembly]
                    self.assertLessEqual(len(assemblies),residential.MAX_ASSEMBLIES)
                    for mesh in (near,lite,col):
                        self.assertTrue(np.isfinite(mesh[0]).all())
                        self.assertLess(mesh[2].max(),len(mesh[0]))
                        self.assertLess(len(mesh[0]),30000)
                    for e in layout.elevations:
                        for o in e.openings:
                            self.assertGreater(o.right,o.left)
                            self.assertLessEqual(o.top,spec.height+.01)
                            self.assertGreaterEqual(o.left,0.)
                            self.assertLessEqual(o.right,e.length)
                            if o.kind!='door':
                                for door in (d for d in e.openings if d.kind in ('door','garage','service')):
                                    self.assertFalse(o.overlaps(door,.15))
                    restored=pickle.loads(pickle.dumps(frozen))
                    np.testing.assert_array_equal(b.build(restored)[0],near[0])
                    signatures.add((len(near[0]),near[0].tobytes(),tuple(near[3])))
        self.assertEqual(seen,set(residential.catalogue()['families']))
        self.assertGreaterEqual(len(signatures),25)

    def test_source_envelope_material_and_collision_survive_family_changes(self):
        meshes=[]
        for family in ('japanese_machiya','japanese_engawa','japanese_compact'):
            spec,frozen,near,lite,col=building('jp_temperate',family,roof_shape='hipped',roof_height=1.5,
                    facade_material='stone',roof_material='metal',facade_color='#778899',roof_color='#335577')
            self.assertEqual(spec.inference.roof_variant,'standard')
            self.assertEqual(spec.roof,'hipped')
            self.assertEqual(spec.height,6.5)
            self.assertEqual(b.LOOKS[spec.facade][1],b.parse_color('#778899'))
            np.testing.assert_array_equal(spec.ring,FP.outer)
            meshes.append(col)
        for mesh in meshes[1:]:
            np.testing.assert_array_equal(mesh[0],meshes[0][0])
            np.testing.assert_array_equal(mesh[2],meshes[0][2])

    def test_courtyard_privacy_and_inward_assemblies_preserve_void(self):
        fp=Footprint(((0,0),(18,0),(18,16),(0,16)),(((5,5),(5,11),(13,11),(13,5)),))
        for region,family in [('sahel','sahel_compound'),('maghreb','maghreb_courtyard')]:
            spec,frozen,near,lite,col=building(region,family,fp=fp,roof_shape='flat')
            layout=frozen[0][0].facades
            self.assertTrue(any(o.assembly=='gallery' for e in layout.elevations if e.boundary for o in e.openings))
            outer=[o for e in layout.elevations if e.boundary==0 for o in e.openings if o.kind=='window']
            self.assertTrue(outer)
            self.assertTrue(all(o.right-o.left<=.75+1e-8 and not o.assembly for o in outer))
            self.assertEqual(frozen[0][0].footprint.holes,fp.holes)

    def test_mixture_does_not_override_structural_geography(self):
        location=regional.catalogue()['korea']['example']
        for variant in ('regional','contemporary','global'):
            style=house_styles.HouseStyle(variant,'italy_regional' if variant=='global' else 'korea',alternate='rendered')
            with patch.object(house_styles,'select',return_value=style):
                spec=b.plan(np.asarray(FP.outer),dict(seed_id='same-local-structure',_footprint=FP,
                           _context=Context(location=(location['lat'],location['lon'])),**{'class':'house','height':8.,'num_floors':2}))
            row=residential.for_spec(spec)
            self.assertEqual(row['region'],'korea')
            self.assertIn(row['id'],('korean_maru','korean_villa','korean_compact'))

    def test_near_rectangle_regional_roofs_are_not_reset_by_compiler(self):
        variants=set()
        for i in range(80):
            spec,*_=building('korea','korean_maru',seed_id='korean-roof-'+str(i))
            variants.add(spec.inference.roof_variant)
            if spec.roof=='flat':continue
            surface=roof_edges.for_spec(spec)
            for tri in surface.triangles:
                self.assertLessEqual(max(p[2] for p in tri),1.+1e-7)
        self.assertIn('flared_hip',variants)
        self.assertIn('cross_gable',variants)


if __name__=='__main__':unittest.main()
