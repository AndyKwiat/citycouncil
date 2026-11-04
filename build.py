#!/usr/bin/env python3
"""Render raw/<date>/ into the static site under site/."""
import collections, datetime as dt, html, itertools, json, math, pathlib, re, shutil
import pipeline as p

e = html.escape
BASE = p.BASE

CSS = """
:root{color-scheme:light dark;--bg:#f7f5ef;--panel:#fffefa;--ink:#1f2421;--muted:#667067;--line:#ddd9cc;
--accent:#1f5f4a;--accent-soft:#e3eee8;--warn:#8a4b12;--warn-soft:#f6ead9;--mark:#fdf3c9;
--serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
@media (prefers-color-scheme:dark){:root{--bg:#141815;--panel:#1b201c;--ink:#e7e9e3;--muted:#99a398;--line:#303730;
--accent:#7cc7a8;--accent-soft:#1f3029;--warn:#e0a868;--warn-soft:#33281b;--mark:#3a3518}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 var(--sans);-webkit-font-smoothing:antialiased}
.wrap{max-width:780px;margin:0 auto;padding:48px 16px 72px}
header.top{margin-bottom:32px}
.eyebrow{font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);font-weight:600}
h1{font:600 38px/1.15 var(--serif);margin:6px 0 10px;letter-spacing:-.01em}
.lede{color:var(--muted);margin:0;max-width:60ch}
a{color:var(--accent);text-underline-offset:2px}
details.meeting{background:var(--panel);border:1px solid var(--line);border-radius:10px;margin-bottom:12px}
details.meeting[open]{box-shadow:0 2px 14px rgba(0,0,0,.06)}
summary{list-style:none;cursor:pointer;display:grid;grid-template-columns:96px 1fr 18px;gap:16px;align-items:start;padding:18px 20px;border-radius:10px}
summary::-webkit-details-marker{display:none}
summary:focus-visible,.vote:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
summary:hover h2{color:var(--accent)}
.date .d{font:600 24px/1.1 var(--serif);display:block}
.date .y,.date .t{font-size:13px;color:var(--muted);display:block}
.date .t{margin-top:2px}
summary h2{font:600 20px/1.3 var(--serif);margin:0 0 3px;transition:color .12s}
summary p{margin:0;color:var(--muted);font-size:14.5px;line-height:1.45}
.chev{color:var(--muted);transition:transform .15s;margin-top:4px;font-size:13px}
details[open] .chev{transform:rotate(90deg)}
.body{padding:2px 20px 22px;border-top:1px solid var(--line)}
.body h3{font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:22px 0 8px;font-weight:600}
.body p{margin:0 0 10px}
.decision{padding:12px 0;border-top:1px solid var(--line)}
.decision:first-of-type{border-top:0;padding-top:2px}
.decision .row{display:flex;gap:10px;justify-content:space-between;align-items:baseline}
.decision b{font-weight:600}
.decision p{margin:3px 0 0;color:var(--muted);font-size:14.5px;line-height:1.5}
.jump{display:flex;flex-wrap:wrap;gap:2px 14px;margin-top:5px;font-size:13.5px}
.vote{appearance:none;border:0;font:inherit;cursor:pointer;flex:none;font-size:12.5px;line-height:1.5;padding:1px 8px;border-radius:99px;background:var(--accent-soft);color:var(--accent);font-variant-numeric:tabular-nums;white-space:nowrap;font-weight:600}
.vote.split{background:var(--warn-soft);color:var(--warn)}
.vote.plain{cursor:help;font-weight:500}
#pop{position:fixed;z-index:10;width:min(340px,calc(100vw - 24px));background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:9px;box-shadow:0 8px 28px rgba(0,0,0,.2);padding:12px 14px;font-size:14px;line-height:1.45}
#pop[hidden]{display:none}
#pop h4{margin:0 0 7px;font-size:14px;font-weight:600}
#pop .side{margin-top:6px}#pop .side b{display:block;font-size:12px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.04em}
#pop .more{display:block;margin-top:8px;font-size:13px}
ul.tight{margin:0;padding-left:18px}ul.tight li{margin-bottom:7px}
.links{display:flex;flex-wrap:wrap;gap:8px 14px;margin-top:20px;padding-top:14px;border-top:1px solid var(--line);font-size:14.5px;align-items:center}
.btn{background:var(--accent);color:var(--panel);text-decoration:none;font-weight:600;padding:6px 13px;border-radius:7px}
footer{margin-top:30px;color:var(--muted);font-size:13.5px}
.tr{font-size:16px}.tr .para{display:grid;grid-template-columns:70px 1fr;gap:14px;padding:5px 8px;margin:0 -8px 8px;border-radius:7px;scroll-margin-top:12px}
.tr .para:target{background:var(--mark)}
.tr .ts{color:var(--muted);font-size:13px;font-variant-numeric:tabular-nums;padding-top:3px}
.tr .para p{margin:0}
.src{font-size:11.5px;color:var(--warn);margin-left:6px;white-space:nowrap}
.note{background:var(--warn-soft);color:var(--ink);border-radius:8px;padding:10px 14px;font-size:14.5px;margin-bottom:24px}
.gap{color:var(--muted);font-size:13.5px;text-align:center;border-block:1px dashed var(--line);padding:6px;margin:0 0 14px}
.mins .item{padding:16px 0;border-top:1px solid var(--line);scroll-margin-top:8px}
.mins h2{font:600 19px/1.35 var(--serif);margin:0 0 6px}.mins .sub h2{font-size:17px}
.mins .num{color:var(--muted);font-family:var(--sans);font-size:14px;margin-right:6px;font-weight:500}
.motion{background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:12px 14px;margin:10px 0;scroll-margin-top:12px}
.motion:target{outline:2px solid var(--accent);background:var(--mark)}
.motion .mhead{display:flex;justify-content:space-between;gap:10px;align-items:baseline;font-weight:600;font-size:14.5px;margin-bottom:3px}
.motion .who{color:var(--muted);font-size:13.5px;margin-bottom:6px}
.motion p,.mins .notes p{margin:0 0 7px}.motion ol,.motion ul{margin:0 0 7px;padding-left:22px}
.tally{font-size:14px;margin-top:6px;color:var(--muted)}.tally b{color:var(--ink);font-weight:600}
.files{font-size:13.5px;margin:6px 0 0;padding-left:18px;color:var(--muted)}
.cn-nav{display:inline-block;margin-top:10px;font-size:15px}
.cn-chart{display:block;width:100%;height:auto;margin:0 auto}
.cn-chart .e{fill:none;stroke:var(--accent);stroke-linecap:round;transition:opacity .12s}
.cn-chart .hit{fill:none;stroke:transparent;pointer-events:stroke;cursor:pointer}
.cn-chart.sel .e{opacity:.04!important}.cn-chart.sel .e.on{opacity:.85!important}
.cn-chart.sel .hit{pointer-events:none}.cn-chart.sel .hit.on{pointer-events:stroke}
.cn-node{cursor:pointer;outline:none}.cn-node .pad{fill:transparent}
.cn-node .dot{fill:var(--ink);stroke:var(--bg);stroke-width:3}
.cn-node text{fill:var(--ink);font:600 18px var(--sans)}
.cn-chart.sel .cn-node:not(.on):not(.near) text{fill:var(--muted);font-weight:400}
.cn-node.on .dot{fill:var(--accent)}
.cn-node:focus-visible .dot{stroke:var(--accent);stroke-width:4}
.cn-legend{display:flex;flex-wrap:wrap;gap:6px 20px;align-items:center;justify-content:center;color:var(--muted);font-size:13.5px;margin:4px 0 20px}
.cn-legend span{display:inline-flex;align-items:center;gap:7px;font-variant-numeric:tabular-nums}
.cn-legend i{display:inline-block;width:34px;background:var(--accent);border-radius:9px}
.cn-panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 18px;min-height:200px}
.cn-panel[hidden]{display:none}.cn-panel h2{font:600 20px/1.3 var(--serif);margin:0 0 2px}
.cn-panel h3{font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:0 0 8px;font-weight:600}
.cn-panel .hint{color:var(--muted);font-size:14px;margin:0 0 12px}
.cn-cols{display:grid;grid-template-columns:1fr 1fr;gap:18px 28px}
.cn-row{display:grid;grid-template-columns:minmax(0,1fr) 72px 64px;gap:10px;align-items:center;font-size:14.5px;padding:2px 0}
.cn-row.pair{grid-template-columns:minmax(0,1fr) 64px}
.cn-row .num{color:var(--muted);text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;font-size:13.5px}
.cn-bar{height:6px;background:var(--line);border-radius:4px;overflow:hidden}.cn-bar b{display:block;height:100%;background:var(--accent);border-radius:4px}
#cntip{position:fixed;z-index:10;pointer-events:none;max-width:280px;background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:8px;box-shadow:0 8px 28px rgba(0,0,0,.2);padding:7px 11px;font-size:14px;line-height:1.4}
#cntip[hidden]{display:none}#cntip span{color:var(--muted);display:block;font-size:13px}
details.more{margin-top:14px;background:var(--panel);border:1px solid var(--line);border-radius:10px}
details.more>summary{display:block;font-weight:600;padding:12px 18px}
details.more>summary:hover{color:var(--accent)}.more .in{padding:0 18px 16px}
.scroll{overflow-x:auto}
table.cn{border-collapse:collapse;font-size:13.5px;font-variant-numeric:tabular-nums}
table.cn th{font-weight:500;text-align:left;white-space:nowrap;padding:3px 8px 3px 0}
table.cn thead th{writing-mode:vertical-rl;transform:rotate(180deg);padding:0 0 6px;text-align:left;height:100px;vertical-align:bottom}
table.cn td{width:30px;min-width:30px;height:28px;text-align:center;border:2px solid var(--panel);border-radius:4px}
table.cn td.self{background:var(--line)}
.cn-vote{display:grid;grid-template-columns:96px minmax(0,1fr) auto;gap:10px;padding:7px 0;border-top:1px solid var(--line);font-size:14.5px;align-items:baseline}
.cn-vote:first-child{border-top:0}.cn-vote .when{color:var(--muted);font-size:13.5px}
@media (max-width:560px){.cn-cols{grid-template-columns:1fr}.cn-node text{font-size:30px}.cn-node .pre{display:none}
.cn-vote{grid-template-columns:minmax(0,1fr) auto}.cn-vote .when{grid-column:1/3}
summary{grid-template-columns:1fr 18px;gap:6px 10px;padding:16px}
.date{grid-column:1/2}.date .d,.date .y,.date .t{display:inline;font-size:14px;font-family:var(--sans);font-weight:500;color:var(--muted);margin-right:4px}
.chev{grid-column:2;grid-row:1}summary .head{grid-column:1/3}h1{font-size:30px}.body{padding:2px 16px 18px}
.tr .para{grid-template-columns:1fr;gap:0}.wrap{padding-top:28px}}
"""

