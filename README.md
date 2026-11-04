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
