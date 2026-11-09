# cityhallvotes.ca: multi-council plan

Status: **draft, not started**. Repo: `~/src/citycouncil`. When work begins, this folder moves to
`docs/multicity/` in that repo (Phase 0) and `TRACKER.md` becomes the live work-in-progress record.

Companion files:
- `TRACKER.md`: the checklist, one row per council per stage. Update it as work lands.
- `SOURCES.md`: how each council publishes data, with URLs and what has been verified.

---

## 1. Goal

Turn the Guelph site into one site serving several councils, with the same features for each:
- meeting summaries
- minutes pages with votes
- transcripts
- the councillors page ("who votes with whom")
- semantic search

The councils:

| Sub-site | Council | Notes |
|---|---|---|
| `/guelph/` | Guelph City Council | Existing. URLs must not change. |
| `/kitchener/` | Kitchener City Council | |
| `/waterloo/` | Waterloo City Council | |
| `/centre-wellington/` | Centre Wellington Township Council | Fergus and Elora share this one council; `/fergus/` and `/elora/` redirect here (D1). |
| `/region-of-waterloo/` | Regional Council of Waterloo Region | Upper tier over Kitchener, Waterloo, Cambridge and 4 townships. |
| `/` | Landing page | Links to every council, plus search across all of them. |

**Date range:** from **2022-11-15** (start of the 2022–2026 council term) to now, which is about 4 years. That
covers the whole previous term plus the new term that began 2026-11-15. Guelph already starts at 2022-12-06.

**Fixed rule:** every council produces the same outputs: the same `meeting.json`, `minutes.json`, `summary.json`,
`transcript.json`, vote exports and search rows. Only the *source adapters* differ.

---

## 2. What the research found (and what it means)

| | Guelph | Kitchener | Region of Waterloo | Waterloo | Centre Wellington |
|---|---|---|---|---|---|
| Minutes system | eSCRIBE | eSCRIBE | eSCRIBE | GovStack calendar | CivicWeb (iCompass) |
| Minutes format | HTML | HTML | HTML | PDF (text) | PDF (text) |
| Meeting list | eSCRIBE JSON | eSCRIBE JSON | eSCRIBE JSON | form POST or URL slugs | crawl folder pages |
| Video | ISI (eSCRIBE) | ISI (eSCRIBE) | ISI (eSCRIBE) | YouTube | YouTube |
| Closed captions | ISI `.vtt` ✅ | **none (404)**, so Whisper | ISI `.vtt` ✅ (client id `waterloo`) | YouTube auto-captions | YouTube auto-captions |
| Item ↔ video timestamps | eSCRIBE bookmarks | eSCRIBE bookmarks | eSCRIBE bookmarks (assumed) | none | none |
| Named votes | ~76% of motions | ~2% (on request) | **every vote since 2023** | on request only | on request only |

The caption checks were made on 2026-11-09 against the Sep 2026 meetings. Kitchener's ISI audio stream (HLS) does
answer, so Whisper can transcribe it.

**The most important consequence: "who votes with whom" needs *split* recorded votes.** Unanimous votes carry no
signal, and Guelph's analysis already uses only non-unanimous ones.
- Guelph and the Region will have rich data.
- Kitchener had **one** split recorded vote in its 9 Council meetings of 2026.
- Waterloo and Centre Wellington are probably similar.

So the councillors page must adapt to how much data a council has (see 4.7). Phase 0 counts split recorded votes per
council per term, so we know before building it.

---

## 3. Decisions

