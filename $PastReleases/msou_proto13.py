"""
M.SOU / FRIENDLY PLUMBER body prototype v11 (Windows 10/11)
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

Camera auto-fits the window. Starts with the custom key/fill/highlight shader ("sou").
L cycles: sou, flat, basic, shadows. The shadows mode is untested on real GPUs (it segfaults
under software GL); cycle past it if it misbehaves.

"his left" = the figure's left = the viewer's right (+x).
Hands: 3 joints per finger and thumb, spring driven (floppy) except in Hunt,
where they lock rigid and spread. Default hand is a proper left/right pair
(thumb forward, palm toward the thigh when the arm hangs).
"""

import sys, math, random
print("[1/5] importing ursina...", flush=True)
from ursina import *
from ursina.shaders import unlit_shader, basic_lighting_shader, lit_with_shadows_shader
from ursina.shader import Shader
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
TFLASH_FRAMES = 2     # Hunt: how many frames the T-pose flash lasts (set 1 for a single frame)

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

def make_visor(nu=26, nv=10):
    """Mario cap bill: wide, curved, arching over the eyes without hiding them. Head-local coords (face = -z)."""
    base_r, L, y0, th = 0.282, 0.100, 0.142, 0.030
    P = []
    for j in range(nv + 1):
        v = j / nv
        row = []
        for i in range(nu + 1):
            u = -1 + 2 * i / nu
            phi = u * math.radians(56)
            ext = L * v * max(0.06, 1 - u * u) ** 0.5
            r = base_r + ext
            droop = 0.22 * ext + 0.08 * u * u * v
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

def make_lathe(points, seg=24):
    """Surface of revolution about the Y axis from profile points (y, r), listed top to bottom."""
    n = len(points)
    verts, norms, tris = [], [], []
    for i, (y, r) in enumerate(points):
        y0, r0 = points[max(i - 1, 0)]
        y1, r1 = points[min(i + 1, n - 1)]
        nr, ny = -(y1 - y0), (r1 - r0)
        ln = math.hypot(nr, ny) or 1.0
        nr, ny = nr / ln, ny / ln
        for j in range(seg):
            a = 2 * math.pi * j / seg
            ca, sa = math.cos(a), math.sin(a)
            verts.append((r * ca, y, r * sa))
            norms.append((nr * ca, ny, nr * sa))
    for i in range(n - 1):
        for j in range(seg):
            a = i * seg + j
            b = i * seg + (j + 1) % seg
            c = (i + 1) * seg + (j + 1) % seg
            d = (i + 1) * seg + j
            tris += [(a, b, c), (a, c, d)]
    return Mesh(vertices=verts, triangles=tris, normals=norms, mode="triangle")

def _interp(table, s):
    if s <= table[0][0]:
        return table[0][1]
    for (s0, v0), (s1, v1) in zip(table, table[1:]):
        if s <= s1:
            t = (s - s0) / (s1 - s0)
            t = t * t * (3 - 2 * t)
            return v0 + (v1 - v0) * t
    return table[-1][1]

def limb_profile(L, table, rings=24, cap_rings=7):
    """Profile (y, r): hemispherical top cap, the tapered limb from y=0 down to y=-L, hemispherical end cap."""
    r_top, r_bot = table[0][1], table[-1][1]
    pts = []
    for k in range(cap_rings):
        th = (math.pi / 2) * k / cap_rings
        pts.append((r_top * math.cos(th), r_top * math.sin(th)))
    for i in range(rings + 1):
        s = i / rings
        pts.append((-L * s, _interp(table, s)))
    for k in range(1, cap_rings + 1):
        th = (math.pi / 2) * k / cap_rings
        pts.append((-L - r_bot * math.sin(th), r_bot * math.cos(th)))
    return pts

def make_capsule(L, rt, rb, seg=14):
    return make_lathe(limb_profile(L, [(0.0, rt), (1.0, rb)], rings=3, cap_rings=5), seg)

def make_ellipsoid(seg=30, rings=20):
    """Smooth unit-diameter sphere; scaled by the entity into any ellipsoid (replaces the faceted built-in)."""
    pts = [(0.5 * math.cos(math.pi * k / rings), 0.5 * math.sin(math.pi * k / rings)) for k in range(rings + 1)]
    return make_lathe(pts, seg)

