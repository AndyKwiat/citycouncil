"""Multi-council core: council settings, keys, terms, vote labels, meeting.json v2 and site text.
Run with: .venv/bin/python -m unittest discover tests"""
import copy, contextlib, io, json, pathlib, re, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build
import pipeline as p
from bs4 import BeautifulSoup
from core import city as cities
from core.summarize import check_summary, closed_only
from sources import escribe

GUELPH = cities.load("guelph")


def council(**escribe_cfg):
    """A copy of Guelph's settings with other eSCRIBE labels, standing in for another council."""
    c = cities.City("guelph")
    c.cfg = copy.deepcopy(c.cfg)
    c.cfg["escribe"].update(escribe_cfg)
    return c


def parse(city, page):
    with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
        d = pathlib.Path(tmp)
        (d / "minutes.html").write_text(page)
        return escribe.parse_minutes(city, d)


KITCHENER_PAGE = """<html><body><div>Present: Mayor B. Vrbanovic Councillor S. Davey Councillor D. Chapman Councilor A. Owodunni
Absent: Councillor P. Singh Staff: D. Chapman</div>
<div class="AgendaItem AgendaItem5"><div class="AgendaItemCounter">5.</div><div class="AgendaItemTitle">Bylaw</div>
<ul><li class="AgendaItemMotion"><div class="MotionText">That it pass.</div>
<table class="MotionVoters">
<tr><td class="VoterVote">In Favour (2)</td><td class="VotesUsers">Mayor B. Vrbanovic and Councillor S. Davey</td></tr>
<tr><td class="VoterVote">Contra (1)</td><td class="VotesUsers">Councillor D. Chapman</td></tr></table>
<div class="MotionResult">Carried, on a recorded vote (2 to 1)</div></li></ul></div></body></html>"""


class VoteLabels(unittest.TestCase):
    def test_every_known_label(self):
        cases = {"Voting in Favour: (11)": "for", "Voting Against: (2)": "against", "Conflict (1)": "other",
                 "In Favour (7)": "for", "Contra (4)": "against", "In Favor (14)": "for", "Opposed (2)": "against",
                 "Voted in Favour": "for", "Voted in Opposition": "against", "Maybe (3)": None}
        for label, side in cases.items():
            self.assertEqual(escribe.vote_side(label, GUELPH), side, label)

    def test_kitchener_contra_is_against_not_other(self):
        k = council(vote_labels={"for": ["in favour"], "against": ["contra"]}, audit_for_pattern=r"In Favour \(",
                    attendance=escribe.DEFAULT_ATTENDANCE)
        out = parse(k, KITCHENER_PAGE)
        x = out["motions"][0]
        self.assertEqual(x["votes"], {"for": ["Mayor Vrbanovic", "Davey"], "against": ["Chapman"], "other": []})
        self.assertEqual(x["recording"], "recorded")
        self.assertEqual(out["roster"], ["Mayor Vrbanovic", "Davey", "Chapman", "Owodunni", "Singh"])
        self.assertEqual(out["absent"], ["Singh"])
        self.assertEqual(out["vote_problems"], [])

    def test_unknown_label_is_a_problem(self):
        out = parse(GUELPH, KITCHENER_PAGE.replace("Contra (1)", "Sideways (1)"))
        self.assertTrue(any("unknown vote label" in x for x in out["vote_problems"]))

    def test_conflicts(self):
        page = "<html><body><p>Councillor Caron declared a conflict with item 3.7, as this property is leased by her employer.</p></body></html>"
        self.assertEqual(escribe.parse_conflicts(BeautifulSoup(page, "html.parser"))[0]["member"], "Caron")
        self.assertEqual(escribe.parse_conflicts(BeautifulSoup(page, "html.parser"))[0]["item_number"], "3.7")


