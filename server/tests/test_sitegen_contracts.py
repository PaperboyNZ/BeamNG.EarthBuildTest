"""M1 immutable records, explicit legacy boundary and ownership invariants."""
from dataclasses import FrozenInstanceError, replace
import json
import os
from pathlib import Path
import pickle
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from buildgen import site_data
from buildgen.site_data import Site, Port
from buildgen.topology import Footprint
from sitegen.adapters import adapt_validated_legacy_site
from sitegen.identity import CanonicalFrame, GeographicFrame, SourceIdentity, SourceRevision
from sitegen.plan import (EntityRef, FrameContext, InterfaceRecord, Membership,
                          PhysicalExtent, Polygon, ResourceRecord, SiteEvidence,
                          SiteGraph, SitePlan, VerticalInterval, MAX_ITEMS)


def entity(name, kind="building"):
    return EntityRef(SourceIdentity("fixture", name), kind)


def polygon(offset=0):
    return Polygon(((offset, 0), (offset + 10, 0), (offset + 10, 10), (offset, 10)))


def evidence(name="complex", members=(), **kwargs):
    identity = SourceIdentity("fixture", name)
    return SiteEvidence(identity, FrameContext("canonical_enu", CanonicalFrame(1726000000, -435000000)),
                        (SourceRevision(identity, "release-1"),), tuple(members), **kwargs)


