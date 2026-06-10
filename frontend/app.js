// ============================================================
// Stage catalog, presets & instance factory
// ============================================================

const STAGE_CATALOG = {
  junk: {
    label: 'Junk Injection',
    description: 'Inserts meaningless statements (arithmetic, bitwise ops, lambdas) to bulk up the AST.',
    defaultConfig: { density: 2, strategies: ['BitwiseStrategy', 'NonConstantTimeStrategy', 'ArithmeticStrategy'] },
    allStrategies: ['ArithmeticStrategy', 'BitwiseStrategy', 'LambdaStrategy', 'NonConstantTimeStrategy', 'TestStrategy'],
  },
  loops: {
    label: 'Loop Obfuscation',
    description: 'Converts for loops into while loops with a configurable index-tracking strategy.',
    defaultConfig: { strategy: 'CollatzStrategy' },
    allStrategies: ['CollatzStrategy', 'PlainStrategy'],
  },
  conditionals: {
    label: 'Conditional Wrapping',
    description: 'Wraps statements in always-true if predicates so control flow is harder to read.',
    defaultConfig: { strategies: ['RandomConditionalStrategy'] },
    allStrategies: ['ConstantFalseStrategy', 'ConstantTrueStrategy', 'RandomConditionalStrategy'],
  },
  identities: {
    label: 'Identity Injection',
    description: 'Wraps expressions in no-op operations (e.g. 1 and x) that evaluate to the original value.',
    defaultConfig: { probability: 0.2 },
  },
  numbers: {
    label: 'Number Obfuscation',
    description: 'Replaces integer literals with multi-step cipher expressions that decode at runtime.',
    defaultConfig: { strategies: ['FeistelNumberStrategy', 'XorStringNumberStrategy'] },
    allStrategies: ['FeistelNumberStrategy', 'SimpleFeistelNumberStrategy', 'TemplateNumberStrategy', 'XorStringNumberStrategy'],
  },
  strings: {
    label: 'String Obfuscation',
    description: 'Replaces string literals with chr()-array expressions or XOR-encrypted byte sequences decoded at runtime.',
    defaultConfig: { strategies: ['XorStringStrategy', 'CharArrayStrategy'] },
    allStrategies: ['CharArrayStrategy', 'XorStringStrategy'],
  },
  renaming: {
    label: 'Renaming',
    description: 'Replaces all user-defined identifiers with random 8-character names.',
    defaultConfig: {},
  },
};

const STAGE_PRESETS = {
  junk: {
    light:  { density: 1, strategies: ['BitwiseStrategy'] },
    medium: { density: 2, strategies: ['BitwiseStrategy', 'NonConstantTimeStrategy', 'ArithmeticStrategy'] },
    heavy:  { density: 4, strategies: ['BitwiseStrategy', 'NonConstantTimeStrategy', 'ArithmeticStrategy', 'LambdaStrategy'] },
  },
  loops: {
    light:  { strategy: 'PlainStrategy' },
    medium: { strategy: 'CollatzStrategy' },
    heavy:  { strategy: 'CollatzStrategy' },
  },
  conditionals: {
    light:  { strategies: ['ConstantTrueStrategy'] },
    medium: { strategies: ['RandomConditionalStrategy'] },
    heavy:  { strategies: ['ConstantTrueStrategy', 'ConstantFalseStrategy', 'RandomConditionalStrategy'] },
  },
  identities: {
    light:  { probability: 0.1 },
    medium: { probability: 0.2 },
    heavy:  { probability: 0.5 },
  },
  numbers: {
    light:  { strategies: ['FeistelNumberStrategy'] },
    medium: { strategies: ['FeistelNumberStrategy', 'XorStringNumberStrategy'] },
    heavy:  { strategies: ['FeistelNumberStrategy', 'XorStringNumberStrategy', 'SimpleFeistelNumberStrategy'] },
  },
  strings: {
    light:  { strategies: ['CharArrayStrategy'] },
    medium: { strategies: ['XorStringStrategy'] },
    heavy:  { strategies: ['XorStringStrategy', 'CharArrayStrategy'] },
  },
};

const WELCOME_KEY = 'pyobfuscate_hide_welcome';

