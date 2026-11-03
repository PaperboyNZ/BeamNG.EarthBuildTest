"""Evidence-bounded common grounds. Plan once in the source frame, then partition.

Interfaces owned by the site are observed external mouths; member interfaces
are destinations. Endpoints are measured opening edges, never route centrelines.
All physical extents describe observed hardstanding, not inferred property area.
"""
from dataclasses import dataclass
import hashlib
import math

import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from buildgen.topology import polygons, triangles
from .identity import canonical_json
from .plan import SitePlan

MAX_PORTS = 24
MAX_ROUTES = 24
MAX_STALLS = 64
MAX_CELLS = 4096
MAX_PROBES = 4096
MAX_SECTORS = 8
GRID = 2.
MAX_GRADE = .08
MAX_FILL = .18


@dataclass(frozen=True, slots=True)
class Route:
    identity: str
    kind: str
    source: str
    destination: str
    points: tuple
    width: float

    def __post_init__(self):
        if self.kind not in ('pedestrian','vehicle','service') or not 1.2<=self.width<=6.:
            raise ValueError('unsupported shared route')
        if not 2<=len(self.points)<=97 or np.shape(self.points)!=(len(self.points),2) or not np.isfinite(self.points).all():
            raise ValueError('invalid shared route points')


@dataclass(frozen=True, slots=True)
class Surface:
    """One canonical top triangle, with one owning physical resource."""
    resource: str
    kind: str
    top: tuple


@dataclass(frozen=True, slots=True)
class SharedLayout:
    plan: SitePlan
    routes: tuple
    stalls: tuple
    beds: tuple
    surfaces: tuple
    coefficients: tuple
    terrain_points: int
    diagnostics: tuple = ()
    sector: str = ''
    contact_revision: str = ''

    def __post_init__(self):
        if type(self.plan) is not SitePlan or len(self.routes)>MAX_ROUTES or len(self.stalls)>MAX_STALLS or len(self.surfaces)>MAX_CELLS:
            raise ValueError('shared layout budget/contract')
        if not 0<self.terrain_points<=MAX_PROBES or len(self.coefficients)!=6 or not np.isfinite(self.coefficients).all():
            raise ValueError('invalid shared surface fit')
        for cell in self.surfaces:
            if type(cell) is not Surface or np.shape(cell.top)!=(3,3) or not np.isfinite(cell.top).all():
                raise ValueError('invalid shared surface triangle')
        if not self.contact_revision:
            if self.sector:raise ValueError('fragment requires complete source contact revision')
            from dataclasses import asdict
            digest=hashlib.sha256(canonical_json(dict(version=1,plan=self.plan.to_dict(),
                surfaces=[asdict(s) for s in self.surfaces])).encode()).hexdigest()
            object.__setattr__(self,'contact_revision',digest)
        if len(self.contact_revision)!=64 or any(c not in '0123456789abcdef' for c in self.contact_revision):
            raise ValueError('invalid source contact revision')

    @property
    def revision(self):
        from dataclasses import asdict
        return hashlib.sha256(canonical_json(asdict(self)).encode()).hexdigest()


def shape(p):
    return Polygon(p.outer,p.holes)


def basis(xy):
    xy=np.asarray(xy,float);x,y=xy[...,0],xy[...,1]
    return np.stack((x*0+1,x,y,x*x,x*y,y*y),axis=-1)


def height(coeff,xy):
    return basis(xy)@np.asarray(coeff)


