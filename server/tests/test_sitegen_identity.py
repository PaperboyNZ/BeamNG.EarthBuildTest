"""Site identity follows complete source geography, never tile residency."""
from dataclasses import FrozenInstanceError
import itertools
import json
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sitegen.identity import (ANGLE_SCALE, MAX_EXTENT_POINTS, CanonicalFrame,
                              GeographicFrame, SourceIdentity, SourceRevision,
                              canonical_json, normalize_longitude, rebase_enu, semantic_id)


class IdentityTests(unittest.TestCase):
    def test_revision_changes_dependency_but_not_semantic_identity(self):
        owner = SourceIdentity("overture:buildings", "stable-record")
        before, after = SourceRevision(owner, "2026-10-21"), SourceRevision(owner, "2026-11-01")
        self.assertNotEqual(before.dependency_key, after.dependency_key)
        self.assertEqual(semantic_id("site", before.identity), semantic_id("site", after.identity))
        self.assertNotEqual(semantic_id("site", owner), semantic_id("building", owner))
        self.assertNotEqual(semantic_id("resource", owner, "deck:1"), semantic_id("resource", owner, "deck:2"))
        self.assertNotEqual(semantic_id("site", owner), semantic_id("site", SourceIdentity("osm", "stable-record")))

    def test_identifiers_are_frozen_and_serialization_is_detached_json(self):
        source = SourceIdentity("local:survey", "id:with:separators/雪")
        revision = SourceRevision(source, "sha256:abc")
        encoded = canonical_json(revision.to_dict())
        restored = SourceRevision.from_dict(json.loads(encoded))
        self.assertEqual(restored, revision)
        with self.assertRaises(FrozenInstanceError):
            source.feature_id = "changed"
        detached = revision.to_dict()
        detached["identity"]["feature_id"] = "changed"
        self.assertEqual(source.feature_id, "id:with:separators/雪")
        self.assertEqual(encoded, canonical_json(json.loads(encoded)))
        with self.assertRaises(ValueError):
            canonical_json({"nonfinite": math.nan})

    def test_ambiguous_concatenations_do_not_collide(self):
        a, b = SourceIdentity("a:b", "c"), SourceIdentity("a", "b:c")
        self.assertNotEqual(semantic_id("site", a), semantic_id("site", b))

    def test_identity_rejects_invalid_inputs_and_unexpected_fields(self):
        for namespace, feature_id in (("", "id"), (" name", "id"), ("a", "id\n"), ("a", 4), ("a" * 129, "b")):
            with self.subTest(namespace=namespace, feature_id=feature_id), self.assertRaises(ValueError):
                SourceIdentity(namespace, feature_id)
        with self.assertRaises(ValueError):
            SourceRevision(SourceIdentity("a", "b"), "")
        with self.assertRaises(ValueError):
            SourceIdentity.from_dict({"namespace": "a", "feature_id": "b", "tile_xy": [0, 0]})
        with self.assertRaises(ValueError):
            semantic_id("site", "tile:123")