class KeysAndTerms(unittest.TestCase):
    def test_keys(self):
        self.assertEqual(GUELPH.make_key("2026-04-20", "City Council"), "2026-04-20")
        self.assertEqual(GUELPH.make_key("2026-04-20", "Committee of the Whole"), "2026-04-20-committee-of-the-whole")

    def test_list_meetings_keys_and_collisions(self):
        def rec(i, name, when):
            return {"ID": f"id{i}", "MeetingName": name, "StartDate": when, "EndDate": when, "MeetingDocumentLink": [], "HasVideo": False}
        with tempfile.TemporaryDirectory() as tmp:
            c = cities.City("guelph")
            c.calendar, c.raw = pathlib.Path(tmp) / "calendar.json", pathlib.Path(tmp) / "raw"
            p.write_json(c.calendar, {"d": [rec(1, "City Council", "2026/04/21 18:00:00"), rec(2, "City Council", "2026/04/21 09:00:00"),
                                            rec(3, "Committee of the Whole", "2026/04/20 09:00:00"), rec(4, "Heritage Advisory Committee", "2026/04/20 09:00:00"),
                                            rec(5, "City Council", "2021/01/05 18:00:00")]})
            ms = escribe.list_meetings(c)
        self.assertEqual([(m["id"], m["key"]) for m in ms],
                         [("id1", "2026-04-21-2"), ("id2", "2026-04-21"), ("id3", "2026-04-20-committee-of-the-whole")])
        self.assertEqual(ms[2]["body"], "committee")

    def test_terms(self):
        self.assertEqual(GUELPH.term_for("2022-12-06"), "2022-2026")
        self.assertEqual(GUELPH.term_for("2026-11-15"), "2026-2030")
        self.assertIsNone(GUELPH.term_for("2020-01-01"))
        self.assertEqual(GUELPH.council_size("2022-2026"), 13)

    def test_council_size_sets_the_digit_check(self):
        summary = {"overview": ["Passed 9-7."], "debate": [], "decisions": [{"motion": "m1", "item": "x", "detail": "y"}]}
        motions = [{"id": "m1", "item_title": "Budget"}]
        self.assertEqual(check_summary(summary, motions, 13), [])
        self.assertTrue(any("digits" in e for e in check_summary(summary, motions, 16)))

    def test_closed_only(self):
        self.assertTrue(closed_only({"motions": [{"id": "m1", "item_title": "Authority to move into closed meeting"},
                                                 {"id": "m2", "item_title": "Adjournment"}]}))
        self.assertFalse(closed_only({"motions": [{"id": "m1", "item_title": "Budget"}]}))
        self.assertFalse(closed_only({"motions": [{"id": "m1", "item_title": "Appointment of Closed Meeting Investigator - 2026-250"}]}))


class GuelphData(unittest.TestCase):
    def test_every_meeting_is_v2(self):
        dirs = p.meeting_dirs(GUELPH)
        self.assertGreaterEqual(len(dirs), 42)
        for d in dirs:
            m = p.read_json(d / "meeting.json")
            self.assertEqual((m["version"], m["key"], m["city"]), (2, d.name, "guelph"), d.name)
            self.assertTrue((d / "source" / "meeting_source.json").exists(), d.name)
            self.assertIn(m["body"], ("council", "committee"))
            if (d / "minutes.html").exists():
                self.assertTrue(m["links"]["official_minutes"].startswith(GUELPH.records_url), d.name)
            self.assertFalse((d / "video_file.txt").exists())


class SiteText(unittest.TestCase):
    """The site describes itself as automated and never uses the word "AI" about itself (meeting content aside)."""

    def test_sources_never_say_ai(self):
        for name in ("build.py", "build_root.py", "search_page.py", "alliance_network.py", "alliance_network.js"):
            text = (ROOT / name).read_text()
            self.assertIsNone(re.search(r"\bAI\b", text), name)

    def test_disclaimer(self):
        footer = build.disclaimer(GUELPH)
        self.assertIn("produced automatically", footer)
        self.assertIn("not affiliated with the City of Guelph", footer)
        self.assertIn("Maksim Sokolov", footer)
        self.assertNotRegex(build.disclaimer(None), r"\bAI\b")

    def test_built_pages_never_say_ai(self):
        site = ROOT / "site"
        if not (site / "index.html").exists():
            self.skipTest("site not built")
        for page in site.rglob("*.html"):
            # Meeting content (summaries, minutes, transcripts, vote titles) may quote people talking about AI.
            text = re.sub(r'<details class="meeting.*?</details>', "", page.read_text(), flags=re.S)
            text = re.sub(r'<div class="(tr|mins)">.*', "", text, flags=re.S)
            text = re.sub(r'<div class="cn-vote">.*?</div>', "", text, flags=re.S)
            self.assertIsNone(re.search(r"\bAI\b", text), page)
            self.assertIn('class="site"', page.read_text(), page)

    def test_filter_chips_only_with_several_kinds(self):
        one = {"a": {"body": "council", "body_name": "City Council", "type": "City Council"}}
        self.assertEqual(build.filter_chips(GUELPH, one), "")
        two = {**one, "b": {"body": "committee", "body_name": "Committee of the Whole", "type": "Committee of the Whole"}}
        chips = build.filter_chips(GUELPH, two)
        self.assertIn('href="#show=committee-of-the-whole"', chips)
        self.assertTrue(chips.index("City Council") < chips.index("Committee of the Whole"))  # main meetings first


