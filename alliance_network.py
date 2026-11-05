"""The Voting Alliance Network section of the councillors page: data, markup and styles.

The interactive behaviour lives in alliance_network.js. To add another visualization, follow the same shape:
a section(...) function returning HTML, with its script handed to build.page().
"""
import html, itertools, json, pathlib
import analysis

e = html.escape
SCRIPT = (pathlib.Path(__file__).resolve().parent / "alliance_network.js").read_text()
BRIDGE_GAP = 0.10  # within 10 points of their own community's agreement, someone is about as close to the others

EXPLANATION = ("Councillors are connected based on how frequently they voted the same way on votes both attended. "
               "Thicker lines indicate stronger agreement, while colours represent groups identified through voting-pattern "
               "analysis. These groups reflect observed voting similarities, not necessarily political affiliations.")

CSS = """
.net{margin-top:8px}.net-explain{color:var(--muted);margin:0 0 14px;max-width:68ch}
.net-controls{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center;background:var(--panel);border:1px solid var(--line);border-radius:10px 10px 0 0;border-bottom:0;padding:12px 14px;font-size:14px}
.net-controls label{display:inline-flex;align-items:center;gap:7px}
.net-controls input[type=range]{width:150px;accent-color:var(--accent)}.net-controls select{font:inherit;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:3px 6px;max-width:190px}
.net-controls .val{font-variant-numeric:tabular-nums;font-weight:600;min-width:3ch}
.net-stage{position:relative;background:var(--panel);border:1px solid var(--line);overflow:hidden}
.net-svg{display:block;width:100%;height:auto;touch-action:pan-y;cursor:grab;user-select:none;-webkit-user-select:none}.net-svg.panning{cursor:grabbing}
.net-svg .ne{stroke:var(--ink);stroke-linecap:round;transition:opacity .18s,stroke .18s;pointer-events:none}
.net-svg .ne.off,.net-svg.sel .ne.off.off{opacity:0!important}.net-svg .ne.hot{stroke:var(--accent);opacity:1!important}
.net-svg .nh{stroke:transparent;stroke-width:12;cursor:pointer}.net-svg .nh.off{pointer-events:none}
.net-svg.sel .ne:not(.on){opacity:.05!important}.net-svg.sel .ne.on{opacity:.75!important}.net-svg.sel .ne.top{stroke:var(--accent);opacity:1!important}
.net-svg.sel .nh:not(.on){pointer-events:none}
.nn{cursor:pointer;outline:none;transition:opacity .18s;touch-action:none}.nn .disc{stroke:var(--panel);stroke-width:3;transition:r .18s;fill:var(--muted)}
.nn.c0 .disc{fill:var(--g0)}.nn.c1 .disc{fill:var(--g1)}.nn.c2 .disc{fill:var(--g2)}.net-svg.plain .nn .disc{fill:var(--muted)}
.nn.face .disc,.net-svg.plain .nn.face .disc{fill:var(--panel);stroke-width:5;stroke:var(--muted)}.nn.face.c0 .disc{stroke:var(--g0)}.nn.face.c1 .disc{stroke:var(--g1)}.nn.face.c2 .disc{stroke:var(--g2)}.net-svg.plain .nn.face .disc{stroke:var(--muted)}
.nn .ini{fill:#fff;font:700 15px var(--sans);text-anchor:middle;dominant-baseline:central;pointer-events:none}
.nn.c2 .ini{fill:var(--g2-ink)}.net-svg.plain .nn .ini{fill:var(--bg)}
.nn .nm{fill:var(--ink);font:500 13px var(--sans);text-anchor:middle;pointer-events:none;paint-order:stroke;stroke:var(--panel);stroke-width:3px}
.nn .mayor{fill:none;stroke:var(--ink);stroke-width:2}.nn image{pointer-events:none}
.nn.sel .disc,.nn:focus-visible .disc,.nn.face.sel .disc,.nn.face:focus-visible .disc{stroke:var(--ink);stroke-width:7}
.net-svg.sel .nn:not(.sel):not(.near){opacity:.45}
.net-tip{position:absolute;left:10px;bottom:10px;max-width:min(330px,calc(100% - 20px));background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:6px 10px;font-size:13.5px;line-height:1.4;pointer-events:none}
.net-tip[hidden]{display:none}.net-tip span{display:block;color:var(--muted);font-size:13px}
.net-tools{display:flex;flex-wrap:wrap;gap:6px;align-items:center;background:var(--panel);border:1px solid var(--line);border-top:0;border-radius:0 0 10px 10px;padding:9px 14px;font-size:13.5px}
.net-tools button{font:inherit;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:3px 10px;cursor:pointer}.net-tools button:hover{border-color:var(--accent)}.net-tools button[aria-pressed=true]{background:var(--accent-soft);border-color:var(--accent)}
.net-tools .sp{flex:1}.net-tools .net-note{color:var(--muted)}
.net-legend{display:flex;flex-wrap:wrap;gap:6px 18px;align-items:center;font-size:13.5px;color:var(--muted);margin:12px 0}
.net-legend span{display:inline-flex;align-items:center;gap:6px}.net-legend i{display:inline-block;flex:none}
.net-legend .dot{width:13px;height:13px;border-radius:50%;background:var(--muted)}.net-legend .dot.c0{background:var(--g0)}.net-legend .dot.c1{background:var(--g1)}.net-legend .dot.c2{background:var(--g2)}
.net-legend .ring{width:15px;height:15px;border-radius:50%;border:2px solid var(--ink)}.net-legend .ln{width:26px;background:var(--ink);border-radius:4px}
.net-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:12px 0}
.net-stat{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 14px}.net-stat b{display:block;font-size:20px;font-weight:600;line-height:1.3}.net-stat span{color:var(--muted);font-size:13px;line-height:1.35;display:block}
.net-side{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin-top:12px}
.net-side h3{font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:0 0 8px;font-weight:600}
.net-side .who{display:flex;gap:12px;align-items:center;margin-bottom:10px}.net-side .who img{width:52px;height:52px;border-radius:50%;flex:none}.net-side .who h4{font:600 20px/1.3 var(--serif);margin:0}
.net-side .who p{margin:0;color:var(--muted);font-size:14px}
.net-facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px 18px;margin:0 0 14px;font-size:14px}.net-facts b{display:block;font-size:17px;font-weight:600}.net-facts span{color:var(--muted);font-size:13px}
.net-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;font-size:14.5px;padding:2px 0}.net-row .num{color:var(--muted);font-variant-numeric:tabular-nums;white-space:nowrap;font-size:13.5px}
.net-cols{display:grid;grid-template-columns:1fr 1fr;gap:14px 28px}.net-side details{margin-top:12px;font-size:14.5px}.net-side summary{display:block;padding:0;cursor:pointer;font-weight:600;color:var(--accent)}
@media (max-width:560px){.net-cols{grid-template-columns:1fr}.nn .ini{font-size:17px}.nn .nm{font-size:17px}.net-controls input[type=range]{width:120px}}
"""


