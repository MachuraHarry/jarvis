'use strict';
/* J.A.R.V.I.S. HUD – robust: jede Nachricht einzeln abgesichert, Fehler werden an Python gemeldet,
   Herzschlag alle 5 s (Python lädt das HUD neu, wenn er ausbleibt). Texte immer per textContent. */
const $ = s => document.querySelector(s);
const post = m => { try { window.webkit.messageHandlers.jarvis.postMessage(JSON.stringify(m)); } catch (e) { /* kein Python */ } };
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
window.addEventListener('error', e => post({ cmd: 'jserr', msg: `${e.message} @${e.lineno}` }));
setInterval(() => post({ cmd: 'hb', fps: window.graphFps || 0 }), 5000);

/* ───── Uhr ───── */
const WD = ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag'];
const MO = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'];
const pad = n => String(n).padStart(2, '0');
/* Nur schreiben, wenn sich der Wert ändert – jede DOM-Änderung kostet ein komplettes Neuzeichnen (GPU + Xorg) */
const setTxt = (e, v) => { if (e && e.textContent !== String(v)) e.textContent = v; };
let paused = false, clockTimer = null;
/* Einfrieren: Bildschirm aus ODER HUD hat keinen Fokus -> keine Uhr, keine Diagramme, keine Animationen.
   Messwerte werden weiter gesammelt und beim Auftauen auf einmal angezeigt. */
const freeze = { screen: false, focus: false };
function setFrozen(why, on) {
  freeze[why] = on;
  const f = freeze.screen || freeze.focus;
  if (f === paused) return;
  paused = f; document.body.classList.toggle('paused', paused);
  if (paused) { clearInterval(clockTimer); clockTimer = null; stopAnim(); stopGraphs(); }
  else { startClock(); if (lastStats && lastStats.cpu !== undefined) stats(lastStats); startGraphs(); if (SPEED[state]) startAnim(); }
}
function tick() {
  const d = new Date();
  const hm = pad(d.getHours()) + ':' + pad(d.getMinutes()), c = $('#clock').firstChild;
  if (c.nodeValue !== hm) c.nodeValue = hm;
  setTxt($('#secs'), pad(d.getSeconds()));
  setTxt($('#date'), `${WD[d.getDay()]}, ${d.getDate()}. ${MO[d.getMonth()]} ${d.getFullYear()}`);
}
function startClock() { clearInterval(clockTimer); tick(); clockTimer = setInterval(tick, 1000); }
startClock();

