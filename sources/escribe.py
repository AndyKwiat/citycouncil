"""eSCRIBE, used by Guelph, Kitchener and the Region of Waterloo: meeting list, documents, and HTML minutes.

The four adapter functions (PLAN 4.2) are list_meetings, fetch_documents, parse_minutes and video_for. Everything
after them (transcripts, summaries, votes, the site, search) works on the shared files and never on eSCRIBE fields.
"""
import datetime as dt, hashlib, json, re, urllib.error, urllib.parse
from core.common import get, log, read_json, request, write_json
from video import isilive

# Labels eSCRIBE councils put beside a list of names. A council's own labels in city.json come first.
DEFAULT_VOTE_LABELS = {
    "for": ["voting in favour", "in favour", "in favor", "voted in favour", "for"],
    "against": ["voting against", "against", "contra", "opposed", "voted in opposition", "in opposition"],
    "other": ["conflict", "absent", "abstain", "abstained"],
}
DEFAULT_ATTENDANCE = {"start": ["Council:", "Present:"], "absent": ["Absent:", "Regrets:"], "end": ["Staff:", "Also Present:"]}


def cfg(city):
    return city.cfg["escribe"]


def base(city):
    return cfg(city)["base"]


# ---------------------------------------------------------------- meeting list

def refresh_calendar(city, start=None, end=None):
    start = start or city.get("start_date")
    end = end or (dt.date.today() + dt.timedelta(days=60)).isoformat()
    body = json.dumps({"calendarStartDate": start, "calendarEndDate": end}).encode()
    with request(f"{base(city)}/MeetingsCalendarView.aspx/GetCalendarMeetings", data=body,
                 headers={"Content-Type": "application/json"}) as r:
        fetched = json.load(r)["d"]
    known = {m["ID"]: m for m in (read_json(city.calendar) or {"d": []})["d"]}
    before = {m["ID"] for m in known.values() if city.meeting_type(m["MeetingName"])}
    known.update({m["ID"]: m for m in fetched})
    write_json(city.calendar, {"d": list(known.values()), "checked_at": dt.datetime.now().isoformat(timespec="seconds")})
    wanted = [m for m in fetched if city.meeting_type(m["MeetingName"])]
    keys = {m["id"]: m["key"] for m in list_meetings(city)}
    new = [m for m in wanted if m["ID"] not in before]
    log(f"Calendar {start} to {end}: {len(fetched)} meetings of all types, {len(wanted)} in scope, {len(new)} new to us.")
    for m in new:
        log("  new:", keys.get(m["ID"], m["ID"]), m["MeetingName"], m["FormattedStart"])


def start_of(rec):
    return dt.datetime.strptime(rec["StartDate"], "%Y/%m/%d %H:%M:%S")


def list_meetings(city):
    """In-scope meetings from the cached calendar, normalized (meeting.json v2), newest first.

    Main council meetings keep the bare date as their key; other types add their slug; a second meeting that would
    still share a key gets -2."""
    recs = [m for m in (read_json(city.calendar) or {"d": []})["d"]
            if city.meeting_type(m["MeetingName"]) and m["StartDate"][:10].replace("/", "-") >= city.get("start_date", "")]
    out, used = [], set()
    for rec in sorted(recs, key=lambda m: (m["StartDate"], m["ID"])):
        key = city.make_key(start_of(rec).date().isoformat(), rec["MeetingName"])
        n = 2
        while key in used:
            key = f"{city.make_key(start_of(rec).date().isoformat(), rec['MeetingName'])}-{n}"
            n += 1
        used.add(key)
        out.append(normalize(city, rec, key, read_json(city.raw / key / "meeting.json")))
    return sorted(out, key=lambda m: m["start"], reverse=True)