def capability(plan):
    e=plan.evidence
    if not plan.interfaces:return 'shared_layout_requires_interfaces'
    if len(plan.interfaces)>MAX_PORTS:return 'shared_layout_interface_budget'
    if e.frame.kind!='canonical_enu' or e.association_extent is None or e.exclusions is None:
        return 'shared_layout_requires_complete_canonical_evidence'
    if abs(e.frame.frame.latitude_e7)>850_000_000:return 'shared_layout_unsupported_latitude'
    if not 1<=len(e.memberships)<=32 or any(m.member.kind not in ('building','lot') or m.interval is not None for m in e.memberships):
        return 'shared_layout_unsupported_members'
    if len(e.physical_extents)>16 or not e.physical_extents:return 'shared_layout_surface_budget'
    if {r.identity for r in plan.resources}!={p.identity for p in e.physical_extents}:
        return 'shared_layout_resource_extent_mismatch'
    members={m.member for m in e.memberships}
    if any(r.producer!=e.ref or r.kind!='shared_circulation' or not r.consumers or not set(r.consumers)<=members for r in plan.resources):
        return 'shared_layout_requires_site_surface_owner'
    if any(p.interval is None or p.interval.basis!='ellipsoidal_height' for p in e.physical_extents):
        return 'shared_layout_requires_ground_heights'
    if any(i.status!='observed' or i.kind not in ('pedestrian','vehicle','parking','service') for i in plan.interfaces):
        return 'shared_layout_requires_observed_ground_interfaces'
    if any(not any(i.owner==m for i in plan.interfaces) for m in members):
        return 'shared_layout_missing_member_interface'
    if any(m.kind=='building' and m.identity.namespace!='beamng-earth/source-building-id' for m in members):
        return 'shared_layout_unknown_building_namespace'
    if any(abs(v)>2048 for p in (e.association_extent,*e.exclusions,*(p.boundary for p in e.physical_extents)) for ring in (p.outer,*p.holes) for xy in ring for v in xy):
        return 'shared_layout_spatial_budget'
    if sum(len(p.outer)+sum(map(len,p.holes)) for p in (e.association_extent,*e.exclusions,*(p.boundary for p in e.physical_extents)))>512:
        return 'shared_layout_vertex_budget'
    return None


def _port(port):
    p=np.asarray(port.endpoints);d=p[1,:2]-p[0,:2];w=float(np.linalg.norm(d))
    return p[:,:2].mean(axis=0),d/max(w,1e-9),w


def _route(a,b,domain,kind):
    """Four bounded cubic alternatives, full strips and rigid-van swept envelope.

    Service routes support a 5.5 m rigid van, not articulated delivery trucks.
    Sharp turns and routes without a complete envelope remain unsupported.
    """
    start,ta,wa=_port(a);end,tb,wb=_port(b)
    minimum=1.2 if kind=='pedestrian' else 3.2
    if min(wa,wb)<minimum:return None
    distance=float(np.linalg.norm(end-start))
    if not 2<=distance<=180:return None
    direction=(end-start)/distance
    na=np.array([-ta[1],ta[0]]);nb=np.array([-tb[1],tb[0]])
    if na@direction<0:na=-na
    if nb@direction<0:nb=-nb
    count=min(97,max(9,math.ceil(distance/1.5)+1));t=np.linspace(0,1,count)
    width=min(wa,wb,2. if kind=='pedestrian' else 6.)
    choices=[]
    for reach in (.25,.45,.7,1.):
        points=(2*t**3-3*t**2+1)[:,None]*start+(t**3-2*t**2+t)[:,None]*distance*reach*na \
            +(-2*t**3+3*t**2)[:,None]*end+(t**3-t**2)[:,None]*distance*reach*nb
        line=LineString(points)
        if not line.is_simple:continue
        strip=line.buffer(width/2,cap_style=2,join_style=2)
        if not domain.buffer(1e-7).covers(strip):continue
        delta=np.diff(points,axis=0);lengths=np.linalg.norm(delta,axis=1)
        if lengths.min()<1e-5:continue
        heading=delta/lengths[:,None]
        turn=np.arccos(np.clip(np.sum(heading[:-1]*heading[1:],axis=1),-1,1))
        if kind!='pedestrian':
            if np.any(turn/np.maximum((lengths[:-1]+lengths[1:])/2,1e-9)>1/6.):continue
            # Sweep the entire vehicle between samples. End overhang may extend
            # beyond a source port; only the middle of the route is evaluated
            # there, while the complete strip checks the portal itself.
            swept=[]
            stations=np.r_[0.,np.cumsum(lengths)]
            for j,p in enumerate(points[:-1]):
                if stations[j]<2.75 or stations[-1]-stations[j]<2.75:continue
                u=heading[j];v=np.array([-u[1],u[0]])
                swept.append(Polygon([p+su*2.75*u+sv*1.25*v for su,sv in ((-1,-1),(1,-1),(1,1),(-1,1))]))
            if any(not domain.buffer(1e-7).covers(p) for p in swept):continue
            if swept and any(not domain.buffer(1e-7).covers(unary_union((p,q)).convex_hull) for p,q in zip(swept,swept[1:])):continue
        choices.append((line.length,tuple(map(tuple,points)),strip))
    if not choices:return None
    _,points,strip=min(choices,key=lambda row:(round(row[0],8),row[1]))
    return Route(a.identity+'>'+b.identity,kind,a.identity,b.identity,points,width),strip


