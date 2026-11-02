import math
from pathlib import Path
import sys
import unittest
from shapely.geometry import Polygon
from shapely.ops import unary_union
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from buildgen import regional_roofs, roofs, roof_edges
from buildgen.topology import Footprint

class RegionalRoofTest(unittest.TestCase):
    def rectangle(self,angle):
        c,s=math.cos(angle),math.sin(angle)
        return Footprint(tuple((8100+x*c-y*s,-6300+x*s+y*c) for x,y in ((-8,-5),(8,-5),(8,5),(-8,5))))
    def test_coverage_planes_and_boundary(self):
        for angle in (0,.37,1.21):
            fp=self.rectangle(angle)
            for variant in regional_roofs.VARIANTS:
                with self.subTest(angle=angle,variant=variant):
                    r=regional_roofs.envelope(fp,'gabled',variant)
                    polygons=[Polygon([p[:2] for p in tri]) for tri in r.triangles]
                    self.assertLess(unary_union(polygons).symmetric_difference(fp.shape()).area,1e-6)
                    self.assertAlmostEqual(sum(p.area for p in polygons),fp.area,places=6)
                    self.assertAlmostEqual(max(p[2] for tri in r.triangles for p in tri),1)
                    self.assertEqual(len(r.boundary),len(r.wall_u))
                    for tri,i in zip(r.triangles,r.triangle_planes):
                        a,b,h=r.planes[i]
                        for x,y,z in tri:
                            self.assertAlmostEqual(z,(a*(x-r.centre[0])+b*(y-r.centre[1])+h)/r.peak,places=6)
                    for segment in r.boundary:
                        for p in segment:self.assertTrue(all(math.isfinite(x) for x in p) and 0<=p[2]<=1)
    def test_distinct_and_fallback(self):
        fp=self.rectangle(.37)
        signatures=[]
        for v in sorted(regional_roofs.VARIANTS):
            r=regional_roofs.envelope(fp,'gabled',v)
            signatures.append(tuple(sorted(round(p[2],3) for segment in r.boundary for p in segment)))
        self.assertEqual(len(set(signatures)),len(signatures))
        other=Footprint(((0,0),(5,0),(5,2),(3,2),(3,4),(0,4)))
        self.assertEqual(regional_roofs.envelope(other,'gabled','gambrel'),roofs._envelope(other,'gabled'))
        self.assertEqual(regional_roofs.envelope(fp,'gabled','standard'),roofs._envelope(fp,'gabled'))
from dataclasses import replace
from unittest.mock import patch
from buildgen.environments import Environment
import numpy as np
import buildings as b
from buildgen import freeze_items, materials, regional_architecture, progressive
from buildgen.geometry import sky_vertex_count
from test_buildgen_facades import building