const STRATEGY_TEMPLATES = {
  junk: `from Injectors.junk_strategies import JunkInjectionStrategy
import ast
from typing import List

class MyJunkStrategy(JunkInjectionStrategy):
    # __init__ inherited: sets self.junk_vars (list of available variable names)

    def get_junk(self, rng) -> List[ast.stmt]:
        # Return AST statement nodes to inject as junk.
        # rng is random.Random; self.junk_vars has pre-generated variable names.
        return []`,
  loops: `from LoopObfuscation.obfuscation_strategies import LoopObfuscationStrategy
import ast
from typing import List

class MyLoopStrategy(LoopObfuscationStrategy):
    # __init__ inherited: sets self.loop_var, self.start, self.stop, self.step, self.rng

    def get_initial(self) -> List[ast.stmt]:
        # Statements to initialise the loop counter before the while loop.
        return []

    def get_condition(self) -> ast.expr:
        # The while-loop condition expression.
        return ast.Constant(value=True)

    def get_advance(self) -> List[ast.stmt]:
        # Statements to update the loop state at the end of each iteration.
        return []`,
  identities: `from Injectors.identity_strategies import IdentityFuncStrategy
import ast

class MyIdentityStrategy(IdentityFuncStrategy):
    def wrap(self, expr: ast.expr, rng) -> ast.expr:
        # Return an expression that always evaluates to the same value as expr.
        # Example: 1 and expr
        return expr`,
  numbers: `from Encryption.number_obscure_strategies import NumberObscureStrategy
import ast

class MyNumberStrategy(NumberObscureStrategy):
    # __init__ inherited: sets self.naming and self.rng

    def obfuscate(self, value: int) -> ast.expr:
        # Return an AST expression that evaluates to value.
        # Use self.rng for randomness; self.naming.get_name() for unique variable names.
        return ast.Constant(value=value)`,
  strings: `from Encryption.string_obscure_strategies import StringObscureStrategy
import ast

class MyStringStrategy(StringObscureStrategy):
    # __init__ inherited: sets self.naming and self.rng

    def obfuscate(self, value: str) -> ast.expr:
        # Return an AST expression that evaluates to value.
        # Use self.rng for randomness; self.naming.get_name() for unique variable names.
        return ast.Constant(value=value)`,
};

let _nextId = 0;

function makeInstance(configType) {
  const def = STAGE_CATALOG[configType];
  return {
    instanceId: _nextId++,
    configType,
    label: def.label,
    enabled: true,
    expanded: false,
    config: JSON.parse(JSON.stringify(def.defaultConfig)),
    allStrategies: def.allStrategies ? [...def.allStrategies] : undefined,
  };
}

function initStages() {
  return ['junk', 'loops', 'conditionals', 'identities', 'numbers', 'strings', 'renaming'].map(makeInstance);
}

const state = {
  stages: initStages(),
  executionPath: 'client',
  pyodide: null,
  pyodideReady: false,
  pyodideError: null,
};

// ============================================================
// DOM helpers
// ============================================================

const $ = id => document.getElementById(id);

// ============================================================
// Config helpers
// ============================================================

function configMatches(config, preset) {
  for (const [k, v] of Object.entries(preset)) {
    if (Array.isArray(v)) {
      if (!Array.isArray(config[k]) || config[k].length !== v.length) return false;
      if (!v.every(s => config[k].includes(s))) return false;
    } else if (typeof v === 'number') {
      if (Math.abs((config[k] ?? v) - v) > 0.001) return false;
    } else {
      if (config[k] !== v) return false;
    }
  }
  return true;
}

function detectPreset(stage) {
  const presets = STAGE_PRESETS[stage.configType];
  if (!presets) return null;
  for (const name of ['light', 'medium', 'heavy']) {
    if (configMatches(stage.config, presets[name])) return name;
  }
  return 'custom';
}