/* ───── Telemetrie & Statusleiste ───── */
const ARC = 188.5;
const gaugeLast = {};
function gauge(id, val, max, unit, warn) {
  const key = Math.round(val || 0) + unit + (warn ? 1 : 0);
  if (gaugeLast[id] === key) return;
  gaugeLast[id] = key;
  const g = $(id), v = Math.max(0, Math.min(1, (val || 0) / max));
  g.querySelector('.val').style.strokeDashoffset = ARC * (1 - v);
  const n = g.querySelector('.g-num'); n.textContent = Math.round(val || 0);
  n.appendChild(el('small', null, unit));
  g.style.setProperty('--gc', warn ? 'var(--red)' : v > .75 ? 'var(--amber)' : 'var(--cyan)');
}
/* Laufende Telemetrie-Diagramme: drei Spuren, scrollen durchgehend flüssig (Werte alle 2 s, dazwischen interpoliert) */
const HIST = 121;   // 2 Minuten bei 1 Messwert pro Sekunde
const lanes = [
  { key: 'cpu', label: 'CPU', unit: '%', max: 100, col: '#38e8ff', h: new Array(HIST).fill(0) },
  { key: 'net', label: 'NETZ ↓', unit: 'KB/s', max: 0, col: '#5dffb0', col2: '#ffb547', label2: '↑', h: new Array(HIST).fill(0), h2: new Array(HIST).fill(0) },
  { key: 'gpu_load', label: 'GPU', unit: '%', max: 100, col: '#b48cff', h: new Array(HIST).fill(0) },
];
const GRAPH_FPS = 5;   // feste Bildrate der Diagramme (0 = Display-Takt, so viel wie möglich)
let lastSampleT = performance.now(), graphTimer = null, SAMPLE_MS = 1000;
const fmtRate = v => v >= 1024 ? (v / 1024).toFixed(1) + ' MB/s' : Math.round(v) + ' KB/s';
function pushSample(s) {
  const now = performance.now(), d = now - lastSampleT;
  if (d > 300 && d < 5000) SAMPLE_MS = SAMPLE_MS * 0.8 + d * 0.2;     // tatsächlichen Messtakt mitlernen
  lanes[0].h.push(s.cpu || 0); lanes[0].h.shift();
  lanes[1].h.push(s.net_rx || 0); lanes[1].h.shift(); lanes[1].h2.push(s.net_tx || 0); lanes[1].h2.shift();
  lanes[2].h.push(s.gpu_load || 0); lanes[2].h.shift();
  lastSampleT = performance.now();
}
function drawGraphs() {
  const c = $('#spark'); if (!c) return;
  const x = c.getContext('2d'), W = c.width, H = c.height;
  const LH = H / lanes.length, step = W / (HIST - 2);
  const frac = Math.min(1, (performance.now() - lastSampleT) / SAMPLE_MS);    // Fortschritt bis zum nächsten Messwert
  x.clearRect(0, 0, W, H);
  lanes.forEach((ln, li) => {
    const y0 = li * LH, top = y0 + 22, bot = y0 + LH - 6, hh = bot - top;
    const max = ln.max || Math.max(8, ...ln.h, ...(ln.h2 || [])) * 1.15;
    x.strokeStyle = 'rgba(56,232,255,.08)'; x.lineWidth = 1;
    for (let g = 0; g <= 2; g++) { const yy = top + hh * g / 2; x.beginPath(); x.moveTo(0, yy); x.lineTo(W, yy); x.stroke(); }
    const series = [[ln.h, ln.col, true]].concat(ln.h2 ? [[ln.h2, ln.col2, false]] : []);
    series.forEach(([arr, col, fill]) => {
      const pts = arr.map((v, i) => [(i - frac) * step, bot - Math.min(1, v / max) * hh]);
      if (fill) {
        const gr = x.createLinearGradient(0, top, 0, bot); gr.addColorStop(0, col + '55'); gr.addColorStop(1, col + '00');
        x.beginPath(); x.moveTo(pts[0][0], bot); pts.forEach(p => x.lineTo(p[0], p[1])); x.lineTo(pts[pts.length - 1][0], bot); x.closePath(); x.fillStyle = gr; x.fill();
      }
      x.beginPath(); pts.forEach((p, i) => i ? x.lineTo(p[0], p[1]) : x.moveTo(p[0], p[1]));
      x.strokeStyle = col; x.lineWidth = 2; x.stroke();
      const lp = pts[pts.length - 1]; x.fillStyle = col; x.beginPath(); x.arc(Math.min(lp[0], W - 4), lp[1], 3, 0, 7); x.fill();
    });
    const cur = ln.h[HIST - 1], cur2 = ln.h2 ? ln.h2[HIST - 1] : null;
    x.font = '600 15px Orbitron'; x.fillStyle = '#5f8a99'; x.fillText(ln.label, 4, y0 + 16);
    x.font = '17px Mono'; x.textAlign = 'right';
    if (ln.key === 'net') { x.fillStyle = ln.col; x.fillText('↓ ' + fmtRate(cur), W - 130, y0 + 16); x.fillStyle = ln.col2; x.fillText('↑ ' + fmtRate(cur2), W - 4, y0 + 16); }
    else { x.fillStyle = ln.col; x.fillText(Math.round(cur) + ' ' + ln.unit, W - 4, y0 + 16); }
    x.textAlign = 'left';
  });
}
// Der Systemgraph (#spark) wurde entfernt (Platz für die Uhr) -> startGraphs/stopGraphs sind nur noch
// die Gegenstücke zu startClock/stopClock in setFrozen, ohne eigene Dauerschleife. Die echte
// fps-Messung für den hb-Herzschlag läuft jetzt in frame() (nur während listening/thinking/speaking aktiv).
function startGraphs() {}
function stopGraphs() {}
window.graphFps = 0;
const fmtUp = s => { const d = Math.floor(s / 86400), h = Math.floor(s % 86400 / 3600), m = Math.floor(s % 3600 / 60); return (d ? d + 'd ' : '') + pad(h) + ':' + pad(m); };
const sigBars = s => s >= 75 ? 4 : s >= 50 ? 3 : s >= 25 ? 2 : s > 0 ? 1 : 0;
let lastStats = {};
function stats(s) {
  if (paused && s !== lastStats) { lastStats = s; pushSample(s); return; }   // eingefroren: nur sammeln
  if (s !== lastStats) { lastStats = s; pushSample(s); }
  gauge('#g-cpu', s.cpu, 100, '%');
  gauge('#g-ram', s.ram, 100, '%', s.ram > 92);
  gauge('#g-bat', s.bat, 100, s.charging ? '⚡' : '%', s.bat < 15 && !s.charging);
  gauge('#g-tmp', s.temp, 90, '°', s.temp > 75);
  setTxt($('#f-thru'), `↓ ${fmtRate(s.net_rx || 0)}  ↑ ${fmtRate(s.net_tx || 0)}`);
  setTxt($('#f-freq'), `A53 ${s.f_little ?? '–'} · A73 ${s.f_big ?? '–'} MHz`);
  setTxt($('#f-gpu'), `${s.gpu_mhz ?? '–'} MHz · ${s.gpu_load ?? '–'} % · ${s.gpu_temp ?? '–'}°`);
  setTxt($('#f-batp'), `${s.bat_ma > 0 ? '+' : ''}${s.bat_ma ?? '–'} mA · ${s.bat_w ?? '–'} W · ${s.bat_temp ?? '–'}°`);
  setTxt($('#f-disk'), `R ${fmtRate(s.disk_r || 0)}  W ${fmtRate(s.disk_w || 0)}`);
  setTxt($('#f-net'), s.ssid || (s.wifi_radio === false ? 'WLAN aus' : 'nicht verbunden'));
  setTxt($('#f-ram'), `${Math.round(s.ram_mb / 10) * 10} / ${s.ram_total} MB`);
  setTxt($('#f-swap'), `${Math.round(s.swap_mb / 10) * 10} MB` + (s.zram_ratio ? ` · zram ${s.zram_ratio}:1` : ''));
  setTxt($('#f-load'), s.load + (s.procs ? ` · ${s.procs} Proz.` : ''));
  setTxt($('#f-up'), fmtUp(s.uptime || 0));
  // Statusleiste
  const bat = $('#c-bat');
  setTxt(bat.querySelector('span'), `${s.bat}%`);
  const bw = String(Math.max(1, Math.round(18 * s.bat / 100)));
  if (bat.querySelector('.fill').getAttribute('width') !== bw) bat.querySelector('.fill').setAttribute('width', bw);
  bat.classList.toggle('charging', !!s.charging);
  bat.classList.toggle('low', s.bat <= 25 && !s.charging);
  bat.classList.toggle('crit', s.bat <= 10 && !s.charging);
  const wf = $('#c-wifi'), b = sigBars(s.signal);
  wf.querySelectorAll('.bars i').forEach((x, i) => x.classList.toggle('on', i < b));
  setTxt(wf.querySelector('.ssid'), s.ssid || (s.wifi_radio === false ? 'WLAN aus' : s.wifi_connecting ? 'verbinde …' : 'kein WLAN'));
  wf.classList.toggle('off', !s.ssid);
  const vol = $('#c-vol');
  setTxt(vol.querySelector('span'), s.muted ? 'STUMM' : `${s.vol}%`);
  vol.classList.toggle('muted', !!s.muted);
  const br = $('#c-brain');
  br.classList.toggle('on', !!s.online); br.classList.toggle('off', !s.online);
  setTxt(br.querySelector('span'), s.online ? 'KI ONLINE' : 'KI OFFLINE');
  document.body.classList.toggle('offline', !s.online);
  recStart = s.rec || 0;
  $('#c-rec').hidden = !recStart; $('#b-rec').classList.toggle('on', !!recStart);
  setTxt($('#b-rec').querySelector('span'), recStart ? 'Stopp' : 'Aufnahme');
  recTick();
  if (!wifiOpen) return;
  $('#w-radio').textContent = s.wifi_radio === false ? 'WLAN EIN' : 'WLAN AUS';
}

