"""One opening layout for walls, windows, entrance props and garage driveways.

Coordinates are metres along an oriented boundary and above the volume's base.
Near/lite geometry use the same apertures; only reveal/trim depth is simplified.
"""
from dataclasses import dataclass, replace
import math

import numpy as np

from . import materials


DOOR_WIDTH = 1.25             # includes the stock one-metre door's frame
DOOR_HEIGHT = 2.25
OPENING_GAP = .25
CORNER_MARGIN = .45
FRAME = .065
REVEAL = .09
MIDDLE_RECESS_M = .30        # retain architectural depth; shallow trim can flatten


@dataclass(frozen=True, slots=True)
class Opening:
    kind: str
    floor: int
    left: float
    right: float
    bottom: float
    top: float
    columns: int = 1
    variant: int = 0
    depth: float | None = None
    assembly: str = ''

    def overlaps(self, other, gap=0.):
        return (self.left < other.right + gap and self.right > other.left - gap and
                self.bottom < other.top + gap and self.top > other.bottom - gap)


@dataclass(frozen=True, slots=True)
class Elevation:
    boundary: int
    edge: int
    length: float
    openings: tuple[Opening, ...]
    role: str = 'generic'


@dataclass(frozen=True, slots=True)
class FacadeLayout:
    elevations: tuple[Elevation, ...]
    wall_scale: tuple[float, float]
    trim: str
    plinth: str
    garage: str
    diagnostics: tuple[str, ...] = ()


def entrance(spec, length, setback):
    """A compatible front elevation: garage beside a separate pedestrian entry.

    An opening only gets a garage when its low detached form and road setback
    support an apron. Existing mapped height/use always constrain this template.
    """
    form = spec.inference.morphology.value
    standalone = spec.inference.selection.preset.id == 'garage_outbuilding'
    if standalone and spec.floors == 1 and spec.floor_h >= 2.6 and length >= 3.4 \
            and setback >= 3.5 and (spec.min_h or 0.) <= .5 and length < 6.5:
        # A narrow mapped garage need not have a separate pedestrian door on
        # this elevation. The garage centre remains the access sampling anchor.
        return length/2, (length/2, min(4.8,length-1.), min(2.3,spec.floor_h-.35))
    if (not standalone and (not spec.inference.selection.preset.garage or form != "detached_lowrise")) \
            or not 1 <= spec.floors <= 2 or spec.floor_h < 2.6 or length < 6.5 \
            or setback < 3.5 or (spec.min_h or 0.) > .5:
        return None
    left = materials.unit(spec.seed, "garage-side") < .5
    width = 4.8 if length >= 12. else 2.8
    gc = .65 + width / 2. if left else length - .65 - width / 2.
    door = length - 1.35 if left else 1.35
    if abs(gc - door) < width / 2. + DOOR_WIDTH / 2. + .65:
        return None
    return door, (float(gc), width, min(2.3, spec.floor_h - .35))


