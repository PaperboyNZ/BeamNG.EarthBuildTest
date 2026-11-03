"""Connected shared sites, continuous contact and deterministic sector partitions."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import geotiles
import productcache
from sitegen import shared_layouts as sl,shared_courts as sc
from sitegen.identity import SourceIdentity,SourceRevision,CanonicalFrame
from sitegen.plan import EntityRef,FrameContext,Membership,PhysicalExtent,Polygon as Ring,ResourceRecord,SiteEvidence,SitePlan,InterfaceRecord,VerticalInterval


def rectangle(x0,y0,x1,y1):return Ring(((x0,y0),(x1,y0),(x1,y1),(x0,y1)))


def fixture(cross=False):
    gx,gy=geotiles.tile_of(-36.91,174.90);tile=geotiles.geobox(gx,gy)
    lat,lon=tile.frame.lat0,tile.frame.lon0
    if cross:lon=geotiles.info(gx,gy)[5]
    frame=CanonicalFrame(round(lon*1e7),round(lat*1e7))
    identity=SourceIdentity('shared-test','grounds');site=EntityRef(identity,'site')
    members=tuple(EntityRef(SourceIdentity(sc.BUILDING_NAMESPACE,name),'building') for name in ('walk','customer','delivery'))
    buildings=(rectangle(6,20,12,28),rectangle(-4,20,4,28),rectangle(-17,20,-9,28))
    ext=PhysicalExtent('ground',rectangle(-20,-20,20,20),VerticalInterval(19,21,'ellipsoidal_height'))
    evidence=SiteEvidence(identity,FrameContext('canonical_enu',frame),(SourceRevision(identity,'1'),),
        tuple(Membership(m) for m in members),rectangle(-24,-20,24,30),(ext,),buildings, 'surveyed_property')
    ports=[]
    for member,kind,x,w in zip(members,('pedestrian','parking','service'),(9.,0.,-13.),(2.,6.,6.)):
        for owner,y,label in ((site,-20.,'entry'),(member,20.,'destination')):
            ports.append(InterfaceRecord(kind+'-'+label,owner,kind,((x-w/2,y,20.03),(x+w/2,y,20.03))))
    plan=SitePlan(evidence,tuple(ports),(ResourceRecord('ground','shared_circulation',site,members),))
    return tile,plan


class SharedLayouts(unittest.TestCase):
    def fit(self,plan=None,elev=None):
        return sl.fit(plan or fixture()[1],elev or (lambda la,lo:np.full(np.shape(la),20.)))

    def test_routes_precede_parking_and_soft_ground(self):
        layout,why=self.fit();self.assertIsNone(why)
        self.assertEqual({r.kind for r in layout.routes},{'pedestrian','vehicle','service'})
        self.assertGreater(len(layout.stalls),0);self.assertGreater(len(layout.beds),0)
        self.assertLessEqual(layout.terrain_points,sl.MAX_PROBES)
        occupied=unary_union([Polygon(np.array(s.top)[:,:2]) for s in layout.surfaces])
        self.assertAlmostEqual(occupied.area,1600.,places=5)
        self.assertAlmostEqual(sum(Polygon(np.array(s.top)[:,:2]).area for s in layout.surfaces),occupied.area,places=5)
        for bed in layout.beds:self.assertLess(bed.shape().intersection(occupied).area,1e-7)
        for a in layout.stalls:
            for b in layout.stalls:
                if a!=b:self.assertLess(Polygon(a).intersection(Polygon(b)).area,1e-7)

    def test_no_safe_pedestrian_route_means_no_parking(self):
        _,plan=fixture()
        kept=tuple(i for i in plan.interfaces if i.kind!='pedestrian')
        members=tuple(m for m in plan.evidence.memberships if m.member.identity.feature_id!='walk')
        evidence=replace(plan.evidence,memberships=members)
        resource=replace(plan.resources[0],consumers=tuple(m.member for m in members))
        layout,why=self.fit(replace(plan,evidence=evidence,interfaces=kept,resources=(resource,)))
        self.assertIsNone(why);self.assertEqual(layout.stalls,())

    def test_missing_and_inconsistent_evidence_fails_atomically(self):
        _,plan=fixture()
        self.assertIsNotNone(self.fit(replace(plan,evidence=replace(plan.evidence,exclusions=None)))[1])
        self.assertIsNotNone(self.fit(elev=lambda la,lo:np.full(np.shape(la),np.nan))[1])
        i=plan.interfaces[0]
        changed=replace(i,endpoints=tuple((x,y,z+2) for x,y,z in i.endpoints))
        self.assertIsNotNone(self.fit(replace(plan,interfaces=(changed,*plan.interfaces[1:])))[1])
        conflict=replace(plan.evidence,exclusions=(rectangle(-1,-1,1,1),))
        self.assertEqual(self.fit(replace(plan,evidence=conflict))[1],'shared_layout_exclusion_conflict')

    def test_cross_sector_fragments_cover_once_with_identical_seams(self):
        _,plan=fixture(cross=True);layout,why=self.fit(plan);self.assertIsNone(why)
        sectors=sl.sectors(plan);self.assertEqual(len(sectors),2)
        fragments=[sl.partition(layout,*s) for s in sectors]
        surfaces=[unary_union([Polygon(np.asarray(c.top)[:,:2]) for c in f.surfaces]) for f in fragments]
        self.assertLess(surfaces[0].intersection(surfaces[1]).area,1e-7)
        self.assertAlmostEqual(unary_union(surfaces).area,1600.,places=5)
        def samples(fragment):
            return {(round(x,7),round(y,7)):z for cell in fragment.surfaces for x,y,z in cell.top}
        a,b=map(samples,fragments);common=a.keys()&b.keys()
        self.assertGreater(len(common),5)
        self.assertLess(max(abs(a[k]-b[k]) for k in common),1e-8)
        for sector,f in zip(sectors,fragments):
            self.assertEqual(f,sl.partition(layout,*sector))
            codec=productcache.Codec();self.assertEqual(codec.decode(codec.encode(f)),f)
            sites,boxes,masks=sl.metadata(f,sc._frame(plan));self.assertTrue(boxes);self.assertTrue(masks)
            self.assertTrue(all(r['fragment'].endswith(f.sector) for r in sites[0]['resources']))

    def test_native_mesh_has_matching_visual_and_contact_heights(self):
        layout,why=self.fit();self.assertIsNone(why)
        mesh=sc.compile((layout,),sc._frame(layout.plan));self.assertIsNotNone(mesh)
        self.assertTrue(np.isfinite(mesh[0]).all())
        top_area=0.
        for face in mesh[1]:
            p=mesh[0][face];n=np.cross(p[1]-p[0],p[2]-p[0])
            if n[2]>1e-8:top_area+=n[2]/2
        self.assertAlmostEqual(top_area,1600.,places=4)

    def test_runtime_catalogue_selects_both_sectors_and_detects_physical_conflict(self):
        _,plan=fixture(cross=True)
        entries=tuple((sector,plan) for sector in sl.sectors(plan))
        outputs=[]
        with patch.object(sc,'catalogue',return_value=('test',entries,())):
            for gx,gy in reversed(sl.sectors(plan)):
                tile=geotiles.geobox(gx,gy)
                layouts,notes=sc.build_tile(tile,tile.frame,lambda la,lo:np.full(np.shape(la),20.))
                self.assertFalse(notes);self.assertEqual(len(layouts),1);outputs.extend(layouts)
                _,boxes,masks=sc.metadata(layouts,tile.frame)
                self.assertTrue(boxes)
                with self.assertRaisesRegex(RuntimeError,'existing_physical_conflict'):
                    sc.build_tile(tile,tile.frame,lambda la,lo:np.full(np.shape(la),20.),obstacles=masks)
        revisions={sl.metadata(layout,sc._frame(plan))[0][0]['surface_revision'] for layout in outputs}
        self.assertEqual(len(revisions),1)

    def test_parking_paint_and_stock_plants_use_resolved_geometry(self):
        layout,why=self.fit();self.assertIsNone(why)
        parking,marks,props=sl.additions(layout,sc._frame(layout.plan),lambda la,lo:np.full(np.shape(la),20.))
        self.assertEqual(len(parking),len(layout.stalls));self.assertGreater(len(marks),0)
        self.assertGreater(len(props),0)
        self.assertTrue(all(p[0] in ('site_shrub','site_rock') for p in props))
        for chunk in marks:
            self.assertTrue(chunk['fixed']);self.assertTrue(chunk['deck'])
            self.assertEqual(chunk['layer'],'mark')
        # Generated marks go through the existing render-only road mesh, never
        # into the shared contact mesh.
        import roadmesh
        ribbons=roadmesh.ribbons(marks)
        self.assertEqual(len(ribbons),len(marks))
        self.assertTrue(all(r[-1] is not None for r in ribbons))

    def test_varying_slope_preserves_pinned_interfaces_and_sector_seams(self):
        _,plan=fixture(cross=True);frame=sc._frame(plan)
        # Analytic, gently changing terrain with measured source-frame openings.
        coeff=np.array([20.03,.005,.002,.0001,0.,.00008])
        interfaces=tuple(replace(i,endpoints=tuple((x,y,float(sl.height(coeff,[[x,y]])[0])) for x,y,_ in i.endpoints)) for i in plan.interfaces)
        plan=replace(plan,interfaces=interfaces)
        def elev(lat,lon):
            x,y,_=frame.geodetic_to_enu(lat,lon,np.zeros(np.shape(lat)))
            xyz=np.c_[x,y,sl.height(coeff,np.c_[x,y])-.03]
            return frame.enu_to_geodetic(xyz[:,0],xyz[:,1],xyz[:,2])[2]
        layout,why=self.fit(plan,elev);self.assertIsNone(why)
        for i in plan.interfaces:
            for x,y,z in i.endpoints:self.assertAlmostEqual(sl.height(layout.coefficients,[[x,y]])[0],z,places=6)
        self.assertGreater(abs(layout.coefficients[3]),.00005)
        # Check actual emitted triangle slopes and equal heights, not just the fit.
        levels={}
        for sector in sl.sectors(plan):
            for cell in sl.partition(layout,*sector).surfaces:
                p=np.array(cell.top);plane=np.linalg.solve(np.c_[p[:,:2],np.ones(3)],p[:,2])
                self.assertLessEqual(np.linalg.norm(plane[:2]),sl.MAX_GRADE)
                for x,y,z in cell.top:
                    key=(round(x,7),round(y,7))
                    if key in levels:self.assertAlmostEqual(levels[key],z,places=7)
                    levels[key]=z

    def test_holes_remain_open_and_detours_do_not_cross_reserved_paths(self):
        _,plan=fixture()
        ext=plan.evidence.physical_extents[0]
        hole=rectangle(15,-3,18,3)
        changed=replace(ext,boundary=Ring(ext.boundary.outer,(hole.outer,)))
        plan=replace(plan,evidence=replace(plan.evidence,physical_extents=(changed,)))
        layout,why=self.fit(plan);self.assertIsNone(why)
        self.assertTrue(all(not Polygon(np.asarray(c.top)[:,:2]).covers(Point(16,0)) for c in layout.surfaces))
        self.assertAlmostEqual(sum(Polygon(np.asarray(c.top)[:,:2]).area for c in layout.surfaces),1582.,places=5)

    def test_production_encoder_and_visual_refinement_retain_shared_physics(self):
        import json
        import blockworker as bw
        from buildgen import products
        from test_sitegen_shared_courts import SharedCourtProductsTests
        case=SharedCourtProductsTests('test_native_product_and_full_upgrade_keep_common_physics_and_source_records')
        case.setUp();self.addCleanup(case.doCleanups)
        tile,plan=fixture();layout,why=self.fit(plan);self.assertIsNone(why)
        case.tile=tile;case.key,case.dependencies=products.address(tile,'shared-layout-fixture')
        fragment=sl.partition(layout,tile.gx,tile.gy)
        P=case.parts('lite');P.shared_courts=(fragment,)
        P.dmesh=sc.compile((fragment,),tile.frame,(*tile.box[:2],0.))
        parking,paint,planting=sl.additions(fragment,tile.frame,lambda la,lo:np.full(np.shape(la),20.))
        P.park.extend(parking);P.chunks.extend(paint);P.props.extend(planting)
        output=case.root/'shared-layout';output.mkdir()
        path,n,info=bw._write_geo_content(str(output),'/shared-layout',tile,P)
        before=json.loads((output/Path(path).name).read_text())
        self.assertEqual(before['sharedSites']['sites'][0]['surface_revision'],fragment.contact_revision)
        self.assertTrue(before['colliders']['deck'])
        self.assertTrue(products.retain(bw,tile,case.key,case.dependencies,P,str(output),'/shared-layout',n,info,case.watched))
        target=case.root/'shared-layout-full';target.mkdir()
        with patch.object(sl,'fit',side_effect=AssertionError('site refit during visual upgrade')),patch.object(bw,'_tile_parts',side_effect=AssertionError('replanned')):
            result=products.refine(bw,tile,case.key,str(target),'/shared-layout-full','full')
        after=json.loads((target/Path(result[0]).name).read_text())
        self.assertEqual(before['physicalHash'],after['physicalHash'])
        self.assertEqual(before['sharedSites'],after['sharedSites'])
        self.assertEqual(before['colliders']['deck'],after['colliders']['deck'])


if __name__=='__main__':unittest.main()
