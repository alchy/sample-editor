/**
 * Sample Editor — frontend aplikace
 * Komunikuje s FastAPI backendem na http://127.0.0.1:8000
 */

const API = 'http://127.0.0.1:8000/api/v1';

// ── Stav aplikace ────────────────────────────────────────
let state = {
  session: null,          // název aktuální session
  velLayers: 8,           // počet velocity vrstev
  samples: [],            // [ { filename, file_path, detected_midi, velocity_amplitude, ... } ]
  mapping: {},            // { "midi_vel": { ...sample } }  klíč = "60_3"
  dragSample: null,       // sample právě přetahovaný
};

// MIDI noty — A0 (21) až C8 (108)
const NOTE_NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
function midiToName(n) {
  const oct = Math.floor(n / 12) - 1;
  return NOTE_NAMES[n % 12] + oct;
}

// ── Helpers ──────────────────────────────────────────────
function status(msg, type = '') {
  const el = document.getElementById('status-bar');
  el.textContent = msg;
  el.className = type;
}

async function api(method, path, body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(API + path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

function openModal(id)  { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

// ── Session ──────────────────────────────────────────────
async function loadSessionList() {
  try {
    const data = await api('GET', '/session/list');
    const sel = document.getElementById('session-select');
    sel.innerHTML = '<option value="">— vybrat session —</option>';
    data.sessions.forEach(name => {
      const opt = document.createElement('option');
      opt.value = opt.textContent = name;
      sel.appendChild(opt);
    });
  } catch (e) {
    status('Nepodařilo se načíst seznam sessions: ' + e.message, 'error');
  }
}

async function loadSession(name) {
  if (!name) return;
  try {
    status('Načítám session…');
    const info = await api('GET', `/session/${encodeURIComponent(name)}`);
    state.session = name;
    state.velLayers = info.velocity_layers || 8;
    document.getElementById('vel-layers').value = state.velLayers;
    document.getElementById('session-label').textContent = `Session: ${name}  (${state.velLayers} vel. vrstev)`;
    document.getElementById('btn-scan').disabled = false;
    document.getElementById('btn-analyze').disabled = false;
    document.getElementById('btn-export').disabled = false;
    rebuildMatrix();
    status(`Session "${name}" načtena.`, 'ok');
    await loadUploadedSamples();
  } catch (e) {
    status('Chyba při načítání session: ' + e.message, 'error');
  }
}

function openNewSessionModal() { openModal('modal-new-session'); }

async function createSession() {
  const name = document.getElementById('ns-name').value.trim();
  if (!name) { alert('Zadej název session.'); return; }
  const vel = parseInt(document.getElementById('ns-vel').value) || 8;
  const instrument = document.getElementById('ns-instrument').value.trim();
  try {
    status('Vytvářím session…');
    await api('POST', '/session', {
      name, velocity_layers: vel,
      instrument_name: instrument || undefined,
    });
    closeModal('modal-new-session');
    await loadSessionList();
    document.getElementById('session-select').value = name;
    await loadSession(name);
  } catch (e) {
    status('Chyba: ' + e.message, 'error');
  }
}

// ── Upload souborů ────────────────────────────────────────
function triggerUpload() {
  document.getElementById('upload-input').click();
}

function handleFileInputChange(input) {
  if (input.files.length) uploadFileList(Array.from(input.files));
  input.value = '';   // reset pro opakované nahrání stejných souborů
}

async function uploadFileList(files) {
  if (!state.session) { status('Nejdříve vyber session.', 'error'); return; }
  const total = files.length;
  setUploadProgress(0, total);
  status(`Nahrávám ${total} souborů na server…`);

  const form = new FormData();
  files.forEach(f => form.append('files', f));

  try {
    const res = await fetch(`${API}/files/${encodeURIComponent(state.session)}/upload`, {
      method: 'POST',
      body: form,
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    setUploadProgress(data.uploaded, total);
    status(`Nahráno ${data.uploaded} souborů${data.skipped ? `, přeskočeno ${data.skipped}` : ''}. Načítám seznam…`, 'ok');
    await loadUploadedSamples();
  } catch (e) {
    status('Chyba při nahrávání: ' + e.message, 'error');
    setUploadProgress(0, 0);
  }
}

async function loadUploadedSamples() {
  try {
    const data = await fetch(`${API}/files/${encodeURIComponent(state.session)}/samples`).then(r => r.json());
    state.samples = data.files.map(fp => ({
      filename: fp.replace(/\\/g, '/').split('/').pop(),
      file_path: fp,
      detected_midi: null,
      velocity_amplitude: null,
      analyzed: false,
    }));
    renderSampleList();
    status(`${data.count} souborů v session. Klikni "Analyzovat".`, 'ok');
  } catch (e) {
    status('Nepodařilo se načíst seznam souborů: ' + e.message, 'error');
  }
}

function setUploadProgress(done, total) {
  const fill = document.getElementById('upload-progress-fill');
  const hint = document.getElementById('upload-hint');
  if (!total) {
    fill.style.width = '0%';
    hint.textContent = '↑ přetáhni WAV/AIF sem';
    return;
  }
  const pct = Math.round((done / total) * 100);
  fill.style.width = pct + '%';
  hint.textContent = done === total ? `✓ ${done} souborů nahráno` : `Nahrávám… ${pct}%`;
}

// ── Drag-drop nahrávání na dropzone ──────────────────────
function initUploadDropzone() {
  const zone = document.getElementById('upload-dropzone');
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dz-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dz-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('dz-over');
    const files = Array.from(e.dataTransfer.files).filter(
      f => /\.(wav|aif|aiff|flac)$/i.test(f.name)
    );
    if (files.length) uploadFileList(files);
  });
  zone.addEventListener('click', () => { if (state.session) triggerUpload(); });
}

// ── Analýza ──────────────────────────────────────────────
async function analyzeAll() {
  if (!state.samples.length) { status('Nejdříve načti složku se sampley.', 'error'); return; }
  const btn = document.getElementById('btn-analyze');
  btn.disabled = true;
  btn.textContent = '⏳ Analyzuji…';

  try {
    status(`Analyzuji ${state.samples.length} souborů (CREPE pitch + RMS velocity)…`);
    const data = await api('POST', '/analyze/batch', {
      file_paths: state.samples.map(s => s.file_path),
      session_name: state.session,
    });

    // Aktualizovat state.samples výsledky analýzy
    const byPath = {};
    data.results.forEach(r => { byPath[r.file_path] = r; });
    state.samples = state.samples.map(s => byPath[s.file_path] || s);

    renderSampleList();
    status(`Analýza dokončena: ${data.successful} OK, ${data.failed} selhalo, ${data.from_cache} z cache.`, 'ok');
  } catch (e) {
    status('Chyba analýzy: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '🔍 Analyzovat';
  }
}

// ── Auto-assign ──────────────────────────────────────────
function autoAssign() {
  // Seřadit sampley podle detected_midi a velocity_amplitude
  const analyzed = state.samples.filter(s => s.detected_midi != null);
  if (!analyzed.length) { status('Nejdříve analyzuj sampley.', 'error'); return; }

  // Seskupit podle MIDI noty
  const byMidi = {};
  analyzed.forEach(s => {
    const m = s.detected_midi;
    if (!byMidi[m]) byMidi[m] = [];
    byMidi[m].push(s);
  });

  // Pro každou notu: seřadit podle velocity_amplitude a rozdělit do vrstev
  const newMapping = {};
  Object.entries(byMidi).forEach(([midi, samples]) => {
    const sorted = [...samples].sort((a, b) => (a.velocity_amplitude || 0) - (b.velocity_amplitude || 0));
    const layers = Math.min(sorted.length, state.velLayers);
    sorted.slice(0, layers).forEach((s, i) => {
      const velIdx = Math.round(i * (state.velLayers - 1) / Math.max(layers - 1, 1));
      newMapping[`${midi}_${velIdx}`] = s;
    });
  });

  state.mapping = newMapping;
  renderMatrix();
  document.getElementById('btn-auto').disabled = false;
  status(`Auto-assign dokončen: ${Object.keys(newMapping).length} buněk přiřazeno.`, 'ok');
}

// ── Sample list ───────────────────────────────────────────
function renderSampleList() {
  const el = document.getElementById('sample-list');
  document.getElementById('sample-count').textContent = state.samples.length;
  document.getElementById('btn-auto').disabled = state.samples.length === 0;

  el.innerHTML = '';
  state.samples.forEach((s, idx) => {
    const div = document.createElement('div');
    div.className = 'sample-item';
    div.draggable = true;
    div.dataset.idx = idx;

    const name = document.createElement('div');
    name.className = 'sample-name';
    name.textContent = s.filename;

    const meta = document.createElement('div');
    meta.className = 'sample-meta';

    if (s.detected_midi != null) {
      const badge = document.createElement('span');
      badge.className = 'midi-badge';
      badge.textContent = midiToName(s.detected_midi) + ' (' + s.detected_midi + ')';
      meta.appendChild(badge);
    } else if (s.analyzed === false) {
      const badge = document.createElement('span');
      badge.style.cssText = 'color:#555; font-size:10px;';
      badge.textContent = 'neanalyzováno';
      meta.appendChild(badge);
    }

    if (s.velocity_amplitude != null) {
      const vel = document.createElement('span');
      vel.className = 'vel-badge';
      vel.textContent = 'vel: ' + s.velocity_amplitude.toFixed(3);
      meta.appendChild(vel);
    }

    div.appendChild(name);
    div.appendChild(meta);

    // Drag events
    div.addEventListener('dragstart', e => {
      state.dragSample = s;
      div.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'copy';
    });
    div.addEventListener('dragend', () => div.classList.remove('dragging'));

    // Klik = přehraj
    div.addEventListener('click', () => playSample(s));

    el.appendChild(div);
  });
}

// ── VU Meter (Web Audio API) ──────────────────────────────
const VU = (() => {
  let ctx = null, analyser = null, source = null, rafId = null;
  const BARS = 20;
  const BAR_GAP = 2;

  function init(audioEl) {
    if (ctx) return;
    ctx = new (window.AudioContext || window.webkitAudioContext)();
    analyser = ctx.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.75;
    source = ctx.createMediaElementSource(audioEl);
    source.connect(analyser);
    analyser.connect(ctx.destination);
  }

  function draw() {
    const canvas = document.getElementById('vu-meter');
    const c = canvas.getContext('2d');
    const W = canvas.width, H = canvas.height;
    rafId = requestAnimationFrame(draw);

    const buf = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(buf);
    const rms = Math.sqrt(buf.reduce((s, v) => s + v * v, 0) / buf.length) / 255;

    c.clearRect(0, 0, W, H);

    // Background track
    c.fillStyle = '#0d1a30';
    c.fillRect(0, 0, W, H);

    const totalW = W - 2;
    const barW = (totalW - (BARS - 1) * BAR_GAP) / BARS;
    const lit = Math.round(rms * BARS);

    for (let i = 0; i < BARS; i++) {
      const x = 1 + i * (barW + BAR_GAP);
      // Color: green → amber → red
      let color;
      if (i < BARS * 0.6)       color = i < lit ? '#00e060' : '#0a2818';
      else if (i < BARS * 0.85) color = i < lit ? '#ffb000' : '#2a1c00';
      else                       color = i < lit ? '#ff2020' : '#2a0808';

      // LED glow on lit bars
      if (i < lit) {
        c.shadowBlur = 4;
        c.shadowColor = color;
      } else {
        c.shadowBlur = 0;
      }

      // Draw bar with slight bevel
      c.fillStyle = color;
      c.fillRect(x, 3, barW, H - 6);

      // Top highlight
      if (i < lit) {
        c.fillStyle = 'rgba(255,255,255,0.15)';
        c.fillRect(x, 3, barW, 2);
      }
    }
    c.shadowBlur = 0;

    // Peak hold indicator
    VU._peak = Math.max(VU._peak * 0.992, rms);
    const px = 1 + Math.round(VU._peak * (BARS - 1)) * (barW + BAR_GAP);
    c.fillStyle = VU._peak > 0.85 ? '#ff2020' : VU._peak > 0.6 ? '#ffb000' : '#00e060';
    c.shadowBlur = 6;
    c.shadowColor = c.fillStyle;
    c.fillRect(px, 3, barW, H - 6);
    c.shadowBlur = 0;
  }

  return {
    _peak: 0,
    start(audioEl) {
      init(audioEl);
      if (ctx.state === 'suspended') ctx.resume();
      if (!rafId) draw();
    },
    stop() {
      if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
    },
  };
})();

// ── Přehrávání ────────────────────────────────────────────
function playSample(s) {
  const audio = document.getElementById('audio-elem');
  const label = document.getElementById('now-playing');
  audio.src = `${API}/audio/file?file_path=${encodeURIComponent(s.file_path)}`;
  label.textContent = s.filename;
  audio.play().catch(() => {});
  VU.start(audio);
  audio.onended = () => { VU._peak = 0; };
}

// ── Mapping matrix ────────────────────────────────────────
function rebuildMatrix() {
  state.velLayers = parseInt(document.getElementById('vel-layers').value) || 8;
  renderMatrix();
}

function renderMatrix() {
  const container = document.getElementById('matrix-container');
  container.innerHTML = '';

  // Hlavička velocity vrstev
  const header = document.createElement('div');
  header.className = 'matrix-header';
  for (let v = 0; v < state.velLayers; v++) {
    const th = document.createElement('div');
    th.className = 'vel-header';
    th.textContent = `vel ${v}`;
    header.appendChild(th);
  }
  container.appendChild(header);

  // Řádky: MIDI noty od 108 (C8) dolů do 21 (A0)
  for (let midi = 108; midi >= 21; midi--) {
    const row = document.createElement('div');
    row.className = 'matrix-row';

    const label = document.createElement('div');
    label.className = 'note-label' + (midi % 12 === 0 ? ' c-note' : '');
    label.textContent = midiToName(midi) + ' (' + midi + ')';
    row.appendChild(label);

    for (let v = 0; v < state.velLayers; v++) {
      row.appendChild(makeCell(midi, v));
    }
    container.appendChild(row);
  }
}

function makeCell(midi, vel) {
  const cell = document.createElement('div');
  cell.className = 'matrix-cell';
  cell.dataset.midi = midi;
  cell.dataset.vel = vel;

  const key = `${midi}_${vel}`;
  if (state.mapping[key]) {
    setCellFilled(cell, state.mapping[key]);
  }

  // Drag-over
  cell.addEventListener('dragover', e => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    cell.classList.add('drag-over');
  });
  cell.addEventListener('dragleave', () => cell.classList.remove('drag-over'));
  cell.addEventListener('drop', e => {
    e.preventDefault();
    cell.classList.remove('drag-over');
    if (state.dragSample) {
      state.mapping[key] = state.dragSample;
      setCellFilled(cell, state.dragSample);
      state.dragSample = null;
    }
  });

  // Klik = přehraj
  cell.addEventListener('click', e => {
    if (e.target.classList.contains('cell-remove')) return;
    if (state.mapping[key]) playSample(state.mapping[key]);
  });

  return cell;
}

function setCellFilled(cell, sample) {
  cell.classList.add('filled');
  cell.innerHTML = `
    <span class="cell-name" title="${sample.filename}">${sample.filename}</span>
    <span class="cell-remove" title="Odebrat" onclick="removeMapping(${cell.dataset.midi},${cell.dataset.vel},this)">✕</span>
  `;
}

function removeMapping(midi, vel, btn) {
  const key = `${midi}_${vel}`;
  delete state.mapping[key];
  const cell = btn.closest('.matrix-cell');
  cell.classList.remove('filled');
  cell.innerHTML = '';
  // Znovu přidat drag listenery
  const newCell = makeCell(parseInt(midi), parseInt(vel));
  cell.parentNode.replaceChild(newCell, cell);
}

// ── Export ────────────────────────────────────────────────
function openExportModal() {
  if (!Object.keys(state.mapping).length) {
    status('Nejdříve přiřaď sampley do matice.', 'error'); return;
  }
  openModal('modal-export');
}

function buildExportMapping() {
  return Object.entries(state.mapping).map(([key, s]) => {
    const [midi, vel] = key.split('_').map(Number);
    return { midi_note: midi, velocity: vel, file_path: s.file_path };
  });
}

async function runExport() {
  closeModal('modal-export');
  const btn = document.getElementById('btn-export');
  btn.disabled = true;
  btn.textContent = '⏳ Exportuji…';
  try {
    status('Exportuji sampley…');
    const result = await api('POST', '/export', {
      session_name: state.session,
      mapping: buildExportMapping(),
      include_instrument_definition: document.getElementById('export-def').checked,
    });
    status(
      `Export dokončen: ${result.exported_count} souborů, ${result.failed_count} chyb.`,
      result.failed_count === 0 ? 'ok' : 'error'
    );
    await showDownloadModal();
  } catch (e) {
    status('Chyba exportu: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '⬇ Export';
  }
}

async function showDownloadModal() {
  try {
    const data = await fetch(`${API}/files/${encodeURIComponent(state.session)}/export`).then(r => r.json());
    const list = document.getElementById('download-file-list');
    list.innerHTML = data.files.map(f =>
      `<div class="download-file-row">
        <span class="download-fname">${f.name}</span>
        <span class="download-fsize">${(f.size/1024).toFixed(1)} kB</span>
        <a class="download-link" href="${API}/files/${encodeURIComponent(state.session)}/export/${encodeURIComponent(f.name)}" download="${f.name}">⬇</a>
       </div>`
    ).join('');
    openModal('modal-download');
  } catch (e) {
    status('Nepodařilo se načíst seznam exportů: ' + e.message, 'error');
  }
}

function downloadZip() {
  window.location.href = `${API}/files/${encodeURIComponent(state.session)}/export/zip`;
}

async function previewExport() {
  try {
    status('Generuji náhled exportu…');
    const items = await api('POST', '/export/preview', {
      session_name: state.session,
      mapping: buildExportMapping(),
      include_instrument_definition: document.getElementById('export-def').checked,
    });
    const valid = items.filter(i => i.valid).length;
    alert(`Náhled exportu:\n${items.length} souborů celkem (${valid} platných)\n\nPrvní soubor: ${items[0]?.output_file || '—'}`);
    status(`Náhled: ${items.length} souborů připraveno.`, 'ok');
  } catch (e) {
    status('Chyba náhledu: ' + e.message, 'error');
  }
}

// ── Log panel ─────────────────────────────────────────────
let _logEs = null;
let _logCount = 0;
let _logHasError = false;

function initLogStream() {
  if (_logEs) { _logEs.close(); _logEs = null; }
  _logEs = new EventSource(`${API}/logs/stream`);
  _logEs.onmessage = e => {
    try {
      const rec = JSON.parse(e.data);
      _appendLogLine(rec.time, rec.level, rec.msg);
    } catch (_) {}
  };
  // EventSource se automaticky reconnectuje při chybě — není třeba handler
}

function _appendLogLine(time, level, msg) {
  const body = document.getElementById('log-body');
  const line = document.createElement('div');
  line.className = `log-line ${level}`;
  line.textContent = `${time} [${level.padEnd(8)}] ${msg}`;
  body.appendChild(line);

  // Max 300 řádků
  while (body.children.length > 300) body.removeChild(body.firstChild);
  body.scrollTop = body.scrollHeight;

  _logCount++;
  const badge = document.getElementById('log-badge');
  badge.textContent = _logCount > 999 ? '999+' : _logCount;

  if (level === 'ERROR' || level === 'CRITICAL') {
    if (!_logHasError) {
      _logHasError = true;
      badge.classList.add('has-error');
      // Rozbal panel při první chybě
      document.getElementById('log-panel').classList.remove('collapsed');
    }
  }
}

function toggleLog() {
  document.getElementById('log-panel').classList.toggle('collapsed');
}

function clearLog(e) {
  e.stopPropagation();
  document.getElementById('log-body').innerHTML = '';
  _logCount = 0;
  _logHasError = false;
  const badge = document.getElementById('log-badge');
  badge.textContent = '0';
  badge.classList.remove('has-error');
}

// ── Init ──────────────────────────────────────────────────
(async function init() {
  initUploadDropzone();
  initLogStream();
  await loadSessionList();
  status('API připojeno. Vytvoř nebo vyber session.');
})();
