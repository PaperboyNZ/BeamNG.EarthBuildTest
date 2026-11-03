"""Specialist diagnostics must not change legacy dispatch or claim geometry."""
from dataclasses import FrozenInstanceError
from itertools import product
import json
from pathlib import Path
import pickle
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import compiler
from buildgen.specialized import LegacyRules, legacy_route, select, selectable
from buildgen.topology import Footprint


def baseline(attrs, area):
    """Frozen pre-adapter expression, independent of compiler integration."""
    cls = str(attrs.get("class") or "").lower()
    name = str(attrs.get("name") or "").lower()
    return bool(attrs.get("ship") or attrs.get("pier") or attrs.get("bridge_part") or attrs.get("bridge_masonry")
                or cls in b.BRIDGE_CLASSES or cls in b.CHURCH_CLASSES
                or any(w in name for w in ("church", "chapel", "cathedral", "terminal", "concourse"))
                or (cls in ("parking", "parking_garage") and area >= b.GARAGE_MIN_M2)
                or "parking garage" in name or ("garage" in name and area > 800)
                or (attrs.get("garage") and cls in b.GARAGE_TAG_CLASSES)
                or (attrs.get("roof_shape") == "pyramidal" and area >= b.PYRAMID_MIN_M2))


RULES = LegacyRules.from_buildings()