def plan_routes(plan,domain):
    """Reserve walking and delivery corridors before customer parking."""
    external=sorted((p for p in plan.interfaces if p.owner==plan.evidence.ref),key=lambda p:p.identity)
    destinations=sorted((p for p in plan.interfaces if p.owner!=plan.evidence.ref),key=lambda p:({'pedestrian':0,'service':1}.get(p.kind,2),p.identity))
    routes=[];walks=[];service=[];vehicle=[]
    for target in destinations:
        kind='pedestrian' if target.kind=='pedestrian' else 'service' if target.kind=='service' else 'vehicle'
        roots=[p for p in external if (p.kind=='pedestrian')==(kind=='pedestrian') and (kind!='service' or p.kind in ('vehicle','service'))]
        reserved=unary_union(walks if kind!='pedestrian' else ())
        space=domain.difference(reserved)
        candidates=[]
        for source in roots[:4]:
            candidate=_route(source,target,space,kind)
            if candidate:candidates.append(candidate)
        if not candidates:return None,'shared_layout_unconnected_'+target.identity
        route,strip=min(candidates,key=lambda r:(LineString(r[0].points).length,r[0].identity))
        routes.append(route)
        (walks if kind=='pedestrian' else service if kind=='service' else vehicle).append(strip)
    return (tuple(routes),unary_union(walks),unary_union(service),unary_union(vehicle)),None


def _parking(routes,domain,walks,service):
    """Full bays only beside a six-metre aisle and a connected pedestrian strip."""
    stalls=[];used=unary_union((walks,service))
    aisles=unary_union([LineString(r.points).buffer(r.width/2,cap_style=2,join_style=2) for r in routes if r.kind!='pedestrian'])
    for route in routes:
        if route.kind!='vehicle' or route.width<6.-1e-6:continue
        line=LineString(route.points)
        for station in np.arange(6.,line.length-6.,2.6):
            p=np.asarray(line.interpolate(station).coords[0]);q=np.asarray(line.interpolate(station+.1).coords[0])
            u=(q-p)/np.linalg.norm(q-p);v=np.array([-u[1],u[0]])
            for side in (-1,1):
                a=p+side*v*route.width/2
                bay=Polygon([a-u*1.25,a+u*1.25,a+u*1.25+side*v*5.,a-u*1.25+side*v*5.])
                # The remote end meets a walking strip. Without this connection
                # we leave paved ground unmarked rather than invent a safe route.
                exit_edge=LineString((a-u*1.25+side*v*5.,a+u*1.25+side*v*5.))
                if (not domain.buffer(1e-7).covers(bay) or bay.intersection(unary_union((used,aisles))).area>1e-7
                        or walks.is_empty or exit_edge.distance(walks)>.05):continue
                stalls.append(tuple(map(tuple,bay.exterior.coords[:-1])))
                used=unary_union((used,bay))
                if len(stalls)>=MAX_STALLS:return tuple(stalls)
    return tuple(stalls)


