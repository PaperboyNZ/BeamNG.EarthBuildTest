-- Coverage and revision handoffs under a one-import frame budget. Renderer
-- opacity/dither is deliberately not simulated by these scene-object tests.
local dir=(arg[0]:match('^(.*)[/\\]') or '.')
local T=dofile(dir..'/testlib.lua')
local S=dofile(dir..'/stubs.lua')
local roads=require('beamngEarth/roads')
local geodesy=require('beamngEarth/geodesy')
local geotile=require('beamngEarth/geotile')
local a=geodesy.newAnchor(0,0)
local gx,gy=geotile.tileOf(0,0)
local k=geotile.key(gx,gy)
local frame={geotile.centre(17,gx,gy)}
local gov={try=function() return true end,charge=function() end,chargeMotion=function() end}
roads.setGeo(true);roads.setFarGeo(true);roads.setSession('test')
local function step(n,aid,anchor)
  for i=1,n do
    local before=S.calls.createObject_TSStatic or 0
    roads.update(gov,aid or 1,vec3(0,0,0),nil,anchor or a)
    T.check((S.calls.createObject_TSStatic or 0)-before<=1,'shared import budget')
  end
end
local function object(shape)
  for _,o in pairs(S.objects) do if o.fields.shapeName==shape then return o end end
end
local function visible(shape)
  local o=object(shape);return o and not o.hidden
end
local function far(hash,shape)
  return roads.onFarTile({anchorId=1,key=k,data={h=hash,frame=frame,shape=shape,pos={0,0,0}}},1)
end
local function near(hash,count,physical)
  local d={h=hash,frame=frame,physicalHash=physical,
    buildingChunks={v=1,visual={},collision={'bldcol'}}}
  for i=1,count do
    local w=i==1 and 'bld' or 'bld'..i
    d.buildingChunks.visual[i]=w
    d[w]={shape='/'..hash..'_'..w..'.cdae',pos={0,0,0}}
  end
  d.bldcol={shape='/collision.cdae',pos={0,0,0}}
  return {anchorId=1,key=k,h=hash,data=d}
end
step(1)
T.check(far('far1','/far1.cdae'),'initial distant tile accepted')
step(4)
T.check(visible('/far1.cdae'),'distant mesh visible')
T.check(far('far2','/far2.cdae'),'replacement distant tile accepted')
T.check(visible('/far1.cdae'),'old distant mesh retained before import')
local create=createObject
createObject=function(class) if class=='TSStatic' then error('simulated import failure') end;return create(class) end
step(4)
createObject=create
T.check(visible('/far1.cdae'),'failed distant replacement retains coverage')
far('far3','/far3.cdae')
step(4)
T.check(visible('/far3.cdae') and not visible('/far1.cdae'),'distant revision handoff')
local msg=near('lite',3,'physical')
roads.onTile(msg,1,a)
for i=1,8 do
  step(1)
  local n=0
  for _,w in ipairs(msg.data.buildingChunks.visual) do if visible('/lite_'..w..'.cdae') then n=n+1 end end
  T.check(n==0 or n==3,'cached near chunks exposed as a complete set')
  T.check(not (n>0 and visible('/far3.cdae')),'far and near never overlap')
  T.check(n==3 or visible('/far3.cdae'),'far retained until complete near set')
end
local col=object('/collision.cdae')
local replacement=near('full',5,'physical')
roads.onTile(replacement,1,a)
T.check(visible('/lite_bld.cdae'),'old near visuals retained during refinement')
roads.onTile(replacement,1,a) -- same-hash retransmission while still importing
for i=1,12 do
  step(1)
  local n=0
  for _,w in ipairs(replacement.data.buildingChunks.visual) do if visible('/full_'..w..'.cdae') then n=n+1 end end
  T.check(n==0 or n==5,'refinement is complete before exposure')
  T.check(not (n>0 and visible('/lite_bld.cdae')),'old and refined facade never overlap')
  T.check(n==5 or visible('/lite_bld.cdae'),'refinement retains old coverage')
  T.check(object('/collision.cdae')==col,'quality refinement preserves physical object identity')
