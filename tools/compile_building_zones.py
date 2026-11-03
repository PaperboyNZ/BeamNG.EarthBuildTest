"""Compile validated normalized GeoJSON to compact, pickle-free WKB arrays.

Geometry coordinates and properties are retained exactly. This reduces startup
JSON/coordinate allocation in each worker; no boundary simplification is used.
"""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import numpy as np
from shapely import to_wkb
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
from buildgen import zones


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('input',type=Path)
    ap.add_argument('output',type=Path)
    args=ap.parse_args()
    if args.output.suffix!='.npz':ap.error('output must end in .npz')
    data=json.loads(args.input.read_text(encoding='utf-8'))
    _,records,_=zones.load(args.input)
    wkbs=to_wkb([g for g,z in records])
    for f in data['features']:f.pop('geometry',None)
    offsets=np.r_[0,np.cumsum([len(w) for w in wkbs])].astype(np.int64)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile('wb',dir=args.output.parent,suffix='.npz',delete=False) as f:
            temporary=Path(f.name)
            np.savez_compressed(f,schema=np.array(1),metadata=np.array(json.dumps(data,separators=(',',':'))),
                                offsets=offsets,geometry=np.frombuffer(b''.join(wkbs),dtype=np.uint8))
        digest,packed,_=zones.load(temporary)
        if len(packed)!=len(records) or any(a[0].wkb!=b[0].wkb or a[1]!=b[1] for a,b in zip(records,packed)):
            raise ValueError('packed zoning verification failed')
        temporary.replace(args.output)
        print(f'{len(records)} zones; {args.output.stat().st_size} bytes; SHA256 {digest}')
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)


if __name__=='__main__':main()
