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
    """The site describes itself as automated and never uses the word "AI" (people quoted in transcripts aside)."""

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
            text = re.sub(r'<div class="tr">.*?</div></div></div>', "", page.read_text(), flags=re.S)  # transcripts quote people
            text = re.sub(r'<div class="tr">.*', "", text, flags=re.S)
            self.assertIsNone(re.search(r"\bAI\b", text), page)
            self.assertIn('class="site"', page.read_text(), page)

    def test_filter_chips_only_with_several_kinds(self):
        one = {"a": {"body": "council", "body_name": "City Council"}}
        self.assertEqual(build.filter_chips(GUELPH, one), "")
        two = {**one, "b": {"body": "committee", "body_name": "Committee of the Whole"}}
        chips = build.filter_chips(GUELPH, two)
        self.assertIn('href="#show=committee-of-the-whole"', chips)
        self.assertIn('data-show="council"', chips)


if __name__ == "__main__":
    unittest.main()
