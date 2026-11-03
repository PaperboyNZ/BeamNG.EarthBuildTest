"""Mixed accepted/cold skyline sectors, with exact emitted-geometry transforms.

Architectural plans remain in their source frames. Only one cached child plan is
loaded at a time; the retained skyline prefix stays within the existing vertex
budget. These products are render-only and confer no new physical ownership.
"""
from bisect import bisect_left
import hashlib
import json

import numpy as np

import geotiles
import inputwatch
from productcache import identity,Store
from . import products


def references(parent,values):
    """Validate the entire optional child inventory, without truncation."""
    children=set(geotiles.children(parent.gx,parent.gy,parent.z,geotiles.Z))
    if not isinstance(values,dict) or len(values)>len(children):return {}
    if any(type(k) is not tuple or len(k)!=2 or any(type(v) is not int for v in k) or
           k not in children or not products.valid_reference(ref) for k,ref in values.items()):return {}
    return {k:dict(values[k]) for k in sorted(values)}


def reference_revision(values):
    return identity({geotiles.key(*k):v for k,v in sorted(values.items())})


class SourceOwners:
    """Exclude accepted children at the complete-source ownership test.

    Called by tile_buildings before projecting/clipping an eligible source;
    never classify a child using the centre of a clipped/resolved footprint.
    """
    def __init__(self,parent,excluded):
        self.parent=parent
        self.excluded=frozenset(excluded)

    def owns(self,x,y):
        x,y=np.broadcast_arrays(np.asarray(x,np.float64),np.asarray(y,np.float64))
        scalar=x.ndim==0
        inside=np.asarray(self.parent.owns(x,y)).reshape(-1)
        points=np.c_[x.ravel(),y.ravel(),np.zeros(x.size)]
        lat,lon,_=geotiles.world_to_geodetic(self.parent.frame,points)
        gx,gy=geotiles.tile_of(lat,lon,geotiles.Z)
        for a,b in self.excluded:inside &= ~((gx==a)&(gy==b))
        return bool(inside[0]) if scalar else inside.reshape(x.shape)


class SkylinePrefix:
    """Same tallest-first complete-building prefix as the existing skyline.

    Inserted candidates can only move the cutoff towards taller work. Keeping
    its sorted prefix bounds temporary meshes even across sixteen dense plans.
    """
    def __init__(self,parent):
        import buildings as b
        self.parent=parent;self.limit=b.MAX_MESH_VERTS
        self.ranks=[];self.rows=[];self.vertices=0;self.cutoff=None
        self.considered=0;self.budget_limited=False

    def add(self,item,source,index):
        import buildings as b
        spec=item[0]
        rank=(-(float(spec.height or 0.)+float(spec.min_h or 0.)),str(spec.seed),source.key,index)
        self.considered+=1
        if self.cutoff is not None and rank>=self.cutoff:return
        mesh=b._sky_mesh((item,))
        if mesh is None:return
        from .geometry import sky_vertex_count
        cost=(sky_vertex_count(spec) if spec.footprint is not None else 5*len(b._sky_ring(spec)))
        cost=max(cost,len(mesh[0]))
        at=bisect_left(self.ranks,rank)
        self.ranks.insert(at,rank);self.rows.insert(at,(cost,mesh))
        self.vertices+=cost
        while self.vertices>self.limit:
            self.budget_limited=True
            cutoff=self.ranks.pop();last=self.rows.pop();self.vertices-=last[0]
            self.cutoff=cutoff if self.cutoff is None else min(self.cutoff,cutoff)
        if at>=len(self.rows):return
        if source.key!=self.parent.key:
            xyz=geotiles.world_map(source.frame,self.parent.frame,
                mesh[0]+np.r_[np.asarray(source.box[:2]),0.])-np.r_[np.asarray(self.parent.box[:2]),0.]
            self.rows[at]=(cost,(xyz,*mesh[1:]))

    def result(self):
        import buildings as b
        return b._concat([mesh for _,mesh in self.rows]) if self.rows else None