JS = """
(function(){
var pop=document.createElement('div');pop.id='pop';pop.hidden=true;pop.setAttribute('role','tooltip');document.body.appendChild(pop);
var pinned=null,hideTimer=null;
function side(label,names){return names.length?'<div class="side"><b>'+label+' ('+names.length+')</b>'+names.join(', ')+'</div>':''}
function fill(b){var d=JSON.parse(b.dataset.vote);
 pop.innerHTML='<h4>'+d.title+'</h4>'+(d.note?'<div>'+d.note+'</div>':'')+side('For',d.yes)+side('Against',d.no)+side('Other',d.other)+side('Absent',d.absent)+(d.href?'<a class="more" href="'+d.href+'">See this motion in the minutes</a>':'');}
function place(b){pop.hidden=false;var r=b.getBoundingClientRect(),h=pop.offsetHeight,w=pop.offsetWidth;
 var x=Math.max(12,Math.min(r.left,innerWidth-w-12));var y=r.bottom+6;if(y+h>innerHeight-8)y=Math.max(8,r.top-h-6);
 pop.style.left=x+'px';pop.style.top=y+'px';}
function show(b){clearTimeout(hideTimer);fill(b);place(b);}
function hide(){pinned=null;pop.hidden=true;}
function soon(){hideTimer=setTimeout(function(){if(!pinned)pop.hidden=true},180);}
document.addEventListener('mouseover',function(ev){var b=ev.target.closest&&ev.target.closest('.vote');if(b&&!pinned)show(b);if(ev.target.closest&&ev.target.closest('#pop'))clearTimeout(hideTimer);});
document.addEventListener('mouseout',function(ev){if(ev.target.closest&&(ev.target.closest('.vote')||ev.target.closest('#pop')))soon();});
document.addEventListener('focusin',function(ev){if(ev.target.matches&&ev.target.matches('.vote')&&!pinned)show(ev.target);});
document.addEventListener('focusout',function(ev){if(ev.target.matches&&ev.target.matches('.vote'))soon();});
document.addEventListener('click',function(ev){var b=ev.target.closest&&ev.target.closest('.vote');
 if(b){ev.preventDefault();ev.stopPropagation();if(pinned===b){hide();return}pinned=b;show(b);return}
 if(!(ev.target.closest&&ev.target.closest('#pop')))hide();});
document.addEventListener('keydown',function(ev){if(ev.key==='Escape')hide();});
addEventListener('scroll',function(){if(!pop.hidden&&!pinned)pop.hidden=true},true);
function openHash(){if(!location.hash)return;var m=document.querySelector(location.hash);if(m&&m.tagName==='DETAILS'){m.open=true;m.scrollIntoView()}}
openHash();addEventListener('hashchange',openHash);
})();
"""