def plan(spec, gmin, gmax):
    import buildings as b
    if getattr(spec, 'city', None) is not None:
        from .city import layout
        return layout(spec, gmin, gmax)
    from . import regional_blocks as blocks
    block_profile=blocks.profile(spec)
    base = b.base_z(spec, gmin, gmax) + (spec.min_h or 0.)
    family = spec.inference.facade.value
    use = spec.inference.use.value
    office = family == "glass"
    recipe = spec.inference.selection.preset
    width, bay = (2.4, 3.25) if office else (recipe.window_width, recipe.bay)
    if use == "residential" and spec.floors >= 4:
        width, bay = 1.5, 3.0
    from . import regional_architecture as regional
    if block_profile:
        regional_profile=None
    else:
        width,bay,regional_profile=regional.window_parameters(spec,width,bay)
        if not regional_profile:
            # Generic presets also describe a range of buildings. Dedicated
            # commercial/city solvers keep their own dimensioning below.
            width*=regional.dimension(spec,'window_width',.88,1.12)
            bay=max(width+.8,bay*regional.dimension(spec,'bay',.90,1.12))
    frame=max(FRAME,regional_profile['frame']) if regional_profile else FRAME
    elevations = []
    from . import commercial
    shared=commercial.derive_programme(spec)
    architecture_openings=0
    block_openings=0
    for boundary, ring in enumerate((spec.footprint.outer, *spec.footprint.holes)):
        for edge, (a, c) in enumerate(zip(ring, ring[1:] + ring[:1])):
            length = float(math.dist(a, c))
            run_context=shared.run(boundary,edge) if shared else None
            if run_context is not None:
                if edge!=run_context.edge:continue
                a,c,length=run_context.start,run_context.end,run_context.length
            openings = []
            garage_only = spec.garage_opening and recipe.id == 'garage_outbuilding' \
                and spec.door and abs(spec.door[1]-spec.garage_opening[1]) < spec.garage_opening[2]/2
            door_member=run_context.member(spec.door[0]) if run_context is not None and spec.door and boundary==0 else None
            if boundary == 0 and spec.door and (door_member is not None or edge == spec.door[0]) and not garage_only:
                z = (b.door_ground(spec, spec.door[0], spec.door[1], gmax) if spec.stoop else gmax) - base
                z += (b.STOOP_H if spec.stoop else 0.) + (b.PORCH_DECK_M if spec.porch else 0.)
                if spec.access is not None:
                    z = spec.access.door_z - base
                anchor=spec.door[1]+(door_member.start if door_member is not None else 0.)
                openings.append(Opening("door", 0, anchor - DOOR_WIDTH / 2., anchor + DOOR_WIDTH / 2.,
                                        float(z), float(z + DOOR_HEIGHT)))
            garage = spec.garage_opening
            if boundary == 0 and garage and edge == garage[0]:
                _, centre, w, h = garage
                z = spec.access.garage_z - base if spec.access is not None and spec.access.garage_z is not None else 0.
                openings.append(Opening("garage", 0, centre - w / 2., centre + w / 2., z, z+h))
            # Specialist adapters get one proposal slot before the ordinary
            # commercial solver; unsupported cases keep the established route.
            from . import terminals
            fitted = terminals.openings(spec,boundary,edge,length,base,gmax,openings,programme=shared)
            architecture = bool(commercial.office_profile(spec) or recipe.id=='ci_strip_shops'
                                or recipe.id in commercial.commercial_forms.IDS)
            budget=max(0,commercial.MAX_ARCHITECTURE_OPENINGS-architecture_openings)+len(openings) if architecture else commercial.MAX_OPENINGS
            if fitted is None:
                fitted = commercial.openings(spec,boundary,edge,length,base,gmax,openings,budget=budget,programme=shared)
            if fitted is not None:
                fitted_openings, role = fitted
                if architecture:
                    architecture_openings+=max(0,len(fitted_openings)-len(openings))
                elevations.append(Elevation(boundary,edge,length,fitted_openings,role))
                continue
            if block_profile:
                fitted_openings,role=blocks.openings(spec,block_profile,boundary,edge,length,openings,
                                                     blocks.MAX_OPENINGS-block_openings)
                block_openings+=len(fitted_openings)-len(openings)
                elevations.append(Elevation(boundary,edge,length,fitted_openings,role))
                continue
            # Closed service shutters share the opening layout; no invented
            # loading dock, traversable interior or untested driveway projection.
            if recipe.service and boundary == 0 and edge == spec.front and spec.door \
                    and spec.floor_h >= 2.6 and length >= 6. and not garage:
                w = min(3.6, max(2.4, length * .22))
                for centre in (length * .25, length * .75):
                    z = max(b.door_ground(spec,edge,centre-w/2,gmax),
                            b.door_ground(spec,edge,centre+w/2,gmax)) - base
                    op = Opening("service", 0, centre-w/2, centre+w/2, z,
                                 min(z+3.6, spec.floor_h-.4))
                    if op.left >= CORNER_MARGIN and op.right <= length-CORNER_MARGIN \
                            and op.top-op.bottom >= 2.2 \
                            and not any(op.overlaps(other, .35) for other in openings):
                        openings.append(op)
                        break
            reserved = tuple(openings)
            regional_front=bool(regional_profile and boundary==0 and edge==spec.front)
            elevation_bay=bay
            if regional_profile:
                elevation_bay=max(width+1.2,bay*.9) if regional_front else bay*1.1
            count = max(0, int((length - 2 * CORNER_MARGIN) / elevation_bay))
            if count == 0 and length >= width + 2 * CORNER_MARGIN:
                count = 1
            for floor in range(int(spec.floors)):
                if spec.windows is False or spec.plain or not count:
                    continue
                zfloor = floor * spec.floor_h
                storefront = floor == 0 and spec.shop and boundary == 0 and edge == spec.front
                sill = .12 if storefront else .25 if office else min(.8, spec.floor_h * .27)
                h = min(2.6 if storefront or office else 1.65, spec.floor_h - sill - .4)
                if regional_profile and not storefront and not office:
                    sill=min(regional_profile['sill'],spec.floor_h*.30)
                    h=min(regional_profile['window_height'],spec.floor_h-sill-.4)
                    sill,h=regional.window_vertical(spec,regional_profile,sill,h)
                    if regional_profile.get('arch_scope')=='front_ground' and (floor or boundary or edge!=spec.front):
                        sill=min(regional_profile['sill'],spec.floor_h*.3)
                        h=min(regional_profile['window_height'],spec.floor_h-sill-.4)
                if h < .65:
                    continue
                w = min(width if not storefront else bay - .4, length / count - .5)
                if regional_profile and regional_profile.get('arch_scope')=='front_ground' and (floor or boundary or edge!=spec.front):
                    w=min(w,regional_profile['window_width'])
                row_count=count
                if regional_profile and not storefront and not office:
                    max_area=length*spec.floor_h*regional.glazing_share(regional_profile,front=regional_front)
                    row_count=min(count,max(1,int(max_area/max(w*h,1e-6))))
                centres = regional.opening_centres(spec,boundary,edge,CORNER_MARGIN,
                    length-CORNER_MARGIN,row_count,w,frame)
                blocked = sorted((op.left - OPENING_GAP - frame, op.right + OPENING_GAP + frame)
                                 for op in reserved if op.bottom < zfloor + sill + h + frame
                                 and op.top > zfloor + sill - frame)
                if blocked:
                    # Compose the remaining wall spans around actual doors and
                    # garages, rather than deleting every conflicting grid bay.
                    spans, start = [], CORNER_MARGIN
                    for left, right in blocked:
                        if left > start:
                            spans.append((start, min(left, length - CORNER_MARGIN)))
                        start = max(start, right)
                    if start < length - CORNER_MARGIN:
                        spans.append((start, length - CORNER_MARGIN))
                    centres = []
                    for lo, hi in spans:
                        if hi - lo < w + 2 * frame:
                            continue
                        if regional_front:
                            # Fit a balanced entrance composition into the clear
                            # spans; a door should not consume another whole bay.
                            spacing=max(w+1.2,elevation_bay*.85)
                            n=max(1,int((hi-lo+1.2)/spacing))
                        else:
                            n = max(1, int((hi - lo) / elevation_bay))
                        centres.extend(regional.opening_centres(spec,boundary,edge,lo,hi,n,w,frame))
                    if len(centres)>row_count:
                        grid=[length*(k+.5)/row_count for k in range(row_count)]
                        centres=sorted(sorted(centres,key=lambda x:min(abs(x-g) for g in grid))[:row_count])
                for k, centre in enumerate(centres):
                    kind = "storefront" if storefront else "office" if office else "window"
                    op = Opening(kind, floor, centre - w / 2., centre + w / 2., zfloor + sill, zfloor + sill + h,
                                 2 if w > 1.6 and kind == "window" else 1,
                                 min(2, int(materials.unit(spec.seed, ("window", boundary, edge, floor, k)) * 3)))
                    if op.left < CORNER_MARGIN or op.right > length - CORNER_MARGIN:
                        continue
                    if not any(op.overlaps(r, OPENING_GAP + frame) for r in reserved):
                        openings.append(op)
            elevations.append(Elevation(boundary, edge, length, tuple(openings)))
    dark = family in ("glass", "metal") or materials.unit(spec.seed, "trim") < .25
    trim = b.custom_look(b.PANEL, (.24, .27, .28) if dark else (.96, .95, .90))
    if regional_profile:trim=b.custom_look(b.PANEL,tuple(regional_profile['trim']))
    if block_profile:trim=b.custom_look(b.PANEL,tuple(block_profile['trim_colour']))
    plinth = b.custom_look(b.PANEL, (.57, .58, .56))
    garage_colour = materials.choose(spec.seed, "garage-paint", (((.86, .87, .84), 4), ((.35, .38, .39), 3),
                                                               ((.52, .44, .36), 2), ((.52, .21, .16), 1)))
    diagnostics=commercial.architecture_diagnostics(spec)
    if regional_profile:
        style=spec.inference.house_style
        label=('contemporary_architecture:'+style.alternate if style.variant=='contemporary' else
               'regional_architecture:'+regional.house_styles.profile_region(spec.inference))
        diagnostics+=(label,
                      'regional_expression:'+regional.variation(spec))
    if block_profile:
        diagnostics+=('regional_block:'+block_profile['id'],
                      'regional_block_grammar:'+block_profile['grammar'],
                      'regional_block_grouped_windows_v1')
    if shared:diagnostics+=('architecture_programme_shared_runs_v1',)
    if shared is False:diagnostics+=('architecture_programme_existing_geometry_fallback',)
    if architecture_openings>=commercial.MAX_ARCHITECTURE_OPENINGS:
        diagnostics+=('ci_optional_opening_budget_reached',)
    from . import residential
    dwelling=residential.for_spec(spec)
    if dwelling:
        composed=[];assemblies=0
        for elevation in elevations:
            elevation=residential.compose(spec,elevation)
            openings=[]
            for opening in elevation.openings:
                if opening.assembly:
                    if assemblies>=residential.MAX_ASSEMBLIES:
                        opening=replace(opening,assembly='',depth=min(.25,opening.depth or .09))
                    else:assemblies+=1
                openings.append(opening)
            composed.append(replace(elevation,openings=tuple(openings)))
        elevations=composed
        diagnostics+=('dwelling_structure:'+dwelling['id'],'dwelling_structure_geography:'+dwelling['region'])
    from .regional_facade_details import compose as compose_modifiers
    elevations=[compose_modifiers(spec,e) for e in elevations]
    shallow_count=sum(len(shallow_openings(spec,e,block_profile,regional_profile,False)) for e in elevations)
    if shallow_count:
        diagnostics+=('generic_upper_shallow_panes:'+str(shallow_count),
                      'generic_upper_detail_depth_at_most_0.09m',)
    return FacadeLayout(tuple(elevations), materials.wall_scale(family), trim, plinth,
                        b.custom_look(b.SHUTTER, garage_colour),diagnostics)


