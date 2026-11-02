"""Import a pinned zoning/land-use snapshot. Run --help; no render-time network.

Christchurch can be fetched from its public council service, including source
status fields, via an IDs-first complete retrieval. NYC imports a local WGS84
MapPLUTO GeoJSON export. Empty/unknown codes fail rather than becoming housing.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
from buildgen import zones, zone_adapters

CCC='https://gis.ccc.govt.nz/server/rest/services/OpenData/DistrictPlan/FeatureServer/78/query'


def request(params):
    url=CCC+'?'+urllib.parse.urlencode(params)
    with urllib.request.urlopen(url,timeout=45) as response:
        result=json.load(response)
    if 'error' in result: raise ValueError(str(result['error']))
    return result


def download(bbox=None):
    params=dict(where="LegalStatus = 'Operative' AND RemovedByPlanChangeIdentifier IS NULL",f='json',returnIdsOnly='true')
    if bbox:
        params.update(geometry=','.join(map(str,bbox)),geometryType='esriGeometryEnvelope',
                      inSR='4326',spatialRel='esriSpatialRelIntersects')
    result=request(params)
    ids=sorted(set(result['objectIds']))
    if len(ids)>15000: raise ValueError('unexpected layer size; review source before importing')
    features=[]
    for off in range(0,len(ids),200):
        page=request(dict(objectIds=','.join(map(str,ids[off:off+200])),outFields='*',
                          outSR=4326,returnGeometry='true',f='geojson'))
        if page.get('exceededTransferLimit'): raise ValueError('truncated zone batch')
        features.extend(page['features'])
        print(f'Fetched {len(features)} / {len(ids)} zone features',flush=True)
    returned=[int(f['properties']['DPZoneID']) for f in features]
    if len(returned)!=len(ids) or set(returned)!=set(ids):
        raise ValueError('zone retrieval incomplete or changed during fetch; retry snapshot')
    return dict(type='FeatureCollection',features=features,source_url=CCC,
                fetched_utc=datetime.now(timezone.utc).isoformat())


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',choices=('christchurch','nyc_pluto'),required=True)
    group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--input',type=Path)
    group.add_argument('--download',action='store_true')
    ap.add_argument('--bbox',nargs=4,type=float,metavar=('WEST','SOUTH','EAST','NORTH'))
    ap.add_argument('--release',help='required for local exports; remote snapshots use retrieval date and source hash')
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--raw-out',type=Path,help='retain the unmodified source snapshot for audit/reprocessing')
    args=ap.parse_args()
    if args.download and args.source!='christchurch': ap.error('download currently supports Christchurch only')
    if args.input and not args.release: ap.error('local input requires --release')
    if args.bbox and not (-180<=args.bbox[0]<args.bbox[2]<=180 and -90<=args.bbox[1]<args.bbox[3]<=90):
        ap.error('invalid geographic bounding box')
    data=download(args.bbox) if args.download else json.loads(args.input.read_text(encoding='utf-8-sig'))
    if args.raw_out:
        args.raw_out.parent.mkdir(parents=True,exist_ok=True)
        args.raw_out.write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    source_hash=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
    release=args.release or datetime.now(timezone.utc).strftime('snapshot-%Y%m%d')+'-'+source_hash[:12]
    result=zone_adapters.normalize(data,args.source,release)
    result['source_sha256']=source_hash
    result['bounds_filter']=args.bbox
    args.out.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=args.out.parent,suffix='.json',delete=False) as f:
            json.dump(result,f,separators=(',',':'),allow_nan=False)
            temporary=Path(f.name)
        digest,records,_=zones.load(temporary)
        temporary.replace(args.out)
        print(json.dumps(dict(features=len(records),sha256=digest,release=release,
                              excluded=result['excluded_nonoperative']),indent=2))
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)


if __name__=='__main__': main()
