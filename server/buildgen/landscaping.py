"""Identity-led cover and planting fitted to accepted soft landscape patches."""
from dataclasses import dataclass,replace
import math
import numpy as np
from . import materials

MAX_PLANTS=8
MAX_GROUNDCOVER_PATCHES=16
# Separate from the small residential frontage allowance. Commercial beds can
# be tens of metres long: retain a visible planted silhouette at both mesh LODs.
MAX_SITE_PLANTS=48
MAX_SITE_PLANTS_PER_BED=24


@dataclass(frozen=True, slots=True)
class Treatment:
    identity: str
    width: float
    margin: float
    covers: tuple
    concrete: tuple
    foliage: tuple
    plants: int


def treatment(spec):
    selection=spec.inference.selection
    use=spec.inference.use.value
    material=spec.inference.facade.value
    env=selection.environment
    # These are construction/landscape priors, not assertions about a country
    # or the planted species actually present at a reconstructed property.
    if use=='industrial':
        return Treatment('utility',1.2,.25,('gravel_margin','paved_margin','gravel_margin'),(.64,.65,.63),(.34,.40,.25),0)
    if use=='commercial':
        from .city import landscape_tint
        # Preserve accepted physical widths, cover choices and planting seeds.
        return Treatment('retail',1.6,.65,('garden_bed','paved_margin','lawn_margin'),landscape_tint(spec,(.72,.71,.67)),(.29,.42,.24),5)
    if env.kind in ('city_centre','town_centre','high_density_residential') or selection.preset.id in ('terrace','perimeter_block','urban_walkup'):
        return Treatment('urban',1.4,.38,('paved_margin','garden_bed','paved_margin'),(.67,.66,.62),(.27,.37,.23),3)
    if env.kind in ('rural','rural_residential') or selection.preset.id in ('small_cabin','rural_lowrise_home'):
        return Treatment('rural',1.2,.8,('lawn_margin','gravel_margin','lawn_margin'),(.67,.65,.58),(.36,.43,.25),4)
    if selection.climate_response=='cold_climate':
        return Treatment('cold',1.3,.48,('gravel_margin','garden_bed','paved_margin'),(.67,.68,.66),(.25,.36,.28),4)
    if selection.climate_response=='solar_shading':
        return Treatment('warm',1.4,.7,('garden_bed','paved_margin','garden_bed'),(.77,.73,.63),(.28,.44,.25),8)
    if material in ('brick','stone'):
        return Treatment('masonry',1.3,.65,('garden_bed','lawn_margin','paved_margin'),(.72,.68,.60),(.28,.39,.23),6)
    if material in ('concrete','glass','metal') and env.region!='nz_temperate':
        return Treatment('restrained',1.4,.5,('paved_margin','garden_bed','gravel_margin'),(.70,.71,.69),(.30,.40,.27),3)
    return Treatment('temperate',1.3,.85,('lawn_margin','garden_bed','lawn_margin'),(.73,.72,.67),(.30,.43,.25),7)


def margins(spec):
    profile=treatment(spec)
    # Independent side widths/kinds, stable under tile offsets and mesh LOD.
    return tuple((profile.margin*(.7+.3*materials.unit(spec.seed,f'land-margin-{side}')),
                  profile.covers[min(len(profile.covers)-1,int(materials.unit(spec.seed,f'land-cover-{side}')*len(profile.covers)))])
                 for side in (-1,1))


def site_candidates(spec,jobs):
    """At most four residual strips beside accepted path candidates, not courts."""
    profile=treatment(spec)
    result=[]
    for job in jobs:
        for kind,q in job['patches']:
            if kind not in ('site_path','site_walk'):continue
            # Long slab edges supply construction axes. Trim both ends so beds
            # do not round a junction into a crossing or a parking aisle.
            from shapely.geometry import Polygon
            if not Polygon(q).exterior.is_ccw:q=q[::-1]
            edges=sorted(zip(q,np.roll(q,-1,axis=0)),key=lambda e:-np.linalg.norm(e[1]-e[0]))[:2]
            for a,c in edges:
                d=c-a;length=float(np.linalg.norm(d))
                if length<3.:continue
                t=d/length;n=np.array([t[1],-t[0]])
                cap=4. if profile.identity=='utility' else 9.
                span=min(cap,length-1.)
                index=len(result)
                offset=.5+(length-1.-span)*materials.unit(spec.seed,f'site-bed-station-{index}')
                a=a+t*offset;c=a+t*span
                width=profile.margin*(.7+.3*materials.unit(spec.seed,f'site-bed-width-{index}'))
                cover='gravel_margin' if profile.identity=='utility' else profile.covers[index%len(profile.covers)]
                if cover=='paved_margin':cover='garden_bed'
                result.append((cover,np.array([a,c,c+n*width,a+n*width]),job))
                if len(result)>=(1 if profile.identity=='utility' else 4):return result
    return result


