"""Automatic commercial access commits complete playable strips, never cut guesses."""
from dataclasses import FrozenInstanceError
from pathlib import Path
import copy
import pickle
import sys
import unittest

import numpy as np
from shapely.geometry import Polygon, box

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from buildgen.access import Solid
from sitegen.commercial_access import propose_access, commit_access, perimeter_curbs, ROAD_LIP
import sidewalks
import vehicle_crossings


def fixture(*, walk=False, terrain=None, offset=(0., 0.), road='residential', obstacles=(), **kwargs):
    offset = np.asarray(offset)
    terrain = terrain or (lambda xy: np.zeros(len(xy)))
    sample = lambda xy: terrain(np.asarray(xy)+offset)
    source = np.c_[[[-3., 0.], [3., 0.]], sample([[-3., 0.], [3., 0.]])+.06]
    rect = np.array([[-10., 0.], [10., 0.], [10., 12.], [-10., 12.]])
    receiver = Solid('site_parking', tuple(map(tuple, np.c_[rect, sample(rect)+.06])), -.1)
    lines = [(np.array([[-50., -12.], [50., -12.]])+offset, 4., road, False)]
    walks = []
    if walk:
        walks = [dict(pts=np.c_[np.array([[-50., -6.75], [50., -6.75]])+offset, [0., 0.]],
                      side=1, w=2.5, caps=(True, True))]
    raw = copy.deepcopy(walks)
    calls = []
    def ground(xy):
        calls.append(np.asarray(xy).copy())
        return terrain(xy)
    proposal = propose_access(source, lines, walks, ground, *offset, owner='site:one',
                              receiving=(receiver,), obstacles=obstacles, **kwargs)
    return proposal, walks, raw, calls, receiver, lines, source


