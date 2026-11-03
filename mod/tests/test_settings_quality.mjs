// Store behavior with a minimal ref/computed adapter; no game or npm install.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import test from 'node:test'

const file = new URL('../beamng_earth/ui/ui-vue/mods/beamngEarth/earthSettingsStore.js', import.meta.url)
const source = readFileSync(file, 'utf8')
const exports = [...source.matchAll(/export (?:const|function) (\w+)/g)].map(m => m[1])
function store() {
  const calls = []
  const code = source.replace(/^import .* from "vue"\r?\n/m, '')
    .replace(/export (const|function) /g, '$1 ')
  const context = vm.createContext({
    ref: value => ({ value }),
    computed: fn => ({ get value() { return fn() } }),
    window: { bngApi: { engineLua: script => calls.push(script) } },
    setInterval, clearInterval, Date, console,
  })
  vm.runInContext(code + `\nglobalThis.api = {${exports.join(',')}}`, context)
  return { ...context.api, calls }
}

test('mode selector and both quality controls appear together once in Graphics', () => {
  const s = store()
  for (const id of ['buildingGenerator', 'buildingQuality', 'groundsQuality']) {
    const owners = s.settingsSchema.filter(c => c.items.some(i => i.id === id))
    assert.equal(owners.length, 1)
    assert.equal(owners[0].name, 'Graphics')
  }
  assert.equal(s.settingsSchema.flatMap(c => c.items).some(i => i.id === 'buildingAdaptive'), false)
})

test('Simple leaves quality choices visible, disabled and unchanged by input/reset', () => {
  const s = store()
  s.config.value = { ...s.defaultSettings, buildingGenerator: 'legacy', buildingQuality: 'ultra', groundsQuality: 'low' }
  const rows = s.visibleItems(s.categoryNamed('Graphics'))
  for (const id of ['buildingQuality', 'groundsQuality']) {
    const item = rows.find(i => i.id === id)
    assert.ok(item)
    assert.equal(s.isItemDisabled(item), true)
    const prior = s.config.value[id]
    s.selectOption(item, 'minimum')
    s.resetSetting(item)
    assert.equal(s.config.value[id], prior)
  }
  assert.equal(s.calls.length, 0)
  assert.equal(rows.some(i => i.id === 'buildingDetailM'), false)
})

test('Advanced enables independent choices and switching mode preserves them', () => {
  const s = store()
  s.config.value = { ...s.defaultSettings, buildingGenerator: 'v2', buildingQuality: 'high', groundsQuality: 'low' }
  const rows = s.categoryNamed('Graphics').items
  const building = rows.find(i => i.id === 'buildingQuality')
  const grounds = rows.find(i => i.id === 'groundsQuality')
  const mode = rows.find(i => i.id === 'buildingGenerator')
  assert.equal(s.isItemDisabled(building), false)
  assert.equal(s.isItemDisabled(grounds), false)
  s.selectOption(building, 'ultra')
  assert.equal(s.config.value.groundsQuality, 'low')
  s.selectOption(grounds, 'very_low')
  assert.equal(s.config.value.buildingQuality, 'ultra')
  s.selectOption(mode, 'legacy')
  assert.equal(s.isItemDisabled(building), true)
  assert.equal(s.config.value.buildingQuality, 'ultra')
  assert.equal(s.config.value.groundsQuality, 'very_low')
  s.selectOption(mode, 'v2')
  assert.equal(s.isItemDisabled(grounds), false)
  assert.equal(s.config.value.groundsQuality, 'very_low')
})