def wall_cells(length, bottom, top, openings):
    """Non-overlapping wall rectangles around windows/garage apertures."""
    if not openings:
        lo, hi = sorted((bottom, top))
        if hi - lo >= 1e-8 and 0. < length - 1e-8:
            yield 0., length, lo, hi
        return
    cuts = sorted({bottom, top, *(max(bottom, min(top, z)) for op in openings for z in (op.bottom, op.top))})
    # Tall facades used to rescan every opening for every height band. Locate
    # each opening's active bands once, preserving the original epsilon tests
    # exactly (including floating-point subtraction at large elevations).
    sweep = len(openings) > 24 and len(cuts) > 8
    if sweep:
        from bisect import bisect_left, bisect_right
        highs = [hi - 1e-8 for hi in cuts[1:]]
        lows = [lo + 1e-8 for lo in cuts[:-1]]
        starts, ends, live = {}, {}, {}
        for key, op in enumerate(openings):
            first = bisect_right(highs, op.bottom)
            end = bisect_left(lows, op.top)
            if first < end:
                starts.setdefault(first, []).append((key, (op.left, op.right)))
                ends.setdefault(end, []).append(key)
    for band, (lo, hi) in enumerate(zip(cuts, cuts[1:])):
        if sweep:
            for key in ends.get(band, ()):
                del live[key]
            for key, span in starts.get(band, ()):
                live[key] = span
        if hi - lo < 1e-8:
            continue
        active = (sorted(live.values()) if sweep else
                  sorted((op.left, op.right) for op in openings if op.bottom < hi - 1e-8 and op.top > lo + 1e-8))
        start = 0.
        for left, right in active:
            if left > start + 1e-8:
                yield start, left, lo, hi
            start = max(start, right)
        if start < length - 1e-8:
            yield start, length, lo, hi