function makeSummary(stage) {
  const c = stage.config;
  const shorten = s => s
    .replace('Strategy', '')
    .replace('NonConstantTime', 'NonConst')
    .replace('Arithmetic', 'Arith')
    .replace('Conditional', '')
    .replace('XorString', 'XorStr')
    .replace('SimpleFeistel', 'SimpleFst')
    .replace('Random', 'Rand');
  switch (stage.configType) {
    case 'junk': {
      const names = (c.strategies || []).map(shorten).join(', ');
      return names ? `${names} · density ${c.density}` : 'no strategies';
    }
    case 'loops':
      return shorten(c.strategy ?? 'Collatz');
    case 'conditionals': {
      const names = (c.strategies || []).map(shorten).join(', ');
      return names || 'none';
    }
    case 'identities':
      return `prob ${(c.probability ?? 0.2).toFixed(2)}`;
    case 'numbers': {
      const names = (c.strategies || []).map(shorten).join(', ');
      return names || 'none';
    }
    case 'strings': {
      const names = (c.strategies || []).map(shorten).join(', ');
      return names || 'none';
    }
    default:
      return '';
  }
}

// ============================================================
// Stage rendering
// ============================================================

function hasConfig(stage) {
  return stage.configType !== 'renaming';
}

function renderPresetRow(stage) {
  const presets = STAGE_PRESETS[stage.configType];
  if (!presets) return '';
  const active = detectPreset(stage);
  const iid = stage.instanceId;
  const names = active === 'custom' ? ['light', 'medium', 'heavy', 'custom'] : ['light', 'medium', 'heavy'];
  const labels = { light: 'Light', medium: 'Medium', heavy: 'Heavy', custom: 'Custom' };
  return `<div class="preset-row">
    ${names.map(n => `
      <button class="preset-btn${active === n ? ' active' : ''}"
              data-preset="${n}" data-iid="${iid}">${labels[n]}</button>
    `).join('')}
  </div>`;
}

function renderConfigHTML(stage) {
  const c = stage.config;
  const iid = stage.instanceId;
  const presetRow = renderPresetRow(stage);
  const desc = STAGE_CATALOG[stage.configType]?.description ?? '';
  const descEl = desc ? `<p class="stage-desc">${desc}</p>` : '';

  switch (stage.configType) {
    case 'junk':
      return `${descEl}
        ${presetRow}
        <div class="config-row chip-row">
          <span class="row-label">Strategies:</span>
          ${(stage.allStrategies || []).map(s => `
            <button class="stage-chip${(c.strategies||[]).includes(s) ? ' active' : ''}"
                    data-chip="junk_strategy" data-iid="${iid}" data-value="${s}">
              ${s.replace('Strategy', '')}
            </button>
          `).join('')}
        </div>
        <div class="config-row">
          <span class="row-label">Density:</span>
          <input type="range" min="1" max="5" value="${c.density}"
            data-config="density" data-iid="${iid}">
          <span class="range-val" id="density-val-${iid}">${c.density}</span>
        </div>`;

    case 'loops':
      return `${descEl}
        ${presetRow}
        <div class="config-row chip-row">
          <span class="row-label">Strategy:</span>
          ${(stage.allStrategies || []).map(s => `
            <button class="stage-chip${c.strategy === s ? ' active' : ''}"
                    data-chip="loop_strategy" data-iid="${iid}" data-value="${s}">
              ${s.replace('Strategy', '')}
            </button>
          `).join('')}
        </div>`;

    case 'conditionals':
      return `${descEl}
        ${presetRow}
        <div class="config-row chip-row">
          <span class="row-label">Strategies:</span>
          ${(stage.allStrategies || []).map(s => `
            <button class="stage-chip${(c.strategies||[]).includes(s) ? ' active' : ''}"
                    data-chip="cond_strategy" data-iid="${iid}" data-value="${s}">
              ${s.replace('Strategy', '')}
            </button>
          `).join('')}
        </div>`;

    case 'identities':
      return `${descEl}
        ${presetRow}
        <div class="config-row">
          <span class="row-label">Probability:</span>
          <input type="range" min="0" max="1" step="0.05" value="${c.probability}"
            data-config="probability" data-iid="${iid}">
          <span class="range-val" id="prob-val-${iid}">${c.probability.toFixed(2)}</span>
        </div>`;

    case 'numbers':
      return `${descEl}
        ${presetRow}
        <div class="config-row chip-row">
          <span class="row-label">Strategies:</span>
          ${(stage.allStrategies || []).map(s => `
            <button class="stage-chip${(c.strategies||[]).includes(s) ? ' active' : ''}"
                    data-chip="num_strategy" data-iid="${iid}" data-value="${s}">
              ${s.replace('Strategy', '')}
            </button>
          `).join('')}
        </div>`;

    case 'strings':
      return `${descEl}
        ${presetRow}
        <div class="config-row chip-row">
          <span class="row-label">Strategies:</span>
          ${(stage.allStrategies || []).map(s => `
            <button class="stage-chip${(c.strategies||[]).includes(s) ? ' active' : ''}"
                    data-chip="str_strategy" data-iid="${iid}" data-value="${s}">
              ${s.replace('Strategy', '')}
            </button>
          `).join('')}
        </div>`;

    default:
      return descEl;
  }
}