def fit(plan,elev,*,point_budget=MAX_PROBES):
    why=capability(plan)
    if why:return None,why
    from .shared_courts import _frame
    e=plan.evidence;frame=_frame(plan)
    occupied=[shape(p.boundary) for p in e.physical_extents]
    domain=unary_union(occupied);boundary=shape(e.association_extent)
    excluded=unary_union([shape(p) for p in e.exclusions])
    if not boundary.covers(domain):return None,'shared_layout_outside_evidence'
    if domain.intersection(excluded).area>1e-7:return None,'shared_layout_exclusion_conflict'
    if any(p.intersection(q).area>1e-7 for j,p in enumerate(occupied) for q in occupied[j+1:]):return None,'shared_layout_duplicate_physical_owner'
    for port in plan.interfaces:
        edge=LineString(np.asarray(port.endpoints)[:,:2])
        if not domain.buffer(.001).covers(edge):return None,'shared_layout_port_outside_surface'
        if port.owner==e.ref and edge.distance(domain.boundary)>.01:return None,'shared_layout_external_port_not_on_boundary'
        if port.owner.kind=='building' and edge.distance(excluded)>.1:
            return None,'shared_layout_missing_member_footprint'
    routed,why=plan_routes(plan,domain)
    if why:return None,why
    routes,walks,service,vehicle=routed
    stalls=_parking(routes,domain,walks,service)
    # Fixed canonical grid: every role, resource and sector derives triangles
    # from the same planes, so clipped seam heights cannot drift independently.
    x0,y0,x1,y1=domain.bounds
    pins=np.array([p for i in plan.interfaces for p in i.endpoints],float)
    xs=np.unique(np.r_[np.arange(math.floor(x0/GRID)*GRID,math.ceil(x1/GRID)*GRID+GRID*.5,GRID),pins[:,0]])
    ys=np.unique(np.r_[np.arange(math.floor(y0/GRID)*GRID,math.ceil(y1/GRID)*GRID+GRID*.5,GRID),pins[:,1]])
    if len(xs)*len(ys)>min(MAX_PROBES,point_budget):return None,'shared_layout_terrain_budget'
    grid=np.array([(x,y) for y in ys for x in xs])
    probes=np.vstack((grid,pins[:,:2]))
    if len(probes)>min(MAX_PROBES,point_budget) or elev is None:return None,'shared_layout_terrain_budget'
    lat,lon,_=frame.enu_to_geodetic(probes[:,0],probes[:,1],np.zeros(len(probes)))
    try:
        h=np.asarray(elev(lat,lon),float).reshape(-1)
        if len(h)!=len(probes) or not np.isfinite(h).all():return None,'shared_layout_missing_terrain'
    except (TypeError,ValueError,OSError):return None,'shared_layout_missing_terrain'
    terrain=frame.geodetic_to_enu(lat,lon,h)[2]
    for extent,p in zip(e.physical_extents,occupied):
        from shapely import intersects_xy
        inside=intersects_xy(p.buffer(1e-7),probes[:,0],probes[:,1])
        if inside.any() and (h[inside].min()<extent.interval.minimum-.02 or h[inside].max()>extent.interval.maximum+.02):
            return None,'shared_layout_ground_height_conflict'
    # Constrained quadratic fit: smooth grade changes, pinned measured entrances.
    # Inconsistent interface elevations reject the whole proposal.
    A=basis(probes);C=basis(pins[:,:2]);target=pins[:,2]
    scale=np.maximum(np.linalg.norm(A,axis=0),1.);As=A/scale;Cs=C/scale
    particular=np.linalg.lstsq(Cs,target,rcond=None)[0]
    _,singular,V=np.linalg.svd(Cs,full_matrices=True)
    rank=int(np.sum(singular>max(Cs.shape)*singular[0]*1e-12))
    null=V[rank:].T
    coeff=particular
    if null.shape[1]:coeff=coeff+null@np.linalg.lstsq(As@null,terrain+.03-As@coeff,rcond=None)[0]
    coeff=coeff/scale
    if np.max(np.abs(C@coeff-target))>.001:return None,'shared_layout_incompatible_port_heights'
    z=A@coeff;fill=z-terrain
    # Contact ports may be flush. Do not excavate, float, or move the doors.
    if fill.min()<-.005 or fill.max()>MAX_FILL:return None,'shared_layout_grading'
    gradient=np.c_[coeff[1]+2*coeff[3]*probes[:,0]+coeff[4]*probes[:,1],coeff[2]+coeff[4]*probes[:,0]+2*coeff[5]*probes[:,1]]
    if np.linalg.norm(gradient,axis=1).max()>MAX_GRADE:return None,'shared_layout_grade'
    for route in routes:
        if route.kind!='pedestrian':continue
        p=np.asarray(route.points);delta=np.diff(p,axis=0);lengths=np.linalg.norm(delta,axis=1)
        if np.max(np.abs(np.diff(height(coeff,p)))/lengths)>.05:return None,'shared_layout_pedestrian_grade'
    zones=(('pedestrian',walks),('service',service.difference(walks)),('vehicle',domain.difference(unary_union((walks,service)))))
    from shapely import STRtree,prepare
    regions=[(extent.identity,kind,area.intersection(zone)) for extent,area in zip(e.physical_extents,occupied)
             for kind,zone in zones if area.intersects(zone)]
    regions=[r for r in regions if r[2].area>1e-9]
    region_shapes=[r[2] for r in regions];prepare(region_shapes);region_tree=STRtree(region_shapes)
    cells=[]
    for y,yn in zip(ys,ys[1:]):
        for x,xn in zip(xs,xs[1:]):
            for corners in (((x,y),(xn,y),(xn,yn)),((x,y),(xn,yn),(x,yn))):
                tri=Polygon(corners)
                if not tri.intersects(domain):continue
                plane=np.linalg.solve(np.c_[corners,np.ones(3)],height(coeff,corners))
                if np.linalg.norm(plane[:2])>MAX_GRADE:return None,'shared_layout_contact_grade'
                for index in sorted(region_tree.query(tri)):
                    resource,kind,region=regions[int(index)]
                    if region.covers(tri):pieces=(corners,)
                    else:
                        clipped=tri.intersection(region)
                        if clipped.area<1e-9:continue
                        pieces=tuple(t for fp in polygons(clipped) for t in triangles(fp))
                    for points in pieces:
                        top=tuple((float(a),float(b),float(plane@[a,b,1])) for a,b in points)
                        cells.append(Surface(resource,kind,top))
                        if len(cells)>MAX_CELLS:return None,'shared_layout_mesh_budget'
    # Only surveyed property permits optional residual soft landscaping. Mapped
    # pavement associations do not grant ownership of neighbouring grass.
    beds=()
    if e.extent_basis=='surveyed_property':
        soft=boundary.difference(unary_union((domain,excluded))).intersection(domain.buffer(2.)).buffer(-.15).buffer(.15)
        soft=soft.difference(unary_union((domain,excluded)))
        approaches=[]
        for port in plan.interfaces:
            p=np.asarray(port.endpoints)[:,:2];centre,tangent,width=_port(port)
            normal=np.array([-tangent[1],tangent[0]])
            if domain.covers(Point(centre+normal*.1)):normal=-normal
            approaches.append(Polygon([p[0],p[1],p[1]+normal*6,p[0]+normal*6]).buffer(.3))
        soft=soft.difference(unary_union(approaches))
        beds=tuple(p for p in polygons(soft) if p.area>=2.)[:16]
    diagnostics=('shared_layout_no_connected_parking',) if not stalls else ()
    return SharedLayout(plan,routes,stalls,beds,tuple(cells),tuple(map(float,coeff)),len(probes),diagnostics),None


