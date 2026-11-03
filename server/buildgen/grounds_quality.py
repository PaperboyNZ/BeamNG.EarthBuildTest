"""Independent sidewalks/property-ground quality captured at worker submission.

None is reserved for old callers without the new wire field. Their initial
policy follows the old building setting for compatibility. New connections send
an explicit value; later building quality changes cannot change this policy.
"""
from contextvars import ContextVar
from .quality import NAMES

CURRENT = ContextVar('grounds_quality', default=None)


def current():
    value = CURRENT.get()
    if value is not None:return value
    from .progressive import DETAIL
    value = DETAIL.get()
    return value if value in NAMES else 'medium'


def site_level():
    return {'minimum':-1, 'very_low':0, 'low':1}.get(current(), 2)


def effective(value, generator):
    """Simple ignores saved Advanced choices without overwriting them."""
    return 'minimum' if generator=='legacy' else value


def recipe_identity():
    import sidewalk_outline, sidewalk_rounding
    return current(), sidewalk_outline.REVISION, sidewalk_rounding.REVISION


def run(value, function, *args, **kwargs):
    if value is not None and value not in NAMES:
        raise ValueError('invalid sidewalks/property grounds quality')
    token = CURRENT.set(value)
    try:return function(*args, **kwargs)
    finally:CURRENT.reset(token)
