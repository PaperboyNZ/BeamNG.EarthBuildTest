"""User-authored regional vocabulary with stable, evidence-aware selection."""
from functools import lru_cache
import json
from pathlib import Path
from . import materials


@lru_cache(maxsize=1)
def catalogue():
    return json.loads(Path(__file__).with_name('catalog').joinpath('architectural_modifiers.json').read_text())['modifiers']


def eligible(region, context):
    from .regional_geography import locate
    location = locate(*context.location) if context.location else None
    rural = any(k in ('rural', 'rural_residential', 'farmland', 'farmyard', 'agriculture') and v >= .6
                for k, v in context.land_use) or any(z.environment in ('rural', 'rural_residential')
                                                    and z.overlap >= .6 for z in context.zones)
    return tuple(key for key, row in catalogue().items() if region in row['regions']
                 and (not row.get('rural_only') or rural)
                 and (not row.get('countries') or location is None or location.theme != region
                      or location.jurisdiction in row['countries'])
                 and (location is None or location.locality not in row.get('localities_excluded', ())))


def select(region, context, identity, use, floors, area, part=False):
    if part or use not in ('residential', 'unknown', 'mixed') or floors > 3 or not 30. <= area <= 650.:
        return ()
    rows = catalogue()
    chosen = [key for key in eligible(region, context)
              if materials.unit(identity, ('architecture-modifier-v1', key)) < rows[key]['chance']]
    # One covering and one wall construction, never mutually contradictory coats.
    for family in ('roof', 'facade'):
        candidates = [key for key in chosen if rows[key].get('family') == family]
        if len(candidates) > 1:
            winner = min(candidates, key=lambda key: materials.unit(identity, ('architecture-material-v1', key)))
            chosen = [key for key in chosen if key not in candidates or key == winner]
    return tuple(sorted(chosen))


def material(selected, family, fallback):
    return next((catalogue()[key]['material'] for key in selected
                 if catalogue()[key].get('family') == family), fallback)


def has(spec, key):
    return bool(spec.inference and key in spec.inference.modifiers and not
                (spec.plain or spec.church or spec.terminal or spec.city or spec.deck))


def profile(spec, row):
    if row is None:
        return row
    row = dict(row)
    row['details'] = [x for x in row['details'] if x != 'shutters']
    if has(spec, 'shutters'):
        row['details'].append('shutters')
    return row
