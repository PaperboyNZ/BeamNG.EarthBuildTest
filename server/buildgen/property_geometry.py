"""Stage-one commercial architecture, fitted to existing openings and envelopes.

The six programmes change facade composition, never source footprint/use/height.
All projections are above the entrance and deep canopies require a known site.
Furniture and named panels are compiled separately by property_assets.
"""
import math
from functools import lru_cache
import numpy as np
from . import property_programme

UV = ((0., 0.), (1., 0.), (1., 1.), (0., 1.))


@lru_cache(maxsize=1024)
def _box_template(width,depth,height):
    from .components import _quads
    xy=[(x*width/2,y*depth/2) for x,y in ((-1,-1),(1,-1),(1,1),(-1,1))]
    low=[(x,0.,-y) for x,y in xy];high=[(x,height,-y) for x,y in xy]
    faces=[(low[i],low[(i+1)%4],high[(i+1)%4],high[i]) for i in range(4)]
    return _quads(faces+[tuple(high),tuple(low[::-1])])


def box(mesh, centre, tangent, width, depth, low, high, material):
    """Closed six-face prism; shared by architecture, props and asset export."""
    if hasattr(mesh,'queue_facade'):
        from .components import facade
        facade(mesh,_box_template(round(width,10),round(depth,10),round(high-low,10)),
               tuple(centre),tuple(tangent),low,0.,0.,material)
        return
    c=np.asarray(centre,float); u=np.asarray(tangent,float); v=np.array((-u[1],u[0]))
    xy=[c+u*x*width/2+v*y*depth/2 for x,y in ((-1,-1),(1,-1),(1,1),(-1,1))]
    bottom=[(*p,low) for p in xy]; top=[(*p,high) for p in xy]
    for i in range(4):
        j=(i+1)%4
        mesh.quad(bottom[i],bottom[j],top[j],top[i],*UV,material)
    mesh.quad(*top,*UV,material); mesh.quad(*bottom[::-1],*UV,material)


def frontage(spec):
    """Use only an accepted exterior frontage, including merged collinear runs."""
    if spec.front is None or spec.footprint is None or (spec.min_h or 0.)>.5:
        return None
    from . import commercial
    shared=commercial.derive_programme(spec)
    if shared is False:return None
    if shared:
        run=shared.run(0,spec.front)
        if run.party_wall:return None
        a,c=np.asarray(run.start),np.asarray(run.end)
        anchor=(spec.door[1]+run.member(spec.door[0]).start
                if spec.door and run.member(spec.door[0]) is not None else None)
        edge=run.edge
    else:
        a=np.asarray(spec.ring[spec.front]); c=np.asarray(spec.ring[(spec.front+1)%len(spec.ring)])
        anchor=spec.door[1] if spec.door and spec.door[0]==spec.front else None
        edge=spec.front
    length=float(np.linalg.norm(c-a))
    if length<3.:return None
    u=(c-a)/length
    return a,u,np.array((u[1],-u[0])),length,anchor,edge


def sign_slot(spec,gmin,gmax):
    """A bounded blank band above apertures; used by frame and exact name panel."""
    import buildings as b
    programme=property_programme.for_spec(spec); front=frontage(spec)
    if programme is None or front is None:return None
    a,u,n,length,anchor,edge=front
    base=b.base_z(spec,gmin,gmax)+(spec.min_h or 0.)
    layout=spec.facades
    if layout is None:
        from .facades import plan
        layout=plan(spec,gmin,gmax)
    elevation=next((e for e in layout.elevations if e.boundary==0 and e.edge==edge),None)
    ceiling=min(spec.height-.22,spec.floor_h-.10)
    if programme.kind=='trade_units':
        width=min(4.,length-1.3); centre=anchor if anchor is not None else length*.5
    elif programme.kind in ('hospital','clinic'):
        width=min(5.2,length-1.3); centre=anchor if anchor is not None else length*.5
    else:
        width=min(12. if programme.kind=='supermarket' else 8.,length-1.3); centre=length*.5
    centre=max(.65+width/2,min(length-.65-width/2,centre))
    # Choose a clear vertical interval for this particular panel. A trade unit
    # can have high clerestory glazing with a useful sign gap below it.
    blocked=sorted((o.bottom-.10,o.top+.12) for o in elevation.openings
                   if o.left<centre+width/2 and o.right>centre-width/2) if elevation else []
    low=2.6;gaps=[]
    for bottom,top in blocked:
        if bottom>low:gaps.append((low,min(bottom,ceiling)))
        low=max(low,top)
    if low<ceiling:gaps.append((low,ceiling))
    gaps=[(l,h) for l,h in gaps if h-l>=.22 and l<ceiling]
    if not gaps:return None
    low,high=max(gaps,key=lambda pair:min(.68,pair[1]-pair[0]))
    high=min(high,low+.68)
    return a+u*centre+n*.085,u,n,width,base+low,base+high


