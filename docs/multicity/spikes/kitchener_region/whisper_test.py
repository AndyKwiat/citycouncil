"""Time Whisper on one full Kitchener Council meeting over HLS (modelled on pipeline.whisper_range)."""
import json, pathlib, re, subprocess, sys, time, urllib.parse, urllib.request, wave
import imageio_ffmpeg, mlx_whisper, numpy as np
OUT = pathlib.Path(__file__).resolve().parent.parent / "whisper"
OUT.mkdir(exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}
fname = sys.argv[1]
hls = f"https://sp2hls.isilive.ca/hls/file/kitchener/{urllib.parse.quote(fname)}/index.m3u8"
master = urllib.request.urlopen(urllib.request.Request(hls, headers=UA), timeout=60)
base, body = master.geturl(), master.read().decode()
variant = next(l for l in body.splitlines() if l and not l.startswith("#"))
time.sleep(1)
pl = urllib.request.urlopen(urllib.request.Request(urllib.parse.urljoin(base, variant), headers=UA), timeout=60).read().decode()
length = sum(float(x) for x in re.findall(r"#EXTINF:([\d.]+)", pl))
print(f"recording length {length:.0f}s ({length/3600:.2f} h)", flush=True)
wav = OUT / "audio.wav"
t0 = time.time()
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-i", hls,
                "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)], check=True)
pull = time.time() - t0
print(f"pulled {wav.stat().st_size/1e6:.0f} MB in {pull:.0f}s", flush=True)
with wave.open(str(wav)) as w:
    audio = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768.0
names = "Vrbanovic, Davey, Schnider, Deneault, Michaud, Owodunni, Singh, Ioannidis, Johnston, Chapman, Stretch"
prompt = f"Kitchener City Council meeting. Mayor Berry Vrbanovic and Councillors {names}. Kitchener, Ontario."
t0 = time.time()
r = mlx_whisper.transcribe(audio, path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language="en",
                           initial_prompt=prompt, condition_on_previous_text=False, verbose=None)
wt = time.time() - t0
print(f"whisper {wt:.0f}s; audio {len(audio)/16000:.0f}s; realtime factor {len(audio)/16000/wt:.1f}x", flush=True)
segs = [{"start": round(s["start"], 1), "end": round(s["end"], 1), "text": s["text"].strip()} for s in r["segments"]]
(OUT / "segments.json").write_text(json.dumps({"file": fname, "length": length, "pull_s": pull, "whisper_s": wt, "segments": segs}, indent=1))
(OUT / "transcript.txt").write_text("\n".join(f"[{s['start']:7.1f}] {s['text']}" for s in segs))
wav.unlink()
print("done", len(segs), "segments", flush=True)