CHART_JS = """
(function(){
var svg=document.querySelector('.cn-chart');if(!svg)return;
var edges=[].slice.call(svg.querySelectorAll('.e')),hits=[].slice.call(svg.querySelectorAll('.hit')),nodes=[].slice.call(svg.querySelectorAll('.cn-node'));
var panels=[].slice.call(document.querySelectorAll('.cn-panel'));
var tip=document.createElement('div');tip.id='cntip';tip.hidden=true;tip.setAttribute('role','tooltip');document.body.appendChild(tip);
var pinned=null;
function mark(list,on){list.forEach(function(x){x.classList.toggle('on',on(x))})}
function pick(name){
 svg.classList.toggle('sel',!!name);
 function touches(x){return x.dataset.a===name||x.dataset.b===name}
 mark(edges,touches);mark(hits,touches);
 nodes.forEach(function(n){var me=n.dataset.name===name;n.classList.toggle('on',me);n.setAttribute('aria-pressed',pinned===name&&me?'true':'false')});
 panels.forEach(function(p){p.hidden=(p.dataset.for||'')!==(name||'')});
}
function single(hit){
 svg.classList.add('sel');
 edges.forEach(function(x){x.classList.toggle('on',x.dataset.i===hit.dataset.i)});
 hits.forEach(function(x){x.classList.toggle('on',x===hit)});
 nodes.forEach(function(n){var m=n.dataset.name===hit.dataset.a||n.dataset.name===hit.dataset.b;n.classList.toggle('near',m)});
}
function clearNear(){nodes.forEach(function(n){n.classList.remove('near')})}
function showTip(hit,ev){
 tip.textContent='';var b=document.createElement('b');b.textContent=hit.dataset.a+' & '+hit.dataset.b;
 var sp=document.createElement('span');sp.textContent=hit.dataset.text;tip.appendChild(b);tip.appendChild(sp);tip.hidden=false;
 var x=Math.max(8,Math.min(ev.clientX+14,innerWidth-tip.offsetWidth-8)),y=ev.clientY-tip.offsetHeight-12;if(y<8)y=ev.clientY+16;
 tip.style.left=x+'px';tip.style.top=y+'px';}
function rest(){tip.hidden=true;clearNear();pick(pinned)}
nodes.forEach(function(n){var name=n.dataset.name;
 n.addEventListener('mouseenter',function(){if(!pinned)pick(name)});
 n.addEventListener('mouseleave',function(){if(!pinned)pick(null)});
 n.addEventListener('focus',function(){if(!pinned)pick(name)});
 n.addEventListener('blur',function(){if(!pinned)pick(null)});
 n.addEventListener('click',function(ev){ev.stopPropagation();pinned=pinned===name?null:name;pick(pinned||name)});
 n.addEventListener('keydown',function(ev){if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();pinned=pinned===name?null:name;pick(pinned||name)}});
});
hits.forEach(function(h){
 h.addEventListener('mouseenter',function(ev){if(!pinned)single(h);showTip(h,ev)});
 h.addEventListener('mousemove',function(ev){showTip(h,ev)});
 h.addEventListener('mouseleave',rest);
 h.addEventListener('click',function(ev){ev.stopPropagation();showTip(h,ev)});
});
document.addEventListener('click',function(ev){if(ev.target.closest&&ev.target.closest('.cn-chart')&&ev.target!==svg)return;tip.hidden=true;if(pinned){pinned=null;pick(null)}else rest()});
document.addEventListener('keydown',function(ev){if(ev.key==='Escape'){pinned=null;rest()}});
})();
"""


