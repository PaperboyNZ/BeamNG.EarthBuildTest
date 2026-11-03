package.path='mod/beamng_earth/lua/ge/extensions/?.lua;'..package.path
local M=require('beamngEarth/shared_sites')
local function data(revision,namespace,feature)
  return {key='g17_1_2',sharedSites={v=1,sites={{partition='canonical-ground-v1',identity={namespace=namespace or 'survey',feature_id=feature or 'site'},surface_revision=string.rep(revision,64),sectors={'g17_1_2','g17_2_2'}}}}}
end
assert(M.compatible(data('a'),{},'one'))
assert(M.compatible(data('a'),{one={data=data('b')}},'one'))
assert(M.compatible(data('a'),{two={data=data('a')}},'one'))
assert(not M.compatible(data('b'),{two={data=data('a')}},'one'))
assert(M.compatible(data('b'),{two={data=data('a'),staged=true}},'one'))
local unrelated=data('a','other');unrelated.sharedSites.sites[1].sectors={'g17_9_9'}
assert(M.compatible(data('b'),{two={data=unrelated}},'one'))
assert(not M.compatible(data('z'),{},'one'))
assert(M.compatible({}, {two={data=data('a')}},'one'))
assert(not M.compatible({sharedSites={v=2,sites={}}},{},'one'))
assert(not M.compatible(data('a'),{two={gkey='g17_2_2',data={}}},'one'))
assert(not M.compatible({key='g17_1_2'},{two={data=data('a')}},'one'))
print('shared sites: 11 assertions passed')
