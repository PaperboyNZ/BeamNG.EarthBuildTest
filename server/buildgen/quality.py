"""Visual ceilings and optional site policies; architectural identity is stable.

The old full/lite worker values remain valid for older clients. Current() is
job-local (ContextVar), so concurrent tiles cannot change each other's quality.
"""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Profile:
    name: str
    rank: int
    reach: float
    fast_enter: float
    fast_exit: float
    settle_s: float
    feature_m: float
    group_size: int
    group_cost: int

    @property
    def fallback(self):
        return self.name if self.rank <= 1 else 'low'


NAMES = ('minimum', 'very_low', 'low', 'medium', 'high', 'very_high', 'ultra')
PROFILES = {p.name:p for p in (
    Profile('minimum', -1, 150., 16., 8., 6., .5, 12, 8192),
    Profile('very_low', 0, 150., 16., 8., 6., .30, 12, 8192),
    Profile('low', 1, 200., 18., 9., 5., .25, 10, 7168),
    Profile('medium', 2, 250., 20., 10., 4., .20, 8, 6144),
    Profile('high', 3, 350., 22., 12., 3., .16, 6, 4096),
    Profile('very_high', 4, 500., 24., 13., 3., .14, 4, 3072),
    Profile('ultra', 5, 640., 26., 14., 2., .12, 2, 2048),
)}
WORKER_VALUES = NAMES + ('full', 'lite')


def cheap_planning():
    """Low ceilings bound inference as well as the final mesh.

    Legacy 'lite' is only a representation of a previously accepted plan.
    It must not change architectural evidence used by distant/high-tier jobs.
    """
    from .progressive import DETAIL
    return DETAIL.get() in ('minimum', 'very_low', 'low')


def import_vertices(stage=2):
    """Cheap coverage imports broadly; increasingly detailed imports get smaller."""
    if current().name == 'minimum':return 20000
    if stage == 0:return 20000
    if stage == 1:return 18000
    return (60000,40000,16000,12000,10000,8000)[current().rank]


def site_level():
    """Accepted physical policy: essential entrances, paths, or complete sites.

    Separate product addresses force a full safe rebuild across policy changes.
    Visual detail changes within the complete-site levels reuse physical output.
    """
    from .grounds_quality import site_level as policy
    return policy()


def current():
    from .progressive import DETAIL
    # Legacy lite is a representation flag, not a new geometry recipe.
    return PROFILES.get(DETAIL.get(), PROFILES['ultra'])


def run(detail, function, *args, **kwargs):
    """Carry a captured distant quality into a worker without leaking context."""
    from .progressive import DETAIL
    token=DETAIL.set(detail if detail in WORKER_VALUES else 'full')
    try:return function(*args, **kwargs)
    finally:DETAIL.reset(token)


def rank(value):
    if value == 'full':return 5
    if value == 'lite':return 1
    return PROFILES[value].rank if isinstance(value,str) and value in PROFILES else -2


def needs_rebuild(existing, target, ceiling):
    """Automatic pressure never destroys completed detail; an explicit lower
    ceiling does replace visuals. Later pressure recovery can then deepen them.
    """
    old, wanted, maximum = rank(existing), rank(target), rank(ceiling)
    return old < wanted or old > maximum


def adaptive_target(tracker, conn, speed, *, busy=False, now=0., free_camera=False):
    """Bound optional CPU work with speed hysteresis and sustained recovery.

    The shared client frame governor still prices and limits every mesh import.
    Busy means outstanding physical coverage or stalled workers, not merely an
    optional upgrade in flight (which would otherwise cause oscillation).
    """
    name=getattr(conn,'building_quality','full')
    p=PROFILES[name]
    # Every named mode owns its pressure policy. The retired independent toggle
    # must not pin expensive generation when restored from an older settings file.
    if name == 'minimum':return name
    if getattr(tracker,'quality_ceiling',None)!=name:
        tracker.quality_ceiling=name
        tracker.quality_fast=False
        tracker.quality_recover_at=0.
    if speed>=p.fast_enter:tracker.quality_fast=True
    elif speed<=p.fast_exit:tracker.quality_fast=False
    pressured=busy or (tracker.quality_fast and not free_camera)
    if pressured:tracker.quality_recover_at=now+p.settle_s
    if pressured or now<getattr(tracker,'quality_recover_at',0.):return p.fallback
    return name
