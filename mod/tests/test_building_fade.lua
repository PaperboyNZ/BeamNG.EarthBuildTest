local dir=(arg[0]:match('^(.*)[/\\]') or '.')
local T=dofile(dir..'/testlib.lua')
local S=dofile(dir..'/stubs.lua')
local time=0
local fade=require('beamngEarth/buildingfade').new({enabled=true,clock=function() return time end})
local function make()
  local o=createObject('TSStatic');o:registerObject('')
  function o:updateInstanceRenderData() self.updates=(self.updates or 0)+1 end
  fade:register(o.id);return o
end
local function tick(ms) time=time+(ms or 25);fade:update();fade:commit() end
local function finish() for _=1,20 do tick() end end
local function bytes(o)
  local t={};for n in o.fields.instanceColor2:gmatch('[%d%.]+') do t[#t+1]=tonumber(n) end;return t
end
local old=make();T.check(old.hidden,'import starts hidden before any frame is rendered')
fade:hide(old.id,false);fade:commit();finish()
T.check(not old.hidden and not fade:busy(),'initial coverage settles opaque')
local new=make()
fade:hide(old.id,true);fade:hide(new.id,false);fade:commit()
T.check(not old.hidden and not new.hidden,'both objects remain resident during dissolve')
T.check(fade:held(old.id),'outgoing mesh cannot be deleted or recycle its slot')
local previous=0
for _=1,15 do
  tick()
  local a,b=bytes(old),bytes(new)
  T.check(a[1]==b[1] and a[2]==1 and b[2]==0,'paired versions use complementary masks')
  T.check(b[1]>=previous and b[1]<1,'coverage advances smoothly before completion');previous=b[1]
end
finish();T.check(old.hidden and not new.hidden and not fade:held(old.id),'retirement waits for final coverage')
fade:forget(old.id)

-- Rapid third revision waits, rather than overlapping three partial versions.
local third=make();local fourth=make()
fade:hide(new.id,true);fade:hide(third.id,false);fade:commit();tick(50)
local first=bytes(third)[1]
fade:hide(third.id,true);fade:hide(fourth.id,false);fade:commit()
T.check(fourth.hidden and bytes(third)[1]==first,'superseding version waits for current wave')
finish();finish()
T.check(new.hidden and third.hidden and not fourth.hidden,'coalesced newest version completes')

-- Repeated reconciliation does not restart the timer; reversal is coalesced.
fade:hide(fourth.id,true);fade:commit()
for _=1,5 do fade:hide(fourth.id,true);tick() end
T.check(bytes(fourth)[1]>0,'repeated hide requests make forward progress')
fade:hide(fourth.id,false);finish();finish()
T.check(not fourth.hidden and not fade:busy(),'visibility reversal returns to full coverage')
fade:hide(fourth.id,true);fade:commit();tick(5000)
T.check(bytes(fourth)[1]<.1,'long frame does not skip entire transition')
fade:finish();T.check(fourth.hidden and not fade:held(fourth.id),'rebase settles retired objects')
fade:clear();T.check(not next(fade.objects),'teardown forgets all state')

-- Integration with real roads/progressive ownership and slot deletion.
local create=createObject
function createObject(class)
  local o=create(class)
  function o:updateInstanceRenderData() end
  return o
end
FS={fileExists=function() return true end}
package.loaded['beamngEarth/stopwatch']={clock=function() return function() return time end end,
  new=function() local start=time;return function() return time-start end end}
package.loaded['beamngEarth/buildingfade']=nil
local roads=require('beamngEarth/roads')
local geotile=require('beamngEarth/geotile');local geodesy=require('beamngEarth/geodesy')
local x,y=geotile.tileOf(0,0);local key=geotile.key(x,y);local lat,lon=geotile.centre(17,x,y)
local anchor=geodesy.newAnchor(0,0)
local gov={try=function() return true end,charge=function() end,chargeMotion=function() end}
local function frame() time=time+25;roads.update(gov,1,nil,nil,anchor) end
local function frames() for _=1,20 do frame() end end
local function offer(stage,name)
  roads.onBuildingProgress({anchorId=1,key=key,token='fade',frame={lat,lon},total=1,group='0',stage=stage,
    parts={bld={shape='/test/'..name..'.cdae',pos={0,0,0}}}},1)
end
local function find(name)
  for _,o in pairs(S.objects) do if o.fields.shapeName=='/test/'..name..'.cdae' then return o end end
end
offer(0,'shell');frames();local shell=find('shell')
offer(1,'facade');frame();local facade=find('facade')
T.check(shell and facade and not shell.hidden and not facade.hidden,'real group replacement dissolves in place')
frame();T.check(S.objects[shell.id]~=nil,'delete queue retains outgoing progressive mesh')
frames();T.check(not S.objects[shell.id] and not facade.hidden,'old progressive mesh released after dissolve')
roads.clear();T.check(not roads.hasWork(),'clear drains transitions and owned objects')
roads.setGeo(true);roads.setFarGeo(true);roads.setSession('fade-slots')
roads.onFarTile({anchorId=1,key=key,data={h='far',frame={lat,lon},shape='/test/far.cdae',pos={0,0,0}}},1)
frames();local far=find('far');T.check(far and not far.hidden,'far coverage becomes fully visible')
local function near(hash,slot)
  return {anchorId=1,key=key,frame={lat,lon},slots={bld={'/test/slot_'..slot..'.cdae',1}},
    data={h=hash,physicalHash='unchanged',chunks={},buildingChunks={v=1,visual={'bld'},collision={'bldcol'}},
      bld={shape='/unused.cdae',pos={0,0,0}},bldcol={shape='/test/collider.cdae',pos={0,0,0}}}}
end
roads.onTile(near('near',701),1,anchor);frame();frame()
local nearOld=find('slot_701')
T.check(nearOld and not nearOld.hidden and not far.hidden,'far and complete near set dissolve together')
frames();T.check(far.hidden and not nearOld.hidden,'near coverage completes before distant mesh hides')
local collider=find('collider')
roads.onTile(near('refined',702),1,anchor);frame()
local nearNew=find('slot_702')
T.check(nearNew and not nearNew.hidden and not nearOld.hidden,'cached final revisions also dissolve')
local function contains(slots,n) for _,s in ipairs(slots) do if s[1]==n then return true end end;return false end
T.check(contains(roads.slotsHeld('fade-slots'),701),'outgoing slot remains held during dissolve')
T.check(not contains(roads.takeSlotsGone('fade-slots'),701),'outgoing slot cannot be reused early')
frames()
T.check(not S.objects[nearOld.id] and contains(roads.takeSlotsGone('fade-slots'),701),'slot releases only after outgoing object deletion')
T.check(find('collider')==collider,'visual dissolve preserves physical collider identity')
roads.clear()
T.done('test_building_fade')