def _visible(spec):
    import buildings as b
    area=spec.footprint.area if spec.footprint is not None else abs(b._area2(spec.ring))/2
    return area>=b.SKY_MIN_AREA_M2


def _output_hash(mesh,lamps):
    digest=hashlib.sha256()
    if mesh is not None:
        for i in (0,1,2,3,5):
            array=np.ascontiguousarray(mesh[i])
            digest.update(array.dtype.str.encode());digest.update(str(array.shape).encode());digest.update(array.tobytes())
        digest.update(json.dumps(mesh[4]).encode())
    digest.update(json.dumps(lamps,separators=(',',':'),allow_nan=False).encode())
    return digest.hexdigest()


def skyline(parent,requested,cache_dir,md,raw,lamp_region=None):
    """Return complete hybrid geometry, or None while cold sources are pending.

    Validated accepted children exclude their entire source-owned inventory from
    fallback, including buildings intentionally absent from the accepted plan.
    A failed child remains a cold sector; its bytes never claim that plan's ID.
    """
    import buildings as b
    import roads
    import revisit
    requested=references(parent,requested)
    children=set(geotiles.children(parent.gx,parent.gy,parent.z,geotiles.Z))
    prefix=SkylinePrefix(parent);used={};physical={};lamps=[];lamp_limited=False
    def add_lamps(rows,source=None):
        nonlocal lamp_limited
        remaining=max(0,b.FAR_LAMP_MAX-len(lamps))
        if len(rows)>remaining:lamp_limited=True
        rows=rows[:remaining]
        if rows:
            lamps.extend(geotiles.world_map(source.frame,parent.frame,np.asarray(rows,float)).tolist()
                         if source is not None else rows)
    store=Store(cache_dir)
    with inputwatch.capture() as watched:
        for key,ref in requested.items():
            child=geotiles.geobox(*key)
            accepted=products.load_accepted(store,child,ref['key'],ref['revision'])
            if accepted is None:continue
            items=accepted.value['plans']
            for index,item in enumerate(items):
                if _visible(item[0]):prefix.add(item,child,index)
            size=max(child.box[2]-child.box[0],child.box[3]-child.box[1])
            built=b.built_squares(items,0.,0.,size)
            if built:
                cds=[md.cell(k,layers=('roads',),kind='background')
                     for k in roads.cells_of_tile(child.frame,child,None,margin=0.)]
                glow=b.far_lamps(child.frame,[c.layers.get('roads') for c in cds],*child.box[:2],size,
                                 built,raw,lamp_region,own=child.box)
                add_lamps(glow,child)
            used[key]=ref;physical[geotiles.key(*key)]=accepted.value['physical_revision']
            # Release this complete cached product before loading the next one.
            del item,items,accepted
        if set(used)!=children:
            keys=roads.cells_of_tile(parent.frame,parent,None,margin=0.)
            got=b.sky_items(parent.frame,parent.box,sorted(keys,key=str),md,raw,lamp_region,
                            own=SourceOwners(parent,used))
            if got is None:return None
            cold,glow=got
            for index,item in enumerate(cold):prefix.add(item,parent,index)
            add_lamps(glow)
            del cold,got
        samples=inputwatch.snapshot(watched)
    mesh=prefix.result()
    if mesh is None:lamps=[]
    representation=identity(dict(accepted=reference_revision(used),source_files=samples,
                                 output=_output_hash(mesh,lamps),generator=revisit.code_key()))
    metadata=dict(revision=reference_revision(used),sectors=physical,
                  acceptedSectors=len(used),requestedSectors=len(requested),
                  selectedBuildings=len(prefix.rows),consideredBuildings=prefix.considered,
                  budgetLimited=prefix.budget_limited,lampBudgetLimited=lamp_limited)
    return mesh,lamps,len(prefix.rows),representation,metadata
