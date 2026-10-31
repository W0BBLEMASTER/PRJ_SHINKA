"""
M.SOU / FRIENDLY PLUMBER body prototype v10 (Windows 10/11)
-----------------------------------------------------------
Primitives and generated meshes only, no imported assets.

Keys:
  1 Look behind (hands claw while he faces away)   2 Face user (Active)
  3 Face user (Deactive)   4 Hunt (floating zombie reach, Springtrap glitch frames)
  5 Wave (looks up and off to his left, waves with his left)
  6 Hips (fists on hips, wrists bent out)   7 Point (index, palm down)   8 Glance (walks away, looks back over the shoulder)
  9 Glare   0 Doubt (hands on hips)
  T Cross: snaps into a T-pose in ONE frame, hands drop like rags, Springtrap twitches
  H flip both hands 180 degrees about the arm (toggle)
  G glitch on/off      L cycle lighting: basic / shadows / flat
  Q / E nudge yaw      Esc quit

Camera auto-fits the window. Starts in basic lighting. Press L to try the
shadow shader (untested on real GPUs, it segfaults under software GL).

"his left" = the figure's left = the viewer's right (+x).
Hands: 3 joints per finger and thumb, spring driven (floppy) except in Hunt,
where they lock rigid and spread. Default hand is a proper left/right pair
(thumb forward, palm toward the thigh when the arm hangs).
"""

import sys, math, random
print("[1/5] importing ursina...", flush=True)
from ursina import *
from ursina.shaders import unlit_shader, basic_lighting_shader, lit_with_shadows_shader
print("[2/5] ursina imported OK", flush=True)

print("[3/5] creating window...", flush=True)
app = Ursina(borderless=False, fullscreen=False, vsync=False,
             title="FRIENDLY PLUMBER", development_mode=True)
window.position = Vec2(100, 100)
window.size = Vec2(1024, 768)
window.always_on_top = False
window.exit_button.visible = True
print("[4/5] window created OK", flush=True)

GLITCH_FRAMES = 1     # Hunt: how many frames each Springtrap twitch lasts

# ---------------------------------------------------------------------
# Mesh generators. A Mesh can only live under ONE Entity, so every part
# builds its own instance. All are rendered double-sided.
# ---------------------------------------------------------------------
def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])

def _unit(n):
    ln = math.sqrt(sum(t * t for t in n)) or 1.0
    return tuple(t / ln for t in n)

def _smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)

def make_cylinder(res=18):
    verts, tris, norms = [], [], []
    r = 0.5
    for i in range(res):
        a0, a1 = 2 * math.pi * i / res, 2 * math.pi * (i + 1) / res
        c0, s0, c1, s1 = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
        b = len(verts)
        verts += [(r * c0, -.5, r * s0), (r * c1, -.5, r * s1), (r * c1, .5, r * s1), (r * c0, .5, r * s0)]
        norms += [(c0, 0, s0), (c1, 0, s1), (c1, 0, s1), (c0, 0, s0)]
        tris += [(b, b + 1, b + 2), (b, b + 2, b + 3)]
        t = len(verts)
        verts += [(0, .5, 0), (r * c0, .5, r * s0), (r * c1, .5, r * s1)]
        norms += [(0, 1, 0)] * 3
        tris += [(t, t + 1, t + 2)]
        u = len(verts)
        verts += [(0, -.5, 0), (r * c0, -.5, r * s0), (r * c1, -.5, r * s1)]
        norms += [(0, -1, 0)] * 3
        tris += [(u, u + 2, u + 1)]
    return Mesh(vertices=verts, triangles=tris, normals=norms, mode="triangle")

def make_torus(R=0.085, r=0.028, seg=28, sides=12):
    """Donut lying flat (ring in the XZ plane, axis along Y)."""
    verts, norms, tris = [], [], []
    for i in range(seg):
        u = 2 * math.pi * i / seg
        cu, su = math.cos(u), math.sin(u)
        for j in range(sides):
            v = 2 * math.pi * j / sides
            cv, sv = math.cos(v), math.sin(v)
            verts.append(((R + r * cv) * cu, r * sv, (R + r * cv) * su))
            norms.append((cv * cu, sv, cv * su))
    for i in range(seg):
        for j in range(sides):
            a = i * sides + j
            b = ((i + 1) % seg) * sides + j
            c = ((i + 1) % seg) * sides + (j + 1) % sides
            d = i * sides + (j + 1) % sides
            tris += [(a, b, c), (a, c, d)]
    return Mesh(vertices=verts, triangles=tris, normals=norms, mode="triangle")

def make_visor(nu=22, nv=9):
    """Small Mario cap bill: short, rounded, angled down. Head-local coords (face = -z)."""
    base_r, L, y0, th = 0.272, 0.075, 0.128, 0.022
    P = []
    for j in range(nv + 1):
        v = j / nv
        row = []
        for i in range(nu + 1):
            u = -1 + 2 * i / nu
            phi = u * math.radians(42)
            ext = L * v * max(0.06, 1 - u * u) ** 0.5
            r = base_r + ext
            droop = 0.30 * ext + 0.08 * u * u * v
            row.append((r * math.sin(phi), y0 - droop, -r * math.cos(phi)))
        P.append(row)
    verts, tris, norms = [], [], []
    def surf(offset, flip):
        base = len(verts)
        for j in range(nv + 1):
            for i in range(nu + 1):
                p = P[j][i]
                a, b = P[min(j + 1, nv)][i], P[max(j - 1, 0)][i]
                c, d = P[j][min(i + 1, nu)], P[j][max(i - 1, 0)]
                n = _unit(_cross((c[0] - d[0], c[1] - d[1], c[2] - d[2]), (a[0] - b[0], a[1] - b[1], a[2] - b[2])))
                if n[1] < 0:
                    n = tuple(-t for t in n)
                if flip:
                    n = tuple(-t for t in n)
                verts.append((p[0], p[1] + offset, p[2]))
                norms.append(n)
        for j in range(nv):
            for i in range(nu):
                a = base + j * (nu + 1) + i
                tris.extend([(a, a + 1, a + nu + 2), (a, a + nu + 2, a + nu + 1)])
    surf(0.0, False)
    surf(-th, True)
    bot = (nv + 1) * (nu + 1)
    def wall(pairs):
        for t0, t1 in pairs:
            tris.extend([(t0, t1, t1 + bot), (t0, t1 + bot, t0 + bot)])
    wall([(nv * (nu + 1) + i, nv * (nu + 1) + i + 1) for i in range(nu)])
    wall([(j * (nu + 1), (j + 1) * (nu + 1)) for j in range(nv)])
    wall([(j * (nu + 1) + nu, (j + 1) * (nu + 1) + nu) for j in range(nv)])
    return Mesh(vertices=verts, triangles=tris, normals=norms, mode="triangle")

