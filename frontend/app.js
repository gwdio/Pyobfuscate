// ============================================================
// Initial state
// ============================================================

const STAGE_DEFS = [
  {
    id: 'junk', label: 'Junk Injection',
    enabled: true, expanded: false,
    configType: 'junk',
    config: { density: 2, strategies: ['BitwiseStrategy', 'NonConstantTimeStrategy', 'ArithmeticStrategy'] },
    allStrategies: ['ArithmeticStrategy', 'BitwiseStrategy', 'LambdaStrategy', 'NonConstantTimeStrategy', 'TestStrategy'],
  },
  {
    id: 'loops', label: 'Loop Obfuscation',
    enabled: true, expanded: false,
    configType: 'loop',
    config: { strategy: 'CollatzStrategy' },
    allStrategies: ['CollatzStrategy', 'PlainStrategy'],
  },
  {
    id: 'conditionals', label: 'Conditional Wrapping',
    enabled: true, expanded: false,
    configType: 'conditionals',
    config: { strategies: ['RandomConditionalStrategy'] },
    allStrategies: ['ConstantFalseStrategy', 'ConstantTrueStrategy', 'RandomConditionalStrategy'],
  },
  {
    id: 'identities', label: 'Identity Injection',
    enabled: true, expanded: false,
    configType: 'identities',
    config: { probability: 0.2 },
  },
  {
    id: 'numbers', label: 'Number Obfuscation',
    enabled: true, expanded: false,
    configType: 'numbers',
    config: { strategies: ['FeistelNumberStrategy', 'XorStringNumberStrategy'] },
    allStrategies: ['FeistelNumberStrategy', 'SimpleFeistelNumberStrategy', 'TemplateNumberStrategy', 'XorStringNumberStrategy'],
  },
  {
    id: 'renaming', label: 'Renaming',
    enabled: true, expanded: false,
    configType: 'renaming',
    config: {},
  },
];

const state = {
  stages: STAGE_DEFS.map(s => ({
    ...s,
    config: Array.isArray(s.config) ? [...s.config] : { ...s.config },
    allStrategies: s.allStrategies ? [...s.allStrategies] : undefined,
  })),
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
// Stage rendering
// ============================================================

function hasConfig(stage) {
  return stage.configType !== 'renaming';
}

function renderConfigHTML(stage, idx) {
  const c = stage.config;
  switch (stage.configType) {
    case 'junk':
      return `
        <div class="config-row">
          <span class="row-label">Density:</span>
          <input type="range" min="1" max="5" value="${c.density}"
            data-config="density" data-idx="${idx}">
          <span class="range-val" id="density-val-${idx}">${c.density}</span>
        </div>
        <div class="config-row">
          <span class="row-label">Strategies:</span>
          ${(stage.allStrategies || []).map(s => `
            <label class="check-label">
              <input type="checkbox" value="${s}"
                data-config="junk_strategy" data-idx="${idx}"
                ${c.strategies.includes(s) ? 'checked' : ''}> ${s}
            </label>
          `).join('')}
        </div>`;

    case 'loop':
      return `
        <div class="config-row">
          <span class="row-label">Strategy:</span>
          ${(stage.allStrategies || []).map(s => `
            <label class="check-label">
              <input type="radio" name="loop-strat-${idx}" value="${s}"
                data-config="loop_strategy" data-idx="${idx}"
                ${c.strategy === s ? 'checked' : ''}> ${s}
            </label>
          `).join('')}
        </div>`;

    case 'conditionals':
      return `
        <div class="config-row">
          <span class="row-label">Strategies:</span>
          ${(stage.allStrategies || []).map(s => `
            <label class="check-label">
              <input type="checkbox" value="${s}"
                data-config="cond_strategy" data-idx="${idx}"
                ${c.strategies.includes(s) ? 'checked' : ''}> ${s}
            </label>
          `).join('')}
        </div>`;

    case 'identities':
      return `
        <div class="config-row">
          <span class="row-label">Probability:</span>
          <input type="range" min="0" max="1" step="0.05" value="${c.probability}"
            data-config="probability" data-idx="${idx}">
          <span class="range-val" id="prob-val-${idx}">${c.probability.toFixed(2)}</span>
        </div>`;

    case 'numbers':
      return `
        <div class="config-row">
          <span class="row-label">Strategies:</span>
          ${(stage.allStrategies || []).map(s => `
            <label class="check-label">
              <input type="checkbox" value="${s}"
                data-config="num_strategy" data-idx="${idx}"
                ${c.strategies.includes(s) ? 'checked' : ''}> ${s}
            </label>
          `).join('')}
        </div>`;

    default:
      return '';
  }
}

function renderStages() {
  const list = $('stage-list');
  list.innerHTML = '';

  state.stages.forEach((stage, idx) => {
    const li = document.createElement('li');
    li.className = `stage-item${stage.enabled ? '' : ' disabled'}`;
    li.dataset.idx = idx;
    li.draggable = true;

    const configPanel = hasConfig(stage)
      ? `<div class="stage-config" id="config-${idx}"
             style="${stage.expanded ? '' : 'display:none'}">
           ${renderConfigHTML(stage, idx)}
         </div>`
      : '';

    li.innerHTML = `
      <div class="stage-row">
        <span class="drag-handle">⠿</span>
        <label class="stage-toggle">
          <input type="checkbox" data-idx="${idx}" ${stage.enabled ? 'checked' : ''}>
        </label>
        <span class="stage-label">${stage.label}</span>
        ${hasConfig(stage)
          ? `<button class="expand-btn" data-idx="${idx}">${stage.expanded ? '▾' : '▸'}</button>`
          : ''}
      </div>
      ${configPanel}`;

    list.appendChild(li);
  });

  // Toggle enable
  list.querySelectorAll('.stage-toggle input').forEach(cb => {
    cb.addEventListener('change', e => {
      const idx = +e.target.dataset.idx;
      state.stages[idx].enabled = e.target.checked;
      list.children[idx].classList.toggle('disabled', !e.target.checked);
    });
  });

  // Expand/collapse
  list.querySelectorAll('.expand-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = +btn.dataset.idx;
      state.stages[idx].expanded = !state.stages[idx].expanded;
      const panel = $(`config-${idx}`);
      panel.style.display = state.stages[idx].expanded ? 'block' : 'none';
      btn.textContent = state.stages[idx].expanded ? '▾' : '▸';
    });
  });

  // Config inputs
  list.querySelectorAll('[data-config]').forEach(el => {
    const event = el.type === 'range' ? 'input' : 'change';
    el.addEventListener(event, handleConfigChange);
  });

  setupDragDrop(list);
}