def initials(name):
    return "".join(w[0] for w in name.replace("Mayor ", "").replace("'", "").split()).upper()[:3]


def network_data(names, agreed, shared, full, photo, ward, communities, positions):
    """One edge per pair, no self-links. A pair who never voted together has no edge at all: unknown, not 0%."""
    edges = [{"a": a, "b": b, "agreed": agreed[a, b], "shared": shared[a, b], "pct": 100 * agreed[a, b] / shared[a, b]}
             for a, b in itertools.combinations(sorted(names), 2) if shared.get((a, b))]
    unknown = [[a, b] for a, b in itertools.combinations(sorted(names), 2) if not shared.get((a, b))]
    member = communities["members"]
    nodes = []
    for n in sorted(names):
        mine = [x for x in edges if n in (x["a"], x["b"])]
        other = lambda x: x["b"] if x["a"] == n else x["a"]
        inside = [x["pct"] for x in mine if member[other(x)] == member[n]]
        outside = [x["pct"] for x in mine if member[other(x)] != member[n]]
        within, across = (sum(v) / len(v) if v else None for v in (inside, outside))
        x, y = positions.get(n, (0, 0))
        nodes.append({"id": n, "name": full(n), "initials": initials(full(n)), "surname": full(n).rsplit(" ", 1)[-1], "ward": ward(n),
                      "photo": photo(n), "mayor": n.startswith("Mayor"), "community": member[n], "x": x, "y": y,
                      "average": sum(x["pct"] for x in mine) / len(mine) if mine else None, "comparisons": len(mine),
                      "within": within, "across": across,
                      "bridge": bool(within is not None and across is not None and within - across < 100 * BRIDGE_GAP),
                      "stays": communities.get("stays_with_community", {}).get(n)})
    return {"nodes": nodes, "edges": edges, "unknown": unknown, "communities": communities["count"],
            "average": 100 * communities["average_agreement"]}


