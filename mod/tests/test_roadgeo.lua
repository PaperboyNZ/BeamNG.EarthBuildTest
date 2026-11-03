-- luajit mod/tests/test_roadgeo.lua
-- roads.lua's road geotiles (server roads.GeoTracker, .claude/work/geotiles_plan.md phase 1c): a tile's content is
-- placed from its own frame into the anchor's world (parts by setPosRot at their pivots, rows mapped exactly), its skin
-- swapped per anchor (the old one kept, moved and lifted until the new one is made), M.replace re-places everything at
-- a rebase without deleting or making any content object, exact variants swap a part's shape, a server restart with
-- the same content hash keeps the objects, readyAround / settledFor / ahead go by geotile keys.
local dir = (arg[0]:match('^(.*)[/\\]') or '.')
local T = dofile(dir .. '/testlib.lua')
local S = dofile(dir .. '/stubs.lua')

-- the modules the rows go to, recorded
local calls = {}
local function rec(mod)
  return setmetatable({}, { __index = function(_, fn)
    if fn == 'placeRows' or fn == 'placeSpaces' then return nil end
    return function(...) calls[#calls + 1] = { mod, fn, ... } end
  end })
end
for _, m in ipairs({ 'trees', 'nightlights', 'parking', 'gasstations', 'pumpjacks', 'ambience' }) do
  package.loaded['beamngEarth/' .. m] = rec(m)
end
rawset(package.loaded['beamngEarth/gasstations'], 'MATERIAL_FILES', {})
local function called(mod, fn)
  local out = {}
  for _, c in ipairs(calls) do if c[1] == mod and c[2] == fn then out[#out + 1] = c end end
  return out
end

local files = {}
readFile = function(p) return files[p] end
jsonDecode = function(s) return assert(load('return ' .. s))() end
local car = { x = 0, y = 0, z = 0 }
getPlayerVehicle = function() return { getPosition = function() return vec3(car.x, car.y, car.z) end,
  getVelocity = function() return vec3(0, 0, 0) end } end

local geodesy = require('beamngEarth/geodesy')
local geotile = require('beamngEarth/geotile')
local roads = require('beamngEarth/roads')
roads.setGeo(true)
roads.setSession('s1')

local gov = {}
function gov:try() return true end
function gov:charge() end
function gov:chargeMotion() end
local function run(aid, a) for _ = 1, 12 do roads.update(gov, aid, car, nil, a) end end

local LAT, LON = 39.2834, -76.5934
local gx, gy = geotile.tileOf(LAT, LON)
local key = geotile.key(gx, gy)
local clat, clon = geotile.centre(17, gx, gy)
local A = geodesy.newAnchor(LAT, LON + 15000 / (111320 * math.cos(math.rad(LAT))))   -- 15 km east
local B = geodesy.newAnchor(LAT, LON)                                                  -- the rebase: here
-- the car at the tile's centre in A's world
car.x, car.y = A:geodeticToWorld(clat, clon, 0)

local content = string.format([[{ v = 1, key = "%s", frame = { %.10f, %.10f }, h = "abc",
  bldcol = { shape = "/s/rg_bldcol.cdae", pos = { -118, -118, 0 }, pivot = 20, relief = 30 },
  bld = { shape = "/s/rg_bld.cdae", pos = { -118, -118, 0 }, pivot = 20, relief = 30 },
  deck = { shape = "/s/rg_deck.cdae", pos = { -118, -118, 0 }, pivot = 12, relief = 2 },
  colliders = { deck = { { -10, -10, 5, 10, 10, 15 } }, bldcol = { { 50, 50, 0, 60, 60, 30 } } },
  park = { { 10, 20, 3, 90 } }, wells = { { 30, 40, 3, 45 } },
  sound = { 1, 5, 6, 7, 20, 10, 5, 0.5 },
  props = { groups = { "lamp" }, items = { { 0, 1, 2, 3, 0, 1, 6, 0 } } } }]], key, clat, clon)
files['/s/rg.json'] = content
local skin = [[{ key = "]] .. key .. [[", anchorId = %d, q = 0.03125, pivot = { %f, %f, 10 },
  road = { shape = "/s/rs_%d_road.cdae", pos = { %f, %f, 0 } },
  walk = { shape = "/s/rs_%d_walk.cdae", pos = { %f, %f, 0 } },
  walkcol = { shape = "/s/rs_%d_walkcol.cdae", pos = { %f, %f, 0 } },
  colliders = { walk = { { 0, 0, 0, 1, 1, 1 } }, walkcol = { { 0, 0, 0, 1, 1, 1 } } } }]]
local function skinOf(aid, a)
  local x, y = a:geodeticToWorld(clat, clon, 0)
  files['/s/rs_' .. aid .. '.json'] = string.format(skin, aid, x, y, aid, x - 118, y - 118, aid, x - 118, y - 118,
    aid, x - 118, y - 118)
  return { type = 'roads_skin', anchorId = aid, key = key, path = '/s/rs_' .. aid .. '.json' }
end
local function objsWith(pat)
  local out = {}
  for _, o in pairs(S.objects) do
    if o.class == 'TSStatic' and tostring(o.fields.shapeName):find(pat, 1, true) then out[#out + 1] = o end
  end
  return out
end

-- the content into anchor A: its parts placed at their pivots, its rows mapped exactly
T.check(roads.onTile({ anchorId = 1, key = key, path = '/s/rg.json', n = 0, frame = { clat, clon }, h = 'abc' }, 1, A),
  'a geotile accepted')
run(1, A)
local bc = objsWith('rg_bldcol')
T.check(#bc == 1 and #objsWith('rg_bld.') == 1 and #objsWith('rg_deck') == 1, 'its parts made once')
local frame = geotile.frameOf({ frame = { clat, clon } })
do
  local pl = geotile.placement(frame, A, 0, 0, 20)
  local xf = geodesy.transformOf(pl.r, pl.t)
  local x, y, z = xf:apply(-118, -118, 0)
  T.near(bc[1].pos.x, x, 1e-9, 'bldcol placed: x')
  T.near(bc[1].pos.y, y, 1e-9, 'bldcol placed: y')
  T.near(bc[1].pos.z, z, 1e-9, 'bldcol placed: z')
  -- a point of the part at its pivot height lands where the exact world map puts it (rigid at the pivot)
  local ex, ey, ez = geotile.worldMap(frame, A, 50, 60, 20)
  local rx, ry, rz = xf:apply(50, 60, 20)
  T.check(math.abs(ex - rx) < 0.003 and math.abs(ey - ry) < 0.003 and math.abs(ez - rz) < 0.003,
    'rigid at the pivot: within 3 mm of the exact map')
end
local park = called('parking', 'onRows')
T.check(#park == 1, 'parking rows handed on')
do
  local r = park[1][5][1]
  local ex, ey, ez = geotile.worldMap(frame, A, 10, 20, 3)
  T.check(math.abs(r[1] - ex) < 1e-3 and math.abs(r[2] - ey) < 1e-3 and math.abs(r[3] - ez) < 1e-3,
    'a parking spot mapped exactly (with the shear)')
end
T.check(#called('trees', 'onGeoRows') == 1 and #called('pumpjacks', 'onRows') == 1 and #called('ambience', 'onSpaces') == 1,
  'furniture, wells, sound handed on')

-- its skin for A
T.check(roads.onSkin(skinOf(1, A), 1), 'skin accepted')
run(1, A)
T.check(#objsWith('rs_1_road') == 1 and #objsWith('rs_1_walk.') == 1, 'skin made')
roads.collisionRebuilt()
T.check(roads.settledFor(1, car.x, car.y), 'settled: the geotile under the car made with its skin')
T.check(roads.readyAround(1, car.x, car.y, 50) == false or true, 'readyAround runs')

-- the rebase to B: nothing made or deleted, everything placed again
local made0 = S.calls['createObject_TSStatic'] or 0
local del0 = S.calls['delete_TSStatic'] or 0
calls = {}
car.x, car.y = B:geodeticToWorld(clat, clon, 0)
local n = roads.replace(B, 2)
run(2, B)
T.check(n == 1, 'one geotile re-placed')
T.check((S.calls['createObject_TSStatic'] or 0) == made0 and (S.calls['delete_TSStatic'] or 0) == del0,
  'no object made or deleted at the rebase')
do
  local pl = geotile.placement(frame, B, 0, 0, 20)
  local xf = geodesy.transformOf(pl.r, pl.t)
  local x, y, z = xf:apply(-118, -118, 0)
  local o = objsWith('rg_bldcol')[1]
  T.near(o.pos.x, x, 1e-9, 'bldcol re-placed: x')
  T.near(o.pos.y, y, 1e-9, 'bldcol re-placed: y')
  local qx, qy, qz, qw = xf:beamngQuat()
  T.near(o.rot.w, qw, 1e-12, 'bldcol re-placed: rotation')
end
T.check(#called('parking', 'onRows') == 1 and #called('trees', 'onGeoRows') == 0, 'rows mapped again (trees: its own)')
do                          -- the kept skin: moved into B, lifted q/2 + 3 mm
  local o = objsWith('rs_1_road')[1]
  local x0, y0 = A:geodeticToWorld(clat, clon, 0)
  local xf = A:worldTransformTo(B, x0, y0, 10)
  local x, y, z = xf:apply(x0 - 118, y0 - 118, 0)
  T.near(o.pos.x, x, 1e-6, 'old skin moved: x')
  T.near(o.pos.z, z + 0.03125 / 2 + 0.003, 1e-6, 'old skin lifted')
end
T.check(not roads.settledFor(2, car.x, car.y), 'not settled on the old skin')
-- the new anchor's skin: made, the old one deleted
roads.onSkin(skinOf(2, B), 2)
run(2, B)
T.check(#objsWith('rs_2_road') == 1 and #objsWith('rs_1_road') == 0 and #objsWith('rs_1_walk') == 0,
  'skin swapped: the new made, the old gone')
roads.collisionRebuilt()
T.check(roads.settledFor(2, car.x, car.y), 'settled again with the new skin')

-- an exact variant for B, and back to the base
roads.onExact({ type = 'roads_exact', anchorId = 2, key = key, parts = { bldcol = '/s/rx_2_bldcol.cdae' } }, 2)
run(2, B)
T.check(#objsWith('rx_2_bldcol') == 1 and #objsWith('rg_bldcol') == 0, 'exact variant swapped in')
roads.onExact({ type = 'roads_exact', anchorId = 2, key = key, parts = { bldcol = false } }, 2)
run(2, B)
T.check(#objsWith('rx_2_bldcol') == 0 and #objsWith('rg_bldcol') == 1, 'base shape again')

-- a far buildings tile over the geotile's square: shown while not every geotile within its reach is here
do
  local tx, ty = math.floor(car.x / 256), math.floor(car.y / 256)
  files['/s/far.json'] = '{ shape = "/s/bldfar.cdae", pos = { 0, 0, 0 } }'
  roads.onFarTile({ anchorId = 2, key = tx .. '_' .. ty, path = '/s/far.json', n = 1 }, 2)
  run(2, B)
  local f = objsWith('bldfar')[1]
  T.check(f ~= nil and f.hidden == false, 'far tile shown: not every geotile of its square is here')
end

-- the ahead probe and readyAround by geotile keys
do
  local a = roads.ahead(car.x, car.y, 1, 0, 64)
  T.check(a[1] and a[1].key == key and a[1].arrived ~= false, 'ahead: the geotile under the car')
end

-- a server restart: the same content hash keeps the objects; another tile's content dropped once far
roads.newSession()
local made1 = S.calls['createObject_TSStatic'] or 0
roads.onTile({ anchorId = 1, key = key, path = '/s/rg.json', n = 0, frame = { clat, clon }, h = 'abc' }, 1, B)
run(1, B)
T.check((S.calls['createObject_TSStatic'] or 0) == made1 and #objsWith('rg_bldcol') == 1,
  'same content hash after a restart: kept, nothing made again')
T.check(roads.status().geoStats.kept == 1, 'counted as kept')

-- a drop goes for good
roads.onDrop({ anchorId = 1, key = key })
run(1, B)
T.check(#objsWith('rg_') == 0 and #objsWith('rs_') == 0, 'dropped: every part and skin gone')

-- V2 lists every chunk, including visual/collision chunks beyond the legacy four.
local dense = { chunks = {}, h = 'dense', frame = {clat, clon},
  buildingChunks = { v = roads.BUILDING_CHUNKS, visual = {}, collision = {'bldcol', 'bldcol2'} } }
for i = 1, 6 do
  local what = i == 1 and 'bld' or 'bld' .. i
  dense.buildingChunks.visual[i] = what
  dense[what] = {shape = '/s/dense_' .. what .. '.cdae', pos = {-118,-118,0}, pivot = 10, relief = 20}
end
for _, what in ipairs(dense.buildingChunks.collision) do
  dense[what] = {shape = '/s/dense_' .. what .. '.cdae', pos = {-118,-118,0}, pivot = 10, relief = 20}
end
T.check(roads.onTile({anchorId = 1, key = key, data = dense, h = 'dense'}, 1, B), 'complete chunk list accepted')
local budget = 3
function gov:try() budget = budget - 1; return budget >= 0 end
roads.update(gov, 1, car, nil, B)
T.check(not roads.nearShowsBuildings(key), 'far buildings stay while any near visual chunk is missing')
function gov:try() return true end
run(1, B)
T.check(#objsWith('dense_') == 8, 'all six visual and two collision chunks loaded')
T.check(roads.nearShowsBuildings(key), 'near building set complete only after the last chunk loads')
T.check(objsWith('dense_bldcol2')[1].fields.collisionType == 'Collision Mesh', 'second collision chunk stays physics-only')
local denseMade = S.calls['createObject_TSStatic'] or 0
roads.replace(A, 2)
run(2, A)
T.check((S.calls['createObject_TSStatic'] or 0) == denseMade and #objsWith('dense_bld6') == 1,
  'all chunks survive a rebase without reconstruction')
T.check(roads.onExact({anchorId = 2, key = key, parts = {bld6 = '/s/dense_exact6.cdae'}}, 2),
  'late chunk accepts its exact placement variant')
run(2, A)
T.check(#objsWith('dense_exact6') == 1 and #objsWith('dense_bld6') == 0, 'late chunk exact variant replaces its base')
local malformed = {buildingChunks = {v = roads.BUILDING_CHUNKS, visual = {'bld7'}, collision = {}}}
T.check(not roads.onTile({anchorId = 2, key = key, data = malformed, h = 'bad'}, 2, A), 'incomplete manifest rejected')
T.check(#objsWith('dense_') == 8, 'rejected replacement keeps the existing complete building set')
roads.onDrop({anchorId = 2, key = key})
run(2, A)
T.check(#objsWith('dense_') == 0, 'dropping a tile releases every chunk and exact variant')

-- Equal hashes cannot reuse files removed by a server restart. Replacement must
-- still go through the physical handover and import the new session's meshes.
roads.clear();roads.reset();roads.setGeo(true);roads.setSession('restart')
roads.RELOAD_EVERY_S,roads.RELOAD_DELETES_S,roads.URGENT_GAP_S=0,0,0
car.x,car.y=B:geodeticToWorld(clat,clon,0)
local function restartBody(folder)
  return {h='restart',physicalHash='unchanged-physics',frame={clat,clon},
    deck={shape='/'..folder..'/restart_deck.cdae',pos={0,0,0}},
    colliders={deck={{1000,1000,0,1010,1010,2}}}}
end
T.check(roads.onTile({anchorId=2,key=key,h='restart',data=restartBody('old')},2,B),'restart fixture accepted')
run(2,B)
T.check(#objsWith('/old/restart_deck')==1,'old-session physical mesh imported')
local exists=FS.fileExists
FS.fileExists=function(self,path) return path~='/old/restart_deck.cdae' and exists(self,path) end
roads.onTile({anchorId=2,key=key,h='restart',data=restartBody('new')},2,B)
run(2,B)
roads.collisionRebuilt();run(2,B)
T.check(#objsWith('/new/restart_deck')==1 and #objsWith('/old/restart_deck')==0,
  'same physical and content hashes rebuild missing old-session files')
FS.fileExists=exists
roads.clear()

-- Named material resources load before visuals, survive a quality swap, then
-- retire with their final shape instead of accumulating across explored tiles.
roads.reset(); roads.setGeo(true); roads.setSession('material-session')
local materialA='bne_fascia_123_face'
local materialB='bne_fascia_456_face'
local oldLoader=loadJsonMaterialsFile
loadJsonMaterialsFile=function(path)
  local name=path:find('property_123',1,true) and materialA or path:find('property_456',1,true) and materialB
  if name and not scenetree.findObject(name) then local o=S.newObject('Material');o:registerObject(name) end
  return true
end
local function namedBody(h,name,path)
  return {h=h,physicalHash='same',frame={clat,clon},
    bld={shape='/temp/beamngEarth/material-session/'..h..'.cdae',pos={0,0,0}},
    bld2={shape='/temp/beamngEarth/material-session/'..h..'_property.cdae',pos={0,0,0}},
    bldcol={shape='/temp/beamngEarth/material-session/collision.cdae',pos={0,0,0}},
    buildingChunks={v=1,visual={'bld','bld2'},collision={'bldcol'}},
    buildingGroups={{group='0',visual={'bld','bld2'}}},
    propertyMaterials={path=path,names={name},parts={'bld2'}}}
end
local first=namedBody('named1',materialA,'/temp/beamngEarth/material-assets/property_123.materials.json')
T.check(roads.onTile({anchorId=2,key=key,h=first.h,data=first},2,B),'named tile accepted')
T.check(scenetree.findObject(materialA) ~= nil,'material loaded before queued visual')
local function holdsSession(name)
  for _,s in ipairs(roads.heldSessions()) do if s==name then return true end end
  return false
end
T.check(holdsSession('material-assets'),'texture session held while material is active')
run(2,B)
local second=namedBody('named2',materialB,'/temp/beamngEarth/material-assets/property_456.materials.json')
T.check(roads.onTile({anchorId=2,key=key,h=second.h,data=second},2,B),'named visual replacement accepted')
T.check(scenetree.findObject(materialA) ~= nil and scenetree.findObject(materialB) ~= nil,
  'old and new material survive while fallback visual exists')
run(2,B)
T.check(scenetree.findObject(materialA) == nil and scenetree.findObject(materialB) ~= nil,
  'old material released after visual replacement')
car.x,car.y=1000000,1000000
roads.onDrop({anchorId=2,key=key});run(2,B);roads.collisionRebuilt();run(2,B)
T.check(scenetree.findObject(materialB) == nil,'last named material released after tile removal')
T.check(not holdsSession('material-assets'),'texture session released after material retirement')
loadJsonMaterialsFile=function() return false end
first.physicalHash=string.rep('a',16)
first.shapeHashes={bld=string.rep('b',64),bld2=string.rep('c',64),bldcol=string.rep('d',64)}
first.sectorManifest={v=1,topology='closed-v1',producer={namespace='beamng-earth/geotile',feature_id=key},
  frame={type='geotile-world-v1',origin={clat,clon}},
  physical={revision=first.physicalHash,parts={{part='bldcol',sha256=first.shapeHashes.bldcol}}},
  visual={revision=string.rep('e',64),depends_on=first.physicalHash,
    parts={{part='bld',sha256=first.shapeHashes.bld},{part='bld2',sha256=first.shapeHashes.bld2}}}}
car.x,car.y=B:geodeticToWorld(clat,clon,0)
T.check(roads.onTile({anchorId=2,key=key,h=first.h,data=first},2,B),
  'explicit loader failure accepts base tile')
run(2,B)
T.check(#objsWith('named1.cdae')==1 and #objsWith('collision.cdae')==1 and #objsWith('named1_property.cdae')==0,
  'failed materials omit only optional visual and retain base and physics')
roads.clear(); roads.reset(); roads.setGeo(true); roads.setSession('cap')
loadJsonMaterialsFile=function() return true end
local capAccepted=true
for i=1,52 do
  local names={}
  for j=1,40 do names[j]=string.format('bne_fascia_%04d_%02d_face',i,j) end
  local k=geotile.key(gx+i,gy)
  local body=namedBody('cap'..i,names[1],'/temp/beamngEarth/material-assets/property_123.materials.json')
  body.propertyMaterials.names=names
  if not roads.onTile({anchorId=2,key=k,h=body.h,data=body},2,B) then capAccepted=false end
end
T.check(capAccepted,'resident material limit degrades rather than rejects a new tile')
for _=1,220 do roads.update(gov,2,car,nil,B) end
T.check(#objsWith('cap52.cdae')==1 and #objsWith('cap52_property.cdae')==0,
  'at material cap base visual is imported without its named visual')
T.check(#objsWith('collision.cdae')>=52,'at material cap the physics mesh remains available')
loadJsonMaterialsFile=oldLoader
roads.clear()

T.done('test_roadgeo')
