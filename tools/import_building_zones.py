"""Normalize a licensed local GeoJSON release using an explicit local codebook.

Run --help. Never guesses a jurisdiction's uses from raw labels. Restart the
server after import: overlays and generated content identities are pinned per run.
"""
import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
from buildgen import zones


def normalize(data, crosswalk, *, field, source, release, lineage, meaning, status):
    if data.get('type') != 'FeatureCollection' or data.get('crs'):
        raise ValueError('input must be RFC 7946 GeoJSON; reproject other CRS before import')
    features=[]
    for feature in data['features']:
        raw=str(feature['properties'][field])
        if raw not in crosswalk:
            raise ValueError(f'unmapped zone code: {raw}')
        features.append(dict(type='Feature',geometry=feature['geometry'],properties=dict(
            source_id=source,release=release,lineage=lineage,raw_code=raw,meaning=meaning,
            status=status,uses=crosswalk[raw])))
    return dict(type='FeatureCollection',features=features)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('geojson',type=Path)
    ap.add_argument('crosswalk',type=Path,help='JSON object: raw code -> list of normalized uses')
    for name in ('field','source','release','lineage'):
        ap.add_argument('--'+name,required=True)
    ap.add_argument('--meaning',choices=('observed','statutory','planned','modelled'),required=True)
    ap.add_argument('--status',choices=('effective','proposed','superseded'),required=True)
    ap.add_argument('--out',type=Path,default=zones.PATH,
                    help='replaces this one pinned catalogue; combine releases before importing')
    args=ap.parse_args()
    result=normalize(json.loads(args.geojson.read_text(encoding='utf-8-sig')),
                     json.loads(args.crosswalk.read_text(encoding='utf-8-sig')),
                     **{key:getattr(args,key) for key in ('field','source','release','lineage','meaning','status')})
    args.out.parent.mkdir(parents=True,exist_ok=True)
    path=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',suffix='.json',dir=args.out.parent,delete=False) as f:
            json.dump(result,f,indent=2)
            path=Path(f.name)
        digest,records,_=zones.load(path)
        path.replace(args.out)
        print(f'Imported {len(records)} features; SHA256 {digest}; restart server to activate')
    finally:
        zones.catalogue.cache_clear()
        if path is not None:
            path.unlink(missing_ok=True)


if __name__=='__main__':
    main()
