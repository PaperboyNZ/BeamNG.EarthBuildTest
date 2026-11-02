-- Generated hardscape wins over vegetation regardless of arrival/rebase order.
local dir=(arg[0]:match('^(.*)[/\\]') or '.')
local T=dofile(dir..'/testlib.lua')
local S=dofile(dir..'/stubs.lua')
local live={}
local create=createObject
createObject=function(class)
  local o=create(class)
  if class=='Forest' then
    local fd={}
    function fd:createNewItem(data,m,sc)
      local it={data=data,pos=vec3(m.p),scale=sc}; live[it]=true; return it
    end
    function fd:removeItem(it) live[it]=nil end
    function o:getData() return fd end
  end
  return o
end
worldEditorCppApi={createObject=function(class) return createObject(class) end}
Sim={getDataBlockSet=function() return {addObject=function() end} end}
MatrixF=function() return {setFromEuler=function() end,setPosition=function(self,p) self.p=vec3(p) end} end
local trees=require('beamngEarth/trees')
local roads=require('beamngEarth/roads')
-- This fixture advances frames without wall-clock delays; permit the deferred
-- collision rebuild so physical retirement can finish on a following frame.
roads.RELOAD_EVERY_S,roads.RELOAD_DELETES_S,roads.URGENT_GAP_S=0,0,0
local geodesy=require('beamngEarth/geodesy')
local geotile=require('beamngEarth/geotile')
trees.EVERY_N,trees.FRAME_MS,trees.POOL_SPARE,trees.PER_FRAME=1,math.huge,0,10000
trees.SHAPE_ITEMS_PER_FRAME=math.huge
local function count() local n=0; for _ in pairs(live) do n=n+1 end; return n end
local function run(aid,p,n) for _=1,n or 8 do trees.update(aid,p or {x=10,y=10}) end end
local function clean()
  roads.clear(); trees.clear(); trees.clearSurfaceExclusions('fixture')
end
local function pavement(hole)
  local rings={{{0,0},{20,0},{20,20},{0,20}}}
  if hole then rings[2]={{5,5},{15,5},{15,15},{5,15}} end
  return {v=1,polygons={{rings=rings,min_z=-.1,max_z=.4,kind='pavement'}}}
end
local function vegetation(rows,groups,key,aid)
  trees.onTile({anchorId=aid or 1,key=key or '0_0',path='inline',
    data={groups=groups or {'rock','shrub','deciduous'},items=rows}},aid or 1)
end

-- These compact aliases are stock shapes with CDAE-measured, origin-centred
-- enclosing XY bounds. Their minimum scale must not shrink the safety mask.
local shrub, shrubScale, shrubHeight=trees.pick('site_shrub',.1,0)
local rock, rockScale, rockHeight=trees.pick('site_rock',.1,0)
T.check(shrub:find('generibush_small',1,true)~=nil and shrubScale==.3,'compact shrub uses the stock bush and minimum scale')
T.check(rock:find('eca_rock_small',1,true)~=nil and rockScale==.3,'compact rock uses the stock rock and minimum scale')
T.check(trees.surfaceRadius('site_shrub',.1,1,shrubHeight)>=2.276*.3+.25,'shrub mask contains the full minimum-size stock asset')
T.check(trees.surfaceRadius('site_rock',.1,1,rockHeight)>=1.202*.3+.25,'rock mask contains the full minimum-size stock asset')
T.check(trees.surfaceRadius('site_shrub',.1,.3,shrubHeight)==trees.surfaceRadius('site_shrub',.1,1,shrubHeight),
  'unused row scale cannot shrink the stock shape mask')

T.check(trees.SURFACE_MAX_POLYGONS>=8192 and trees.SURFACE_MAX_VERTICES>=131072,'producer limits accepted')
T.check(trees.surfaceRadius('rock',2,1)>1.2+.24,'asset envelope and rounding margin expand the source footprint')
T.check(trees.surfaceRadius('deciduous',10,.5)==trees.surfaceRadius('deciduous',10,1),
  'unused subunit row scale cannot shrink the actual rendered crown')
T.check(trees.surfaceRadius('deciduous',.01,1,8)>trees.surfaceRadius('deciduous',.01,1),
  'selected asset minimum scale contributes its actual catalogue height')
