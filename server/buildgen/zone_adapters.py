"""Explicit source codebooks; retain provenance and never conflate legal status."""
import json
from pathlib import Path

CAT = Path(__file__).with_name('catalog')


def normalize(data, source, release):
    from shapely.geometry import shape, mapping
    from shapely import make_valid
    if source not in ('christchurch', 'nyc_pluto'):
        raise ValueError('unsupported zone adapter')
    if data.get('type') != 'FeatureCollection' or data.get('crs'):
        raise ValueError('input must be WGS84 RFC 7946 GeoJSON')
    if not release or not isinstance(release,str):
        raise ValueError('release is required')
    table = json.loads((CAT/f'crosswalk_{source}.json').read_text())
    features, excluded, repairs = [], 0, 0
    for feature in data['features']:
        raw = feature['properties']
        if source == 'christchurch':
            if raw.get('LegalStatus') != 'Operative' or raw.get('RemovedByPlanChangeIdentifier'):
                excluded += 1
                continue
            code = str(raw.get('Code',''))
            meaning, lineage = 'statutory', 'christchurch-district-plan'
            source_record = str(raw.get('DPZoneID',feature.get('id','')))
        else:
            fields = {k.lower():v for k,v in raw.items()}
            value = fields.get('landuse')
            code = '' if value is None or str(value).strip()=='' else str(int(value)).zfill(2)
            meaning, lineage = 'observed', 'nyc-mappluto-tax-lots'
            source_record = str(fields.get('bbl',feature.get('id','')))
        if code not in table['codes']:
            raise ValueError(f'unmapped {source} code {code!r}; update the explicit crosswalk')
        if not source_record:
            raise ValueError('zone lacks source feature identity')
        classification = table['codes'][code]
        properties = dict(source_id=table['source'],feature_id=source_record,release=release,lineage=lineage,
                          raw_code=code,meaning=meaning,status='effective',uses=classification['uses'],
                          environment=classification['environment'],region=table['region'],
                          source_url=table['source_url'],raw_attributes=raw)
        geometry = feature['geometry']
        g = shape(geometry)
        if not g.is_valid:
            fixed = make_valid(g)
            if g.area <= 0 or fixed.geom_type not in ('Polygon','MultiPolygon') or \
                    abs(fixed.area-g.area) > g.area*1e-8:
                raise ValueError(f'zone {source_record} requires manual geometry review')
            geometry = mapping(fixed)
            properties['geometry_repair'] = 'make_valid_area_preserved_within_1e-8'
            repairs += 1
        features.append(dict(type='Feature',geometry=geometry,properties=properties))
    return dict(type='FeatureCollection',features=features,excluded_nonoperative=excluded,
                geometry_repairs=repairs,
                attribution='Christchurch City Council District Plan' if source=='christchurch' else
                            'NYC Department of City Planning MapPLUTO')
