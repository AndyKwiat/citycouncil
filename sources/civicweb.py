"""CivicWeb (iCompass) portals with PDF minutes: the Township of Centre Wellington (Fergus and Elora).

Meetings come from the portal's meeting list per type; each meeting's published minutes are its DocumentType 10
document, and /api/videolink/{id} names its YouTube stream. Motions read "Moved by Councillor X, Seconded by
Councillor Y. THAT … CARRIED"; a recorded vote, when a member asks for one, lists "Councillor X For/Against".
"""
import datetime as dt, hashlib, html, json, re, time, urllib.parse
from core.common import UA, POLITE_SECONDS, log, read_json, write_json
from sources import pdf_minutes
from video import youtube

OUTCOME = re.compile(r"^(CARRIED|DEFEATED|LOST|WITHDRAWN|TIED|CARRIED, as amended|CARRIED AS AMENDED|DEFERRED|REFERRED)\b(.*)$")
VOTE_LINE = re.compile(r"^(Mayor|Councill?or)\s+(.+?)\s+(For|Against|Abstained|Yea|Nay)$")
NAME_WORD = r"(?!(?:Mayor|Councill?or|Seconded|Moved|THAT)\b)[A-Z][\w'’.-]*"
WHO = rf"(Mayor|Councill?or)\s+((?:{NAME_WORD}\s+){{0,3}}{NAME_WORD}(?:-\s?[A-Z][\w'’-]+)?)"
EVENT = re.compile(rf"{WHO}\s+(left|joined|rejoined|returned to) the meeting")
ITEM = re.compile(r"^(\d{1,2})(?:\.(\d{1,2}))?\.?\s+(\S.*)$")


def cfg(city):
    return city.cfg["civicweb"]


def base(city):
    return cfg(city)["base"]


# ---------------------------------------------------------------- meeting list

def _get(url, **kw):
    import requests
    time.sleep(POLITE_SECONDS)
    r = requests.get(url, headers=UA, timeout=60, **kw)
    r.raise_for_status()
    return r


def refresh_calendar(city, start=None, end=None):
    """Meetings of each in-scope type from the portal, then each new meeting's minutes document and video."""
    known = {str(r["id"]): r for r in (read_json(city.calendar) or {"d": []})["d"]}
    start = start or city.get("start_date")
    added = 0
    for type_id in cfg(city)["types"]:
        page = _get(f"{base(city)}/Portal/MeetingInformation.aspx?type={type_id}").text
        for mid, day, name in re.findall(r'MeetingButton(\d+)".*?meeting-list-item-button-date">([^<]+)<.*?title="([^"]*)"', page, re.S):
            date = dt.datetime.strptime(day.strip(), "%d %b %Y").date().isoformat()
            if date < start:
                continue
            row = known.setdefault(mid, {"id": int(mid), "date": date, "name": name.strip(), "type": type_id})
            row.update(date=date, name=name.strip())
            if "minutes_doc" not in row or not row.get("minutes_doc"):
                docs = _get(f"{base(city)}/Services/MeetingsService.svc/meetings/{mid}/meetingDocuments").json()
                row["minutes_doc"] = next((d["Id"] for d in docs if d.get("DocumentType") == 10 and d.get("IsPublic", True)), None)
                added += 1
            if "youtube" not in row:
                try:
                    links = _get(f"{base(city)}/api/videolink/{mid}").json()
                    row["youtube"] = [l["YouTubeEventId"] for l in links if l.get("YouTube") and l.get("YouTubeEventId")]
                except Exception:
                    row["youtube"] = []
    write_json(city.calendar, {"d": list(known.values()), "checked_at": dt.datetime.now().isoformat(timespec="seconds")})
    log(f"Calendar: {len(known)} meetings known, {added} checked for minutes.")


def meeting_type(city, row):
    """CivicWeb's names carry the date ("Council - 24 Aug 2026"); match on the part before it."""
    name = re.split(r"\s+-\s+\d", row["name"])[0].strip()
    return name, city.meeting_type(name)