def normalize(city, rec, key, previous=None):
    """The shared meeting record (PLAN 4.3). `_source` is the council's own record; it is saved separately."""
    b, mid = base(city), rec["ID"]
    t = city.meeting_type(rec["MeetingName"])
    docs = {x["Title"]: x for x in rec.get("MeetingDocumentLink", [])}
    link = lambda title: urllib.parse.urljoin(b + "/", docs[title]["Url"].lstrip("./")) if title in docs else None
    start, end = start_of(rec), dt.datetime.strptime(rec["EndDate"], "%Y/%m/%d %H:%M:%S") if rec.get("EndDate") else None
    previous = previous if (previous or {}).get("version") == 2 else {}
    video = None
    if rec.get("HasVideo"):
        video = previous.get("video") or {"provider": "isilive", "parts": [{"url": isilive.player_url(b, mid), "file": None, "hls": None, "captions": None}]}
    return {
        "version": 2, "id": mid, "city": city.slug, "key": key, "type": rec["MeetingName"],
        "body": t["body"], "body_name": t["label"], "title": rec["MeetingName"],
        "start": start.isoformat(), "end": end.isoformat() if end else None, "location": rec.get("Location") or "",
        "links": {"official_minutes": link("Minutes (HTML)"), "minutes_pdf": link("Minutes (PDF)"),
                  "agenda": link("Revised Agenda (HTML)") or link("Agenda (HTML)"),
                  "meeting_page": f"{b}/Meeting.aspx?Id={mid}&Agenda=PostMinutes&lang=English",
                  "video": isilive.player_url(b, mid) if rec.get("HasVideo") else None},
        "video": video, "term": city.term_for(start.date()), "minutes_posted": "Minutes (HTML)" in docs,
        "source_hashes": previous.get("source_hashes", {}), "_source": rec,
    }


def save_meeting(city, m):
    d = city.raw / m["key"]
    write_json(d / "source" / "meeting_source.json", m["_source"])
    write_json(d / "meeting.json", {k: v for k, v in m.items() if k != "_source"})


# ---------------------------------------------------------------- documents

def fetch_documents(city, m, force=False):
    d = city.raw / m["key"]
    save_meeting(city, m)  # first, so a folder never lacks its meeting.json even if a download fails
    links = m["links"]
    if links["official_minutes"] and (force or not (d / "minutes.html").exists()):
        body = get(links["official_minutes"])
        (d / "minutes.html").write_bytes(body)
        m["source_hashes"]["minutes.html"] = hashlib.sha256(body).hexdigest()
        log("  downloaded minutes")
    elif not links["official_minutes"]:
        log("  the city hasn't posted minutes yet")
    if links["agenda"] and (force or not (d / "agenda.html").exists()):
        (d / "agenda.html").write_bytes(get(links["agenda"]))
        log("  downloaded agenda")
    video_for(city, m, force)
    save_meeting(city, m)


def video_for(city, m, force=False):
    """Fill in the recording's file name, HLS stream and captions, and download the captions."""
    d = city.raw / m["key"]
    if not m["video"]:
        log("  no video listed for this meeting")
        return None
    part = m["video"]["parts"][0]
    if force or not part.get("file"):
        name = isilive.file_name(base(city), m["id"])
        if not name:
            log("  video player has no file name; skipping captions")
            return m["video"]
        m["video"]["parts"] = [isilive.part(base(city), cfg(city)["isi_client"], m["id"], name)]
        part = m["video"]["parts"][0]
    if force or not (d / "captions.vtt").exists():
        try:
            (d / "captions.vtt").write_bytes(get(part["captions"]))
            log("  downloaded closed captions")
        except urllib.error.HTTPError as e:
            log(f"  no closed captions available (HTTP {e.code})")
    return m["video"]


# ---------------------------------------------------------------- minutes

def surname(name):
    name = re.sub(r"\s+", " ", name).strip()
    name = re.sub(r"^(and\s+)", "", name).strip()
    mayor = name.startswith("Mayor")
    last = name.split(" ")[-1]
    return f"Mayor {last}" if mayor else last


def split_names(text):
    return [surname(n) for n in re.split(r",|\band\b", text) if n.strip()]


