"""Worker-side staged building groups and event-loop delivery.

Spatial/cost-bounded groups (at most twelve buildings), bounded imports and atomic manifests.
Only the additional shell is new geometry work; facade meshes become final LODs.
Transient previews never enter collision or persistent revisit content.
"""
from contextvars import ContextVar
from pathlib import Path
import json
import math
import os
import re
import tempfile
import pickle

LITE_MEMORY_BYTES = 32 << 20
GROUP_SPAN = 64.
GROUP_COST = 8192

ACTIVE = ContextVar('building_progress', default=None)
DETAIL = ContextVar('building_detail', default='full')
GROUP_SIZE = 12
VERSION = 1
MAX_MANIFEST_BYTES = 1 << 20
MAX_MANIFEST_GROUPS = 256
MAX_PARTS_PER_GROUP = 256
MAX_MANIFEST_PARTS = 4096
MAX_DELIVERY_PER_POLL = 4


def manifest_path(out_dir, token):
    if not isinstance(token,str) or not re.fullmatch(r'[0-9a-f]{32}', token):
        raise ValueError('invalid building progress token')
    import staging
    # Progress metadata is never read by the game. Keep frequent atomic updates
    # outside its file watcher; stale cancelled jobs join the staging age sweep.
    aside=staging.staging_dir(os.path.join(out_dir,'progress'))
    return Path(aside or out_dir)/f'bp_{token}.progress.tmp'


def cancellation_path(out_dir,token):
    """A token-specific tombstone outside the game's watched folder when possible."""
    return manifest_path(out_dir,token).with_name(f'bp_{token}.cancel.tmp')


def limit_detail(out_dir,token):
    """One-way per-job visual downgrade; collision and access still build fully."""
    path=manifest_path(out_dir,token).with_name(f'bp_{token}.lite.tmp')
    try:
        path.parent.mkdir(parents=True,exist_ok=True)
        path.touch(exist_ok=True)
        return True
    except OSError:return False


def cancel(out_dir,token):
    """Stop optional previews cooperatively; never abort final geometry.

    Keep the tombstone until the real worker completes, not merely its awaiting
    outer future. Staging's age sweep handles abandoned tokens after a crash.
    Returns False on filesystem failure; callers must also stop token delivery.
    """
    path=cancellation_path(out_dir,token)
    try:
        path.parent.mkdir(parents=True,exist_ok=True)
        path.touch(exist_ok=True)
        return True
    except OSError:return False


def _finite(value,low,high):
    try:return type(value) in (int,float) and math.isfinite(value) and low<=value<=high
    except OverflowError:return False


