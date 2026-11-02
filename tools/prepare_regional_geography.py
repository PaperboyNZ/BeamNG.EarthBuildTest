"""Compile pinned Natural Earth polygons into offline architectural theme coverage.

Input: Natural Earth vector v5.1.2 geojson/ne_10m_admin_{0_map_units,1_states_provinces}.geojson.
The upstream repository tag is pinned; source hashes are retained in the output.
Administrative boundaries are routing evidence, not a claim of cultural uniformity.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from shapely.geometry import shape, mapping, box, Point
from shapely.affinity import scale
from shapely import make_valid

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/'
COUNTRIES = {
    'us_northeast': 'USA',
    'canada_atlantic': 'CAN SPM',
    'arctic_north_america': 'GRL',
    'latin_american_local': 'MEX',
    'caribbean_creole': 'CUB HTI DOM JAM PRI BHS BMU TCA CUW ABW NLY TTO GRD VCT BRB LCA MTQ DMA GLP MSR ACA ACB ATG KNA VIR BLM AIA VGB CYM MAF SXM USG BQI BJN SER',
    'central_america': 'BLZ GTM HND SLV NIC CRI PAN',
    'andean_highlands': 'COL ECU PER BOL VEN',
    'brazil_coastal': 'BRA',
    'amazon_guianas': 'GUY SUR GUF',
    'southern_cone': 'ARG URY PRY BRI FLK',
    'chile_pacific': 'CHL SPI',
    'eu_atlantic': 'GBR ENG WLS SCT NIR IRL JEY GGY IMN PAZ PMD',
    'eu_mediterranean': 'ESP PRT PRX AND GIB',
    'nordic_cold': 'NOR NOW SWE FIN DNK ISL FRO ALD NJM NSV',
    'france_regional': 'FRA FXX MCO',
    'low_countries': 'NLD NLX BEL BFR BWR BCR LUX',
    'central_europe': 'DEU CZE POL SVK AUT CHE',
    'alpine': 'LIE',
    'italy_regional': 'ITA SMR VAT MLT',
    'adriatic_balkans': 'SVN HRV BIH BHF BIS BHB SRB SRS SRV MNE KOS ALB MKD',
    'aegean': 'GRC CYP CYN CNM ESB WSB',
    'eastern_europe': 'EST LVA LTU BLR UKR MDA ROU BGR HUN',
    'russia_north': 'RUS',
    'african_local': 'SEN GMB GNB GIN SLE LBR CIV GHA TGO BEN NGA CPV',
    'maghreb': 'MAR SAH DZA TUN LBY',
    'sahel': 'MRT MLI BFA NER TCD',
    'nile_valley': 'EGY SDN BRT',
    'horn_africa': 'ETH ERI DJI SOM SOP SOX SOL',
    'swahili_east_africa': 'KEN TZA TZZ UGA RWA BDI',
    'central_africa': 'CMR CAF SSD SDS GNQ GAB COG COD STP',
    'southern_africa': 'AGO ZMB MWI MOZ ZWE BWA NAM ZAF LSO SWZ SHN',
    'indian_ocean_africa': 'MDG COM MYT MUS REU SYC',
    'arid_warm': 'SAU ARE OMN YEM QAT BHR KWT',
    'levant': 'LBN SYR SYX SYU JOR ISR PSX PSE GAZ WEB',
    'anatolia_caucasus': 'TUR ARM GEO GEG GEA AZE',
    'iran_plateau': 'IRN AFG',
    'mesopotamia': 'IRQ IRR IRK',
    'central_asia_oases': 'UZB TKM TJK',
    'central_asia_steppe': 'KAZ KGZ MNG KAB',
    'indus_gangetic': 'PAK IND',
    'bengal_delta': 'BGD',
    'himalayan': 'NPL BTN KAS',
    'sri_lanka_maldives': 'LKA MDV IOT',
    'jp_temperate': 'JPN',
    'china_north': 'CHN',
    'china_south': 'HKG MAC TWN PFA',
    'korea': 'KOR PRK KNX KNZ',
    'tropical_humid': 'MYS SGP BRN CCK',
    'mainland_southeast_asia': 'MMR THA LAO KHM VNM',
    'indonesian_archipelago': 'IDN TLS CXR',
    'philippines': 'PHL SCR PGA',
    'nz_temperate': 'NZL NFK',
    'au_southeast': 'AUS',
    'pacific_islands': 'PNG PNX PNB SLB VUT NCL FJI WSM ASM TON TUV NIU COK TKL WLF PYF PCN KIR MHL FSM NRU PLW GUM MNP JQI CSI DQI FQI HQI WQI MQI CLP ATC LQI KQI',
    'antarctic_stations': 'ATA ATF HMD SGS BVT',
}
DEFAULTS = {code: region for region, codes in COUNTRIES.items() for code in codes.split()}
OVERRIDES = {
    'us_northeast': 'US-ME US-NH US-VT US-MA US-RI US-CT US-NY US-NJ US-PA US-DE US-MD US-DC',
    'us_southeast': 'US-VA US-WV US-NC US-SC US-GA US-FL US-AL US-MS US-LA US-AR US-TN US-KY US-TX',
    'us_midwest': 'US-OH US-MI US-IN US-IL US-WI US-MN US-IA US-MO US-ND US-SD US-NE US-KS US-OK US-MT US-ID US-WY US-CO',
    'us_southwest': 'US-AZ US-NM US-NV US-UT',
    'us_pacific': 'US-CA US-OR US-WA',
    'arctic_north_america': 'US-AK CA-YT CA-NT CA-NU',
    'pacific_islands': 'US-HI',
    'canada_prairie': 'CA-AB CA-SK CA-MB',
    'canada_pacific': 'CA-BC',
    'amazon_guianas': 'BR-AM BR-AC BR-RO BR-RR BR-AP BR-PA CO-AMA CO-PUT CO-CAQ CO-GUV CO-GUA CO-VAU CO-VID PE-LOR PE-MDD PE-UCA PE-SAM EC-U EC-D EC-Y EC-S EC-Z EC-N BO-N BO-B BO-S',
    'caribbean_creole': 'CO-LAG CO-CES CO-COR CO-SUC CO-BOL CO-ATL CO-MAG CO-SAP',
    'southern_cone': 'BR-RS BR-SC BR-PR',
    'alpine': 'CH-VS CH-TI CH-GR CH-UR CH-SZ CH-GL CH-NW CH-OW AT-8 AT-7 AT-5 AT-2 IT-23 IT-32 FR-73 FR-74 FR-05',
    'china_south': 'CN-YN CN-GX CN-GD CN-HI CN-FJ CN-ZJ CN-SH CN-JS CN-SC CN-CQ CN-GZ CN-HN CN-JX CN-HB CN-AH',
    'tibetan_plateau': 'CN-XZ CN-QH',
    'central_asia_oases': 'CN-XJ',
    'central_asia_steppe': 'CN-NM',
    'himalayan': 'IN-LA IN-AR IN-SK IN-UT IN-HP IN-JK PK-GB PK-JK',
    'bengal_delta': 'IN-WB IN-AS IN-NL IN-MN IN-MZ IN-TR IN-ML',
    'india_peninsular': 'IN-AP IN-OR IN-DH IN-MH IN-GA IN-KA IN-KL IN-PY IN-TN IN-LD IN-AN IN-JH IN-MP IN-CT IN-TG',
    'au_tropical_arid': 'AU-NT AU-QLD',
    'antarctic_stations': 'AU-X03~',
    'sahel': 'NG-SO NG-KE NG-ZA NG-KT NG-KN NG-JI NG-YO NG-BO NG-BA NG-GO',
}
BY_ISO = {code: region for region,codes in OVERRIDES.items() for code in codes.split()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, default=ROOT/'build/regional-runtime/downloads')
    parser.add_argument('--out', type=Path, default=ROOT/'server/buildgen/catalog/regional_geography.json')
    args = parser.parse_args()
    regions = json.loads((ROOT/'server/buildgen/catalog/environments.json').read_text())['regions']
    records, sources, unresolved = [], [], []
    def add(geometry, theme, name, priority, source, jurisdiction):
        if not geometry.is_valid:
            geometry = make_valid(geometry)
        geometry = geometry.simplify(.001, preserve_topology=True)
        if geometry.is_empty:
            return
        if geometry.geom_type == 'GeometryCollection':
            for part in geometry.geoms:
                if part.geom_type in ('Polygon','MultiPolygon'):
                    add(part,theme,name,priority,source,jurisdiction)
            return
        assert theme in regions, (theme,name)
        records.append(dict(type='Feature', properties=dict(theme=theme,name=name,priority=priority,source=source,jurisdiction=jurisdiction),
                            geometry=mapping(geometry)))
    for level,filename in ((0,'admin0'),(1,'admin1')):
        path=args.inputs/(filename+'.geojson')
        content=path.read_bytes()
        sources.append(dict(file=filename, sha256=hashlib.sha256(content).hexdigest(),
                            url=BASE+('ne_10m_admin_0_map_units.geojson' if level==0 else 'ne_10m_admin_1_states_provinces.geojson')))
        for feature in json.loads(content)['features']:
            p=feature['properties']
            if level==0:
                code=p['GU_A3']; name=p['GEOUNIT']
                theme=DEFAULTS.get(code) or DEFAULTS.get(p['ADM0_A3'])
                if theme is None:
                    unresolved.append((code,name)); continue
                add(shape(feature['geometry']),theme,name,0,'Natural Earth '+code,p['ADM0_A3'])
            else:
                iso=p['iso_3166_2']; name=p['name'] or p['adm1_code']
                theme=BY_ISO.get(iso)
                if theme:
                    add(shape(feature['geometry']),theme,name,10,'Natural Earth '+iso,p['adm0_a3'])
                # Authored climatic transition masks are clipped to real admin
                # polygons. They are not independent country bounding boxes.
                masks = {
                    'CA-BC': [('canada_prairie',box(-122,48,-110,61),'interior BC')],
                    'AU-WA': [('au_southeast',box(110,-36,130,-29),'southwest WA'),('au_tropical_arid',box(110,-29,130,-10),'northern WA')],
                    'AU-SA': [('au_tropical_arid',box(125,-31,142,-25),'inland SA')],
                    'US-TX': [('us_southwest',box(-108,25,-101,37),'west Texas')],
                    'US-CA': [('us_southwest',box(-117.8,32,-114,36),'California desert')],
                }.get(iso,())
                for theme,mask,label in masks:
                    add(shape(feature['geometry']).intersection(mask),theme,label,20,'Natural Earth '+iso+'; authored transition',p['adm0_a3'])
    # Natural Earth's generalized ice coastline omits this mapped station's
    # rocky peninsula. A documented locality patch is narrower than inflating
    # every world's coastline to make one test pass.
    lat,lon=-68.5763,77.9688
    patch=scale(Point(lon,lat).buffer(1.,quad_segs=16),
                xfact=1500/(111320*math.cos(math.radians(lat))),yfact=1500/111320,origin=(lon,lat))
    add(patch,'antarctic_stations','Davis research station locality',30,
        'https://www.antarctica.gov.au/antarctic-operations/stations-and-field-locations/davis/','ATA')
    assert not unresolved, unresolved
    assert {r['properties']['theme'] for r in records} == set(regions), set(regions)-{r['properties']['theme'] for r in records}
    result=dict(type='FeatureCollection', schema=1, source='Natural Earth vector v5.1.2',
                licence='Public domain', attribution='Made with Natural Earth',
                licence_url='https://www.naturalearthdata.com/about/terms-of-use/',
                sources=sources, simplification_degrees=.001,
                note='Authored architectural routing; administrative and climate transitions are approximate, not cultural borders. Point lookup is offline; no nearest-country airport heuristic.',
                features=records)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,separators=(',',':'),ensure_ascii=True)+'\n',encoding='utf-8')
    print(json.dumps(dict(features=len(records),themes=len(regions),bytes=args.out.stat().st_size,
                         assignments=Counter(r['properties']['theme'] for r in records)),indent=2))

if __name__=='__main__':main()