function renderStages() {
  const list = $('stage-list');
  list.innerHTML = '';

  state.stages.forEach(stage => {
    const iid = stage.instanceId;
    const li = document.createElement('li');
    const isPinned = stage.configType === 'renaming';

    let cls = 'stage-item';
    if (isPinned) cls += ' stage-pinned';
    if (!stage.enabled) cls += ' disabled';
    li.className = cls;
    li.dataset.iid = iid;

    const configPanel = hasConfig(stage)
      ? `<div class="stage-config" id="config-${iid}"
             style="${stage.expanded ? '' : 'display:none'}">
           ${renderConfigHTML(stage)}
         </div>`
      : '';

    const summary = hasConfig(stage)
      ? `<span class="stage-summary">${makeSummary(stage)}</span>`
      : '';

    const toggleBtn = `<button class="stage-item-btn stage-toggle-btn"
               data-action="toggle" data-iid="${iid}"
               title="${stage.enabled ? 'Disable stage' : 'Enable stage'}">${stage.enabled ? '⊙' : '○'}</button>`;

    const actionBtns = isPinned
      ? `<button class="stage-item-btn stage-item-remove" data-action="remove" data-iid="${iid}" title="Remove">×</button>`
      : `<button class="stage-item-btn stage-item-dup" data-action="dup" data-iid="${iid}" title="Duplicate">⧉</button>
         <button class="stage-item-btn stage-item-remove" data-action="remove" data-iid="${iid}" title="Remove">×</button>`;

    li.innerHTML = `
      <div class="stage-row">
        ${isPinned ? '<span class="drag-handle drag-handle-spacer"></span>' : '<span class="drag-handle">⠿</span>'}
        <div class="stage-label-group">
          <span class="stage-label">${stage.label}</span>
          ${summary}
        </div>
        ${toggleBtn}
        ${hasConfig(stage)
          ? `<button class="expand-btn" data-iid="${iid}">${stage.expanded ? '▾' : '▸'}</button>`
          : ''}
        ${actionBtns}
      </div>
      ${configPanel}`;

    list.appendChild(li);
  });

  // Add-step row
  let addRow = $('add-step-row');
  if (!addRow) {
    addRow = document.createElement('div');
    addRow.id = 'add-step-row';
    list.parentElement.appendChild(addRow);
  }
  const hasRenaming = state.stages.some(s => s.configType === 'renaming');
  const addableTypes = Object.keys(STAGE_CATALOG).filter(t => t !== 'renaming' || !hasRenaming);
  addRow.innerHTML = `
    <select id="add-step-select">
      ${addableTypes.map(t => `<option value="${t}">${STAGE_CATALOG[t].label}</option>`).join('')}
    </select>
    <button class="btn-secondary" id="add-step-btn">+ Add step</button>`;

  // Wire expand/collapse
  list.querySelectorAll('.expand-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const iid = +btn.dataset.iid;
      const stage = state.stages.find(s => s.instanceId === iid);
      stage.expanded = !stage.expanded;
      const panel = $(`config-${iid}`);
      panel.style.display = stage.expanded ? 'block' : 'none';
      btn.textContent = stage.expanded ? '▾' : '▸';
    });
  });

  // Wire action buttons (toggle, remove, dup)
  list.querySelectorAll('[data-action]').forEach(btn => {
    btn.addEventListener('click', () => {
      const iid = +btn.dataset.iid;
      const action = btn.dataset.action;
      if (action === 'remove')      removeStage(iid);
      else if (action === 'dup')    duplicateStage(iid);
      else if (action === 'toggle') toggleStage(iid);
    });
  });

  // Wire range inputs
  list.querySelectorAll('[data-config]').forEach(el => {
    el.addEventListener('input', handleConfigChange);
  });

  // Wire strategy chips
  list.querySelectorAll('[data-chip]').forEach(btn => {
    btn.addEventListener('click', handleChipClick);
  });

  // Wire preset buttons
  list.querySelectorAll('[data-preset]').forEach(btn => {
    btn.addEventListener('click', handlePresetClick);
  });

  // Wire add-step
  $('add-step-btn').addEventListener('click', () => {
    addStage($('add-step-select').value);
  });

  setupSortable(list);
}

