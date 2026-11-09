"""Run with: .venv/bin/python -m unittest discover tests"""
import itertools, json, pathlib, sys, tempfile, unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import alliance_network
import search_index
import analysis
import pipeline as p
from bs4 import BeautifulSoup
from core import city as cities
from sources import escribe

GUELPH = cities.load("guelph")


def motion(mid="m1", title="Some item", yes=(), no=(), result="", inherited=False):
    r = p.parse_result(result)
    return {"id": mid, "item": "1", "item_number": "1", "item_title": title, "name": "", "moved_by": "", "seconded_by": "",
            "text": "", "text_html": "", "post_html": "", "result": r,
            "votes": {"for": list(yes), "against": list(no), "other": []}, "inherited": inherited}


MINUTES_PAGE = """<html><head><title>City Council</title></head><body>
<div>Council: Mayor C. Guthrie Councillor D. Gibson Councillor P. Allt Absent: Councillor C. Billings Staff: A. Clerk</div>
<script>var x = { Bookmarks: [{"AgendaItemId": 11, "TimeStart": 5000, "TimeEnd": 9000}], Other: 1 };</script>
<div class="AgendaItem AgendaItem11"><div class="AgendaItemCounter">4.</div><div class="AgendaItemTitle">Road Plan</div>
 <ul><li class="AgendaItemMotion">
  <div class="MovedBy"><span class="Value">Councillor Gibson</span></div>
  <div class="SecondedBy"><span class="Value">Mayor Guthrie</span></div>
  <div class="MotionText"><p>That the plan be approved.</p></div>
  <table class="MotionVoters">
   <tr><td class="VoterVote">Voting in Favour (2)</td><td class="VotesUsers">Mayor Guthrie and Councillor Gibson</td></tr>
   <tr><td class="VoterVote">Voting Against (1)</td><td class="VotesUsers">Councillor Allt</td></tr>
  </table>
  <div class="MotionResult">Carried (2 to 1)</div>
 </li></ul></div>
<div class="AgendaItem AgendaItem12"><div class="AgendaItemCounter">7.</div><div class="AgendaItemTitle">Consent Report</div>
 <ul><li class="AgendaItemMotion"><div class="MotionText">Receive the report.</div></li></ul></div>
<div class="AgendaItem AgendaItem13"><div class="AgendaItemCounter">7.1</div><div class="AgendaItemTitle">Sub item</div>
 <ul><li class="AgendaItemMotion"><div class="MotionText">Approve it.</div>
  <table class="MotionVoters"><tr><td class="VoterVote">Voting in Favour (3)</td><td class="VotesUsers">Mayor Guthrie, Councillor Gibson and Councillor Allt</td></tr></table>
  <div class="MotionResult">Carried (3 to 0)</div></li></ul></div>
</body></html>"""


class Names(unittest.TestCase):
    def test_surname(self):
        self.assertEqual(p.surname("Councillor  D. Gibson"), "Gibson")
        self.assertEqual(p.surname("Mayor Cam Guthrie"), "Mayor Guthrie")
        self.assertEqual(p.surname("and Councillor Allt"), "Allt")
        self.assertEqual(p.surname("Councillor D. O'Rourke"), "O'Rourke")

    def test_split_names(self):
        self.assertEqual(p.split_names("Mayor Guthrie, Councillor Allt and Councillor Caron"), ["Mayor Guthrie", "Allt", "Caron"])


class Results(unittest.TestCase):
    def test_counts(self):
        r = p.parse_result("Carried (8 to 5)")
        self.assertEqual((r["label"], r["for"], r["against"], r["outcome"], r["inferred"]), ("8-5", 8, 5, "Carried", False))
        self.assertEqual(p.parse_result("Defeated (3 to 10)")["label"], "Defeated 3-10")

    def test_count_without_word_is_inferred(self):
        r = p.parse_result("(7 to 6)")
        self.assertEqual((r["outcome"], r["inferred"]), ("Carried", True))
        self.assertEqual(p.parse_result("(6 to 7)")["outcome"], "Defeated")

    def test_no_count(self):
        r = p.parse_result("Carried")
        self.assertIsNone(r["for"])
        self.assertEqual(r["outcome"], "Carried")
        self.assertIsNone(p.parse_result("")["outcome"])


