"""Isolate the incremental property geometry/text cost at each detail setting.

Synthetic repeated building shapes with distinct names, no network or game.
Does not measure the existing full building compiler or engine import/FPS.
"""
from pathlib import Path
from dataclasses import replace
import sys,time,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
from buildgen import font_bootstrap
from preview_commercial_stage_one import fixture,FAMILIES
from buildgen import quality,property_assets as assets,property_geometry as geometry
import buildings as b


def run():
    templates=[fixture(row)[0][0][0] for row in FAMILIES]
    items=tuple((replace(templates[i%6],property_identity=dict(templates[i%6].property_identity,
        display_name='Example property '+str(i),revision=str(i))),0.,0.) for i in range(500))
    result=[]
    def geometry_batch():
        mesh=b.Mesh()
        for s,lo,hi in items:geometry.draw(mesh,s,lo,hi)
        mesh.flush_components()
        return len(mesh.T)//3
    for detail in ('minimum','very_low','low','medium','high','very_high','ultra'):
        start=time.perf_counter();triangles=quality.run(detail,geometry_batch)
        geometry_ms=(time.perf_counter()-start)*1000
        start=time.perf_counter();meshes,boards=quality.run(detail,assets.visuals,items)
        cold_ms=(time.perf_counter()-start)*1000
        start=time.perf_counter();quality.run(detail,assets.visuals,items)
        warm_ms=(time.perf_counter()-start)*1000
        rank=quality.PROFILES[detail].rank
        result.append(dict(detail=detail,buildings=500,incremental_facade_triangles=triangles,
            incremental_geometry_ms=round(geometry_ms,2),new_text_ms=round(cold_ms,2),
            cached_text_ms=round(warm_ms,2),fascia_count=len(boards),
            trolley_triangles=len(assets.furniture_template('trolley_shelter',rank)[2]) if rank>=2 else 0))
    return {'scope':__doc__,'results':result}


if __name__=='__main__':print(json.dumps(run(),indent=2))
