-- Validate the entire declared resource inventory BEFORE any resident tile is
-- retired. Hashes identify file contents; pooled paths may change independently.
local M = { VERSION = 1, MAX_PARTS = 4096 }
local function hex(v,n) return type(v)=='string' and #v==n and not v:find('[^a-f0-9]') end
local function dense(t,limit)
  if type(t)~='table' or #t>limit then return false end
  local count=0
  for k in pairs(t) do
    if type(k)~='number' or k%1~=0 or k<1 or k>#t then return false end
    count=count+1
  end
  return count==#t
end
local function finite(v) return type(v)=='number' and v==v and math.abs(v)<math.huge end
function M.valid(data,key,required)
  if type(data)~='table' or type(key)~='string' then return false end
  local m=data.sectorManifest
  if m==nil then return not required end -- explicit legacy compatibility
  if type(m)~='table' or m.v~=M.VERSION or m.topology~='closed-v1'
    or type(m.producer)~='table' or m.producer.namespace~='beamng-earth/geotile'
    or m.producer.feature_id~=key or type(m.frame)~='table' or m.frame.type~='geotile-world-v1'
    or not dense(m.frame.origin,2) or #m.frame.origin~=2 or not dense(data.frame,2) or #data.frame~=2
    or not finite(m.frame.origin[1]) or not finite(m.frame.origin[2])
    or math.abs(m.frame.origin[1])>90 or math.abs(m.frame.origin[2])>180
    or m.frame.origin[1]~=data.frame[1] or m.frame.origin[2]~=data.frame[2]
    or type(m.physical)~='table' or not hex(m.physical.revision,16) or m.physical.revision~=data.physicalHash
    or type(m.visual)~='table' or not hex(m.visual.revision,64) or m.visual.depends_on~=m.physical.revision
    or not dense(m.physical.parts,M.MAX_PARTS) or not dense(m.visual.parts,M.MAX_PARTS)
    or #m.physical.parts+#m.visual.parts>M.MAX_PARTS or type(data.shapeHashes)~='table' then return false end
  local z,x,y=key:match('^g(%d+)_(%d+)_(%d+)$')
  if tonumber(z)~=17 or tonumber(x)>=2^17 or tonumber(y)>=2^17 then return false end
  local expectedVisual={}
  if type(data.bldcol)=='table' then
    for _,what in ipairs(data.buildingChunks and data.buildingChunks.visual or {}) do expectedVisual[what]=true end
  end
  local seen={}
  for _,group in ipairs({'physical','visual'}) do
    for _,r in ipairs(m[group].parts) do
      if type(r)~='table' or type(r.part)~='string' or #r.part>32 or not r.part:match('^[a-z][a-z0-9]*$')
        or seen[r.part] or not hex(r.sha256,64) or data.shapeHashes[r.part]~=r.sha256
        or type(data[r.part])~='table' or type(data[r.part].shape)~='string'
        or ((group=='visual')~=(expectedVisual[r.part]==true)) then return false end
      seen[r.part]=true
    end
  end
  for what in pairs(data.shapeHashes) do if not seen[what] then return false end end
  for what,r in pairs(data) do
    if type(r)=='table' and r.shape~=nil and not seen[what] then return false end
  end
  return true
end
return M
