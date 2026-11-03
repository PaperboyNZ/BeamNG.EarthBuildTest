local dir=(arg[0]:match('^(.*)[/\\]') or '.')
local T=dofile(dir..'/testlib.lua')
local S=dofile(dir..'/stubs.lua')
local tick=0
local function clock() local at=tick;return function() tick=tick+.001;return tick-at end end
package.loaded['beamngEarth/stopwatch']={clock=clock,new=clock}
local roads=require('beamngEarth/roads')
local a=require('beamngEarth/geodesy').newAnchor(0,0)
local aid=1
local key='g17_65536_65536'
local car={p=vec3(200,200,1),getPosition=function(self) return self.p end,getVelocity=function() return vec3() end}
getPlayerVehicle=function() return car end
roads.setGeo(true);roads.setSession('handover')
roads.RELOAD_EVERY_S=0;roads.RELOAD_DELETES_S=0;roads.URGENT_GAP_S=0
local gov={try=function(self,kind) return not (self.pausedDelete and kind=='roadDelete') end,charge=function() end,chargeMotion=function() end}
-- Model the documented asynchronous boundary, not just reload call counts:
-- a request takes a snapshot, applied at the next test frame.
local engine={live={}}
local function snapshot()
  local out={}
  for _,o in pairs(S.objects) do
    if o.class=='TSStatic' and o.fields.collisionType~='None' then out[o.fields.shapeName]=true end
  end
  return out
end
be.reloadCollision=function()
  S.count('reloadCollision')
  if engine.failNext then engine.failNext=false;error('simulated rebuild failure') end
  engine.pending=snapshot()
end
local function frame()
  if engine.pending then engine.live=engine.pending;engine.pending=nil end
  local count=S.calls.createObject_TSStatic or 0
  roads.update(gov,aid,car.p,nil,a)
  T.check((S.calls.createObject_TSStatic or 0)-count<=1,'transaction respects shared single-import frame cap')
end
local function step(n) for i=1,n do frame() end end
local function object(path)
  for _,o in pairs(S.objects) do if o.fields.shapeName==path then return o end end
end
local function has(rows,n) for _,r in ipairs(rows) do if r[1]==n then return true end end;return false end
local function path(slot) return '/temp/beamngEarth/handover/slot_'..slot..'.cdae' end
local function content(h,start,offset)
  offset=offset or 0
  local d={h=h,physicalHash=h,frame={0,0},
    buildingChunks={v=1,visual={'bld','bld2'},collision={'bldcol'}},
    colliders={deck={{offset-10,-10,-2.2,offset+10,10,2}},bldcol={{40,40,0,60,60,20}}}}
  local slots={}
  for i,what in ipairs({'deck','bld','bld2','bldcol'}) do
    d[what]={shape='/'..h..'_'..what..'.cdae',pos={0,0,0}}
    slots[what]={path(start+i),1}
  end
  return {key=key,anchorId=aid,h=h,data=d,slots=slots},path(start+1)
end
local function skin(h,start)
  return {key=key,anchorId=aid,slots={road={path(start+1),1},walkcol={path(start+2),1}},
    data={contentHash=h,pivot={0,0,0},road={shape='/road.cdae',pos={0,0,0}},
      walkcol={shape='/walk.cdae',pos={0,0,0}},colliders={walkcol={{20,-10,-.2,30,10,1}}}}}
end
local initial,initialDeck=content('A',100)
T.check(roads.onTile(initial,1,a),'accepted initial content')
roads.onSkin(skin('A',110),1);step(12)
local accepted=object(initialDeck)
local acceptedVisual=object(path(102))
T.check(accepted and engine.live[initialDeck] and acceptedVisual and not acceptedVisual.hidden,'initial visual and physical route live')
local baseline=roads.status().resourceLifetime.owners
-- A permanent shape import failure must not retire any accepted product.
local bad,badDeck=content('bad',200)
local create=createObject
createObject=function(class)
  local o=create(class);local set=o.setField
  function o:setField(field,index,value)
    if field=='shapeName' and value==path(203) then error('simulated importer failure') end
    return set(self,field,index,value)
  end
  return o
