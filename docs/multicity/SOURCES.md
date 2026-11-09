# Council data sources

How each council publishes minutes, votes and video. ✅ means checked against a live page, ❓ means not yet
verified (a Phase 0 spike). Last research: 2026-11-09. All city sites listed here except Guelph's return 403 to
bare HTTP clients; a normal browser User-Agent works.

---

## Guelph (existing)

- ✅ eSCRIBE `https://pub-guelph.escribemeetings.com`. Meetings come from `GetCalendarMeetings`; type "City Council".
- ✅ HTML minutes; named votes on most motions ("Voting in Favour …").
- ✅ ISI video, client `guelph`; captions at `https://video.isilive.ca/guelph/<file>.vtt`; HLS at
  `https://sp2hls.isilive.ca/hls/file/guelph/<file>/index.m3u8`. Agenda item to video times come from the `Bookmarks`
  in the minutes page.

---

## Kitchener

**Minutes**
- ✅ eSCRIBE `https://pub-kitchener.escribemeetings.com`.
  - `PastMeetings` POST `{"type":"Council Meeting","pageNumber":N}` returns 50 per page.
  - `GetCalendarMeetings` works one month at a time.
- ✅ The archive starts September 2021, so it covers the whole date range. Older minutes are in Laserfiche
  (`lf.kitchener.ca/WebLinkExt`); they are not needed.
- ✅ Minutes are HTML: `Meeting.aspx?Id={guid}&Agenda=PostMinutes&lang=English`. There are 22 meeting types; in scope
  is "Council Meeting".

**Votes**
- ✅ Recorded votes appear as `TABLE.MotionVoters`: `TD.VoterVote` "In Favour (n)" / "Contra (n)", and `TD.VotesUsers`
  with names ("Mayor B. Vrbanovic, Councillor S. Davey, …,  and Councillor S. Stretch").
- ✅ The result is in `DIV.MotionResult`, e.g. "Carried, on a recorded vote (7 to 4)".
- ✅ Recorded votes are rare. 2026 Council: 4 recorded out of 188 results, and 1 split vote. Unrecorded motions say only
  "Carried" (also "as amended" or "under Delegations"). It never says "Carried unanimously" without a recorded vote.
- ✅ Committee reports are adopted as a bundle (e.g. 7.1 covers 7.1.a–g); an item can be split out for a recorded vote.
- ✅ Conflicts appear as text: "Councillor X declared a pecuniary interest on Item …", with an icon
  `PublishConflict`.
- ✅ Attendance header: "Present: Mayor B. Vrbanovic Councillor S. Davey … (virtually) …".

**Video**
- ✅ ISI, `data-client_id="kitchener"`, files like `Compact Encoder_CM_2026-09-28-06-56.mp4`. HLS answers (307).
- ✅ **No captions**: `.vtt` returns 404 for Sep 2026 and Nov 2025. Transcripts need Whisper.
- ✅ Bookmarks exist (`video.Bookmarks = [{AgendaItemId, TimeStart, TimeEnd}]`, in ms).
- Before about August 2022 the video was on YouTube; that is outside the range.

---

## Region of Waterloo

**Minutes**
- ✅ eSCRIBE `https://pub-regionofwaterloo.escribemeetings.com`. `GetCalendarMeetings` works.
- ✅ Types include "Council Meeting", "Special Council", "Administration and Finance", "Community and Health Services",
  "Sustainability, Infrastructure, and Development", "Licensing and Hearings" and advisory bodies.
- ❓ When the eSCRIBE archive starts. The legacy archive covers 2011 to May 2022, so eSCRIBE should cover the range.

**Votes**
- ✅ Every motion has a `MotionVoters` table: "In Favor (14) B. Vrbanovic, J. Erb, … Carried (14 to 0)". Names have
  no "Councillor" title. The spelling is "Favor".
- ✅ The Region has recorded all council and committee votes since 2023.
- ❓ What Nov–Dec 2022 minutes look like.

**Video**
- ✅ ISI with **`data-client_id="waterloo"`** (not "regionofwaterloo"); files like
  `iSi Live Encoder 619_CM_2026-09-23-05-28.mp4`.
- ✅ Captions return 200 at `https://video.isilive.ca/waterloo/<file>.vtt`; HLS answers.
- ❓ Captions in earlier years.

**Members**
- Regional Chair, 7 mayors (including Kitchener's and Waterloo's) and regional councillors elected from Kitchener,
  Waterloo and Cambridge. People overlap with the city councils; link people across councils later (optional).

---

## Waterloo (city)

