"""Explicit canonical common pavement: one producer, bounded fit and live products."""
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
import os
from pathlib import Path
import pickle
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from shapely.geometry import Polygon, Point

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import blockworker as bw
import buildings as b
import geodesy
import geotiles
import inputwatch
import productcache
from buildgen import freeze_items, products
from buildgen.topology import Footprint
from sitegen import shared_courts as sc
from sitegen.identity import CanonicalFrame, SourceIdentity, SourceRevision
from sitegen.plan import (EntityRef, FrameContext, Membership, PhysicalExtent, Polygon as RecordPolygon,
                         ResourceRecord, SiteEvidence, SiteGraph, SitePlan, VerticalInterval)
import test_buildgen_facades as facades
import test_buildgen_products as product_tests


def polygon(x0, y0, x1, y1, holes=()):
    return RecordPolygon(((x0,y0),(x1,y0),(x1,y1),(x0,y1)), holes)


def fixture():
    gx, gy = geotiles.tile_of(-36.91493, 174.9094)
    tile = geotiles.geobox(gx, gy)
    frame = CanonicalFrame(round(tile.frame.lon0*1e7), round(tile.frame.lat0*1e7))
    identity = SourceIdentity('survey-pilot', 'court')
    members = tuple(EntityRef(SourceIdentity(sc.BUILDING_NAMESPACE, name), 'building') for name in ('A', 'B'))
    footprints = (polygon(-50,-10,-30,10), polygon(30,-10,50,10))
    surface = polygon(-15,-20,15,20, (polygon(-3,-3,3,3).outer,))
    e = SiteEvidence(identity, FrameContext('canonical_enu', frame), (SourceRevision(identity, 'survey-1'),),
        tuple(Membership(m) for m in members), polygon(-60,-45,60,45),
        (PhysicalExtent('court-surface', surface, VerticalInterval(19.98,20.02,'ellipsoidal_height')),), footprints)
    plan = SitePlan(e, resources=(ResourceRecord('court-surface','shared_circulation',e.ref,members),))
    source = sc._frame(plan)
    items = []
    for member, fp in zip(members, footprints):
        points = sc.project_points([(*p,0.) for p in fp.outer], source, tile.frame)
        local = points[:, :2]-np.asarray(tile.box[:2])
        spec = facades.building(fp=Footprint(local), seed_id=member.identity.feature_id,
                               **{'class':'house','height':6.,'roof_shape':'flat'})
        items.append((spec,20.,20.))
    return tile, plan, tuple(items)


