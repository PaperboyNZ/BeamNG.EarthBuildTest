"""Bounded vehicle kerb profiles; retain a level rear strip wherever width permits."""
import numpy as np
FLARE=1.2
WALK_CLEAR=1.2
MIN_WIDTH=1.5


def section(w,h,amount,lip=None):
    import sidewalks as s
    lip=s.RAMP_H if lip is None else lip
    rr=min(1.8,w-WALK_CLEAR) if w >= 2.4 else w-.1
    length=rr-s.CURB_W
    ease=min(.2,length*.15)
    full=s.profile(h,w)
    xs=np.unique(np.r_[full[:,0],s.CURB_W+ease,rr-ease,rr])
    z0,z1=lip,h+rr*s.CROSS_SLOPE
    gradient=(z1-z0-ease*s.CROSS_SLOPE/2)/(length-ease)
    x=xs-s.CURB_W
    z=np.where(x<ease,z0+gradient*x*x/(2*ease),z0+gradient*(x-ease/2))
    tail=np.maximum(0.,x-(length-ease))
    z=np.where(x>length-ease,z0+gradient*(length-1.5*ease)+gradient*tail+
               (s.CROSS_SLOPE-gradient)*tail*tail/(2*ease),z)
    z=np.where(xs>=rr,h+xs*s.CROSS_SLOPE,z)
    f=lip/h if h > 0 else 0.
    vehicle=np.array([[0,-s.SINK],[s.BATTER*f,lip-s.NOSE*f],
                      [s.NOSE_W*f,lip],[s.CURB_W,lip]])
    front=xs<=s.CURB_W
    z[front]=np.interp(xs[front],vehicle[:,0],vehicle[:,1])
    z[-1]=-s.SINK
    normal=np.interp(xs,full[:,0],full[:,1])
    return np.column_stack((xs,normal*(1-amount)+z*amount))


def add(builder,curb,out,w,h,caps,ramps,slab,ranges,verge=False,texture_path=None):
    curb,out=np.asarray(curb,float),np.asarray(out,float)
    arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(curb[:,:2],axis=0),axis=1))]
    total=arc[-1]
    import sidewalks as sw
    texture_path = (curb, out) if texture_path is None else texture_path
    ranges=sorted((max(0.,row[0]-FLARE),max(0.,row[0]),min(total,row[1]),min(total,row[1]+FLARE),
                   row[2] if len(row)>2 else sw.RAMP_H) for row in ranges
                  if len(row)>=2 and np.isfinite(row).all() and row[1]>row[0] and row[1]>0 and row[0]<total)
    merged=[]
    for row in ranges:
        if merged and row[0]<=merged[-1][3]:
            old=merged[-1];merged[-1]=(old[0],old[1],max(old[2],row[2]),max(old[3],row[3]),min(old[4],row[4]))
        else:merged.append(row)
    def interp(values,stations):
        return np.column_stack([np.interp(stations,arc,values[:,i]) for i in range(values.shape[1])])
    def normal(a,b):
        if b-a<1e-6:return
        at=np.r_[a,arc[(arc>a)&(arc<b)],b]
        builder.add_run(interp(curb,at),interp(out,at),w,h,
                        (caps[0] if a==0 else False,caps[1] if b==total else False),
                        [(max(a,x)-a,min(b,y)-a) for x,y in ramps if y>a and x<b],slab,verge=verge,
                        texture_path=texture_path)
    previous=0.
    for a,b,c,d,lip in merged:
        normal(previous,a)
        at=np.unique(np.r_[np.linspace(a,b,7),np.linspace(c,d,7),arc[(arc>a)&(arc<d)]])
        centre,direction=interp(curb,at),interp(out,at)
        normal_profile=section(w,h,0.,lip)
        profile_delta=section(w,h,1.,lip)-normal_profile
        positions=[]
        for distance,p,n in zip(at,centre,direction):
            amount=min(1.,(distance-a)/max(b-a,1e-8),(d-distance)/max(d-c,1e-8))
            if b<=distance<=c:amount=1.
            amount=amount*amount*(3.-2.*amount)
            prof=normal_profile+max(0.,amount)*profile_delta
            positions.append(np.c_[p[:2]+prof[:,0,None]*n,p[2]+prof[:,1]])
        P=np.concatenate(positions)-builder.origin
        cols=len(positions[0])
        indices=(np.arange(len(at)-1)[:,None]*cols+np.arange(cols-1)).ravel()
        T=np.stack((np.column_stack((indices,indices+cols,indices+cols+1)),
                    np.column_stack((indices,indices+cols+1,indices+1))),axis=1).reshape(-1,3)
        a1=P[T[:,1],:2]-P[T[:,0],:2];a2=P[T[:,2],:2]-P[T[:,0],:2]
        reverse=a1[:,0]*a2[:,1]-a1[:,1]*a2[:,0]<0
        T[reverse]=T[reverse,::-1]
        M=np.tile(np.repeat([0 if col<3 or col==cols-2 else slab for col in range(cols-1)],2),len(at)-1)
        builder.vehicle_meshes.append((P,T,P[:,:2]/3.,M))
        # Material boundaries need independent UVs. Reusing pavement XY UVs
        # on the curb sampled painted bands at random across every driveway.
        curb_tri=M==0
        vertices=np.unique(T[curb_tri])
        remap=np.zeros(len(P),dtype=np.int64)
        remap[vertices]=len(P)+np.arange(len(vertices))
        visual_t=T.copy();visual_t[curb_tri]=remap[T[curb_tri]]
        band=np.full(cols,sw.V_BAND_TOP)
        band[:4]=[sw.V_BAND_LOW,sw.V_LIGHT_LOW,sw.V_BAND_TOP-.02,sw.V_BAND_TOP]
        band[-2:]=[sw.V_LIGHT_LOW,sw.V_BAND_LOW]
        curb_uv=np.c_[at[vertices//cols]/sw.CURB_REPEAT_M,band[vertices%cols]]
        surface_uv = np.c_[np.repeat(at+sw.path_station(curb[0],texture_path),cols),
                           np.tile(normal_profile[:,0],len(at))]
        builder.vehicle_visuals.append((np.vstack((P,P[vertices])),visual_t,
                                        np.vstack((surface_uv,curb_uv)),M))
        previous=d
    normal(previous,total)
    builder._built=None


def combine(mesh,extra):
    if not extra:return mesh
    P,T,UV,M=map(np.asarray,mesh)
    ps=[P];ts=[T];uvs=[UV];ms=[M];off=len(P)
    for p,t,uv,m in extra:
        ps.append(p);ts.append(t+off);uvs.append(uv);ms.append(m);off+=len(p)
    return tuple(np.concatenate(a) for a in (ps,ts,uvs,ms))
