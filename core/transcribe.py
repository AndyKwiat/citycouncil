"""Transcripts: closed captions first, Whisper on gaps of 5+ minutes or on the whole recording if captions are thin."""
import pathlib, re, subprocess, tempfile, time, wave
from core.common import log, read_json, write_json
from video import isilive, youtube

WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"
MIN_WORDS_PER_MIN = 10   # below this over a whole recording, the captions are effectively missing
GAP_SECONDS = 300        # silence in the captions this long gets checked with Whisper
GAP_SPEECH_WPM = 20      # Whisper finding this much speech in a gap means the captions missed it


def seconds(t):
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def parse_vtt(text):
    cues = re.findall(r"(\d\d:\d\d:\d\d\.\d+) --> (\d\d:\d\d:\d\d\.\d+)[^\n]*\n(.*?)(?:\n\n|\Z)", text, re.S)
    return [{"start": round(seconds(a), 1), "end": round(seconds(b), 1), "text": " ".join(t.split()),
             "source": "captions"} for a, b, t in cues if t.strip()]


def clean_segments(segs):
    """Drop Whisper's silence hallucinations and runs of repeated lines."""
    out, last, repeats = [], None, 0
    for s in segs:
        t = s["text"].strip()
        if not t or (s.get("no_speech", 0) > 0.6 and s.get("logprob", 0) < -0.5):
            continue
        repeats = repeats + 1 if t == last else 0
        last = t
        if repeats < 2:
            out.append(s)
    return out


TITLE = r"(?:Councill?ors?|Counsell?ors?|Counci?lor|Mayor|Chair|Regional Chair)"


def fix_names(segs, roster):
    """Whisper mishears members' names ("Chaplin" for Chapman). Its name prompt only covers the first 30 seconds, so
    names right after a title are matched to the meeting's roster instead, when they are close."""
    import difflib
    names = sorted({n.replace("Mayor ", "") for n in roster})
    if not names:
        return segs

    def swap(m):
        word = m.group(2)
        if word in names:
            return m.group(0)
        close = difflib.get_close_matches(word, names, n=1, cutoff=0.6)
        return f"{m.group(1)} {close[0]}" if close else m.group(0)
    for s in segs:
        s["text"] = re.sub(rf"\b({TITLE})\s+([A-Z][A-Za-z'’-]+)", swap, s["text"])
    return segs


def whisper_range(city, d, hls, roster, start=None, length=None):
    """Transcribe all or part of a recording's audio; returns segments with recording-relative times."""
    import imageio_ffmpeg, mlx_whisper, numpy as np
    names = ", ".join(n.replace("Mayor ", "") for n in roster)
    prompt = f"{city.council_name} meeting. Mayor and Councillors {names}. {city.get('place', city.name)}."
    with tempfile.TemporaryDirectory(dir=d) as tmp:
        wav = pathlib.Path(tmp) / "audio.wav"
        cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y"]
        if start is not None:
            cmd += ["-ss", str(start), "-t", str(length)]
        cmd += ["-i", hls, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)]
        t0 = time.time()
        subprocess.run(cmd, check=True)
        log(f"    pulled {wav.stat().st_size / 1e6:.0f} MB of audio in {time.time() - t0:.0f}s, transcribing...")
        with wave.open(str(wav)) as w:
            audio = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768.0
    t0 = time.time()
    r = mlx_whisper.transcribe(audio, path_or_hf_repo=WHISPER_MODEL, language="en", initial_prompt=prompt,
                               condition_on_previous_text=False, verbose=None)
    log(f"    Whisper finished in {time.time() - t0:.0f}s")
    offset = start or 0
    return fix_names(clean_segments([{"start": round(s["start"] + offset, 1), "end": round(s["end"] + offset, 1),
                            "text": s["text"].strip(), "no_speech": round(s["no_speech_prob"], 3),
                            "logprob": round(s["avg_logprob"], 3), "source": "whisper"} for s in r["segments"]]), roster)


def find_gaps(segs, lo, hi):
    gaps, last = [], lo
    for s in segs:
        if s["start"] > hi:
            break
        if s["start"] - last >= GAP_SECONDS:
            gaps.append((last, s["start"]))
        last = max(last, s["end"])
    if hi - last >= GAP_SECONDS:
        gaps.append((last, hi))
    return gaps