def make_shoe(nu=26, nv=22):
    """Mario-64-style shoe: fat rounded toe box, narrower heel, flat sole, lower toward the toe.
    Toe = -z, ankle at z = 0."""
    W, L, H, zc = 0.30, 0.44, 0.185, -0.115
    verts, norms, tris = [], [], []
    for i in range(nu + 1):
        th = (math.pi / 2) * i / nu
        for j in range(nv):
            ph = 2 * math.pi * j / nv
            ux, uy, uz = math.sin(th) * math.cos(ph), math.cos(th), math.sin(th) * math.sin(ph)
            t = (1 - uz) / 2
            wid = 0.80 + 0.30 * t
            hgt = H * (1.0 - 0.20 * t)
            verts.append((W / 2 * ux * wid, hgt * uy, zc + (L / 2) * uz))
            norms.append(_unit((ux / (W / 2 * wid), uy / hgt, uz / (L / 2))))
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
    (0.215, 0.135, 0.135, 0.135, 2.0),
    (0.150, 0.205, 0.205, 0.205, 2.0),
    (0.080, 0.250, 0.240, 0.240, 2.0),
    (0.000, 0.268, 0.250, 0.250, 2.0),
    (-0.060, 0.268, 0.242, 0.238, 2.05),
    (-0.120, 0.246, 0.232, 0.215, 2.15),
    (-0.175, 0.212, 0.218, 0.185, 2.25),
    (-0.225, 0.165, 0.206, 0.150, 2.3),
    (-0.265, 0.108, 0.182, 0.105, 2.3),
    (-0.292, 0.055, 0.130, 0.060, 2.2),
    (-0.308, 0.000, 0.000, 0.000, 2.0),
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
        y = 0.25 - 0.558 * (j / ny)
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
            y_bot = -0.04 - 0.17 * back ** 0.7
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
SKIN      = color.rgb32(255, 222, 40)
GLOVE     = SKIN                         # gloves, cuff and face share one canary yellow
CAP_RED   = color.rgb32(222, 32, 24)
SHIRT_RED = color.rgb32(236, 40, 26)
OVERALLS  = color.rgb32(244, 126, 20)
SOLE      = color.rgb32(150, 18, 14)
BOOT      = color.rgb32(224, 32, 24)
BUTTON    = color.rgb32(240, 204, 44)
BUTTON_RIM = color.rgb32(176, 132, 22)
EYE_RIM   = color.rgb32(170, 20, 16)
BLACK     = color.rgb32(6, 6, 6)
RED_LIP   = color.rgb32(222, 26, 26)
DARK      = color.rgb32(30, 30, 30)
GLITCH_PALETTE = [color.rgb32(255, 0, 40), color.rgb32(0, 255, 120),
                  color.rgb32(255, 255, 0), color.rgb32(120, 0, 255)]

# Ursina's "basic" shader ignores lights and just shades by surface direction (front faces get ~46%
# brightness, which is why everything looked dull olive). This one is a real key + fill + soft highlight.
sou_shader = Shader(name="sou_shader", language=Shader.GLSL,
vertex="""
#version 140
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
in vec3 p3d_Normal;
out vec2 texcoord;
out vec3 world_normal;
void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    texcoord = p3d_MultiTexCoord0;
    world_normal = normalize(mat3(p3d_ModelMatrix) * p3d_Normal);
}
""",
fragment="""
#version 140
uniform sampler2D p3d_Texture0;
uniform vec4 p3d_ColorScale;
in vec2 texcoord;
in vec3 world_normal;
out vec4 fragColor;
void main() {
    vec3 N = normalize(world_normal);
    vec3 key  = normalize(vec3(-0.50, 0.72, -0.70));   // toward the light: upper front-left of the viewer
    vec3 fill = normalize(vec3( 0.70, 0.10, -0.55));   // weak fill from the right
    float diff = max(dot(N, key), 0.0);
    float fl = max(dot(N, fill), 0.0);
    float amb = 0.40 + 0.10 * N.y;
    float lit = amb + 0.78 * diff + 0.18 * fl;
    vec4 base = texture(p3d_Texture0, texcoord) * p3d_ColorScale;
    vec3 H = normalize(key + vec3(0.0, 0.0, -1.0));     // the camera always looks along +z
    float spec = pow(max(dot(N, H), 0.0), 36.0) * 0.30;
    fragColor = vec4(base.rgb * lit + vec3(spec), base.a);
}
""")
SHADERS = {"sou": sou_shader, "shadows": lit_with_shadows_shader, "basic": basic_lighting_shader, "flat": unlit_shader}
LIGHT_ORDER = ["sou", "flat", "basic", "shadows"]
BASE_Y = 0.4
state = {"pose": "idle", "t": 0.0, "pose_t0": 0.0, "auto_spin": True, "corrupted": False,
         "light": "sou", "aspect": 0, "flip": False, "gl_next": 0.0, "gl_left": 0, "tf_left": 0, "tf_next": 0.0}

