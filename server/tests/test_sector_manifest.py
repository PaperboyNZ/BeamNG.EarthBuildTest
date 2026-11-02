import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sector


class SectorManifestTests(unittest.TestCase):
    def data(self):
        return dict(key='g17_129218_80016', frame=[-36.9,174.9], physicalHash='a'*16,
                    bld=dict(shape='/one/visual.cdae',pos=[0,0,0]),
                    bldcol=dict(shape='/one/collision.cdae',pos=[0,0,0]),
                    buildingChunks=dict(v=1,visual=['bld'],collision=['bldcol']),
                    shapeHashes=dict(bld='b'*64,bldcol='c'*64))

    def test_visual_refinement_and_paths_do_not_change_physical_identity(self):
        data=self.data();a=sector.manifest(data)
        data['bld']['shape']='/another/slot_1.cdae';data['bldcol']['shape']='/another/slot_2.cdae'
        self.assertEqual(sector.manifest(data),a)
        data['shapeHashes']['bld']='d'*64;b=sector.manifest(data)
        self.assertEqual(a['physical'],b['physical'])
        self.assertNotEqual(a['visual']['revision'],b['visual']['revision'])
        self.assertEqual(a['producer'],b['producer'])
        data['physicalHash']='e'*16;c=sector.manifest(data)
        self.assertEqual(c['visual']['depends_on'],'e'*16)
        self.assertEqual(a['producer'],c['producer'])

    def test_incomplete_oversized_nonfinite_and_unknown_resources_rejected(self):
        for mutate in (lambda d:d['shapeHashes'].pop('bldcol'),
                       lambda d:d['shapeHashes'].update(extra='a'*64),
                       lambda d:d.update(frame=[float('nan'),1]),
                       lambda d:d.update(frame=[False,1]),
                       lambda d:d.update(key='g17_131072_0'),
                       lambda d:d.update(physicalHash='unversioned'),
                       lambda d:d['shapeHashes'].update(bld='bad')):
            with self.subTest(mutate=mutate):
                data=self.data();mutate(data)
                with self.assertRaises(ValueError):sector.manifest(data)
        data=self.data();data['shapeHashes']={str(i):'a'*64 for i in range(sector.MAX_PARTS+1)}
        with self.assertRaises(ValueError):sector.manifest(data)

    def test_manifest_is_deterministic_complete_and_capability_is_explicit(self):
        data=self.data();a=sector.manifest(data)
        data['shapeHashes']=dict(reversed(list(data['shapeHashes'].items())))
        self.assertEqual(a,sector.manifest(data))
        self.assertEqual(a['physical']['parts'],[dict(part='bldcol',sha256='c'*64)])
        self.assertEqual(a['visual']['parts'],[dict(part='bld',sha256='b'*64)])
        self.assertTrue(sector.negotiated(True,1))
        for value in (None,False,True,1.,2,'1'):
            self.assertFalse(sector.negotiated(True,value))
        self.assertFalse(sector.negotiated(False,1))
