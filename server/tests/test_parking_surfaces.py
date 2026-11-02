"""Regression cases for crossing lots, full surface coverage and gentle grading."""
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from shapely.geometry import Polygon, LineString, box

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import parking
import parkinggrade
import surface
import grading
import sidewalks
import streetscape
import roads
from test_roads import FRAME, features, rules


def lots(surface_name="", ring=None):
    xy = np.asarray(ring if ring is not None else [(0, 25), (80, 25), (80, 75), (0, 75), (0, 25)])
    la, lo, _ = FRAME.enu_to_geodetic(xy[:, 0], xy[:, 1], 0.)
    f = features([[(0, 0), (1, 1)]], ["parking"], ids=["lot"])
    f.layer = "infrastructure"
    f.kind[:] = 3
    f.lonlat = np.c_[lo, la]
    f.coord_off[-1] = len(xy)
    f.attrs["surface"] = np.array([surface_name])
    return f


def aisle(fid="a", xy=((0, 50), (80, 50)), kind="paved"):
    return fid, roads.Spec(6., kind, True, "service", False), np.c_[xy, np.zeros(len(xy))], 0.


def spot_shape(row):
    a = np.radians(row[3])
    h = np.array([np.cos(a), np.sin(a)]) * parking.LOT_SPOT_D_M/2
    v = np.array([-np.sin(a), np.cos(a)]) * parking.LOT_SPOT_W_M/2
    q = np.array(row[:2])
    return Polygon([q-h-v, q+h-v, q+h+v, q-h+v])


class LayoutTest(unittest.TestCase):
    def test_crossing_aisles_and_rows_never_overlap(self):
        data = [aisle(), aisle("b", ((40, 10), (40, 90))), aisle("c", ((0, 63), (80, 63)))]
        rows = parking.aisle_spots(data, {"a", "b", "c"}, (-10, -10, 100, 100))
        self.assertGreater(len(rows), 20)
        polygons = [spot_shape(r).buffer(-.04) for r in rows]
        for i, p in enumerate(polygons):
            self.assertFalse(any(p.intersects(q) for q in polygons[i+1:]))
        for fid, spec, line, _ in data:
            corridor = LineString(line[:, :2]).buffer(spec.width/2-.04, cap_style=2)
            self.assertFalse(any(p.intersects(corridor) for p in polygons))
        self.assertEqual(rows, parking.aisle_spots(data[::-1], {"a", "b", "c"}, (-10, -10, 100, 100)))
        a = parking.aisle_spots(data, {"a", "b", "c"}, (-10, -10, 40, 100))
        b = parking.aisle_spots(data, {"a", "b", "c"}, (40, -10, 100, 100))
        self.assertEqual(sorted(a+b), sorted(rows))

    def test_curved_stalls_are_valid_and_disjoint(self):
        data = [aisle(xy=((0, 0), (30, 0), (32, 3), (32, 40)))]
        polygons = [p for *_, keep, footprints in parking._aisle_layout(data, {"a"})
                    for p, yes in zip(footprints, keep) if yes]
        self.assertTrue(polygons)
        self.assertTrue(all(p.is_valid for p in polygons))
        for i, p in enumerate(polygons):
            self.assertFalse(any(p.buffer(-.02).intersects(q.buffer(-.02)) for q in polygons[i+1:]))

    def test_duplicate_and_overlapping_mapped_lots_have_one_layout(self):
        a, b = np.asarray(box(0, 0, 60, 40).exterior.coords), np.asarray(box(25, 0, 80, 40).exterior.coords)
        rows = parking.lot_spots([a, b, a], (-10, -10, 100, 100), lambda x,y: x*0)
        self.assertEqual(rows, parking.lot_spots([b, a], (-10, -10, 100, 100), lambda x,y: x*0))
        polygons = [spot_shape(r).buffer(-.02) for r in rows]
        for i, p in enumerate(polygons):
            self.assertFalse(any(p.intersects(q) for q in polygons[i+1:]))

    def test_obstacle_that_only_hits_stall_edge_blocks_the_whole_bay(self):
        data = [aisle()]
        rows = parking.aisle_spots(data, {"a"}, (0, 0, 100, 100))
        p = spot_shape(rows[0])
        obstacle = box(p.bounds[0]-.2, p.bounds[1]+1, p.bounds[0]+.25, p.bounds[3]-1)
        rings = [np.asarray(obstacle.exterior.coords)]
        kept = parking.aisle_spots(data, {"a"}, (0, 0, 100, 100), blockers=rings)
        self.assertNotIn(rows[0], kept)
        marks = parking.aisle_markings(data, {"a"}, (0, 0, 100, 100))
        clean = parking.drop_covered(marks, rings)
        self.assertTrue(clean)
        self.assertTrue(all(not LineString(np.asarray(ch['n'])[:, :2]).intersects(obstacle) for ch in clean))
        self.assertTrue(all('_parking_footprint' not in ch for ch in clean))

    def test_unpaved_lot_removes_paved_aisle_paint(self):
        data = [aisle()]
        marks = parking.aisle_markings(data, {"a"}, (0, 0, 100, 100))
        for material in ('gravel', 'dirt', 'grass'):
            md = SimpleNamespace(cell=lambda *a, **kw: SimpleNamespace(layers={'infrastructure': lots(material)}))
            self.assertEqual(parking.finish_markings(FRAME, 0, 0, md, lambda a,b: a*0, marks=marks), [])
        self.assertEqual(parking.aisle_markings([aisle(kind='gravel')], {'a'}, (0,0,100,100)), [])

    def test_untagged_lot_adopts_its_aisle_surface_consistently(self):
        road = features([[(0,50),(80,50)]], ['service'], surfaces=[(0,'gravel')], widths=[(0,6.)])
        road.rules['subclass'] = rules([(0,'parking_aisle')])
        original = lots()
        resolved = parking.resolved_lots([original], [road])[0]
        self.assertEqual(resolved.attrs['surface'][0], 'gravel')
        self.assertEqual(original.attrs['surface'][0], '', 'shared source features stay immutable')
        self.assertFalse(surface._parking(resolved)[0])
        explicit = parking.resolved_lots([lots('asphalt')], [road])[0]
        self.assertTrue(surface._parking(explicit)[0])
        md = SimpleNamespace(cell=lambda *a, **kw: SimpleNamespace(layers={'infrastructure':original,'roads':road}))
        self.assertEqual(parking.finish_markings(FRAME,0,0,md,lambda a,b:a*0), [])

    def test_mapped_rows_leave_mapped_driving_aisles_clear(self):
        road = features([[(0,50),(80,50)]], ['service'], widths=[(0,6.)])
        road.rules['subclass'] = rules([(0,'parking_aisle')])
        md = SimpleNamespace(cell=lambda *a, **kw: SimpleNamespace(layers={'infrastructure': lots(), 'roads': road}))
        marks = parking.finish_markings(FRAME, 0, 0, md, lambda a,b: a*0)
        self.assertTrue(marks)
        _, corridors = parking._lot_context(FRAME, 0, 0, md)
        for ch in marks:
            self.assertFalse(any(LineString(np.asarray(ch['n'])[:, :2]).intersects(Polygon(r)) for r in corridors))