end
roads.onTile(bad,1,a);roads.onSkin(skin('bad',210),1)
for i=1,14 do
  frame()
  T.check(engine.live[initialDeck] and object(initialDeck)==accepted,'failed candidate retains accepted collision and object identity')
  T.check(acceptedVisual and not acceptedVisual.hidden,'failed candidate retains accepted visuals')
end
createObject=create
T.check(not object(badDeck) and roads.status().resourceLifetime.transactions.failed==1,'failed staged objects discarded')
T.check(roads.status().resourceLifetime.owners==baseline,'failure releases all candidate metadata owners')
T.check(not has(roads.takeSlotsGone('handover'),101),'accepted file never released by failed candidate')
-- A missing file is caught before scene registration, independently of errors.
local missing=content('missing',220)
local exists=FS.fileExists
FS.fileExists=function(_,p) return p~=path(223) end
roads.onTile(missing,1,a);roads.onSkin(skin('missing',230),1);step(14)
FS.fileExists=exists
T.check(object(initialDeck)==accepted and engine.live[initialDeck],'missing file leaves accepted physics intact')
T.check(roads.status().resourceLifetime.owners==baseline,'missing-file rollback has no owner leak')
-- Fully imported candidates remain hidden/noncolliding until a matching skin.
local waiting,waitingDeck=content('waiting',300)
roads.onTile(waiting,1,a);step(8)
T.check(object(waitingDeck) and object(waitingDeck).hidden and object(waitingDeck).fields.collisionType=='None','all imported candidate parts remain inert')
T.check(object(initialDeck)==accepted and engine.live[initialDeck],'missing skin does not create an incomplete physical handover')
local otherKey='g17_65537_65536'
roads.onTile({key=otherKey,anchorId=1,h='priority-probe',data={h='priority-probe',frame={0,0},deck={shape='/probe.cdae',pos={0,0,0}}}},1,a)
local jobs={{key=roads.geoKey(key)..'#physical',what='deck'},{key=roads.geoKey(otherKey),what='deck'}}
T.check(roads.nextWalk(jobs)==2 and roads.urgentWalk(jobs)==2,'missing collision coverage outranks optional physical replacement imports')
roads.onDrop({key=otherKey,anchorId=1})
-- Superseding a prepared-but-inert revision is safe and does not grow a chain.
local rollback,rollbackDeck=content('rollback',400)
roads.onTile(rollback,1,a);roads.onSkin(skin('rollback',410),1)
car.p=vec3(0,0,.5);step(10)
T.check(not object(waitingDeck) and object(rollbackDeck),'superseded inert candidate is replaced within existing queues')
T.check(object(rollbackDeck).fields.collisionType=='None','occupied old route prevents activation')
car.p=vec3(200,200,1);engine.failNext=true
for i=1,8 do frame();T.check(engine.live[initialDeck],'rebuild failure preserves old engine collision snapshot') end
T.check(object(initialDeck)==accepted and accepted.fields.collisionType=='Visible Mesh Final','failed rebuild restores accepted collision fields')
T.check(not object(rollbackDeck) and roads.status().resourceLifetime.owners==baseline,'failed rebuild rolls back staged resources')
-- Partial field application must restore the old set before any rebuild.
local fieldBad,fieldDeck=content('field-failure',450)
car.p=vec3(0,0,.5)
roads.onTile(fieldBad,1,a);roads.onSkin(skin('field-failure',460),1);step(10)
local failObject=object(fieldDeck);local oldSetter=failObject.setField
local failOnce=true
function failObject:setField(field,index,value)
  if failOnce and field=='collisionType' and value~='None' then failOnce=false;error('field change failure') end
  return oldSetter(self,field,index,value)
