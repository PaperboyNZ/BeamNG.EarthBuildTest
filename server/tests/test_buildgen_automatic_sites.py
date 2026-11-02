"""Default commercial grounds use the real building/access runtime."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from shapely.geometry import Polygon, box
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import automatic_sites, freeze_items, sitework
from buildgen.topology import Footprint
from test_buildgen_commercial import fixture
from test_buildgen_facades import building


def road(y=-25.):
    return [(np.array([[-50.,y],[100.,y]]),3.,'residential',False)]

def flat(p): return np.zeros(len(p))

def area(s): return Polygon([p[:2] for p in s.top])

class AutomaticSitesTests(unittest.TestCase):
    def test_bed_curb_ring_has_closed_corners_and_preserves_fitted_surface(self):
        from buildgen.access import Solid
        from shapely.ops import unary_union
        for angle,origin,z0 in ((0.,np.zeros(2),0.),(.63,np.array([117.,-89.]),213.)):
            tangent=np.array([np.cos(angle),np.sin(angle)])
            normal=np.array([-tangent[1],tangent[0]])
            xy=np.array([origin+tangent*x+normal*y for x,y in ((0,0),(15,0),(15,3),(0,3))])
            plane=np.array([.04,-.025,z0])
            z=np.c_[xy,np.ones(4)]@plane
            bed=Solid('site_garden_bed',tuple(map(tuple,np.c_[xy,z])),float(z.min()-.1))
            interiors,curbs=automatic_sites._curbed_beds([bed],origin,tangent,normal)
            self.assertEqual(len(interiors),1);self.assertEqual(len(curbs),4)
            union=unary_union([area(v) for v in (*interiors,*curbs)])
            self.assertLess(union.symmetric_difference(area(bed)).area,1e-8)
            for i,curb in enumerate(curbs):
                self.assertLess(area(curb).intersection(area(interiors[0])).area,1e-8)
                for other in curbs[i+1:]:self.assertLess(area(curb).intersection(area(other)).area,1e-8)
                points=np.asarray(curb.top)
                np.testing.assert_allclose(points[:,2],np.c_[points[:,:2],np.ones(4)]@plane+.12,atol=1e-8)
            points=np.asarray(interiors[0].top)
            np.testing.assert_allclose(points[:,2],np.c_[points[:,:2],np.ones(4)]@plane,atol=1e-8)

    def test_sloped_runtime_curbs_and_native_plants_share_translated_ground_datum(self):
        from shapely.geometry import Point
        from buildgen import landscaping
        results=[]
        for z0 in (0.,137.):
            offset=np.array([1000.,-2000.])
            terrain=lambda p:z0+.02*(p[:,0]-offset[0])+.006*(p[:,1]-offset[1])
            fp=Footprint(((30,40),(74,40),(74,64),(30,64)))
            spec=building(44,24,fp=fp,**{'class':'supermarket','height':6.,'roof_shape':'flat',
                                        'seed_id':'grade','facade_material':'concrete'})
            spec.gring=terrain(np.asarray(spec.ring)+offset)
            item=(spec,float(spec.gring.min()),float(spec.gring.max()))
            lines=[(np.array([[-50.,15.],[150.,15.]])+offset,3.,'residential',False)]
            xy=np.array([[-50.,19.25],[150.,19.25]])+offset
            walks=[dict(pts=np.c_[xy,terrain(xy)],side=1,w=2.5)]
            b.doors([item],lines,*offset,ground=terrain,walks=walks)
            b.garage_drives([item],lines,*offset,ground=terrain,walks=walks)
            beds=[v for v in spec.access.landscape if v.kind=='site_garden_bed']
            curbs=[v for v in spec.access.solids if v.kind=='site_curb']
            self.assertTrue(beds and curbs)
            for curb in curbs:
                top=np.asarray(curb.top)
                np.testing.assert_allclose(top[:,2],terrain(top[:,:2]+offset)+.145,atol=1e-8)
            rows=b.landscape_props([item],*offset)
            self.assertTrue(rows)
            for row in rows:
                local=np.asarray(row[1:3])-offset;point=Point(local)
                radius=landscaping.native_radius(row[0],row[6])
                self.assertTrue(any(area(bed).covers(point) and area(bed).boundary.distance(point)>=radius
                                    for bed in beds))
                self.assertTrue(all(area(curb).distance(point)>=radius for curb in curbs))
            self.assertNotIn('automatic_entry_link_unresolved',spec.access.site_layout.diagnostics)
            self.assertIn('automatic_pedestrian_steps',spec.access.site_layout.diagnostics)
            self.assertGreater(spec.access.site_layout.parking,0)
            self.assertEqual(len(walks[0]['driveways']),1)
            results.append(np.asarray([row[1:7] for row in rows]))
        np.testing.assert_allclose(results[1]-results[0],
                                   np.tile([0,0,137.,0,0,0],(len(results[0]),1)),atol=1e-7)

    def test_short_pedestrian_stairs_match_endpoints_and_have_safe_treads(self):
        from buildgen.access import MAX_RISE,TREAD,LANDING
        from shapely.ops import unary_union
        for reverse in (False,True):
            points=np.array([[0,0,.3],[1.2,0,.3],[1.2,2.,.025],[0,2.,.025]])
            if reverse:points[:,2]=.325-points[:,2]
            links=automatic_sites._entry_steps(points,'step',flat,np.zeros(2))
            self.assertEqual(len(links),3)
            self.assertEqual([s.kind for s in links],['site_step','site_step','site_walk'])
            self.assertLess(unary_union([area(v) for v in links]).symmetric_difference(Polygon(points[:,:2])).area,1e-8)
            for i,link in enumerate(links):
                self.assertGreaterEqual(np.ptp(np.asarray(link.top)[:,1]),LANDING-1e-8 if i==len(links)-1 else TREAD-1e-8)
                if i:
                    self.assertGreater(area(link).boundary.intersection(area(links[i-1]).boundary).length,1.19)
                    self.assertLessEqual(abs(link.top[0][2]-links[i-1].top[0][2]),MAX_RISE+1e-8)
            self.assertAlmostEqual(links[0].top[0][2],points[0,2])
            self.assertAlmostEqual(links[-1].top[0][2],points[2,2])
            short=points.copy();short[:,1]*=.5
            self.assertIsNone(automatic_sites._entry_steps(short,'step',flat,np.zeros(2)))
            self.assertIsNone(automatic_sites._entry_steps(points,'step',lambda p:np.full(len(p),np.nan),np.zeros(2)))

    def test_millimetre_terrain_ripple_does_not_disconnect_frontage_pieces(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
        from site_terrain_check import scene
        for angle,offset,datum in ((0.,(0.,0.),0.),(-23.,(1000.,-2000.),213.)):
            result=scene('ripple-regression',angle=angle,origin=offset,datum=datum,
                         slope=(.005,.01),rough=.008)
            self.assertGreater(result['parking'],0)
            self.assertEqual(result['cuts'],1);self.assertEqual(result['raw_cuts'],1)
            self.assertNotIn('automatic_entry_link_unresolved',result['diagnostics'])
            self.assertNotIn('automatic_surface_seam_conflict',result['diagnostics'])
            self.assertGreater(result['native_props']['site_shrub'],0)
            self.assertLess(result['bed_overlap_m2'],1e-7)
        # Sharing a datum must still reject a local hump that penetrates it.
        q=np.array([[0.,0.],[4.,0.],[4.,4.],[0.,4.]])
        terrain=lambda p:np.where((p[:,0]==2)&(p[:,1]==2),.2,0.)
        self.assertIsNone(automatic_sites._fit_rect(q,terrain,np.zeros(2),np.array([0.,0.,.025])))

    def test_default_runtime_paving_beds_and_connected_parking(self):
        item=fixture('supermarket',40,20); spec=item[0]
        outline=np.array(spec.ring,copy=True)
        records=automatic_sites.resolve([item],road(),0,0,ground=flat)
        layout=spec.access.site_layout
        self.assertIsNone(spec.site)
        self.assertGreater(layout.parking,1)
        self.assertEqual(len(records),1)
        self.assertGreater(sum(area(s).area for s in spec.access.solids if s.kind=='site_parking'),100.)
        self.assertGreater(sum(area(s).area for s in spec.access.landscape if s.kind=='site_garden_bed'),10.)
        sitework.coordinate([item])
        self.assertTrue(any(s.kind=='site_garden_bed' for s in spec.access.landscape))
        self.assertTrue(np.array_equal(outline,spec.ring))
        for mesh in (b.build([item]),b.build([item],lite=True),b.collision_mesh([item])):
            self.assertTrue(np.isfinite(mesh[0]).all())
        frozen=freeze_items([item])
        self.assertTrue(frozen)

    def test_no_catalogue_reproducible_and_varied_use(self):
        for cls in ('commercial','retail','office','industrial','warehouse','supermarket'):
            item=fixture(cls,40,20)
            automatic_sites.resolve([item],road(),0,0,ground=flat)
            a=item[0].access
            self.assertTrue(any(s.kind=='site_service' or s.kind=='site_parking' for s in a.solids),cls)
            automatic_sites.resolve([item],road(),0,0,ground=flat)
            self.assertEqual(a,item[0].access,cls)

    def test_missing_terrain_shallow_restricted_and_obstacle(self):
        for depth,reason in [(-100.,'automatic_no_compatible_road')]:
            item=fixture('commercial',40,20)
            automatic_sites.resolve([item],road(depth),0,0,ground=flat)
            self.assertIn(reason,item[0].access.site_layout.diagnostics)
        item=fixture('commercial',40,20)
        automatic_sites.resolve([item],road(),0,0,ground=lambda p:np.full(len(p),np.nan))
        self.assertIn('automatic_missing_or_rough_terrain',item[0].access.site_layout.diagnostics)
        item=fixture('commercial',40,20)
        barrier=box(0,-19,20,0)
        automatic_sites.resolve([item],road(),0,0,ground=flat,obstacles=(barrier,))
        for solid in item[0].access.solids:
            if solid.kind.startswith('site_'):
                self.assertLess(area(solid).intersection(barrier).area,1e-7)
        item=fixture('commercial',40,20)
        automatic_sites.resolve([item],road(),0,0,ground=flat,bounds=(0,-10,40,20))
        for solid in item[0].access.solids:
            if solid.kind.startswith('site_'):
                self.assertTrue(box(0,-10,40,20).buffer(1e-7).covers(area(solid)))

    def test_entry_link_matches_existing_and_pavement_edges(self):
        from shapely.geometry import Point
        for y in (-7., -9., -12., -25.):
            spec=building(40,20,**{'class':'supermarket','height':6.,'roof_shape':'flat',
                                   'seed_id':'actual-road','facade_material':'concrete'})
            spec.gring=flat(spec.ring)
            item=(spec,0.,0.)
            b.doors([item],road(y),0.,0.,ground=flat)
            automatic_sites.resolve([item],road(y),0,0,ground=flat)
            spec=item[0]
            links=[s for s in spec.access.solids if s.kind=='site_walk']
            self.assertTrue(links, y)
            entry=[s for s in spec.access.solids if s.kind in ('path','threshold','step')]
            paving=[s for s in spec.access.solids if s.kind in ('site_service','site_parking')]
            def shared_z(a,b):
                boundary=area(a).boundary.intersection(area(b).boundary)
                if boundary.length < 1.19:return False
                def z_at(s,p):
                    top=np.asarray(s.top)
                    for x,z in zip(top,np.roll(top,-1,axis=0)):
                        d=z[:2]-x[:2]; length=d@d
                        t=np.clip((np.asarray(p)-x[:2])@d/length,0,1)
                        if np.linalg.norm(x[:2]+t*d-p)<1e-6:
                            return x[2]+t*(z[2]-x[2])
                    return float('nan')
                segments=list(boundary.geoms) if hasattr(boundary,'geoms') else [boundary]
                for seg in segments:
                    if not hasattr(seg,'coords'):continue
                    for p in seg.coords:
                        if abs(z_at(a,p)-z_at(b,p))>.005:return False
                return True
            self.assertTrue(any(shared_z(link,e) for link in links for e in entry),y)
            self.assertTrue(any(shared_z(link,p) for link in links for p in paving),y)
            self.assertGreater(sum(area(p).area for p in paving),20.,y)

    def test_validated_connection_crosses_public_sidewalk(self):
        spec=building(40,20,**{'class':'supermarket','height':6.,'roof_shape':'flat',
                               'seed_id':'actual-walk','facade_material':'concrete'})
        spec.gring=flat(spec.ring); item=(spec,0.,0.)
        b.doors([item],road(),0.,0.,ground=flat)
        walks=[dict(pts=np.array([[-50.,-20.75,0.],[100.,-20.75,0.]]),side=1,w=2.5)]
        records=automatic_sites.resolve([item],road(),0,0,ground=flat,walks=walks)
        self.assertGreater(spec.access.site_layout.parking,0)
        self.assertEqual(len(records),1)
        self.assertEqual(len(walks[0].get('driveways',())),1)
        self.assertTrue(any(s.kind=='site_driveway' for s in spec.access.solids))

    def test_shallow_actual_sidewalk_preserves_connected_walk(self):
        for y in (-7.,-9.):
            spec=building(40,20,**{'class':'supermarket','height':6.,'roof_shape':'flat',
                                   'seed_id':'shallow-walk','facade_material':'concrete'})
            spec.gring=flat(spec.ring); item=(spec,0.,0.)
            walks=[dict(pts=np.array([[-50.,y+4.25,0.],[100.,y+4.25,0.]]),side=1,w=2.5)]
            b.doors([item],road(y),0,0,ground=flat,walks=walks)
            automatic_sites.resolve([item],road(y),0,0,ground=flat,walks=walks)
            self.assertGreater(sum(area(s).area for s in spec.access.solids if s.kind=='site_service'),20.)
            links=[s for s in spec.access.solids if s.kind=='site_walk']
            self.assertTrue(links)
            entries=[s for s in spec.access.solids if s.kind in ('path','threshold','step')]
            self.assertTrue(any(area(s).boundary.intersection(area(e).boundary).length>=.59
                                for s in links for e in entries))
            self.assertEqual(spec.access.site_layout.parking,0)

    def test_full_runtime_keeps_beds_around_entry_link(self):
        for cls in ('supermarket','workshop','office'):
            fp=Footprint(((30,40),(74,40),(74,64),(30,64)))
            spec=building(44,24,fp=fp,**{'class':cls,'height':6.,'roof_shape':'flat',
                                        'seed_id':'translated','facade_material':'concrete'})
            spec.gring=flat(spec.ring); item=(spec,0.,0.)
            lines=[(np.array([[-50.,15.],[150.,15.]]),3.,'residential',False)]
            walks=[dict(pts=np.array([[-50.,19.25,0.],[150.,19.25,0.]]),side=1,w=2.5)]
            b.doors([item],lines,0,0,ground=flat,walks=walks)
            b.garage_drives([item],lines,0,0,ground=flat,walks=walks)
            beds=[v for v in spec.access.landscape if v.kind=='site_garden_bed']
            self.assertGreater(sum(area(v).area for v in beds),20.,cls)
            self.assertTrue(any(v.kind=='site_walk' for v in spec.access.solids))
            for bed in beds:
                for solid in spec.access.solids:
                    self.assertLess(area(bed).intersection(area(solid)).area,1e-7,cls)
            for i,bed in enumerate(beds):
                for other in beds[i+1:]:
                    self.assertLess(area(bed).intersection(area(other)).area,1e-7,cls)
            curbs=[v for v in spec.access.solids if v.kind=='site_curb']
            paving=[v for v in spec.access.solids if v.kind in ('site_parking','site_service')]
            links=[v for v in spec.access.solids if v.kind=='site_walk']
            # The parking-facing planted boundary has raised edging; the old
            # renderer only curbed the edge nearest the building facade.
            self.assertGreater(sum(area(c).boundary.intersection(area(p).boundary).length
                                   for c in curbs for p in paving),10.,cls)
            self.assertTrue(all(area(c).distance(area(link))>=.09 for c in curbs for link in links),cls)
            self.assertIn(f'automatic_bed_m2={sum(area(v).area for v in beds):.1f}',
                          spec.access.site_layout.diagnostics)
            props=b.landscape_props([item],0,0)
            self.assertIn('site_shrub',{r[0] for r in props},cls)
            self.assertIn('site_rock',{r[0] for r in props},cls)
            self.assertGreater(spec.access.site_layout.parking,0,cls)

    def test_neighboring_buildings_and_order(self):
        def scene(reverse=False):
            left=fixture('commercial',40,20,seed='left')
            right=fixture('commercial',40,20,seed='right',fp=Footprint(((41,0),(81,0),(81,20),(41,20))))
            items=[left,right]
            automatic_sites.resolve(items[::-1] if reverse else items,road(),0,0,ground=flat)
            return items
        items=scene()
        other=scene(True)
        for left,right in zip(items,other):
            self.assertEqual(left[0].access,right[0].access)
        for i,(spec,_,_) in enumerate(items):
            neighbour=items[1-i][0].footprint.shape()
            for solid in (*spec.access.solids,*spec.access.landscape):
                if solid.kind.startswith('site_'):
                    self.assertLess(area(solid).intersection(neighbour).area,1e-7)
        aa=[area(s) for s in items[0][0].access.solids if s.kind.startswith('site_')]
        bb=[area(s) for s in items[1][0].access.solids if s.kind.startswith('site_')]
        self.assertTrue(all(x.intersection(y).area<1e-7 for x in aa for y in bb))

    def test_nonlinear_terrain_never_commits_mismatched_shared_edges(self):
        terrain=lambda p: .012*np.sin(p[:,0]/4.)+.006*np.sin(p[:,1]/3.)
        item=fixture('commercial',40,20,ground=terrain)
        automatic_sites.resolve([item],road(),0,0,ground=terrain)
        solids=[s for s in item[0].access.solids if s.kind in ('site_service','site_parking')]
        self.assertTrue(solids)
        for i,a in enumerate(solids):
            for c in solids[i+1:]:
                shared=area(a).boundary.intersection(area(c).boundary)
                if shared.length<.05:continue
                aa=np.asarray(a.top);cc=np.asarray(c.top)
                pa=np.linalg.lstsq(np.c_[aa[:,:2],np.ones(4)],aa[:,2],rcond=None)[0]
                pc=np.linalg.lstsq(np.c_[cc[:,:2],np.ones(4)],cc[:,2],rcond=None)[0]
                segments=list(shared.geoms) if hasattr(shared,'geoms') else [shared]
                for line in segments:
                    if not hasattr(line,'coords'):continue
                    for point in line.coords:
                        self.assertLessEqual(abs((pa-pc)@[*point,1]),.00501)

    def test_slope_and_disable(self):
        item=fixture('commercial',40,20)
        slope=lambda p: .01*p[:,0]+.01*p[:,1]
        automatic_sites.resolve([item],road(),0,0,ground=slope)
        solids=[s for s in item[0].access.solids if s.kind in ('site_service','site_parking')]
        for i,a in enumerate(solids):
            for c in solids[i+1:]:
                edge=area(a).boundary.intersection(area(c).boundary)
                if edge.length < .05:continue
                x=np.asarray(a.top); y=np.asarray(c.top)
                pa=np.linalg.lstsq(np.c_[x[:,:2],np.ones(4)],x[:,2],rcond=None)[0]
                pc=np.linalg.lstsq(np.c_[y[:,:2],np.ones(4)],y[:,2],rcond=None)[0]
                for point in list(edge.coords):
                    self.assertLessEqual(abs((pa-pc)@[*point,1]),.00501)
        item=fixture('office',40,20)
        with patch.dict(os.environ,{'BNE_BUILDING_PATHS':'off'}):
            self.assertFalse(automatic_sites.eligible(item[0]))
            self.assertEqual(automatic_sites.resolve([item],road(),0,0,ground=flat),[])
            self.assertIsNone(item[0].access.site_layout)

if __name__=='__main__': unittest.main()
