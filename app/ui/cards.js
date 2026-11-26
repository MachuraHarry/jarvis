'use strict';
/* J.A.R.V.I.S. Holo-Karten – visuelle Ergebnisse im rechten Panel.
   Sicherheit: Karteninhalte stammen oft aus Mails/Nachrichten -> ausschließlich textContent, kein innerHTML,
   Bilder nur als data:image/…-URI (jarvis-show bettet sie ein). */
(function () {
  const g = id => document.getElementById(id);
  const mk = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null && text !== '') e.textContent = String(text); return e; };
  const S = (tag, attrs) => { const e = document.createElementNS('http://www.w3.org/2000/svg', tag); for (const k in attrs || {}) e.setAttribute(k, attrs[k]); return e; };
  const send = m => { try { window.webkit.messageHandlers.jarvis.postMessage(JSON.stringify(m)); } catch (e) { } };
  const str = v => (v == null ? '' : String(v));
  const arr = v => (Array.isArray(v) ? v : []);
  const MAX = 10;
  /* Bilder über Blob-URLs anzeigen und alte sofort freigeben – data:-URIs bleiben sonst dekodiert im
     WebKit-Cache (GPU-Speicher, ca. 40 MB pro Bild) und lassen das HUD irgendwann abstürzen. */
  function b64ToBlob(uri) {
    const i = uri.indexOf(','), mime = uri.slice(5, uri.indexOf(';')), bin = atob(uri.slice(i + 1));
    const u8 = new Uint8Array(bin.length); for (let k = 0; k < bin.length; k++) u8[k] = bin.charCodeAt(k);
    return new Blob([u8], { type: mime });
  }
  function setImg(im, uri) {
    const old = im.dataset.blob;
    const u = URL.createObjectURL(b64ToBlob(uri));
    im.dataset.blob = u; im.src = u;
    if (old) im.addEventListener('load', () => URL.revokeObjectURL(old), { once: true });
  }
  function freeImgs(root) {
    root.querySelectorAll('img[data-blob]').forEach(i => { URL.revokeObjectURL(i.dataset.blob); i.removeAttribute('src'); delete i.dataset.blob; });
  }
  let gcTimer = null;
  const gcSoon = () => { clearTimeout(gcTimer); gcTimer = setTimeout(() => send({ cmd: 'gc' }), 1500); };
  const ACC = ['cyan', 'amber', 'red', 'green'];
  const COLORS = ['#38e8ff', '#ffb547', '#5dffb0', '#ff4d5e', '#b48cff', '#8ff4ff'];

  let cards = [], idx = -1, tab = 'log';
  const panel = g('logpanel'), box = g('cards'), view = g('c-view'), logEl = g('log');

  /* ── Reiter ── */
  function setTab(t) {
    tab = t;
    g('t-cards').classList.toggle('on', t === 'cards'); g('t-log').classList.toggle('on', t === 'log');
    box.hidden = t !== 'cards'; logEl.hidden = t !== 'log';
    if (t === 'cards') g('t-badge').hidden = true;
    if (t !== 'cards') panel.classList.remove('max');
  }
  g('t-cards').addEventListener('click', () => setTab('cards'));
  g('t-log').addEventListener('click', () => setTab('log'));

  /* ── Navigation ── */
  function nav() {
    const d = g('c-dots'); d.textContent = '';
    cards.forEach((_, i) => { const dot = mk('i', i === idx ? 'on' : ''); d.appendChild(dot); });
    g('c-prev').disabled = idx <= 0; g('c-next').disabled = idx >= cards.length - 1;
    g('c-close').disabled = g('c-max').disabled = idx < 0;
  }
  function show(i, still) {
    idx = Math.max(-1, Math.min(i, cards.length - 1));
    const keep = still ? view.scrollTop : 0;
    freeImgs(view); view.textContent = ''; view.scrollTop = 0;
    if (idx < 0) {
      const e = mk('div', 'c-empty', 'Keine Anzeige'); e.appendChild(mk('small', null, 'Frag Jarvis nach Mails, Terminen, Wetter …'));
      view.appendChild(e); panel.classList.remove('max');
    } else {
      try { view.appendChild(render(cards[idx].card, false, still)); if (still) view.scrollTop = keep; }
      catch (e) { view.appendChild(mk('div', 'c-empty', 'Karte fehlerhaft')); send({ cmd: 'jserr', msg: 'card: ' + e.message }); }
    }
    nav();
  }
  g('c-prev').addEventListener('click', () => show(idx - 1));
  g('c-next').addEventListener('click', () => show(idx + 1));
  g('c-max').addEventListener('click', () => panel.classList.toggle('max'));
  g('c-close').addEventListener('click', () => {
    if (idx < 0) return;
    const [gone] = cards.splice(idx, 1);
    send({ cmd: 'card_closed', id: gone.id }); gcSoon();
    show(Math.min(idx, cards.length - 1));
  });
  // Wischen
  let tx = null, ty = 0;
  view.addEventListener('touchstart', e => { tx = e.touches[0].clientX; ty = e.touches[0].clientY; }, { passive: true });
  view.addEventListener('touchend', e => {
    if (tx == null) return;
    const dx = e.changedTouches[0].clientX - tx, dy = e.changedTouches[0].clientY - ty; tx = null;
    if (Math.abs(dx) > 70 && Math.abs(dx) > Math.abs(dy) * 1.5) show(idx + (dx < 0 ? 1 : -1));
  }, { passive: true });

  /* ── Bausteine ── */
  function act(node, ask) {
    if (!ask) return node;
    node.classList.add('tappable');
    node.addEventListener('click', ev => { ev.stopPropagation(); send({ cmd: 'ask', text: str(ask).slice(0, 500), src: 'card' }); });
    return node;
  }
  function stag(node, i) { node.classList.add('stag'); node.style.setProperty('--i', Math.min(i, 14)); return node; }
  function head(c, small) {
    const h = mk('div', 'c-head');
    if (c.icon) h.appendChild(mk('div', 'c-ico', c.icon));
    const t = mk('div', 'c-tt');
    t.appendChild(mk('div', 'c-title', c.title || ''));
    if (c.subtitle) t.appendChild(mk('div', 'c-sub', c.subtitle));
    h.appendChild(t);
    if (small && c.badge) h.appendChild(mk('span', 'badge n', c.badge));
    return h;
  }
  const initials = s => { const w = str(s).replace(/[^\p{L}\p{N} ]/gu, ' ').trim().split(/\s+/); return ((w[0] || '?')[0] + (w[1] ? w[1][0] : '')).toUpperCase(); };

  /* ── Renderer pro Typ ── */
  const R = {
    list(c) {
      const l = mk('div', 'c-list');
      arr(c.items).forEach((it, i) => {
        const r = mk('div', 'li' + (it.unread ? ' unread' : ''));
        if (it.avatar !== false) {
          const emo = it.icon;
          r.appendChild(mk('div', 'av' + (emo ? ' e' : ''), emo || it.avatar || initials(it.title)));
        }
        const b = mk('div', 'lb'); b.appendChild(mk('div', 'lt', it.title)); if (it.sub) b.appendChild(mk('div', 'ls', it.sub)); r.appendChild(b);
        if (it.meta || it.badge || it.count) {
          const m = mk('div', 'lm');
          if (it.meta) m.appendChild(mk('span', 'meta', it.meta));
          if (it.count) m.appendChild(mk('span', 'badge n', it.count));
          if (it.badge) m.appendChild(mk('span', 'badge', it.badge));
          r.appendChild(m);
        }
        l.appendChild(stag(act(r, it.ask), i));
      });
      if (!l.children.length) l.appendChild(mk('div', 'c-empty', c.empty || 'Nichts vorhanden'));
      return l;
    },
    agenda(c) {
      const a = mk('div', 'c-agenda'); let lastDay = null, i = 0;
      arr(c.events).forEach(ev => {
        if (ev.day && ev.day !== lastDay) { a.appendChild(stag(mk('div', 'ag-day', ev.day), i++)); lastDay = ev.day; }
        const r = mk('div', 'ev' + (ev.now ? ' now' : '') + (ev.past ? ' past' : ''));
        const t = mk('div', 'et', ev.allday ? 'ganzt.' : ev.start || ''); if (!ev.allday && ev.end) t.appendChild(mk('small', null, ev.end));
        r.appendChild(t); r.appendChild(mk('div', 'rail'));
        const b = mk('div', 'eb'); b.appendChild(mk('div', 'en', ev.title));
        const p = [ev.place, ev.calendar].filter(Boolean).join(' · '); if (p) b.appendChild(mk('div', 'ep', p));
        r.appendChild(b);
        a.appendChild(stag(act(r, ev.ask), i++));
      });
      if (!a.children.length) a.appendChild(mk('div', 'c-empty', c.empty || 'Keine Termine'));
      return a;
    },
    chat(c) {
      const w = mk('div', 'c-chat'); let lastDay = null;
      arr(c.messages).forEach((m, i) => {
        if (m.day && m.day !== lastDay) { w.appendChild(mk('div', 'sep', m.day)); lastDay = m.day; }
        const b = mk('div', 'bub' + (m.me ? ' me' : ''));
        if (!m.me && m.from && c.group !== false) b.appendChild(mk('div', 'bf', m.from));
        b.appendChild(mk('div', 'bt', m.text || ''));
        if (m.time) b.appendChild(mk('div', 'bm', m.time));
        w.appendChild(stag(b, i));
      });
      setTimeout(() => { if (view.contains(w)) view.scrollTop = view.scrollHeight; }, 60);
      return w;
    },
    read(c) {
      const w = mk('div', 'c-read');
      const dl = mk('dl', 'rd-meta');
      [['Von', c.from], ['An', c.to], ['Datum', c.date]].forEach(([k, v]) => { if (v) { dl.appendChild(mk('dt', null, k)); dl.appendChild(mk('dd', null, v)); } });
      w.appendChild(dl);
      if (c.subject) w.appendChild(mk('div', 'rd-subj', c.subject));
      const body = mk('div', 'rd-body');
      str(c.body).split(/\n{2,}/).slice(0, 80).forEach(p => { if (p.trim()) body.appendChild(mk('p', null, p.trim())); });
      w.appendChild(body);
      return w;
    },
    stats(c) {
      const w = mk('div', 'c-stats');
      arr(c.tiles).forEach((t, i) => {
        const d = mk('div', 'tile' + (['warn', 'crit', 'ok'].includes(t.level) ? ' ' + t.level : ''));
        d.appendChild(mk('div', 'tl', t.label));
        const v = mk('div', 'tv', t.value); if (t.unit) v.appendChild(mk('small', null, t.unit)); d.appendChild(v);
        if (t.note || t.trend) {
          const n = mk('div', 'tn');
          if (t.trend) n.appendChild(mk('span', 'tr ' + (t.trend > 0 ? 'up' : 'down'), (t.trend > 0 ? '▲ ' : '▼ ') + Math.abs(t.trend) + ' '));
          if (t.note) n.appendChild(document.createTextNode(str(t.note)));
          d.appendChild(n);
        }
        if (typeof t.gauge === 'number') { const gb = mk('div', 'tg'); gb.style.width = '0'; d.appendChild(gb); setTimeout(() => { gb.style.width = Math.max(0, Math.min(100, t.gauge)) + '%'; }, 80); }
        w.appendChild(stag(d, i));
      });
      return w;
    },
    chart(c) {
      const w = mk('div', 'c-chart');
      const labels = arr(c.labels).map(str), series = arr(c.series).filter(s => Array.isArray(s.values));
      if (!labels.length || !series.length) return w;
      const W = 600, Hh = c.height || 240, L = 40, B = 28, T = 18, Rr = 8, n = labels.length;
      const all = series.flatMap(s => s.values.filter(v => typeof v === 'number'));
      let lo = Math.min(0, ...all), hi = Math.max(...all); if (hi === lo) hi = lo + 1;
      const raw = (hi - lo) / 4, mag = Math.pow(10, Math.floor(Math.log10(raw))), stepN = [1, 2, 2.5, 5, 10].find(f => f * mag >= raw) * mag;
      lo = Math.floor(lo / stepN) * stepN; hi = Math.ceil(hi / stepN) * stepN; if (hi - lo < stepN * 4) hi = lo + stepN * 4;
      const y = v => T + (Hh - T - B) * (1 - (v - lo) / (hi - lo));
      const xs = i => L + (W - L - Rr) * (n === 1 ? .5 : (c.kind === 'bar' ? (i + .5) / n : i / (n - 1)));
      const svg = S('svg', { viewBox: `0 0 ${W} ${Hh}`, preserveAspectRatio: 'xMidYMid meet' });
      for (let v = lo; v <= hi + stepN / 2; v += stepN) {
        const yy = y(v);
        svg.appendChild(S('line', { x1: L, x2: W - Rr, y1: yy, y2: yy, class: 'gl' }));
        const t = S('text', { x: L - 6, y: yy + 4, 'text-anchor': 'end' }); t.textContent = Math.round(v * 100) / 100; svg.appendChild(t);
      }
      svg.appendChild(S('line', { x1: L, x2: W - Rr, y1: y(Math.max(lo, 0)), y2: y(Math.max(lo, 0)), class: 'ax' }));
      const every = Math.ceil(n / 12);
      labels.forEach((lb, i) => { if (i % every) return; const t = S('text', { x: xs(i), y: Hh - 8, 'text-anchor': 'middle' }); t.textContent = lb; svg.appendChild(t); });
      if (c.kind === 'bar') {
        const bw = (W - L - Rr) / n * .7 / series.length;
        series.forEach((s, si) => s.values.forEach((v, i) => {
          if (typeof v !== 'number') return;
          const x = xs(i) - bw * series.length / 2 + si * bw, y0 = y(Math.max(lo, 0)), y1 = y(v);
          const r = S('rect', { x, y: Math.min(y0, y1), width: bw - 2, height: Math.max(1, Math.abs(y1 - y0)), fill: s.color || COLORS[si % 6], class: 'bar' });
          r.style.animationDelay = (i * 40) + 'ms'; svg.appendChild(r);
          if (c.values !== false && series.length === 1 && n <= 14) { const t = S('text', { x: x + bw / 2 - 1, y: Math.min(y0, y1) - 5, 'text-anchor': 'middle', class: 'v' }); t.textContent = v; svg.appendChild(t); }
        }));
      } else {
        series.forEach((s, si) => {
          const col = s.color || COLORS[si % 6];
          const pts = s.values.map((v, i) => typeof v === 'number' ? [xs(i), y(v)] : null).filter(Boolean);
          if (!pts.length) return;
          const d = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
          if (series.length === 1) svg.appendChild(S('path', { d: d + ` L${pts[pts.length - 1][0]} ${y(Math.max(lo, 0))} L${pts[0][0]} ${y(Math.max(lo, 0))} Z`, fill: col, class: 'ar' }));
          svg.appendChild(S('path', { d, stroke: col, class: 'ln' }));
        });
      }
      w.appendChild(svg);
      if (series.length > 1 || series[0].name) {
        const lg = mk('div', 'c-legend');
        series.forEach((s, si) => { const sp = mk('span'); const i = mk('i'); i.style.background = s.color || COLORS[si % 6]; sp.appendChild(i); sp.appendChild(document.createTextNode(str(s.name))); lg.appendChild(sp); });
        w.appendChild(lg);
      }
      return w;
    },
    table(c) {
      const w = mk('div', 'c-table'), t = mk('table'), cols = arr(c.columns);
      if (cols.length) { const tr = mk('tr'); cols.forEach(h => tr.appendChild(mk('th', null, h))); const th = mk('thead'); th.appendChild(tr); t.appendChild(th); }
      const tb = mk('tbody');
      arr(c.rows).forEach((row, i) => {
        const tr = mk('tr'); arr(row).forEach(v => tr.appendChild(mk('td', typeof v === 'number' ? 'num' : '', v)));
        tb.appendChild(stag(tr, i));
      });
      t.appendChild(tb); w.appendChild(t); return w;
    },
    text(c) {
      const w = mk('div', 'c-text'); let i = 0;
      if (c.headline) w.appendChild(stag(mk('div', 'hl', c.headline), i++));
      if (c.text) str(c.text).split(/\n{2,}/).forEach(p => w.appendChild(stag(mk('p', null, p), i++)));
      arr(c.sections).forEach(s => {
        if (s.heading) w.appendChild(stag(mk('h3', null, s.heading), i++));
        arr(s.paragraphs).forEach(p => w.appendChild(stag(mk('p', null, p), i++)));
        if (arr(s.bullets).length) { const ul = mk('ul'); s.bullets.forEach(b => ul.appendChild(mk('li', null, b))); w.appendChild(stag(ul, i++)); }
      });
      return w;
    },
    image(c) {
      const f = mk('figure', 'c-img'); f.style.margin = '0';
      if (/^data:image\/(png|jpe?g|gif|webp);base64,/.test(str(c.src))) { const im = new Image(); setImg(im, c.src); im.alt = str(c.caption); f.appendChild(im); }
      else f.appendChild(mk('div', 'c-empty', 'Bild nicht verfügbar'));
      if (c.caption) f.appendChild(mk('figcaption', null, c.caption));
      return f;
    },
    steps(c) {
      const w = mk('div', 'c-steps');
      arr(c.items).forEach((s, i) => { const d = mk('div', 'stp' + (s.done ? ' done' : '')); d.appendChild(mk('div', 'sx', typeof s === 'string' ? s : s.text)); w.appendChild(stag(act(d, s.ask), i)); });
      return w;
    },
    dashboard(c) {
      const w = mk('div', 'c-dash');
      arr(c.cells).forEach((cell, i) => { if (cell && cell.type !== 'dashboard') { const d = render(cell, true); d.classList.add('cell'); if (cell.wide) d.classList.add('wide'); w.appendChild(stag(d, i)); } });
      return w;
    },

    /* Live-Fortschritt einer Recherche */
    research(c, ctx) {
      const key = 'r' + c.started, prev = seen[key] || { q: 0, s: 0, f: 0 };
      const fresh = (node, i, n) => { if (!ctx.still || i >= n) { node.classList.add('stag'); node.style.setProperty('--i', ctx.still ? 0 : Math.min(i, 10)); } return node; };
      const w = mk('div', 'c-research');
      w.appendChild(mk('div', 'rs-scan'));
      const ph = mk('div', 'rs-phase' + (c.phase === 'Fertig' ? ' done' : c.phase === 'Fehlgeschlagen' ? ' fail' : ''));
      ph.appendChild(mk('span', 'rs-spin')); ph.appendChild(mk('span', 'rs-ptxt', c.phase || '…'));
      const tm = mk('span', 'rs-time'); ph.appendChild(tm);
      let armed = false; const tick = () => { if (armed && !tm.isConnected) return clearInterval(iv); armed = true; const s = Math.max(0, Math.round(Date.now() / 1000 - c.started)); tm.textContent = Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };
      const iv = setInterval(tick, 1000); tick();
      w.appendChild(ph);
      if (arr(c.plan).length) {
        const pl = mk('div', 'rs-plan'); const done = arr(c.done); let active = false;
        c.plan.forEach((t, i) => {
          const isDone = done.includes(i + 1), isAct = !isDone && !active; if (isAct) active = true;
          const r = mk('div', 'rs-step' + (isDone ? ' ok' : isAct ? ' act' : ''));
          r.appendChild(mk('i', null, isDone ? '✓' : String(i + 1))); r.appendChild(mk('span', null, t));
          pl.appendChild(ctx.still ? r : stag(r, i));
        });
        w.appendChild(pl);
      }
      if (arr(c.queries).length) {
        w.appendChild(mk('div', 'rs-h', 'Suchanfragen'));
        const ql = mk('div', 'rs-q'); c.queries.forEach((q, i) => ql.appendChild(fresh(mk('div', null, '⌕ ' + q), i, prev.q))); w.appendChild(ql);
      }
      if (arr(c.sources).length) {
        w.appendChild(mk('div', 'rs-h', 'Quellen'));
        const sl = mk('div', 'rs-src'); c.sources.forEach((s, i) => sl.appendChild(fresh(mk('span', s.ok ? 'ok' : '', s.d), i, prev.s))); w.appendChild(sl);
      }
      if (arr(c.findings).length) {
        w.appendChild(mk('div', 'rs-h', 'Erkenntnisse'));
        const fl = mk('ul', 'rs-find'); c.findings.forEach((f, i) => fl.appendChild(fresh(mk('li', null, f), i, prev.f))); w.appendChild(fl);
      }
      seen[key] = { q: arr(c.queries).length, s: arr(c.sources).length, f: arr(c.findings).length };
      return w;
    },

    /* Aufbereitetes Recherche-Ergebnis */
    dossier(c) {
      const w = mk('div', 'c-dossier'); let i = 0;
      if (c.image && /^data:image\/(png|jpe?g|webp);base64,/.test(str(c.image.src))) {
        const f = mk('figure', 'ds-hero'); const im = new Image(); setImg(im, c.image.src); f.appendChild(im);
        if (c.image.credit) f.appendChild(mk('figcaption', null, c.image.credit));
        w.appendChild(f);
      }
      if (c.answer) w.appendChild(stag(mk('div', 'ds-answer', c.answer), i++));
      if (c.confidence) {
        const lv = /hoch/i.test(c.confidence) ? 'hi' : /niedrig/i.test(c.confidence) ? 'lo' : 'mid';
        const cf = mk('div', 'ds-conf ' + lv); cf.appendChild(mk('b', null, 'Verlässlichkeit: ' + c.confidence));
        if (c.confidence_note) cf.appendChild(mk('span', null, c.confidence_note));
        w.appendChild(stag(cf, i++));
      }
      if (arr(c.facts).length) w.appendChild(stag(R.stats({ tiles: c.facts }), i++));
      arr(c.sections).forEach(s => {
        const sec = mk('section', 'ds-sec');
        if (s.heading) sec.appendChild(mk('h3', null, s.heading));
        if (s.kind === 'table') sec.appendChild(R.table(s));
        else if (s.kind === 'chart' && s.chart) sec.appendChild(R.chart(s.chart));
        else if (s.kind === 'proscons') {
          const pc = mk('div', 'ds-pc');
          [['pro', 'Pro', s.pros], ['con', 'Contra', s.cons]].forEach(([k, lbl, list]) => {
            const col = mk('div', k); col.appendChild(mk('div', 'pch', lbl));
            arr(list).forEach(x => col.appendChild(mk('div', 'pci', x))); pc.appendChild(col);
          });
          sec.appendChild(pc);
        } else if (s.kind === 'timeline') {
          const tl = mk('div', 'ds-tl');
          arr(s.events).forEach(e => { const r = mk('div', 'tle'); r.appendChild(mk('div', 'tld', e.date)); r.appendChild(mk('div', 'tlt', e.text)); tl.appendChild(r); });
          sec.appendChild(tl);
        } else {
          const t = mk('div', 'c-text');
          arr(s.paragraphs).forEach(p => t.appendChild(mk('p', null, p)));
          if (arr(s.bullets).length) { const ul = mk('ul'); s.bullets.forEach(b => ul.appendChild(mk('li', null, b))); t.appendChild(ul); }
          sec.appendChild(t);
        }
        w.appendChild(stag(sec, i++));
      });
      if (arr(c.sources).length) {
        const so = mk('section', 'ds-sec ds-srcs'); so.appendChild(mk('h3', null, 'Quellen'));
        c.sources.forEach((x, k) => { const r = mk('div', 'dsrc'); r.appendChild(mk('i', null, String(k + 1))); const b = mk('div');
          b.appendChild(mk('div', 'dst', x.title)); b.appendChild(mk('div', 'dsd', [x.domain, x.date].filter(Boolean).join(' · '))); r.appendChild(b); so.appendChild(r); });
        w.appendChild(stag(so, i++));
      }
      return w;
    },
  };
  const seen = {};

  function render(c, small, still) {
    const card = mk('div', 'card ' + (ACC.includes(c.accent) ? c.accent : 'cyan') + (still ? ' still' : ''));
    if (c.title || c.icon) card.appendChild(head(c, small));
    const f = R[c.type] || R.text;
    card.appendChild(f(c, { still }));
    if (!small && c.footer) card.appendChild(mk('div', 'c-foot', c.footer));
    if (!small && arr(c.actions).length) {
      const a = mk('div', 'c-acts');
      c.actions.slice(0, 6).forEach(x => { if (x && x.label && x.ask) a.appendChild(act(mk('button', null, x.label), x.ask)); });
      card.appendChild(a);
    }
    return card;
  }

  window.CARDS = {
    card(m) {
      const c = m.card; if (!c || typeof c !== 'object') return;
      const id = m.id || String(Date.now());
      const old = cards.findIndex(x => x.id === id);
      if (m.update && old >= 0) {               // Live-Aktualisierung: an Ort und Stelle, ohne Neu-Animation
        const prev = cards[old].card;
        cards[old].card = c;
        if (old === idx && c.type === 'image' && prev.type === 'image' && view.querySelector('.c-img img')) {
          setImg(view.querySelector('.c-img img'), c.src);              // nur das Bild austauschen
          const cap = view.querySelector('.c-img figcaption'); if (cap) cap.textContent = str(c.caption);
          const tt = view.querySelector('.c-title'); if (tt && tt.textContent !== str(c.title)) tt.textContent = str(c.title);
          const card = view.querySelector('.card'); if (card) card.className = 'card still ' + (ACC.includes(c.accent) ? c.accent : 'cyan');
          return;
        }
        if (old === idx) show(idx, true);
        else if (tab !== 'cards') g('t-badge').hidden = false;
        return;
      }
      if (old >= 0) cards.splice(old, 1);
      cards.push({ id, card: c });
      while (cards.length > MAX) cards.shift();
      gcSoon();
      if (m.restore) { show(cards.length - 1); return; }
      show(cards.length - 1);
      if (tab !== 'cards') { if (m.focus === false) g('t-badge').hidden = false; else setTab('cards'); }
      if (m.max && m.focus !== false) { panel.classList.remove('max'); void panel.offsetWidth; panel.classList.add('max'); }
    },
    unmax() { panel.classList.remove('max'); },
    clear() { cards = []; show(-1); gcSoon(); },
    tab: setTab,
  };
  nav();
})();
