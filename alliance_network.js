// Voting Alliance Network: a small force layout and its controls. No external libraries.
(function () {
  var source = document.getElementById('net-data');
  if (!source) return;
  var data = JSON.parse(source.textContent);
  var NS = 'http://www.w3.org/2000/svg';
  var $ = function (id) { return document.getElementById(id); };
  var svg = $('net-svg'), tip = $('net-tip');
  var narrow = svg.clientWidth < 560;
  var W = narrow ? 560 : 900, H = narrow ? 480 : 600;
  svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);

  function el(tag, attrs, parent) {
    var n = document.createElementNS(NS, tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }
  function html(tag, cls, text, parent) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    if (parent) parent.appendChild(n);
    return n;
  }
  var pct = function (v) { return Math.round(v) + '%'; };
  var COMMUNITY = function (c) { return 'Community ' + (c + 1); };
  var byId = {};
  var nodes = data.nodes.map(function (n) {
    var copy = Object.assign({ vx: 0, vy: 0, pinned: false }, n);
    byId[n.id] = copy;
    return copy;
  });
  var edges = data.edges.map(function (x, i) {
    return Object.assign({ i: i, A: byId[x.a], B: byId[x.b] }, x);
  });
  var low = Math.min.apply(null, edges.map(function (x) { return x.pct; }));
  var high = Math.max.apply(null, edges.map(function (x) { return x.pct; }));
  var span = Math.max(high - low, 1);
  function other(x, n) { return x.A === n ? x.B : x.A; }
  function edgesOf(n) { return edges.filter(function (x) { return x.A === n || x.B === n; }); }
  function ranked(n) { return edgesOf(n).sort(function (p, q) { return q.pct - p.pct || q.shared - p.shared; }); }

  // ------------------------------------------------------------ layout
  var COLLIDE = 92;
  edges.forEach(function (x) {
    x.target = 92 + 430 * (high - x.pct) / span;   // every known pair counts, whatever the slider shows
    x.pull = 0.012 + 0.03 * Math.pow((x.pct - low) / span, 2);
  });
  (function seed() {
    var scale = 620;  // the map's starting positions are fractions of a vote, so spread them out
    nodes.forEach(function (n) { n.x = n.x * scale; n.y = n.y * scale; });
  })();
  function tick(alpha) {
    edges.forEach(function (x) {
      var dx = x.B.x - x.A.x, dy = x.B.y - x.A.y, d = Math.hypot(dx, dy) || 0.01;
      var f = (d - x.target) / d * x.pull * alpha;
      x.A.vx += dx * f; x.A.vy += dy * f; x.B.vx -= dx * f; x.B.vy -= dy * f;
    });
    for (var i = 0; i < nodes.length; i++) for (var j = i + 1; j < nodes.length; j++) {
      var a = nodes[i], b = nodes[j], dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy);
      if (!d) { dx = 1; dy = (i - j) * 0.1; d = Math.hypot(dx, dy); }
      if (d < COLLIDE) {   // no two circles or their labels on top of each other
        var push = (COLLIDE - d) / d * 0.5;
        a.x -= dx * push; a.y -= dy * push; b.x += dx * push; b.y += dy * push;
      }
    }
    nodes.forEach(function (n) {
      n.vx -= n.x * 0.002 * alpha; n.vy -= n.y * 0.002 * alpha;   // keeps isolated people on the page
      if (n.pinned) { n.vx = n.vy = 0; return; }
      n.vx *= 0.82; n.vy *= 0.82;
      n.x += n.vx; n.y += n.vy;
    });
  }
  for (var k = 0; k < 900; k++) tick(1);
  nodes.forEach(function (n) { n.vx = n.vy = 0; n.homeX = n.x; n.homeY = n.y; });

  // ------------------------------------------------------------ drawing
  var view = el('g', {}, svg);
  var lineLayer = el('g', {}, view), hitLayer = el('g', {}, view), nodeLayer = el('g', {}, view);
  function weight(p) { return Math.pow((p - low) / span, 2); }
  edges.forEach(function (x) {
    x.line = el('line', { 'class': 'ne', 'stroke-width': (0.7 + 8 * weight(x.pct)).toFixed(2), opacity: (0.16 + 0.6 * weight(x.pct)).toFixed(2) }, lineLayer);
    x.hit = el('line', { 'class': 'nh', 'data-i': x.i }, hitLayer);
  });
  var BASE = 26;
  function placeFace(n, r) {
    n.disc.setAttribute('r', r.toFixed(1));
    if (n.face) {
      n.face.setAttribute('x', (-r).toFixed(1)); n.face.setAttribute('y', (-r).toFixed(1));
      n.face.setAttribute('width', (2 * r).toFixed(1)); n.face.setAttribute('height', (2 * r).toFixed(1));
    }
    if (n.ring) n.ring.setAttribute('r', (r + 6).toFixed(1));
    n.label.setAttribute('y', (r + (n.ring ? 21 : 17)).toFixed(1));
  }
  var defs = el('defs', {}, svg), clip = el('clipPath', { id: 'net-face', clipPathUnits: 'objectBoundingBox' }, defs);
  el('circle', { cx: 0.5, cy: 0.5, r: 0.5 }, clip);
  nodes.forEach(function (n) {
    n.g = el('g', { 'class': 'nn c' + n.community, tabindex: 0, role: 'button', 'data-id': n.id,
      'aria-label': n.name + (n.mayor ? ', the mayor' : '') + '. ' + COMMUNITY(n.community) + '. Average agreement ' + pct(n.average) + '.' }, nodeLayer);
    n.ring = n.mayor ? el('circle', { 'class': 'mayor' }, n.g) : null;
    n.label = el('text', { 'class': 'nm' });
    n.disc = el('circle', { 'class': 'disc', r: BASE }, n.g);
    if (n.photo) {
      n.g.classList.add('face');
      n.face = el('image', { href: n.photo, 'clip-path': 'url(#net-face)' }, n.g);
    } else {
      var ini = el('text', { 'class': 'ini' }, n.g); ini.textContent = n.initials;
    }
    placeFace(n, BASE);
    n.g.appendChild(n.label); n.label.textContent = n.surname + (n.mayor ? ' (Mayor)' : '');
  });
  function paint() {
    edges.forEach(function (x) {
      [x.line, x.hit].forEach(function (l) {
        l.setAttribute('x1', x.A.x); l.setAttribute('y1', x.A.y); l.setAttribute('x2', x.B.x); l.setAttribute('y2', x.B.y);
      });
    });
    nodes.forEach(function (n) { n.g.setAttribute('transform', 'translate(' + n.x.toFixed(1) + ' ' + n.y.toFixed(1) + ')'); });
  }

  // ------------------------------------------------------------ zoom and pan
  var zoom = { k: 1, x: 0, y: 0 };
  function applyZoom() { view.setAttribute('transform', 'translate(' + zoom.x + ' ' + zoom.y + ') scale(' + zoom.k + ')'); }
  function fit() {
    var xs = nodes.map(function (n) { return n.x; }), ys = nodes.map(function (n) { return n.y; });
    var x0 = Math.min.apply(null, xs) - 60, x1 = Math.max.apply(null, xs) + 60, y0 = Math.min.apply(null, ys) - 40, y1 = Math.max.apply(null, ys) + 60;
    zoom.k = Math.min(W / (x1 - x0), H / (y1 - y0), 1.5);
    zoom.x = (W - (x0 + x1) * zoom.k) / 2; zoom.y = (H - (y0 + y1) * zoom.k) / 2;
    applyZoom();
  }
  function zoomBy(f, cx, cy) {
    cx = cx == null ? W / 2 : cx; cy = cy == null ? H / 2 : cy;
    var k = Math.max(0.3, Math.min(5, zoom.k * f)), r = k / zoom.k;
    zoom.x = cx - (cx - zoom.x) * r; zoom.y = cy - (cy - zoom.y) * r; zoom.k = k;
    applyZoom();
  }
  function toView(ev) { var m = svg.getScreenCTM().inverse(); return { x: ev.clientX * m.a + m.e, y: ev.clientY * m.d + m.f }; }
  function toWorld(p) { return { x: (p.x - zoom.x) / zoom.k, y: (p.y - zoom.y) / zoom.k }; }

  // ------------------------------------------------------------ the running simulation
  var frozen = false, alpha = 0, running = false;
  var still = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  function heat(a) {
    if (frozen) return;
    alpha = Math.max(alpha, a);
    if (still) { for (var i = 0; i < 200; i++) tick(alpha); alpha = 0; paint(); return; }
    if (!running) { running = true; requestAnimationFrame(frame); }
  }
  function frame() {
    if (alpha < 0.02 || frozen) { running = false; return; }
    tick(alpha); alpha *= 0.985; paint();
    requestAnimationFrame(frame);
  }

  // ------------------------------------------------------------ filtering, sizing, selection
  var threshold = 75, selected = null;
  function sizes() {
    var mode = $('net-size').value;
    var values = nodes.map(function (n) {
      if (mode === 'average') return n.average;
      return edgesOf(n).reduce(function (s, x) { return s + (x.pct >= threshold ? x.pct / 100 : 0); }, 0);
    });
    var lo = Math.min.apply(null, values), hi = Math.max.apply(null, values);
    nodes.forEach(function (n, i) {
      placeFace(n, mode === 'uniform' || hi === lo ? BASE : 16 + 18 * (values[i] - lo) / (hi - lo));
    });
    legend();
  }
  function filter() {
    var shown = 0;
    edges.forEach(function (x) {
      var on = x.pct >= threshold;
      if (on) shown++;
      var hidden = !on && !(selected && x.line.classList.contains('top'));
      x.line.classList.toggle('off', hidden);
      x.hit.classList.toggle('off', hidden);
    });
    $('net-count').textContent = shown + ' of ' + edges.length + ' pairs shown';
    if ($('net-size').value === 'connectivity') sizes();
  }
  function select(n) {
    selected = n || null;
    svg.classList.toggle('sel', !!selected);
    var strongest = selected ? ranked(selected).slice(0, 5) : [];
    edges.forEach(function (x) {
      var on = !!selected && (x.A === selected || x.B === selected);
      x.line.classList.toggle('on', on); x.hit.classList.toggle('on', on);
      x.line.classList.toggle('top', strongest.indexOf(x) >= 0);
    });
    nodes.forEach(function (m) {
      m.g.classList.toggle('sel', m === selected);
      m.g.classList.toggle('near', !!selected && strongest.some(function (x) { return other(x, selected) === m; }));
      m.g.setAttribute('aria-pressed', m === selected ? 'true' : 'false');
    });
    $('net-select').value = selected ? selected.id : '';
    filter();
    side();
  }
  function showTip(title, sub) {
    tip.textContent = '';
    html('b', '', title, tip); html('span', '', sub, tip);
    tip.hidden = false;
  }
  function nodeTip(n) {
    showTip(n.name, [n.ward, COMMUNITY(n.community), 'average agreement ' + pct(n.average)].filter(Boolean).join(' · '));
  }
  function edgeTip(x) {
    showTip(x.A.name + ' & ' + x.B.name, pct(x.pct) + ' agreement: ' + x.agreed + ' of ' + x.shared + ' votes both attended');
  }

  // ------------------------------------------------------------ panels
  function row(label, x, parent) {
    var r = html('div', 'net-row', null, parent);
    html('span', '', label, r);
    html('span', 'num', pct(x.pct) + ' (' + x.agreed + ' of ' + x.shared + ')', r);
  }
  function fact(value, label, parent) {
    var f = html('div', '', null, parent);
    html('b', '', value, f); html('span', '', label, f);
  }
  function side() {
    var box = $('net-side');
    box.textContent = '';
    if (!selected) {
      html('h3', '', 'Strongest alliances', box);
      edges.slice().sort(function (p, q) { return q.pct - p.pct || q.shared - p.shared; }).slice(0, 5).forEach(function (x) {
        row(x.A.name + ' & ' + x.B.name, x, box);
      });
      var hint = html('p', '', 'Select a councillor in the graph or the menu above for their full record. Select empty space to clear it.', box);
      hint.style.cssText = 'color:var(--muted);font-size:14px;margin:12px 0 0';
      return;
    }
    var n = selected, who = html('div', 'who', null, box);
    if (n.photo) { var img = html('img', '', null, who); img.src = n.photo; img.alt = ''; }
    var text = html('div', '', null, who);
    html('h4', '', n.name, text);
    html('p', '', [n.ward, COMMUNITY(n.community), n.bridge ? 'bridging position' : ''].filter(Boolean).join(' · '), text);
    var facts = html('div', 'net-facts', null, box);
    fact(pct(n.average), 'average agreement with colleagues', facts);
    fact(String(n.comparisons), 'colleagues with shared votes', facts);
    if (n.within != null && n.across != null) fact(pct(n.within) + ' / ' + pct(n.across), 'within their community / with everyone else', facts);
    if (n.stays != null) fact(pct(100 * n.stays), 'stayed with this community when votes were resampled', facts);
    var all = ranked(n), cols = html('div', 'net-cols', null, box);
    var top = html('div', '', null, cols), bottom = html('div', '', null, cols);
    html('h3', '', 'Most aligned', top); html('h3', '', 'Least aligned', bottom);
    all.slice(0, 5).forEach(function (x) { row(other(x, n).name, x, top); });
    all.slice(-5).reverse().forEach(function (x) { row(other(x, n).name, x, bottom); });
    var more = html('details', '', null, box);
    html('summary', '', 'Everyone, highest to lowest', more);
    all.forEach(function (x) { row(other(x, n).name, x, more); });
    data.unknown.forEach(function (pair) {
      if (pair.indexOf(n.id) >= 0) {
        var r = html('div', 'net-row', null, more);
        html('span', '', byId[pair[0] === n.id ? pair[1] : pair[0]].name, r);
        html('span', 'num', 'unknown: never voted together', r);
      }
    });
  }
  function legend() {
    var box = $('net-legend'), mode = $('net-size').value;
    box.textContent = '';
    function item(cls, label) { var s = html('span', '', null, box); html('i', cls, null, s); s.appendChild(document.createTextNode(label)); return s; }
    if ($('net-colour').checked) {
      for (var c = 0; c < data.communities; c++) item('dot c' + c, COMMUNITY(c));
    }
    item('ring', 'Mayor');
    [[Math.ceil(low), low], [75, 75], [Math.floor(high), high]].forEach(function (pair) {
      var s = item('ln', pct(pair[1]));
      s.firstChild.style.height = (0.7 + 8 * weight(pair[1])).toFixed(1) + 'px';
    });
    var sized = { uniform: 'All circles the same size', average: 'Larger circle: higher average agreement', connectivity: 'Larger circle: more total agreement at or above the slider' };
    html('span', '', sized[mode], box);
  }
  function stats() {
    var box = $('net-stats');
    var sorted = edges.slice().sort(function (p, q) { return q.pct - p.pct || q.shared - p.shared; });
    var hi = sorted[0], lo = sorted[sorted.length - 1];
    function stat(value, label) { var d = html('div', 'net-stat', null, box); html('b', '', value, d); html('span', '', label, d); }
    stat(pct(data.average), 'average agreement across all pairs');
    stat(pct(hi.pct), 'strongest: ' + hi.A.name + ' & ' + hi.B.name);
    stat(pct(lo.pct), 'weakest: ' + lo.A.name + ' & ' + lo.B.name);
    stat(String(data.communities), 'communities detected');
    var bridges = nodes.filter(function (n) { return n.bridge; }).map(function (n) { return n.name; });
    stat(bridges.length ? String(bridges.length) : '0', bridges.length ? 'in bridging positions: ' + bridges.join(', ') : 'in bridging positions');
  }

  // ------------------------------------------------------------ pointer handling
  var drag = null;
  svg.addEventListener('pointerdown', function (ev) {
    if (ev.button) return;
    var g = ev.target.closest('.nn'), hit = ev.target.closest('.nh'), p = toView(ev);
    drag = { node: g ? byId[g.dataset.id] : null, hit: hit, start: p, last: p, moved: false, id: ev.pointerId };
    if (g && ev.pointerType !== 'mouse') ev.preventDefault();
    if (drag.node) { drag.node.pinned = true; svg.setPointerCapture(ev.pointerId); }
    else if (ev.pointerType === 'mouse') { svg.setPointerCapture(ev.pointerId); svg.classList.add('panning'); }
  });
  svg.addEventListener('pointermove', function (ev) {
    if (!drag || ev.pointerId !== drag.id) return;
    var p = toView(ev);
    if (Math.hypot(p.x - drag.start.x, p.y - drag.start.y) > 4) drag.moved = true;
    if (!drag.moved) return;
    if (drag.node) {
      var w = toWorld(p);
      drag.node.x = w.x; drag.node.y = w.y;
      paint();
      heat(0.25);
    } else {   // on touch, the browser keeps vertical drags for page scrolling
      zoom.x += p.x - drag.last.x; zoom.y += p.y - drag.last.y;
      applyZoom();
    }
    drag.last = p;
  });
  function release(ev) {
    if (!drag || ev.pointerId !== drag.id) return;
    var was = drag;
    drag = null;
    svg.classList.remove('panning');
    if (was.moved) return;
    if (was.node) {
      if (!was.node.pinnedByDrag) was.node.pinned = false;
      select(selected === was.node ? null : was.node);
    } else if (was.hit) {
      edgeTip(edges[+was.hit.dataset.i]);
    } else {
      select(null);
      tip.hidden = true;
    }
  }
  svg.addEventListener('pointerup', function (ev) { if (drag && drag.node && drag.moved) drag.node.pinnedByDrag = true; release(ev); });
  svg.addEventListener('pointercancel', function () { drag = null; svg.classList.remove('panning'); });
  svg.addEventListener('pointerover', function (ev) {
    var g = ev.target.closest('.nn'), hit = ev.target.closest('.nh');
    if (g) nodeTip(byId[g.dataset.id]);
    else if (hit) { var x = edges[+hit.dataset.i]; x.line.classList.add('hot'); edgeTip(x); }
  });
  svg.addEventListener('pointerout', function (ev) {
    var hit = ev.target.closest('.nh');
    if (hit) edges[+hit.dataset.i].line.classList.remove('hot');
    if (ev.target.closest('.nn') || hit) tip.hidden = true;
  });
  svg.addEventListener('wheel', function (ev) {   // plain scrolling must keep moving the page
    if (!(ev.ctrlKey || ev.metaKey)) return;
    ev.preventDefault();
    var p = toView(ev);
    zoomBy(ev.deltaY < 0 ? 1.12 : 1 / 1.12, p.x, p.y);
  }, { passive: false });
  svg.addEventListener('focusin', function (ev) { var g = ev.target.closest('.nn'); if (g) nodeTip(byId[g.dataset.id]); });
  svg.addEventListener('focusout', function () { tip.hidden = true; });
  svg.addEventListener('keydown', function (ev) {
    var g = ev.target.closest('.nn');
    if (g && (ev.key === 'Enter' || ev.key === ' ')) { ev.preventDefault(); var n = byId[g.dataset.id]; select(selected === n ? null : n); }
  });
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape' && selected) select(null); });

  // ------------------------------------------------------------ controls
  $('net-threshold').addEventListener('input', function () {
    threshold = +this.value;
    $('net-threshold-val').textContent = threshold + '%';
    filter();
  });
  $('net-size').addEventListener('change', sizes);
  $('net-colour').addEventListener('change', function () { svg.classList.toggle('plain', !this.checked); legend(); });
  var menu = $('net-select');
  nodes.slice().sort(function (a, b) { return a.surname.localeCompare(b.surname); }).forEach(function (n) {
    var o = html('option', '', n.name, menu); o.value = n.id;
  });
  menu.addEventListener('change', function () { select(byId[this.value] || null); });
  $('net-in').addEventListener('click', function () { zoomBy(1.25); });
  $('net-out').addEventListener('click', function () { zoomBy(0.8); });
  $('net-reset').addEventListener('click', function () {
    alpha = 0;
    nodes.forEach(function (n) { n.x = n.homeX; n.y = n.homeY; n.vx = n.vy = 0; n.pinned = n.pinnedByDrag = false; });
    paint(); fit();
  });
  $('net-freeze').addEventListener('click', function () {
    frozen = !frozen;
    this.setAttribute('aria-pressed', frozen ? 'true' : 'false');
    this.textContent = frozen ? 'Unfreeze layout' : 'Freeze layout';
    if (frozen) nodes.forEach(function (n) { n.vx = n.vy = 0; });
  });

  // ------------------------------------------------------------ export
  function save(blob, name) {
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
  }
  function standalone() {   // CSS variables and classes don't travel with a file, so write the computed styles onto a copy
    var copy = svg.cloneNode(true), from = svg.querySelectorAll('*'), to = copy.querySelectorAll('*');
    ['fill', 'stroke', 'stroke-width', 'opacity', 'font-family', 'font-size', 'font-weight', 'text-anchor', 'dominant-baseline', 'stroke-linecap', 'paint-order'].forEach(function (prop) {
      from.forEach(function (node, i) { to[i].style.setProperty(prop, getComputedStyle(node).getPropertyValue(prop)); });
    });
    copy.querySelectorAll('.nh').forEach(function (n) { n.remove(); });
    copy.querySelectorAll('.off').forEach(function (n) { n.remove(); });
    copy.querySelectorAll('image').forEach(function (n) { n.setAttribute('href', embedded[n.getAttribute('href')] || n.getAttribute('href')); });
    copy.setAttribute('xmlns', NS); copy.setAttribute('width', W * 2); copy.setAttribute('height', H * 2);
    var bg = el('rect', { width: W, height: H, fill: getComputedStyle($('net-side')).backgroundColor });
    copy.insertBefore(bg, copy.firstChild);
    return new XMLSerializer().serializeToString(copy);
  }
  // Portraits are separate files, which a saved image can't reach, so they are copied into it.
  var embedded = {};
  function embed() {
    var wanted = nodes.filter(function (n) { return n.photo && !embedded[n.photo]; });
    return Promise.all(wanted.map(function (n) {
      return fetch(n.photo).then(function (r) { return r.blob(); }).then(function (b) {
        return new Promise(function (done) {
          var read = new FileReader();
          read.onload = function () { embedded[n.photo] = read.result; done(); };
          read.readAsDataURL(b);
        });
      });
    }));
  }
  $('net-svgdl').addEventListener('click', function () {
    embed().then(function () { save(new Blob([standalone()], { type: 'image/svg+xml' }), 'voting-alliance-network.svg'); });
  });
  $('net-png').addEventListener('click', function () { embed().then(function () {
    var img = new Image();
    img.onload = function () {
      var c = document.createElement('canvas'); c.width = W * 2; c.height = H * 2;
      c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
      c.toBlob(function (b) { save(b, 'voting-alliance-network.png'); });
    };
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(standalone());
  }); });
  $('net-csv').addEventListener('click', function () {
    var quote = function (s) { return '"' + String(s).replace(/"/g, '""') + '"'; };
    var lines = ['councillor_a,councillor_b,agreement_percent,votes_agreed,votes_both_attended'];
    edges.forEach(function (x) { lines.push([quote(x.A.name), quote(x.B.name), x.pct.toFixed(2), x.agreed, x.shared].join(',')); });
    data.unknown.forEach(function (p) { lines.push([quote(byId[p[0]].name), quote(byId[p[1]].name), '', '', 0].join(',')); });
    save(new Blob([lines.join('\n') + '\n'], { type: 'text/csv' }), 'council-pairwise-agreement.csv');
  });

  paint(); fit(); sizes(); filter(); stats(); side();
})();
