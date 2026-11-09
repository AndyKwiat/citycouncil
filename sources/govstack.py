"""GovStack meeting calendars with PDF minutes: the City of Waterloo (events.waterloo.ca).

Meetings come from the calendar's search form (a POST with the page's anti-forgery token and session cookie). Minutes
are PDFs; their text is kept as minutes.txt. Votes: "Carried Unanimously" by default; a divided vote always gives a
tally and names the members in opposition, and a requested recorded vote names both sides.
"""
import datetime as dt, hashlib, html, re, time, urllib.parse
from core.common import UA, POLITE_SECONDS, log, read_json, write_json
from sources import pdf_minutes
from video import youtube

OUTCOME = re.compile(r"^(Carried Unanimously|Carried|Motion Failed|Motion Defeated|Motion failed|Motion defeated|Defeated|Lost)\s*\.?$")
TALLY = re.compile(r"^(\d+) Vot(?:ed|ing) in (Favou?r|Opposition)\s*$")
VOTER = re.compile(r"^\((MAYOR|COUNCILLOR|Mayor|Councillor)\s+([^)]+)\)\s*$")
MOVED = re.compile(r"^Moved by (?:Councillor|Council|Mayor)\s*([A-Z][\w'’-]*)?[,;:]?\s*(?:[Ss]econded by (?:Councillor|Mayor)\s*([A-Z][\w'’-]*))?")
HEADING = re.compile(r"^(\d{1,2})\.\s+([A-Z0-9][A-Z0-9 ,&'’()/:\-–.]+)$")
SUB = re.compile(r"^([a-z])\)\s+(.+)$")
WHO = r"(Mayor|Councillor)\s+((?:[A-Z][\w'’.-]*\s+){0,3}[A-Z][\w'’-]+)"
EVENT = re.compile(rf"{WHO}\s+(left|joined|rejoined|returned to) the meeting")


SMALL = {"a", "an", "and", "as", "at", "by", "for", "in", "of", "on", "or", "the", "to", "with"}


def headline(text):
    """ "DISCLOSURE OF PECUNIARY INTEREST AND THE GENERAL NATURE THEREOF" -> "Disclosure of Pecuniary Interest and the …"."""
    words = text.lower().split()
    return " ".join(w if i and w in SMALL else w[:1].upper() + w[1:] for i, w in enumerate(words))


def cfg(city):
    return city.cfg["govstack"]


def base(city):
    return cfg(city)["base"]


# ---------------------------------------------------------------- meeting list

def _session(city):
    import requests
    s = requests.Session()
    s.headers.update(UA)
    return s


def _search(s, city, token, start, end, calendar, page):
    from bs4 import BeautifulSoup
    time.sleep(POLITE_SECONDS)
    r = s.post(f"{base(city)}/meetings/Index", timeout=60, headers={"Referer": f"{base(city)}/meetings"},
               data={"__RequestVerificationToken": token, "StartDate": start, "EndDate": end, "Calendar": calendar,
                     "Keywords": "", "Page": str(page)})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    count = soup.select_one(".resultsNumber")
    total = int(re.search(r"(\d+)", count.get_text()).group(1)) if count else 0
    heads = {th.get("id"): th.get_text(strip=True) for th in soup.select("thead th")}
    rows = []
    for tr in soup.select("tbody tr"):
        tds, a = tr.select("td"), tr.select_one("td[headers=c2] a")
        if not tds or not a:
            continue
        docs = {}
        for td in tds[2:]:
            for da in td.select("a[href]"):
                docs[heads.get(" ".join(td.get("headers") or []), "doc")] = da["href"]
        rows.append({"when": tds[0].get_text(" ", strip=True), "name": a.get_text(" ", strip=True), "href": a["href"],
                     "docs": docs, "calendar": calendar})
    return total, rows


