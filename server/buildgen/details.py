"""Small closed construction details, separate from primary collision shells."""
from runtimeprofiler import step as profile_step
import math
import numpy as np


UV=((0.,0.),(1.,0.),(1.,1.),(0.,1.))


def beam(mesh,a,c,radius,mat,sides=8):
    """Capped polygonal tube; a stable frame handles vertical downpipes too."""
    from .components import beam as stamp
    stamp(mesh,a,c,radius,mat,sides)


def seam(mesh,a,c,width,mat):
    """A narrow surface groove representation, not a raised rod."""
    a,c=np.asarray(a,dtype=float),np.asarray(c,dtype=float)
    d=c[:2]-a[:2]
    length=float(np.linalg.norm(d))
    if length<1e-7:
        return
    n=np.array([-d[1],d[0],0.])*width/(2*length)
    mesh.quad(a-n,c-n,c+n,a+n,*UV,mat)


def corners(mesh,spec,base,layout,mats):
    """Mitered corner boards on lightweight cladding; no painted brick quoins."""
    if spec.inference.facade.value not in ('wood','metal'):
        return
    from . import regional_architecture as regional
    profile=regional.for_spec(spec)
    if (profile and profile['massing_grammar'] in ('timber_veranda','alpine_timber','east_asian_timber')
            and spec.inference.facade.value=='wood' and spec.inference.use.value=='residential'
            and spec.floors<=3 and spec.height<=11.5 and spec.footprint.is_rectangle()):
        return # planned, opening-aware corner boards already wrap these corners
    mat=mats[layout.trim]
    for ring in (spec.footprint.outer,*spec.footprint.holes):
        for i,p in enumerate(ring):
            p=np.asarray(p)
            before=p-np.asarray(ring[i-1]); after=np.asarray(ring[(i+1)%len(ring)])-p
            l0,l1=np.linalg.norm(before),np.linalg.norm(after)
            if min(l0,l1)<.6:
                continue
            u,v=before/l0,after/l1
            cross=u[0]*v[1]-u[1]*v[0]
            if cross<.7: # convex corners only; skip acute and internal returns
                continue
            n0,n1=np.array([u[1],-u[0]]),np.array([v[1],-v[0]])
            miter=(n0+n1)*.02/(1.+float(n0@n1))
            # Six-point L section returns to the cladding at both ends. Both
            # legs use the same miter vertex, preventing a bright corner crack.
            section=[p-u*.12,p-u*.12+n0*.02,p+miter,p+v*.12+n1*.02,p+v*.12,p]
            z0,z1=base+.28,base+spec.height-.03
            if z1<=z0:
                continue
            for a,c in zip(section,section[1:]+section[:1]):
                mesh.quad((*a,z0),(*c,z0),(*c,z1),(*a,z1),*UV,mat)
            # Triangulate the cap rather than filling the concave L with a fan.
            from .topology import Footprint,triangles
            for t in triangles(Footprint(tuple(tuple(p) for p in section))):
                mesh.tri(*[(*p,z1) for p in t],(0.,0.),(1.,0.),(1.,1.),mat)
                mesh.tri(*[(*p,z0) for p in t[::-1]],(0.,0.),(1.,0.),(1.,1.),mat)


