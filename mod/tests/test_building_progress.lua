local dir=(arg[0]:match('^(.*)[/\\]') or '.')
local T=dofile(dir..'/testlib.lua')
local S=dofile(dir..'/stubs.lua')
local rows={}
package.loaded['beamngEarth/trees']={onGeoRows=function(key,_,items) rows[key]=items end,dropKey=function() end}
local geodesy=require('beamngEarth/geodesy')
local geotile=require('beamngEarth/geotile')
local roads=require('beamngEarth/roads')
local anchor=geodesy.newAnchor(0,0)
local x,y=geotile.tileOf(0,0);local key=geotile.key(x,y)
local lat,lon=geotile.centre(17,x,y)
local gov={try=function() return true end,charge=function() end,chargeMotion=function() end}
roads.setSession('progress-test');roads.setGeo(true)
local function frame()
  local count=S.calls.createObject_TSStatic or 0
  roads.update(gov,1,nil,nil,anchor)
  T.check((S.calls.createObject_TSStatic or 0)-count<=1,'one shared import per frame')
end
local function msg(stage,parts)
  return {anchorId=1,key=key,token='revision-1',frame={lat,lon},group='0',stage=stage,parts=parts}
end
local function part(name) return {shape='/test/'..name..'.cdae',pos={0,0,0}} end
local function shown(name)
  for _,o in pairs(S.objects) do if o.fields.shapeName=='/test/'..name..'.cdae' and not o.hidden then return o.id end end
end
T.check(roads.onBuildingProgress(msg(0,{p0=part('shell')}),1),'shell accepted before road content')
frame();T.check(shown('shell')~=nil,'shell appears before final tile')
T.check(roads.onBuildingProgress(msg(1,{p0=part('facade-a'),p1=part('facade-b')}),1),'facade replacement queued')
frame();T.check(shown('shell')~=nil and not shown('facade-a'),'old shell retained during partial replacement')
frame();T.check(not shown('shell') and shown('facade-a') and shown('facade-b'),'whole replacement swapped in one frame')
T.check(not roads.onBuildingProgress(msg(0,{p0=part('stale')}),1),'older stage rejected')
roads.onBuildingProgress(msg(2,{bld=part('detail')}),1);frame()
local detail=shown('detail');T.check(detail~=nil,'fine detail appears before roads finish')
T.check(S.objects[detail].fields.dynamic=='false','completed preview enables native static-manager LOD')
local data={chunks={},buildingChunks={v=1,visual={'bld'},collision={}},
  buildingGroups={{group='0',visual={'bld'}}},bld=part('final-file'),h='final',
  props={groups={'door'},items={{0,0,0,0,0,1,2,0}}}}
local count=S.calls.createObject_TSStatic or 0
roads.onTile({anchorId=1,key=key,frame={lat,lon},data=data,buildingProgressToken='revision-1'},1,anchor)
frame()
T.check((S.calls.createObject_TSStatic or 0)==count,'complete final object adopted without duplicate import')
T.check(shown('detail')==detail,'adoption preserves the visible object')
T.check(not roads.onBuildingProgress(msg(2,{bld=part('late')}),1),'late preview rejected after final adoption')
roads.onDrop({anchorId=1,key=key});frame();T.check(not shown('detail'),'adopted mesh unloads with tile')

local m=msg(0,{p0=part('cancelled')});m.token='revision-2'
roads.onBuildingProgress(m,1)
roads.onBuildingProgress({anchorId=1,key=key,token='revision-2',cancel=true},1)
frame();T.check(not shown('cancelled'),'cancelled queued stage never imports')