CYL = "cyl"   # sentinel: part() builds a fresh cylinder mesh each time
PARTS = []
def part(model, col, scale, position, parent, rotation=(0, 0, 0), ds=False):
    is_cyl = model is CYL
    if is_cyl:
        model = make_cylinder()
    elif isinstance(model, str) and model == "sphere":
        model = make_ellipsoid()
        ds = True
    e = Entity(model=model, color=col, scale=scale, position=position,
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
head_grp = Entity(parent=figure, position=(0, 0.545, 0), scale=0.86)
part(make_head(), SKIN, 1, Vec3(0, 0, 0), head_grp, ds=True)                    # skull + cheeks + jaw + chin

# ears: big smooth convex ovals at eye level, tilted out at the top, NO lobe
for s in (-1, 1):
    ear = Entity(parent=head_grp, position=(s * 0.282, 0.005, 0.030), rotation=(0, -s * 18, s * 10))
    part("sphere", SKIN, (0.080, 0.215, 0.135), Vec3(0, 0, 0), ear)

# cap: big rounded crown that bulges out behind, SMALL curved bill
part("sphere", CAP_RED, (0.60, 0.38, 0.66), Vec3(0, 0.168, 0.05), head_grp)
part(make_visor(), CAP_RED, 1, Vec3(0, 0, 0), head_grp, ds=True)

# hair: wide mass across the back (the shape you liked) + a real SPIRAL curl at each temple
part(make_hair(), BLACK, 1, Vec3(0, 0, 0), head_grp, ds=True)
def curl_points(phi0=70.0, y0=0.058, turns=1.8, rad0=0.050, r0=0.0165, r1=0.0075, n=46):
    pts = []
    for i in range(n):
        t = i / (n - 1)
        th = turns * 2 * math.pi * t + 0.6
        rho = rad0 * (1 - 0.80 * t)
        yy = y0 + rho * math.cos(th)
        r_xy = max(head_radius(phi0, yy), 0.05)
        pts.append((on_head_ang(phi0 - math.degrees(rho * math.sin(th) / r_xy), yy, sink=0.002), r0 + (r1 - r0) * t))
    return pts
for s in (-1, 1):
    for p, r in curl_points():
        part("sphere", BLACK, r * 2, Vec3(s * p.x, p.y, p.z), head_grp)

# eyes: sunk-in flat discs (lid lumps removed)
EYE_T = 0.014
pupils = {}
eye_jitter = {-1: (0.0, 0.004), 1: (-0.004, -0.006)}
for s in (-1, 1):
    ex, ey = s * 0.102 + eye_jitter[s][0], 0.025 + eye_jitter[s][1]
    rot = head_rot(ex, ey)
    part("sphere", EYE_RIM, (0.135, 0.135, EYE_T), on_head(ex, ey, sink=0.0), head_grp, rotation=rot)
    pupils[s] = part("sphere", BLACK, (0.084, 0.105, EYE_T), on_head(ex, ey, sink=-0.006), head_grp, rotation=rot)

# SOU's nose: short, wide, smooth horizontal oval tucked into the bridge, sitting on the mustache. No nostrils.
part("sphere", SKIN, (0.172, 0.092, 0.150), Vec3(0, -0.116, face_z(0, -0.116) - 0.022), head_grp, rotation=(-10, 0, 0))

# mustache: small spheres sweeping out from under the nose, curling up at the tips
def mustache_path():
    pts = []
    for k in range(9):
        t = k / 8
        pts.append((0.016 + 0.116 * t, -0.178 - 0.010 * math.sin(math.pi * t), 0.034 - 0.011 * t))
    cx, cy = 0.132, -0.178 + 0.030
    for k in range(1, 9):
        ang = math.radians(-90 + 38 * k)
        rad = 0.030 * (1 - 0.07 * k)
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang), 0.022 - 0.0014 * k))
    return pts