let recStart = 0;
function recTick() { if (recStart) { const d = Math.max(0, Math.floor(Date.now() / 1000 - recStart));
  $('#c-rec').querySelector('span').textContent = `REC ${Math.floor(d / 60)}:${pad(d % 60)}`; } }
setInterval(recTick, 1000);

/* ───── Wetter ───── */
const WICON = c => c === 0 ? '☀️' : c <= 2 ? '🌤️' : c === 3 ? '☁️' : c <= 48 ? '🌫️' : c <= 57 ? '🌦️' : c <= 67 ? '🌧️' : c <= 77 ? '🌨️' : c <= 82 ? '🌦️' : c <= 86 ? '🌨️' : '⛈️';
const WTXT = {0:'Klar',1:'Überwiegend klar',2:'Teils bewölkt',3:'Bedeckt',45:'Nebel',48:'Reifnebel',51:'Leichter Niesel',53:'Niesel',55:'Starker Niesel',61:'Leichter Regen',63:'Regen',65:'Starker Regen',71:'Leichter Schnee',73:'Schnee',75:'Starker Schnee',80:'Schauer',81:'Schauer',82:'Heftige Schauer',85:'Schneeschauer',86:'Schneeschauer',95:'Gewitter',96:'Gewitter',99:'Gewitter'};
function weather(w) {
  const c = w.current, d = w.daily;
  $('#w-icon').textContent = (!c.is_day && c.weather_code <= 1) ? '🌙' : WICON(c.weather_code);
  $('#w-temp').textContent = Math.round(c.temperature_2m) + '°';
  $('#w-desc').textContent = `${WTXT[c.weather_code] || ''} · ${w.city || ''} · ${Math.round(c.wind_speed_10m)} km/h`;
  const box = $('#w-days'); box.textContent = '';
  for (let i = 0; i < Math.min(4, d.time.length); i++) {
    const name = i === 0 ? 'Heute' : i === 1 ? 'Morgen' : WD[new Date(d.time[i]).getDay()].slice(0, 2);
    const day = el('div', null, name);
    day.appendChild(el('span', 'ic', WICON(d.weather_code[i])));
    day.appendChild(el('b', null, `${Math.round(d.temperature_2m_max[i])}° / ${Math.round(d.temperature_2m_min[i])}°`));
    day.appendChild(document.createTextNode(`${d.precipitation_probability_max[i] ?? 0}% 💧`));
    box.appendChild(day);
  }
}

