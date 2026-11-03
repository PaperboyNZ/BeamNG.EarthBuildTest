"""Compact regional buildings: shared materials, batched atlas windows, one mesh.

No detailed opening objects, recess subtraction, per-window frames or site trim.
Source topology, inferred identity and roof envelopes remain authoritative.
"""
import math
import numpy as np


def enabled():
    from .progressive import DETAIL
    return DETAIL.get() == 'minimum'


def visual_enabled(spec=None):
    # Compact accepted physical envelopes cannot acquire projected structural
    # assemblies during a visual refinement. Keep the compatible representation
    # until its anchored fast/detailed replacements are available.
    if getattr(spec, 'physical_mode', None) == 'compact':
        return True
    from .progressive import DETAIL
    if DETAIL.get() == 'minimum':
        return True
    # Downgrading a previously accepted detailed plan preserves its established
    # aperture layout. Fresh source-local Very Low plans use compact facades.
    inference = getattr(spec, 'inference', None)
    return (DETAIL.get() == 'very_low' and inference is not None and
            inference.context.profile == 'source-local-low-v1')


def physical_enabled(spec):
    """Accepted collision recipe; visual quality cannot change this decision."""
    mode = getattr(spec, 'physical_mode', None)
    return mode == 'compact' if mode is not None else enabled()


def collision(mesh, spec, gmin, gmax):
    """Match the compact body, supports and access; omit removed facade bays."""
    import buildings as b
    from .geometry import horizontal
    from . import roofs, regional_supports, regional_roof_details
    mats=b._Looks(spec.seed)
    wall=(b.MATERIALS.index(b.PANEL),(128,128,128,255))
    base=b.base_z(spec,gmin,gmax)+(spec.min_h or 0.)
    bottom=gmin-b.FOUNDATION_M if (spec.min_h or 0.)<=.5 else base
    top=base+spec.height
    regional_supports.draw(mesh,spec,gmin,gmax,wall)
    for ring in (spec.footprint.outer,*spec.footprint.holes):
        for a,c in zip(ring,ring[1:]+ring[:1]):
            mesh.quad((*a,bottom),(*c,bottom),(*c,top),(*a,top),*((0.,0.),)*4,wall)
    if spec.roof!='flat':roofs.draw(mesh,spec,top,mats,overhang=False)
    else:
        horizontal(mesh,spec.footprint,top-(.9 if regional_roof_details.recessed_deck(spec) else 0.),wall)
        regional_roof_details.draw(mesh,spec,top,regional_roof_details.looks(spec,mats))
    if (spec.min_h or 0.)>.5:horizontal(mesh,spec.footprint,bottom,wall,down=True)
    if spec.access:
        from .access import draw as access
        access(mesh,spec,True,detail=False)


def _windows(mesh, a, direction, left, right, bottom, top, material):
    """Append an entire elevation's windows directly to numeric streams."""
    import buildings as b
    count = len(left)
    if not count:return
    if count<=16:
        dx,dy=direction
        u0,u1,v0,v1=b.WIN_UV
        for l,r,lo,hi in zip(left,right,bottom,top):
            x0=a[0]+dx*l+dy*.018;y0=a[1]+dy*l-dx*.018
            x1=a[0]+dx*r+dy*.018;y1=a[1]+dy*r-dx*.018
            mesh.quad((x0,y0,lo),(x1,y1,lo),(x1,y1,hi),(x0,y0,hi),
                      (u0,v0),(u1,v0),(u1,v1),(u0,v1),material)
        return
    dx, dy = direction
    along = np.column_stack((left, right, right, left))
    height = np.column_stack((bottom, bottom, top, top))
    points = np.empty((count, 4, 3))
    points[:,:,0] = a[0] + dx*along + dy*.018
    points[:,:,1] = a[1] + dy*along - dx*.018
    points[:,:,2] = height
    u0,u1,v0,v1 = b.WIN_UV
    uv = np.tile(((u0,v0),(u1,v0),(u1,v1),(u0,v1)), (count,1))
    start = mesh.n
    mesh.P.extend(points.ravel());mesh.UV.extend(uv.ravel())
    mesh.C.extend(np.tile(material[1], count*4).astype(np.uint8))
    mesh.T.extend((np.arange(count)[:,None]*4 + np.array((0,1,2,0,2,3)) + start).ravel())
    mesh.M.extend(np.full(count*2,material[0],np.int64))
    mesh.n += count*4


