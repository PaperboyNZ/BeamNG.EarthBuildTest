-- Isolated A/B scene for the assets exported by tools/building_render_lab.py.
-- Load on a flat test map: extensions.load('beamngEarth_renderLab')
local M = {}
local root = '/levels/beamng_earth/art/shapes/buildingRenderLab/'
local modes = {near=true, lite=true, baked=true, shadow_detail=true, shadow_geometry=true}
local fixtures = {'house','block','office','courtyard'}
local objects = {}
local anchor
local timer = 0
local lastNight
local materials
M.mode = 'near'

local function clear()
  for _, o in ipairs(objects) do if o and o.delete then o:delete() end end
  objects = {}
end

function M.setMode(mode)
  assert(modes[mode], 'Use near, lite, baked, shadow_detail or shadow_geometry')
  clear()
  M.mode = mode
  for i, name in ipairs(fixtures) do
    local o = createObject('TSStatic')
    o:setField('shapeName',0,root .. name .. '_' .. mode .. '.cdae')
    o:setField('collisionType',0,'None')
    o:setField('decalType',0,'None')
    o:setField('dynamic',0,'true')
    o.canSave = false
    o:setPosition(vec3(anchor.x+(i-1)*60,anchor.y+25,anchor.z))
    o:registerObject('bneRenderLab_' .. i)
    scenetree.MissionGroup:addObject(o)
    objects[#objects+1] = o
  end
  log('I','buildingRenderLab','Mode: ' .. mode .. '. Same fixture positions; collision disabled.')
end

function M.inspect()
  local result = {mode=M.mode, objects={}, shadowMaterials={}}
  for i,o in ipairs(objects) do
    result.objects[i] = {name=fixtures[i],shape=o:getField('shapeName',0)}
  end
  for name,def in pairs(materials or {}) do
    if name:find('bne_lab_micro_',1,true)==1 then
      local m = scenetree.findObject(name)
      result.shadowMaterials[name] = m and m:getField('castShadows',0) or 'MISSING'
    end
  end
  return result
end

function M.onUpdate(dt)
  timer = timer+(dt or 0)
  if timer<1 then return end
  timer=0
  local env=rawget(_G,'core_environment')
  local state=env and env.getLightState and env.getLightState()
  if type(state)~='table' then return end
  local night=state.isNight==true
  if night==lastNight then return end
  lastNight=night
  -- Only private probe materials are modified, including source clones for a
  -- fair night comparison on maps where the main Earth mod is not running.
  local glow={bne_bld_facade={'1 1 1',200},bne_bld_office={'0.95 0.97 1',70},bne_bld_shop={'1 0.80 0.58',30}}
  for name,_ in pairs(materials or {}) do
    local source=name:match('^bne_lab_source_(.*)')
    local g=glow[source] or (name:find('bne_lab_baked_',1,true)==1 and {'1 1 1',200})
    if g then
      local m=scenetree.findObject(name)
      if m then
        m:setField('emissiveFactor',0,night and g[1] or '0 0 0')
        m:setField('emissiveIntensityNits',0,tostring(night and g[2] or -1))
        m:flush();m:reload()
      end
    end
  end
end

function M.onExtensionLoaded()
  loadJsonMaterialsFile(root .. 'render_lab.materials.json')
  materials=jsonReadFile(root .. 'render_lab.materials.json')
  local vehicle=getPlayerVehicle(0)
  anchor=vehicle and vehicle:getPosition() or getCameraPosition()
  M.setMode('near')
end

M.onExtensionUnloaded=clear
return M