class Whisper(unittest.TestCase):
    def test_names_after_titles_are_matched_to_the_roster(self):
        from core.transcribe import fix_names
        segs = [{"text": "Thank you Councillor Chaplin. Councilor Onitis, then Mayor Verbanovic and Councillor Smith."}]
        out = fix_names(segs, ["Mayor Vrbanovic", "Chapman", "Ioannidis", "Davey"])[0]["text"]
        self.assertEqual(out, "Thank you Councillor Chapman. Councilor Onitis, then Mayor Vrbanovic and Councillor Smith.")  # too far to guess safely


class ProseVotes(unittest.TestCase):
    def test_kitchener_narrated_votes(self):
        text = ("Councillor S. Davey's amendment was then voted on and was LOST on a tie , on a recorded vote with Councillors "
                "S. Davey, B. Ioannidis, C. Michaud and D. Schinder voting in favour, and Mayor B. Vrbanovic and Councillors "
                "D. Chapman, J. Deneault and M. Johnston voting in opposition.")
        v = escribe.prose_votes(text)[0]
        self.assertEqual((v["outcome"], v["for"], v["against"]),
                         ("Lost", ["Davey", "Ioannidis", "Michaud", "Schinder"], ["Mayor Vrbanovic", "Chapman", "Deneault", "Johnston"]))
        one_side = escribe.prose_votes("The motion was Carried, on a recorded vote, with Mayor B. Vrbanovic and Councillors S. Davey voting in favour.")[0]
        self.assertEqual((one_side["for"], one_side["against"]), (["Mayor Vrbanovic", "Davey"], []))

    def test_minutes_typos_and_missing_words(self):
        # The minutes drop the second "voting in opposition", and the next clause must not be swallowed.
        text = ("Clause 1 was then voted on and was LOST on a recorded vote, with Councillors D. Chapman and A. Owodunni voting in "
                "favour; and, Mayor B. Vrbanovic and Councillors S. Davey, J Deneault, D. Schnider. Clause 2 was then voted on "
                "and was LOST on a recorded vote, with Councillor D. Chapman voting in favour; and, Mayor B. Vrbanovic voting in opposition.")
        a, b = escribe.prose_votes(text)
        self.assertEqual((a["for"], a["against"]), (["Chapman", "Owodunni"], ["Mayor Vrbanovic", "Davey", "Deneault", "Schnider"]))
        self.assertEqual((b["for"], b["against"]), (["Chapman"], ["Mayor Vrbanovic"]))
        declined = escribe.prose_votes("They were Carried on a recorded vote, with Mayor B. Vrbanovic and Councillors S. Davey voting in favour; "
                                       "and, Councillor D. Chapman declined to vote and the refusal is recorded as a vote in opposition.")[0]
        self.assertEqual(declined["against"], ["Chapman"])
        typo = escribe.prose_votes("It was Carried, on a recorded vote , with Councillors S. Davey, D. Schnider. J. Deneault voting in favour.")[0]
        self.assertEqual(typo["for"], ["Davey", "Schnider", "Deneault"])

    def test_results(self):
        r = escribe.parse_result("Carried, as amended, on a recorded vote (7 to 4)")
        self.assertEqual((r["outcome"], r["label"], r["for"]), ("Carried", "7-4", 7))
        self.assertEqual(escribe.parse_result("LOST (3 to 7)")["label"], "Lost 3-7")
        self.assertEqual(escribe.parse_result("Carried, unanimously on a recorded vote (11 to 0)")["label"], "11-0")


WATERLOO_TEXT = """PRESENT: Mayor Dorothy McCabe, Councillor Sandra Hanmer, Councillor Royce
Bodaly, Councillor Hans Roach
ABSENT: Councillor Julie Wright
1. STAFF REPORTS
a) Title: Fireworks By-law Amendment
Moved by Councillor Hanmer, Seconded by Councillor Roach:
That Council approve report COM2025-021.
Carried Unanimously
Councillor Roach left the meeting. (Time: 3:22 p.m.)
Moved by Councillor Bodaly, Seconded by Councillor Hanmer:
That the plan be approved.
Carried
2 Voting in Favour
1 Voting in Opposition
(COUNCILLOR BODALY)
That the second clause be approved.
Motion Failed
1 Voting in Favour
2 Voting in Opposition
(MAYOR MCCABE)
(COUNCILLOR HANMER)
"""