function toggleStage(iid) {
  const stage = state.stages.find(s => s.instanceId === iid);
  if (stage) stage.enabled = !stage.enabled;
  renderStages();
}

function removeStage(iid) {
  state.stages = state.stages.filter(s => s.instanceId !== iid);
  renderStages();
}

function duplicateStage(iid) {
  const idx = state.stages.findIndex(s => s.instanceId === iid);
  const src = state.stages[idx];
  if (src.configType === 'renaming') return;
  const copy = makeInstance(src.configType);
  copy.config = JSON.parse(JSON.stringify(src.config));
  copy.allStrategies = src.allStrategies ? [...src.allStrategies] : undefined;
  state.stages.splice(idx + 1, 0, copy);
  renderStages();
}

function addStage(configType) {
  const inst = makeInstance(configType);
  if (configType === 'renaming') {
    state.stages.push(inst);
  } else {
    const renamingIdx = state.stages.findIndex(s => s.configType === 'renaming');
    const insertAt = renamingIdx >= 0 ? renamingIdx : state.stages.length;
    state.stages.splice(insertAt, 0, inst);
  }
  renderStages();
}

function handleConfigChange(e) {
  const iid = +e.target.dataset.iid;
  const key = e.target.dataset.config;
  const stage = state.stages.find(s => s.instanceId === iid);
  if (!stage) return;

  if (key === 'density') {
    const v = +e.target.value;
    stage.config.density = v;
    const span = $(`density-val-${iid}`);
    if (span) span.textContent = v;
  } else if (key === 'probability') {
    const v = parseFloat(e.target.value);
    stage.config.probability = v;
    const span = $(`prob-val-${iid}`);
    if (span) span.textContent = v.toFixed(2);
  }

  // Update summary and preset row without full re-render
  updateSummaryAndPreset(stage);
}

function handleChipClick(e) {
  const btn = e.currentTarget;
  const iid = +btn.dataset.iid;
  const key = btn.dataset.chip;
  const value = btn.dataset.value;
  const stage = state.stages.find(s => s.instanceId === iid);
  if (!stage) return;

  if (key === 'loop_strategy') {
    stage.config.strategy = value;
  } else {
    const arr = stage.config.strategies;
    const idx = arr.indexOf(value);
    if (idx >= 0) arr.splice(idx, 1);
    else arr.push(value);
  }
  renderStages();
}

function handlePresetClick(e) {
  const btn = e.currentTarget;
  const iid = +btn.dataset.iid;
  const presetName = btn.dataset.preset;
  const stage = state.stages.find(s => s.instanceId === iid);
  if (!stage || presetName === 'custom') return;
  const preset = STAGE_PRESETS[stage.configType]?.[presetName];
  if (!preset) return;
  stage.config = JSON.parse(JSON.stringify(preset));
  renderStages();
}

function updateSummaryAndPreset(stage) {
  // Lightweight update: just refresh the summary text and preset row active state
  // without re-rendering the whole list (avoids collapsing panels on range drag)
  const iid = stage.instanceId;
  const summaryEl = document.querySelector(`[data-iid="${iid}"] .stage-summary`);
  if (summaryEl) summaryEl.textContent = makeSummary(stage);

  const active = detectPreset(stage);
  document.querySelectorAll(`[data-preset][data-iid="${iid}"]`).forEach(btn => {
    btn.classList.toggle('active', btn.dataset.preset === active);
  });
}

