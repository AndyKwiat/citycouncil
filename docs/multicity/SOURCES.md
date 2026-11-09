# Council data sources

How each council publishes minutes, votes and video. ✅ means checked against a live page, ❓ means not yet
verified (a Phase 0 spike). Last research: 2026-11-09 (Phase 0 spikes for every council). All city sites listed here except Guelph's return 403 to
bare HTTP clients; a normal browser User-Agent works.

---

## Guelph (existing)

- ✅ eSCRIBE `https://pub-guelph.escribemeetings.com`. Meetings come from `GetCalendarMeetings`; type "City Council".
- ✅ HTML minutes; named votes on most motions ("Voting in Favour …").
- ✅ ISI video, client `guelph`; captions at `https://video.isilive.ca/guelph/<file>.vtt`; HLS at
  `https://sp2hls.isilive.ca/hls/file/guelph/<file>/index.m3u8`. Agenda item to video times come from the `Bookmarks`
  in the minutes page.
- ✅ In scope (Phase 0, from the cached calendar, 2022-11-15 → 2026-11-09), with minutes and split recorded votes:

  | Type | Body | Meetings with minutes | Split recorded votes |
  |---|---|---|---|
  | City Council | council | 42 | 73 |
  | Council Planning | council | 42 | 65 |
  | Special Council Meeting | council | 28 | 19 |
  | Special Council Meeting - Budget | council | 12 | 38 |
  | Committee of the Whole | committee | 40 | 41 |

  All 167 parse with no vote problems. Out of scope: advisory committees, Committee of Adjustment, Information
  Items, workshops, the inaugural meeting and "City Council as Shareholder" meetings.
