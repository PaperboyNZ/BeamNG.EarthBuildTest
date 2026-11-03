"""Distant work must not prevent an idle road pool from accepting nearby work."""
from concurrent.futures import Future
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pools


class Executor:
    def __init__(self, workers, **kwargs):
        self._max_workers = workers
        self.futures = []

    def submit(self, *args, **kwargs):
        future = Future()
        self.futures.append(future)
        return future

    def shutdown(self, **kwargs):
        pass


class SchedulingTests(unittest.TestCase):
    def test_far_backlog_does_not_block_terrain_or_idle_road_workers(self):
        # The failed native run's admission pattern: queued far-building work
        # consumed reservations before execution, starving an unrelated road pool.
        with patch.object(pools, 'ProcessPoolExecutor', Executor):
            far = pools.RespawningPool('far building', 1)
            terrain = pools.RespawningPool('block', 1)
            roads = pools.RespawningPool('road tile', 4)
            distant = [far.submit(abs, -i) for i in range(16)]
            ground = terrain.submit(abs, -1)
            nearby = roads.submit(abs, -2)
            self.assertEqual(len(far._pool.futures), 16)
            self.assertEqual(len(terrain._pool.futures), 1)
            self.assertEqual(len(roads._pool.futures), 1)
            self.assertFalse(nearby.done())
            nearby.set_result(2)
            self.assertEqual(nearby.result(), 2)
            self.assertTrue(all(not job.done() for job in distant))
            self.assertFalse(ground.done())
            self.assertEqual(roads.inflight, 0)
            for job in distant + [ground]:
                job.cancel()
            self.assertEqual(far.inflight, 0)
            self.assertEqual(terrain.inflight, 0)


if __name__ == '__main__':
    unittest.main()