/* ───── Kern & Wellenring (gedrosselt; im Leerlauf steht alles still) ───── */
const FPS = 20, N = 72, bars = new Float32Array(N);
const SPEED = { idle: 0, listening: 2.2, thinking: 4, speaking: 1.4, boot: 0, error: 0 };
let level = 0, target = 0, state = 'boot', timer = null, rot = 0, waveCol = '#38e8ff';
let fpsN = 0, fpsT = performance.now();
const wave = $('#wave'), wx = wave.getContext('2d');
const rings = [...document.querySelectorAll('#core .ring')].map(e => ({ e, speed: +e.dataset.speed, a: Math.random() * 360 }));
const reactor = $('#core .reactor');
function frame() {
  const sp = SPEED[state] || 0;
  for (const r of rings) { r.a = (r.a + r.speed * sp / FPS) % 360; r.e.style.transform = `rotate(${r.a.toFixed(1)}deg)`; }
  level += (target - level) * .5; target *= .7;
  for (let i = N - 1; i > 0; i--) bars[i] = bars[i - 1] * .9;
  bars[0] = level * (0.6 + Math.random() * .8);
  const think = state === 'thinking' ? Math.sin(performance.now() / 160) * .04 : 0;
  reactor.style.transform = `scale(${(.85 + level * .45 + think).toFixed(3)})`;
  drawWave();
  // Echte Render-Rate der Wellenanimation fürs hb-fps-Feld (jarvis-doctor) -- misst, ob der Timer
  // tatsächlich mit FPS mithält oder (bei Überlastung) hinterherhinkt; läuft nur während der Animation.
  fpsN++; const t = performance.now();
  if (t - fpsT >= 2000) { window.graphFps = Math.round(fpsN * 1000 / (t - fpsT)); fpsN = 0; fpsT = t; }
  if (sp === 0 && level < .004 && target < .004 && !bars.some(b => b > .01)) stopAnim();
}
function drawWave() {
  const W = wave.width, cx = W / 2, r0 = W * .235;
  wx.clearRect(0, 0, W, W);
  if (!bars.some(b => b > .01)) return;
  wx.strokeStyle = waveCol; wx.lineWidth = 4; wx.lineCap = 'round';
  rot += .02; wx.beginPath();
  for (let i = 0; i < N; i++) {
    const v = bars[i < N / 2 ? i : N - 1 - i], ang = rot + i / N * Math.PI * 2, len = 3 + v * W * .13;
    const c = Math.cos(ang), s = Math.sin(ang);
    wx.moveTo(cx + c * r0, cx + s * r0); wx.lineTo(cx + c * (r0 + len), cx + s * (r0 + len));
  }
  wx.stroke();
}
function startAnim() { if (!timer) timer = setInterval(frame, 1000 / FPS); }
function stopAnim() { clearInterval(timer); timer = null; wx.clearRect(0, 0, wave.width, wave.width); reactor.style.transform = 'scale(.85)'; window.graphFps = 0; fpsN = 0; fpsT = performance.now(); }
function pushLevel(v) { if (v > .02) { target = Math.max(target, v); startAnim(); } }

const LABEL = { idle: 'BEREIT', listening: 'ICH HÖRE', thinking: 'ANALYSE', speaking: 'ANTWORT', boot: 'START', micoff: 'STUMM' };
let micOn = true;
function setState(s) {
  state = s;
  waveCol = s === 'thinking' ? '#ffb547' : s === 'listening' ? '#c8fbff' : '#38e8ff';
  if (SPEED[s]) startAnim();
  document.body.classList.remove('idle', 'listening', 'thinking', 'speaking', 'error');
  document.body.classList.add(s);
  $('#core-label').textContent = LABEL[(!micOn && s === 'idle') ? 'micoff' : s] || s.toUpperCase();
  $('#brand-state').textContent = s === 'thinking' ? 'VERARBEITUNG' : s === 'listening' ? 'EMPFANG' : 'SYSTEM ONLINE';
}
$('#core').addEventListener('click', () => post({ cmd: (state === 'speaking' || state === 'thinking') ? 'stop' : 'listen' }));