- ✅ One set of minutes (2024-07-16 special) spells "Councilor"; the parser accepts both.
- 2026–30 council (election 2026-10-26), ❓ **unofficial and incomplete**: Mayor **Leanne Caron** (Ward 5
  councillor 2022–26), about 54% of the vote over Ken Yee Chew. A local outlet headlines "7 new councillors". Reported
  ward winners so far: Rodrigo Goller (Ward 2, returning), Brendan Clark (Ward 4, over Linda Busuttil), Rebecca Adam
  (Ward 6). Sources: [Guelph Politico](https://guelphpolitico.ca/2026/10/27/election-results-carons-the-new-mayor-with-7-new-councillors/),
  [CTV Kitchener](https://www.ctvnews.ca/kitchener/article/election-results-heres-who-voters-picked-for-mayor-and-council/).
  Fill `cities/guelph/councillors.json` from the City's certified results before the first 2026–30 meeting.

---

## Kitchener and Region of Waterloo

_Phase 0 spike, 2026-11-09. Scripts in `docs/multicity/spikes/kitchener_region/` (they cache downloads locally). Correction to the earlier notes: the Region records named votes from **August 2023**, not all of 2023._

### Kitchener and Region counts (2022-11-15 → 2026-11-09, in-scope meetings with HTML minutes)

| | Meetings | Motions | Recorded (`MotionVoters` with names) | **Split recorded** (against > 0) |
|---|---|---|---|---|
| **Kitchener council** (Council Meeting + Special Council Meeting) | 151 | 1,373 | 39 | **27** |
| **Kitchener committees** (FCS, PSI, CIS) | 137 | 443 | 12 | **11** |
| Kitchener votes written as prose (not in tables, see K-votes) | | | ~98 "on a recorded vote" mentions | **~42** "voting in opposition" (29 council, 13 committee) |
| **Region council** (Council, Special, Emergency Special, Inaugural, Board of Health) | 93 | 1,223 | 790 | **134** |
| **Region committees** (A&F, CHS, P&W→SID, SP&B and variants) | 172 | 1,263 | 931 | **336** (247 of them in Strategic Planning and Budget) |

Per year (motions / recorded / split):

| Year | Kitchener council | Kitchener committees | Region council | Region committees |
|---|---|---|---|---|
| 2022 (from Nov 15) | 44 / 2 / 2 | 14 / 0 / 0 | 27 / 0 / 0 | 19 / 1 / 1 |
| 2023 | 401 / 13 / 8 | 138 / 3 / 2 | 272 / 91 / 8 | 401 / 216 / 90 |
| 2024 | 370 / 9 / 8 | 121 / 1 / 1 | 279 / 210 / 28 | 431 / 372 / 167 |
| 2025 | 312 / 10 / 7 | 93 / 5 / 5 | 312 / 232 / 38 | 244 / 207 / 58 |
| 2026 | 246 / 5 / 2 | 77 / 3 / 3 | 333 / 257 / 60 | 168 / 135 / 20 |

The bottom line for 4.7:
- **The Region is a full-data council.** It has 470 split named votes in the term, and about 80% of motions have named votes
  from August 2023 on.
- **Kitchener is thin, but not as thin as the tables suggest.**
  - Table-only split votes: 38.
  - Adding the prose-recorded ones: about 80 split votes over 4 years, roughly 20 a year.

---

## Kitchener

**Meeting types (Q1)**

✅ How: `GetCalendarMeetings` month by month from 2021-01 to 2026-12, which returned 895 meetings. Counts per year:

| MeetingName | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Scope |
|---|---|---|---|---|---|---|---|
| Council Meeting | 4 | 9 | 12 | 11 | 12 | 10 | **in (council)** |
| Special Council Meeting | 10 | 27 | 30 | 27 | 24 | 23 | **in (council)**. Many are closed-session-only or budget meetings. |
| Finance and Corporate Services Committee | 7 | 10 | 21 | 17 | 15 | 11 | **in (committee)** |
| Planning and Strategic Initiatives Committee | 3 | 10 | 15 | 15 | 14 | 12 | **in (committee)** |
| Community and Infrastructure Services Committee | 3 | 8 | 13 | 13 | 13 | 11 | **in (committee)** |
| Audit Committee | – | 4 | 4 | 3 | 4 | 4 | optional. Its members are the whole council, but it had 0 recorded votes in the term. |
| Climate Change and Environment Committee | – | – | 4 | 10 | 10 | 7 | out (citizen members, so advisory; no video) |
| Striking Committee | – | 1 | – | – | – | – | out (one meeting, 2022-11-16) |
| Committee of Adjustment | – | 11 | 12 | 12 | 12 | 12 | out |
| Property Standards Committee | – | 4 | 10 | 9 | 11 | 6 | out (tribunal) |
| Dog Designation Appeal Committee | – | – | 2 | 5 | 4 | 3 | out (tribunal) |
| Licensing Tribunal | – | – | 1 | 1 | – | – | out |
| Heritage Kitchener Committee | – | 8 | 10 | 10 | 11 | 9 | out (advisory) |
| Active Transportation and Trails, Arts and Culture, Compass Kitchener, Downtown, Economic Development, Equity and Anti-Racism, GRAAC (all advisory) | | | | | | | out |
| Electronic Council Communication Information Package (2025+) | | | | | 30 | 43 | out (an info package, not a meeting) |
| My Ideal City | – | 1 | 1 | 1 | 1 | 1 | out |

- ✅ **No committee renames** between terms. The same three standing committees are already scheduled for 2026-11-30 and
  2026-12.
- ✅ **Calendar quirk:** each committee has extra entries timed `00:00` that have an agenda but never get minutes (in the
  term: 21 CIS, 11 FCS, 1 PSI). Treat "no minutes and 00:00" as a placeholder, not a missing meeting.
  - In-scope term totals: 108 Special Council, 45 Council, 64 FCS, 56 PSI and 50 CIS calendar entries. Of these, 106, 45,
    53, 55 and 29 have HTML minutes.

**Votes (Q2)**

✅ How: parsed all 288 in-scope minutes with BeautifulSoup.
- ✅ Vote labels in `TD.VoterVote` are "In Favour (n)", "Contra (n)" and **"Conflict (n)"** (9 rows). Nothing else.
- ✅ Results:
  - Recorded: "Carried, on a recorded vote (7 to 4)", "Carried, as amended, on a recorded vote (n to n)", "Carried,
    unanimously on a recorded vote (n to n)", "Carried (n to n)" and "LOST (n to n)".
  - Unrecorded: "Carried" (1,407), "Carried, as amended", "Carried, under Delegations" and "LOST". 217 motions have an
    empty result.
- ✅ Names in tables look like "Mayor B. Vrbanovic" and "Councillor S. Davey". A suffix " (virtually)" sometimes appears
  **inside the name cell**, so strip it.
- ⚠️ **Prose-recorded votes (important).**
  - Many recorded votes are not in a `MotionVoters` table. They are narrated in `.AgendaItemMinutes`, e.g. "…was LOST on a
    recorded vote, with Councillors D. Chapman and J. Deneault voting in favour; and, Mayor B. Vrbanovic and Councillors …
    voting in opposition."
  - This is typical for amendments and for clauses voted on separately.
  - In the term there are ~98 "on a recorded vote" mentions in prose and 42 "voting in opposition", which is **roughly as
    many split votes as the tables hold**.
  - Also, ~19 motions say "on a recorded vote" but have an empty `MotionVoters` table: mostly unanimous ones, but 4 are not
    (e.g. PSI 2023-10-02 and Council 2025-08-25). The names for those are in the prose nearby.
  - **The Kitchener adapter needs a prose vote parser**, and a vote audit that counts "recorded vote" mentions.
- ✅ Attendance header words: `Present:` (293 meetings), `Absent:` (120), `Staff:` (294) and once `Additional Staff:`.
  The format is "Present: Mayor B. Vrbanovic Councillor S. Davey … Absent: Councillor S. Stretch", with no commas.
- ✅ Committee attendance lists the whole council: FCS, PSI and CIS are committees of all members.

**Captions, bookmarks and Whisper (Q4)**

✅ How: player page `data-file_name`, then GET `video.isilive.ca/kitchener/<file>.vtt`.
- ✅ **No captions in any year.** `.vtt` returns 404 for Council 2022-12-19, 2023-03-20, 2023-10-16, 2024-04-08, 2024-11-18
  and 2025-06-23, FCS 2023-01-09, PSI 2024-01-22, CIS 2023-12-04 and Special Council 2024-01-08.
- ✅ Encoder file names change over time:
  - "New Encoder_Council Meeting_2022-12-19-07-03.mp4"
  - "New Encoder_CM_2023-…"
  - "Encoder 790_CM_2024-04-08-…"
  - "Compact Encoder_CM_2024-11-18-…"
  - The client id is always `kitchener`.
- ✅ Bookmarks are present in 128 of 151 council minutes and 101 of 137 committee minutes. Every sampled meeting had 5–36
  `AgendaItemId` entries.
- ✅ **Whisper timing** (`whisper_test.py`, same approach as `pipeline.whisper_range`), on Council 2026-09-28
  (`Compact Encoder_CM_2026-09-28-06-56.mp4`):
  - Recording: 8,410 s (2 h 20 min). The HLS playlist `#EXTINF` sum matched the WAV length.
  - Audio pull (ffmpeg over HLS, 16 kHz mono WAV, 269 MB): **373 s** (about 22× realtime).
  - mlx_whisper large-v3-turbo: **257 s (33× realtime)**, 1,659 segments and 22k words. The model was already cached.
  - **Total about 10.5 min per 2.3 h meeting.** On this machine the backfill of about 290 Kitchener in-scope meetings is
    roughly 30–50 h if all have video.
- ✅ Transcript quality:
  - The prose is good, e.g. "On motion by Councillor Johnson, the minutes of the regular meeting held August 24th and
    special meetings held August 24th and September 14th as mailed to the mayor and councillors be accepted."
  - **Names are poor:**
    - "Chaplin" for Chapman
    - "Deneau" for Deneault
    - "O'Dooney" for Owodunni
    - "Onitis" for Ioannidis
    - "Schneider" for Schnider
    - "Shingh" and "Seng" for Singh
    - "Verbanovic" for Vrbanovic
    - "Johnson" for Johnston
    - a hallucinated "Mayor Redekop"
  - Problems:
    - 10 min of pre-meeting silence came out as "Thank you." every 30 s (21 in a row).
    - One 3× repeat ("Councillor Onitis.").
  - Likely cause: with `condition_on_previous_text=False`, Whisper drops the `initial_prompt` after the first window.
    So the roster prompt only helps for the first 30 s.
  - Fix ideas:
    - VAD or trim to the first bookmark.
    - Fuzzy-map councillor names after transcription.
    - Pass the prompt per chunk.
    - These apply to Guelph's Whisper fallback too.

**Archive**
- ✅ eSCRIBE starts 2021-09-13, so it covers the term.

---

## Region of Waterloo

**Meeting types (Q1)**

✅ How: `GetCalendarMeetings` month by month, which returned 462 meetings. Counts per year:

| MeetingName | 2022 | 2023 | 2024 | 2025 | 2026 | First → last | Scope |
|---|---|---|---|---|---|---|---|
| Council Meeting | 7 | 11 | 11 | 11 | 11 | 2022-05-25 → | **in (council)** |
| Special Council | 6 | 10 | 8 | 11 | 19 | | **in (council)** |
| Emergency Special Council | – | – | – | 1 | – | 2025-03-06 | **in (council)** |
| Inaugural Council Meeting | 1 | – | – | – | – | 2022-11-23 | **in (council)**. No recorded votes. |
| Board of Health (Regional Council) | 2 | – | – | – | – | 2022-08 → 2022-12-14 | in (council sitting as BoH); 1 in the term |
| Administration and Finance | 7 | 11 | 11 | 11 | 11 | | **in (committee)** |
| Community and Health Services | 7 | 11 | 11 | 11 | 10 | | **in (committee)** |
| **Planning and Works** | 8 | 11 | 7 | – | – | → 2024-06-04 | **in (committee)**. **Renamed to:** |
| **Sustainability, Infrastructure, and Development** | – | – | 6 | 11 | 11 | 2024-08-13 → | **in (committee)** |
| Special Planning and Works / Special Sustainability, Infrastructure, and Development | – | 1 | – | 2 | – | | in (committee) |
| Planning and Works Regional Official Plan / … Statutory Public Meeting – ROPA | 2 | 1 | – | – | – | | in (committee); public meetings, few votes |
| **Strategic Planning and Budget Committee** | 1 | 13 | 7 | 5 | 1 | 2022-12-14 → | **in (committee of the whole on the budget)**. 247 split votes! |
| Strategic Planning and Budget Public Input Committee | – | 5 | 3 | 2 | – | | in or optional (delegations; 6 recorded, 0 split) |
| Strategic Planning and Budget Sub-committee | – | – | 4 | – | – | 2024-08 → 10 | optional (a subset; 0 recorded) |
| Audit Committee | 2 | 3 | 3 | 2 | 1 | | optional (5 councillors; 14 recorded, 0 split; its tables use the label "Carried") |
| Library Committee | – | 3 | 4 | 7 | 6 | | optional (township mayors only; 2 split) |
| Licensing and Hearings | 1 | 1 | 3 | 4 | 2 | | out (tribunal) |
| All Councils | – | 2 | 2 | 2 | 1 | | out (joint information session, 0 motions) |
| Nominating Panel, Order of Speakers Selection, Jack Young Civic Award Committee | | | | | | | out |
| Waterloo Regional Heritage Foundation (+ AGM), Active Transportation AC, Public Art AC, Ecological and Environmental AC, Heritage Planning AC, Economic Development Committee | | | | | | | out (advisory or boards) |

- ✅ The 2026–30 schedule already shows SID, A&F, CHS and SP&B (2026-12-08 and 12-16), so **the names carry into the new
  term**.
- ✅ **The archive starts 2022-03-28.** The first council-type meeting is 2022-05-25, and video starts June 2022, so the
  term is fully covered.

**Votes (Q2)**

✅ How: parsed all 265 in-scope minutes.
- ✅ Labels: "In Favor (n)" (1,772 rows), "Opposed (n)" (472), "Conflict" (26) and "Conflict:" (3).
- ⚠️ **Ballot-style tables.** The 2025-08-14 Special Council (filling the Kitchener regional councillor vacancy) has rows
  labelled with candidate names and percentages, e.g. "Joseph Gowing(53.33 %):", with the result "Majority Winner: Joseph
  Gowing". The parser must skip these (or treat them as an appointment).
- ✅ Results:
  - "Carried (n to n)" and "Defeated (n to n)" (149 defeated). Plain "Carried" is unrecorded.
  - Names have no titles ("B. Vrbanovic, J. Erb, … and K. Williams"). Ignore the empty spacer `<tr>` rows inside
    `MotionVoters`.
- ✅ **Correction to SOURCES.md: not "every vote since 2023".** Named votes start **August 2023**:

  | Period | Share of motions with named votes |
  |---|---|
  | Nov 2022 – Jun 2023 | about 2–28% (budget meetings were named) |
  | 2023 Q3 | 68% |
  | 2023 Q4 onward | 73–86% |

  - From Nov 2022 to Jul 2023 most votes are tally-only, "Carried (14 to 0)" with no names: 165 motions, 12 of them split.
  - After Aug 2023 the roughly 20% of motions that are unrecorded are mostly by-law readings, confirming by-laws and "For
    information" items marked only "Carried".
- ✅ **Nov–Dec 2022:** the Nov 15 Special Council, Nov 23 Inaugural, Dec 6 committees and Dec 14 Council had 0 named votes.
  Most results are tallies such as "Carried (15 to 0)". There were 2 named split votes, both at Administration and Finance
  (Nov 8, which is pre-term, and Dec 6).
- ✅ Attendance header words: `Members Present:` (306) and `Members Absent:` (179); comma-separated with a final "and".
  - "All Councils" meetings use `Attendance:` with "Kitchener Council:", "Regional Council:" and so on.
  - Some committees use plain `Present:`.

**Captions and bookmarks (Q3)**

✅ How: the player's `data-file_name`, then GET `video.isilive.ca/waterloo/<file>.vtt`. Client id `waterloo` was confirmed
on every sample.
- ✅ Captions return 200 for every sample:
  - Council: 2022-11-08, 2022-12-14, 2023-03-22, 2023-10-25, 2024-04-24, 2024-11-20, 2025-05-21, 2025-10-22, 2026-09-23.
  - A&F 2023-01-10, P&W 2022-06-07 and 2023-10-10, CHS 2024-01-16 and 2026-02-10, SID 2025-01-14.
  - Density is 88–174 words per minute, except Council 2022-12-14 at 49 wpm (sparse).
- ⚠️ **Early-2023 caption files are malformed.**
  - Affected: A&F 2023-01-10 and Council 2023-03-22.
  - The file has a header like "Wed Jan 11 2023 13:46:41 GMT…" and numbered cues **with no timestamps**.
  - Treat these as "captions without timing": use the text for search, and Whisper for timing.
  - ❓ How many meetings are affected. The window is probably about Jan–Mar 2023.
- ✅ Bookmarks were present in 252 of 265 in-scope minutes. Samples had 6–70 `AgendaItemId` entries.
- ✅ File names: "iSi Live Encoder 619_CM_…", "…_Council Meeting_2022-12-14-…", "…_AF_…", "…_PW_…", "…_CHS_…" and
  "…_Sustainability Infrastructure and Development_…".
- ❓ Video for the Strategic Planning and Budget Committee. No 2025 SP&B meeting had `HasVideo`; other years were not
  checked.

---

## Kitchener and Region rosters

**Kitchener 2022–26**

✅ How: minutes attendance and vote tables, plus kitchener.ca.

| Ward | Name | In minutes |
|---|---|---|
| Mayor | Berry Vrbanovic | Mayor B. Vrbanovic |
| 1 | Scott Davey | Councillor S. Davey |
| 2 | Dave Schnider | Councillor D. Schnider |
| 3 | Jason Deneault | Councillor J. Deneault |
| 4 | Christine Michaud | Councillor C. Michaud |
| 5 | Ayo Owodunni | Councillor A. Owodunni |
| 6 | Paul Singh | Councillor P. Singh |
| 7 | Bil Ioannidis | Councillor B. Ioannidis |
| 8 | Margaret Johnston | Councillor M. Johnston |
| 9 | Debbie Chapman | Councillor D. Chapman |
| 10 | Aislinn Clancy (to 2023-12-11, then elected MPP) → Stephanie Stretch (from 2024-01-22, appointed) | Councillor A. Clancy / Councillor S. Stretch |

- ⚠️ "D. Chapman" is also the Chief Administrative Officer (Dan Chapman), listed under `Staff:`. Parse attendance only
  before `Staff:`.

**Kitchener 2026–30**

✅ How: kitchener.ca "Official City of Kitchener 2026 … election results" (posted 2026-10-27).
- Mayor Berry Vrbanovic (4th term).
- Wards:

  | Ward | Name |
  |---|---|
  | 1 | Scott Davey |
  | 2 | Dave Schnider |
  | 3 | Jason Deneault |
  | 4 | Christine Michaud |
  | 5 | **Tracey Weiler** (new; Owodunni did not run; won by 7 votes over Rich Peers) |
  | 6 | Paul Singh |
  | 7 | Bil Ioannidis |
  | 8 | Margaret Johnston |
  | 9 | Debbie Chapman |
  | 10 | **Sam Nabi** (new; beat Stretch by 2,701 to 2,689) |

- **Sworn in 2026-11-23**, per the city, not Nov 15. The first regular Council meeting is 2026-12-14.
- ❓ Whether the 7-vote Ward 5 and 12-vote Ward 10 margins went to recounts. Wikipedia's tally for Ward 10 is inconsistent.

**Region 2022–26**

✅ How: `Members Present` blocks and vote tables. 16 members: Chair, 7 mayors, 8 regional councillors.

| Role | Name | In minutes |
|---|---|---|
| Regional Chair | Karen Redman | K. Redman |
| Mayor, Kitchener | Berry Vrbanovic | B. Vrbanovic |
| Mayor, Waterloo | Dorothy McCabe | D. McCabe |
| Mayor, Cambridge | Jan Liggett | J. Liggett |
| Mayor, North Dumfries | Sue Foxton | S. Foxton |
| Mayor, Wellesley | Joe Nowak | J. Nowak |
| Mayor, Wilmot | Natasha Salonen | N. Salonen |
| Mayor, Woolwich | Sandy Shantz | S. Shantz |
| Regional Councillor, Cambridge | Doug Craig, Pam Wolf | D. Craig, P. Wolf |
| Regional Councillor, Waterloo | Jim Erb, Chantal Huinink | J. Erb, C. Huinink |
| Regional Councillor, Kitchener | Colleen James, Michael Harris | C. James, M. Harris |
| Regional Councillor, Kitchener | Rob Deutschmann (last seen 2024-12-20) → **Matt Rodrigues** (from 2025-03-28) | R. Deutschmann / M. Rodrigues |
| Regional Councillor, Kitchener | Kari Williams (last seen 2025-04-23) → **Joe Gowing** (chosen by ballot 2025-08-14; seated 2025-08-27) | K. Williams / J. Gowing |

- The replacement pairings are inferred from first and last attendance dates. ❓ Confirm who replaced whom, and why.

**Region 2026–30**

✅ How: regionofwaterloo.ca election results page and its official PDF.
- The Regional Chair is **provincially appointed** (Better Regional Governance Act, 2026). ❓ Who was appointed: no
  announcement found as of 2026-11-09.
- Regional Councillors:
  - Kitchener: Colleen James, Michael Harris, Matt Rodrigues, Joe Gowing.
  - Waterloo: Jim Erb, Chantal Huinink (beat Chris Moser by 3 votes).
  - Cambridge: Doug Craig, Pam Wolf.
- Mayors:

  | Municipality | Mayor | Status |
  |---|---|---|
  | Kitchener | Berry Vrbanovic | |
  | Waterloo | **Shannon Weber** | new |
  | Cambridge | **Scott Hamilton** | new |
  | North Dumfries | **Rodney Rolleman** | new |
  | Wellesley | **Chris Martin** | new |
  | Wilmot | **Kristopher Wilkinson** | new |
  | Woolwich | **Evan Burgess** | new |

- ❓ The Region's inaugural meeting date. Nothing in eSCRIBE yet; the next Council Meeting is 2026-12-16.

**Portraits and licence**
- ✅ Kitchener:
  - Each councillor has a page at
    `kitchener.ca/council-and-city-administration/mayor-and-council/city-council/councillor-<first>-<last>/`
    with a headshot, e.g. `/media/ehvdipyw/cor_omc_sd_headshot.jpg`, alt "Headshot of Councillor Davey".
  - No photo credit is given.
  - The site's "Website policy" says nothing about reuse; the footer only says "© 2026 City of Kitchener".
  - The pages still show the 2022–26 council.
- ✅ Region:
  - Member pages at `regionofwaterloo.ca/government-and-council/council/council-members/councillor-<first>-<last>/`
    have portraits, e.g. `media-003-ca.cdn.govstack.com/regionofwaterloo-018-ca/media/yh2bo4jt/berry-vrbanovic-websize.jpg`.
    No credit is given.
  - Website Terms of Use: content is owned by the Region; copying is allowed for "personal, educational or non-commercial
    use"; other reproduction needs prior written consent. Attribution is not mentioned.
- Recommendation: link to or hotlink the official pages, or ask both clerks for written permission. Wikimedia Commons was
  not checked.

---

### Kitchener and Region: surprises and parser implications
1. **Kitchener's prose votes.** About half of Kitchener's split recorded votes are only in narrative text. Without a prose
   parser Kitchener has 38 split votes in the term; with one, about 80.
2. **Region named voting starts Aug 2023, not Jan 2023.** For Nov 2022 – Jul 2023 there are tallies without names.
3. **The Region's budget committee (Strategic Planning and Budget) holds 247 of the 470 split votes.** It must be in
   scope, and it will dominate "who votes with whom" unless weighted or filtered.
4. **Region ballot tables** for appointments (candidate names as labels) and Audit Committee tables labelled "Carried".
5. **Early-2023 Region VTTs have no timestamps.**
6. **Whisper names are weak** because the initial prompt is dropped after the first window when
   `condition_on_previous_text=False`. This affects Guelph's fallback too.
7. **Minutes HTML is heavy:** 98 MB for this one term of two councils (Kitchener 45 MB, Region 53 MB). Revisit the 250 MB
   estimate in PLAN 4.11.
8. **Kitchener's new council is sworn in Nov 23**, not Nov 15, and two seats changed (Wards 5 and 10).

---

## Waterloo (city)

_Phase 0 spike, 2026-11-09. Scripts in `docs/multicity/spikes/waterloo_cw/` (they cache to a local `dl/` folder)._

### Waterloo and Centre Wellington counts (2022-26 term, to 2026-11-09)

| | Waterloo Council | CW Council | CW Committee of the Whole |
|---|---|---|---|
| Meetings held (not cancelled) | 113 | 80 (incl. 1 orientation) | 28 |
| Minutes PDFs posted and parsed | 111 | 78 | 22 |
| Motions (outcome lines) | 1,346 | 1,061 | 115 |
| "Moved by" lines | 1,333 | 1,073 | 118 |
| Recorded votes (all members named) | 11 requested, 10 unanimous + 2 split named in full | **10** | 0 |
| **Split votes with names** | **60** (dissenters named on every divided vote) | **9** | 0 |
| Recorded/split per year | 2022: 0 · 2023: 10 · 2024: 24 · 2025: 18 · 2026: 8 | 2024: 8 · 2025: 1 · 2026: 0 (+1 unanimous) | 0 |
| Videos on YouTube | 107 of 113 meetings (40 in two parts) | 76 of 80 | 19 of 28 |

The vote counts come from `docs/multicity/spikes/waterloo_cw/wl_analyze.py` and `cw_analyze.py` run over every minutes PDF in the
window. They are regex counts, not a full parse, but every block found was read by eye.



**Listing meetings: solved**
- ✅ The `/meetings/Index` search form POST works (`docs/multicity/spikes/waterloo_cw/wl_enumerate.py`, tested for 2022–2026 with both calendars).
  1. `GET https://events.waterloo.ca/meetings` in a `requests.Session`. This sets the cookies
     `__RequestVerificationToken` and `<guid>_Previous`. The page has **two** hidden `__RequestVerificationToken`
     inputs, and either one works.
  2. `POST https://events.waterloo.ca/meetings/Index` with the same session, header `Referer: …/meetings`, and form
     fields:
     - `__RequestVerificationToken=<token from the page>`
     - `StartDate=01/01/2023`, `EndDate=12/31/2023` (MM/DD/YYYY)
     - `Calendar=` one of `""` (all), `Council Calendar`, `Committee Calendar`
     - `Keywords=`
     - `Page=0` (0-based)
  3. The response has `.resultsNumber` ("31 Results Found") and **25 rows per page**. Each `tbody tr` holds:
     - `td[headers=c1]`: the date and time text
     - `td[headers=c2] a`: the meeting name and `/meetings/Detail/{slug}`
     - one cell per document column (`Agenda`, `Revised Agenda`, `Minutes`, `Packet`, `Revised Packet`); the
       column names come from the `thead th` ids.
  4. Without the session cookie the POST returns an "Error" page. "All" for 2023 gives 111 = 31 Council + 80
     Committee, so the two calendars cover everything.
- ✅ Document links `/meetings/Detail/{slug}/{GUID}` return `application/pdf` directly, with no viewer page.
- ✅ The slug fallback is not needed. Slugs are irregular anyway (`…-Committee-of-Adjustment-Meeting2`,
  `INAUGURAL-MEETING`).
- ✅ Cancelled meetings stay listed with "CANCELLED" in the name and no documents.

**Meeting types and scope**
- ✅ Council Calendar, 2022-11-15 → now: Council Meeting (106 held), Special Council Meeting (5), INAUGURAL
  MEETING (2022-11-21), All Council Meeting (2024-12-06), and 6 cancelled. Upcoming: Inaugural 2026-11-16,
  Council 2026-12-07 and 2026-12-14.
- ✅ The Committee Calendar holds advisory committees, Committee of Adjustment, Sign/Fence Variance, Municipal
  Heritage and similar.
  - **There is no Committee of the Whole or other standing committee in the 2022–26 term.** CoW and Finance &
    Strategic Planning existed in 2018–22 (seen in YouTube titles), and an Audit Committee met three times in
    2022, the last on Nov 3, 2022.
  - **In scope for Waterloo: the Council Calendar only.**
- ❓ Whether "All Council Meeting" (2024-12-06) is a joint regional meeting worth excluding. It has minutes.
- Minutes are missing for 2023-05-29 (agenda only). The 2026-11-02 minutes are not posted yet.

**Votes** (all 111 minutes PDFs downloaded, 78 MB, and extracted with pdfplumber; 264k words)
- ✅ Outcome lines:
  - "Carried Unanimously" 1,285
  - "Carried" 42
  - "Motion Failed" 16
  - "Motion Defeated" 3
- ✅ **A plain "Carried" (or "Motion Failed") always means a divided vote, and it is always followed by a tally plus
  the dissenters' names**, even when no recorded vote was requested:
  ```
  Carried
  7 Voting in Favour
  1 Voting in Opposition
  (COUNCILLOR ROACH)
  ```
  - Tally labels vary: `N Voting in Favour`, `N Voted in Favour`, `N Voted in Favor`, and the matching
    `… in Opposition`.
  - The names in parentheses are those **in opposition**. A 4–4 tie that fails lists the 4 "opposition" names.
  - All 42 plain "Carried" lines have a tally, and the name count equals the opposition count in all 60 split
    votes. The single exception is "Motion Failed / Council unanimously voted against the motion" on 2024-02-12.
  - So `unanimous` can be inferred safely: "Carried Unanimously" means everyone present voted yes. On a split
    vote, the yes side is everyone present minus the named dissenters, minus anyone with a declared conflict.
    That needs the attendance and left/joined tracking to be right.
- ✅ Requested recorded votes: 11 ("Mayor McCabe requested a recorded vote." ×10, Freeman ×1).
  - When one is requested, the `Voting in Favour` names are listed as well.
  - 2 of the 11 are split (2025), e.g. 2025-06-16: 4 in favour (named), 3 in opposition (named).
- ✅ Split votes per member (named in opposition, 2022–26): Roach 35, Bodaly 27, Vasic 26, Wright 18, Roe 15,
  Freeman 12, Hanmer 11, McCabe 10.
- ✅ Abstention is rare. Once (2023-02-13): "Councillor Roe abstained from voting, and, in accordance with the
  Municipal Act …" (deemed a negative vote).
- ✅ Name formats:
  - PRESENT/ABSENT blocks use full names ("Councillor Royce Bodaly"), wrapped over several lines, with
    "(Time: 3:02 p.m.)" for late arrivals.
  - Motions use "Moved by Councillor Roe, Seconded by Councillor Roach:". Variants: lower-case "seconded" (17),
    a missing comma (6), ";" (2), "Moved by Mayor," (1), "Council Vasic" (1).
  - Vote names are upper case in parentheses: `(COUNCILLOR ROACH)`, `(MAYOR McCABE)` / `(MAYOR MCCABE)`.
- ✅ Left/joined lines: 476, e.g. "Councillor Freeman joined the meeting. (Time: 3:02 p.m.)". There are also
  "… left the Chair", "… in the Chair", and "having previously declared a pecuniary interest was absent for the
  taking of the vote".
- ✅ There is a running **header only, no footer**: `September 8, 2025 Page 150 Council Meeting` at the top of every
  page. Page numbers run on through the year. It can land inside a name list; regex
  `^[A-Z][a-z]+ \d{1,2}, \d{4} Page \d+ .*Meeting$`.
- ✅ Each minutes PDF covers both sessions (closed at 2 pm and public at 3 pm / 6:30 pm), with recess and reconvene
  lines and a second PRESENT block.

**Video**
- ✅ `yt-dlp --flat-playlist -J https://www.youtube.com/channel/UCVP6QGtoGy5jmMkKhE3FRPA/streams` lists 397 streams
  (the `/videos` tab has 9 more), back to 2016. **The whole term is covered.**
- ✅ Title patterns:
  - since 2022: `City of Waterloo Council Meeting {Month D, YYYY} @ {H:MM}PM`, with occasional `@3:00 PM` / `AM`
  - `City of Waterloo Special Council Meeting …`
  - `City of Waterloo Inaugural Council Meeting November 21, 2022 @ 6:30PM`
  - before 2022, also `- Part N`, `Pt N` and `{Month D, YYYY} Waterloo City Council Meeting @ …`
  - 11 untitled "Waterloo City Council Live Stream" items, all old
  - Flat listings carry no upload date, so match on the date in the title.
- ✅ Matching by title date: 107 of 113 meetings have video. 67 have one video and 40 have two (afternoon and
  6:30 pm parts).
  - With no video: Special 2023-09-06, 2023-12-18 and 2025-10-15 (probably closed only), All Council 2024-12-06,
    Council 2025-04-07 and 2026-01-12.
  - Some "parts" are very short (90–800 s, the closed-session open).
  - Total about 272 hours.
- ✅ Auto-captions for Sep 8, 2025 3:00 PM (`gebmFBf08Jo`, 116 min), track `en-orig` json3, 2 MB:
  - 19,276 words, **166 wpm**, no long gaps
  - punctuated and cased, with `>>` marking a change of speaker
  - Sample: "…is there any um protection for them under eight stories then? … >> through through the chair without
    the rental replacement bylaw in place at this point in time? I would have to say say no…"
  - Names are rarely spoken: McCabe 8, Freeman 21, Wright 9, Hanmer 3; Bodaly and Vasic 0. Some are garbled
    ("McKibb").
  - Good enough for search and summaries. Not usable for attributing votes.
- ✅ Throttling: the listing and the `en-orig` caption download were instant. **The second track (`en`, a translated
  copy of the same ASR) returned HTTP 429.** Request only `--sub-langs en-orig` (or `en`, not both) and add
  `--sleep-subtitles`.
  - yt-dlp warns that "no impersonate target is available"; `pip install curl_cffi` may reduce 429s.
  - ❓ Behaviour over a 200-video backfill.

**Rosters**
- ✅ 2022–26 (from waterloo.ca "Find your councillor and ward", still showing the old council on 2026-11-09):

  | Seat | Member |
  |---|---|
  | Mayor | Dorothy McCabe |
  | Ward 1 | Sandra Hanmer |
  | Ward 2 | Royce Bodaly |
  | Ward 3 | Hans Roach |
  | Ward 4 | Diane Freeman |
  | Ward 5 | Jen Vasic |
  | Ward 6 | Mary Lou Roe |
  | Ward 7 | Julie Wright |

- ✅ 2026–30, from the official certificate (PDF, Clerk Julie Finley-Swaren, dated 2026-10-27; linked from
  `/council-and-committees/municipal-elections/2026-elections-results/`):

  | Seat | Member | Note |
  |---|---|---|
  | Mayor | **Shannon Weber** | 15,002 votes to McCabe's 8,623 |
  | Ward 1 | Sandra Hanmer | |
  | Ward 2 | **Shawn Humes** | new; Bodaly did not run |
  | Ward 3 | **Victoria Robertson** | beat Roach |
  | Ward 4 | Diane Freeman | |
  | Ward 5 | **Scott Piatkowski** | new; Vasic did not run |
  | Ward 6 | Mary Lou Roe | |
  | Ward 7 | Julie Wright | |

  The Regional Councillor results are on the same certificate (Jim Erb first, 13,994). Their seat count belongs to
  the Region's spike. 4 of 8 members are returning.
- ✅ Portraits: each ward page (`/council-and-committees/mayor-and-city-council/ward-N-councillor/`, `mayor-of-waterloo/`)
  has a headshot, e.g. `media-002-ca.cdn.govstack.com/waterloo-013-ca/media/34mfbnma/councillor-hanmer.jpg`.
  - ❓ Licence: the Terms of use say nothing about reuse. Treat them as all rights reserved and ask
    council@waterloo.ca.
  - The new members' pages are not up yet.

---

## Centre Wellington (CivicWeb)

**Document tree**
- ✅ `/filepro/documents/5559` (Council minutes) has one folder per year: 2022 `44854`, 2023 `52504`, 2024 `59304`,
  2025 `71390`, 2026 `80290`.
- ✅ `/filepro/documents/5551` (Committee of the Whole): 2022 `45606`, 2023 `51866`, 2024 `61943`, 2025 `77687`.
  **There is no 2026 folder**, and the last CoW was 2025-11-10.
- ✅ Each folder page lists `href="/document/{id}"` with link text
  `{Meeting Name} - {DD Mon YYYY} - Minutes - Pdf`.
  - 2022 also has `- Minutes - Html` duplicates; skip them.
  - One badly spaced name: `Committee of the Whole (Budget)- 19 Sep 2024 - Minutes - Pdf`.
  - No pagination was seen; the largest folder has 23 items.
- ✅ `GET /document/{id}` returns the PDF directly (`content-disposition: inline; filename="Council - 24 Aug 2026 -
  Minutes - Pdf.pdf"`).
- ✅ **A reliable meeting→minutes mapping exists through JSON** (found in `/js/webforms/portal/meetings`):
  - Meeting list per type: `GET /Portal/MeetingInformation.aspx?type=18` (Council) or `?type=10` (CoW). The left
    pane has every meeting back to 2015 as
    `<button id="ctl00_MainContent_MeetingButton{MeetingId}">…<div class="meeting-list-item-button-date">24 Aug 2026</div><div … title="Council ">`.
    That gives 193 Council meetings and 129 CoW meetings.
  - `GET /Services/MeetingsService.svc/meetings/{MeetingId}/meetingData` returns `{Id, Name:"Council - 24 Aug 2026",
    Time:"05:00 PM", TypeId:18, Location}`.
  - `GET /Services/MeetingsService.svc/meetings/{MeetingId}/meetingDocuments` returns a list of `{Id, DocumentType,
    MeetingId, Name, IsPublic}`. **`DocumentType 10` = published minutes PDF** (its `Id` is the `/document/{id}`;
    e.g. meeting 1002 → document 83103), 1 = agenda HTML, 4 = agenda PDF. The type enum is in the page JS
    (`publishedMinutesOpenPdf:10`).
  - `GET /api/videolink/{MeetingId}` returns `[{"YouTube":true,"YouTubeEventId":"fHOHy0_PO7I","IndexPoints":"",…}]`.
    **This gives the YouTube video for each meeting directly.** `IndexPoints` is empty, so there are no agenda
    timestamps.
- Recipe: list the meetings from the type page, then call `meetingDocuments` and `videolink` for each one (2 requests
  per meeting). The folder crawl works as a cross-check; its names match the meeting names exactly.
- Other meeting types (from `/Portal/MeetingTypeList.aspx`) are out of scope:
  - Committee of Adjustment (21)
  - advisory committees (24, 26, 30, 33)
  - Public Meeting Under the Planning Act (25)
  - Heritage Centre Wellington (19)
  - EDTMSC corporation board (34)
  - Joint Compliance Audit, Property Standards Appeal, Economic Development Task Force (ended 2022), Ad Hoc
    Procedure By-law (2021)

**In-scope types, 2022-11-15 → now** (from the type pages):

| Year | Council (type 18) | Committee of the Whole (type 10) |
|---|---|---|
| 2022 | Council 2 (incl. inaugural 21 Nov), Council Orientation 1 | CoW 3 |
| 2023 | Council 16, "Council - 26 Jun 2023 - Part 2" 1 | CoW 14, Strategic Planning Workshop 1, "(continued)" 1 |
| 2024 | Council 20, Special Council 1 | CoW 1, CoW (Budget) 2, Budget CoW 1, Econ Dev & Tourism Strategy Workshop 1 |
| 2025 | Council 21, Council (Budget) 2 | CoW 4 |
| 2026 | Council 14, Special Council 2 | (none) |

- In 2023, CoW met roughly every other week alongside Council. From 2024 it is used only for budget and workshops.
  So "Committee of the Whole" is in scope but small.
- No renames other than the budget variants. Treat "Council Orientation" and the workshops as out of scope (no
  motions).
- Minutes not posted: Council 2026-09-28. 6 CoW meetings have no minutes PDF in the folder.

**Votes** (100 PDFs downloaded: 78 Council, 22 CoW)
- ✅ Outcomes:
  - Council: `CARRIED` 1,042; `CARRIED, as amended` 13; `DEFEATED` 4; `WITHDRAWN` 1; `CARRIED on a Recorded Vote of 7-0` 1
  - CoW: 114 CARRIED, 1 as amended
- ✅ **A plain `CARRIED` says nothing about unanimity**: no tally and no names unless a recorded vote is requested. No
  "unanimous" wording appears anywhere.
- ✅ Recorded votes: **10 in the term (all Council, none in CoW), 9 of them split.**
  - 2024-01-29 (5–1)
  - 2024-02-12 ×2 (3–2 with 1 abstained, then 4–2)
  - 2024-05-27 ×3 (6–1, 6–1, 2–5)
  - 2024-06-24 (one with 2 members missing a vote word)
  - 2024-10-15 (2–3)
  - 2025-05-26 (5–1)
  - 2026-08-24 (7–0)
  - None in 2022–23.
- ✅ The request wording varies: "requested a recorded vote" / "asked for a recorded vote" / "called for a Recorded
  Vote" / "requested a recorded vote for this item". It usually comes **before** the "Moved by".
- ✅ The vote list comes after the outcome; the newest format puts it before "CARRIED on a Recorded Vote of 7-0":
  ```
  CARRIED
  Mayor Shawn Watters For
  Councillor Lisa MacDonald For
  Councillor Barbara Lustgarten- Against
  Evoy
  Councillor Denis Craddock Abstained
  ```
  - The table's second column comes out at the end of the line.
  - "Lustgarten-Evoy" wraps, so "Evoy" lands alone on the next line.
  - The 2026 format uses surnames for some members ("Councillor Wilton For", "Councillor Craddock For") and full
    names for others.
  - 2024-06-24 has rows with an empty vote cell (Mayor, Jefferson), probably not voting.
- ✅ An oddity: on 2024-03-25 "Councillor Wilton noted the recorded vote was omitted from the January 29th minutes".
  The posted Jan 29 PDF does include the block, so the PDF was revised after the fact. Minutes PDFs can change.
- ✅ Name formats:
  - Motions: "Moved by Councillor Bronwynne Wilton, Seconded by Councillor Lisa MacDonald." (full names, ends with a
    period, often wrapped mid-name)
  - Narrative: "Mayor Watters", "Councillor Adams joined the meeting at approximately 5:01 p.m." (64 left/joined
    lines in Council)
  - Attendance: `PRESENT:` with one member per line, then `REGRETS:` and `STAFF:`
- ✅ Headers and footers: a footer `Page N of M`, then a header on the next page `Council Minutes August 24, 2026`
  (or `Committee of the Whole Minutes …`). Both break into vote blocks. The header is not a first-page header; the
  first page starts "Township of Centre Wellington / Council Minutes / Monday, August 24, 2026".

**Video**
- ✅ `…/channel/UCNtoKR8bjPIx9giRQXnK50A/streams` has 290 items, back to 2016-01-18. `/videos` has 116 more (mostly
  promotional).
- ✅ Title patterns: `Council - 24 Aug 2026` (118), an older variant without the hyphen `Council   24 Aug 2026` (33),
  `Committee of the Whole - …`, `Special Council - …`, `… (Part 1)`, `Council (Budget) - …`.
- ✅ Coverage in the term:
  - Council: 76 of 80 meetings have video; 3 have two parts and 2 have three items, often a "Public Meeting Under the
    Planning Act" on the same day.
  - Missing: Special Council 2026-05-21, Council 2026-04-13, 2024-01-11, and the Orientation.
  - CoW: 19 of 28.
- ✅ **No renovation gap.** The only gaps over 40 days are summer and holiday breaks (Jul–Sep 2024, Dec–Jan).
- ✅ Auto-captions for Council 2026-08-24 (`fHOHy0_PO7I`, 283 min), `en-orig` json3, 2.4 MB:
  - 22,747 words
  - the stream runs through closed session, leaving a **124-minute silent gap** at minute 5; speech density is about
    155 wpm outside it
  - punctuated, with `>>` turns
  - The spoken recorded-vote roll call is captured: "…I ask for a recorded vote… Councelor Wilton, >> yay.
    >> Councelor Kratic, >> yay. >> Councelor McDonald… Councor Eboy. >> Yay… >> Waters. >> Yay." So the names
    are mangled (Watters→"Waters" ×31, Craddock→"Kratic", Lustgarten-Evoy→"Eboy").
  - Fine for search and summaries, but captions need a name-alias pass.
- ✅ The two caption downloads above did not trigger a 429. That came only from the extra `en` track on the Waterloo
  video.

**Rosters**
- ✅ 2022–26 (centrewellington.ca/township-services/mayor-and-council/, "has been serving Ward N since 2022"):

  | Seat | Member |
  |---|---|
  | Mayor | Shawn Watters |
  | Ward 1 | Lisa MacDonald |
  | Ward 2 | Kimberley Jefferson |
  | Ward 3 | Barbara Lustgarten-Evoy |
  | Ward 4 | Jennifer Adams |
  | Ward 5 | Bronwynne Wilton |
  | Ward 6 | Denis Craddock |

- ✅ 2026–30, from the official EL08 certificate (Clerk Tyler Sager, 2026-10-27, `media-001-ca.cdn.govstack.com/centrewellington-004-ca/media/0akptfpu/el08-certificate-of-election-results.pdf`):

  | Seat | Member | Note |
  |---|---|---|
  | Mayor | **Bronwynne Wilton** | 4,731; Dunsmore 2,736, Linton 2,252, Watters 1,912, Kitras 953 |
  | Ward 1 | **Sophie Hogan** | beat MacDonald |
  | Ward 2 | **Darcy Saunders** | beat Jefferson |
  | Ward 3 | Barbara Lustgarten Evoy | written **without the hyphen** on the certificate |
  | Ward 4 | Jennifer Adams | |
  | Ward 5 | **Julie Charbonneau** | Wilton's old ward |
  | Ward 6 | **Richard Pinder** | Craddock did not run |

  The incumbent mayor lost and only 2 councillors return. Wilton changes role from Ward 5 councillor to Mayor, so the
  alias table must be keyed per term.
- ✅ Portraits: the township page has images (e.g. `/media/feugjwkn/web_shawn_1650.png`,
  `/media/qvmc52mk/web_bronwynne_1560.png`) with empty alt text. ❓ Licence: only a privacy policy is linked; ask the
  Clerk.
- ❓ The CW inaugural meeting date for 2026–30 (not in the type-18 list yet; expected on or after 2026-11-15). Also
  `/portal/members.aspx?id=18` (CivicWeb members list) was not checked.

---

**Still open (Waterloo, Centre Wellington)**

- ❓ How YouTube rate-limits a full caption backfill (about 200 Waterloo videos and about 100 CW videos).
- ❓ Whether the Waterloo yes-side inference (present − dissenters − conflicts) reconciles with the tally numbers
  for all 60 split votes. The tally numbers make this checkable automatically.
- ❓ Portrait licences for both councils.

---

## Not in scope (for reference)

- **Wellington County** (upper tier for Centre Wellington): eSCRIBE `https://pub-wellington.escribemeetings.com`;
  YouTube `CountyofWellington`. Vote-recording practice ❓.