def draw(mesh, spec, gmin, gmax):
    import buildings as b
    from . import materials, regional_architecture as regional, regional_blocks, roofs
    from . import fast_facade
    from .geometry import horizontal
    from .regional_supports import draw as supports
    fp = spec.footprint
    mats = b._Looks(spec.seed)
    garage_material = mats[b.custom_look(b.SHUTTER,materials.garage_colour(spec.seed))] if spec.garage_opening else None
    base = b.base_z(spec,gmin,gmax)+(spec.min_h or 0.)
    bottom = gmin-b.SKIRT_LITE_M if (spec.min_h or 0.)<=.5 else base
    top = base+spec.height
    recipe = spec.inference.selection.preset
    width,bay,profile = regional.window_parameters(spec,recipe.window_width,recipe.bay)
    lower,upper = regional.wall_materials(spec,profile,mats,mats[spec.facade])
    block = regional_blocks.profile(spec)
    if block:
        looks = regional_blocks.wall_looks(spec,block)
        lower,upper = mats[looks[0]],mats[looks[1]]
    su,sv = materials.wall_scale(spec.inference.facade.value)
    sill = min(.8,spec.floor_h*.27)
    height = min(1.65,spec.floor_h-sill-.4)
    if profile:
        sill,height = regional.window_vertical(spec,profile,min(profile['sill'],spec.floor_h*.30),
                                               min(profile['window_height'],spec.floor_h-.8))
    glass = spec.inference.facade.value == 'glass'
    supports(mesh,spec,gmin,gmax,mats[spec.facade])
    for boundary,ring in enumerate((fp.outer,*fp.holes)):
        for edge,(a,c) in enumerate(zip(ring,ring[1:]+ring[:1])):
            length = math.dist(a,c)
            if length < 1e-9:continue
            dx,dy = (c[0]-a[0])/length,(c[1]-a[1])/length
            def wall(lo,hi,material):
                mesh.quad((*a,lo),(*c,lo),(*c,hi),(*a,hi),
                          (0,(lo-base)/sv),(length/su,(lo-base)/sv),
                          (length/su,(hi-base)/sv),(0,(hi-base)/sv),material)
            if glass:
                # A single repeating pane/mullion tile, not a four-storey atlas
                # compressed into each storey. Retain the selected glass tint.
                token=(b.MATERIALS.index('bne_minimum_glass'),mats[spec.facade][1])
                mesh.quad((*a,bottom),(*c,bottom),(*c,top),(*a,top),
                          (0,(bottom-base)/spec.floor_h),(length/3.25,(bottom-base)/spec.floor_h),
                          (length/3.25,spec.height/spec.floor_h),(0,spec.height/spec.floor_h),token)
            else:
                split = min(top,base+spec.floor_h)
                if lower != upper and split < top:
                    wall(bottom,split,lower);wall(split,top,upper)
                else:wall(bottom,top,upper)
            if not glass and spec.windows is not False and not spec.plain and height>.4:
                n = max(0,int((length-.9)/max(bay,width+.8)))
                if not n and length>=width+.9:n=1
                if profile:
                    share=regional.glazing_share(profile,front=boundary==0 and edge==spec.front)
                    n=min(n,max(1,int(length*spec.floor_h*share/max(width*height,1e-6))))
                if n:
                    # Upper storeys share one masked, repeating window grid per
                    # elevation. Ground-floor panes retain exact door clearance.
                    rows = spec.floors
                    if rows > 2 and enabled():
                        pattern = profile.get('opening_pattern') if profile else None
                        kind = {'vertical':'tall','horizontal':'wide','grouped':'wide'}.get(pattern,'sash')
                        if spec.cls in ('office','commercial'):kind='modern'
                        token=(b.MATERIALS.index('bne_minimum_'+kind),(255,255,255,255))
                        lo=base+spec.floor_h
                        a1=(a[0]+dy*.018,a[1]-dx*.018)
                        c1=(c[0]+dy*.018,c[1]-dx*.018)
                        mesh.quad((*a1,lo),(*c1,lo),(*c1,top),(*a1,top),
                                  (0,0),(n,0),(n,rows-1),(0,rows-1),token)
                        rows=1
                    centres=(np.arange(n)+.5)*length/n
                    left=np.tile(centres-width/2,rows)
                    right=left+width
                    z=np.repeat(np.arange(rows)*spec.floor_h+sill,n)+base
                    reserved=fast_facade.reservations(spec,boundary,edge,base,gmax)
                    keep=fast_facade.window_mask(left,right,z,height,top,reserved)
                    _windows(mesh,a,(dx,dy),left[keep],right[keep],z[keep],z[keep]+height,mats['bne_bld_fac_white'])
            if boundary==0 and spec.garage_opening and edge==spec.garage_opening[0]:
                _,centre,w,h=spec.garage_opening
                gz=spec.access.garage_z if spec.access and spec.access.garage_z is not None else base
                def at(s,z):return (a[0]+dx*s+dy*.02,a[1]+dy*s-dx*.02,z)
                mesh.quad(at(centre-w/2,gz),at(centre+w/2,gz),at(centre+w/2,gz+h),at(centre-w/2,gz+h),
                          (0,0),(1,0),(1,1),(0,1),garage_material)
    if spec.roof != 'flat':roofs.draw(mesh,spec,top,mats,overhang=False)
    else:
        from . import regional_roof_details as details
        horizontal(mesh,fp,top-(.9 if details.recessed_deck(spec) else 0.),mats[spec.roof_mat],b.ROOF_UV_M)
        details.draw(mesh,spec,top,details.looks(spec,mats))
    if (spec.min_h or 0.)>.5:horizontal(mesh,fp,bottom,mats[spec.facade],down=True)
    if spec.access:
        from .access import draw as access
        access(mesh,spec,False,detail=False)
    if getattr(spec, 'physical_mode', None) == 'standard':
        # Accepted projected bays remain visible through a Minimum downgrade.
        # Their closed physical faces are already anchored in the frozen layout;
        # this emits only the required silhouette, without decorative railings.
        from .regional_facade_details import draw_collision_bays
        draw_collision_bays(mesh,spec,gmin,gmax,mats[spec.facade])