end
T.check(visible('/full_bld.cdae'),'full refinement visible')
-- Rebase a replacement while its fallback is still live.
roads.onTile(near('again',2,'physical'),1,a)
step(1)
roads.newSession()
T.check(visible('/full_bld.cdae') and not visible('/again_bld.cdae'),'restart keeps incomplete replacement hidden')
local b=geodesy.newAnchor(0,.01)
roads.replace(b,2)
T.check(visible('/full_bld.cdae'),'retained visual survives rebase')
roads.clear()
T.check(not visible('/full_bld.cdae'),'clear hides retained visuals immediately')
-- Receipt is not readiness: all child messages can arrive before the last
-- child mesh is imported, while their parent must remain visible.
local sx,sy=math.floor(gx/4),math.floor(gy/4)
local sk=geotile.key(sx,sy,15)
roads.onFarTile({anchorId=1,key=sk,data={h='sky',frame={geotile.centre(15,sx,sy)},
  shape='/sky.cdae',pos={0,0,0}}},1,'S')
step(4)
for y=0,3 do for x=0,3 do
  local child=geotile.key(sx*4+x,sy*4+y)
  if child~=k then roads.onFarTile({anchorId=1,key=child,data={h='empty',
    frame={geotile.centre(17,sx*4+x,sy*4+y)}}},1) end
end end
far('last','/last.cdae')
T.check(visible('/sky.cdae'),'sky remains after all messages arrive but last mesh is unready')
step(4)
T.check(not visible('/sky.cdae') and visible('/last.cdae'),'last successful import atomically hands off skyline')
roads.clear();step(2)
roads.setSession('slots')
local pooled=near('pooled',1,'same-physics')
pooled.slots={bld={'/p/slot_501.cdae',1},bldcol={'/p/slot_502.cdae',1}}
roads.onTile(pooled,1,a);step(5)
local nextPooled=near('pooled-next',2,'same-physics')
nextPooled.slots={bld={'/p/slot_511.cdae',1},bld2={'/p/slot_512.cdae',1},bldcol={'/p/slot_513.cdae',1}}
roads.takeSlotsGone('slots')
roads.onTile(nextPooled,1,a)
local function contains(slots,n)
  for _,sl in ipairs(slots) do if sl[1]==n then return true end end;return false
end
T.check(contains(roads.slotsHeld('slots'),501),'retained visual slot is reported held on reconnect')
T.check(contains(roads.slotsHeld('slots'),502),'original physical slot remains held')
local gone=roads.takeSlotsGone('slots')
T.check(not contains(gone,501) and contains(gone,513),'old visual not released; unused replacement collider released')
step(8)
T.check(contains(roads.takeSlotsGone('slots'),501),'retained visual slot released after actual deletion')
T.check(not contains(roads.slotsHeld('slots'),501) and contains(roads.slotsHeld('slots'),502),'only current visual and original physical slots remain')
-- Refinement may arrive across a rebase. Retaining physical objects must still
-- honor a newly-required exact variant, and later return to the base shape.
roads.replace(b,2)
local exact=near('rebase-quality',1,'same-physics')
exact.anchorId=2;exact.exact={bldcol='/collision-exact.cdae'}
exact.slots={['x:bldcol']={'/p/slot_520.cdae',1}}
roads.onTile(exact,2,b)
T.check(object('/p/slot_502.cdae')~=nil,'physical base retained while exact replacement is queued')
step(8,2,b)
T.check(object('/p/slot_520.cdae')~=nil,'refinement honors required exact physical variant')
local base=near('base-quality',1,'same-physics');base.anchorId=2
roads.onTile(base,2,b);step(8,2,b)
T.check(object('/p/slot_502.cdae')~=nil and object('/p/slot_520.cdae')==nil,'refinement can return retained collision to base')
T.done('test_building_streaming')
