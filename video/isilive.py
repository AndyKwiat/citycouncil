"""ISI Live, the video service behind eSCRIBE: player file name, closed captions and the HLS audio stream."""
import html, re, urllib.parse
from core.common import get, request


def player_url(base, meeting_id):
    return f"{base}/Players/ISIStandAlonePlayer.aspx?Id={meeting_id}"


def file_name(base, meeting_id):
    """The recording's file name, read from eSCRIBE's player page; None when the player has none."""
    player = get(player_url(base, meeting_id)).decode("utf8", "ignore")
    found = re.search(r'data-file_name="([^"]+)"', player)
    return html.unescape(found.group(1)) if found else None


def captions_url(client, name):
    return f"https://video.isilive.ca/{client}/{urllib.parse.quote(name)}.vtt"


def hls_url(client, name):
    return f"https://sp2hls.isilive.ca/hls/file/{client}/{urllib.parse.quote(name)}/index.m3u8"


def part(base, client, meeting_id, name):
    """One recording, in the shape meeting.json keeps under video.parts."""
    return {"url": player_url(base, meeting_id), "file": name, "hls": hls_url(client, name), "captions": captions_url(client, name)}


def recording_seconds(hls):
    with request(hls, timeout=60) as master:
        base, body = master.geturl(), master.read().decode()
    variant = next(l for l in body.splitlines() if l and not l.startswith("#"))
    playlist = get(urllib.parse.urljoin(base, variant), 60).decode()
    return sum(float(x) for x in re.findall(r"#EXTINF:([\d.]+)", playlist))