def make_nose(rings=30, seg=26):
    """SOU's nose: a wedge. Tall and wide where it leaves the face, narrowing to a small rounded
    tip; the ridge arches down from between the eyes, the underside stays flat. Head-local coords."""
    z_r, L = -0.17, 0.235
    grid, cys = [], []
    for i in range(rings + 1):
        t = i / rings
        cap = math.sqrt(max(0.0, 1 - t ** 7))
        y_top = 0.03 - 0.115 * t ** 0.75
        y_bot = -0.135
        c = (y_top + y_bot) / 2
        H = (y_top - y_bot) / 2 * cap
        W = (0.105 - 0.055 * t) * cap
        z = z_r - L * t
        row = []
        for j in range(seg):
            ph = 2 * math.pi * j / seg
            q = (1 - math.cos(ph)) / 2
            g = 0.40 + 0.60 * q ** 0.6
            row.append((W * g * math.sin(ph), c + H * math.cos(ph), z))
        grid.append(row)
        cys.append(c)
    verts, norms, tris = [], [], []
    for i in range(rings + 1):
        for j in range(seg):
            p = grid[i][j]
            a, b = grid[min(i + 1, rings)][j], grid[max(i - 1, 0)][j]
            c_, d_ = grid[i][(j + 1) % seg], grid[i][(j - 1) % seg]
            n = _cross((c_[0] - d_[0], c_[1] - d_[1], c_[2] - d_[2]), (a[0] - b[0], a[1] - b[1], a[2] - b[2]))
            out = (p[0], p[1] - cys[i], 0.0)
            if math.sqrt(sum(t * t for t in n)) < 1e-9:
                n = (0.0, 0.0, -1.0)
            elif n[0] * out[0] + n[1] * out[1] < 0:
                n = tuple(-t for t in n)
            verts.append(p)
            norms.append(_unit(n))
    for i in range(rings):
        for j in range(seg):
            a = i * seg + j
            b = i * seg + (j + 1) % seg
            c = (i + 1) * seg + (j + 1) % seg
            d = (i + 1) * seg + j
            tris += [(a, b, c), (a, c, d)]
    return Mesh(vertices=verts, triangles=tris, normals=norms, mode="triangle")

def make_pyramid():
    """Simple low-poly tooth: 4-sided pyramid, base on y = 0, apex at y = 1."""
    base = [(-0.5, 0, -0.5), (0.5, 0, -0.5), (0.5, 0, 0.5), (-0.5, 0, 0.5)]
    apex = (0.0, 1.0, 0.0)
    verts, norms, tris = [], [], []
    for i in range(4):
        p0, p1 = base[i], base[(i + 1) % 4]
        n = _unit(_cross((p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]), (apex[0] - p0[0], apex[1] - p0[1], apex[2] - p0[2])))
        mid = ((p0[0] + p1[0] + apex[0]) / 3, (p0[1] + p1[1] + apex[1]) / 3 - 0.3, (p0[2] + p1[2] + apex[2]) / 3)
        if n[0] * mid[0] + n[1] * mid[1] + n[2] * mid[2] < 0:
            n = tuple(-t for t in n)
        b = len(verts)
        verts += [p0, p1, apex]
        norms += [n] * 3
        tris.append((b, b + 1, b + 2))
    b = len(verts)
    verts += base
    norms += [(0, -1, 0)] * 4
    tris += [(b, b + 1, b + 2), (b, b + 2, b + 3)]
    return Mesh(vertices=verts, triangles=tris, normals=norms, mode="triangle")

def make_shoe(nu=26, nv=22):
    """Real shoe: elongated dome (rounded toe box + heel), flat sole, lower toward the toe.
    Toe = -z, ankle at z = 0. Analytic normals, so no dark patches at the ends."""
    W, L, H, zc = 0.29, 0.42, 0.19, -0.11
    verts, norms, tris = [], [], []
    for i in range(nu + 1):
        th = (math.pi / 2) * i / nu
        for j in range(nv):
            ph = 2 * math.pi * j / nv
            ux, uy, uz = math.sin(th) * math.cos(ph), math.cos(th), math.sin(th) * math.sin(ph)
            t = (1 - uz) / 2                      # 0 at the heel, 1 at the toe
            hgt = H * (1.0 - 0.28 * t)
            verts.append((W / 2 * ux, hgt * uy, zc + (L / 2) * uz))
            norms.append(_unit((ux / (W / 2), uy / hgt, uz / (L / 2))))
    for i in range(nu):
        for j in range(nv):
            a = i * nv + j
            b = i * nv + (j + 1) % nv
            c = (i + 1) * nv + (j + 1) % nv
            d = (i + 1) * nv + j
            tris += [(a, b, c), (a, c, d)]
    base = len(verts)
    verts.append((0.0, 0.0, zc))
    norms.append((0, -1, 0))
    rim = nu * nv
    for j in range(nv):
        verts.append(verts[rim + j])
        norms.append((0, -1, 0))
    for j in range(nv):
        tris.append((base, base + 1 + j, base + 1 + (j + 1) % nv))
    return Mesh(vertices=verts, triangles=tris, normals=norms, mode="triangle")

# ---------------------------------------------------------------------
# HEAD SHAPE: a loft of superellipse cross-sections with an explicit silhouette:
# wide cheeks, squared jaw tapering to a broad chin, a long lower face, and a
# jawline that climbs from the chin back up toward the ear. All face features
# are seated on this exact surface via face_z().
# ---------------------------------------------------------------------
HEAD_R = 0.25
# rows (top to bottom): y, half-width a, front depth bf, back depth bb, superellipse exponent n
_HP = [
    (0.250, 0.000, 0.000, 0.000, 2.0),
    (0.215, 0.130, 0.130, 0.130, 2.0),
    (0.150, 0.200, 0.200, 0.200, 2.0),
    (0.080, 0.238, 0.238, 0.238, 2.0),
    (0.000, 0.250, 0.250, 0.250, 2.1),
    (-0.080, 0.252, 0.238, 0.234, 2.3),
    (-0.150, 0.246, 0.232, 0.218, 2.6),
    (-0.200, 0.234, 0.226, 0.200, 3.0),
    (-0.240, 0.160, 0.208, 0.165, 3.0),
    (-0.285, 0.095, 0.176, 0.115, 2.8),
    (-0.320, 0.052, 0.120, 0.060, 2.5),
    (-0.338, 0.000, 0.000, 0.000, 2.2),
]
_HY = [r[0] for r in _HP]

