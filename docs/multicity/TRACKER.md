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
| Move plan docs into `docs/multicity/` | todo | |
| Waterloo: meeting enumeration spike | todo | |
| Centre Wellington: CivicWeb crawl spike | todo | |
| YouTube auto-caption spike (Waterloo, CW) | todo | |
| Kitchener: Whisper timing on one meeting; confirm no captions in older years | todo | Sep 2026 and Nov 2025: no `.vtt` (404); HLS answers |
| Region: captions and bookmarks across 2023–26 | todo | Sep 2026: `.vtt` OK under client `waterloo` |
| Split-recorded-vote counts per council, 2022–26 term | todo | Kitchener 2026: 1 split vote in 9 meetings |
| In-scope meeting types per council, 2022–26 (including committee renames) | todo | |
| Rosters for both terms, for all 4 new councils | todo | |
| Portraits with attribution | todo | |

## Phase 1: Multi-council core (Guelph only)

| Task | Status | Notes |
|---|---|---|
| Golden snapshot of the current Guelph site and 10 saved searches | todo | |
| Repo restructure (`cities/`, `data/`, `core/`, `sources/`, `video/`) | todo | |
| `meeting.json` v2 plus Guelph migration | todo | |
| eSCRIBE adapter extracted from `pipeline.py` | todo | |
| Terms: per-term councillors and analysis, term selector | todo | |
| Committees: keys, `body`, per-meeting roster, filters, summary wording | todo | |
| Guelph committee backfill | todo | |
| Vote-label maps, attendance per adapter, council-size check | todo | |
| Theme pipeline (duotone, emblem, card, OG image) | todo | |
| Disclaimer footer; check for "AI" in user-facing text | todo | |
| Landing page `/` and `_redirects` | todo | |
| Search: `city`/`date` columns, `cities=` parameter, Worker | todo | |
| Golden diff shows only intended changes; deploy | todo | |

## Councils

| Stage | Kitchener | Region of Waterloo | Waterloo | Centre Wellington |
|---|---|---|---|---|
| Sources documented (`SOURCES.md`) | partial | partial | partial | partial |
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

- 2026-11-09: D7 decided: photos chosen (all CC BY-SA, from Wikimedia Commons).
- 2026-11-09: D2 decided: council plus standing committees, for every council including Guelph.
- 2026-11-09: D1 decided: one Centre Wellington site, with Fergus and Elora redirects.
- 2026-11-09: Plan drafted. Captions checked: Kitchener has no ISI captions; the Region's are at ISI client `waterloo`.
