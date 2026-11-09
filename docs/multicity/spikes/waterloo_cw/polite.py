"""Polite cached HTTP fetcher: browser UA, >=1.1 s between requests per host, disk cache."""
import hashlib, os, time, urllib.parse
import requests

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dl", "cache")
os.makedirs(BASE, exist_ok=True)
_last = {}
S = requests.Session()
S.headers.update({"User-Agent": UA, "Accept-Language": "en-CA,en;q=0.9"})


def _wait(url):
    h = urllib.parse.urlparse(url).netloc
    dt = time.time() - _last.get(h, 0)
    if dt < 1.1:
        time.sleep(1.1 - dt)
    _last[h] = time.time()


def key(url, data=None):
    extra = repr(sorted(data.items())) if isinstance(data, dict) else repr(data)
    return hashlib.sha1((url + extra).encode()).hexdigest()


def get(url, binary=False, cache=True, **kw):
    p = os.path.join(BASE, key(url))
    if cache and os.path.exists(p):
        b = open(p, "rb").read()
        return b if binary else b.decode("utf-8", "replace")
    _wait(url)
    r = S.get(url, timeout=60, **kw)
    r.raise_for_status()
    if cache:
        open(p, "wb").write(r.content)
    return r.content if binary else r.text


def post(url, data, cache=True, **kw):
    p = os.path.join(BASE, key(url, {k: v for k, v in data.items() if k != "__RequestVerificationToken"}))
    if cache and os.path.exists(p):
        return open(p, "rb").read().decode("utf-8", "replace")
    _wait(url)
    r = S.post(url, data=data, timeout=60, **kw)
    r.raise_for_status()
    if cache:
        open(p, "wb").write(r.content)
    return r.text