function handleConfigChange(e) {
  const idx = +e.target.dataset.idx;
  const key = e.target.dataset.config;
  const stage = state.stages[idx];

  switch (key) {
    case 'density': {
      const v = +e.target.value;
      stage.config.density = v;
      const span = $(`density-val-${idx}`);
      if (span) span.textContent = v;
      break;
    }
    case 'probability': {
      const v = parseFloat(e.target.value);
      stage.config.probability = v;
      const span = $(`prob-val-${idx}`);
      if (span) span.textContent = v.toFixed(2);
      break;
    }
    case 'loop_strategy':
      stage.config.strategy = e.target.value;
      break;
    case 'junk_strategy':
      stage.config.strategies = checkedValues(`[data-config="junk_strategy"][data-idx="${idx}"]`);
      break;
    case 'cond_strategy':
      stage.config.strategies = checkedValues(`[data-config="cond_strategy"][data-idx="${idx}"]`);
      break;
    case 'num_strategy':
      stage.config.strategies = checkedValues(`[data-config="num_strategy"][data-idx="${idx}"]`);
      break;
  }
}

function checkedValues(selector) {
  return Array.from(document.querySelectorAll(selector + ':checked')).map(el => el.value);
}

// ============================================================
// Drag & drop
// ============================================================

let dragSrcIdx = null;

function setupDragDrop(list) {
  Array.from(list.children).forEach(item => {
    item.addEventListener('dragstart', e => {
      dragSrcIdx = +item.dataset.idx;
      item.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
    });
    item.addEventListener('dragend', () => {
      item.classList.remove('dragging');
      dragSrcIdx = null;
    });
    item.addEventListener('dragover', e => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      item.classList.add('drag-over');
    });
    item.addEventListener('dragleave', () => item.classList.remove('drag-over'));
    item.addEventListener('drop', e => {
      e.preventDefault();
      item.classList.remove('drag-over');
      const destIdx = +item.dataset.idx;
      if (dragSrcIdx !== null && dragSrcIdx !== destIdx) {
        const [moved] = state.stages.splice(dragSrcIdx, 1);
        state.stages.splice(destIdx, 0, moved);
        renderStages();
      }
    });
  });
}

// ============================================================
// Pyodide init & package load
// ============================================================

async function initPyodide() {
  const statusEl = $('pyodide-status');
  try {
    if (typeof loadPyodide === 'undefined') throw new Error('Pyodide script not loaded');
    statusEl.textContent = 'Loading Pyodide…';
    statusEl.className = 'pyodide-status loading';

    state.pyodide = await loadPyodide();
    statusEl.textContent = 'Loading package…';

    await loadPackage();

    state.pyodideReady = true;
    statusEl.textContent = 'Client ready';
    statusEl.className = 'pyodide-status ready';
  } catch (err) {
    state.pyodideError = err.message;
    statusEl.textContent = 'Pyodide unavailable — server mode only';
    statusEl.className = 'pyodide-status error';
    console.warn('Pyodide init failed:', err);

    // Switch UI to server mode
    const radio = document.querySelector('input[name="execPath"][value="server"]');
    if (radio) radio.checked = true;
    state.executionPath = 'server';
    updateUploadVisibility();
  }
}