| # | Decision | Recommendation |
|---|---|---|
| D1 | Fergus and Elora | **One dataset, one site** at `/centre-wellington/` titled "Centre Wellington (Fergus & Elora)". `/fergus/` and `/elora/` redirect to it. **Decided 2026-11-09.** |
| D2 | Which meetings | **Council plus standing committees, for every council including Guelph.** Decided 2026-11-09. Advisory committees, Committee of Adjustment, boards and closed-only special meetings are excluded. Each council's `city.json` lists the in-scope meeting types; see 4.12. |
| D3 | Source of truth | **JSON files stay canonical** (diffable, committed, easy to re-run). SQLite holds only derived data: the search index, extended with `city`. No new server database is needed. |
| D4 | Votes nobody recorded | Record what is true: `recording: "unrecorded"`, outcome only, mover and seconder. **Never infer individual votes**, with one exception: Waterloo's explicit "Carried Unanimously" becomes `recording: "unanimous"`, with "for" set to the members present. This is flagged as inferred and excluded from agreement statistics, which ignore unanimous votes anyway. |
| D5 | Councillors and terms | Make the council term a first-class concept. Councillors and portraits are stored per term, and agreement statistics are computed per term. Every council changed membership on 2026-11-15, so this is required now, not later. |
| D6 | Where processing runs | **On the Mac**, unchanged. Whisper and the `claude` CLI login live there, and step1 has 2 GB of RAM. Automation is a `launchd` job on the Mac; step1 only serves search. |
| D7 | Images | One photo per council, made into a soft duotone in that council's accent colour. Sourced from Wikimedia Commons and credited in the footer. **Chosen 2026-11-09; see 4.8.** |
| D8 | Repo | Keep `citycouncil` as the one repo and refactor it in place. Guelph moves first and must come out unchanged (golden test). |

---

## 4. Architecture

### 4.1 Repo layout (after the refactor)

```
cities/<slug>/
  city.json            name, display name, council name, adapter, URLs, meeting types, terms, theme, credits
  councillors.json     per term: members, wards, roles, portrait files, name aliases used in minutes
  portraits/
  theme/               source photo + generated duotone/emblem images (generated ones not committed)
data/<slug>/
  raw/<key>/           per meeting (see 4.3); was raw/ for Guelph
  votes/               votes.json, motions.csv, votes_by_councillor.csv, clusters.json
core/                  shared steps: transcribe, summarize, votes export, audit helpers, status, terms
sources/
  escribe.py           Guelph, Kitchener, Region (generalised from today's pipeline.py)
  waterloo_govstack.py Waterloo meeting list + PDF minutes
  civicweb.py          Centre Wellington folder crawl + PDF minutes
  pdf_minutes.py       shared PDF text extraction (page header/footer stripping, line joining)
video/
  isilive.py           ISI player: file name, HLS audio, .vtt captions
  youtube.py           match video to meeting by title/date, auto-captions, audio for Whisper
site/<slug>/  site/index.html  site/search.html     generated
state/                 jobs, stamps, search index, per-city status (generated)
pipeline.py            CLI: everything takes --city <slug>|all
build.py               per-council site; build_root.py for / and /search
```

Git history is kept with `git mv raw data/guelph/raw` and similar moves.

### 4.2 Adapter interface

Each source adapter implements four functions:

```python
list_meetings(city, start, end) -> [Meeting]       # normalized records (4.3), all types; filtered by city.json
fetch_documents(city, meeting, dir, force)          # minutes (HTML or PDF), agenda; stores source files + hashes
parse_minutes(city, meeting, dir) -> Minutes        # the shared minutes.json shape, plus audit problems
video_for(city, meeting) -> Video | None            # provider, id/url, HLS/audio url, captions url, multi-part list
```

Transcription, summaries, vote export, analysis, build and search are shared and never branch on the source.

### 4.3 Shared per-meeting files (`data/<slug>/raw/<key>/`)

- **Key:**
  - Main council meetings: `YYYY-MM-DD`, so Guelph's existing keys and URLs stay the same.
  - Committees and special meetings: `YYYY-MM-DD-<type-slug>`, e.g. `2026-04-20-finance-and-corporate-services`.
  - A `-2` is added only if a council still has two keys that collide.