class ContractTests(unittest.TestCase):
    def test_nested_mutable_inputs_are_detached_and_really_frozen(self):
        ring = [[0., 0.], [10., 0.], [10., 10.], [0., 10.]]
        endpoints = [[0., 0., 0.], [1., 0., 0.]]
        members = [Membership(entity("building"), "tenant")]
        p = Polygon(ring)
        e = evidence(members=members, association_extent=p, exclusions=[])
        interface = InterfaceRecord("door", entity("building"), "pedestrian", endpoints)
        plan = SitePlan(e, interfaces=[interface], diagnostics=["fixture"])
        original = plan.to_json()
        ring[0][0] = 99
        endpoints[0][0] = 99
        members.clear()
        self.assertEqual(original, plan.to_json())
        self.assertEqual(e.exclusions, ())
        with self.assertRaises(FrozenInstanceError):
            plan.evidence = e
        with self.assertRaises(TypeError):
            p.outer[0][0] = 99
        with self.assertRaises(AttributeError):
            plan.__dict__

    def test_json_and_pickle_worker_round_trips(self):
        station = entity("station", "station")
        e = evidence(members=[Membership(station, "fuel")], exclusions=[polygon(30)])
        resources = [ResourceRecord("pump", "pump", station, [e.ref]),
                     ResourceRecord("common", "shared_circulation", e.ref, [station])]
        graph = SiteGraph([SitePlan(e, resources=resources)])
        decoded = SiteGraph.from_json(graph.to_json())
        self.assertEqual(graph, decoded)
        self.assertEqual(graph, pickle.loads(pickle.dumps(graph)))
        self.assertEqual(graph.to_json(), decoded.to_json())
        payload = graph.to_dict()
        payload["record"]["value"]["sites"].clear()
        self.assertEqual(len(graph.sites), 1)

    def test_order_permutation_ring_rotation_and_winding_are_deterministic(self):
        a, b = entity("a"), entity("b")
        members = [Membership(a, "tenant"), Membership(b, "anchor")]
        ring = [(0, 0), (10, 0), (10, 10), (0, 10)]
        e1 = evidence(members=members, association_extent=Polygon(ring), exclusions=[polygon(20), polygon(40)])
        e2 = evidence(members=members[::-1], association_extent=Polygon(ring[2:] + ring[:2]),
                      exclusions=[polygon(40), polygon(20)])
        self.assertEqual(e1.to_json(), e2.to_json())
        self.assertEqual(Polygon(ring), Polygon(ring[::-1]))
        s1, s2 = SitePlan(e1), SitePlan(evidence("other"))
        self.assertEqual(SiteGraph([s1, s2]).to_json(), SiteGraph([s2, s1]).to_json())

    def test_unknown_exclusions_remain_distinct_from_complete_empty(self):
        unknown = evidence()
        empty = replace(unknown, exclusions=[])
        self.assertIsNone(SiteEvidence.from_json(unknown.to_json()).exclusions)
        self.assertEqual(SiteEvidence.from_json(empty.to_json()).exclusions, ())
        self.assertNotEqual(unknown.to_json(), empty.to_json())

    def test_standalone_lot_needs_no_building_and_association_is_not_pavement(self):
        e = evidence(association_extent=polygon(), extent_basis="mapped_lot")
        self.assertEqual(e.memberships, ())
        self.assertEqual(e.physical_extents, ())
        self.assertEqual(SiteGraph([SitePlan(e)]).sites[0].evidence, e)

    def test_overlapping_mixed_uses_and_levels_do_not_claim_surface_resolution(self):
        member = entity("mixed-use")
        members = [Membership(member, "tenant", VerticalInterval(0, 2)),
                   Membership(member, "parking", VerticalInterval(1, 3)),
                   Membership(entity("deck", "lot"), "parking", VerticalInterval(9, 12, "ellipsoidal_height"))]
        e = evidence(members=members, association_extent=polygon(), physical_extents=[
            PhysicalExtent("lower", polygon(), VerticalInterval(0, 1)),
            PhysicalExtent("upper", polygon(), VerticalInterval(1, 2))])
        plan = SitePlan(e)
        self.assertEqual(len(plan.evidence.memberships), 3)
        self.assertEqual(plan.surface_validation, "unresolved")
        with self.assertRaises(ValueError):
            replace(plan, surface_validation="validated")

    def test_same_level_overlapping_surfaces_remain_explicitly_unresolved(self):
        e = evidence(physical_extents=[PhysicalExtent("one", polygon(), VerticalInterval(0, 0)),
                                       PhysicalExtent("two", polygon(), VerticalInterval(0, 0))])
        self.assertEqual(SitePlan(e).surface_validation, "unresolved")

    def test_missing_resident_members_and_resources_retain_references(self):
        nested, absent = entity("nested", "site"), entity("station", "station")
        e = evidence(members=[Membership(nested), Membership(absent, "fuel")])
        resource = ResourceRecord("common", "shared_circulation", e.ref, [absent, nested])
        restored = SiteGraph.from_json(SiteGraph([SitePlan(e, resources=[resource])]).to_json())
        self.assertEqual(len(restored.sites), 1)
        self.assertEqual(set(restored.sites[0].resources[0].consumers), {absent, nested})
        self.assertEqual(resource.retention, "while_referenced")

    def test_nested_acyclic_associations_accept_load_order_and_reject_cycles(self):
        a = evidence("a", members=[Membership(entity("b", "site"))])
        b = evidence("b", members=[Membership(entity("c", "site"))])
        c = evidence("c")
        graph = SiteGraph([SitePlan(a), SitePlan(b), SitePlan(c)])
        self.assertEqual(graph.to_json(), SiteGraph(list(reversed(graph.sites))).to_json())
        cycle = replace(c, memberships=[Membership(a.ref)])
        with self.assertRaisesRegex(ValueError, "cyclic"):
            SiteGraph([SitePlan(a), SitePlan(b), SitePlan(cycle)])
        with self.assertRaisesRegex(ValueError, "itself"):
            evidence("a", members=[Membership(a.ref)])

    def test_duplicate_resource_and_conflicting_producers_are_rejected(self):
        owner = entity("building")
        e = evidence(members=[Membership(owner)])
        common = ResourceRecord("shared", "surface", e.ref, [owner])
        conflict = replace(common, producer=owner)
        with self.assertRaises(ValueError):
            SitePlan(e, resources=[common, conflict])
        other = evidence("other")
        with self.assertRaises(ValueError):
            SiteGraph([SitePlan(e, resources=[common]),
                       SitePlan(other, resources=[replace(common, producer=other.ref, consumers=())])])

    def test_station_function_and_shared_circulation_keep_their_owners(self):
        station = entity("station", "station")
        e = evidence(members=[Membership(station, "fuel")])
        pump = ResourceRecord("pump", "pump", station, [e.ref])
        trigger = ResourceRecord("trigger", "refuelling_trigger", station)
        common = ResourceRecord("common", "shared_circulation", e.ref, [station])
        plan = SitePlan(e, resources=[pump, trigger, common])
        self.assertEqual(len(plan.resources), 3)
        with self.assertRaises(ValueError):
            replace(pump, producer=e.ref)
        with self.assertRaises(ValueError):
            replace(common, producer=station)
        with self.assertRaises(ValueError):
            replace(common, retention="producer_resident")
        with self.assertRaises(ValueError):
            SitePlan(e, resources=[replace(common, consumers=[entity("undeclared")])])

    def test_schema_unknown_fields_and_conflicting_revisions_fail_closed(self):
        e = evidence()
        for version in (True, 0, 2):
            payload = e.to_dict()
            payload["schema_version"] = version
            with self.assertRaises(ValueError):
                SiteEvidence.from_dict(payload)
        payload = e.to_dict()
        payload["record"]["value"]["unexpected"] = 1
        with self.assertRaises(ValueError):
            SiteEvidence.from_dict(payload)
        with self.assertRaises(ValueError):
            replace(e, revisions=[e.revisions[0], SourceRevision(e.identity, "release-2")])
        with self.assertRaises(ValueError):
            VerticalInterval(float("nan"), 1)

    def test_record_limits_stop_consuming_oversized_iterables(self):
        owner = entity("owner")
        def over_budget(value, count):
            for _ in range(count + 1):
                yield value
            raise AssertionError("iterable consumed after overflow was already known")
        with self.assertRaises(ValueError):
            ResourceRecord("surface", "surface", owner, over_budget(owner, MAX_ITEMS))
        with self.assertRaises(ValueError):
            InterfaceRecord("door", owner, "pedestrian", over_budget((0, 0, 0), 2))
        with self.assertRaises(ValueError):
            InterfaceRecord("door", owner, "pedestrian", [over_budget(0, 3), (1, 1, 1)])
        with self.assertRaises(ValueError):
            SitePlan(evidence(), diagnostics=over_budget("diagnostic", MAX_ITEMS))
        with self.assertRaises(ValueError):
            ResourceRecord("x" * 513, "surface", owner)