/* ───── Live-Aktivität des Agenten ───── */
const AICO = { idle: '●', listen: '◉', heard: '✓', think: '◆', run: '⟩', search: '⌕', web: '⇣', read: '▤', write: '✎', blocked: '⛨', speak: '♪' };
let actT0 = 0, actTimer = null;
function activity(kind, text, detail) {
  const a = $('#activity');
  a.className = kind;
  a.querySelector('.a-ico').textContent = AICO[kind] || '◆';
  const idleTxt = micOn ? 'Bereit – sag „Jarvis“ oder tippe auf den Kern' : 'Mikrofon aus – tippe auf den Kern oder schreib mir';
  a.querySelector('.a-lbl').textContent = kind === 'idle' ? idleTxt : (text || '');
  a.querySelector('.a-det').textContent = detail ? '· ' + detail.replace(/\s+/g, ' ') : '';
  clearInterval(actTimer); a.querySelector('.a-time').textContent = '';
  if (kind !== 'idle' && kind !== 'speak' && kind !== 'blocked') {
    actT0 = performance.now();
    actTimer = setInterval(() => { a.querySelector('.a-time').textContent = ((performance.now() - actT0) / 1000).toFixed(1) + ' s'; }, 250);
  }
}

/* ───── Protokoll ───── */
const log = $('#log');
let live = null;
const tools = {};
const nowHM = () => { const d = new Date(); return pad(d.getHours()) + ':' + pad(d.getMinutes()); };
const nearBottom = () => log.scrollHeight - log.scrollTop - log.clientHeight < 80;
function scrollDown(force) { if (force || nearBottom()) log.scrollTop = log.scrollHeight; }
function addMsg(cls, who, text) {
  const m = el('div', 'msg ' + cls);
  const w = el('div', 'who', who); w.appendChild(el('time', null, nowHM()));
  m.appendChild(w); m.appendChild(el('div', 'txt', text || ''));
  const stick = nearBottom();
  log.appendChild(m);
  while (log.children.length > 80) log.firstChild.remove();
  scrollDown(stick);
  return m;
}
const ensureLive = () => live || (live = addMsg('jarvis live', 'Jarvis', ''));
function addTool(m) {
  const l = ensureLive();
  const t = el('div', 'tool run');
  const h = el('div', 't-head'); h.appendChild(el('span', 't-lbl', m.label || m.name)); h.appendChild(el('span', 't-st', 'läuft …'));
  t.appendChild(h); t.appendChild(el('div', 't-cmd', m.detail || '')); t.appendChild(el('div', 't-out', ''));
  t.addEventListener('click', () => t.classList.toggle('open'));
  const stick = nearBottom();
  l.insertBefore(t, l.querySelector('.txt'));
  if (m.id) tools[m.id] = t;
  scrollDown(stick);
}
function toolResult(m) {
  const t = tools[m.id]; if (!t) return;
  delete tools[m.id];
  t.classList.remove('run'); t.classList.add(m.status);
  const txt = { ok: '✓', err: '✗ Fehler', blocked: '⛨ blockiert' }[m.status] || m.status;
  t.querySelector('.t-st').textContent = `${txt} · ${m.dur} s`;
  t.querySelector('.t-out').textContent = (m.out || '').trim();
}

/* ───── Hinweise ───── */
const TICO = { battery: '▮', charge: '⚡', wifi: '≋', info: 'i' };
function toast(m) {
  const box = $('#toasts');
  const t = el('div', 'toast ' + (m.level || 'info'));
  t.appendChild(el('span', 'ti', TICO[m.icon] || 'i')); t.appendChild(el('span', null, m.text));
  const kill = () => { t.classList.add('out'); setTimeout(() => t.remove(), 320); };
  t.addEventListener('click', kill);
  box.appendChild(t);
  while (box.children.length > 4) box.firstChild.remove();
  setTimeout(kill, m.level === 'crit' ? 30000 : 7000);
}

