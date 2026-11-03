-- Live actor positions for collision activation and occupied-resource retention.
-- Parked vehicles retain support too. Inactive walkers and remote vehicles
-- explicitly floating off our physics block follow collisionfoci's exclusions.
local M = { MAX_ACTORS = 512 }
local cf = require('beamngEarth/collisionfoci')
local function finite(v) return type(v)=='number' and v==v and math.abs(v)<math.huge end
-- Compose a resource's old inverse with the inverse of a world rebase. Flatten
-- the matrix immediately so repeated rebases never create a transform chain.
function M.rebaseInverse(previous,motion)
  local inv=motion:inverse()
  if not previous then return inv end
  local r={}
  for i=0,2 do for j=0,2 do
    local v=0
    for k=0,2 do v=v+previous.r[i*3+k+1]*inv.r[k*3+j+1] end
    r[i*3+j+1]=v
  end end
  local x,y,z=previous:apply(inv.t[1],inv.t[2],inv.t[3])
  return require('beamngEarth/geodesy').transformOf(r,{x,y,z})
end
function M.snapshot(skipActive)
  local out = { positions = {}, unknown = false }
  local seen = {}
  local function actorKey(o)
    if not o then return nil end
    local fn=o.getId or o.getID
    if fn then
      local ok,id=pcall(fn,o)
      if ok and id~=nil then return id end
    end
    return o
  end
  local function add(o,active)
    local key=actorKey(o)
    if not key or seen[key] then return end
    seen[key]=true
    if not active then
      local ms=package.loaded['beamngEarth/mpsession']
      if cf.isWalker(o) or (ms and ms.isFloating and o.getId and ms.isFloating(o:getId())) then return end
    end
    local ok,p=pcall(function() return o:getPosition() end)
    if not ok or not p or not finite(p.x) or not finite(p.y) or not finite(p.z) then out.unknown=true;return end
    out.positions[#out.positions+1]={x=p.x,y=p.y,z=p.z}
  end
  local active=getPlayerVehicle and getPlayerVehicle(0)
  if skipActive and active then seen[actorKey(active)]=true else add(active,true) end
  if be and be.getObjectCount and be.getObject then
    local ok,n=pcall(function() return be:getObjectCount() end)
    if not ok or not finite(n) or n%1~=0 or n<0 or n>M.MAX_ACTORS then out.unknown=true;return out end
    for i=0,n-1 do
      local got,o=pcall(function() return be:getObject(i) end)
      if not got then out.unknown=true else add(o,false) end
    end
  end
  return out
end

local function nearRings(rings,x,y,r)
  local inside=false
  for _,ring in ipairs(rings) do
    local j=#ring
    for i=1,#ring do
      local a,b=ring[j],ring[i]
      local dx,dy=b[1]-a[1],b[2]-a[2]
      local len=dx*dx+dy*dy
      local along=len>0 and math.max(0,math.min(1,((x-a[1])*dx+(y-a[2])*dy)/len)) or 0
      local qx,qy=x-a[1]-along*dx,y-a[2]-along*dy
      if qx*qx+qy*qy<=r*r then return true end
      if (a[2]>y)~=(b[2]>y) and x<a[1]+(y-a[2])*dx/dy then inside=not inside end
      j=i
    end
  end
  return inside
end

function M.intersects(actors,boxes,what,inv,retiring,settings)
  if actors.unknown then return true end -- bounded fail-safe, never truncate actors
  if type(boxes)~='table' or #boxes==0 then return false end
  local r=(what=='walk' or what=='walkcol') and settings.WALK_PLAYER_R or settings.PLAYER_R
  if retiring then r=settings.PLAYER_R end
  local dz=settings.PLAYER_DZ
  for _,world in ipairs(actors.positions) do
    local x,y,z=world.x,world.y,world.z
    if inv then x,y,z=inv:apply(x,y,z) end
    for _,b in ipairs(boxes) do
      if x>=b[1]-r and x<=b[4]+r and y>=b[2]-r and y<=b[5]+r then
        if what=='deck' and not retiring then
          local surf=b[3]+settings.DECK_BOX_BELOW_M
          if z<surf-settings.DECK_ON_M and z>surf-settings.DECK_BOX_BELOW_M-dz then return true end
        elseif z>=b[3]-dz and z<=b[6]+dz
          and (type(b[7])~='table' or nearRings(b[7],x,y,r)) then return true end
      end
    end
  end
  return false
end
return M
