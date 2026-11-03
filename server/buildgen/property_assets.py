"""Commercial furniture authored in metres and batched with building visuals.

No new per-object scene entities, network calls, or generated legal lot extents.
Optional furniture is visual-only in stage one. Its footprints must be proven
clear inside an accepted shared site; explicit placements use canonical ENU.
"""
import hashlib
import logging
import math
from functools import lru_cache
import numpy as np
from .property_geometry import box, frontage, sign_slot, UV

log=logging.getLogger(__name__)
MAX_FASCIAS=32
MAX_DIRECTORY_BOARDS=8
MAX_FURNITURE=24
PANEL='bne_bld_panel'


def budgets(rank):
    """Fascias, directory pages, furniture, fascia pixels, directory pixels.

    Cheap coverage never starts font selection/text rasterization. All work is
    per worker product, not per rendered frame; an entire directory fits or is
    omitted, regardless of this ceiling.
    """
    return {2:(8,4,6,256,256),3:(16,6,12,512,512),
            4:(24,8,18,512,512),5:(32,8,24,1024,512)}.get(rank,(0,0,0,0,0))


class Mesh:
    """Local material indices: parallel jobs never mutate buildings.MATERIALS."""
    def __init__(self):
        self.points=[]; self.uv=[]; self.tris=[]; self.mid=[]; self.colours=[]; self.materials=[]

    def paint(self,colour=(.28,.32,.33),name=PANEL):
        if name not in self.materials:self.materials.append(name)
        return self.materials.index(name),tuple(round(max(0,min(1,v))*255) for v in colour)+(255,)

    def quad(self,a,b,c,d,uva,uvb,uvc,uvd,mat):
        start=len(self.points);self.points.extend((a,b,c,d));self.uv.extend((uva,uvb,uvc,uvd))
        self.tris.extend(((start,start+1,start+2),(start,start+2,start+3)))
        self.mid.extend((mat[0],mat[0]));self.colours.extend((mat[1],)*4)

    def append(self,other,transform=None):
        p,uv,t,mi,mats,col=other.arrays() if isinstance(other,Mesh) else other
        if transform is not None:p=transform(p)
        offset=len(self.points); mapping=[]
        for name in mats:
            if name not in self.materials:self.materials.append(name)
            mapping.append(self.materials.index(name))
        self.points.extend(p);self.uv.extend(uv);self.tris.extend(t+offset)
        self.mid.extend(np.asarray(mapping,dtype=np.int32)[mi]);self.colours.extend(col)

    def arrays(self):
        return (np.asarray(self.points,float).reshape(-1,3),np.asarray(self.uv,float).reshape(-1,2),
                np.asarray(self.tris,np.int64).reshape(-1,3),np.asarray(self.mid,np.int32),
                list(self.materials),np.asarray(self.colours,np.uint8).reshape(-1,4))


def beam(mesh,a,b,width,mat):
    """Square-section rail, correctly capped, arbitrary 3-D orientation."""
    a,b=np.asarray(a,float),np.asarray(b,float); along=b-a
    along/=np.linalg.norm(along)
    cross=np.cross(along,(0,0,1) if abs(along[2])<.9 else (0,1,0))
    cross*=width/(2*np.linalg.norm(cross)); up=np.cross(along,cross)
    corners=[cross*x+up*y for x,y in ((-1,-1),(1,-1),(1,1),(-1,1))]
    low=[a+c for c in corners];high=[b+c for c in corners]
    for i in range(4):
        j=(i+1)%4;mesh.quad(low[i],low[j],high[j],high[i],*UV,mat)
    mesh.quad(*low[::-1],*UV,mat);mesh.quad(*high,*UV,mat)


def directory(board,style='metal',palette=None):
    """Two uprights, framed address header and stacked printed tenant panels."""
    m=Mesh(); dark=m.paint(tuple(v/255 for v in palette[0]) if palette else ((.16,.19,.20) if style!='timber' else (.36,.25,.16)))
    edge=m.paint(tuple(v/255 for v in palette[2]) if palette else (.57,.59,.56)); ink=m.paint((1,1,1),board.material)
    w=board.physical_width; h=board.physical_height; bottom=.38
    for x in (-w/2-.065,w/2+.065):
        box(m,(x,0),(1,0),.10,.14,-.08,bottom+h+.10,dark)
        box(m,(x,0),(1,0),.13,.17,bottom+h+.10,bottom+h+.125,edge)
    box(m,(0,0),(1,0),w+.025,.10,bottom-.025,bottom+h+.025,dark)
    # Runtime CDAE flips V on export; the already-flipped bitmap uses V=0 at
    # board top in this mesh. Both faces read normally, never mirror the back.
    uv=((0,board.used_ratio),(1,board.used_ratio),(1,0),(0,0))
    m.quad((-w/2,-.056,bottom),(w/2,-.056,bottom),(w/2,-.056,bottom+h),(-w/2,-.056,bottom+h),*uv,ink)
    m.quad((w/2,.056,bottom),(-w/2,.056,bottom),(-w/2,.056,bottom+h),(w/2,.056,bottom+h),*uv,ink)
    return m