class CommercialAccessTests(unittest.TestCase):
    def test_detached_flat_route_shares_source_and_road_and_batches_terrain(self):
        p, walks, raw, calls, receiver, _, source = fixture()
        self.assertIsNotNone(p)
        self.assertEqual(len(calls), 1)
        self.assertLessEqual(p.terrain_points, 4*33*5+25)
        self.assertEqual(walks, [])
        self.assertEqual(p.receiving, (receiver,))
        points = np.array([point for s in p.surfaces for point in s.top])
        self.assertTrue(np.allclose(points[np.isclose(points[:, 1], -8.), 2], ROAD_LIP))
        self.assertTrue(np.allclose(points[np.isclose(points[:, 1], 0.), 2], .06))
        for solid in p.surfaces:
            a, b, c, _ = np.array(solid.top)
            self.assertGreater(np.cross(b-a, c-a)[2], 0.)
        with self.assertRaises(FrozenInstanceError):
            p.width = 7.

    def test_slope_and_rebase_use_same_frozen_geometry(self):
        terrain = lambda xy: np.asarray(xy)[:, 0]*.005-np.asarray(xy)[:, 1]*.01
        p, *_ = fixture(terrain=terrain)
        self.assertIsNotNone(p)
        offset = np.array([123456., 654321.])
        rebased_terrain = lambda xy: terrain(np.asarray(xy)-offset)
        q, *_ = fixture(terrain=rebased_terrain, offset=offset)
        self.assertIsNotNone(q)
        np.testing.assert_allclose([s.top for s in p.surfaces], [s.top for s in q.surfaces])
        np.testing.assert_allclose(np.asarray(q.parking_record()['n'])[:, :2]-offset,
                                   np.asarray(p.parking_record()['n'])[:, :2])

    def test_walk_cut_has_exact_seam_and_idempotent_owned_commit(self):
        p, walks, raw, calls, *_ = fixture(walk=True)
        self.assertIsNotNone(p)
        self.assertNotIn('driveways', walks[0])
        points = np.array([point for s in p.surfaces for point in s.top])
        rear = sidewalks.CURB_H+2.5*sidewalks.CROSS_SLOPE
        self.assertTrue(np.allclose(points[np.isclose(points[:, 1], -5.5), 2], rear))
        drives = []
        self.assertTrue(commit_access(p, walks, raw, drives))
        self.assertTrue(commit_access(p, walks, raw, drives))
        self.assertEqual(len(walks[0]['driveways']), 1)
        self.assertEqual(walks[0]['driveways'], raw[0]['driveways'])
        self.assertEqual(walks[0]['driveways'][0][-1], ROAD_LIP)
        self.assertEqual(len(drives), 1)
        self.assertEqual(drives[0]['n'][-1][1], -8.)
        section = vehicle_crossings.section(2.5, sidewalks.CURB_H, 1., ROAD_LIP)
        self.assertAlmostEqual(np.interp(2.5, section[:, 0], section[:, 1]), rear)

    def test_commit_rechecks_later_pedestrian_ramp_without_partial_mutation(self):
        p, walks, raw, *_ = fixture(walk=True)
        walks[0]['ramps'] = [(48., 52.)]
        before = pickle.dumps((walks, raw))
        drives = [{'original': True}]
        self.assertFalse(commit_access(p, walks, raw, drives))
        self.assertEqual(pickle.dumps((walks, raw)), before)
        self.assertEqual(drives, [{'original': True}])

    def test_neighbor_flare_and_pedestrian_flare_are_reserved(self):
        p, walks, raw, _, receiver, lines, source = fixture(walk=True)
        lo, hi = p.crossing[1:3]
        for key in ('driveways', 'ramps'):
            walks[0][key] = [(hi+1., hi+3.)]
            proposal = propose_access(source, lines, walks, lambda xy: np.zeros(len(xy)),
                                      0., 0., owner='site:one', receiving=(receiver,))
            self.assertIsNone(proposal, key)
            walks[0].pop(key)

    def test_unknown_receiving_area_rejects_whole_proposal(self):
        def unknown(xy):
            xy = np.asarray(xy)
            return np.where(xy[:, 1] > 5., np.nan, 0.)
        p, walks, *_ = fixture(terrain=unknown, walk=True)
        self.assertIsNone(p)
        self.assertNotIn('driveways', walks[0])

    def test_unknown_route_or_hidden_full_width_ridge_rejects(self):
        for terrain in (lambda xy: np.where(np.asarray(xy)[:, 1] < -1., np.nan, 0.),
                        lambda xy: np.where((abs(np.asarray(xy)[:, 0]-1.5) < .1)
                                            & (np.asarray(xy)[:, 1] < -.1), .8, 0.)):
            p, walks, *_ = fixture(terrain=terrain, walk=True)
            self.assertIsNone(p)
            self.assertNotIn('driveways', walks[0])

    def test_obstacles_and_controlled_roads_do_not_cut(self):
        for kwargs in (dict(obstacles=(box(-1., -4., 1., -2.),)),
                       dict(road='motorway'), dict(road='trunk'),
                       dict(bounds=(-100., -5., 100., 100.))):
            p, walks, *_ = fixture(walk=True, **kwargs)
            self.assertIsNone(p)
            self.assertNotIn('driveways', walks[0])

    def test_receiving_height_must_match_source_and_cannot_float(self):
        p, walks, _, _, receiver, lines, source = fixture()
        high = np.asarray(source).copy(); high[:, 2] += .01
        self.assertIsNone(propose_access(high, lines, walks, lambda xy: np.zeros(len(xy)),
                                         0., 0., owner='site:one', receiving=(receiver,)))
        unknown = lambda xy: np.where(np.asarray(xy)[:, 1] > 5., np.nan, 0.)
        self.assertIsNone(propose_access(source, lines, walks, unknown,
                                         0., 0., owner='site:one', receiving=(receiver,)))

    def test_one_batch_for_bounded_alternatives_and_unknown_nearest_falls_back(self):
        p, walks, _, _, receiver, lines, source = fixture()
        # Roads on opposite sides of the source give two true alternatives.
        roads = [*lines, (np.array([[-50., 16.], [50., 16.]]), 4., 'residential', False)]
        # Omit a receiving area here to isolate route fallback semantics.
        calls = []
        def terrain(xy):
            calls.append(len(xy))
            return np.where(np.asarray(xy)[:, 1] < -2., np.nan, 0.)
        alternative = propose_access(source, roads, [], terrain, 0., 0., owner='site:one')
        self.assertIsNotNone(alternative)
        self.assertEqual(len(calls), 1)
        self.assertEqual(alternative.terrain_points, 2*33*5)
        self.assertEqual(alternative.route[-1][1], 12.)

    def test_reservation_added_after_plan_blocks_atomic_commit(self):
        p, walks, raw, *_ = fixture(walk=True)
        _, lo, hi, _ = p.crossing
        walks[0]['driveways'] = [(hi+1., hi+3.)]
        before = pickle.dumps((walks, raw))
        self.assertFalse(commit_access(p, walks, raw, []))
        self.assertEqual(pickle.dumps((walks, raw)), before)

    def test_stale_raw_walk_does_not_mutate_actual_or_drive_records(self):
        p, walks, raw, *_ = fixture(walk=True)
        raw[0]['pts'][0, 0] += 1.
        before = copy.deepcopy((walks, raw))
        drives = []
        self.assertFalse(commit_access(p, walks, raw, drives))
        self.assertEqual(walks[0].get('driveways'), None)
        np.testing.assert_array_equal(raw[0]['pts'], before[1][0]['pts'])
        self.assertEqual(drives, [])

    def test_raw_walks_match_xy_before_road_draping_and_can_be_reordered(self):
        p, walks, raw, *_ = fixture(walk=True)
        raw[0]['pts'][:, 2] += 7.25
        another = copy.deepcopy(raw[0])
        another['pts'][:, 0] += 150.
        raw.insert(0, another)
        self.assertTrue(commit_access(p, walks, raw, []))
        self.assertEqual(walks[0]['driveways'], raw[1]['driveways'])
        self.assertNotIn('driveways', raw[0])

    def test_perimeter_curbs_leave_full_walk_and_drive_openings(self):
        edges = [((-10., 0., .06), (10., 0., .06))]
        openings = (box(-3., -5., 3., 5.), box(6., -2., 7.5, 2.))
        blocks = perimeter_curbs(edges, openings)
        self.assertEqual(len(blocks), 3)
        for block in blocks:
            self.assertEqual(block.kind, 'site_curb')
            shape = Polygon(np.asarray(block.top)[:, :2])
            self.assertFalse(any(shape.intersects(p) for p in openings))
            self.assertTrue(np.allclose(np.asarray(block.top)[:, 2], .18))
            self.assertLess(block.bottom, .06)

    def test_curbs_preserve_crossfall_and_vertical_offset_at_every_corner(self):
        plane=np.array([.035,-.08,137.4])
        xy=np.array([[10.,15.],[31.,19.]])
        edge=np.c_[xy,np.c_[xy,np.ones(2)]@plane]
        blocks=perimeter_curbs((edge,),openings=(box(19.,10.,21.,25.),),base_plane=plane)
        self.assertEqual(len(blocks),2)
        for block in blocks:
            top=np.asarray(block.top)
            base=np.c_[top[:,:2],np.ones(4)]@plane
            np.testing.assert_allclose(top[:,2]-base,.12,atol=1e-10)
            self.assertLess(block.bottom,float(base.min()))
            self.assertFalse(Polygon(top[:,:2]).intersects(box(19.,10.,21.,25.)))
        wrong=edge.copy();wrong[:,2]+=.02
        self.assertEqual(perimeter_curbs((wrong,),base_plane=plane),())


if __name__ == '__main__':
    unittest.main()