def trim_to_links(bands,linked):
    """Retain compact beds beside a replacement entrance link, not ghost paths.

    Trim along existing sampled strip edges. Their interpolation was already
    validated by sitework, so no new terrain query or polygon clipping is needed.
    """
    if not linked:return bands
    points=np.array([p[:2] for s in linked for p in s.top])
    result=[]
    for band in bands:
        p=np.array(band.top,float);d=p[1,:2]-p[0,:2];length=float(np.linalg.norm(d))
        if length<.1:continue
        reach=float(((points-p[0,:2])@(d/length)).max())+.5
        if reach<.2:continue
        if reach<length:
            u=reach/length
            p[1]=p[0]*(1-u)+p[1]*u;p[2]=p[3]*(1-u)+p[2]*u
            band=replace(band,top=tuple(tuple(map(float,q)) for q in p))
        result.append(band)
    return tuple(result)


def accepted_groundcover(spec, band, clear):
    """Detached decorative quad fitted to known extent and final reservations.

    The original planner supplies terrain/fill validation. This final commit
    checks the complete envelope and retained grade, rather than a bed centre.
    """
    from shapely.geometry import Polygon
    from sitegen.surfaces import contains_known_site
    points=np.asarray(band.top,float)
    if points.shape!=(4,3) or not np.isfinite(points).all() or not math.isfinite(band.bottom):return None
    polygon=Polygon(points[:,:2])
    if not polygon.is_valid or polygon.area<.01 or not contains_known_site(spec,polygon) or not clear(polygon):return None
    # All emitted cover quads have terrain-fitted edges. Keep the authored 25%
    # cap for optional groundcover; difficult terrain cannot become free land.
    for a,c in zip(points,np.roll(points,-1,axis=0)):
        length=float(np.linalg.norm(c[:2]-a[:2]))
        if length<1e-8 or abs(c[2]-a[2])/length>.25+1e-8:return None
    return replace(band,top=tuple(tuple(map(float,p)) for p in points),bottom=float(band.bottom))


def _patch_frame(top):
    """CCW convex quad with its longer pair of edges along the planting row."""
    p=np.asarray(top,float)
    if p.shape!=(4,3) or not np.isfinite(p).all():return None
    e=np.roll(p[:,:2],-1,axis=0)-p[:,:2]
    cross=e[:,0]*np.roll(e,-1,axis=0)[:,1]-e[:,1]*np.roll(e,-1,axis=0)[:,0]
    if np.all(cross < -1e-9):p=p[::-1]
    elif not np.all(cross > 1e-9):return None
    if np.linalg.norm(p[3,:2]-p[0,:2])>np.linalg.norm(p[1,:2]-p[0,:2]):p=np.roll(p,-1,axis=0)
    length=min(np.linalg.norm(p[1,:2]-p[0,:2]),np.linalg.norm(p[2,:2]-p[3,:2]))
    # Perpendicular distance, rather than side length, avoids oversizing shrubs
    # in strongly skewed accepted quads.
    axis=p[1,:2]-p[0,:2];axis/=np.linalg.norm(axis)
    normal=np.array([-axis[1],axis[0]])
    width=min(abs(normal@(p[3,:2]-p[0,:2])),abs(normal@(p[2,:2]-p[1,:2])))
    return p,float(length),float(width)


def _cover_height(p,xy):
    """Height on the same two planar triangles emitted by draw()."""
    for a,c,d in ((p[0],p[1],p[2]),(p[0],p[2],p[3])):
        e=c-a;f=d-a;r=np.asarray(xy)-a[:2]
        det=e[0]*f[1]-e[1]*f[0]
        s=(r[0]*f[1]-r[1]*f[0])/det
        t=(e[0]*r[1]-e[1]*r[0])/det
        if min(s,t,1-s-t)>=-1e-8:return float(a[2]+s*e[2]+t*f[2])
    return None