def parse_result(text):
    text = " ".join(text.split())
    # "Carried (8 to 5)", "(7 to 6)", or Kitchener's "Carried, on a recorded vote (7 to 4)".
    found = re.match(r"(?:(\w+)(?:,? on a recorded vote)?\s*)?\((\d+) to (\d+)\)", text)
    if found:
        word, a, b = found.groups()
        # The minutes occasionally give only a count. A majority in favour carries; anything else fails.
        inferred = not word
        word = word or ("Carried" if int(a) > int(b) else "Defeated")
        label = f"{a}-{b}" if word == "Carried" else f"{word} {a}-{b}"
        return {"text": text, "label": label, "for": int(a), "against": int(b), "outcome": word, "inferred": inferred}
    return {"text": text, "label": text, "for": None, "against": None, "outcome": text or None, "inferred": False}


def vote_side(label, city=None):
    """'for', 'against' or 'other' for a label such as "Voting in Favour: (11)" or "Contra (4)"; None if unknown."""
    plain = re.sub(r"\(\d+\)", "", label.lower()).strip(" :")
    plain = " ".join(plain.split())
    own = (cfg(city).get("vote_labels") if city else None) or {}
    for labels in (own, DEFAULT_VOTE_LABELS):
        for side in ("for", "against", "other"):
            if plain in labels.get(side, []):
                return side
    return None


def clean_rich(el, root):
    """Keep simple formatting from the city's HTML and drop everything else."""
    from bs4 import BeautifulSoup
    allowed = {"p", "ul", "ol", "li", "strong", "b", "em", "i", "br", "a", "table", "tr", "td", "th", "tbody", "thead"}
    soup = BeautifulSoup(el.decode_contents(), "html.parser")
    for tag in soup.find_all(True):
        if tag.name not in allowed:
            tag.unwrap()
            continue
        href = tag.get("href") if tag.name == "a" else None
        tag.attrs = {}
        if href:
            tag["href"] = urllib.parse.urljoin(root + "/", href)
    return str(soup).strip()


def text_of(el):
    return " ".join(el.get_text(" ", strip=True).split()) if el else ""


def parse_attendance(soup, markers=None):
    """Roster and absences from the header block of the minutes."""
    markers = markers or DEFAULT_ATTENDANCE
    text = soup.get_text("\n", strip=True)
    found = [(text.find(s), s) for s in markers["start"] if text.find(s) >= 0]
    if not found:
        return [], []
    start = min(found)[0]
    ends = [text.find(s, start) for s in markers["end"] if text.find(s, start) > 0]
    end = min(ends) if ends else start + 800
    block = text[start:end]
    cut = min((block.find(a) for a in markers["absent"] if block.find(a) >= 0), default=-1)
    present_part, absent_part = (block[:cut], block[cut:]) if cut >= 0 else (block, "")
    who = r"(Mayor|Councill?or)\s+(?:[A-Z]\.\s*)?([A-Z][A-Za-z'’-]+)"  # the minutes sometimes spell it "Councilor"
    fmt = lambda t: [f"Mayor {n}" if r == "Mayor" else n for r, n in re.findall(who, t)]
    present, absent = fmt(present_part), fmt(absent_part)
    return present + absent, absent


def parse_conflicts(soup):
    """Declared pecuniary interests written into the minutes as text."""
    out = []
    text = soup.get_text(" ", strip=True)
    for found in re.finditer(r"((?:Mayor|Councillor)\s+(?:[A-Z]\.\s*)?[A-Z][A-Za-z'’-]+)\s+declared\s+(?:an?\s+)?(?:potential\s+)?"
                             r"(?:pecuniary interest|conflict)(?:[^.]|\.(?=\d))*\.", text):
        item = re.search(r"\bitems?\s+(\d+(?:\.\d+)*)", found.group(0), re.I)
        out.append({"member": surname(found.group(1)), "item_number": item.group(1) if item else None,
                    "text": " ".join(found.group(0).split())})
    return out