def _valid_manifest(data,token,key):
    """Validate the complete bounded v1 preview envelope before any delivery."""
    import geotiles
    fields={'v','token','key','frame','sequence','total','groups'}
    if not isinstance(data,dict) or set(data)!=fields:return False
    if type(data['v']) is not int or data['v']!=VERSION or data['token']!=token:return False
    if data['key']!=geotiles.key(*key):return False
    frame=data['frame']
    if not isinstance(frame,list) or len(frame)!=2 or not _finite(frame[0],-90,90) or not _finite(frame[1],-180,180):return False
    # Content always uses this geotile's exact WorldFrame centre. Accepting an
    # unrelated geographic frame would misplace otherwise valid preview meshes.
    if frame!=list(geotiles.centre(*key)):return False
    position=[float(v) for v in geotiles.geobox(*key).box[:2]]+[0.]
    if type(data['sequence']) is not int or not 1<=data['sequence']<=2**31-1:return False
    if type(data['total']) is not int or not 1<=data['total']<=MAX_MANIFEST_GROUPS:return False
    groups=data['groups']
    if not isinstance(groups,list) or not 1<=len(groups)<=min(data['total'],MAX_MANIFEST_GROUPS):return False
    seen=set();part_count=0
    for group in groups:
        if not isinstance(group,dict) or set(group)!={'group','stage','parts'}:return False
        gid,stage,parts=group['group'],group['stage'],group['parts']
        if not isinstance(gid,str) or not re.fullmatch(r'0|[1-9][0-9]{0,2}',gid):return False
        if int(gid)>=data['total'] or gid in seen or type(stage) is not int or stage not in (0,1,2):return False
        seen.add(gid)
        if not isinstance(parts,dict) or not 1<=len(parts)<=MAX_PARTS_PER_GROUP:return False
        part_count+=len(parts)
        if part_count>MAX_MANIFEST_PARTS:return False
        files=set()
        for what,part in parts.items():
            if not isinstance(what,str) or not re.fullmatch(r'p[0-9]{1,3}|bld(?:[0-9]{1,8})?',what):return False
            if (not isinstance(part,dict) or not {'shape','pos','pivot','relief'}<=set(part)
                    or set(part)-{'shape','pos','pivot','relief','center','cost'}):return False
            shape,pos=part['shape'],part['pos']
            if not isinstance(shape,str) or len(shape)>4096 or '\\' in shape or any(ord(c)<32 for c in shape):return False
            pieces=shape.split('/')
            if any(p in ('.','..') for p in pieces):return False
            match=re.fullmatch(rf'bp_{token}_{gid}_{stage}_([0-9]{{1,3}})\.cdae',pieces[-1])
            if not match or int(match[1])>=MAX_PARTS_PER_GROUP or shape in files:return False
            files.add(shape)
            if not isinstance(pos,list) or len(pos)!=3 or not all(_finite(v,-1e8,1e8) for v in pos):return False
            if pos!=position:return False
            if not _finite(part['pivot'],-1e6,1e6) or not _finite(part['relief'],0,1e6):return False
            if 'center' in part and (not isinstance(part['center'],list) or len(part['center'])!=3
                    or not all(_finite(v,-1e8,1e8) for v in part['center'])):return False
            if 'cost' in part:
                cost=part['cost']
                if (not isinstance(cost,dict) or set(cost)!={'bytes','vertices','primitives'}
                    or any(type(v) is not int or not 0<=v<=2**31 for v in cost.values())):return False
    return True


def _json_object(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('duplicate preview JSON field')
        result[key]=value
    return result


def _invalid_constant(value):
    raise ValueError('nonfinite preview JSON value')


def shell(items):
    import buildings as b
    from .geometry import horizontal
    from . import roofs
    m=b.Mesh()
    for spec,lo,hi in items:
        m.weather(spec,lo,hi)
        if spec.footprint is None or spec.inference is None:
            # Keep special structure geometry: a solid proxy could cover a bridge.
            continue
        fp=spec.footprint; mats=b._Looks(spec.seed)
        base=b.base_z(spec,lo,hi)+(spec.min_h or 0.)
        bottom=base if (spec.min_h or 0.)>.5 else lo-b.SKIRT_M
        # Complex outlines get a cheap envelope before roof solving/facades.
        # Keep courtyard holes and mapped elevated bases; this is render-only.
        simple_roof=spec.roof!='flat' and not fp.is_rectangle()
        top=base+spec.height+(spec.inference.roof_rise if simple_roof else 0.)
        for ring in (fp.outer,*fp.holes):
            for a,c in zip(ring,ring[1:]+ring[:1]):
                m.quad((*a,bottom),(*c,bottom),(*c,top),(*a,top),
                       (0,0),(1,0),(1,1),(0,1),mats[spec.facade])
        if spec.roof!='flat' and not simple_roof:roofs.draw(m,spec,top,mats,overhang=True)
        else:horizontal(m,fp,top,mats[spec.roof_mat],b.ROOF_UV_M)
    if not m.n:return None
    positions,uv,tris,mat,colours=m.arrays()
    return positions,uv,tris,mat,b.MATERIALS,colours


def local_view(frame,tile,x,y,camera=None):
    """Transform a transient priority hint into the tile's geometry frame."""
    import geotiles
    hx,hy=(camera.get('fx',0.),camera.get('fy',0.)) if isinstance(camera,dict) else (0.,0.)
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (x,y,hx,hy)):return None
    lat,lon,_=frame.enu_to_geodetic(x,y,0.)
    la2,lo2,_=frame.enu_to_geodetic(x+hx,y+hy,0.)
    px,py,_=geotiles.geodetic_to_world(tile.frame,lat,lon)
    ex,ey,_=geotiles.geodetic_to_world(tile.frame,la2,lo2)
    return tuple(map(float,(px-tile.box[0],py-tile.box[1],ex-px,ey-py)))