def _tang(i, k):
    if i == 0:
        return (_HP[0][k + 1] - _HP[1][k + 1]) / (_HY[0] - _HY[1])
    if i == len(_HP) - 1:
        return (_HP[-2][k + 1] - _HP[-1][k + 1]) / (_HY[-2] - _HY[-1])
    return (_HP[i - 1][k + 1] - _HP[i + 1][k + 1]) / (_HY[i - 1] - _HY[i + 1])

def _prof(y):
    y = max(_HY[-1], min(_HY[0], y))
    i = 0
    while i < len(_HY) - 2 and y < _HY[i + 1]:
        i += 1
    h = _HY[i] - _HY[i + 1]
    t = (_HY[i] - y) / h
    out = []
    for k in range(4):
        p0, p1 = _HP[i][k + 1], _HP[i + 1][k + 1]
        m0, m1 = _tang(i, k) * (-h), _tang(i + 1, k) * (-h)
        t2, t3 = t * t, t * t * t
        out.append((2 * t3 - 3 * t2 + 1) * p0 + (t3 - 2 * t2 + t) * m0 + (-2 * t3 + 3 * t2) * p1 + (t3 - t2) * m1)
    out[0] = max(out[0], 0.0)
    out[1] = max(out[1], 0.0)
    out[2] = max(out[2], 0.0)
    out[3] = max(out[3], 2.0)
    return out

def _crescent(x, y):
    """Forehead-to-nose crescent: brow ridge bulges forward, nose bridge dips back."""
    return (-0.013 * math.exp(-((y - 0.078) / 0.028) ** 2) * math.exp(-(x / 0.16) ** 2)
            + 0.010 * math.exp(-((y + 0.02) / 0.035) ** 2) * math.exp(-(x / 0.075) ** 2))

def face_z(x, y):
    """z of the head's front surface at (x, y)."""
    a, bf, bb, n = _prof(y)
    if a < 1e-6:
        return 0.0
    u = min(1.0, abs(x) / a)
    zr = (1 - u ** n) ** (1.0 / n)
    return -bf * zr + _crescent(x, y) * _smooth(0.0, 0.5, zr)

def on_head(x, y, sink=0.0, side=-1):
    """Point on the head surface. sink > 0 buries it, sink < 0 lifts it out."""
    if side < 0:
        return Vec3(x, y, face_z(x, y) + sink)
    a, bf, bb, n = _prof(y)
    u = min(1.0, abs(x) / max(a, 1e-6))
    return Vec3(x, y, bb * (1 - u ** n) ** (1.0 / n) - sink)

def head_radius(phi_deg, y):
    """Distance from the head axis to the surface along azimuth phi (0 = ahead, 90 = side, 180 = back)."""
    a, bf, bb, n = _prof(y)
    if a < 1e-6:
        return 0.0
    ph = math.radians(phi_deg)
    sx, cz = abs(math.sin(ph)), math.cos(ph)
    b = bf if cz > 0 else bb
    return ((sx / a) ** n + (abs(cz) / b) ** n) ** (-1.0 / n)

def on_head_ang(phi_deg, y, sink=0.0):
    r = head_radius(phi_deg, y) - sink
    ph = math.radians(phi_deg)
    return Vec3(r * math.sin(ph), y, -r * math.cos(ph))

def make_head(ny=84, na=96):
    rows = []
    for j in range(ny + 1):
        y = 0.25 - 0.588 * (j / ny)
        a, bf, bb, n = _prof(y)
        row = []
        for i in range(na):
            al = 2 * math.pi * i / na
            c, sn = math.cos(al), math.sin(al)
            x = a * math.copysign(abs(c) ** (2 / n), c)
            zr = math.copysign(abs(sn) ** (2 / n), sn)
            if zr < 0:
                z = bf * zr + _crescent(x, y) * _smooth(0.0, 0.5, -zr)
            else:
                z = bb * zr
            row.append((x, y, z))
        rows.append(row)
    verts, norms, tris = [], [], []
    for j in range(ny + 1):
        for i in range(na):
            p = rows[j][i]
            a_, b_ = rows[min(j + 1, ny)][i], rows[max(j - 1, 0)][i]
            c_, d_ = rows[j][(i + 1) % na], rows[j][(i - 1) % na]
            n = _cross((c_[0] - d_[0], c_[1] - d_[1], c_[2] - d_[2]), (a_[0] - b_[0], a_[1] - b_[1], a_[2] - b_[2]))
            if math.sqrt(sum(t * t for t in n)) < 1e-10:
                n = (p[0], p[1], p[2])
            if n[0] * p[0] + n[1] * p[1] + n[2] * p[2] < 0:
                n = tuple(-t for t in n)
            verts.append(p)
            norms.append(_unit(n))
    for j in range(ny):
        for i in range(na):
            a = j * na + i
            b = j * na + (i + 1) % na
            c = (j + 1) * na + (i + 1) % na
            e = (j + 1) * na + i
            tris += [(a, b, c), (a, c, e)]
    return Mesh(vertices=verts, triangles=tris, normals=norms, mode="triangle")

def make_hair(nu=46, nv=16):
    """Back-of-head hair: wraps behind the ears, front edge slants back toward the nape (a swoop),
    flares out wide at the back, feathers into the skull at its edges. Hugs the real jaw."""
    rows = []
    for j in range(nv + 1):
        v = j / nv
        ph0 = 80 + 36 * v ** 1.4
        row = []
        for i in range(nu + 1):
            deg = ph0 + (360 - 2 * ph0) * i / nu
            ph = math.radians(deg)
            back = max(0.0, -math.cos(ph))
            y_bot = -0.05 - 0.23 * back ** 0.7
            y = 0.10 + (y_bot - 0.10) * v
            edge = max(0.0, min(1.0, (deg - ph0) / 22.0, (360 - ph0 - deg) / 22.0, (1 - v) / 0.16))
            edge = edge * edge * (3 - 2 * edge)
            r = head_radius(deg, y) + 0.004 + (0.010 + 0.052 * back ** 1.2 * (1 - 0.45 * v)) * edge
            row.append((r * math.sin(ph), y, -r * math.cos(ph)))
        rows.append(row)
    verts, norms, tris = [], [], []
    for j in range(nv + 1):
        for i in range(nu + 1):
            p = rows[j][i]
            verts.append(p)
            norms.append(_unit((p[0], p[1] * 0.35, p[2])))
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            tris.extend([(a, a + 1, a + nu + 2), (a, a + nu + 2, a + nu + 1)])
    return Mesh(vertices=verts, triangles=tris, normals=norms, mode="triangle")

