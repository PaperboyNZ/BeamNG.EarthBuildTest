-- Canonical site fragments have independent sector collision owners. Adjacent
-- resident fragments must agree on the full site's accepted surface revision.
-- A new source/terrain revision waits for old neighbours to retire; it cannot
-- create a temporary step while a car still pins an old sector.
local M={}
local function records(data)
  local out={}
  if type(data)~='table' or data.sharedSites==nil then return out end
  local root=data.sharedSites
  if type(root)~='table' or root.v~=1 or type(root.sites)~='table' or #root.sites>8 then return nil end
  for _,s in ipairs(root.sites) do
    if s.partition=='canonical-ground-v1' then
      local id=s.identity
      if type(id)~='table' or type(id.namespace)~='string' or type(id.feature_id)~='string'
          or type(s.surface_revision)~='string' or #s.surface_revision~=64
          or s.surface_revision:find('[^0-9a-f]') then return nil end
      local key=#id.namespace..':'..id.namespace..id.feature_id
      if type(s.sectors)~='table' or #s.sectors>8 then return nil end
      local sectors={}
      for _,sector in ipairs(s.sectors) do
        if type(sector)~='string' or not sector:match('^g17_%d+_%d+$') then return nil end
        sectors[sector]=true
      end
      if out[key] and out[key].revision~=s.surface_revision then return nil end
      out[key]={revision=s.surface_revision,sectors=sectors}
    end
  end
  return out
end
function M.compatible(data,tiles,ownKey)
  local wanted=records(data);if not wanted then return false end
  for key,t in pairs(tiles or {}) do
    if key~=ownKey and not t.staged then
      local old=records(t.data);if not old then return false end
      for id,record in pairs(wanted) do
        if old[id] and old[id].revision~=record.revision then return false end
        if t.gkey and record.sectors[t.gkey] and not old[id] then return false end
      end
      for id,record in pairs(old) do
        if data.key and record.sectors[data.key] and not wanted[id] then return false end
      end
    end
  end
  return true
end
return M