/* ───── WLAN-Manager ───── */
let wifiOpen = false, wifiAuto = false, wifiSel = null, wifiBusy = null;
const LOCK = '<svg viewBox="0 0 24 24"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 018 0v3"/></svg>';
function openWifi(auto) {
  wifiOpen = true; wifiAuto = !!auto;
  $('#wifi').hidden = false;
  $('#w-title').textContent = auto ? 'Keine WLAN-Verbindung – Netzwerk wählen' : 'WLAN';
  wmsg('', '');
  post({ cmd: 'wifi_scan', rescan: true });
}
function closeWifi() { wifiOpen = false; wifiSel = null; $('#wifi').hidden = true; post({ cmd: 'kbd_hide' }); }
function wmsg(text, cls) { const m = $('#w-msg'); m.textContent = text; m.className = cls || ''; }
function wifiList(nets, status) {
  if (!wifiOpen) return;
  const cur = $('#w-cur'); cur.textContent = '';
  if (status && status.ssid) { cur.appendChild(document.createTextNode('Verbunden mit ')); cur.appendChild(el('b', null, status.ssid)); }
  else cur.textContent = status && status.radio === false ? 'WLAN ist ausgeschaltet.' : 'Nicht verbunden.';
  $('#w-radio').textContent = status && status.radio === false ? 'WLAN EIN' : 'WLAN AUS';
  const list = $('#w-list');
  const typed = {}; list.querySelectorAll('.net').forEach(n => { const i = n.querySelector('input'); if (i && i.value) typed[n.dataset.ssid] = i.value; });
  list.textContent = '';
  if (!nets.length) { list.appendChild(el('div', 'w-empty', status && status.radio === false ? 'Schalte WLAN ein, um Netze zu sehen.' : 'Keine Netzwerke gefunden.')); return; }
  for (const n of nets) {
    const box = el('div', 'net' + (n.active ? ' active' : '') + (wifiSel === n.ssid ? ' open' : '') + (wifiBusy === n.ssid ? ' busy' : ''));
    box.dataset.ssid = n.ssid;
    const row = el('div', 'n-row');
    const b = el('span', 'bars'); for (let i = 0; i < 4; i++) { const x = el('i'); if (i < sigBars(n.signal)) x.className = 'on'; b.appendChild(x); }
    row.appendChild(b);
    row.appendChild(el('span', 'n-name', n.ssid));
    const tags = el('span', 'n-tags');
    if (n.active) tags.appendChild(el('span', null, 'verbunden'));
    else if (n.saved) tags.appendChild(el('span', null, 'gespeichert'));
    if (wifiBusy === n.ssid) tags.appendChild(el('span', null, '…'));
    if (n.secure) { const l = el('span'); l.innerHTML = LOCK; tags.appendChild(l); }
    row.appendChild(tags);
    row.addEventListener('click', () => { wifiSel = wifiSel === n.ssid ? null : n.ssid; list.querySelectorAll('.net').forEach(x => x.classList.toggle('open', x.dataset.ssid === wifiSel));
      const inp = box.querySelector('input'); if (inp && wifiSel === n.ssid) { inp.focus(); } });
    box.appendChild(row);
    const act = el('div', 'n-act');
    const btn = (label, fn, cls) => { const x = el('button', cls || '', label); x.type = 'button'; x.addEventListener('click', e => { e.stopPropagation(); fn(); }); act.appendChild(x); return x; };
    if (n.active) {
      btn('TRENNEN', () => post({ cmd: 'wifi_disconnect' }));
      btn('VERGESSEN', () => post({ cmd: 'wifi_forget', ssid: n.ssid }), 'danger');
    } else if (n.saved || !n.secure) {
      btn('VERBINDEN', () => connect(n.ssid, ''));
      if (n.saved) btn('VERGESSEN', () => post({ cmd: 'wifi_forget', ssid: n.ssid }), 'danger');
    } else {
      const inp = el('input'); inp.type = 'password'; inp.placeholder = 'Passwort für ' + n.ssid; inp.value = typed[n.ssid] || '';
      inp.autocomplete = 'off'; inp.spellcheck = false;
      inp.addEventListener('focus', () => post({ cmd: 'kbd_show' }));
      inp.addEventListener('keydown', e => { if (e.key === 'Enter') connect(n.ssid, inp.value); });
      inp.addEventListener('click', e => e.stopPropagation());
      act.appendChild(inp);
      btn('👁', () => { inp.type = inp.type === 'password' ? 'text' : 'password'; }, 'eye');
      btn('VERBINDEN', () => connect(n.ssid, inp.value));
    }
    box.appendChild(act);
    list.appendChild(box);
  }
}
function connect(ssid, pw) {
  const n = [...document.querySelectorAll('.net')].find(x => x.dataset.ssid === ssid);
  const needsPw = n && n.querySelector('input');
  if (needsPw && pw.length < 8) { wmsg('WPA-Passwörter haben mindestens 8 Zeichen.', 'err'); return; }
  post({ cmd: 'kbd_hide' });
  post({ cmd: 'wifi_connect', ssid, password: pw });
}
$('#w-close').addEventListener('click', closeWifi);
$('#w-refresh').addEventListener('click', () => { wmsg('Suche Netzwerke …', 'busy'); post({ cmd: 'wifi_scan', rescan: true }); });
$('#w-radio').addEventListener('click', () => post({ cmd: 'wifi_radio', on: $('#w-radio').textContent === 'WLAN EIN' }));
$('#wifi').addEventListener('click', e => { if (e.target.id === 'wifi') closeWifi(); });

/* ───── Boot ───── */
const bootLog = $('#boot-log');
const bootLines = {};
function hideBoot() { const b = $('#boot'); if (!b) return; b.classList.add('gone'); setTimeout(() => b.remove(), 1400); }
function boot(step, text) {
  if (!$('#boot')) return;
  const base = step.replace(/_ok$/, '');
  if (step.endsWith('_ok') && bootLines[base]) { bootLines[base].textContent = text; bootLines[base].classList.add('ok'); return; }
  const d = el('div', null, text); bootLog.appendChild(d); bootLines[base] = d;
  if (step === 'done') { d.classList.add('ok'); setTimeout(hideBoot, 900); }
}
['Kernsysteme', 'Telemetrie', 'Benutzeroberfläche'].forEach((t, i) =>
  setTimeout(() => { if ($('#boot')) bootLog.prepend(el('div', 'ok', t + ' initialisiert')); }, 150 + i * 220));