// ============================================================
// SortableJS drag & drop
// ============================================================

let _sortable = null;

function setupSortable(list) {
  if (_sortable) { _sortable.destroy(); _sortable = null; }
  if (typeof Sortable === 'undefined') return;
  _sortable = Sortable.create(list, {
    handle: '.drag-handle:not(.drag-handle-spacer)',
    filter: '.stage-pinned',
    preventOnFilter: false,
    animation: 120,
    ghostClass: 'dragging',
    onMove(evt) {
      return !evt.related.classList.contains('stage-pinned');
    },
    onEnd(evt) {
      if (evt.oldIndex === evt.newIndex) return;
      const moved = state.stages.splice(evt.oldIndex, 1)[0];
      state.stages.splice(evt.newIndex, 0, moved);
      renderStages();
    },
  });
}

// ============================================================
// Pyodide init & package load
// ============================================================

function syncRunButton() {
  const loading = state.executionPath === 'client' && !state.pyodideReady && !state.pyodideError;
  const btn = $('submit-btn');
  btn.disabled = loading;
  if (loading && btn.textContent === 'Obfuscate') btn.textContent = 'Loading…';
  if (!loading && btn.textContent === 'Loading…') btn.textContent = 'Obfuscate';
}

async function initPyodide() {
  const statusEl = $('pyodide-status');
  try {
    if (typeof loadPyodide === 'undefined') throw new Error('Pyodide script not loaded');
    console.log('[pyodide] starting loadPyodide()');
    statusEl.textContent = 'Loading Pyodide…';
    statusEl.className = 'pyodide-status loading';

    state.pyodide = await loadPyodide();
    console.log('[pyodide] loadPyodide() done');
    statusEl.textContent = 'Loading package…';

    await loadPackage();
    console.log('[pyodide] loadPackage() done');

    state.pyodideReady = true;
    statusEl.textContent = 'Client ready';
    statusEl.className = 'pyodide-status ready';
    syncRunButton();
  } catch (err) {
    state.pyodideError = err.message;
    statusEl.textContent = 'Pyodide failed — switch to Server mode to continue';
    statusEl.className = 'pyodide-status error';
    console.error('[pyodide] init failed:', err);
    syncRunButton();
  }
}

async function loadPackage() {
  console.log('[pyodide] fetching /package.json');
  const resp = await fetch('/package.json');
  console.log('[pyodide] /package.json status:', resp.status, 'content-type:', resp.headers.get('content-type'));
  if (!resp.ok) throw new Error(`/package.json returned ${resp.status}`);
  let files;
  try {
    files = await resp.json();
    console.log('[pyodide] /package.json parsed OK, file count:', Object.keys(files).length);
  } catch {
    throw new Error(`/package.json returned non-JSON (content-type: ${resp.headers.get('content-type')})`);
  }

  const py = state.pyodide;

  const dirs = new Set();
  for (const path of Object.keys(files)) {
    const parts = path.split('/');
    for (let i = 1; i < parts.length; i++) {
      dirs.add(parts.slice(0, i).join('/'));
    }
  }
  for (const dir of dirs) {
    try { py.FS.mkdir('/home/pyodide/' + dir); } catch (_) {}
  }

  for (const [path, content] of Object.entries(files)) {
    py.FS.writeFile('/home/pyodide/' + path, content, { encoding: 'utf8' });
  }

  console.log('[pyodide] importing pipeline');
  await py.runPythonAsync(`
import sys
if '/home/pyodide' not in sys.path:
    sys.path.insert(0, '/home/pyodide')
import pipeline
`);
  console.log('[pyodide] pipeline imported OK');
}

// ============================================================
// Config builder
// ============================================================

function buildConfig() {
  const phase_configs = state.stages
    .filter(s => s.enabled !== false)
    .map(s => ({ type: s.configType, config: s.config }));
  const seedRaw = $('seed').value.trim();
  return {
    phase_configs,
    seed: seedRaw ? parseInt(seedRaw, 10) : null,
    return_code: true,
  };
}