- **`meeting.json` (v2, normalized):**
  - `{id, city, key, type, title, start, end, location`
  - `links: {official_minutes, minutes_pdf, agenda, meeting_page, video}`
  - `video: {provider: isilive|youtube, parts: [{url, hls|youtube_id, captions}]}`
  - `term, minutes_posted, source_hashes}`
  - The council's raw record goes to `source/meeting_source.json`.
  - Guelph is migrated by a one-off script. `build.py` stops reading eSCRIBE fields directly.
- **`minutes.json`:** today's shape, kept: `roster, absent, items[], motions[]` with `votes {for, against, other}`
  and `result`. Additions:
  - `motion.recording`: `recorded | unanimous | unrecorded`
  - `motion.present`: who was present for that motion, where it can be worked out from attendance changes
  - `conflicts[]`: `{member, item_number, text}` (declared pecuniary interests)
  - `attendance_events[]`: Waterloo's timed "left / joined" lines
  - `source_format`: `escribe-html | pdf`, plus `pages` for PDFs (so minutes pages can link to the PDF page)
- **`transcript.json`, `transcript_meta.json`:** unchanged. Add `meta.source`: `isilive-captions | youtube-auto |
  whisper | mixed`, and a part offset for meetings split across several videos.
- **`summary.json`:** unchanged schema. The prompt is parameterized by council name. Item-to-video times may be
  missing (YouTube councils), and every link degrades gracefully.

### 4.4 Parsing changes the new councils force (known now)

1. **Vote labels:** add a per-council map. Kitchener uses "In Favour" / "Contra", the Region "In Favor" / "Opposed",
   Waterloo "Voted in Favour" / "Voted in Opposition", CW "For" / "Against". Today's code would put Kitchener's
   "Contra" and the Region's "In Favor" into `other`, which is **a bug to fix before any import**.
2. **Attendance:** the parser looks for "Council:"; Kitchener uses "Present:". It becomes per-adapter.
3. **Council size:** `check_summary` assumes at most 13 members. Use the term's roster size instead (Region: 16).
4. **Vote audit for PDFs:** count "recorded vote" / "Voted in Favour" occurrences in the raw text and compare with
   what was parsed. A PDF meeting cannot be published with unexplained differences, the same rule as for HTML.
5. **PDF cleanup:** strip running headers and footers ("Page 16 of 17 / Council Minutes …") that break into vote
   blocks. Use `pdfplumber`, cropping by position, plus a per-council regex.
6. **Name aliases:** "Councillor Wilton" and "Councillor Bronwynne Wilton" map to one person through `councillors.json`
   aliases, keyed per term.

### 4.5 Site and URLs

- `build.py --city <slug>` writes `site/<slug>/`, with the same pages as Guelph today: index, minutes, transcripts,
  councillors, search. Relative links already make sub-paths work.
- `build_root.py` writes:
  - `site/index.html`: one card per council (image, name, number of meetings, latest meeting)
  - `site/search.html`: all-councils search
  - `_redirects`: `/fergus` and `/elora` go to `/centre-wellington/`; the old `/ → /guelph/` redirect is removed
- Deploy assembles every council into one `dist/` and runs `wrangler deploy` once. Cloudflare uploads only changed
  files.
- Every page footer gets the disclaimer below. The current footer says "AI-generated", so it is replaced. Before
  shipping, run a grep check that no user-facing text contains "AI".

**Disclaimer (draft):**

> This site is produced automatically. Summaries and transcripts are generated by software from the official minutes
> and meeting recordings, with no human review, so they can contain mistakes: misheard words, missing context or
> the wrong emphasis. Vote results and names come directly from the official minutes, but always check the
> [official record] before relying on anything here. cityhallvotes.ca is independent and not affiliated with
> {council}.

### 4.6 Theming (a slightly different feel per council)

`city.json` → `theme: {accent, accent_ink, photo, photo_credit, photo_licence, focal_point}`. A small script (Pillow,
run once per photo) produces:

- **Header backdrop:** a duotone in the accent colour, about 12% opacity behind the header, fading into the page
  through a gradient. The text stays readable at any width.
- **Emblem:** a 64 px round crop shown next to the council name in the header, and used as the favicon.
- **Landing card image** on `/`, and an **Open Graph image** for link previews.

CSS stays inline, as today. The accent colour is applied through CSS variables (`--accent`) on links, badges and
chart highlights. No dark mode, as now. Check at phone width.

### 4.7 Councillors page for councils with few recorded votes

The page works out its own data level for the selected term:

- **Enough split recorded votes** (30 or more in the term, `ENOUGH_SPLIT_VOTES` in `build.py`. Phase 0, 2022–26: Region 470, Guelph 73 at council alone, Waterloo 60, Kitchener 38 in tables or about 80 with prose votes, Centre Wellington 9): today's page, with the alliance
  network, voting-groups map and agreement circle.
- **Too few:** a "Recorded votes" page instead, with:
  - every named vote, showing who was for and against
  - per member: attendance rate, motions moved and seconded, conflicts declared, and times on the losing side of a
    recorded vote
  - a plain note: "{Council} records individual votes only when a member asks, so most decisions show only the
    outcome."
- **Everywhere:** the vote badge shows "Carried · not recorded" instead of a count when nobody's votes were recorded.

A **term selector** sits on the councillors page. It defaults to the most recent term that has enough data.

### 4.8 Photos (chosen 2026-11-09)

All five photos are from Wikimedia Commons and all are CC BY-SA. That means:
- Each council's footer carries a credit line: "Photo: {artist}, {licence}, via Wikimedia Commons", linked to the file page.
- The tinted versions we make are released under the same licence. Their `README` in `cities/<slug>/theme/` says so.

| Council | Photo | Licence | By | Size | File page |
|---|---|---|---|---|---|
| Guelph | Basilica of Our Lady Immaculate, front view | CC BY-SA 4.0 | Maksim Sokolov (maxergon.com) | 3116×4858 (portrait) | https://commons.wikimedia.org/wiki/File:Basilica_of_Our_Lady_Immaculate,_Guelph_-_Frontal_view.jpg |
| Kitchener | Kitchener City Hall (2015) | CC BY-SA 4.0 | JustSomePics | 2869×2869 | https://commons.wikimedia.org/wiki/File:Kitchener_City_Hall_2015.jpg |
| Waterloo | The Seagram Lofts (2025) | CC BY-SA 4.0 | Ryan Hodnett | 5680×3195 | https://commons.wikimedia.org/wiki/File:The_Seagram_Lofts_-_Waterloo,_Ontario_2025-09-14.jpg |
| Centre Wellington | Elora Mill (2014) | CC BY-SA 4.0 | JustSomePics | 4000×3000 | https://commons.wikimedia.org/wiki/File:Elora_Mill_2014.jpg |
| Region of Waterloo | ION train 505 at Kitchener City Hall | CC BY-SA 3.0 | *Youngjin | 1500×844 | https://commons.wikimedia.org/wiki/File:ION_505_Kitchener_City_Hall.jpg |

Notes for the theme step:
- **Guelph** is portrait: crop the header backdrop to the towers, and use the full height for the emblem.
- **Region**: at 1500 px wide it's fine for a faint backdrop and a 1200×630 link-preview image, but check it isn't
  soft at retina header widths.
- **Kitchener and Region** both show Kitchener City Hall. Their accent colours should differ clearly so the two
  sub-sites don't look alike.

### 4.9 Search across councils

- **Chunks:** gain `city` and `date` fields. `meeting` becomes `<city>/<key>` for display. The embedded prefix names
  the council ("Council vote, Kitchener City Council, May 4, 2026. …"). Guelph's prefix is unchanged, so its
  existing vectors are reused.
- **SQLite schema:** add `city TEXT`, `date TEXT` and an index on them. Date filtering moves from string compares on
  `meeting` to `date`.