setTimeout(hideBoot, 30000);   // Sicherheitsnetz

/* ───── Garmin-Uhr (jarvis-watch) ───── */
const hrHist = [];
let lastHrTs = 0;
function watch(w) {
  const on = !!w.connected, box = $('#watch'), chip = $('#c-watch');
  box.classList.toggle('off', !on); chip.classList.toggle('off', !on);
  chip.hidden = !w.ts;                                   // nie verbunden gewesen -> Chip ausblenden
  setTxt($('#wt-state'), on ? 'live' : w.ts ? 'getrennt' : 'nicht verbunden');
  const hr = on ? w.hr : null;
  setTxt($('#wt-bpm'), hr ?? '--');
  setTxt(chip.querySelector('span'), hr ? `${hr}` : 'UHR');
  if (hr) document.documentElement.style.setProperty('--beat', (60 / hr).toFixed(2) + 's');
  if (hr && w.hr_ts !== lastHrTs) { lastHrTs = w.hr_ts; hrHist.push(hr); if (hrHist.length > 120) hrHist.shift(); drawHr(); }
  const n = v => v == null ? '–' : Number(v).toLocaleString('de-DE');
  setTxt($('#wt-rhr'), n(w.rhr));
  setTxt($('#wt-hrv'), n(w.hrv_rmssd));
  setTxt($('#wt-stress'), n(w.stress));
  const st = $('#wt-stress-t');
  st.classList.toggle('hi', w.stress > 50 && w.stress <= 75); st.classList.toggle('crit', w.stress > 75);
  const pct = (a, b) => b ? Math.min(100, Math.round(100 * a / b)) + '%' : '0%';
  setTxt($('#wt-steps'), w.steps != null ? `${n(w.steps)} / ${n(w.steps_goal)}` : '—');
  $('#wt-steps-p').style.width = pct(w.steps, w.steps_goal);
  setTxt($('#wt-int'), w.intensity_week != null ? `${w.intensity_week} / ${w.intensity_goal} min` : '—');
  $('#wt-int-p').style.width = pct(w.intensity_week, w.intensity_goal);
  setTxt($('#wt-kcal'), w.kcal != null ? `${n(w.kcal)} · aktiv ${n(w.kcal_active)}` : '—');
  setTxt($('#wt-floors'), w.floors_up != null ? `↑${w.floors_up} ↓${w.floors_down} / ${w.floors_goal}` : '—');
  const b = $('#wt-bat');
  setTxt(b, w.battery != null ? `${w.battery} %` : '—');
  b.classList.toggle('crit', w.battery != null && w.battery <= 15);
}
function drawHr() {
  const c = $('#wt-spark'), g = c.getContext('2d'), W = c.width, Hh = c.height;
  g.clearRect(0, 0, W, Hh);
  if (hrHist.length < 2) return;
  const lo = Math.min(...hrHist) - 5, hi = Math.max(...hrHist) + 5;
  const x = i => i * W / (hrHist.length - 1), y = v => Hh - 3 - (v - lo) / (hi - lo) * (Hh - 6);
  g.beginPath(); hrHist.forEach((v, i) => i ? g.lineTo(x(i), y(v)) : g.moveTo(x(i), y(v)));
  g.strokeStyle = '#ff4d6d'; g.lineWidth = 2; g.lineJoin = 'round'; g.stroke();
  g.lineTo(W, Hh); g.lineTo(0, Hh); g.closePath();
  const gr = g.createLinearGradient(0, 0, 0, Hh); gr.addColorStop(0, 'rgba(255,77,109,.28)'); gr.addColorStop(1, 'rgba(255,77,109,0)');
  g.fillStyle = gr; g.fill();
}