# ---------------------------------------------------------------------
# Palette (0-255 via rgb32; plain color.rgb wants 0-1 floats)
# ---------------------------------------------------------------------
SKIN      = color.rgb32(232, 197, 68)
GLOVE     = SKIN                         # gloves, cuff ring and face share one yellow
CAP_RED   = color.rgb32(205, 30, 22)
SHIRT_RED = color.rgb32(222, 34, 22)
OVERALLS  = color.rgb32(238, 120, 12)
BOOT      = color.rgb32(200, 28, 20)
EYE_RIM   = color.rgb32(170, 20, 16)
BLACK     = color.rgb32(6, 6, 6)
TOOTH     = color.rgb32(232, 224, 200)
DARK      = color.rgb32(30, 30, 30)
GLITCH_PALETTE = [color.rgb32(255, 0, 40), color.rgb32(0, 255, 120),
                  color.rgb32(255, 255, 0), color.rgb32(120, 0, 255)]

SHADERS = {"shadows": lit_with_shadows_shader, "basic": basic_lighting_shader, "flat": unlit_shader}
LIGHT_ORDER = ["basic", "shadows", "flat"]
BASE_Y = 0.4
state = {"pose": "idle", "t": 0.0, "pose_t0": 0.0, "auto_spin": True, "corrupted": False,
         "light": "basic", "aspect": 0, "flip": False, "gl_next": 0.0, "gl_left": 0}

CYL = "cyl"   # sentinel: part() builds a fresh cylinder mesh each time
PARTS = []
def part(model, col, scale, position, parent, rotation=(0, 0, 0), ds=False):
    is_cyl = model is CYL
    e = Entity(model=make_cylinder() if is_cyl else model, color=col, scale=scale, position=position,
               rotation=rotation, parent=parent, shader=SHADERS[state["light"]])
    if is_cyl or ds:
        e.double_sided = True
    e._orig = col
    PARTS.append(e)
    return e

def rot_from_inward(f):
    """Euler (pitch, yaw, roll) that points an entity's +z axis along vector f."""
    fx, fy, fz = f
    L = math.sqrt(fx * fx + fy * fy + fz * fz) or 1.0
    fx, fy, fz = fx / L, fy / L, fz / L
    return (math.degrees(-math.asin(max(-1, min(1, fy)))), math.degrees(math.atan2(fx, fz)), 0)

def head_rot(x, y):
    """Orientation that lays a flat part on the head surface at (x, y)."""
    e = 0.004
    fx = (face_z(x + e, y) - face_z(x - e, y)) / (2 * e)
    fy = (face_z(x, y + e) - face_z(x, y - e)) / (2 * e)
    return rot_from_inward((-fx, -fy, 1.0))

def dense(pts, k=0.55):
    out = [pts[0]]
    for (x0, y0, r0), (x1, y1, r1) in zip(pts, pts[1:]):
        n = max(1, math.ceil(math.hypot(x1 - x0, y1 - y0) / (k * (r0 + r1) / 2)))
        for i in range(1, n + 1):
            t = i / n
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, r0 + (r1 - r0) * t))
    return out

figure = Entity(y=BASE_Y)       # origin = centre of the torso

# ---------------------------------------------------------------------
# HEAD. Face is at -z (camera looks toward +z). Head sits low so there is
# almost no neck.
# ---------------------------------------------------------------------
head_grp = Entity(parent=figure, position=(0, 0.55, 0), scale=0.80)
part(make_head(), SKIN, 1, Vec3(0, 0, 0), head_grp, ds=True)                    # skull + cheeks + jaw + chin

# ears: big smooth convex ovals at eye level, tilted out at the top, NO lobe
for s in (-1, 1):
    ear = Entity(parent=head_grp, position=(s * 0.262, 0.005, 0.030), rotation=(0, -s * 18, s * 10))
    part("sphere", SKIN, (0.080, 0.215, 0.135), Vec3(0, 0, 0), ear)

# cap: big rounded crown that bulges out behind, SMALL curved bill
part("sphere", CAP_RED, (0.56, 0.44, 0.64), Vec3(0, 0.200, 0.04), head_grp)
part(make_visor(), CAP_RED, 1, Vec3(0, 0, 0), head_grp, ds=True)

# hair: wide mass across the back (front edge slants back = swoop) + a curly swoop at each temple
part(make_hair(), BLACK, 1, Vec3(0, 0, 0), head_grp, ds=True)
SWOOP_PHI0 = 74.0       # azimuth where the temple swoop starts (set back from v6)
SWOOP = [(0.0, 0.088, 0.026), (3.5, 0.066, 0.026), (6.0, 0.044, 0.024), (7.2, 0.022, 0.022),
         (6.8, 0.000, 0.019), (4.2, -0.020, 0.016), (-0.5, -0.036, 0.0125), (-6.5, -0.046, 0.009)]
for s in (-1, 1):
    pts = [(on_head_ang(SWOOP_PHI0 + dph, y, sink=0.004), r) for dph, y, r in SWOOP]
    dpts = []
    for (p0, r0), (p1, r1) in zip(pts, pts[1:]):
        n = max(1, math.ceil((p1 - p0).length() / (0.55 * (r0 + r1) / 2)))
        for i in range(0 if not dpts else 1, n + 1):
            t = i / n
            dpts.append((p0 + (p1 - p0) * t, r0 + (r1 - r0) * t))
    for p, r in dpts:
        part("sphere", BLACK, r * 2.3, Vec3(s * p.x, p.y, p.z), head_grp)

# eyes: sunk-in flat discs (lid lumps removed)
EYE_T = 0.014
pupils = {}
eye_jitter = {-1: (0.0, 0.004), 1: (-0.004, -0.006)}
for s in (-1, 1):
    ex, ey = s * 0.102 + eye_jitter[s][0], 0.025 + eye_jitter[s][1]
    rot = head_rot(ex, ey)
    part("sphere", EYE_RIM, (0.135, 0.135, EYE_T), on_head(ex, ey, sink=0.0), head_grp, rotation=rot)
    pupils[s] = part("sphere", BLACK, (0.084, 0.105, EYE_T), on_head(ex, ey, sink=-0.006), head_grp, rotation=rot)