class SpecializedTest(unittest.TestCase):
    def test_exact_legacy_dispatch_matrix(self):
        classes = (None, "", "church", "CHAPEL", " church ", "cathedral", "parking", "parking_garage",
                   "bridge_structure", "apartments", "retail", "industrial", "terminal", "religious")
        names = (None, "", "Terminal Hotel", "Concourse Coffee", "Church Street Shop", "cathedral crafts",
                 "CHAPEL VIEW", "parking garage", "Garage", "ordinary office")
        areas = (0., 399.99, 400., 499.99, 500., 800., 800.01, float("nan"), float("inf"))
        for cls, name, area in product(classes, names, areas):
            attrs = {"class": cls, "name": name}
            expected = baseline(attrs, area)
            with self.subTest(attrs=attrs, area=area):
                self.assertIs(legacy_route(attrs, area, rules=RULES), expected)
                self.assertIs(select(attrs, area, rules=RULES).legacy_route, expected)
                self.assertIs(compiler.specialised(attrs, area), expected)

    def test_legacy_flag_roof_and_garage_boundaries(self):
        for key in ("ship", "pier", "bridge_part", "bridge_masonry", "garage"):
            for value in (None, False, True, "no", {}, {"source": "mapped"}):
                for cls in ("", "apartments", "industrial", "garage"):
                    attrs = {key: value, "class": cls}
                    self.assertIs(legacy_route(attrs, 800., rules=RULES), baseline(attrs, 800.))
                    self.assertIs(select(attrs, 800., rules=RULES).legacy_route, baseline(attrs, 800.))
        for roof in (None, "pyramidal", "Pyramidal", " pyramidal "):
            for area in (499.99, 500., float("nan")):
                attrs = {"roof_shape": roof}
                self.assertIs(legacy_route(attrs, area, rules=RULES), baseline(attrs, area))
        self.assertFalse(legacy_route({"name": "garage"}, 800.))
        self.assertTrue(legacy_route({"name": "garage"}, 800.01))

    def test_short_circuit_and_first_match_reasons(self):
        attrs = {"ship": {"mapped": True}, "class": "parking", "name": "Terminal"}
        # The old selector never compares this area after the ship match.
        self.assertTrue(baseline(attrs, object()))
        self.assertTrue(legacy_route(attrs, object(), rules=RULES))
        self.assertEqual(select(attrs, object(), rules=RULES).legacy_reasons, ("legacy_flag:ship",))
        self.assertFalse(legacy_route({}, object(), rules=RULES))
        for operation in (baseline, legacy_route, select):
            with self.assertRaises(TypeError):
                operation({"class": "parking"}, None)

    def test_lightweight_route_does_not_build_diagnostics(self):
        with mock.patch("buildgen.specialized._observations", side_effect=AssertionError("diagnostic allocation")), \
             mock.patch.object(LegacyRules, "from_buildings", side_effect=AssertionError("rule allocation")):
            self.assertTrue(legacy_route({"class": "church"}, 100.))
        with mock.patch.object(b, "GARAGE_MIN_M2", 900.):
            self.assertFalse(legacy_route({"class": "parking"}, 500.))
            self.assertTrue(legacy_route({"class": "parking"}, 500., rules=RULES))

    def test_keyword_false_positives_keep_legacy_route_only(self):
        for attrs in ({"class": "hotel", "name": "Terminal Hotel"},
                      {"class": "retail", "name": "Concourse Coffee"},
                      {"class": "retail", "name": "Church Street Shop"},
                      {"class": "hotel", "name": "Chapel View Hotel"}):
            result = select(attrs, 100.)
            self.assertTrue(result.legacy_route)
            self.assertTrue(result.ambiguous)
            self.assertEqual(result.architectural_fabric, "unknown")
            self.assertEqual(result.facility_use, "hotel" if attrs["class"] == "hotel" else "retail")
            self.assertIn("name_keyword_does_not_confirm_specialist", result.reasons)
            self.assertIsNone(result.family)
            self.assertIsNone(result.vocabulary)

    def test_converted_church_retains_fabric_without_active_worship_claim(self):
        result = select({"class": "church", "use": "residential", "name": "Converted Chapel"}, 180.)
        self.assertTrue(result.legacy_route)
        self.assertEqual((result.facility_use, result.architectural_fabric), ("residential", "church"))
        self.assertIn("church_fabric_with_different_current_use", result.reasons)
        result = select({"class": "retail", "building": "church"}, 180.)
        self.assertFalse(result.legacy_route)
        self.assertEqual((result.facility_use, result.architectural_fabric), ("retail", "church"))
        result = select({"building": "church"}, 180.)
        self.assertEqual((result.facility_use, result.architectural_fabric), ("unknown", "church"))

    def test_generic_religious_does_not_confirm_church(self):
        for attrs in ({"class": "religious"}, {"amenity": "place_of_worship", "religion": "christian"},
                      {"class": "mosque"}, {"class": "synagogue"}):
            result = select(attrs, 200.)
            self.assertEqual(result.facility_use, "religious")
            self.assertEqual(result.architectural_fabric, "unknown")
            self.assertFalse(result.legacy_route)
            self.assertIn("generic_religious_is_not_confirmed_church", result.reasons)
        result = select({"class": "chapel", "subtype": "religious"}, 200.)
        self.assertEqual((result.facility_use, result.confidence), ("church", "observed"))

    def test_passenger_freight_and_unknown_terminals_are_separate(self):
        attrs = {"class": "terminal", "name": "Terminal"}
        result = select(attrs, 1500.)
        self.assertEqual((result.facility_use, result.transport_mode), ("terminal_unknown", "unknown"))
        self.assertTrue(result.ambiguous)
        self.assertIn("passenger_or_freight_unknown", result.reasons)
        passenger = select(dict(attrs, terminal_use="passenger"), 1500.)
        freight = select(dict(attrs, terminal_use="freight"), 1500.)
        self.assertEqual((passenger.facility_use, passenger.transport_mode), ("passenger_terminal", "unknown"))
        self.assertEqual((freight.facility_use, freight.owner), ("freight_terminal", "commercial_industrial"))
        self.assertTrue(passenger.legacy_route)
        self.assertTrue(freight.legacy_route)
        # Class-only classifications are diagnostic, never new legacy positives.
        self.assertFalse(select({"class": "freight_terminal"}, 1500.).legacy_route)
        named = select({"name": "Freight Terminal"}, 1500.)
        self.assertEqual(named.facility_use, "unknown")
        self.assertEqual(named.owner, "buildgen")

    def test_modes_require_direct_mode_evidence(self):
        for mode in ("air", "bus", "ferry", "rail"):
            result = select({"class": "passenger_terminal", "transport_mode": mode}, 1000.)
            self.assertEqual((result.facility_use, result.transport_mode), ("passenger_terminal", mode))
        airport = select({"aeroway": "terminal"}, 1000.)
        self.assertEqual((airport.facility_use, airport.transport_mode), ("terminal_unknown", "air"))
        for attrs, mode in (({"amenity": "bus_station"}, "bus"), ({"amenity": "ferry_terminal"}, "ferry"),
                            ({"railway": "station"}, "rail")):
            result = select(attrs, 1000.)
            self.assertEqual((result.facility_use, result.transport_mode), ("passenger_terminal", mode))
        nearby = select({"name": "Terminal", "country": "NZ", "nearby_airport": True, "brand": "Air New Zealand"}, 1000.)
        self.assertEqual((nearby.facility_use, nearby.transport_mode), ("unknown", "unknown"))
        self.assertEqual(select({"transport_mode": "bus"}, 100.).facility_use, "unknown")

    def test_conflicting_evidence_stays_diagnosed(self):
        result = select({"class": "passenger_terminal", "terminal_use": "freight", "aeroway": "terminal",
                         "transport_mode": "bus"}, 1000.)
        self.assertEqual((result.facility_use, result.transport_mode, result.confidence),
                         ("terminal_unknown", "unknown", "conflict"))
        self.assertIn("conflicting_current_use", result.reasons)
        self.assertIn("conflicting_transport_mode", result.reasons)
        self.assertFalse(result.capability.geometry_accepted)
        self.assertNotEqual(result.owner, "commercial_industrial")

    def test_unsupported_topology_is_reported_without_accepting_fallback(self):
        fp = Footprint(((0, 0), (20, 0), (20, 20), (0, 20)),
                       (((5, 5), (15, 5), (15, 15), (5, 15)),))
        result = select({"class": "church", "_footprint": fp, "min_height": 4., "parent_id": "P1",
                         "roof_shape": "dome"}, fp.area)
        self.assertEqual(result.capability.required_features,
                         ("source_voids", "elevated_volume", "mapped_part_relationship", "special_roof"))
        self.assertEqual(result.capability.unsupported_features, result.capability.required_features)
        self.assertTrue(result.legacy_route)
        self.assertEqual(result.capability.fallback, "legacy_compatibility")
        self.assertFalse(result.capability.geometry_accepted)
        self.assertFalse(result.capability.fallback_topology_verified)
        self.assertEqual(select({"_footprint": fp}, fp.area).capability.fallback, "existing_route")
        # Source topology survives a clipped planning fragment.
        fragment = Footprint(((0, 0), (2, 0), (2, 2), (0, 2)))
        self.assertIn("source_voids", select({"_footprint": fragment, "_planning_footprint": fp}, 4.).capability.required_features)

    def test_fuel_ownership_stays_with_gasstations(self):
        for attrs in ({"amenity": "fuel"}, {"class": "gas_station"}, {"class": "fueling_station"}):
            result = select(attrs, 500.)
            self.assertEqual((result.facility_use, result.owner), ("fuel_station", "gasstations"))
            self.assertFalse(result.legacy_route)
            self.assertFalse(result.capability.geometry_accepted)
        result = select({"class": "retail", "name": "Shell", "brand": "Shell"}, 100.)
        self.assertEqual((result.facility_use, result.owner), ("retail", "buildgen"))

    def test_output_is_finite_detached_immutable_and_pickleable(self):
        attrs = {"class": "church", "height": float("nan"), "min_height": float("inf"),
                 "src_record": ["not a supported scalar"], "name": float("nan")}
        result = select(attrs, float("nan"))
        encoded = result.to_json()
        json.loads(encoded, parse_constant=lambda value: self.fail("nonfinite JSON: " + value))
        with self.assertRaises(FrozenInstanceError):
            result.facility_use = "retail"
        with self.assertRaises(FrozenInstanceError):
            result.capability.geometry_accepted = True
        self.assertEqual(pickle.loads(pickle.dumps(result)), result)
        attrs["class"] = "retail"
        attrs["src_record"].append("mutated")
        self.assertEqual(result.to_json(), encoded)
        detached = result.to_dict()
        detached["capability"]["adapter"] = "mutated"
        self.assertEqual(result.to_json(), encoded)
        self.assertTrue(all(o.status == "invalid" for o in result.observations if o.field in ("min_height", "name")))

    def test_determinism_and_explicit_rule_injection(self):
        attrs = {"class": "church", "use": "retail", "subtype": "passenger_terminal", "terminal_use": "freight",
                 "src_dataset": "fixture", "src_record": "B1", "transport_mode": "bus", "aeroway": "terminal"}
        self.assertEqual(select(attrs, 900.).to_json(), select(dict(reversed(tuple(attrs.items()))), 900.).to_json())
        self.assertEqual(selectable(attrs, 900.), select(attrs, 900.))
        rules = LegacyRules(set(), {"custom"}, set(), 1000., 2000.)
        with mock.patch.object(LegacyRules, "from_buildings", side_effect=AssertionError("unexpected lazy import")):
            self.assertTrue(legacy_route({"class": "custom"}, 1., rules=rules))
            self.assertTrue(select({"class": "custom"}, 1., rules=rules).legacy_route)
        self.assertIsInstance(rules.church_classes, frozenset)


if __name__ == "__main__":
    unittest.main()