def roof_seams(spec,top):
    """Folded ridge/hip caps and valleys from adjacent analytical roof planes."""
    from shapely.geometry import Polygon
    from .roofs import envelope
    from .roofs import for_spec
    roof=for_spec(spec)
    edges={}
    for tri,pid in zip(roof.triangles,roof.triangle_planes):
        for p,q in zip(tri,tri[1:]+tri[:1]):
            key=tuple(sorted((tuple(round(v,7) for v in p[:2]),tuple(round(v,7) for v in q[:2]))))
            edges.setdefault(key,[]).append((pid,np.mean(np.asarray(tri)[:,:2],axis=0)))
    seams=[]
    rise=spec.inference.roof_rise
    occupied=spec.footprint.shape().buffer(1e-8)
    for (pa,pb),sides in sorted(edges.items()):
        if len(sides)!=2 or sides[0][0]==sides[1][0]:
            continue
        a,c=np.asarray(pa),np.asarray(pb)
        d=c-a; length=float(np.linalg.norm(d))
        if length<.6:
            continue
        d/=length
        mid=(a+c)/2
        normals=[]
        for pid,centroid in sides:
            n=centroid-mid-d*float((centroid-mid)@d)
            norm=float(np.linalg.norm(n))
            if norm<1e-8:
                break
            normals.append(n/norm)
        if len(normals)!=2:
            continue
        slopes=[float(np.asarray(roof.planes[pid][:2])@n) for (pid,_),n in zip(sides,normals)]
        if max(slopes)<-1e-6:
            kind='ridge_cap'
        elif min(slopes)>1e-6:
            kind='valley_flashing'
        else:
            continue
        # Trim ends to keep folded sheets off neighbouring eaves/courtyard voids.
        a,c=a+d*.12,c-d*.12
        width=min(.09,length*.08)
        for (pid,_),n in zip(sides,normals):
            xy=[a,c,c+n*width,a+n*width]
            if not occupied.covers(Polygon(xy)):
                break
        else:
            panels=[]
            for (pid,_),n in zip(sides,normals):
                normal=np.array(roof.planes[pid][:2]); offset=roof.planes[pid][2]
                xy=[a,c,c+n*width,a+n*width]
                q=[]
                for i,p in enumerate(xy):
                    roof_z=top+(float((p-np.asarray(roof.centre))@normal)+offset)*rise/roof.peak
                    q.append((*tuple(p),min(top+rise,roof_z+(.002 if i<2 else .006))))
                if np.cross(np.r_[xy[1]-xy[0],0.],np.r_[xy[2]-xy[0],0.])[2]<0:
                    q.reverse()
                panels.append(tuple(q))
            seams.append((kind,tuple(panels)))
        if len(seams)>=64:
            break
    return tuple(seams)


@profile_step('Building roof flashing')
def roof_caps(mesh,spec,top,mats):
    import buildings as b
    from .materials import roof_scale
    if spec.footprint.vertex_count>64 or spec.footprint.is_rectangle():
        # On simple roofs the 2â€“6 mm folded overlays duplicate the existing
        # roof-covering normal maps and hard plane crease. Preserve actual roof
        # shape, fascia and gutters; retain explicit flashing on complex valleys.
        return
    for kind,panels in roof_seams(spec,top):
        mat=mats[spec.roof_mat] if kind=='ridge_cap' else mats[b.custom_look(b.METALWALL,(.46,.48,.49))]
        for p in panels:
            length=math.dist(p[0],p[1])
            scale=roof_scale(spec.inference.roof_material.value)[0]
            mesh.quad(*p,(0.,0.),(length/scale,0.),(length/scale,.05),(0.,.05),mat)


def eave_runs(roof):
    """Remove triangulation cuts from straight physical eave edges."""
    runs=[]
    for a,c in roof.boundary:
        if max(a[2],c[2])>1e-7:
            continue
        if runs and math.dist(runs[-1][1][:2],a[:2])<1e-7:
            old=np.subtract(runs[-1][1][:2],runs[-1][0][:2]); new=np.subtract(c[:2],a[:2])
            if abs(old[0]*new[1]-old[1]*new[0])<1e-7 and old@new>0:
                runs[-1]=(runs[-1][0],c)
                continue
        runs.append((a,c))
    return tuple(runs)