trees.setSurfaceExclusions('fixture',pavement(true),nil,{0,0,20,20})
T.check(trees.surfaceBlocked('rock',2,2,0,.6,1),'rock on paving suppressed')
T.check(trees.surfaceBlocked('site_shrub',2,2,.5,1.,1),'raised origin still checks stock foliage below it')
T.check(trees.surfaceBlocked('rock',21,2,0,.6,1),'whole rock envelope crossing pavement edge suppressed')
T.check(not trees.surfaceBlocked('rock',25,2,0,.6,1),'rock clear of paving survives')
T.check(not trees.surfaceBlocked('shrub',10,10,0,2,1),'whole bush fits in a garden hole')
T.check(trees.surfaceBlocked('shrub',14.5,10,0,2,1),'bush crown crossing garden edge is suppressed')
T.check(not trees.surfaceBlocked('bench',2,2,0,1,1),'street props exempt by group')
T.check(not trees.surfaceBlocked('rock',2,2,10,.6,1),'plant above a different surface level retained')
local deck=pavement(false); deck.polygons[1].min_z,deck.polygons[1].max_z=8,8.4
trees.setSurfaceExclusions('fixture',deck,nil,{0,0,20,20})
T.check(not trees.surfaceBlocked('shrub',10,10,0,2,1),'low growth beneath a raised deck retained')
T.check(trees.surfaceBlocked('deciduous',10,10,0,10,1),'tree extending into raised paving suppressed')
clean()

-- Compact road-prop rows share natural mask lifecycle: a late hard surface
-- removes the intersecting plant and retiring it restores the same stock item.
trees.onRows(1,'compact',{{0,2,2,0,0,1,.7,0},{1,10,10,0,0,1,.3,0}}, {'site_shrub','site_rock'})
run(1); T.check(count()==2,'compact stock rows render before hardscape')
trees.setSurfaceExclusions('fixture',pavement(true),nil,{0,0,20,20}); run(1)
T.check(count()==1,'compact plant on hardscape is suppressed and garden rock remains')
trees.clearSurfaceExclusions('fixture'); run(1)
T.check(count()==2,'retiring hardscape restores compact plant')
clean()

-- A newer server may send an alias unknown to an older client. The row is
-- hidden rather than falling back to the generic deciduous catalogue.
local savedCompact=trees.CATALOG.site_shrub
trees.CATALOG.site_shrub=nil
trees.onRows(1,'unknown-compact',{{0,10,10,0,0,1,.7,0}}, {'site_shrub'})
run(1); T.check(count()==0,'unknown compact group never renders a fallback tree')
trees.CATALOG.site_shrub=savedCompact
clean()

-- Vegetation first: both existing items and future respawns obey the final mask.
local rows={{0,2,2,0,0,1,.6,0},{0,21,2,0,0,1,.6,0},
  {1,10,10,0,0,1,2,0},{2,35,10,0,0,1,10,0}}
vegetation(rows); run(1)
T.check(count()==4,'natural rows initially visible')
trees.setSurfaceExclusions('fixture',pavement(true),nil,{0,0,20,20}); run(1)
T.check(count()==2,'late paving removes already spawned intersecting plants')
trees.clearSurfaceExclusions('fixture'); run(1)
T.check(count()==4,'retired owner restores deterministic source vegetation')
trees.clear()
trees.setSurfaceExclusions('fixture',pavement(true),nil,{0,0,20,20})
vegetation(rows); run(1)
T.check(count()==2,'mask first gives the same vegetation result')
clean()

-- Street-tree rows share the natural group policy; benches and garden plants do not disappear.
trees.onRows(1,'p0_0',{{0,2,2,0,0,1,4,0},{0,10,10,0,0,1,4,0},{1,2,3,0,0,1,.9,0}},
  {'deciduous','bench'})
run(1); T.check(count()==3,'mixed authored rows initially visible')
T.check(roads.onTile({anchorId=1,key='0_0',path='inline',data={chunks={},vegetationExclusions=pavement(true)}},1),
  'road manifest accepted')
run(1); T.check(count()==2,'street tree on paving removed while garden tree and bench survive')
roads.onDrop({anchorId=1,key='0_0'}); run(1)
T.check(count()==3,'road retirement releases its exclusion owner')
clean()

