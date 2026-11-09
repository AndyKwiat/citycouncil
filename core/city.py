"""One council: its settings (cities/<slug>/city.json), where its data lives, its terms and its members."""
import datetime as dt, functools, re
from core.common import ROOT, SITE, read_json

CITIES = ROOT / "cities"
DATA = ROOT / "data"
DEFAULT = "guelph"


class City:
    def __init__(self, slug):
        self.slug = slug
        self.dir = CITIES / slug
        self.cfg = read_json(self.dir / "city.json")
        if not self.cfg:
            raise SystemExit(f"No council '{slug}': expected {self.dir / 'city.json'}")
        self.data = DATA / slug
        self.raw = self.data / "raw"
        self.votes = self.data / "votes"
        self.calendar = self.data / "calendar.json"
        self.site = SITE / slug
        self.portraits = self.dir / "portraits"
        self.theme_dir = self.dir / "theme"

    def __repr__(self):
        return f"City({self.slug!r})"

    # ---- names
    @property
    def name(self):  # "Guelph"
        return self.cfg["name"]

    @property
    def council_name(self):  # "Guelph City Council"
        return self.cfg["council_name"]

    @property
    def adapter(self):
        return self.cfg["adapter"]

    def get(self, key, default=None):
        return self.cfg.get(key, default)

    # ---- meeting types (D2)
    def meeting_type(self, name):
        """The in-scope type a council's own meeting name maps to, or None when it's out of scope."""
        return self.cfg["meeting_types"].get(name)

    def make_key(self, date, type_name):
        t = self.meeting_type(type_name) or {}
        return date + (f"-{t['slug']}" if t.get("slug") else "")

    # ---- terms (D5)
    @property
    def terms(self):
        return self.cfg.get("terms", [])

    def term_for(self, date):
        date = str(date)[:10]
        return next((t["id"] for t in self.terms if t["start"] <= date <= t["end"]), None)

    def term(self, term_id):
        return next((t for t in self.terms if t["id"] == term_id), None)

    @functools.cached_property
    def councillors(self):
        return read_json(self.dir / "councillors.json") or {}

    def members(self, term_id):
        """Members for a term, keyed by the name the minutes use."""
        return self.councillors.get("terms", {}).get(term_id, {})

    def council_size(self, term_id):
        """How many votes a full council casts; used to recognise vote counts written as digits."""
        t = self.term(term_id) or {}
        return t.get("seats") or len(self.members(term_id)) or 13

    def canonical(self, name, term_id):
        """Map a spelling seen in the minutes to the member's key, through the aliases in councillors.json."""
        members = self.members(term_id)
        if name in members:
            return name
        for key, m in members.items():
            if name in m.get("aliases", []):
                return key
        return name

    # ---- links
    @property
    def records_url(self):
        return self.cfg["urls"]["records"]


@functools.lru_cache(maxsize=None)
def load(slug=DEFAULT):
    return City(slug)


def all_slugs():
    return sorted(p.parent.name for p in CITIES.glob("*/city.json"))


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def today():
    return dt.date.today()