class Parsing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raw = pathlib.Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        (self.raw / "2024-01-02").mkdir()
        (self.raw / "2024-01-02" / "minutes.html").write_text(MINUTES_PAGE)
        self.out = escribe.parse_minutes(GUELPH, self.raw / "2024-01-02")

    def test_attendance(self):
        self.assertEqual(self.out["absent"], ["Billings"])
        self.assertEqual(self.out["roster"], ["Mayor Guthrie", "Gibson", "Allt", "Billings"])

    def test_votes_and_bookmarks(self):
        first = self.out["motions"][0]
        self.assertEqual(first["votes"]["for"], ["Mayor Guthrie", "Gibson"])
        self.assertEqual(first["votes"]["against"], ["Allt"])
        self.assertEqual(first["moved_by"], "Gibson")
        self.assertEqual(self.out["items"][0]["video_start"], 5.0)

    def test_consent_items_share_one_vote(self):
        header, sub = self.out["motions"][1], self.out["motions"][2]
        self.assertTrue(header["inherited"] and sub["inherited"])
        self.assertEqual(header["votes"], sub["votes"])
        self.assertEqual(self.out["vote_problems"], [])

    def test_audit_catches_a_missing_vote(self):
        page = MINUTES_PAGE.replace("</body>", "<p>Voting in Favour: everyone (9 to 0)</p></body>")
        motions = self.out["motions"]
        motions[1]["votes"] = motions[2]["votes"]  # shared in memory while parsing; JSON loading separates them
        problems = p.audit_votes(page, BeautifulSoup(page, "html.parser"), motions, self.out["roster"])
        self.assertTrue(any("Voting in Favour" in x for x in problems))
        self.assertTrue(any("counted results" in x for x in problems))

    def test_consent_items_keep_their_own_votes(self):
        page = """<html><body><div>Council: Mayor C. Guthrie Councillor D. Gibson Staff: X</div>
        <div class="AgendaItem AgendaItem1"><div class="AgendaItemCounter">4.</div><div class="AgendaItemTitle">Consent Agenda</div></div>""" + "".join(
            f"""<div class="AgendaItem AgendaItem{n}"><div class="AgendaItemCounter">4.{n}</div><div class="AgendaItemTitle">Item</div>
            <ul><li class="AgendaItemMotion"><div class="MotionText">Do it</div>
            <table class="MotionVoters"><tr><td class="VoterVote">Voting in Favour ({len(names)})</td><td class="VotesUsers">{" and ".join(names)}</td></tr></table>
            <div class="MotionResult">Carried ({len(names)} to 0)</div></li></ul></div>"""
            for n, names in ((2, ["Mayor Guthrie", "Councillor Gibson"]), (3, ["Councillor Gibson"]))) + "</body></html>"
        (self.raw / "2024-01-02" / "minutes.html").write_text(page)
        out = escribe.parse_minutes(GUELPH, self.raw / "2024-01-02")
        self.assertEqual([x["result"]["for"] for x in out["motions"]], [2, 1])
        self.assertEqual([x["inherited"] for x in out["motions"]], [False, False])
        self.assertEqual(out["vote_problems"], [])

    def test_bare_unanimous_count_is_not_a_problem_but_a_bare_split_is(self):
        fine, bad = motion(result="Carried (12 to 0)"), motion("m2", result="Carried (7 to 5)")
        problems = p.audit_votes("", BeautifulSoup("", "html.parser"), [fine, bad], [])
        self.assertEqual(len(problems), 1)
        self.assertIn("m2", problems[0])

    def test_audit_catches_wrong_counts_and_names(self):
        bad = motion(yes=["Gibson", "Stranger"], no=["Gibson"], result="Carried (5 to 1)")
        problems = p.audit_votes("", BeautifulSoup("", "html.parser"), [bad], ["Gibson"])
        text = " ".join(problems)
        self.assertIn("result says 5-1", text)
        self.assertIn("Stranger", text)
        self.assertIn("both sides", text)