def list_meetings(city):
    rows = [r for r in (read_json(city.calendar) or {"d": []})["d"] if meeting_type(city, r)[1] and r["date"] >= city.get("start_date")]
    out, used = [], set()
    for r in sorted(rows, key=lambda r: (r["date"], r["id"])):
        name, _ = meeting_type(city, r)
        key = city.make_key(r["date"], name)
        stem, n = key, 2
        while key in used:
            key, n = f"{stem}-{n}", n + 1
        used.add(key)
        out.append(normalize(city, r, key, read_json(city.raw / key / "meeting.json")))
    return sorted(out, key=lambda m: m["start"], reverse=True)


def normalize(city, row, key, previous=None):
    name, t = meeting_type(city, row)
    previous = previous if (previous or {}).get("version") == 2 else {}
    doc = row.get("minutes_doc")
    start = dt.datetime.fromisoformat(row["date"] + "T" + row.get("time", "17:00"))
    return {
        "version": 2, "id": str(row["id"]), "city": city.slug, "key": key, "type": name, "body": t["body"], "body_name": t["label"],
        "title": row["name"], "start": start.isoformat(), "end": None, "location": "",
        "links": {"official_minutes": f"{base(city)}/document/{doc}" if doc else None, "minutes_pdf": f"{base(city)}/document/{doc}" if doc else None,
                  "agenda": None, "meeting_page": f"{base(city)}/Portal/MeetingInformation.aspx?Id={row['id']}",
                  "video": (previous.get("links") or {}).get("video")},
        "video": previous.get("video"), "term": city.term_for(start.date()), "minutes_posted": bool(doc),
        "source_hashes": previous.get("source_hashes", {}), "_source": row,
    }


def save_meeting(city, m):
    d = city.raw / m["key"]
    write_json(d / "source" / "meeting_source.json", m["_source"])
    write_json(d / "meeting.json", {k: v for k, v in m.items() if k != "_source"})


# ---------------------------------------------------------------- documents and video

def fetch_documents(city, m, force=False):
    d = city.raw / m["key"]
    save_meeting(city, m)
    pdf = d / "source" / "minutes.pdf"
    if m["links"]["minutes_pdf"] and (force or not (d / "minutes.txt").exists()):
        if force or not pdf.exists():
            pdf.parent.mkdir(parents=True, exist_ok=True)
            pdf.write_bytes(_get(m["links"]["minutes_pdf"]).content)
            log("  downloaded minutes (PDF)")
        m["source_hashes"]["minutes.pdf"] = hashlib.sha256(pdf.read_bytes()).hexdigest()
        pdf_minutes.save_text(pdf_minutes.extract(pdf, cfg(city).get("header")), d / "minutes.txt")
    elif not m["links"]["minutes_pdf"]:
        log("  the township hasn't posted minutes yet")
    video_for(city, m, force)
    save_meeting(city, m)


def video_for(city, m, force=False):
    if m.get("video") and not force:
        return m["video"]
    ids = m["_source"].get("youtube") or []
    by_id = {v["id"]: v for v in youtube.listing(city)}
    if ids:
        found = [by_id.get(i, {"id": i, "title": "", "duration": None}) for i in ids]
    else:
        found = youtube.find(city, dt.date.fromisoformat(m["start"][:10]), m["type"])
    if not found:
        log("  no video for this meeting")
        return None
    m["video"] = {"provider": "youtube", "parts": [youtube.part(v) for v in sorted(found, key=lambda v: youtube.order_key(v["title"]))]}
    m["links"]["video"] = m["video"]["parts"][0]["url"]
    return m["video"]


# ---------------------------------------------------------------- minutes

def person(title, name, city, term):
    """ "Councillor Barbara Lustgarten-Evoy", "Councillor Wilton", "Mayor Shawn Watters" -> the member's key."""
    name = re.sub(r"-\s+", "-", name.strip()).rstrip(".,;:")
    last = name.split()[-1]
    key = f"Mayor {last}" if title.lower() == "mayor" else last
    members = city.members(term)
    for k, info in members.items():
        if k.lower() == key.lower() or key in info.get("aliases", []):
            return k
    # The mayor is sometimes named by surname alone after a role change; match any member by surname.
    for k in members:
        if k.split()[-1].lower() == last.lower():
            return k
    return key