# SOU's nose
part(make_nose(), SKIN, 1, Vec3(0, 0, 0), head_grp, ds=True)
NOSTRIL = color.rgb32(120, 88, 20)
for s in (-1, 1):
    part("sphere", NOSTRIL, (0.026, 0.012, 0.045), Vec3(s * 0.024, -0.133, -0.358), head_grp)

# mustache: small spheres sweeping out from under the nose, curling up at the tips
def mustache_path():
    pts = []
    for k in range(9):
        t = k / 8
        pts.append((0.012 + 0.128 * t, -0.192 - 0.010 * math.sin(math.pi * t), 0.034 - 0.011 * t))
    cx, cy = 0.140, -0.192 + 0.032
    for k in range(1, 10):
        ang = math.radians(-90 + 40 * k)
        rad = 0.032 * (1 - 0.07 * k)
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang), 0.022 - 0.0014 * k))
    return pts
for s in (-1, 1):
    for x, y, r in dense(mustache_path()):
        part("sphere", BLACK, r * 2, on_head(s * x, y, sink=0.0), head_grp)
part("sphere", BLACK, (0.17, 0.07, 0.085), Vec3(0, -0.198, on_head(0, -0.198).z - 0.02), head_grp)

# mouth: dark cavity, upper teeth (same shape, now RED), lower teeth = simple red pyramids
TOOTH_RED = color.rgb32(196, 26, 26)
mouth_cavity = part("sphere", BLACK, (0.15, 0.06, 0.05), on_head(0, -0.262, sink=0.0), head_grp, rotation=head_rot(0, -0.262))
teeth = []
for tx in (-0.0775, -0.0465, -0.0155, 0.0155, 0.0465, 0.0775):
    teeth.append(part("cube", TOOTH_RED, (0.022, 0.034, 0.014), on_head(tx, -0.243, sink=-0.026), head_grp, rotation=head_rot(tx, -0.243)))
for tx in (-0.052, -0.026, 0.0, 0.026, 0.052):
    teeth.append(part(make_pyramid(), TOOTH_RED, (0.024, 0.032, 0.020), on_head(tx, -0.286, sink=-0.014), head_grp,
                      rotation=head_rot(tx, -0.286), ds=True))

# ---------------------------------------------------------------------
# TORSO: one squash/potato mass. Red shirt underneath, orange overalls on
# top with a real U-shaped bib edge and straps (high-res so edges are smooth).
# ---------------------------------------------------------------------
TX, TY, TZ = 0.33, 0.31, 0.28
Y_UC, UD, XU = -0.10, 0.07, 0.17

def torso_pt(th, ph):
    c, s = math.cos(th), math.sin(th)
    bulge = 1.0 - 0.10 * c
    rx, rz = TX * bulge, TZ * bulge * (1 + 0.10 * math.cos(ph))
    x, y, z = rx * s * math.sin(ph), TY * c, -rz * s * math.cos(ph)
    return (x, y, z), _unit((x / rx ** 2, y / TY ** 2, z / rz ** 2))

def make_torso(select=None, lift=0.0, na=84, nt=62):
    pts = [[torso_pt(math.pi * j / nt, 2 * math.pi * i / na) for i in range(na + 1)] for j in range(nt + 1)]
    verts, norms, tris = [], [], []
    for j in range(nt):
        for i in range(na):
            quad = [pts[j][i], pts[j][i + 1], pts[j + 1][i + 1], pts[j + 1][i]]
            if select:
                cx = sum(q[0][0] for q in quad) / 4
                cy = sum(q[0][1] for q in quad) / 4
                cz = sum(q[0][2] for q in quad) / 4
                if not select(cx, cy, cz):
                    continue
            b = len(verts)
            for p, n in quad:
                verts.append((p[0] + n[0] * lift, p[1] + n[1] * lift, p[2] + n[2] * lift))
                norms.append(n)
            tris.extend([(b, b + 1, b + 2), (b, b + 2, b + 3)])
    return Mesh(vertices=verts, triangles=tris, normals=norms, mode="triangle")

def is_overalls(x, y, z):
    ax = abs(x)
    bump = max(0.0, 1 - (ax / XU) ** 2)
    thr = (Y_UC - UD * bump) if z < 0 else (Y_UC + 0.10 * bump)
    if y < thr:
        return True
    xs = 0.165 - 0.05 * ((y - Y_UC) / (0.31 - Y_UC))
    return abs(ax - xs) < 0.034

part(make_torso(), SHIRT_RED, 1, Vec3(0, 0, 0), figure, ds=True)                                 # shirt
part("sphere", SHIRT_RED, (0.27, 0.09, 0.23), Vec3(0, 0.275, 0.01), figure)                         # shirt collar: no neck
part(make_torso(is_overalls, lift=0.005, na=240, nt=180), OVERALLS, 1, Vec3(0, 0, 0), figure, ds=True)
for s in (-1, 1):                                                                                # buttons, lower tummy
    bx, by = s * XU, Y_UC
    c = by / TY
    bulge = 1.0 - 0.10 * c
    bz = -TZ * bulge * 1.085 * math.sqrt(max(1 - (bx / (TX * bulge)) ** 2 - c * c, 0.02))
    part("sphere", SKIN, 0.062, Vec3(bx, by, bz - 0.012), figure)

# ---------------------------------------------------------------------
# HANDS: jointed, spring-driven. s = +1 is HIS LEFT (viewer's right).
# Built palm-forward with the thumb on the LATERAL side (a correct pair);
# the wrist twist then turns the palm (default: toward the thigh, thumb forward).
# ---------------------------------------------------------------------
JOINTS = []
def mk_joint(parent, pos, rot=(0, 0, 0), base=False):
    j = Entity(parent=parent, position=pos, rotation=rot)
    j._ang = j._vel = j._tgt = 0.0
    j._amp, j._w, j._ph = 0.0, 2.0, 0.0
    j._k, j._c = 130.0, 8.5
    j._fan = j._fan_t = float(rot[2])
    j._base = base
    j._fx = 0.0
    JOINTS.append(j)
    return j

def build_chain(parent, pos, lengths, widths, lscale=1.0, rot=(0, 0, 0)):
    joints, p = [], parent
    for idx, (L, Wd) in enumerate(zip(lengths, widths)):
        L *= lscale
        if idx == 0:
            j = mk_joint(p, pos, rot, base=True)
        else:
            j = mk_joint(p, (0, -lengths[idx - 1] * lscale, 0))
        part("sphere", GLOVE, (Wd * 1.08, L * 1.5, Wd * 1.08), Vec3(0, -L / 2, 0), j)
        joints.append(j)
        p = j
    return joints