def draw(mesh,spec,gmin,gmax,lite=False):
    import buildings as b
    from .quality import current
    programme=property_programme.for_spec(spec)
    if programme is None or current().rank<1:return
    front=frontage(spec)
    if front is None:return
    a,u,n,length,anchor,edge=front
    mats=b._Looks(spec.seed)
    from .property_palette import resolve as palette
    background,_,highlight=palette(spec)
    dark=tuple(v/255 for v in background);pale=tuple(v/255 for v in highlight)
    accent=mats[b.custom_look(b.PANEL,dark)]; trim=mats[b.custom_look(b.PANEL,pale)]
    base=b.base_z(spec,gmin,gmax)+(spec.min_h or 0.)
    slot=sign_slot(spec,gmin,gmax)
    if slot:
        c,_,_,width,z0,z1=slot
        if current().rank==1:
            # Distant low-detail bands need only their visible face, not six
            # box surfaces, beveled trim or a rasterized text material.
            left=c-u*width/2+n*.075;right=c+u*width/2+n*.075
            mesh.quad((*left,z0),(*right,z0),(*right,z1),(*left,z1),*UV,accent)
            return
        box(mesh,c,u,width+.12,.14,z0-.045,z1+.045,accent)
        if not lite and current().rank>=3:
            box(mesh,c+n*.075,u,width+.14,.04,z1+.02,z1+.065,trim)
    if lite or current().rank<2:return
    layout=spec.facades
    if layout is None:
        from .facades import plan
        layout=plan(spec,gmin,gmax)
    elevation=next((e for e in layout.elevations if e.boundary==0 and e.edge==edge),None)
    if elevation is None:return
    ops=elevation.openings
    # Recognizable family details follow real aperture boundaries, not a second
    # independent door/window grid which could cover the accepted entry.
    if programme.kind in ('grocery_store','strip_shops','trade_units'):
        selected=[o for o in ops if o.floor==0 and o.kind in ('storefront','service')][:{2:4,3:8}.get(current().rank,12)]
        for op in selected:
            for x in (op.left-.08,op.right+.08):
                if .16<x<length-.16:
                    box(mesh,a+u*x+n*.045,u,.09,.09,base+op.bottom,base+op.top+.06,accent)
            if op.kind=='service':
                box(mesh,a+u*((op.left+op.right)/2)+n*.045,u,op.right-op.left+.20,.10,
                    base+op.top+.05,base+op.top+.16,trim)
    if programme.kind in ('clinic','hospital'):
        for op in [o for o in ops if o.kind in ('window','office')][:{2:6,3:12}.get(current().rank,24)]:
            width=op.right-op.left; centre=(op.left+op.right)/2
            if programme.kind=='clinic' and op.floor==0:
                # A shallow privacy band on the existing glazed opening.
                box(mesh,a+u*centre+n*.018,u,width,.025,base+op.bottom,
                    base+min(op.top,op.bottom+.55),trim)
            if programme.regional_style in ('japanese_urban','tropical_contemporary'):
                box(mesh,a+u*centre+n*.10,u,width+.10,.20,base+op.top+.04,base+op.top+.10,trim)
        # Hospital floor datums remain between the existing window apertures.
        # A small coherent colour accent reads at distance without inventing an
        # emergency department, helipad, wing or service entrance.
        if programme.kind=='hospital':
            for floor in range(1,min(8,spec.floors)):
                low=floor*spec.floor_h-.20;high=low+.12
                if not any(o.bottom<high and o.top>low for o in ops):
                    box(mesh,a+u*length/2+n*.035,u,length-.30,.07,base+low,base+high,accent)
    if anchor is None:return
    door=next((o for o in ops if o.kind in ('door','public_entry')),None)
    if door is None:return
    # Light entrance surround with clear door width and clear headroom.
    if programme.kind in ('clinic','hospital','supermarket'):
        for x in (door.left-.12,door.right+.12):
            box(mesh,a+u*x+n*.055,u,.13,.11,base+door.bottom,base+door.top+.18,accent)
    if 'awning' not in programme.decorations and not any(t in programme.decorations for t in ('entry_canopy','shared_canopy')):
        return
    z0=base+max(door.top+.25,2.8); z1=z0+.12
    if z1>base+spec.height-.18:return
    extension=1.2 if programme.variant in ('central_entry','street_entry','entrance','regular_bays') else .8
    width=min(length-1.3, max(3.,door.right-door.left+extension))
    centre=max(.65+width/2,min(length-.65-width/2,anchor))
    depth=.24
    # Substantial projecting cover needs confirmed available property ground.
    from shapely.geometry import Polygon
    from sitegen.surfaces import contains_known_site
    proposed=1.25 if programme.regional_style in ('nz_australia','tropical_contemporary') else .85
    corners=[a+u*(centre+x)+n*y for x,y in ((-width/2,0),(width/2,0),(width/2,proposed),(-width/2,proposed))]
    if spec.site is not None and contains_known_site(spec,Polygon(corners)):depth=proposed
    box(mesh,a+u*centre+n*depth/2,u,width,depth,z0,z1,accent)
    box(mesh,a+u*centre+n*(depth-.025),u,width,.05,z0-.08,z0,trim)
