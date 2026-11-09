"""The site's search page. It calls /api/search on its own domain; the site's Cloudflare Worker passes that on to
the private search API with a secret key."""
import html

e = html.escape
SEARCH_API = "/api"  # same site, absolute: the Cloudflare Worker forwards searches to the API
KINDS = [("summary", "Summaries"), ("vote", "Votes"), ("minutes", "Minutes"), ("transcript", "Transcripts")]

CSS = """
.sr-form{display:flex;gap:8px;margin:0 0 12px}
.sr-form input[type=search]{flex:1;min-width:0;font:inherit;font-size:17px;padding:9px 12px;border:1px solid var(--line);border-radius:8px;background:var(--panel);color:var(--ink)}
.sr-form input[type=search]:focus{outline:2px solid var(--accent);outline-offset:1px}
.sr-form button,.sr-mini button{font:inherit;font-weight:600;border:0;border-radius:8px;padding:9px 16px;background:var(--accent);color:var(--panel);cursor:pointer}
.sr-filters{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;font-size:14.5px;margin-bottom:18px}
.sr-filters label{display:inline-flex;align-items:center;gap:6px;cursor:pointer}
.sr-filters select{font:inherit;font-size:14px;border:1px solid var(--line);border-radius:6px;padding:3px 6px;background:var(--panel);color:var(--ink)}
.sr-status{color:var(--muted);font-size:14.5px;margin:0 0 12px;min-height:1.4em}
.sr-hit{padding:14px 0;border-top:1px solid var(--line)}
.sr-meta{display:flex;flex-wrap:wrap;gap:4px 10px;align-items:center;font-size:13px;color:var(--muted);margin-bottom:3px}
.sr-kind{font-weight:600;text-transform:uppercase;letter-spacing:.05em;font-size:11.5px;padding:1px 7px;border-radius:99px;background:var(--accent-soft);color:var(--accent)}
.sr-kind.vote{background:var(--warn-soft);color:var(--warn)}
.sr-hit a.t{font:600 18px/1.35 var(--serif);text-decoration:none}.sr-hit a.t:hover{text-decoration:underline}
.sr-hit p{margin:4px 0 0;font-size:15px;line-height:1.55}.sr-hit mark{background:var(--mark);color:inherit;border-radius:2px}
.sr-label{font-weight:600;color:var(--ink)}.sr-exact{font-size:12px}
.sr-weak{background:var(--warn-soft);border-radius:8px;padding:10px 14px;font-size:14.5px;margin-bottom:6px}
.sr-mini{display:flex;gap:6px;margin-top:14px;max-width:460px}
.sr-mini input{flex:1;min-width:0;font:inherit;font-size:15px;padding:7px 10px;border:1px solid var(--line);border-radius:8px;background:var(--panel);color:var(--ink)}
.sr-mini button{padding:7px 14px}
.sr-body{font-size:11.5px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);border:1px solid var(--line);border-radius:99px;padding:0 7px}
.sr-where{display:inline-flex;flex-wrap:wrap;gap:8px 16px}.sr-council{font-weight:600;color:var(--accent)}
"""

