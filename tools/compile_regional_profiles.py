"""Validate and install the reviewed 64-theme authoring inputs (no network)."""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DETAILS={'sash','shutters','lintels','floor_bands','timber_bands','screens','canopies'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--designs',type=Path,default=ROOT/'build/regional-runtime/designs')
    args=parser.parse_args()
    profiles={};sources={}
    for name in ('americas_oceania','europe_africa','asia'):
        path=args.designs/(name+'.json')
        raw=path.read_bytes(); data=json.loads(raw)
        assert not set(profiles)&set(data),name
        profiles.update(data);sources[name]=hashlib.sha256(raw).hexdigest()
    env_path=ROOT/'server/buildgen/catalog/environments.json'
    env=json.loads(env_path.read_bytes())
    assert set(profiles)==set(env['regions']) and len(profiles)==64
    for key,p in profiles.items():
        for field,minimum,maximum in (('window_width',.8,2.),('bay',1.8,4.5),('sill',.5,1.2),
                                       ('window_height',1.,2.1),('reveal',.04,.2),('frame',.03,.12)):
            assert minimum<=p[field]<=maximum,(key,field,p[field])
        assert p['bay']>p['window_width']+.7,key
        assert 10<=p['pitch'][0]<=p['pitch'][1]<=50,key
        assert set(p['details'])<=DETAILS,key
        assert p['massing_grammar'] in {'timber_veranda','masonry_terrace','render_shutters','arcaded_front',
            'screened_tropical','compact_courtyard','alpine_timber','east_asian_timber','urban_shophouse',
            'panel_modern','arctic_modular','earthen_recess','stone_loggia','brick_pattern'},key
        assert p['opening_pattern'] in ('grouped','vertical','horizontal','regular'),key
        assert p['opening_shape'] in ('rectangular','arched','segmental'),key
        assert .12<=p['facade_depth']<=.45,key
        assert all(v in ('standard','gambrel','mansard','saltbox','shed','broad_eave') and w>0 for v,w in p['roof_variants']),key
        for field,allowed in (('facade',{'brick','stone','wood','render','concrete','metal'}),
                              ('roof',{'metal','tile','slate','shingle','membrane'}),
                              ('roof_shapes',{'flat','gabled','hipped'})):
            assert p[field] and all(v in allowed and isinstance(w,(int,float)) and math.isfinite(w) and w>0
                                    for v,w in p[field]),(key,field)
        for field,palette in [('colours',p['colours']),*p.get('material_colours',{}).items()]:
            assert len(palette)==16,(key,field,'expected 16 wall colours')
            assert all(len(rgb)==3 and all(type(v) in (int,float) and math.isfinite(v) and 0<=v<=1
                                          for v in rgb) for rgb in palette),(key,field)
            assert len({tuple(rgb) for rgb in palette})==16,(key,field,'duplicate wall colours')
        assert len(p['colour_names'])==16 and all(isinstance(n,str) and n.strip() for n in p['colour_names']),key
        assert p['colour_rationale'] and p['palette_interpretation'],key
        for family,palette in p.get('material_colours',{}).items():
            assert len(p['material_colour_names'][family])==len(palette),(key,family)
        for rgb in [p['trim'],p['accent']]:
            assert len(rgb)==3 and all(isinstance(v,(int,float)) and 0<=v<=1 for v in rgb),(key,rgb)
        assert set(p['roof_colours'])=={v for v,w in p['roof']},key
        for palette in p['roof_colours'].values():
            assert 2<=len(palette)<=3,key
            assert all(len(rgb)==3 and all(isinstance(v,(int,float)) and 0<=v<=1 for v in rgb) for rgb in palette),key
        assert p['references'] and all(r.get('image_viewed') is True and r['image_url'].startswith('https://')
                                       and r['observed_features'] for r in p['references']),key
        p['interpretation']='Authored from viewed locality photographs; not a measured prevalence or building-specific style classification.'
    # These route fixtures use actual land/station coordinates, rather than
    # rounded city centres that fall in a harbour or on generalized ice shores.
    profiles['us_southeast']['example'].update(lat=32.790,lon=-79.940)
    profiles['antarctic_stations']['example'].update(lat=-68.5763,lon=77.9688)
    result=dict(schema=1,version='regional-architecture-v4-palettes16',authoring_sha256=sources,
                limits=dict(detail_components_per_building=96,detail_components_per_elevation=24,window_canopies_per_building=16,arched_openings_per_building=32),
                note='64 active parameterized regional grammars with ordinary/local-detail/contemporary expressions and 16 authored wall colours per theme. Expanded palettes are design choices, not surveyed colour prevalence. Photographs are linked as research references and not redistributed assets.',
                profiles=profiles)
    (ROOT/'server/buildgen/catalog/regional_profiles.json').write_text(json.dumps(result,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')
    for key,pack in env['regions'].items():
        pack['status']='active'
        pack['geometry_status']='parameterized_regional_grammar_v3_polished'
        pack['design_status']='photo_informed_authored_defaults'
        pack['selection_scope']='explicit_overlay_then_bundled_geographic_polygons'
        pack['facade']=profiles[key]['facade'];pack['roof']=profiles[key]['roof']
        pack['runtime_profile']='regional_profiles.json#'+key
    env['catalogue_revision']=3
    env['note']='64 active regional themes selected by explicit overlays or bundled geographic polygons. Parameters are authored visual priors; mapped evidence has priority. Advanced heritage forms and unsurveyed local variants remain outside this bounded grammar.'
    env['authoring_contract']['activation']='All 64 themes use a bundled offline polygon map and bounded regional grammar. Further local variants require reference review, geometry checks and game playtesting.'
    env['authoring_contract']['coverage']='Global country/map-unit coverage with province/locality overrides and 500 m unambiguous shoreline tolerance; administrative and authored transitions approximate architectural geography.'
    env_path.write_text(json.dumps(env,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')
    print('Installed and activated 64 photo-informed profiles.')


if __name__=='__main__':main()
