-- Render-only, revisioned replacement groups. Imports are granted by roads.lua's
-- existing shared frame budget; a replacement is exposed only when complete.
local geotile = require('beamngEarth/geotile')
local geodesy = require('beamngEarth/geodesy')
local stopwatch = require('beamngEarth/stopwatch')
local M = {}
M.FAIR_WAIT_S=5
M.SAMPLE_KEEP=256

function M.new(api)
  local self = { entries = {}, closed = {}, closedOrder = {}, serial = 0, api = api,
    samples={},sampleAt=0,queuedParts=0,
    stats={imports=0,failures=0,bytes=0,vertices=0,primitives=0,totalMs=0,worstMs=0,coverageMs=0,covered=0,
           wastedImports=0,wastedBytes=0,wastedMs=0,supersededParts=0,queuePeak=0,worstQueueMs=0,
           visibleGroups=0,visibleMs=0,worstVisibleMs=0} }
  local wall=stopwatch.clock()
  local clock=api.clock or function() return wall()/1000 end
  local function metric(v) return type(v)=='number' and v==v and v>=0 and v<=2147483648 and v or 0 end
  local function work(p)
    local c=p.cost or {}
    return 1+metric(c.bytes)/262144+metric(c.vertices)/8192+metric(c.primitives)/4
  end
  local function close(key, token)
    if not token then return end
    self.closed[key]=token
    self.closedOrder[#self.closedOrder+1]={key,token}
    if #self.closedOrder>256 then
      local old=table.remove(self.closedOrder,1)
      if self.closed[old[1]]==old[2] then self.closed[old[1]]=nil end
    end
  end
  local function hide(id, value)
    if api.hide then api.hide(id,value);return end
    local o = id and scenetree.findObjectById(id)
    if o then o:setHidden(value) end
  end
  local function discard(v, obsolete)
    if not v then return end
    self.queuedParts=self.queuedParts-math.max(0,#v.parts-v.next+1)
    for _, p in ipairs(v.parts) do
      if p.id then
        hide(p.id, true); api.delete(p.id)
        if not v.exposed then
          self.stats.wastedImports=self.stats.wastedImports+1
          self.stats.wastedBytes=self.stats.wastedBytes+metric((p.cost or {}).bytes)
          self.stats.wastedMs=self.stats.wastedMs+(p.importMs or 0)
        end
      end
      if obsolete then self.stats.supersededParts=self.stats.supersededParts+1 end
      api.release(p.slot)
    end
  end
  function self:drop(key)
    local e = self.entries[key]
    if not e then return end
    close(key,e.token)
    for _, g in pairs(e.groups) do discard(g.pending,true); discard(g.shown);discard(g.queued,true) end
    for _,id in ipairs(e.finished) do hide(id,false) end -- final-tile objects have a different owner
    self.entries[key] = nil
    if api.reconcile then api.reconcile(key) end
  end
  function self:complete(key,token)
    if self.entries[key] and self.entries[key].attached then close(key,token);return end
    self:drop(key);close(key,token)
  end
  function self:clear()
    for key in pairs(self.entries) do self:drop(key) end
    self.closed = {};self.closedOrder={};self.anchor=nil;self.focus=nil
  end
  function self:receive(msg, anchorId)
    local function release()
      for w in pairs(msg.slots or {}) do api.release(api.slot(msg,w)) end
    end
    if msg.anchorId ~= anchorId or type(msg.token) ~= 'string' or not geotile.isKey(msg.key) then release(); return false end
    local e = self.entries[msg.key]
    if msg.cancel then
      if e and e.token == msg.token then self:drop(msg.key) end
      close(msg.key,msg.token)
      release(); return true
    end
    if self.closed[msg.key] == msg.token then release(); return false end
    if type(msg.group) ~= 'string' or type(msg.stage) ~= 'number' or msg.stage < 0 or msg.stage > 2
      or type(msg.parts) ~= 'table' then release(); return false end
    local frame = geotile.frameOf({frame=msg.frame,key=msg.key})
    if not frame then release(); return false end
    if e and e.token ~= msg.token then self:drop(msg.key); e=nil end
    if not e then e={token=msg.token,frame=frame,groups={},finished={},done=0,key=msg.key}; self.entries[msg.key]=e end
    e.total=tonumber(msg.total) or 0
    local g=e.groups[msg.group] or {latest=-1,at=clock()}; e.groups[msg.group]=g
    if msg.stage <= g.latest then release(); return false end
    local parts={}
    for w,p in pairs(msg.parts) do
      if type(w)~='string' or type(p)~='table' or type(p.shape)~='string' or type(p.pos)~='table' then release(); return false end
      if p.cost~=nil and type(p.cost)~='table' then release();return false end
      if p.center~=nil then
        if type(p.center)~='table' or #p.center~=3 then release();return false end
        for _,v in ipairs(p.center) do
          if type(v)~='number' or v~=v or math.abs(v)>1e8 then release();return false end
        end
      end
      local sl=api.slot(msg,w)
      parts[#parts+1]={what=w,shape=sl and sl.path or p.shape,pos=p.pos,pivot=p.pivot or 0,slot=sl,stage=msg.stage,
                       center=p.center,cost=p.cost}
    end
    if #parts==0 then release(); return false end
    table.sort(parts,function(a,b) return a.what<b.what end)
    self.serial=self.serial+1
    local incoming={stage=msg.stage,parts=parts,next=1,order=self.serial,at=clock()}
    g.latest=msg.stage
    if not g.shown and g.pending then
      -- Preserve the first cheap coverage even when the producer outruns imports.
      discard(g.queued,true);g.queued=incoming
    else discard(g.pending,true);g.pending=incoming end
    self.queuedParts=self.queuedParts+#parts
    self.stats.queuePeak=math.max(self.stats.queuePeak,self.queuedParts)
    e.at=clock(); return true
  end
  function self:covers(key)
    local e=self.entries[key]
    if not e or e.total<=0 then return false end
    local n=e.done
    for _,g in pairs(e.groups) do if g.shown then n=n+1 end end
    return n>=e.total
  end
  function self:visibility(key, coordinated)
    if api.reconcile and not coordinated then api.reconcile(key); return end
    local e=self.entries[key]
    if not e then return end
    if self:covers(key) and api.hideFar then api.hideFar(key) end
    local hidden=(api.blocked and api.blocked(key))
      or (api.farVisible and api.farVisible(key) and not self:covers(key))
    for _,id in ipairs(e.finished) do hide(id,hidden or false) end
    for _,g in pairs(e.groups) do if g.shown then
      for _,p in ipairs(g.shown.parts) do hide(p.id,hidden or false) end
      if not hidden then
        g.shown.exposed=true
        if not g.seen then
          local ms=math.max(0,(clock()-(g.at or g.shown.at))*1000)
          self.stats.visibleGroups=self.stats.visibleGroups+1
          self.stats.visibleMs=self.stats.visibleMs+ms
          self.stats.worstVisibleMs=math.max(self.stats.worstVisibleMs,ms)
          g.seen=true
        end
      end
    end end
  end
  local function placed(e,p,a)
    local pl=geotile.placement(e.frame,a,0,0,p.pivot)
    local xf=geodesy.transformOf(pl.r,pl.t)
    local x,y,z=xf:apply(p.pos[1],p.pos[2],p.pos[3])
    return {shape=p.shape,pos={x,y,z},rot={xf:beamngQuat()},nativeLod=p.stage==2}
  end
  function self:place(a)
    if self.anchor==a then return end
    self.anchor=a;self.focus=nil
    for _,e in pairs(self.entries) do
      for _,g in pairs(e.groups) do
        for _,v in pairs({shown=g.shown,pending=g.pending,queued=g.queued}) do
          for _,p in ipairs(v.parts) do
            local o=p.id and scenetree.findObjectById(p.id)
            if o then local w=placed(e,p,a);o:setPosRot(w.pos[1],w.pos[2],w.pos[3],unpack(w.rot)) end
          end
        end
      end
    end
  end
  function self:prepare(a,focus,camera)
    if not a then return nil end
    self:place(a)
    local at=clock();local velocity={0,0}
    local fx=focus and (focus.x or focus[1] or 0);local fy=focus and (focus.y or focus[2] or 0)
    if fx and self.focus then
      local dt=at-self.focus.at
      if dt>.001 and dt<2 then
        local vx,vy=(fx-self.focus.x)/dt,(fy-self.focus.y)/dt
        if vx*vx+vy*vy<=150*150 then velocity={vx,vy} end -- teleports have no prediction
      end
    end
    if fx then self.focus={x=fx,y=fy,at=at} end
    local entry,group,version,bestMissing,bestBenefit,bestLate,bestAt
    for key,e in pairs(self.entries) do
      if not e.attached and at-(e.at or 0)>120 then self:drop(key)
      else for _,g in pairs(e.groups) do
        if g.pending then
          local missing=not g.shown and 0 or 1
          local distance=0;local approach=0;local facing=1
          if focus then
            local part=g.pending.parts[1]
            local p=placed(e,{pos=part.center or part.pos,pivot=0},a).pos
            local dx,dy=p[1]-fx,p[2]-fy
            distance=math.sqrt(dx*dx+dy*dy)
            approach=math.max(0,(dx*velocity[1]+dy*velocity[2])/math.max(1,distance))
            local hx,hy=camera and camera.fx,camera and camera.fy
            if type(hx)=='number' and type(hy)=='number' then
              local length=math.sqrt(hx*hx+hy*hy)
              if length>.001 and length<2 and distance>.001 then
                facing=1+2*math.max(0,(dx*hx+dy*hy)/(distance*length))
              end
            end
          end
          local effort=0
          for i=g.pending.next,#g.pending.parts do effort=effort+work(g.pending.parts[i]) end
          local predictedMs=math.max(.1,(self.msPerWork or 1)*effort)
          -- Strict missing-coverage priority; within it, bounded-age fairness
          -- precedes approaching-camera benefit per measured import work.
          local reach=math.max(0,distance-approach*2)
          local benefit=facing*(1+math.min(120,at-g.pending.at)/4)/(1+reach/64)/predictedMs
          local late=at-g.pending.at>=M.FAIR_WAIT_S
          if not version or missing<bestMissing or (missing==bestMissing and
            ((late and not bestLate) or (late==bestLate and
              ((late and (g.pending.at<bestAt or (g.pending.at==bestAt and g.pending.order<version.order))) or
               (not late and (benefit>bestBenefit or (benefit==bestBenefit and g.pending.order<version.order))))))) then
            entry,group,version=e,g,g.pending;bestMissing,bestBenefit,bestLate,bestAt=missing,benefit,late,g.pending.at
          end
        end
      end end
    end
    if not version then return nil end
    local p=version.parts[version.next]
    return {entry=entry,group=group,version=version,part=p,anchor=a,
            ms=math.min(10000,math.max(.1,(self.msPerWork or 3)*work(p)))}
  end
  function self:step(a,focus,choice)
    choice=choice or self:prepare(a,focus)
    if not choice then return false end
    local entry,group,version,p=choice.entry,choice.group,choice.version,choice.part
    if choice.anchor~=a or self.entries[entry.key]~=entry or group.pending~=version
      or version.parts[version.next]~=p then return false end
    local queueMs=math.max(0,(clock()-version.at)*1000)
    self.stats.worstQueueMs=math.max(self.stats.worstQueueMs,queueMs)
    local started=clock()
    local ok,id=pcall(api.create,placed(entry,p,a))
    local ms=math.max(0,(clock()-started)*1000)
    self.stats.totalMs=self.stats.totalMs+ms;self.stats.worstMs=math.max(self.stats.worstMs,ms)
    self.sampleAt=self.sampleAt%M.SAMPLE_KEEP+1
    self.samples[self.sampleAt]={ms=ms,queueMs=queueMs,failed=not ok or not id}
    if not ok or not id then
      self.stats.failures=self.stats.failures+1
      discard(version);group.pending=group.queued;group.queued=nil;return true
    end -- keep last good stage
    if ms>0 then self.msPerWork=self.msPerWork and self.msPerWork*.8+ms/work(p)*.2 or ms/work(p) end
    self.stats.imports=self.stats.imports+1
    for _,k in ipairs({'bytes','vertices','primitives'}) do self.stats[k]=self.stats[k]+metric((p.cost or {})[k]) end
    p.id=id;p.importMs=ms;hide(id,true);api.made(id,p.shape);version.next=version.next+1
    self.queuedParts=self.queuedParts-1
    if version.next>#version.parts then
      if not group.shown then
        self.stats.coverageMs=self.stats.coverageMs+math.max(0,(clock()-version.at)*1000)
        self.stats.covered=self.stats.covered+1
      end
      -- A complete group can still be hidden behind incomplete far/near
      -- coverage. Only mark it useful when visibility actually exposes it.
      discard(group.shown);group.shown=version;group.pending=group.queued;group.queued=nil
      self:visibility(entry.key)
    end
    return true
  end
  function self:diagnostics()
    local out={}
    for k,v in pairs(self.stats) do out[k]=v end
    local pending,parts,oldest=0,0,0
    local at=clock()
    for _,e in pairs(self.entries) do for _,g in pairs(e.groups) do
      for _,v in pairs({pending=g.pending,queued=g.queued}) do
        pending=pending+1;parts=parts+#v.parts-v.next+1
        oldest=math.max(oldest,math.max(0,(at-v.at)*1000))
      end
    end end
    out.pendingGroups=pending;out.pendingParts=parts;out.oldestQueueMs=oldest
    local times,queues={},{}
    for _,s in ipairs(self.samples) do times[#times+1]=s.ms;queues[#queues+1]=s.queueMs end
    table.sort(times);table.sort(queues)
    out.sampleCount=#times
    for _,p in ipairs({50,95,99}) do
      out['importP'..p..'Ms']=times[math.max(1,math.ceil(#times*p/100))] or 0
      out['queueP'..p..'Ms']=queues[math.max(1,math.ceil(#queues*p/100))] or 0
    end
    out.msPerWork=self.msPerWork or 3
    return out
  end
  function self:attach(t,msg)
    local e=self.entries[t.gkey]
    close(t.gkey,msg.buildingProgressToken)
    if not e or e.token~=msg.buildingProgressToken then
      if e then self:drop(t.gkey) end
      -- Warm cache hits and clients without previews need the same complete-set
      -- handover as progressive imports. Otherwise each final chunk appears on
      -- top of the still-visible far mesh while the rest are loading.
      e={token=msg.buildingProgressToken,frame=t.frame,groups={},finished={},done=0,key=t.gkey}
      self.entries[t.gkey]=e
    end
    for _,g in pairs(e.groups) do
      discard(g.queued);g.queued=nil
      if g.shown then discard(g.pending);g.pending=nil end
    end
    t.progressGroups=t.data.buildingGroups or {}
    if #t.progressGroups==0 then
      local visual={}
      for what in pairs(t.parts) do
        if what=='bld' or what:match('^bld%d+$') then visual[#visual+1]=what end
      end
      table.sort(visual)
      t.progressGroups=#visual>0 and {{group='final',visual=visual}} or {}
    end
    if #t.progressGroups==0 then self:drop(t.gkey);return end
    e.completed={};e.total=#t.progressGroups;e.attached=t
    for _,row in ipairs(t.progressGroups) do
      local g=e.groups[row.group];local v=g and g.shown
      local fits=v and v.stage==2 and #v.parts==#row.visual
      if fits then
        for _,p in ipairs(v.parts) do
          if not t.parts[p.what] or t.exactShape[p.what] then fits=false;break end
        end
      end
      if fits then
        for _,p in ipairs(v.parts) do
          api.release(t.slots[p.what]);t.slots[p.what]=p.slot
          t[p.what]=p.id;t.parts[p.what].shape=p.shape
          e.finished[#e.finished+1]=p.id
        end
        e.groups[row.group]=nil
        e.completed[row.group]=true
        e.done=e.done+1
      end
    end
    self:sync(t)
  end
  function self:replaceInstance(t,oldId,newId)
    local e=self.entries[t.gkey]
    if e and e.attached==t then
      for i,id in ipairs(e.finished) do if id==oldId then e.finished[i]=newId end end
    end
  end
  function self:sync(t)
    local e=self.entries[t.gkey]
    if not e or e.attached~=t or not t.progressGroups then return end
    local allComplete=true
    for _,row in ipairs(t.progressGroups) do
      local g=e.groups[row.group]
      if not e.completed[row.group] then
        local complete=true
        for _,what in ipairs(row.visual) do if not t[what] then complete=false;break end end
        for _,what in ipairs(row.visual) do hide(t[what],not complete) end
        if complete then
          for _,what in ipairs(row.visual) do e.finished[#e.finished+1]=t[what] end
          if g then discard(g.shown);discard(g.pending);discard(g.queued) end
          e.groups[row.group]=nil;e.completed[row.group]=true;e.done=e.done+1
        else allComplete=false end
      end
    end
    self:visibility(t.gkey)
    if allComplete then self.entries[t.gkey]=nil end
  end
  function self:held(session)
    local out={}
    for _,e in pairs(self.entries) do for _,g in pairs(e.groups) do
      for _,v in pairs({shown=g.shown,pending=g.pending,queued=g.queued}) do for _,p in ipairs(v.parts) do
        if p.slot and p.slot[3]==session then out[#out+1]={p.slot[1],p.slot[2]} end
      end end
    end end
    return out
  end
  function self:hasWork()
    for _,e in pairs(self.entries) do for _,g in pairs(e.groups) do if g.pending then return true end end end
    return false
  end
  return self
end
return M
