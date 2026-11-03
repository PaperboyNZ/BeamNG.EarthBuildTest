-- Deleted collision shapes can remain referenced by the asynchronous physics
-- rebuild. Follow the same next-update convention as terrainpatch.groundReady;
-- requesting a rebuild alone is not permission to overwrite a pooled file.
local M = {}
function M.new()
  local self = { frame = 0, pending = {} }
  function self:deleted(key) self.pending[key] = false end
  function self:held(key) return self.pending[key] ~= nil end
  function self:submitted()
    for key, at in pairs(self.pending) do
      if at == false then self.pending[key] = self.frame end
    end
  end
  function self:step()
    self.frame = self.frame + 1
    local released = {}
    for key, at in pairs(self.pending) do
      if type(at) == 'number' and at < self.frame then
        self.pending[key] = nil; released[#released + 1] = key
      end
    end
    return released
  end
  function self:clear() self.pending = {} end -- level teardown: engine took all objects
  function self:stats()
    local waitingRebuild,waitingFrame=0,0
    for _,at in pairs(self.pending) do
      if at==false then waitingRebuild=waitingRebuild+1 else waitingFrame=waitingFrame+1 end
    end
    return {awaitingRebuild=waitingRebuild,awaitingFrame=waitingFrame}
  end
  return self
end
return M
