# Multi-council work tracker

The live record of progress. Update this file in the same commit as the work. Statuses: `todo`, `doing`, `done`,
`blocked: <why>`, `n/a`. The admin panel's "All councils" coverage table shows *data* progress (meetings parsed,
summarized and so on); this file tracks *build* progress.

## Decisions

| # | Decision | Status | Answer |
|---|---|---|---|
| D1 | Fergus and Elora: one Centre Wellington site with redirects? | decided | Yes: one site at `/centre-wellington/`; `/fergus` and `/elora` redirect (2026-11-09) |
| D2 | Council meetings only, or committees too? | decided | Council plus standing committees, every council including Guelph (2026-11-09). See PLAN 4.12 |
| D7 | Photo for each council | decided | G2 Basilica front view · K1 Kitchener City Hall · W1 Seagram Lofts · C1 Elora Mill · R2 ION train at Kitchener City Hall (2026-11-09). See PLAN 4.8 |

## Phase 0: Ground truth

| Task | Status | Notes |
|---|---|---|
| Move plan docs into `docs/multicity/` | done | 2026-11-09, branch `multicity` |
| Waterloo: meeting enumeration spike | done | `/meetings/Index` POST with session cookie and anti-forgery token works; 113 Council-calendar meetings in the term. Recipe in SOURCES.md |
| Centre Wellington: CivicWeb crawl spike | done | `MeetingInformation.aspx?type=18|10` lists meetings; `meetingDocuments` DocumentType 10 is the minutes PDF; `/api/videolink/{id}` gives the YouTube id |
| YouTube auto-caption spike (Waterloo, CW) | done | `en-orig` auto-captions on both (about 160 wpm, `>>` speaker turns, names mangled). Requesting a second track gave HTTP 429: fetch `en-orig` only, with `--sleep-subtitles` |
| Kitchener: Whisper timing on one meeting; confirm no captions in older years | done | No captions 2022–25 (10 samples). 2h20 meeting: 373 s audio pull + 257 s Whisper ≈ 10.5 min. Names poor: the roster prompt is dropped after the first window with `condition_on_previous_text=False` |
| Region: captions and bookmarks across 2023–26 | done | Captions 15/15 samples (two early-2023 files lack timestamps); bookmarks in 252 of 265 meetings. Named votes only from Aug 2023 |
| Split-recorded-vote counts per council, 2022–26 term | done | Region 470 (247 in budget committee), Guelph 73 at council (committees: see log), Waterloo 60 (dissenters always named), Kitchener 38 in tables + ~42 in prose, CW 9 |
| In-scope meeting types per council, 2022–26 (including committee renames) | done | PLAN 4.12 table updated. Region: Planning and Works → SID in Aug 2024. Waterloo has no standing committee this term |
| Rosters for both terms, for all 4 new councils | done | In SOURCES.md, from the 2026-10-27 certificates. Region chair for 2026–30 unknown (provincially appointed). Guelph 2026–30: partial, unofficial (see Guelph section) |
| Portraits with attribution | blocked: licences | Every council's headshots carry no reuse licence (the Region's terms forbid commercial use without consent). Ask each Clerk |

## Phase 1: Multi-council core (Guelph only)