// ============================================================
// Submit & execution
// ============================================================

async function handleSubmit() {
  const code = $('input').value;
  if (!code.trim()) return;

  const btn = $('submit-btn');
  btn.disabled = true;
  btn.textContent = 'Running…';
  $('error-msg').textContent = '';
  $('output').value = '';
  $('copy-btn').disabled = true;

  try {
    let result;
    if (state.executionPath === 'client') {
      result = await runClientSide(code);
    } else {
      result = await runServerSide(code);
    }
    $('output').value = result;
    $('copy-btn').disabled = false;
  } catch (err) {
    $('error-msg').textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Obfuscate';
  }
}

async function runClientSide(code) {
  if (!state.pyodideReady) {
    throw new Error('Pyodide is still loading — please wait.');
  }

  const py = state.pyodide;
  const cfg = buildConfig();

  py.globals.set('_code', code);
  py.globals.set('_cfg_json', JSON.stringify(cfg));

  return await py.runPythonAsync(`
import json
from pathlib import Path
from pipeline import ObfuscationConfig, run_pipeline

cfg_data = json.loads(_cfg_json)

with open('/tmp/input.py', 'w') as f:
    f.write(_code)

cfg = ObfuscationConfig(
    input_path=Path('/tmp/input.py'),
    phase_configs=cfg_data['phase_configs'],
    seed=cfg_data['seed'],
)
run_pipeline(cfg)
`);
}

async function runServerSide(code) {
  const payload = JSON.stringify({ source: code, ...buildConfig() });

  const payloadBytes = new TextEncoder().encode(payload);
  const hashBuffer = await crypto.subtle.digest('SHA-256', payloadBytes);
  const hashHex = Array.from(new Uint8Array(hashBuffer))
    .map(b => b.toString(16).padStart(2, '0')).join('');

  const resp = await fetch('/obfuscate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-amz-content-sha256': hashHex,
    },
    body: payload,
  });

  let data;
  try {
    data = await resp.json();
  } catch {
    throw new Error(`Server error ${resp.status}: unexpected non-JSON response`);
  }
  if (!resp.ok) throw new Error(data.error ?? `Server error ${resp.status}`);
  return data.code;
}

// ============================================================
// Custom module upload
// ============================================================

async function handleCustomUpload(file) {
  const statusEl = $('upload-status');

  if (!state.pyodideReady) {
    statusEl.textContent = 'Custom modules require client mode — Pyodide not ready.';
    statusEl.className = 'upload-status error';
    return;
  }

  try {
    const text = await file.text();
    const py = state.pyodide;
    const safeName = file.name.replace(/\.py$/i, '').replace(/[^a-zA-Z0-9_]/g, '_');
    const moduleName = 'custom_' + safeName;

    py.FS.writeFile(`/home/pyodide/${moduleName}.py`, text, { encoding: 'utf8' });

    py.globals.set('_module_name', moduleName);
    await py.runPythonAsync(`
import importlib.util, sys
_path = '/home/pyodide/' + _module_name + '.py'
spec = importlib.util.spec_from_file_location(_module_name, _path)
mod = importlib.util.module_from_spec(spec)
sys.modules[_module_name] = mod
spec.loader.exec_module(mod)
`);

    await refreshStrategyDropdowns();
    statusEl.textContent = `Loaded: ${file.name}`;
    statusEl.className = 'upload-status ok';
  } catch (err) {
    statusEl.textContent = `Error loading ${file.name}: ${err.message}`;
    statusEl.className = 'upload-status error';
  }
}