class SurfaceTest(unittest.TestCase):
    def service(self, material=''):
        f = features([[(0,50),(80,50)]], ['service'], widths=[(0,6.)])
        f.rules['subclass'] = rules([(0,'parking_aisle')])
        return SimpleNamespace(roads=lambda *a:([f],True), urban=lambda a,b: np.zeros(np.shape(a),bool),
                               lots=lambda *a:[lots(material)], fuel_pads=lambda *a:[], gas_pads=False), f

    def test_aisle_bays_get_photo_and_mask_asphalt(self):
        service, f = self.service()
        service.lots = lambda *a: []
        rgb = np.full((200,200,3), (35,100,20), np.uint8)
        out = surface.paint_square(rgb, FRAME, 0,0,100,service)
        mask = surface.road_mask(FRAME,0,0,100,200,service)
        # y=57.5 is in a bay, beyond the 3m aisle half width.
        self.assertTrue(np.array_equal(out[85,80], np.array(surface.PHOTO_ROAD_RGBA['paved'][:3],np.uint8)))
        self.assertEqual(mask[85,80],255)
        self.assertTrue(np.array_equal(out[60,80],rgb[60,80]))

    def test_explicit_unpaved_surface_wins_everywhere_in_lot(self):
        for name, mat in (('gravel',surface.LOOSE),('dirt',surface.DIRT)):
            service, f = self.service(name)
            rgb = np.full((200,200,3), (35,100,20), np.uint8)
            out = surface.paint_square(rgb,FRAME,0,0,100,service)
            mask = surface.road_mask(FRAME,0,0,100,200,service)
            self.assertTrue(np.array_equal(out[100,80],out[80,80]))
            self.assertEqual(mask[100,80],0)
            xx,yy = np.meshgrid(np.arange(100.),np.arange(100.))
            la,lo,_ = FRAME.enu_to_geodetic(xx,yy,0.)
            idx = surface.paint_roads(np.full(xx.shape,surface.GRASS,np.uint8),la,lo,[f],1.)
            idx = surface.paint_lots(idx,la,lo,[lots(name)])
            self.assertTrue(np.all(idx[30:70,5:75] == mat))

    def test_paved_fill_is_opaque_with_a_short_soft_edge(self):
        f = lots()
        rgb = np.full((400,400,3),(35,100,20),np.uint8)
        out = surface.photo_lots(rgb,FRAME,-10,0,100,[f])
        target = np.array(surface.PHOTO_ROAD_RGBA['paved'][:3],np.uint8)
        self.assertTrue(np.array_equal(out[200,160],target))
        self.assertTrue(np.array_equal(out[200,20],rgb[200,20]))
        edge = out[200,36:40]
        self.assertTrue(any(not np.array_equal(p,target) and not np.array_equal(p,rgb[200,0]) for p in edge))


