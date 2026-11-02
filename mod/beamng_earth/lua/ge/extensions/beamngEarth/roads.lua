-- Roads near the player (docs/ROADMAP.md v1.6 "Roads", server/roads.py): the server announces road
-- tiles (`roads_tile`: a JSON file of chunks in the anchor frame) and drops them (`roads_drop`); each
-- chunk becomes one DecalRoad drawn on the physics ground (engine probes P1-P3, 2026-10-11: they
-- render on the hidden block, re-clip by themselves when it is re-imported or moved, and cost
-- ~0.45 ms per 100-node road with insertNodeNoRegen + regenerate). Creation and deletion run under the
-- frame governor (kinds roadChunk / roadDelete). A new anchor makes every road of the old one go
-- (the server sends the new frame's tiles again).
--
-- Materials are stock ones from official levels, loaded at runtime from the player's own install
-- (nothing copied): West Coast USA's asphalt strip, sidewalks and lines, Johnson Valley's dirt road
-- tracks, Italy's cobblestone.
--
-- Raised sidewalks (curbs, sidewalk slabs): one mesh per tile (server/sidewalks.py, the way West
-- Coast USA builds its sidewalks: one modelled mesh per district, with its `curbs` and `sidewalk1`
-- materials), announced as the tile's "walk" {shape, pos} and shown as a TSStatic that collides with
-- its visible mesh. A TSStatic only collides after be:reloadCollision() (asynchronous: in effect a
-- frame later; ~1.8 ms), so that runs once per RELOAD_EVERY_S at most while sidewalks come and go.
-- (First cut, replaced: a MeshRoad per sidewalk piece, 3 draw calls each and no curb profile.)
-- Storm drains are DecalRoad chunks like the rest (Driver Training's m_metal_grid_drain).
-- Console: beamngEarth_roads.status(), .setEnabled(bool)

local stopwatch = require('beamngEarth/stopwatch')

local M = {}

M.MATERIAL_FILES = { '/levels/west_coast_usa/art/road/main.materials.json',
  '/levels/east_coast_usa/art/road/main.materials.json',         -- ECA_road_edge_dirt (the asphalt's edge, roads.EDGE_DECAL)
  '/levels/west_coast_usa/art/decals/main.materials.json',       -- roadmarkings1 (turn arrows, markings.ARROW_MATERIAL)
  '/levels/west_coast_usa/art/shapes/roads/main.materials.json',   -- curbs, sidewalk1 (the sidewalk mesh)
  '/levels/johnson_valley/art/decalroad/main.materials.json',
  '/levels/italy/art/shapes/buildings/main.materials.json',        -- italy_cobblestone (paving stones)
  '/levels/driver_training/art/road/main.materials.json',          -- m_metal_grid_drain (storm drains)
  '/levels/gridmap_v2/art/shapes/grid/main.materials.json',        -- m_gm_concrete_plain (concrete streets)
  '/levels/beamng_earth/art/shapes/beamngEarth/buildings.materials.json',  -- buildings (server/buildings.py)
  '/levels/beamng_earth/art/shapes/beamngEarth/building_details.materials.json',
  '/levels/beamng_earth/art/shapes/beamngEarth/sidewalk.materials.json', -- metric slab paving
  -- highway signs (server/signstream.py: exit and overhead panels, mile markers, merge warnings)
  '/levels/beamng_earth/art/shapes/beamngEarth/roadside/exit.materials.json',
  '/levels/beamng_earth/art/shapes/beamngEarth/roadside/merge.materials.json' }
M.FADE = '450 150'          -- distanceFade: start, range (m)
M.enabled = true
-- the highway signs (server signstream.py, from cody196's PR #363) and the speed-limit signs (speedsigns.py): sign tiles
-- (key "s<tx>_<ty>") carry the render-only shapes SIGN_WHATS; switched off, their objects go but each tile keeps its data
-- (signData) to show again at once
M.signsEnabled = true
M.SIGN_WHATS = { 'exits', 'mileposts', 'merges', 'speeds' }
-- be:reloadCollision() at most this often: every rebuild is a ~20 ms physics frame (2026-10-13, the
-- engine's frame metrics), and while driving new sidewalk tiles arrive all the time. They arrive ~640 m
-- ahead (11 s at 58 m/s), so a few seconds before they collide do not matter. A terrain commit rebuilds
-- collision anyway: M.collisionRebuilt() clears the pending rebuild.
-- 2026-10-14: a rebuild had grown to ~56 ms (1.1 M collision vertices with the buildings) and ran every 3 s
-- while driving, most of the hitches of a 34 mph drive: new colliders now wait up to 6 s (still 11 s of margin
-- at 130 mph), and colliders deleted far behind the car (their stale collision harms nobody) up to 30 s.
M.RELOAD_EVERY_S = 6
-- Collision only near the car (2026-10-15: the rebuild cost scales with every colliding triangle loaded, ~40 ms in
-- Fells Point with all 36 tiles' buildings and sidewalks): a tile's colliders (sidewalks, decks, the buildings'
-- lean collision mesh "bldcol") are made once its centre is within COLLIDE_LEAD_S of driving (COLLIDE_M min / max)
-- and dropped again UNCOLLIDE_M beyond that. The drawn building meshes only render when the tile has a bldcol.
M.TILE_M = 256
M.COLLIDE_M = { 320, 2000 }
M.COLLIDE_LEAD_S = 14
M.UNCOLLIDE_M = 350
M.COLLIDE_CHECK_S = 0.25
M.RELOAD_DELETES_S = 30
M.DELETE_NEAR_M = 200       -- a collider deleted this close to the player counts as new (no ghost walls)
-- High speed (the user, 2026-10-19: "I always want the ground and any bridges/buildings to have collision ... going at
-- high speeds"; at 180 mph a bridge's collider was solid only 32 m ahead, held back by RELOAD_EVERY_S): above
-- FAST_MS the COLLIDE_LEAD_S reach is ahead of the car only (COLLIDE_M max), beside and behind it COLLIDE_M min;
-- and a collider the car reaches within URGENT_S is made solid at once (URGENT_GAP_S between those rebuilds at most).
M.FAST_MS = 25
M.SIDE_PENALTY = 4          -- nextWalk at FAST_MS: m along the path a metre sideways counts as (server roads.py)
M.LEAD_MAX_M = 2000         -- ... and what every tile behind the car comes after
M.URGENT_S = 6
M.URGENT_GAP_S = 1
-- What the car drives on comes first (nextWalk): a bridge deck's or a tunnel's collider counts this much nearer than the
-- rest (on a Steam Deck at 80 mph in Phoenix the import queue grew to 140 behind ~20 ms imports, and an I-10 overpass's
-- deck turned solid only as the car reached it, behind the sidewalks' and buildings' colliders of the same tiles)
M.DRIVE_FIRST_M = 400
-- ... and one the car reaches within URGENT_S (150 m at least) is made at once, whatever the governor's budget (its cost
-- still charged: what follows waits), one every URGENT_EVERY_FRAMES at most: at ~20 ms an import on a Steam Deck, the
-- 2-4 ms budget let ~3 a second through, fewer than a city's tiles bring at 80 mph
M.URGENT_EVERY_FRAMES = 3
-- No be:reloadCollision for SWAP_QUIET_FRAMES frames and SWAP_QUIET_MS after a terrain .ter swap (M.terrainSwapped): the
-- swapped block's collision follows by itself a frame later, and a rebuild in between took the block before its
-- heights were in: flat ground at z 0 for a second, and a ball at 180 mph sank under the real ground and fell through
-- it for good (in-game 2026-10-19, once the urgent rebuilds above made that coincidence common).
M.SWAP_QUIET_FRAMES = 3
M.SWAP_QUIET_MS = 150
-- A collision rebuild (be:reloadCollision, ~10-25 ms on a Steam Deck) in a frame that already spent RELOAD_ROOM_MS on
-- imports waits for the next frame, RELOAD_WAIT_FRAMES at most, unless the car is held over a collider (holdActive):
-- an urgent import, another and the rebuild made 70-80 ms frames on a Deck's Baltimore drive (2026-10-23)
M.RELOAD_ROOM_MS = 8.0
M.RELOAD_WAIT_FRAMES = 3
local reloadWaits = 0
-- A generous/loading governor allowance must not bunch several synchronous
-- TSStatic imports into one frame. Near, far and collision meshes share this cap.
M.MAX_IMPORTS_PER_FRAME = 1
M.MAX_PHYSICAL_STAGES = 2 -- admission extends the same queues; native memory calibration remains pending
local importsThisFrame, deferImports = 0, false
local buildingProgress
local physicalHandover
local occupancy = require('beamngEarth/occupancy')
local actorPositions, inUpdate = nil, false
local progressFrame = 0
-- A bounded share of eligible import frames supplies missing distant coverage.
-- Urgent collision and collision rebuilds always retain priority.
M.FAR_IMPORT_EVERY = 4
M.BUILDING_PROGRESS = 1
local sectorManifest = require('beamngEarth/sector_manifest')
local sharedSites = require('beamngEarth/shared_sites')
M.SECTOR_MANIFEST = 1
local sectorManifestRequired = false
function M.setSectorManifest(version) sectorManifestRequired = version == M.SECTOR_MANIFEST end

local newColliders = {}    -- { id, walkQ entry } of the colliders made since the last reloadCollision
local parked = {}          -- walkQ entries of colliders whose tile is not near enough yet
local sinceCollideCheck = stopwatch.new()
local held = {}            -- walkQ entries of colliding meshes held while the player is in their boxes
local noteNewColliders, playerIn, releaseHeld
M.BUILDING_CHUNKS = 1
local function buildingVisual(what)
  return what == 'bld' or type(what) == 'string' and what:match('^bld%d+$') ~= nil
end
local function buildingCollision(what)
  return what == 'bldcol' or type(what) == 'string' and what:match('^bldcol%d+$') ~= nil
end
local function validBuildingChunks(data)
  local chunks = data.buildingChunks
  if chunks == nil then return true end
  if type(chunks) ~= 'table' or chunks.v ~= M.BUILDING_CHUNKS
    or type(chunks.visual) ~= 'table' or type(chunks.collision) ~= 'table' then return false end
  local seen = {}
  for _, group in ipairs({ 'visual', 'collision' }) do
    for _, what in ipairs(chunks[group]) do
      local valid = group == 'visual' and buildingVisual(what) or group == 'collision' and buildingCollision(what)
      if not valid or seen[what] or type(data[what]) ~= 'table' or type(data[what].shape) ~= 'string'
        or type(data[what].pos) ~= 'table' then return false end
      seen[what] = true
    end
  end
  return true
end
local function meshWhats(base, data)
  local out, seen = {}, {}
  for _, what in ipairs(base) do out[#out + 1] = what; seen[what] = true end
  local chunks = data and data.buildingChunks
  if chunks then
    for _, group in ipairs({ 'visual', 'collision' }) do
      for _, what in ipairs(chunks[group]) do
        if not seen[what] then out[#out + 1] = what; seen[what] = true end
      end
    end
  end
  return out
end
local tiles = {}            -- key "a:tx_ty" -> { anchor, objs = { DecalRoad ids }, queued = n, walk = TSStatic id,
                            --   road = TSStatic id }
local walkQ = {}            -- { key, walk = {shape, pos}, what = 'walk' | 'road' } FIFO
local createQ = {}          -- { key, chunk } FIFO
local deleteQ = {}          -- object ids
local retiringSurfaceOwners = {} -- road tile key -> pooled slots still referenced by retiring geometry
local loadedMaterials = false
local anchorId = nil
local far = {}              -- far buildings (server buildings.far_tile): key "a:tx_ty" -> { anchor, id, shape, pos, hidden }
local farSeen = {}          -- far tile keys that arrived (with buildings or none): the skyline tiles' test
local farQ = {}             -- keys of far tiles to make
local lastError = nil
local sinceChange = stopwatch.new()  -- ms since a tile arrived / went or a road was made / deleted
local sinceReload = stopwatch.new()
local collisionDirty = false
local propCollisionDirty = false -- removed/moved Forest colliders cannot wait six seconds
local lastReloadAt = -math.huge   -- now() of the last be:reloadCollision (ours or another's): M.ahead
local reloads = 0                 -- be:reloadCollision runs so far (ours or another's): M.reloads
local sinceUrgent = math.huge     -- frames since the last urgent walk import (M.urgentWalk)
local deletesDirty = false  -- only far colliders deleted since the last rebuild (RELOAD_DELETES_S)

-- Every road object lives in one SimGroup. A Lua reload (Lua:requestReload) rebuilds the VM without
-- unloading the extensions, so nothing deletes the old objects: 2026-10-11, after a few reloads, 3,558
-- DecalRoads and 120 sidewalk MeshRoads were in the scene for 1,011 + 51 tracked (the user saw fps drop).
-- The group is emptied when this module loads (see the end of the file).
M.GROUP = 'bngEarthRoads'

local function group()
  local g = scenetree.findObject(M.GROUP)
  if not g then
    g = createObject('SimGroup')
    g.canSave = false
    g:registerObject(M.GROUP)
    scenetree.MissionGroup:addObject(g)
  end
  return g
end

-- Objects of a previous Lua state deleted. Returns how many.
function M.sweep()
  local g = scenetree.MissionGroup and scenetree.findObject(M.GROUP)
  if not g then return 0 end
  local n = g:getCount()
  if n > 0 then
    g:deleteAllObjects()
    be:reloadCollision()
  end
  return n
end

-- The road surfaces drawn opaque (2026-10-14): the stock decal materials are all translucent, and inside
-- one road mesh the markings showed only while the engine happened to draw them after the asphalt; with
-- many more translucent objects in view (buildings' windows, signals) they vanished. Opaque asphalt is
-- drawn first, always, and the translucent lines, crossings and gutters over it.
M.OPAQUE = { 'road_asphalt_2lane', 'italy_cobblestone' }
-- The opaque road surfaces cast no sun shadow (from Madderose's PR #41). Translucent, as the stock decal materials are,
-- they drew none; made opaque (above) they joined the shadow pass: every road tile's mesh drawn into each shadow
-- cascade every frame (the tiles are dynamic TSStatics, no cached shadow map), for a shadow that fell under the road
-- itself. The decks' slabs, the curbs and the sidewalks keep theirs.
M.NO_SHADOW = { 'road_asphalt_2lane', 'italy_cobblestone', 'm_gm_concrete_plain' }

local function loadMaterials()
  if loadedMaterials then return end
  for _, f in ipairs(M.MATERIAL_FILES) do loadJsonMaterialsFile(f) end
  for _, f in ipairs(require('beamngEarth/gasstations').MATERIAL_FILES) do loadJsonMaterialsFile(f) end   -- (pumps)
  local fields, order = {}, {}
  for _, name in ipairs(M.OPAQUE) do
    if not fields[name] then fields[name] = {}; order[#order + 1] = name end
    fields[name].translucent = '0'
  end
  for _, name in ipairs(M.NO_SHADOW) do
    if not fields[name] then fields[name] = {}; order[#order + 1] = name end
    fields[name].castShadows = '0'
  end
  for _, name in ipairs(order) do       -- (one reload a material)
    local m = scenetree.findObject(name)
    if m then
      pcall(function()
        for k, v in pairs(fields[name]) do m:setField(k, 0, v) end
        m:flush(); m:reload()
      end)
    end
  end
  local pad = scenetree.findObject('tactile_indicator')    -- curb ramp pads: US truncated domes are yellow
  if pad then pcall(function() pad:setField('baseColorFactor', 0, '0.95 0.78 0.18 1'); pad:flush(); pad:reload() end) end
  loadedMaterials = true
end

local function tileKey(aid, k) return tostring(aid) .. ':' .. tostring(k) end

-- Pooled shape files (server/matslots.py, 2026-10-16: the engine's frame cost grows with every distinct shape file it
-- ever loaded): roads_tile / bldfar_tile carry `slots` {what = {path, serial}}, shape files the server re-uses for
-- later tiles once we report [slot, serial] gone (core.lua pose.slotsGone). A slot goes when its tile is dropped AND
-- its last object is deleted (a collider deleted and made again while the tile lives keeps it).
local session = nil        -- the server session the slots belong to (setSession)
local objSlot = {}         -- object id -> session-qualified pooled file key
local slotLive = {}        -- session-qualified key -> objects alive with it
local slotDropped = {}     -- key -> { slot number, serial, session }, reported after object/engine retirement
local slotRefs = {}        -- key -> {slot, serial, session, count}: metadata owners independent of scene instances
local objectSessions = {}  -- unpooled and pooled instances keep their source folder alive too
local slotsGone = {}       -- { n, serial, session } to report
local engineDebt = require('beamngEarth/engine_debt').new()
local function slotOf(path) return tonumber(type(path) == 'string' and path:match('/slot_(%d+)%.cdae$') or nil) end
local function slotKey(n,sess) return tostring(sess)..':'..tostring(n) end

function M.setSession(s) session = s end

-- An object with a pooled shape was made / is deleted.
local function slotMade(id, path)
  local folder=type(path)=='string' and path:match('^/temp/beamngEarth/([^/]+)/')
  if folder then objectSessions[id]=folder end
  local n = slotOf(path)
  if not n then return end
  local sess=path:match('/temp/beamngEarth/([^/]+)/slot_%d+%.cdae$') or session
  local key=slotKey(n,sess)
  objSlot[id] = key
  slotLive[key] = (slotLive[key] or 0) + 1
end
local function slotObjGone(id, collided)
  local folder=objectSessions[id];objectSessions[id]=nil
  local key = objSlot[id]
  if not key then
    if collided and folder then engineDebt:deleted('folder:'..folder) end
    return
  end
  if collided then engineDebt:deleted(key) end
  objSlot[id] = nil
  slotLive[key] = (slotLive[key] or 1) - 1
  if slotLive[key] <= 0 then
    slotLive[key] = nil
    local d = slotDropped[key]
    if d and not engineDebt:held(key) then slotDropped[key] = nil; slotsGone[#slotsGone + 1] = d end
  end
end
-- A tile's slot { n, serial, session } is let go: at once if no object has it, else at its last delete.
local function slotDrop(sl)
  if not sl then return end
  local key=slotKey(sl[1],sl[3])
  if sl._released then return end
  sl._released=true
  local ref=slotRefs[key]
  if sl._refKey and ref then
    ref.count=ref.count-1
    if ref.count<=0 then slotRefs[key]=nil;ref=nil end
  end
  if ref then return end
  if (slotLive[key] or 0) > 0 or engineDebt:held(key) then slotDropped[key] = { sl[1], sl[2], sl[3] }
  else slotsGone[#slotsGone + 1] = { sl[1], sl[2], sl[3] } end
end
-- Is any mesh file a tile's parts (and exact variants) are made from gone? A server restart sends the same content
-- again (its hash h), whose objects the tile keeps, but the new server deletes the old run's session folder their
-- files were in: the objects showed nothing after the next reload of their shapes (the Stelvio's summit buildings,
-- 2026-10-31: three restarts in an evening, every building of the pass gone; their world box 0..2 m at the origin).
-- Such a tile is made again from the new message.
local function filesGone(parts, exact)
  for _, p in pairs(parts or {}) do
    local sh = type(p) == 'table' and p.shape
    if type(sh) == 'string' and sh ~= '' and not FS:fileExists(sh) then return true end
  end
  for _, sh in pairs(exact or {}) do
    if type(sh) == 'string' and sh ~= '' and not FS:fileExists(sh) then return true end
  end
  return false
end
-- The slots of msg.slots[what] as { n, serial, session } (nil: not pooled).
local function msgSlot(msg, what)
  local e = type(msg.slots) == 'table' and msg.slots[what]
  if type(e) ~= 'table' then return nil end
  local n, serial = slotOf(e[1]), tonumber(e[2])
  if not n or not serial or serial~=serial or serial<0 or serial>=2^53 or serial%1~=0 then return nil end
  local folder=e[1]:match('^/temp/beamngEarth/([^/]+)/') or session
  local sl={ n, serial, folder, path = e[1] }
  local key=slotKey(n,folder)
  local ref=slotRefs[key]
  if not ref then ref={n,serial,folder,count=0};slotRefs[key]=ref end
  ref.count=ref.count+1;sl._refKey=key;slotDropped[key]=nil
  return sl
end

local function releaseSlots(slots)
  for _,sl in ipairs(slots or {}) do slotDrop(sl) end
end
local function messageSlots(msg)
  local out={}
  local n=0;for _ in pairs(msg.slots or {}) do n=n+1;if n>8192 then error('oversized pooled shape inventory') end end
  for w in pairs(msg.slots or {}) do local sl=msgSlot(msg,w);if sl then out[#out+1]=sl end end
  return out
end
function M._admit(fn,msg,...)
  local claimed,refs=pcall(messageSlots,msg)
  if not claimed then lastError=tostring(refs);return false end
  local ok,result=pcall(fn,msg,...)
  releaseSlots(refs)
  if not ok then lastError=tostring(result);return false end
  return result
end
local function releasePending(t,replacement)
  local p=t.pendingGeo
  if not p then return end
  releaseSlots(p.slots,replacement);releaseSlots(p.skinSlots,replacement);releaseSlots(p.exactSlots,replacement)
  t.pendingGeo=nil
end
function M._holdReplacement(t,msg,data,currentAnchor)
  releasePending(t,msg)
  local pending={msg={},anchor=currentAnchor,slots=messageSlots(msg),sourceSession=session}
  for w,v in pairs(msg) do pending.msg[w]=v end
  pending.msg.data=data
  t.pendingGeo=pending;t.retireRequested=nil
  return true
end

-- The [slot, serial] pairs gone since the last call, for server session `sess`.
function M.takeSlotsGone(sess)
  if #slotsGone == 0 then return {} end
  local out = {}
  for _, g in ipairs(slotsGone) do if g[3] ~= nil and g[3] == sess then out[#out + 1] = { g[1], g[2] } end end
  slotsGone = {}
  return out
end

-- Every [slot, serial] held for session `sess` (hello after a reconnect): live tiles' slots and dropped ones whose
-- objects are not deleted yet.
function M.slotsHeld(sess)
  local out = {}
  for _,ref in pairs(slotRefs) do if ref[3]==sess then out[#out+1]={ref[1],ref[2]} end end
  for _, d in pairs(slotDropped) do if d[3] == sess then out[#out + 1] = { d[1], d[2] } end end
  return out
end

-- Source folders also contain unpooled base/exact files and parked resources.
-- They remain claimed until metadata, instances AND asynchronous physics let go.
function M._fileSessions(t)
  local out={}
  local function add(path)
    local s=type(path)=='string' and path:match('^/temp/beamngEarth/([^/]+)/')
    if s then out[s]=true end
  end
  add(t.shape)
  for _,p in pairs(t.parts or {}) do add(p.shape) end
  for _,path in pairs(t.exactShape or {}) do add(path) end
  for _,p in pairs(t.skin or {}) do if type(p)=='table' then add(p.shape) end end
  t.fileSessions=out
end
function M.heldSessions()
  local held={}
  for _,s in ipairs(M._shapeSessions()) do held[s]=true end
  for _,ref in pairs(slotRefs) do if ref[3] then held[ref[3]]=true end end
  for _,ref in pairs(slotDropped) do if ref[3] then held[ref[3]]=true end end
  for _,s in pairs(objectSessions) do held[s]=true end
  for key in pairs(engineDebt.pending) do local s=type(key)=='string' and key:match('^folder:(.+)$');if s then held[s]=true end end
  for _,t in pairs(tiles) do
    for s in pairs(t.fileSessions or {}) do held[s]=true end
    if t.pendingGeo and t.pendingGeo.sourceSession then held[t.pendingGeo.sourceSession]=true end
    for s in pairs(t.pendingPatch and t.pendingPatch.fileSessions or {}) do held[s]=true end
  end
  for _,f in pairs(far) do
    for s in pairs(f.fileSessions or {}) do held[s]=true end
    for s in pairs(f.previous and f.previous.fileSessions or {}) do held[s]=true end
  end
  local out={};for s in pairs(held) do out[#out+1]=s end;table.sort(out);return out
end

local function now() return os.clock() * 1000 end

-- Main-thread cost of each kind of unit (n, total ms, worst ms) since the level loaded: road chunks, deletes, each
-- mesh kind of a road tile (road, walk, bld, bldcol, deck ...), far building tiles, collision reloads. status().units
local unitStats = {}
local unitLog = {}       -- the last UNIT_LOG units: { kind, ms, shape } (status().unitLog)
M.UNIT_LOG = 400
local function noteUnit(kind, ms, shape)
  unitLog[#unitLog + 1] = { kind, ms, shape }
  if #unitLog > M.UNIT_LOG then table.remove(unitLog, 1) end
  local u = unitStats[kind]
  if not u then u = { n = 0, ms = 0, max = 0 }; unitStats[kind] = u end
  u.n, u.ms = u.n + 1, u.ms + ms
  if ms > u.max then u.max = ms end
end

local function releaseSurfaceOwners()
  if #deleteQ>0 then return end
  local trees=require('beamngEarth/trees')
  for key,slots in pairs(retiringSurfaceOwners) do
    local held=false
    for n in pairs(slots) do if (slotLive[n] or 0)>0 or engineDebt:held(n) then held=true; break end end
    if tiles[key] or not held then
      if not tiles[key] and trees.clearSurfaceExclusions then trees.clearSurfaceExclusions('road:'..key) end
      retiringSurfaceOwners[key]=nil
    end
  end
end

local buildingFade = require('beamngEarth/buildingfade').new()
local function hideBuilding(id, hidden) buildingFade:hide(id,hidden) end

local function ownBuildingsReady(t)
  if not t then return false end
  for what in pairs(t.parts or {}) do if buildingVisual(what) and not t[what] then return false end end
  return true
end

local function dropBuildingFallback(t)
  local f=t.buildingFallback
  if not f then return end
  for what in pairs(f.parts) do
    if f[what] then hideBuilding(f[what],true);deleteQ[#deleteQ+1]=f[what] end
  end
  for _,sl in pairs(f.slots) do slotDrop(sl) end
  t.buildingFallback=nil
end

local function dropTile(key, keepProgress, force)
  local t = tiles[key]
  if not t then return end
  if not force and physicalHandover and not physicalHandover:drop(key) then t.retireRequested=true;return false end
  if not force and M.occupied and M.occupied(t) then
    releasePending(t);M._releasePatch(t);t.retireRequested=true;return false
  end
  releasePending(t);M._releasePatch(t)
  if buildingProgress and not keepProgress then buildingProgress:drop((key:gsub('^g:', ''))) end
  dropBuildingFallback(t)
  local surfaceSlots={}
  for _,sl in pairs(t.slots or {}) do surfaceSlots[slotKey(sl[1],sl[3])]=true end
  retiringSurfaceOwners[key]=surfaceSlots
  for _, sl in pairs(t.slots or {}) do slotDrop(sl) end
  for w, v in pairs(t.oldSkin or {}) do       -- (a geotile's previous skin and replaced parts: road geotiles below)
    if type(w) == 'string' and w:sub(1, 2) == 's:' then slotDrop(v) else deleteQ[#deleteQ + 1] = v end
  end
  for _, id in pairs(t.oldPart or {}) do deleteQ[#deleteQ + 1] = id end
  for _, sl in pairs(t.oldPartSlot or {}) do slotDrop(sl) end
  t.oldSkin, t.oldPart, t.oldPartSlot = nil, nil, nil
  for _, id in ipairs(t.objs) do deleteQ[#deleteQ + 1] = id end
  if t.walk then deleteQ[#deleteQ + 1] = t.walk end
  if t.road then deleteQ[#deleteQ + 1] = t.road end
  if t.deck then deleteQ[#deleteQ + 1] = t.deck end
  for _, w in ipairs(meshWhats({ 'bld', 'bld2', 'bld3', 'bld4', 'bldcol', 'walkcol', 'tunnel', 'rail', 'railcol' }, t.data)) do
    if t[w] then
      if buildingVisual(w) then hideBuilding(t[w],true) end
      deleteQ[#deleteQ + 1] = t[w]
    end
  end
  if t.wire then deleteQ[#deleteQ + 1] = t.wire end
  for _, w in ipairs(M.SIGN_WHATS) do if t[w] then deleteQ[#deleteQ + 1] = t[w] end end
  -- and its meshes not made yet (from KyzoFox's 1.5.4, PR #64): a tile sent again under the same key left its old
  -- walkQ / held / createQ entries, which were then made for the new tile from pooled shape paths that had just been
  -- reported gone and refilled with another tile's shape: that tile's buildings drawn here at its ground height (houses
  -- floating in the sky near Cleburne, AL, 2026-10-19)
  local function purge(list)
    local keep = {}
    for _, q in ipairs(list) do if q.key ~= key then keep[#keep + 1] = q end end
    return keep
  end
  parked, walkQ, held, createQ = purge(parked), purge(walkQ), purge(held), purge(createQ)
  if t.props then require('beamngEarth/trees').dropKey((key:gsub(':', ':p', 1))) end
  if t.doorProps then require('beamngEarth/trees').dropKey('g:pd'..t.gkey) end
  if t.guardrails then require('beamngEarth/trees').dropKey((key:gsub(':', ':g', 1))) end
  if t.props then require('beamngEarth/nightlights').dropKey(key) end
  if t.park then require('beamngEarth/parking').dropKey(key) end
  if t.fuel then require('beamngEarth/gasstations').dropKey(key) end
  if t.sound then require('beamngEarth/ambience').dropSpaces(key) end
  if t.wells then require('beamngEarth/pumpjacks').dropKey(key) end
  tiles[key] = nil
  if M.refreshBuildingCoverage and t.geo then M.refreshBuildingCoverage(t.gkey) end
  releaseSurfaceOwners()
  return true
end

-- A far tile's street lamps (server buildings.far_lamps: { {x, y, z}, ... }, the far and skyline tiles' streets past
-- the road tiles; the user, 2026-10-27: "extend the street and window lights as far as the buildings render"): glow
-- rows of trees.lua's lampglow group (drawn at night only) while the tile shows, one trees tile per 256 m square
-- (its distance rings and caps; ranks hashed under the farthest ring's 0.2: every one shown, a cap thinning evenly).
M.FAR_LAMP_GROUPS = { 'lampglow' }
local function farLamps(key, f, on)
  if on == (f.lampKeys ~= nil) then return end
  local ok, trees = pcall(require, 'beamngEarth/trees')
  if not ok then return end
  if not on then
    for _, k in ipairs(f.lampKeys) do trees.dropKey(k) end
    f.lampKeys = nil
    return
  end
  local by, tag = {}, 'FL' .. tostring(key):gsub('[^%w]', '') .. '|'
  for i, p in ipairs(f.lamps) do
    if type(p) == 'table' and p[1] and p[2] and p[3] then
      local k = tag .. math.floor(p[1] / 256) .. '_' .. math.floor(p[2] / 256)
      by[k] = by[k] or {}
      by[k][#by[k] + 1] = { 0, p[1], p[2], p[3], 0, 1, 1, ((i * 7919) % 997) / 997 * 0.19 }
    end
  end
  f.lampKeys = {}
  for k, rows in pairs(by) do
    trees.onRows(f.anchor, k, rows, M.FAR_LAMP_GROUPS)
    f.lampKeys[#f.lampKeys + 1] = f.anchor .. ':' .. k
  end
end

-- Every road not of anchor aid goes (a new anchor: the server re-sends its tiles).
local function switchAnchor(aid)
  if aid == anchorId then return end
  anchorId = aid
  for key, t in pairs(tiles) do
    if t.anchor ~= aid and not t.ghost and not t.geo then dropTile(key) end   -- (geotiles: M.replace)
  end
  for key, f in pairs(far) do
    if f.anchor ~= aid and not f.ghost and not f.geo then      -- (far geotiles: M.replace)
      farLamps(key, f, false)
      if f.id then deleteQ[#deleteQ + 1] = f.id end
      slotDrop(f.slot)
      far[key] = nil
    end
  end
  for key in pairs(farSeen) do
    if string.sub(key, 1, #tostring(aid) + 1) ~= tostring(aid) .. ':' and not (far[key] and far[key].geo) then
      farSeen[key] = nil
    end
  end
  local keep = {}
  for _, q in ipairs(createQ) do if tiles[q.key] then keep[#keep + 1] = q end end
  createQ = keep
  keep = {}
  for _, q in ipairs(walkQ) do if tiles[q.key] then keep[#keep + 1] = q end end
  walkQ = keep
end

-- Pure: the DecalRoad fields of a chunk (name, value), in order.
function M.fieldsFor(chunk)
  return {
    { 'material', chunk.m }, { 'textureLength', tostring(chunk.tl or 10) },
    { 'renderPriority', tostring(chunk.p or 20) }, { 'drivability', '-1' }, { 'improvedSpline', 'true' },
    { 'overObjects', 'false' }, { 'distanceFade', M.FADE }, { 'decalBias', '0.1' },
  }
end

-- The collision radius around the player (m): COLLIDE_LEAD_S of driving at its speed, within COLLIDE_M.
function M.collideRadius(speed)
  return math.max(M.COLLIDE_M[1], math.min(M.COLLIDE_M[2], (speed or 0) * M.COLLIDE_LEAD_S))
end

local lastRadius = M.COLLIDE_M[1]
local foci = {}             -- other vehicles' collision islands { x, y, r } (M.setFoci)
local collisionfoci = require('beamngEarth/collisionfoci')
local lastSpeed = 0
local holdActive = false
local swapQuiet = nil       -- { frames left, stopwatch } after a terrain swap (M.terrainSwapped)    -- core's drop hold: the game paused, the car frozen where it was dropped (M.setHold)
local lastDir = nil         -- unit { x, y } of the player's motion at FAST_MS or more, else nil
-- The collision radius towards tile centre (cx, cy) from the player at p: lastRadius ahead of a fast car (within 45
-- degrees of its heading, and its own tile), COLLIDE_M min beside and behind it; lastRadius all round when slow.
function M.radiusToward(p, cx, cy, radius, dir)
  if not dir then return radius end
  local dx, dy = cx - p.x, cy - p.y
  local d = math.sqrt(dx * dx + dy * dy)
  if d <= M.TILE_M or (dx * dir.x + dy * dir.y) >= 0.7071 * d then return radius end
  return math.min(radius, M.COLLIDE_M[1])
end
-- Is tile t's centre within the collision radius of the player? (no car or no centre: yes)
function M.collideNear(t, extra)
  if not t or not t.cx then return true end
  local veh = getPlayerVehicle and getPlayerVehicle(0)
  if not veh then return true end
  local r = M.radiusToward(veh:getPosition(), t.cx, t.cy, lastRadius, lastDir)
  if M.nearPlayer(vec3(t.cx, t.cy, 0), r + (extra or 0) + M.TILE_M * 0.71) then return true end
  -- or near another vehicle's collision island (collisionfoci.lua: other players' cars, traffic)
  return #foci > 0 and collisionfoci.near(foci, t.cx, t.cy, (extra or 0) + M.TILE_M * 0.71) or false
end

-- Other vehicles' collision foci (collisionfoci.lua, through core.lua): their tiles' colliders are made too.
function M.setFoci(f) foci = f or {} end

-- Every COLLIDE_CHECK_S: parked colliders whose tile came near queued; far tiles' colliders dropped.
local function updateCollideRange()
  if sinceCollideCheck() < M.COLLIDE_CHECK_S * 1000 then return end
  sinceCollideCheck = stopwatch.new()
  local veh = getPlayerVehicle and getPlayerVehicle(0)
  local v = veh and veh.getVelocity and veh:getVelocity()
  local sp = v and math.sqrt(v.x * v.x + v.y * v.y) or 0
  lastRadius = M.collideRadius(sp)
  lastSpeed = sp
  lastDir = sp >= M.FAST_MS and { x = v.x / sp, y = v.y / sp } or nil
  if #parked > 0 then
    local keep = {}
    for _, q in ipairs(parked) do
      local t = tiles[q.key]
      if t then
        if M.collideNear(t) then walkQ[#walkQ + 1] = q else keep[#keep + 1] = q end
      end
    end
    parked = keep
  end
  for key, t in pairs(tiles) do
    if not t.staged and t.cq and not M.collideNear(t, M.UNCOLLIDE_M) and not M.occupied(t) then
      for what, q in pairs(t.cq) do
        if t[what] then deleteQ[#deleteQ + 1] = t[what]; t[what] = nil end
        if not t.ghost then parked[#parked + 1] = q end   -- a ghost's queue entries are the old frame's
      end
      t.cq = nil
    end
  end
end

local function isCollider(o)
  local c = o.class or (o.getClassName and o:getClassName())
  if c == 'MeshRoad' then return true end
  return c == 'TSStatic' and o:getField('collisionType', 0) ~= 'None'
end

function M.setRoadsideWireBlocked(key,blocked)
  local t=tiles[key]
  if not t then return end
  t.roadsideWireBlocked=blocked
  local o=t.wire and scenetree.findObjectById(t.wire)
  if o then o:setHidden(blocked) end
end

-- collide: true ('Visible Mesh Final'), a collision type name, or false / nil (render only)
local function createWalk(walk, collide)
  if FS and FS.fileExists and not FS:fileExists(walk.shape) then error('missing shape '..tostring(walk.shape)) end
  if walk.staged then collide=false end
  local o = createObject('TSStatic')
  o:setField('shapeName', 0, walk.shape)
  -- 'Visible Mesh Final' (the engine's own suggestion: 'Performance: Mesh is using visible collision ... switch the
  -- mesh to Visible Mesh Final'); the same collision (in-game rays, 2026-10-17)
  o:setField('collisionType', 0, type(collide) == 'string' and collide or (collide and 'Visible Mesh Final' or 'None'))
  o:setField('decalType', 0, 'None')
  -- Completed building shapes contain native LODs. Their old dynamic=true path
  -- bypassed the static shape manager (and its instanced LOD crossfade).
  -- Terrain/road crossovers and provisional shells retain the dynamic path.
  o:setField('dynamic', 0, walk.nativeLod and not collide and 'false' or 'true')
  o.canSave = false
  if walk.buildingFade and buildingFade.enabled then
    o:setField('useInstanceRenderData',0,'true')
    o:setHidden(true)
  elseif walk.staged then o:setHidden(true) end
  o:setPosition(vec3(walk.pos[1], walk.pos[2], walk.pos[3]))
  o:registerObject('')
  if walk.rot then        -- (a geotile's part: placed from its tile's frame, M.geoWalk)
    local r = walk.rot
    o:setPosRot(walk.pos[1], walk.pos[2], walk.pos[3], r[1], r[2], r[3], r[4])
  end
  group():addObject(o)
  if walk.buildingFade then
    buildingFade:register(o:getID())
    hideBuilding(o:getID(),walk.staged or false)
  end
  return o:getID()
end

function M._collisionKind(what,q)
  if q.renderOnly or what=='road' or what=='wire' then return false end
  if buildingCollision(what) or what=='walkcol' or what=='railcol' then return 'Collision Mesh' end
  return 'Visible Mesh Final'
end
buildingProgress = require('beamngEarth/buildingprogress').new({
  create = function(w) loadMaterials(); w.buildingFade=true; return createWalk(w, false) end,
  hide = hideBuilding,
  delete = function(id) deleteQ[#deleteQ+1]=id end,
  made = slotMade, release = slotDrop, slot = msgSlot,
  reconcile = function(key) M.refreshBuildingCoverage(key) end,
  minimumStage = function(key)
    local t=tiles['g:'..key]
    if t and (t.buildingFallback or ownBuildingsReady(t)) then return 2 end
    local f=far['F:'..key]
    if f and f.previous then f=f.previous end
    if f then for _,p in pairs(f.parts or {}) do if p.id then return 1 end end end
    return M.skyBlocksBuildings(key) and 1 or 0
  end,
  blocked = function(key)
    local t=tiles['g:'..key]
    local e=buildingProgress.entries[key]
    return M.skyBlocksBuildings(key) or (t and
      ((t.buildingFallback and not ownBuildingsReady(t)) or (e and e.attached~=t and ownBuildingsReady(t))))
  end,
  hideFar = function(key)
    local f=far['F:'..key]
    if f and f.previous then f=f.previous end
    if f then for _,p in pairs(f.parts or {}) do
      local o=p.id and scenetree.findObjectById(p.id)
      if o then hideBuilding(p.id,true);p.hidden=true end
    end end
  end,
  farVisible = function(key)
    local f=far['F:'..key]
    if f and f.previous then f=f.previous end
    if f then for _,p in pairs(f.parts or {}) do if p.id and not p.hidden then return true end end end
    return false
  end
})

function M.onBuildingProgress(msg, currentAnchor)
  if not M.enabled then
    for w in pairs(msg.slots or {}) do slotDrop(msgSlot(msg,w)) end
    return false
  end
  local accepted=buildingProgress:receive(msg,currentAnchor)
  if accepted then M.refreshBuildingCoverage(msg.key) end
  return accepted
end

local function createChunk(chunk)
  local r = createObject('DecalRoad')
  for _, f in ipairs(M.fieldsFor(chunk)) do r:setField(f[1], 0, f[2]) end
  r.canSave = false
  r:registerObject('')
  group():addObject(r)
  for _, n in ipairs(chunk.n) do r:insertNodeNoRegen(vec3(n[1], n[2], n[3]), chunk.w, -1) end
  r:regenerate()
  return r:getId()
end
function M._createChunk(chunk,staged)
  local id=createChunk(chunk)
  if staged then
    local o=scenetree.findObjectById(id)
    local ok=pcall(function() o:setHidden(true) end)
    if not ok then if o then o:delete() end;error('cannot stage road chunk') end
  end
  return id
end

-- Road geotiles (server --geo-tiles on, hello.roadGeo = M.ROAD_GEO; .claude/work/geotiles_plan.md phase 1c): a road
-- tile keyed 'g17_x_y' (geotile.lua) whose CONTENT (buildings and their collision mesh, decks, tunnels, rails, wires,
-- street furniture and guard rails, parking spots, gas stations, pump jacks, sound spaces) is in the tile's own frame
-- and belongs to no anchor: it stays across rebases and teleports near, each shape placed into the current anchor's
-- world at its pivot (setPosRot: geotile.placement, rigid; a tall part the rigid move would leave off comes as its
-- "exact variant" from the server, roads_exact), each row mapped exactly (geotile.apply). Its SKIN (the draped road
-- mesh, plazas, sidewalks and their collision) follows the anchor's 2 m lattice and height quantum: a skin per anchor
-- (roads_skin), the old one kept, moved and lifted q/2 + SKIN_LIFT_M (no poke-through on the new block) until the
-- new one is made. M.replace(anchor) re-places everything at a rebase (core.lua finishRebase): no ghosts, colliders
-- and slots kept.
M.ROAD_GEO = 1
M.SKIN_LIFT_M = 0.003
M.geoStats = { tiles = 0, kept = 0, replaced = 0, skins = 0, skinSwaps = 0, exact = 0, exactBase = 0 }
local geotile = require('beamngEarth/geotile')
local geodesy = require('beamngEarth/geodesy')
local anchorObj = nil       -- the current anchor (geodesy) the geotiles are placed into (M.update, onTile)
M.CONTENT_WHATS = { 'deck', 'bld', 'bld2', 'bld3', 'bld4', 'bldcol', 'wire', 'tunnel', 'rail', 'railcol' }
M.SKIN_WHATS = { 'road', 'walk', 'walkcol' }

local function geoKey(gkey) return 'g:' .. tostring(gkey) end
M.geoKey = geoKey

-- A geotile's placement of a part (its pivot) into anchor a: { pl = geotile.placement, xf = rigid transform, q }.
local function partPlacement(t, a, pivot)
  local pl = geotile.placement(t.frame, a, 0, 0, pivot or 0)
  local xf = geodesy.transformOf(pl.r, pl.t)
  local qx, qy, qz, qw = xf:beamngQuat()
  return { pl = pl, xf = xf, q = { qx, qy, qz, qw }, inv = xf:inverse() }
end

-- Pure-ish: tile t's placements into anchor a (each part's at its pivot, the rows' at the tile's), its centre.
function M.placeGeoTile(t, a)
  t.anchorObj = a
  t.pls = {}
  for what, p in pairs(t.parts or {}) do t.pls[what] = partPlacement(t, a, p.pivot) end
  t.rowPl = partPlacement(t, a, t.rowPivot or 0)
  local cx, cy = geotile.apply(t.rowPl.pl, 0, 0, t.rowPivot or 0)
  t.cx, t.cy = cx, cy
end

-- Rows of a road tile's content mapped into its placement (exact: geotile.apply with the shear): parking spots
-- [x, y, z, heading], pump jacks [x, y, z, yaw], sound rows (flat, 8 a row: kind, x, y, z, l, w, h, yaw rad),
-- station records (props / areas pos + yaw, area icons), furniture rows [group, x, y, z, yaw, ...] (the lamps).
local function mapPt(pl, p)
  local x, y, z = geotile.apply(pl, p[1], p[2], p[3])
  return { x, y, z }
end
function M.mapRows(pl, rows, xi, yawi, rad)
  if type(rows) ~= 'table' then return rows end
  local dyaw = geotile.yawOf(pl)
  if rad then dyaw = math.rad(dyaw) end
  local out = {}
  for i, r in ipairs(rows) do
    if type(r) == 'table' then
      local n = {}
      for k, v in pairs(r) do n[k] = v end
      if type(r[xi]) == 'number' and type(r[xi + 1]) == 'number' and type(r[xi + 2]) == 'number' then
        n[xi], n[xi + 1], n[xi + 2] = geotile.apply(pl, r[xi], r[xi + 1], r[xi + 2])
      end
      if yawi and type(r[yawi]) == 'number' then n[yawi] = r[yawi] + dyaw end
      out[i] = n
    else
      out[i] = r
    end
  end
  return out
end
function M.mapFlat(pl, flat, stride, xi, yawi)
  if type(flat) ~= 'table' then return flat end
  local out, dyaw = {}, math.rad(geotile.yawOf(pl))
  for i = 1, #flat do out[i] = flat[i] end
  for b = 0, #flat - stride, stride do
    out[b + xi], out[b + xi + 1], out[b + xi + 2] = geotile.apply(pl, flat[b + xi], flat[b + xi + 1], flat[b + xi + 2])
    if yawi then out[b + yawi] = flat[b + yawi] + dyaw end
  end
  return out
end
function M.mapStations(pl, recs)
  if type(recs) ~= 'table' then return recs end
  local dyaw = geotile.yawOf(pl)
  local out = {}
  for i, r in ipairs(recs) do
    local n = {}
    for k, v in pairs(r) do n[k] = v end
    n.props, n.areas = {}, {}
    for j, p in ipairs(r.props or {}) do
      local q = {}
      for k, v in pairs(p) do q[k] = v end
      if type(p.pos) == 'table' then q.pos = mapPt(pl, p.pos) end
      if type(p.yaw) == 'number' then q.yaw = p.yaw + dyaw end
      n.props[j] = q
    end
    for j, a in ipairs(r.areas or {}) do
      local q = {}
      for k, v in pairs(a) do q[k] = v end
      if type(a.pos) == 'table' then q.pos = mapPt(pl, a.pos) end
      if type(a.icon) == 'table' then q.icon = mapPt(pl, a.icon) end
      if type(a.yaw) == 'number' then q.yaw = a.yaw + dyaw end
      n.areas[j] = q
    end
    out[i] = n
  end
  return out
end

-- The rows of tile t (key) handed to their modules, mapped into its current placement (made: replaced in place).
local function buildingsReady(t)
  for _,what in ipairs(t.data and t.data.buildingChunks and t.data.buildingChunks.visual or {}) do
    if not t[what] then return false end
  end
  return true
end

local function flushBuildingDoors(t)
  if t.pendingDoorProps and buildingsReady(t) then
    local p=t.pendingDoorProps
    require('beamngEarth/trees').onGeoRows('pd'..t.gkey,t.gkey,p.items,p.groups,nil,
      t.frame,t.rowPivot or 0,t.anchorObj)
    t.pendingDoorProps=nil;t.doorProps=true
  end
end

local function vegetationBounds(key,t)
  if t.geo and t.anchorObj then
    local z,x,y=geotile.parse(t.gkey)
    local box={math.huge,math.huge,-math.huge,-math.huge}
    for _,p in ipairs(geotile.quad(t.anchorObj,z,x,y)) do
      box[1],box[2],box[3],box[4]=math.min(box[1],p[1]),math.min(box[2],p[2]),math.max(box[3],p[1]),math.max(box[4],p[2])
    end
    return box
  end
  local x,y=tostring(key):match('(%-?%d+)_(%-?%d+)$')
  if x then x,y=tonumber(x)*256,tonumber(y)*256; return {x,y,x+256,y+256} end
end
local function installVegetationExclusions(key,t,data,pl)
  retiringSurfaceOwners[key]=nil -- a replacement owner's mask must never be released by an old retirement
  local trees=require('beamngEarth/trees')
  if trees.setSurfaceExclusions then
    trees.setSurfaceExclusions('road:'..key,data.vegetationExclusions,pl,vegetationBounds(key,t))
  end
end

local function geoRows(key, t, data, replacing)
  local pl = t.rowPl.pl
  installVegetationExclusions(key,t,data,pl)
  if type(data.props) == 'table' and type(data.props.items) == 'table' then   -- street lights, poles (trees.lua)
    -- (at a rebase trees.lua places its own geotiles: trees.transform)
    if not replacing then
      local rows=data.props.items
      if not buildingsReady(t) then
        local normal,doors={},{}
        for _,row in ipairs(rows) do
          local list=data.props.groups[(row[1] or -1)+1]=='door' and doors or normal
          list[#list+1]=row
        end
        rows=normal
        if #doors>0 then t.pendingDoorProps={items=doors,groups=data.props.groups} end
      end
      require('beamngEarth/trees').onGeoRows('p' .. t.gkey, t.gkey, rows, data.props.groups, nil,
        t.frame, t.rowPivot or 0, t.anchorObj, key)
    end
    require('beamngEarth/nightlights').onRows(key, M.mapRows(pl, data.props.items, 2, 5), data.props.groups)
    t.props = true
  end
  if type(data.guardrails) == 'table' and type(data.guardrails.items) == 'table' and #data.guardrails.items > 0 then
    if not replacing then
      require('beamngEarth/trees').onGeoRows('g' .. t.gkey, t.gkey, data.guardrails.items, data.guardrails.groups,
        17, t.frame, t.rowPivot or 0, t.anchorObj)
    end
    t.guardrails = true
    t.guardrailRows = #data.guardrails.items
  end
  if type(data.park) == 'table' and data.park[1] then
    require('beamngEarth/parking').onRows(t.anchor, key, M.mapRows(pl, data.park, 1, 4))
    t.park = true
  end
  if type(data.fuel) == 'table' and data.fuel[1] then
    require('beamngEarth/gasstations').onRows(t.anchor, key, M.mapStations(pl, data.fuel))
    t.fuel = true
  end
  if type(data.wells) == 'table' and data.wells[1] then
    local pj = require('beamngEarth/pumpjacks')
    local rows = M.mapRows(pl, data.wells, 1, 4)
    if t.wells and pj.placeRows then pj.placeRows(key, rows) else pj.onRows(key, rows) end
    t.wells = true
  end
  if type(data.sound) == 'table' and data.sound[1] then
    local amb = require('beamngEarth/ambience')
    local flat = M.mapFlat(pl, data.sound, 8, 2, 8)
    if t.sound and amb.placeSpaces then amb.placeSpaces(key, flat) else amb.onSpaces(key, flat) end
    t.sound = true
  end
end

-- The mesh parts of geotile t queued (each its placement's, made by update); t.exactShape[what]: its exact variant.
local function queueGeoParts(key, t, data, visualOnly)
  local lean = t.leanBuildings or t.parts.bldcol ~= nil
  local leanRail = t.leanRails or t.parts.railcol ~= nil
  for _, what in ipairs(meshWhats(M.CONTENT_WHATS, data)) do
    if t.parts[what] and not t[what] and (not visualOnly or buildingVisual(what)) then
      local q = { key = key, what = what, tile = t, geo = true,
        renderOnly = what == 'wire' or (lean and buildingVisual(what)) or (leanRail and what == 'rail') }
      if not q.renderOnly then t.colWant[what] = true end
      if q.renderOnly or M.collideNear(t) then walkQ[#walkQ + 1] = q else parked[#parked + 1] = q end
    end
  end
end

-- The shape a geotile's part shows now: its exact variant for this anchor, else its base.
local function partShape(t, what)
  return (t.exactShape and t.exactShape[what]) or (t.parts[what] and t.parts[what].shape)
end

-- A geotile's part as createWalk takes it: its shape, placed (position and rotation).
function M.geoWalk(t, what)
  local p = t.parts[what]
  local pp = t.pls and t.pls[what]
  if not p or not pp then return nil end
  local x, y, z = pp.xf:apply(p.pos[1], p.pos[2], p.pos[3])
  return { shape = partShape(t, what), pos = { x, y, z }, rot = pp.q }
end

-- Server message `roads_tile` for a geotile key: its content (data: the JSON; frame, h, slots, exact).
function M.onGeoTile(msg, currentAnchor, a, staged, admitted)
  if not admitted then return M._admit(M.onGeoTile,msg,currentAnchor,a,staged,true) end
  a = a or anchorObj
  if not a then return false end
  anchorObj = a
  local ok, data = true, msg.data
  if type(data) ~= 'table' then ok, data = pcall(jsonDecode, readFile(msg.path) or '') end
  if not ok or type(data) ~= 'table' or not validBuildingChunks(data)
    or not sectorManifest.valid(data,msg.key,sectorManifestRequired) then
    lastError = 'unreadable road geotile ' .. tostring(msg.path)
    return false
  end
  local key = staged and staged.key or geoKey(msg.key)
  local old = tiles[key]
  if not staged and not old and not sharedSites.compatible(data,tiles,key) then
    lastError='shared site surface revision waits for resident neighbours'
    return false
  end
  local h = msg.h or data.h
  local filesPresent=old and old.geo and not filesGone(old.parts, old.exactShape)
  local reuse=filesPresent and data.physicalHash and old.data.physicalHash==data.physicalHash
  if old and not staged then
    local handled=M._handover('offer',key,msg,data,currentAnchor,a,reuse or filesPresent and h and old.h==h)
    if handled~=nil then return handled end
  end
  if filesPresent and h and old.h == h then
    releasePending(old,msg)
    old.retireRequested=nil
    buildingProgress:complete(msg.key,msg.buildingProgressToken)
    -- the same content again (a server restart): its objects stay; the new message's slots are not used
    releaseSlots(messageSlots(msg),nil,old.slots)
    old.anchor, old.orphan = currentAnchor, nil
    -- (its furniture and guard rails again where trees.lua has them no more: a disconnect clears them all, trees.clear;
    -- the poles near the car were gone after a server restart, their wires, part of the tile, still up: the Stelvio,
    -- 2026-10-31)
    local T = require('beamngEarth/trees')
    if type(data.props) == 'table' and type(data.props.items) == 'table' and not T.hasGeo('p' .. old.gkey) then
      T.onGeoRows('p' .. old.gkey, old.gkey, data.props.items, data.props.groups, nil, old.frame, old.rowPivot or 0,
        old.anchorObj)
    end
    if type(data.guardrails) == 'table' and type(data.guardrails.items) == 'table' and #data.guardrails.items > 0
        and not T.hasGeo('g' .. old.gkey) then
      T.onGeoRows('g' .. old.gkey, old.gkey, data.guardrails.items, data.guardrails.groups, 17, old.frame,
        old.rowPivot or 0, old.anchorObj)
    end
    M._incomingExact(old,msg,currentAnchor)
    M.geoStats.kept = M.geoStats.kept + 1
    return true
  end
  local frame = geotile.frameOf({ frame = msg.frame or data.frame, key = msg.key })
  if not frame then lastError = 'road geotile without a frame: ' .. tostring(msg.key); return false end
  -- A quality-only replacement can keep every physical object, skin and prop.
  -- The server hashes the actual nonvisual bytes, not just their bounds.
  local fallback=old and old.buildingFallback
  if old and not fallback and ownBuildingsReady(old) then
    fallback={frame=old.frame,parts={},slots={},exactShape={},exactOf={}}
    for what,p in pairs(old.parts) do if buildingVisual(what) then
      fallback.parts[what]=p;fallback[what]=old[what];old[what]=nil
      fallback.exactShape[what]=old.exactShape[what];fallback.exactOf[what]=old.exactOf[what]
      for _,w in ipairs({what,'x:'..what}) do fallback.slots[w]=old.slots[w];old.slots[w]=nil end
    end end
  end
  if old then
    old.buildingFallback=nil
    if reuse then
      for what in pairs(old.parts) do if buildingVisual(what) then
        if old[what] then hideBuilding(old[what],true);deleteQ[#deleteQ+1]=old[what] end
        old[what]=nil;old.parts[what]=nil;old.exactShape[what]=nil;old.exactOf[what]=nil
        for _,w in ipairs({what,'x:'..what}) do slotDrop(old.slots[w]);old.slots[w]=nil end
      end end
      local function purge(list)
        local keep={};for _,q in ipairs(list) do
          if not (q.tile==old and buildingVisual(q.what)) then keep[#keep+1]=q end
        end;return keep
      end
      walkQ,parked,held=purge(walkQ),purge(parked),purge(held)
    else dropTile(key,true,true) end -- occupancy checked before detaching visuals
  end
  local t = reuse and old or { anchor = currentAnchor, geo = true, gkey = msg.key, frame = frame, h = h, objs = {}, queued = 0,
    colliders = {}, slots = {}, at = now(), colWant = {}, parts = {}, exactShape = {}, exactOf = {} }
  t.h=h;t.anchor=currentAnchor;t.buildingFallback=fallback
  t.staged=staged
  if staged then staged.tile=t end
  local cols = type(data.colliders) == 'table' and data.colliders or {}
  local pivots, np = 0, 0
  for _, what in ipairs(meshWhats(M.CONTENT_WHATS, data)) do
    local e = data[what]
    if reuse and not buildingVisual(what) then
      slotDrop(msgSlot(msg,what))
    elseif type(e) == 'table' and e.shape and type(e.pos) == 'table' then
      local sl = msgSlot(msg, what)
      t.parts[what] = { shape = sl and sl.path or e.shape, pos = e.pos, pivot = tonumber(e.pivot) or 0,
        relief = tonumber(e.relief) or 0 }
      if sl then t.slots[what] = sl end
      if cols[what] then t.colliders[what] = cols[what] end
      pivots, np = pivots + (tonumber(e.pivot) or 0), np + 1
    else
      slotDrop(msgSlot(msg, what))
    end
  end
  local retainedExact={anchorId=currentAnchor,key=msg.key,contentHash=h,parts={},slots={}}
  for what, path in pairs(type(msg.exact) == 'table' and msg.exact or {}) do
    if reuse and not buildingVisual(what) then
      if type(path)=='string' and t.exactOf[what]~=currentAnchor then
        retainedExact.parts[what]=path
        retainedExact.slots[what]=msg.slots and msg.slots['x:'..what]
      else slotDrop(msgSlot(msg,'x:'..what)) end
    elseif t.parts[what] and type(path) == 'string' then
      local sl = msgSlot(msg, 'x:' .. what)
      t.exactShape[what] = sl and sl.path or path
      t.exactOf[what] = currentAnchor
      if sl then t.slots['x:' .. what] = sl end
    end
  end
  if reuse then
    for what in pairs(t.parts) do
      if not buildingVisual(what) and t.exactShape[what] and not (msg.exact and msg.exact[what]) then
        retainedExact.parts[what]=false -- the base is exact enough in this anchor again
      end
    end
  end
  if not reuse then t.rowPivot = np > 0 and pivots / np or 0 end
  t.data = data
  M._fileSessions(t)
  M.placeGeoTile(t, a)
  tiles[key] = t
  if not staged then buildingProgress:attach(t,msg) end
  sinceChange = stopwatch.new()
  if not reuse and not staged then geoRows(key, t, data) end
  queueGeoParts(key, t, data, reuse)
  if next(retainedExact.parts) then M.onExact(retainedExact,currentAnchor) end
  if not staged then flushBuildingDoors(t);M.refreshBuildingCoverage(t.gkey) end
  M.geoStats.tiles = M.geoStats.tiles + 1
  return true
end

-- Server message `roads_skin` {anchorId, key, data / path, slots}: the draped surfaces of a geotile for this anchor.
-- The old skin's objects stay until the new ones are made (per part; what the new skin lacks: with its road mesh).
function M.onSkin(msg, currentAnchor, admitted, target)
  if not admitted then return M._admit(M.onSkin,msg,currentAnchor,true) end
  local t = target or tiles[geoKey(msg.key)]
  local function release()
    if type(msg.slots) == 'table' then for w in pairs(msg.slots) do slotDrop(msgSlot(msg, w)) end end
  end
  if not t or msg.anchorId ~= currentAnchor then release(); return false end
  if not target and t.retireRequested then release();return false end
  local ok, data = true, msg.data
  if type(data) ~= 'table' then ok, data = pcall(jsonDecode, readFile(msg.path) or '') end
  if not ok or type(data) ~= 'table' then release(); lastError = 'unreadable road skin ' .. tostring(msg.path); return false end
  local candidate,transaction
  if not target then candidate,transaction=M._handover('route',geoKey(msg.key),data.contentHash) end
  if candidate then
    if transaction.phase=='awaitFrame' or transaction.phase=='rebaseWait' then
      releaseSlots(transaction.skinSlots,msg);transaction.skinMsg={};for w,v in pairs(msg) do transaction.skinMsg[w]=v end
      transaction.skinMsg.data=data;transaction.skinSlots=messageSlots(msg)
      return true
    end
    t=candidate
  end
  if t.pendingGeo then
    local p=t.pendingGeo
    if data.contentHash~=p.msg.h then release();return false end
    releaseSlots(p.skinSlots,msg)
    p.skinMsg={};for w,v in pairs(msg) do p.skinMsg[w]=v end;p.skinMsg.data=data
    p.skinSlots=messageSlots(msg)
    return true
  end
  if t.physicalReplacement and t.physicalReplacement.kind~='patch' then release();return false end
  if (sectorManifestRequired and data.contentHash==nil) or (data.contentHash and data.contentHash~=t.h) then
    release();return false
  end
  if not target and not t.staged and (t.skin or t.physicalReplacement) then
    return M._handover('patch',geoKey(msg.key),'skin',msg,data,currentAnchor,anchorObj)
  end
  -- the previous skin: its objects kept as the old ones (swapped as the new are made), its queue entries gone
  t.oldSkin = t.oldSkin or {}
  for _, w in ipairs(M.SKIN_WHATS) do
    if t[w] then
      if t.oldSkin[w] then deleteQ[#deleteQ + 1] = t.oldSkin[w] end
      t.oldSkin[w] = t[w]
      t[w] = nil
    end
    if t.cq then t.cq[w] = nil end
    if t.slots[w] then
      slotDrop(t.oldSkin['s:'..w]);t.oldSkin['s:' .. w] = t.slots[w]; t.slots[w] = nil
    end
  end
  for _, id in ipairs(t.objs) do deleteQ[#deleteQ + 1] = id end
  t.objs, t.queued = {}, 0
  local function purge(list)
    local keep = {}
    for _, q in ipairs(list) do if not (q.tile == t and q.skin) then keep[#keep + 1] = q end end
    return keep
  end
  walkQ, parked, held, createQ = purge(walkQ), purge(parked), purge(held), purge(createQ)
  local cols = type(data.colliders) == 'table' and data.colliders or {}
  t.colliders.walk, t.colliders.walkcol = cols.walk, cols.walkcol
  t.colWant.walk, t.colWant.walkcol = nil, nil
  local pv = type(data.pivot) == 'table' and data.pivot or {}
  t.skin = { anchor = msg.anchorId, anchorObj = anchorObj, pending = 0,
    pivot = { tonumber(pv[1]) or t.cx or 0, tonumber(pv[2]) or t.cy or 0, tonumber(pv[3]) or 0 }, q = tonumber(data.q) or 0 }
  local road = type(data.road) == 'table' and data.road.shape and type(data.road.pos) == 'table' and data.road
  local leanWalk = type(data.walkcol) == 'table' and data.walkcol.shape ~= nil
  for _, what in ipairs(M.SKIN_WHATS) do
    local w = data[what]
    local sl = msgSlot(msg, what)
    if type(w) == 'table' and w.shape and type(w.pos) == 'table' then
      if sl then w = { shape = sl.path, pos = w.pos }; t.slots[what] = sl end
      t.skin[what] = { shape = w.shape, pos = w.pos }
      local q = { key = t.staged and t.staged.key or geoKey(msg.key), walk = w, what = what, tile = t, skin = true,
        renderOnly = what == 'road' or (leanWalk and what == 'walk') }
      if not q.renderOnly then t.colWant[what] = true end
      t.skin.pending = t.skin.pending + 1
      if q.renderOnly or M.collideNear(t) then walkQ[#walkQ + 1] = q else parked[#parked + 1] = q end
    else
      slotDrop(sl)
    end
  end
  if not road and type(data.chunks) == 'table' then       -- (no road mesh: DecalRoads, as an anchor tile's)
    for _, c in ipairs(data.chunks) do createQ[#createQ + 1] = { key = t.staged and t.staged.key or geoKey(msg.key), chunk = c, skin = true, tile = t } end
    t.queued = #data.chunks
  end
  if t.skin.pending == 0 then M.dropOldSkin(t) end
  M._fileSessions(t)
  M.geoStats.skins = M.geoStats.skins + 1
  sinceChange = stopwatch.new()
  return true
end

-- A geotile's old skin objects go (all, or only part what: its new one is made).
function M.dropOldSkin(t, what)
  if not t.oldSkin then return end
  local function drop(w)
    if t.oldSkin[w] then deleteQ[#deleteQ + 1] = t.oldSkin[w]; t.oldSkin[w] = nil; M.geoStats.skinSwaps = M.geoStats.skinSwaps + 1 end
    if t.oldSkin['s:' .. w] then slotDrop(t.oldSkin['s:' .. w]); t.oldSkin['s:' .. w] = nil end
  end
  if what then drop(what) else for _, w in ipairs(M.SKIN_WHATS) do drop(w) end end
  if next(t.oldSkin) == nil then t.oldSkin = nil end
end

-- Server message `roads_exact` {anchorId, key, parts {what: path | false}, slots}: parts shown as their exact variant
-- for this anchor (false: the base shape again), each swapped once its new object is made.
function M.onExact(msg, currentAnchor, admitted)
  if not admitted then return M._admit(M.onExact,msg,currentAnchor,true) end
  local t = tiles[geoKey(msg.key)]
  if t and t.retireRequested then releaseSlots(messageSlots(msg));return false end
  local candidate,transaction=M._handover('route',geoKey(msg.key),msg.contentHash)
  if candidate then
    if transaction.phase=='awaitFrame' or transaction.phase=='rebaseWait' then
      releaseSlots(transaction.exactSlots,msg);transaction.exactMsg=msg;transaction.exactSlots=messageSlots(msg)
      return true
    end
    t=candidate
  end
  if not t or msg.anchorId ~= currentAnchor or type(msg.parts) ~= 'table' then
    if type(msg.slots) == 'table' then for w in pairs(msg.slots) do slotDrop(msgSlot(msg, w)) end end
    return false
  end
  local count=0
  for what,path in pairs(msg.parts) do
    count=count+1
    if count>4096 or type(what)~='string' or (path~=false and (type(path)~='string' or #path==0 or #path>4096)) then
      releaseSlots(messageSlots(msg));return false
    end
  end
  if t.pendingGeo then
    local p=t.pendingGeo
    if msg.contentHash~=p.msg.h then releaseSlots(messageSlots(msg));return false end
    releaseSlots(p.exactSlots,msg)
    p.exactMsg=msg;p.exactSlots=messageSlots(msg)
    return true
  end
  if t.physicalReplacement and t.physicalReplacement.kind~='patch' then releaseSlots(messageSlots(msg));return false end
  if (sectorManifestRequired and msg.contentHash==nil) or (msg.contentHash and msg.contentHash~=t.h) then
    releaseSlots(messageSlots(msg));return false
  end
  if not t.staged then
    local live=t.physicalReplacement~=nil
    for what in pairs(msg.parts) do if t.parts[what] and t[what] then live=true end end
    if live then return M._handover('patch',geoKey(msg.key),'exact',msg,nil,currentAnchor,anchorObj) end
  end
  for what, path in pairs(msg.parts) do
    if t.parts[what] then
      local sl = msgSlot(msg, what)
      if t.slots['x:' .. what] then
        if t[what] then
          t.oldPartSlot=t.oldPartSlot or {};slotDrop(t.oldPartSlot[what]);t.oldPartSlot[what]=t.slots['x:'..what]
        else slotDrop(t.slots['x:'..what]) end
      end
      t.slots['x:' .. what] = sl
      if path then
        t.exactShape[what] = sl and sl.path or path
        t.exactOf[what] = msg.anchorId
        M.geoStats.exact = M.geoStats.exact + 1
      else
        t.exactShape[what], t.exactOf[what] = nil, nil
        M.geoStats.exactBase = M.geoStats.exactBase + 1
      end
      if t[what] then         -- made: the new shape made beside it, the old one deleted then (update)
        t.oldPart = t.oldPart or {}
        if t.oldPart[what] then deleteQ[#deleteQ + 1] = t.oldPart[what] end
        t.oldPart[what] = t[what]
        t[what] = nil
        if t.cq then t.cq[what] = nil end
        local keep = {}
        for _, q in ipairs(walkQ) do if not (q.tile == t and q.what == what) then keep[#keep + 1] = q end end
        walkQ = keep
        local lean = t.leanBuildings or t.parts.bldcol ~= nil
        local q = { key = t.staged and t.staged.key or geoKey(msg.key), what = what, tile = t, geo = true, swap = true,
          renderOnly = what == 'wire' or (lean and buildingVisual(what))
            or ((t.leanRails or t.parts.railcol ~= nil) and what == 'rail') }
        walkQ[#walkQ + 1] = q
      end
    end
  end
  sinceChange = stopwatch.new()
  M._fileSessions(t)
  return true
end

-- A complete body retransmission still carries the current anchor's precision
-- choices. Equal content hashes must not suppress these independent products.
function M._incomingExact(t,msg,aid)
  local parts,slots={},{}
  for what,path in pairs(msg.exact or {}) do
    parts[what]=path;slots[what]=msg.slots and msg.slots['x:'..what]
  end
  for what in pairs(t.exactShape or {}) do if not (msg.exact and msg.exact[what]) then parts[what]=false end end
  for _,inputs in ipairs({(t.physicalReplacement and t.physicalReplacement.patchInputs) or {},(t.pendingPatch and t.pendingPatch.inputs) or {}}) do
    for what in pairs(inputs.exact and inputs.exact.parts or {}) do
      if not (msg.exact and msg.exact[what]) then parts[what]=false end
    end
  end
  if next(parts) then M.onExact({anchorId=aid,key=t.gkey,contentHash=t.h,parts=parts,slots=slots},aid) end
end

-- A rebase / teleport near (core.lua): every geotile placed into anchor a (aid): its made parts moved (setPosRot),
-- its rows mapped again for their modules, its skin moved and lifted until the new anchor's comes (onSkin). Returns
-- the tiles moved.
function M.replace(a, aid)
  if not a then return 0 end
  buildingFade:finish()
  M._handover('rebase')
  anchorObj = a
  buildingProgress:place(a)
  local n = 0
  for key, t in pairs(tiles) do
    if t.geo then
      if t.pendingGeo and t.pendingGeo.anchor~=aid then releasePending(t) end
      if t.pendingPatch and t.pendingPatch.aid~=aid then M._releasePatch(t);M._handover('resync') end
      t.anchor = aid
      M.placeGeoTile(t, a)
      if t.buildingFallback then
        local f=t.buildingFallback;M.placeGeoTile(f,a)
        for what in pairs(f.parts) do
          local w=M.geoWalk(f,what);local o=f[what] and scenetree.findObjectById(f[what])
          if o then o:setPosRot(w.pos[1],w.pos[2],w.pos[3],unpack(w.rot)) end
        end
      end
      for what, pp in pairs(t.pls) do
        local p = t.parts[what]
        local x, y, z = pp.xf:apply(p.pos[1], p.pos[2], p.pos[3])
        for _, id in ipairs({ t[what], t.oldPart and t.oldPart[what] or false }) do
          local o = id and scenetree.findObjectById(id)
          if o then o:setPosRot(x, y, z, pp.q[1], pp.q[2], pp.q[3], pp.q[4]) end
        end
      end
      -- the skin (its anchor's world): moved rigidly at its pivot into this one, lifted over the new block's quantum
      local sk = t.skin
      if sk and sk.anchorObj and sk.anchor ~= aid then
        local pv = sk.pivot
        local xf = sk.anchorObj:worldTransformTo(a, pv[1], pv[2], pv[3])
        local qx, qy, qz, qw = xf:beamngQuat()
        local lift = (sk.q or 0) / 2 + M.SKIN_LIFT_M
        local occupancyXf=geodesy.transformOf(xf.r,{xf.t[1],xf.t[2],xf.t[3]+lift})
        sk.occupancyInv=occupancyXf:inverse()
        for _, w in ipairs(M.SKIN_WHATS) do
          local e = sk[w]
          local o = e and t[w] and scenetree.findObjectById(t[w])
          if o then
            local x, y, z = xf:apply(e.pos[1], e.pos[2], e.pos[3])
            o:setPosRot(x, y, z + lift, qx, qy, qz, qw)
          end
        end
        for _, id in ipairs(t.objs) do deleteQ[#deleteQ + 1] = id end      -- (DecalRoads cannot turn)
        t.objs, t.queued = {}, 0
        sk.stale = true
      end
      if t.data and not t.staged then geoRows(key, t, t.data, true) end
      n = n + 1
    end
  end
  -- the far geotiles: their made parts moved (their lamps are trees.lua geotiles: placed by trees.transform / reanchor)
  for _, f in pairs(far) do
    if f.geo then
      f.anchor = aid
      if f.previous then
        for _,p in pairs(f.previous.parts) do
          M._farPartPlace(f.previous,p,a)
          local o=p.id and scenetree.findObjectById(p.id)
          if o then o:setPosRot(p.at[1],p.at[2],p.at[3],unpack(p.rot)) end
        end
      end
      for _, p in pairs(f.parts) do
        M._farPartPlace(f, p, a)          -- (defined below, with the far geotiles)
        local o = p.id and scenetree.findObjectById(p.id)
        if o then o:setPosRot(p.at[1], p.at[2], p.at[3], p.rot[1], p.rot[2], p.rot[3], p.rot[4]) end
      end
      M.geoStats.farReplaced = (M.geoStats.farReplaced or 0) + 1
    end
  end
  -- queued entries of the skins of other anchors go (their positions are those anchors')
  local function keep(list)
    local out = {}
    for _, q in ipairs(list) do
      if not (q.skin and q.tile and q.tile.skin and q.tile.skin.anchor ~= aid) then out[#out + 1] = q end
    end
    return out
  end
  walkQ, parked, held, createQ = keep(walkQ), keep(parked), keep(held), keep(createQ)
  if n > 0 then collisionDirty = true; sinceChange = stopwatch.new() end
  M.geoStats.replaced = M.geoStats.replaced + n
  return n
end

-- The geotile keys whose quads in the current anchor's world come within r of (x, y).
function M.geoKeysNear(x, y, r)
  local a = anchorObj
  if not a then return {} end
  local la, lo = a:worldToGeodetic(x, y, 0)
  local kx, ky = geotile.tileOf(la, lo)
  local side = 40075016.686 * math.max(math.cos(math.rad(la)), 0.01) / 2 ^ geotile.Z
  local rings = math.ceil(r / side) + 1
  local out = {}
  for dy = -rings, rings do
    for dx = -rings, rings do
      local gx, gy = kx + dx, ky + dy
      if geotile.quadDist(geotile.quad(a, geotile.Z, gx, gy), x, y) <= r then
        out[#out + 1] = geotile.key(gx, gy)
      end
    end
  end
  return out
end

-- The geotile under (x, y) of the current anchor's world, or nil.
function M.geoKeyAt(x, y)
  local a = anchorObj
  if not a then return nil end
  local la, lo = a:worldToGeodetic(x, y, 0)
  return geotile.key(geotile.tileOf(la, lo))
end

-- Is geotile t made for anchor aid: its content's colliding parts made (busy: tile keys with meshes queued), its skin
-- this anchor's and made?
local function geoMade(t, aid, busy)
  if not t or not t.geo or busy[geoKey(t.gkey)] then return false end
  if M._physicalPending(t) then return false end
  if not t.skin or t.skin.anchor ~= aid or t.skin.pending > 0 or t.queued > 0 then return false end
  return true
end
M._geoMade = geoMade

-- Server message `roads_tile` {anchorId, key, path, n, data (the file's JSON, optional), slots}. A geotile key
-- (geotile.lua): onGeoTile (a: the current anchor, geodesy).
function M.onTile(msg, currentAnchor, a, admitted)
  if not admitted then return M._admit(M.onTile,msg,currentAnchor,a,true) end
  if not M.enabled then return false end
  switchAnchor(currentAnchor)
  if geotile.isKey(msg.key) then return M.onGeoTile(msg, currentAnchor, a) end
  if msg.anchorId ~= currentAnchor then return false end
  local key = tileKey(msg.anchorId, msg.key)
  -- the file's JSON in the message (server staging.inline_json: Windows' first read of a file the server just wrote took
  -- up to 0.5 s in the frame), else the file
  local ok, data = true, msg.data
  if type(data) ~= 'table' then ok, data = pcall(jsonDecode, readFile(msg.path) or '') end
  if not ok or type(data) ~= 'table' or type(data.chunks) ~= 'table' or not validBuildingChunks(data) then
    lastError = 'unreadable road tile ' .. tostring(msg.path)
    return false
  end
  if tiles[key] then
    if M.occupied(tiles[key]) then return M._holdReplacement(tiles[key],msg,data,currentAnchor) end
    dropTile(key,false,true)
  end
  -- pooled shape files: the server's slot paths instead of the tile's own files
  local slots = {}
  for _, what in ipairs(meshWhats({ 'road', 'deck', 'walk', 'walkcol', 'bld', 'bld2', 'bld3', 'bld4', 'bldcol', 'wire', 'tunnel', 'rail',
      'railcol', 'exits', 'mileposts', 'merges', 'speeds' }, data)) do
    local sl = msgSlot(msg, what)
    if sl then
      if type(data[what]) == 'table' and type(data[what].pos) == 'table' then
        data[what] = { shape = sl.path, pos = data[what].pos }
        slots[what] = sl
      else
        slotDrop(sl)                -- nothing will load it
      end
    end
  end
  local road = type(data.road) == 'table' and data.road.shape and type(data.road.pos) == 'table' and data.road
  tiles[key] = { anchor = msg.anchorId, objs = {}, queued = road and 0 or #data.chunks,
    colliders = type(data.colliders) == 'table' and data.colliders or {}, slots = slots, at = now(), colWant = {}, data = data }
  tiles[key].fileSessions={}
  for _,e in pairs(data) do
    local s=type(e)=='table' and type(e.shape)=='string' and e.shape:match('^/temp/beamngEarth/([^/]+)/')
    if s then tiles[key].fileSessions[s]=true end
  end
  installVegetationExclusions(key,tiles[key],data)
  sinceChange = stopwatch.new()
  if road then                -- the tile's road mesh replaces its DecalRoads (server/roadmesh.py)
    walkQ[#walkQ + 1] = { key = key, walk = road, what = 'road', tile = tiles[key] }
  else
    for _, c in ipairs(data.chunks) do createQ[#createQ + 1] = { key = key, chunk = c } end
  end
  if type(data.props) == 'table' and type(data.props.items) == 'table' then   -- street lights, poles (trees.lua)
    require('beamngEarth/trees').onRows(msg.anchorId, 'p' .. tostring(msg.key), data.props.items, data.props.groups, nil, key)
    require('beamngEarth/nightlights').onRows(key, data.props.items, data.props.groups)   -- (the lamps' light)
    tiles[key].props = true
  end
  if type(data.guardrails) == 'table' and type(data.guardrails.items) == 'table' and #data.guardrails.items > 0 then
    require('beamngEarth/trees').onRows(msg.anchorId, 'g' .. tostring(msg.key),
      data.guardrails.items, data.guardrails.groups, 17)
    tiles[key].guardrails = true
    tiles[key].guardrailRows = #data.guardrails.items
  end
  if type(data.park) == 'table' and data.park[1] then      -- curbside parking spots (parking.lua)
    require('beamngEarth/parking').onRows(msg.anchorId, key, data.park)
    tiles[key].park = true
  end
  if type(data.fuel) == 'table' and data.fuel[1] then      -- gas stations: pumps, refuel areas (gasstations.lua)
    require('beamngEarth/gasstations').onRows(msg.anchorId, key, data.fuel)
    tiles[key].fuel = true
  end
  if type(data.wells) == 'table' and data.wells[1] then    -- oil wells' pump jacks (pumpjacks.lua)
    require('beamngEarth/pumpjacks').onRows(key, data.wells)
    tiles[key].wells = true
  end
  if type(data.sound) == 'table' and data.sound[1] then    -- tunnels' and bridges' sound spaces (ambience.lua)
    require('beamngEarth/ambience').onSpaces(key, data.sound)
    tiles[key].sound = true
  end
  if type(data.wire) == 'table' and data.wire.shape and type(data.wire.pos) == 'table' then    -- pole wires
    walkQ[#walkQ + 1] = { key = key, walk = data.wire, what = 'wire', tile = tiles[key] }
  end
  -- a sign tile (key "s<tx>_<ty>"): its render-only sign shapes, kept in signData for setSignsEnabled
  tiles[key].signOnly = tostring(msg.key):match('^s%-?%d+_') ~= nil
  tiles[key].signData = {}
  for _, what in ipairs(M.SIGN_WHATS) do
    local sign = data[what]
    if type(sign) == 'table' and sign.shape and type(sign.pos) == 'table' then
      tiles[key].signData[what] = sign
      if M.signsEnabled then
        walkQ[#walkQ + 1] = { key = key, walk = sign, what = what, tile = tiles[key], renderOnly = true }
      end
    end
  end
  -- sidewalks, bridge decks, buildings (split in parts under the engine's 16-bit index limit), the buildings'
  -- lean collision mesh: colliders only near the car (M.COLLIDE_M); with a bldcol the drawn buildings only render
  local tx, ty = tostring(msg.key):match('^s?(%-?%d+)_(%-?%d+)$')
  tiles[key].cx = tx and (tonumber(tx) + 0.5) * M.TILE_M or nil
  tiles[key].cy = ty and (tonumber(ty) + 0.5) * M.TILE_M or nil
  -- a lean collision mesh ("bldcol", "walkcol", "railcol": server cdae collision_only) makes the drawn ones render-only
  -- (railcol: the track's bed and decks without its rails and sleepers, server railways.collision_mesh; mpsteppe's, from
  -- Madderose's PR #41)
  local lean = type(data.bldcol) == 'table' and data.bldcol.shape ~= nil
  local leanWalk = type(data.walkcol) == 'table' and data.walkcol.shape ~= nil
  local leanRail = type(data.railcol) == 'table' and data.railcol.shape ~= nil
  -- tunnels (server roadmesh.tunnel: tubes and portals) and railway tracks (server railways.py) collide like the decks
  for _, what in ipairs(meshWhats({ 'walk', 'deck', 'bld', 'bld2', 'bld3', 'bld4', 'bldcol', 'walkcol', 'tunnel', 'rail', 'railcol' }, data)) do
    local w = data[what]
    if type(w) == 'table' and w.shape and type(w.pos) == 'table' then
      local q = { key = key, walk = w, what = what, tile = tiles[key],
        renderOnly = (lean and buildingVisual(what)) or (leanWalk and what == 'walk')
          or (leanRail and what == 'rail') }
      if not q.renderOnly then tiles[key].colWant[what] = true end
      if q.renderOnly or M.collideNear(tiles[key]) then walkQ[#walkQ + 1] = q else parked[#parked + 1] = q end
    end
  end
  return true
end

-- Server message `bldfar_tile` {anchorId, key, path, n}: a far tile's buildings (render-only, the lite mesh);
-- shown only while the road tile of the same square has no building mesh of its own. `bldsky_tile` the same for a
-- skyline tile (server buildings.skyline_tile: SKY_UNIT x SKY_UNIT road tiles, key "ux_uy"), shown only while not all
-- of its squares' far tiles are here (they come as whole groups: no hole while they arrive, none left over after).
M.SKY_UNIT = 4
-- `brfar_tile` (kind 'B'): a far bridge tile's decks (server buildings.far_bridge_tile), shown only while the road
-- tile of the same square has no deck or road mesh of its own.
function M.onFarTile(msg, currentAnchor, kind)
  if kind == true then kind = 'S' end
  local sky = kind == 'S'
  if not M.enabled then return false end
  if geotile.isKey(msg.key) then return M.onFarGeo(msg, currentAnchor, kind) end
  switchAnchor(currentAnchor)
  if msg.anchorId ~= currentAnchor then return false end
  local ok, data = true, msg.data              -- (in the message, else the file: as onTile)
  if type(data) ~= 'table' then ok, data = pcall(jsonDecode, readFile(msg.path) or '') end
  if not ok or type(data) ~= 'table' then lastError = 'unreadable far building tile ' .. tostring(msg.path); return false end
  local key = tileKey(msg.anchorId, (kind or '') .. msg.key)
  if not kind then farSeen[key] = nil end
  local old = far[key]
  if old then farLamps(key, old, false) end
  if old and old.id then deleteQ[#deleteQ + 1] = old.id end
  if old then slotDrop(old.slot) end
  far[key] = nil
  local sl = msgSlot(msg, 'shape')
  if data.shape and type(data.pos) == 'table' then
    local ux, uy = nil, nil
    if sky then ux, uy = string.match(tostring(msg.key), '^(-?%d+)_(-?%d+)$') end
    far[key] = { anchor = msg.anchorId, shape = sl and sl.path or data.shape, pos = data.pos, slot = sl,
                 sky = sky and { tonumber(ux), tonumber(uy) } or nil,
                 deckOf = kind == 'B' and tileKey(msg.anchorId, msg.key) or nil,
                 lamps = type(data.lamps) == 'table' and #data.lamps > 0 and data.lamps or nil }
    M._fileSessions(far[key])
    farQ[#farQ + 1] = key
  else
    slotDrop(sl)
    if not kind then farSeen[key] = true end -- confirmed empty coverage
  end
  return true
end

-- Server message `bldfar_drop` {anchorId, key} (`bldsky_drop` with sky).
function M.onFarDrop(msg, kind)
  if kind == true then kind = 'S' end
  if geotile.isKey(msg.key) then return M.dropFarGeo(M.farGeoKey(kind or 'F', msg.key)) end
  local key = tileKey(msg.anchorId, (kind or '') .. msg.key)
  if not kind then farSeen[key] = nil end
  local f = far[key]
  if f and f.ghost then return end
  if f then farLamps(key, f, false) end
  if f and f.id then deleteQ[#deleteQ + 1] = f.id end
  if f then slotDrop(f.slot) end
  far[key] = nil
end

-- A far tile is hidden while its square's road tile shows buildings (they are the same, colliding).
-- Pure: are all the far tiles of skyline square (ux, uy) of anchor aid here (seen: key -> true)?
function M.skyCovered(seen, aid, ux, uy)
  local n = M.SKY_UNIT
  for i = 0, n - 1 do
    for j = 0, n - 1 do
      if not seen[tileKey(aid, (ux * n + i) .. '_' .. (uy * n + j))] then return false end
    end
  end
  return true
end

-- Road geotiles (M.geo): a far tile's 256 m square (key "a:[B]tx_ty") is the road tiles' when every geotile within its
-- reach has its content here (buildings made, or none; decks: its deck made or none, and its skin's road mesh), the
-- keys found once per far tile (its anchor's world). With anchor far tiles (a server without hello.farGeo) a square at
-- the road tiles' edge shows its far buildings over the geotiles it overlaps; far geotiles (below) have no such seam.
local function geoSquareCovered(f, sq, deck)
  if not f.geoKeys then
    local tx, ty = tostring(sq):match('(%-?%d+)_(%-?%d+)$')
    if not tx or not anchorObj then return false end
    f.geoKeys = M.geoKeysNear((tonumber(tx) + 0.5) * M.TILE_M, (tonumber(ty) + 0.5) * M.TILE_M, M.TILE_M * 0.5)
  end
  if #f.geoKeys == 0 then return false end
  for _, k in ipairs(f.geoKeys) do
    local t = tiles[geoKey(k)]
    if not t then return false end
    if deck then
      if (t.parts.deck and not t.deck) or not t.road then return false end
    elseif t.parts.bld and not t.bld then
      return false
    end
  end
  return true
end

-- Far geotiles (server hello.farGeo == M.FAR_GEO: blockworker.far_geo; .claude/work/geotiles_plan.md phase 2): the far
-- buildings (kind 'F', key 'g17_x_y': the road geotiles' own grid), the skyline ('S', 'g15_x_y': 4 x 4 of them) and
-- the far bridges ('B', 'g15_x_y': a piece per road geotile under it), each made once in its tile's frame and kept
-- across rebases and teleports near: M.replace places its parts rigidly at their pivots into the new anchor (render-
-- only, nothing made again). One ownership rule by geotile key: a far buildings tile holds the very buildings the road
-- geotile of its key holds and hides once that one's are made; a far bridge piece hides once its road geotile's deck
-- and road mesh are made; a skyline tile while all 16 far buildings tiles of its square are here. Their street lamps
-- are trees.lua geotiles (one per road geotile key, placed and moved with the trees'), shown while their tile shows.
M.FAR_GEO = 1
M.farGeo = false
function M.setFarGeo(on) M.farGeo = on and true or false end
local function farGeoKey(kind, gkey) return tostring(kind) .. ':' .. tostring(gkey) end
M.farGeoKey = farGeoKey
M.FAR_GEO_ORPHAN_S = 120    -- a far geotile of an old server session not sent again goes after this long

-- A far geotile part's placement into anchor a: its position (p.at) and rotation (p.rot), rigid at its pivot.
local function farPartPlace(f, p, a)
  local pl = geotile.placement(f.frame, a, 0, 0, p.pivot or 0)
  local xf = geodesy.transformOf(pl.r, pl.t)
  local qx, qy, qz, qw = xf:beamngQuat()
  local x, y, z = xf:apply(p.pos[1], p.pos[2], p.pos[3])
  p.at, p.rot = { x, y, z }, { qx, qy, qz, qw }
end
M._farPartPlace = farPartPlace

-- A far geotile's lamps on / off: each road geotile key's rows a trees.lua geotile 'FL<kind><key>' (lampglow).
local function farGeoLamps(f, on)
  on = on and f.lamps ~= nil and anchorObj ~= nil
  if on == (f.lampOn == true) then return end
  local ok, trees = pcall(require, 'beamngEarth/trees')
  if not ok then return end
  f.lampOn = on or nil
  for k17, g in pairs(f.lamps or {}) do
    local tk = 'FL' .. f.kind .. tostring(k17)
    if on then
      local rows = {}
      for i, pt in ipairs(type(g) == 'table' and type(g.rows) == 'table' and g.rows or {}) do
        if type(pt) == 'table' and tonumber(pt[1]) and tonumber(pt[2]) and tonumber(pt[3]) then
          rows[#rows + 1] = { 0, pt[1], pt[2], pt[3], 0, 1, 1, ((i * 7919) % 997) / 997 * 0.19 }
        end
      end
      local fr = geotile.frameOf(k17)
      if #rows > 0 and fr then
        trees.onGeoRows(tk, k17, rows, M.FAR_LAMP_GROUPS, nil, fr, tonumber(g.pivot) or 0, anchorObj)
      end
    else
      trees.dropKey('g:' .. tk)
    end
  end
end

-- A far geotile goes (its objects, slots and lamps).
local function retireFar(f)
  if not f then return end
  farGeoLamps(f,false)
  for _,p in pairs(f.parts) do
    if p.id then hideBuilding(p.id,true);deleteQ[#deleteQ+1]=p.id end
    slotDrop(p.slot)
  end
end

local function farReady(f)
  for _,p in pairs(f.parts) do if not p.id then return false end end
  return true
end

local function finishFarReplacement(f)
  if f.kind=='S' and f.previous then
    -- Children may complete/drop while a parent revision waits for import.
    -- Inherit the old parent's current decision, not its receipt-time state.
    f.skyOwned=f.previous.skyOwned;f.skyYielded=f.previous.skyYielded;f.covered=nil
  end
  retireFar(f.previous);f.previous=nil
end

function M.dropFarGeo(key)
  local f = far[key]
  if not f or not f.geo then return false end
  retireFar(f.previous);retireFar(f)
  if f.kind == 'F' then farSeen[key] = nil end
  far[key] = nil
  if M.refreshBuildingCoverage and f.kind~='B' then
    if f.kind=='S' then
      for _,child in ipairs(f.skyKeys or (f.previous and f.previous.skyKeys) or {}) do M.refreshBuildingCoverage(child:sub(3)) end
    else M.refreshBuildingCoverage(f.gkey) end
  end
  return true
end

-- Server messages `bldfar_tile` / `bldsky_tile` / `brfar_tile` with a geotile key (kind nil / 'S' / 'B'): {key, frame,
-- path / data {shape, pos, pivot, lamps {key: {pivot, rows}}; brfar: parts {key: {shape, pos, pivot}}, h}, slots}.
-- The same content again (h: a server restart, a tile dropped and wanted again) keeps its objects.
function M.onFarGeo(msg, currentAnchor, kind)
  local k = kind or 'F'
  local function release(keep)
    if type(msg.slots) == 'table' then
      for w in pairs(msg.slots) do if not (keep and keep[w]) then slotDrop(msgSlot(msg, w)) end end
    end
  end
  local ok, data = true, msg.data
  if type(data) ~= 'table' then ok, data = pcall(jsonDecode, readFile(msg.path) or '') end
  if not ok or type(data) ~= 'table' then
    release()
    lastError = 'unreadable far geotile ' .. tostring(msg.path)
    return false
  end
  local key = farGeoKey(k, msg.key)
  local old = far[key]
  local h = data.h
  if old and old.geo and h ~= nil and old.h == h and not filesGone(old.parts) then
    release()
    old.orphan, old.anchor = nil, currentAnchor
    M.geoStats.farKept = (M.geoStats.farKept or 0) + 1
    return true
  end
  local frame = geotile.frameOf({ frame = msg.frame or data.frame, key = msg.key })
  if not frame then release(); lastError = 'far geotile without a frame: ' .. tostring(msg.key); return false end
  if k~='B' and data.shape~=nil and (type(data.shape)~='string' or type(data.pos)~='table'
    or type(data.pos[1])~='number' or type(data.pos[2])~='number' or type(data.pos[3])~='number') then
    release();lastError='invalid far building shape';return false
  end
  local previous
  if old then
    if old.geo and k~='B' then
      if old.previous then previous=old.previous;retireFar(old)
      elseif farReady(old) then previous=old
      else retireFar(old) end
      -- Stale queue entries identify only key/sub, so discard them before
      -- queuing a replacement with the same identity.
      local keep={};for _,q in ipairs(farQ) do
        if q:sub(1,#key+1)~=key..'#' then keep[#keep+1]=q end
      end;farQ=keep
    elseif old.geo then M.dropFarGeo(key) else far[key]=nil end
  end
  local f = { geo = true, kind = k, gkey = msg.key, frame = frame, h = h, anchor = currentAnchor, parts = {},
    previous=previous,lamps = type(data.lamps) == 'table' and next(data.lamps) ~= nil and data.lamps or nil }
  if k == 'S' then
    local z, x, y = geotile.parse(msg.key)
    f.sky = { z, x, y }
  end
  local list = {}
  if k == 'B' then
    for sub, e in pairs(type(data.parts) == 'table' and data.parts or {}) do list[#list + 1] = { sub, e } end
    table.sort(list, function(a, b) return tostring(a[1]) < tostring(b[1]) end)
  elseif type(data.shape) == 'string' then
    list[1] = { 'shape', { shape = data.shape, pos = data.pos, pivot = data.pivot } }
  end
  local used = {}
  for _, it in ipairs(list) do
    local sub, e = it[1], it[2]
    if type(e) == 'table' and type(e.shape) == 'string' and type(e.pos) == 'table' then
      local sl = msgSlot(msg, sub)
      used[sub] = true
      -- (near: the road geotile whose own content shows these buildings / this deck)
      local p = { shape = sl and sl.path or e.shape, slot = sl, pos = e.pos, pivot = tonumber(e.pivot) or 0,
        near = (k == 'B' and sub) or (k == 'F' and msg.key) or nil }
      if anchorObj then farPartPlace(f, p, anchorObj) end
      f.parts[sub] = p
      farQ[#farQ + 1] = key .. '#' .. sub
    end
  end
  release(used)
  M._fileSessions(f)
  far[key] = f
  if farReady(f) then finishFarReplacement(f) end
  if k=='F' then farSeen[key]=(farReady(f) or f.previous~=nil) or nil end
  if k~='B' then M.refreshBuildingCoverage(f.gkey) end
  M.geoStats.far = (M.geoStats.far or 0) + 1
  return true
end

-- Is road geotile gkey showing its own buildings (every building mesh of its content made; none: it has none)?
-- (tk: its key in tiles, 'g:' .. gkey, when the caller has it: the far geotiles ask every frame)
local BLD_WHATS = { 'bld', 'bld2', 'bld3', 'bld4' }
function M.nearShowsBuildings(gkey, tk)
  if buildingProgress:covers(gkey) then return true end
  local t = tiles[tk or geoKey(gkey)]
  if not t or not t.geo then return false end
  if t.buildingFallback then return true end
  for _, what in ipairs(t.data and t.data.buildingChunks and t.data.buildingChunks.visual or BLD_WHATS) do
    if t.parts[what] and not t[what] and not (t.oldPart and t.oldPart[what]) then return false end
  end
  return true
end

-- ... its own deck (made, or none) and road surface (its skin's road mesh made, or a skin without one)?
function M.nearShowsDeck(gkey, tk)
  local t = tiles[tk or geoKey(gkey)]
  if not t or not t.geo then return false end
  if t.parts.deck and not t.deck then return false end
  if t.road then return true end
  return t.skin ~= nil and t.skin.road == nil and (t.skin.pending or 0) <= 0
end

local function finerBuildingsReady(key)
  local f=far[farGeoKey('F',key)]
  if f and f.previous then f=f.previous end
  if f then for _,p in pairs(f.parts) do if p.id then return true end end end
  if buildingProgress:hasDetail(key) then return true end
  local t=tiles[geoKey(key)]
  if t and t.buildingFallback then
    for what in pairs(t.buildingFallback.parts) do if t.buildingFallback[what] then return true end end
  end
  if t and ownBuildingsReady(t) then
    for what in pairs(t.parts) do if buildingVisual(what) and t[what] then return true end end
  end
  return false
end

-- Is far geotile f's part sub hidden now (the ownership rule above)?
function M.farGeoHidden(f, sub)
  if f.kind == 'S' then
    if f.covered~=nil then return f.covered end
    if not f.skyKeys then           -- (its square's far buildings tiles' keys, once)
      local z, x, y = f.sky[1], f.sky[2], f.sky[3]
      if not z then return false end
      local n = 2 ^ (geotile.Z - z)
      f.skyKeys = {}
      for j = 0, n - 1 do
        for i = 0, n - 1 do f.skyKeys[#f.skyKeys + 1] = farGeoKey('F', geotile.key(x * n + i, y * n + j, geotile.Z)) end
      end
    end
    local complete,finer=true,false
    for _, k in ipairs(f.skyKeys) do
      if not farSeen[k] and not M.nearShowsBuildings(k:sub(3)) then complete=false end
      if finerBuildingsReady(k:sub(3)) then finer=true end
    end
    -- A skyline is indivisible. If it arrived first, keep its atomic 16-child
    -- handoff. If finer children arrived first (or this parent already yielded),
    -- never cover them again just because a sibling is still missing/dropped.
    if complete or (finer and (f.skyYielded or not f.skyOwned)) then
      f.skyYielded=true;f.skyOwned=nil;f.covered=true
    else
      f.skyYielded=nil;f.covered=false
      if farReady(f) then f.skyOwned=true end
    end
    return f.covered
  end
  local p = f.parts[sub]
  if not p or not p.near then return false end
  p.nearKey = p.nearKey or geoKey(p.near)
  if f.kind == 'B' then return M.nearShowsDeck(p.near, p.nearKey) end
  return M.nearShowsBuildings(p.near, p.nearKey) or M.skyBlocksBuildings(p.near)
end

local function skylineFor(key)
  local z,x,y=geotile.parse(key)
  if not z then return nil end
  local f
  if z==15 then f=far[farGeoKey('S',key)]
  elseif z==geotile.Z then f=far[farGeoKey('S',geotile.key(math.floor(x/4),math.floor(y/4),15))] end
  return f and (not farReady(f) and f.previous or f)
end

function M.skyBlocksBuildings(key)
  local f=skylineFor(key)
  if not f or not next(f.parts) then return false end
  for _,p in pairs(f.parts) do if not p.id then return false end end
  return not M.farGeoHidden(f)
end

local function updateFarGeo(key, f)
  if f.previous then f=f.previous end
  local shown = false
  for sub, p in pairs(f.parts) do
    if p.id then
      local hide = M.farGeoHidden(f, sub)
      if hide ~= (p.hidden or false) then
        local o = scenetree.findObjectById(p.id)
        if o then hideBuilding(p.id,hide) end
        p.hidden = hide
      end
      if not hide then shown = true end
    end
  end
  if f.lamps then farGeoLamps(f, shown) end
end

-- Coverage changes are applied in their completion/drop frame, independently
-- of the round-robin maintenance scan. A skyline's 16 children form one atomic
-- coverage group: no early parent retirement, no coplanar partial overlap.
function M.refreshBuildingCoverage(key)
  local current=tiles[geoKey(key)]
  if current and ownBuildingsReady(current) then dropBuildingFallback(current) end
  local sky=skylineFor(key)
  local keys={farGeoKey('F',key)}
  if sky then
    -- Coverage changes only on import, cancellation, replacement or drop. Avoid
    -- re-scanning 16 children for every far object in the frame maintenance loop.
    sky.covered=nil
    M.farGeoHidden(sky) -- also establishes children for a confirmed empty skyline
    updateFarGeo(farGeoKey('S',sky.gkey),sky)
    keys=sky.skyKeys or keys
  end
  for _,fk in ipairs(keys) do
    local f=far[fk]
    if f then updateFarGeo(fk,f) end
    local gkey=fk:sub(3)
    local t=tiles[geoKey(gkey)]
    if t and t.buildingFallback then
      for what in pairs(t.buildingFallback.parts) do
        hideBuilding(t.buildingFallback[what],M.skyBlocksBuildings(gkey))
      end
    end
    if buildingProgress.entries[gkey] then buildingProgress:visibility(gkey,true)
    else
      local t=tiles[geoKey(gkey)]
      if t then
        local hidden=M.skyBlocksBuildings(gkey) or (not ownBuildingsReady(t)
          and (t.buildingFallback~=nil or buildingProgress.api.farVisible(gkey)))
        for what in pairs(t.parts) do if buildingVisual(what) and t[what] then
          hideBuilding(t[what],hidden)
        end end
      end
    end
  end
end

-- The far tiles' hide checks, round-robin: at most FAR_CHECKS_PER_FRAME a frame (all ~600 of them every frame cost
-- ~0.85 ms of every frame while driving, 2026-10-29; a far building shown or hidden a few frames later is not seen)
M.FAR_CHECKS_PER_FRAME = 80
local farCursor = nil
local function updateFarOne(key, f)
    if f.geo then
      updateFarGeo(key, f)
    elseif f.id then
      local hide
      if f.sky then
        hide = M.skyCovered(farSeen, f.anchor, f.sky[1], f.sky[2])
      elseif f.deckOf and M.geo then      -- (a ghost: as it was, its square is another anchor's)
        hide = f.ghost and (f.hidden or false) or geoSquareCovered(f, f.deckOf, true)
      elseif f.deckOf then
        local t = tiles[f.deckOf]
        hide = t ~= nil and (t.deck ~= nil or t.road ~= nil)
      elseif M.geo then
        hide = f.ghost and (f.hidden or false) or geoSquareCovered(f, key, false)
      else
        hide = tiles[key] ~= nil and tiles[key].bld ~= nil
      end
      if hide ~= (f.hidden or false) then
        local o = scenetree.findObjectById(f.id)
        if o then hideBuilding(f.id,hide) end
        f.hidden = hide
      end
    end
    if f.lamps and not f.geo then farLamps(key, f, f.id ~= nil and not f.hidden) end
end
local function updateFar(gov, importOnly)
  if not importOnly then
  if farCursor ~= nil and far[farCursor] == nil then farCursor = nil end     -- (gone: next() cannot go on from it)
  local key, f = next(far, farCursor)
  local wrapped = farCursor == nil
  for _ = 1, M.FAR_CHECKS_PER_FRAME do
    if key == nil then
      farCursor = nil
      if wrapped then break end
      wrapped = true
      key, f = next(far)
      if key == nil then break end
    end
    updateFarOne(key, f)
    farCursor = key
    key, f = next(far, key)
  end
  end
  while #farQ > 0 and (importOnly or #walkQ == 0) and not deferImports and importsThisFrame < M.MAX_IMPORTS_PER_FRAME and gov:try('roadWalk') do
    local key = table.remove(farQ, 1)
    local gk, sub = key:match('^(.-)#(.*)$')
    local f = far[gk or key]
    local p = f and f.geo and sub and f.parts[sub]
    if p and not p.id and anchorObj then        -- (a far geotile's part: placed as its tile is now)
      local t0 = now()
      loadMaterials()
      farPartPlace(f, p, anchorObj)
      importsThisFrame = importsThisFrame + 1
      local ok, id = pcall(createWalk, { shape = p.shape, pos = p.at, rot = p.rot, buildingFade=f.kind~='B' }, false)
      if ok and id then
        p.id = id
        slotMade(id, p.shape)
        if farReady(f) then finishFarReplacement(f) end
        p.hidden = M.farGeoHidden(f, sub)
        hideBuilding(id,p.hidden)
        if f.kind=='F' then farSeen[gk]=true end
        if f.kind~='B' then M.refreshBuildingCoverage(f.gkey) end
      else lastError = tostring(id) end
      local ms = now() - t0
      gov:charge('roadWalk', ms)
      noteUnit('far' .. f.kind, ms, p.shape)
    elseif f and not f.geo and not f.id then
      local t0 = now()
      loadMaterials()
      importsThisFrame = importsThisFrame + 1
      local ok, id = pcall(createWalk, { shape = f.shape, pos = f.pos, buildingFade=true }, false)
      if ok and id then
        f.id = id; slotMade(id, f.shape)
        if not f.sky and not f.deckOf then farSeen[key]=true end
        updateFarOne(key,f)
      else lastError = tostring(id) end
      local ms = now() - t0
      gov:charge('roadWalk', ms)
      noteUnit('bldfar', ms, f.shape)
    end
  end
end

-- Server message `roads_drop` {anchorId, key}. (A ghost goes when covered: releaseGhosts.)
function M.onDrop(msg)
  local key = geotile.isKey(msg.key) and geoKey(msg.key) or tileKey(msg.anchorId, msg.key)   -- (a geotile: any anchor's)
  local t = tiles[key]
  if t and t.ghost then return end
  dropTile(key)
  sinceChange = stopwatch.new()
end

-- A gas station's colliding props were made (gasstations.lua): rebuilt with the roads' next collision rebuild.
function M.markCollisionDirty() collisionDirty = true end

-- Origin rebase (core.lua finishRebase): the shown tiles move into the new frame (p_new = R*p + t: their TSStatics
-- turned by R, as farfield.transform) and stay as "ghosts" until the new anchor's tiles over them are made
-- (ghostsCovered). Before (2026-10-17, forced rebase at Fells Point) every building, road mesh and sidewalk went at
-- once and came back over ~26 s as the server re-sent the tiles. DecalRoads (no rotation) and anything still queued go
-- now: their positions are the old frame's. A ghost's colliders are not made again (updateCollideRange).
M.GHOST_MAX_S = 120         -- ghosts left after this long go anyway
M.GHOST_FAR_M = 960         -- ... and once farther from the player than this (the server's roads DROP_M; a disc)
-- Pure: m from (x, y) to the square of half-size h round (cx, cy): to its nearest point (Euclidean, as the server's
-- roads.tile_distance; 0 inside).
function M.boxGap(x, y, cx, cy, h)
  local dx = math.max(math.abs(x - cx) - h, 0)
  local dy = math.max(math.abs(y - cy) - h, 0)
  return math.sqrt(dx * dx + dy * dy)
end
M.GHOST_FAR_WAIT_S = 2      -- ... from this long after the rebase on
local ghostSince = nil      -- stopwatch since the last rebase that left ghosts

local WHATS = { 'walk', 'road', 'deck', 'bld', 'bld2', 'bld3', 'bld4', 'bldcol', 'walkcol', 'wire', 'tunnel', 'rail', 'railcol',
  'exits', 'mileposts', 'merges', 'speeds' }

function M.transform(xf, geodesy)
  local bx, by, bz, bw = xf:beamngQuat()
  local function moveObj(id, q)
    local o = id and scenetree.findObjectById(id)
    if not o then return end
    local p = o:getPosition()
    local x, y, z = xf:apply(p.x, p.y, p.z)
    o:setPosRot(x, y, z, q[1], q[2], q[3], q[4])
  end
  local function newQ(q)
    local x, y, z, w = geodesy.quatMul(q[1], q[2], q[3], q[4], bx, by, bz, bw)
    return { x, y, z, w }
  end
  local any = false
  for key, t in pairs(tiles) do
    if t.geo then goto continue end        -- (placed again by M.replace)
    releasePending(t)
    t.retentionInv=occupancy.rebaseInverse(t.retentionInv,xf)
    t.q = newQ(t.q or { 0, 0, 0, 1 })
    for _, what in ipairs(meshWhats(WHATS, t.data)) do moveObj(t[what], t.q) end
    for _, id in ipairs(t.objs) do deleteQ[#deleteQ + 1] = id end
    t.objs, t.queued, t.cq = {}, 0, nil
    if t.cx then t.cx, t.cy = xf:apply(t.cx, t.cy, 0) end
    local trees=require('beamngEarth/trees')
    if trees.transformSurfaceExclusions then trees.transformSurfaceExclusions('road:'..key,xf) end
    t.ghost = true
    any = true
    ::continue::
  end
  for _, f in pairs(far) do
    if f.id and not f.geo then          -- (far geotiles: placed again by M.replace)
      f.q = newQ(f.q or { 0, 0, 0, 1 })
      moveObj(f.id, f.q)
      f.ghost = true
      any = true
    end
  end
  local function keepNew(list)
    local keep = {}
    for _, q in ipairs(list) do if tiles[q.key] and not tiles[q.key].ghost then keep[#keep + 1] = q end end
    return keep
  end
  walkQ, createQ, parked = keepNew(walkQ), keepNew(createQ), keepNew(parked)
  local fq = {}
  for _, k in ipairs(farQ) do
    local f = far[k:match('^(.-)#') or k]
    if f and not f.ghost then fq[#fq + 1] = k end
  end
  farQ = fq
  if any then ghostSince = stopwatch.new(); sinceChange = stopwatch.new(); collisionDirty = true end
end

-- Is the square of side M.TILE_M around (cx, cy) covered by made tiles of the current anchor (every one of the new
-- grid's squares it overlaps has a tile with nothing queued)?
-- done: the new grid's squares whose tile is made (madeSquares). signs: the sign tiles' squares instead (a sign
-- tile is no road tile: it never covers a road ghost, nor a road tile a sign ghost)
local function madeSquares(aid, busy, signs)
  local n, done = M.TILE_M, {}
  for key, t in pairs(tiles) do
    if t.anchor == aid and not t.ghost and not t.geo and t.cx and (t.signOnly == true) == (signs == true) then
      done[math.floor(t.cx / n) .. '_' .. math.floor(t.cy / n)] = t.queued <= 0 and not busy[key]
    end
  end
  return done
end
-- True once the road tile of anchor aid under (x, y) is made, no other anchor's road (a rebase's ghost too) is near
-- it, and the collision is rebuilt after (core.floorCheck: a ray found the old session's tunnel floor at a teleport's
-- spot, the car went down onto it and fell when that mesh went, 2026-10-17). Must come after madeSquares.
function M.settledFor(aid, x, y)
  if anchorId ~= aid or #deleteQ > 0 or collisionDirty then return false end
  local n = M.TILE_M
  for _, t in pairs(tiles) do
    -- (a sign tile has no collision; a geotile's old skin, moved from another anchor, counts as another's road)
    local other = (not t.geo and (t.anchor ~= aid or t.ghost)) or (t.geo and t.skin and t.skin.anchor ~= aid)
    if not t.signOnly and other then
      if not t.cx or (math.abs(t.cx - x) < 1.5 * n and math.abs(t.cy - y) < 1.5 * n) then return false end
    end
  end
  local busy = {}
  for _, q in ipairs(walkQ) do busy[q.key] = true end
  if M.geo then
    local k = M.geoKeyAt(x, y)
    return k ~= nil and geoMade(tiles[geoKey(k)], aid, busy)
  end
  return madeSquares(aid, busy)[math.floor(x / n) .. '_' .. math.floor(y / n)] == true
end

local covered0
-- (a ghost square is covered by geotiles too: every geotile within its corners' reach made for the anchor)
local function covered(done, cx, cy, busy)
  if covered0(done, cx, cy) then return true end
  if not M.geo or not anchorObj then return false end
  for _, k in ipairs(M.geoKeysNear(cx, cy, M.TILE_M * 0.71)) do
    if not geoMade(tiles[geoKey(k)], anchorId, busy or {}) then return false end
  end
  return true
end
covered0 = function(done, cx, cy)
  local h, n = M.TILE_M / 2, M.TILE_M
  for gx = math.floor((cx - h) / n), math.floor((cx + h - 1e-6) / n) do
    for gy = math.floor((cy - h) / n), math.floor((cy + h - 1e-6) / n) do
      if not done[gx .. '_' .. gy] then return false end
    end
  end
  return true
end

local function releaseGhosts(player)
  if not ghostSince then return end
  local busyKeys = {}
  for _, q in ipairs(walkQ) do busyKeys[q.key] = true end
  local all = ghostSince() > M.GHOST_MAX_S * 1000
  local left = false
  local done = madeSquares(anchorId, busyKeys)
  local signsDone = madeSquares(anchorId, busyKeys, true)
  local p = player             -- core's player (the camera's focus: a test drive's vehicle is not the player's car)
  for key, t in pairs(tiles) do
    if t.ghost then
      -- (not in the rebase's first GHOST_FAR_WAIT_S: in its frame the player is still read in the old frame, every
      -- ghost looked kilometres away and all went: 46 road tiles -> 0 at each rebase, 2026-10-17)
      local far = p and t.cx and ghostSince() > M.GHOST_FAR_WAIT_S * 1000
        and M.boxGap(p.x, p.y, t.cx, t.cy, M.TILE_M / 2) > M.GHOST_FAR_M
      if all or far or (t.cx and (t.signOnly and covered0(signsDone, t.cx, t.cy) or (not t.signOnly and covered(done, t.cx, t.cy, busyKeys)))) then
        if dropTile(key) then
          if not t.signOnly then collisionDirty = true end
        else left=true end
      else left = true end
    end
  end
  for key, f in pairs(far) do
    if f.ghost then
      if all then
        farLamps(key, f, false)
        if f.id then deleteQ[#deleteQ + 1] = f.id end
        slotDrop(f.slot)
        far[key] = nil
      else left = true end
    end
  end
  if not left then ghostSince = nil end
end

-- Once per frame (core onUpdate): deletions, then creations, within the governor's budget.
local viewAt = nil  -- core.viewAway(): the camera's { x, y } when it is away from the car, else nil (M.nextWalk)
local prewarmId, prewarmPath, prewarmWant = nil, nil, nil     -- (the materials' prewarm shape, below)
local prewarmNow

-- The last frame's update in parts (ms; diagnostics: the frame-time probes, 2026-10-29)
M.steps = {}
local stepClock = stopwatch.clock()
local stepT0 = 0
local function step(name)
  local t = stepClock()
  M.steps[name] = t - stepT0
  stepT0 = t
end
local handoverResync=false
function M.takeResync() local wanted=handoverResync;handoverResync=false;return wanted end
function M._tileIds(t)
  local ids,seen={},{}
  local function add(id) if type(id)=='number' and not seen[id] then seen[id]=true;ids[#ids+1]=id end end
  for _,id in ipairs(t.objs or {}) do add(id) end
  for _,what in ipairs(meshWhats({'road','walk','walkcol','deck','bld','bld2','bld3','bld4','bldcol','wire','tunnel','rail','railcol'},t.data)) do add(t[what]) end
  for _,what in ipairs(M.SIGN_WHATS) do add(t[what]) end
  for _,id in pairs(t.oldPart or {}) do add(id) end
  for _,id in pairs(t.oldSkin or {}) do add(id) end
  for what in pairs(t.buildingFallback and t.buildingFallback.parts or {}) do add(t.buildingFallback[what]) end
  return ids
end
function M._releasePatch(t)
  if t.pendingPatch then releaseSlots(t.pendingPatch.tokens);t.pendingPatch=nil end
end
function M._cancelQueued(t) releasePending(t);M._releasePatch(t) end
function M._normalizeExact(t,input,aid)
  if not input then return end
  for w,v in pairs(input.parts) do
    local sl=input.slots and input.slots[w];local old=t.slots['x:'..w]
    local same=old and sl and old.path==sl[1] and old[2]==tonumber(sl[2]) and t.exactOf[w]==aid
    if (v==false and not t.exactShape[w]) or (v~=false and same) then
      input.parts[w]=nil;if input.slots then input.slots[w]=nil end
    end
  end
end
function M._sameExact(a,b)
  if not a or not b then return a==b end
  for _,pair in ipairs({{a,b},{b,a}}) do
    for w,v in pairs(pair[1].parts) do
      local sa,sb=pair[1].slots and pair[1].slots[w],pair[2].slots and pair[2].slots[w]
      if pair[2].parts[w]~=v or (sa==nil)~=(sb==nil) or (sa and (sa[1]~=sb[1] or sa[2]~=sb[2])) then return false end
    end
  end
  return true
end
function M._holdPatch(t,kind,msg,data,aid,r)
  local previous=t.pendingPatch and t.pendingPatch.inputs or
    (r and (r.phase=='loading' or r.phase=='prepared') and r.patchInputs) or {}
  local inputs={};for k,v in pairs(previous) do inputs[k]=v end
  if kind=='skin' then
    local copy={};for k,v in pairs(msg) do copy[k]=v end;copy.data=data;inputs.skin=copy
  else
    local copy={key=msg.key,anchorId=aid,contentHash=msg.contentHash,parts={},slots={}}
    if inputs.exact then
      for w,v in pairs(inputs.exact.parts) do copy.parts[w]=v end
      for w,v in pairs(inputs.exact.slots or {}) do copy.slots[w]=v end
    end
    for w,v in pairs(msg.parts) do copy.parts[w]=v;copy.slots[w]=msg.slots and msg.slots[w] or nil end
    if not r or r.phase=='loading' or r.phase=='prepared' then M._normalizeExact(t,copy,aid) end
    inputs.exact=copy
  end
  if r and (r.phase=='loading' or r.phase=='prepared') and not t.pendingPatch
    and inputs.skin==r.patchInputs.skin and M._sameExact(inputs.exact,r.patchInputs.exact) then return false end
  local p={inputs=inputs,aid=aid,h=t.h,tokens={}}
  local files={parts={}}
  for _,input in pairs(inputs) do for _,sl in ipairs(messageSlots(input)) do p.tokens[#p.tokens+1]=sl end end
  files.skin=inputs.skin and inputs.skin.data
  for w,path in pairs(inputs.exact and inputs.exact.parts or {}) do files.parts[w]={shape=path} end
  M._fileSessions(files);p.fileSessions=files.fileSessions
  M._releasePatch(t);t.pendingPatch=p
end
function M._buildPatch(r,aid,a)
  local old=r.old
  local t={anchor=aid,geo=true,gkey=old.gkey,frame=old.frame,h=old.h,data=old.data,
    objs={},queued=0,colliders={},slots={},parts={},exactShape={},exactOf={},colWant={},at=now(),
    rowPivot=old.rowPivot,staged=r,leanBuildings=old.parts.bldcol~=nil,leanRails=old.parts.railcol~=nil}
  r.tile=t;r.targets={};r.exactTargets={};r.hasSkin=r.patchInputs.skin~=nil;r.needsSkin=r.hasSkin
  tiles[r.key]=t
  local input=r.patchInputs.exact
  for what,path in pairs(input and input.parts or {}) do
    if old.parts[what] then
      local p={};for k,v in pairs(old.parts[what]) do p[k]=v end;t.parts[what]=p
      t.colliders[what]=old.colliders[what];r.targets[what]=true;r.exactTargets[what]=true
      if path~=false then
        local sl=msgSlot(input,what);t.slots['x:'..what]=sl
        t.exactShape[what]=sl and sl.path or path;t.exactOf[what]=aid
      end
    end
  end
  M.placeGeoTile(t,a)
  queueGeoParts(r.key,t,t.data)
  if r.hasSkin then
    for _,w in ipairs(M.SKIN_WHATS) do r.targets[w]=true end
    if not M.onSkin(r.patchInputs.skin,aid,true,t) then return false end
  end
  M._fileSessions(t)
  return true
end
function M._patchOldView(r)
  local selected={}
  for what in pairs(r.targets) do
    if (r.old.retentionColliders and r.old.retentionColliders[what]) or (r.old.cq and r.old.cq[what]) then selected[what]=true end
  end
  return setmetatable({retentionColliders=selected},{__index=r.old})
end
function M._patchOldIds(r)
  local ids,seen={},{}
  local function add(id) if type(id)=='number' and not seen[id] then seen[id]=true;ids[#ids+1]=id end end
  for what in pairs(r.targets) do
    add(r.old[what]);add(r.old.oldPart and r.old.oldPart[what]);add(r.old.oldSkin and r.old.oldSkin[what])
  end
  if r.hasSkin then for _,id in ipairs(r.old.objs) do add(id) end end
  return ids
end
function M._commitPatch(r)
  local old,t=r.old,r.tile
  local function purge(list)
    local keep={}
    for _,q in ipairs(list) do
      if q.tile~=old or not (r.targets[q.what] or (r.hasSkin and q.skin)) then keep[#keep+1]=q end
    end
    return keep
  end
  walkQ,parked,held,createQ=purge(walkQ),purge(parked),purge(held),purge(createQ)
  for _,id in ipairs(M._patchOldIds(r)) do hideBuilding(id,true);deleteQ[#deleteQ+1]=id end
  for what in pairs(r.targets) do
    local prior=old[what]
    old[what]=t[what]
    if buildingVisual(what) then buildingProgress:replaceInstance(old,prior,t[what]) end
    if old.oldPart then old.oldPart[what]=nil end
    if old.oldPartSlot then slotDrop(old.oldPartSlot[what]);old.oldPartSlot[what]=nil end
    if old.oldSkin then slotDrop(old.oldSkin['s:'..what]);old.oldSkin[what]=nil;old.oldSkin['s:'..what]=nil end
    if r.exactTargets[what] then
      slotDrop(old.slots['x:'..what]);old.slots['x:'..what]=t.slots['x:'..what]
      old.exactShape[what]=t.exactShape[what];old.exactOf[what]=t.exactOf[what]
    else
      slotDrop(old.slots[what]);old.slots[what]=t.slots[what]
      old.colliders[what]=t.colliders[what]
    end
    old.cq=old.cq or {};old.cq[what]=t.cq and t.cq[what]
    if old.cq[what] then old.cq[what].key=r.parent;old.cq[what].tile=old end
    old.colWant[what]=t.colWant[what]
    old.retentionColliders=old.retentionColliders or {};old.retentionColliders[what]=t.retentionColliders and t.retentionColliders[what]
    old.colReload=old.colReload or {};old.colReload[what]=old.cq[what] and reloads or nil
    old.colAt=old.colAt or {};old.colAt[what]=old.cq[what] and lastReloadAt or nil
    hideBuilding(old[what],false)
  end
  if r.hasSkin then
    old.skin=t.skin;old.objs=t.objs;old.queued=0
    for _,id in ipairs(old.objs) do hideBuilding(id,false) end
  end
  if old.oldSkin and next(old.oldSkin)==nil then old.oldSkin=nil end
  old.retireRequested=r.retire or old.retireRequested
  tiles[r.key]=nil
  M._fileSessions(old);buildingProgress:sync(old);M.refreshBuildingCoverage(old.gkey)
end
physicalHandover=require('beamngEarth/physicalhandover').new({
  lookup=function(key) return tiles[key] end,
  build=function(r,msg,aid,a) return M.onGeoTile(msg,aid,a,r) end,
  hold=function(t,msg,data,aid) return M._holdReplacement(t,msg,data,aid) end,
  consumePending=M._cancelQueued,
  cancelPending=M._cancelQueued,
  holdPatch=M._holdPatch,
  normalizePatch=function(t,p,aid) M._normalizeExact(t,p.inputs.exact,aid) end,
  releasePatch=M._releasePatch,
  releasePatchTokens=function(p) releaseSlots(p.tokens) end,
  buildPatch=M._buildPatch,
  available=function(records)
    if #deleteQ>0 then return false end
    local count=0;for _ in pairs(records) do count=count+1 end
    return count<M.MAX_PHYSICAL_STAGES
  end,
  releaseDuplicate=function(msg,r)
    releasePending(r.old)
    if r.kind=='patch' then M._incomingExact(r.old,msg,msg.anchorId or r.aid) end
    releaseSlots(messageSlots(msg))
  end,
  frame=function() return engineDebt.frame end,
  requestCollision=function() M.requestCollision(true) end,
  resync=function() handoverResync=true end,
  destroy=function(r)
    if tiles[r.key] then dropTile(r.key,true,true) end
    releaseSlots(r.skinSlots);releaseSlots(r.exactSlots)
  end,
  ready=function(r)
    local t=r.tile
    if not t or t.importFailed or (t.queued or 0)>0 then return false end
    if not sharedSites.compatible(t.data,tiles,r.parent) then return false end
    for what in pairs(t.parts) do if not t[what] then return false end end
    if r.needsSkin and (not t.skin or t.skin.pending>0 or t.skin.anchor~=t.anchor) then return false end
    return not t.skin or t.skin.pending==0
  end,
  clear=function(r) return not M.occupied(r.kind=='patch' and M._patchOldView(r) or r.old,true) and not M.occupied(r.tile,true) end,
  direct=function(r)
    if r.kind~='patch' or next(r.tile.cq or {}) then return false end
    for _,id in ipairs(M._patchOldIds(r)) do local o=scenetree.findObjectById(id);if o and isCollider(o) then return false end end
    return true
  end,
  swapCollision=function(r)
    local changes={}
    for _,id in ipairs(r.kind=='patch' and M._patchOldIds(r) or M._tileIds(r.old)) do
      local o=scenetree.findObjectById(id)
      if o and isCollider(o) then changes[#changes+1]={o=o,old=o:getField('collisionType',0),new='None',id=id,retiring=true} end
    end
    for what,q in pairs(r.tile.cq or {}) do
      local id=r.tile[what];local o=id and scenetree.findObjectById(id)
      if not o then return false end
      changes[#changes+1]={o=o,old=o:getField('collisionType',0),new=M._collisionKind(what,q),id=id}
    end
    local function undo()
      for _,c in ipairs(changes) do pcall(c.o.setField,c.o,'collisionType',0,c.old) end
    end
    local ok,err=pcall(function()
      for _,c in ipairs(changes) do
        if c.retiring and objSlot[c.id] then engineDebt:deleted(objSlot[c.id]) end
        c.o:setField('collisionType',0,c.new)
      end
    end)
    if not ok then undo();lastError=tostring(err);return false end
    return true,undo
  end,
  commit=function(r)
    if r.kind=='patch' then return M._commitPatch(r) end
    local t=r.tile;local pending=r.old.pendingGeo;r.old.pendingGeo=nil
    tiles[r.key]=nil
    dropTile(r.parent,true,true)
    tiles[r.parent]=t;t.staged=nil;t.pendingGeo=pending;t.retireRequested=r.retire or nil
    for _,list in ipairs({walkQ,parked,held,createQ}) do
      for _,q in ipairs(list) do if q.tile==t then q.key=r.parent end end
    end
    for _,q in pairs(t.cq or {}) do q.key=r.parent end
    for _,id in ipairs(M._tileIds(t)) do
      hideBuilding(id,false)
    end
    for what in pairs(t.cq or {}) do
      t.colAt=t.colAt or {};t.colAt[what]=lastReloadAt
      t.colReload=t.colReload or {};t.colReload[what]=reloads
    end
    buildingProgress:drop(t.gkey)
    buildingProgress:attach(t,r.msg)
    local ok,err=pcall(geoRows,r.parent,t,t.data)
    if not ok then lastError=tostring(err) end
    flushBuildingDoors(t);M.refreshBuildingCoverage(t.gkey)
  end,
  after=function(r)
    local t=tiles[r.parent]
    if r.skinMsg then M.onSkin(r.skinMsg,t.anchor);releaseSlots(r.skinSlots) end
    if r.exactMsg then M.onExact(r.exactMsg,t.anchor);releaseSlots(r.exactSlots) end
  end,
})
function M._handover(event,...)
  if event=='offer' then return physicalHandover:offer(...) end
  if event=='route' then return physicalHandover:route(...) end
  if event=='patch' then return physicalHandover:patch(...) end
  if event=='rebase' then return physicalHandover:rebase() end
  if event=='clear' then return physicalHandover:clear() end
  if event=='busy' then return physicalHandover:busy() end
  if event=='resync' then handoverResync=true end
end
function M._physicalPending(t)
  local r=t and t.physicalReplacement
  return r and (r.phase=='awaitFrame' or r.phase=='rebaseWait' or r.phase=='submitting') or false
end
function M._solid(t,what)
  if not t[what] or M._physicalPending(t) then return false end
  local epoch=t.colReload and t.colReload[what]
  if epoch then return epoch<=reloads end
  return ((t.colAt and t.colAt[what]) or math.huge)<lastReloadAt
end
function M._rebuildCollision()
  local changed=physicalHandover:beforeRebuild()
  local ok,err=pcall(be.reloadCollision,be)
  physicalHandover:submitted(changed,ok)
  if not ok then lastError=tostring(err);return false end
  return true
end
-- Keep lifecycle work outside update's already-large closure (LuaJIT has a
-- strict 60-upvalue limit). It shares the existing queues and import governor.
function M._lifetime(event,currentAnchor)
  if event=='begin' then
    inUpdate,actorPositions=true,nil
    for _,key in ipairs(engineDebt:step()) do
      local d=slotDropped[key]
      if d and not slotLive[key] then slotDropped[key]=nil;slotsGone[#slotsGone+1]=d end
    end
  elseif event=='end' then inUpdate,actorPositions=false,nil
  elseif event=='submitted' then engineDebt:submitted()
  elseif event=='stats' then
    local out=engineDebt:stats();out.pendingPhysical=0;out.occupiedRetirements=0
    for _,t in pairs(tiles) do
      if t.pendingGeo then out.pendingPhysical=out.pendingPhysical+1 end
      if t.pendingPatch then out.pendingPhysical=out.pendingPhysical+1 end
      if t.physicalReplacement then out.pendingPhysical=out.pendingPhysical+1 end
      if t.retireRequested then out.occupiedRetirements=out.occupiedRetirements+1 end
    end
    out.transactions=physicalHandover.stats
    out.activeTransactions=0;for _ in pairs(physicalHandover.records) do out.activeTransactions=out.activeTransactions+1 end
    out.owners=0;out.ownedFiles=0
    for _,ref in pairs(slotRefs) do out.owners=out.owners+ref.count;out.ownedFiles=out.ownedFiles+1 end
    return out
  elseif event=='retry' then
    physicalHandover:step()
    for key,t in pairs(tiles) do
      if not t.staged and t.retireRequested and not M.occupied(t) then dropTile(key)
      elseif not t.staged and not t.physicalReplacement and t.pendingGeo and physicalHandover:canStage()
        and (geotile.isKey(t.pendingGeo.msg.key) or not M.occupied(t)) then
        local p=t.pendingGeo
        if p.anchor==currentAnchor and (anchorObj or not geotile.isKey(p.msg.key)) then
          t.pendingGeo=nil
          if M.onTile(p.msg,currentAnchor,anchorObj) then
            if p.skinMsg then M.onSkin(p.skinMsg,currentAnchor) end
            if p.exactMsg then M.onExact(p.exactMsg,currentAnchor) end
          end
          releaseSlots(p.slots);releaseSlots(p.skinSlots);releaseSlots(p.exactSlots)
        elseif p.anchor~=currentAnchor then releasePending(t) end
      elseif not t.staged and not t.physicalReplacement and not t.pendingGeo and t.pendingPatch and physicalHandover:canStage() then
        physicalHandover:resumePatch(key,currentAnchor,anchorObj)
      end
    end
  end
end
function M.update(gov, currentAnchor, player, view, a, camera)
  buildingFade:update()
  M._lifetime('begin')
  stepT0 = stepClock()
  importsThisFrame, deferImports = 0, false
  viewAt = view
  if a then anchorObj = a end
  if prewarmWant then
    if gov:try('roadWalk') then
      local t0 = now()
      if prewarmNow() then
        importsThisFrame = 1
        local ms = now() - t0
        gov:charge('roadWalk', ms)
        noteUnit('prewarm', ms)
      end
    end
  elseif prewarmId and not scenetree.findObjectById(prewarmId) then   -- (the level loaded again: gone with it)
    prewarmId, prewarmWant = nil, prewarmPath
  end
  if currentAnchor then switchAnchor(currentAnchor) end
  M._lifetime('retry',currentAnchor)
  step('anchor')
  releaseGhosts(player)
  step('ghosts')
  if M._releaseOrphans then M._releaseOrphans(player) end
  step('orphans')
  local deferredDeletes={}
  while #deleteQ > 0 and gov:try('roadDelete') do
    local t0 = now()
    local did = table.remove(deleteQ)
    if buildingFade:held(did) then
      hideBuilding(did,true);deferredDeletes[#deferredDeletes+1]=did
    else
      buildingFade:forget(did)
      local o = scenetree.findObjectById(did)
      local collided = o and isCollider(o)
      if o then
        if isCollider(o) then
          if M.nearPlayer(o:getPosition(), M.DELETE_NEAR_M) then collisionDirty = true else deletesDirty = true end
        end
        o:delete()
      end
      slotObjGone(did, collided)
      local ms = now() - t0
      gov:charge('roadDelete', ms)
      noteUnit('delete', ms)
      sinceChange = stopwatch.new()
    end
  end
  for _,id in ipairs(deferredDeletes) do deleteQ[#deleteQ+1]=id end
  releaseSurfaceOwners()
  while #createQ > 0 and gov:try('roadChunk') do
    local q = table.remove(createQ, 1)
    local t = tiles[q.key]
    if t then
      local t0 = now()
      loadMaterials()
      local ok, id = pcall(M._createChunk, q.chunk, t.staged)
      if ok then t.objs[#t.objs + 1] = id else lastError = tostring(id) end
      if not ok and t.staged then t.importFailed=true end
      t.queued = t.queued - 1
      local ms = now() - t0
      gov:charge('roadChunk', ms)
      noteUnit('chunk', ms)
      sinceChange = stopwatch.new()
    end
  end
  step('deletes+chunks')
  releaseHeld()
  step('held')
  updateCollideRange()
  step('collideRange')
  -- Reserve a frame for an already-due rebuild so a continuous import queue
  -- cannot starve collision, or stack a rebuild on top of a mesh import.
  deferImports = not swapQuiet and ((collisionDirty and (propCollisionDirty or sinceReload() > M.RELOAD_EVERY_S * 1000))
    or (collisionDirty and (holdActive or M.urgentColliders()) and sinceReload() > M.URGENT_GAP_S * 1000)
    or (deletesDirty and sinceReload() > M.RELOAD_DELETES_S * 1000))
  local forced = nil
  if #walkQ > 0 and sinceUrgent >= M.URGENT_EVERY_FRAMES and not (gov.isHeavyFrame and gov:isHeavyFrame()) then
    forced = M.urgentWalk(walkQ)
  end
  sinceUrgent = sinceUrgent + 1
  progressFrame = progressFrame + 1
  if not forced and progressFrame % M.FAR_IMPORT_EVERY == 0 then updateFar(gov,true) end
  if not forced and not deferImports and importsThisFrame < M.MAX_IMPORTS_PER_FRAME
    and (#walkQ == 0 or progressFrame % 2 == 0) then
    local choice=buildingProgress:prepare(anchorObj,view or player,camera)
    if choice and gov:try('roadWalk',choice.ms) then
      local elapsed=stopwatch.new()
      if buildingProgress:step(anchorObj,view or player,choice) then
        importsThisFrame = importsThisFrame + 1
        local ms=elapsed();gov:charge('roadWalk',ms);noteUnit('buildingProgress',ms)
      end
    end
  end
  while #walkQ > 0 and not deferImports and importsThisFrame < M.MAX_IMPORTS_PER_FRAME and (forced or gov:try('roadWalk')) do
    local q = table.remove(walkQ, forced or M.nextWalk(walkQ))
    if forced then forced, sinceUrgent, M.urgentWalks = nil, 0, (M.urgentWalks or 0) + 1 end
    local t = tiles[q.key]
    if t and q.tile and q.tile ~= t then t = nil end
    -- (an entry of an earlier tile under this key: not made)
    -- (only a colliding mesh waits: a render-only one (q.renderOnly: the drawn sidewalks and buildings beside their lean
    -- collision meshes) cannot catch the car, and holding it hid a whole tile's sidewalks while the car stood in their
    -- box: a roundabout's island band was never drawn, 2026-10-17 Harbor Point)
    if t and not t.staged and q.what ~= 'road' and not q.renderOnly and playerIn(t.colliders[q.what], q.what, t) then
      held[#held + 1] = q           -- the car is on it: made once the car is clear (playerIn)
      t = nil
    end
    local walk = q.walk
    if t and q.geo then walk = M.geoWalk(t, q.what) end      -- (a geotile's part: placed as the tile is now)
    if t and walk then
      local t0 = now()
      loadMaterials()
      local isRoad = q.what == 'road' or q.what == 'wire' or q.renderOnly   -- render-only meshes
      walk.buildingFade=buildingVisual(q.what) and q.renderOnly
      walk.nativeLod=buildingVisual(q.what) and isRoad
      walk.staged=t.staged~=nil
      importsThisFrame = importsThisFrame + 1
      -- the buildings' and sidewalks' lean meshes are a collision detail (server cdae collision_only): never drawn
      local ok, id = pcall(createWalk, walk, M._collisionKind(q.what,q))
      if ok then slotMade(id, walk.shape) end
      if ok and q.what=='wire' and t.roadsideWireBlocked then
        local o=scenetree.findObjectById(id);if o then o:setHidden(true) end
      end
      if ok and q.skin and t.skin then             -- a new skin's part: the old one's goes (all, with the last)
        t.skin.pending = t.skin.pending - 1
        M.dropOldSkin(t, q.what)
        if t.skin.pending <= 0 then M.dropOldSkin(t) end
      end
      if ok and q.swap and t.oldPart and t.oldPart[q.what] then     -- an exact variant / the base again: swapped
        if buildingVisual(q.what) then
          hideBuilding(t.oldPart[q.what],true)
        end
        deleteQ[#deleteQ + 1] = t.oldPart[q.what]
        t.oldPart[q.what] = nil
        if t.oldPartSlot and t.oldPartSlot[q.what] then slotDrop(t.oldPartSlot[q.what]); t.oldPartSlot[q.what] = nil end
      end
      if ok then
        if not isRoad then
          t.cq = t.cq or {}; t.cq[q.what] = q
          t.retentionColliders=t.retentionColliders or {};t.retentionColliders[q.what]=true
        end
        if isRoad then t[q.what] = id else
          t[q.what] = id
          if not t.staged then
            collisionDirty = true; newColliders[#newColliders + 1] = { id, q }
            t.colAt = t.colAt or {}; t.colAt[q.what] = now()
            if t.colReload then t.colReload[q.what]=nil end
          end
        end
      else lastError = tostring(id);if t.staged then t.importFailed=true end end
      if ok and t.geo and not t.staged and buildingVisual(q.what) then
        buildingProgress:sync(t)
        M.refreshBuildingCoverage(t.gkey)
        flushBuildingDoors(t)
      end
      local ms = now() - t0
      gov:charge('roadWalk', ms)
      noteUnit(tostring(q.what), ms, walk and walk.shape)
      sinceChange = stopwatch.new()
    end
  end
  step('walks')
  updateFar(gov)                -- remaining far work shares the frame's import budget
  step('far')
  if swapQuiet then
    swapQuiet.frames = swapQuiet.frames - 1
    if swapQuiet.frames <= 0 and swapQuiet.since() >= M.SWAP_QUIET_MS then swapQuiet = nil end
  end
  local urgent = collisionDirty and (holdActive or M.urgentColliders()) and sinceReload() > M.URGENT_GAP_S * 1000
  local due = not swapQuiet and ((collisionDirty and (propCollisionDirty or sinceReload() > M.RELOAD_EVERY_S * 1000)) or urgent
      or (deletesDirty and sinceReload() > M.RELOAD_DELETES_S * 1000))
  if importsThisFrame > 0 then due = false end
  if due and not holdActive and reloadWaits < M.RELOAD_WAIT_FRAMES and gov.roomFor and not gov:roomFor(M.RELOAD_ROOM_MS) then
    reloadWaits = reloadWaits + 1
    due = false
  end
  if due then
    reloadWaits = 0
    local t0 = now()
    noteNewColliders()
    if M._rebuildCollision() then
      M._lifetime('submitted')
      lastReloadAt, reloads = now(), reloads + 1
      collisionDirty, deletesDirty, sinceReload = false, false, stopwatch.new()
      propCollisionDirty = false
    end
    local ms = now() - t0
    -- out of the frame's budget, not into the meshes' cost estimate (from PR #41: a ~40 ms rebuild in the roadWalk
    -- EMA held the next sidewalk and building meshes back as if each cost that much more)
    gov:chargeMotion(ms)
    noteUnit('reloadCollision', ms)
  end
  step('collision')
  buildingFade:commit()
  M.importsThisFrame = importsThisFrame
  M._lifetime('end')
end

-- A colliding mesh (sidewalks, bridge decks) never turns solid around the player's car (2026-10-13: the
-- intermittent NaN drives; a late curb or deck appearing around a vehicle). The server's road tile lists
-- boxes around its pieces (roads.collider_boxes); a mesh the car is in is not made (held) or, made since
-- the last reloadCollision, is removed again before it, and made once the car is clear.
M.PLAYER_R = 3.0    -- m around the player's position (half a car's length, and some)
M.PLAYER_DZ = 2.5   -- m above / below
-- a sidewalk's boxes already reach past its slab by about 1 m (server roads.collider_boxes: half its width + 0.5 m
-- + COLLIDER_MARGIN_M): only the car over the sidewalk itself holds it. With PLAYER_R a car anywhere within ~4 m of a
-- curb held the whole tile's sidewalk collision (one mesh a tile), and a tile made again while the car drove its
-- streets had no solid sidewalks at all (the user, 2026-10-27: "sidewalks are missing collision", Fells Point)
M.WALK_PLAYER_R = 0.0
M.DECK_BOX_BELOW_M = 2.2    -- a deck box's floor is this far under its lowest surface (server roads.collider_boxes:
                            -- roadmesh.DECK_DEPTH 1.2 + 1.0)
M.DECK_ON_M = 0.2           -- the car's position this far under that surface or less: on the deck (not held)

-- Is world position p within r m (horizontally) of the player's car? (no car: yes, to be safe)
function M.nearPlayer(p, r)
  local veh = getPlayerVehicle and getPlayerVehicle(0)
  if not veh or not p then return true end
  local q = veh:getPosition()
  local dx, dy = p.x - q.x, p.y - q.y
  return dx * dx + dy * dy <= r * r
end

-- V2 occupancy rings follow a collider box as its optional seventh element.
-- Even-odd containment leaves courtyards clear; distance to every boundary keeps
-- the car's existing clearance margin on both courtyard and exterior walls.
local function actors()
  if inUpdate then actorPositions=actorPositions or occupancy.snapshot();return actorPositions end
  return occupancy.snapshot()
end

playerIn = function(boxes, what, t)
  if type(boxes)~='table' or #boxes==0 then return false end
  local pp = t and t.geo and t.pls and t.pls[what]
  -- A frozen teleporting player may have colliders placed around it. Other
  -- supported actors still participate in the safety check during that hold.
  local inv=pp and pp.inv or (t and t.skin and t.skin[what] and t.skin.occupancyInv) or (t and t.retentionInv)
  return occupancy.intersects(holdActive and occupancy.snapshot(true) or actors(),boxes,what,inv,false,M)
end

function M.occupied(t,allowDropHold)
  local snapshot=allowDropHold and holdActive and occupancy.snapshot(true) or actors()
  for what in pairs(t.retentionColliders or t.cq or {}) do
    if t[what] then
      if snapshot.unknown then return true end
      local boxes=t.colliders and t.colliders[what]
      local pp=t.geo and t.pls and t.pls[what]
      local inv=pp and pp.inv or (t.skin and t.skin[what] and t.skin.occupancyInv) or t.retentionInv
      if type(boxes)=='table' and #boxes>0 then
        if occupancy.intersects(snapshot,boxes,what,inv,true,M) then return true end
      else
        -- Old products may lack a collider inventory: conservatively retain
        -- their whole tile near an actor rather than guessing its surface.
        for _,p in ipairs(snapshot.positions) do
          if not t.cx or (math.abs(p.x-t.cx)<=M.TILE_M/2+M.PLAYER_R
            and math.abs(p.y-t.cy)<=M.TILE_M/2+M.PLAYER_R) then return true end
        end
      end
    end
  end
  return false
end

releaseHeld = function()
  if #held == 0 then return end
  local keep = {}
  for _, q in ipairs(held) do
    local t = tiles[q.key]
    if t then
      if playerIn(t.colliders[q.what], q.what, t) then keep[#keep + 1] = q else walkQ[#walkQ + 1] = q end
    end
  end
  held = keep
end

noteNewColliders = function()
  local removed = 0
  for _, c in ipairs(newColliders) do
    local q = c[2]
    local t = tiles[q.key]
    if t and t[q.what] == c[1] and playerIn(t.colliders[q.what], q.what, t) then
      local o = scenetree.findObjectById(c[1])
      if o then o:delete(); slotObjGone(c[1], true) end
      t[q.what] = nil
      held[#held + 1] = q
      removed = removed + 1
      M.solidAround = (M.solidAround or 0) + 1
      log('I', 'beamngEarth', 'roads: a ' .. tostring(q.what) .. ' mesh around the player held until it is clear')
    end
  end
  newColliders = {}
  return removed
end
M._noteNewColliders = noteNewColliders

-- The player's position and motion now: p (vec3) and its unit horizontal direction at FAST_MS or more, else nil.
local function playerNow()
  local veh = getPlayerVehicle and getPlayerVehicle(0)
  if not veh then return nil end
  return veh:getPosition(), lastDir
end

-- Which walkQ entry to make next (index): the road meshes and colliders before the render-only meshes (drawn
-- buildings, wires), each by the distance to its tile's centre (behind a fast car counting three times): the tiles
-- the car reaches first (the user, 2026-10-19: high speeds, the road texture struggling to keep up). A render-only
-- mesh by its distance to the camera instead when that is nearer (viewAt: what is drawn follows the camera).
function M.nextWalk(q)
  if #q <= 1 then return 1 end
  local p, dir = playerNow()
  if not p then return 1 end
  local best, bestKey = 1, math.huge
  for i, e in ipairs(q) do
    local t = tiles[e.key]
    local k = 1e9
    if t and t.cx then
      local dx, dy = t.cx - p.x, t.cy - p.y
      k = math.sqrt(dx * dx + dy * dy)
      if dir then         -- fast: by the way along the path ahead, sideways counting SIDE_PENALTY times (the server's
        local along = dx * dir.x + dy * dir.y               -- roads.path_key); behind the car after all of those
        local side = math.abs(dx * dir.y - dy * dir.x)
        if along < -M.TILE_M / 2 then k = k * 3 + M.LEAD_MAX_M     -- (its centre half a tile behind: left behind)
        else k = math.max(0, along) + M.SIDE_PENALTY * math.max(0, side - M.TILE_M / 2) end
      end
      if viewAt and (e.renderOnly or e.what == 'wire') then
        local vx, vy = t.cx - viewAt.x, t.cy - viewAt.y
        k = math.min(k, math.sqrt(vx * vx + vy * vy))
      end
    end
    if e.renderOnly or e.what == 'wire' then k = k + 1e6 end
    if t and t.staged then k=k+2e6 end -- accepted coverage exists; missing coverage comes first
    if e.what == 'deck' or e.what == 'tunnel' then k = math.max(0, k - M.DRIVE_FIRST_M) end
    if k < bestKey then best, bestKey = i, k end
  end
  return best
end

-- The walkQ index of a bridge deck's or tunnel's collider the car reaches within URGENT_S (150 m at least; not behind a
-- fast car), the nearest, or nil.
function M.urgentWalk(q)
  local p, dir = playerNow()
  if not p then return nil end
  local reach = math.max(150, lastSpeed * M.URGENT_S) + M.TILE_M * 0.71
  local best, bd = nil, math.huge
  for i, e in ipairs(q) do
    if e.what == 'deck' or e.what == 'tunnel' then
      local t = tiles[e.key]
      if t and t.cx and not t.ghost and not t.staged and (not e.tile or e.tile == t) then
        local dx, dy = t.cx - p.x, t.cy - p.y
        local d = math.sqrt(dx * dx + dy * dy)
        if d <= reach and d < bd and (not dir or dx * dir.x + dy * dir.y > -M.TILE_M / 2) then best, bd = i, d end
      end
    end
  end
  return best
end

-- Is a collider made since the last rebuild one the car reaches soon (its tile within URGENT_S of driving, 150 m at
-- least)? Then the rebuild runs now, not after RELOAD_EVERY_S.
function M.urgentColliders()
  if #newColliders == 0 then return false end
  local p = playerNow()
  if not p then return true end
  local reach = math.max(150, lastSpeed * M.URGENT_S) + M.TILE_M * 0.71
  for _, c in ipairs(newColliders) do
    local t = tiles[c[2].key]
    if t and t.cx then
      local dx, dy = t.cx - p.x, t.cy - p.y
      if dx * dx + dy * dy <= reach * reach then return true end
    end
  end
  return false
end

-- core swapped the terrain block's .ter this frame (terrain.swap): no collision rebuild until it has settled.
function M.terrainSwapped() swapQuiet = { frames = M.SWAP_QUIET_FRAMES, since = stopwatch.new() } end
function M.swapQuiet() return swapQuiet ~= nil end

-- core's drop hold on / off: while it holds, colliders around the frozen car are made (not held for it) and rebuilt
-- at once, so the hold can wait for them (M.readyAround) and set the car on top.
function M.setHold(on) holdActive = on and true or false end

-- Are the road tiles of anchor aid within r of (x, y) all in, their colliders (decks, tunnels, sidewalks, buildings)
-- made and solid (made before the last collision rebuild)? Only what collides counts: the drawn road surface, building
-- facades and wires come when they come (in Manhattan they kept a drop hold 20 s). Roads off: yes.
function M.readyAround(aid, x, y, r)
  if not M.enabled then return true end
  if anchorId ~= aid then return false end
  local busy = {}
  for _, q in ipairs(walkQ) do
    if not q.renderOnly and q.what ~= 'road' and q.what ~= 'wire' then busy[q.key] = true end
  end
  local n = M.TILE_M
  if M.geo then           -- (geotiles: those whose quads come within r, their skins this anchor's)
    for _, k in ipairs(M.geoKeysNear(x, y, r)) do
      local key = geoKey(k)
      local t = tiles[key]
      if not t or M._physicalPending(t) or busy[key] or not t.skin or t.skin.anchor ~= aid then return false end
      for what in pairs(t.colWant or {}) do
        if not M._solid(t,what) then return false end
      end
    end
    return true
  end
  for gx = math.floor((x - r) / n), math.floor((x + r) / n) do
    for gy = math.floor((y - r) / n), math.floor((y + r) / n) do
      local key = tileKey(aid, gx .. '_' .. gy)
      local t = tiles[key]
      if not t or t.ghost or busy[key] then return false end
      for what in pairs(t.colWant or {}) do
        if not M._solid(t,what) then return false end
      end
    end
  end
  return true
end

-- Something else made colliding objects near the player (trees.lua's Forest items): rebuild collision at the
-- next throttled slot.
function M.requestCollision(removedOrMoved)
  collisionDirty = true
  propCollisionDirty = propCollisionDirty or removedOrMoved == true
end

-- Collision rebuilds so far (be:reloadCollision, ours or the terrain commit's): what was made before one collides from
-- the frame after it (terrainpatch.groundReady).
function M.reloads() return reloads end

function M.hasWork() return buildingFade:busy() or #createQ > 0 or #deleteQ > 0 or #walkQ > 0 or #farQ > 0 or collisionDirty or buildingProgress:hasWork() or M._handover('busy') end


-- Somebody else just ran be:reloadCollision() (the terrain commit): the sidewalks made so far collide.
function M.collisionRebuilt()
  -- that rebuild already made them solid: one held now leaves the physics at the next one
  engineDebt:submitted()
  local removed = noteNewColliders()
  lastReloadAt, reloads = now(), reloads + 1
  collisionDirty, deletesDirty, sinceReload = removed > 0, false, stopwatch.new()
  propCollisionDirty = false
end

-- Every road removed now (setting off, mod unload).
-- Server hello.prewarm: a tiny shape listing every material the server's shapes use, loaded once when it connects
-- (server/prewarm.py): a material's first shape in a session set it up (a tunnel's first tile 65 ms, later ones ~2 ms),
-- now while the level starts. Kept far below the map (one per path; nil: an older server, nothing).
prewarmNow = function()
  local path = prewarmWant
  -- (the hello comes at the main menu, before the level's objects and with the roads off outside our level)
  if not path or not M.enabled or not scenetree.MissionGroup then return end
  prewarmWant = nil
  if path == prewarmPath and prewarmId and scenetree.findObjectById(prewarmId) then return end   -- (made already)
  if prewarmId then
    local o = scenetree.findObjectById(prewarmId)
    if o then o:delete() end
    slotObjGone(prewarmId)
    prewarmId = nil
  end
  loadMaterials()
  local t = stopwatch.new()
  local ok, id = pcall(createWalk, { shape = path, pos = { 0, 0, -5000 } }, false)
  if not ok then lastError = tostring(id); return true end
  slotMade(id,path)
  prewarmId, prewarmPath = id, path
  log('I', 'beamngEarth', string.format('roads: materials prewarmed in %.0f ms (%s)', t(), path))
  return true
end

function M.prewarm(path)
  if type(path) ~= 'string' then return false end
  prewarmWant = path
  return true
end

function M.clear()
  buildingFade:clear()
  handoverResync=false
  M._handover('clear')
  buildingProgress:clear()
  -- Explicit mod unload/off is a teardown. Normal retirement never uses force.
  for key in pairs(tiles) do dropTile(key,false,true) end
  for key, f in pairs(far) do
    if f.geo then M.dropFarGeo(key) end
    if f.id then deleteQ[#deleteQ + 1] = f.id end
    slotDrop(f.slot)
  end
  far, farQ, farSeen = {}, {}, {}
  createQ, held, newColliders = {}, {}, {}
  for _, id in ipairs(deleteQ) do
    local o = scenetree.findObjectById(id)
    local collided = o and isCollider(o)
    if o then
      if isCollider(o) then collisionDirty = true end
      o:delete()
    end
    slotObjGone(id, collided)
  end
  deleteQ = {}
  releaseSurfaceOwners()
  walkQ, parked = {}, {}
  if collisionDirty or deletesDirty then
    be:reloadCollision(); engineDebt:submitted(); collisionDirty, deletesDirty = false, false
  end
  propCollisionDirty = false
end

-- The level ended: its objects are gone with it.
function M.reset()
  handoverResync=false
  M._handover('clear')
  buildingProgress:clear()
  -- (the level took the objects: every slot goes)
  for key, t in pairs(tiles) do
    releasePending(t)
    M._releasePatch(t)
    local trees=require('beamngEarth/trees')
    if trees.clearSurfaceExclusions then trees.clearSurfaceExclusions('road:'..key) end
  end
  local treeMasks=require('beamngEarth/trees')
  for key in pairs(retiringSurfaceOwners) do
    if treeMasks.clearSurfaceExclusions then treeMasks.clearSurfaceExclusions('road:'..key) end
  end
  retiringSurfaceOwners={}
  for _,ref in pairs(slotRefs) do slotsGone[#slotsGone+1]={ref[1],ref[2],ref[3]} end
  for _, d in pairs(slotDropped) do slotsGone[#slotsGone + 1] = d end
  objSlot, slotLive, slotDropped, slotRefs, objectSessions = {}, {}, {}, {}, {}
  engineDebt:clear()
  tiles, createQ, deleteQ, walkQ, anchorId, loadedMaterials = {}, {}, {}, {}, nil, false
  far, farQ, farSeen = {}, {}, {}
  collisionDirty, deletesDirty = false, false
  propCollisionDirty = false
end

-- On / off (the settings page, through core.setRoadsEnabled, which asks the server for the tiles
-- again when switched back on). Returns true if it was off and is on now.
function M.setEnabled(on)
  local was = M.enabled
  M.enabled = on and true or false
  if not M.enabled then M.clear() end
  return M.enabled and not was
end

-- The highway signs on / off (the settings page's highwaySigns, through core.setHighwaySigns): only the sign objects
-- go or come back (from each tile's signData); the roads, their colliders and the held shape slots stay. Returns true
-- if it changed.
function M.setSignsEnabled(on)
  on = on and true or false
  if M.signsEnabled == on then return false end
  M.signsEnabled = on
  local isSign = {}
  for _, w in ipairs(M.SIGN_WHATS) do isSign[w] = true end
  local keep = {}
  for _, q in ipairs(walkQ) do if not isSign[q.what] then keep[#keep + 1] = q end end
  walkQ = keep
  for key, t in pairs(tiles) do
    for _, what in ipairs(M.SIGN_WHATS) do
      if t[what] then deleteQ[#deleteQ + 1] = t[what]; t[what] = nil end
      local sign = t.signData and t.signData[what]
      if on and M.enabled and not t.ghost and sign then
        walkQ[#walkQ + 1] = { key = key, walk = sign, what = what, tile = t, renderOnly = true }
      end
    end
  end
  return true
end

-- The state of the road tiles along a line (tools: how far ahead of a fast car its tiles are ready). From (x, y)
-- along the unit direction (hx, hy) to dist m, every 32 m: { d, key, arrived (ms ago or false), road (its road mesh
-- made), col ('none': no colliders, 'parked' / 'made' / 'solid': made before the last collision rebuild) }.
function M.ahead(x, y, hx, hy, dist)
  local out, seen, n, tnow = {}, {}, M.TILE_M, now()
  for d = 0, dist, 32 do
    local px, py = x + hx * d, y + hy * d
    local sq = math.floor(px / n) .. '_' .. math.floor(py / n)
    local tkey = tileKey(anchorId, sq)
    if M.geo then sq = M.geoKeyAt(px, py) or sq; tkey = geoKey(sq) end
    if not seen[sq] then
      seen[sq] = true
      local t = tiles[tkey]
      local e = { d = d, key = sq, arrived = t and math.floor(tnow - (t.at or tnow)) or false }
      if t then
        e.road = t.road ~= nil or (t.queued or 0) <= 0
        e.bld = t.bld ~= nil                    -- (a tile without buildings never has one)
        e.walk = t.walk ~= nil
        local want, made, solid = 0, 0, 0
        for what in pairs(t.colWant or {}) do
          want = want + 1
          if t[what] then
            made = made + 1
            if M._solid(t,what) then solid = solid + 1 end
          end
        end
        e.col = want == 0 and 'none' or (solid == want and 'solid') or (made == want and 'made') or 'parked'
        if e.col == 'parked' then       -- where each missing collider waits: walk (the import queue), parked (not near
          e.miss = {}                   -- enough yet), held (the car in its box), none (no entry: dropped)
          for what in pairs(t.colWant or {}) do
            if not t[what] then e.miss[what] = 'none' end
          end
          for _, set in ipairs({ { walkQ, 'walk' }, { parked, 'parked' }, { held, 'held' } }) do
            for _, q in ipairs(set[1]) do
              if q.key == tkey and e.miss[q.what] then e.miss[q.what] = set[2] end
            end
          end
        end
      end
      out[#out + 1] = e
    end
  end
  return out
end

-- The server's hello: road tiles as geotiles (hello.roadGeo == M.ROAD_GEO) or the anchor's.
function M.setGeo(on) M.geo = on and true or false end

-- A new server session (core.lua hello: a restarted server, its anchor ids from 1 again): every anchor tile goes (as
-- M.clear: they belonged to the old session), the geotiles stay as orphans: one the new session sends again with the
-- same content hash (h) keeps its objects (onGeoTile), the others go once ORPHAN_FAR_M away or after ORPHAN_MAX_S
-- (releaseOrphans). Their skins are no anchor's now (the new session's come with their content).
M.ORPHAN_MAX_S = 120
M.ORPHAN_FAR_M = 960
local orphanSince = nil
function M.newSession()
  buildingFade:finish()
  M._handover('rebase')
  buildingProgress:clear()
  if not M.geo and not M.farGeo then return M.clear() end      -- (anchor tiles only: all of them go)
  local any = false
  for key, t in pairs(tiles) do
    releasePending(t)
    M._releasePatch(t)
    if t.geo and M.geo then
      t.orphan = true
      if t.skin then t.skin.anchor = -1 end
      any = true
    else
      dropTile(key)
    end
  end
  -- (the far geotiles stay as orphans too: the new session's same content (h) keeps them, the rest go after
  -- FAR_GEO_ORPHAN_S)
  local keepFar, keepSeen = {}, {}
  for key, f in pairs(far) do
    if f.geo and M.farGeo then
      f.orphan = true
      keepFar[key] = f
      if farSeen[key] then keepSeen[key] = true end
      any = true
    else
      if f.id then deleteQ[#deleteQ + 1] = f.id end
      slotDrop(f.slot)
      if f.geo then
        farGeoLamps(f, false)
        for _, p in pairs(f.parts) do
          if p.id then deleteQ[#deleteQ + 1] = p.id end
          slotDrop(p.slot)
        end
      end
    end
  end
  far, farSeen = keepFar, keepSeen
  for _,t in pairs(tiles) do if t.geo then M.refreshBuildingCoverage(t.gkey) end end
  local fq = {}
  for _, k in ipairs(farQ) do if far[k:match('^(.-)#') or k] then fq[#fq + 1] = k end end
  farQ = fq
  createQ, held, newColliders = {}, {}, {}
  local keep = {}
  for _, q in ipairs(walkQ) do if tiles[q.key] and not q.skin then keep[#keep + 1] = q end end
  walkQ = keep
  orphanSince = any and stopwatch.new() or nil
  collisionDirty = true
end
local function releaseOrphans(player)
  if not orphanSince then return end
  local all = orphanSince() > M.ORPHAN_MAX_S * 1000
  local left = false
  for key, f in pairs(far) do
    if f.orphan then
      if orphanSince() > M.FAR_GEO_ORPHAN_S * 1000 then M.dropFarGeo(key) else left = true end
    end
  end
  for key, t in pairs(tiles) do
    if t.orphan and not t.staged then
      local far_ = player and t.cx and M.boxGap(player.x, player.y, t.cx, t.cy, M.TILE_M / 2) > M.ORPHAN_FAR_M
      if (all or far_) and dropTile(key) then collisionDirty = true else left = true end
    end
  end
  if not left then orphanSince = nil end
end
M._releaseOrphans = releaseOrphans

-- The sign tiles shown (diagnostics): how many, and the farthest one's centre from (x, y) in m.
function M.signTiles(x, y)
  local n, far = 0, 0
  for _, t in pairs(tiles) do
    if t.signOnly and not t.ghost and t.cx then
      n = n + 1
      far = math.max(far, math.sqrt((t.cx - x) ^ 2 + (t.cy - y) ^ 2))
    end
  end
  return n, far
end

-- The server session folders the road tiles' and the far geotiles' objects are made from (their parts', exact
-- variants' and far parts' shapes): claimed with the far field's (core.lua hello / pose `sessions`), so a restarted
-- server keeps an earlier run's folder while a tile it sent again unchanged still shows its files. Only the far
-- field's were claimed: the kept road tiles' folder went 10 minutes after a server restart, their buildings with it
-- (the Stelvio's summit, 2026-10-31).
-- (each path's folder memoised: it runs on every pose, farfield.heldSessions; cleared past HELD_MEMO_MAX paths)
local HELD_MEMO_MAX = 20000
local heldMemo, heldMemoN = {}, 0
function M._shapeSessions()
  local ff = require('beamngEarth/farfield')
  local set = {}
  local function add(sh)
    if type(sh) ~= 'string' then return end
    local f = heldMemo[sh]
    if f == nil then
      f = ff.folderOf(sh) or false
      if heldMemoN >= HELD_MEMO_MAX then heldMemo, heldMemoN = {}, 0 end
      heldMemo[sh], heldMemoN = f, heldMemoN + 1
    end
    if f then set[f] = true end
  end
  for _, t in pairs(tiles) do
    for _, p in pairs(t.parts or {}) do if type(p) == 'table' then add(p.shape) end end
    for _, sh in pairs(t.exactShape or {}) do add(sh) end
  end
  for _, f in pairs(far) do
    if f.shape then add(f.shape) end
    for _, p in pairs(f.parts or {}) do if type(p) == 'table' then add(p.shape) end end
  end
  local out = {}
  for f in pairs(set) do out[#out + 1] = f end
  table.sort(out)
  return out
end

-- Every server session folder the scene's objects still use (core.lua hello / pose `sessions`): the far field's and
-- the road tiles' (heldSessions)
function M.allHeldSessions()
  local out, seen = {}, {}
  for _, list in ipairs({ require('beamngEarth/farfield').heldSessions(), M.heldSessions() }) do
    for _, f in ipairs(list) do if not seen[f] then seen[f] = true; out[#out + 1] = f end end
  end
  table.sort(out)
  return out
end

function M.status()
  local nt, no, nw, nr, nd, nb, ngForest, ngRows = 0, 0, 0, 0, 0, 0, 0, 0
  for _, t in pairs(tiles) do
    nt = nt + 1; no = no + #t.objs
    if t.walk then nw = nw + 1 end
    if t.road then nr = nr + 1 end
    if t.deck then nd = nd + 1 end
    if t.bld then nb = nb + 1 end
    if t.guardrails then ngForest = ngForest + 1; ngRows = ngRows + (t.guardrailRows or 0) end
  end
  local nf, ngf, ngShown = 0, 0, 0
  for _, f in pairs(far) do
    if f.id and not f.hidden then nf = nf + 1 end
    if f.geo then
      ngf = ngf + 1
      for _, p in pairs(f.parts) do if p.id and not p.hidden then nf, ngShown = nf + 1, ngShown + 1 end end
    end
  end
  return { enabled = M.enabled, tiles = nt, roads = no, queued = #createQ, deleting = #deleteQ, anchor = anchorId,
    walks = nw, roadMeshes = nr, decks = nd, buildings = nb, guardrailForestTiles = ngForest,
    guardrailForestRows = ngRows, farBuildings = nf, walksQueued = #walkQ, solidAround = M.solidAround or 0,
    urgentWalks = M.urgentWalks or 0, quietS = sinceChange() / 1000, error = lastError, units = unitStats, unitLog = unitLog,
    buildingProgress = buildingProgress:diagnostics(),
    resourceLifetime = M._lifetime('stats'),
    geo = M.geo or false, geoStats = M.geoStats, farGeo = M.farGeo or false, farGeoTiles = ngf,
    farGeoShown = ngShown }
end

local okSweep, swept = pcall(M.sweep)
if okSweep and swept > 0 then log('W', 'beamngEarth', 'roads: deleted ' .. swept .. ' road objects left by a previous Lua state') end

return M
