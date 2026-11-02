local dir=(arg[0]:match('^(.*)[/\\]') or '.')
local T=dofile(dir..'/testlib.lua')
local S=dofile(dir..'/stubs.lua')
local manifest=require('beamngEarth/sector_manifest')
local key='g17_65536_65536'
local function data()
  local d={key=key,frame={0,0},physicalHash=string.rep('a',16),
    bld={shape='/old.cdae',pos={0,0,0}},bldcol={shape='/collision.cdae',pos={0,0,0}},
    shapeHashes={bld=string.rep('b',64),bldcol=string.rep('c',64)},
    buildingChunks={v=1,visual={'bld'},collision={'bldcol'}}}
  d.sectorManifest={v=1,producer={namespace='beamng-earth/geotile',feature_id=key},
    frame={type='geotile-world-v1',origin={0,0}},topology='closed-v1',
    physical={revision=d.physicalHash,parts={{part='bldcol',sha256=d.shapeHashes.bldcol}}},
    visual={revision=string.rep('d',64),depends_on=d.physicalHash,parts={{part='bld',sha256=d.shapeHashes.bld}}}}
  return d
end
T.check(manifest.valid(data(),key,true),'complete supported manifest accepted')
T.check(manifest.valid({},key,false) and not manifest.valid({},key,true),'missing manifests require explicit legacy negotiation')
for _,mutate in ipairs({
  function(d) d.sectorManifest.v=2 end,
  function(d) d.sectorManifest.topology='multi-level' end,
  function(d) d.sectorManifest.producer.feature_id='another' end,
  function(d) d.sectorManifest.frame.origin[1]=0/0 end,
  function(d) d.sectorManifest.frame.origin[2]=1 end,
  function(d) d.sectorManifest.visual.depends_on='old' end,
  function(d) d.sectorManifest.physical.parts={} end,
  function(d) d.sectorManifest.visual.parts[2]=d.sectorManifest.visual.parts[1] end,
  function(d) d.sectorManifest.visual.parts[3]=d.sectorManifest.visual.parts[1] end,
  function(d) d.sectorManifest.visual.parts.extra={} end,
  function(d) d.shapeHashes.bld='changed' end,
  function(d) d.extra={shape='/undeclared.cdae',pos={0,0,0}} end,
  function(d) d.sectorManifest.physical.parts[1].part='bld' end,
}) do
  local d=data();mutate(d);T.check(not manifest.valid(d,key,true),'malformed/incomplete resource inventory rejected')
end
local roads=require('beamngEarth/roads')
local geo=require('beamngEarth/geodesy').newAnchor(0,0)
roads.setGeo(true);roads.setSectorManifest(1)
local old=data();old.h='old'
T.check(roads.onTile({key=key,data=old,h='old',anchorId=1},1,geo),'negotiated production tile accepted')
local gov={try=function() return true end,charge=function() end,chargeMotion=function() end}
for i=1,8 do roads.update(gov,1,vec3(),nil,geo) end
local oldObject
for _,o in pairs(S.objects) do if o.fields.shapeName=='/old.cdae' then oldObject=o end end
T.check(oldObject~=nil,'old visual resident')
local malformed=data();malformed.h='new';malformed.sectorManifest.physical.revision='wrong'
T.check(not roads.onTile({key=key,data=malformed,h='new',anchorId=1},1,geo),'invalid replacement rejected before retirement')
roads.update(gov,1,vec3(),nil,geo)
T.check(oldObject and S.objects[oldObject.id]==oldObject,'invalid replacement leaves accepted scene object intact')
T.done('test_sector_manifest')
