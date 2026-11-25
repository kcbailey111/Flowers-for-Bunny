"""Spinning 3D ASCII bouquet for Bunny.

Builds a 3D point model (roses, stems, ivy leaves, wrapping paper), renders it
as shaded ASCII from many angles, and bakes the frames into index.html.
Run `python flowers.py --play` to also watch it spin in the terminal.
"""
import html
import json
import math
import sys
import time

NAME = "Bunny"
PINK = "#FA8072"   # AKA salmon pink
GREEN = "#8DB600"  # AKA apple green
PAPER = "#f3e9e4"

W, H = 80, 46
FRAMES = 72
SHADES = ".,-~:;=!*#$@"
LIGHT = (-0.4, 0.7, -0.6)


def norm(v):
    l = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2) or 1.0
    return (v[0] / l, v[1] / l, v[2] / l)


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def rot_x(p, a):
    c, s = math.cos(a), math.sin(a)
    return (p[0], p[1] * c - p[2] * s, p[1] * s + p[2] * c)


def rot_y(p, a):
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c + p[2] * s, p[1], -p[0] * s + p[2] * c)


def rot_z(p, a):
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c, p[2])


def surface(f, us, vs, color, transform):
    """Sample a parametric surface f(u, v) into (point, normal, color) tuples."""
    pts = []
    eps = 1e-3
    for u in us:
        for v in vs:
            p = f(u, v)
            du = [a - b for a, b in zip(f(u + eps, v), p)]
            dv = [a - b for a, b in zip(f(u, v + eps), p)]
            n = norm(cross(du, dv))
            pts.append((transform(p), transform(n, True), color))
    return pts


def frange(a, b, n):
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def rose_point(x1, th):
    """Paul Nylander's parametric rose. Returns (x, y-up, z)."""
    phi = (math.pi / 2) * math.exp(-th / (8 * math.pi))
    X = 1 - 0.5 * (1.25 * (1 - ((3.6 * th) % (2 * math.pi)) / math.pi) ** 2 - 0.25) ** 2
    y = 1.95653 * x1 ** 2 * (1.27689 * x1 - 1) ** 2 * math.sin(phi)
    r = X * (x1 * math.sin(phi) + y * math.cos(phi))
    h = X * (x1 * math.cos(phi) - y * math.sin(phi))
    return (r * math.sin(th), h, r * math.cos(th))


def placed(offset, scale=1.0, tilt_x=0.0, tilt_z=0.0):
    def t(p, is_normal=False):
        q = rot_z(rot_x(p, tilt_x), tilt_z)
        if is_normal:
            return q
        return (q[0] * scale + offset[0], q[1] * scale + offset[1], q[2] * scale + offset[2])
    return t


def tube(a, b, radius, color, n_len=40, n_around=8):
    ax, ay, az = a
    d = (b[0] - ax, b[1] - ay, b[2] - az)
    dn = norm(d)
    side = norm(cross(dn, (0, 0, 1) if abs(dn[2]) < 0.9 else (1, 0, 0)))
    up = cross(dn, side)
    pts = []
    for i in range(n_len):
        t = i / (n_len - 1)
        c = (ax + d[0] * t, ay + d[1] * t, az + d[2] * t)
        for j in range(n_around):
            ang = 2 * math.pi * j / n_around
            n = tuple(side[k] * math.cos(ang) + up[k] * math.sin(ang) for k in range(3))
            pts.append(((c[0] + n[0] * radius, c[1] + n[1] * radius, c[2] + n[2] * radius), n, color))
    return pts


def leaf(base, direction, length, width, color):
    dn = norm(direction)
    side = norm(cross(dn, (0, 0, 1)))
    normal = cross(side, dn)
    pts = []
    for u in frange(0, 1, 18):
        half = width * math.sin(math.pi * u) * (1 - 0.3 * u)
        for v in frange(-1, 1, 9):
            curl = 0.15 * length * (v * v)
            p = tuple(base[k] + dn[k] * u * length + side[k] * v * half + normal[k] * curl for k in range(3))
            pts.append((p, normal, color))
    return pts


def build_scene():
    pts = []
    gather = (0.0, -0.9, 0.0)
    roses = [
        ((0.0, 1.55, 0.0), 0.75, -0.25, 0.0),
        ((-0.95, 1.05, 0.25), 0.62, -0.2, 0.35),
        ((0.95, 1.05, 0.25), 0.62, -0.2, -0.35),
        ((-0.45, 0.85, -0.7), 0.55, 0.3, 0.2),
        ((0.5, 0.9, -0.65), 0.55, 0.3, -0.2),
    ]
    for offset, scale, tx, tz in roses:
        pts += surface(rose_point, frange(0, 1, 22), frange(-2 * math.pi, 15 * math.pi, 420),
                       "p", placed(offset, scale, tx, tz))
        pts += tube(offset, gather, 0.035, "g")
        mid = tuple((offset[k] + gather[k]) / 2 for k in range(3))
        pts += leaf(mid, (offset[0] * 1.5 + 0.3, 0.4, offset[2] + 0.3), 0.55, 0.22, "g")
        pts += leaf(mid, (offset[0] * 1.5 - 0.3, 0.2, offset[2] - 0.3), 0.45, 0.18, "g")

    pts += tube(gather, (0.0, -2.5, 0.0), 0.12, "g")

    def cone(u, v):
        r = 0.18 + 1.05 * u
        y = -2.35 + 1.9 * u
        wave = 0.06 * math.sin(7 * v) * u
        return ((r + wave) * math.cos(v), y, (r + wave) * math.sin(v))
    pts += surface(cone, frange(0, 1, 30), frange(0, 2 * math.pi, 110), "w", placed((0, 0, 0)))

    def ribbon(u, v):
        return (0.42 * math.cos(v), -1.95 + 0.14 * u, 0.42 * math.sin(v))
    pts += surface(ribbon, frange(0, 1, 5), frange(0, 2 * math.pi, 90), "g", placed((0, 0, 0)))
    return pts


