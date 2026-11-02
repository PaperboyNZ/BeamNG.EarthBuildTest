"""Offline real-map lite/full plan reuse against retained source caches.

Downloads are disabled. Derived test products go only beneath --out; existing
map/terrain caches supply source data. Native game loading is not measured here.
"""
import argparse,hashlib,json,os,sys,time
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--lat',type=float,default=-36.91493)
    parser.add_argument('--lon',type=float,default=174.9094);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--read-cache',type=Path,default=Path.home()/'.cache/beamng-earth')
    parser.add_argument('--require-reuse',action='store_true',help='Forbid all combined planning in a fresh worker process')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    os.environ['BNE_BUILDING_GENERATOR']='v2';os.environ['BNE_REVISIT']='off'
    import buildings as b,blockworker as bw,geotiles,revisit
    from buildgen.progressive import DETAIL
    from buildgen import products
    from productcache import Store
    import inputwatch
    bw._s=bw._State(str(args.read_cache),True,True,True,True,True,True,False)
    bw._s.cache_dir=str(args.out/'derived-cache');revisit.CACHE_DIR=bw._s.cache_dir
    gx,gy=geotiles.tile_of(args.lat,args.lon);tile=geotiles.geobox(gx,gy)
    result=dict(place=(args.lat,args.lon),tile=tile.key,scope='Offline actual map/terrain/access/physical planning, visual generation, encoding and publication; no game imports or frame-time claim',
                source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                    [ROOT/'server/blockworker.py',ROOT/'server/buildgen/products.py',ROOT/'server/productcache.py',ROOT/'server/inputwatch.py']})
    result_path=args.out/('restart-results.json' if args.require_reuse else 'results.json')
    for quality in ('lite','full'):
        out=args.out/quality;out.mkdir(exist_ok=True);token=DETAIL.set(quality);start=time.perf_counter()
        guard=patch.object(bw,'_tile_parts',side_effect=AssertionError('restart repeated combined planning')) if args.require_reuse else nullcontext()
        try:
          with guard:
            if quality=='full':
                key,deps=products.address(tile,bw._geo_content_key(tile.key,15,True,False,False,False,0.,None,None,building_detail='accepted-plan-v1'))
                store=Store(bw._s.cache_dir);plan=store.load('accepted-plan',key);physical=store.load('physical',key)
                diagnostic=dict(key=key,dependencies=deps,plan=plan.status,physical=physical.status)
                if plan.status=='ready':
                    diagnostic['changed_inputs']=[p for p,s in plan.value['inputs'] if inputwatch.stamp(p)!=(tuple(s) if s is not None else None)]
                if physical.status=='ready' and plan.status=='ready':
                    diagnostic['matching_revisions']=physical.value['plan_revision']==plan.revision
                    diagnostic['matching_physics']=physical.value['data']['physicalHash']==plan.value['physical_revision']
                result['upgrade_diagnostic']=diagnostic
                result_path.write_text(json.dumps(result,indent=2)+'\n')
                print('upgrade diagnostic',diagnostic,flush=True)
                with patch.object(bw,'_tile_parts',side_effect=AssertionError('combined pipeline re-entered')),\
                     patch.object(b,'collision_mesh',side_effect=AssertionError('collision regenerated')):
                    answer=bw._geo_content(gx,gy,15,str(out),'/'+quality,True,False,False,False,0.,None,None)
            else:answer=bw._geo_content(gx,gy,15,str(out),'/'+quality,True,False,False,False,0.,None,None)
        finally:DETAIL.reset(token)
        elapsed=1000*(time.perf_counter()-start)
        meta=json.loads((out/bw.geo_names(tile.key)['json']).read_text())
        result[quality]=dict(total_ms=elapsed,physicalHash=meta.get('physicalHash'),shapeHashes=meta.get('shapeHashes'),
                             parts=len(answer[2].get('parts',{})),buildingDetail=meta.get('buildingDetail'))
        print(quality,round(elapsed,2),'ms',meta.get('physicalHash'),flush=True)
        result_path.write_text(json.dumps(result,indent=2)+'\n')
    assert result['lite']['physicalHash']==result['full']['physicalHash']
    for what,digest in result['lite']['shapeHashes'].items():
        if what.startswith('bld') and not what.startswith('bldcol'):continue
        assert result['full']['shapeHashes'][what]==digest,(what,'changed physical bytes')
    result['stats']=bw.geo_stats()
    result['combined_planning_and_collision_skipped_on_upgrade']=True
    result_path.write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