for s in (-1, 1):
    for x, y, r in dense(mustache_path()):
        part("sphere", BLACK, r * 2, on_head(s * x, y, sink=0.0), head_grp)
part("sphere", BLACK, (0.15, 0.06, 0.07), Vec3(0, -0.180, face_z(0, -0.180) - 0.016), head_grp)

# mouth: deep black cavity bordered by two solid angular red bars (lips / tooth line), directly under the nose
MOUTH_TOP = -0.226
mouth_top = part("cube", RED_LIP, (0.120, 0.028, 0.032), on_head(0, MOUTH_TOP, sink=0.002), head_grp, rotation=head_rot(0, MOUTH_TOP))
mouth_bot = part("cube", RED_LIP, (0.094, 0.028, 0.032), on_head(0, MOUTH_TOP - 0.050, sink=0.002), head_grp, rotation=head_rot(0, MOUTH_TOP - 0.050))
mouth_cavity = part("cube", BLACK, (0.100, 0.034, 0.030), on_head(0, MOUTH_TOP - 0.025, sink=0.008), head_grp, rotation=head_rot(0, MOUTH_TOP - 0.025))

# ---------------------------------------------------------------------
# TORSO: one squash/potato mass. Red shirt underneath, orange overalls on
# top with a real U-shaped bib edge and straps (high-res so edges are smooth).
# ---------------------------------------------------------------------
TX, TY, TZ = 0.36, 0.31, 0.30
Y_UC, UD, XU = -0.035, 0.07, 0.17       # bib edge higher (buttons ride up with it)

def torso_pt(th, ph):
    c, s = math.cos(th), math.sin(th)
    bulge = 1.0 - 0.14 * c                                 # pear: narrower chest, fuller belly
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
    xs = 0.15 - 0.03 * ((y - Y_UC) / (0.31 - Y_UC))
    return abs(ax - xs) < 0.034

part(make_torso(), SHIRT_RED, 1, Vec3(0, 0, 0), figure, ds=True)                                 # shirt
part("sphere", SHIRT_RED, (0.30, 0.09, 0.23), Vec3(0, 0.275, 0.01), figure)                         # shirt collar: no neck
part(make_torso(is_overalls, lift=0.005, na=240, nt=180), OVERALLS, 1, Vec3(0, 0, 0), figure, ds=True)
part("sphere", OVERALLS, (0.58, 0.26, 0.44), Vec3(0, -0.31, 0), figure)                             # pelvis: overalls hang low
for s in (-1, 1):                                                                                   # 3D domed buttons
    bx, by = s * XU, Y_UC
    c = by / TY
    bulge = 1.0 - 0.14 * c
    rx, rz = TX * bulge, TZ * bulge * 1.10
    bz = -rz * math.sqrt(max(1 - (bx / rx) ** 2 - c * c, 0.02))
    rot = rot_from_inward((-bx / rx ** 2, -by / TY ** 2, -bz / rz ** 2))
    part("sphere", BUTTON_RIM, (0.094, 0.080, 0.026), Vec3(bx, by, bz - 0.004), figure, rotation=rot)
    part("sphere", BUTTON, (0.078, 0.064, 0.044), Vec3(bx, by, bz - 0.016), figure, rotation=rot)

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