end
car.p=vec3(200,200,1);step(8)
T.check(engine.live[initialDeck] and accepted.fields.collisionType=='Visible Mesh Final','partial collision-field failure restores accepted set')
T.check(not object(fieldDeck) and roads.status().resourceLifetime.owners==baseline,'partial field failure releases failed candidate')
-- Occupancy must inspect candidate geometry as well as the accepted geometry.
local next,nextDeck=content('E',500,100)
roads.onTile(next,1,a);roads.onSkin(skin('E',510),1)
car.p=vec3(100,0,.5);step(10)
T.check(object(nextDeck) and object(nextDeck).fields.collisionType=='None','actor in candidate footprint prevents swap even outside old footprint')
be:reloadCollision();roads.collisionRebuilt();frame()
T.check(engine.live[initialDeck] and not engine.live[nextDeck],'unrelated rebuild cannot activate a staged collider')
T.check(roads.status().resourceLifetime.pendingPhysical==1,'exactly one physical candidate retained')
-- Successful collision transfer occurs in one snapshot. Keep the old render
-- and file until that snapshot has reached the following frame.
car.p=vec3(200,200,1)
frame()
T.check(engine.pending and engine.pending[nextDeck] and not engine.pending[initialDeck],'single rebuild snapshot replaces entire collision set')
T.check(engine.live[initialDeck] and object(initialDeck)==accepted and not acceptedVisual.hidden,'old coverage retained in submission frame')
T.check(not has(roads.takeSlotsGone('handover'),101),'submission alone cannot recycle old file')
local nearKeys=roads.geoKeysNear;roads.geoKeysNear=function() return {key} end
T.check(not roads.readyAround(aid,0,0,0) and roads.hasWork(),'drop hold cannot treat an asynchronous collision swap as ready')
-- Rapid reversal while the atomic request is in flight: retain only the latest
-- desired content and matching skin, then perform a second complete transfer.
roads.onTile(initial,1,a);roads.onSkin(skin('A',110),1)
frame()
T.check(engine.live[nextDeck] and not engine.live[initialDeck],'physics applies new set on the next frame')
T.check(object(nextDeck) and not object(nextDeck).hidden,'new render exposed with ready collision')
T.check(roads.readyAround(aid,0,0,0),'acknowledged transaction is ready without an unrelated extra collision rebuild')
roads.geoKeysNear=nearKeys
T.check(not has(roads.takeSlotsGone('handover'),101),'queued reversal retains old source file ownership')
for i=1,18 do
  frame()
  T.check(engine.live[initialDeck] or engine.live[nextDeck],'rapid reversal never loses physical coverage')
  T.check(not (engine.live[initialDeck] and engine.live[nextDeck]),'replacement never leaves two active deck generations')