@profile_step('Building rainwater detail')
def rainwater(mesh,spec,top,mats,gmin,gmax,detail=True):
    """Gutter channels/outlets and wall-following downpipes on low pitched roofs.

Sizing is a visual recipe, not a catchment/rainfall capacity calculation. Downpipes
end at visible receiver collars; underground drainage remains unknown.
"""
    import buildings as b
    from . import roofs,facades
    if spec.floors>3 or spec.height>12. or spec.footprint.vertex_count>32:
        return
    layout=spec.facades or facades.plan(spec,gmin,gmax)
    mat=mats[layout.trim]
    rectangle=spec.footprint.is_rectangle()
    from . import roof_edges
    treatment=roof_edges.treatment(spec)
    roof=roof_edges.for_spec(spec)
    # Boundary spans with positive normalized height are gables, not gutters.
    count=0
    runs=eave_runs(roof)
    for pa,pb in runs:
        if abs(pa[2]-pb[2])>1e-7:continue
        base=top+pa[2]*spec.inference.roof_rise
        a,c=np.asarray(pa[:2]),np.asarray(pb[:2])
        length=float(np.linalg.norm(c-a))
        if not 1.5<=length<=30.:
            continue
        d=(c-a)/length; n=np.array([d[1],-d[0]])
        def miter(p,at_start):
            for qa,qb in runs:
                if at_start and math.dist(qb[:2],p)<1e-7:
                    v=np.subtract(qb[:2],qa[:2])
                elif not at_start and math.dist(qa[:2],p)<1e-7:
                    v=np.subtract(qb[:2],qa[:2])
                else:
                    continue
                v=v/np.linalg.norm(v); other=np.array([v[1],-v[0]])
                if float(n@other)>-.5:
                    return (n+other)/(1.+float(n@other)),True
            return n,False
        start_miter,start_join=miter(a,True)
        end_miter,end_join=miter(c,False)
        # Keep the channel rim below the roof edge, with a shallow U section.
        outlet=min(length*.5,treatment.eave+.25)
        # Choose a wall attachment clear of every door/window, trying both ends.
        attachment=None
        for position in (outlet,length-outlet):
            p=a+d*position
            ring=spec.footprint.outer
            matches=[]
            for edge,(wa,wc) in enumerate(zip(ring,ring[1:]+ring[:1])):
                wa,wc=np.asarray(wa),np.asarray(wc); wd=wc-wa
                wl=float(np.linalg.norm(wd)); wd/=wl
                along=float(np.clip((p-wa)@wd,0.,wl)); foot=wa+wd*along
                distance=float(np.linalg.norm(p-foot))
                openings=next((e.openings for e in layout.elevations if e.boundary==0 and e.edge==edge),())
                if distance<=max(.6,treatment.eave+.05) and not any(op.left-.1<along<op.right+.1 for op in openings):
                    matches.append((distance,edge,along,foot,np.array([wd[1],-wd[0]])))
            if matches:
                attachment=min(matches,key=lambda m:m[0])
                outlet=position
                break
        if attachment is None:
            continue
        if not detail:
            # Very High keeps the gutter/downpipe silhouette as closed beams;
            # Ultra adds the channel, falls, elbows, receiver and brackets.
            beam(mesh,(*a,base-.07),(*c,base-.07),.055,mat,sides=4)
            distance,edge,along,foot,normal=attachment
            pipe=foot+normal*.07
            ground=b.door_ground(spec,edge,along,gmax)
            if base-.13-ground >= .6:
                beam(mesh,(*pipe,base-.13),(*pipe,ground+.08),.04,mat,sides=4)
            count+=1
            if count>=12:break
            continue
        drop=.002*min(outlet,length-outlet)
        cuts=(0.,outlet,length)
        for s0,s1 in zip(cuts,cuts[1:]):
            def profile(s):
                # Adjacent corners share a datum; positive falls lead toward
                # this run's outlet. Hydraulic sizing is outside this recipe.
                z=base-.13-drop*(s/outlet if s<=outlet else (length-s)/(length-outlet))
                p=a+d*s
                normal=start_miter if s==0. else end_miter if s==length else n
                return [(*tuple(p+normal*w),zz) for w,zz in
                        ((0.,base-.025),(.012,base-.025),(.012,z+.012),(.10,z+.012),
                         (.10,base-.025),(.112,base-.025),(.112,z), (0.,z))]
            left,right=profile(s0),profile(s1)
            for i,j in zip(range(8),list(range(1,8))+[0]):
                mesh.quad(left[i],right[i],right[j],left[j],*UV,mat)
        # End stops close isolated gutter runs. The narrow seams at adjacent
        # segments are intentional; gutters are not drawn across a gable rake.
        for s in (0.,length):
            if (s==0. and start_join) or (s==length and end_join):
                continue
            p=a+d*s
            z=base-.13
            cap=[(*tuple(p+n*w),zz) for w,zz in ((0.,z),(.112,z),(.112,base-.025),(0.,base-.025))]
            mesh.quad(*(cap if s==length else cap[::-1]),*UV,mat)
        p=a+d*outlet
        distance,edge,along,foot,normal=attachment
        pipe=foot+normal*.07
        ground=b.door_ground(spec,edge,along,gmax)
        ztop=base-.13-drop
        if ztop-ground<.6:
            continue
        outlet_xy=p+n*.055
        beam(mesh,(*outlet_xy,ztop),(*outlet_xy,ztop-.15),.04,mat)
        beam(mesh,(*outlet_xy,ztop-.15),(*pipe,ztop-.38),.04,mat)
        beam(mesh,(*pipe,ztop-.38),(*pipe,ground+.08),.04,mat)
        # Visible receiver only: never discharge an elbow across the walking path.
        b._box(mesh,pipe,np.array([1.,0.]),.07,.07,ground+.015,ground+.09,mat)
        for z in np.arange(ground+.6,ztop-.4,1.6):
            beam(mesh,(*foot,float(z)),(*pipe,float(z)),.018,mat,sides=6)
        count+=1
        if count>=12:
            break
