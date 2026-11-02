"""Visual quality ceilings; physical plans never depend on these profiles.

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
        return NAMES[min(self.rank, 1)]


NAMES = ('very_low', 'low', 'medium', 'high', 'very_high', 'ultra')
PROFILES = {p.name:p for p in (
    Profile('very_low', 0, 150., 16., 8., 6., .30, 12, 8192),
    Profile('low', 1, 200., 18., 9., 5., .25, 10, 7168),
    Profile('medium', 2, 250., 20., 10., 4., .20, 8, 6144),
    Profile('high', 3, 350., 22., 12., 3., .16, 6, 4096),
    Profile('very_high', 4, 500., 24., 13., 3., .14, 4, 3072),
    Profile('ultra', 5, 640., 26., 14., 2., .12, 2, 2048),
)}
WORKER_VALUES = NAMES + ('full', 'lite')


def import_vertices(stage=2):
    """Cheap coverage imports broadly; increasingly detailed imports get smaller."""
    if stage == 0:return 20000
    if stage == 1:return 18000
    return (20000,18000,16000,12000,10000,8000)[current().rank]


def current():
    from .progressive import DETAIL
    # Legacy lite is a representation flag, not a new geometry recipe.
    return PROFILES.get(DETAIL.get(), PROFILES['ultra'])


def rank(value):
    if value == 'full':return 5
    if value == 'lite':return 1
    return PROFILES[value].rank if isinstance(value,str) and value in PROFILES else -1


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
    if not getattr(conn,'building_adaptive',True):return name
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
