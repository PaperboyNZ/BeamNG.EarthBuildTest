"""Fitted bay glazing, balconies, verandas, awnings and half-timber framing.

Assemblies use existing apertures; bays and awnings can project modestly where
street clearance permits. Covered porches use validated access landings.
"""
from dataclasses import replace
import numpy as np
from . import architectural_modifiers as modifiers


def compose(spec, elevation):
    if elevation.boundary or not spec.inference:
        return elevation
    # Reserve parapet headroom on every elevation, including side/rear windows.
    if spec.roof=='flat' and (modifiers.has(spec,'roof_terrace') or modifiers.has(spec,'water_tanks')):
        rows=[replace(o,top=min(o.top,spec.height-1.05)) if o.kind=='window' and o.floor==spec.floors-1 else o for o in elevation.openings]
        elevation=replace(elevation,openings=tuple(o for o in rows if o.top-o.bottom>=.5))
    front = spec.front if spec.front is not None else 0
    if elevation.edge != front:
        return elevation
    rows = list(elevation.openings)
    balcony = 'timber_balcony' if modifiers.has(spec, 'timber_balconies') else 'iron_balcony' if modifiers.has(spec, 'iron_balconies') else ''
    # Select by floor/position, not by mutable neighbour or tile order.
    for floor in range(min(3, spec.floors)):
        candidates = sorted((o for o in rows if o.kind == 'window' and o.floor == floor), key=lambda o:o.left)
        if not candidates:
            continue
        assembly = ('veranda' if floor == 0 and modifiers.has(spec, 'veranda') else
                    balcony if floor > 0 and balcony else
                    'bay' if modifiers.has(spec, 'bay_windows') else '')
        if not assembly:
            continue
        group = candidates[:1]
        if assembly in ('veranda', 'timber_balcony', 'iron_balcony') and len(candidates)>1:
            a,b=candidates[:2]
            if b.right-a.left<=5.8 and b.left-a.right<1.7 and not any(
                    o.kind!='window' and o.left<b.right and o.right>a.left and o.floor==floor for o in rows):
                group.append(b)
        first=group[0];right=group[-1].right
        low = floor*spec.floor_h+.18 if assembly!='bay' else first.bottom
        # A gallery changes sill/depth, while the original row's window heads
        # remain aligned across the elevation.
        high = first.top
        op=replace(first,right=right,bottom=low,top=high,assembly='regional_'+assembly,
                   depth=1.1 if assembly=='veranda' else .85 if balcony else .55)
        rows=[o for o in rows if o not in group]+[op]
    return replace(elevation,openings=tuple(sorted(rows,key=lambda o:(o.floor,o.left))))


def draw_opening(mesh,spec,op,at,quad,body,trim,window,lite=False):
    if not op.assembly.startswith('regional_'):
        return False
    import buildings as b
    kind=op.assembly.removeprefix('regional_')
    l,r,lo,hi=op.left,op.right,op.bottom,op.top
    width=r-l;back=-float(op.depth)
    uv=((0.,0.),(1.,0.),(1.,1.),(0.,1.))
    u0,u1,v0,v1=b.WIN_UV; glass_uv=((u0,v0),(u1,v0),(u1,v1),(u0,v1))
    def face(points,material,tex=uv):mesh.quad(*points,*tex,material)
    def rail(a,c,z0,z1,depth,material=trim):
        quad(a,c,z0,z1,material,depth)
        if not lite:
            p=((a,z0),(c,z0),(c,z1),(a,z1))
            for x,y in zip(p,p[1:]+p[:1]):face((at(*x,depth),at(*y,depth),at(*y,depth-.05),at(*x,depth-.05)),material)
    if kind=='bay':
        # Three glazed faces: a broad front with angled returns and closed
        # sill/head. Fit in the source opening rather than guessing plot space.
        inset=min(.32,width*.18)
        projection=0. if 'footprint_clipped_clear_of_street' in (spec.diagnostics or ()) else .30
        corners=((l,back),(l+inset,projection),(r-inset,projection),(r,back))
        for (a,da),(c,dc) in zip(corners,corners[1:]):
            face((at(a,lo,da),at(c,lo,dc),at(c,hi,dc),at(a,hi,da)),window,glass_uv)
            rail(a-.035,a+.035,lo,hi,da+.025)
        rail(r-.035,r+.035,lo,hi,back+.025)
        for z,order in ((lo,tuple(reversed(corners))),(hi,corners)):
            face(tuple(at(x,z,d) for x,d in order),body)
        rail(l,r,lo-.08,lo,.025);rail(l,r,hi,hi+.08,.025)
        return True
    # Deep covered galleries provide actual jambs, floor, soffit and back wall.
    quad(l,r,lo,lo+.22,body,back)
    quad(l,r,lo+.22,hi,window,back,glass_uv)
    for points in ((at(l,lo),at(r,lo),at(r,lo,back),at(l,lo,back)),
                   (at(l,hi,back),at(r,hi,back),at(r,hi),at(l,hi)),
                   (at(l,lo,back),at(l,hi,back),at(l,hi),at(l,lo)),
                   (at(r,lo),at(r,hi),at(r,hi,back),at(r,lo,back))):face(points,body)
    timber=kind in ('timber_balcony','veranda')
    structure=b._Looks(spec.seed)[b.custom_look(b.SIDING,(.36,.25,.16))] if timber else \
              b._Looks(spec.seed)[b.custom_look(b.METALWALL,(.13,.15,.16))]
    rail(l-.05,r+.05,lo-.08,lo,.035,structure)
    if kind=='veranda':
        n=min(4,max(2,round(width/2.4)+1))
        for x in np.linspace(l+.07,r-.07,n):rail(x-.065,x+.065,lo,hi,.025,structure)
        rail(l,r,hi-.15,hi,.03,structure)
    else:
        rail(l,r,lo+.98,lo+1.06,.035,structure)
        rail(l,r,lo+.15,lo+.21,.035,structure)
        count=min(24,max(4,round(width/(.25 if timber else .18))))
        for x in np.linspace(l+.07,r-.07,count):
            thickness=.045 if timber else .016
            rail(x-thickness,x+thickness,lo+.21,lo+.98,.025,structure)
    return True