- **API:** add `cities=guelph,kitchener` (default all). Diversify by `(city, meeting, kind)`. Results include `city`
  and an absolute URL (`/kitchener/minutes/…`).
- **Worker:** allow `cities` in the cache key parameters.
- **Pages:**
  - per-council search defaults to that council, with an "All councils" toggle
  - `/search.html` has council checkboxes
  - the landing page has a search box
- **Size:** about 25,000–30,000 chunks × 768 floats ≈ 90 MB in memory. That fits inside the existing 900 MB service
  limit, and a brute-force scan stays fast. Re-check the memory limit after the first full index.

### 4.10 Automatic updates

`pipeline.py update --city all`, run nightly by a `launchd` agent (`~/Library/LaunchAgents/ca.cityhallvotes.update.plist`,
05:30, wrapped in `caffeinate`). For each council:

1. Refresh the meeting list for the last 120 days through the next 60.
2. For past meetings in scope:
   - fetch documents not yet fetched
   - **re-check minutes for meetings in the last 90 days**: posting lags 2–6 weeks, and minutes are sometimes
     revised (compare source hashes)
   - on a change, re-parse, re-transcribe if the video changed, and re-summarize
3. Export votes, then recompute analysis per term.
4. **Publish gates:**
   - a meeting with vote-audit problems, a failed summary check or a failed adapter is **held back**: it's left out
     of the site and listed in the report
   - every other meeting publishes
   - the tests must pass, or nothing is deployed
5. Build all councils and the root; deploy the front end. Re-index search; deploy search if the index changed.
6. Write `state/update_report.json` and send one notification: what was new, what was held and why. Use a macOS
   notification, plus email or Telegram if wanted.

Other rules:
- A lock file prevents overlapping runs. The admin panel's job queue uses the same lock.
- The admin panel gains a council switcher, plus an **"All councils" coverage table**: per council, meetings
  found / with minutes / parsed / transcribed / summarized / on the site / held. This is the live view of progress.
- Be polite to the city sites: a browser User-Agent where required (Kitchener, Waterloo and Wellington County
  refuse bare clients), no more than 1 request per second per host, and cached source files.

### 4.12 Committees (D2)

**Proposed scope.** Phase 0 confirms these against each council's list of meeting types for 2022–2026, because
committees were renamed between terms.