def _point(p,u,v):
    point=(1-u)*((1-v)*p[0]+v*p[3])+u*((1-v)*p[1]+v*p[2])
    point[2]=_cover_height(p,point[:2])
    return point


def _support_range(p,centre,radius):
    """Exact linear-height extrema over a circle intersecting the cover triangles.

    An upright stock model cannot follow the ground's tilt. Checking its whole
    native footprint lets us seat its low point and reject severe burial, rather
    than placing a horizontal base at the centre of a slope and leaving it afloat.
    """
    values=[];centre=np.asarray(centre,float)
    for tri in (p[[0,1,2]],p[[0,2,3]]):
        xy=tri[:,:2]
        plane=np.linalg.solve(np.c_[xy-centre,np.ones(3)],tri[:,2])
        candidates=[]
        def inside(q):
            e=np.roll(xy,-1,axis=0)-xy;r=q-xy
            return bool(np.all(e[:,0]*r[:,1]-e[:,1]*r[:,0]>=-1e-8))
        if inside(centre):candidates.append(centre)
        gradient=plane[:2];grade=float(np.linalg.norm(gradient))
        if grade>1e-12:
            for sign in (-1,1):
                q=centre+sign*radius*gradient/grade
                if inside(q):candidates.append(q)
        for a,b in zip(xy,np.roll(xy,-1,axis=0)):
            if np.linalg.norm(a-centre)<=radius+1e-9:candidates.append(a)
            v=b-a;w=a-centre;aa=v@v;bb=2*(v@w);cc=w@w-radius*radius
            discriminant=bb*bb-4*aa*cc
            if discriminant < -1e-9:continue
            root=math.sqrt(max(0.,discriminant))
            for t in ((-bb-root)/(2*aa),(-bb+root)/(2*aa)):
                if -1e-9<=t<=1+1e-9:candidates.append(a+np.clip(t,0,1)*v)
        values.extend(float(plane@np.r_[q-centre,1.]) for q in candidates)
    return (min(values),max(values)) if values else None


# Single existing stock shapes selected by trees.lua. Bounds are conservative
# origin-centred radii measured from the shipped CDAE geometry, not new assets.
# (XY radius, catalog height, actual minimum Z); keep aligned with trees.lua.
NATIVE_ASSETS={
    'site_shrub':(2.276,2.08571,-.6789932251),
    'site_rock':(1.202,.63454,-.3542777002),
}
NATIVE_CLEARANCE=.25
NATIVE_MIN_SCALE=.3


def native_radius(group,height):
    """Full native asset envelope plus the same clearance used by the client."""
    radius,nominal,_=NATIVE_ASSETS[group]
    return radius*max(NATIVE_MIN_SCALE,min(2.5,float(height)/nominal))+NATIVE_CLEARANCE