class GradingTest(unittest.TestCase):
    @staticmethod
    def elevation(la,lo):
        x,y,_ = FRAME.geodetic_to_enu(la,lo,0.)
        return 10 + .03*x + .02*y + .22*np.sin(x/1.8)*np.cos(y/2.5)

    def test_small_bumps_reduce_slope_stays_and_falloff_is_local(self):
        p = parkinggrade.Patch(FRAME,box(0,0,60,40),self.elevation)
        xx,yy = np.meshgrid(np.arange(-10,71.),np.arange(-10,51.))
        la,lo,_ = FRAME.enu_to_geodetic(xx.ravel(),yy.ravel(),0.)
        raw = self.elevation(la,lo)
        idx,delta,w = p.corrections(la,lo)
        out = raw.copy();out[idx] += delta*w
        inside = (xx.ravel()>5)&(xx.ravel()<55)&(yy.ravel()>5)&(yy.ravel()<35)
        plane = 10+.03*xx.ravel()+.02*yy.ravel()
        self.assertLess(np.std((out-plane)[inside]),np.std((raw-plane)[inside])*.65)
        self.assertLessEqual(np.max(np.abs(out-raw)),parkinggrade.MAX_CHANGE_M)
        far = (xx.ravel() < -4.01)|(xx.ravel()>64.01)|(yy.ravel() < -4.01)|(yy.ravel()>44.01)
        np.testing.assert_array_equal(out[far],raw[far])
        # A planar slope must remain planar.
        def ramp(a,b):
            x,y,_=FRAME.geodetic_to_enu(a,b,0.)
            return 10+.03*x+.02*y
        planar = parkinggrade.Patch(FRAME,box(0,0,60,40),ramp)
        _,d,_=planar.corrections(la,lo)
        self.assertLess(np.max(np.abs(d)),1e-7)
        # Sampling neighbouring tiles gives exactly the same correction.
        split=[]
        for part in (slice(0,1500),slice(1500,None)):
            ix,d,w=p.corrections(la[part],lo[part]);v=np.zeros(len(la[part]));v[ix]=d*w;split.extend(v)
        np.testing.assert_allclose(out-raw,split,atol=1e-14)

    def test_runtime_grader_reads_parking_and_is_anchor_independent(self):
        md = SimpleNamespace(cell=lambda *a,**kw: SimpleNamespace(layers={'infrastructure':lots()}))
        x=np.linspace(10,70,100);y=np.full(100,55.)
        la,lo,_=FRAME.enu_to_geodetic(x,y,0.)
        pg=parkinggrade.ParkingGrader(md,self.elevation)
        raw=self.elevation(la,lo)
        out=pg.apply(la,lo,raw)
        self.assertGreater(np.max(np.abs(out-raw)),.01)
        np.testing.assert_array_equal(out,pg.apply(la,lo,raw))
        np.testing.assert_allclose(out,np.r_[pg.apply(la[:50],lo[:50],raw[:50]),pg.apply(la[50:],lo[50:],raw[50:])])
        g=grading.Grader(FRAME,md,self.elevation)
        fake=SimpleNamespace(apply=lambda la,lo,base,*a:base)
        with patch.object(g.store,'planners_of',return_value=[(fake,None)]):
            np.testing.assert_allclose(g.apply(la,lo,raw),out)

    def test_overlapping_footprints_do_not_double_the_correction(self):
        f=lots(); md=SimpleNamespace(cell=lambda *a,**kw:SimpleNamespace(layers={'infrastructure':f}))
        pg=parkinggrade.ParkingGrader(md,self.elevation)
        la,lo,_=FRAME.enu_to_geodetic(np.linspace(10,70,100),np.full(100,55.),0.)
        raw=self.elevation(la,lo)
        out=pg.apply(la,lo,raw)
        self.assertLessEqual(np.max(np.abs(out-raw)),parkinggrade.MAX_CHANGE_M)