class Waterloo(unittest.TestCase):
    def test_pdf_minutes(self):
        from sources import govstack
        c = cities.load("waterloo")
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            d = pathlib.Path(tmp)
            (d / "minutes.txt").write_text("".join(f"1\t{l}\n" for l in WATERLOO_TEXT.splitlines()))
            p.write_json(d / "meeting.json", {"term": "2022-2026", "title": "Council Meeting"})
            out = govstack.parse_minutes(c, d)
        self.assertEqual(out["roster"], ["Mayor McCabe", "Hanmer", "Bodaly", "Roach", "Wright"])
        self.assertEqual(out["absent"], ["Wright"])
        first, split, failed = out["motions"]
        self.assertEqual((first["recording"], first["result"]["label"], first["moved_by"], first["text"]),
                         ("unanimous", "Carried unanimously", "Hanmer", "That Council approve report COM2025-021."))
        self.assertEqual(first["votes"]["for"], [])  # nobody's vote is invented for a unanimous motion
        self.assertEqual((split["votes"]["for"], split["votes"]["against"], split["for_inferred"]), (["Hanmer", "Mayor McCabe"], ["Bodaly"], True))
        self.assertEqual((failed["result"]["label"], failed["votes"]["against"], failed["text"]),
                         ("Defeated 1-2", ["Mayor McCabe", "Hanmer"], "That the second clause be approved."))
        self.assertEqual(out["items"][1]["number"], "1a")
        self.assertEqual(out["vote_problems"], [])

    def test_youtube_titles(self):
        from video import youtube
        import datetime
        self.assertEqual(youtube.title_date("City of Waterloo Council Meeting September 8, 2025 @ 3:00PM"), datetime.date(2025, 9, 8))
        self.assertEqual(youtube.title_date("Council - 24 Aug 2026 (Part 2)"), datetime.date(2026, 8, 24))
        titles = ["X September 8, 2025 @ 6:30PM", "X September 8, 2025 @ 3:00PM"]
        self.assertEqual(sorted(titles, key=youtube.order_key), titles[::-1])


CW_TEXT = """PRESENT: Mayor Shawn Watters
Councillor Lisa MacDonald
Councillor Barbara Lustgarten-Evoy
Councillor Bronwynne Wilton
REGRETS: Councillor Denis Craddock
STAFF: Chief Administrative Officer, Dan Wilson
1. Call to Order
Mayor Watters called the meeting to order.
2. Consent Items
Moved by Councillor Bronwynne Wilton, Seconded by Councillor Lisa
MacDonald.
THAT the Council approve consent agenda items 2.1 through 2.2.
2.1
THAT the minutes be approved.
2.2 Appointments
THAT the following be appointed:
1. Jane Doe
CARRIED
3. Zoning
Councillor Wilton requested a recorded vote.
3.1 Moved by Councillor Barbara Lustgarten-Evoy, Seconded by Councillor
Lisa MacDonald.
THAT the zoning amendment be approved.
CARRIED
Mayor Shawn Watters For
Councillor Lisa MacDonald For
Councillor Barbara Lustgarten- For
Evoy
Councillor Wilton Against
"""


class CentreWellington(unittest.TestCase):
    def test_pdf_minutes(self):
        from sources import civicweb
        c = cities.load("centre-wellington")
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            d = pathlib.Path(tmp)
            (d / "minutes.txt").write_text("".join(f"1\t{l}\n" for l in CW_TEXT.splitlines()))
            p.write_json(d / "meeting.json", {"term": "2022-2026"})
            out = civicweb.parse_minutes(c, d)
        self.assertEqual(out["roster"], ["Mayor Watters", "MacDonald", "Lustgarten-Evoy", "Wilton", "Craddock"])
        consent, zoning = out["motions"]
        self.assertIn("THAT the following be appointed", consent["text"])  # sub-items stay inside the consent motion
        self.assertEqual((consent["moved_by"], consent["seconded_by"], consent["recording"]), ("Wilton", "MacDonald", "unrecorded"))
        self.assertEqual((zoning["item_number"], zoning["result"]["label"], zoning["votes"]["for"], zoning["votes"]["against"]),
                         ("3.1", "3-1", ["Mayor Watters", "MacDonald", "Lustgarten-Evoy"], ["Wilton"]))
        self.assertEqual(out["vote_problems"], [])


class Cycles(unittest.TestCase):
    def test_other_meetings_fold_under_the_next_council_meeting(self):
        def it(day, kind):
            return (__import__("datetime").datetime.fromisoformat(day), {"type": kind, "body_name": kind}, day)
        items = [it("2026-01-05", "Committee of the Whole"), it("2026-01-27", "City Council"), it("2026-02-02", "Council Planning"),
                 it("2026-02-10", "Committee of the Whole"), it("2026-02-24", "City Council"), it("2026-03-02", "Committee of the Whole")]
        groups = build.cycles(GUELPH, items)
        self.assertEqual([(a[2] if a else None, [x[2] for x in subs]) for a, subs in groups],
                         [(None, ["2026-03-02"]), ("2026-02-24", ["2026-02-02", "2026-02-10"]), ("2026-01-27", ["2026-01-05"])])
        html = build.listing_html(GUELPH, items)
        self.assertIn("Since the last council meeting", html)
        self.assertIn("2 other meetings (Council Planning, Committee of the Whole)", html)


if __name__ == "__main__":
    unittest.main()