class Transcripts(unittest.TestCase):
    def test_vtt(self):
        segs = p.parse_vtt("WEBVTT\n\n00:00:01.000 --> 00:00:03.500\nHello\nthere\n\n01:00:00.000 --> 01:00:01.000\nBye")
        self.assertEqual(segs[0], {"start": 1.0, "end": 3.5, "text": "Hello there", "source": "captions"})
        self.assertEqual(segs[1]["start"], 3600.0)

    def test_gaps(self):
        segs = [{"start": 0, "end": 10}, {"start": 500, "end": 510}, {"start": 520, "end": 530}]
        self.assertEqual(p.find_gaps(segs, 0, 2000), [(10, 500), (530, 2000)])
        self.assertEqual(p.find_gaps(segs, 0, 600), [(10, 500)])

    def test_repeated_whisper_lines_dropped(self):
        segs = [{"text": "thanks"} for _ in range(5)] + [{"text": "next"}, {"text": ""}]
        self.assertEqual([s["text"] for s in p.clean_segments(segs)], ["thanks", "thanks", "next"])


class Summaries(unittest.TestCase):
    def summary(self, motion_id="m1", detail="Approved {{vote:m1}}."):
        return {"overview": ["ok"], "debate": [], "decisions": [{"motion": motion_id, "item": "x", "detail": detail}]}

    def test_good(self):
        self.assertEqual(p.check_summary(self.summary(), [motion()]), [])

    def test_rejects(self):
        for s, expected in ((self.summary("m9"), "unknown motion"), (self.summary(detail="{{vote:m9}}"), "unknown vote token"),
                            (self.summary(detail="Passed 8-5."), "digits")):
            self.assertTrue(any(expected in e for e in p.check_summary(s, [motion()])), expected)
        procedural = [motion(title="Closed Meeting")]
        self.assertTrue(any("procedural" in e for e in p.check_summary(self.summary(), procedural)))


class Clusters(unittest.TestCase):
    def votes(self):
        a, b = ["A1", "A2", "A3", "A4"], ["B1", "B2", "B3", "B4"]
        return [{"for": a, "against": b} for _ in range(6)] + [{"for": b, "against": a} for _ in range(6)]

    def test_finds_two_blocs(self):
        c = analysis.clusters(self.votes())
        self.assertEqual(c["groups_chosen"], 2)
        groups = {frozenset(g["members"]) for g in c["groups"].values()}
        self.assertEqual(groups, {frozenset(["A1", "A2", "A3", "A4"]), frozenset(["B1", "B2", "B3", "B4"])})
        self.assertEqual(c["agreement_between"]["A-B"], 0)

    def test_people_who_never_voted_together_are_not_assumed_opposed(self):
        # "Old" served first and "New" replaced them; both always side with group A.
        a, b = ["A1", "A2", "A3"], ["B1", "B2", "B3"]
        early = [{"for": a + ["Old"], "against": b} for _ in range(5)] + [{"for": b, "against": a + ["Old"]} for _ in range(5)]
        late = [{"for": a + ["New"], "against": b} for _ in range(5)] + [{"for": b, "against": a + ["New"]} for _ in range(5)]
        c = analysis.clusters(early + late)
        self.assertEqual(c["members"]["Old"]["group"], c["members"]["New"]["group"])
        self.assertEqual(c["members"]["Old"]["group"], c["members"]["A1"]["group"])

    def test_stable_between_runs(self):
        self.assertEqual(analysis.clusters(self.votes()), analysis.clusters(self.votes()))