def page(title, body, script=True, extra_js=""):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)}</title>'
            f'<style>{CSS}</style></head><body><div class="wrap">{body}</div>'
            + (f"<script>{JS}</script>" if script else "") + (f"<script>{extra_js}</script>" if extra_js else "") + "</body></html>")


def hms(s):
    s = int(s)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def paragraphs(segs, gap=4.0, max_s=75):
    paras, cur = [], None
    for s in segs:
        if cur and (s["start"] - cur["end"] > gap or s["end"] - cur["start"] > max_s or s.get("source") != cur["source"]):
            paras.append(cur)
            cur = None
        if not cur:
            cur = {"start": s["start"], "end": s["end"], "text": [], "source": s.get("source")}
        cur["text"].append(s["text"])
        cur["end"] = s["end"]
    if cur:
        paras.append(cur)
    return paras


def vote_badge(x, minutes, key, prefix=""):
    """The clickable result for a motion, with who voted which way carried in a data attribute."""
    r = x["result"]
    label = r["label"] or "No vote"
    if not r["label"]:
        return ""
    voted = x["votes"]["for"] + x["votes"]["against"] + x["votes"]["other"]
    absent = [n for n in minutes["roster"] if n not in voted] if voted else []
    title = x["name"] or x["item_title"]
    note = ""
    if x["inherited"]:
        note = "Passed as part of the consent report." + ("" if voted else " No individual votes were recorded.")
    elif r.get("inferred"):
        note = f"The minutes give only the count, not the word \"{r['outcome']}\"; the outcome is inferred from the count."
    elif not voted:
        note = {"Withdrawn": "Withdrawn before a vote.", "Out of order": "Ruled out of order, so there was no vote.",
                "Referred": "Referred, so there was no final vote."}.get(r["outcome"], "No individual votes were recorded.")
    data = {"title": e(title), "note": e(note), "yes": x["votes"]["for"], "no": x["votes"]["against"],
            "other": x["votes"]["other"], "absent": absent, "href": f"{prefix}minutes/{key}.html#{x['id']}" if prefix is not None else ""}
    split = "split" if r["against"] or r["outcome"] in ("Defeated", "Lost") else ""
    desc = f"For: {', '.join(x['votes']['for'])}. Against: {', '.join(x['votes']['against']) or 'none'}." if voted else note
    return (f'<button type="button" class="vote {split}" aria-label="{e(label + ". " + desc)}" '
            f"data-vote='{e(json.dumps(data), quote=True)}'>{e(label)}</button>")


def rich(text, motions, minutes, key):
    """Escape summary prose and swap {{vote:mN}} tokens for vote badges."""
    def sub(found):
        x = motions.get(found.group(1))
        return vote_badge(x, minutes, key) if x else ""
    return re.sub(r"\{\{vote:(m\d+)\}\}", sub, e(text))


