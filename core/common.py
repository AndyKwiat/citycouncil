"""Small helpers every step shares: paths, logging, polite HTTP and JSON files."""
import hashlib, json, pathlib, time, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE = ROOT / "state"
SITE = ROOT / "site"
# Several council sites refuse bare HTTP clients, so every request looks like a normal browser.
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126 Safari/537.36 citycouncil"}
POLITE_SECONDS = 1.0  # at most about one request a second to any one host
_last = {}


def log(*a):
    print(*a, flush=True)


def _wait(url):
    host = urllib.parse.urlsplit(url).hostname
    gap = time.monotonic() - _last.get(host, 0)
    if gap < POLITE_SECONDS:
        time.sleep(POLITE_SECONDS - gap)
    _last[host] = time.monotonic()


def request(url, data=None, headers=None, timeout=120):
    _wait(url)
    return urllib.request.urlopen(urllib.request.Request(url, data=data, headers={**UA, **(headers or {})}), timeout=timeout)


def get(url, timeout=120):
    with request(url, timeout=timeout) as r:
        return r.read()


def write_json(path, data):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    tmp.replace(path)


def read_json(path, default=None):
    try:
        return json.loads(pathlib.Path(path).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