def render(pts, angle):
    chars = [[" "] * W for _ in range(H)]
    colors = [[" "] * W for _ in range(H)]
    zbuf = [[-1e9] * W for _ in range(H)]
    light = norm(LIGHT)
    k2, k1 = 7.5, 118
    for p, n, col in pts:
        x, y, z = rot_y(p, angle)
        nx, ny, nz = rot_y(n, angle)
        ooz = 1 / (z + k2)
        xp = int(W / 2 + k1 * x * ooz)
        yp = int(H / 2 - 0.5 * k1 * (y - 0.2) * ooz)
        if 0 <= xp < W and 0 <= yp < H and ooz > zbuf[yp][xp]:
            zbuf[yp][xp] = ooz
            lum = abs(nx * light[0] + ny * light[1] + nz * light[2])
            chars[yp][xp] = SHADES[min(len(SHADES) - 1, int(lum * len(SHADES)))]
            colors[yp][xp] = col
    return "\n".join("".join(r) for r in chars), "\n".join("".join(r) for r in colors)


MESSAGE = [
    f"For my beautiful {NAME} 💗💚",
    "Pink tea roses for my Pretty Pearl,",
    "ivy that grows as strong as you.",
    "Alpha Kappa Alpha · Est. 1908 · J-15",
    "Service to all mankind, and all my love to you.",
]


def build_html(frames, path="python_version.html"):
    msg = "".join(f"<p>{html.escape(line)}</p>" for line in MESSAGE)
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Flowers for {NAME} 💗💚</title>
<style>
  body {{ margin:0; min-height:100vh; display:flex; flex-direction:column; align-items:center;
         justify-content:center; background:radial-gradient(#3a1f24, #120a0c); color:{PAPER};
         font-family:Georgia, serif; overflow-x:hidden; }}
  h1 {{ font-weight:normal; letter-spacing:.4em; margin:.6em 0 0; color:{PINK};
        text-shadow:0 0 12px {PINK}88; font-size:clamp(18px, 5vw, 34px); }}
  h2 {{ font-weight:normal; letter-spacing:.8em; margin:.2em 0; color:{GREEN};
        font-size:clamp(12px, 3vw, 18px); }}
  pre {{ font-family:"Courier New", monospace; font-size:clamp(5px, 1.55vw, 13px);
         line-height:1; margin:.5em 0; cursor:grab; }}
  .p {{ color:{PINK}; }} .g {{ color:{GREEN}; }} .w {{ color:{PAPER}; }}
  .msg {{ text-align:center; line-height:1.5; font-size:clamp(13px, 3.5vw, 18px); padding:0 1em 2em; }}
  .msg p {{ margin:.2em 0; opacity:0; animation:fade 1s forwards; }}
  @keyframes fade {{ to {{ opacity:1; }} }}
</style>
</head>
<body>
<h1>SKEE-WEE!</h1>
<h2>ΑΚΑ</h2>
<pre id="art"></pre>
<div class="msg">{msg}</div>
<script>
const frames = {json.dumps(frames)};
const art = document.getElementById('art');
const esc = c => c === '<' ? '&lt;' : c === '>' ? '&gt;' : c === '&' ? '&amp;' : c;
const htmlFrames = frames.map(([chars, cols]) => {{
  let out = '', run = '', cur = null;
  for (let i = 0; i < chars.length; i++) {{
    const c = cols[i] === '\\n' ? null : cols[i];
    if (c !== cur) {{ if (run) out += cur && cur !== ' ' ? `<span class="${{cur}}">${{run}}</span>` : run; run = ''; cur = c; }}
    run += esc(chars[i]);
  }}
  return out + (cur && cur !== ' ' ? `<span class="${{cur}}">${{run}}</span>` : run);
}});
let f = 0, speed = 1, dragX = null;
setInterval(() => {{ f = (f + speed + frames.length) % frames.length; art.innerHTML = htmlFrames[Math.floor(f)]; }}, 70);
art.addEventListener('pointerdown', e => {{ dragX = e.clientX; speed = 0; }});
addEventListener('pointermove', e => {{ if (dragX !== null) {{ f = (f + (e.clientX - dragX) / 8 + frames.length) % frames.length; dragX = e.clientX; }} }});
addEventListener('pointerup', () => {{ dragX = null; speed = 1; }});
document.querySelectorAll('.msg p').forEach((p, i) => p.style.animationDelay = (1 + i * 0.8) + 's');
</script>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(f"Wrote {path}")


def play(frames):
    ansi = {"p": "\033[38;2;250;128;114m", "g": "\033[38;2;141;182;0m", "w": "\033[38;2;243;233;228m"}
    print("\033[2J", end="")
    try:
        while True:
            for chars, cols in frames:
                out = "".join(ansi.get(cl, "") + ch for ch, cl in zip(chars, cols))
                print("\033[H" + out + "\033[0m", flush=True)
                time.sleep(0.07)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    print("Building 3D bouquet...")
    scene = build_scene()
    frames = [render(scene, 2 * math.pi * i / FRAMES) for i in range(FRAMES)]
    build_html(frames)
    if "--play" in sys.argv:
        play(frames)
    else:
        print(frames[0][0])