def item_time(minutes, item_id, number):
    """Where in the recording an agenda item starts, falling back to its parent item."""
    by_number = {i["number"]: i for i in minutes["items"]}
    item = next((i for i in minutes["items"] if i["id"] == item_id), None)
    while item:
        if item["video_start"] is not None:
            return item["video_start"], item["id"]
        item = by_number.get(item["number"].rsplit(".", 1)[0]) if "." in item["number"] else None
    return None, None


SOURCE_NOTE = {
    "captions": "From the closed captions on the city's video.",
    "captions+whisper": "From the closed captions on the city's video, with Whisper speech recognition filling stretches the captions missed (labelled below).",
    "whisper": "Generated from the meeting audio with Whisper speech recognition instead of the city's captions.",
}


def build_transcript(out, key, sumr, m, meta, segs, docs, long_date):
    video = f"{BASE}/Players/ISIStandAlonePlayer.aspx?Id={m['ID']}"
    checked = {g["start"]: g for g in meta.get("gaps", [])}
    paras, prev_end, starts = "", None, []
    for pr in paragraphs(segs):
        if prev_end is not None and pr["start"] - prev_end > p.GAP_SECONDS:
            minutes_gap = round((pr["start"] - prev_end) / 60)
            verified = any(g["end"] >= pr["start"] - 60 and not g["filled"] for g in checked.values())
            paras += (f'<div class="gap">No text for {minutes_gap} minutes'
                      + (" (audio checked: no real speech, likely a closed session or recess)" if verified else "") + "</div>")
        start = int(pr["start"])
        starts.append(start)
        tag = '<span class="src">Whisper</span>' if pr["source"] == "whisper" and meta["method"] == "captions+whisper" else ""
        paras += f'<div class="para" id="t-{start}"><div class="ts">{hms(start)}</div><p>{e(" ".join(pr["text"]))}{tag}</p></div>'
        prev_end = pr["end"]
    (out / "transcripts" / f"{key}.html").write_text(page(f"Transcript: {long_date}", f"""
<header class="top"><div class="eyebrow"><a href="../index.html#m-{key}">&larr; All meetings</a></div>
<h1>{e(sumr['title'])}</h1><p class="lede">Guelph City Council, {long_date}. {meta['words']:,} words.
<a href="{video}">Watch the recording</a>.</p></header>
<div class="note">{SOURCE_NOTE[meta['method']]} Expect misspelled names and misheard words, and there are no speaker labels.
Timestamps are positions in the recording, not clock time. For what was officially decided, rely on the
<a href="../minutes/{key}.html">minutes</a>.</div>
<div class="tr">{paras}</div>""", script=False))
    return starts


def build_minutes(out, key, sumr, minutes, m, official, long_date):
    motions = {x["id"]: x for x in minutes["motions"]}
    html_items = ""
    for it in minutes["items"]:
        sub = "sub" if "." in it["number"] else ""
        body = "".join(f'<div class="notes">{n}</div>' for n in it["notes"])
        for mid in it["motions"]:
            x = motions[mid]
            who = " · ".join(filter(None, [f"Moved by {x['moved_by']}" if x["moved_by"] else "", f"Seconded by {x['seconded_by']}" if x["seconded_by"] else ""]))
            tally = ""
            if x["votes"]["for"]:
                tally += f'<div class="tally"><b>For ({len(x["votes"]["for"])}):</b> {e(", ".join(x["votes"]["for"]))}</div>'
            if x["votes"]["against"]:
                tally += f'<div class="tally"><b>Against ({len(x["votes"]["against"])}):</b> {e(", ".join(x["votes"]["against"]))}</div>'
            result = e(x["result"]["text"] or x["result"]["label"] or "")
            if x["inherited"]:
                result = "Passed with the consent report" + (f": {result}" if result else "")
            elif x["result"].get("inferred"):
                result = f"{e(x['result']['outcome'])} {result} (outcome inferred; the minutes give only the count)"
            body += (f'<div class="motion" id="{x["id"]}"><div class="mhead"><span>{e(x["name"] or "Motion")}</span><span>{result}</span></div>'
                     + (f'<div class="who">{e(who)}</div>' if who else "") + x["text_html"] + tally + x["post_html"] + "</div>")
        if it["attachments"]:
            body += '<ul class="files">' + "".join(f'<li><a href="{e(a["url"], quote=True)}">{e(a["name"])}</a></li>' for a in it["attachments"]) + "</ul>"
        anchor = f' id="i-{it["id"]}"' if it["id"] else ""
        html_items += f'<section class="item {sub}"{anchor}><h2><span class="num">{e(it["number"])}</span>{e(it["title"])}</h2>{body}</section>'
    present = [n for n in minutes["roster"] if n not in minutes["absent"]]
    attendance = f"Present: {', '.join(present)}." + (f" Absent: {', '.join(minutes['absent'])}." if minutes["absent"] else "")
    (out / "minutes" / f"{key}.html").write_text(page(f"Minutes: {long_date}", f"""
<header class="top"><div class="eyebrow"><a href="../index.html#m-{key}">&larr; All meetings</a></div>
<h1>Minutes: {long_date}</h1><p class="lede">{e(attendance)}</p></header>
<div class="note">A copy of the city's published minutes, reformatted for this site. The
<a href="{official}">official minutes</a> are the record.</div>
<div class="mins">{html_items}</div>""", script=False))


