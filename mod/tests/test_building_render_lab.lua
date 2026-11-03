-- Probe lifecycle and namespace isolation, without native renderer claims.
local objects, materialObjects, loaded = {}, {}, {}
local definitions = {
  bne_lab_baked_test = {}, bne_lab_micro_test = {},
  bne_lab_source_bne_bld_facade = {}, bne_lab_source_bne_bld_office = {}
}
local deleted, errors = 0, 0
local function check(v, message) if not v then error(message) end end
function vec3(x,y,z) return {x=x,y=y,z=z} end
function getPlayerVehicle() return {getPosition=function() return vec3(10,20,3) end} end
function log() end
function jsonReadFile() return definitions end
function createObject()
  local o={fields={}}
  function o:setField(k,i,v) self.fields[k]=v end
  function o:getField(k) return self.fields[k] end
  function o:setPosition(p) self.pos=p end
  function o:registerObject(n) self.name=n;objects[n]=self end
  function o:delete() objects[self.name]=nil;deleted=deleted+1 end
  return o
end
scenetree={MissionGroup={addObject=function() end},findObject=function(n) return materialObjects[n] end}
function loadJsonMaterialsFile(path)
  loaded[#loaded+1]=path
  for name in pairs(definitions) do
    local m=createObject();m.fields.castShadows=name:find('micro',1,true) and '0' or '1'
    function m:flush() end
    function m:reload() end
    materialObjects[name]=m
  end
end
local night=false
core_environment={getLightState=function() return {isNight=night} end}
local M=dofile('probes/building_render_lab.lua')
M.onExtensionLoaded()
check(#loaded==1,'probe loads only private laboratory materials')
check(M.mode=='near','starts with reference geometry')
check(objects.bneRenderLab_1.pos.x==10,'reference position')
M.setMode('baked')
check(deleted==4,'old mode removed atomically before new scene')
check(objects.bneRenderLab_1.fields.shapeName:find('house_baked.cdae',1,true),'baked variant selected')
check(objects.bneRenderLab_1.fields.collisionType=='None','no changes to driving collision')
local ok=pcall(M.setMode,'unsupported')
check(not ok and M.mode=='baked','invalid mode leaves scene intact')
M.onUpdate(1)
check(materialObjects.bne_lab_baked_test.fields.emissiveFactor=='0 0 0','daytime atlas is not glowing')
night=true;M.onUpdate(1)
check(materialObjects.bne_lab_source_bne_bld_office.fields.emissiveIntensityNits=='70','source office intensity retained')
check(materialObjects.bne_lab_baked_test.fields.emissiveIntensityNits=='200','baked atlas night intensity applied')
check(M.inspect().shadowMaterials.bne_lab_micro_test=='0','shadow material can be inspected')
M.onExtensionUnloaded()
check(next(objects)==nil,'unload removes all test objects')
print('12 render laboratory checks passed')
