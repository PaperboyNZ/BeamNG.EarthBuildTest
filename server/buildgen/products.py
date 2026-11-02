"""Persistent accepted plans, physical products and independent visual upgrades."""
from runtimeprofiler import step as profile_step
from pathlib import Path
import hashlib,json,math,os,pickle,re
from productcache import Store,identity
from sitegen.identity import SourceIdentity,SourceRevision,GeographicFrame
import inputwatch


def address(tile,content_dependencies):
    import revisit,dem
    source=SourceIdentity('beamng-earth/geotile',tile.key)
    revision=SourceRevision(source,str(content_dependencies))
    frame=GeographicFrame(float(tile.frame.lon0),float(tile.frame.lat0))
    dependencies=dict(source=revision.to_dict(),frame=frame.to_dict(),generator=revisit.code_key(),
                      terrain_decoder=dem.DECODED_VERSION,plan_schema=__import__('buildgen.plan',fromlist=['SCHEMA_VERSION']).SCHEMA_VERSION,
                      street_access_materials=str(content_dependencies))
    return identity(dependencies),dependencies


def _replace_paths(value,old,new):
    return json.loads(json.dumps(value,separators=(',',':'),sort_keys=True).replace(old,new))


def valid_reference(value):
    """Internal immutable-product reference, independent of session shape paths."""
    return (isinstance(value,dict) and set(value)=={'key','revision'} and
            all(isinstance(value[k],str) and re.fullmatch(r'[a-f0-9]{64}',value[k]) for k in value))


def _current_inputs(records):
    if not isinstance(records,tuple) or len(records)>inputwatch.MAX_FILES:return False
    for row in records:
        if not isinstance(row,tuple) or len(row)!=2 or not isinstance(row[0],str):return False
        stamp=row[1]
        if stamp is not None and (not isinstance(stamp,tuple) or len(stamp)!=2 or
                                  any(type(v) is not int or v<0 for v in stamp)):return False
    return inputwatch.current(records)


def load_accepted(store,tile,key,revision=None):
    """Resolve this exact accepted plan, with current source and frame checks.

    Failure is a normal cache miss. A reference cannot select another geotile,
    an obsolete generator or a replacement that raced its requested revision.
    """
    from .plan import BuildingPlan
    import revisit
    plan=store.load('accepted-plan',key)
    if (plan.status!='ready' or not isinstance(plan.value,dict) or
            not {'plans','physical_revision','inputs','dependencies'}<=set(plan.value) or
            revision is not None and plan.revision!=revision):return None
    value=plan.value;deps=value['dependencies'];items=value['plans']
    if (not isinstance(deps,dict) or not isinstance(deps.get('source'),dict) or identity(deps)!=key or
            deps.get('source',{}).get('identity')!=SourceIdentity('beamng-earth/geotile',tile.key).to_dict() or
            deps.get('frame')!=GeographicFrame(float(tile.frame.lon0),float(tile.frame.lat0)).to_dict() or
            deps.get('generator')!=revisit.code_key() or not _current_inputs(value['inputs']) or
            not isinstance(value['physical_revision'],str) or
            not re.fullmatch(r'[a-f0-9]{16}',value['physical_revision']) or
            not isinstance(items,tuple) or not items or
            any(not isinstance(it,tuple) or len(it)!=3 or type(it[0]) is not BuildingPlan or
                any(type(z) not in (float,int) or not math.isfinite(z) for z in it[1:]) for it in items)):
        return None
    return plan


def retain(worker,tile,key,dependencies,P,out_dir,vfs_dir,n,info,watched):
    """Commit only complete accepted plans and their matching physical revision."""
    if not getattr(P,'plans',None) or watched is None:return False
    names=worker.geo_names(tile.key,parts=info.get('parts'))
    data=json.loads((Path(out_dir)/names['json']).read_text())
    if 'bldcol' not in info.get('parts',{}):return False
    visual=set(data.get('buildingChunks',{}).get('visual',()))
    if not visual:return False
    store=Store(worker._s.cache_dir)
    planned=store.put('accepted-plan',key,dict(plans=P.plans,physical_revision=data['physicalHash'],
                     inputs=watched,dependencies=dependencies,shared_sites=getattr(P,'shared_courts',())))
    if planned.status!='ready':return False
    physical=_replace_paths(data,vfs_dir+'/', '@V@/')
    physical.pop('h',None);physical.pop('buildingGroups',None);physical.pop('buildingDetail',None)
    physical.pop('sectorManifest',None)
    for what in visual:physical.pop(what,None)
    physical['buildingChunks']['visual']=[]
    physical['shapeHashes']={k:v for k,v in physical.get('shapeHashes',{}).items() if k not in visual}
    if 'colliders' in physical:physical['colliders']={k:v for k,v in physical['colliders'].items() if k not in visual}
    blobs={}
    for what,name in names.items():
        if what in visual or what in ('json','inputs'):continue
        path=Path(out_dir)/name
        if path.is_file():blobs[name]=path.read_bytes()
    result=store.put('physical',key,dict(plan_revision=planned.revision,data=physical,files=blobs,n=n,
                      parts={k:v for k,v in info['parts'].items() if k not in visual},
                      skin_inputs=dict(chunks=P.chunks,ctx=P.ctx,walks=P.walks_raw),fuel_pads=P.fuel_pads))
    if result.status=='ready':info['acceptedPlan']=dict(key=key,revision=planned.revision)
    return result.status=='ready'