def drainage(layout):
    """Surface fall direction only; no invented underground drain or outlet."""
    p=shape(layout.plan.evidence.association_extent).centroid;c=layout.coefficients
    gradient=np.array([c[1]+2*c[3]*p.x+c[4]*p.y,c[2]+c[4]*p.x+2*c[5]*p.y])
    length=float(np.linalg.norm(gradient))
    return dict(direction=tuple(map(float,-gradient/max(length,1e-12))),slope=length,outlet='unresolved')


def sectors(plan):
    """Bounded geographic inventory, independent of the first resident tile."""
    import geotiles
    from .shared_courts import _frame
    p=plan.evidence.association_extent;frame=_frame(plan)
    xy=np.array(p.outer);lat,lon,_=frame.enu_to_geodetic(xy[:,0],xy[:,1],np.zeros(len(xy)))
    gx,gy=geotiles.tile_of(lat,lon)
    if (int(gx.max()-gx.min())+1)*(int(gy.max()-gy.min())+1)>MAX_SECTORS:
        return ()
    return tuple((x,y) for x in range(int(gx.min()),int(gx.max())+1) for y in range(int(gy.min()),int(gy.max())+1)
                 if shape(p).intersection(sector_shape(plan,x,y)).area>1e-7)


def sector_shape(plan,gx,gy):
    """Identical geographic edge samples on both sides of every sector seam."""
    import geotiles
    from .shared_courts import _frame
    s,w,n,e=geotiles.info(gx,gy)[2:];frame=_frame(plan)
    ll=[]
    for a,b in (((w,s),(e,s)),((e,s),(e,n)),((e,n),(w,n)),((w,n),(w,s))):
        # Integer interpolation endpoints are shared even when winding reverses.
        low,high=sorted((a,b));points=[tuple(np.asarray(low)+(np.asarray(high)-low)*(j/16)) for j in range(17)]
        ll.extend(points if a==low else points[::-1])
    lon,lat=np.array(ll).T;x,y,_=frame.geodetic_to_enu(lat,lon,np.zeros(len(ll)))
    return Polygon(np.c_[x,y])