def shallow_openings(spec,elevation,block_profile,regional_profile,lite):
    """Generic upper apertures eligible for compact closed bevelled surrounds."""
    if lite or block_profile or regional_profile or spec.church or spec.terminal or spec.deck or spec.site is not None:
        return frozenset()
    return frozenset(op for op in elevation.openings if op.floor>=2 and op.kind in ('window','office')
                     and not op.assembly and (op.depth is None or op.depth<=REVEAL))


def draw(mesh, spec, gmin, gmax, bottom, lite=False):
    import buildings as b
    from . import components as templates
    if getattr(spec, 'city', None) is not None:
        from .city import draw as draw_city
        return draw_city(mesh, spec, gmin, gmax, bottom, lite=lite)
    from . import regional_blocks as blocks
    block_profile=blocks.profile(spec)
    layout = spec.facades or plan(spec, gmin, gmax)
    from . import commercial
    shared=commercial.derive_programme(spec)
    glazing_grids={}
    from . import commercial_detail
    detail_plan=commercial_detail.plan(spec,layout,shared,commercial.detail_family(spec))
    detail_elevations={(e.boundary,e.edge):e.components for e in detail_plan.elevations}
    base = b.base_z(spec, gmin, gmax) + (spec.min_h or 0.)
    mats = b._Looks(spec.seed)
    body = mats[spec.facade] if spec.inference.facade.value != "glass" else mats[layout.trim]
    window = mats["bne_bld_fac_white"]
    trim, plinth = mats[layout.trim], mats[layout.plinth]
    from . import regional_architecture as regional
    from . import residential
    dwelling=residential.for_spec(spec)
    regional_profile=None if block_profile else regional.for_spec(spec)
    frame=regional_profile['frame'] if regional_profile else FRAME
    reveal=regional_profile['reveal'] if regional_profile else REVEAL
    accent=mats[b.custom_look(b.PANEL,tuple(regional_profile['accent']))] if regional_profile else trim
    lower_body,upper_body=regional.wall_materials(spec,regional_profile,mats,body)
    wall_trim=(trim[0],tuple(round(.8*upper_body[1][i]+.2*trim[1][i]) for i in range(3))+(255,))
    if regional_profile:reveal=regional_profile.get('facade_depth',reveal)
    if block_profile:
        frame=blocks.frame(spec,block_profile)
        reveal=blocks.reveal(spec,block_profile)
        accent=mats[b.custom_look(b.PANEL,tuple(block_profile['accent_colour']))]
        block_looks=tuple(mats[look] for look in blocks.wall_looks(spec,block_profile))
        block_section_width=blocks.value(spec,block_profile,'section-width',(9.,16.))
    regional_budget=regional.MAX_COMPONENTS
    canopy_budget=regional.MAX_CANOPIES
    allow_arches=sum(op.kind=='window' for e in layout.elevations for op in e.openings)<=regional.MAX_ARCHES
    rings = (spec.footprint.outer, *spec.footprint.holes)
    run, last_boundary = 0., -1
    for elevation in layout.elevations:
        boundary, edge, length = elevation.boundary, elevation.edge, elevation.length
        if length < 1e-9:
            continue
        if boundary != last_boundary:
            run, last_boundary = 0., boundary
        ring = rings[boundary]
        source_run=shared.run(boundary,edge) if shared else None
        if source_run is not None and math.isclose(length,source_run.length,abs_tol=1e-8):
            a,c=np.asarray(source_run.start),np.asarray(source_run.end)
        else:
            a, c = np.asarray(ring[edge]), np.asarray(ring[(edge + 1) % len(ring)])
        d = (c - a) / length
        ax, ay, dx, dy = float(a[0]), float(a[1]), float(d[0]), float(d[1])

        def at(s, z, depth=0.):
            return (ax + dx * s + dy * depth, ay + dy * s - dx * depth, base + z)

        def quad(s0, s1, z0, z1, material, depth=0., uv=None):
            if s1 - s0 < 1e-8 or z1 - z0 < 1e-8:
                return
            if uv is None:
                su, sv = layout.wall_scale
                if material in (lower_body,upper_body):
                    su,sv=materials.wall_scale('stone' if b.MATERIALS[material[0]] in (b.STONE,b.BRICK_WALL) else 'render')
                uv = (((run + s0) / su, z0 / sv), ((run + s1) / su, z0 / sv),
                      ((run + s1) / su, z1 / sv), ((run + s0) / su, z1 / sv))
            mesh.quad(at(s0, z0, depth), at(s1, z0, depth), at(s1, z1, depth), at(s0, z1, depth), *uv, material)

        openings = [op for op in elevation.openings if op.kind != "door"]
        zbottom = bottom - base
        # The generic path must not become dramatically dearer just outside a
        # designed grammar's eligibility limits. Upper generic apertures have
        # only a 9 cm reveal: retain its actual depth with four closed bevelled
        # faces instead of full trim and sill components. Street rows and deep
        # structural openings retain their original construction.
        shallow=shallow_openings(spec,elevation,block_profile,regional_profile,lite)
        # Close/middle share aperture positions. Assemblies and deep recesses
        # retain holes and closed returns; only shallow openings use overlays.
        deep=frozenset(op for op in openings if (op.depth if op.depth is not None else reveal)>=MIDDLE_RECESS_M)
        structural=[op for op in openings if op.assembly or op in deep]
        cells = (wall_cells(length,zbottom,spec.height,structural) if lite and structural else
                 [(0., length, zbottom, spec.height)] if lite else
                 wall_cells(length,zbottom,spec.height,
                    [replace(op,left=op.left-frame,right=op.right+frame,bottom=op.bottom-frame,top=op.top+frame)
                     if op in shallow else op for op in openings]))
        for s0, s1, z0, z1 in cells:
            if block_profile:
                for a,c,lo,hi,material in blocks.paint_cells(spec,block_profile,elevation,(s0,s1,z0,z1),block_looks,
                                                           section_width=block_section_width):
                    quad(a,c,lo,hi,material)
                continue
            if lower_body!=upper_body and z0<spec.floor_h<z1:
                quad(s0,s1,z0,spec.floor_h,lower_body)
                quad(s0,s1,spec.floor_h,z1,upper_body)
            else:
                quad(s0,s1,z0,z1,lower_body if z1<=spec.floor_h else upper_body)
        plinth_top = min(.28, spec.floor_h * .1)
        for s0, s1, z0, z1 in wall_cells(length, zbottom, plinth_top, openings):
            quad(s0, s1, z0, z1, plinth, .012)
        for left,right,lo,hi in commercial.bands(spec,elevation,programme=shared):
            for s0,s1,z0,z1 in wall_cells(length,lo,hi,elevation.openings):
                quad(max(left,s0),min(right,s1),z0,z1,trim,.008)
        components=detail_elevations.get((boundary,edge),())
        regional_components=(blocks.components(spec,block_profile,elevation,regional_budget) if block_profile else
                             regional.components(spec,elevation,regional_profile,regional_budget))
        regional_budget-=len(regional_components)
        components=components+regional_components+residential.frame_components(spec,elevation,dwelling)
        band_at=None
        def detail(component):
            nonlocal band_at
            material=(plinth if component.material=='plinth' else accent if component.material=='accent'
                      else wall_trim if component.material=='wall_trim' else trim)
            depth=(.035 if lite else -reveal+.016) if component.overlay else .012
            if component.kind in ('corner_board','deep_beam','dwelling_frame'):depth=.035
            if component.kind in ('screen','block_screen') and not lite:depth=.025
            s0,s1,z0,z1=component.left,component.right,component.bottom,component.top
            wrap=component.kind in ('deep_beam','upper_cornice','floor_band','corner_board') and source_run is None
            if wrap and band_at is None:band_at=regional.band_frame(ring,edge,base)
            point=band_at if wrap else at
            corners=((s0,z0),(s1,z0),(s1,z1),(s0,z1))
            mesh.quad(*(point(*p,depth) for p in corners),(0,0),((s1-s0)/3,0),((s1-s0)/3,(z1-z0)/3),(0,(z1-z0)/3),material)
            if not lite and component.kind not in (
                    'sash','mullion','recess_panel','transom','spandrel','block_lower_panel'):
                # Closed shallow returns keep strips solid from oblique views.
                # Inset surface patterns need only their textured face; 12 mm
                # hidden returns add no useful silhouette or collision detail.
                back=0. if component.kind in ('corner_board','deep_beam') else depth-.012
                for p,q in zip(corners,corners[1:]+corners[:1]):
                    mesh.quad(point(*p,depth),point(*q,depth),point(*q,back),point(*p,back),
                              (0,0),(1,0),(1,.1),(0,.1),material)
        for component in components:
            if not component.overlay and not (lite and component.near_only):detail(component)
        if lite:
            for op in elevation.openings:
                if op.kind == "door":
                    quad(op.left + .125, op.right - .125, op.bottom, op.top - .05,
                         mats[b.custom_look(b.PANEL, (.25, .28, .29))], .025)
        for op in openings:
            x0, x1, z0, z1 = op.left, op.right, op.bottom, op.top
            from .regional_facade_details import draw_opening as draw_modifier_opening
            if draw_modifier_opening(mesh,spec,op,at,quad,lower_body if op.floor==0 else upper_body,
                                     trim,window,lite=lite):continue
            if residential.draw_opening(mesh,spec,op,at,quad,
                    lower_body if op.floor==0 else upper_body,trim,window,lite=lite,elevation=elevation):continue
            arch=regional.aperture_shape(spec,regional_profile,elevation,op) if allow_arches else 'rectangular'
            opening_reveal=op.depth if op.depth is not None else reveal
            flattened=lite and op not in deep
            depth = .02 if flattened else -opening_reveal
            if op.kind == 'staff_door':
                quad(x0,x1,z0,z1,mats[b.custom_look(b.PANEL,(.25,.28,.29))],depth)
                if not lite:
                    quad(x1-.16,x1-.10,z0+.95,z0+1.12,trim,depth+.01)
            elif op.kind in ("garage", "service"):
                # Four 0.32 m slats per texture repeat; no stripe geometry.
                v=(z1-z0)/1.28
                quad(x0,x1,z0,z1,mats[layout.garage],depth,((0,0),(1,0),(1,v),(0,v)))
            else:
                for l,r,col,mullion in commercial.glazing_segments(spec,elevation,op,shared,glazing_grids):
                    if op.kind == "window":
                        bay = (0, 2, 3)[(op.variant + col) % 3]
                        u0, u1, v0, v1 = b.WIN_UV
                        u0, u1 = u0 + bay / 5., u1 + bay / 5.
                        material = window
                    else:
                        band = 2 if op.kind in ("storefront", "public_entry") else 0
                        bays = 2 if band == 2 else 5
                        slot = (op.variant + col) % bays
                        u0, u1 = slot / bays + .003, (slot + 1) / bays - .003
                        v0, v1 = 1. - (band + 1) / 4. + .003, 1. - band / 4. - .003
                        material = mats[b.SHOP if band == 2 else b.OFFICE]
                    quad(l, r, z0, z1, material, depth, ((u0, v0), (u1, v0), (u1, v1), (u0, v1)))
                    if mullion and not flattened:
                        quad(l - .025, l + .025, z0, z1, trim, -.005)
            if arch!='rectangular':
                from .regional_openings import draw_arch
                arch_wall=lower_body if op.floor==0 else upper_body
                su,sv=materials.wall_scale('stone' if b.MATERIALS[arch_wall[0]] in (b.STONE,b.BRICK_WALL) else 'render')
                draw_arch(mesh,op,at,arch_wall,trim,opening_reveal,frame,arch,lite,
                          lambda s,z:((run+s)/su,z/sv),retain_depth=not flattened)
            if lite and not flattened and arch=='rectangular':
                # Four plain returns keep the deep opening closed from oblique
                # views, without close-tier surround strips, sills or hoods.
                corners=((x0,z0),(x1,z0),(x1,z1),(x0,z1))
                for j in range(4):
                    k=(j+1)%4
                    mesh.quad(at(*corners[j]),at(*corners[k]),at(*corners[k],depth),at(*corners[j],depth),
                              (0,0),(1,0),(1,opening_reveal),(0,opening_reveal),trim)
            if not lite and op in shallow:
                # Outer rim meets the cut wall plane exactly; the inner rim
                # meets the unchanged recessed glass. No opaque backing panel
                # hides the depth from a close free camera at upper storeys.
                outer=((x0-frame,z0-frame),(x1+frame,z0-frame),(x1+frame,z1+frame),(x0-frame,z1+frame))
                inner=((x0,z0),(x1,z0),(x1,z1),(x0,z1))
                for j in range(4):
                    k=(j+1)%4
                    mesh.quad(at(*outer[j]),at(*outer[k]),at(*inner[k],depth),at(*inner[j],depth),
                              (0,0),(1,0),(1,.1),(0,.1),trim)
            if not lite and op not in shallow and arch=='rectangular':
                su,sv=layout.wall_scale
                if trim in (lower_body,upper_body):
                    su,sv=materials.wall_scale('stone' if b.MATERIALS[trim[0]] in (b.STONE,b.BRICK_WALL) else 'render')
                templates.facade(mesh,templates.surround(round(x1-x0,12),round(z1-z0,12),frame,opening_reveal),
                                 (ax,ay),(dx,dy),base,x0,z0,trim,(run,su,sv))
                if op.kind == "window":
                    # Closed sill with a sloping top, underside and end caps.
                    # The previous single plane disappeared from below.
                    def ledge(lo, hi, z, depth, thickness):
                        templates.facade(mesh,templates.sill(round(hi-lo,12),depth,thickness),
                                         (ax,ay),(dx,dy),base,lo,z,trim)
                    ledge(x0-frame, x1+frame, z0-frame, .12, .07)
                    # Recess-compatible sun hood stays beneath the existing
                    # rectangular eave; suppress near doors or other openings.
                    selection = spec.inference.selection
                    regional_canopy = regional_profile and 'canopies' in regional_profile['details'] and canopy_budget>0
                    if (selection.climate_response == "solar_shading" or regional_canopy) and spec.footprint.is_rectangle() \
                            and (spec.roof != "flat" or regional_canopy) and z1+.18 < spec.height and z1>2.1 \
                            and not any(other is not op and other.overlaps(
                                Opening("hood",op.floor,x0-.12,x1+.12,z1,z1+.18), .05)
                                        for other in elevation.openings):
                        ledge(x0-.1, x1+.1, z1+.15, min(.25, b.EAVE_M), .08)
                        if regional_canopy:canopy_budget-=1
        for component in components:
            if component.overlay and not (lite and component.near_only):detail(component)
        from .regional_facade_details import draw_surface_details
        draw_surface_details(mesh,spec,elevation,at,quad,mats,lite=lite)
        run += length
    if not lite:
        from .details import corners
        corners(mesh,spec,base,layout,mats)