class Publisher:
    def __init__(self,out_dir,vfs_dir,tile,token,view=None):
        self.path=manifest_path(out_dir,token)
        self.out_dir,self.vfs_dir,self.tile,self.token=out_dir,vfs_dir,tile,token
        self.groups={};self.sequence=0
        self.total=0
        self.final_files={}
        self._previews_stopped=False
        self.detail=DETAIL.get()
        self.view=view
        # Keep solved roof envelopes across the three passes. A bounded job-local
        # working set avoids thrashing the smaller process-wide LRU on dense tiles.
        self.roof_cache={};self.roof_cache_vertices=0

    def checkpoint(self):
        """A cooperative optional-work checkpoint; final build loops always run."""
        if not self._previews_stopped:
            try:self._previews_stopped=cancellation_path(self.out_dir,self.token).exists()
            except OSError:self._previews_stopped=True
        return not self._previews_stopped

    def publish(self,group,stage,meshes,names=None):
        """Optional preview I/O must not prevent the final tile from building."""
        try:return self._publish(group,stage,meshes,names)
        except OSError:
            self._previews_stopped=True
            return False

    def _publish(self,group,stage,meshes,names=None):
        import buildings as b
        import blockworker
        import numpy as np
        if not self.checkpoint():return False
        if (self.total>MAX_MANIFEST_GROUPS or len(meshes)>MAX_PARTS_PER_GROUP
                or (str(group) not in self.groups and len(self.groups)>=MAX_MANIFEST_GROUPS)):
            self._previews_stopped=True
            return False
        self.path.parent.mkdir(parents=True,exist_ok=True)
        records={}
        pos=[float(v) for v in self.tile.box[:2]]+[0.]
        for i,mesh in enumerate(meshes):
            if not self.checkpoint():return False
            what=names[i] if names else f'p{i}'
            name=f'bp_{self.token}_{group}_{stage}_{i}.cdae'
            path=os.path.join(self.out_dir,name)
            # Inspect the exact encoded bytes already in memory. Avoid opening
            # and reading every newly written file a second time for metadata.
            stats={}
            def encoded(data):
                import fast
                n,med,lo,hi=fast._ef.cdae_zstats(data)
                pivot=float(med) if n else 0.
                stats.update(pivot=round(pivot,3),relief=round(max(abs(float(hi)-pivot),abs(pivot-float(lo))) if n else 0.,3))
            b.write(path,mesh,encoded_callback=encoded)
            if stage==2:self.final_files[what]=path
            records[what]=dict(shape=f'{self.vfs_dir}/{name}',pos=pos,
                               **stats)
            stored=[mesh]+([mesh[6]] if len(mesh)>6 and mesh[6] is not None else [])
            center=(np.asarray(mesh[0]).min(axis=0)+np.asarray(mesh[0]).max(axis=0))*.5+pos
            records[what]['center']=[float(v) for v in center]
            records[what]['cost']=dict(bytes=os.path.getsize(path),vertices=sum(len(m[0]) for m in stored),
                                       primitives=sum(len(np.unique(m[3])) for m in stored))
        if not self.checkpoint():return False
        groups=dict(self.groups)
        groups[str(group)]=dict(group=str(group),stage=stage,parts=records)
        data=dict(v=VERSION,token=self.token,
            key=self.tile.key,frame=[self.tile.frame.lat0,self.tile.frame.lon0],
            sequence=self.sequence+1,total=self.total,groups=list(groups.values()))
        # Bound temporary preview metadata too. Final meshes and group mapping
        # are still returned even if this optional publication is suppressed.
        if not _valid_manifest(data,self.token,_tile_key(self.tile.key)):
            self._previews_stopped=True
            return False
        encoded=json.dumps(data,separators=(',',':'),allow_nan=False).encode()
        if len(encoded)>MAX_MANIFEST_BYTES:
            self._previews_stopped=True
            return False
        if not self.checkpoint():return False
        blockworker._write_bytes(str(self.path),encoded)
        self.groups,self.sequence=groups,self.sequence+1
        return True

    def partition(self,items):
        """Stable compact replacement groups with bounded estimated facade work."""
        import numpy as np
        if hasattr(self,'group_indices') and self.item_count==len(items):
            return [[items[j] for j in group] for group in self.group_indices]
        from .quality import current
        quality=current()
        centres=[np.asarray(item[0].ring).mean(axis=0)[:2] for item in items]
        order=sorted(range(len(items)),key=lambda i:(math.floor(centres[i][0]/32),math.floor(centres[i][1]/32),
                     centres[i][0],centres[i][1],str(items[i][0].seed)))
        indices=[];group=[];cost=0
        for i in order:
            spec=items[i][0]
            work=len(spec.ring)*min(64,max(1,spec.floors or 1))*64
            distant=group and max(float(np.linalg.norm(centres[i]-centres[j])) for j in group)>GROUP_SPAN
            if group and (len(group)>=min(GROUP_SIZE,quality.group_size) or cost+work>min(GROUP_COST,quality.group_cost) or distant):
                indices.append(group);group=[];cost=0
            group.append(i);cost+=work
        if group:indices.append(group)
        self.group_indices=indices;self.item_count=len(items)
        return [[items[j] for j in group] for group in indices]

    def shells(self,items):
        import buildings as b
        from .quality import import_vertices
        if self.detail in ('very_low','low'):return
        groups=self.partition(items);self.total=len(groups)
        for i,group in self.view_order(groups):
            if not self.checkpoint():break
            try:
                mesh=shell(group)
                if mesh is not None:self.publish(i,0,b.split_mesh(mesh,min(b.V2_IMPORT_VERTS,import_vertices(0))))
            except OSError:
                self._previews_stopped=True
                break

    def build(self,items):
        import buildings as b
        from .quality import import_vertices
        from .plan import freeze_items
        items=freeze_items(items)
        if self.detail in ('very_low','low'):
            # One final tile product: no proxy, no spool and no repeated
            # growing manifests. Lossless splitting retains every triangle.
            mesh=b.build(items,lite=True)
            meshes=b.split_mesh(mesh,import_vertices()) if mesh is not None else []
            names=['bld' if i==0 else f'bld{i+1}' for i in range(len(meshes))]
            self.total=1
            if meshes and self.checkpoint():self.publish(0,2,meshes,names)
            return meshes,[dict(group='0',visual=names)] if meshes else []
        groups=self.partition(items);self.total=len(groups)
        meshes=[];mapping=[];cached={};used=0
        # All cheap facades are ready before optional close-detail work begins.
        # Large tiles spill exact reusable arrays to the job's temporary directory,
        # outside the game file watcher. The cache is removed on failure/cancel too.
        parent=self.path.parent
        parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='building-lite-',dir=parent) as spool:
            for i,group in self.view_order(groups):
                simple=[b.build([item],lite=True) for item in group]
                ready=[m for m in simple if m is not None]
                if ready and self.checkpoint():self.publish(i,1,b.split_mesh(b._concat(ready),min(b.V2_IMPORT_VERTS,import_vertices(1))))
                size=sum(a.nbytes for m in ready for a in m if hasattr(a,'nbytes'))
                if used+size<=LITE_MEMORY_BYTES:cached[i]=simple;used+=size
                else:
                    path=Path(spool)/f'{i}.pickle'
                    with path.open('wb') as stream:pickle.dump(simple,stream,protocol=5)
                    cached[i]=path
            for i,group in enumerate(groups):
                simple=cached.pop(i)
                if isinstance(simple,Path):
                    with simple.open('rb') as stream:simple=pickle.load(stream)
                ready=[m for m in simple if m is not None]
                from .quality import PROFILES
                if self.detail not in ('lite','very_low','low'):
                    try:
                        if self.path.with_name(f'bp_{self.token}.lite.tmp').exists():
                            self.detail=PROFILES[self.detail].fallback if self.detail in PROFILES else 'lite'
                    except OSError:pass
                if self.detail in ('lite','very_low','low'):
                    detailed=b.split_mesh(b._concat(ready),min(b.V2_IMPORT_VERTS,import_vertices())) if ready else []
                else:
                    state=DETAIL.set(self.detail)
                    try:detailed=b.build_parts(group,max_verts=min(b.V2_IMPORT_VERTS,import_vertices()),with_lod=True,lite_meshes=simple)
                    finally:DETAIL.reset(state)
                names=['bld' if k==0 else f'bld{k+1}' for k in range(len(meshes),len(meshes)+len(detailed))]
                meshes.extend(detailed);mapping.append(dict(group=str(i),visual=names))
                if detailed and self.checkpoint():self.publish(i,2,detailed,names)
        return meshes,mapping

    def view_order(self,groups):
        """Coverage first around the viewer; stable IDs and final content order."""
        rows=list(enumerate(groups))
        if not self.view:return rows
        import numpy as np
        x,y,hx,hy=self.view;length=math.hypot(hx,hy)
        def score(row):
            centre=np.mean([np.asarray(item[0].ring).mean(axis=0)[:2] for item in row[1]],axis=0)
            dx,dy=centre-[x,y];distance=math.hypot(dx,dy)
            facing=max(0.,(dx*hx+dy*hy)/(distance*length)) if distance>.001 and length>.001 else 0.
            return distance/(1.+2.*facing),row[0]
        return sorted(rows,key=score)