**Minutes**
- ✅ GovStack calendar at `https://events.waterloo.ca/meetings`.
  - Meeting pages: `/meetings/Detail/{YYYY-MM-DD-HHMM-Meeting-Name}`, e.g. `2025-12-01-1400-Council-Meeting`.
  - Documents: `/meetings/Detail/{slug}/{GUID}`; the `aria-label` names the document ("… Minutes Council
    Meeting.pdf").
- ✅ Each meeting has an Agenda, Revised Agenda, Minutes and Packet.
- ✅ Minutes are PDF only, created digitally (Word to PDF), so the text extracts cleanly. Page numbers run on through
  the year.
- ✅ The archive goes back to at least 2019.
- ❓ **Listing meetings:** `/meetings/Index` search is a POST with an anti-forgery token (`StartDate`, `EndDate`,
  `Calendar`, `Keywords`, `Page`); GET parameters are ignored. A fallback is slug guessing from YouTube titles.

**Votes**
- ✅ The default is "Moved by Councillor X, Seconded by Councillor Y: … Carried Unanimously".
- ✅/❓ Recorded votes read "Voted in Favour: … / Voted in Opposition: …". This was seen in search-indexed text for
  Sep 8, 2025, not yet in a PDF.
- ✅ Attendance is PRESENT / ABSENT lists, plus timed "Councillor X left/joined the meeting".
- ❓ Whether non-unanimous unrecorded votes always say plain "Carried". This decides the `unanimous` inference (D4).

**Video**
- ✅ YouTube channel `UCVP6QGtoGy5jmMkKhE3FRPA` (@citywaterloo). RSS:
  `https://www.youtube.com/feeds/videos.xml?channel_id=UCVP6QGtoGy5jmMkKhE3FRPA`.
- ✅ Titles look like "City of Waterloo Council Meeting {Month D, YYYY} @ {H:MM}PM"; there are often two parts
  (3:00 and 6:30 PM).
- ✅ YouTube auto-captions exist (3 of 3 checked). There is no description, no chapters and no agenda timestamps.
- Meeting pages link only the generic `/live` URL, so videos must be matched by title and date.
- ❓ How far back the uploads go (needed: Nov 2022). Rogers TV also airs meetings (not needed).

**Watch out:** search results mix in the Region of Waterloo, Waterloo IL and Waterloo IA. The "Recorded Votes 2015"
open dataset is the Region's.

---

## Centre Wellington (Fergus, Elora)

**Minutes**
- ✅ CivicWeb `https://centrewellington.civicweb.net`.
  - Meetings: `/Portal/MeetingInformation.aspx?Id=N` (Council type 18).
  - Document tree: `/filepro/documents`. Council minutes are in `/filepro/documents/5559`, one folder per year
    2015–2026 (2026 = `/80290`). Committee of the Whole is in `/5551`.
- ✅ Minutes are PDF only, created digitally, posted 2–6 weeks after the meeting. Newest on 2026-11-09:
  2026-08-24.
- ❓ A reliable way to match a minutes PDF to a meeting date. Probably the file name or title; confirm in the spike.

**Votes**
- ✅ Motions read "Moved by Councillor X, Seconded by Councillor Y. THAT … CARRIED".
- ✅ Recorded votes read: "Councillor A requested a recorded vote", then one line per member ("Councillor Wilton
  For", "Mayor Shawn Watters For"), then "CARRIED on a Recorded Vote of 7-0". Seen: 1 of about 29 motions on
  2026-08-24.
- ✅ Watch out:
  - Name formats vary inside one vote block, so map names through aliases.
  - Page headers and footers interrupt vote blocks.
  - The PRESENT / REGRETS attendance block can be parsed.
- 2022–26 council: Mayor Shawn Watters; Councillors Lisa MacDonald, Kimberley Jefferson, Barbara Lustgarten-Evoy,
  Jennifer Adams, Bronwynne Wilton, Denis Craddock. The 2026–30 council is ❓.

**Video**
- ✅ YouTube channel `UCNtoKR8bjPIx9giRQXnK50A` (407 videos). RSS available.
- ✅ Titles equal the CivicWeb meeting names ("Council - 24 Aug 2026"), sometimes split "(Part 1)" and "(Part 2)".
- ✅ YouTube auto-captions only.
- ❓ How far back the uploads go, and gaps during the building renovation.

---

## Not in scope (for reference)

- **Wellington County** (upper tier for Centre Wellington): eSCRIBE `https://pub-wellington.escribemeetings.com`;
  YouTube `CountyofWellington`. Vote-recording practice ❓.
