"""Three conservative church envelopes share source height, topology and seeds."""
from dataclasses import FrozenInstanceError
import hashlib
import itertools
from pathlib import Path
import pickle
import sys
import unittest
from unittest.mock import patch

import numpy as np
from shapely.geometry import MultiPoint, Polygon
from shapely.ops import unary_union

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import churches, freeze_items, programme
from buildgen.topology import Footprint


def footprints():
    return (Footprint(((0,0),(18,0),(18,10),(0,10))),
            Footprint(((0,0),(22,0),(22,8),(14,8),(14,15),(0,15))),
            Footprint(((0,0),(24,0),(24,18),(0,18)),(((8,6),(16,6),(16,12),(8,12)),)))


def make(family=churches.FAMILIES[0],fp=None,seed='source-church',**extra):
    fp=fp or footprints()[0]
    attrs=dict(_footprint=fp,seed_id=seed,**{'class':'church','height':9.,'num_floors':1,
               'roof_shape':'gabled','roof_height':2.,'_church_family':family})
    attrs.update(extra)
    spec=b.plan(np.asarray(fp.outer),attrs)
    spec.gring=np.zeros(len(spec.ring))
    return spec,attrs


def compiled(spec,collision=False,lite=False):
    items=freeze_items([(spec,0.,0.)])
    return b.collision_mesh(items) if collision else b.build(items,lite=lite)


def digest(mesh):
    return hashlib.sha256(b''.join(np.ascontiguousarray(a).tobytes() for a in (mesh[0],mesh[2],mesh[3],mesh[5]))).hexdigest()