def agreement(built):
    """Who agreed with whom, counted only on recorded votes where at least one councillor dissented."""
    if not (p.ROOT / "votes" / "votes.json").exists():
        p.export_votes()
    rows = p.read_json(p.ROOT / "votes" / "votes.json")["motions"]
    votes = [r for r in rows if r["meeting_date"] in built and r["for"] and r["against"] and not r["duplicate_of_consent_vote"]]
    agreed, shared = {}, {}
    names = sorted({n for r in votes for n in r["for"] + r["against"]})
    for r in votes:
        yes, no = set(r["for"]), set(r["against"])
        for a, b in itertools.combinations(sorted(yes | no), 2):
            shared[a, b] = shared.get((a, b), 0) + 1
            agreed[a, b] = agreed.get((a, b), 0) + ((a in yes) == (b in yes))
    return votes, names, agreed, shared


def circle_order(names, agreed):
    """Seat people who agree most next to each other, so the thick lines stay readable."""
    w = lambda a, b: agreed.get((min(a, b), max(a, b)), 0)
    total = lambda o: sum(w(o[i], o[(i + 1) % len(o)]) for i in range(len(o)))
    order, improved = list(names), True
    while improved:
        improved = False
        for i in range(len(order) - 1):
            for j in range(i + 2, len(order) + 1):
                trial = order[:i] + order[i:j][::-1] + order[j:]
                if total(trial) > total(order):
                    order, improved = trial, True
    top = next((i for i, n in enumerate(order) if n.startswith("Mayor")), 0)
    return order[top:] + order[:top]