def build_chain(parent, pos, lengths, radii, lscale=1.0, rot=(0, 0, 0)):
    """Finger/thumb: 3 joints; each segment is ONE smooth tapered capsule whose radii match its
    neighbours, so the digit reads as a single tapering rubber-hose finger."""
    joints, p = [], parent
    for idx in range(3):
        L = lengths[idx] * lscale
        if idx == 0:
            j = mk_joint(p, pos, rot, base=True)
        else:
            j = mk_joint(p, (0, -lengths[idx - 1] * lscale, 0))
        part(make_capsule(L, radii[idx], radii[idx + 1]), GLOVE, 1, Vec3(0, 0, 0), j, ds=True)
        joints.append(j)
        p = j
    return joints

SEG_L = (0.078, 0.058, 0.046)
FING_R = (0.0195, 0.0172, 0.0150, 0.0128)
THUMB_R = (0.0235, 0.0210, 0.0180, 0.0150)
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
ARM_UP, ARM_FORE = 0.30, 0.255        # 16% longer than v10
for s in (-1, 1):
    sh = Entity(parent=figure, position=(s * 0.285, 0.185, 0), rotation=(0, 0, -s * 12))
    shoulders[s] = sh
    part("sphere", SHIRT_RED, (0.225, 0.205, 0.205), Vec3(0, 0.005, 0), sh)             # broad deltoid
    part(CYL, SHIRT_RED, (0.17, ARM_UP, 0.17), Vec3(0, -ARM_UP / 2, 0), sh)
    el = Entity(parent=sh, position=(0, -ARM_UP, 0), rotation=(8, 0, 0))
    elbows[s] = el
    part("sphere", SHIRT_RED, 0.17, Vec3(0, 0, 0), el)
    part(CYL, SHIRT_RED, (0.15, ARM_FORE, 0.15), Vec3(0, -ARM_FORE / 2, 0), el)
    wr = mk_joint(el, (0, -ARM_FORE, 0))
    wr._tw = wr._twc = s * 90.0                                                          # palm toward the thigh
    wr._zang = wr._zvel = wr._ztgt = 0.0
    wr._kz, wr._cz = 130.0, 8.5
    wrists[s] = wr
    part(CYL, GLOVE, (0.140, 0.055, 0.140), Vec3(0, -0.018, 0), wr)                       # glove wrist
    part(make_torus(0.080, 0.027), GLOVE, 1, Vec3(0, -0.040, 0), wr, ds=True)             # ONE thick cuff where wrist meets palm
    part("sphere", GLOVE, (0.160, 0.178, 0.086), Vec3(0, -0.130, 0), wr)                  # smooth palm
    fingers[s] = []
    for k, (fx, ls) in enumerate(FINGERS):
        ch = build_chain(wr, (fx, -0.200, -0.012), SEG_L, FING_R, ls)
        ch[0]._fx = fx
        fingers[s].append(ch)
    thumbs[s] = build_chain(wr, (s * 0.080, -0.155, -0.022), (0.064, 0.052, 0.042), THUMB_R, 1.0, rot=(0, 0, -s * 38))

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
THIGH_L, SHIN_L = 0.34, 0.36
THIGH_T = [(0.0, 0.118), (0.16, 0.124), (0.50, 0.101), (0.86, 0.082), (1.0, 0.086)]
SHIN_T = [(0.0, 0.084), (0.14, 0.084), (0.34, 0.093), (0.62, 0.075), (0.90, 0.064), (1.0, 0.062)]
for s in (-1, 1):
    hp = Entity(parent=figure, position=(s * 0.18, -0.30, 0))
    hips[s] = hp
    part(make_lathe(limb_profile(THIGH_L, THIGH_T), 24), OVERALLS, 1, Vec3(0, 0, 0), hp, ds=True)
    kn = Entity(parent=hp, position=(0, -THIGH_L, 0))
    knees[s] = kn
    part(make_lathe(limb_profile(SHIN_L, SHIN_T), 24), OVERALLS, 1, Vec3(0, 0, 0), kn, ds=True)
    part(make_shoe(), BOOT, 1, Vec3(0, -0.45, 0), kn, ds=True)
    part("sphere", SOLE, (0.320, 0.046, 0.480), Vec3(0, -0.452, -0.115), kn)

for s in (-1, 1):
    set_hand(s, "rest", twist=s * 90.0, snap=True)