class ChurchTests(unittest.TestCase):
    def test_three_families_three_footprints_three_seeds_preserve_envelopes(self):
        for family,fp,seed in itertools.product(churches.FAMILIES,footprints(),('church-A','church-B','church-C')):
            with self.subTest(family=family,vertices=fp.vertex_count,seed=seed):
                spec,_=make(family,fp,seed)
                self.assertTrue(spec.church.accepted)
                self.assertFalse(spec.steeple)
                self.assertFalse(spec.shop)
                self.assertEqual(spec.footprint,fp)
                self.assertEqual(spec.height+spec.church.roof_rise,9.)
                boxes=b.collider_boxes([(spec,0.,0.)],0.,0.)
                self.assertAlmostEqual(boxes[0][5],9.,places=6)
                self.assertEqual(len(boxes[0][6]),1+len(fp.holes))
                for mesh in (compiled(spec),compiled(spec,lite=True),compiled(spec,collision=True)):
                    self.assertTrue(np.isfinite(mesh[0]).all())
                    self.assertAlmostEqual(float(mesh[0][:,2].max()),9.,places=5)
                    np.testing.assert_allclose(mesh[0][:,:2].min(0),np.asarray(fp.outer).min(0),atol=1e-6)
                    np.testing.assert_allclose(mesh[0][:,:2].max(0),np.asarray(fp.outer).max(0),atol=1e-6)

    def test_same_outline_height_and_material_have_three_distinct_compositions(self):
        signatures=[];collisions=[]
        for family in churches.FAMILIES:
            spec,_=make(family,facade_material='render',facade_color='#d8d3c5')
            signatures.append(digest(compiled(spec)))
            collisions.append(compiled(spec,collision=True))
            self.assertEqual(spec.roof,'gabled')
            self.assertAlmostEqual(spec.church.total_height,9.)
        self.assertEqual(len(set(signatures)),3)
        for mesh in collisions[1:]:
            np.testing.assert_array_equal(mesh[0],collisions[0][0])
            np.testing.assert_array_equal(mesh[2],collisions[0][2])

    def test_flat_gabled_hipped_roof_and_mapped_materials_are_preserved(self):
        for roof in ('flat','gabled','hipped'):
            spec,_=make(churches.FAMILIES[2],footprints()[1],roof_shape=roof,
                        roof_height=0. if roof=='flat' else 1.75,roof_material='slate',
                        roof_color='#304858',facade_material='stone')
            self.assertTrue(spec.church.accepted)
            self.assertEqual(spec.roof,roof)
            self.assertEqual(spec.church.vocabulary,'stone')
            self.assertEqual(spec.church.roof_material,'slate')
            self.assertIn('c_0.188',spec.roof_mat)
            self.assertAlmostEqual(float(compiled(spec)[0][:,2].max()),9.,places=5)

    def test_courtyard_roof_and_collision_do_not_fill_source_void(self):
        fp=footprints()[2];hole=Polygon(fp.holes[0])
        for family in churches.FAMILIES:
            spec,_=make(family,fp)
            for mesh in (compiled(spec),compiled(spec,lite=True),compiled(spec,collision=True)):
                triangles=[]
                for ids in mesh[2]:
                    p=mesh[0][ids]
                    if p[:,2].min()<spec.height-1e-5:continue
                    tri=Polygon(p[:,:2])
                    if tri.area>1e-8:triangles.append(tri)
                cover=unary_union(triangles)
                self.assertLess(cover.intersection(hole).area,1e-7)
                self.assertAlmostEqual(cover.area,fp.area,places=5)

    def test_seed_replay_translation_and_ring_rotation_keep_choices(self):
        fp=footprints()[0]
        for family in churches.FAMILIES:
            a,_=make(family,fp,'stable-owner')
            repeated,_=make(family,Footprint(fp.outer[2:]+fp.outer[:2]),'stable-owner')
            shifted,_=make(family,fp.translated(10000,-20000),'stable-owner')
            self.assertEqual(a.church,shifted.church)
            self.assertEqual(digest(compiled(a)),digest(compiled(repeated)))
            near,rebased=compiled(a),compiled(shifted)
            np.testing.assert_allclose(near[0],rebased[0]-np.array([10000,-20000,0]),atol=.002)
            np.testing.assert_array_equal(near[2],rebased[2])

    def test_layout_reserves_entry_and_shared_walls_in_near_and_lite(self):
        for family in churches.FAMILIES:
            spec,_=make(family,_party_walls=((0,1),))
            spec.door=(0,9.);spec.front=0
            layout=churches.layout(spec,0.,0.)
            self.assertEqual(next(e for e in layout.elevations if e.edge==1).openings,())
            for elevation in layout.elevations:
                for i,opening in enumerate(elevation.openings):
                    self.assertGreaterEqual(opening.left,.45)
                    self.assertLessEqual(opening.right,elevation.length-.45)
                    self.assertLessEqual(opening.top,spec.height-.14)
                    for other in elevation.openings[i+1:]:self.assertFalse(opening.overlaps(other,.2))
            self.assertTrue(any(o.kind=='door' for e in layout.elevations for o in e.openings))
            self.assertLess(len(compiled(spec,lite=True)[0]),len(compiled(spec)[0]))

    def test_current_use_and_fabric_remain_separate_without_symbols(self):
        spec,_=make(churches.FAMILIES[0],**{'class':'office','building':'church','building_use':'office'})
        self.assertTrue(spec.church.accepted)
        self.assertEqual(spec.church.current_use,'office')
        self.assertEqual(spec.church.architectural_fabric,'church')
        self.assertIn('converted_fabric_no_active_worship_identity',spec.church.diagnostics)
        self.assertFalse(spec.steeple)

    def test_names_and_generic_religion_do_not_activate_church_architecture(self):
        for attrs in ({'class':'office','name':'Church Street Offices'},
                      {'class':'retail','name':'Church Street Shop'},
                      {'class':'religious','name':'New Chapel','religion':'christian'},
                      {'class':'temple','name':'Church Road Temple'}):
            spec,_=make(**attrs)
            self.assertIsNone(spec.church)
            self.assertIsNotNone(spec.inference)
            self.assertFalse(spec.steeple)
            self.assertIn('name_keyword_does_not_confirm_church',spec.diagnostics)
            self.assertTrue(np.isfinite(compiled(spec)[0]).all())

    def test_church_street_garage_keeps_genuine_garage_geometry(self):
        fp=Footprint(((0,0),(60,0),(60,40),(0,40)))
        spec,_=make(fp=fp,**{'class':'parking_garage','name':'Church Street Garage',
                            'height':8.,'num_floors':2,'roof_shape':'flat','roof_height':0.})
        self.assertIsNone(spec.church)
        self.assertTrue(spec.deck)
        self.assertFalse(spec.steeple)
        self.assertIsNotNone(b.deck_plan(spec,0.,0.))

    def test_oversized_or_tall_church_retains_diagnosed_source_height_fallback(self):
        for fp,height,reason in ((Footprint(((0,0),(80,0),(80,40),(0,40))),9.,'church_phase1_footprint_budget'),
                                 (footprints()[0],25.,'church_height_envelope_unsupported')):
            spec,_=make(fp=fp,height=height)
            self.assertFalse(spec.church.accepted)
            self.assertEqual(spec.church.total_height,height)
            self.assertIn(reason,spec.church.diagnostics)
            self.assertIn('church_phase1_legacy_fallback',spec.diagnostics)

    def test_unsupported_cases_leave_adapter_input_unchanged(self):
        fp=footprints()[0]
        for extra in ({'roof_shape':'dome'},{'roof_direction':90.},{'num_floors':2},
                      {'class':'cathedral'},{'tower':'bell_tower'},{'min_height':4.},
                      {'roof_height':9.},{'facade_material':'unsupported'},{'_church_family':'invented'}):
            attrs={'class':'church','height':9.,'roof_shape':'gabled','roof_height':2.,'_footprint':fp}
            attrs.update(extra)
            raw=b._legacy_plan(np.asarray(fp.outer),attrs)
            before={field:getattr(raw,field) for field in b.Spec.__slots__}
            metadata=churches.adapt(raw,attrs,fp)
            self.assertIsNotNone(metadata)
            self.assertFalse(metadata.accepted)
            self.assertIn('church_phase1_legacy_fallback',metadata.diagnostics)
            for field,value in before.items():
                current=getattr(raw,field)
                if isinstance(value,np.ndarray):np.testing.assert_array_equal(current,value)
                else:self.assertEqual(current,value)

    def test_production_nan_numeric_fields_are_missing_not_invalid(self):
        missing={name:np.nan for name in ('height','num_floors','min_height','roof_height','roof_direction')}
        spec,_=make(**missing)
        self.assertTrue(spec.church.accepted)
        self.assertFalse(any('invalid' in reason for reason in spec.church.diagnostics))
        self.assertTrue(np.isfinite(compiled(spec)[0]).all())

    def test_frozen_worker_roundtrip_retains_church_and_layout(self):
        spec,_=make(churches.FAMILIES[1]);spec.door=(0,9.)
        plan=freeze_items([(spec,0.,0.)])[0][0]
        restored=pickle.loads(pickle.dumps(plan))
        self.assertEqual(restored.church,plan.church)
        self.assertEqual(churches.layout(restored,0.,0.),churches.layout(plan,0.,0.))
        with self.assertRaises(FrozenInstanceError):restored.church.family='changed'
        self.assertEqual(digest(compiled(restored)),digest(compiled(spec)))

    def test_grounded_door_does_not_create_residential_drive_fence_or_shop(self):
        for family in churches.FAMILIES:
            spec,_=make(family,roof_shape='flat',roof_height=0.)
            roads=[(np.array([(-30.,-10.),(60.,-10.)]),3.,'residential',True)]
            drives=[]
            props=b.doors([(spec,0.,0.)],roads,0.,0.,drives,ground=lambda xy:np.zeros(len(xy)))
            self.assertIsNotNone(spec.door)
            self.assertEqual(drives,[])
            self.assertFalse(spec.shop)
            self.assertIsNone(spec.stoop)
            self.assertFalse(any(row[0] in ('fence','sign') for row in props))

    def test_chunking_retains_all_source_triangles(self):
        spec,_=make(churches.FAMILIES[1],footprints()[2]);mesh=compiled(spec)
        chunks=b.split_mesh(mesh,300)
        self.assertGreater(len(chunks),1)
        self.assertTrue(all(len(chunk[0])<=300 for chunk in chunks))
        self.assertEqual(sum(len(chunk[2]) for chunk in chunks),len(mesh[2]))

    def test_unrelated_features_return_before_specialist_diagnostic_allocation(self):
        fp=footprints()[0]
        with patch('buildgen.specialized.select',side_effect=AssertionError('unrelated diagnostic allocation')):
            for attrs in ({'class':'house'},{'class':'office','name':'Church Street Offices'},
                          {'class':'religious','religion':'christian'},{'class':'mosque','name':'Chapel Road'}):
                self.assertIsNone(churches.adapt(None,attrs,fp))

    def test_skyline_count_height_and_source_holes_match_actual_envelope(self):
        from buildgen.geometry import sky, sky_vertex_count
        for fp,roof in itertools.product(footprints(),('flat','gabled','hipped')):
            with self.subTest(vertices=fp.vertex_count,roof=roof):
                spec,_=make(churches.FAMILIES[1],fp,roof_shape=roof,roof_height=0. if roof=='flat' else 2.)
                plan=freeze_items([(spec,0.,0.)])[0][0]
                mesh=b.Mesh();sky(mesh,plan,0.,0.)
                self.assertEqual(mesh.n,sky_vertex_count(plan))
                positions,uv,tris,mid,colours=mesh.arrays()
                self.assertAlmostEqual(float(positions[:,2].max()),9.,places=5)
                projected=[]
                for ids in tris:
                    p=positions[ids]
                    if p[:,2].min()<spec.height-1e-5:continue
                    triangle=Polygon(p[:,:2])
                    if triangle.area>1e-8:projected.append(triangle)
                cover=unary_union(projected)
                self.assertAlmostEqual(cover.area,fp.area,places=5)
                for hole in fp.holes:self.assertLess(cover.intersection(Polygon(hole)).area,1e-7)

    def test_shared_roof_material_aliases_and_unsupported_glass(self):
        for source,resolved in (('wood','shingle'),('zinc','metal'),('tiles','tile'),('stone','slate'),('felt','membrane')):
            spec,_=make(roof_material=source)
            self.assertTrue(spec.church.accepted)
            self.assertEqual(spec.church.roof_material,resolved)
        spec,_=make(roof_material='glass')
        self.assertFalse(spec.church.accepted)
        self.assertIn('church_mapped_roof_material_unsupported',spec.church.diagnostics)

    def test_infrastructure_cut_declines_before_using_clipped_area_or_width(self):
        source=Footprint(((0,0),(60,0),(60,50),(0,50)))
        clipped=Footprint(((0,0),(30,0),(30,20),(0,20)))
        spec,_=make(fp=clipped,_planning_footprint=source)
        self.assertFalse(spec.church.accepted)
        self.assertIn('church_infrastructure_cut_source_envelope_unsupported',spec.church.diagnostics)
        self.assertEqual(spec.church.total_height,9.)

    def test_three_spire_kinds_share_bounded_visual_collision_sky_silhouettes(self):
        from buildgen.geometry import sky,sky_vertex_count
        for kind,fp in itertools.product(churches.SPIRE_KINDS,footprints()):
            with self.subTest(kind=kind,vertices=fp.vertex_count):
                spec,_=make(churches.FAMILIES[1],fp,height=15.,roof_height=np.nan,_church_spire=kind)
                spire=spec.church.spire
                self.assertIsNotNone(spire)
                self.assertEqual(spire.kind,kind)
                self.assertTrue(fp.shape().covers(spire.footprint.shape()))
                self.assertGreaterEqual(fp.shape().boundary.distance(spire.footprint.shape()),.3)
                self.assertGreaterEqual(spire.base_height,3.4)
                spec.door=(0,math_dist(fp.outer[0],fp.outer[1])/2)
                door=next(op for elevation in churches.layout(spec,0.,0.).elevations for op in elevation.openings if op.kind=='door')
                self.assertGreater(spire.base_height,door.top)
                plan=freeze_items([(spec,0.,0.)])[0][0]
                skyline=b.Mesh();sky(skyline,plan,0.,0.)
                self.assertEqual(skyline.n,sky_vertex_count(plan))
                p,uv,t,mid,colours=skyline.arrays()
                self.assertAlmostEqual(float(p[:,2].max()),15.,places=5)
                for mesh in (compiled(spec),compiled(spec,lite=True),compiled(spec,collision=True)):
                    self.assertAlmostEqual(float(mesh[0][:,2].max()),15.,places=5)
                    self.assertTrue(np.isfinite(mesh[0]).all())
                    np.testing.assert_allclose(mesh[0][:,:2].min(0),np.asarray(fp.outer).min(0),atol=1e-6)
                    np.testing.assert_allclose(mesh[0][:,:2].max(0),np.asarray(fp.outer).max(0),atol=1e-6)
                    upper=mesh[0][mesh[0][:,2]>=spire.shoulder_height-.9,:2]
                    self.assertTrue(spire.footprint.shape().buffer(1e-6).covers(MultiPoint(upper)))
                self.assertAlmostEqual(b.collider_boxes([(spec,0.,0.)],0.,0.)[0][5],15.,places=5)
                restored=pickle.loads(pickle.dumps(plan))
                self.assertEqual(restored.church.spire,spire)
                with self.assertRaises(FrozenInstanceError):restored.church.spire.kind='changed'

    def test_spire_subset_is_stable_and_observed_roof_height_has_priority(self):
        selected=[]
        for i in range(32):
            spec,_=make(seed=f'church-spire-{i}',height=15.,roof_height=np.nan)
            selected.append(spec.church.spire is not None)
            repeat,_=make(seed=f'church-spire-{i}',height=15.,roof_height=np.nan)
            self.assertEqual(spec.church,repeat.church)
        self.assertTrue(any(selected))
        self.assertFalse(all(selected))
        spec,_=make(height=15.,roof_height=2.,_church_spire='square_broach')
        self.assertIsNone(spec.church.spire)
        self.assertIn('church_spire_omitted_preserve_mapped_roof_height',spec.church.diagnostics)
        short,_=make(height=6.,roof_height=np.nan,_church_spire='octagonal_needle')
        self.assertTrue(short.church.accepted)
        self.assertIsNone(short.church.spire)
        self.assertAlmostEqual(float(compiled(short)[0][:,2].max()),6.,places=5)

    def test_flat_main_roof_and_curated_tower_extent_keep_height_and_source_void(self):
        from buildgen.geometry import sky,sky_vertex_count
        fp=footprints()[2]
        extent=Footprint(((2,2),(5,2),(5,5),(2,5)))
        spec,_=make(fp=fp,height=12.,roof_shape='flat',roof_height=np.nan,
                    _church_spire='short_pyramidal',_church_tower_footprint=extent)
        self.assertIsNotNone(spec.church.spire)
        self.assertTrue(extent.shape().covers(spec.church.spire.footprint.shape()))
        plan=freeze_items([(spec,0.,0.)])[0][0]
        skyline=b.Mesh();sky(skyline,plan,0.,0.)
        self.assertEqual(skyline.n,sky_vertex_count(plan))
        self.assertAlmostEqual(float(np.asarray(skyline.P).reshape(-1,3)[:,2].max()),12.,places=5)
        for mesh in (compiled(spec),compiled(spec,lite=True),compiled(spec,collision=True)):
            projected=[Polygon(mesh[0][ids][:,:2]) for ids in mesh[2] if np.ptp(mesh[0][ids][:,2])<1e-5]
            hole=Polygon(fp.holes[0])
            self.assertLess(sum(p.intersection(hole).area for p in projected if p.area>1e-8),1e-7)

    def test_collinear_source_vertices_keep_complete_church_apertures(self):
        full=Footprint(((0,0),(24,0),(24,12),(0,12)))
        sampled=Footprint(((0,0),(7,0),(15,0),(24,0),(24,12),(0,12)))
        for family in churches.FAMILIES:
            a,_=make(family,full,roof_shape='flat',roof_height=0.,_church_spire='none')
            c,_=make(family,sampled,roof_shape='flat',roof_height=0.,_church_spire='none')
            a.door=(0,12.);c.door=(1,5.)
            def apertures(spec):
                resolved=programme.derive(spec)
                return {(resolved.run(e.boundary,e.edge).start,resolved.run(e.boundary,e.edge).end):
                        tuple((o.kind,o.left,o.right,o.bottom,o.top,o.columns) for o in e.openings)
                        for e in churches.layout(spec,0.,0.).elevations}
            self.assertEqual(apertures(a),apertures(c))
            for lite in (False,True):
                left,right=b.Mesh(),b.Mesh()
                churches._walls(left,a,0.,0.,-b.SKIRT_M,lite)
                churches._walls(right,c,0.,0.,-b.SKIRT_M,lite)
                self.assertEqual(left.P,right.P)
                self.assertEqual(left.T,right.T)

    def test_collinear_party_wall_change_stops_the_shared_grid(self):
        fp=Footprint(((0,0),(7,0),(15,0),(24,0),(24,12),(0,12)))
        spec,_=make(fp=fp,roof_shape='flat',roof_height=0.,_party_walls=((0,1),))
        resolved=programme.derive(spec)
        layouts=churches.layout(spec,0.,0.)
        opaque=next(e for e in layouts.elevations if e.boundary==0 and e.edge==1)
        self.assertEqual(opaque.openings,())
        self.assertTrue(resolved.run(0,1).party_wall)
        self.assertNotEqual(resolved.run(0,0),resolved.run(0,2))


def math_dist(a,c):
    return float(np.linalg.norm(np.asarray(c)-a))


if __name__=='__main__':unittest.main()
