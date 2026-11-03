-- Revision dissolves use complementary screen-space coverage, not transparency.
-- Requests are committed together after coverage reconciliation. A second wave
-- waits for the first, so rapid revisions cannot stack three partial versions.
local M = {DURATION=.4, MAX_DT=.05}
function M.new(api)
  api=api or {}
  local self={objects={},active={},pending={},enabled=api.enabled}
  if self.enabled==nil then
    self.enabled=FS and FS.fileExists and FS:fileExists('/shaders/beamngEarth/buildingFade.ready') or false
  end
  local clock=api.clock or require('beamngEarth/stopwatch').clock()
  local last=clock()
  local function object(id) return scenetree.findObjectById(id) end
  local function mask(o,threshold,outgoing)
    -- Unused palette channel: exact byte marker isolates this shader feature
    -- from vehicles, terrain, other mods, and ordinary TSStatic instances.
    o:setField('instanceColor2',0,string.format('%.9f %d %.9f %.9f',threshold,outgoing and 1 or 0,173/255,91/255))
    o:updateInstanceRenderData()
  end
  function self:register(id)
    local o=object(id)
    if not self.enabled or not o or not o.updateInstanceRenderData then return end
    o:setField('useInstanceRenderData',0,'true')
    o:setHidden(true)
    self.objects[id]={hidden=true}
  end
  function self:hide(id,hidden)
    if not id then return end
    local r=self.objects[id]
    if not r then local o=object(id);if o then o:setHidden(hidden) end;return end
    self.pending[id]=hidden -- false is a request too
  end
  function self:commit()
    if next(self.active) then return end
    for id,hidden in pairs(self.pending) do
      local r,o=self.objects[id],object(id)
      if r and o and r.hidden~=hidden then
        self.active[id]={outgoing=hidden,t=0}
        mask(o,0,hidden);o:setHidden(false)
      end
    end
    self.pending={}
  end
  function self:update()
    local now=clock();local dt=math.max(0,math.min(M.MAX_DT,(now-last)/1000));last=now
    for id,a in pairs(self.active) do
      local o,r=object(id),self.objects[id]
      if not o or not r then self.active[id]=nil;self.objects[id]=nil
      else
        a.t=math.min(1,a.t+dt/M.DURATION)
        local t=a.t*a.t*(3-2*a.t)
        mask(o,t,a.outgoing)
        if a.t>=1 then
          r.hidden=a.outgoing;o:setHidden(r.hidden)
          self.active[id]=nil
        end
      end
    end
  end
  function self:held(id)
    local r=self.objects[id]
    return r and (self.active[id]~=nil or self.pending[id]~=nil or not r.hidden) or false
  end
  function self:forget(id)
    self.objects[id]=nil;self.pending[id]=nil;self.active[id]=nil
  end
  function self:finish()
    -- Before rebase/teardown: retired objects have no tile owner to move them.
    for id,a in pairs(self.active) do
      local o,r=object(id),self.objects[id]
      if o and r then mask(o,1,a.outgoing);r.hidden=a.outgoing;o:setHidden(r.hidden) end
    end
    self.active={}
    for id,hidden in pairs(self.pending) do
      local o,r=object(id),self.objects[id]
      if o and r then mask(o,1,hidden);r.hidden=hidden;o:setHidden(hidden) end
    end
    self.pending={}
  end
  function self:clear() self:finish();self.objects={} end
  function self:busy() return next(self.active)~=nil or next(self.pending)~=nil end
  return self
end
return M