data.h='another';data.bld=part('delayed-building');data.buildingGroups=nil
roads.onTile({anchorId=1,key=key,frame={lat,lon},data=data},1,anchor)
T.check(rows['p'..key] and #rows['p'..key]==0,'front-door props withheld while building imports')
frame();T.check(rows['pd'..key] and #rows['pd'..key]==1,'front-door props released after host building')
roads.clear()

-- Isolate the far/near handover and failure paths from the roads scheduler.
local farVisible=true;local fail=false;local releases=0
local P=require('beamngEarth/buildingprogress').new({
  create=function(w)
    if fail then error('fixture import failure') end
    local o=createObject('TSStatic');o:setField('shapeName',0,w.shape);o:registerObject('');return o.id
  end,
  delete=function(id) local o=S.objects[id];if o then o:delete() end end,
  made=function() end,release=function(s) if s then releases=releases+1 end end,
  slot=function(m,w) return m.slots and m.slots[w] end,
  farVisible=function() return farVisible end,hideFar=function() farVisible=false end
})
local a=msg(2,{bld=part('far-adopt-a')});a.total=2
P:receive(a,1);P:step(anchor)
T.check(not shown('far-adopt-a') and farVisible,'partial near coverage retains the complete far mesh')
local c=msg(2,{bld2=part('far-adopt-b')});c.total=2;c.group='1'
P:receive(c,1);P:step(anchor)
T.check(shown('far-adopt-a') and shown('far-adopt-b') and not farVisible,'complete near coverage replaces far mesh together')
-- Simulate a far object arriving between progress and final content.
farVisible=true;P:visibility(key)
local t={gkey=key,parts={bld=part('canonical-a'),bld2=part('canonical-b')},slots={},exactShape={},
  data={buildingGroups={{group='0',visual={'bld'}},{group='1',visual={'bld2'}}}}}
P:attach(t,{buildingProgressToken='revision-1'})
T.check(t.bld and t.bld2 and shown('far-adopt-a') and shown('far-adopt-b'),'adoption preserves visibility across far handover')
T.check(not P:hasWork() and next(P.entries)==nil,'adoption leaves no transient work')
P:clear();farVisible=true
a=msg(2,{bld=part('partial-adopt')});a.total=2;a.token='partial'
P:receive(a,1);P:step(anchor)
t={gkey=key,parts={bld=part('canonical-a'),bld2=part('normal-rest')},slots={},exactShape={},
  data={buildingGroups={{group='0',visual={'bld'}},{group='1',visual={'bld2'}}}}}
P:attach(t,{buildingProgressToken='partial'})
T.check(P.entries[key] and not shown('partial-adopt'),'partial final adoption retains its handover state')
local rest=createObject('TSStatic');rest:setField('shapeName',0,'/test/normal-rest.cdae');rest:registerObject('')
t.bld2=rest.id;P:sync(t)
T.check(shown('partial-adopt') and shown('normal-rest') and not farVisible,'normal completion reveals adopted and never-previewed groups together')
T.check(not P.entries[key],'handover state released after every final group completes')
P:clear();farVisible=false
a=msg(0,{p0=part('failure-shell')});a.token='failure';a.total=1
P:receive(a,1);P:step(anchor)
c=msg(1,{p0=part('failure-facade')});c.token='failure';c.total=1
P:receive(c,1);fail=true;P:step(anchor);fail=false
T.check(shown('failure-shell') and not shown('failure-facade'),'failed replacement retains last complete geometry')
local before=S.calls.setPosRot or 0
P:place(geodesy.newAnchor(.001,.001))
T.check((S.calls.setPosRot or 0)>before,'visible progress follows anchor rebases')
local stale=msg(1,{p0=part('stale-anchor')});stale.slots={p0={1,2,'session',path='/test/stale.cdae'}}
T.check(not P:receive(stale,2) and releases==1,'stale-anchor message releases its pooled shape')
P:receive({anchorId=1,key=key,token='failure',cancel=true},1)
T.check(not shown('failure-shell') and not P:receive(c,1),'cancellation drops previews and rejects late stages')
for i=1,300 do P:receive({anchorId=1,key=key,token='closed-'..i,cancel=true},1) end
T.check(#P.closedOrder<=256,'completed revision bookkeeping stays bounded')
P:clear()
a=msg(0,{p0=part('old-session')});a.token='old-session'
roads.onBuildingProgress(a,1);frame();roads.newSession();frame()
T.check(not shown('old-session'),'new server session clears transient geometry')
roads.enabled=false
T.check(not roads.onBuildingProgress(a,1),'disabled roads reject progressive imports')
roads.enabled=true;roads.clear()

-- Fast producers must not replace queued cheap coverage with a costly import.
P:clear();farVisible=false
local first=msg(0,{p0=part('queued-shell')});first.token='queue';first.total=2
P:receive(first,1)
local detailMsg=msg(2,{bld=part('queued-detail')});detailMsg.token='queue';detailMsg.total=2
P:receive(detailMsg,1)
local second=msg(0,{p0=part('second-shell')});second.token='queue';second.total=2;second.group='1'
P:receive(second,1);P:step(anchor)
T.check(shown('queued-shell') and not shown('queued-detail'),'cheap queued coverage survives later detail')
P:step(anchor)
T.check(shown('second-shell') and not shown('queued-detail'),'missing group covered before existing group refines')
P:step(anchor)
T.check(shown('queued-detail') and not shown('queued-shell'),'refinement resumes after coverage')
P:clear()

-- Price optional imports using shape bytes, stored primitives and measured cost.
-- Missing coverage remains a separate, strict priority and failures keep it.
local time=10
local made={}
local C=require('beamngEarth/buildingprogress').new({
  clock=function() return time end,
  create=function(w)
    time=time+.020;made[#made+1]=w.shape
    local o=createObject('TSStatic');o:setField('shapeName',0,w.shape);o:registerObject('');return o.id
  end,
  delete=function(id) local o=S.objects[id];if o then o:delete() end end,
  made=function() end,release=function() end,slot=function() end
})
local costly=msg(2,{bld=part('costly')});costly.total=2;costly.token='cost';costly.parts.bld.cost={bytes=8000000,vertices=90000,primitives=30}
local cheap=msg(0,{p0=part('cheap')});cheap.total=2;cheap.token='cost';cheap.group='1';cheap.parts.p0.cost={bytes=1000,vertices=64,primitives=1}
C:receive(costly,1);C:receive(cheap,1);C:step(anchor)
T.check(made[1]=='/test/cheap.cdae','equal-distance missing coverage uses measured work features')
local refine=msg(2,{bld=part('cheap-refine')});refine.total=2;refine.token='cost';refine.group='1'
C:receive(refine,1);C:step(anchor)
T.check(made[2]=='/test/costly.cdae','expensive missing coverage precedes optional refinement')
T.check(C.stats.imports==2 and C.stats.bytes==8001000 and C.stats.primitives==31,'bounded aggregate import features recorded')
T.check(C.msPerWork and math.abs(C.stats.worstMs-20)<.001,'actual synchronous import duration feeds future estimates')
local malformed=msg(2,{bld=part('bad-cost')});malformed.token='bad';malformed.parts.bld.cost=4
T.check(not C:receive(malformed,1),'invalid optional cost metadata rejected')
C:clear()

-- A completed group can receive an exact visual replacement while another
-- group is still incomplete. Later far/near visibility must target the new ID.
P:clear();farVisible=false
local original=createObject('TSStatic');original:registerObject('')
local replacement=createObject('TSStatic');replacement:registerObject('')
local partial={gkey=key,bld=original.id,parts={bld=part('one'),bld2=part('two')},slots={},exactShape={},
  data={buildingGroups={{group='one',visual={'bld'}},{group='two',visual={'bld2'}}}}}
P:attach(partial,{buildingProgressToken='partial-exact'})
original:setHidden(true);partial.bld=replacement.id
P:replaceInstance(partial,original.id,replacement.id)
farVisible=true;P:visibility(key)
T.check(replacement.hidden,'partial-group exact replacement follows far coverage visibility')
farVisible=false;P:visibility(key)
T.check(not replacement.hidden and original.hidden,'visibility follows replacement without reviving retired ID')
P:clear()
T.check(not replacement.hidden,'final owner retains current replacement on progress cleanup')

-- Stationary camera rotation changes priority; old off-screen work still wins
-- once its fairness deadline is reached.
C:clear();time=20
local forward=msg(0,{p0=part('forward')});forward.token='view';forward.total=2
local behind=msg(0,{p0=part('behind')});behind.token='view';behind.total=2;behind.group='1'
forward.parts.p0.center={30,0,0};behind.parts.p0.center={-30,0,0}
C:receive(behind,1);time=20.1;C:receive(forward,1)
local viewAnchor=geodesy.newAnchor(lat,lon)
local choice=C:prepare(viewAnchor,{x=0,y=0},{fx=1,fy=0})
T.check(choice.part.shape=='/test/forward.cdae','stationary camera facing prioritizes visible coverage')
choice=C:prepare(viewAnchor,{x=0,y=0},{fx=-1,fy=0})
T.check(choice.part.shape=='/test/behind.cdae','rotating camera reverses equal-distance preference')
time=26
choice=C:prepare(viewAnchor,{x=0,y=0},{fx=1,fy=0})
T.check(choice.part.shape=='/test/behind.cdae','aged off-screen coverage cannot starve')
C:clear()
T.done('test_building_progress')