def partition(layout,gx,gy):
    """One contact owner per clipped patch; no shared collider across lifetimes."""
    from dataclasses import replace
    import geotiles
    clip=sector_shape(layout.plan,gx,gy);cells=[]
    for cell in layout.surfaces:
        xyz=np.asarray(cell.top);plane=np.linalg.solve(np.c_[xyz[:,:2],np.ones(3)],xyz[:,2])
        for fp in polygons(Polygon(xyz[:,:2]).intersection(clip)):
            if fp.area<1e-8:continue
            for tri in triangles(fp):
                cells.append(Surface(cell.resource,cell.kind,tuple((float(x),float(y),float(plane@[x,y,1])) for x,y in tri)))
    stalls=tuple(p for p in layout.stalls if clip.buffer(1e-7).covers(Polygon(p)))
    return replace(layout,surfaces=tuple(cells),stalls=stalls,sector=geotiles.key(gx,gy))


def compile(layout,target,origin=(0.,0.,0.)):
    from .shared_courts import _frame,project_points
    import roadmesh
    P=[];T=[];UV=[];M=[]
    levels={};footprints=[]
    def emit(xyz,mat):
        start=len(P);P.extend(xyz);T.append((start,start+1,start+2));UV.extend(np.asarray(xyz)[:,:2]/4.);M.append(mat)
    for cell in layout.surfaces:
        p=np.asarray(cell.top);bottom=p.copy();bottom[:,2]-=.3
        emit(p,0 if cell.kind=='pedestrian' else 1);emit(bottom[::-1],0)
        footprints.append(Polygon(p[:,:2]))
        for x,y,z in p:levels[(round(x,8),round(y,8))]=z
    # Only the exterior and source-hole boundaries need side walls. Building a
    # closed prism for every grid triangle triples collision/rendering cost.
    for fp in polygons(unary_union(footprints)):
        for ring in (fp.outer,*fp.holes):
            for a,b in zip(ring,ring[1:]+ring[:1]):
                za=levels[(round(a[0],8),round(a[1],8))];zb=levels[(round(b[0],8),round(b[1],8))]
                A=(*a,za);B=(*b,zb);la=(*a,za-.3);lb=(*b,zb-.3)
                emit((la,lb,B),0);emit((la,B,A),0)
    if not P:return None
    # One geographic transform for the complete batch, not one per triangle.
    return project_points(P,_frame(layout.plan),target,origin),np.asarray(T,np.int64),np.asarray(UV),[roadmesh.DECK_SIDE,roadmesh.DECK_TOP],np.asarray(M,np.int64)


def metadata(layout,target):
    from .shared_courts import _frame,project_points
    e=layout.plan.evidence;boxes=[];masks=[]
    # Merge top footprints for compact masks without filling source holes.
    merged=unary_union([Polygon(np.asarray(s.top)[:,:2]) for s in layout.surfaces])
    for fp in polygons(merged):
        rings=[]
        for ring in (fp.outer,*fp.holes):
            xy=np.asarray(ring);z=height(layout.coefficients,xy)
            rings.append(project_points(np.c_[xy,z],_frame(layout.plan),target))
        allp=np.concatenate(rings);lo=allp.min(axis=0);hi=allp.max(axis=0)
        # Interior extrema can exceed boundary heights on a quadratic surface.
        xyz=project_points(np.array([p for s in layout.surfaces for p in s.top]),_frame(layout.plan),target)
        lo[2]=min(lo[2],xyz[:,2].min())-.35;hi[2]=max(hi[2],xyz[:,2].max())+.1
        plain=[r[:,:2].tolist() for r in rings]
        boxes.append([*map(float,lo),*map(float,hi),plain])
        masks.append(dict(rings=plain,min_z=float(lo[2]),max_z=float(hi[2]+.3),kind='hardscape'))
    site=dict(identity=e.identity.to_dict(),frame=e.frame.frame.to_dict(),revision=layout.revision,
              surface_revision=layout.contact_revision,
              sectors=['g17_'+str(x)+'_'+str(y) for x,y in sectors(layout.plan)],
              sector=layout.sector,partition='canonical-ground-v1',drainage=drainage(layout),
              source_plan_sha256=hashlib.sha256(layout.plan.to_json().encode()).hexdigest(),
              routes=[dict(identity=r.identity,kind=r.kind,source=r.source,destination=r.destination) for r in layout.routes],
              resources=[dict(identity=r.identity,fragment=r.identity+'@'+layout.sector,kind=r.kind,
                              producer=r.producer.to_dict(),consumers=[c.to_dict() for c in r.consumers],
                              retention='sector_contact') for r in layout.plan.resources],
              parking=len(layout.stalls),beds=len(layout.beds),diagnostics=layout.diagnostics)
    return [site],boxes,masks