JS = r"""
(function(){
var CFG = %s, API = CFG.api, HERE = CFG.here, COUNCILS = CFG.councils, SLUGS = Object.keys(COUNCILS), form = document.getElementById('sr-form'), box = document.getElementById('sr-q'), status = document.getElementById('sr-status'), list = document.getElementById('sr-results');
var ALL = ['summary','vote','minutes','transcript'], NAMES = {summary:'Summary', vote:'Vote', minutes:'Minutes', transcript:'Transcript'};
function el(tag, cls, text, parent){ var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; if (parent) parent.appendChild(n); return n; }
function kinds(){ return ALL.filter(function(k){ return document.getElementById('sr-k-' + k).checked; }); }
var allBox = document.getElementById('sr-all'), comBox = document.getElementById('sr-com');
// Which councils to search: this one unless "All councils" is ticked, or the ticked ones on the all-councils page.
function councils(){
  if (HERE) return allBox && allBox.checked ? SLUGS : [HERE];
  return SLUGS.filter(function(c){ var b = document.getElementById('sr-c-' + c); return !b || b.checked; });
}
// Results link to pages relative to the council's folder; this page may be in it, beside it, or above it.
function link(h){ var c = h.city || HERE || (SLUGS.length === 1 ? SLUGS[0] : null); if (!c) return h.url; return (HERE ? (c === HERE ? '' : '../' + c + '/') : c + '/') + h.url; }
function when(d){ var t = new Date(d + 'T12:00:00'); return t.toLocaleDateString('en-CA', {year:'numeric', month:'short', day:'numeric'}); }
// Highlight query words in plain text without ever inserting HTML from the result.
function highlight(parent, text, q){
  var words = q.toLowerCase().split(/[^a-z0-9]+/).filter(function(w){ return w.length > 2; });
  if (!words.length){ parent.appendChild(document.createTextNode(text)); return; }
  var re = new RegExp('(' + words.map(function(w){ return w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }).join('|') + ')', 'gi');
  text.split(re).forEach(function(part, i){ if (i %% 2) el('mark', '', part, parent); else parent.appendChild(document.createTextNode(part)); });
}
function readUrl(){
  var u = new URLSearchParams(location.search);
  box.value = u.get('q') || '';
  var want = (u.get('kinds') || ALL.join(',')).split(',');
  ALL.forEach(function(k){ document.getElementById('sr-k-' + k).checked = want.indexOf(k) >= 0; });
  document.getElementById('sr-from').value = u.get('from') || '';
  document.getElementById('sr-to').value = u.get('to') || '';
  if (allBox) allBox.checked = u.get('all') === '1';
  comBox.checked = u.get('bodies') !== 'council';
  if (!HERE) { var want2 = (u.get('cities') || SLUGS.join(',')).split(','); SLUGS.forEach(function(c){ var b = document.getElementById('sr-c-' + c); if (b) b.checked = want2.indexOf(c) >= 0; }); }
}
function query(){
  var u = new URLSearchParams();
  u.set('q', box.value.trim());
  var k = kinds(); if (k.length < ALL.length) u.set('kinds', k.join(','));
  ['from','to'].forEach(function(f){ var v = document.getElementById('sr-' + f).value; if (v) u.set(f, v); });
  if (HERE && allBox && allBox.checked) u.set('all', '1');
  if (!comBox.checked) u.set('bodies', 'council');
  if (!HERE && councils().length < SLUGS.length) u.set('cities', councils().join(','));
  return u;
}
var seq = 0;
function run(push){
  var u = query();
  if (!u.get('q')) { status.textContent = 'Search summaries, votes, minutes and transcripts by meaning, not just exact words.'; list.textContent = ''; return; }
  if (!kinds().length) { status.textContent = 'Pick at least one kind of result.'; list.textContent = ''; return; }
  if (!councils().length) { status.textContent = 'Pick at least one council.'; list.textContent = ''; return; }
  if (push) history.replaceState(null, '', '?' + u.toString());
  var mine = ++seq;
  status.textContent = 'Searching…';
  u.set('limit', '40');
  u.delete('all');
  u.set('cities', councils().join(','));
  fetch(API + '/search?' + u.toString()).then(function(r){
    return r.json().catch(function(){ return {}; }).then(function(body){ if (!r.ok) throw new Error(body.error || ('The search service answered ' + r.status)); return body; });
  }).then(function(body){
    if (mine !== seq) return;
    list.textContent = '';
    status.textContent = body.results.length ? body.results.length + ' best matches from ' + body.searched.toLocaleString() + ' passages.' : 'Nothing found.';
    if (body.weak) {
      var note = el('div', 'sr-weak', null, list);
      el('b', '', 'Nothing in these records closely matches “' + body.query + '”.', note);
      el('span', '', ' No passage uses those words, and none is close in meaning, so the results below are only the nearest and are probably unrelated. Council may not have discussed it at the meetings on this site.', note);
    }
    body.results.forEach(function(h){
      var item = el('div', 'sr-hit', null, list), meta = el('div', 'sr-meta', null, item);
      el('span', 'sr-kind ' + h.kind, NAMES[h.kind] || h.kind, meta);
      if (h.city && (!HERE || h.city !== HERE)) el('span', 'sr-council', COUNCILS[h.city] || h.city, meta);
      el('span', '', when(h.date || h.meeting.slice(0, 10)), meta);
      if (h.body === 'committee') el('span', 'sr-body', 'Committee', meta);
      if (h.label) el('span', 'sr-label', h.label, meta);
      if (h.exact) el('span', 'sr-exact', 'uses your words', meta);
      var a = el('a', 't', h.title, item); a.href = link(h);
      highlight(el('p', '', null, item), h.snippet, body.query);
    });
  }).catch(function(err){
    if (mine !== seq) return;
    list.textContent = '';
    status.textContent = '';
    status.textContent = (err && err.message && err.message.indexOf('fetch') < 0 ? err.message : "Couldn't reach the search service.") + ' Try again in a moment.';
  });
}
form.addEventListener('submit', function(ev){ ev.preventDefault(); run(true); });
document.getElementById('sr-filters').addEventListener('change', function(){ if (box.value.trim()) run(true); });
addEventListener('popstate', function(){ readUrl(); run(false); });
readUrl(); run(false);
if (!box.value) box.focus();
})();
"""


