"""Catalog coverage, safe restart/merge, and real harness integration with a fake game."""
import argparse
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import world_tour as tour
import benchmark as bm
from test_benchmark_tool import FakeGame, FakeClock


class WorldTourTests(unittest.TestCase):
    def setUp(self):
        self.data = tour.read_json(tour.CATALOG)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def capture(self, name='capture', rows=None):
        rows = rows or self.data['places'][:2]
        plan = bm.plan({**self.data, 'places': rows}, 'all')
        folder = self.base / name
        game = FakeGame(self.base / ('game_' + name))
        before = dict(game.player)
        rec = bm.run(game, plan, folder, bm.options(), clock=FakeClock(), log=lambda _: None,
                     meta={'tourBuild': 'build_a', 'setDigest': tour.digest(self.data),
                           'tourCatalog': self.data, 'captureSettings': {'png': False}, 'label': name})
        self.assertTrue(rec['restore']['ok'])
        self.assertEqual((game.player['lat'], game.player['lon']), (before['lat'], before['lon']))
        self.assertEqual(game.camera, 'game')
        return folder, rec

    def test_full_catalog_routes_all_64_styles_and_has_balanced_coverage(self):
        self.assertEqual(tour.validate(self.data, routing=True), 64)
        self.assertEqual(len(self.data['places']), 128)
        self.assertEqual(sum(p['country'] == 'USA' for p in self.data['places']), 5)
        self.assertEqual(sum(p['country'] == 'New Zealand' for p in self.data['places']), 1)
        self.assertEqual(len(bm.plan(self.data, 'all')), 128)
        self.assertEqual(sum(len(p['views']) for p in bm.plan(self.data, 'all')), 640)

    def test_filters_compose_and_offset_is_applied_after_filter(self):
        args = argparse.Namespace(group='stress', theme=None, tag=['industrial'], places=None, offset=2, limit=3)
        rows = tour.select(self.data, args)
        expected = [p for p in self.data['places'] if p['group'] == 'stress' and 'industrial' in p['tags']][2:5]
        self.assertEqual(rows, expected)
        args.places = 'not_a_place'
        with self.assertRaises(ValueError):
            tour.select(self.data, args)

    def test_harness_produces_ten_images_restores_and_resume_skips_them(self):
        folder, rec = self.capture()
        self.assertEqual(len(list(folder.glob('*.jpg'))), 10)
        self.assertEqual(tour.skip_completed(self.data['places'][:2], self.data, [folder], 'build_a'), [])
        # A missing image makes the whole place eligible for retry.
        (folder / rec['places'][0]['views'][0]['file']).unlink()
        remaining = tour.skip_completed(self.data['places'][:2], self.data, [folder], 'build_a')
        self.assertEqual([p['id'] for p in remaining], [self.data['places'][0]['id']])

    def test_view_timeout_cannot_be_accepted_even_if_old_harness_marks_place_ok(self):
        folder, rec = self.capture()
        rec['places'][0]['views'][0]['timedOut'] = True
        bm._write_json(folder / 'run.json', rec)
        remaining = tour.skip_completed(self.data['places'][:2], self.data, [folder], 'build_a')
        self.assertEqual(len(remaining), 1)
        self.assertFalse(tour.safe_image(folder, '../outside.jpg'))

    def test_resume_rejects_different_build_or_catalog(self):
        folder, _ = self.capture()
        with self.assertRaises(ValueError):
            tour.skip_completed(self.data['places'], self.data, [folder], 'build_b')
        changed = copy.deepcopy(self.data)
        changed['defaults']['views'][0]['heading'] = 30
        with self.assertRaises(ValueError):
            tour.skip_completed(changed['places'], changed, [folder], 'build_a')

    def test_merge_handles_hard_kill_snapshot_and_refuses_overwrite_or_mixed_build(self):
        a, _ = self.capture('a', self.data['places'][:1])
        b, rec = self.capture('b', self.data['places'][1:2])
        output = self.base / 'merged'
        tour.merge_runs(output, [a, b])
        merged = tour.read_json(output / 'run.json')
        self.assertEqual(len(merged['places']), 2)
        self.assertEqual(len(list(output.glob('*.jpg'))), 10)
        with self.assertRaises(FileExistsError):
            tour.merge_runs(output, [a, b])
        rec['tourBuild'] = 'different'
        bm._write_json(b / 'run.json', rec)
        with self.assertRaises(ValueError):
            tour.merge_runs(self.base / 'bad_merge', [a, b])
        self.assertFalse((self.base / 'bad_merge').exists())

    def test_compare_flags_real_camera_motion_and_unfinished_loading(self):
        a, _ = self.capture('a', self.data['places'][:1])
        b, rec = self.capture('b', self.data['places'][:1])
        rec['places'][0]['views'][0]['placed']['z'] += 5
        rec['places'][0]['views'][0]['timedOut'] = True
        bm._write_json(b / 'run.json', rec)
        output = self.base / 'comparison'
        tour.compare_runs(a, b, output)
        note = tour.read_json(output / 'compare.json')['places'][0]['views'][0]['note']
        self.assertIn('ACTUAL CAMERA MOVED', note)
        self.assertIn('INCOMPLETE', note)
        self.assertTrue((output / 'index.html').is_file())

    def test_runner_forwards_full_capture_and_records_catalog(self):
        real_run = bm.run
        game = FakeGame(self.base / 'cli_game')
        def fake_run(_game, planned, out, opts, **kw):
            return real_run(game, planned, out, opts, clock=FakeClock(), log=lambda _: None, **kw)
        with patch.object(bm, 'run', side_effect=fake_run), patch.object(bm, 'Game', return_value=game):
            result = tour.main(['run', '--label', 'pilot', '--build', 'candidate', '--limit', '2', '--runs', str(self.base / 'runs')])
        self.assertEqual(result, 0)
        folder = next((self.base / 'runs').iterdir())
        self.assertTrue((folder / 'catalog.json').exists())
        self.assertEqual(tour.read_json(folder / 'run.json')['tourBuild'], 'candidate')


if __name__ == '__main__':
    unittest.main()