def additions(layout,target,elev):
    """Stock planting, parking positions and render-only paint on accepted ground."""
    from .shared_courts import _frame,project_points
    from buildgen.landscaping import NATIVE_ASSETS,native_radius
    from shapely import STRtree
    source=_frame(layout.plan);cells=[Polygon(np.asarray(c.top)[:,:2]) for c in layout.surfaces]
    tree=STRtree(cells)
    def z_at(xy):
        result=[]
        for q in xy:
            hit=next((int(i) for i in tree.query(Point(q)) if cells[int(i)].buffer(1e-8).covers(Point(q))),None)
            if hit is None:raise ValueError('shared marking outside accepted contact')
            xyz=np.asarray(layout.surfaces[hit].top)
            plane=np.linalg.solve(np.c_[xyz[:,:2],np.ones(3)],xyz[:,2])
            result.append(float(plane@[*q,1.]))
        return np.asarray(result)
    park=[];marks=[]
    for bay in layout.stalls:
        p=np.asarray(bay);centre=p.mean(axis=0);direction=(p[2]+p[3]-p[0]-p[1])/2
        points=project_points(np.c_[[centre,centre+direction*.4],z_at([centre,centre+direction*.4])],source,target)
        heading=math.degrees(math.atan2(*(points[1,:2]-points[0,:2])[::-1]))
        park.append([*map(float,points[0]),heading,1])
        for a,b in ((p[0],p[3]),(p[1],p[2]),(p[2],p[3])):
            # Stay inside the bay so paint never trespasses into its walking strip.
            a=a*.99+centre*.01;b=b*.99+centre*.01
            n=max(2,math.ceil(np.linalg.norm(b-a)/.5)+1);xy=a+(b-a)*np.linspace(0,1,n)[:,None]
            xyz=project_points(np.c_[xy,z_at(xy)],source,target)
            marks.append(dict(m='line_white',tl=6.4,p=2,w=.08,n=[[*map(float,q),0.] for q in xyz],deck=True,fixed=True,layer='mark'))
    # Candidate positions derive from complete source beds before sector clipping.
    clip=None
    if layout.sector:
        _,gx,gy=layout.sector.split('_');clip=sector_shape(layout.plan,int(gx),int(gy))
    candidates=[];attempts=0
    for bed in layout.beds:
        shape=bed.shape();x0,y0,x1,y1=shape.bounds
        for y in np.arange(math.floor(y0/3)*3,y1,3.):
            for x in np.arange(math.floor(x0/3)*3,x1,3.):
                attempts+=1
                if attempts>2048:break
                digest=hashlib.sha256(canonical_json([layout.plan.evidence.identity.to_dict(),float(x),float(y)]).encode()).digest()
                q=np.array([x+(digest[0]/255-.5)*.4,y+(digest[1]/255-.5)*.4])
                group='site_rock' if digest[2]<64 else 'site_shrub';h=.22 if group=='site_rock' else .64
                radius=native_radius(group,h);envelope=Point(q).buffer(radius)
                if not shape.covers(envelope) or clip is not None and not clip.covers(envelope):continue
                candidates.append((q,group,h,digest[3]/255*360.,radius))
                if len(candidates)>=48:break
            if attempts>2048 or len(candidates)>=48:break
        if attempts>2048 or len(candidates)>=48:break
    props=[]
    if candidates and elev is not None:
        xy=np.array([q+radius*np.array([math.cos(t),math.sin(t)]) for q,_,_,_,radius in candidates for t in np.linspace(0,2*math.pi,9)])
        lat,lon,_=source.enu_to_geodetic(xy[:,0],xy[:,1],np.zeros(len(xy)))
        try:
            h=np.asarray(elev(lat,lon),float).reshape(-1)
            if len(h)!=len(xy):return park,marks,props
            z=source.geodetic_to_enu(lat,lon,h)[2].reshape(-1,9)
        except (ValueError,TypeError,OSError):return park,marks,props
        for (q,group,h,yaw,_),levels in zip(candidates,z):
            if not np.isfinite(levels).all() or np.ptp(levels)>.2:continue
            _,nominal,base=NATIVE_ASSETS[group];origin=float(levels.min()-base*h/nominal-.018)
            p=project_points([[*q,origin]],source,target)[0]
            props.append([group,*map(float,p),yaw,1.,h,.05])
    return park,marks,props
