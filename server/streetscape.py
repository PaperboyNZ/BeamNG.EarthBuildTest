"""Small regional roadside palette; authored defaults, never survey evidence.

Uses the existing native bevel sweep and materials. Crossfall stays shared with
access planners; only the upstand changes. No per-building random curb styles.
"""
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Style:
    height: float
    gutter: float
    verge: bool = False
    pavers: bool = False


STYLES = {
    'concrete_channel': Style(.15, .50, True),
    'precast_channel': Style(.15, .45, True),
    'compact_precast': Style(.125, .30),
    'paved_edge': Style(.12, .25, False, True),
    'cold_climate': Style(.16, .35),
    'deep_channel': Style(.18, .55),
}
GROUPS = {
    'concrete_channel': 'us_northeast us_southeast us_midwest us_southwest us_pacific canada_atlantic canada_prairie canada_pacific latin_american_local central_america southern_cone chile_pacific',
    'precast_channel': 'nz_temperate au_southeast au_tropical_arid southern_africa',
    'compact_precast': 'eu_atlantic france_regional central_europe alpine eastern_europe jp_temperate korea china_north anatolia_caucasus iran_plateau central_asia_steppe',
    'paved_edge': 'low_countries eu_mediterranean italy_regional adriatic_balkans aegean maghreb arid_warm levant nile_valley mesopotamia central_asia_oases',
    'cold_climate': 'arctic_north_america antarctic_stations nordic_cold russia_north andean_highlands himalayan tibetan_plateau',
    'deep_channel': 'caribbean_creole brazil_coastal amazon_guianas pacific_islands african_local sahel horn_africa swahili_east_africa central_africa indian_ocean_africa indus_gangetic india_peninsular bengal_delta sri_lanka_maldives china_south tropical_humid mainland_southeast_asia indonesian_archipelago philippines',
}
THEMES = {theme: name for name, themes in GROUPS.items() for theme in themes.split()}
COUNTRIES = {**dict.fromkeys(('US', 'CA'), 'concrete_channel'),
             **dict.fromkeys(('NZ', 'AU', 'ZA'), 'precast_channel'),
             **dict.fromkeys(('GB', 'IE', 'FR', 'DE', 'AT', 'CH', 'JP', 'KR'), 'compact_precast'),
             **dict.fromkeys(('NL', 'BE', 'IT', 'ES', 'PT', 'GR'), 'paved_edge'),
             **dict.fromkeys(('NO', 'SE', 'FI', 'IS'), 'cold_climate'),
             **dict.fromkeys(('SG', 'MY', 'ID', 'PH', 'TH', 'VN', 'IN', 'BD', 'LK', 'BR', 'FJ'), 'deep_channel')}


def for_country(country):
    return STYLES[COUNTRIES.get(str(country or '').upper(), 'concrete_channel')]


def annotate(walks, frame, country=None, road_classes=None, source_locations=None):
    """Persist styles with source walks so rebased skins use identical profiles."""
    from buildgen.regional_geography import locate
    road_classes = road_classes or {}
    source_locations = source_locations or {}
    for walk in walks:
        points = np.asarray(walk['corner']['arc'] if 'corner' in walk else walk['pts'])
        location = source_locations.get(walk.get('fid'))
        if location is None:
            point = points[len(points)//2]
            lat, lon, _ = frame.enu_to_geodetic(float(point[0]), float(point[1]), 0.)
        else:
            lat, lon = location
        theme = locate(float(lat), float(lon)).theme
        name = THEMES.get(theme,
                          COUNTRIES.get(str(country or '').upper(), 'concrete_channel'))
        style = STYLES[name]
        walk['curb_style'] = name
        walk['curb_h'] = style.height
        # Road ribbons select by country before the walk exists. Keep grates
        # centred inside that exact same gutter even at a theme boundary.
        walk['gutter_w'] = for_country(country).gutter
        # Preserve a continuous >=1.5 m pedestrian strip. Only local streets
        # get a planted strip; corners, medians and narrow paths remain paved.
        walk['verge'] = bool(style.verge and not walk.get('median') and 'corner' not in walk
                             and walk.get('w', 2.5) >= 2.4
                             and road_classes.get(walk.get('fid')) in ('residential', 'living_street'))
        paved = style.pavers and not walk.get('median')
        # Red herringbone is characteristic of the low-countries palette;
        # Mediterranean and dry-region paved edges use the stock stone tiles.
        brick = theme == 'low_countries' or (not theme and str(country or '').upper() in ('NL', 'BE'))
        walk['pavement'] = ('brick' if brick else 'stone') if paved else 'slab'
        walk['brick'] = walk['pavement'] == 'brick'
