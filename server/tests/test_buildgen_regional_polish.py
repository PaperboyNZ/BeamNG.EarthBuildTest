"""Visible join, source topology and LOD regressions from the personal audit."""
import math
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import regional_architecture as regional,facades,roofs,freeze_items
from buildgen.topology import Footprint
from test_buildgen_regions import building

class RegionalPolishTests(unittest.TestCase):
    def test_veranda_styles_do_not_paint_unsupported_posts_on_flat_walls(self):
        checked=0
        for key,p in regional.catalogue().items():
            if p['massing_grammar']!='timber_veranda':continue
            spec=building(key);layout=facades.plan(spec,0.,0.)
            components=[c for e in layout.elevations for c in regional.components(spec,e,p,200)]
            self.assertFalse(any(c.kind=='structural_pier' for c in components),key)
            self.assertTrue(any(c.kind=='deep_beam' for c in components),key)
            checked+=1
        self.assertGreater(checked,0)
        for key in ('alpine','jp_temperate','antarctic_stations'):
            spec=building(key);p=regional.profile(key)
            components=[c for e in facades.plan(spec,0.,0.).elevations for c in regional.components(spec,e,p,200)]
            self.assertFalse(any(c.kind=='structural_pier' for c in components),key)
            self.assertTrue(all(c.material=='wall_trim' for c in components if c.kind=='deep_beam'),key)

    def test_timber_corner_boards_fit_scale_material_and_openings(self):
        from dataclasses import replace
        p=regional.profile('nz_temperate')
        for length in (5.,12.,30.):
            fp=Footprint(((0.,0.),(length,0.),(length,9.),(0.,9.)))
            spec=building('nz_temperate',fp=fp,facade_material='wood')
            found=0
            for e in facades.plan(spec,0.,0.).elevations:
                boards=[c for c in regional.components(spec,e,p,200) if c.kind=='corner_board']
                for c in boards:
                    self.assertEqual(c.material,'trim')
                    self.assertTrue(c.left==0 or abs(c.right-e.length)<1e-8)
                    self.assertTrue(.089<=c.right-c.left<=.161)
                    self.assertAlmostEqual(c.bottom,.35);self.assertAlmostEqual(c.top,spec.height-.12)
                    found+=1
                if e.openings:
                    blocked=replace(e,openings=(replace(e.openings[0],left=0.,right=.5),))
                    self.assertFalse(any(c.kind=='corner_board' and c.left==0 for c in regional.components(spec,blocked,p,200)))
            self.assertGreater(found,0)
        for attrs in ({'facade_material':'brick'}, {'facade_material':'wood','height':20.,'num_floors':6}):
            spec=building('nz_temperate',**attrs)
            self.assertFalse(any(c.kind=='corner_board' for e in facades.plan(spec,0.,0.).elevations
                                 for c in regional.components(spec,e,p,200)))

    def test_regional_windows_leave_proportional_solid_wall(self):
        for key in regional.catalogue():
            with self.subTest(theme=key):
                spec=building(key);profile=regional.for_spec(spec)
                layout=facades.plan(spec,0.,0.)
                for e in layout.elevations:
                    for floor in range(int(spec.floors)):
                        openings=[o for o in e.openings if o.kind=='window' and o.floor==floor]
                        front=e.boundary==0 and e.edge==spec.front
                        structured=profile.get('residential_structure')
                        self.assertLessEqual(len(openings),4 if front and structured else 3 if front else 2)
                        from buildgen import residential
                        private=structured and residential.catalogue()['families'][structured].get('privacy')
                        if front and not private:
                            self.assertGreaterEqual(len(openings),2,
                                'The entrance facade should retain two windows per floor on this 12 m fixture')
                        if len(openings)>1:
                            area=sum((o.right-o.left)*(o.top-o.bottom) for o in openings)
                            self.assertLessEqual(area,e.length*spec.floor_h*regional.glazing_share(profile,front=front)+1e-8)

    def test_continuous_trim_has_shared_miter_vertices(self):
        for ring in (((0.,0.),(12.,0.),(12.,9.),(0.,9.)),((0.,0.),(12.,0.),(12.,5.),(6.,5.),(6.,9.),(0.,9.))):
            for angle in (0.,.47):
                c,s=math.cos(angle),math.sin(angle)
                rr=tuple((100+x*c-y*s,-300+x*s+y*c) for x,y in ring)
                for i in range(len(rr)):
                    prev=(i-1)%len(rr)
                    for depth in (0.,.012,.06,.12):
                        a=regional.band_point(rr,prev,math.dist(rr[prev],rr[i]),2.,depth,17.)
                        d=regional.band_point(rr,i,0.,2.,depth,17.)
                        np.testing.assert_allclose(a,d,atol=1e-10)

    def test_gable_cladding_continues_the_upper_storey(self):
        spec=building('alpine',seed='alpine-cladding',roof_shape='gabled')
        mats=b._Looks(spec.seed)
        _,expected=regional.wall_materials(spec,regional.for_spec(spec),mats,mats[spec.facade])
        m=b.Mesh();roofs.draw(m,spec,spec.height,mats)
        pos,uv,tri,mi,col=m.arrays();start=len(roofs.for_spec(spec).triangles)
        self.assertGreater(len(tri),start)
        self.assertTrue(np.all(mi[start:]==expected[0]))
        np.testing.assert_array_equal(col[np.unique(tri[start:])],np.tile(expected[1],(len(np.unique(tri[start:])),1)))

    def test_arches_stay_on_the_intended_front_storey(self):
        spec=building('italy_regional');p=regional.for_spec(spec)
        layout=facades.plan(spec,0.,0.)
        found=0
        for e in layout.elevations:
            for op in e.openings:
                shape=regional.aperture_shape(spec,p,e,op)
                if shape!='rectangular':
                    found+=1;self.assertEqual(e.edge,spec.front);self.assertEqual(op.floor,0)
        self.assertGreater(found,0)

    def test_all_themes_keep_polish_on_narrow_irregular_and_courtyard_footprints(self):
        cases=(Footprint(((0.,0.),(5.,0.),(5.,15.),(0.,15.))),
               Footprint(((0.,0.),(14.,0.),(14.,7.),(7.,7.),(7.,12.),(0.,12.))),
               Footprint(((0.,0.),(18.,0.),(18.,16.),(0.,16.)),(((5.,5.),(5.,11.),(13.,11.),(13.,5.)),)))
        for key in regional.catalogue():
            for i,fp in enumerate(cases):
                with self.subTest(theme=key,case=i):
                    spec=building(key,fp=fp,seed='polish-stress',height=11.,num_floors=3)
                    items=freeze_items([(spec,0.,0.)]);layout=items[0][0].facades
                    for mesh in (b.build(items),b.build(items,lite=True),b.collision_mesh(items)):
                        self.assertTrue(np.isfinite(mesh[0]).all() and np.isfinite(mesh[1]).all())
                        self.assertLess(mesh[2].max(),len(mesh[0]))
                    budget=regional.MAX_COMPONENTS
                    for e in layout.elevations:
                        components=regional.components(spec,e,regional.for_spec(spec),budget);budget-=len(components)
                        self.assertGreaterEqual(budget,0)
                        for component in components:
                            if component.kind=='structural_pier':
                                # No clipped orphan pieces above or below windows.
                                self.assertAlmostEqual(component.bottom,.35)
                                self.assertAlmostEqual(component.top,spec.height-.16)

if __name__=='__main__':unittest.main()