def native_props(spec,x0=0.,y0=0.):
    """Native Forest rows after final access/driveway/landscape coordination.

    Rows are [group, world X, world Y, origin Z, yaw degrees, 1, height, rank].
    The client reuses stock assets and their own LODs. Narrow beds fail closed;
    there is deliberately no generated shrub/rock mesh fallback.
    """
    from shapely.geometry import Point,Polygon
    access=getattr(spec,'access',None)
    if access is None or not access.landscape or getattr(spec,'inference',None) is None:return []
    profile=treatment(spec)
    hard=[]
    for solid in (*access.solids,*getattr(getattr(spec,'garage_access',None),'surfaces',())):
        q=np.asarray(solid.top,float)
        if q.ndim==2 and q.shape[1]>=2:
            shape=Polygon(q[:,:2])
            if shape.is_valid and not shape.is_empty:hard.append(shape)
    footprint=getattr(spec,'footprint',None)
    if footprint is not None:hard.append(footprint.shape())
    elif getattr(spec,'ring',None) is not None:hard.append(Polygon(np.asarray(spec.ring)[:,:2]))
    bands=[]
    for index,band in enumerate(access.landscape):
        if band.kind.removeprefix('site_') not in ('garden_bed','lawn_margin'):continue
        frame=_patch_frame(band.top)
        if frame is None:continue
        p,length,width=frame
        broad=band.kind.startswith('site_') and width>=.9 and length*width>=5.
        bands.append((index,band,p,length,width,broad))
    site_remaining=sum(row[-1] for row in bands)
    site_count=0;count=0;rows=[];placed=[]
    for index,band,p,length,width,broad in bands:
        lanes=max(1,min(4,int(width/2.4))) if broad else 1
        if broad:
            available=MAX_SITE_PLANTS-site_count
            allowance=min(available,max(1,available//site_remaining))
            site_remaining-=1
            spacing=2.0 if band.kind=='site_garden_bed' else 2.8
            n=min(MAX_SITE_PLANTS_PER_BED,allowance,max(1,int(length/spacing))*lanes)
        else:n=min(3,max(1,int(length/1.8)),min(MAX_PLANTS,profile.plants)-count)
        if n<=0:continue
        shape=Polygon(p[:,:2]);admitted=0
        columns=max(1,math.ceil(n/lanes))
        phase=materials.unit(spec.seed,f'native-landscape-{index}-phase')*2*math.pi
        # Jittered stations and meandering lanes retain gaps and loose clusters,
        # instead of a uniform hedge. Retries are capped and never change a row
        # already admitted, making repeated loads and detail stages identical.
        for attempt in range(n*6):
            if admitted>=n:break
            channel=f'native-landscape-{index}-{attempt}'
            rand=lambda name:materials.unit(spec.seed,channel+'-'+name)
            station=attempt%n;lane=station%lanes;column=station//lanes
            u=(column+.15+.7*rand('station'))/columns
            drift=.13*math.sin(u*math.pi*2+phase) if lanes>1 else 0.
            v=np.clip((lane+.5+.65*(rand('row')-.5))/lanes+drift,.04,.96)
            if lanes==1:
                # A strip still wanders, but does not squander its little
                # plantable width by repeatedly proposing along the curb edge.
                spread=min(.24,max(.025,(width-1.9)/(2*width)))
                v=.5+(rand('row')-.5)*2*spread
            centre=_point(p,u,v);point=Point(centre[:2])
            clearance=float(shape.boundary.distance(point))-.015
            if not shape.covers(point):continue
            for obstacle in hard:clearance=min(clearance,float(obstacle.distance(point))-.015)
            rock=rand('kind')<.25
            options=('site_rock',) if rock else ('site_shrub','site_rock')
            for group in options:
                radius,nominal,min_z=NATIVE_ASSETS[group]
                desired=(.24+.15*rand('height')) if group=='site_rock' else (.72+.48*rand('height'))
                height=min(desired,(clearance-NATIVE_CLEARANCE)*nominal/radius)
                if height<nominal*NATIVE_MIN_SCALE:continue
                envelope=native_radius(group,height)
                if envelope>clearance+1e-9:continue
                if any(np.linalg.norm(centre[:2]-other)<envelope+other_radius
                       for other,other_radius in placed):continue
                scale=height/nominal
                support=_support_range(p,centre[:2],radius*scale)
                if support is None or support[1]-support[0]>min(.28,height*.4):continue
                origin=float(support[0]-min_z*scale-.018)
                rows.append([group,float(centre[0]+x0),float(centre[1]+y0),origin,
                             float(rand('yaw')*360.),1.,float(height),float(rand('rank')*.18)])
                placed.append((centre[:2].copy(),envelope));admitted+=1
                if broad:site_count+=1
                else:count+=1
                break
    return rows


def draw(mesh,spec,detail=False):
    """Accepted groundcover only; every shrub/rock uses native_props assets."""
    import buildings as b
    access=getattr(spec,'access',None)
    if access is None or not access.landscape:return
    looks=b._Looks(spec.seed)
    cover_mats={'lawn_margin':looks[b.custom_look(b.LAWN,(.82,.87,.75))],
                'garden_bed':looks[b.custom_look(b.GARDEN,(.67,.57,.45))],
                'gravel_margin':looks[b.custom_look(b.GRAVEL,(.70,.68,.61))]}
    for band in access.landscape:
        frame=_patch_frame(band.top)
        if frame is None:continue
        p,_,_=frame
        cover=band.kind.removeprefix('site_')
        mesh.quad(*p,*tuple((v[0]/1.4,v[1]/1.4) for v in p),cover_mats.get(cover,cover_mats['gravel_margin']))