def trolley_shelter(style='metal',detail=True,cart_count=5):
    """3.2 x 2.4 m open-front shelter with nested carts; entrance faces -Y."""
    m=Mesh();steel=m.paint((.34,.40,.40));roof=m.paint((.20,.32,.32));trim=m.paint((.80,.79,.70))
    for x in (-1.50,1.50):
        for y in (-1.10,1.10):box(m,(x,y),(1,0),.065,.065,0,2.30,steel)
        for z in (.40,.90):beam(m,(x,-1.1,z),(x,1.1,z),.045,steel)
    # Roof chords form a low ridged rain canopy. Thin closed planes retain
    # a visible underside, unlike a floating single-sided transparent sheet.
    chords=((-1.64,2.30),(-.55,2.49),(.55,2.49),(1.64,2.30))
    for (x,z),(xx,zz) in zip(chords,chords[1:]):
        low=[(x,-1.24,z),(xx,-1.24,zz),(xx,1.24,zz),(x,1.24,z)]
        top=[(px,py,pz+.055) for px,py,pz in low]
        m.quad(*top,*UV,roof);m.quad(*low[::-1],*UV,roof)
        for i in range(4):
            j=(i+1)%4;m.quad(low[i],low[j],top[j],top[i],*UV,roof)
        beam(m,(x,-1.25,z),(xx,-1.25,zz),.07,trim)
    beam(m,(-1.5,1.1,.9),(1.5,1.1,.9),.045,steel)
    if detail:
        for x,y in ((-.65,.55),(.65,.55),(-.65,.10),(.65,.10),(-.65,-.35))[:max(0,min(5,cart_count))]:
            trolley(m,(x,y),steel,roof)
    return m


def trolley(m,centre,steel,handle):
    x,y=centre
    # Nested tapered basket: open wire rails and a small solid base, not an
    # opaque cuboid. Five carts are enough to read as a station at road speed.
    lower=[(x-.24,y-.27,.56),(x+.24,y-.27,.56),(x+.24,y+.30,.56),(x-.24,y+.30,.56)]
    upper=[(x-.30,y-.38,1.02),(x+.30,y-.38,1.02),(x+.30,y+.36,1.02),(x-.30,y+.36,1.02)]
    for i in range(4):
        j=(i+1)%4
        beam(m,lower[i],lower[j],.018,steel);beam(m,upper[i],upper[j],.023,steel)
        beam(m,lower[i],upper[i],.018,steel)
        beam(m,(np.asarray(lower[i])+upper[i])/2,(np.asarray(lower[j])+upper[j])/2,.014,steel)
    for side in (-1,1):
        beam(m,(x+side*.24,y-.28,.18),(x+side*.24,y+.30,.18),.028,steel)
        beam(m,(x+side*.24,y-.28,.18),(x+side*.29,y-.40,1.05),.024,steel)
        for yy in (-.26,.29):box(m,(x+side*.24,y+yy),(1,0),.07,.11,.06,.17,handle)
    beam(m,(x-.30,y-.43,1.05),(x+.30,y-.43,1.05),.045,handle)


def furniture(kind,detail=True,cart_count=5):
    if kind=='trolley_shelter':return trolley_shelter(detail=detail,cart_count=cart_count)
    m=Mesh(); metal=m.paint((.23,.28,.29)); wood=m.paint((.60,.43,.27)); light=m.paint((.80,.80,.73))
    if kind=='bench':
        for x in (-.65,.65):
            box(m,(x,0),(1,0),.065,.48,0,.44,metal)
            box(m,(x,.20),(1,0),.055,.055,.40,.84,metal)
        for y in (-.17,0,.17):box(m,(0,y),(1,0),1.65,.13,.43,.49,wood)
        for z in (.62,.78):box(m,(0,.22),(1,0),1.65,.055,z,z+.10,wood)
    elif kind=='bollard':
        box(m,(0,0),(1,0),.13,.13,0,.88,metal)
        box(m,(0,0),(1,0),.135,.135,.70,.78,light)
    elif kind=='bike_rack':
        for x in (-.35,.35):box(m,(x,0),(1,0),.045,.045,0,.80,metal)
        beam(m,(-.35,0,.8),(.35,0,.8),.045,metal)
    elif kind=='service_cabinet':
        box(m,(0,0),(1,0),.70,.40,0,1.1,light)
        box(m,(0,-.208),(1,0),.58,.025,.12,1.02,metal)
        for z in (.25,.35,.45):box(m,(0,-.225),(1,0),.43,.012,z,z+.018,light)
    elif kind=='planter':
        box(m,(0,0),(1,0),.75,.75,0,.48,light)
        soil=m.paint((.21,.18,.14));leaf=m.paint((.28,.38,.22))
        box(m,(0,0),(1,0),.65,.65,.481,.49,soil)
        for x,y in ((-.16,0),(.17,.12),(0,-.16)):
            box(m,(x,y),(1,0),.26,.25,.49,.76,leaf)
    else:raise ValueError('unsupported commercial furniture')
    return m