| Council | Council meetings | Standing committees (in scope) |
|---|---|---|
| Guelph | City Council, Special Council Meeting (open part), Special Council Meeting - Budget, Council Planning (a meeting of Council, so `body: council`) | Committee of the Whole |
| Kitchener | Council Meeting, Special Council Meeting (open part) | Finance and Corporate Services; Planning and Strategic Initiatives; Community and Infrastructure Services (no renames). Audit Committee optional; Climate Change and Environment is advisory (out) |
| Region | Council Meeting, Special Council, Emergency Special, Inaugural, Board of Health | Administration and Finance; Community and Health Services; Planning and Works (to 2024-06) → Sustainability, Infrastructure, and Development (from 2024-08); **Strategic Planning and Budget** (247 of the Region's 470 split votes). Audit and Library optional |
| Waterloo | Council Calendar: Council Meeting, Special Council Meeting, Inaugural, All Council | **None in 2022–26** (CoW and Finance & Strategic Planning ended with the 2018–22 term) |
| Centre Wellington | Council, Special Council, Council (Budget) (type 18) | Committee of the Whole incl. (Budget) variants (type 10); workshops and orientation have no motions |

**Out of scope:**
- advisory committees, which have citizen members
- Committee of Adjustment and licensing or hearing tribunals (quasi-judicial)
- library and police boards
- special meetings that only move into closed session; these are detected when the minutes have no open motions,
  and skipped

**Data model:**
- `meeting.json` gains `body: council | committee` and `body_name`.
- A meeting's roster comes from its own attendance block. That matters where a committee has fewer members than
  council, so a non-member is never counted as absent.

**Committee recommendation, then council adoption.** The same issue is often voted on twice.
- Both votes are kept. They are separate votes, and members do sometimes change position.
- The councillors page gets a filter: **All votes** (default) / **Council only** / **Committees only**. The count
  of votes behind each percentage is shown.
- Later (Phase 7): link a council adoption to the committee meeting that recommended it. Kitchener's minutes name it,
  e.g. "Finance and Corporate Services Committee – April 20, 2026". Each decision then shows both votes.

**Site:**
- The meeting list shows the body on every card.
- A filter chip row (All · Council · each committee) lives in the URL hash, so the static site still works.
- Summaries of committee meetings say what was *recommended* to Council, not decided. The prompt gets the body type.

**Search:** chunks carry `body`, and there's an optional `bodies=` filter later. Volume is about 2.5 times
council-only (see section 6).

### 4.11 Storage and backups

- **Committed:** derived JSON, plus HTML minutes and VTT captions, as today (Guelph's `raw/` is 36 MB; estimate
  about 250 MB for all councils).
- **Not committed (re-downloadable, listed with hashes):** PDFs, audio and YouTube caption downloads.
- Add `data/` to the existing restic backup if the repo grows uncomfortably.

---

## 5. Phases

Each phase ends with something shippable. The councils are independent of each other once Phase 1 lands, so Phases
2–4 can run in parallel sessions (one council each, separate files).

### Phase 0: Ground truth (about 1–2 days, no site changes)
- Move these docs into `docs/multicity/` in the repo.
- Spikes, each written up in `SOURCES.md`:
  - Waterloo: list meetings through the form POST with anti-forgery token, 2022→now; or confirm a slug-guessing fallback.
  - Centre Wellington: crawl the folder tree; map documents to meetings (a council minutes PDF to its date).
  - YouTube: fetch auto-captions with `yt-dlp` for one Waterloo and one CW meeting; check quality and blocking.
  - Kitchener: time Whisper on one full Council meeting over HLS. Confirm no captions exist in older years either.
  - Region: confirm captions and bookmarks across 2023–2026; confirm every motion has a vote table.
- For every council, count meetings in scope and split recorded votes in the 2022–26 term. This sets the threshold in
  4.7 and which councils get the full councillors page.
- Collect councillor rosters for **both** terms (2022–26 and 2026–30), with wards and roles; source portraits with
  attribution.
- List every meeting type per council for 2022–2026 and fix the in-scope list (4.12), including committee renames
  between terms.
- All decisions (D1, D2, D7) are made.

### Phase 1: Multi-council core, Guelph only (about 3–5 days)
- Add a golden snapshot first: build today's Guelph site into `golden/`.
- Restructure (4.1); `city.json` for Guelph; normalized `meeting.json` v2 plus a migration; split the adapter from the
  shared steps.
- Add terms (D5): per-term councillors and analysis; term selector.
- Committees (4.12): meeting keys, `body` field, roster per meeting, meeting-list filter, councillors-page filter,
  committee wording in summaries. Backfill Guelph's committees.
- Theming (4.6) with the Basilica photo; the disclaimer footer; landing page `/` (Guelph only for now); `_redirects`.
- Search: `city` and `date` columns, the `cities=` parameter, the Worker allowing it, a re-index.
- **Exit:**
  - the Guelph site diff against `golden/` shows only the intended changes (footer, theme, landing page)
  - tests pass; search returns the same top results for 10 saved queries
  - deployed

### Phase 2: Kitchener + Region of Waterloo (both eSCRIBE, about 3–4 days)
- Per-council vote-label maps, attendance parsing, council size.
- Kitchener: Whisper over HLS for every meeting (no captions). Region: ISI captions under client `waterloo`.
- Fixtures with real minutes samples, including recorded and unrecorded votes, conflicts and consent bundles; audit
  rules.
- Backfill from 2022-11-15, then summaries (spread over several days to stay within `claude` usage).
- Councillors page: the full page for the Region; probably the "Recorded votes" page for Kitchener.
- **Exit:** both sub-sites live, zero unexplained vote problems, and both appear in search and on the landing page.

### Phase 3: Waterloo (about 3–4 days)
- GovStack adapter, PDF minutes parser ("Voted in Favour / Voted in Opposition", "Carried Unanimously",
  "left/joined" events).
- YouTube matcher: titles like "City of Waterloo Council Meeting {date} @ {time}"; join afternoon and evening parts
  into one transcript with offsets.
- Same exit criteria.

### Phase 4: Centre Wellington (about 3 days)
- CivicWeb crawler, PDF parser ("Councillor X For" lines, "CARRIED on a Recorded Vote of 7-0"), name aliases.
- YouTube matcher (titles equal CivicWeb meeting names; "(Part 1)", "(Part 2)").
- `/fergus` and `/elora` redirects.
- Same exit criteria.

### Phase 5: Search across councils (about 1–2 days, any time after Phase 2)
- All-councils search page, council checkboxes, toggle on council pages, landing search box. Check ranking quality
  with saved queries per council.

### Phase 6: Automation (about 2 days, after Phase 2)
- `pipeline.py update`, publish gates, lock, report, notification, `launchd` plist, admin coverage table.
- Run it by hand for a week, then enable the schedule.

### Phase 7: Polish
- Open Graph images, councillor activity stats for every council, accessibility pass, phone checks.
- Link council adoptions to the committee recommendation behind them (4.12).

---

## 6. Rough compute for the backfill

Meeting counts are estimates; Phase 0 replaces them with real counts.

Including committees (D2):

| Council | Meetings since 2022-11 (est.) | Transcript source | Whisper time (est.) |
|---|---|---|---|
| Guelph (new: committees only) | ~60 | ISI captions | small |
| Kitchener | ~55 council + ~120 committee | Whisper (full) | ~175 meetings × ~5 min ≈ 15 h |
| Region | ~60 council + ~150 committee | ISI captions | small (gaps only) |
| Waterloo | ~70 council + ~30 committee | YouTube auto-captions | small; full Whisper only where captions fail |
| Centre Wellington | ~70 council + ~50 committee | YouTube auto-captions | small |

- **Summaries:** about 650 new ones, each one `claude -p` call. At 20–40 a day that is **3–5 weeks** of background
  backfill. Order it newest first, and council meetings before committees, so each sub-site is useful early. A
  sub-site can go live with its council meetings while committee backfill continues.
- **Search size:** about 60,000–75,000 chunks × 768 floats ≈ 200–230 MB of vectors. That still fits the 900 MB
  service limit, but brute-force query time grows. Phase 1 measures it. If it's slow, store vectors as f16 or int8
  (half or a quarter of the memory), or pre-filter by city before scoring.

---

## 7. Risks

| Risk | Mitigation |
|---|---|
| Sparse recorded votes make the agreement analysis meaningless for 3 councils | Adaptive councillors page (4.7); be explicit on the page about what the minutes record |
| City sites block scripted clients (403) | Browser User-Agent, slow polite fetching, cached sources; a failure holds back only that council |
| PDF layout changes between years | Fixtures from several years per council; audit counts; held-back meetings are surfaced, never silently wrong |
| YouTube blocks `yt-dlp` or changes captions | Fall back to Whisper on downloaded audio; flag in the report |
| Mac asleep or off: no updates | `caffeinate` plus a missed-run catch-up; the report says when the last successful run was |
| `claude` usage limits during backfill | Throttle summaries per day; the queue resumes |
| Election turnover (new members on 2026-11-15) | Per-term rosters (D5) in Phase 0/1, before any new council goes live |
| Names of private individuals in transcripts and minutes | Existing summary rules apply to all councils; no new PII surfaces added |
| Breaking Guelph during the refactor | Golden-site diff plus search query snapshots in Phase 1 |