def draw_surface_details(mesh,spec,elevation,at,quad,mats,lite=False):
    if elevation.boundary or not spec.inference:
        return
    import buildings as b
    uv=((0.,0.),(1.,0.),(1.,1.),(0.,1.))
    if modifiers.has(spec,'awnings'):
        fabric=mats[b.custom_look(b.PANEL,(.64,.37,.22))]
        for op in [o for o in elevation.openings if o.kind=='window'][:4]:
            l,r,z=op.left,op.right,op.top-.04
            # Sheltered fabric canopy fits into the recessed window reveal.
            back=-max(.18,min(.48,op.depth or .30))
            front=.025 if 'footprint_clipped_clear_of_street' in (spec.diagnostics or ()) else .45
            mesh.quad(at(l,z+.13,back),at(r,z+.13,back),at(r,z-.16,front),at(l,z-.16,front),*uv,fabric)
            quad(l,r,z-.30,z-.16,fabric,front)
    if not modifiers.has(spec,'half_timber'):
        return
    from shapely.geometry import box,LineString
    from shapely.ops import unary_union
    from .topology import Footprint,triangles
    occupied=box(.07,.25,elevation.length-.07,spec.height-.08)
    holes=[box(o.left-.10,o.bottom-.10,o.right+.10,o.top+.10) for o in elevation.openings]
    if holes:occupied=occupied.difference(unary_union(holes))
    timber=mats[b.custom_look(b.SIDING,(.20,.12,.065))]
    width=elevation.length; beams=[]
    for floor in range(min(3,spec.floors)):
        lo=max(.35,floor*spec.floor_h+.07)
        hi=min(spec.height-.18,(floor+1)*spec.floor_h-.07)
        beams.extend([((.16,lo),(width-.16,lo),.09,True),
                      ((.16,hi),(width-.16,hi),.09,True)])
        spans=sorted((max(.25,o.left-.12),min(width-.25,o.right+.12))
                     for o in elevation.openings if o.bottom<hi and o.top>lo)
        gaps=[];cursor=.25
        for left,right in spans:
            if left>cursor:gaps.append((cursor,left))
            cursor=max(cursor,right)
        if cursor<width-.25:gaps.append((cursor,width-.25))
        for index,(left,right) in enumerate(gaps):
            if right-left<.25:continue
            if right-left>=1.0:
                beams.extend([((left+.09,lo),(left+.09,hi),.075,False),
                              ((right-.09,lo),(right-.09,hi),.075,False)])
                if not lite:
                    ends=((left+.12,lo+.08),(right-.12,hi-.08)) if index%2==0 else \
                         ((right-.12,lo+.08),(left+.12,hi-.08))
                    beams.append((*ends,.065,False))
            else:
                x=(left+right)/2
                beams.append(((x,lo),(x,hi),.08,False))
    for x in (.16,width-.16):beams.append(((x,.35),(x,spec.height-.18),.09,True))
    for a,c,half,clip in beams[:48]:
        strip=LineString((a,c)).buffer(half,cap_style='flat')
        if clip:strip=strip.intersection(occupied)
        elif not occupied.covers(strip):continue
        parts=[strip] if strip.geom_type=='Polygon' else getattr(strip,'geoms',())
        for part in parts:
            if part.geom_type!='Polygon' or part.area<.04:continue
            for tri in triangles(Footprint(part.exterior.coords,tuple(h.coords for h in part.interiors))):
                mesh.tri(*(at(s,z,.055) for s,z in tri),*((s/3,z/3) for s,z in tri),timber)