def mini_form(action="search.html", placeholder="Search votes, minutes and transcripts"):
    """A small search box for other pages; it opens the search page."""
    return (f'<form class="sr-mini" action="{action}" method="get" role="search">'
            f'<input type="search" name="q" placeholder="{e(placeholder, quote=True)}" aria-label="Search council records">'
            '<button type="submit">Search</button></form>')


def councils():
    from core import city as cities
    return {s: cities.load(s).get("display_name", cities.load(s).name) for s in cities.all_slugs()}


def page_body(years, city=None):
    """The search page of one council (city) or, with city=None, of all of them (at the site's root)."""
    boxes = "".join(f'<label><input type="checkbox" id="sr-k-{k}" checked> {e(name)}</label>' for k, name in KINDS)
    options = lambda first: f'<option value="">{first}</option>' + "".join(f'<option value="{y}-{"01-01" if first == "Any start" else "12-31"}">{y}</option>' for y in years)
    names = councils()
    if city:
        where = (f'<label><input type="checkbox" id="sr-all"> All councils</label>' if len(names) > 1 else "")
        back, title = '<a href="index.html">&larr; All meetings</a>', "Search council records"
    else:
        where = "".join(f'<label><input type="checkbox" id="sr-c-{s}" checked> {e(n)}</label>' for s, n in names.items()) if len(names) > 1 else ""
        back, title = '<a href="index.html">&larr; All councils</a>', "Search every council"
    return f"""
<header class="top"><div class="eyebrow">{back}</div>
<h1>{title}</h1>
<p class="lede">Finds passages by meaning: a search for “homelessness” also finds encampments, shelters and drop-in funding.</p></header>
<form class="sr-form" id="sr-form" role="search"><input type="search" id="sr-q" name="q" placeholder="What are you looking for?" aria-label="Search">
<button type="submit">Search</button></form>
<div class="sr-filters" id="sr-filters">{boxes}
<label>From <select id="sr-from" aria-label="From year">{options("Any start")}</select></label>
<label>to <select id="sr-to" aria-label="To year">{options("Any end")}</select></label>
<label title="Standing committees make recommendations that Council then decides on"><input type="checkbox" id="sr-com" checked> Include committee meetings</label>{f'<span class="sr-where">{where}</span>' if where else ''}</div>
<p class="sr-status" id="sr-status" aria-live="polite"></p>
<div id="sr-results"></div>
<footer>Results come from the councils' minutes, the automated summaries on this site and machine transcripts of the recordings,
so transcript passages can contain misheard words.</footer>"""


def script(city=None):
    import json
    return JS % json.dumps({"api": SEARCH_API if city is None else SEARCH_API, "here": city.slug if city else None, "councils": councils()})
