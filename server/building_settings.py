"""Saved building mode and immutable per-job selection for live switching."""
from contextvars import ContextVar
import json
import os
from pathlib import Path

GENERATORS = ("legacy", "v2")
LABELS = {"legacy": "Simple", "v2": "Advanced"}
_mode = ContextVar("building_generator", default=None)
_default = None


def current():
    return _mode.get() or _default or os.environ.get("BNE_BUILDING_GENERATOR", "legacy")


def set_default(mode):
    global _default
    if mode not in GENERATORS:
        raise ValueError("Invalid building generator")
    _default = mode


def run(mode, function, *args, **kwargs):
    """Picklable worker entry point; concurrent old/new jobs never share a mode."""
    if mode not in GENERATORS:
        raise ValueError("Invalid building generator")
    token = _mode.set(mode)
    try:
        return function(*args, **kwargs)
    finally:
        _mode.reset(token)


def cache_identity():
    mode = current()
    if mode == 'legacy':
        return (mode,)
    import shapely
    from buildgen import roof_colours, zones, site_data
    from sitegen import shared_courts
    return (mode, shapely.__version__, shapely.geos_version_string,
            roof_colours.catalogue()[0], zones.catalogue()[0],
            site_data.catalogue()[0], shared_courts.catalogue()[0])


def prebuild(mode, function, *args, **kwargs):
    """Preserve RespawningPool's optional-work classification for prebuilt areas."""
    return run(mode, function, *args, **kwargs)


def saved_generator(user_dir):
    """Read the mod's saved choice, including BeamNG's lowercase Linux filename."""
    if not user_dir:
        return None
    for name in ("beamngEarth.json", "beamngearth.json"):
        try:
            values = json.loads((Path(user_dir) / "settings" / name).read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        value = values.get("buildingGenerator") if isinstance(values, dict) else None
        return value if value in GENERATORS else None
    return None


def resolve(user_dir, explicit=None, environ=None):
    """CLI > environment > saved mod setting > Simple (the existing default)."""
    environ = os.environ if environ is None else environ
    value = explicit if explicit is not None else environ.get("BNE_BUILDING_GENERATOR")
    if value is not None:
        if value not in GENERATORS:
            raise ValueError("Building generator must be legacy (Simple) or v2 (Advanced)")
        return value
    return saved_generator(user_dir) or "legacy"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-dir", required=True)
    args = parser.parse_args()
    try:
        print(resolve(args.user_dir))
    except ValueError as error:
        parser.error(str(error))