def bay_faces(spec,gmin,gmax):
    """Closed projected bay fronts for physics and occupancy checks."""
    if not modifiers.has(spec,'bay_windows') or 'footprint_clipped_clear_of_street' in (spec.diagnostics or ()):
        return ()
    import buildings as b
    from . import facades
    layout=spec.facades or facades.plan(spec,gmin,gmax)
    base=b.base_z(spec,gmin,gmax)+(spec.min_h or 0.)
    result=[]
    for e in layout.elevations:
        if e.boundary:continue
        a=np.array(spec.ring[e.edge]);d=np.array(spec.ring[(e.edge+1)%len(spec.ring)])-a
        d/=np.linalg.norm(d);n=np.array((d[1],-d[0]))
        for o in e.openings:
            if o.assembly!='regional_bay':continue
            inset=min(.32,(o.right-o.left)*.18)
            ring=[a+d*s+n*t for s,t in ((o.left,0.),(o.left+inset,.30),(o.right-inset,.30),(o.right,0.))]
            faces=[tuple((*p,base+o.bottom) for p in reversed(ring)),tuple((*p,base+o.top) for p in ring)]
            faces += [((*p,base+o.bottom),(*q,base+o.bottom),(*q,base+o.top),(*p,base+o.top)) for p,q in zip(ring,ring[1:]+ring[:1])]
            result.append(tuple(faces))
    return tuple(result)


def draw_gable_frame(mesh,spec,top,mats):
    if not modifiers.has(spec,'half_timber') or spec.roof!='gabled':return
    from . import roofs,attics,roof_edges
    if roofs.variant(spec)!='standard':return
    from shapely.geometry import Polygon,LineString,box
    from .topology import Footprint,triangles
    import buildings as b
    roof=roofs.for_spec(spec);rise=spec.inference.roof_rise
    if rise<.7:return
    timber=mats[b.custom_look(b.SIDING,(.20,.12,.065))]
    windows=attics.plan(spec)[0]
    for a,c in zip(spec.footprint.outer,spec.footprint.outer[1:]+spec.footprint.outer[:1]):
        a,c=np.array(a),np.array(c);length=float(np.linalg.norm(c-a));d=(c-a)/length
        if roof_edges.height(roof,(a+c)/2)*rise<rise*.8:continue
        normal=np.array((d[1],-d[0]));mid=length/2
        face=Polygon(((0.,0.),(length,0.),(mid,rise)))
        for w in windows:
            xy=np.array(w.centre)-a
            if abs(float(xy@normal))<.03:
                s=float(xy@d);face=face.difference(box(s-w.width/2-.10,w.bottom-.10,s+w.width/2+.10,w.bottom+w.height+.10))
        beams=(((.05,.04),(length-.05,.04)),((mid,.04),(mid,rise-.06)),
               ((.10,.10),(mid,rise-.10)),((mid,rise-.10),(length-.10,.10)))
        for pa,pb in beams:
            shape=LineString((pa,pb)).buffer(.075,cap_style='flat').intersection(face)
            parts=[shape] if shape.geom_type=='Polygon' else getattr(shape,'geoms',())
            for part in parts:
                if part.geom_type!='Polygon' or part.area<.01:continue
                for tri in triangles(Footprint(part.exterior.coords,tuple(h.coords for h in part.interiors))):
                    points=[(*tuple(a+d*s+normal*.058),top+z) for s,z in tri]
                    mesh.tri(*points,*((s/3,z/3) for s,z in tri),timber)


def draw_collision_bays(mesh,spec,gmin,gmax,material):
    for faces in bay_faces(spec,gmin,gmax):
        for face in faces:mesh.quad(*face,(0,0),(1,0),(1,1),(0,1),material)


def bay_boxes(spec,gmin,gmax,x0,y0):
    for faces in bay_faces(spec,gmin,gmax):
        p=np.array([v for face in faces for v in face]);ring=faces[1]
        yield [float(p[:,0].min()+x0),float(p[:,1].min()+y0),float(p[:,2].min()),
               float(p[:,0].max()+x0),float(p[:,1].max()+y0),float(p[:,2].max()),
               [[[float(x+x0),float(y+y0)] for x,y,_ in ring]]]
