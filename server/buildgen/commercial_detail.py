"""Bounded coherent commercial trim over accepted, closed facade compositions.

These are shallow inferred subdivisions, not observed structural systems or new
roof topology. No component produces access, collision, a canopy or an interior.
"""
from dataclasses import dataclass, replace


MAX_COMPONENTS = 192
MAX_PER_ELEVATION = 32
MAX_PANELS = 512
CLEARANCE = .08


@dataclass(frozen=True, slots=True)
class Component:
    kind: str
    left: float
    right: float
    bottom: float
    top: float
    material: str = 'trim'
    overlay: bool = False
    near_only: bool = False


@dataclass(frozen=True, slots=True)
class ElevationDetails:
    boundary: int
    edge: int
    components: tuple[Component, ...]


@dataclass(frozen=True, slots=True)
class DetailPlan:
    elevations: tuple[ElevationDetails, ...]
    diagnostics: tuple[str, ...] = ()

    def elevation(self,boundary,edge):
        return next((e.components for e in self.elevations if e.boundary==boundary and e.edge==edge),())


def _wall_fragments(component,openings):
    """Clip the complete rectangle, including trim clearance around entrances."""
    relevant=tuple(o for o in openings if o.left-CLEARANCE<component.right and o.right+CLEARANCE>component.left
                   and o.bottom-CLEARANCE<component.top and o.top+CLEARANCE>component.bottom)
    if not relevant:
        return (component,)
    cuts=sorted({component.bottom,component.top,
                 *(max(component.bottom,min(component.top,z)) for o in relevant
                   for z in (o.bottom-CLEARANCE,o.top+CLEARANCE))})
    result=[]
    for bottom,top in zip(cuts,cuts[1:]):
        if top-bottom<.025:continue
        start=component.left
        for left,right in sorted((o.left-CLEARANCE,o.right+CLEARANCE) for o in relevant
                                  if o.bottom-CLEARANCE<top and o.top+CLEARANCE>bottom):
            if left>start+.025:
                result.append(replace(component,left=start,right=min(left,component.right),bottom=bottom,top=top))
            start=max(start,right)
        if component.right-start>.025:
            result.append(replace(component,left=start,bottom=bottom,top=top))
    return tuple(c for c in result if c.right-c.left>.025 and c.top-c.bottom>.025)


def plan(spec,layout,programme,family):
    """One accepted elevation programme drives both visual tiers' major detail."""
    if not programme or not family:
        return DetailPlan(())
    result=[];total=0;panels=0;limited=False;obstructed=False
    for elevation in layout.elevations:
        if total>=MAX_COMPONENTS or panels>=MAX_PANELS:
            limited=True;break
        run=programme.run(elevation.boundary,elevation.edge)
        if run.party_wall or elevation.boundary:
            continue
        if f'ci_obstruction_run:{elevation.boundary}:{elevation.edge}' in layout.diagnostics:
            # The opening fitter proved individual clear intervals, not the
            # gaps needed by a continuous pier/cap. Decline this optional run.
            obstructed=True;continue
        accepted=tuple(o for o in elevation.openings if o.kind not in ('door','public_entry','garage'))
        if not accepted:
            continue
        if family.startswith('office_'):
            floor=max(o.floor for o in accepted)
            reference=tuple(o for o in accepted if o.floor==floor)
        elif family in ('ci_trade_units','ci_logistics_hall'):
            reference=tuple(o for o in accepted if o.kind=='service') or accepted
        else:
            reference=tuple(o for o in accepted if o.kind=='storefront') or accepted
        spans=sorted(set((o.left,o.right) for o in reference))
        if not spans:continue
        left=max(.45,spans[0][0]-.22)
        right=min(elevation.length-.45,max(c for _,c in spans)+.22)
        if right-left<.8:continue
        width=.06 if family=='office_curtain' else .14+.08*programme.seed('structure',('pier-width',family))
        joint_material='plinth' if family.startswith('ci_') and programme.seed('vocabulary',('joint-tone',family))<.35 else 'trim'
        marks=[spans[0][0]-.14,max(c for _,c in spans)+.14]
        marks.extend((a[1]+b[0])/2 for a,b in zip(spans,spans[1:]) if b[0]-a[1]>.15)
        candidates=[]
        # Piers end below the roof-edge cap instead of crossing its silhouette.
        for centre in marks[:MAX_PER_ELEVATION-4]:
            candidates.append(Component('pier',max(.45,centre-width/2),min(elevation.length-.45,centre+width/2),
                                        .28,max(.28,spec.height-.32),joint_material))
        cap_top=spec.height-.04
        cap_bottom=max(.3,cap_top-(.25 if family!='office_curtain' else .16))
        candidates.append(Component('roof_edge',left,right,cap_bottom,cap_top))
        if family=='office_ribbon':
            for datum in programme.datums:
                if datum.height>=3.:
                    candidates.append(Component('spandrel',left,right,datum.top-.94,datum.top-.49,'plinth'))
        components=[]
        for candidate in candidates:
            if len(components)>=MAX_PER_ELEVATION or total>=MAX_COMPONENTS or panels>=MAX_PANELS:
                limited=True;break
            if candidate.right-candidate.left<.025 or candidate.top-candidate.bottom<.025:continue
            for fragment in _wall_fragments(candidate,elevation.openings):
                if len(components)>=MAX_PER_ELEVATION or total>=MAX_COMPONENTS or panels>=MAX_PANELS:
                    limited=True;break
                components.append(fragment);total+=1;panels+=1
        if family in ('office_curtain','ci_strip_shops','ci_supermarket'):
            actual_door=next((o for o in elevation.openings if o.kind in ('door','public_entry')),None)
            head=(actual_door.top-actual_door.floor*spec.floor_h) if actual_door else min(2.25,spec.floor_h*.65)
            for opening in accepted:
                if opening.kind not in ('office','storefront'):continue
                datum=programme.datum(opening.floor)
                z=datum.bottom+head
                if opening.bottom+.2<z<opening.top-.2 and opening.right-opening.left>.5:
                    if len(components)>=MAX_PER_ELEVATION or total>=MAX_COMPONENTS or panels>=MAX_PANELS:
                        limited=True;break
                    components.append(Component('transom',opening.left+.04,opening.right-.04,z-.03,z+.03,
                                                overlay=True,near_only=True))
                    total+=1;panels+=1
        result.append(ElevationDetails(elevation.boundary,elevation.edge,tuple(components)))
    diagnostics=(('commercial_detail_budget_reached',) if limited else ())
    if obstructed:diagnostics+=('commercial_detail_omitted_obstructed_run',)
    return DetailPlan(tuple(result),diagnostics)
