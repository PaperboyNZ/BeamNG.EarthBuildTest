"""Lean quality policies retain architectural plans and isolate physical caches."""
import unittest
from unittest.mock import patch
from test_buildgen_quality import tier
from test_buildgen_regions import building
from buildgen import quality,products,sitework,automatic_sites,freeze_items,regional_architecture
import geotiles

class LeanTests(unittest.TestCase):
    def test_physical_products_isolate_essential_paths_and_complete_sites(self):
        tile=geotiles.geobox(100,100)
        keys={}
        for name in quality.NAMES:
            with tier(name):keys[name]=products.address(tile,'identical-inputs')[0]
        self.assertEqual(len({keys[n] for n in ('minimum','very_low','low','medium')}),4)
        self.assertEqual(len({keys[n] for n in ('medium','high','very_high','ultra')}),1)

    def test_all_regions_keep_source_envelope_under_bounded_low_planning(self):
        for theme in regional_architecture.catalogue():
            with tier('ultra'):a=freeze_items([(building(theme),0.,0.)])[0][0]
            with tier('very_low'):z=freeze_items([(building(theme),0.,0.)])[0][0]
            # New low planning intentionally omits inferred roof variants and
            # rebuilds apertures for that body. Observed source and mapped top
            # remain fixed. Downgrading an accepted plan is tested separately.
            for key in ('seed','floors','footprint','evidence'):
                self.assertEqual(getattr(a,key),getattr(z,key),(theme,key))
            self.assertAlmostEqual(a.height+a.inference.roof_rise, z.height+z.inference.roof_rise)

    def test_full_site_planning_is_not_entered_at_low_levels(self):
        for name in ('very_low','low'):
            with tier(name),patch.object(automatic_sites,'_resolve_staged',side_effect=AssertionError('full site solve')):
                self.assertEqual(automatic_sites.resolve([(building('nz_temperate'),0.,0.)],[],0.,0.,ground=None),[])

    def test_essential_policy_skips_only_inferred_front_path_candidates(self):
        spec=building('nz_temperate')
        with tier('very_low'):
            self.assertIsNone(sitework.candidate(spec,(0.,-10.)))

if __name__=='__main__':unittest.main()
