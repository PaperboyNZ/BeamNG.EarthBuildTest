"""Sparse-data commercial/industrial architecture, without inferred businesses.

Measured envelopes and observed neighbours weight compatible compositions.
The road-facing run is fitted later, so a long footprint never implies that its
longest wall faces the street. All apertures use the shared clearance/terrain
resolver and the same near/middle layout. No inferred truck yards or extra routes.
"""
import math

from . import materials

COMMERCIAL = ('ci_form_glazed_pavilion', 'ci_form_display_hall',
              'ci_form_pier_frontage', 'ci_form_ribbon_block')
INDUSTRIAL = ('ci_form_service_hall', 'ci_form_clerestory_hall',
              'ci_form_glazed_workhall', 'ci_form_industrial_grid')
IDS = frozenset(COMMERCIAL + INDUSTRIAL)
BROAD_CLASSES = {'', 'yes', 'building', 'commercial', 'industrial',
                 'factory', 'manufacture', 'manufacturing'}


def weights(use, classes, footprint, floors, body_height=None, context=None):
    if use not in ('commercial', 'industrial') or any(c not in BROAD_CLASSES for c in classes):
        return {}, ()
    shape = footprint.shape()
    corners = tuple(shape.minimum_rotated_rectangle.exterior.coords)
    sides = sorted(math.dist(a,b) for a,b in zip(corners,corners[1:]))
    short, long = sides[0], sides[-1]
    aspect = long / max(short, .01)
    area = footprint.area
    floor_h = body_height/floors if body_height is not None else 3.4
    nearby = tuple(n for n in getattr(context, 'neighbours', ()) if n.distance_m <= 75.)
    coverage = min(1.,sum(n.area_m2 for n in nearby)/(math.pi*75.**2))
    large = sum(n.area_m2 >= 600. for n in nearby)
    compact = sum(n.area_m2 < 350. for n in nearby)
    dense = coverage >= .28 or len(nearby) >= 12
    if use == 'commercial':
        w = dict(zip(COMMERCIAL, (2., 2., 2., 1.5)))
        if area < 180. or short < 8.:
            w[COMMERCIAL[2]] *= 4.
            w[COMMERCIAL[0]] *= .5
        if area >= 900. and short >= 15.:
            w[COMMERCIAL[1]] *= 3.
        if aspect >= 2.5:
            w[COMMERCIAL[2]] *= 2.5
            w[COMMERCIAL[3]] *= 1.6
        if floors >= 3:
            w[COMMERCIAL[3]] *= 4.
        if dense or compact >= 4:
            w[COMMERCIAL[2]] *= 2.5
            w[COMMERCIAL[0]] *= .5
        elif len(nearby) >= 3:
            w[COMMERCIAL[0]] *= 2.
        if large >= 3:
            w[COMMERCIAL[1]] *= 2.
    else:
        w = dict(zip(INDUSTRIAL, (2., 2., 2., 1.5)))
        if area >= 900. and short >= 15.:
            w[INDUSTRIAL[0]] *= 3.
        if area < 300. or compact >= 4:
            w[INDUSTRIAL[2]] *= 3.
        if aspect >= 2.5:
            w[INDUSTRIAL[1]] *= 3.
        if large >= 3:
            w[INDUSTRIAL[0]] *= 2.
            w[INDUSTRIAL[1]] *= 2.
        if floors >= 3 or dense:
            w[INDUSTRIAL[3]] *= 4.
        # High windows need a real wall above the shutter head.
        if floor_h < 4.2:
            w.pop(INDUSTRIAL[1])
        if floor_h < 3.1 or short < 5.:
            w.pop(INDUSTRIAL[0])
    if shape.area / max(shape.minimum_rotated_rectangle.area,.01) < .65 or footprint.holes:
        w = {k:v*(2. if k in (COMMERCIAL[2], INDUSTRIAL[3]) else .7) for k,v in w.items()}
    return w, ('sparse_use_architecture_v1', 'composition:inferred_visual_prior',
               f'footprint_aspect:{aspect:.2f}', f'observed_local_buildings:{len(nearby)}',
               f'observed_local_coverage:{coverage:.2f}')


def entry_position(spec, length):
    k = spec.inference.selection.preset.id
    if k not in IDS or length < 5.:
        return None
    u = materials.unit(spec.seed, 'sparse-entry-v1')
    if k in INDUSTRIAL[:3]:
        return min(3.,length*.2) if u < .5 else length-min(3.,length*.2)
    return length*(.35+.3*u)


