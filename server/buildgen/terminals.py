"""Conservative airport hall facades on the shared closed-shell compiler.

Only retained class/subtype evidence activates this adapter. Names establish no
transport mode; no gates, airside boundaries, roads or passenger interiors arise.
"""
import math

from . import materials, programme as shared_programme

AIR = frozenset(('airport_terminal', 'airport_concourse'))
FREIGHT = frozenset(('freight_terminal', 'cargo_terminal', 'freight_station'))
TERMINAL = AIR | FREIGHT | frozenset(('terminal', 'concourse', 'passenger_terminal',
                                      'bus_station', 'ferry_terminal', 'train_station'))
MAX_OPENINGS = 96


def classify(attrs, footprint):
    """Return detached plain metadata, or None for an unrelated building."""
    import buildings as b
    name = str(attrs.get('name') or '').lower()
    source = attrs.get('_planning_footprint') or footprint
    if any(attrs.get(k) for k in ('bridge_part', 'bridge_pier', 'bridge_masonry', 'ship', 'pier', 'garage')) \
            or str(attrs.get('class') or '').lower() in (*b.BRIDGE_CLASSES, *b.CHURCH_CLASSES,
                   'parking', 'parking_garage', 'bridge', 'ship', 'pier', 'toll_booth') \
            or 'parking garage' in name or ('garage' in name and footprint.area > 800):
        return None
    if attrs.get('roof_shape') == 'pyramidal' and footprint.area >= b.PYRAMID_MIN_M2:
        return None
    tags = {str(attrs.get(k) or '').strip().lower() for k in ('class', 'subtype')}
    keyword = any(v in name for v in ('terminal', 'concourse'))
    if not tags.intersection(TERMINAL) and not keyword:
        return None
    result = dict(kind='terminal', family=None, accepted=False, route='ordinary',
                  transport_mode='unknown', evidence='class_subtype', diagnostics=())
    if tags & FREIGHT:
        result['diagnostics'] = ('freight_uses_commercial_shell',)
        return result
    if not tags & AIR:
        result['diagnostics'] = (('terminal_mode_not_confirmed',) if tags & TERMINAL else
                                 ('name_keyword_does_not_confirm_terminal',))
        return result
    if tags & (TERMINAL - AIR) - {'terminal', 'concourse', 'passenger_terminal'}:
        result['diagnostics'] = ('conflicting_terminal_mode',)
        return result
    _, _, hl, hw = b.oriented_box(source.outer)
    roof = str(attrs.get('roof_shape') or '').strip().lower()
    if roof and roof not in ('flat', 'gabled', 'hipped'):
        result['diagnostics'] = ('terminal_special_roof_shell_fallback',)
        return result
    if attrs.get('_part') or attrs.get('parent_id'):
        result['diagnostics'] = ('terminal_part_assembly_deferred',)
        return result
    if source.area > 10000 or sum(map(len, (source.outer, *source.holes))) > 256:
        result['diagnostics'] = ('terminal_large_assembly_deferred',)
        return result
    for key, limit in (('height', 40), ('num_floors', 6)):
        try:
            if float(attrs.get(key) or 0) > limit:
                result['diagnostics'] = ('terminal_large_assembly_deferred',)
                return result
        except (ValueError, TypeError, OverflowError):
            pass  # the shared evidence resolver diagnoses invalid dimensions
    family = ('terminal_linear_concourse' if 'airport_concourse' in tags or
              ('concourse' in tags and hl >= hw * 2.5) else 'terminal_regional_hall')
    result.update(family=family, accepted=True, transport_mode='air',
                  diagnostics=('terminal_public_front_is_road_inferred',
                               'terminal_transport_side_unknown'))
    return result


def attach(spec, record):
    spec.terminal = record
    if record is None:
        return
    spec.diagnostics = tuple(spec.diagnostics or ()) + tuple(record['diagnostics'])
    if record['accepted']:
        spec.shop = spec.porch = spec.steeple = False
        spec.windows = True
        spec.plain = False


def openings(spec, boundary, edge, length, base, high, reserved, programme=None):
    """Fit bounded glazing groups around the shared entrance reservation."""
    record = getattr(spec, 'terminal', None)
    if not record or not record['accepted']:
        return None
    if programme is False:return None
    try:
        programme=programme if programme is not None else shared_programme.derive(spec)
        run=programme.run(boundary,edge)
    except ValueError:
        return None  # optional composition cannot abort the physical source shell
    from .facades import Opening
    result = list(reserved)
    if boundary or length < 2.0:
        return tuple(result), 'terminal_opaque'
    whole_run=math.isclose(length,run.length,abs_tol=1e-7)
    front = run.member(spec.front) is not None and spec.door is not None
    linear = record['family'] == 'terminal_linear_concourse'
    budget = max(len(reserved), MAX_OPENINGS // len(programme.runs))
    lengths = [candidate.length for candidate in programme.runs if candidate.boundary==0]
    long_side = run.length >= max(lengths) * .7
    # Arrival is only the existing road-inferred front. Other long elevations
    # have neutral hall glazing, never invented gate or boarding interfaces.
    role = 'terminal_public' if front else 'terminal_hall' if linear and long_side else 'terminal_service'
    for datum in programme.datums[:6]:
        floor=datum.index
        if len(result) >= budget:
            break
        z = datum.bottom
        sill = .45 if front else 1.0 if role == 'terminal_hall' else max(1.5, datum.height * .55)
        top = min(spec.height - .3, datum.top - .45, z + sill + (3.1 if front else 2.3))
        bottom = z + sill
        if top - bottom < .65:
            continue
        bay = (4.2 if linear else 5.0) + shared_programme.legacy_seed(spec,'structure','terminal-bay') * 1.2
        width=3.7 if front or role=='terminal_hall' else 1.8
        offset=0. if whole_run else run.member(edge).start
        relevant=tuple((op.left+offset,op.right+offset) for op in reserved if op.bottom<top+.35 and op.top>bottom-.35)
        if not whole_run and spec.door and spec.door[0]!=edge:
            door_member=run.member(spec.door[0])
            door_z=spec.access.door_z-base if spec.access is not None else high-base
            if door_member is not None and door_z<top+.35 and door_z+2.25>bottom-.35:
                centre=door_member.start+spec.door[1]
                relevant+=((centre-.625,centre+.625),)
        grid=shared_programme.fit_grid(run.length,bay,width,margin=.8,reserved=relevant,gap=.8,
                                      max_bays=24,mode='centered',allow_single=False,
                                      reserved_mode='omit',reservation_gap=.35)
        if not whole_run:grid=shared_programme.project_grid(grid,run,edge)
        for module in grid.bays:
            if len(result) >= budget:
                break
            if role == 'terminal_service' and module.index % 3 != 1:
                continue
            op = Opening('office', floor, module.left,module.right, bottom, top,
                         3 if front else 2, 0)
            if any(op.overlaps(other, .35) for other in result):
                continue
            result.append(op)
    return tuple(sorted(result, key=lambda o: (o.floor, o.left))), role
