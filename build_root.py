"""The site's root: the landing page at /, search across every council at /search.html, and _redirects."""
import datetime as dt, html
import build
import search_page
from core import city as cities

e = html.escape


def card(b):
    image = f'<img src="{b["slug"]}/theme/card.jpg" alt="" loading="lazy">' if b.get("themed") else ""
    latest = b.get("latest")
    when = ""
    if latest:
        day = dt.date.fromisoformat(latest["date"])
        when = f'Latest: {day:%B} {day.day}, {day.year}, <span class="mt">{e(latest["title"])}</span>.'
    count = b.get("count", 0)
    return (f'<a class="council" href="{b["slug"]}/">{image}<div><h2>{e(b["name"])}</h2>'
            f'<p>{e(b["council"])}. {count} meeting{"s" if count != 1 else ""} summarized. {when}</p></div></a>')


def write(out, built):
    """built: what build.build_city returned for each council, keyed by slug."""
    shown = [built[s] for s in cities.all_slugs() if s in built and built[s].get("count")]
    years = sorted({y for b in shown if b.get("first") for y in range(int(b["first"][:4]), dt.date.today().year + 1)})
    many = len(shown) > 1
    (out / "index.html").write_text(build.page("cityhallvotes.ca: council votes and meetings", f"""
<header class="top"><div class="eyebrow">Ontario council meetings, in brief</div><h1>City Hall Votes</h1>
<p class="lede">Summaries of council and committee meetings, how each member voted, and searchable transcripts{' for ' + str(len(shown)) + ' councils' if many else ''}.
Pick a council, or search {'all of them' if many else 'its records'} at once.</p>
{search_page.mini_form(placeholder="Search every council's votes, minutes and transcripts")}</header>
<div class="councils">{"".join(card(b) for b in shown)}</div>""", script=False))
    (out / "search.html").write_text(build.page("Search every council", search_page.page_body([str(y) for y in years]),
                                                 extra_js=search_page.script()))
    # Cloudflare serves this file as rules; old links to a town's name go to the council that covers it.
    rules = []
    for slug in cities.all_slugs():
        if slug in built:
            for alias in cities.load(slug).get("redirect_from", []):
                rules += [f"/{alias} /{slug}/ 301", f"/{alias}/ /{slug}/ 301", f"/{alias}/* /{slug}/:splat 301"]
    (out / "_redirects").write_text("".join(r + "\n" for r in rules))
