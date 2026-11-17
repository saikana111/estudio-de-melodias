// Controller unit checks with a small DOM stub; not a real-browser UI test.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'web/index.html'), 'utf8');
const elements = {};
for (const match of html.matchAll(/<[^>]+\bid="([^"]+)"[^>]*>/g)) {
  const tag = match[0];
  elements[match[1]] = {
    value: tag.match(/\bvalue="([^"]*)"/)?.[1] ?? '',
    checked: /\bchecked\b/.test(tag),
    type: tag.match(/\btype="([^"]*)"/)?.[1] ?? '',
    min: tag.match(/\bmin="([^"]*)"/)?.[1] ?? '',
    max: tag.match(/\bmax="([^"]*)"/)?.[1] ?? '',
    tagName: tag.match(/^<(\w+)/)[1].toUpperCase(),
    options: [], add(option) { this.options.push(option); },
    addEventListener() {}, classList: { contains() { return false; } },
  };
}
for (const match of html.matchAll(/<select id="([^"]+)"[^>]*>([\s\S]*?)<\/select>/g)) {
  const el = elements[match[1]];
  for (const option of match[2].matchAll(/<option([^>]*)>([^<]*)<\/option>/g)) {
    const value = option[1].match(/value="([^"]*)"/)?.[1] ?? option[2];
    el.options.push({value});
    if (el.options.length === 1 || option[1].includes('selected')) el.value = value;
  }
}
let selected = 'ensemble';
const context = {
  document: {
    getElementById: id => { assert.ok(elements[id], `Missing control ${id}`); return elements[id]; },
    querySelectorAll: () => [],
    querySelector: selector => selector.endsWith(':checked') ? {value: selected} : {
      set checked(value) { if (value) selected = selector.match(/value=([^\]]+)/)[1]; },
    },
  },
  Option: function(text, value) { this.text = text; this.value = String(value); },
  fetch: async () => ({json: async () => ({available: true, font: 'Test.sf2'})}),
  console,
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(root, 'web/es.js'), 'utf8'), context);
vm.runInContext(fs.readFileSync(path.join(root, 'web/app.js'), 'utf8'), context);
const settings = () => JSON.parse(vm.runInContext('JSON.stringify(settings())', context));
(async () => {
  assert.equal(settings().mode, 'ensemble');
  assert.equal(settings().brief.intensidad, 68);
  assert.equal(settings().song.expresion_secciones, null);
  elements.intensity.value = '85';
  elements.dynamics.value = 'crescendo';
  elements.sectionExpression.checked = true;
  assert.equal(settings().brief.intensidad, 85);
  assert.equal(settings().song.expresion_secciones.contrast.intensidad, 91);
  const saved = settings();
  saved.song.expresion_secciones.contrast.intensidad = 80;
  saved.brief.numerator = 3;
  await elements.importSettings.onchange({target: {files: [{text: async () => JSON.stringify(saved)}]}});
  assert.equal(settings().song.expresion_secciones.contrast.intensidad, 80);
  assert.equal(settings().brief.numerator, 3);
  assert.equal(settings().brief.curva_dinamica, 'crescendo');
  console.log('Dashboard controls: default mode, expression controls and settings round-trip passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
