"""Opt-in aggregate access telemetry; never retained in a building/worker plan.

Counts describe resolver invocations, not unique properties across revisits.
Candidate rejections count segment/proposal checks; final outcomes count eligible buildings.
No source IDs, geometry or unbounded per-building history are retained.
"""
from collections import Counter


class DrivewayAudit:
    def __init__(self):
        self._counts = {key: Counter() for key in (
            'eligibility', 'candidates', 'candidate_rejections', 'outcomes',
            'crossings', 'work', 'resolver_skipped')}

    def record(self, group, reason, count=1):
        self._counts[group][reason] += count

    def snapshot(self):
        return {
            'schema_version': 1,
            'scope': 'driveway_resolver_invocations',
            'candidate_rejections_scope': 'street_segments_and_ranked_routes_first_failed_check',
            'crossing_only_feasibility': 'not_evaluated',
            'counts': {group: dict(sorted(counts.items()))
                       for group, counts in self._counts.items()},
        }