@profile_step('Building visual refinement')
def refine(worker,tile,key,out_dir,vfs_dir,detail):
    """Return a complete tile using only accepted plans plus changed visuals.

    A cache failure is a normal miss; no active physical resource is retired.
    No terrain, road, station, driveway, planting or collision generator runs.
    """
    import buildings as b
    from .progressive import ACTIVE
    store=Store(worker._s.cache_dir)
    plan=load_accepted(store,tile,key)
    if plan is None:return None
    physical=store.load('physical',key)
    if (physical.status!='ready' or not isinstance(physical.value,dict) or
            not {'plan_revision','data','files','n','parts','skin_inputs','fuel_pads'}<=set(physical.value) or
            physical.value['plan_revision']!=plan.revision):return None
    accepted=physical.value
    if accepted['data']['physicalHash']!=plan.value['physical_revision']:return None
    visual_key=identity(dict(plan=plan.revision,quality=detail))
    names=worker.geo_names(tile.key)
    origin=[float(v) for v in tile.box[:2]]+[0.]
    def build_visual():
        meshes,groups,ready=b.visual_products(plan.value['plans'])
        if not meshes:raise ValueError('accepted building plan produced no visual coverage')
        entries={};blobs={};parts={};hashes={}
        for index,mesh in enumerate(meshes):
            what='bld' if not index else f'bld{index+1}'
            name=worker.geo_names(tile.key,parts={what:{}})[what]
            path=Path(out_dir)/name
            existing=ready.get(what)
            if existing and Path(existing).is_file():worker._write_bytes(str(path),Path(existing).read_bytes())
            else:b.write(str(path),mesh)
            blob=path.read_bytes();info=worker._shape_info(str(path),origin,what);info['col']=False
            entries[what]=dict(shape='@V@/'+name,pos=origin,**{k:v for k,v in info.items() if k!='col'})
            parts[what]=info;blobs[name]=blob;hashes[what]=hashlib.sha256(blob).hexdigest()
        quality=ACTIVE.get().detail if ACTIVE.get() else detail
        return dict(entries=entries,files=blobs,parts=parts,hashes=hashes,groups=groups,detail=quality)
    visual=store.get_or_build('visual-'+detail.replace('_','-'),visual_key,build_visual,
                             valid=lambda:inputwatch.current(plan.value['inputs']) and
                                 (ACTIVE.get() is None or ACTIVE.get().detail==detail))
    if visual.value is None:return None
    visual=visual.value
    # Essential files are byte-identical to the previously accepted physical
    # product. Publish metadata last; failure leaves the client's complete stage.
    for name,blob in {**accepted['files'],**visual['files']}.items():
        worker._write_bytes(str(Path(out_dir)/name),blob)
    data=_replace_paths(accepted['data'],'@V@/',vfs_dir+'/')
    data.update(_replace_paths(visual['entries'],'@V@/',vfs_dir+'/'))
    data['buildingChunks']['visual']=list(visual['entries'])
    if visual['groups'] is not None:data['buildingGroups']=visual['groups']
    data['buildingDetail']=visual['detail']
    data['shapeHashes'].update(visual['hashes'])
    import sector
    data['sectorManifest']=sector.manifest(data)
    h=worker._content_hash(json.dumps(data,separators=(',',':'),sort_keys=True),vfs_dir)
    data['h']=h
    inputs=dict(accepted['skin_inputs'],h=h)
    worker._write_bytes(str(Path(out_dir)/names['inputs']),pickle.dumps(inputs,protocol=4))
    worker._write_bytes(str(Path(out_dir)/names['json']),json.dumps(data,separators=(',',':'),sort_keys=True).encode())
    with worker._geo_lock:
        worker._geo_inputs[tile.key]=inputs
        while len(worker._geo_inputs)>worker.GEO_INPUTS_KEPT:worker._geo_inputs.pop(next(iter(worker._geo_inputs)))
    worker._geo_stats['plan_reuse']=worker._geo_stats.get('plan_reuse',0)+1
    return vfs_dir+'/'+names['json'],accepted['n'],dict(h=h,parts={**accepted['parts'],**visual['parts']},
                                                     buildingDetail=visual['detail'],
                                                     acceptedPlan=dict(key=key,revision=plan.revision)),accepted['fuel_pads']
