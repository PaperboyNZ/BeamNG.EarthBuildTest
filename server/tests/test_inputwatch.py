"""Source additions, removal and replacement invalidate accepted products."""
from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import inputwatch


class InputWatchTests(unittest.TestCase):
    def test_nested_scope_and_absence_have_explicit_revision(self):
        with tempfile.TemporaryDirectory() as folder:
            existing=Path(folder)/'existing';existing.write_bytes(b'initial')
            absent=Path(folder)/'not-downloaded'
            with inputwatch.capture() as outer:
                inputwatch.paths([existing,absent])
                with inputwatch.capture() as inner:inputwatch.paths([Path(folder)/'other'])
                self.assertEqual(len(outer['files']),2)
                self.assertEqual(len(inner['files']),1)
            snapshot=inputwatch.snapshot(outer)
            self.assertTrue(inputwatch.current(snapshot))
            absent.write_bytes(b'new terrain now available')
            self.assertFalse(inputwatch.current(snapshot))
            absent.unlink();existing.write_bytes(b'new street/access revision')
            self.assertFalse(inputwatch.current(snapshot))

    def test_budget_overflow_suppresses_caching_without_losing_geometry(self):
        from unittest.mock import patch
        with patch.object(inputwatch,'MAX_FILES',2),inputwatch.capture() as state:
            inputwatch.paths(['one','two','three'])
            self.assertTrue(state['overflow'])
            self.assertIsNone(inputwatch.snapshot(state))
        self.assertIsNone(inputwatch.ACTIVE.get())


if __name__=='__main__':unittest.main()