end
T.check(engine.live[initialDeck] and object(initialDeck) and not object(initialDeck).hidden,'latest requested revision restored after in-flight handover')
T.check(not object(nextDeck) and roads.status().resourceLifetime.owners==baseline,'completed reversal retains only current metadata owners')
T.check(roads.status().resourceLifetime.transactions.committed==2,'both physical transactions committed completely')
-- A rebase can arrive after the swap request and before its asynchronous frame.
local rebased,rebasedDeck=content('rebased',600)
car.p=vec3(0,0,.5);roads.onTile(rebased,1,a);roads.onSkin(skin('rebased',610),1);step(10)
car.p=vec3(200,200,1);frame()
local b=require('beamngEarth/geodesy').newAnchor(0,.01)
local motion=a:worldTransformTo(b,0,0,0)
car.p=vec3(motion:apply(car.p.x,car.p.y,car.p.z));roads.replace(b,2);a=b;aid=2
T.check(roads.takeResync(),'in-flight rebase requests a fresh tracker sync')
engine.failNext=true;frame()
T.check(engine.live[rebasedDeck] and object(rebasedDeck),'failed rebase rebuild never destroys already-active candidate')
step(5)
T.check(engine.live[rebasedDeck] and object(rebasedDeck) and not object(rebasedDeck).hidden,'in-flight transaction completes after rebase rebuild recovers')
T.check(roads.status().resourceLifetime.transactions.committed==3,'rebase commits exactly one physical generation')
-- A new server session cancels inert work and retains an occupied accepted tile.
local interrupted,interruptedDeck=content('interrupted',700)
local deckPosition=object(rebasedDeck):getPosition()
car.p=vec3(deckPosition.x,deckPosition.y,deckPosition.z+.5)
roads.onTile(interrupted,2,a);roads.onSkin(skin('interrupted',710),2);step(10)
T.check(object(interruptedDeck) and object(interruptedDeck).fields.collisionType=='None','session interruption starts with inert candidate')
roads.setSession('new-session');roads.newSession();roads.ORPHAN_MAX_S=-1;step(4)
T.check(not object(interruptedDeck) and object(rebasedDeck) and engine.live[rebasedDeck],'restart cancels staged candidate while occupied old route remains')
T.check(has(roads.slotsHeld('handover'),601),'reconnect reports occupied resources of older session')
roads.clear();step(3)
T.check(roads.status().resourceLifetime.owners==0 and #roads.slotsHeld('handover')==0,'explicit teardown releases all owners and settled engine debt')
-- Deletion backpressure must stop new native imports while coalescing metadata.
local base,baseDeck=content('debt-base',1000)
car.p=vec3(-900,200,1);roads.onTile(base,2,a);roads.onSkin(skin('debt-base',1010),2);step(12)
local pos=object(baseDeck):getPosition();car.p=vec3(pos.x,pos.y,pos.z+.5)
local spare,spareDeck=content('spare',1100)
roads.onTile(spare,2,a);roads.onSkin(skin('spare',1110),2);step(10)
T.check(object(spareDeck) and object(spareDeck).fields.collisionType=='None','inert generation ready before cleanup is saturated')
local beforeImports=S.calls.createObject_TSStatic or 0
gov.pausedDelete=true
local newestDeck,newestSlot
for i=1,30 do
  local offset=2000+i*10;local m,p=content('latest-'..i,offset)
  newestDeck=p;newestSlot=offset+1
  roads.onTile(m,2,a);roads.onSkin(skin('latest-'..i,offset+6),2);frame()
  T.check(engine.live[baseDeck],'saturated deletion preserves accepted physics')
  T.check(roads.status().resourceLifetime.owners<=2*baseline,'only accepted and latest pending metadata retain owners')
end
T.check((S.calls.createObject_TSStatic or 0)==beforeImports,'blocked cleanup admits no additional native generation')
local gone=roads.takeSlotsGone('handover')
T.check(not has(gone,newestSlot) and not has(gone,1101),'latest request and undeleted inert instance files remain protected')
T.check(roads.status().resourceLifetime.pendingPhysical==1,'saturation coalesces to one latest pending revision')
gov.pausedDelete=false;car.p=vec3(-900,200,1);step(22)
T.check(object(newestDeck) and engine.live[newestDeck] and not object(newestDeck).hidden,'latest pending generation resumes after cleanup debt drains')
T.check(roads.status().resourceLifetime.owners==baseline and roads.status().resourceLifetime.pendingPhysical==0,'resumed replacement leaves only accepted ownership')
roads.clear();step(3)
T.check(roads.status().resourceLifetime.owners==0,'saturation recovery has no reference leak')
-- Retirement intent survives a rebase during the asynchronous swap.
local retiring,retiringDeck=content('retire-base',3000)
roads.onTile(retiring,aid,a);roads.onSkin(skin('retire-base',3010),aid);step(12)
pos=object(retiringDeck):getPosition();car.p=vec3(pos.x,pos.y,pos.z+.5)
local retireNext,retireDeck=content('retire-next',3100)
roads.onTile(retireNext,aid,a);roads.onSkin(skin('retire-next',3110),aid);step(10)
car.p=vec3(pos.x+200,pos.y+200,pos.z+1);frame()
roads.onDrop({key=key,anchorId=aid})
local c=require('beamngEarth/geodesy').newAnchor(0,.02)
motion=a:worldTransformTo(c,0,0,0);car.p=vec3(motion:apply(car.p.x,car.p.y,car.p.z))
roads.replace(c,3);a=c;aid=3;step(8)
T.check(not object(retiringDeck) and not object(retireDeck) and roads.status().resourceLifetime.owners==0,'in-flight retirement remains effective after rebase')
-- A newer residency offer cancels retirement and supersedes an obsolete queued
-- revision without leaking its never-imported files.
local renewBase,renewBaseDeck=content('renew-base',4000)
roads.onTile(renewBase,aid,a);roads.onSkin(skin('renew-base',4010),aid);step(12)
pos=object(renewBaseDeck):getPosition();car.p=vec3(pos.x,pos.y,pos.z+.5)
local renewed,renewedDeck=content('renewed',4100)
roads.onTile(renewed,aid,a);roads.onSkin(skin('renewed',4110),aid);step(10)
car.p=vec3(pos.x+200,pos.y+200,pos.z+1);frame()
roads.onDrop({key=key,anchorId=aid})
local obsolete,obsoleteDeck=content('obsolete',4200)
roads.onTile(obsolete,aid,a);roads.onSkin(skin('obsolete',4210),aid)
roads.onTile(renewed,aid,a);step(12)
T.check(engine.live[renewedDeck] and object(renewedDeck) and not object(renewedDeck).hidden,'newest matching offer renews an in-flight residency')
T.check(not object(obsoleteDeck) and roads.status().resourceLifetime.owners==baseline,'renewed target cancels obsolete queued revision and its ownership')
roads.clear();step(3)
T.check(roads.status().resourceLifetime.owners==0 and #roads.heldSessions()==0,'final transaction teardown leaves neither file nor source-folder claims')
-- Global admission holds later sectors in metadata while two candidates share
-- the existing import governor. They resume after earlier retirement drains.
local sectors={}
for i=1,3 do
  local m,p=content('sector-old-'..i,5000+i*100)
  m.key='g17_'..(65536+i)..'_65536';sectors[i]={key=m.key,old=p}
  roads.onTile(m,aid,a)
end
step(20)
for i,row in ipairs(sectors) do
  local m,p=content('sector-new-'..i,6000+i*100);m.key=row.key;row.new=p
  roads.onTile(m,aid,a)
end
T.check(roads.status().resourceLifetime.activeTransactions==2 and roads.status().resourceLifetime.pendingPhysical==3,'global admission starts two sectors and retains a third pending descriptor')
for i=1,30 do
  frame()
  T.check(roads.status().resourceLifetime.activeTransactions<=2,'global physical staging cap retained through handovers')
end
for _,row in ipairs(sectors) do T.check(engine.live[row.new] and not engine.live[row.old],'every admitted sector eventually transfers complete physics') end
T.check(roads.status().resourceLifetime.pendingPhysical==0 and roads.status().resourceLifetime.owners==12,'global admission drains without retaining superseded owners')
roads.clear();step(3)
T.check(roads.status().resourceLifetime.owners==0 and #roads.heldSessions()==0,'global admission teardown balances all owners and source folders')
-- Controlled teleport holds own the frozen active car's placement. They may
-- transfer its support, but must not exempt another live actor from clearance.
local heldBase,heldBaseDeck=content('hold-base',7000)
roads.onTile(heldBase,aid,a);roads.onSkin(skin('hold-base',7010),aid);step(12)
pos=object(heldBaseDeck):getPosition();car.p=vec3(pos.x,pos.y,pos.z+.5)
local companion={p=vec3(car.p.x,car.p.y,car.p.z),getId=function() return 2 end,getPosition=function(self) return self.p end}
be.getObjectCount=function() return 2 end
be.getObject=function(_,i) return i==0 and car or companion end
roads.setHold(true)
local heldNext,heldNextDeck=content('hold-next',7100)
roads.onTile(heldNext,aid,a);roads.onSkin(skin('hold-next',7110),aid);step(10)
T.check(engine.live[heldBaseDeck] and object(heldNextDeck).fields.collisionType=='None','teleport hold continues to protect another actor on accepted support')
companion.p=vec3(pos.x+200,pos.y+200,pos.z+1);step(5)
T.check(engine.live[heldNextDeck] and object(heldNextDeck) and not object(heldNextDeck).hidden,'frozen active player does not deadlock controlled physical handover')
nearKeys=roads.geoKeysNear;roads.geoKeysNear=function() return {key} end
T.check(roads.readyAround(aid,car.p.x,car.p.y,0),'controlled hold can observe acknowledged replacement readiness')
roads.geoKeysNear=nearKeys
roads.onDrop({key=key,anchorId=aid});step(3)
T.check(object(heldNextDeck)~=nil,'ordinary retirement still pins held active actor support')
roads.setHold(false);car.p=vec3(pos.x+200,pos.y+200,pos.z+1);step(6)
T.check(not object(heldNextDeck),'ordinary retirement resumes after actual actor departure')
be.getObjectCount=nil;be.getObject=nil
roads.clear();step(3)
T.check(roads.status().resourceLifetime.owners==0 and #roads.heldSessions()==0,'hold transfer releases all references after departure')
T.done('test_physical_handover')