# ---------------------------------------------------------------------
# Camera (auto-fit) + lights
# ---------------------------------------------------------------------
CAM_Y = 0.265
def fit_camera():
    asp = getattr(window, "aspect_ratio", 4 / 3)
    hfov = math.radians(camera.fov)
    vfov = 2 * math.atan(math.tan(hfov / 2) / asp)
    d = max((2.5 / 2) / math.tan(vfov / 2), (1.9 / 2) / math.tan(hfov / 2))
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
    "hips": dict(pitch=2, head=(6, 0, 0), sh=both((0, 64)), el=both((0, -88)),
                 fing=both("fist"), wz={-1: 28.0, 1: -28.0}, mouth=1.0),
    # points with the INDEX finger, palm facing down
    "point": dict(head=(-8, 0, 8), sh={-1: (82, 0), 1: (0, 12)}, el={-1: (6, 0), 1: (8, 0)},
                  fing={-1: "point", 1: "rest"}, twist={-1: 180.0, 1: 90.0}),
    "glance": dict(yaw=158, y=BASE_Y - 0.02, head=(-4, -72, 4),
                   sh={-1: (28, 12), 1: (-30, 12)}, el={-1: (22, 0), 1: (14, 0)},
                   hip={-1: -20, 1: 26}, knee={-1: -42, 1: 0}),
    # hands on hips, skeptical head tilt (from the hands-on-hips reference shots)
    "doubt": dict(pitch=3, head=(4, -12, 11), sh=both((0, 64)), el=both((0, -88)),
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
    gap = 0.018 + 0.032 * open_amount
    mouth_bot.animate_y(MOUTH_TOP - gap, duration=0.25)
    mouth_cavity.animate_y(MOUTH_TOP - gap / 2, duration=0.25)
    mouth_cavity.animate_scale_y(max(0.012, gap - 0.016), duration=0.25)
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
    state["tf_left"] = 0
    state["tf_next"] = state["t"] + 2.2
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
    """Slow circling arms + float bob. Springtrap glitches: an erratic twitch frame, and every few
    seconds a T-POSE FLASH (arms snap straight out, hands drop like rags), then straight back."""
    twitch = state["gl_left"] > 0
    flash = state["tf_left"] > 0
    for s in (-1, 1):
        ph = 0.0 if s == 1 else math.pi
        w = age * 1.9 + ph
        rx = 84 + 12 * math.sin(w)
        rz = 10 + 10 * math.cos(w)
        ex, ez = 10.0, 24.0
        if twitch:
            rx += random.uniform(-38, 38)
            rz += random.uniform(-22, 22)
        if flash:
            rx, rz, ex, ez = 0.0, 90.0, 0.0, 0.0
        shoulders[s].rotation_x = rx
        shoulders[s].rotation_z = -s * rz
        elbows[s].rotation_x = ex
        elbows[s].rotation_z = s * ez
        knees[s].rotation_x = -72 + 8 * math.sin(age * 1.3 + ph)
        if flash:
            wrists[s]._zang = -s * 85.0                     # hands flop down (Hunt palms are twisted 180), the spring pulls them back
            wrists[s]._zvel = 0.0
    figure.y = BASE_Y + 0.20 + 0.035 * math.sin(age * 1.4)
    if flash:
        state["tf_left"] -= 1
        head_grp.rotation = Vec3(-12, 0, 0)
        figure.rotation_z = 0
        figure.x = 0
    elif twitch:
        state["gl_left"] -= 1
        head_grp.rotation = Vec3(HEAD_HUNT[0] + random.uniform(-30, 30), random.uniform(-48, 48),
                                 HEAD_HUNT[2] + random.uniform(-32, 32))
        figure.rotation_z = random.uniform(-9, 9)
        figure.x = random.uniform(-0.05, 0.05)
    else:
        head_grp.rotation = Vec3(*HEAD_HUNT)                    # same posture every time
        figure.rotation_z = 0
        figure.x = 0
        if t >= state["tf_next"]:
            state["tf_left"] = TFLASH_FRAMES
            state["tf_next"] = t + random.uniform(2.5, 5.5)
        elif t >= state["gl_next"]:
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