SEG_L, SEG_W = (0.080, 0.060, 0.048), (0.038, 0.032, 0.027)
FINGERS = [(-0.052, 1.00), (-0.018, 1.12), (0.018, 1.06), (0.052, 0.88)]
VAR = (1.0, 1.12, 1.05, 0.86)

HAND_MODES = {
    "rest":   dict(c=(14, 24, 18), th=(6, 14, 10), fanK=160, wr=10, amp=7),
    "limp":   dict(c=(26, 36, 30), th=(10, 20, 16), fanK=120, wr=18, amp=3),
    "spread": dict(c=(-8, -4, 0), th=(-8, -6, -4), fanK=-380, wr=-5, amp=5),
    "claw":   dict(c=(52, 68, 48), th=(30, 38, 28), fanK=-140, wr=24, amp=8),
    "grab":   dict(c=(8, 12, 8), th=(-4, -6, -4), fanK=-420, wr=30, amp=0, stiff=True),   # Hunt: rigid, spread
    "fist":   dict(c=(78, 92, 60), th=(48, 52, 34), fanK=60, wr=8, amp=2),
    "point":  dict(c=(84, 95, 62), idx=(0, 2, 0), th=(46, 50, 30), fanK=100, wr=0, amp=3),
}

shoulders, elbows, wrists, fingers, thumbs = {}, {}, {}, {}, {}
for s in (-1, 1):
    sh = Entity(parent=figure, position=(s * 0.265, 0.19, 0), rotation=(0, 0, -s * 12))
    shoulders[s] = sh
    part("sphere", SHIRT_RED, 0.172, Vec3(0, 0, 0), sh)                       # shoulder = same width as the arm
    part(CYL, SHIRT_RED, (0.17, 0.26, 0.17), Vec3(0, -0.13, 0), sh)
    el = Entity(parent=sh, position=(0, -0.26, 0), rotation=(8, 0, 0))
    elbows[s] = el
    part("sphere", SHIRT_RED, 0.17, Vec3(0, 0, 0), el)
    part(CYL, SHIRT_RED, (0.15, 0.22, 0.15), Vec3(0, -0.11, 0), el)
    wr = mk_joint(el, (0, -0.22, 0))
    wr._tw = wr._twc = s * 90.0                                               # palm toward the thigh
    wr._zang = wr._zvel = wr._ztgt = 0.0
    wr._kz, wr._cz = 130.0, 8.5
    wrists[s] = wr
    part(CYL, GLOVE, (0.142, 0.060, 0.142), Vec3(0, -0.020, 0), wr)
    part(make_torus(0.076, 0.016), GLOVE, 1, Vec3(0, 0.008, 0), wr, ds=True)  # ONE thin donut cuff
    part("sphere", GLOVE, (0.158, 0.175, 0.090), Vec3(0, -0.120, 0), wr)
    fingers[s] = []
    for k, (fx, ls) in enumerate(FINGERS):
        ch = build_chain(wr, (fx, -0.190, -0.012), SEG_L, SEG_W, ls)
        ch[0]._fx = fx
        fingers[s].append(ch)
    # thumb on the LATERAL side, angled away from the fingers, root a little lower on the palm
    thumbs[s] = build_chain(wr, (s * 0.078, -0.150, -0.022), (0.064, 0.052, 0.042), (0.044, 0.037, 0.031),
                            1.0, rot=(0, 0, -s * 38))

def set_hand(s, name, twist=None, snap=False, wz=0.0, rag=False):
    m = HAND_MODES[name]
    k_, c_ = (520.0, 46.0) if m.get("stiff") else (130.0, 8.5)
    index_k = 0 if s == -1 else 3
    for k, chain in enumerate(fingers[s]):
        cs = m["idx"] if ("idx" in m and k == index_k) else tuple(c * VAR[k] for c in m["c"])
        for n, j in enumerate(chain):
            j._tgt = cs[n]
            j._amp = m["amp"] * (0.6 if n == 0 else 1.0)
            j._w = 2.0 + 0.45 * k + 0.3 * n
            j._ph = k * 0.9 + n * 0.8 + (1.3 if s > 0 else 0.0)
            j._k, j._c = k_, c_
            if snap:
                j._ang = j._tgt
        chain[0]._fan_t = chain[0]._fx * m["fanK"]
    for n, j in enumerate(thumbs[s]):
        j._tgt = m["th"][n]
        j._amp = m["amp"] * 0.8
        j._w = 1.7 + 0.3 * n
        j._ph = 2.4 + n * 0.8 + (1.3 if s > 0 else 0.0)
        j._k, j._c = k_, c_
        if snap:
            j._ang = j._tgt
    wr = wrists[s]
    wr._tgt, wr._amp, wr._w, wr._ph = m["wr"], (0.0 if m.get("stiff") else 2.0), 1.4, 0.7 * s
    wr._k, wr._c = k_, c_
    wr._ztgt = wz
    wr._kz, wr._cz = (22.0, 1.8) if rag else (130.0, 8.5)
    if twist is not None:
        wr._tw = twist
        if snap:
            wr._twc = twist
    if snap:
        wr._ang = wr._tgt

def step_joints(dt, t):
    dt = min(dt, 1 / 30)
    for j in JOINTS:
        tgt = j._tgt + j._amp * math.sin(t * j._w + j._ph)
        j._vel += (j._k * (tgt - j._ang) - j._c * j._vel) * dt
        j._ang += j._vel * dt
        j.rotation_x = j._ang
        if j._base:
            j._fan += (j._fan_t - j._fan) * min(1.0, dt * 10)
            j.rotation_z = j._fan
    for s in (-1, 1):
        wr = wrists[s]
        tw = wr._tw + (180.0 if state["flip"] else 0.0)
        wr._twc += (tw - wr._twc) * min(1.0, dt * 9)
        wr.rotation_y = wr._twc
        tz = wr._ztgt + (4.0 if wr._kz < 100 else 0.0) * math.sin(t * 1.7 + s)
        wr._zvel += (wr._kz * (tz - wr._zang) - wr._cz * wr._zvel) * dt
        wr._zang += wr._zvel * dt
        wr.rotation_z = wr._zang