def names_block(lines, city, term):
    return [person(t, n, city, term) for t, n in re.findall(WHO, ", ".join(lines))]


def heading(line, top):
    """An agenda item heading ("4. Disclosure …" or "3.1 Addition:"), not a numbered line inside a motion."""
    it = ITEM.match(line)
    if not it or line.startswith(("Moved", "THAT")) or it.group(3).startswith(("Moved by", "THAT", "AND THAT", "That")):
        return None
    n, sub = int(it.group(1)), it.group(2)
    if (sub is None and n in (top + 1, top + 2) and it.group(3)[:1].isupper()) or (sub is not None and n == top):
        return n, sub, it.group(3)
    return None


def parse_minutes(city, d):
    if not (d / "minutes.txt").exists():
        log("  skipped parsing: no minutes yet")
        return None
    meeting = read_json(d / "meeting.json") or {}
    term = meeting.get("term")
    lines = pdf_minutes.load_text(d / "minutes.txt")
    roster, absent, items, motions, problems, notes_out, events, conflicts = [], [], [], [], [], [], [], {}
    present = set()
    item, notes, top = None, [], 0

    def flush():
        nonlocal notes
        if item is not None and notes:
            item["notes"] += [f"<p>{html.escape(p)}</p>" for p in pdf_minutes.paragraphs(notes)]
        notes = []

    # Attendance: PRESENT: … REGRETS: … STAFF:, one member a line.
    texts = [l for _, l in lines]
    if "PRESENT:" in " ".join(texts[:40]):
        i = next(k for k, l in enumerate(texts) if l.startswith("PRESENT:"))
        block, section = {"present": [], "absent": []}, "present"
        for l in texts[i:i + 40]:
            if l.startswith("STAFF") or heading(l, 0):
                break
            if l.startswith(("REGRETS", "ABSENT")):
                section = "absent"
            block[section].append(l)
        here, gone = names_block(block["present"], city, term), names_block(block["absent"], city, term)
        roster, absent, present = here + [n for n in gone if n not in here], gone, set(here)
    else:
        problems.append("no PRESENT block found")

    i = 0
    pending_votes = []
    while i < len(texts):
        page, line = lines[i]
        ev = EVENT.search(line)
        if ev:
            who = person(ev.group(1), ev.group(2), city, term)
            (present.discard if ev.group(3) == "left" else present.add)(who)
            events.append({"member": who, "event": "left" if ev.group(3) == "left" else "joined", "text": line, "page": page})
        con = re.search(rf"{WHO}\s+declared a (?:conflict|pecuniary interest)[^.]*?items?\s+([\d.]+)", line)
        if con:
            conflicts.setdefault(con.group(3).rstrip("."), set()).add(person(con.group(1), con.group(2), city, term))
        h = heading(line, top)
        if h:
            n, sub, title = h
            if True:
                if sub is None:
                    top = n
                flush()
                number = f"{n}.{sub}" if sub else str(n)
                mv_inline = title.startswith("Moved by")
                item = {"id": number, "number": number, "title": title.rstrip(":"), "closed": False, "video_start": None,
                        "video_end": None, "notes": [], "attachments": [], "motions": [], "page": page}
                items.append(item)
                i += 1
                continue
        # "5.1 Moved by …" (or "6.4" alone on its line, then "Moved by …") starts a motion under that item number.
        if re.match(r"^\d{1,2}\.\d{1,2}$", line) and i + 1 < len(texts) and texts[i + 1].startswith("Moved by"):
            i += 1
            line = f"{line} {texts[i]}"
            page = lines[i][0]
        inline = re.match(r"^(\d{1,2}\.\d{1,2})\s+(Moved by .*)$", line)
        if inline:
            number = inline.group(1)
            if not item or item["number"] != number:
                carry = [n for n in notes[-3:] if re.search(r"(requested|asked for|called for) a recorded vote", n, re.I)]
                notes = [n for n in notes if n not in carry]
                flush()
                notes = carry
                item = {"id": number, "number": number, "title": item["title"] if item else "", "closed": False, "video_start": None,
                        "video_end": None, "notes": [], "attachments": [], "motions": [], "page": page}
                items.append(item)
            line = inline.group(2)
        if line.startswith("Moved by") and item is not None:
            # The request for a recorded vote usually comes just before the motion.
            asked = [n for n in notes[-3:] if re.search(r"(requested|asked for|called for) a recorded vote", n, re.I)]
            notes = [n for n in notes if n not in asked]
            flush()
            head = line
            j = i + 1
            while not re.search(r"\.\s*$", head) and j < len(texts) and len(head) < 220 and not texts[j].startswith(("THAT", "AND THAT", "That")):
                head += " " + texts[j]
                j += 1
            movers = [person(t, n, city, term) for t, n in re.findall(WHO, head)]
            body, votes_lines, recorded = [], [], bool(asked)
            def ends_motion(k):
                """A heading-like line ends a motion only if the next "Moved by" comes before the next outcome line;
                otherwise it is part of the motion (consent agenda items, numbered lists)."""
                if not heading(texts[k], top):
                    return False
                outcome_at = next((x for x in range(k, len(texts)) if OUTCOME.match(texts[x])), len(texts))
                moved_at = next((x for x in range(k, len(texts)) if re.match(r"^(\d{1,2}\.\d{1,2}\s+)?Moved by", texts[x])), len(texts))
                return moved_at < outcome_at
            while j < len(texts) and not OUTCOME.match(texts[j]) and not texts[j].startswith("Moved by") and not ends_motion(j) \
                    and not re.match(r"^\d{1,2}\.\d{1,2}\s+Moved by", texts[j]) \
                    and not (re.match(r"^\d{1,2}\.\d{1,2}$", texts[j]) and j + 1 < len(texts) and texts[j + 1].startswith("Moved by")):
                if re.search(r"(requested|asked for|called for) a recorded vote", texts[j], re.I):
                    recorded = True
                elif VOTE_LINE.match(texts[j]) or (votes_lines and re.match(r"^[A-Z][a-z]+$", texts[j])):
                    votes_lines.append(texts[j])
                else:
                    body.append(texts[j])
                j += 1
            outcome = texts[j] if j < len(texts) and OUTCOME.match(texts[j]) else ""
            j += 1 if outcome else 0
            while j < len(texts) and (VOTE_LINE.match(texts[j]) or (votes_lines and re.match(r"^[A-Z][a-z]+$", texts[j]) and VOTE_LINE.match(texts[j - 1]))
                                     or re.match(r"^(Mayor|Councill?or)\s+[A-Z][\w'’ -]+$", texts[j]) and recorded):
                votes_lines.append(texts[j])
                j += 1
            if votes_lines and j < len(texts) and OUTCOME.match(texts[j]) and "Recorded Vote" in texts[j]:
                outcome = texts[j]
                j += 1
            pending_votes = []
            sides = {"for": [], "against": [], "other": []}
            for k, vl in enumerate(votes_lines):
                vm = VOTE_LINE.match(vl)
                if not vm:
                    continue
                name = vm.group(2)
                if name.endswith("-") and k + 1 < len(votes_lines) and not VOTE_LINE.match(votes_lines[k + 1]):
                    name += votes_lines[k + 1]
                side = {"For": "for", "Yea": "for", "Against": "against", "Nay": "against"}.get(vm.group(3), "other")
                sides[side].append(person(vm.group(1), name, city, term))
            word = outcome.split(",")[0].split()[0].capitalize() if outcome else None
            word = {"Lost": "Defeated"}.get(word, word)
            stated = re.search(r"(\d+)\s*-\s*(\d+)", outcome)
            if sides["for"] or sides["against"]:
                a, b = len(sides["for"]), len(sides["against"])
                result = {"text": outcome, "label": f"{a}-{b}" if word == "Carried" else f"{word} {a}-{b}", "for": a, "against": b,
                          "outcome": word, "inferred": False}
                if stated and (int(stated.group(1)), int(stated.group(2))) != (a, b):
                    problems.append(f"m{len(motions) + 1}: minutes say {stated.group(0)} but names give {a}-{b}")
                recording = "recorded"
            else:
                label = outcome.capitalize() if outcome else ""
                result = {"text": outcome, "label": label.replace("Carried, as amended", "Carried as amended"), "for": None, "against": None,
                          "outcome": word, "inferred": False}
                recording = "unrecorded"
                if recorded:
                    problems.append(f"m{len(motions) + 1}: a recorded vote was requested but no votes were found")
            mid = f"m{len(motions) + 1}"
            text = " ".join(body)
            motions.append({"id": mid, "item": item["id"], "item_number": item["number"], "item_title": item["title"], "name": "",
                            "moved_by": movers[0] if movers else "", "seconded_by": movers[1] if len(movers) > 1 else "",
                            "text": text, "text_html": "".join(f"<p>{html.escape(p)}</p>" for p in re.split(r"\s(?=\([a-z]\)\s)", text)),
                            "post_html": "", "result": result, "votes": sides, "inherited": False, "recording": recording,
                            "requested_recorded_vote": recorded, "present": sorted(present), "page": page})
            item["motions"].append(mid)
            i = j
            continue
        bare = OUTCOME.match(line)
        if bare and item is not None:
            # An outcome with no "Moved by" before it: the motion is the text since the last one.
            start = max((k for k, n in enumerate(notes) if n.startswith(("THAT", "That", "WHEREAS"))), default=0)
            text, notes = " ".join(notes[start:]), notes[:start]
            flush()
            word = {"Lost": "Defeated"}.get(line.split(",")[0].split()[0].capitalize(), line.split(",")[0].split()[0].capitalize())
            mid = f"m{len(motions) + 1}"
            motions.append({"id": mid, "item": item["id"], "item_number": item["number"], "item_title": item["title"], "name": "",
                            "moved_by": "", "seconded_by": "", "text": text, "text_html": f"<p>{html.escape(text)}</p>" if text else "",
                            "post_html": "", "result": {"text": line, "label": line.capitalize(), "for": None, "against": None,
                                                        "outcome": word, "inferred": False},
                            "votes": {"for": [], "against": [], "other": []}, "inherited": False, "recording": "unrecorded",
                            "requested_recorded_vote": False, "present": sorted(present), "page": page})
            item["motions"].append(mid)
            i += 1
            continue
        if item is not None and not ev:
            notes.append(line)
        i += 1
    flush()
    said = sum(1 for l in texts if OUTCOME.match(l))
    decided = sum(1 for x in motions if x["result"]["outcome"])
    if said != decided:
        problems.append(f"page has {said} outcome lines but {decided} motions with an outcome were parsed")
    for x in motions:
        unknown = [n for n in x["votes"]["for"] + x["votes"]["against"] if n not in roster]
        if unknown:
            problems.append(f"{x['id']}: names not on the roster: {', '.join(unknown)}")
    said_rec = sum(1 for l in texts if re.search(r"(requested|asked for|called for) a recorded vote", l, re.I))
    got_rec = sum(1 for x in motions if x["requested_recorded_vote"])
    if said_rec != got_rec:
        problems.append(f"page asks for {said_rec} recorded votes but {got_rec} were found with motions")
    minutes = {"title": meeting.get("title", ""), "source_format": "pdf", "pages": max((p for p, _ in lines), default=0),
               "roster": roster, "absent": absent, "items": items, "motions": motions,
               "conflicts": [{"member": n, "item_number": k, "text": ""} for k, ns in conflicts.items() for n in sorted(ns)],
               "attendance_events": events, "other_vote_labels": {}, "vote_problems": problems, "vote_notes": notes_out}
    for found, why in ((read_json(city.dir / "explained.json") or {}).get(d.name) or {}).items():
        minutes["vote_notes"] += [f"{p} (explained: {why})" for p in minutes["vote_problems"] if found in p]
        minutes["vote_problems"] = [p for p in minutes["vote_problems"] if found not in p]
    write_json(d / "minutes.json", minutes)
    for p in minutes["vote_problems"]:
        log(f"  VOTE PROBLEM: {p}")
    log(f"  parsed minutes: {len(items)} items, {len(motions)} motions, {sum(1 for x in motions if x['recording'] == 'recorded')} recorded votes")
    return minutes
