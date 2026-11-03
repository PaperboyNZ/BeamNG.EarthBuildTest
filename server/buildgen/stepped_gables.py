"""Proportion gates for the tall, narrow stepped-gable silhouette."""
import math


def span(footprint):
    if not footprint.is_rectangle():
        return None
    return min(math.dist(a,b) for a,b in zip(footprint.outer,footprint.outer[1:]+footprint.outer[:1]))


def suitable_footprint(footprint):
    width=span(footprint)
    return width is not None and 4. <= width <= 8.


def fits(footprint,kind,variant,rise):
    if kind!='gabled' or variant!='standard' or not suitable_footprint(footprint):
        return False
    # Short wide triangles produced the squat staircase the user rejected.
    # Keep mapped dimensions; omit the ornament if they cannot support it.
    return rise >= 1.65 and .75 <= 2.*rise/span(footprint) <= 1.65


def for_spec(spec):
    from . import roofs
    return bool(spec.inference and 'stepped_gable' in spec.inference.modifiers and
                fits(spec.footprint,spec.roof,roofs.variant(spec),spec.inference.roof_rise))
