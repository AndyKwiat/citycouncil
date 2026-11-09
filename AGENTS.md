# Notes for agents working on this project

Read `README.md` first for what each part does. This file is the short operational guide: layout, how to run and
ship things, and what can go wrong.

## What this is

A public site of Guelph City Council meeting summaries, votes and transcripts, with semantic search:
https://cityhallvotes.ca/guelph/. Everything is built on the owner's Mac and driven from a local admin panel
(`./admin`, http://127.0.0.1:8750/). Repo: github.com/AndyKwiat/citycouncil (private).

## Layout

| Path | What |
|---|---|
| `pipeline.py` | Every data step (calendar, documents, minutes parsing and vote audit, transcripts, summaries), plus both deploys. CLI: `calendar`, `process`, `build`, `deploy`, `search-index`, `search-deploy`. |
| `build.py` | Renders `raw/` into the static site in `site/`. |
| `analysis.py` | Voting groups (MDS plus hierarchical clustering) and communities (Louvain). |
| `alliance_network.py/.js`, `search_page.py` | Page sections with their own data, markup and script. New visualizations follow this shape. |
| `search_index.py` | Cuts meetings into search passages for the Rust indexer. |
| `search/` | Rust crate: embedding (candle), indexer, and the search API server. |
| `cf/` | Cloudflare Worker config and code for the public site. |
| `admin.py`, `admin.html`, `./admin` | The local panel and its one-at-a-time job queue. |
| `raw/<date>/` | Downloaded and generated data per meeting (committed). |
| `votes/` | Every vote as JSON and CSV, plus `clusters.json` (committed). |
| `councillors.json`, `portraits/` | Full names, wards and photos, keyed by the surname used in the minutes. |
| `site/`, `state/` | Generated: the built site, job logs, deploy stamps, search index, Cloudflare dist. Not committed. |
| `search/model/` | The embedding model on the laptop (downloaded on first index). Not committed. |

## Two separate deploys

| | Front end | Search server |
|---|---|---|
| What | All static pages plus the Worker | Rust API plus the search index |
| Where | Cloudflare Worker `cityhallvotes`, at cityhallvotes.ca | radify app `api-citycouncil` on step1, at api-citycouncil.akwiat.com |
| Commands | `pipeline.py build`, then `pipeline.py deploy` | `pipeline.py search-index`, then `pipeline.py search-deploy` |
| Panel | Website card | Search card |

After processing new meetings, do both. A page or Worker change needs only the front end; a change in `search/` or
`search_index.py` needs only the server. Order between them doesn't matter.

## Setup on a fresh Mac

- Python 3.12 venv: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`. Whisper's model
  (about 3 GB) downloads to `~/.cache/huggingface` the first time it runs.
- Summaries use the `claude` CLI with the owner's login (`claude -p`), so no API key.
- Rust with targets `aarch64-apple-darwin` and `x86_64-unknown-linux-musl`. There is no Xcode: `search/.cargo/config.toml`
  links with zig through `~/.local/bin/zcc-*` wrappers, copied from `~/radify/.cargo/config.toml`.
- Node, for `npx wrangler@4`.
- radify CLI at `~/radify/bin/radify` with `~/.config/akwiat/radify.env`, and SSH aliases `step1` (root) and
  `step1-deploy`. See the radify skill or `~/radify/README.md`.
- `~/.config/akwiat/secrets.env` must contain `CLOUDFLARE_WORKERS_TOKEN` (Workers edit plus DNS edit on
  cityhallvotes.ca). Never print it or commit it.

## Secrets and access

- The search API answers only requests with `APP_KEY`, which exists only as a radify env var on the server and as a
  Worker secret. It isn't stored on the laptop. To rotate: generate one value, then `radify env-set api-citycouncil
  APP_KEY=...`, `radify restart api-citycouncil` and `npx wrangler@4 secret put APP_KEY --config cf/wrangler.jsonc`
  (with `CLOUDFLARE_API_TOKEN` set to the Workers token and `CLOUDFLARE_ACCOUNT_ID` set).
- The API's radify policy is `public` on purpose: the key, not the Google sign-in gate, protects it.

## Checks before shipping

- `.venv/bin/python -m unittest discover tests` and, in `search/`, `cargo test --release`.
- Every parse runs a vote audit against the raw minutes. Problems appear in the job log as `VOTE PROBLEM` and in red
  in the panel. Don't ship with unexplained ones: every vote must be captured.
- Check pages in a browser at desktop and phone width. The site has no dark mode by design.

## Gotchas

- The panel imports `pipeline.py` once. After changing `admin.py`, `admin.html` or the panel's actions, restart it.
  Jobs run `pipeline.py` as a fresh process, so pipeline changes apply to the next job without a restart.
- The search server needs about 450 MB, so `app@api-citycouncil` has a systemd override raising `MemoryMax` to 900 MB
  (`/etc/systemd/system/app@api-citycouncil.service.d/override.conf` on step1). radify's default is 512 MB.
- Cloudflare redirects `page.html` to `page`, and the Worker runs only for `www.` and `/api/search`. Pages must keep
  using relative links, because the site lives under `/guelph/`.
- Only meetings the city labels "City Council" are processed. A new council term begins after each election (next
  in late 2026), and its members need entries in `councillors.json` and `portraits/`. The voting pages currently
  mix every term in `raw/`, so a filter by term will be needed.
- Transcripts and minutes copies include residents' and delegates' names, and the site is public; summaries are
  told not to name private individuals.