-- A mask change only invalidates intersecting vegetation tiles, not every scene row.
vegetation(rows)
local far={}; for i=1,100 do far[#far+1]={0,10000+i,10,0,0,1,12,0} end
trees.onRows(1,'40_0',far,{'deciduous'}); run(1)
trees.setSurfaceExclusions('fixture',pavement(true),nil,{0,0,20,20})
trees.update(1,{x=10,y=10})
T.check(trees.lastRows==#rows,'late mask scans affected tile rows only')
clean()

-- Malformed/oversized data fails closed inside the owning road tile, never globally.
T.check(not trees.setSurfaceExclusions('fixture',{v=2,polygons={}},nil,{0,0,20,20}),'unknown version rejected')
T.check(trees.surfaceBlocked('rock',10,10,0,.6,1),'malformed envelope still excludes its affected tile')
T.check(not trees.surfaceBlocked('rock',500,500,0,.6,1),'malformed envelope does not exclude unrelated gardens')
local bad=pavement(); bad.polygons[1].rings[1][1][1]=0/0
T.check(not trees.setSurfaceExclusions('fixture',bad,nil,{0,0,20,20}),'nonfinite polygon rejected')
T.check(not trees.setSurfaceExclusions('fixture',{v=1,polygons={bad='object'}},nil,{0,0,20,20}),
  'object masquerading as an array rejected')
local many={v=1,polygons={}}
local small={rings={{{0,0},{1,0},{1,1},{0,1}}},min_z=0,max_z=.4,kind='pavement'}
for i=1,trees.SURFACE_MAX_POLYGONS do many.polygons[i]=small end
T.check(trees.setSurfaceExclusions('fixture',many,nil,{0,0,20,20}),'full producer polygon limit accepted')
T.check(trees.surfaceBlocked('rock',25,25,0,.6,1) and (trees.surfaceQueryOverflow or 0)>0,
  'overfull local query is bounded and conservative')
many.polygons[#many.polygons+1]=small
T.check(not trees.setSurfaceExclusions('fixture',many,nil,{0,0,20,20}),'polygon overflow diagnosed')
local soft=pavement(); soft.polygons[1].kind='garden'
T.check(trees.setSurfaceExclusions('fixture',soft,nil,{0,0,20,20}),'explicit soft surface is harmless')
T.check(not trees.surfaceBlocked('shrub',10,10,0,2,1),'garden record does not ban planting')
clean()

-- Unknown-height sentinels must not turn into kilometre-wide XY shadows at a rebase.
local unknown=pavement(); unknown.polygons[1].unknown_height=true
unknown.polygons[1].min_z,unknown.polygons[1].max_z=-1e6,1e6
local shear={r={1,0,0,0,1,0,0,0,1},t={100,200,0},c={.01,.02,0},pz=0}
trees.setSurfaceExclusions('fixture',unknown,shear,{100,200,120,220})
T.check(trees.surfaceBlocked('rock',110,210,10000,.6,1),'unknown vertical placement remains conservative')
T.check(not trees.surfaceBlocked('rock',500,500,0,.6,1),'unknown-height sentinel does not expand XY bounds')
clean()

-- Actual roads/vegetation geotile integration, including Forest move/flush and owner retirement.
roads.setGeo(true)
local gx,gy=geotile.tileOf(0,0)
local key=geotile.key(gx,gy)
local lat,lon=geotile.centre(17,gx,gy)
local source=geodesy.newAnchor(lat,lon)
local A,B=geodesy.newAnchor(0,0),geodesy.newAnchor(0,.05)
local function pose(a) local x,y=geotile.apply(geotile.placement(source,a,0,0,0),0,0,0); return {x=x,y=y} end
local data={groups={'rock','shrub'},items={{0,0,0,0,0,1,.6,0},{1,30,30,0,0,1,2,0}}}
trees.onTile({anchorId=1,key=key,path='inline',frame={lat,lon},data=data},1,A)
run(1,pose(A)); T.check(count()==2,'geotile vegetation initially visible')
local mask={v=1,polygons={{rings={{{-10,-10},{10,-10},{10,10},{-10,10}}},min_z=-.1,max_z=.4,kind='driveway'}}}
local content={chunks={},vegetationExclusions=mask}
T.check(roads.onTile({anchorId=1,key=key,path='inline',frame={lat,lon},h='surface-test',data=content},1,A),
  'geotile road owns frame-local mask')
run(1,pose(A)); T.check(count()==1,'late geotile paving removes natural rock')
trees.transform(A:worldTransformTo(B,0,0,0),geodesy,B)
roads.replace(B,2)
run(2,pose(B),12); T.check(count()==1,'rebase keeps the same plant suppressed')
trees.clear() -- retained road content survives a disconnect; its mask must survive too
trees.onTile({anchorId=2,key=key,path='inline',frame={lat,lon},data=data},2,B)
run(2,pose(B)); T.check(count()==1,'vegetation reload cannot bypass a retained road owner')
roads.onDrop({anchorId=2,key=key}); run(2,pose(B))
T.check(count()==2,'geotile retirement restores its natural source rows')
clean()

-- Retirement is complete only after queued paving objects and pooled references go.
roads.setGeo(false)
roads.setSession('surface-retirement')
local gov={blockDeletes=false}
function gov:try(kind) return not (self.blockDeletes and kind=='roadDelete') end
function gov:charge() end
function gov:chargeMotion() end
local function meshTile(serial)
  return {anchorId=1,key='0_0',path='inline',slots={walk={'/slots/slot_88.cdae',serial}},
    data={chunks={},walk={shape='/vfs/walk.cdae',pos={0,0,0}},vegetationExclusions=pavement(false)}}
end
local function roadRun(n) for _=1,n or 6 do roads.update(gov,1,{x=10,y=10,z=0}) end end
vegetation({{0,2,2,0,0,1,.6,0}})
roads.onTile(meshTile(1),1); roadRun(); run(1)
T.check(count()==0,'visible paving excludes its natural prop')
roads.onDrop({anchorId=1,key='0_0'})
gov.blockDeletes=true; roadRun(); run(1)
T.check(trees.surfaceBlocked('rock',2,2,0,.6,1) and count()==0,
  'queued physical paving deletion retains its mask')
gov.blockDeletes=false; roadRun(); run(1)
T.check(not trees.surfaceBlocked('rock',2,2,0,.6,1) and count()==1,
  'mask releases after physical deletion and pooled-reference retirement')
roads.onTile(meshTile(2),1); roadRun(); run(1)
roads.onDrop({anchorId=1,key='0_0'})
roads.onTile(meshTile(3),1); roadRun(); run(1)
T.check(count()==0 and trees.surfaceBlocked('rock',2,2,0,.6,1),
  'same-key replacement survives old deletion-queue drain')
roads.onDrop({anchorId=1,key='0_0'})
roads.reset()
T.check(not trees.surfaceBlocked('rock',2,2,0,.6,1),'level reset clears pending retiring mask owners')
clean()

-- Furniture can stand on paving, but a later neighbouring access mask wins.
local access=pavement(false); access.polygons[1].kind='access'
trees.onRows(1,'street-clearance',{{0,2,2,0,0,1,1.1,0},{1,25,2,0,0,1,.9,0}}, {'bin','hydrant'})
run(1); T.check(count()==2,'roadside furniture initially visible')
trees.setSurfaceExclusions('fixture',pavement(false),nil,{0,0,20,20});run(1)
T.check(count()==2,'ordinary paving permits clear furniture zones')
trees.setSurfaceExclusions('fixture',access,nil,{0,0,20,20});run(1)
T.check(count()==1,'late neighbouring driveway removes an existing bin')
T.check(trees.surfaceBlocked('hydrant',20.2,2,0,.9,1),'hydrant envelope overlaps access despite centre outside')
T.check(not trees.surfaceBlocked('door',2,2,0,2,1),'entrance geometry is not roadside decoration')
T.check(not trees.surfaceBlocked('bin',2,2,10,1.1,1),'independent bridge level is retained')
trees.clearSurfaceExclusions('fixture');run(1)
T.check(count()==2,'retiring access restores deterministic furniture')
local shifted={apply=function(_,x,y,z) return x+100,y+200,z end}
trees.setSurfaceExclusions('fixture',access,shifted,{100,200,120,220})
T.check(trees.surfaceBlocked('bin',102,202,0,1.1,1),'rebased furniture mask follows owner frame')
T.check(not trees.surfaceBlocked('bin',2,2,0,1.1,1),'old frame is no longer blocked')
clean()

-- The lens is offset and elevated: every member must query the support, then
-- translate together when a late route occupies the original position.
local meta={root={2,2,0},group='streetlight',height=9,scale=1,choices={{0,0,0},{24,0,0}}}
trees.onRows(1,'assembly',{{0,2,2,0,0,1,9,0,meta},{1,4,2,8,0,1,1,0,meta}},
  {'streetlight','lamplens'},nil,'assembly-light')
run(1);T.check(count()==2,'complete lamp assembly initially visible')
trees.setSurfaceExclusions('fixture',access,nil,{0,0,20,20});run(1)
T.check(count()==2,'late access relocates lamp instead of deleting it')
local positions={};for it in pairs(live) do positions[it.pos.x]=true end
T.check(positions[26] and positions[28],'support and offset lens move together')
local lights=require('beamngEarth/nightlights').nearest(28,2,10,10)
T.check(#lights==1 and lights[1][1]==28,'night light follows relocated lens')
trees.clearSurfaceExclusions('fixture');run(1)
positions={};for it in pairs(live) do positions[it.pos.x]=true end
T.check(positions[2] and positions[4],'retiring route restores the assembly deterministically')
trees.setSurfaceExclusions('fixture',{v=0},nil,{0,0,100,100});run(1)
T.check(count()==2,'malformed vegetation fallback does not erase street furniture')
clean()

-- Model the engine's cached collision separately from live Forest rendering.
-- It must refresh at the new support position, including solid removals during
-- a partial cleanup pass and solid -> non-solid distance changes.
local physical={}
local reload=be.reloadCollision
be.reloadCollision=function()
  reload();physical={}
  for it in pairs(live) do
    if it.data.fields.collidable=='1' then physical[it.pos.x]=true end
  end
end
local function refresh()
  local before=S.calls.reloadCollision or 0
  roads.update(gov,1,{x=10,y=10,z=0})
  return (S.calls.reloadCollision or 0)-before
end
for _,kind in ipairs({'streetlight','bin','hydrant','bench'}) do
  clean()
  local m={root={2,2,0},group=kind,height=2,scale=1,choices={{0,0,0},{24,0,0}}}
  trees.onRows(1,'solid-move',{{0,2,2,0,0,1,2,0,m}},{kind})
  run(1);be:reloadCollision();roads.collisionRebuilt()
  T.check(physical[2],kind..' begins with collision at its original position')
  trees.setSurfaceExclusions('fixture',access,nil,{0,0,20,20});run(1)
  T.check(refresh()==1,kind..' relocation rebuilds without the ordinary six-second wait')
  T.check(physical[26] and not physical[2],kind..' collider follows its moved visible item')
  trees.clearSurfaceExclusions('fixture');run(1)
  T.check(refresh()==1 and physical[2] and not physical[26],kind..' restored collider leaves no ghost')
  run(1,{x=10000,y=10000})
  T.check(refresh()==1 and not next(physical),kind..' distance removal clears old collision')
end
clean()
trees.onRows(1,'partial-drop',{{0,2,2,0,0,1,1,0},{0,30,2,0,0,1,1,0}},{'bin'})
run(1);be:reloadCollision();roads.collisionRebuilt()
trees.PER_FRAME=1;trees.dropKey('1:partial-drop');trees.update(1,{x=10,y=10})
T.check(count()==1,'drop pauses after its one-item budget')
T.check(refresh()==1 and (physical[2]~=physical[30]),'partial drop refreshes collision before returning')
trees.PER_FRAME=10000;run(1)
T.check(refresh()==1 and not next(physical),'remaining dropped collision is removed')
clean()
local gm={root={2,2,0},group='hydrant',height=1,scale=1,choices={{0,0,0},{24,0,0}}}
trees.onGeoRows('p'..key,key,{{0,2,2,0,0,1,1,0,gm}},{'hydrant'},nil,source,0,A)
run(1,pose(A));be:reloadCollision();roads.collisionRebuilt()
local pa=geotile.placement(source,A,0,0,0)
trees.setSurfaceExclusions('fixture',access,geodesy.transformOf(pa.r,pa.t))
run(1,pose(A));refresh()
local ax=geotile.apply(pa,26,2,0)
T.check(physical[ax],'geotile relocation puts collision at the transformed alternative')
local pb=geotile.placement(source,B,0,0,0)
trees.setSurfaceExclusions('fixture',access,geodesy.transformOf(pb.r,pb.t))
trees.transform(A:worldTransformTo(B,0,0,0),geodesy,B);run(2,pose(B),12)
roads.update(gov,2,pose(B),nil,B)
local bx=geotile.apply(pb,26,2,0)
T.check(physical[bx] and not physical[ax],'rebase rebuilds the relocated collider without old-frame ghosts')
clean()
T.done('test_surface_exclusions')