# ---------------------------------------------------------------------
# LEGS: tubular thigh and shin, knobby knee ball, real shoe.
# ---------------------------------------------------------------------
hips, knees = {}, {}
for s in (-1, 1):
    hp = Entity(parent=figure, position=(s * 0.17, -0.27, 0))
    hips[s] = hp
    part("sphere", OVERALLS, 0.20, Vec3(0, 0, 0), hp)
    part(CYL, OVERALLS, (0.18, 0.40, 0.18), Vec3(0, -0.20, 0), hp)
    kn = Entity(parent=hp, position=(0, -0.40, 0))
    knees[s] = kn
    part("sphere", OVERALLS, 0.215, Vec3(0, 0, -0.012), kn)
    part(CYL, OVERALLS, (0.16, 0.42, 0.16), Vec3(0, -0.22, 0), kn)
    part(make_shoe(), BOOT, 1, Vec3(0, -0.45, 0), kn, ds=True)

for s in (-1, 1):
    set_hand(s, "rest", twist=s * 90.0, snap=True)

# ---------------------------------------------------------------------
# Camera (auto-fit) + lights
# ---------------------------------------------------------------------
CAM_Y = 0.285
def fit_camera():
    asp = getattr(window, "aspect_ratio", 4 / 3)
    hfov = math.radians(camera.fov)
    vfov = 2 * math.atan(math.tan(hfov / 2) / asp)
    d = max((2.55 / 2) / math.tan(vfov / 2), (1.8 / 2) / math.tan(hfov / 2))
    camera.position = (0, CAM_Y, -d)
    camera.rotation = (0, 0, 0)
    state["aspect"] = asp
fit_camera()

sun = DirectionalLight(shadows=True, shadow_map_resolution=Vec2(2048, 2048))
sun.look_at(Vec3(-0.5, -0.9, 1))
ambient = AmbientLight(color=color.rgba(0.62, 0.58, 0.62, 1))
sun.update_bounds(figure)

pose_label = Text(text="MODE: idle", position=window.top_left + Vec2(0.02, -0.03), scale=1.0, color=color.white)
Text(text="[1] Look behind [2] Active [3] Deactive [4] Hunt [5] Wave [6] Hips [7] Point [8] Glance [9] Glare [0] Doubt [T] Cross   [H] flip hands [G] glitch [L] light [Q/E] rotate [Esc] quit",
     position=window.bottom_left + Vec2(0.02, 0.02), scale=0.6, color=color.white)

def set_lighting(mode):
    state["light"] = mode
    for e in PARTS:
        e.shader = SHADERS[mode]
    print("lighting:", mode, flush=True)

# ---------------------------------------------------------------------
# Poses. Order is fixed: 1-7 as before, 8-9 appended.
# Conventions (verified against renders): shoulder/hip rx > 0 swings the
# limb FORWARD; knee rx < 0 bends the shin back; head rx > 0 looks UP;
# head ry < 0 turns the face toward his left (+x). sh/el = (pitch,
# outward-roll) per side; roll is applied as -side*value. twist = palm turn
# about the arm (default s*90 = palm toward the thigh, thumb forward).
# ---------------------------------------------------------------------
def both(v):
    return {-1: v, 1: v}

REST = dict(yaw=0, pitch=0, y=BASE_Y, sc=1.0, head=(0, 0, 0),
            sh=both((0, 12)), el=both((8, 0)), hip=both(0), knee=both(0),
            fing=both("rest"), twist={-1: -90.0, 1: 90.0}, wz=both(0.0), rag=False, snap=False,
            mouth=1.0, eye=0.105, eyew=0.8, eyec=BLACK)

HEAD_HUNT = (14, 0, 6)
POSES = {
    "look_behind": dict(yaw=180, sh=both((8, 14)), el=both((26, 0)), fing=both("claw")),
    "face_active": dict(),
    "face_deactive": dict(y=BASE_Y - 0.05, head=(-10, 0, 5), sh=both((-6, 12)), el=both((4, 0)),
                          fing=both("limp"), mouth=0.15, eye=0.07, eyec=DARK),
    # floating zombie reach: hands raised, rigid wrists, spread fingers, palms down;
    # eyes blotted black with a thin red band; Springtrap twitch frames in update()
    "hunt": dict(pitch=-16, y=BASE_Y + 0.20, sc=1.04, head=HEAD_HUNT,
                 sh=both((84, 10)), el=both((10, -24)), hip=both(44), knee=both(-72),
                 fing=both("grab"), twist=both(180.0), mouth=1.4, eye=0.108, eyew=1.0),
    "wave": dict(head=(18, -32, 6), sh={-1: (0, 12), 1: (0, 50)}, el={-1: (8, 0), 1: (0, 106)},
                 fing={-1: "rest", 1: "spread"}, twist={-1: -90.0, 1: 0.0}),
    # confident stance from the pipe reference: fists on the hips, elbows out, wrists bent outward
    "hips": dict(pitch=2, head=(6, 0, 0), sh=both((4, 58)), el=both((0, -98)),
                 fing=both("fist"), wz={-1: 28.0, 1: -28.0}, mouth=1.0),
    # points with the INDEX finger, palm facing down
    "point": dict(head=(-8, 0, 8), sh={-1: (82, 0), 1: (0, 12)}, el={-1: (6, 0), 1: (8, 0)},
                  fing={-1: "point", 1: "rest"}, twist={-1: 180.0, 1: 90.0}),
    "glance": dict(yaw=158, y=BASE_Y - 0.02, head=(-4, -72, 4),
                   sh={-1: (28, 12), 1: (-30, 12)}, el={-1: (22, 0), 1: (14, 0)},
                   hip={-1: -20, 1: 26}, knee={-1: -42, 1: 0}),
    # hands on hips, skeptical head tilt (from the hands-on-hips reference shots)
    "doubt": dict(pitch=3, head=(4, -12, 11), sh=both((6, 64)), el=both((0, -100)),
                  fing=both("fist"), mouth=0.30, eye=0.105),
    # the cross: snaps into a T in ONE frame, hands drop like rags (loose wrist spring), Springtrap twitches
    "cross": dict(snap=True, head=(-12, 0, 0), sh=both((0, 90)), el=both((0, 0)), fing=both("limp"),
                  twist=both(0.0), wz={-1: -85.0, 1: 85.0}, rag=True, mouth=0.15),
    "glare": dict(pitch=-10, y=BASE_Y - 0.04, sc=1.03, head=(-4, 0, 0),
                  sh=both((12, 10)), el=both((28, 0)), fing=both("fist"), mouth=0.15, eye=0.12),
}
KEYS = {"1": "look_behind", "2": "face_active", "3": "face_deactive", "4": "hunt",
        "5": "wave", "6": "hips", "7": "point", "8": "glance", "9": "glare", "0": "doubt"}

