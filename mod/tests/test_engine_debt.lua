local dir=(arg[0]:match('^(.*)[/\\]') or '.')
local T=dofile(dir..'/testlib.lua')
local S=dofile(dir..'/stubs.lua')
local debt=require('beamngEarth/engine_debt').new()
debt:deleted(7)
for i=1,10 do T.check(#debt:step()==0,'deletion without rebuild cannot release file') end
debt:submitted()
T.check(debt:held(7),'rebuild request does not release asynchronously referenced file')
debt:deleted(7) -- another collider using the same file disappears AFTER request
T.check(#debt:step()==0 and debt:held(7),'late deletion needs a newer rebuild')
debt:submitted()
T.check(debt:step()[1]==7 and not debt:held(7),'next update releases settled debt')
debt:deleted(8);debt:clear()
T.check(not debt:held(8),'level teardown clears engine references')

local files={['/t.json']="{chunks={},walk={shape='/walk.cdae',pos={0,0,0}},walkcol={shape='/col.cdae',pos={0,0,0}}}"}
readFile=function(p) return files[p] end
jsonDecode=function(s) return assert(load('return '..s))() end
local roads=require('beamngEarth/roads')
roads.RELOAD_EVERY_S=1e12;roads.RELOAD_DELETES_S=1e12;roads.URGENT_GAP_S=1e12
roads.MAX_IMPORTS_PER_FRAME=math.huge
roads.setSession('debt')
local gov={try=function() return true end,charge=function() end,chargeMotion=function() end}
local function step() roads.update(gov,1) end
local function has(rows,n) for _,r in ipairs(rows) do if r[1]==n then return true end end;return false end
local function sessionHeld(name) for _,s in ipairs(roads.heldSessions()) do if s==name then return true end end;return false end
roads.onTile({anchorId=1,key='0_0',path='/t.json',n=0,slots={
  walk={'/p/slot_21.cdae',4},walkcol={'/p/slot_22.cdae',5}}},1)
step();roads.onDrop({anchorId=1,key='0_0'});step()
local gone=roads.takeSlotsGone('debt')
T.check(has(gone,21) and not has(gone,22),'render slot releases while collision slot remains pinned')
T.check(has(roads.slotsHeld('debt'),22),'reconnect includes deleted collider awaiting engine')
for i=1,5 do step() end
T.check(#roads.takeSlotsGone('debt')==0,'unreloaded debt survives arbitrary updates')
roads.collisionRebuilt()
T.check(#roads.takeSlotsGone('debt')==0,'external rebuild submission alone keeps slot held')
step()
gone=roads.takeSlotsGone('debt')
T.check(#gone==1 and gone[1][1]==22 and gone[1][2]==5,'external rebuild settles on next update with original serial')
T.check(not has(roads.slotsHeld('debt'),22),'settled physical slot no longer held')
step();T.check(#roads.takeSlotsGone('debt')==0,'release is reported once')
-- A restarted server can allocate the same numeric slot while old-session
-- objects are still resident. Their references and engine debt are independent.
roads.clear();step()
local function loadSession(sess,key,serial)
  roads.setSession(sess)
  local path='/temp/beamngEarth/'..sess..'/slot_22.cdae'
  roads.onTile({anchorId=1,key=key,n=0,data={chunks={},walkcol={shape='/collision.cdae',pos={0,0,0}}},
    slots={walkcol={path,serial}}},1)
  step();return path
end
local oldPath=loadSession('older','0_0',5)
local newPath=loadSession('newer','1_0',9)
roads.onDrop({anchorId=1,key='0_0'});step()
T.check(has(roads.slotsHeld('older'),22) and has(roads.slotsHeld('newer'),22),'same slot number held independently by two sessions')
T.check(sessionHeld('older') and sessionHeld('newer'),'both source session folders remain claimed during asynchronous retirement')
roads.collisionRebuilt();step()
gone=roads.takeSlotsGone('older')
T.check(#gone==1 and gone[1][1]==22 and gone[1][2]==5,'old-session debt retires without waiting for new-session object')
T.check(has(roads.slotsHeld('newer'),22),'retiring old session does not release newer session slot')
T.check(not sessionHeld('older') and sessionHeld('newer'),'source folder releases only after metadata, scene and engine references settle')
roads.onDrop({anchorId=1,key='1_0'});step();roads.collisionRebuilt();step()
gone=roads.takeSlotsGone('newer')
T.check(#gone==1 and gone[1][1]==22 and gone[1][2]==9,'new-session slot retains its own serial and retirement')
roads.clear();step()
loadSession('shared','0_0',11);loadSession('shared','1_0',11)
roads.onDrop({anchorId=1,key='0_0'});step();roads.collisionRebuilt();step()
T.check(#roads.takeSlotsGone('shared')==0,'one tile cannot retire a file another tile owns')
T.check(has(roads.slotsHeld('shared'),22),'shared owner reported after first consumer retires')
roads.COLLIDE_CHECK_S=0
local car={p=vec3(-10000,-10000,0),getPosition=function(self) return self.p end,getVelocity=function() return vec3() end}
getPlayerVehicle=function() return car end
for i=1,4 do step() end
roads.collisionRebuilt();step()
T.check(#roads.takeSlotsGone('shared')==0 and has(roads.slotsHeld('shared'),22),'metadata owner retains file while its last collider is outside active range')
T.check(sessionHeld('shared'),'parked collider retains its source folder without a scene object')
getPlayerVehicle=nil
for i=1,4 do step() end
local made=false
for _,o in pairs(S.objects) do if o.fields.shapeName=='/temp/beamngEarth/shared/slot_22.cdae' then made=true end end
T.check(made,'retained tile can recreate its collider from the same protected file')
roads.onDrop({anchorId=1,key='1_0'});step();roads.collisionRebuilt();step()
gone=roads.takeSlotsGone('shared')
T.check(#gone==1 and gone[1][1]==22 and gone[1][2]==11,'shared file releases exactly once after last owner, object and engine reference')
T.check(roads.status().resourceLifetime.owners==0,'all ownership tokens balanced')
T.check(not sessionHeld('shared'),'last settled owner releases its source folder')
-- Delayed messages can refer to an older folder after the current hello.
roads.setSession('current')
roads.onTile({anchorId=1,key='2_0',n=0,data={chunks={},walkcol={shape='/unused.cdae',pos={0,0,0}}},
  slots={walkcol={'/temp/beamngEarth/older-path/slot_22.cdae',31}}},1)
step()
T.check(has(roads.slotsHeld('older-path'),22) and not has(roads.slotsHeld('current'),22),'pooled ownership follows actual file session rather than current hello')
roads.onDrop({anchorId=1,key='2_0'});step();roads.collisionRebuilt();step()
gone=roads.takeSlotsGone('older-path')
T.check(#gone==1 and gone[1][2]==31,'delayed old-session instance and metadata retire together')
-- Unpooled files need folder protection even though no slotsHeld row exists.
roads.onTile({anchorId=1,key='3_0',n=0,data={chunks={},walkcol={shape='/temp/beamngEarth/unpooled/raw.cdae',pos={0,0,0}}}},1)
step()
T.check(sessionHeld('unpooled') and #roads.slotsHeld('unpooled')==0,'unpooled source folder claimed independently of slot allocation')
roads.onDrop({anchorId=1,key='3_0'});step()
T.check(sessionHeld('unpooled'),'unpooled folder survives last object deletion while physics retains it')
roads.collisionRebuilt()
T.check(sessionHeld('unpooled'),'unpooled folder survives collision request frame')
step();T.check(not sessionHeld('unpooled'),'unpooled folder releases after collision boundary')
T.done('test_engine_debt')
