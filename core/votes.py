"""Every motion and every member's vote, written to data/<city>/votes/ for analysis and the site."""
import csv, datetime as dt
from core.common import log, read_json, write_json


def meeting_dirs(city):
    return sorted(x for x in city.raw.iterdir() if x.is_dir()) if city.raw.exists() else []


def export_votes(city):
    motions, long_rows = [], []
    for d in meeting_dirs(city):
        minutes, m = read_json(d / "minutes.json"), read_json(d / "meeting.json")
        if not (minutes and m):
            continue
        seen = set()
        for x in minutes["motions"]:
            v, r = x["votes"], x["result"]
            voted = v["for"] + v["against"] + v["other"]
            # A consent report is one vote covering several items: count it once.
            ballot = tuple(voted) + (r["text"],)
            duplicate = x["inherited"] and ballot in seen
            seen.add(ballot)
            row = {"meeting_date": m["start"][:10], "meeting_key": d.name, "meeting_id": m["id"], "city": city.slug,
                   "body": m.get("body"), "meeting_type": m.get("type"), "term": m.get("term"), "motion_id": x["id"],
                   "motion_key": f"{d.name}/{x['id']}", "item_number": x["item_number"], "item_title": x["item_title"],
                   "motion_name": x["name"], "moved_by": x["moved_by"], "seconded_by": x["seconded_by"], "text": x["text"],
                   "outcome": r["outcome"], "outcome_inferred": r.get("inferred", False), "result_text": r["text"], "for_count": r["for"], "against_count": r["against"],
                   "recording": x.get("recording", "recorded" if voted else "unrecorded"),
                   "recorded_vote": bool(voted), "part_of_consent_report": x["inherited"], "duplicate_of_consent_vote": duplicate,
                   "for": v["for"], "against": v["against"], "other": v["other"],
                   "not_voting": [n for n in minutes["roster"] if n not in voted] if voted else [],
                   "minutes_url": m["links"]["meeting_page"]}
            motions.append(row)
            if voted and not duplicate:
                for side, names in (("for", v["for"]), ("against", v["against"]), ("other", v["other"]), ("not_voting", row["not_voting"])):
                    long_rows += [{"meeting_date": row["meeting_date"], "meeting_key": d.name, "body": row["body"], "term": row["term"],
                                   "motion_key": row["motion_key"], "item_number": x["item_number"],
                                   "item_title": x["item_title"], "motion_name": x["name"], "outcome": r["outcome"],
                                   "councillor": n, "vote": side} for n in names]
    out = city.votes
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "votes.json", {"generated_at": dt.datetime.now().isoformat(timespec="seconds"), "motions": motions})
    flat = [{k: "; ".join(v) if isinstance(v, list) else v for k, v in row.items()} for row in motions]
    for name, rows in (("motions.csv", flat), ("votes_by_councillor.csv", long_rows)):
        with open(out / name, "w", newline="") as f:
            if rows:
                w = csv.DictWriter(f, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
    recorded = sum(1 for r in motions if r["recorded_vote"] and not r["duplicate_of_consent_vote"])
    log(f"Votes exported: {len(motions)} motions, {recorded} recorded votes, {len(long_rows)} councillor votes in {out}")
    return motions
