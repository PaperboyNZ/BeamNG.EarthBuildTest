-- Building imports stay staged even when the governor allows unlimited work.
local dir = (arg[0]:match('^(.*)[/\\]') or '.')
local T = dofile(dir .. '/testlib.lua')
local S = dofile(dir .. '/stubs.lua')
local roads = require('beamngEarth/roads')
local gov = {}
function gov:try() return true end
function gov:charge() end
function gov:chargeMotion() end
local data = { chunks = {}, buildingChunks = {v = 1, visual = {}, collision = {'bldcol'}} }
for i = 1, 6 do
  local what = i == 1 and 'bld' or 'bld' .. i
  data.buildingChunks.visual[i] = what
  data[what] = {shape = '/test/' .. what .. '.cdae', pos = {0, 0, 0}}
end
data.bldcol = {shape = '/test/bldcol.cdae', pos = {0, 0, 0}}
roads.RELOAD_EVERY_S = 0
T.check(roads.MAX_IMPORTS_PER_FRAME == 1, 'one shared import slot per frame by default')
T.check(roads.onTile({anchorId = 1, key = '0_0', data = data}, 1), 'dense building set queued')
T.check(roads.onFarTile({anchorId = 1, key = '1_0', data = {shape = '/test/far.cdae', pos = {256, 0, 0}}}, 1),
  'distant buildings queued alongside near buildings')
local beforePrewarm = S.calls.createObject_TSStatic or 0
roads.prewarm('/test/prewarm.cdae')
T.check((S.calls.createObject_TSStatic or 0) == beforePrewarm, 'material prewarm is queued, not imported in the message callback')
local imports, reloads = 0, 0
for frame = 1, 12 do
  local before = S.calls.createObject_TSStatic or 0
  local rebuilt = S.calls.reloadCollision or 0
  roads.update(gov, 1)
  local made = (S.calls.createObject_TSStatic or 0)-before
  local reload = (S.calls.reloadCollision or 0)-rebuilt
  T.check(made <= 1, 'at most one mesh imported in frame ' .. frame)
  T.check(made == 0 or reload == 0, 'collision never rebuilt in an import frame ' .. frame)
  imports, reloads = imports+made, reloads+reload
  if frame==4 then
    local farReady=false
    for _,o in pairs(S.objects) do if o.fields.shapeName=='/test/far.cdae' then farReady=true end end
    T.check(farReady,'far import receives a slot before the dense near queue drains')
  end
end
T.check(imports == 9, 'prewarm, six near visuals, collider and far mesh share the import slots')
T.check(reloads == 1, 'collision activates once in its own frame without starvation')
roads.onDrop({anchorId = 1, key = '0_0'})
roads.update(gov, 1)
T.check(roads.status().tiles == 0, 'staged building set unloads')
roads.clear();roads.RELOAD_EVERY_S=6
roads.onTile({anchorId=1,key='0_0',data=data},1)
roads.collisionRebuilt();roads.requestCollision(true)
local before=S.calls.createObject_TSStatic or 0
local rebuilt=S.calls.reloadCollision or 0
roads.update(gov,1)
T.check((S.calls.reloadCollision or 0)==rebuilt+1,'moved prop requests the next collision slot')
T.check((S.calls.createObject_TSStatic or 0)==before,'moved-prop collision rebuild reserves its own import-free frame')
T.done('test_building_staging')