class SharedCourtTests(unittest.TestCase):
    def setUp(self):
        self.tile, self.plan, self.items = fixture()

    def build(self, plan=None, **kwargs):
        with patch.object(sc, 'catalogue', return_value=('fixture', (((self.tile.gx,self.tile.gy),plan or self.plan),), ())):
            return sc.build_tile(self.tile, self.tile.frame, lambda lat,lon: np.full(np.shape(lat),20.),
                                 items=kwargs.pop('items', self.items), origin=(*self.tile.box[:2],0.), **kwargs)

    def test_empty_tile_does_not_collect_physical_masks(self):
        from unittest.mock import Mock
        collect=Mock(side_effect=AssertionError('unneeded physical masks'))
        with patch.object(sc,'catalogue',return_value=('fixture',(),())):
            self.assertEqual(sc.build_tile(self.tile,self.tile.frame,None,obstacle_factory=collect),((),()))
        collect.assert_not_called()

    def test_lazy_physical_masks_preserve_courts_and_conflict_rejection(self):
        from unittest.mock import Mock
        collect=Mock(return_value=())
        self.assertEqual(self.build(),self.build(obstacle_factory=collect))
        collect.assert_called_once_with()
        rings=[[list(p) for p in sc.project_points([(-10,-10,20.),(-5,-10,20.),(-5,10,20.),(-10,10,20.)],
                    sc._frame(self.plan),self.tile.frame)[:,:2]]]
        collect=Mock(return_value=[dict(rings=rings,min_z=19.,max_z=21.)])
        with self.assertRaisesRegex(RuntimeError,'shared_court_physical_conflict'):
            self.build(obstacle_factory=collect)
        collect.assert_called_once_with()

    def test_empty_tile_still_rejects_changed_catalogue_before_collecting(self):
        from unittest.mock import Mock
        collect=Mock(side_effect=AssertionError('unneeded physical masks'))
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'sites.json';path.write_text('{}')
            with patch.dict(os.environ,{'BNE_SHARED_SITE_RECORDS':str(path)}), \
                 patch.object(sc,'catalogue',return_value=('old-digest',(),())):
                with self.assertRaisesRegex(RuntimeError,'catalogue changed'):
                    sc.build_tile(self.tile,self.tile.frame,None,obstacle_factory=collect)
        collect.assert_not_called()

    def test_two_members_share_one_closed_court_with_exact_hole(self):
        courts, notes = self.build()
        self.assertEqual(notes, ())
        self.assertEqual(len(courts), 1)
        court = courts[0]
        self.assertEqual(len(court.plan.resources[0].consumers), 2)
        self.assertEqual(court.plan.resources[0].producer, self.plan.evidence.ref)
        self.assertEqual(court.plan.surface_validation, 'unresolved')
        self.assertLessEqual(court.terrain_points, sc.MAX_POINTS)
        mesh = sc.compile(courts, sc._frame(self.plan))
        points, faces = mesh[:2]
        top = []
        for face in faces:
            p = points[face]
            n = np.cross(p[1]-p[0], p[2]-p[0])
            if n[2] > 1e-8: top.append(Polygon(p[:,:2]))
        self.assertAlmostEqual(sum(p.area for p in top), 30*40-6*6, places=6)
        self.assertTrue(all(not p.covers(Point(0,0)) for p in top))
        # Exact coordinate edges pair twice in a closed physical shell.
        edges = {}
        for face in faces:
            xyz = [tuple(p) for p in points[face]]
            for a,c in zip(xyz,xyz[1:]+xyz[:1]):
                key = tuple(sorted((a,c))); edges[key] = edges.get(key,0)+1
        self.assertEqual(set(edges.values()), {2})

    def test_missing_evidence_and_unsupported_levels_never_become_free_ground(self):
        e = self.plan.evidence
        variants = (
            replace(self.plan, evidence=replace(e, exclusions=None)),
            replace(self.plan, evidence=replace(e, physical_extents=(replace(e.physical_extents[0],interval=None),))),
            replace(self.plan, evidence=replace(e, memberships=(replace(e.memberships[0],interval=VerticalInterval(0,1)),*e.memberships[1:]))),
        )
        for plan in variants:
            court, why = sc.fit(plan, lambda lat,lon: np.full(np.shape(lat),20.))
            self.assertIsNone(court); self.assertIsNotNone(why)
        with self.assertRaisesRegex(RuntimeError,'shared_court_unresolved_member'):
            self.build(items=self.items[:1])

    def test_terrain_failure_roughness_height_conflict_and_grade_are_atomic(self):
        frame = sc._frame(self.plan)
        def x(lat,lon): return frame.geodetic_to_enu(lat,lon,np.zeros(np.shape(lat)))[0]
        callbacks = (None, lambda lat,lon:np.full(np.shape(lat),np.nan), lambda lat,lon:np.zeros(1),
            lambda lat,lon:np.full(np.shape(lat),40.), lambda lat,lon:20.+.8*np.sin(x(lat,lon)),
            lambda lat,lon:20.+.1*x(lat,lon))
        wide = replace(self.plan, evidence=replace(self.plan.evidence, physical_extents=(
            replace(self.plan.evidence.physical_extents[0],interval=VerticalInterval(18,22,'ellipsoidal_height')),)))
        for callback in callbacks:
            court, why = sc.fit(wide, callback)
            self.assertIsNone(court); self.assertIsNotNone(why)
        self.assertEqual(sc.fit(self.plan, lambda lat,lon:np.full(np.shape(lat),20.),point_budget=2)[1],
                         'shared_court_terrain_budget')

    def test_overlap_exclusions_and_existing_host_surfaces_omit_whole_court(self):
        e = self.plan.evidence
        blocked = replace(self.plan, evidence=replace(e, exclusions=(*e.exclusions, polygon(-10,-10,-5,10))))
        self.assertEqual(sc.fit(blocked, lambda lat,lon:np.full(np.shape(lat),20.))[1], 'shared_court_physical_conflict')
        extra = replace(e.physical_extents[0],identity='overlap')
        duplicate = replace(self.plan, evidence=replace(e,physical_extents=(*e.physical_extents,extra)),
            resources=(*self.plan.resources,replace(self.plan.resources[0],identity='overlap')))
        self.assertEqual(sc.fit(duplicate, lambda lat,lon:np.full(np.shape(lat),20.))[1], 'shared_court_duplicate_physical_owner')
        rings = [[list(p) for p in sc.project_points([(-10,-10,20.),(-5,-10,20.),(-5,10,20.),(-10,10,20.)],
                    sc._frame(self.plan),self.tile.frame)[:,:2]]]
        with self.assertRaisesRegex(RuntimeError,'shared_court_physical_conflict'):
            self.build(obstacles=[dict(rings=rings,min_z=19.,max_z=21.)])

    def test_multisector_source_is_not_split_into_load_order_fragments(self):
        cross = replace(self.plan,evidence=replace(self.plan.evidence,association_extent=polygon(-200,-45,200,45)))
        self.assertIsNone(sc.host(cross))
        self.assertEqual(sc.host(self.plan), (self.tile.gx,self.tile.gy))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'shared.json'; path.write_text(SiteGraph((cross,)).to_json())
            with patch.dict(os.environ,{'BNE_SHARED_SITE_RECORDS':str(path)}):
                sc.catalogue.cache_clear()
                try:
                    _, entries, notes = sc.catalogue()
                    self.assertEqual(entries, ())
                    self.assertEqual(notes[0][1], 'shared_court_cross_sector_requires_retention')
                finally: sc.catalogue.cache_clear()

    def test_full_xyz_rebase_and_canonical_revision_survive_worker_cache(self):
        courts, _ = self.build(); court = courts[0]
        with self.assertRaises(FrozenInstanceError): court.bottom = 0.
        codec = productcache.Codec(); encoded = codec.encode(court)
        for restored in (pickle.loads(pickle.dumps(court)), codec.decode(encoded)):
            self.assertEqual(restored, court); self.assertEqual(restored.revision, court.revision)
        target = geodesy.EnuFrame(-36.9,174.8,15.)
        source = sc._frame(self.plan)
        original = sc.compile(courts, source)
        projected = sc.compile(courts, target, (100.,200.,3.))
        back = sc.project_points(projected[0]+(100.,200.,3.),target,source)
        np.testing.assert_allclose(back,original[0],atol=4e-9,rtol=0.)
        np.testing.assert_array_equal(projected[1], original[1])
        np.testing.assert_array_equal(projected[2], original[2])

    def test_source_order_does_not_create_duplicate_owners_and_tile_budget_is_atomic(self):
        _, entries, _ = 'fixture', (((self.tile.gx,self.tile.gy),self.plan),), ()
        with patch.object(sc,'catalogue',return_value=('fixture',entries*(sc.MAX_TILE_SITES+1),())):
            with self.assertRaisesRegex(RuntimeError,'shared_court_tile_budget'):
                sc.build_tile(self.tile,self.tile.frame,lambda lat,lon:np.full(np.shape(lat),20.))
        changed = replace(self.plan,evidence=replace(self.plan.evidence,identity=SourceIdentity('survey-pilot','second'),
                          physical_extents=(replace(self.plan.evidence.physical_extents[0],identity='second-surface'),)),
                          resources=())
        # Give the other site its own producer; same ground still has one owner.
        changed = replace(changed, resources=(replace(self.plan.resources[0],identity='second-surface',producer=changed.evidence.ref),))
        SiteGraph((self.plan,changed))  # Real catalogue producer rules also hold.
        records = (((self.tile.gx,self.tile.gy),self.plan),((self.tile.gx,self.tile.gy),changed))
        for order in (records, records[::-1]):
            with patch.object(sc,'catalogue',return_value=('fixture',order,())):
                with self.assertRaisesRegex(RuntimeError,'shared_court_physical_conflict'):
                    sc.build_tile(self.tile,self.tile.frame,lambda lat,lon:np.full(np.shape(lat),20.),
                        items=self.items,origin=(*self.tile.box[:2],0.))

    def test_catalogue_hash_input_watch_and_vegetation_overflow(self):
        import revisit
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'shared.json'; path.write_text(SiteGraph((self.plan,)).to_json())
            with patch.dict(os.environ,{'BNE_SHARED_SITE_RECORDS':str(path),'BNE_BUILDING_GENERATOR':'v2'}), patch.object(revisit,'_code',[]):
                sc.catalogue.cache_clear()
                try:
                    first = revisit.code_key()
                    with inputwatch.capture() as watched:
                        courts, _ = sc.build_tile(self.tile,self.tile.frame,lambda lat,lon:np.full(np.shape(lat),20.),
                            items=self.items,origin=(*self.tile.box[:2],0.))
                    self.assertEqual(len(courts),1)
                    snapshot = inputwatch.snapshot(watched)
                    self.assertTrue(inputwatch.current(snapshot))
                    path.write_text(SiteGraph(()).to_json())
                    with self.assertRaisesRegex(RuntimeError,'restart'):
                        sc.build_tile(self.tile,self.tile.frame,lambda lat,lon:np.full(np.shape(lat),20.),
                            items=self.items,origin=(*self.tile.box[:2],0.))
                    sc.catalogue.cache_clear(); revisit._code.clear()
                    self.assertFalse(inputwatch.current(snapshot)); self.assertNotEqual(first,revisit.code_key())
                finally: sc.catalogue.cache_clear()
        _, _, masks = sc.metadata(courts,self.tile.frame)
        from sitegen import hardscape
        with patch.object(hardscape,'MAX_POLYGONS',0):
            result = sc.extend_masks(dict(v=1,polygons=[]),masks,(-1,-2,3,4))
        self.assertEqual(len(result['polygons']),1)
        self.assertTrue(result['polygons'][0]['unknown_height'])

    def test_malformed_and_oversized_catalogues_are_bounded_before_record_construction(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'sites.json'
            with patch.dict(os.environ,{'BNE_SHARED_SITE_RECORDS':str(path)}):
                try:
                    for value in ({'record':[]}, {'record':{'type':'SiteGraph','value':{'sites':[None]*(sc.MAX_SITES+1)}}}):
                        path.write_text(json.dumps(value)); sc.catalogue.cache_clear()
                        with self.assertRaises(ValueError): sc.catalogue()
                    path.write_bytes(b' '*(sc.MAX_BYTES+1)); sc.catalogue.cache_clear()
                    with self.assertRaisesRegex(ValueError,'byte budget'): sc.catalogue()
                finally: sc.catalogue.cache_clear()

    def test_specialist_without_footprint_cannot_be_silently_ignored(self):
        points = sc.project_points([(-4,-4,0.),(4,-4,0.),(4,4,0.),(-4,4,0.)],
                                  sc._frame(self.plan),self.tile.frame)[:,:2]-self.tile.box[:2]
        specialist = SimpleNamespace(ring=points,footprint=None,evidence=None,access=None)
        with self.assertRaisesRegex(RuntimeError,'shared_court_physical_conflict'):
            self.build(items=(*self.items,(specialist,20.,20.)))
        with self.assertRaisesRegex(RuntimeError,'shared_court_unknown_building_obstacle'):
            self.build(items=(*self.items,(SimpleNamespace(),20.,20.)))

    def test_two_touching_resources_share_one_accepted_grade_plane(self):
        ext = self.plan.evidence.physical_extents[0]
        extents = (replace(ext,identity='left',boundary=polygon(-15,-20,0,20)),
                   replace(ext,identity='right',boundary=polygon(0,-20,15,20)))
        resources = tuple(replace(self.plan.resources[0],identity=p.identity) for p in extents)
        plan = replace(self.plan,evidence=replace(self.plan.evidence,physical_extents=extents),resources=resources)
        frame = sc._frame(plan)
        def elev(lat,lon):
            x = frame.geodetic_to_enu(lat,lon,np.zeros(np.shape(lat)))[0]
            return 20.+x*.03
        plan = replace(plan,evidence=replace(plan.evidence,physical_extents=tuple(
            replace(p,interval=VerticalInterval(19,21,'ellipsoidal_height')) for p in extents)))
        court, why = sc.fit(plan,elev)
        self.assertIsNone(why); self.assertIsNotNone(court)
        self.assertAlmostEqual(court.plane[0],.03,places=5)
        self.assertLessEqual(court.terrain_points,sc.MAX_POINTS)
        mesh = sc.compile((court,),frame)
        seam = mesh[0][np.abs(mesh[0][:,0])<1e-7]
        upper = seam[seam[:,2]>court.bottom+.01]
        # Both resources use exactly the same height at every shared coordinate.
        for y in set(upper[:,1]):
            self.assertLess(np.ptp(upper[upper[:,1]==y,2]),1e-9)


class SharedCourtProductsTests(unittest.TestCase):
    parts = product_tests.IndependentProductsTests.parts

    def setUp(self):
        product_tests.IndependentProductsTests.setUp(self)
        self.addCleanup(self.close_index)
        self.tile, self.site, items = fixture()
        self.plans = freeze_items(items)

    def close_index(self):
        import revisit
        fd = revisit._where.pop(str(self.cache),None)
        if fd is not None: os.close(fd)

    def test_native_product_and_full_upgrade_keep_common_physics_and_source_records(self):
        with patch.object(sc,'catalogue',return_value=('fixture',(((self.tile.gx,self.tile.gy),self.site),),())):
            courts, notes = sc.build_tile(self.tile,self.tile.frame,lambda lat,lon:np.full(np.shape(lat),20.),
                items=self.plans,origin=(*self.tile.box[:2],0.))
        self.assertEqual(notes,()); self.assertEqual(len(courts),1)
        P = self.parts('lite'); P.shared_courts = courts
        P.dmesh = sc.compile(courts,self.tile.frame,(*self.tile.box[:2],0.))
        output = self.root/'common'; output.mkdir()
        path,n,info = bw._write_geo_content(str(output),'/common',self.tile,P)
        before = json.loads((output/Path(path).name).read_text())
        self.assertEqual(before['sharedSites']['host'],self.tile.key)
        resource = before['sharedSites']['sites'][0]['resources'][0]
        self.assertEqual(resource['producer'],self.site.evidence.ref.to_dict())
        self.assertEqual(len(resource['consumers']),2)
        self.assertIn('deck',before['colliders']); self.assertTrue(info['parts']['deck']['col'])
        self.assertTrue(products.retain(bw,self.tile,self.key,self.dependencies,P,str(output),'/common',n,info,self.watched))
        cached = productcache.Store(str(self.cache)).load('accepted-plan',self.key)
        self.assertEqual(cached.value['shared_sites'],courts)
        newdir = self.root/'full-common'; newdir.mkdir()
        with patch.object(bw,'_tile_parts',side_effect=AssertionError('replanned')),\
             patch.object(sc,'fit',side_effect=AssertionError('refit common surface')):
            result = products.refine(bw,self.tile,self.key,str(newdir),'/full-common','full')
        after = json.loads((newdir/Path(result[0]).name).read_text())
        self.assertEqual(before['physicalHash'],after['physicalHash'])
        self.assertEqual(before['sharedSites'],after['sharedSites'])
        self.assertEqual(before['colliders']['deck'],after['colliders']['deck'])
        deck = bw.geo_names(self.tile.key)['deck']
        self.assertEqual((output/deck).read_bytes(),(newdir/deck).read_bytes())


if __name__ == '__main__': unittest.main()