def begin(tracker,key):
    import uuid
    token=uuid.uuid4().hex
    if not hasattr(tracker,'_building_progress'):tracker._building_progress={}
    tracker._building_progress[key]=dict(token=token,seen={})
    return token


def _tile_key(value):
    import geotiles
    parsed=geotiles.parse(value)
    if parsed is None or parsed[0]!=geotiles.Z:raise ValueError('invalid progress geotile key')
    return parsed[1:]


def poll(tracker,conn,aid,key,limit=4):
    job=getattr(tracker,'_building_progress',{}).get(key)
    server=getattr(conn,'s',None)
    if not job or server is None or aid!=tracker.aid:return
    if type(limit) is not int or limit<0:return
    limit=min(limit,MAX_DELIVERY_PER_POLL)
    if not limit:return
    try:
        if cancellation_path(server.out_dir,job['token']).exists():return
        path=manifest_path(server.out_dir,job['token'])
        stat=path.stat()
        if stat.st_size>MAX_MANIFEST_BYTES:return
        stamp=(stat.st_mtime_ns,stat.st_size,stat.st_ino)
        if job.get('stamp')!=stamp:
            with path.open('rb') as stream:raw=stream.read(MAX_MANIFEST_BYTES+1)
            if len(raw)>MAX_MANIFEST_BYTES:return
            data=json.loads(raw,object_pairs_hook=_json_object,parse_constant=_invalid_constant)
            if not _valid_manifest(data,job['token'],key):return
            if 'data' in job and data['sequence']<=job['data']['sequence']:return
            job['data']=data;job['stamp']=stamp
        data=job['data']
    except (OSError,ValueError,TypeError,RecursionError):return
    count=0
    for group in data['groups']:
        if job['seen'].get(group['group'],-1)>=group['stage']:continue
        if count>=limit:break
        try:
            if cancellation_path(server.out_dir,job['token']).exists():return
        except OSError:return
        msg=dict(type='building_progress',anchorId=aid,key=data['key'],token=job['token'],
                 frame=data['frame'],total=data.get('total',0),group=group['group'],stage=group['stage'],parts=group['parts'])
        pool=getattr(server,'pool_shapes',None)
        if pool:msg['slots']=pool(conn,{w:os.path.basename(p['shape']) for w,p in group['parts'].items()})
        conn.send(msg);job['seen'][group['group']]=group['stage'];count+=1


def finish(tracker,conn,aid,key,success,token=None):
    """Finish a tracker token; optional expected token rejects stale callbacks.

    Failure cancels worker previews before dropping delivery. A tombstone remains
    until actual worker completion/age sweep; cancellation never stops its final
    content/colliders. Old callers may omit token for compatibility.
    """
    if aid != tracker.aid:return None
    jobs=getattr(tracker,'_building_progress',{})
    job=jobs.get(key)
    if job is None:return
    if token is not None and token!=job['token']:return
    jobs.pop(key)
    server=getattr(conn,'s',None)
    if server is not None:
        if not success:cancel(server.out_dir,job['token'])
        try:manifest_path(server.out_dir,job['token']).unlink(missing_ok=True)
        except OSError:pass
    import geotiles
    if not success:conn.send(dict(type='building_progress',anchorId=aid,key=geotiles.key(*key),
                                 token=job['token'],cancel=True))
    return job['token']
