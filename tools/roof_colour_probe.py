"""Compatibility entry point for the offline roof experiment."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'server'))
from buildgen.roof_sampling import CachedTiles, mercator_pixels, lab, sample