class HardscapeGradingTest(unittest.TestCase):
    elevation = staticmethod(GradingTest.elevation)

    def grader(self, road=None, widths=None):
        layers = {'infrastructure': lots(ring=[(-80,-80),(140,-80),(140,100),(-80,100),(-80,-80)]),
                  'roads': road}
        return parkinggrade.ParkingGrader(SimpleNamespace(cell=lambda *a, **kw: SimpleNamespace(layers=layers)),
                                         self.elevation, widths)

    def heights(self, pg, xy):
        xy = np.asarray(xy)
        la,lo,_ = FRAME.enu_to_geodetic(xy[:,0],xy[:,1],0.)
        raw = self.elevation(la,lo)
        return raw, pg.apply(la,lo,raw)

    def test_cut_and_fill_vanish_on_sidewalk_and_terrain_support_vertices(self):
        road = features([[(-100,0),(160,0)]], ['residential'], widths=[(0,8.)])
        pg = self.grader(road)
        xx,yy = np.meshgrid(np.arange(-40.,101.),np.arange(-12.,13.))
        xy = np.c_[xx.ravel(),yy.ravel()]
        raw,out = self.heights(pg,xy)
        # Includes carriageway, both raised walks, their back skins and the
        # neighbouring 2 m lattice vertices that interpolate under those skins.
        np.testing.assert_array_equal(out,raw)
        bare = self.grader()
        _,changed = self.heights(bare,xy)
        self.assertGreater(np.max(changed-raw),.01)
        self.assertLess(np.min(changed-raw),-.01)
        raw,out = self.heights(pg,np.c_[np.arange(-40.,101.),np.full(141,50.)])
        self.assertGreater(np.max(np.abs(out-raw)),.01,'clear lot interiors still smooth')

    def test_bent_wide_walks_all_regional_profiles_and_one_sided_tags(self):
        line = np.array([[-50.,0.,0.],[0.,0.,0.],[0.,50.,0.]])
        road = features([line[:,:2]], ['residential'])
        road.attrs['osm_sidewalk'] = np.array(['left'])
        widths = lambda *a: (14.,4.5)
        pg = self.grader(road,widths)
        spec = roads.road_specs(road,None,widths)[0]._replace(urban=True)
        samples=[]
        for look,w,pts in roads.extras(spec,line,0.):
            if look['m'] != roads.SIDEWALK['m']:
                continue
            curb,outward = sidewalks.run_geometry(pts,look['side'],w)
            for style in streetscape.STYLES.values():
                profile = sidewalks.profile(h=style.height,w=w)
                samples.extend((curb[:,:2,None]+outward[:,:,None]*profile[:,0]).transpose(0,2,1).reshape(-1,2))
        self.assertTrue(samples)
        raw,out=self.heights(pg,samples)
        np.testing.assert_array_equal(out,raw)

    def test_fixed_protection_is_identical_for_batches_order_and_anchor(self):
        road=features([[(-100,0),(160,0)]],['residential'],widths=[(0,8.)])
        xy=np.c_[np.linspace(-40,100,301),np.linspace(-30,60,301)]
        raw,out=self.heights(self.grader(road),xy)
        chunked=np.concatenate([self.heights(self.grader(road),part)[1] for part in np.array_split(xy,7)])
        np.testing.assert_array_equal(out,chunked)
        _,reverse=self.heights(self.grader(road),xy[::-1])
        np.testing.assert_array_equal(out,reverse[::-1])
        la,lo,_=FRAME.enu_to_geodetic(xy[:,0],xy[:,1],0.)
        import geodesy
        g=grading.Grader(geodesy.EnuFrame(FRAME.lat0+.01,FRAME.lon0-.01),self.grader(road).md,self.elevation)
        fake=SimpleNamespace(apply=lambda la,lo,base,*a:base)
        with patch.object(g.store,'planners_of',return_value=[(fake,None)]):
            np.testing.assert_array_equal(out,g.apply(la,lo,raw))

    def test_final_road_grade_at_junction_and_crossing_is_unchanged(self):
        road=features([[(-100,0),(160,0)],[(0,-100),(0,120)]],
                      ['residential','residential'],widths=[(0,8.),(1,10.)])
        pg=self.grader(road)
        g=grading.Grader(FRAME,pg.md,self.elevation)
        xx,yy=np.meshgrid(np.arange(-12.,13.),np.arange(-12.,13.))
        la,lo,_=FRAME.enu_to_geodetic(xx.ravel(),yy.ravel(),0.)
        raw=self.elevation(la,lo)
        decorated=g.apply(la,lo,raw,grading.ROAD_LIFT)
        with patch.object(g.store.parking,'apply',side_effect=lambda la,lo,base,*a:base):
            original=g.apply(la,lo,raw,grading.ROAD_LIFT)
        np.testing.assert_array_equal(decorated,original)

    def test_coarse_collision_lattice_cannot_transfer_displacement_under_walk(self):
        road=features([[(-100,0),(160,0)]],['residential'],widths=[(0,8.)])
        # All vertices of an 8 m collision square straddling the rear sidewalk
        # remain identical, so either triangle's interpolation remains identical.
        xy=np.array([[16.,0.],[24.,0.],[16.,8.],[24.,8.]])
        raw,out=self.heights(self.grader(road),xy)
        np.testing.assert_array_equal(out,raw)

    def test_neighbouring_cell_roads_are_loaded_for_the_whole_patch(self):
        road=features([[(-100,0),(160,0)]],['residential'],widths=[(0,8.)])
        pg=self.grader()
        keys=[]
        def cell(key,**kw):
            keys.append(str(key))
            return SimpleNamespace(layers={'roads':road})
        pg.md=SimpleNamespace(cell=cell)
        shape=box(-40,-30,100,60)
        protected=pg._protected(FRAME,shape)
        self.assertFalse(protected.is_empty)
        self.assertGreater(len(keys),1,'protection crosses the nearby source cell boundaries')
        self.assertTrue(protected.covers(LineString([(-40,8),(100,8)])))

    def test_cached_footprints_still_obtain_road_protection(self):
        road=features([[(-100,0),(160,0)]],['residential'],widths=[(0,8.)])
        pg=self.grader(road)
        # _cell can restore just footprints.json, without populating road_features.
        saved=list(parkinggrade._sources(lots(ring=[(-40,-30),(100,-30),(100,60),(-40,60),(-40,-30)])))
        with patch.object(pg,'_cell',return_value=saved):
            raw,out=self.heights(pg,[(20.,5.),(30.,7.)])
        np.testing.assert_array_equal(out,raw)
        self.assertTrue(pg.road_features)

    def test_failed_or_incomplete_road_inventory_skips_smoothing_and_retries(self):
        for incomplete in (False,True):
            pg=self.grader()
            original=pg.md
            import revisit
            def cell(key,**kw):
                if kw.get('layers') == ('roads',):
                    if incomplete:
                        revisit.fault()
                        return SimpleNamespace(layers={})
                    raise OSError('road inventory unavailable')
                return original.cell(key,**kw)
            pg.md=SimpleNamespace(cell=cell)
            saved=list(parkinggrade._sources(original.cell(None).layers['infrastructure']))
            with patch.object(pg,'_cell',return_value=saved):
                raw,out=self.heights(pg,[(20.,5.),(30.,7.),(40.,50.)])
                np.testing.assert_array_equal(out,raw)
                self.assertFalse(pg.cache,'an incomplete protection mask must not be cached')
                pg.md=original
                raw,out=self.heights(pg,[(20.,5.),(30.,7.),(40.,50.)])
            self.assertGreater(np.max(np.abs(out-raw)),.01,'a later complete inventory retries')

    def test_protection_fades_smoothly_for_positive_and_negative_changes(self):
        protected=box(-20,-20,20,20)
        p=parkinggrade.Patch(FRAME,box(-50,-50,80,80),self.elevation,protected)
        xy=np.c_[np.array([19.,20.,21.,22.,23.,24.,25.]),np.full(7,5.)]
        la,lo,_=FRAME.enu_to_geodetic(xy[:,0],xy[:,1],0.)
        idx,change,weight=p.corrections(la,lo)
        np.testing.assert_array_equal(idx,np.arange(7))
        np.testing.assert_allclose(weight,[0,0,.15625,.5,.84375,1,1],atol=1e-8)
        self.assertTrue(np.isfinite(change).all())


if __name__ == '__main__':
    unittest.main()
