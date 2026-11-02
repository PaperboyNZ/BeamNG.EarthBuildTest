-- Adversarial message/import order: coverage must not regress visible quality.
local dir=(arg[0]:match('^(.*)[/\\]') or '.')
local T=dofile(dir..'/testlib.lua')
local S=dofile(dir..'/stubs.lua')
local roads=require('beamngEarth/roads')
local geodesy=require('beamngEarth/geodesy')
local geotile=require('beamngEarth/geotile')
local a=geodesy.newAnchor(0,0)
local x,y=geotile.tileOf(0,0)
local k=geotile.key(x,y)
local frame={geotile.centre(17,x,y)}
local sx,sy=math.floor(x/4),math.floor(y/4)
local sk=geotile.key(sx,sy,15)
local gov={try=function() return true end,charge=function() end,chargeMotion=function() end}
roads.setGeo(true);roads.setFarGeo(true);roads.setSession('quality')
local function step(n,anchor,aid)
  for i=1,n do
    local before=S.calls.createObject_TSStatic or 0
    roads.update(gov,aid or 1,vec3(0,0,0),nil,anchor or a)
    T.check((S.calls.createObject_TSStatic or 0)-before<=1,'one shared import per frame')
  end
end
local function object(shape)
  for _,o in pairs(S.objects) do if o.fields.shapeName=='/'..shape..'.cdae' then return o end end
end
local function visible(shape) local o=object(shape);return o and not o.hidden end
local function far(shape)
  roads.onFarTile({anchorId=1,key=k,data={h=shape,frame=frame,shape='/'..shape..'.cdae',pos={0,0,0}}},1)
end
local function sky(shape)
  roads.onFarTile({anchorId=1,key=sk,data={h=shape,frame={geotile.centre(15,sx,sy)},
    shape='/'..shape..'.cdae',pos={0,0,0}}},1,'S')
end
local function progress(stage,shape,group,total,slots)
  roads.onBuildingProgress({anchorId=1,key=k,frame=frame,token='quality',group=group or '0',
    total=total or 1,stage=stage,slots=slots,parts={p0={shape='/'..shape..'.cdae',pos={0,0,0}}}},1)
end
local function reset() roads.clear();step(2);roads.setSession('quality') end
step(1)
far('far');step(3)
progress(0,'shell');step(3)
T.check(visible('far') and not object('shell'),'textured far coverage skips late shell import')
progress(1,'facade');step(3)
T.check(visible('facade') and not visible('far'),'complete facade replaces far')
sky('late-sky');step(3)
T.check(visible('facade') and not visible('late-sky'),'late skyline cannot suppress finer preview')
sky('revised-sky');step(3)
T.check(visible('facade') and not visible('revised-sky'),'skyline revision retains quality handoff')
local b=geodesy.newAnchor(0,.001)
roads.replace(b,2);step(3,b,2)
T.check(visible('facade') and not visible('revised-sky'),'quality ownership survives rebase')
roads.onBuildingProgress({anchorId=2,key=k,token='quality',cancel=true},2);step(3,b,2)
T.check(visible('far') and not visible('revised-sky'),'cancelled preview falls back to textured far')
roads.onFarDrop({anchorId=2,key=k});step(3,b,2)
T.check(visible('revised-sky'),'skyline can recover once all finer coverage is gone')

reset()
progress(0,'early-shell');step(3)
T.check(visible('early-shell'),'shell still fills genuinely missing coverage')
far('arriving-far');step(3)
T.check(visible('arriving-far') and not visible('early-shell'),'late far improves shell coverage')
progress(1,'group-a','0',2);step(3)
T.check(visible('arriving-far') and not visible('group-a'),'partial facade coverage retains whole far tile')
progress(0,'group-b-shell','1',2);step(3)
T.check(visible('arriving-far') and not object('group-b-shell'),'mixed shell/facade set cannot retire far')
progress(1,'group-b','1',2);step(3)
T.check(not visible('arriving-far') and visible('group-a') and visible('group-b'),'all facade groups hand off together')

reset()
progress(0,'obsolete-shell')
progress(1,'queued-facade')
step(3)
T.check(not object('obsolete-shell') and visible('queued-facade'),'superseded shell is never imported')

reset()
sky('first-sky');step(3)
far('child');step(3)
T.check(visible('first-sky') and not visible('child'),'skyline-first retains atomic coverage')
sky('waiting-revision') -- its previous parent will yield while this import waits
for dy=0,3 do for dx=0,3 do
  local child=geotile.key(sx*4+dx,sy*4+dy)
  if child~=k then roads.onFarTile({anchorId=1,key=child,data={h='empty',
    frame={geotile.centre(17,sx*4+dx,sy*4+dy)}}},1) end
end end
T.check(not visible('first-sky') and visible('child'),'complete children retire skyline')
local sibling=geotile.key(sx*4+(x%4+1)%4,y)
roads.onFarDrop({anchorId=1,key=sibling});step(3)
T.check(visible('child') and not visible('waiting-revision'),'revision inherits handoff changes made while waiting for import')
roads.onFarDrop({anchorId=1,key=sibling});step(3)
T.check(visible('child') and not visible('waiting-revision'),'missing sibling cannot resurrect retired skyline over fine child')

reset()
far('ready-before-sky');step(3)
sky('late-over-far');step(3)
T.check(visible('ready-before-sky') and not visible('late-over-far'),'late skyline preserves textured far child')

reset()
roads.onTile({anchorId=1,key=k,data={h='near',frame=frame,
  buildingChunks={v=1,visual={'bld'},collision={}},bld={shape='/final.cdae',pos={0,0,0}}}},1,a)
step(4)
sky('late-over-final');step(3)
T.check(visible('final') and not visible('late-over-final'),'late skyline preserves completed near buildings')

-- Standalone queue checks cover slot release and arrival during partial import.
reset()
local covered=false;local released={};local imported={}
local P=require('beamngEarth/buildingprogress').new({
  create=function(w)
    imported[#imported+1]=w.shape
    local o=createObject('TSStatic');o:registerObject('');return o.id
  end,
  made=function() end,delete=function(id) S.objects[id]:delete() end,
  slot=function(m,w) return m.slots and m.slots[w] end,
  release=function(sl) if sl then released[sl]=(released[sl] or 0)+1 end end,
  minimumStage=function() return covered and 1 or 0 end
})
local shell={anchorId=1,key=k,frame=frame,token='partial',group='0',total=1,stage=0,
  slots={p0='slot-a',p1='slot-b'},parts={p0={shape='/partial-a',pos={0,0,0}},p1={shape='/partial-b',pos={0,0,0}}}}
P:receive(shell,1);P:step(a);covered=true
T.check(not P:prepare(a),'new far coverage cancels remaining shell imports')
T.check(#imported==1 and released['slot-a']==1 and released['slot-b']==1,'partial shell releases all slots exactly once')
T.check(P.queuedParts==0 and not P:hasWork(),'cancelled shell leaves no queued work')
P:clear()
T.done('test_building_quality_handoff')