async function loadPackage() {
  const resp = await fetch('/package');
  if (!resp.ok) throw new Error(`/package returned ${resp.status}`);
  const files = await resp.json();

  const py = state.pyodide;

  // Create subdirectories
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

  // Write source files
  for (const [path, content] of Object.entries(files)) {
    py.FS.writeFile('/home/pyodide/' + path, content, { encoding: 'utf8' });
  }

  // Add to sys.path and trigger all registry registrations
  await py.runPythonAsync(`
import sys
if '/home/pyodide' not in sys.path:
    sys.path.insert(0, '/home/pyodide')
import pipeline
`);
}

// ============================================================
// Config builder
// ============================================================

function buildConfig() {
  const get = id => state.stages.find(s => s.id === id) || {};
  const junk  = get('junk');
  const loops = get('loops');
  const conds = get('conditionals');
  const ids   = get('identities');
  const nums  = get('numbers');
  const ren   = get('renaming');

  const seedRaw = $('seed').value.trim();

  return {
    enable_junk:          junk.enabled  ?? true,
    enable_loops:         loops.enabled ?? true,
    enable_conditionals:  conds.enabled ?? true,
    enable_identities:    ids.enabled   ?? true,
    enable_numbers:       nums.enabled  ?? true,
    enable_renaming:      ren.enabled   ?? true,
    junk_strategies:      junk.config?.strategies  ?? [],
    junk_density:         junk.config?.density     ?? 2,
    loop_strategy:        loops.config?.strategy   ?? 'CollatzStrategy',
    conditional_strategies: conds.config?.strategies ?? [],
    identity_probability: ids.config?.probability  ?? 0.2,
    number_strategies:    nums.config?.strategies  ?? [],
    stage_order:          state.stages.map(s => s.id),
    seed:                 seedRaw ? parseInt(seedRaw, 10) : null,
    return_code:          true,
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
    // Stub: echo with notice when opened outside the FastAPI server
    return `# [Demo mode — Pyodide not available]\n# Serve via FastAPI for full client-side execution.\n\n${code}`;
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
    enable_junk=cfg_data['enable_junk'],
    enable_loops=cfg_data['enable_loops'],
    enable_conditionals=cfg_data['enable_conditionals'],
    enable_identities=cfg_data['enable_identities'],
    enable_numbers=cfg_data['enable_numbers'],
    enable_renaming=cfg_data['enable_renaming'],
    junk_strategies=cfg_data['junk_strategies'],
    junk_density=cfg_data['junk_density'],
    loop_strategy=cfg_data['loop_strategy'],
    conditional_strategies=cfg_data['conditional_strategies'],
    identity_probability=cfg_data['identity_probability'],
    number_strategies=cfg_data['number_strategies'],
    stage_order=cfg_data['stage_order'],
    seed=cfg_data['seed'],
)
run_pipeline(cfg)
`);
}

async function runServerSide(_code) {
  // Lambda path wired in plan 4a
  throw new Error('Server (Lambda) execution not yet wired — coming in plan 4a.\nUse Client mode for now.');
}

// ============================================================
// Custom module upload (plan 2c)
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
json.dumps({
    'junk': sorted(k for k in JunkInjectionStrategy._registry if k != 'JunkInjectionStrategy'),
    'conditional': sorted(k for k in JunkConditionalStrategy._registry if k != 'JunkConditionalStrategy'),
    'loop': sorted(k for k in LoopObfuscationStrategy._registry if k != 'LoopObfuscationStrategy'),
    'number': sorted(k for k in NumberObscureStrategy._registry if k != 'NumberObscureStrategy'),
})
`);

  const reg = JSON.parse(registriesJson);

  state.stages.forEach(stage => {
    if (stage.id === 'junk')         stage.allStrategies = reg.junk;
    if (stage.id === 'loops')        stage.allStrategies = reg.loop;
    if (stage.id === 'conditionals') stage.allStrategies = reg.conditional;
    if (stage.id === 'numbers')      stage.allStrategies = reg.number;
  });

  renderStages();
}

// ============================================================
// UI helpers
// ============================================================

function updateUploadVisibility() {
  const section = $('upload-section');
  if (section) section.style.display = state.executionPath === 'client' ? '' : 'none';
}

// ============================================================
// Init
// ============================================================

function init() {
  renderStages();

  // Execution path toggle
  document.querySelectorAll('input[name="execPath"]').forEach(radio => {
    radio.addEventListener('change', e => {
      state.executionPath = e.target.value;
      updateUploadVisibility();
    });
  });

  // Submit button
  $('submit-btn').addEventListener('click', handleSubmit);

  // Ctrl+Enter shortcut
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
  });

  // Copy button
  $('copy-btn').addEventListener('click', () => {
    const text = $('output').value;
    if (text) navigator.clipboard.writeText(text).catch(() => {});
  });

  // Custom module upload
  $('custom-upload').addEventListener('change', e => {
    const file = e.target.files[0];
    if (file) handleCustomUpload(file);
    e.target.value = '';
  });

  // Kick off Pyodide (non-blocking)
  initPyodide();
}

document.addEventListener('DOMContentLoaded', init);
