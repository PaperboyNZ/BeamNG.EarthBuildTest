"""Visual priors for unmapped roofs, shared by all v2 house styles.

These bounds are authoring choices, not surveyed roof measurements. Explicit
roof heights bypass them; a mapped total height remains the final envelope.
"""
import math

from . import roofs


def inferred_rise(footprint, kind, variant, half_width, pitch, height, fixed_top,
                  domestic):
    roof = roofs.envelope(footprint, kind, variant)
    # Only emitted planes count: cross-gables also contain inactive end planes.
    gradient = max(math.hypot(*roof.planes[i][:2])
                   for i in set(roof.triangle_planes)) / roof.peak
    # A courtyard or joined wing can have a much shorter run than the overall
    # bounding box. Using the latter stretches the solved slopes vertically.
    run = 1. / gradient if variant == 'standard' else half_width
    if variant == 'shed':
        # One slope crosses the full width. Keep its high wall subordinate.
        run = 1. / gradient
        pitch = min(pitch * .5, 14.)
    rise = run * math.tan(math.radians(pitch))
    if domestic:
        broken = variant in ('gambrel', 'mansard')
        ratio, maximum = (.75, 3.6) if broken else (.60, 3.)
        body_limit = height / (1. + ratio) if fixed_top else height
        rise = min(rise, ratio * body_limit, maximum,
                   math.tan(math.radians(60. if broken else 42.)) / gradient)
    return rise
