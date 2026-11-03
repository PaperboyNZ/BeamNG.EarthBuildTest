"""Offline sidewalk regression suite; real-data cache-dependent tests are separate."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/sidewalk-uv/final-tests'
NAMES = ['test_sidewalk_uv', 'test_sidewalk_layout', 'test_sidewalk_collision', 'test_streetscape',
         'test_buildgen_driveways', 'test_buildgen_garages', 'test_islands', 'test_roadcorners',
         'test_roads', 'test_roadmesh', 'test_sitegen_hardscape', 'test_roadgeo.OwnershipTest',
         'test_roadgeo.SeamsTest', 'test_roadgeo.ExactVariantTest', 'test_roadgeo.GeoTrackerRebaseTest']


def main():
    os.chdir(ROOT)
    tmp = ROOT / 'build/sidewalk-uv/tmp'
    tmp.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, TEMP=str(tmp), TMP=str(tmp))
    result = subprocess.run([sys.executable, 'tools/run_tests.py', *NAMES, '--logs', str(OUT),
                             '--par', '3', '--timeout', '180'], env=env)
    if result.returncode:
        return result.returncode
    total = 0
    for name in NAMES:
        text = (OUT / (name + '.log')).read_text()
        assert re.search(r'^OK$', text, re.M), name
        total += int(re.search(r'Ran (\d+) tests?', text)[1])
    code = ("import sys;sys.path.insert(0,'build/lua-runtime');from lupa.luajit21 import LuaRuntime;"
            "LuaRuntime().execute(\"arg={[0]='mod/tests/test_roads.lua'};dofile(arg[0])\")")
    lua = subprocess.run([sys.executable, '-B', '-c', code], env=env, capture_output=True, text=True)
    (OUT / 'roads-lua.log').write_text(lua.stdout + lua.stderr)
    print(lua.stdout, end='')
    if lua.returncode:
        print(lua.stderr)
        return lua.returncode
    assertions = int(re.search(r': (\d+) passed, 0 failed', lua.stdout)[1])
    report = dict(status='passed', python_tests=total, python_suites=len(NAMES), lua_assertions=assertions,
                  scope='Offline synthetic geometry/UV/style/export/streaming checks; no engine/FPS acceptance',
                  cache_dependent_tests='Two test_roadgeo.RealDataTest cases require missing Overture cached parquet; not included')
    (OUT.parent / 'tests.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
