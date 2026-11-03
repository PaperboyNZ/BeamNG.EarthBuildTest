"""Stable house-style mixtures, separate from geographic/source evidence.

These are visual authoring probabilities, not claims about local prevalence.
One source identity owns one choice across tiles, clipping and representations.
"""
from dataclasses import dataclass
from . import materials


@dataclass(frozen=True, slots=True)
class HouseStyle:
    variant: str = 'unmixed'
    profile: str = ''
    version: int = 1
    alternate: str = ''


HOUSE_CLASSES = frozenset(('', 'house', 'detached', 'semidetached_house',
                           'bungalow', 'residential', 'terrace', 'town_house', 'cabin'))

# Five shared families worldwide. The first retains the earlier generic house
# composition; the others vary its cladding and fitted openings without adding
# a second set of 64 geographic recipes or new textures/physical assemblies.
CONTEMPORARY = {
    'suburban': None,
    'timber': dict(facade='wood', window_width=1.65, bay=3.6, window_height=1.40),
    'brick': dict(facade='brick', window_width=1.70, bay=3.7, window_height=1.35),
    'rendered': dict(facade='render', window_width=1.85, bay=3.8, window_height=1.50),
    'mixed_infill': dict(facade='render', window_width=1.75, bay=3.7, window_height=1.45,
                         base_material='brick', upper_material='render'),
}


def contemporary_profile(style):
    row = CONTEMPORARY.get(style.alternate) if style.variant == 'contemporary' else None
    if row is None:
        return None
    return dict(dict(massing_grammar='plain_modern', opening_pattern='regular',
                     sill=.85, frame=.07, reveal=.08, facade_depth=.08,
                     trim=(.84,.85,.83), accent=(.32,.35,.36),
                     colours=((.91,.89,.84),), details=[]), **row)


def facade_prior(style, fallback):
    row = CONTEMPORARY.get(style.alternate) if style.variant == 'contemporary' else None
    return row['facade'] if row else fallback


def select(region, identity, use, cls, floors, height, area, part=False):
    from . import regional_architecture as regional
    if (identity is None or part or use not in ('residential', 'unknown')
            or cls not in HOUSE_CLASSES or floors > 3 or height > 15. or area > 500.
            or regional.profile(region) is None):
        return HouseStyle('unmixed', region)
    roll = materials.unit(identity, 'house-style-mixture-v1')
    if roll < .70:
        return HouseStyle('regional', region)
    if roll < .90:
        # The pre-global-regional v2 house recipe: broader punched windows,
        # plain cladding, varied brick/render/timber and ordinary fitted roofs.
        alternate = materials.choose(identity, 'house-contemporary-family-v1',
                                     tuple((key, 3 if key == 'suburban' else 1) for key in CONTEMPORARY))
        return HouseStyle('contemporary', '', alternate=alternate)
    choices = sorted(k for k in regional.catalogue() if k != region and regional.profile(k))
    if not choices:
        return HouseStyle('regional', region)
    index = min(int(materials.unit(identity, 'house-global-style-v1')*len(choices)), len(choices)-1)
    return HouseStyle('global', choices[index])


def profile_region(resolution):
    return resolution.house_style.profile if resolution.house_style.variant != 'unmixed' \
        else resolution.selection.environment.region


def broad_palette(identity, channel):
    """Keep local paint dominant while restoring the broader material palette."""
    return materials.unit(identity, ('house-colour-range-v1', channel)) >= .65