def audit_votes(raw, soup, motions, roster, pattern=r"Voting in Favour"):
    """Compare what we parsed with the raw minutes, so a vote can't go missing unnoticed."""
    problems = []
    own = [x for x in motions if x["votes"]["for"] or x["votes"]["against"] or x["votes"]["other"]]
    unique = {id(x["votes"]) for x in own}
    # Votes anywhere on the page, including ones written into free text rather than the motion block.
    page = re.sub(r"<script.*?</script>", " ", raw, flags=re.S)
    in_favour = len(re.findall(pattern, page))
    if in_favour != len(unique):
        problems.append(f"page has {in_favour} '{pattern}' lists but {len(unique)} were parsed")
    results_on_page = len(re.findall(r"\(\d+\s+to\s+\d+\)", text_of(soup)))
    results_parsed = len(soup.select(".MotionResult")) and sum(1 for r in soup.select(".MotionResult") if re.search(r"\(\d+ to \d+\)", r.get_text()))
    if results_on_page != results_parsed:
        problems.append(f"page text has {results_on_page} counted results but motion blocks have {results_parsed}")
    for x in own:
        r, v = x["result"], x["votes"]
        if r["for"] is None:
            problems.append(f"{x['id']}: names recorded but the result has no count: '{r['text']}'")
        elif (r["for"], r["against"]) != (len(v["for"]), len(v["against"])):
            problems.append(f"{x['id']}: result says {r['for']}-{r['against']} but names give {len(v['for'])}-{len(v['against'])}")
        unknown = [n for n in v["for"] + v["against"] + v["other"] if n not in roster]
        if unknown:
            problems.append(f"{x['id']}: names not on the roster: {', '.join(unknown)}")
        both = set(v["for"]) & set(v["against"])
        if both:
            problems.append(f"{x['id']}: listed on both sides: {', '.join(both)}")
    for x in motions:
        # The city often gives a bare "12 to 0" on adjournments, which loses nothing. A split with no names does.
        if x["result"]["against"] and not (x["votes"]["for"] or x["votes"]["against"]):
            problems.append(f"{x['id']}: split vote {x['result']['for']}-{x['result']['against']} but no names")
    return problems