@lru_cache(maxsize=24)
def furniture_template(kind,rank):
    """Immutable local mesh templates reused by every instance in a worker."""
    count=0 if rank<3 else 2 if rank==3 else 3 if rank==4 else 5
    result=furniture(kind,detail=rank>=3,cart_count=count).arrays()
    for values in result:
        if isinstance(values,np.ndarray):values.flags.writeable=False
    return result


def _stable(spec):
    identity=getattr(spec,'property_identity',None) or {}
    source=getattr(getattr(spec,'evidence',None),'source_id',None)
    return str(source or identity.get('revision') or spec.seed)


def visuals(items,shared_sites=(),frame=None,origin=(0.,0.,0.)):
    """One bounded optional visual mesh and its exact immutable text assets."""
    from .quality import current
    rank=current().rank
    limit,_,_,pixels,_=budgets(rank)
    if not limit:return (),()
    from . import property_sign_text,property_programme
    from .property_palette import resolve as palette
    mesh=Mesh();boards=[];count=0
    for spec,lo,hi in sorted(items,key=lambda row:_stable(row[0])):
        identity=getattr(spec,'property_identity',None) or {}
        name=identity.get('display_name');programme=property_programme.for_spec(spec)
        if not name or identity.get('status') not in ('verified','supported') or programme is None:continue
        slot=sign_slot(spec,lo,hi)
        if slot is None:continue
        role={'grocery_store':'grocer','supermarket':'big_box','trade_units':'trade',
              'strip_shops':'artisan','clinic':'clinical','hospital':'clinical'}[programme.kind]
        c,u,n,width,z0,z1=slot
        # Stay within the text raster's aspect budget rather than stretching a
        # small bitmap into an arbitrarily long wall-wide business name.
        width=min(width,24*(z1-z0))
        region=spec.inference.selection.environment.region
        locale=identity.get('locale') or {'jp_temperate':'ja','korea':'ko',
            'china_north':'zh-Hans','china_south':'zh-Hans'}.get(region,'')
        try:board=property_sign_text.prepare_fascia(name,style=role,locale=locale,
            aspect=max(2.,width/(z1-z0)),palette=palette(spec),pixel_width=pixels)
        except (ValueError,OSError) as exc:
            log.debug('Property fascia omitted: %s',exc);continue
        c=c+n*.077
        material=mesh.paint((1,1,1),board.material)
        left=c-u*width/2;right=c+u*width/2
        mesh.quad((*left,z0),(*right,z0),(*right,z1),(*left,z1),
                  (0,board.used_ratio),(1,board.used_ratio),(1,0),(0,0),material)
        boards.append(board);count+=1
        if count>=limit:break
    if frame is not None and shared_sites:
        _shared(mesh,boards,items,shared_sites,frame,origin)
    return ((mesh.arrays(),) if mesh.points else ()),tuple({b.material:b for b in boards}.values())