def refresh_calendar(city, start=None, end=None):
    start = dt.date.fromisoformat(start or city.get("start_date"))
    end = dt.date.fromisoformat(end) if end else dt.date.today() + dt.timedelta(days=60)
    s = _session(city)
    page = s.get(f"{base(city)}/meetings", timeout=60).text
    token = re.findall(r'name="__RequestVerificationToken" type="hidden" value="([^"]+)"', page)[0]
    fetched = []
    for year in range(start.year, end.year + 1):
        a, b = max(start, dt.date(year, 1, 1)), min(end, dt.date(year, 12, 31))
        for calendar in cfg(city)["calendars"]:
            n = 0
            while True:
                total, rows = _search(s, city, token, f"{a:%m/%d/%Y}", f"{b:%m/%d/%Y}", calendar, n)
                fetched += rows
                if not rows or (n + 1) * 25 >= total:
                    break
                n += 1
    known = {r["href"]: r for r in (read_json(city.calendar) or {"d": []})["d"]}
    before = set(known)
    known.update({r["href"]: r for r in fetched})
    write_json(city.calendar, {"d": list(known.values()), "checked_at": dt.datetime.now().isoformat(timespec="seconds")})
    new = [r for r in fetched if r["href"] not in before and city.meeting_type(r["name"])]
    log(f"Calendar {start} to {end}: {len(fetched)} meetings, {len(new)} new in scope.")


def start_of(row):
    return dt.datetime.strptime(row["when"].replace(".", "").upper(), "%B %d, %Y %I:%M %p")


def list_meetings(city):
    rows = [r for r in (read_json(city.calendar) or {"d": []})["d"]
            if city.meeting_type(r["name"]) and "CANCEL" not in r["name"].upper() and start_of(r).date().isoformat() >= city.get("start_date")]
    out, used = [], set()
    for r in sorted(rows, key=lambda r: (start_of(r), r["href"])):
        key = city.make_key(start_of(r).date().isoformat(), r["name"])
        stem, n = key, 2
        while key in used:
            key, n = f"{stem}-{n}", n + 1
        used.add(key)
        out.append(normalize(city, r, key, read_json(city.raw / key / "meeting.json")))
    return sorted(out, key=lambda m: m["start"], reverse=True)


def normalize(city, row, key, previous=None):
    t = city.meeting_type(row["name"])
    previous = previous if (previous or {}).get("version") == 2 else {}
    url = lambda p: urllib.parse.urljoin(base(city) + "/", p) if p else None
    docs = row["docs"]
    start = start_of(row)
    return {
        "version": 2, "id": row["href"].rsplit("/", 1)[-1], "city": city.slug, "key": key, "type": row["name"],
        "body": t["body"], "body_name": t["label"], "title": row["name"], "start": start.isoformat(), "end": None,
        "location": "", "links": {"official_minutes": url(docs.get("Minutes")), "minutes_pdf": url(docs.get("Minutes")),
                                  "agenda": url(docs.get("Revised Agenda") or docs.get("Agenda")),
                                  "meeting_page": url(row["href"]), "video": (previous.get("links") or {}).get("video")},
        "video": previous.get("video"), "term": city.term_for(start.date()), "minutes_posted": bool(docs.get("Minutes")),
        "source_hashes": previous.get("source_hashes", {}), "_source": row,
    }


def save_meeting(city, m):
    d = city.raw / m["key"]
    write_json(d / "source" / "meeting_source.json", m["_source"])
    write_json(d / "meeting.json", {k: v for k, v in m.items() if k != "_source"})


# ---------------------------------------------------------------- documents and video

def fetch_documents(city, m, force=False):
    import requests
    d = city.raw / m["key"]
    save_meeting(city, m)
    pdf = d / "source" / "minutes.pdf"
    if m["links"]["minutes_pdf"] and (force or not (d / "minutes.txt").exists()):
        if force or not pdf.exists():
            time.sleep(POLITE_SECONDS)
            r = requests.get(m["links"]["minutes_pdf"], headers=UA, timeout=120)
            r.raise_for_status()
            pdf.write_bytes(r.content)
            log("  downloaded minutes (PDF)")
        m["source_hashes"]["minutes.pdf"] = hashlib.sha256(pdf.read_bytes()).hexdigest()
        pdf_minutes.save_text(pdf_minutes.extract(pdf, cfg(city).get("header")), d / "minutes.txt")
    elif not m["links"]["minutes_pdf"]:
        log("  the city hasn't posted minutes yet")
    video_for(city, m, force)
    save_meeting(city, m)