def _face(open_amount, eye_h, eye_w, eye_color):
    mouth_cavity.animate_scale_y(0.06 * open_amount, duration=0.25)
    for t in teeth:
        t.enabled = open_amount > 0.3
    for s in (-1, 1):
        pupils[s].animate_scale(Vec3(eye_h * eye_w, eye_h, EYE_T), duration=0.25)
        pupils[s].animate_color(eye_color, duration=0.25)

def apply_pose(name):
    P = dict(REST)
    P.update(POSES[name])
    state["pose"] = name
    state["pose_t0"] = state["t"]
    state["auto_spin"] = False
    state["gl_left"] = 0
    state["gl_next"] = state["t"] + 1.2
    figure.rotation_z = 0
    figure.x = 0
    pose_label.text = f"MODE: {name}"
    d = 0.016 if P.get("snap") else 0.35
    figure.animate_rotation_y(P["yaw"], duration=d)
    figure.animate_rotation_x(P["pitch"], duration=d)
    figure.animate_y(P["y"], duration=d)
    figure.animate_scale(P["sc"], duration=d)
    hx, hy, hz = P["head"]
    head_grp.animate_rotation_x(hx, duration=d)
    head_grp.animate_rotation_y(hy, duration=d)
    head_grp.animate_rotation_z(hz, duration=d)
    for s in (-1, 1):
        rx, rz = P["sh"][s]
        shoulders[s].animate_rotation_x(rx, duration=d)
        shoulders[s].animate_rotation_z(-s * rz, duration=d)
        rx, rz = P["el"][s]
        elbows[s].animate_rotation_x(rx, duration=d)
        elbows[s].animate_rotation_z(-s * rz, duration=d)
        hips[s].animate_rotation_x(P["hip"][s], duration=d)
        knees[s].animate_rotation_x(P["knee"][s], duration=d)
        set_hand(s, P["fing"][s], twist=P["twist"][s], wz=P["wz"][s], rag=P["rag"])
    _face(P["mouth"], P["eye"], P["eyew"], P["eyec"])

def _glitch_off():
    for e in PARTS:
        e.color = e._orig
    figure.x = 0
    if state["pose"] != "idle":
        apply_pose(state["pose"])

def input(key):
    if key in KEYS:
        apply_pose(KEYS[key])
    if key == "t":
        apply_pose("cross")
    if key == "h":
        state["flip"] = not state["flip"]
    if key == "g":
        state["corrupted"] = not state["corrupted"]
        if not state["corrupted"]:
            _glitch_off()
    if key == "l":
        set_lighting(LIGHT_ORDER[(LIGHT_ORDER.index(state["light"]) + 1) % len(LIGHT_ORDER)])
    if key in ("q", "e"):
        state["auto_spin"] = False
        figure.rotation_y += -15 if key == "q" else 15

def _hunt_motion(age, t):
    """Slow circling arms + float bob, plus Springtrap twitch frames: ONE erratic frame,
    then straight back to the same head posture."""
    twitch = state["gl_left"] > 0
    for s in (-1, 1):
        ph = 0.0 if s == 1 else math.pi
        w = age * 1.9 + ph
        rx = 84 + 12 * math.sin(w)
        rz = 10 + 10 * math.cos(w)
        if twitch:
            rx += random.uniform(-38, 38)
            rz += random.uniform(-22, 22)
        shoulders[s].rotation_x = rx
        shoulders[s].rotation_z = -s * rz
        knees[s].rotation_x = -72 + 8 * math.sin(age * 1.3 + ph)
    figure.y = BASE_Y + 0.20 + 0.035 * math.sin(age * 1.4)
    if twitch:
        state["gl_left"] -= 1
        head_grp.rotation = Vec3(HEAD_HUNT[0] + random.uniform(-30, 30), random.uniform(-48, 48),
                                 HEAD_HUNT[2] + random.uniform(-32, 32))
        figure.rotation_z = random.uniform(-9, 9)
        figure.x = random.uniform(-0.05, 0.05)
    else:
        head_grp.rotation = Vec3(*HEAD_HUNT)                    # same posture every time
        figure.rotation_z = 0
        figure.x = 0
        if t >= state["gl_next"]:
            state["gl_left"] = GLITCH_FRAMES
            state["gl_next"] = t + (0.06 if random.random() < 0.3 else random.uniform(0.6, 2.0))

HEAD_CROSS = (-12, 0, 0)
def _cross_motion(age, t):
    """Held cross: arms locked out, hands flop loose; every so often ONE twitch frame
    (head snaps, arms jerk, wrists get kicked), then straight back to the same pose."""
    twitch = state["gl_left"] > 0
    for s in (-1, 1):
        rx, rz = 0.0, 90.0
        if twitch:
            rx += random.uniform(-30, 30)
            rz += random.uniform(-28, 28)
            wrists[s]._zvel += random.uniform(-260, 260)
        shoulders[s].rotation_x = rx
        shoulders[s].rotation_z = -s * rz
    if twitch:
        state["gl_left"] -= 1
        head_grp.rotation = Vec3(HEAD_CROSS[0] + random.uniform(-32, 32), random.uniform(-52, 52), random.uniform(-30, 30))
        figure.rotation_z = random.uniform(-8, 8)
    else:
        head_grp.rotation = Vec3(*HEAD_CROSS)
        figure.rotation_z = 0
        if t >= state["gl_next"]:
            state["gl_left"] = GLITCH_FRAMES
            state["gl_next"] = t + (0.06 if random.random() < 0.25 else random.uniform(0.8, 2.4))

def update():
    dt = time.dt
    state["t"] += dt
    t = state["t"]
    age = t - state["pose_t0"]
    if abs(getattr(window, "aspect_ratio", 4 / 3) - state["aspect"]) > 1e-3:
        fit_camera()
    if state["auto_spin"]:
        figure.y = BASE_Y + math.sin(t * 2.0) * 0.03
        figure.rotation_y += dt * 4
    if state["pose"] == "wave" and age > 0.5:
        elbows[1].rotation_z = -(106 + 16 * math.sin(age * 8))
    if state["pose"] == "hunt" and age > 0.5:
        _hunt_motion(age, t)
    elif state["pose"] == "cross" and age > 0.1:
        _cross_motion(age, t)
    step_joints(dt, t)
    if state["corrupted"]:
        figure.x = math.sin(t * 40) * 0.02
        for e in PARTS:
            if random.random() < 0.03:
                e.color = random.choice(GLITCH_PALETTE)

print("[5/5] entering main loop", flush=True)
try:
    app.run()
except Exception as e:
    print(f"app.run() raised: {e!r}", file=sys.stderr, flush=True)
    raise
