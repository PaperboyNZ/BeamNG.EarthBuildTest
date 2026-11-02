"""Real source polygons must receive joined visible eaves, not only ideal boxes."""
import json
from pathlib import Path
import pickle
import unittest
import numpy as np
from shapely.geometry import Polygon, MultiPoint
from shapely.ops import unary_union
from test_buildgen_facades import building
import buildings as b
from buildgen import freeze_items, roofs, roof_edges
from buildgen.geometry import sky_vertex_count
from buildgen.topology import Footprint


def source_cases():
    data=json.loads((Path(__file__).parent/'fixtures/real_roof_outlines.json').read_text())
    return [Footprint(row['outer'],row['holes']) for row in data['fixtures']]


class PolygonEaveTest(unittest.TestCase):
    def cases(self):
        return [Footprint(((0,0),(12,0),(12.001,9),(0,9))),
                Footprint(((0,0),(6,0),(12,0),(12,9),(0,9))),
                Footprint(((0,0),(14,0),(14,5),(6,5),(6,12),(0,12))),
                Footprint(((0,0),(18,0),(18,16),(0,16)),(((5,5),(5,11),(13,11),(13,5)),)),
                *source_cases()]

    def test_real_and_complex_walls_receive_surface_and_downward_soffits(self):
        for fp in self.cases():
            for kind in ('gabled','hipped'):
                with self.subTest(fp=fp.outer,kind=kind):
                    spec=building(fp=fp,height=8.,roof_shape=kind,roof_height=2.)
                    surface=roof_edges.for_spec(spec)
                    treatment=roof_edges.treatment(spec)
                    self.assertGreater(treatment.eave,.01)
                    shape=unary_union([Polygon([p[:2] for p in tri]) for tri in surface.triangles])
                    self.assertLess(fp.shape().difference(shape).area,1e-6)
                    self.assertGreater(shape.difference(fp.shape()).area,.1)
                    self.assertAlmostEqual(shape.area,sum(Polygon([p[:2] for p in tri]).area for tri in surface.triangles),places=5)
                    for hole in fp.holes:
                        self.assertLess(shape.intersection(Polygon(hole)).area,1e-6)
                    self.assertLessEqual(max(p[2] for tri in surface.triangles for p in tri),1.+1e-7)
                    edge=b.Mesh();roof_edges.draw(edge,spec,spec.height,b._Looks(spec.seed))
                    positions,uv,indices,_,_=edge.arrays()
                    normals=np.cross(positions[indices[:,1]]-positions[indices[:,0]],positions[indices[:,2]]-positions[indices[:,0]])
                    self.assertTrue(np.any(normals[:,2]<-.001))
                    for lite in (False,True):
                        mesh=b.build(freeze_items([(spec,0.,0.)]),lite=lite)
                        self.assertTrue(np.isfinite(mesh[0]).all())
                        self.assertAlmostEqual(mesh[0][:,2].max(),8.,places=5)
                        import cdae
                        encoded=cdae.encode(mesh[0],mesh[2],uvs=mesh[1],tri_materials=mesh[3],
                                            material=list(mesh[4]),colors=mesh[5])
                        native=cdae.decode(encoded)
                        restored=cdae.mesh_arrays(native['meshes'][0])
                        # The native writer batches vertices by material.
                        np.testing.assert_array_equal(np.asarray(sorted(map(tuple,restored['verts']))),
                                                      np.asarray(sorted(map(tuple,mesh[0].astype(np.float32)))))
                    collision=b.collision_mesh(freeze_items([(spec,0.,0.)]))
                    self.assertTrue(fp.shape().buffer(1e-6).covers(MultiPoint(collision[0][:,:2])))

    def test_imagery_domains_keep_roof_and_refit_all_representations(self):
        for fp in self.cases():
            for kind in ('gabled','hipped'):
                with self.subTest(fp=fp.outer,kind=kind):
                    spec=building(fp=fp,height=8.,roof_shape=kind,roof_height=2.,ml=True)
                    self.assertEqual(spec.roof_outline,fp)
                    self.assertLess(spec.footprint.area,fp.area)
                    surface=roof_edges.for_spec(spec)
                    shape=unary_union([Polygon([p[:2] for p in tri]) for tri in surface.triangles])
                    self.assertLess(shape.symmetric_difference(fp.shape()).area,1e-6)
                    walls=roofs.for_spec(spec)
                    for p,q in walls.boundary:
                        for point in (p,q):
                            self.assertAlmostEqual(point[2],roof_edges.height(surface,point[:2]),places=6)
                    frozen=pickle.loads(pickle.dumps(freeze_items([(spec,0.,0.)])))
                    for mesh in (b.build(frozen),b.build(frozen,lite=True),b._sky_mesh(frozen),b.collision_mesh(frozen)):
                        self.assertTrue(np.isfinite(mesh[0]).all())
                        self.assertLessEqual(mesh[0][:,2].max(),8.+1e-5)
                    self.assertEqual(len(b._sky_mesh(frozen)[0]),sky_vertex_count(frozen[0][0]))

    def test_translated_roof_and_courtyard_stay_identical(self):
        for fp in self.cases()[:4]:
            a=building(fp=fp,roof_shape='hipped',roof_height=2.)
            shifted=fp.translated(8100.,-6300.)
            c=building(fp=shifted,roof_shape='hipped',roof_height=2.)
            ra,rc=roof_edges.for_spec(a),roof_edges.for_spec(c)
            sa=unary_union([Polygon([p[:2] for p in t]) for t in ra.triangles])
            from shapely.affinity import translate
            sc=translate(unary_union([Polygon([p[:2] for p in t]) for t in rc.triangles]),xoff=-8100.,yoff=6300.)
            self.assertLess(sa.symmetric_difference(sc).area,1e-5)


if __name__=='__main__':unittest.main()