def build_councillors(out, all_minutes):
    votes, names, agreed, shared = agreement(all_minutes)
    if len(names) < 2:
        return False
    order = circle_order(names, agreed)
    most = max(agreed.values())
    pair = lambda a, b: (min(a, b), max(a, b))
    # Squaring the count makes the differences readable; the legend shows real examples.
    width = lambda n: max(0.8, 15 * (n / most) ** 2)
    W, H, cx, cy, R = 900, 680, 450, 340, 280
    pos = {n: (cx + R * math.sin(2 * math.pi * i / len(order)), cy - R * math.cos(2 * math.pi * i / len(order))) for i, n in enumerate(order)}

    def curve(a, b):
        (x1, y1), (x2, y2) = pos[a], pos[b]
        qx, qy = cx + ((x1 + x2) / 2 - cx) * .45, cy + ((y1 + y2) / 2 - cy) * .45
        return f"M{x1:.1f} {y1:.1f}Q{qx:.1f} {qy:.1f} {x2:.1f} {y2:.1f}"

    links = sorted(((agreed[k], k) for k in shared), key=lambda t: (t[0], t[1]))
    lines, hits = "", ""
    for i, (n, (a, b)) in enumerate(links):
        attrs = f'data-i="{i}" data-a="{e(a, quote=True)}" data-b="{e(b, quote=True)}"'
        lines += f'<path class="e" {attrs} d="{curve(a, b)}" stroke-width="{width(n):.1f}" opacity="{.22 + .5 * (n / most) ** 2:.2f}"/>'
        text = f"Voted the same way on {n} of the {shared[a, b]} contested votes they both attended"
        # Thin lines sit on top so they stay reachable; a small target stops them stealing hover from thick ones.
        hits = f'<path class="hit" {attrs} data-text="{e(text, quote=True)}" d="{curve(a, b)}" stroke-width="{max(8, width(n) + 2):.1f}"/>' + hits
    nodes = ""
    for n in order:
        x, y = pos[n]
        dx, dy = (x - cx) / R, (y - cy) / R
        anchor = "middle" if abs(dx) < .2 else ("start" if dx > 0 else "end")
        tx, ty = x + dx * 20, y + dy * 20 + 6 + (-8 if dy < -.9 else 8 if dy > .9 else 0)
        pre, last = n.rsplit(" ", 1) if " " in n else ("", n)
        label = (f'<tspan class="pre">{e(pre)} </tspan>' if pre else "") + e(last)
        ranked = sorted(((agreed[pair(n, o)], o) for o in names if o != n and pair(n, o) in shared), key=lambda t: (-t[0], t[1]))
        desc = f"{n}. Agreed most with {ranked[0][1]}, on {ranked[0][0]} votes, and least with {ranked[-1][1]}, on {ranked[-1][0]}."
        nodes += (f'<g class="cn-node" role="button" tabindex="0" aria-pressed="false" data-name="{e(n, quote=True)}" aria-label="{e(desc, quote=True)}">'
                  f'<circle class="pad" cx="{x:.1f}" cy="{y:.1f}" r="22"/><circle class="dot" cx="{x:.1f}" cy="{y:.1f}" r="9"/>'
                  f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="{anchor}">{label}</text></g>')
    legend = "".join(f'<span><i style="height:{width(n):.1f}px"></i>{n} votes</span>' for n in sorted({round(most * .35), round(most * .65), most}))

    def row(label, n, of, bar=True):
        fill = f'<div class="cn-bar"><b style="width:{100 * n / most:.0f}%"></b></div>' if bar else ""
        return f'<div class="cn-row{"" if bar else " pair"}"><span>{e(label)}</span>{fill}<span class="num">{n} of {of}</span></div>'

    def ties(ranked, count=5):
        return [t for t in ranked if (t[0] >= ranked[count - 1][0] if ranked[0][0] >= ranked[-1][0] else t[0] <= ranked[count - 1][0])]

    by_pair = sorted(((agreed[k], k) for k in shared), key=lambda t: (-t[0], t[1]))
    pair_rows = lambda items: "".join(row(f"{a} & {b}", n, shared[a, b], bar=False) for n, (a, b) in items)
    panels = (f'<div class="cn-panel" data-for=""><p class="hint">Select a name to see only their lines, or select a line for its count.</p>'
              f'<div class="cn-cols"><div><h3>Agreed most</h3>{pair_rows(ties(by_pair))}</div>'
              f'<div><h3>Agreed least</h3>{pair_rows(ties(by_pair[::-1]))}</div></div></div>')
    for n in order:
        ranked = sorted(((agreed[pair(n, o)], o) for o in names if o != n and pair(n, o) in shared), key=lambda t: (-t[0], t[1]))
        panels += (f'<div class="cn-panel" data-for="{e(n, quote=True)}" hidden><h2>{e(n)}</h2><p class="hint">How often they voted the same way as each colleague.</p>'
                   + "".join(row(o, c, shared[pair(n, o)]) for c, o in ranked) + "</div>")

    def shade(c):
        return f"background:color-mix(in srgb,var(--accent) {45 * (c / most) ** 2:.0f}%,transparent)"
    head = "".join(f"<th scope=\"col\">{e(n)}</th>" for n in order)
    body = ""
    for a in order:
        cells = ""
        for b in order:
            cells += ('<td class="self"></td>' if a == b else
                      f'<td style="{shade(agreed[pair(a, b)])}" title="{e(a, quote=True)} and {e(b, quote=True)}: {agreed[pair(a, b)]} of {shared[pair(a, b)]}">{agreed[pair(a, b)]}</td>'
                      if pair(a, b) in shared else "<td></td>")
        body += f'<tr><th scope="row">{e(a)}</th>{cells}</tr>'
    vote_rows = ""
    for r in votes:
        minutes = all_minutes[r["meeting_date"]]
        x = next(y for y in minutes["motions"] if y["id"] == r["motion_id"])
        day = dt.date.fromisoformat(r["meeting_date"])
        title = r["motion_name"] or r["item_title"]
        vote_rows += (f'<div class="cn-vote"><span class="when">{day:%b} {day.day}, {day.year}</span>'
                      f'<a href="minutes/{r["meeting_date"]}.html#{r["motion_id"]}">{e(title)}</a>{vote_badge(x, minutes, r["meeting_date"])}</div>')
    largest_day, largest = collections.Counter(r["meeting_date"] for r in votes).most_common(1)[0]
    busy = dt.date.fromisoformat(largest_day)
    (out / "councillors.html").write_text(page("Who votes with whom", f"""
<header class="top"><div class="eyebrow"><a href="index.html">&larr; All meetings</a></div>
<h1>Who votes with whom</h1>
<p class="lede">The thicker the line, the more often two council members voted the same way. This counts only the
{len(votes)} recorded votes that were not unanimous, from {len(all_minutes)} meetings.</p></header>
<svg class="cn-chart" viewBox="0 0 {W} {H}" role="img" aria-labelledby="cn-title">
<title id="cn-title">Circle of {len(order)} council members joined by curved lines. Line thickness shows how many contested votes each pair agreed on. The table below has every number.</title>
<g>{lines}</g><g>{hits}</g><g>{nodes}</g></svg>
<div class="cn-legend">{legend}<span>in agreement</span></div>
{panels}
<details class="more"><summary>Every pair, as a table</summary><div class="in"><div class="scroll"><table class="cn">
<thead><tr><td></td>{head}</tr></thead><tbody>{body}</tbody></table></div></div></details>
<details class="more"><summary>The {len(votes)} votes counted</summary><div class="in">{vote_rows}</div></details>
<footer>Two people agree when both vote for or both vote against, whichever side wins. A member who missed a vote is left out
of it, so pairs shared between {min(shared.values())} and {max(shared.values())} of these votes. People who often agree are placed
next to each other around the circle; the placement has no other meaning. Amendments and separate clauses each count as a vote,
so one issue can weigh heavily: {largest} of the {len(votes)} votes come from {busy:%B} {busy.day}, {busy.year}. Line thickness grows faster than the count, to make
differences easier to see. Votes come from the city's minutes.</footer>""", extra_js=CHART_JS))
    return True


def main():
    out = p.ROOT / "site.tmp"
    shutil.rmtree(out, ignore_errors=True)
    (out / "transcripts").mkdir(parents=True)
    (out / "minutes").mkdir()
    cards, stamps, all_minutes = [], {}, {}
    for d in sorted((x for x in p.RAW.iterdir() if x.is_dir()), reverse=True):
        key = d.name
        m = p.read_json(d / "meeting.json")
        sumr, minutes = p.read_json(d / "summary.json"), p.read_json(d / "minutes.json")
        if not (m and sumr and minutes):
            continue
        start = dt.datetime.strptime(m["StartDate"], "%Y/%m/%d %H:%M:%S")
        docs = {x["Title"]: x for x in m["MeetingDocumentLink"]}
        long_date = f"{start:%A, %B} {start.day}, {start.year}"
        clock = f"{start:%I:%M %p}".lstrip("0")
        official = f"{BASE}{docs['Minutes (HTML)']['Url']}"
        agenda = docs.get("Revised Agenda (HTML)") or docs.get("Agenda (HTML)")
        video = f"{BASE}/Players/ISIStandAlonePlayer.aspx?Id={m['ID']}"
        meeting_page = f"{BASE}/Meeting.aspx?Id={m['ID']}&Agenda=PostMinutes&lang=English"
        meta, segs = p.read_json(d / "transcript_meta.json"), p.read_json(d / "transcript.json")
        starts = build_transcript(out, key, sumr, m, meta, segs, docs, long_date) if meta and segs else []
        build_minutes(out, key, sumr, minutes, m, official, long_date)
        motions = {x["id"]: x for x in minutes["motions"]}

        decisions = ""
        for x in sumr["decisions"]:
            mo = motions[x["motion"]]
            t, bookmark = item_time(minutes, mo["item"], mo["item_number"])
            jumps = [f'<a href="minutes/{key}.html#{mo["id"]}">Minutes</a>']
            if t is not None and starts:
                anchor = next((s for s in starts if s >= t - 1), starts[-1])
                jumps.insert(0, f'<a href="transcripts/{key}.html#t-{anchor}">Transcript at {hms(t)}</a>')
            if bookmark:
                jumps.insert(1 if starts and t is not None else 0, f'<a href="{e(meeting_page, quote=True)}#{bookmark}">Video at {hms(t)}</a>')
            decisions += (f'<div class="decision"><div class="row"><b>{e(x["item"])}</b>{vote_badge(mo, minutes, key)}</div>'
                          f'<p>{rich(x["detail"], motions, minutes, key)}</p><div class="jump">{"".join(jumps)}</div></div>')
        debate = "".join(f"<li>{rich(b, motions, minutes, key)}</li>" for b in sumr.get("debate", []))
        overview = "".join(f"<p>{rich(t, motions, minutes, key)}</p>" for t in sumr["overview"])
        transcript_link = f'<a class="btn" href="transcripts/{key}.html">Read full transcript</a>' if starts else ""
        video_link = f'<a href="{video}">Video</a>' if m.get("HasVideo") else ""
        agenda_link = f'<a href="{BASE}{agenda["Url"]}">Agenda</a>' if agenda else ""
        cards.append(f"""
<details class="meeting" id="m-{key}">
<summary>
<div class="date"><span class="d">{start:%b} {start.day}</span><span class="y">{start.year}</span><span class="t">{clock}</span></div>
<div class="head"><h2>{e(sumr['title'])}</h2><p>{e(sumr['subtitle'])}</p></div>
<span class="chev" aria-hidden="true">&#9654;</span>
</summary>
<div class="body">
<h3>Summary</h3>{overview}
<h3>Key decisions</h3>{decisions}
{f'<h3>What the debate was about</h3><ul class="tight">{debate}</ul>' if debate else ''}
<div class="links">{transcript_link}{video_link}
<a href="minutes/{key}.html">Minutes</a>
<a href="{official}">Official minutes</a>{agenda_link}</div>
</div>
</details>""")
        stamps[key] = p.content_stamp(d)
        all_minutes[key] = minutes

    has_chart = build_councillors(out, all_minutes)
    (out / "index.html").write_text(page("Guelph City Council", f"""
<header class="top"><div class="eyebrow">Guelph, Ontario</div><h1>City Council, in brief</h1>
<p class="lede">{len(cards)} recent City Council meetings. Select one for a summary, decisions and the full transcript. Select a vote to see who voted which way.</p>
{'<a class="cn-nav" href="councillors.html">See who votes with whom &rarr;</a>' if has_chart else ''}</header>
{''.join(cards)}
<footer>Source: <a href="{BASE}">City of Guelph eSCRIBE</a>. Summaries are AI-generated from the official minutes and
transcripts of the recordings, so check the minutes before relying on them. Vote counts come directly from the minutes.</footer>"""))
    shutil.rmtree(p.SITE, ignore_errors=True)
    out.rename(p.SITE)
    p.write_json(p.STATE / "build.json", {"built_at": dt.datetime.now().isoformat(timespec="seconds"), "meetings": stamps, "fingerprint": p.site_fingerprint()})
    p.log(f"Built {len(cards)} meetings into {p.SITE}")


if __name__ == "__main__":
    main()