class LegacyAdapterTests(unittest.TestCase):
    def legacy(self):
        boundary = Footprint(((0, 0), (20, 0), (20, 20), (0, 20)))
        exclusion = Footprint(((1, 1), (2, 1), (2, 2), (1, 2)))
        return Site("property", "digest-1", boundary, (exclusion, exclusion),
                    (Port("parking", (4., 0., .2), (7., 0., .2)),), 1.1, exclusion)

    def context(self):
        return FrameContext("legacy_projected_xy", GeographicFrame(172.6, -43.5, 30), 1000, -300)

    def test_explicit_context_owner_and_validated_type_are_required(self):
        site = self.legacy()
        with self.assertRaises(TypeError):
            adapt_validated_legacy_site(site, owner=entity("station", "station"), frame=self.context(), source_namespace="survey")
        with self.assertRaises(ValueError):
            adapt_validated_legacy_site(site, owner=entity("owner"), frame=evidence().frame, source_namespace="survey")
        with self.assertRaises(TypeError):
            adapt_validated_legacy_site({}, owner=entity("owner"), frame=self.context(), source_namespace="survey")
        with self.assertRaises(ValueError):
            self.context().require_canonical()

    def test_legacy_owner_exact_geometry_holes_exclusions_and_heights_survive(self):
        site = self.legacy()
        adapted = adapt_validated_legacy_site(site, owner=entity("owner"), frame=self.context(), source_namespace="survey")
        self.assertEqual(adapted.to_legacy_site(), site)
        self.assertEqual(adapted.evidence.memberships, (Membership(entity("owner"), "owner"),))
        self.assertEqual(adapted.evidence.frame.kind, "legacy_projected_xy")
        self.assertEqual(adapted.evidence.physical_extents, ())
        self.assertIsNotNone(adapted.evidence.exclusions)
        self.assertEqual(pickle.loads(pickle.dumps(adapted)).to_legacy_site(), site)
        self.assertEqual(SitePlan.from_json(adapted.plan.to_json()), adapted.plan)
        other = adapt_validated_legacy_site(site, owner=entity("owner"), frame=self.context(), source_namespace="another-survey")
        self.assertNotEqual(adapted.plan.interfaces[0].identity, other.plan.interfaces[0].identity)

    def test_legacy_frame_local_interface_ids_survive_earlier_port_insertion(self):
        site = self.legacy()
        def adapt(value, frame=None):
            return adapt_validated_legacy_site(value, owner=entity("owner"),
                        frame=frame or self.context(), source_namespace="survey")
        original = adapt(site)
        earlier = Port("parking", (0., 0., .2), (3., 0., .2))
        expanded_site = replace(site, ports=(earlier, *site.ports))
        expanded = adapt(expanded_site)
        endpoint_to_id = {i.endpoints: i.identity for i in expanded.plan.interfaces}
        unchanged = original.plan.interfaces[0]
        self.assertEqual(endpoint_to_id[unchanged.endpoints], unchanged.identity)
        self.assertTrue(unchanged.identity.startswith("legacy-frame-interface-v1:"))
        self.assertEqual(expanded.to_legacy_site(), expanded_site)
        rebased = adapt(site, replace(self.context(), x0=1001.))
        self.assertNotEqual(rebased.plan.interfaces[0].identity, unchanged.identity)
        # Existing duplicate-port acceptance is retained, with occurrence suffixes
        # confined to identical content rather than indices over every port.
        duplicate_site = replace(site, ports=(*site.ports, *site.ports))
        duplicated = adapt(duplicate_site)
        self.assertEqual(len(duplicated.plan.interfaces), 2)
        self.assertIn(unchanged.identity, {i.identity for i in duplicated.plan.interfaces})
        self.assertEqual(duplicated.to_legacy_site(), duplicate_site)

    def test_legacy_catalogue_still_rejects_overlapping_properties_and_unknown_inventory(self):
        geometry = {"type": "Polygon", "coordinates": [[[172.6, -43.5], [172.601, -43.5],
                     [172.601, -43.499], [172.6, -43.499], [172.6, -43.5]]]}
        def feature(name, complete=True):
            return {"type": "Feature", "geometry": geometry, "properties": {
                "site_id": name, "owner_id": name, "source": "fixture", "release": "1",
                "obstacles_complete": complete}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sites.json"
            with patch.dict(os.environ, {"BNE_BUILDING_SITES": str(path)}):
                try:
                    for features in ([feature("one"), feature("two")], [feature("one", False)]):
                        path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
                        site_data.catalogue.cache_clear()
                        with self.assertRaises(ValueError):
                            site_data.catalogue()
                finally:
                    site_data.catalogue.cache_clear()

    def test_projected_real_catalogue_adapter_roundtrip_keeps_legacy_output(self):
        import geodesy
        geometry = {"type": "Polygon", "coordinates": [[[172.6, -43.5], [172.601, -43.5],
                     [172.601, -43.499], [172.6, -43.499], [172.6, -43.5]]]}
        props = dict(site_id="survey-site", owner_id="building", source="survey", release="1",
                     obstacles_complete=True)
        data = dict(type="FeatureCollection", features=[dict(type="Feature", geometry=geometry, properties=props)])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sites.json"
            path.write_text(json.dumps(data))
            with patch.dict(os.environ, {"BNE_BUILDING_SITES": str(path)}):
                site_data.catalogue.cache_clear()
                try:
                    old = site_data.project("building", geodesy.EnuFrame(-43.5, 172.6, 30), x0=1000, y0=-300)
                    adapted = adapt_validated_legacy_site(old, owner=entity("building"),
                                frame=self.context(), source_namespace="survey")
                    self.assertEqual(adapted.to_legacy_site(), old)
                    self.assertEqual(adapted.evidence.exclusions, ())
                    self.assertEqual(adapted.evidence.frame.frame.height, 30.)
                finally:
                    site_data.catalogue.cache_clear()


if __name__ == "__main__":
    unittest.main()