class Communities(unittest.TestCase):
    def pairs(self, groups, inside=18, across=6, total=20):
        names = sorted(n for g in groups for n in g)
        agreed, shared = {}, {}
        for a, b in itertools.combinations(names, 2):
            same = any(a in g and b in g for g in groups)
            agreed[a, b], shared[a, b] = (inside if same else across), total
        return names, agreed, shared

    def test_finds_blocs(self):
        names, agreed, shared = self.pairs([["A", "B", "C", "D"], ["E", "F", "G", "H"], ["I", "J", "K"]])
        c = analysis.communities(names, agreed, shared)
        self.assertEqual(c["count"], 3)
        self.assertEqual(c["members"]["A"], c["members"]["D"])
        self.assertNotEqual(c["members"]["A"], c["members"]["E"])

    def test_uniform_agreement_forms_no_blocs(self):
        names, agreed, shared = self.pairs([["A", "B", "C", "D", "E", "F"]], inside=12)
        self.assertEqual(analysis.communities(names, agreed, shared)["count"], 6)

    def test_is_repeatable(self):
        names, agreed, shared = self.pairs([["A", "B", "C"], ["D", "E", "F"]])
        self.assertEqual(analysis.communities(names, agreed, shared), analysis.communities(names, agreed, shared))

    def test_network_keeps_one_edge_per_pair_and_unknowns_unknown(self):
        names, agreed, shared = self.pairs([["A", "B", "C"], ["D", "E", "F"]])
        del agreed["A", "D"], shared["A", "D"]
        c = analysis.communities(names, agreed, shared)
        data = alliance_network.network_data(names, agreed, shared, str, lambda n: "", lambda n: "", c, {})
        self.assertEqual(len(data["edges"]), 14)
        self.assertEqual(data["unknown"], [["A", "D"]])
        self.assertEqual({tuple(sorted((x["a"], x["b"]))) for x in data["edges"]}.__len__(), 14)
        self.assertFalse([x for x in data["edges"] if x["a"] == x["b"]])
        self.assertEqual(data["edges"][0]["pct"], 90)
        node = next(n for n in data["nodes"] if n["id"] == "A")
        self.assertEqual(node["comparisons"], 4)
        self.assertEqual(node["average"], (90 + 90 + 30 + 30) / 4)

    def test_initials(self):
        self.assertEqual(alliance_network.initials("Mayor Cam Guthrie"), "CG")
        self.assertEqual(alliance_network.initials("Ken Yee Chew"), "KYC")
        self.assertEqual(alliance_network.initials("Dominique O'Rourke"), "DO")


