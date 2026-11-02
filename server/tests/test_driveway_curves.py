"""Curved rear seams and independently usable receiving areas."""
from pathlib import Path
import sys
import copy
import unittest
import numpy as np
from shapely.geometry import Polygon
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings
import sidewalks
from buildgen.topology import Footprint
from buildgen import driveways
from test_buildgen_driveways import walk
from test_buildgen_facades import building,road


class CurvedAccess(unittest.TestCase):
    def test_curved_sidewalk_has_supported_full_route_and_exact_rear_vertices(self):
        spec=building();xs=np.arange(-50.,51.,2.)
        wk=walk();wk['pts']=np.c_[xs,-7.75+.002*xs*xs,np.zeros(len(xs))]
        raw=copy.deepcopy([wk]);records=[]
        buildings.doors([(spec,0.,0.)],road(),0.,0.,records,ground=lambda p:np.zeros(len(p)),walks=[wk],raw_walks=raw)
        self.assertIn('driveway_connected',spec.access.diagnostics)
        panels=[s for s in spec.access.solids if s.kind=='driveway']
        self.assertGreater(len(panels),8)
        self.assertTrue(all(Polygon(np.asarray(s.top)[:,:2]).is_valid for s in panels))
        curb,out=sidewalks.run_geometry(wk['pts'],wk['side'],wk['w'])
        keep=sidewalks.simplify(curb,tol=1e-6);curb,out=curb[keep],out[keep]
        arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(curb[:,:2],axis=0),axis=1))]
        lo,hi=wk['driveways'][0];middle=(lo+hi)/2;mouth=(hi-lo)-.2
        stations=np.unique(np.r_[np.linspace(middle-mouth/2,middle+mouth/2,9),arc[(arc>middle-mouth/2)&(arc<middle+mouth/2)]])
        rear=np.c_[[np.interp(stations,arc,curb[:,i])+wk['w']*np.interp(stations,arc,out[:,i]) for i in (0,1)]].T
        vertices=np.array([p for s in panels for p in s.top])
        for p in rear:self.assertLess(np.linalg.norm(vertices[:,:2]-p,axis=1).min(),1e-7)
        self.assertEqual(wk['driveways'],raw[0]['driveways'])

    def test_blocked_internal_drive_can_keep_clear_receiving_area(self):
        spec=building(fp=Footprint(((0,10),(20,10),(20,20),(0,20))))
        obstacle=building(fp=Footprint(((-3,6),(23,6),(23,8),(-3,8))),**{'class':'utility'})
        obstacle.inference=None;obstacle.plain=True
        wk=walk();raw=copy.deepcopy([wk]);records=[]
        items=[(spec,0.,0.),(obstacle,0.,0.)]
        buildings.doors(items,road(),0,0,records,ground=lambda p:np.zeros(len(p)),walks=[wk],raw_walks=raw)
        self.assertIn('driveway_crossing_only',spec.access.diagnostics)
        self.assertNotIn('driveway_connected',spec.access.diagnostics)
        self.assertEqual(len(records),1);self.assertEqual(len(wk['driveways']),1)
        for s in spec.access.solids:
            if s.kind=='driveway':self.assertLess(Polygon(np.asarray(s.top)[:,:2]).intersection(obstacle.footprint.shape()).area,1e-7)

    def test_missing_receiving_ground_cannot_create_crossing(self):
        spec=building(fp=Footprint(((0,10),(20,10),(20,20),(0,20))))
        obstacle=building(fp=Footprint(((-3,6),(23,6),(23,8),(-3,8))),**{'class':'utility'})
        obstacle.inference=None;obstacle.plain=True;wk=walk();records=[]
        buildings.doors([(spec,0.,0.),(obstacle,0.,0.)],road(),0,0,records,
                        ground=lambda p:np.where(p[:,1]<0,np.nan,0.),walks=[wk])
        self.assertFalse(wk.get('driveways'));self.assertNotIn('driveway_crossing_only',spec.access.diagnostics)


if __name__=='__main__':unittest.main()
