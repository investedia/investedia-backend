"""Share cards: one 1200x630 image + one small Open Graph page per article (option 9B, real Investedia logo).

Why a page per article: link previews (Messages, WhatsApp, X, LinkedIn ...) read the HTML of the shared URL and do not run JavaScript,
so the single-page article view cannot provide the preview. Each assets/share/<id>.html carries the Open Graph tags and sends people on
to story.html?id=<id>. Pages are marked noindex so they never compete with the real article page in search.

The pills show the real move of each exposed asset since the article was published (prices recorded in assets/globe/news-track.json).
Without a recorded price after the article they show today's move and say so. Without a priced asset they show the direction the
article implies, labelled as such. Nothing is invented.
"""
import json, math, os, sys, html
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
G = os.path.join(ROOT, 'assets', 'globe')
FONTS = os.path.join(ROOT, 'tools', 'share')
OUTS = [os.path.join(ROOT, 'assets', 'share'), os.path.join(ROOT, 'docs', 'assets', 'share')]
SITE = 'https://investedia.com'
W, H = 1200, 630
BG, FG, MUTED, ORANGE = (10, 10, 11), (255, 255, 255), (161, 161, 170), (255, 122, 26)
UP, DN, FLAT = (52, 211, 153), (248, 113, 113), (161, 161, 170)
CAT = {'markets': 'Markets', 'companies': 'Companies', 'economy': 'Economy', 'technology': 'Technology', 'crypto': 'Crypto', 'commodities': 'Commodities', 'geopolitics': 'Geopolitics'}
MAX_CARDS = 48
MIN = 60
LATE = 90 * 60


def load(path, default):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def parse(ts):
    return datetime.fromisoformat(str(ts).replace('Z', '+00:00')).astimezone(timezone.utc)


def resolve(ticker, known):
    t = str(ticker or '').upper()
    for c in (t, t + '-USD', t[:-2] if t.endswith('=X') else None):
        if c and c in known:
            return c
    return None


def move_since(published_ts, series):
    """Same rule as assets/since-news.js: first recorded price at/after publication to the latest one. None if not measurable."""
    pts = sorted((p[0] * 60, p[1]) for p in (series or []) if isinstance(p, list) and len(p) == 2 and p[1] and p[1] > 0)
    after = [p for p in pts if p[0] >= published_ts]
    if len(after) < 2:
        return None
    before = [p for p in pts if published_ts - 3 * 3600 <= p[0] < published_ts]
    if after[0][0] - published_ts > LATE and not before:
        return None
    return (after[-1][1] / after[0][1] - 1) * 100


def pills(story, by, track):
    """Up to two pills: (label, value or None, kind) with kind 'since' | 'today' | 'implied'."""
    out, seen = [], set()
    pub = parse(story['published_at']).timestamp()
    for i in story.get('impacts') or []:
        sym = resolve((i or {}).get('ticker'), by)
        if sym and sym not in seen:
            seen.add(sym)
            a = by[sym]
            v = move_since(pub, (track.get('s') or {}).get(sym))
            if v is not None:
                out.append((a.get('n') or i.get('name') or sym, v, 'since'))
            elif isinstance(a.get('d'), (int, float)):
                out.append((a.get('n') or i.get('name') or sym, a['d'], 'today'))
        if len(out) == 2:
            return out
    if not out:
        for i in story.get('impacts') or []:
            d = {'up': 1, 'down': -1}.get((i or {}).get('direction'))
            if d and i.get('name'):
                out.append((i['name'], d, 'implied'))
            if len(out) == 2:
                break
    return out


def caption(ps):
    kinds = {k for _, _, k in ps}
    if kinds == {'since'}:
        return 'Moves since the article was published'
    if kinds == {'today'}:
        return 'Moves today'
    if kinds == {'implied'}:
        return 'Direction the article implies'
    return 'Moves since the article, or today where not yet recorded'