def parse_minutes(city, d):
    """Read d/minutes.html and write d/minutes.json. Returns the parsed minutes, or None when there are none yet."""
    from bs4 import BeautifulSoup
    if not (d / "minutes.html").exists():
        log("  skipped parsing: no minutes yet")
        return None
    root = base(city)
    raw = (d / "minutes.html").read_text(encoding="utf8", errors="ignore")
    bookmarks = {}
    found = re.search(r"Bookmarks\s*:\s*(\[.*?\])\s*,", raw, re.S)
    if found:
        for b in json.loads(found.group(1)):
            bookmarks.setdefault(str(b["AgendaItemId"]), []).append((b["TimeStart"] / 1000, b["TimeEnd"] / 1000))
    soup = BeautifulSoup(raw, "html.parser")
    roster, absent = parse_attendance(soup, cfg(city).get("attendance"))
    items, motions, tally_problems, other_labels = [], [], [], {}
    for it in soup.select(".AgendaItem"):
        cls = [c for c in it.get("class", []) if re.fullmatch(r"AgendaItem\d+", c)]
        item_id = cls[0][len("AgendaItem"):] if cls else None
        counter = text_of(it.select_one(".AgendaItemCounter,.ClosedAgendaItemCounter")).rstrip(".")
        title = text_of(it.select_one(".AgendaItemTitle,.ClosedAgendaItemTitle"))
        spans = bookmarks.get(item_id or "", [])
        item = {"id": item_id, "number": counter, "title": title, "closed": not item_id,
                "video_start": spans[0][0] if spans else None, "video_end": spans[-1][1] if spans else None,
                "notes": [clean_rich(n, root) for n in it.select(".AgendaItemMinutes") if text_of(n)],
                "attachments": [], "motions": []}
        for a in it.select(".AgendaItemAttachment a[href]"):
            name, href = text_of(a), a["href"]
            if name and "javascript" not in href and name not in [x["name"] for x in item["attachments"]]:
                item["attachments"].append({"name": name, "url": urllib.parse.urljoin(root + "/", href)})
        for li in it.select(".AgendaItemMotion"):
            mid = f"m{len(motions) + 1}"
            votes = {"for": [], "against": [], "other": []}
            for row in li.select(".MotionVoters tr"):
                label, names = text_of(row.select_one(".VoterVote")), row.select_one(".VotesUsers")
                if not label or not names:
                    continue
                side = vote_side(label, city)
                if side is None:
                    tally_problems.append(f"{mid}: unknown vote label '{label}' (add it to vote_labels in city.json)")
                bucket = side or "other"
                people = split_names(text_of(names))
                votes[bucket] += people
                stated = re.search(r"\((\d+)\)", label)
                if stated and int(stated.group(1)) != len(people):
                    tally_problems.append(f"{mid}: '{label.lower()}' lists {len(people)} names")
                if bucket == "other":
                    other_labels[mid] = label.lower()
            motion = {"id": mid, "item": item_id, "item_number": counter, "item_title": title,
                      "name": text_of(li.select_one(".Number .Value")),
                      "moved_by": surname(text_of(li.select_one(".MovedBy .Value"))) if li.select_one(".MovedBy .Value") else "",
                      "seconded_by": surname(text_of(li.select_one(".SecondedBy .Value"))) if li.select_one(".SecondedBy .Value") else "",
                      "text": text_of(li.select_one(".MotionText")),
                      "text_html": clean_rich(li.select_one(".MotionText"), root) if li.select_one(".MotionText") else "",
                      "post_html": clean_rich(li.select_one(".PostMotionText"), root) if text_of(li.select_one(".PostMotionText")) else "",
                      "result": parse_result(text_of(li.select_one(".MotionResult"))),
                      "votes": votes, "inherited": False}
            motions.append(motion)
            item["motions"].append(mid)
        items.append(item)
    # A consent report's items (7, 7.1, 7.2...) pass together: the city records the result on only one of them.
    for parent in items:
        if "consent" not in parent["title"].lower():
            continue
        group = [x for x in motions if x["item_number"] == parent["number"] or x["item_number"].startswith(parent["number"] + ".")]
        decided = [x for x in group if x["result"]["outcome"]]
        # Sometimes each item gets its own recorded vote; those must keep it. Fill in only motions the city left blank,
        # and only when one vote can be the one that covered them.
        for x in group:
            if x["result"]["outcome"] or re.search(r"withdrawn|out of order|referred", x["post_html"], re.I):
                continue
            own_item = [y for y in decided if y["item_number"] == x["item_number"]]
            source = own_item[0] if own_item else decided[0] if len(decided) == 1 else None
            if source:
                x["result"], x["votes"], x["inherited"] = source["result"], source["votes"], True
                source["inherited"] = source["consent_source"] = True
    # Motions that never reached a vote say why in the text after them.
    for x in motions:
        if not x["result"]["outcome"]:
            after = re.sub(r"<[^>]+>", " ", x["post_html"]).lower()
            label = "Withdrawn" if "withdrawn" in after else "Out of order" if "out of order" in after else "Referred" if "referred" in after else ""
            x["result"] = {**x["result"], "label": label, "outcome": label or None}
    for x in motions:
        v = x["votes"]
        x["recording"] = "recorded" if v["for"] or v["against"] or v["other"] else "unrecorded"
    if not roster:
        roster = sorted({n for x in motions for n in x["votes"]["for"] + x["votes"]["against"]})
    problems = tally_problems + audit_votes(raw, soup, motions, roster, cfg(city).get("audit_for_pattern", r"Voting in Favour"))
    minutes = {"title": text_of(soup.select_one("title")), "source_format": "escribe-html", "roster": roster, "absent": absent,
               "items": items, "motions": motions, "conflicts": parse_conflicts(soup), "attendance_events": [],
               "other_vote_labels": other_labels, "vote_problems": problems}
    write_json(d / "minutes.json", minutes)
    for problem in problems:
        log(f"  VOTE PROBLEM: {problem}")
    voted = sum(1 for x in motions if x["result"]["for"] is not None)
    log(f"  parsed minutes: {len(items)} items, {len(motions)} motions, {voted} recorded votes, "
        f"{sum(1 for i in items if i['video_start'] is not None)} items with video bookmarks")
    return minutes
