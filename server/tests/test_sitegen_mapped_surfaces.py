"""Cached physical painting coverage, source holes, frame and fail-closed caps."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from shapely.geometry import Point

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import geodesy
import mapgeom
from sitegen import mapped_surfaces


def features(frame,cls='parking',subtype='',surface='',hole=False):
    outer=np.array(((0,0),(20,0),(20,20),(0,20),(0,0)),float)
    rings=[outer]
    if hole:rings.append(np.array(((6,6),(14,6),(14,14),(6,14),(6,6)),float))
    def geographic(ring):
        la,lo,_=frame.enu_to_geodetic(ring[:,0],ring[:,1],np.zeros(len(ring)))
        return np.column_stack((lo,la))
    f=mapgeom.build('infrastructure',np.array(['fixture']),[(mapgeom.POLYGON,[[geographic(r) for r in rings]])])
    f.attrs.update({'class':np.array([cls]),'subtype':np.array([subtype]),'surface':np.array([surface])})
    return f


class MappedSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.frame=geodesy.EnuFrame(-43.5,172.6)
        self.bounds=(-10.,-10.,30.,30.)

    def collect(self,*tables,extra=None,bounds=None):
        calls=[]
        service=SimpleNamespace(lots=lambda la,lo:(calls.append((la,lo)) or list(tables)),extra_pads=extra,
                                fuel_pads=lambda *args:(_ for _ in ()).throw(AssertionError('must not re-export fuel')))
        result=mapped_surfaces.collect(self.frame,bounds or self.bounds,service)
        self.assertEqual(len(calls),1)
        return result

    def test_current_frame_parking_body_not_only_stall_markings_is_exported(self):
        result=self.collect(features(self.frame))
        self.assertEqual(len(result),1)
        kind,shape=result[0]
        self.assertEqual(kind,'parking')
        self.assertTrue(shape.covers(Point(10,10)))
        np.testing.assert_allclose(shape.bounds,(0,0,20,20),atol=.001)

    def test_painted_parking_and_plaza_holes_still_cover_paved_ground(self):
        parking=self.collect(features(self.frame,hole=True))[0][1]
        plaza=self.collect(features(self.frame,'plaza','pedestrian',hole=True))[0][1]
        self.assertTrue(parking.covers(Point(10,10)))
        self.assertEqual(len(parking.interiors),0)
        self.assertTrue(plaza.covers(Point(10,10)))
        self.assertEqual(len(plaza.interiors),0)

    def test_green_land_use_and_explicit_unpaved_parking_remain_available(self):
        for table in (features(self.frame,'garden'),features(self.frame,'grass'),
                      features(self.frame,surface='grass'),features(self.frame,surface='gravel')):
            self.assertEqual(self.collect(table),())

    def test_painted_substation_yard_is_protected(self):
        result=self.collect(features(self.frame,'substation'))
        self.assertEqual(result[0][0],'hardscape')
        self.assertTrue(result[0][1].covers(Point(10,10)))

    def test_current_runway_extra_pad_delegate_is_used_without_fuel_duplicate(self):
        table=features(self.frame)
        ring=table.parts(0)[0][0]
        calls=[]
        def extra(lat,lon):
            calls.append((lat.copy(),lon.copy()))
            return [(ring[:,1],ring[:,0])]
        result=self.collect(extra=extra)
        self.assertEqual(len(calls),1)
        self.assertEqual(result[0][0],'road')
        self.assertTrue(result[0][1].covers(Point(10,10)))

    def test_clip_tracks_actual_painted_coverage_and_source_arrays_are_unmodified(self):
        table=features(self.frame,'plaza','pedestrian',hole=True)
        original=table.lonlat.copy()
        result=self.collect(table,bounds=(4.,4.,16.,16.))
        shape=result[0][1]
        self.assertEqual(shape.bounds,(4.,4.,16.,16.))
        self.assertTrue(shape.covers(Point(10,10)))
        np.testing.assert_array_equal(table.lonlat,original)

    def test_empty_cached_results_or_absent_service_do_not_invent_pavement(self):
        self.assertEqual(self.collect(None),())
        self.assertEqual(mapped_surfaces.collect(self.frame,self.bounds,None),())

    def test_overflow_or_failed_relevant_source_returns_whole_bounds(self):
        with patch.object(mapped_surfaces,'MAX_POLYGONS',0):
            result=self.collect(features(self.frame))
        self.assertEqual(result[0][0],'hardscape')
        self.assertEqual(result[0][1].bounds,self.bounds)
        service=SimpleNamespace(lots=lambda *args:(_ for _ in ()).throw(OSError('cached file unavailable')))
        self.assertEqual(mapped_surfaces.collect(self.frame,self.bounds,service)[0][1].bounds,self.bounds)
        service=SimpleNamespace(lots=lambda *args:[],extra_pads=lambda *args:(_ for _ in ()).throw(RuntimeError('runway callback failed')))
        self.assertEqual(mapped_surfaces.collect(self.frame,self.bounds,service)[0][1].bounds,self.bounds)

    def test_oversized_iterator_stops_at_declared_budget(self):
        def source():
            for _ in range(mapped_surfaces.MAX_TABLES+1):yield None
            raise AssertionError('consumed after known overflow')
        service=SimpleNamespace(lots=lambda *args:source())
        result=mapped_surfaces.collect(self.frame,self.bounds,service)
        self.assertEqual(result[0][1].bounds,self.bounds)

    def test_rebased_frame_projects_same_source_into_new_content_coordinates(self):
        table=features(self.frame)
        shifted=geodesy.EnuFrame(-43.5001,172.6001)
        service=SimpleNamespace(lots=lambda *args:[table])
        first=mapped_surfaces.collect(self.frame,(-100,-100,100,100),service)[0][1]
        second=mapped_surfaces.collect(shifted,(-100,-100,100,100),service)[0][1]
        for original,moved in zip(first.exterior.coords,second.exterior.coords):
            la,lo,h=self.frame.enu_to_geodetic(original[0],original[1],0.)
            x,y,_=shifted.geodetic_to_enu(la,lo,0.)
            np.testing.assert_allclose(moved,(x,y),atol=.001)


if __name__=='__main__':unittest.main()