class RegionalRoofIntegrationTest(unittest.TestCase):
    def test_imagery_outline_contains_roof_and_inset_physical_walls(self):
        import pickle
        from buildgen import roof_outline
        for variant in ('standard',*sorted(regional_roofs.VARIANTS)):
            for angle in (0.,.37):
                fp=RegionalRoofTest().rectangle(angle)
                spec=building(fp=fp,height=9.,roof_shape='hipped' if variant=='mansard' else 'gabled',roof_height=2.)
                spec.inference=replace(spec.inference,roof_variant=variant)
                roof_outline.fit(spec,imagery=True)
                self.assertEqual(spec.roof_outline,fp)
                self.assertTrue(fp.shape().contains(spec.footprint.shape()))
                self.assertLess(spec.footprint.area,fp.area)
                surface=roof_edges.for_spec(spec)
                union=unary_union([Polygon([p[:2] for p in tri]) for tri in surface.triangles])
                self.assertLess(union.symmetric_difference(fp.shape()).area,1e-6)
                walls=roofs.for_spec(spec)
                for p,q in walls.boundary:
                    for point in (p,q):self.assertAlmostEqual(point[2],roof_edges.height(surface,point[:2]))
                items=freeze_items([(spec,0.,0.)]);restored=pickle.loads(pickle.dumps(items))
                self.assertEqual(restored[0][0].roof_outline,fp)
                for mesh in (b.build(items),b.build(items,lite=True),b._sky_mesh(items),progressive.shell(items)):
                    self.assertTrue(np.isfinite(mesh[0]).all())
                    self.assertAlmostEqual(mesh[0][:,2].max(),9.,places=5)
                sky=b._sky_mesh(items)
                self.assertEqual(len(sky[0]),sky_vertex_count(items[0][0]))
                collision=b.collision_mesh(items)
                self.assertLessEqual(collision[0][:,2].max(),9.+1e-6)
                self.assertGreater(collision[0][:,2].max(),8.) # high shed overhang is render-only
                from shapely.geometry import MultiPoint
                self.assertTrue(spec.footprint.shape().buffer(1e-6).covers(MultiPoint(collision[0][:,:2])))

    def test_imagery_routing_ground_and_street_refit(self):
        from buildgen import roof_outline
        from buildgen.road_conflicts import _refit
        from unittest.mock import Mock
        spec=building(roof_shape='gabled',ml=True)
        self.assertIsNotNone(spec.roof_outline)
        source=spec.roof_outline
        sampler=Mock(side_effect=lambda xy:xy[:,0]*.1+xy[:,1]*.02)
        items=roof_outline.resample_ground([(spec,0.,0.)],sampler)
        self.assertEqual(sampler.call_count,1)
        np.testing.assert_allclose(spec.gring,spec.ring[:,0]*.1+spec.ring[:,1]*.02)
        self.assertEqual(items[0][1],spec.gring.min())
        clipped=Footprint(((0.,4.35),(12.,4.35),(12.,10.),(0.,10.)))
        changed,lo,hi=_refit(spec,clipped,lambda xy:np.zeros(len(xy)),np.zeros(2),0.,0.)
        self.assertEqual(changed.roof_outline,clipped)
        self.assertTrue(clipped.shape().contains(changed.footprint.shape()))
        self.assertGreaterEqual(min(p[1] for tri in roof_edges.for_spec(changed).triangles for p in tri),4.35-1e-8)
        self.assertIsNone(building(roof_shape='gabled',ml=True,_footprint_role='wall').roof_outline)
        self.assertIsNone(building(roof_shape='flat',ml=True).roof_outline)
        from buildgen.access import basis
        b.doors([(spec,0.,0.)],[(np.array([[-50.,-10.],[50.,-10.]]),3.,'residential',False)],0.,0.,
                ground=lambda xy:np.zeros(len(xy)))
        self.assertIsNotNone(spec.door)
        point=basis(spec,*spec.door)[0]
        from shapely.geometry import Point
        self.assertLess(spec.footprint.shape().boundary.distance(Point(point)),1e-7)
        self.assertGreater(source.shape().boundary.distance(Point(point)),.05)

    def test_extended_planes_and_closed_edges_across_forms(self):
        for variant in ('standard',*sorted(regional_roofs.VARIANTS)):
            for kind in ('gabled','hipped'):
                for angle in (0.,.37):
                    fp=RegionalRoofTest().rectangle(angle)
                    spec=building(fp=fp,height=9.,roof_shape=kind,roof_height=1.1)
                    spec.inference=replace(spec.inference,roof_variant=variant)
                    r=roof_edges.for_spec(spec);t=roof_edges.treatment(spec)
                    polygons=[Polygon([p[:2] for p in tri]) for tri in r.triangles]
                    union=unary_union(polygons)
                    self.assertLess(fp.shape().difference(union).area,1e-6)
                    self.assertGreater(union.area,fp.area)
                    self.assertAlmostEqual(union.area,sum(p.area for p in polygons),places=6)
                    self.assertAlmostEqual(max(p[2] for tri in r.triangles for p in tri),1.)
                    for tri,i in zip(r.triangles,r.triangle_planes):
                        a,c,h=r.planes[i]
                        for x,y,z in tri:self.assertAlmostEqual(z,(a*(x-r.centre[0])+c*(y-r.centre[1])+h)/r.peak,places=6)
                    mesh=b.Mesh();roof_edges.draw(mesh,spec,spec.height,b._Looks(spec.seed))
                    pos=mesh.arrays()[0]
                    for p,q in r.boundary:
                        for x,y,h in (p,q):
                            z=spec.height+h*spec.inference.roof_rise
                            self.assertLess(np.linalg.norm(pos-(x,y,z),axis=1).min(),.001)
                            self.assertLess(np.linalg.norm(pos-(x,y,z-t.depth),axis=1).min(),.001)
                    self.assertLess(len(pos),800) # perimeter detail, no per-tile tessellation

    def test_all_regional_styles_and_contemporary_families_receive_edges(self):
        from test_buildgen_regions import building as regional_building
        from buildgen import house_styles
        signatures=set()
        for key in regional_architecture.catalogue():
            spec=regional_building(key,roof_shape='gabled',roof_height=2.)
            spec.inference=replace(spec.inference,house_style=house_styles.HouseStyle('regional',key))
            t=roof_edges.treatment(spec);signatures.add((t.eave,t.rake))
            self.assertTrue(.10<=t.eave<=.72 and .09<=t.rake<=.45,key)
            self.assertTrue(.10<=t.depth<=.24,key)
            near=b.Mesh();lite=b.Mesh()
            from buildgen.geometry import draw
            draw(near,spec,0.,0.);draw(lite,spec,0.,0.,lite=True)
            # Roof boundary and its visible underside are retained in both LODs.
            for mesh in (near,lite):
                pos=mesh.arrays()[0]
                for p,q in roof_edges.for_spec(spec).boundary:
                    for x,y,h in (p,q):
                        z=b.base_z(spec,0.,0.)+spec.height+h*spec.inference.roof_rise-t.depth
                        self.assertLess(np.linalg.norm(pos-(x,y,z),axis=1).min(),1e-4,key)
        self.assertGreater(len(signatures),10)
        for family in house_styles.CONTEMPORARY:
            spec.inference=replace(spec.inference,house_style=house_styles.HouseStyle('contemporary','',alternate=family))
            self.assertGreater(roof_edges.treatment(spec).eave,.1)

    def test_complex_courtyards_keep_voids_with_exterior_eaves(self):
        fp=Footprint(((0,0),(14,0),(14,12),(0,12)),(((4,4),(4,8),(10,8),(10,4)),))
        spec=building(fp=fp,roof_shape='hipped')
        self.assertGreater(roof_edges.treatment(spec).eave,0.)
        roof=roof_edges.for_spec(spec)
        shape=unary_union([Polygon([p[:2] for p in tri]) for tri in roof.triangles])
        self.assertGreater(shape.area,fp.area)
        self.assertLess(shape.intersection(Polygon(fp.holes[0])).area,1e-7)

    def test_planned_variants_match_near_lite_collision_and_uv(self):
        for variant in sorted(regional_roofs.VARIANTS):
            with self.subTest(variant=variant):
                kind='hipped' if variant=='mansard' else 'gabled'
                spec=building(width=16.,depth=10.,height=9.,roof_shape=kind,roof_height=2.5)
                spec.inference=replace(spec.inference,roof_variant=variant)
                self.assertEqual(roofs.variant(spec),variant)
                roof=roofs.for_spec(spec)
                self.assertEqual(roof.strategy,'regional_'+variant)
                m=b.Mesh();roofs.draw(m,spec,spec.height,b._Looks(spec.seed))
                pos,uv,tris,_,_=m.arrays()
                self.assertTrue(np.isfinite(pos).all() and np.isfinite(uv).all())
                for tri in tris[:len(roof.triangles)]:
                    xyz=pos[tri]; tex=uv[tri]
                    real=np.linalg.norm(xyz-np.roll(xyz,1,axis=0),axis=1)
                    mapped=np.linalg.norm((tex-np.roll(tex,1,axis=0))*materials.roof_scale(spec.inference.roof_material.value),axis=1)
                    np.testing.assert_allclose(real,mapped,atol=5e-5)
                items=freeze_items([(spec,0.,0.)])
                near=b.build(items)
                lite=b.build(items,lite=True)
                collision=b.collision_mesh(items)
                sky=b._sky_mesh(items)
                shell=progressive.shell(items)
                self.assertEqual(len(sky[0]),sky_vertex_count(items[0][0]))
                self.assertLessEqual(len(sky[0]),256)
                for mesh in (near,lite,collision,sky,shell):
                    self.assertTrue(np.isfinite(mesh[0]).all() and np.isfinite(mesh[1]).all())
                    self.assertAlmostEqual(float(mesh[0][:,2].max()),9.,places=5)
                    self.assertGreaterEqual(float(mesh[0][:,0].min()),-1.)
                    self.assertLessEqual(float(mesh[0][:,0].max()),17.)
                    self.assertGreaterEqual(float(mesh[0][:,1].min()),-1.)
                    self.assertLessEqual(float(mesh[0][:,1].max()),11.)
    def test_explicit_mapped_shapes_remain_standard(self):
        profile = dict(regional_architecture.profile('jp_temperate'))
        profile['roof_variants'] = [['gambrel',1]]
        for kind in ('gabled','hipped','flat'):
            with self.subTest(kind=kind), patch('buildgen.environments.resolve', return_value=Environment('unknown','jp_temperate')):
                # Force a nonstandard regional proposal; explicit source shape wins.
                with patch('buildgen.regional_architecture.roof_default', return_value='gabled'), patch('buildgen.regional_architecture.profile', return_value=profile):
                    spec=building(height=9.,roof_shape=kind,roof_height=2.)
                self.assertEqual(spec.inference.roof_variant,'standard')
                self.assertEqual(spec.inference.roof.value,kind)

if __name__=='__main__':unittest.main()
