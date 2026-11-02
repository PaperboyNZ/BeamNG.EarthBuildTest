local dir=(arg[0]:match('^(.*)[/\\]') or '.')
local T=dofile(dir..'/testlib.lua')
local S=dofile(dir..'/stubs.lua')
local calls={}
local geoRows={}
for _,name in ipairs({'trees','nightlights','parking','gasstations','pumpjacks','ambience'}) do
  package.loaded['beamngEarth/'..name]=setmetatable({}, {__index=function(_,fn)
    if fn=='placeRows' or fn=='placeSpaces' then return nil end
    if name=='trees' and fn=='hasGeo' then return function(key) return geoRows[key]~=nil end end
    return function(...)
      if name=='trees' and fn=='onGeoRows' then geoRows[select(1,...)]=true end
      if name=='trees' and fn=='dropKey' then geoRows[select(1,...)]=nil end
      calls[#calls+1]={name,fn,...}
    end
  end})
end
package.loaded['beamngEarth/gasstations'].MATERIAL_FILES={}
local tick=0
local function clock() local at=tick;return function() tick=tick+.001;return tick-at end end
package.loaded['beamngEarth/stopwatch']={clock=clock,new=clock}
local roads=require('beamngEarth/roads')
local a=require('beamngEarth/geodesy').newAnchor(0,0)
local key='g17_65536_65536';local aid=1
local car={p=vec3(200,200,1),getPosition=function(self) return self.p end,getVelocity=function() return vec3() end}
getPlayerVehicle=function() return car end
roads.setGeo(true);roads.setSession('patches')
roads.RELOAD_EVERY_S=0;roads.RELOAD_DELETES_S=0;roads.URGENT_GAP_S=0
local gov={try=function(self,k) return not (self.pauseDeletes and k=='roadDelete') end,charge=function() end,chargeMotion=function() end}
local engine={live={},calls=0}
be.reloadCollision=function()
  engine.calls=engine.calls+1
  if engine.failNext then engine.failNext=false;error('rebuild failure') end
  local out={}
  for _,o in pairs(S.objects) do
    if o.class=='TSStatic' and o.fields.collisionType~='None' then out[o.fields.shapeName]=true end
  end
  engine.pending=out
end
local function frame()
  if engine.pending then engine.live=engine.pending;engine.pending=nil end
  local before=S.calls.createObject_TSStatic or 0
  roads.update(gov,aid,car.p,nil,a)
  T.check((S.calls.createObject_TSStatic or 0)-before<=1,'partial products share the single-import frame cap')
end
local function step(n) for i=1,n do frame() end end
local function path(n) return '/temp/beamngEarth/patches/slot_'..n..'.cdae' end
local function object(p) for _,o in pairs(S.objects) do if o.fields.shapeName==p then return o end end end
local function contains(rows,n) for _,r in ipairs(rows) do if r[1]==n then return true end end;return false end
local body={h='body',physicalHash='physical',frame={0,0},buildingChunks={v=1,visual={'bld','bld2'},collision={'bldcol'}},
  colliders={deck={{-10,-10,-2.2,10,10,2}},bldcol={{40,40,0,60,60,20}},railcol={{70,70,-1,80,80,2}}},
  props={groups={'lamp'},items={{0,0,0,3,0,1,6,0}}},park={{100,100,0,0}}}
local slots={}
for i,w in ipairs({'deck','bld','bld2','bldcol','rail','railcol'}) do body[w]={shape='/'..w..'.cdae',pos={0,0,0}};slots[w]={path(100+i),1} end
local function skin(n)
  return {key=key,anchorId=aid,slots={road={path(n+1),1},walk={path(n+2),1},walkcol={path(n+3),1}},
    data={contentHash='body',pivot={0,0,0},q=.03125,
      road={shape='/road.cdae',pos={0,0,0}},walk={shape='/walk.cdae',pos={0,0,0}},walkcol={shape='/walkcol.cdae',pos={0,0,0}},
      colliders={walk={{20,-10,-.2,30,10,1}},walkcol={{20,-10,-.2,30,10,1}}}}}
end
local function exact(parts,ns)
  local m={key=key,anchorId=aid,contentHash='body',parts=parts,slots={}}
  for w,n in pairs(ns or {}) do m.slots[w]={path(n),1} end
  return m
end
T.check(roads.onTile({key=key,anchorId=aid,h='body',data=body,slots=slots},aid,a),'body accepted')
roads.onSkin(skin(200),aid);step(16)
local stable={};for i=1,6 do stable[i]=object(path(100+i)) end
local owners=roads.status().resourceLifetime.owners
local function propCalls()
  local n=0;for _,r in ipairs(calls) do if r[2]=='onRows' or r[2]=='onGeoRows' or r[2]=='dropKey' then n=n+1 end end;return n
end
local props=propCalls()
car.p=vec3(0,0,.5) -- unchanged bridge support must not pin an unrelated sidewalk patch
local imports=S.calls.createObject_TSStatic or 0
T.check(roads.onSkin(skin(300),aid),'replacement skin accepted')
for i=1,8 do frame();T.check(engine.live[path(101)] and object(path(101))==stable[1],'skin patch retains unchanged bridge physics and identity') end
T.check(object(path(303)) and engine.live[path(303)] and not object(path(201)),'skin commits as a complete replacement')
T.check((S.calls.createObject_TSStatic or 0)-imports==3,'skin patch imports no unchanged content')
T.check(propCalls()==props and roads.status().resourceLifetime.owners==owners,'skin preserves props and balances metadata ownership')
-- A missing final collision mesh keeps every accepted skin part intact.
local oldRoad,oldWalk,oldCol=object(path(301)),object(path(302)),object(path(303))
local exists=FS.fileExists;FS.fileExists=function(_,p) return p~=path(403) end
roads.onSkin(skin(400),aid);step(9);FS.fileExists=exists
T.check(object(path(301))==oldRoad and object(path(302))==oldWalk and object(path(303))==oldCol and engine.live[path(303)],'failed skin retains the full accepted visual/collision set')
T.check(roads.status().resourceLifetime.owners==owners,'failed skin releases all temporary owners')
-- Occupied changed surfaces block transfer; failed rebuild restores only them.
car.p=vec3(25,0,.5);roads.onSkin(skin(450),aid);step(6)
T.check(object(path(453)).fields.collisionType=='None' and engine.live[path(303)],'actor on changed sidewalk pins its accepted support')
car.p=vec3(0,0,.5);engine.failNext=true;step(6)
T.check(object(path(303))==oldCol and oldCol.fields.collisionType=='Collision Mesh' and engine.live[path(303)],'skin rebuild failure restores old collision')
T.check(roads.status().resourceLifetime.owners==owners,'skin rebuild rollback has no reference leak')
-- Exact collision precision changes only the requested part.
imports=S.calls.createObject_TSStatic or 0
roads.onExact(exact({bldcol='/exact.cdae'},{bldcol=501}),aid);step(5)
T.check(object(path(501)) and engine.live[path(501)] and not engine.live[path(104)],'exact collision part commits')
T.check((S.calls.createObject_TSStatic or 0)-imports==1,'exact variant imports one changed part')
T.check(object(path(101))==stable[1] and object(path(102))==stable[2] and object(path(106))==stable[6],'exact variant retains unrelated structure identities')
T.check(roads.status().resourceLifetime.owners==owners+1,'base file stays owned for future return while exact file is active')
roads.takeSlotsGone('patches');roads.onExact(exact({bldcol=false}),aid);step(5)
local gone=roads.takeSlotsGone('patches')
T.check(engine.live[path(104)] and not object(path(501)) and contains(gone,501) and not contains(gone,104),'return to base retires only the exact file')
-- A visual-only exact variant retains lean collision dispatch and needs no rebuild.
local reloads=engine.calls
roads.onExact(exact({bld2='/visual-exact.cdae'},{bld2=601}),aid);step(4)
T.check(object(path(601)) and object(path(601)).fields.collisionType=='None' and object(path(601)).fields.dynamic=='false','partial visual inherits parent collision/LOD dispatch')
T.check(engine.calls==reloads and engine.live[path(104)],'render-only precision update leaves physics untouched')
-- Equal body content still carries independent per-anchor precision products.
roads.onTile({key=key,anchorId=aid,h='body',data=body,exact={bldcol='/another-exact.cdae'},slots={['x:bldcol']={path(701),1}}},aid,a)
step(7)
T.check(engine.live[path(701)] and object(path(103)) and not object(path(601)),'same-hash body applies exact collision and explicit visual base selections')
roads.onTile({key=key,anchorId=aid,h='body',data=body},aid,a);step(5)
T.check(engine.live[path(104)] and not object(path(701)),'same-hash body can return precision products to base')
-- Two exact messages merge per resource; cancelling one before activation does
-- not discard the other or reimport an already-accepted base.
local acceptedBase=object(path(104));imports=S.calls.createObject_TSStatic or 0
roads.onExact(exact({bldcol='/temporary.cdae'},{bldcol=801}),aid);frame()
roads.onExact(exact({railcol='/rail-exact.cdae'},{railcol=802}),aid)
roads.onExact(exact({bldcol=false}),aid);step(9)
T.check(object(path(104))==acceptedBase and engine.live[path(802)] and not object(path(801)),'coalescing preserves independent resource requests and cancels obsolete precision')
T.check((S.calls.createObject_TSStatic or 0)-imports==2,'cancellation avoids redundant base import')
T.check(roads.status().resourceLifetime.owners==owners+1 and propCalls()==props,'coalesced exact update balances owners without replacing props')
T.check(not roads.onExact(exact({bldcol=true}),aid),'invalid exact path rejected before mutation')
-- A newer skin arriving in the asynchronous request frame survives the first
-- commit and then transfers as another complete subset.
roads.onSkin(skin(1000),aid)
for i=1,8 do frame();if engine.pending and engine.pending[path(1003)] then break end end
T.check(engine.pending and engine.pending[path(1003)],'first skin collision request in flight')
roads.onSkin(skin(1100),aid)
for i=1,12 do
  frame()
  T.check(engine.live[path(303)] or engine.live[path(1003)] or engine.live[path(1103)],'queued skin updates never lose accepted collision coverage')
end
T.check(engine.live[path(1103)] and object(path(1103)) and not object(path(1003)),'newest skin survives in-flight handover')
T.check(roads.status().resourceLifetime.owners==owners+1,'in-flight updates do not leak owners')
-- Cleanup debt coalesces resource patches without new native generations.
roads.onSkin(skin(1200),aid);frame();frame();gov.pauseDeletes=true
imports=S.calls.createObject_TSStatic or 0
for i=1,20 do
  roads.onSkin(skin(1300+i*10),aid);frame()
  T.check(roads.status().resourceLifetime.owners<=owners+4,'patch backpressure retains only accepted and latest requested metadata')
end
T.check((S.calls.createObject_TSStatic or 0)==imports,'blocked patch cleanup admits no further native imports')
gov.pauseDeletes=false;step(10)
T.check(engine.live[path(1503)] and roads.status().resourceLifetime.owners==owners+1,'latest skin resumes after patch deletion debt drains')
T.check(object(path(101))==stable[1] and object(path(102))==stable[2] and propCalls()==props,'all partial updates preserve unchanged body and props')
-- Full-body retransmissions preserve identical staged precision work, and their
-- explicit base selection cancels both inert and already-submitted variants.
car.p=vec3(45,50,.5);acceptedBase=object(path(104))
roads.onExact(exact({bldcol='/duplicate-exact.cdae'},{bldcol=1601}),aid);step(3)
local staged=object(path(1601));imports=S.calls.createObject_TSStatic or 0
roads.onTile({key=key,anchorId=aid,h='body',data=body,
  exact={bldcol='/duplicate-exact.cdae',railcol='/rail-exact.cdae'},
  slots={['x:bldcol']={path(1601),1},['x:railcol']={path(802),1}}},aid,a);step(2)
T.check(object(path(1601))==staged and (S.calls.createObject_TSStatic or 0)==imports,'identical full-body precision selection preserves inert candidate')
local selectBase={key=key,anchorId=aid,h='body',data=body,exact={railcol='/rail-exact.cdae'},slots={['x:railcol']={path(802),1}}}
roads.onTile(selectBase,aid,a);step(5)
T.check(object(path(104))==acceptedBase and not object(path(1601)),'full-body base selection cancels an unaccepted variant without reimport')
car.p=vec3(0,0,.5)
roads.onExact(exact({bldcol='/inflight-variant.cdae'},{bldcol=1701}),aid)
for i=1,6 do frame();if engine.pending and engine.pending[path(1701)] then break end end
roads.onTile(selectBase,aid,a)
for i=1,9 do frame();T.check(engine.live[path(104)] or engine.live[path(1701)],'in-flight precision reversal retains collision coverage') end
T.check(engine.live[path(104)] and not object(path(1701)) and roads.status().resourceLifetime.owners==owners+1,'full-body base selection reverses an in-flight variant with balanced owners')
-- Cancel an inert subset at a real geographic rebase, then honor a complete
-- same-hash precision selection for the new anchor without rebuilding its body.
car.p=vec3(45,50,.5)
local originalBody=object(path(104))
roads.onExact(exact({bldcol='/cancel-at-rebase.cdae'},{bldcol=2001}),aid);step(4)
local b=require('beamngEarth/geodesy').newAnchor(0,.01)
local motion=a:worldTransformTo(b,0,0,0)
car.p=vec3(motion:apply(car.p.x,car.p.y,car.p.z))
roads.replace(b,2);a=b;aid=2;step(3)
T.check(not object(path(2001)) and object(path(104))==originalBody,'real rebase cancels inert subset without replacing accepted body')
T.check(roads.takeResync(),'cancelled subset requests fresh precision/skin products')
roads.onTile({key=key,anchorId=aid,h='body',data=body,exact={railcol='/new-anchor-rail.cdae'},slots={['x:railcol']={path(2102),1}}},aid,a)
step(5)
T.check(engine.live[path(2102)] and object(path(104))==originalBody,'same-hash resync replaces precision only for the selected new-anchor resource')
-- Occupancy of a retained skin uses its transformed original frame. A controlled
-- drop hold exempts the frozen active actor, then readiness observes the new skin.
car.p=vec3(motion:apply(25,0,.5))
local rebasedSkin=skin(2200)
local ox,oy,oz=motion:apply(0,0,0)
for _,w in ipairs({'road','walk','walkcol'}) do rebasedSkin.data[w].pos={ox,oy,oz} end
rebasedSkin.data.pivot={ox,oy,oz}
local wx,wy,wz=motion:apply(25,0,0)
rebasedSkin.data.colliders.walk={{wx-5,wy-10,wz-.2,wx+5,wy+10,wz+1}}
rebasedSkin.data.colliders.walkcol=rebasedSkin.data.colliders.walk
roads.onSkin(rebasedSkin,aid);step(6)
T.check(engine.live[path(1503)] and object(path(2203)).fields.collisionType=='None','rebased actor pins accepted skin in its transformed resource frame')
roads.setHold(true);step(5)
local near=roads.geoKeysNear;roads.geoKeysNear=function() return {key} end
T.check(engine.live[path(2203)] and roads.readyAround(aid,car.p.x,car.p.y,0),'controlled hold transfers rebased skin and observes collision readiness')
roads.geoKeysNear=near;roads.setHold(false)
-- A mixed subset must remain atomic when a newly requested exact mesh fails.
car.p=vec3(motion:apply(0,0,.5));props=propCalls()
oldRoad=object(path(2201));oldCol=object(path(2203))
roads.onSkin(skin(2300),aid);frame();frame()
exists=FS.fileExists;FS.fileExists=function(_,p) return p~=path(2401) end
roads.onExact(exact({bldcol='/bad-mixed.cdae'},{bldcol=2401}),aid);step(8);FS.fileExists=exists
T.check(object(path(2201))==oldRoad and object(path(2203))==oldCol and engine.live[path(2203)] and engine.live[path(104)],'failed mixed subset keeps every accepted surface and body resource')
T.check(roads.status().resourceLifetime.owners==owners+1 and propCalls()==props,'failed mixed subset releases all candidates while preserving props')
roads.onDrop({key=key,anchorId=aid})
imports=S.calls.createObject_TSStatic or 0
T.check(not roads.onSkin(skin(2600),aid) and not roads.onExact(exact({bldcol='/late.cdae'},{bldcol=2701}),aid),'late optional products cannot revive a retiring tile')
step(2)
T.check((S.calls.createObject_TSStatic or 0)==imports and roads.status().resourceLifetime.owners==owners+1,'occupied retirement rejects late imports without releasing accepted ownership')
roads.clear();step(3)
T.check(roads.status().resourceLifetime.owners==0 and #roads.heldSessions()==0,'patch teardown balances metadata, instances and source folders')
T.done('test_resource_patches')