async function refreshStrategyDropdowns() {
  if (!state.pyodideReady) return;

  const registriesJson = await state.pyodide.runPythonAsync(`
import json
from Injectors.junk_strategies import JunkInjectionStrategy
from Injectors.junk_conditional_strategies import JunkConditionalStrategy
from LoopObfuscation.obfuscation_strategies import LoopObfuscationStrategy
from Encryption.number_obscure_strategies import NumberObscureStrategy
from Encryption.string_obscure_strategies import StringObscureStrategy
json.dumps({
    'junk': sorted(k for k in JunkInjectionStrategy._registry if k != 'JunkInjectionStrategy'),
    'conditional': sorted(k for k in JunkConditionalStrategy._registry if k != 'JunkConditionalStrategy'),
    'loop': sorted(k for k in LoopObfuscationStrategy._registry if k != 'LoopObfuscationStrategy'),
    'number': sorted(k for k in NumberObscureStrategy._registry if k != 'NumberObscureStrategy'),
    'string': sorted(k for k in StringObscureStrategy._registry if k != 'StringObscureStrategy'),
})
`);

  const reg = JSON.parse(registriesJson);

  state.stages.forEach(stage => {
    if (stage.configType === 'junk')         stage.allStrategies = reg.junk;
    if (stage.configType === 'loops')        stage.allStrategies = reg.loop;
    if (stage.configType === 'conditionals') stage.allStrategies = reg.conditional;
    if (stage.configType === 'numbers')      stage.allStrategies = reg.number;
    if (stage.configType === 'strings')      stage.allStrategies = reg.string;
  });

  renderStages();
}

// ============================================================
// UI helpers
// ============================================================

function updateUploadVisibility() {
  const input = $('custom-upload');
  const status = $('upload-status');
  if (!input) return;

  const isServer = state.executionPath === 'server';
  input.disabled = isServer;
  input.title = isServer ? 'Custom modules require Pyodide — switch to Client mode' : '';
  $('upload-section').style.opacity = isServer ? '0.45' : '';
  if (isServer) {
    status.textContent = 'Not available in server mode';
    status.className = 'upload-status';
  } else if (status.textContent === 'Not available in server mode') {
    status.textContent = '';
    status.className = 'upload-status';
  }
}

// ============================================================
// Welcome modal
// ============================================================

function showWelcomeModal() {
  $('welcome-modal').removeAttribute('hidden');
  $('hide-welcome').checked = false;
}

function closeWelcomeModal() {
  $('welcome-modal').setAttribute('hidden', '');
  if ($('hide-welcome').checked) {
    localStorage.setItem(WELCOME_KEY, '1');
  }
}

// ============================================================
// Init
// ============================================================

function init() {
  renderStages();
  updateUploadVisibility();

  if (!localStorage.getItem(WELCOME_KEY)) showWelcomeModal();
  $('welcome-close').addEventListener('click', closeWelcomeModal);
  $('help-btn').addEventListener('click', showWelcomeModal);
  $('welcome-modal').addEventListener('click', e => {
    if (e.target === $('welcome-modal')) closeWelcomeModal();
  });

  const tmplLabels = {
    junk: 'Junk Injection',
    loops: 'Loop Obfuscation',
    identities: 'Identity Injection',
    numbers: 'Number Obfuscation',
    strings: 'String Obfuscation',
  };
  $('template-content').innerHTML = Object.entries(STRATEGY_TEMPLATES)
    .map(([k, t]) => `<p class="tmpl-label">${tmplLabels[k]}</p><pre>${t.replace(/&/g, '&amp;').replace(/</g, '&lt;')}</pre>`)
    .join('');

  document.querySelectorAll('input[name="execPath"]').forEach(radio => {
    radio.addEventListener('change', e => {
      state.executionPath = e.target.value;
      updateUploadVisibility();
      syncRunButton();
    });
  });

  $('submit-btn').addEventListener('click', handleSubmit);

  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
    if (e.key === 'Escape' && !$('welcome-modal').hasAttribute('hidden')) {
      closeWelcomeModal();
    }
  });

  $('copy-btn').addEventListener('click', () => {
    const text = $('output').value;
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
      const btn = $('copy-btn');
      btn.textContent = 'Copied';
      btn.disabled = true;
      setTimeout(() => {
        btn.textContent = 'Copy';
        btn.disabled = false;
      }, 1500);
    }).catch(() => {});
  });

  $('custom-upload').addEventListener('change', e => {
    const file = e.target.files[0];
    if (file) handleCustomUpload(file);
    e.target.value = '';
  });

  syncRunButton();
  initPyodide();
}

document.addEventListener('DOMContentLoaded', init);
