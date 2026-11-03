"""Boolean feed observations survive caches/plans without invented false values."""
from pathlib import Path
import io,sys,unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import mapgeom as mg,overture,buildings as b
from buildgen import freeze_items
from buildgen.evidence import normalise_attributes,feature_attributes
from shapely.geometry import Polygon


class NullableFieldTests(unittest.TestCase):
    def features(self):
        wkb=Polygon(((0,0),(12,0),(12,9),(0,9))).wkb
        class Connection:
            def execute(self,sql):self.sql=sql;return self
            def fetchall(self):
                if 'ORDER BY fi' in self.sql:return [(str(i),wkb,6.,4.5,v,v) for i,v in enumerate((True,False,None))]
                return []
        spec=dict(cols='has_parts,is_underground',clip=False,bool=('has_parts','is_underground'))
        return object.__new__(overture.Reader)._run(Connection(),'test',[],'buildings',spec,(-1,-1,20,20),[])[0]

    def test_feed_cache_evidence_and_frozen_plan_round_trip(self):
        f=self.features();buffer=io.BytesIO();np.savez_compressed(buffer,**f.to_arrays(''))
        buffer.seek(0)
        with np.load(buffer,allow_pickle=False) as archive:f=mg.Features.from_arrays('buildings',dict(archive),'')
        np.testing.assert_array_equal(f.attrs['has_parts'],[True,False,False])
        np.testing.assert_array_equal(f.attrs['has_parts__known'],[True,True,False])
        from buildgen.topology import Footprint
        fp=Footprint(((0.,0.),(12.,0.),(12.,9.),(0.,9.)))
        for i,expected in enumerate((True,False,None)):
            attrs=feature_attributes(f,i);attrs.update(seed_id='boolean-'+str(i),_footprint=fp,height=6.,num_floors=2)
            evidence=normalise_attributes(attrs)
            self.assertIs(evidence.get('has_parts').value,expected)
            self.assertEqual(evidence.get('has_parts').status,'unknown' if expected is None else 'observed')
            spec=b.plan(np.asarray(fp.outer),attrs)
            self.assertEqual(freeze_items([(spec,0.,0.)])[0][0].evidence,evidence)

    def test_legacy_false_is_unknown_and_survives_mixed_cache_concatenation(self):
        f=self.features();old=self.features()
        del old.attrs['has_parts__known'];del old.attrs['is_underground__known']
        self.assertIs(feature_attributes(old,0)['has_parts'],True)
        unknown=normalise_attributes(feature_attributes(old,1)).get('has_parts')
        self.assertEqual(unknown.status,'unknown');self.assertIn('legacy cache',unknown.reason)
        f.ids=np.array(['3','4','5'])
        merged=mg.concat(old,f)
        self.assertIs(feature_attributes(merged,1)['has_parts'],None)
        self.assertIs(feature_attributes(merged,4)['has_parts'],False)

    def test_strings_and_integer_flags_are_not_boolean_evidence(self):
        for raw in ('false','true',0,1,{},float('inf')):
            self.assertEqual(normalise_attributes({'has_parts':raw}).get('has_parts').status,'invalid')


if __name__=='__main__':unittest.main()
