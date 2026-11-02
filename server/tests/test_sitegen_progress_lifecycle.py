"""Tracker cancellation stops optional previews while final workers keep running."""
from concurrent.futures import Future
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import geodesy
import geotiles
import roads
import buildings
from buildgen import progressive


class EssentialFuture(Future):
    def __init__(self):
        super().__init__()
        self.cancel_calls = 0
        self.set_running_or_notify_cancel()

    def cancel(self):
        self.cancel_calls += 1
        return super().cancel()


class FakePool:
    def __init__(self):
        self.shutdown_calls = []

    def shutdown(self, **kwargs):
        self.shutdown_calls.append(kwargs)


class FakeLoop:
    """Capture executor submissions without threads, event loops or sockets."""
    def __init__(self):
        self.submitted = []

    def run_in_executor(self, pool, builder, *args):
        future = EssentialFuture()
        self.submitted.append((future, builder, args))
        return future


class ProgressLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.frame = geodesy.EnuFrame(0., 0.)
        self.key = geotiles.tile_of(0., 0.)

    def launch(self):
        tracker = roads.GeoTracker()
        tracker.pool = FakePool()
        self.addCleanup(tracker.close)
        loop = FakeLoop()
        messages = []
        conn = SimpleNamespace(building_progress=True, send=messages.append,
                               s=SimpleNamespace(out_dir=self.tmp.name))
        with patch.object(roads, 'geo_wanted', return_value={self.key: 0.}):
            tracker.on_pose(conn, 1, 0., 0., loop, lambda *a, **kw: None, frame=self.frame)
        future, builder, _ = loop.submitted[0]
        token = builder.keywords['progress_token']
        self.assertEqual(tracker._building_progress[self.key]['token'], token)
        return tracker, loop, conn, future, token, messages

    def final_result(self):
        return dict(content=('/vfs/final.json', 0, {'h': 'fixture-final', 'parts': {}}, []))

    def test_close_signals_worker_without_cancelling_essential_future(self):
        tracker, _, conn, future, token, messages = self.launch()
        publisher = progressive.Publisher(self.tmp.name, '/vfs', None, token)
        self.assertTrue(publisher.checkpoint())
        self.assertEqual(tracker._progress_out_dir, conn.s.out_dir)
        tracker.close()
        self.assertTrue(progressive.cancellation_path(self.tmp.name, token).exists())
        self.assertFalse(publisher.checkpoint())
        self.assertEqual(tracker._building_progress, {})
        self.assertEqual(future.cancel_calls, 0)
        self.assertTrue(future.running())
        self.assertFalse(future.cancelled())
        self.assertIn({'wait': False, 'cancel_futures': True}, tracker.pool.shutdown_calls)
        # Completion remains possible after optional preview cancellation.
        with patch.object(roads.staging, 'inline_json', return_value=None):
            future.set_result(self.final_result())
        self.assertTrue(future.done())
        self.assertIn(self.key, tracker.sent)
        final = next(m for m in messages if m['type'] == 'roads_tile')
        self.assertNotIn('buildingProgressToken', final)
        tracker.close()  # No token resurrection on repeated close.
        self.assertEqual(tracker._building_progress, {})

    def test_close_signals_every_active_token(self):
        tracker, _, _, future, first, _ = self.launch()
        second_key = (self.key[0] + 1, self.key[1])
        second = progressive.begin(tracker, second_key)
        tracker.close()
        self.assertTrue(progressive.cancellation_path(self.tmp.name, first).exists())
        self.assertTrue(progressive.cancellation_path(self.tmp.name, second).exists())
        self.assertEqual(tracker._building_progress, {})
        self.assertEqual(future.cancel_calls, 0)

    def test_stale_captured_callbacks_cannot_finish_replacement_token(self):
        for completion in ('success', 'none', 'error'):
            with self.subTest(completion=completion):
                tracker, _, conn, old_future, old_token, messages = self.launch()
                progressive.finish(tracker, conn, 1, self.key, False, token=old_token)
                replacement = progressive.begin(tracker, self.key)
                replacement_future = EssentialFuture()
                tracker.futs[self.key] = replacement_future
                tracker.building.add(self.key)
                path = progressive.manifest_path(self.tmp.name, replacement)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('{}', encoding='utf-8')
                messages.clear()
                with patch.object(roads.staging, 'inline_json', return_value=None), \
                     patch.object(roads.log, 'warning'):
                    if completion == 'error':
                        old_future.set_exception(OSError('obsolete worker fixture'))
                    else:
                        old_future.set_result(self.final_result() if completion == 'success' else None)
                self.assertEqual(tracker._building_progress[self.key]['token'], replacement)
                self.assertIs(tracker.futs[self.key], replacement_future)
                self.assertIn(self.key, tracker.building)
                self.assertTrue(path.exists())
                self.assertFalse(progressive.cancellation_path(self.tmp.name, replacement).exists())
                self.assertFalse(any(m.get('cancel') and m.get('token') == replacement for m in messages))
                self.assertFalse(any(m.get('buildingProgressToken') == replacement for m in messages))
                self.assertEqual(replacement_future.cancel_calls, 0)

    def test_far_unwanted_preview_is_cancelled_without_aborting_final_worker(self):
        tracker, loop, conn, future, token, messages = self.launch()
        with patch.object(roads, 'geo_wanted', return_value={}), \
             patch.object(geotiles, 'quad_dist', return_value=roads.DROP_M + 1.):
            tracker.on_pose(conn, 1, 0., 0., loop, None, frame=self.frame)
        self.assertNotIn(self.key, tracker._building_progress)
        self.assertTrue(progressive.cancellation_path(self.tmp.name, token).exists())
        self.assertTrue(any(m.get('cancel') and m.get('token') == token for m in messages))
        self.assertEqual(future.cancel_calls, 0)
        self.assertTrue(future.running())
        self.assertIs(tracker.futs[self.key], future)
        self.assertIn(self.key, tracker.building)
        self.assertEqual(len(loop.submitted), 1)

    def test_wanted_near_view_and_focus_previews_are_retained(self):
        cases = ('wanted', 'near', 'view', 'focus')
        for case in cases:
            with self.subTest(case=case):
                tracker, loop, conn, future, token, messages = self.launch()
                view = (100., 100.) if case == 'view' else None
                foci = ((200., 200., 100.),) if case == 'focus' else ()

                def distance(_quad, x, y):
                    if case == 'near' or (case == 'view' and (x, y) == view):
                        return roads.DROP_M - 1.
                    if case == 'focus' and (x, y) == foci[0][:2]:
                        return foci[0][2] + roads.TILE - 1.
                    return roads.DROP_M + 1.

                with patch.object(roads, 'geo_wanted', return_value={self.key: 0.} if case == 'wanted' else {}), \
                     patch.object(geotiles, 'tiles_near', return_value=[]), \
                     patch.object(geotiles, 'quad_dist', side_effect=distance):
                    tracker.on_pose(conn, 1, 0., 0., loop, None, view=view, foci=foci, frame=self.frame)
                self.assertEqual(tracker._building_progress[self.key]['token'], token)
                self.assertFalse(progressive.cancellation_path(self.tmp.name, token).exists())
                self.assertFalse(any(m.get('cancel') for m in messages))
                self.assertEqual(future.cancel_calls, 0)

    def test_published_mesh_reuse_keeps_old_destination_until_atomic_replace(self):
        folder = Path(self.tmp.name)
        source = folder / 'published.cdae'
        destination = folder / 'bld_1_0_0.cdae'
        source.write_bytes(b'complete published mesh')
        destination.write_bytes(b'previous complete mesh')
        mesh = object()  # Reuse should never require inspecting/reencoding it.
        groups = [dict(group='0', visual=['bld'])]
        temporary_paths = []
        original_copy, original_replace = shutil.copyfile, roads.staging.replace

        def copy_with_observer(src, temporary):
            temporary = Path(temporary)
            temporary_paths.append(temporary)
            self.assertNotEqual(temporary, destination)
            temporary.write_bytes(b'partial')
            self.assertEqual(destination.read_bytes(), b'previous complete mesh')
            original_copy(src, temporary)
            self.assertEqual(destination.read_bytes(), b'previous complete mesh')

        def replace_with_observer(temporary, path):
            if Path(path) == destination:
                self.assertEqual(destination.read_bytes(), b'previous complete mesh')
                self.assertEqual(Path(temporary).read_bytes(), b'complete published mesh')
            original_replace(temporary, path)

        with patch.dict(os.environ, {'BNE_BUILDING_GENERATOR': 'v2'}), \
             patch.object(shutil, 'copyfile', side_effect=copy_with_observer), \
             patch.object(roads.staging, 'replace', side_effect=replace_with_observer), \
             patch.object(buildings, 'write', side_effect=AssertionError('published mesh reencoded')):
            roads.write_tile(str(folder), '/vfs', 1, 0, 0, [],
                             bld=([mesh], [], None, groups, {'bld': str(source)}))
        self.assertEqual(destination.read_bytes(), source.read_bytes())
        self.assertEqual(len(temporary_paths), 1)
        self.assertFalse(temporary_paths[0].exists())
        metadata = json.loads((folder / 'roads_1_0_0.json').read_text())
        self.assertEqual(metadata['buildingGroups'], groups)

    def test_partial_preview_copy_is_cleaned_before_final_mesh_reencoding(self):
        folder = Path(self.tmp.name)
        source = folder / 'published.cdae'
        destination = folder / 'bld_1_0_0.cdae'
        source.write_bytes(b'optional published mesh')
        destination.write_bytes(b'previous complete mesh')
        mesh = object()
        copied = []

        def partial_copy(_source, temporary):
            copied.append(Path(temporary))
            Path(temporary).write_bytes(b'partial failed preview copy')
            self.assertEqual(destination.read_bytes(), b'previous complete mesh')
            raise PermissionError('optional published source locked during copy')

        def encode_final(path, actual_mesh):
            self.assertIs(actual_mesh, mesh)
            self.assertEqual(Path(path), destination)
            self.assertFalse(copied[0].exists())
            self.assertEqual(destination.read_bytes(), b'previous complete mesh')
            temporary = roads.staging.tmp_for(path)
            Path(temporary).write_bytes(b'authoritative final mesh')
            roads.staging.replace(temporary, path)

        with patch.dict(os.environ, {'BNE_BUILDING_GENERATOR': 'v2'}), \
             patch.object(shutil, 'copyfile', side_effect=partial_copy), \
             patch.object(buildings, 'write', side_effect=encode_final) as encoded:
            roads.write_tile(str(folder), '/vfs', 1, 0, 0, [],
                             bld=([mesh], [], None, [], {'bld': str(source)}))
        encoded.assert_called_once_with(str(destination), mesh)
        self.assertEqual(destination.read_bytes(), b'authoritative final mesh')
        self.assertFalse(copied[0].exists())
        self.assertEqual(source.read_bytes(), b'optional published mesh')
        metadata = json.loads((folder / 'roads_1_0_0.json').read_text())
        self.assertEqual(metadata['buildingChunks']['visual'], ['bld'])


if __name__ == '__main__':
    unittest.main()