def section(votes, names, agreed, shared, full, photo, ward, positions):
    """Returns (html, communities) for the network section."""
    c = analysis.communities(names, agreed, shared, votes)
    data = network_data(names, agreed, shared, full, photo, ward, c, positions)
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    runs = c.get("resamples_count", {})
    held = runs.get(str(c["count"]), 0) / max(c.get("resamples", 1), 1)
    html_out = f"""
<section class="net" id="alliance-network" aria-label="Voting Alliance Network">
<h2 class="sec" style="margin-top:0">Voting Alliance Network</h2>
<p class="net-explain">{e(EXPLANATION)}</p>
<div class="net-controls">
 <label>Show agreement of at least <input type="range" id="net-threshold" min="0" max="100" step="1" value="75"><span class="val" id="net-threshold-val">75%</span></label>
 <label>Councillor <select id="net-select"><option value="">Choose…</option></select></label>
 <label>Node size <select id="net-size"><option value="uniform">Uniform</option><option value="average">Average agreement</option><option value="connectivity">Weighted connectivity</option></select></label>
 <label><input type="checkbox" id="net-colour" checked> Community colours</label>
</div>
<div class="net-stage"><svg class="net-svg" id="net-svg" role="group" aria-label="Network of council members. Lines join pairs by how often they agree. The table further down this page has every number."></svg><div class="net-tip" id="net-tip" hidden></div></div>
<div class="net-tools">
 <button type="button" id="net-in" aria-label="Zoom in">+</button><button type="button" id="net-out" aria-label="Zoom out">−</button>
 <button type="button" id="net-reset">Reset view</button><button type="button" id="net-freeze" aria-pressed="false">Freeze layout</button>
 <span class="net-note" id="net-count"></span><span class="sp"></span>
 <button type="button" id="net-png">PNG</button><button type="button" id="net-svgdl">SVG</button><button type="button" id="net-csv">CSV</button>
</div>
<div class="net-legend" id="net-legend"></div>
<div class="net-stats" id="net-stats"></div>
<div class="net-side" id="net-side" aria-live="polite"></div>
<details class="more"><summary>How this network is built</summary><div class="in">
<p><b>Lines and percentages</b> come straight from the votes: of the {len(votes)} non-unanimous recorded votes, the share both people attended on which they voted the same way. Pairs who never voted together have no line, because that is unknown rather than 0%.</p>
<p><b>Positions:</b> every known pair pulls toward a distance set by its agreement, including pairs below the slider, so moving the slider never rearranges the network. Layout starts from fixed positions, so it comes out the same on every visit.</p>
<p><b>Communities</b> use the Louvain method on the full network, whatever the slider says. On average, any two members here agree {c['average_agreement']:.0%} of the time, and with raw percentages those moderate links would blur everything into one group. So only agreement above that average counts as a link, and an unknown pair counts as no evidence either way. Modularity is {c['modularity']:.2f}, where 0 means no community structure, so these communities are real but overlapping.</p>
<p><b>How firm they are:</b> on {c.get('resamples', 0)} random resamples of the votes, {c['count']} communities came out {held:.0%} of the time. Each person's detail panel shows how often they stayed with their community. <b>Bridging</b> marks someone whose average agreement within their community is less than {100 * BRIDGE_GAP:.0f} points above their average with everyone else; that cutoff is a judgement call.</p>
<p>These communities can differ from the voting groups further down the page, which use a different method. Comparing the two shows which memberships are firm: people in the same group under both are the most consistent allies.</p>
</div></details>
<script type="application/json" id="net-data">{payload}</script>
</section>
<style>{CSS}</style>"""
    return html_out, c
