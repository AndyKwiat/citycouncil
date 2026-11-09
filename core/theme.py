"""Each council's look (PLAN 4.6): one photo made into a soft duotone in its accent colour.

From cities/<slug>/theme/<photo> this makes, in state/theme/<slug>/ (not committed, rebuilt when the photo or the
settings change):
  header.jpg   a wide duotone strip shown faintly behind the page header
  emblem.png   a round crop for the header and the browser tab (128 px, shown at 64 or less)
  card.jpg     the council's card on the landing page
  og.jpg       1200x630, for link previews
"""
import hashlib, json, shutil
from core.common import STATE, log

OUTPUTS = ("header.jpg", "emblem.png", "card.jpg", "og.jpg")


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def duotone(img, dark, light):
    from PIL import ImageOps
    grey = ImageOps.autocontrast(ImageOps.grayscale(img), cutoff=1)
    return ImageOps.colorize(grey, black=hex_rgb(dark), white=hex_rgb(light))


def crop_to(img, ratio, focal):
    """The largest crop of the given width/height ratio, centred as near the focal point (0-1, 0-1) as fits."""
    w, h = img.size
    cw, ch = (w, round(w / ratio)) if w / h < ratio else (round(h * ratio), h)
    fx, fy = focal
    left = min(max(round(fx * w - cw / 2), 0), w - cw)
    top = min(max(round(fy * h - ch / 2), 0), h - ch)
    return img.crop((left, top, left + cw, top + ch))


def out_dir(city):
    return STATE / "theme" / city.slug


def ensure(city):
    """Make the theme images if they're missing or out of date; returns their folder, or None without a photo."""
    t = city.get("theme") or {}
    src = city.theme_dir / t.get("photo", "")
    if not t.get("photo") or not src.is_file():
        return None
    out = out_dir(city)
    stamp = hashlib.sha256(src.read_bytes() + json.dumps(t, sort_keys=True).encode()).hexdigest()
    if (out / "stamp").exists() and (out / "stamp").read_text() == stamp and all((out / n).exists() for n in OUTPUTS):
        return out
    from PIL import Image, ImageDraw
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    img = Image.open(src).convert("RGB")
    dark, light = t.get("duotone_dark", t["accent"]), t.get("duotone_light", "#f7f5ef")
    focal = tuple(t.get("focal_point", (0.5, 0.5)))
    tone = duotone(img, dark, light)
    if t.get("header_crop"):  # a portrait photo: use its most telling band for the wide header
        x0, y0, x1, y1 = t["header_crop"]
        w, h = tone.size
        band = tone.crop((round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h)))
    else:
        band = tone
    crop_to(band, 1600 / 520, (0.5, 0.5)).resize((1600, 520), Image.LANCZOS).save(out / "header.jpg", quality=72, optimize=True, progressive=True)
    crop_to(tone, 16 / 9, focal).resize((800, 450), Image.LANCZOS).save(out / "card.jpg", quality=78, optimize=True, progressive=True)
    crop_to(tone, 1200 / 630, focal).resize((1200, 630), Image.LANCZOS).save(out / "og.jpg", quality=80, optimize=True, progressive=True)
    square = crop_to(tone, 1, focal).resize((128, 128), Image.LANCZOS)
    mask = Image.new("L", (512, 512), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 511, 511), fill=255)
    emblem = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    emblem.paste(square, (0, 0), mask.resize((128, 128), Image.LANCZOS))
    emblem.save(out / "emblem.png", optimize=True)
    (out / "stamp").write_text(stamp)
    log(f"Theme images made for {city.slug} in {out}")
    return out


def copy_to(city, site_dir):
    """Put the theme images into the built site at <site_dir>/theme/. Returns True when there are any."""
    src = ensure(city)
    if not src:
        return False
    (site_dir / "theme").mkdir(parents=True, exist_ok=True)
    for n in OUTPUTS:
        shutil.copy(src / n, site_dir / "theme" / n)
    return True