def _shared(mesh,boards,items,shared_sites,target,origin):
    from shapely.geometry import Polygon,LineString
    from shapely.ops import unary_union
    from sitegen import property_directories as pd,shared_layouts as sl,shared_courts as sc
    from . import property_sign_text
    from .property_palette import for_site
    from .quality import current
    rank=current().rank
    _,board_limit,furniture_limit,_,directory_pixels=budgets(rank)
    nboards=0;furniture_count=0
    for court in sorted(shared_sites,key=lambda c:pd.member_key(c.plan.evidence.ref)):
        data=pd.catalogue()[1].get(pd.member_key(court.plan.evidence.ref))
        if data is None:continue
        palette=for_site(court,items)
        source=sc._frame(court.plan);e=court.plan.evidence
        boundary=Polygon(e.association_extent.outer,e.association_extent.holes)
        obstacles=[Polygon(p.outer,p.holes) for p in e.exclusions or ()]
        for spec,_,_ in items:
            fp=spec.footprint
            if fp is not None:
                p=sc.project_points([(x+origin[0],y+origin[1],0) for x,y in fp.outer],target,source)
                obstacles.append(Polygon(p[:,:2]).buffer(.3))
        is_layout=isinstance(court,sl.SharedLayout)
        if is_layout:
            obstacles.extend(LineString(r.points).buffer(r.width/2+.5) for r in court.routes)
            obstacles.extend(Polygon(p).buffer(.3) for p in court.stalls)
            ground=lambda xy:sl.height(court.coefficients,xy)
            owner=sl.sector_shape(court.plan,*map(int,court.sector.split('_')[1:])) if court.sector else boundary
        else:
            ground=lambda xy:np.c_[np.asarray(xy),np.ones(len(xy))]@court.plane
            owner=boundary
        occupied=unary_union(obstacles)
        admitted=[]
        def place(asset,position,angle):
            p=asset.arrays()[0] if isinstance(asset,Mesh) else asset[0]
            r=math.radians(angle);rotation=np.array(((math.cos(r),-math.sin(r)),(math.sin(r),math.cos(r))))
            xy=p[:,:2]@rotation.T+position
            shape=Polygon(xy).convex_hull.buffer(.18)
            if not boundary.covers(shape) or not owner.covers(shape) or occupied.intersects(shape) or any(shape.intersects(v) for v in admitted):return False
            if not is_layout and not unary_union([Polygon(p.boundary.outer,p.boundary.holes) for p in e.physical_extents]).covers(shape):return False
            heights=ground(np.asarray(shape.exterior.coords))
            if np.ptp(heights)>.12:return False
            z=float(np.max(heights))
            def transform(points):
                xy=points[:,:2]@rotation.T+position
                return sc.project_points(np.c_[xy,points[:,2]+z],source,target,origin)
            mesh.append(asset,transform);admitted.append(shape);return True
        try:directory_plan=pd.for_plan(court.plan)
        except ValueError as exc:
            log.debug('Property directory omitted: %s',exc);directory_plan=None
        if directory_plan is not None and nboards<board_limit:
            if len(directory_plan.boards)>board_limit-nboards:
                log.info('Property directory omitted: detail board budget (%s)',directory_plan.site_id)
                directory_plan=None
        if directory_plan is not None and nboards<board_limit:
            try:panels=property_sign_text.prepare(directory_plan,palette=palette,pixel_width=directory_pixels)
            except (ValueError,OSError) as exc:
                log.debug('Property directory text omitted: %s',exc);panels=()
            # A deliberately declared position wins. Automatic signs use only
            # complete landscape beds, never a vehicle/pedestrian circulation.
            display=data.get('display')
            candidates=[]
            if isinstance(display,dict):
                q=display.get('position');angle=display.get('heading_degrees',0)
                try:
                    if np.shape(q)==(2,) and np.isfinite(q).all() and isinstance(angle,(int,float)) and math.isfinite(angle):candidates=[(np.asarray(q,float),angle)]
                except (TypeError,ValueError):pass
            elif is_layout:
                candidates=[(np.asarray(p.shape().representative_point().coords[0]),0.) for p in court.beds[:16]]
            # All pages are a single assembly. Never show a partial directory
            # whose last occupants silently vanished due to the tile cap.
            if panels and len(panels)+nboards<=board_limit:
                assembly=Mesh()
                for i,board in enumerate(panels):
                    assembly.append(directory(board,directory_plan.style,palette),
                        lambda p,i=i:p+((i-(len(panels)-1)/2)*1.85,0.,0.))
                for position,angle in candidates:
                    if place(assembly,position,angle):
                        boards.extend(panels);nboards+=len(panels);break
                else:log.info('Property directory omitted: no clear placement for all %d pages (%s)',len(panels),directory_plan.site_id)
            elif panels:log.info('Property directory omitted: tile board budget (%s)',directory_plan.site_id)
        # Optional furniture positions are explicit site authoring data, not
        # fabricated from a nearby POI. The same clearance fitter validates all.
        rows=data.get('furniture',())
        if not isinstance(rows,(list,tuple)):continue
        for row in rows[:furniture_limit-furniture_count]:
            if not isinstance(row,dict):continue
            kind=row.get('kind');q=row.get('position');angle=row.get('heading_degrees',0)
            if np.shape(q)!=(2,) or not isinstance(angle,(int,float)) or not math.isfinite(angle):continue
            try:
                if not np.isfinite(q).all():continue
                asset=furniture_template(kind,rank)
            except (TypeError,ValueError):continue
            if place(asset,np.asarray(q,float),angle):furniture_count+=1
