local dir=(arg[0]:match('^(.*)[/\\]') or '.')
local T=dofile(dir..'/testlib.lua')
local S=dofile(dir..'/stubs.lua')
local occ=require('beamngEarth/occupancy')
local roads=require('beamngEarth/roads')
local geodesy=require('beamngEarth/geodesy')
local a=geodesy.newAnchor(0,0)
local key='g17_65536_65536'
local function veh(id,x,y,z,walker)
  return {id=id,p=vec3(x,y,z),getId=function(self) return self.id end,
    getPosition=function(self) return self.p end,getVelocity=function() return vec3() end,
    getJBeamFilename=function() return walker and 'unicycle' or 'pickup' end}
end
local active,other,parked,walker=veh(1,100,100,1),veh(2,100,100,1),veh(3,200,200,1),veh(4,0,0,1,true)
local vehicles={active,other,parked,walker}
be.getObjectCount=function() return #vehicles end
be.getObject=function(_,i) return vehicles[i+1] end
getPlayerVehicle=function() return active end
local snap=occ.snapshot()
T.check(#snap.positions==3 and not snap.unknown,'active deduplicated, other and parked actors included, inactive walker excluded')
vehicles[5]=veh(1,100,100,1)
T.check(#occ.snapshot().positions==3,'different native wrappers for the same actor ID are deduplicated')
T.check(#occ.snapshot(true).positions==2,'teleport hold excludes active actor ID through every wrapper')
vehicles[5]=nil
active=walker
T.check(#occ.snapshot().positions==4,'active walking actor participates in occupancy')
active=vehicles[1]
local onDeck={positions={{x=0,y=0,z=.5}},unknown=false}
local boxes={{-10,-10,-2.2,10,10,2}}
T.check(not occ.intersects(onDeck,boxes,'deck',nil,false,roads),'standing on surface permits late deck activation')
T.check(occ.intersects(onDeck,boxes,'deck',nil,true,roads),'standing on surface pins deck retirement')
local above={positions={{x=0,y=0,z=20}},unknown=false}
T.check(not occ.intersects(above,boxes,'deck',nil,true,roads),'vertically separated actor does not pin another level')
local inv={apply=function(_,x,y,z) return x-100,y-200,z-20 end}
T.check(occ.intersects({positions={{x=100,y=200,z=20.5}}},boxes,'deck',inv,true,roads),'occupancy transforms into resource frame')
local origCount=be.getObjectCount
be.getObjectCount=function() return occ.MAX_ACTORS+1 end
T.check(occ.snapshot().unknown,'actor overflow is diagnosed instead of silently truncated')
be.getObjectCount=origCount
local original=parked.p;parked.p={x=0/0,y=0,z=0}
T.check(occ.snapshot().unknown,'invalid actor position prevents unsafe retirement')
parked.p=original
T.check(occ.intersects({positions={},unknown=true},boxes,'deck',nil,true,roads),'unknown actor state retains physical resource')

roads.setGeo(true);roads.setSession('occupied')
roads.RELOAD_EVERY_S=0;roads.URGENT_GAP_S=0;roads.RELOAD_DELETES_S=0
local gov={try=function() return true end,charge=function() end,chargeMotion=function() end}
local function step(n,aid)
  for i=1,n do roads.update(gov,aid or 1,active.p,nil,a) end
end
local function object(shape)
  for _,o in pairs(S.objects) do if o.fields.shapeName==shape then return o end end
end
local function has(rows,n) for _,r in ipairs(rows) do if r[1]==n then return true end end;return false end
local function content(h,slot,aid)
  return {key=key,anchorId=aid or 1,h=h,slots={deck={'/p/slot_'..slot..'.cdae',1}},
    data={h=h,frame={0,0},physicalHash=h,deck={shape='/deck.cdae',pos={0,0,0}},colliders={deck=boxes}}}
end
local old=content('old',301)
T.check(roads.onTile(old,1,a),'initial physical route accepted')
step(5)
local accepted=object('/p/slot_301.cdae')
T.check(accepted~=nil,'initial deck loaded')
other.p=vec3(0,0,.5) -- active car is elsewhere; another actor uses the deck
roads.onDrop({key=key,anchorId=1});step(4)
T.check(object('/p/slot_301.cdae')==accepted,'nonactive occupied deck survives retirement request')
T.check(not has(roads.takeSlotsGone('occupied'),301),'occupied physical file remains held')
-- A revisit cancels retirement without replacing the accepted object.
roads.onTile({key=key,anchorId=1,h='old',data=old.data},1,a)
local next=content('new',401)
T.check(roads.onTile(next,1,a),'occupied revision retained as a bounded pending message')
step(4)
T.check(object('/p/slot_301.cdae')==accepted and object('/p/slot_401.cdae')
  and object('/p/slot_401.cdae').fields.collisionType=='None' and object('/p/slot_401.cdae').hidden,
  'replacement stages hidden and noncolliding while occupied accepted deck remains live')
T.check(roads.status().resourceLifetime.pendingPhysical==1,'pending physical revision has bounded diagnostic count')
local latest=content('newer',411)
roads.onTile(latest,1,a)
step(1)
T.check(has(roads.takeSlotsGone('occupied'),401),'superseded unused revision releases its pooled file')
roads.onTile(latest,1,a)
T.check(not has(roads.takeSlotsGone('occupied'),411),'identical pending retransmission does not release its own file')
local function skin(hash,slot,aid)
  return {key=key,anchorId=aid or 1,slots={walkcol={'/p/slot_'..slot..'.cdae',1}},
    data={contentHash=hash,pivot={0,0,0},walkcol={shape='/walkcol.cdae',pos={0,0,0}},colliders={walkcol=boxes}}}
end
T.check(roads.onSkin(skin('newer',412),1),'matching skin waits with occupied content revision')
T.check(not roads.onSkin(skin('old',501),1),'stale skin cannot mutate the occupied revision')
T.check(has(roads.takeSlotsGone('occupied'),501),'unused stale skin file released')
local exact={key=key,anchorId=1,contentHash='newer',parts={deck='/exact.cdae'},slots={deck={'/p/slot_413.cdae',1}}}
T.check(roads.onExact(exact,1),'matching exact variant waits with pending content')
step(4)
T.check(object('/p/slot_412.cdae') and object('/p/slot_412.cdae').fields.collisionType=='None'
  and object('/p/slot_413.cdae') and object('/p/slot_413.cdae').fields.collisionType=='None',
  'skin and exact variant stage without activating over occupied route')
local held=roads.slotsHeld('occupied')
T.check(has(held,301) and has(held,411) and has(held,412) and has(held,413),'reconnect retains accepted and bounded pending resources')
roads.replace(a,2)
step(2,2)
local gone=roads.takeSlotsGone('occupied')
T.check(has(gone,411) and has(gone,412) and has(gone,413) and not has(gone,301),'rebase cancels obsolete pending messages but keeps occupied route')
T.check(roads.takeResync() and not roads.takeResync(),'cancelled transaction requests one fresh existing-protocol road sync')
latest=content('newest',421,2);roads.onTile(latest,2,a)
roads.onSkin(skin('newest',422,2),2)
other.p=vec3(200,200,1)
step(16,2)
T.check(not object('/p/slot_301.cdae') and object('/p/slot_421.cdae') and object('/p/slot_422.cdae'),'latest route and its matching skin apply after every actor leaves')
T.check(has(roads.takeSlotsGone('occupied'),301),'retired file released after deletion and asynchronous collision rebuild')
-- A real origin change must retain the skin using its original coordinate frame.
roads.clear();step(2,2)
local skinOnly={key=key,anchorId=2,h='skin-only',data={h='skin-only',frame={0,0}}}
roads.onTile(skinOnly,2,a);roads.onSkin(skin('skin-only',451,2),2);step(6,2)
other.p=vec3(0,0,.5)
local b=geodesy.newAnchor(0,.01)
local motion=a:worldTransformTo(b,0,0,0)
for _,v in ipairs(vehicles) do v.p=vec3(motion:apply(v.p.x,v.p.y,v.p.z)) end
roads.replace(b,3);a=b
roads.onDrop({key=key,anchorId=3});step(4,3)
T.check(object('/p/slot_451.cdae')~=nil,'occupied skin survives a nonidentity geographic rebase')
other.p=vec3(motion:apply(200,200,1));step(6,3)
T.check(not object('/p/slot_451.cdae'),'rebased skin retires after actor leaves its transformed surface')
-- Legacy ghosts retain their resource inventory after creation queues disappear.
roads.clear();step(2,3);roads.setGeo(false)
active.p=vec3(100,100,1);other.p=vec3(100,100,1);parked.p=vec3(300,300,1)
local legacy={key='0_0',anchorId=3,n=0,data={chunks={},deck={shape='/legacy.cdae',pos={0,0,0}},colliders={deck=boxes}}}
roads.onTile(legacy,3,a);step(5,3)
local shift=geodesy.transformOf({1,0,0,0,1,0,0,0,1},{100,200,0})
roads.transform(shift,geodesy);other.p=vec3(100,200,.5)
roads.GHOST_MAX_S=-1;step(4,4)
T.check(object('/legacy.cdae')~=nil,'occupied legacy ghost survives timeout with transformed collision inventory')
other.p=vec3(500,500,1);step(6,4)
T.check(not object('/legacy.cdae'),'legacy ghost releases after transformed occupant leaves')
roads.clear();step(2,4);roads.setGeo(true)
active.p=vec3(100,100,1);other.p=vec3(200,200,1);a=geodesy.newAnchor(0,0)
-- Player teleport holds exempt only the frozen active actor from activation.
roads.clear();step(2,2)
other.p=vec3(0,0,-1);roads.setHold(true)
roads.onTile(content('held',431,2),2,a);step(4,2)
T.check(not object('/p/slot_431.cdae'),'another actor in slab still holds activation during active-player teleport hold')
other.p=vec3(200,200,1);step(8,2)
T.check(object('/p/slot_431.cdae')~=nil,'activation resumes when other actor clears')
roads.setHold(false);roads.clear();step(2,2)
T.done('test_occupied_resources')