| Task | Status | Notes |
|---|---|---|
| Golden snapshot of the current Guelph site and 10 saved searches | done | Site in `state/golden/site/` (101 files, not committed); searches in `docs/multicity/golden/searches.md`; check with `tools/golden_diff.py` |
| Repo restructure (`cities/`, `data/`, `core/`, `sources/`, `video/`) | done | `git mv` of raw, votes, councillors, portraits; `pipeline.py` is the CLI and re-exports helpers for tests and the panel |
| `meeting.json` v2 plus Guelph migration | done | `tools/migrate_v2.py`; eSCRIBE record kept in `source/meeting_source.json`; `video_file.txt` folded into `video.parts`. Re-parse of all 42 meetings identical to before |
| eSCRIBE adapter extracted from `pipeline.py` | done | `sources/escribe.py` + `video/isilive.py`; shared steps in `core/` |
| Terms: per-term councillors and analysis, term selector | done | `terms` in city.json; councillors.json per term; one councillors page per term with data, linked by chips (hidden while only one term has data). Guelph 2026–30 roster still empty |
| Committees: keys, `body`, per-meeting roster, filters, summary wording | done | Keys `YYYY-MM-DD-<type>`; `body`/`body_name` in meeting.json; roster from each meeting's attendance; meeting-list chips (`#show=`) checked in the browser with a placeholder; council/committee councillors pages appear once a term has split votes in both (not yet seen with real data); committee prompt says 'recommended'; closed-only meetings skipped |
| Guelph committee backfill | doing | Documents and minutes done for 125 meetings (0 vote problems). Transcripts and summaries (`claude -p`, about 125 calls) wait for the go-ahead |
| Vote-label maps, attendance per adapter, council-size check | done | Labels in `city.json` plus defaults (Contra, In Favor, Opposed…); unknown labels are vote problems. Also fixed: Kitchener's "Carried, on a recorded vote (7 to 4)" had no count. Council size from term `seats` |
| Theme pipeline (duotone, emblem, card, OG image) | done | `core/theme.py` (Pillow) from `cities/<slug>/theme/source.jpg`; images generated into `state/theme/` |
| Disclaimer footer; check for "AI" in user-facing text | done | Footer on every page; tests check sources and built pages (transcripts quote speakers, so their text is exempt) |
| Landing page `/` and `_redirects` | done | `build_root.py`: council cards, search box, all-councils `search.html`; `_redirects` from `redirect_from` (empty for Guelph, so the old `/ → /guelph/` is gone) |
| Search: `city`/`date` columns, `cities=` parameter, Worker | done | Chunks carry `city`, `date`, `body`; SQLite gets `city`/`date` columns and an index; dates filter on `date`; results diversified by (council, meeting, kind); Worker passes `cities`. Re-index reused all 4,347 vectors; the 10 saved searches return identical results. Not deployed |
| Golden diff shows only intended changes; deploy | doing | `tools/golden_diff.py`: 99 of 101 pages identical apart from style, theme, footer and scripts; the other 2 differ only by dropping 'AI' from footers; 4 theme images added. Not deployed: needs approval |

## Councils

| Stage | Kitchener | Region of Waterloo | Waterloo | Centre Wellington |
|---|---|---|---|---|
| Sources documented (`SOURCES.md`) | done | done | done | done |
| `city.json` and theme photo | todo | todo | todo | todo |
| Adapter: meeting list | todo (eSCRIBE) | todo (eSCRIBE) | todo (GovStack) | todo (CivicWeb) |
| Adapter: documents | todo | todo | todo | todo |
| Adapter: minutes parse and audit, with fixtures | todo | todo | todo (PDF) | todo (PDF) |
| Video and transcripts | todo (Whisper) | todo (ISI captions) | todo (YouTube) | todo (YouTube) |
| Backfill from 2022-11-15: documents and parse | todo | todo | todo | todo |
| Backfill: transcripts | todo | todo | todo | todo |
| Backfill: summaries (council meetings) | todo | todo | todo | todo |
| Backfill: summaries (committees) | todo | todo | todo | todo |
| Zero unexplained vote problems | todo | todo | todo | todo |
| Councillors page (full or recorded-votes page) | todo | todo | todo | todo |
| Sub-site live | todo | todo | todo | todo |
| In search and on the landing page | todo | todo | todo | todo |
| Included in nightly update | todo | todo | todo | todo |

## Phase 5: Search across councils

| Task | Status |
|---|---|
| All-councils search page with checkboxes | todo |
| "All councils" toggle on council search | todo |
| Landing page search box | todo |
| Ranking check with saved queries per council | todo |

## Phase 6: Automation

| Task | Status |
|---|---|
| `pipeline.py update --city all` with publish gates | todo |
| Minutes re-check window (90 days, source hashes) | todo |
| Lock shared with the admin job queue | todo |
| `update_report.json` and notification | todo |
| Admin panel: council switcher and coverage table | todo |
| `launchd` agent plus `caffeinate`; one week of manual runs first | todo |

## Log

Newest first. One line per notable event: what changed, what broke, what was decided.

- 2026-11-09: Phase 1 search: city/date/body on every chunk; all 4,347 vectors reused; 10 saved searches identical.
- 2026-11-09: Phase 1 restructure landed; golden diff shows only the emblem, footer wording and theme images.
- 2026-11-09: Bug found by the new tests: Kitchener's "Carried, on a recorded vote (7 to 4)" had no count; fixed.
- 2026-11-09: Phase 0 done. Surprises: Kitchener writes about half its split votes as prose; Waterloo names dissenters on every split vote; Region names only from Aug 2023; Waterloo has no standing committee.
- 2026-11-09: Golden snapshot of the Guelph site and 10 saved searches taken before any code change.

- 2026-11-09: D7 decided: photos chosen (all CC BY-SA, from Wikimedia Commons).
- 2026-11-09: D2 decided: council plus standing committees, for every council including Guelph.
- 2026-11-09: D1 decided: one Centre Wellington site, with Fergus and Elora redirects.
- 2026-11-09: Plan drafted. Captions checked: Kitchener has no ISI captions; the Region's are at ISI client `waterloo`.
