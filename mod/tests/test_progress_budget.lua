-- Scheduling/budget integration with deterministic elapsed wall time. Engine
-- contact, native import cost and deferred renderer time remain native gates.
local dir=(arg[0]:match('^(.*)[/\\]') or '.')
local T=dofile(dir..'/testlib.lua')
local S=dofile(dir..'/stubs.lua')
local time=0
function hptimer()
  local previous=time
  return {stopAndReset=function() local elapsed=time-previous;previous=time;return elapsed end}
end
local progress=require('beamngEarth/buildingprogress')
local governor=require('beamngEarth/governor')
local geodesy=require('beamngEarth/geodesy')
local geotile=require('beamngEarth/geotile')
local anchor=geodesy.newAnchor(0,0)
local x,y=geotile.tileOf(0,0)
local key=geotile.key(x,y)
local lat,lon=geotile.centre(17,x,y)
local made,released,claims={},{},{}
local failShape,blocked
local function newProgress()
  return progress.new({
    create=function(w)
      -- CPU time is deliberately unrelated to this timer.
      time=time+20
      if w.shape==failShape then error('native import fixture') end
      local o=createObject('TSStatic');o:setField('shapeName',0,w.shape);o:registerObject('')
      made[#made+1]=w.shape;return o.id
    end,
    made=function() end,
    delete=function(id) S.objects[id]:delete() end,
    slot=function(m,w) return m.slots and m.slots[w] end,
    release=function(s) if s then released[s]=(released[s] or 0)+1 end end,
    blocked=function() return blocked end,
  })
end
local function message(group,stage,count,token,cost)
  local parts,slots={},{}
  for i=1,count do
    local name=group..'-'..stage..'-'..i
    parts['p'..i]={shape=name,pos={0,0,0},cost=cost or {bytes=100,vertices=64,primitives=1}}
    slots['p'..i]=name..':'..(token or 'revision');claims[slots['p'..i]]=true
  end
  return {anchorId=1,key=key,token=token or 'revision',frame={lat,lon},total=1,
          group=group,stage=stage,parts=parts,slots=slots}
end
local function shown(name)
  for _,o in pairs(S.objects) do if o.fields.shapeName==name and not o.hidden then return true end end
  return false
end

-- Quoted work uses the real governor. Expensive units wait for accumulated
-- tokens instead of bypassing the budget or waiting forever at its old cap.
local P=newProgress()
P:receive(message('priced',0,1),1)
local quote=P:prepare(anchor)
T.check(quote and quote.ms>3,'bytes, vertices and primitives supplement the import estimate')
local G=governor.new({clock=function() return time end})
local frames=0
repeat
  frames=frames+1;time=time+16;G:beginFrame(true)
  quote=P:prepare(anchor)
  if G:try('roadWalk',quote.ms) then
    local start=time;T.check(P:step(anchor,nil,quote),'quoted candidate imports after governor grant')
    G:charge('roadWalk',time-start);break
  end
until frames>200
T.check(frames>1 and frames<=200,'priced unit waits and eventually runs')
T.near(P:diagnostics().importP50Ms,20,1e-8,'production wall timer measures native callback duration')
T.near(G.est.roadWalk,6.4,1e-8,'same shared governor learns measured wall cost')
T.check(P.msPerWork and P:diagnostics().queueP95Ms>0,'elapsed queue time and learned effort are reported')
local estimate=P.msPerWork
P:receive(message('priced',1,1),1)
quote=P:prepare(anchor)
T.check(quote.ms>15 and quote.ms<25,'next similarly sized chunk uses its measured import cost')
P:receive(message('priced',2,1),1)
local before=#made
T.check(not P:step(anchor,nil,quote) and #made==before,'superseded budget quote cannot import a different candidate')
T.check(P.msPerWork==estimate,'cancelled work does not train the import model')
P:clear()

-- A large hint must survive beginFrame's bucket cap. Existing engine debt,
-- heavy frames and the per-frame limit still constrain this same governor.
G=governor.new({clock=function() return time end})
frames=0
repeat
  time=time+16;frames=frames+1;G:beginFrame(true)
  if G:try('roadWalk',40) then break end
until frames>200
T.check(frames<=200 and G.tokens>=40,'a unit larger than the generic average can bank enough shared tokens')
G:chargeEngine(100)
T.check(not G:try('roadWalk',40),'engine debt also defers a priced unit')
G.blocked=true;G.tokens=100
T.check(not G:try('roadWalk',40),'heavy/quiet blocking cannot be bypassed by a price hint')
G.blocked=false;G:try('roadWalk',40)
G:beginFrame(true);G:beginFrame(true)
T.check(G:maxUnit()<40,'abandoned price hints expire without inflating future buckets')
for _,bad in ipairs({0,-1,0/0,math.huge,10001,'40'}) do
  G.predicted.roadWalk=nil
  G:try('roadWalk',bad)
  T.check(G.predicted.roadWalk==nil,'invalid price hints fall back to the ordinary estimate')
end
G=governor.new({clock=function() return time end})
frames=0
repeat
  time=time+16;frames=frames+1;G:beginFrame(true)
  if G:try('roadWalk',40) then break end
  G:try('roadWalk') -- an ordinary collider can be waiting without running
until frames>200
T.check(frames<=200 and G.tokens>=40,'ordinary work of the same kind does not erase a waiting priced unit')

-- Missing coverage is strict. Once it exists, waiting expensive work cannot
-- starve behind an endless stream of newly arriving cheap refinements.
P=newProgress();made={}
P:receive(message('expensive',0,1,nil,{bytes=8000000,vertices=20000,primitives=40}),1)
P:receive(message('cheap',0,1),1)
P:step(anchor)
T.check(made[1]=='cheap-0-1','new equal-distance coverage starts with the cheap chunk')
time=time+(progress.FAIR_WAIT_S+1)*1000
P:receive(message('new',0,1),1)
P:step(anchor)
T.check(made[2]=='expensive-0-1','old expensive missing coverage wins after bounded waiting')
P:receive(message('expensive',2,1),1)
P:step(anchor)
T.check(made[3]=='new-0-1','new missing coverage still precedes a late optional refinement')
P:clear()

-- Saturate 160 independent groups, let producers race ahead, partially import
-- a replacement and cancel it, inject a failed import, then drain the latest
-- complete stages. Every accepted slot must release once.
P=newProgress();made={};blocked=false
for i=1,160 do
  local name=string.format('group%03d',i)
  P:receive(message(name,0,1),1)
  P:receive(message(name,1,2),1)
  P:receive(message(name,2,2),1)
end
local d=P:diagnostics()
T.check(d.pendingGroups==160 and d.pendingParts==320 and d.queuePeak==320,'saturated queue keeps only the latest stage per group')
for _=1,160 do P:step(anchor) end
T.check(P:diagnostics().pendingParts==160,'import budget is spent directly on latest coverage')
local completed=0
for i=1,160 do
  local name=string.format('group%03d',i)
  T.check(not shown(name..'-0-1') and not shown(name..'-1-1'),'obsolete shells and facades never surface')
  if shown(name..'-2-1') and shown(name..'-2-2') then completed=completed+1 end
end
T.check(completed==80,'multi-part latest coverage is exposed only in complete groups')
P:step(anchor)
local pending=P:prepare(anchor)
T.check(pending and pending.version.next==2,'a multi-part replacement remains partially imported')
local partialGroup=pending.entry.groups
local ownerGroup
for gid,g in pairs(partialGroup) do if g==pending.group then ownerGroup=gid end end
P:receive(message(ownerGroup,0,1,'new-revision'),1)
T.check(not P:step(anchor,nil,pending),'a revision change invalidates an outstanding quote')
d=P:diagnostics()
T.check(d.wastedImports==1 and d.wastedBytes==100 and math.abs(d.wastedMs-20)<1e-8,'cancelled partial native work is measured exactly once')
T.check(d.pendingParts==1 and P.queuedParts==1,'revision replacement clears obsolete queue ownership')
P:step(anchor)
P:receive(message(ownerGroup,1,2,'new-revision'),1)
failShape=ownerGroup..'-1-2'
P:step(anchor);P:step(anchor)
T.check(shown(ownerGroup..'-0-1'),'failed multi-part update preserves last complete coverage')
d=P:diagnostics()
T.check(d.failures==1 and d.wastedImports==2,'failed replacement counts its hidden partial work')
T.check(d.pendingParts==0 and P.queuedParts==0,'failed replacement releases every remaining pending part')
P:clear();failShape=nil
for slot in pairs(claims) do T.check(released[slot]==1,'pooled slot releases once through supersession, cancellation and failure: '..slot) end

-- A group hidden by aggregate coverage is wasted if replaced before it ever
-- renders; previously visible coverage is useful even after normal retirement.
P=newProgress();blocked=true
P:receive(message('hidden',0,1,'hidden'),1);P:step(anchor)
T.check(P:diagnostics().visibleGroups==0,'hidden completed imports are not counted as visible coverage')
P:receive(message('hidden',1,1,'hidden'),1);P:step(anchor)
T.check(P:diagnostics().wastedImports==1,'never-exposed complete stage counts as wasted work')
blocked=false;time=time+1000;P:visibility(key)
d=P:diagnostics()
T.check(d.visibleGroups==1 and d.worstVisibleMs>=1000,'first real exposure records visible coverage latency')
P:clear()
T.check(P:diagnostics().wastedImports==1,'normal retirement does not count visible stages as wasted')

-- Diagnostics retain fixed storage even across many completed revisions.
P=newProgress()
for i=1,400 do
  P:receive(message('bounded',0,1,'revision'..i),1);P:step(anchor)
end
d=P:diagnostics()
T.check(d.sampleCount==progress.SAMPLE_KEEP and #P.samples==progress.SAMPLE_KEEP,'timing percentile storage remains bounded')
T.near(d.importP99Ms,20,1e-8,'recent import percentile uses elapsed wall-time samples')
T.near(d.queueP50Ms,0,1e-8,'recent queue percentile uses elapsed wall-time samples')
T.check(d.imports==400 and d.pendingParts==0,'aggregate totals survive bounded sample rollover')
P:clear()

-- The production roads path passes the quote to its existing governor and
-- shares its one-import frame cap with ordinary meshes.
package.loaded['beamngEarth/trees']={onGeoRows=function() end,dropKey=function() end}
local roads=require('beamngEarth/roads')
roads.setSession('priced-progress');roads.setGeo(true)
local seenPrice,granted=false,false
local fakeGov={
  try=function(_,kind,ms) if ms then seenPrice=ms end;return granted end,
  charge=function() end,chargeMotion=function() end,
}
roads.onBuildingProgress(message('real',0,2,'production'),1)
before=S.calls.createObject_TSStatic or 0
roads.update(fakeGov,1,nil,nil,anchor)
T.check(type(seenPrice)=='number' and seenPrice>3,'production scheduler submits a chunk quote to its governor')
T.check((S.calls.createObject_TSStatic or 0)==before,'production path respects denied priced grant')
granted=true
for i=1,2 do
  before=S.calls.createObject_TSStatic or 0
  roads.update(fakeGov,1,nil,nil,anchor)
  T.check((S.calls.createObject_TSStatic or 0)-before<=1,'production priced imports retain shared one-import cap')
end
T.check(roads.status().buildingProgress.pendingParts==0,'production diagnostics expose the drained priced queue')
roads.clear()
T.done('test_progress_budget')