def ago_text(published, now):
    m = max(0, int((now - parse(published)).total_seconds() // 60))
    if m < 60:
        return f'{max(1, m)} min ago'
    if m < 1440:
        return f'{m // 60} h ago'
    return f'{m // 1440} d ago'


def wrap(draw, text, font, width, lines=3):
    words, rows, cur = text.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if draw.textlength(t, font=font) <= width or not cur:
            cur = t
        else:
            rows.append(cur); cur = w
    rows.append(cur)
    if len(rows) > lines:
        rows = rows[:lines]
        while draw.textlength(rows[-1] + '…', font=font) > width and ' ' in rows[-1]:
            rows[-1] = rows[-1].rsplit(' ', 1)[0]
        rows[-1] += '…'
    return rows


def spaced(draw, xy, text, font, fill, tracking=2):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking
    return x


def draw_logo(d, F):
    s = 54; ox, oy = 56, 44
    d.rounded_rectangle((ox, oy, ox + s, oy + s), radius=int(s * .2), fill=(0, 0, 0))
    k = s / 40
    d.polygon([(ox + 0, oy + 31 * k), (ox + 11 * k, oy + 24.5 * k), (ox + 18 * k, oy + 29 * k), (ox + 28 * k, oy + 19 * k), (ox + 40 * k, oy + 25.5 * k), (ox + 40 * k, oy + 40 * k), (ox, oy + 40 * k)], fill=(30, 30, 33))
    d.line([(ox + 0, oy + 28 * k), (ox + 11 * k, oy + 21.5 * k), (ox + 18 * k, oy + 26 * k), (ox + 28 * k, oy + 16 * k), (ox + 40 * k, oy + 22.5 * k)], fill=ORANGE, width=max(2, int(4 * k)), joint='curve')
    wm = F('Inter-Bold.otf', 36); x = ox + s + 18; y = oy + 5
    d.text((x, y), 'Invested', font=wm, fill=FG); x2 = x + d.textlength('Invested', font=wm)
    d.text((x2, y), 'ı', font=wm, fill=FG); dot = x2 + d.textlength('ı', font=wm) / 2
    d.ellipse((dot - 4.2, y + 10, dot + 4.2, y + 18.4), fill=ORANGE)
    d.text((x2 + d.textlength('ı', font=wm), y), 'a', font=wm, fill=FG)


def render_site():
    """1200x630 default preview for the site (homepage and any page without its own card)."""
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    F = lambda n, sz: ImageFont.truetype(os.path.join(FONTS, n), sz)
    im = Image.new('RGB', (W, H), BG)
    dots = load(os.path.join(ROOT, 'tools', 'globe', 'dots.json'), [])
    lat0, lon0 = math.radians(22), math.radians(-18)
    R, cx, cy = 430, 900, 330
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    for k in range(0, len(dots) - 1, 2):
        lat, lon = math.radians(dots[k] / 10), math.radians(dots[k + 1] / 10)
        c = math.sin(lat0) * math.sin(lat) + math.cos(lat0) * math.cos(lat) * math.cos(lon - lon0)
        if c <= 0.02:
            continue
        x = cx + R * math.cos(lat) * math.sin(lon - lon0)
        y = cy - R * (math.cos(lat0) * math.sin(lat) - math.sin(lat0) * math.cos(lat) * math.cos(lon - lon0))
        d.ellipse((x - 1.5, y - 1.5, x + 1.5, y + 1.5), fill=(255, 150, 70, int(25 + 120 * c)))
    im.paste(layer, (0, 0), layer)
    ring = Image.new('RGBA', (W, H), (0, 0, 0, 0)); g = ImageDraw.Draw(ring)
    g.ellipse((cx - R, cy - R, cx + R, cy + R), outline=(255, 122, 26, 150), width=3)
    glow = ring.filter(ImageFilter.GaussianBlur(14)); im.paste(glow, (0, 0), glow); im.paste(ring, (0, 0), ring)
    pts = Image.new('RGBA', (W, H), (0, 0, 0, 0)); g = ImageDraw.Draw(pts)
    for lat_, lon_ in ((51.5, -0.1), (40.7, -74), (48.9, 2.3), (30, 31.2), (-23.5, -46.6), (25.2, 55.3), (35.7, 139.7), (-1.3, 36.8), (6.5, 3.4), (19.4, -99.1)):
        la, lo = math.radians(lat_), math.radians(lon_)
        c = math.sin(lat0) * math.sin(la) + math.cos(lat0) * math.cos(la) * math.cos(lo - lon0)
        if c <= 0.05:
            continue
        x = cx + R * math.cos(la) * math.sin(lo - lon0); y = cy - R * (math.cos(lat0) * math.sin(la) - math.sin(lat0) * math.cos(la) * math.cos(lo - lon0))
        g.ellipse((x - 16, y - 16, x + 16, y + 16), fill=(255, 122, 26, 120))
    pts = pts.filter(ImageFilter.GaussianBlur(9)); im.paste(pts, (0, 0), pts)
    d = ImageDraw.Draw(im)
    for lat_, lon_ in ((51.5, -0.1), (40.7, -74), (48.9, 2.3), (30, 31.2), (-23.5, -46.6), (25.2, 55.3), (35.7, 139.7), (-1.3, 36.8), (6.5, 3.4), (19.4, -99.1)):
        la, lo = math.radians(lat_), math.radians(lon_)
        c = math.sin(lat0) * math.sin(la) + math.cos(lat0) * math.cos(la) * math.cos(lo - lon0)
        if c <= 0.05:
            continue
        x = cx + R * math.cos(la) * math.sin(lo - lon0); y = cy - R * (math.cos(lat0) * math.sin(la) - math.sin(lat0) * math.cos(la) * math.cos(lo - lon0))
        d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=ORANGE)
    shade = Image.new('RGBA', (W, H)); px = shade.load()
    for x in range(W):
        a = int(max(0, min(1, (700 - x) / 420)) * 240)
        for y in range(H):
            px[x, y] = (10, 10, 11, a)
    im.paste(shade, (0, 0), shade); d = ImageDraw.Draw(im)
    draw_logo(d, F)
    big = F('Inter-Bold.otf', 84)
    d.text((56, 232), 'Invest with clarity.', font=big, fill=FG)
    d.text((56, 330), 'See the world move.', font=big, fill=(150, 150, 160))
    d.text((56, 566), 'investedia.com', font=F('Inter-SemiBold.otf', 26), fill=ORANGE)
    return im


def render(story, ps, now=None):
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    now = now or datetime.now(timezone.utc)
    F = lambda n, s: ImageFont.truetype(os.path.join(FONTS, n), s)
    im = Image.new('RGB', (W, H), BG)
    # Orthographic globe of land dots centred on the article location, glow on the spot.
    dots = load(os.path.join(ROOT, 'tools', 'globe', 'dots.json'), [])
    loc = story.get('location') or {}
    lat0, lon0 = math.radians(loc.get('lat', 20)), math.radians(loc.get('lon', 0))
    R, cx, cy = 760, 880, 470
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    for k in range(0, len(dots) - 1, 2):
        lat, lon = math.radians(dots[k] / 10), math.radians(dots[k + 1] / 10)
        c = math.sin(lat0) * math.sin(lat) + math.cos(lat0) * math.cos(lat) * math.cos(lon - lon0)
        if c <= 0.02:
            continue
        x = cx + R * math.cos(lat) * math.sin(lon - lon0)
        y = cy - R * (math.cos(lat0) * math.sin(lat) - math.sin(lat0) * math.cos(lat) * math.cos(lon - lon0))
        if -4 < x < W + 4 and -4 < y < H + 4:
            d.ellipse((x - 1.7, y - 1.7, x + 1.7, y + 1.7), fill=(255, 122, 26, int(30 + 120 * c)))
    im.paste(layer, (0, 0), layer)
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0)); g = ImageDraw.Draw(glow)
    g.ellipse((cx - 22, cy - 22, cx + 22, cy + 22), fill=(255, 122, 26, 200))
    glow = glow.filter(ImageFilter.GaussianBlur(26)); im.paste(glow, (0, 0), glow)
    d = ImageDraw.Draw(im); d.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), fill=ORANGE, outline=FG, width=2)
    # Darken the left so the text reads cleanly.
    shade = Image.new('RGBA', (W, H)); px = shade.load()
    for x in range(W):
        a = int(max(0, min(1, (760 - x) / 560)) * 235)
        for y in range(0, H):
            px[x, y] = (10, 10, 11, a)
    im.paste(shade, (0, 0), shade); d = ImageDraw.Draw(im)
    draw_logo(d, F)
    # Eyebrow
    place = (loc.get('place') or '').split(',')[0]
    eb = ' · '.join(p for p in [CAT.get(story.get('category'), '').upper(), place.upper(), parse(story['published_at']).strftime('%d %b · %H:%M UTC').lstrip('0').upper()] if p)
    spaced(d, (56, 150), eb, F('Inter-SemiBold.otf', 21), MUTED, 2.2)
    # Headline
    hf = F('Inter-Bold.otf', 50)
    rows = wrap(d, story['headline'], hf, 740, 3)
    y = 190
    for r in rows:
        d.text((56, y), r, font=hf, fill=FG); y += 62
    # Pills
    py = max(y + 22, 372); pf, vf = F('Inter-SemiBold.otf', 27), F('Inter-Bold.otf', 27); px_ = 56
    for name, v, kind in pills_cache(story, ps):
        col = UP if v > 0 else DN if v < 0 else FLAT
        arrow = '↑' if v > 0 else '↓' if v < 0 else '↔'
        val = arrow if kind == 'implied' else f'{arrow} {abs(v):.2f}%'
        name = name if d.textlength(name, font=pf) < 300 else name[:22].rstrip() + '…'
        wn, wv = d.textlength(name, font=pf), d.textlength(val, font=vf)
        pw = 22 + wn + 14 + wv + 22
        d.rounded_rectangle((px_, py, px_ + pw, py + 52), radius=26, fill=(14, 14, 16), outline=(70, 70, 76), width=2)
        d.text((px_ + 22, py + 9), name, font=pf, fill=FG); d.text((px_ + 22 + wn + 14, py + 9), val, font=vf, fill=col)
        px_ += pw + 14
    if ps:
        d.text((56, py + 70), caption(ps), font=F('Inter-Medium.otf', 24), fill=MUTED)
    d.text((56, 566), 'investedia.com', font=F('Inter-SemiBold.otf', 26), fill=MUTED)
    return im