class SearchChunks(unittest.TestCase):
    def setUp(self):
        self.minutes = {"motions": [
            {"id": "m1", "item": "5", "item_number": "5", "item_title": "Encampment Response", "name": "", "moved_by": "Caron",
             "seconded_by": "Allt", "text": "That the encampment pilot be approved. " + "word " * 600,
             "result": p.parse_result("Carried (8 to 5)"), "votes": {"for": ["Caron"], "against": ["Gibson"], "other": []}},
            {"id": "m2", "item": "6", "item_number": "6", "item_title": "Header", "name": "", "moved_by": "", "seconded_by": "",
             "text": "", "result": p.parse_result(""), "votes": {"for": [], "against": [], "other": []}}],
            "items": [{"id": "5", "number": "5", "title": "Encampment Response", "video_start": 100.0, "video_end": 900.0,
                       "notes": ["<p>Staff presented the encampment response plan to council and answered several detailed questions from members about costs.</p>"]},
                      {"id": "1", "number": "1", "title": "Call to Order", "video_start": 0.0, "video_end": 1.0,
                       "notes": ["<p>Called to order.</p>"]}]}
        self.summary = {"title": "Encampments", "subtitle": "Also parking.", "overview": ["Council approved a pilot {{vote:m1}}."],
                        "decisions": [{"motion": "m1", "item": "Encampment pilot", "detail": "Approved {{vote:m1}}."}],
                        "debate": ["Delegates spoke."]}
        self.transcript = [{"start": 120.0 + 10 * i, "end": 125.0 + 10 * i, "text": "we discuss the shelter plan now", "source": "captions"}
                           for i in range(80)]
        m = {"key": "2026-07-21", "start": "2026-07-21T18:00:00", "type": "City Council", "body": "council", "body_name": "City Council"}
        self.rows = search_index.meeting_chunks(search_index.meeting_info(GUELPH, m), self.summary, self.minutes, self.transcript)

    def kinds(self, kind):
        return [r for r in self.rows if r["kind"] == kind]

    def test_every_kind_links_to_the_site(self):
        self.assertEqual({r["kind"] for r in self.rows}, {"summary", "vote", "minutes", "transcript"})
        self.assertTrue(all(r["url"].startswith(("index.html#m-", "minutes/", "transcripts/")) for r in self.rows))
        self.assertEqual(self.kinds("vote")[0]["url"], "minutes/2026-07-21.html#m1")
        self.assertTrue(self.kinds("transcript")[0]["url"].startswith("transcripts/2026-07-21.html#t-"))

    def test_vote_tokens_become_counts(self):
        text = " ".join(r["text"] for r in self.kinds("summary"))
        self.assertIn("(8-5)", text)
        self.assertNotIn("{{vote", text)

    def test_long_motions_split_and_names_kept_out_of_embedding(self):
        votes = self.kinds("vote")
        self.assertEqual(len(votes), 3)  # 600 words in pieces of 280; the empty header motion is skipped
        self.assertIn("For: Caron", votes[0]["text"])
        self.assertNotIn("Caron", votes[0]["embed"])
        self.assertTrue(all(r["label"] == "8-5" for r in votes))

    def test_trivial_minutes_skipped_and_transcripts_titled_by_topic(self):
        self.assertEqual([r["title"] for r in self.kinds("minutes")], ["5 Encampment Response"])
        self.assertTrue(all(r["title"].startswith("Encampment Response") for r in self.kinds("transcript")))
        self.assertTrue(all(len(r["text"].split()) < 260 for r in self.kinds("transcript")))

    def test_embedded_text_carries_context(self):
        self.assertTrue(self.kinds("vote")[0]["embed"].startswith("Council vote, Guelph City Council, July 21, 2026."))
        self.assertEqual({(r["city"], r["date"], r["body"]) for r in self.rows}, {("guelph", "2026-07-21", "council")})
        m = {"key": "2026-07-20-committee-of-the-whole", "start": "2026-07-20T09:00:00", "type": "Committee of the Whole",
             "body": "committee", "body_name": "Committee of the Whole"}
        rows = search_index.meeting_chunks(search_index.meeting_info(GUELPH, m), self.summary, self.minutes, [])
        self.assertTrue(rows[0]["embed"].startswith("Meeting summary, Guelph Committee of the Whole, July 20, 2026."))
        self.assertEqual(rows[0]["url"], "index.html#m-2026-07-20-committee-of-the-whole")


class RealData(unittest.TestCase):
    """Whatever has been downloaded must stay internally consistent."""

    def test_recorded_votes_match_their_counts(self):
        for d in p.meeting_dirs(GUELPH):
            minutes = p.read_json(d / "minutes.json")
            for x in (minutes or {}).get("motions", []):
                r, v = x["result"], x["votes"]
                if v["for"] or v["against"]:
                    self.assertEqual((r["for"], r["against"]), (len(v["for"]), len(v["against"])), f"{d.name}/{x['id']}")
                    self.assertFalse(set(v["for"]) & set(v["against"]), f"{d.name}/{x['id']}")

    def test_summaries_point_at_real_motions(self):
        for d in p.meeting_dirs(GUELPH):
            minutes, summary = p.read_json(d / "minutes.json"), p.read_json(d / "summary.json")
            if minutes and summary:
                ids = {x["id"] for x in minutes["motions"]}
                for x in summary["decisions"]:
                    self.assertIn(x["motion"], ids, d.name)


if __name__ == "__main__":
    unittest.main()
