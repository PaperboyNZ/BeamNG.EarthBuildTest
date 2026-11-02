"""Offline building streaming regression checks; no renderer/FPS claims.

Run with the project's Python environment. LuaJIT tests use the optional lupa
runtime in build/lua-runtime (or an installed lupa). Real-data/network tests are
excluded; architecture and geometry tests use deterministic local fixtures.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


def main():
    os.chdir(ROOT)
    sys.dont_write_bytecode=True
    os.environ['BNE_BUILDING_GENERATOR']='v2'
    tmp=ROOT/'build/streaming-optimization/tmp';tmp.mkdir(parents=True,exist_ok=True)
    tempfile.tempdir=str(tmp)
    os.environ['TMP']=os.environ['TEMP']=str(tmp)
    sys.path[:0]=[str(ROOT/'server'),str(ROOT/'server/tests')]
    names=['test_building_fade_shader','test_buildgen_progressive','test_building_streaming.BuildingStreamingTests','test_buildgen_band_frame',
           'test_roadgeo.OwnershipTest','test_roadgeo.SeamsTest',
           'test_roadgeo.ExactVariantTest','test_roadgeo.GeoTrackerRebaseTest',
           'test_buildgen_city','test_buildgen_regional_blocks','test_buildgen_regions',
           'test_buildgen_regional_roofs','test_buildgen_regional_openings',
           'test_buildgen_regional_polish','test_buildgen_road_conflicts','test_buildgen_middle_recess',
           'test_buildgen_far_plan','test_far_plan_lifecycle','test_fargeo.TrackerTest','test_buildgen_sky_plan']
    result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(names))
    ok=result.wasSuccessful()
    for name in ('building_fade','building_progress','building_staging','building_streaming','fargeo','roadgeo','roads','settings','engine_debt','sector_manifest','occupied_resources','collisionfoci','physical_handover','resource_patches','governor','progress_budget'):
        code=("import sys;sys.path.insert(0,'build/lua-runtime');from lupa.luajit21 import LuaRuntime;"
              f"LuaRuntime().execute(\"arg={{[0]='mod/tests/test_{name}.lua'}};dofile(arg[0])\")")
        proc=subprocess.run([sys.executable,'-B','-c',code])
        ok=ok and proc.returncode==0
    return 0 if ok else 1


if __name__=='__main__':sys.exit(main())
