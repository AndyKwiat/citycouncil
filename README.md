# Guelph City Council

Static site of council meeting summaries, driven from a local admin panel.

    ./admin

Opens http://127.0.0.1:8750/. Everything runs from there: checking for meetings, processing them,
updating the website, and publishing it to https://cityhallvotes.ca/ (public, hosted on Cloudflare).

Working on the code, or an agent picking this up? Start with `AGENTS.md`: layout, setup, both deploys and gotchas.
To set up Python: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.

- `pipeline.py` does the work: calendar, documents, minutes parsing, transcripts, summaries, deploy.
- `build.py` renders `data/<slug>/raw/<key>/` into `site/<slug>/`; `build_root.py` writes the landing page at `/`.
- Each council is set up in `cities/<slug>/city.json`. `pipeline.py` takes `--city <slug>` (default `guelph`).
- `admin.py` and `admin.html` are the panel and its one-at-a-time job runner.
- Two deploys: the website goes to Cloudflare (`pipeline.py deploy`), and the search API to radify
  (`pipeline.py search-deploy`). See *Hosting on Cloudflare* and *Search* below.
- Transcripts use the city's closed captions. Whisper runs only on gaps of 5+ minutes, or on the whole
  recording if the captions are under 10 words per minute.
- Summaries call the `claude` CLI with your existing login, so no API key is needed.
- Vote counts and who voted how come straight from the minutes, never from the summary.

## Votes

`data/<slug>/votes/` is rewritten whenever minutes are parsed:

- `votes.json`: every motion with who voted which way.
- `motions.csv`: the same, one row per motion.
- `votes_by_councillor.csv`: one row per councillor per recorded vote, for analysis.

Each meeting's parse also checks its votes against the raw minutes (counts, names, anything written outside
a motion block). Problems show in red in the panel's Votes column and in the job log.

## Who votes with whom

`site/<slug>/councillors.html` is rebuilt with every website update, from the non-unanimous votes in `data/<slug>/votes/votes.json`. It covers one council term; other terms, and council-only or committee-only views, get their own pages linked from it.

- Line thickness and the hover percentages use the share of votes both people attended, not a raw count, because some members served only part of the term.
- `analysis.py` finds the voting groups and writes `data/<slug>/votes/clusters.json`. The number of groups comes from the data (silhouette score), and anyone scoring under 0.1 is shown between groups. People who never voted together get an estimated distance instead of being treated as opposites.
- Names, wards and photos live in `cities/<slug>/councillors.json` (per term) and `cities/<slug>/portraits/`. After an election, add the new term's members there or they appear with only the name from the minutes and no photo.

## Voting Alliance Network

The top of the councillors page. `alliance_network.py` prepares the data and markup, and `alliance_network.js` runs the graph with no external libraries. Add further visualizations the same way, as a `section()` plus a script passed to `build.page()`.

- Percentages come straight from the votes both people attended. A pair who never voted together has no line and shows as unknown, never 0%.
- Positions use every known pair, so the slider never moves anyone. Layout starts from fixed positions, so it is the same on every visit.
- Communities come from Louvain (`analysis.communities`) on agreement above the council's average, on the full network regardless of the slider. They can differ from the voting groups on the map, which use hierarchical clustering.

## Hosting on Cloudflare

The site is public at https://cityhallvotes.ca/; each council is at `/<slug>/` and `/` is the landing page. `pipeline.py deploy`
(the panel's Deploy button) copies `site/` to `state/cf/dist/` and runs `wrangler deploy` with `cf/wrangler.jsonc`.

- **Static:** every page, image and stylesheet is a Cloudflare static asset, served free with no code running.
  Redirects (for example `/fergus` to `/centre-wellington/`) are a static `_redirects` file built from `redirect_from` in `city.json`.
- **Worker** (`cf/src/worker.js`): runs only for `www.` and `/api/search`. It caches identical searches for an hour,
  limits each visitor to about 15 new searches a minute, and forwards the rest to the search API with a secret key.
- **Token:** deploys use `CLOUDFLARE_WORKERS_TOKEN` in `~/.config/akwiat/secrets.env`, made from Cloudflare's
  *Edit Cloudflare Workers* template for the account, plus Zone DNS Edit on cityhallvotes.ca. Radify's own
  `CLOUDFLARE_API_TOKEN` only manages DNS.

## Search

`search.html` (and the box on the home page) searches summaries, votes, minutes and transcripts by meaning. The page
calls `/api/search` on its own domain; the Worker passes that to https://api-citycouncil.akwiat.com.

- **Model:** Snowflake's `snowflake-arctic-embed-m-v1.5` (Apache-2.0), one of the strongest free retrieval models
  of its size. The `search/` Rust crate runs it with candle, so the laptop (documents) and server (queries) use
  identical code. It is pinned to one revision and checked by hash.
- **Index:** `search_index.py` cuts meetings into passages (`state/search/chunks.jsonl`), and the Rust indexer embeds
  them into SQLite (`state/search/search.sqlite`): vectors plus an FTS5 keyword index. Unchanged passages keep their
  vectors, so re-indexing after a new meeting takes seconds. The first full run takes 10 to 20 minutes.
- **Ranking:** cosine similarity over every passage, merged with keyword (BM25) matches by reciprocal rank fusion,
  so related meaning and exact names both count. At most two results per meeting and kind come first. When no
  passage uses the words and nothing is close in meaning, the page says the results are probably unrelated.
- **Access:** the API is a public radify app, but it answers only requests with the `APP_KEY` shared with the
  Worker (a radify env var on one side, a Worker secret on the other). To rotate it, set the same new value with
  `radify env-set api-citycouncil APP_KEY=...` (then `radify restart api-citycouncil`) and
  `npx wrangler@4 secret put APP_KEY --config cf/wrangler.jsonc`.
- **Limits:** about 15 new searches a minute per visitor at Cloudflare, then 30 a minute per visitor and 300 a minute
  in total at the server (`SEARCHES_PER_MINUTE`, `ALL_SEARCHES_PER_MINUTE`), with one search computed at a time.
- **Logs:** the server logs one line per search, with a short hashed visitor id instead of the IP address:
  `radify logs api-citycouncil --since -1d --grep "search q="`. Searches answered from Cloudflare's cache never
  reach the server; those appear in the Cloudflare dashboard under Workers & Pages, cityhallvotes, Logs (kept 3 days).
- **Memory:** the model needs about 450 MB, so the app has a systemd override raising its limit to 900 MB
  (`/etc/systemd/system/app@api-citycouncil.service.d/override.conf` on step1, kept by radify's backups).
- **Running it:** in the panel, *Update search index*, then *Deploy search API*. Or `pipeline.py search-index` and
  `pipeline.py search-deploy`. The server downloads the model into its data directory on first start.
- **Tests:** `cargo test --release` in `search/`, plus the Python tests.

## Coverage

Each council's `city.json` lists the meeting types in scope: council meetings plus standing committees (for Guelph: City Council, Special Council, Budget, Council Planning and Committee of the Whole), from 2022-11-15. A meeting appears on the site once it has a summary; special meetings that only went into closed session are skipped. Every page carries a footer saying the site is produced automatically.

## Tests

    .venv/bin/python -m unittest discover tests

These cover parsing, the vote audit, transcripts, summary checks, clustering, communities and search chunking, and check
the downloaded data stays consistent. The search crate has its own: `cd search && cargo test --release`.
