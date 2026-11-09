import json, sys, datetime as dt
from common import *
def months(a, b):
    y, m = a
    while (y, m) <= b:
        yield y, m
        y, m = (y + (m == 12), m % 12 + 1)
for council, base in BASES.items():
    allm = {}
    for y, m in months((2021, 1), (2026, 12)):
        s = dt.date(y, m, 1); e = (dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1))
        body = json.dumps({"calendarStartDate": s.isoformat(), "calendarEndDate": e.isoformat()}).encode()
        r = json.loads(fetch(base + "/MeetingsCalendarView.aspx/GetCalendarMeetings", body, f"cal/{council}/{y}-{m:02d}.json"))["d"]
        for x in r: allm[x["ID"]] = x
        print(council, y, m, len(r), flush=True)
    (CACHE / f"cal_{council}.json").write_text(json.dumps(list(allm.values()), indent=1))
