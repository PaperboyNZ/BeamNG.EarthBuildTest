-- Transactions extend roads.lua's existing tile queues and collision rebuild.
-- Staged objects are hidden/noncolliding until all imports are ready. Exactly
-- one candidate and one coalesced later message can belong to an accepted tile.
local M = {}
function M.new(api)
  local self={records={},stats={started=0,committed=0,aborted=0,failed=0,waitingActors=0,admissionWaits=0}}
  function self:canStage() return not api.available or api.available(self.records) end
  function self:peek(key) return self.records[key] end
  function self:finish(r)
    api.commit(r)
    self.records[r.parent]=nil;r.old.physicalReplacement=nil
    self.stats.committed=self.stats.committed+1
    if api.after then api.after(r) end
  end
  function self:busy()
    for _,r in pairs(self.records) do
      if r.phase=='awaitFrame' or r.phase=='rebaseWait' or r.phase=='submitting' then return true end
    end
    return false
  end
  function self:abort(r,reason)
    if r.phase=='awaitFrame' or r.phase=='rebaseWait' then
      if reason=='retire' then r.retire=true end
      return false
    end
    api.destroy(r)
    self.records[r.parent]=nil;r.old.physicalReplacement=nil
    self.stats.aborted=self.stats.aborted+1
    if reason=='failure' then self.stats.failed=self.stats.failed+1 end
    return true
  end
  function self:offer(key,msg,data,aid,anchor,reuse)
    local r=self.records[key]
    if r then
      r.retire=nil;r.old.retireRequested=nil -- the newest offer renews residency
      if (msg.h or data.h)==r.h then api.releaseDuplicate(msg,r);return true end
      if self:abort(r,'superseded') then return self:offer(key,msg,data,aid,anchor,reuse) end
      api.hold(r.old,msg,data,aid);return true
    end
    if reuse then return nil end
    local old=api.lookup(key)
    if not old then return nil end
    if not self:canStage() then
      api.hold(old,msg,data,aid);self.stats.admissionWaits=self.stats.admissionWaits+1;return true
    end
    api.consumePending(old)
    r={kind='content',parent=key,key=key..'#physical',old=old,h=msg.h or data.h,phase='loading',
      aid=aid,msg={},needsSkin=old.skin~=nil}
    for k,v in pairs(msg) do r.msg[k]=v end;r.msg.data=data
    self.records[key]=r;old.physicalReplacement=r
    local ok,result=pcall(api.build,r,r.msg,aid,anchor)
    if not ok or not result then self:abort(r,'failure');return false end
    self.stats.started=self.stats.started+1
    return true
  end
  function self:route(key,hash)
    local r=self.records[key]
    if r and r.kind=='content' and hash==r.h then return r.tile,r end
  end
  function self:patch(key,kind,msg,data,aid,anchor)
    local old=api.lookup(key);if not old then return false end
    local r=self.records[key]
    if r and r.kind~='patch' then return nil end
    if api.holdPatch(old,kind,msg,data,aid,r)==false then return true end
    if r and not self:abort(r,'superseded') then return true end
    return self:resumePatch(key,aid,anchor)
  end
  function self:resumePatch(key,aid,anchor)
    local old=api.lookup(key);local p=old and old.pendingPatch
    if not p or self.records[key] then return false end
    if p.aid~=aid or p.h~=old.h then api.releasePatch(old);return false end
    if not self:canStage() then self.stats.admissionWaits=self.stats.admissionWaits+1;return true end
    if api.normalizePatch then api.normalizePatch(old,p,aid) end
    old.pendingPatch=nil
    local r={kind='patch',parent=key,key=key..'#physical',old=old,h=old.h,phase='loading',
      aid=aid,patchInputs=p.inputs,msg={key=old.gkey,anchorId=aid,h=old.h,data=old.data}}
    self.records[key]=r;old.physicalReplacement=r
    local ok,result=pcall(api.buildPatch,r,aid,anchor)
    api.releasePatchTokens(p)
    if not ok or not result then self:abort(r,'failure');return false end
    self.stats.started=self.stats.started+1;return true
  end
  function self:step()
    self.stats.waitingActors=0
    local work={};for _,r in pairs(self.records) do work[#work+1]=r end
    for _,r in ipairs(work) do
      if r.phase=='loading' or r.phase=='prepared' then
        if r.tile and r.tile.importFailed then self:abort(r,'failure')
        elseif api.ready(r) then
          r.phase='prepared'
          if api.clear(r) then
            if api.direct and api.direct(r) then self:finish(r) else api.requestCollision() end
          else self.stats.waitingActors=self.stats.waitingActors+1 end
        end
      elseif r.phase=='awaitFrame' and api.frame()>r.submittedFrame then
        self:finish(r)
      elseif r.phase=='rebaseWait' then api.requestCollision() end
    end
  end
  function self:beforeRebuild()
    local changed={}
    for _,r in pairs(self.records) do
      if r.phase=='prepared' and api.ready(r) and api.clear(r) then
        local ok,undo=api.swapCollision(r)
        if ok then r.undo=undo;r.phase='submitting';changed[#changed+1]=r
        else r.tile.importFailed=true end
      elseif r.phase=='rebaseWait' then r.wasRebase=true;r.phase='submitting';changed[#changed+1]=r end
    end
    return changed
  end
  function self:submitted(changed,success)
    for _,r in ipairs(changed or {}) do
      if success then r.phase='awaitFrame';r.submittedFrame=api.frame();r.undo=nil;r.wasRebase=nil
      else
        if r.wasRebase then r.wasRebase=nil;r.phase='rebaseWait'
        else
          if r.undo then r.undo() end
          r.undo=nil;r.phase='loading';r.tile.importFailed=true
        end
      end
    end
  end
  function self:drop(key)
    local r=self.records[key]
    if not r then return true end
    if api.cancelPending then api.cancelPending(r.old) end
    if self:abort(r,'retire') then return true end
    r.retire=true;return false
  end
  function self:rebase()
    local work={};for _,r in pairs(self.records) do work[#work+1]=r end
    for _,r in ipairs(work) do
      if not self:abort(r,'rebase') then r.phase='rebaseWait' end
      api.resync()
    end
  end
  function self:clear()
    -- Explicit teardown: roads.lua owns destruction of all map entries.
    for _,r in pairs(self.records) do r.old.physicalReplacement=nil end
    self.records={}
  end
  return self
end
return M
