import hashlib, json, pathlib, time, urllib.request, urllib.error, urllib.parse
ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}
BASES = {"kitchener": "https://pub-kitchener.escribemeetings.com", "region": "https://pub-regionofwaterloo.escribemeetings.com"}
_last = {}
def _wait(url):
    host = urllib.parse.urlparse(url).netloc
    dt = time.time() - _last.get(host, 0)
    if dt < 1.05: time.sleep(1.05 - dt)
    _last[host] = time.time()
def fetch(url, data=None, cache_name=None, method=None, allow_status=False):
    """Cached fetch. Returns bytes, or (status, bytes) if allow_status."""
    key = cache_name or hashlib.sha1((url + (data.decode() if data else "")).encode()).hexdigest()
    p = CACHE / key
    meta = p.with_name(p.name + ".status")
    if p.exists():
        st = int(meta.read_text()) if meta.exists() else 200
        b = p.read_bytes()
        return (st, b) if allow_status else b
    _wait(url)
    hdr = dict(UA)
    if data: hdr["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdr, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            st, b = r.status, r.read()
    except urllib.error.HTTPError as e:
        if not allow_status: raise
        st, b = e.code, b""
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b); meta.write_text(str(st))
    return (st, b) if allow_status else b