/* ───── Nachrichten von Python ───── */
const H = {
  stats, weather, watch,
  state: m => setState(m.s),
  level: m => pushLevel(m.v),
  mic: m => { if (state === 'listening') pushLevel(m.v * .9); },
  partial: m => { $('#partial').textContent = m.text; },
  activity: m => activity(m.kind, m.text, m.detail),
  user: m => { live = null; addMsg('user', m.src === 'voice' ? 'Harry · Sprache' : m.src === 'socket' ? 'System' : 'Harry', m.text); scrollDown(true); },
  reply_start: () => { live = null; },
  delta: m => { const t = ensureLive().querySelector('.txt'); const s = nearBottom(); t.textContent += m.text; scrollDown(s); },
  tool: addTool,
  tool_result: toolResult,
  reply_end: () => {
    if (live) { live.classList.remove('live'); if (!live.querySelector('.txt').textContent.trim() && !live.querySelector('.tool')) live.remove(); }
    live = null;
  },
  error: m => { addMsg('err', 'Fehler', m.text); document.body.classList.add('error'); setTimeout(() => document.body.classList.remove('error'), 2500); },
  note: m => addMsg('note', 'Jarvis', m.text),
  log_clear: () => { log.textContent = ''; live = null; for (const k in tools) delete tools[k]; },
  boot: m => boot(m.step, m.text),
  micstate: m => { micOn = m.on; const c = $('#c-mic'); c.classList.toggle('on', micOn); c.classList.toggle('off', !micOn);
    c.querySelector('span').textContent = micOn ? 'MIKRO' : 'MIKRO AUS'; document.body.classList.toggle('micoff', !micOn); setState(state);
    if ($('#activity').className === 'idle') activity('idle'); },
  toast,
  pause: m => setFrozen('screen', !!m.on),
  focus: m => { document.body.classList.toggle('dim', !m.on); setFrozen('focus', !m.on); },
  card: m => window.CARDS && CARDS.card(m),
  cards_clear: () => window.CARDS && CARDS.clear(),
  cards_tab: m => window.CARDS && CARDS.tab(m.tab),
  cards_unmax: () => window.CARDS && CARDS.unmax(),
  wifi_open: m => openWifi(m.auto),
  wifi_list: m => { if (wifiBusy == null) wmsg('', ''); wifiList(m.nets || [], m.status || {}); },
  wifi_busy: m => { wifiBusy = m.ssid || '*'; wmsg({ connect: `Verbinde mit ${m.ssid} …`, disconnect: 'Trenne …', forget: 'Entferne …', radio: 'Schalte WLAN um …' }[m.op] || '…', 'busy'); },
  wifi_result: m => { wifiBusy = null; wmsg(m.msg, m.ok ? 'ok' : 'err'); if (m.ok && m.op === 'connect') { wifiSel = null; if (wifiAuto) setTimeout(closeWifi, 1800); } },
  wifi_connected: () => { if (wifiOpen && wifiAuto) setTimeout(closeWifi, 1800); },
  insets: m => { const r = document.documentElement.style;
    r.setProperty('--top', m.top + 'px'); r.setProperty('--left', m.left + 'px'); r.setProperty('--right', m.right + 'px'); r.setProperty('--bottom', m.bottom + 'px'); },
};
window.J = {
  recv(m) {
    try { const f = H[m.type]; if (f) f(m); }
    catch (e) { post({ cmd: 'jserr', msg: `${m && m.type}: ${e.message}` }); }
  }
};

/* ───── Bedienelemente ───── */
document.querySelectorAll('[data-app]').forEach(b => b.addEventListener('click', () => post({ cmd: 'launch', app: b.dataset.app })));
$('#b-brief').addEventListener('click', () => post({ cmd: 'briefing' }));
$('#b-rec').addEventListener('click', () => post({ cmd: 'rec_toggle' }));
$('#c-rec').addEventListener('click', () => post({ cmd: 'rec_stop' }));
$('#b-wifi').addEventListener('click', () => openWifi(false));
$('#c-wifi').addEventListener('click', () => openWifi(false));
$('#c-mic').addEventListener('click', () => post({ cmd: 'mic', on: !micOn }));
$('#c-vol').addEventListener('click', () => post({ cmd: 'vol_mute' }));
$('#c-brain').addEventListener('click', () => post({ cmd: 'ask', text: 'Wie ist dein Systemstatus? Kurz.' }));
$('#c-bat').addEventListener('click', () => toast({ level: 'info', icon: 'battery',
  text: `Akku ${lastStats.bat ?? '?'} %${lastStats.charging ? ' · lädt' : ''} · CPU ${lastStats.temp ?? '?'} °C` }));
$('#b-kbd').addEventListener('click', () => { $('#q').focus(); post({ cmd: 'keyboard' }); });
$('#q').addEventListener('focus', () => post({ cmd: 'kbd_show' }));
$('#newchat').addEventListener('click', () => post({ cmd: 'newchat' }));
{ // Protokoll leeren: erster Tipp scharf schalten, zweiter Tipp (innerhalb 3 s) löscht
  const b = $('#logclear'); let armT = null;
  b.addEventListener('click', () => {
    if (!armT) { b.classList.add('arm'); b.textContent = 'SICHER?'; armT = setTimeout(reset, 3000); return; }
    reset(); H.log_clear(); post({ cmd: 'log_clear' });
  });
  function reset() { clearTimeout(armT); armT = null; b.classList.remove('arm'); b.textContent = 'LEEREN'; }
}
$('#ask').addEventListener('submit', e => {
  e.preventDefault();
  const q = $('#q').value.trim();
  if (q) { post({ cmd: 'ask', text: q }); $('#q').value = ''; post({ cmd: 'kbd_hide' }); }
});

setState('boot');
activity('idle');
post({ cmd: 'ready' });