def openings(spec, boundary, edge, length, base, high, reserved, budget, shared):
    from . import commercial as c, programme
    from .facades import Opening
    import buildings as b
    k = spec.inference.selection.preset.id
    if k not in IDS or not shared:
        return None
    result = list(reserved)
    run = shared.run(boundary,edge)
    if run.party_wall:
        return tuple(result), 'party_wall'
    # Courtyard windows follow their own boundary; ground sampling for these
    # runs is not yet supported by the exterior resolver.
    if boundary or length < 2*c.MARGIN+1.:
        return tuple(result), 'sparse_blank'
    front = c._front(spec,boundary,edge,shared)
    limit = min(c.MAX_OPENINGS, max(len(result),budget))

    def add(kind,left,right,bottom,top,floor=0,columns=1):
        if len(result) >= limit:
            return
        op = Opening(kind,floor,left,right,bottom,top,columns)
        if (left < c.MARGIN or right > length-c.MARGIN or right-left < .65
                or top-bottom < .65 or top > spec.height-.2 or bottom < 0.):
            return
        if not any(op.overlaps(other,.32) for other in result):
            result.append(op)

    def row(lo,hi,bay,width,bottom,top,floor=0,kind='window',columns=1):
        if hi-lo < .8 or top-bottom < .65:
            return
        grid = programme.fit_grid(hi-lo,bay,width,margin=0.,gap=.4,max_bays=16,
                                  mode='centered',allow_single=True)
        # Refit clear intervals inside a bay around the actual entrance.
        for module in grid.bays:
            for a,z in c._free_spans(lo+module.left,lo+module.right,bottom,top,reserved):
                add(kind,a,z,bottom,top,floor,columns)

    lo,hi = c.MARGIN,length-c.MARGIN
    floor_h = spec.floor_h
    head = min(floor_h-.35,spec.height-.35)
    u = shared.seed('structure',('sparse-grid',k))
    # Ground-level service apertures only on a resolved, grounded road frontage.
    if front and spec.door and (spec.min_h or 0.) <= .5 and k in INDUSTRIAL[:3] and head >= 2.9:
        anchor = spec.door[1]+run.member(spec.door[0]).start
        staff = min(10.,max(4.,length*.2))
        left_staff = anchor < length/2
        a,z = (max(lo,staff),hi) if left_staff else (lo,min(hi,length-staff))
        if k == INDUSTRIAL[0]:
            grid = programme.fit_grid(max(0.,z-a),5.8+u*1.6,3.2,margin=0.,gap=.5,max_bays=12,mode='centered')
            spans = [(a+t.left,a+t.right) for t in grid.bays]
        elif k == INDUSTRIAL[1]:
            count = min(3,max(1,int(length/22.)))
            spans = [(a+(z-a)*(i+.5)/count-1.6,a+(z-a)*(i+.5)/count+1.6) for i in range(count)]
        else:
            centre = (a+z)/2
            spans = [(centre-1.5,centre+1.5)] if z-a>=3.4 else []
        for a,z in spans:
            def ground_at(t):
                source_edge,along = c._source_position(spec,shared,edge,t)
                return b.door_ground(spec,source_edge,along,high)
            bottom = max(ground_at(a),ground_at(z))-base+.06
            add('service',a,z,bottom,min(bottom+3.5,head))
        if k == INDUSTRIAL[0]:
            a,z = (lo,min(hi,staff-.5)) if left_staff else (max(lo,length-staff+.5),hi)
            row(a,z,2.7,1.7,1.,min(2.6,head),kind='office')

    for datum in shared.datums:
        if len(result) >= limit:
            break
        bottom,top = datum.bottom,datum.top-.3
        if k == COMMERCIAL[0]:
            # Low glazed pavilion: broad panes and a quieter secondary skin.
            row(lo,hi,3.4+.5*u,3.0+.5*u,bottom+.2 if front else bottom+.9,
                top,datum.index,'office',3 if front else 2)
        elif k == COMMERCIAL[1]:
            # Concentrated entrance display, broad opaque end walls.
            if front and not datum.index and spec.door:
                anchor=spec.door[1]+run.member(spec.door[0]).start
                span=min(length*.65,20.+8.*u)
                a,z=max(lo,anchor-span/2),min(hi,anchor+span/2)
                row(a,z,4.2,3.8,bottom+.25,min(top,bottom+3.1),datum.index,'storefront',3)
            elif datum.index or not front:
                row(lo,hi,8.,1.8,bottom+max(.9,floor_h*.48),top,datum.index)
        elif k == COMMERCIAL[2]:
            # Deep opaque piers alternate with grouped display/window bays.
            row(lo,hi,3.5+.6*u,2.4+.3*u,bottom+(.25 if front and not datum.index else .85),
                min(top,bottom+3.),datum.index,'storefront' if front and not datum.index else 'window',2)
        elif k == COMMERCIAL[3]:
            row(lo,hi,7.+u*1.5,6.2+u*1.5,bottom+.95,min(top,bottom+2.9),datum.index,'office',5)
        elif k == INDUSTRIAL[1]:
            # Continuous high-level glazing over solid process/service walls.
            row(lo,hi,4.5+.6*u,3.5+.6*u,max(bottom+2.9,top-1.1),top,datum.index,'office',3)
        elif k == INDUSTRIAL[2]:
            # Windowed workhall with a single service zone at the frontage.
            row(lo,hi,3.5+.7*u,2.0,bottom+1.05,min(top,bottom+2.7),datum.index,'window',2)
        elif k == INDUSTRIAL[3]:
            row(lo,hi,3.4+.6*u,1.6+.2*u,bottom+.9,min(top,bottom+2.7),datum.index)
    return tuple(sorted(result,key=lambda o:(o.floor,o.left))), k+('_front' if front else '_secondary')