def transcribe(city, m, force=False, whisper=False):
    d = city.raw / m["key"]
    meta_path, out = d / "transcript_meta.json", d / "transcript.json"
    if out.exists() and meta_path.exists() and not force and not whisper:
        log("  transcript already done")
        return True
    if (m.get("video") or {}).get("provider") == "youtube":
        return transcribe_youtube(city, m, d, out, meta_path)
    parts = [x for x in ((m.get("video") or {}).get("parts") or []) if x.get("hls")]
    if not parts:
        log("  skipped transcript: no video for this meeting")
        return False
    hls = parts[0]["hls"]
    minutes = read_json(d / "minutes.json") or {}
    roster = minutes.get("roster", [])
    duration = isilive.recording_seconds(hls)
    captions = parse_vtt((d / "captions.vtt").read_text()) if (d / "captions.vtt").exists() else []
    words = sum(len(s["text"].split()) for s in captions)
    wpm = words / max(duration / 60, 1)
    meta = {"recording_seconds": round(duration), "caption_words": words, "caption_wpm": round(wpm, 1), "gaps": []}
    log(f"  captions: {words:,} words over {duration / 3600:.1f} h = {wpm:.1f} words per minute")

    if whisper or wpm < MIN_WORDS_PER_MIN:
        log("  " + ("Whisper requested" if whisper else f"captions too thin (under {MIN_WORDS_PER_MIN} wpm)") + ": transcribing the whole recording")
        segs = whisper_range(city, d, hls, roster)
        meta["method"] = "whisper"
        meta["reason"] = "requested" if whisper else "captions mostly missing"
    else:
        # Only speech between the first and last agenda bookmark matters; before and after is setup and tear-down.
        spans = [(i["video_start"], i["video_end"]) for i in minutes.get("items", []) if i.get("video_start") is not None]
        lo = min((a for a, _ in spans), default=0)
        hi = max((b for _, b in spans), default=duration)
        segs = list(captions)
        filled = 0
        for a, b in find_gaps(captions, lo, hi):
            log(f"  gap in captions {a / 60:.0f}-{b / 60:.0f} min: checking the audio with Whisper")
            found = whisper_range(city, d, hls, roster, a, b - a)
            n = sum(len(s["text"].split()) for s in found)
            real = n / max((b - a) / 60, 1) >= GAP_SPEECH_WPM
            meta["gaps"].append({"start": round(a), "end": round(b), "whisper_words": n, "filled": real})
            log(f"    {n} words found: " + ("speech the captions missed, merging it in" if real else "no real speech (likely closed session or recess)"))
            if real:
                segs += found
                filled += 1
        segs.sort(key=lambda s: s["start"])
        meta["method"] = "captions+whisper" if filled else "captions"
    meta["source"] = {"captions": "isilive-captions", "captions+whisper": "mixed", "whisper": "whisper"}[meta["method"]]
    meta["words"] = sum(len(s["text"].split()) for s in segs)
    write_json(out, segs)
    write_json(meta_path, meta)
    log(f"  transcript saved: {meta['method']}, {meta['words']:,} words")
    return True


def transcribe_youtube(city, m, d, out, meta_path):
    """YouTube's automatic captions, one video after another; a later part's times continue from the earlier ones."""
    segs, offset, parts = [], 0.0, []
    for part in m["video"]["parts"]:
        f = youtube.captions(part["youtube_id"], d / "source" / "captions")
        found = youtube.parse_json3(f, offset) if f else []
        parts.append({"youtube_id": part["youtube_id"], "offset": round(offset), "captions": bool(found)})
        segs += found
        offset += part.get("duration") or (found[-1]["end"] - offset if found else 0)
    if not segs:
        log("  no YouTube captions for this meeting")
        return False
    words = sum(len(s["text"].split()) for s in segs)
    meta = {"method": "youtube-auto", "source": "youtube-auto", "recording_seconds": round(offset), "caption_words": words,
            "caption_wpm": round(words / max(offset / 60, 1), 1), "gaps": [], "words": words, "parts": parts}
    write_json(out, segs)
    write_json(meta_path, meta)
    log(f"  transcript saved from YouTube captions: {len(parts)} part(s), {words:,} words")
    return True
