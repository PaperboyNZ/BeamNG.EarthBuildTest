"""Finite vegetation footprints avoid observed hardscape and retain green space."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import mapgeom
import vegetation as veg
from test_vegetation import FakeMapData,KEY


def raster():
    return SimpleNamespace(x0=0.,y0=160.,dx=1.,dy=1.,data=np.zeros((160,160)))


def feature(layer,cls,outer,holes=(),surface='',subtype='',line=False,width=None):
    rings=[]
    for ring in (outer,*holes):
        x,y=np.asarray(ring,float).T
        lo,la=veg._to4326(x,y)
        rings.append(np.column_stack((lo,la)))
    f=mapgeom.build(layer,np.array(['fixture']),[(mapgeom.LINE if line else mapgeom.POLYGON,[rings])])
    f.attrs.update({'class':np.array([cls]),'subtype':np.array([subtype]),'surface':np.array([surface])})
    if width is not None:f.attrs['width']=np.array([width])
    return f


def items(points,groups=(veg.G_DECIDUOUS,veg.G_SHRUB,veg.G_ROCK),height=5.,scale=1.):
    x,y=np.asarray(points,float).T
    lo,la=veg._to4326(x,y)
    groups=np.resize(np.asarray(groups,np.uint8),len(x))
    h=np.full(len(x),height,np.float32)
    radius=np.where(np.isin(groups,(veg.G_ROCK,veg.G_DESERT_ROCK)),.6*h,
                    np.where(np.isin(groups,(veg.G_SHRUB,veg.G_DESERT_SHRUB)),np.maximum(.12*h+1,.6*h),.12*h+1))
    return veg.Items(lo,la,h,radius.astype(np.float32),np.where(groups==veg.G_ROCK,veg.KIND_ROCK,
                     np.where(groups==veg.G_SHRUB,veg.KIND_BUSH,veg.KIND_TREE)).astype(np.uint8),groups,
                     np.zeros(len(x),np.float32),np.zeros(len(x),np.float32),np.full(len(x),scale,np.float32))


class VegetationSurfaceTests(unittest.TestCase):
    def test_tree_bush_and_rock_all_blocked_on_mapped_parking_green_space_retained(self):
        chm=raster();mask=np.zeros(chm.data.shape,bool)
        f=feature('infrastructure','parking',((60,60),(100,60),(100,100),(60,100),(60,60)))
        veg._mask_paved(f,mask,chm)
        source=items(((80,80),(81,80),(82,80),(30,30),(31,30),(32,30)))
        kept=veg._clear_surface_footprints(source,mask,chm)
        self.assertEqual(len(kept),3)
        self.assertEqual(set(kept.kind),{veg.KIND_TREE,veg.KIND_BUSH,veg.KIND_ROCK})
        x,y=veg._to3857(kept.lon,kept.lat)
        self.assertTrue((x<40).all())

    def test_pedestrian_plaza_substation_and_observed_pavement_are_blocked(self):
        for layer,cls,sub,surface in (('land_use','plaza','pedestrian',''),
                                      ('land_use','unknown','pedestrian',''),
                                      ('infrastructure','substation','',''),
                                      ('infrastructure','unknown','','concrete')):
            chm=raster();mask=np.zeros(chm.data.shape,bool)
            veg._mask_paved(feature(layer,cls,((60,60),(100,60),(100,100),(60,100),(60,60)),
                                   subtype=sub,surface=surface),mask,chm,land_use=layer=='land_use')
            self.assertEqual(len(veg._clear_surface_footprints(items(((80,80),)),mask,chm)),0)

    def test_grass_garden_and_declared_unpaved_parking_are_not_blanket_hardscape(self):
        for layer,cls,sub,material in (('land_use','grass','','grass'),('land_use','garden','',''),
                                       ('infrastructure','parking','','grass')):
            chm=raster();mask=np.zeros(chm.data.shape,bool)
            veg._mask_paved(feature(layer,cls,((20,20),(140,20),(140,140),(20,140),(20,20)),
                                   subtype=sub,surface=material),mask,chm,land_use=layer=='land_use')
            self.assertFalse(mask.any())
            self.assertEqual(len(veg._clear_surface_footprints(items(((80,80),(82,80),(84,80))),mask,chm)),3)

    def test_road_shoulder_and_scaled_full_footprint_are_clear(self):
        chm=raster();mask=np.zeros(chm.data.shape,bool)
        road=feature('roads','residential',((80,10),(80,150)),line=True,width=10.)
        veg._mask_roads(road,mask,chm,clear=0.)
        source=items(((86,80),(92,80),(88,80)),groups=(veg.G_DECIDUOUS,veg.G_DECIDUOUS,veg.G_ROCK),height=2.,scale=3.)
        kept=veg._clear_surface_footprints(source,mask,chm,ground_only=False)
        x,y=veg._to3857(kept.lon,kept.lat)
        self.assertEqual(len(kept),1)
        self.assertAlmostEqual(x[0],92.,places=5)

    def test_footways_and_measured_widths_are_reserved(self):
        chm=raster();mask=np.zeros(chm.data.shape,bool)
        road=feature('roads','footway',((80,10),(80,150)),line=True,width=12.)
        veg._mask_roads(road,mask,chm,clear=0.)
        self.assertEqual(len(veg._clear_surface_footprints(items(((84,80),(95,80))),mask,chm)),1)

    def test_polygon_holes_allow_only_footprints_that_fit_fully(self):
        chm=raster();mask=np.zeros(chm.data.shape,bool)
        f=feature('infrastructure','parking',((20,20),(140,20),(140,140),(20,140),(20,20)),
                  holes=(((50,50),(110,50),(110,110),(50,110),(50,50)),))
        veg._mask_paved(f,mask,chm)
        kept=veg._clear_surface_footprints(items(((80,80),(51,80))),mask,chm)
        self.assertEqual(len(kept),1)
        self.assertAlmostEqual(veg._to3857(kept.lon,kept.lat)[0][0],80.,places=5)

    def test_subpixel_paving_and_after_jitter_positions_cannot_escape(self):
        chm=raster();mask=np.zeros(chm.data.shape,bool)
        f=feature('infrastructure','parking',((80.1,20),(80.2,20),(80.2,140),(80.1,140),(80.1,20)))
        veg._mask_paved(f,mask,chm)
        self.assertTrue(mask.any())
        kept=veg._clear_surface_footprints(items(((79.8,80),(90,80))),mask,chm)
        self.assertEqual(len(kept),1)

    def test_finite_radius_formula_matches_client_row8_contract(self):
        source=items(((40,40),(50,50),(60,60)),height=10.,scale=1.2)
        np.testing.assert_allclose(veg.footprint_radius(source),np.array((2.2,6.,6.))*1.2,rtol=1e-6)
        source.scale[0]=float('nan')
        self.assertEqual(len(veg._clear_surface_footprints(source,np.zeros((160,160),bool),raster())),2)

    def test_build_filters_canopy_trees_and_scatter_edge_after_paving_is_known(self):
        md=FakeMapData();lo,la=md.lonlat(100,100)
        x,y=veg._to3857(lo,la)
        raw=feature('infrastructure','parking',((x-20,y-20),(x+20,y-20),(x+20,y+20),(x-20,y+20),(x-20,y-20)))
        original=md.cell
        def cell(key,layers=None,kind='demand'):
            result=original(key,layers,kind)
            if tuple(key)[1:]==(KEY.x,KEY.y):
                result.layers['infrastructure']=raw
            return result
        md.cell=cell
        with patch.object(veg.Vegetation,'_specs',return_value=[None]):
            actual=veg.Vegetation(md,None).cell(KEY)
        px,py=veg._to3857(actual.lon,actual.lat)
        self.assertFalse(((abs(px-x)<20)&(abs(py-y)<20)).any())
        self.assertGreater(len(actual),0)
        self.assertEqual(veg.VERSION,22)


if __name__=='__main__':unittest.main()