class CanonicalFrameTests(unittest.TestCase):
    def test_rotation_winding_duplicates_holes_and_member_load_order(self):
        ring = [(174.75, -36.85), (174.751, -36.85), (174.751, -36.849), (174.75, -36.849)]
        hole = [(174.7502, -36.8498), (174.7504, -36.8498), (174.7503, -36.8496)]
        other_member = [(174.7498, -36.85), (174.7499, -36.8499)]
        expected = CanonicalFrame.from_geographic_extent(ring + hole + other_member)
        for reverse, rotation in itertools.product((False, True), range(len(ring))):
            rotated = ring[rotation:] + ring[:rotation]
            if reverse:
                rotated.reverse()
            for members in ((rotated + rotated[:1], hole, other_member), (other_member, hole[::-1], rotated)):
                got = CanonicalFrame.from_geographic_extent([p for member in members for p in member])
                self.assertEqual(got, expected)

    def test_dateline_and_wrapped_longitude_have_identical_anchor(self):
        points = [(179.9998, -17.), (-179.9998, -16.9998)]
        frame = CanonicalFrame.from_geographic_extent(points)
        self.assertEqual(frame.longitude_e7, -180 * ANGLE_SCALE)
        self.assertEqual(frame, CanonicalFrame.from_geographic_extent([(539.9998, -17.), (180.0002, -16.9998)]))
        self.assertEqual(CanonicalFrame.from_geographic_extent([(180., 0.)]),
                         CanonicalFrame.from_geographic_extent([(-180., 0.)]))
        self.assertEqual(normalize_longitude(540.), -180.)
        self.assertEqual(normalize_longitude(-540.), -180.)
        # Modulo on float degrees before quantization perturbs half-step ties.
        for longitude, expected in ((10.00000005, 100_000_000), (10.00000015, 100_000_002)):
            frames = [CanonicalFrame.from_geographic_extent([(lon, 0.)])
                      for lon in (longitude, longitude + 360, longitude - 360)]
            self.assertTrue(all(frame.longitude_e7 == expected for frame in frames))
        for longitudes, expected in (((2.5e-7, 360.00000025, -359.99999975), 2),
                                     ((-2.5e-7, -360.00000025, 359.99999975), -2),
                                     ((-10.00000005, -370.00000005, 349.99999995), -100_000_000)):
            frames = [CanonicalFrame.from_geographic_extent([(longitude, 0.)]) for longitude in longitudes]
            self.assertTrue(all(frame.longitude_e7 == expected for frame in frames))

    def test_anchor_quantization_does_not_snap_projected_geometry(self):
        frame = CanonicalFrame.from_geographic_extent([(10.000000041, 20.000000041)])
        self.assertEqual((frame.longitude_e7, frame.latitude_e7), (100_000_000, 200_000_000))
        x, y, _ = frame.geodetic_to_enu(10.000000041, 20.000000041)
        self.assertGreater(abs(x), .001)
        self.assertGreater(abs(y), .001)
        self.assertAlmostEqual(x, .00429, delta=.0001)

    def test_known_axes_and_three_dimensional_rebase(self):
        equator = GeographicFrame(0., 0.)
        self.assertEqual(equator.geodetic_to_enu(0., 0., 17.), (0., 0., 17.))
        target = CanonicalFrame.from_geographic_extent([(174.77, -36.85), (174.771, -36.849)])
        original = GeographicFrame(174.76, -36.86, 61.25)
        shifted = GeographicFrame(174.78, -36.84, 10.)
        geographic = (174.7701, -36.8493, 84.625)
        p = original.geodetic_to_enu(*geographic)
        q = shifted.geodetic_to_enu(*geographic)
        from_p = rebase_enu(p, original, target)
        from_q = rebase_enu(q, shifted, target)
        direct = target.geodetic_to_enu(*geographic)
        for a, b, c in zip(from_p, from_q, direct):
            self.assertAlmostEqual(a, b, delta=1e-7)
            self.assertAlmostEqual(a, c, delta=1e-7)
        for a, b in zip(target.enu_to_geodetic(*direct), geographic):
            self.assertAlmostEqual(a, b, delta=1e-7)

    def test_scalar_conversion_matches_existing_geodesy_convention(self):
        import geodesy
        for lon, lat, altitude in ((174.76, -36.86, 61.25), (179.999, 75., -30.), (23., 90., 12.)):
            ours, native = GeographicFrame(lon, lat, altitude), geodesy.EnuFrame(lat, lon, altitude)
            for point in ((lon, lat, altitude), (lon + .0001, min(lat + .0001, 90.), altitude + 25.)):
                actual = ours.geodetic_to_enu(*point)
                expected = native.geodetic_to_enu(point[1], point[0], point[2])
                for a, b in zip(actual, expected):
                    self.assertAlmostEqual(a, b, delta=1e-7)

    def test_poles_and_geographic_owner_boundaries(self):
        for lat in (-90., 90.):
            self.assertEqual(CanonicalFrame.from_geographic_extent([(17., lat)]),
                             CanonicalFrame.from_geographic_extent([(-130., lat)]))
            frame = CanonicalFrame.from_geographic_extent([(0., lat)])
            lon2, lat2, h2 = frame.enu_to_geodetic(*frame.geodetic_to_enu(0., lat, 12.5))
            self.assertEqual(lon2, 0.)
            self.assertEqual(lat2, lat)
            self.assertAlmostEqual(h2, 12.5, delta=1e-8)
        west = CanonicalFrame(-1, 0).owner_cell()
        edge = CanonicalFrame(0, 0).owner_cell()
        east = CanonicalFrame(1, 0).owner_cell()
        self.assertNotEqual(west, edge)
        self.assertEqual(edge, east)
        self.assertEqual(CanonicalFrame(0, 90 * ANGLE_SCALE).owner_cell(),
                         CanonicalFrame(0, 90 * ANGLE_SCALE - 1).owner_cell())
        with self.assertRaises(ValueError):
            CanonicalFrame(0, 0).owner_cell(7)

    def test_canonical_and_exact_source_frame_json_roundtrip(self):
        for frame in (CanonicalFrame(-180 * ANGLE_SCALE, 170_000_000), GeographicFrame(174.123456789, -36.7, 47.125)):
            restored = type(frame).from_dict(json.loads(canonical_json(frame.to_dict())))
            self.assertEqual(restored, frame)
            with self.assertRaises(FrozenInstanceError):
                restored.longitude = 5
            data = frame.to_dict()
            data["vertical_datum"] = "unknown_height"
            with self.assertRaises(ValueError):
                type(frame).from_dict(data)
        data = CanonicalFrame(0, 0).to_dict()
        data["height"] = False
        with self.assertRaises(ValueError):
            CanonicalFrame.from_dict(data)

    def test_extent_budget_and_geographic_limits(self):
        invalid = ([], [(0., 0., 0.)], [(math.inf, 0.)], [(0., math.nan)], [(541., 0.)],
                   [(0., 91.)], [(True, 0.)], [(0., 0.), (1.000001, 0.)],
                   [(0., 0.), (180., 0.)], [(0., 0.), (0., 1.000001)])
        for points in invalid:
            with self.subTest(points=points), self.assertRaises(ValueError):
                CanonicalFrame.from_geographic_extent(points)
        with self.assertRaises(ValueError):
            CanonicalFrame.from_geographic_extent(itertools.repeat((0., 0.), MAX_EXTENT_POINTS + 1))
        self.assertEqual(CanonicalFrame.from_geographic_extent([(0., 0.), (1., 1.)]), CanonicalFrame(5_000_000, 5_000_000))
        for args in ((True, 0), (180 * ANGLE_SCALE, 0), (0, 90 * ANGLE_SCALE + 1), (1, 90 * ANGLE_SCALE)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                CanonicalFrame(*args)
        with self.assertRaises(ValueError):
            GeographicFrame(0, 0).enu_to_geodetic(1_000_001, 0, 0)


if __name__ == "__main__":
    unittest.main()