def pills_cache(story, ps):
    return ps


def page(story, now=None):
    sid = story['id']
    title = html.escape(story['headline'], quote=True)
    desc = html.escape((story.get('summary') or 'News and market intelligence on Investedia.')[:200], quote=True)
    img = f'{SITE}/assets/share/{sid}.png'
    go = f'../../story.html?id={sid}'
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{title} · Investedia</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><meta name="description" content="{desc}">
<link rel="canonical" href="{SITE}/story.html?id={sid}">
<meta property="og:site_name" content="Investedia"><meta property="og:type" content="article"><meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}"><meta property="og:url" content="{SITE}/assets/share/{sid}.html">
<meta property="og:image" content="{img}"><meta property="og:image:width" content="{W}"><meta property="og:image:height" content="{H}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{title}"><meta name="twitter:description" content="{desc}"><meta name="twitter:image" content="{img}">
<meta http-equiv="refresh" content="0;url={go}"><script>location.replace({json.dumps(go)})</script></head>
<body style="background:#0a0a0b;color:#fff;font-family:system-ui,sans-serif"><p style="padding:24px">Opening <a style="color:#ff9a4d" href="{go}">{title}</a>…</p></body></html>
'''


def run(now=None):
    now = now or datetime.now(timezone.utc)
    stories = (load(os.path.join(G, 'news-live.json'), {}).get('stories')) or []
    markets = load(os.path.join(G, 'markets.json'), {})
    extra = load(os.path.join(G, 'news-prices.json'), {})
    by = {}
    for k, a in (extra.get('assets') or {}).items():
        if isinstance(a, dict):
            by[k] = a
    for a in markets.get('assets') or []:
        if isinstance(a, dict) and a.get('s'):
            by[a['s']] = a
    track = load(os.path.join(G, 'news-track.json'), {})
    keep, made = set(), 0
    from PIL import Image
    for out in OUTS:
        os.makedirs(out, exist_ok=True)
    stories = sorted((s for s in stories if s.get('published_at')), key=lambda s: s['published_at'], reverse=True)[:MAX_CARDS]
    for s in stories:
        if not s.get('id') or not s.get('headline') or not s.get('published_at'):
            continue
        keep.add(s['id'])
        ps = pills(s, by, track)
        sig = json.dumps([s['headline'], s.get('location'), [(n, round(v, 2), k) for n, v, k in ps]], sort_keys=True)
        marker = os.path.join(OUTS[0], s['id'] + '.json')
        if os.path.exists(marker) and open(marker).read() == sig and os.path.exists(os.path.join(OUTS[0], s['id'] + '.png')):
            continue
        try:
            im = render(s, ps, now)
        except Exception as e:
            print('share card failed', s['id'], type(e).__name__, e); continue
        for out in OUTS:
            im.convert('P', palette=Image.ADAPTIVE, colors=128).save(os.path.join(out, s['id'] + '.png'), optimize=True)
            with open(os.path.join(out, s['id'] + '.html'), 'w', encoding='utf-8') as f:
                f.write(page(s))
            with open(os.path.join(out, s['id'] + '.json'), 'w') as f:
                f.write(sig)
        made += 1
    for out in OUTS:
        with open(os.path.join(out, 'index.json'), 'w') as f:
            json.dump(sorted(keep), f, separators=(',', ':'))
    removed = 0
    for out in OUTS:
        for fn in os.listdir(out):
            if fn == 'index.json':
                continue
            sid = fn.rsplit('.', 1)[0]
            if fn.endswith(('.png', '.html', '.json')) and sid not in keep:
                os.remove(os.path.join(out, fn)); removed += 1
    return made, removed, len(keep)


if __name__ == '__main__':
    if '--site' in sys.argv:
        from PIL import Image
        im = render_site()
        for out in (os.path.join(ROOT, 'assets'), os.path.join(ROOT, 'docs', 'assets')):
            os.makedirs(out, exist_ok=True)
            im.convert('P', palette=Image.ADAPTIVE, colors=160).save(os.path.join(out, 'og-default.png'), optimize=True)
        print('site card written'); sys.exit(0)
    try:
        m, r, n = run()
        print(f'share cards: {n} articles, {m} drawn, {r} old files removed')
    except Exception as e:
        print('share cards failed, keeping the previous files:', type(e).__name__, e)
    sys.exit(0)