def video_for(city, m, force=False):
    if m.get("video") and not force:
        return m["video"]
    found = youtube.find(city, dt.date.fromisoformat(m["start"][:10]), m["type"])
    if not found:
        log("  no video found on YouTube for this meeting")
        return None
    m["video"] = {"provider": "youtube", "parts": [youtube.part(v) for v in found]}
    m["links"]["video"] = m["video"]["parts"][0]["url"]
    log(f"  video: {len(found)} part(s) on YouTube")
    return m["video"]


# ---------------------------------------------------------------- minutes

def person(title, name, city, term):
    """ "Councillor Royce Bodaly" or "(COUNCILLOR ROACH)" -> the member's key, e.g. "Bodaly" or "Mayor McCabe"."""
    last = name.split()[-1]
    key = f"Mayor {last}" if title.lower() == "mayor" else last
    for k in city.members(term):
        if k.lower() == key.lower():
            return k
    return city.canonical(key, term)


def names_in(text, city, term):
    text = re.sub(r"\(Time:[^)]*\)", " ", text)
    return [person(t, n, city, term) for t, n in re.findall(WHO, text)]


def parse_minutes(city, d):
    if not (d / "minutes.txt").exists():
        log("  skipped parsing: no minutes yet")
        return None
    meeting = read_json(d / "meeting.json") or {}
    term = meeting.get("term")
    lines = pdf_minutes.load_text(d / "minutes.txt")
    roster, absent, present = [], [], set()
    items, motions, problems, events, conflicts, vote_notes = [], [], [], [], {}, []
    item = None
    notes = []

    def new_item(number, title):
        nonlocal item, notes
        flush_notes()
        item = {"id": number, "number": number, "title": title, "closed": False, "video_start": None, "video_end": None,
                "notes": [], "attachments": [], "motions": [], "page": page}
        items.append(item)

    def flush_notes():
        nonlocal notes
        if item is not None and notes:
            item["notes"] += [f"<p>{html.escape(p)}</p>" for p in pdf_minutes.paragraphs(notes)]
        notes = []

    i = 0
    while i < len(lines):
        page, line = lines[i]
        # Attendance blocks: PRESENT: … ABSENT: …, wrapped over lines. A second PRESENT block follows a recess.
        if line.startswith("PRESENT:") or line.startswith("ABSENT:"):
            block, j = [line], i + 1
            while j < len(lines) and not re.match(r"^(PRESENT:|ABSENT:|\d{1,2}\.\s|[A-Z][a-z]+ [A-Z][\w'’-]+ in the Chair|Councillor \w+ in the Chair|Mayor \w+ in the Chair|STAFF|ALSO PRESENT)", lines[j][1]):
                if not re.search(r"(Councillor|Mayor|p\.m\.\)|a\.m\.\)|^[A-Z][a-z]+(?: [A-Z][\w'’-]+)*,?$|^Bodaly|,$)", lines[j][1]):
                    break
                block.append(lines[j][1])
                j += 1
            text = " ".join(block)
            pres, _, absn = text.partition("ABSENT:")
            if line.startswith("ABSENT:"):
                pres, absn = "", text
            here = names_in(pres.replace("PRESENT:", ""), city, term)
            late = {person(t, n, city, term) for t, n, _ in re.findall(rf"{WHO}\s*(\(Time:[^)]*\))", pres)}
            gone = names_in(absn, city, term)
            if here:
                present = set(here) - late
            roster += [n for n in here + gone if n not in roster]
            absent += [n for n in gone if n not in absent and n not in here]
            i = j
            continue
        ev = EVENT.search(line)
        if ev:
            who = person(ev.group(1), ev.group(2), city, term)
            if ev.group(3) == "left":
                present.discard(who)
            else:
                present.add(who)
            events.append({"member": who, "event": "left" if ev.group(3) == "left" else "joined", "text": line, "page": page})
        con = re.search(rf"{WHO}\s+declared a (?:conflict|pecuniary interest)[^.]*?item\s+(\d+\s*[a-z]?)\)?", line)
        if con:
            num = con.group(3).replace(" ", "")
            conflicts.setdefault(num, set()).add(person(con.group(1), con.group(2), city, term))
        h = HEADING.match(line)
        if h and line.upper() == line:
            title = h.group(2)
            while i + 1 < len(lines) and lines[i + 1][1].isupper() and not HEADING.match(lines[i + 1][1]) and len(lines[i + 1][1]) < 60:
                i += 1
                title += " " + lines[i][1]
            new_item(h.group(1), headline(title))
            i += 1
            continue
        s = SUB.match(line)
        if s and item is not None and not MOVED.match(line):
            parent = re.match(r"\d+", item["number"]).group(0)
            title = re.sub(r"^Title:\s*", "", s.group(2))
            while i + 1 < len(lines) and not re.match(r"^(Report No|Prepared By|Moved by|[A-Z][a-z]+ [A-Z]|\d|[a-z]\))", lines[i + 1][1]) \
                    and title.startswith(("Title", s.group(2)[:6])) and s.group(2).startswith("Title:") and len(lines[i + 1][1]) < 60:
                i += 1
                title += " " + lines[i][1]
            new_item(f"{parent}{s.group(1)}", title)
            i += 1
            continue
        mv = MOVED.match(line)
        bare = OUTCOME.match(line) and item is not None  # a clause voted on under an earlier "Moved by"
        if (mv and item is not None) or bare:
            if mv:
                flush_notes()
                body, j, recorded = [line[mv.end():].strip(" :;,")], i + 1, False
                while j < len(lines) and not OUTCOME.match(lines[j][1]) and not MOVED.match(lines[j][1]) and not HEADING.match(lines[j][1]):
                    if "requested a recorded vote" in lines[j][1]:
                        recorded = True
                    else:
                        body.append(lines[j][1])
                    j += 1
                mover, seconder = mv.group(1), mv.group(2)
            else:
                # The clause's own text is what was written since the last motion or heading.
                recorded = any("requested a recorded vote" in n for n in notes)
                body = [n for n in notes if "requested a recorded vote" not in n]
                notes = []
                j, mover, seconder = i, None, None
            outcome_line = lines[j][1] if j < len(lines) and OUTCOME.match(lines[j][1]) else ""
            j += 1 if outcome_line else 0
            tally, sides, side = {}, {"for": [], "against": []}, None
            while j < len(lines):
                t, v = TALLY.match(lines[j][1]), VOTER.match(lines[j][1])
                if t:
                    side = "for" if t.group(2).startswith("Favo") else "against"
                    tally[side] = int(t.group(1))
                elif v and side:
                    sides[side].append(person(v.group(1), v.group(2).title(), city, term))
                elif lines[j][1].startswith("Council unanimously voted against"):
                    tally = {"for": 0, "against": len(present)}
                else:
                    break
                j += 1
            mid = f"m{len(motions) + 1}"
            text = " ".join(x for x in body if x)
            word = "Carried" if outcome_line.startswith("Carried") else "Defeated" if outcome_line else None
            conflicted = conflicts.get(item["number"], set()) | conflicts.get(re.match(r"\d+", item["number"]).group(0), set())
            here = sorted(present - conflicted)
            votes, recording, inferred = {"for": [], "against": [], "other": []}, "unrecorded", False
            if outcome_line.startswith("Carried Unanimously"):
                recording = "unanimous"
                result = {"text": outcome_line, "label": "Carried unanimously", "for": len(here), "against": 0, "outcome": "Carried", "inferred": True}
            elif tally:
                votes["against"] = sides["against"]
                if sides["for"]:
                    votes["for"] = sides["for"]
                else:
                    # Only the dissenters are named: everyone else present (minus declared conflicts) voted in favour.
                    votes["for"] = [n for n in here if n not in sides["against"]]
                    inferred = True
                recording = "recorded"
                a, b = tally.get("for", 0), tally.get("against", 0)
                result = {"text": f"{outcome_line} ({a} to {b})", "label": f"{a}-{b}" if word == "Carried" else f"{word} {a}-{b}",
                          "for": a, "against": b, "outcome": word, "inferred": False}
                if inferred and len(votes["for"]) != a and len(votes["against"]) == b:
                    # Someone present didn't vote (the chair, say) and the minutes don't say who: don't guess.
                    vote_notes.append(f"{mid}: tally {a}-{b}, but {len(votes['for'])} others were present; only the dissenters are listed")
                    votes["for"], inferred, recording = [], False, "dissent named"
                elif (len(votes["for"]), len(votes["against"])) != (a, b):
                    problems.append(f"{mid}: tally {a}-{b} but names give {len(votes['for'])}-{len(votes['against'])}"
                                    + (" (yes side worked out from attendance)" if inferred else ""))
            else:
                result = {"text": outcome_line, "label": outcome_line, "for": None, "against": None, "outcome": word, "inferred": False}
                if outcome_line == "Carried":
                    problems.append(f"{mid}: plain 'Carried' with no tally")
            motions.append({"id": mid, "item": item["id"], "item_number": item["number"], "item_title": item["title"], "name": "",
                            "moved_by": person("Councillor", mover, city, term) if mover else "",
                            "seconded_by": person("Councillor", seconder, city, term) if seconder else "",
                            "text": text, "text_html": "".join(f"<p>{html.escape(p)}</p>" for p in re.split(r"\s(?=\d+\.\s+That\b)", text)),
                            "post_html": "", "result": result, "votes": votes, "inherited": False, "recording": recording,
                            "for_inferred": inferred, "requested_recorded_vote": recorded, "present": here, "page": page})
            item["motions"].append(mid)
            i = j
            continue
        if item is not None and not ev:
            notes.append(line)
        i += 1
    flush_notes()
    if not roster:
        problems.append("no PRESENT block found")
    said = sum(1 for _, l in lines if OUTCOME.match(l))
    decided = sum(1 for x in motions if x["result"]["outcome"])
    if said != decided:
        problems.append(f"page has {said} outcome lines but {decided} motions with an outcome were parsed")
    for x in motions:
        unknown = [n for n in x["votes"]["for"] + x["votes"]["against"] if n not in roster]
        if unknown:
            problems.append(f"{x['id']}: names not on the roster: {', '.join(unknown)}")
    minutes = {"title": meeting.get("title", ""), "source_format": "pdf", "pages": max((p for p, _ in lines), default=0),
               "roster": roster, "absent": absent, "items": items, "motions": motions,
               "conflicts": [{"member": n, "item_number": k, "text": ""} for k, ns in conflicts.items() for n in sorted(ns)],
               "attendance_events": events, "other_vote_labels": {}, "vote_problems": problems, "vote_notes": vote_notes}
    for found, why in ((read_json(city.dir / "explained.json") or {}).get(d.name) or {}).items():
        minutes["vote_notes"] += [f"{p} (explained: {why})" for p in minutes["vote_problems"] if found in p]
        minutes["vote_problems"] = [p for p in minutes["vote_problems"] if found not in p]
    write_json(d / "minutes.json", minutes)
    for p in minutes["vote_problems"]:
        log(f"  VOTE PROBLEM: {p}")
    log(f"  parsed minutes: {len(items)} items, {len(motions)} motions, "
        f"{sum(1 for x in motions if x['votes']['against'])} split votes")
    return minutes
