# Guelph City Council

Static site of council meeting summaries, driven from a local admin panel.

    ./admin

Opens http://127.0.0.1:8750/. Everything runs from there: checking for meetings, processing them,
updating the website, and deploying it to citycouncil.akwiat.com (private to you@example.com).

- `pipeline.py` does the work: calendar, documents, minutes parsing, transcripts, summaries, deploy.
- `build.py` renders `raw/<date>/` into `site/`.
- `admin.py` and `admin.html` are the panel and its one-at-a-time job runner.
- Transcripts use the city's closed captions. Whisper runs only on gaps of 5+ minutes, or on the whole
  recording if the captions are under 10 words per minute.
- Summaries call the `claude` CLI with your existing login, so no API key is needed.
- Vote counts and who voted how come straight from the minutes, never from the summary.

## Votes

`votes/` is rewritten whenever minutes are parsed:

- `votes.json`: every motion with who voted which way.
- `motions.csv`: the same, one row per motion.
- `votes_by_councillor.csv`: one row per councillor per recorded vote, for analysis.

Each meeting's parse also checks its votes against the raw minutes (counts, names, anything written outside
a motion block). Problems show in red in the panel's Votes column and in the job log.

## Who votes with whom

`site/councillors.html` is rebuilt with every website update, from the non-unanimous votes in `votes/votes.json`.

- Line thickness and the hover percentages use the share of votes both people attended, not a raw count, because some members served only part of the term.
- `analysis.py` finds the voting groups and writes `votes/clusters.json`. The number of groups comes from the data (silhouette score), and anyone scoring under 0.1 is shown between groups. People who never voted together get an estimated distance instead of being treated as opposites.
- Names, wards and photos live in `councillors.json` and `portraits/`. After an election, add new members there or they appear with only the name from the minutes and no photo. The page also mixes every council in `raw/`, so a new term will need a filter by term.

## Voting Alliance Network

The top of the councillors page. `alliance_network.py` prepares the data and markup, and `alliance_network.js` runs the graph with no external libraries. Add further visualizations the same way, as a `section()` plus a script passed to `build.page()`.

- Percentages come straight from the votes both people attended. A pair who never voted together has no line and shows as unknown, never 0%.
- Positions use every known pair, so the slider never moves anyone. Layout starts from fixed positions, so it is the same on every visit.
- Communities come from Louvain (`analysis.communities`) on agreement above the council's average, on the full network regardless of the slider. They can differ from the voting groups on the map, which use hierarchical clustering.

## Coverage

Only meetings the city labels "City Council" are processed, from December 6, 2022. Inaugural, special, budget and Council Planning meetings aren't, so their votes aren't counted.

## Tests

    .venv/bin/python -m unittest discover tests

These cover parsing, the vote audit, transcripts, summary checks and clustering, and check the downloaded data stays consistent.
