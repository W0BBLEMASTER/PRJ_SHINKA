"""
M.SOU / FRIENDLY PLUMBER body prototype v5 (Windows 10/11)
-----------------------------------------------------------
Primitives and generated meshes only, no imported assets.

Keys:
  1 Look behind   2 Face user (Active)   3 Face user (Deactive)   4 Hunt
  5 Wave (looks up and off to his left, waves with his left)
  6 Strut         7 Point
  G glitch on/off      L cycle lighting: basic / shadows / flat
  Q / E nudge yaw      Esc quit

Camera auto-fits the window. Starts in basic lighting. Press L to try the
shadow shader (untested on real GPUs, it segfaults under software GL).

"his left" = the figure's left = the viewer's right (+x).
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

# ---------------------------------------------------------------------
# Mesh generators. A Mesh can only live under ONE Entity, so every part
# builds its own instance. All are rendered double-sided.
# ---------------------------------------------------------------------
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

def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])

def make_visor(nu=22, nv=9):
    """Mario-style cap bill: rounded oval outline, curved, drooping away from the cap.
    Built in head-local coordinates (face = -z)."""
    base_r, L, y0, th = 0.275, 0.26, 0.135, 0.026
    P = []
    for j in range(nv + 1):
        v = j / nv
        row = []
        for i in range(nu + 1):
            u = -1 + 2 * i / nu
            phi = u * math.radians(48)
            ext = L * v * max(0.12, 1 - 0.80 * u * u) ** 0.8
            r = base_r + ext
            droop = 0.17 * ext + 0.06 * u * u * v
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
                n = _cross((c[0] - d[0], c[1] - d[1], c[2] - d[2]), (a[0] - b[0], a[1] - b[1], a[2] - b[2]))
                ln = math.sqrt(sum(t * t for t in n)) or 1.0
                n = tuple(t / ln for t in n)
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

# ---------------------------------------------------------------------
# Palette (0-255 via rgb32; plain color.rgb wants 0-1 floats)
# ---------------------------------------------------------------------
SKIN      = color.rgb32(232, 197, 68)
GLOVE     = SKIN                         # gloves, cuff donuts and face share one yellow
CAP_RED   = color.rgb32(205, 30, 22)
SHIRT_RED = color.rgb32(222, 34, 22)
OVERALLS  = color.rgb32(238, 120, 12)
STRAP     = color.rgb32(214, 100, 10)
BOOT      = color.rgb32(190, 26, 20)
EYE_RIM   = color.rgb32(170, 20, 16)
BLACK     = color.rgb32(6, 6, 6)
TOOTH     = color.rgb32(232, 224, 200)
GUM       = color.rgb32(150, 18, 18)
DARK      = color.rgb32(30, 30, 30)
GLITCH_PALETTE = [color.rgb32(255, 0, 40), color.rgb32(0, 255, 120),
                  color.rgb32(255, 255, 0), color.rgb32(120, 0, 255)]

SHADERS = {"shadows": lit_with_shadows_shader, "basic": basic_lighting_shader, "flat": unlit_shader}
LIGHT_ORDER = ["basic", "shadows", "flat"]
BASE_Y = 0.4
state = {"pose": "idle", "t": 0.0, "pose_t0": 0.0, "auto_spin": True, "corrupted": False,
         "light": "basic", "aspect": 0}

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

figure = Entity(y=BASE_Y)       # origin = centre of the torso

# ---------------------------------------------------------------------
# HEAD. Face is at -z (camera looks toward +z). on_head() seats features
# on the skull surface so nothing floats.
# ---------------------------------------------------------------------
HEAD_R = 0.25
head_grp = Entity(parent=figure, position=(0, 0.58, 0))

def on_head(x, y, sink=0.0, side=-1):
    sd = math.sqrt(max(HEAD_R ** 2 - x * x - y * y, 1e-5))
    return Vec3(x, y, side * sd - side * sink)

def head_rot(x, y, side=-1):
    sd = math.sqrt(max(HEAD_R ** 2 - x * x - y * y, 1e-5))
    return rot_from_inward((-x, -y, -side * sd))

part("sphere", SKIN, HEAD_R * 2, Vec3(0, 0, 0), head_grp)                       # skull
for s in (-1, 1):
    part("sphere", SKIN, 0.11, Vec3(s * 0.243, -0.012, 0.02), head_grp)          # ears

# cap: dome + curved Mario bill
part("sphere", CAP_RED, (0.58, 0.34, 0.58), Vec3(0, 0.17, 0.01), head_grp)
part(make_visor(), CAP_RED, 1, Vec3(0, 0, 0), head_grp, ds=True)

def dense(pts, k=0.55):
    out = [pts[0]]
    for (x0, y0, r0), (x1, y1, r1) in zip(pts, pts[1:]):
        n = max(1, math.ceil(math.hypot(x1 - x0, y1 - y0) / (k * (r0 + r1) / 2)))
        for i in range(1, n + 1):
            t = i / n
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, r0 + (r1 - r0) * t))
    return out

# hair: little swoop at each temple (comma curling toward the face) + back tuft
SWOOP = [(0.205, 0.078, 0.026), (0.213, 0.054, 0.024), (0.218, 0.030, 0.022),
         (0.216, 0.008, 0.019), (0.207, -0.012, 0.016), (0.194, -0.026, 0.013)]
for s in (-1, 1):
    for x, y, r in dense(SWOOP):
        part("sphere", BLACK, r * 2.3, on_head(s * x, y, sink=0.004), head_grp)
    part("sphere", BLACK, (0.10, 0.16, 0.08), on_head(s * 0.12, 0.02, sink=0.02, side=1), head_grp)
part("sphere", BLACK, (0.30, 0.20, 0.10), on_head(0, 0.03, sink=0.02, side=1), head_grp)

# eyes: SUNK IN (unchanged design), 20% closer together than v4
EYE_T = 0.014
pupils = {}
eye_jitter = {-1: (0.0, 0.004), 1: (-0.004, -0.006)}
for s in (-1, 1):
    ex, ey = s * 0.112 + eye_jitter[s][0], 0.025 + eye_jitter[s][1]
    rot = head_rot(ex, ey)
    part("sphere", EYE_RIM, (0.135, 0.135, EYE_T), on_head(ex, ey, sink=0.0), head_grp, rotation=rot)
    pupils[s] = part("sphere", BLACK, (0.084, 0.105, EYE_T), on_head(ex, ey, sink=-0.006), head_grp, rotation=rot)
    for dy, h in ((-0.078, 0.036), (0.078, 0.042)):
        part("sphere", SKIN, (0.125, h, 0.032), on_head(ex, ey + dy, sink=-0.002), head_grp,
             rotation=head_rot(ex, ey + dy))

# nose
part("sphere", SKIN, (0.14, 0.115, 0.15), on_head(0, -0.075, sink=-0.03), head_grp)

# mustache: small spheres sweeping out from under the nose, curling up at the tips
def mustache_path():
    pts = []
    for k in range(9):
        t = k / 8
        pts.append((0.012 + 0.150 * t, -0.122 - 0.010 * math.sin(math.pi * t), 0.034 - 0.011 * t))
    cx, cy = 0.162, -0.122 + 0.032
    for k in range(1, 10):
        ang = math.radians(-90 + 40 * k)
        rad = 0.032 * (1 - 0.07 * k)
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang), 0.022 - 0.0014 * k))
    return pts
for s in (-1, 1):
    for x, y, r in dense(mustache_path()):
        part("sphere", BLACK, r * 2, on_head(s * x, y, sink=0.0), head_grp)
part("sphere", BLACK, (0.17, 0.07, 0.085), Vec3(0, -0.128, -0.235), head_grp)    # fills under the nose

# mouth: dark cavity, teeth row, gum line
mouth_cavity = part("sphere", BLACK, (0.17, 0.07, 0.05), on_head(0, -0.185, sink=0.0), head_grp, rotation=head_rot(0, -0.185))
mouth_gum = part("sphere", GUM, (0.17, 0.02, 0.045), on_head(0, -0.217, sink=-0.012), head_grp, rotation=head_rot(0, -0.217))
teeth = []
for tx in (-0.07, -0.042, -0.014, 0.014, 0.042, 0.07):
    teeth.append(part("cube", TOOTH, (0.03, 0.034, 0.016), on_head(tx, -0.172, sink=-0.03), head_grp, rotation=head_rot(tx, -0.172)))

# ---------------------------------------------------------------------
# TORSO: one squash/potato mass (wider toward the bottom). Red shirt mesh
# underneath, orange overalls mesh on top with a real U-shaped bib edge
# and straps over the shoulders, front and back.
# ---------------------------------------------------------------------
TX, TY, TZ = 0.33, 0.31, 0.28
Y_UC, UD, XU = -0.10, 0.07, 0.17      # U corner height (buttons), U depth, half-width

def torso_pt(th, ph):
    c, s = math.cos(th), math.sin(th)
    bulge = 1.0 - 0.10 * c
    rx, rz = TX * bulge, TZ * bulge
    x, y, z = rx * s * math.sin(ph), TY * c, -rz * s * math.cos(ph)
    n = (x / rx ** 2, y / TY ** 2, z / rz ** 2)
    ln = math.sqrt(sum(t * t for t in n)) or 1.0
    return (x, y, z), tuple(t / ln for t in n)

def make_torso(select=None, lift=0.0, na=140, nt=108):
    pts = [[torso_pt(math.pi * j / nt, 2 * math.pi * i / na) for i in range(na + 1)] for j in range(nt + 1)]
    verts, norms, tris = [], [], []
    for j in range(nt):
        for i in range(na):
            quad = [pts[j][i], pts[j][i + 1], pts[j + 1][i + 1], pts[j + 1][i]]
            cx = sum(q[0][0] for q in quad) / 4
            cy = sum(q[0][1] for q in quad) / 4
            cz = sum(q[0][2] for q in quad) / 4
            if select and not select(cx, cy, cz):
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
    thr = (Y_UC - UD * bump) if z < 0 else (Y_UC + 0.10 * bump)      # front: U dips down; back: rises
    if y < thr:
        return True
    xs = 0.165 - 0.05 * ((y - Y_UC) / (0.31 - Y_UC))                  # straps converge toward the neck
    return abs(ax - xs) < 0.034

part("sphere", SKIN, (0.17, 0.10, 0.15), Vec3(0, 0.33, 0), figure)                         # neck
part(make_torso(), SHIRT_RED, 1, Vec3(0, 0, 0), figure, ds=True)                          # shirt
part(make_torso(is_overalls, lift=0.005), OVERALLS, 1, Vec3(0, 0, 0), figure, ds=True)    # overalls
for s in (-1, 1):                                                                         # buttons on the lower tummy
    bx, by = s * XU, Y_UC
    c = by / TY
    bulge = 1.0 - 0.10 * c
    bz = -TZ * bulge * math.sqrt(max(1 - (bx / (TX * bulge)) ** 2 - c * c, 0.02))
    part("sphere", SKIN, 0.062, Vec3(bx, by, bz - 0.012), figure)

# ---------------------------------------------------------------------
# ARMS: thick sleeves. shoulder -> upper arm -> elbow -> forearm -> two
# donut cuffs -> palm + long-oval fingers (each finger is a pivot).
# s = +1 is HIS LEFT (viewer's right).
# ---------------------------------------------------------------------
shoulders, elbows, fingers = {}, {}, {}
for s in (-1, 1):
    sh = Entity(parent=figure, position=(s * 0.27, 0.20, 0), rotation=(0, 0, -s * 12))
    shoulders[s] = sh
    part("sphere", SHIRT_RED, 0.20, Vec3(0, 0, 0), sh)
    part(CYL, SHIRT_RED, (0.17, 0.26, 0.17), Vec3(0, -0.13, 0), sh)
    el = Entity(parent=sh, position=(0, -0.26, 0), rotation=(8, 0, 0))
    elbows[s] = el
    part("sphere", SHIRT_RED, 0.17, Vec3(0, 0, 0), el)
    part(CYL, SHIRT_RED, (0.15, 0.22, 0.15), Vec3(0, -0.11, 0), el)
    wr = Entity(parent=el, position=(0, -0.22, 0))
    part(make_torus(0.082, 0.028), GLOVE, 1, Vec3(0, 0.005, 0), wr, ds=True)               # donut cuff
    part(make_torus(0.086, 0.028), GLOVE, 1, Vec3(0, -0.045, 0), wr, ds=True)              # donut cuff
    part("sphere", GLOVE, (0.15, 0.16, 0.085), Vec3(0, -0.11, 0), wr)                       # palm
    fingers[s] = []
    for fx, fl in [(-0.05, 0.12), (-0.017, 0.14), (0.017, 0.14), (0.05, 0.12)]:
        pv = Entity(parent=wr, position=(fx, -0.17, -0.012), rotation=(-8, 0, fx * 160))
        pv._fx = fx
        part("sphere", GLOVE, (0.034, fl, 0.034), Vec3(0, -fl / 2, 0), pv)
        fingers[s].append(pv)
    part("sphere", GLOVE, (0.036, 0.10, 0.036), Vec3(-s * 0.08, -0.13, -0.02), wr, rotation=(0, 0, -s * 35))  # thumb

# ---------------------------------------------------------------------
# LEGS: tubular thigh and shin, knobby knee ball, big round red shoe.
# ---------------------------------------------------------------------
hips, knees = {}, {}
for s in (-1, 1):
    hp = Entity(parent=figure, position=(s * 0.17, -0.27, 0))
    hips[s] = hp
    part("sphere", OVERALLS, 0.20, Vec3(0, 0, 0), hp)
    part(CYL, OVERALLS, (0.18, 0.28, 0.18), Vec3(0, -0.14, 0), hp)
    kn = Entity(parent=hp, position=(0, -0.28, 0))
    knees[s] = kn
    part("sphere", OVERALLS, 0.215, Vec3(0, 0, -0.012), kn)
    part(CYL, OVERALLS, (0.16, 0.27, 0.16), Vec3(0, -0.145, 0), kn)
    part("sphere", BOOT, (0.25, 0.15, 0.34), Vec3(0, -0.34, -0.07), kn)

# ---------------------------------------------------------------------
# Camera (auto-fit) + lights
# ---------------------------------------------------------------------
CAM_Y = 0.38
def fit_camera():
    asp = getattr(window, "aspect_ratio", 4 / 3)
    hfov = math.radians(camera.fov)
    vfov = 2 * math.atan(math.tan(hfov / 2) / asp)
    d = max((2.25 / 2) / math.tan(vfov / 2), (1.8 / 2) / math.tan(hfov / 2))
    camera.position = (0, CAM_Y, -d)
    camera.rotation = (0, 0, 0)
    state["aspect"] = asp
fit_camera()

sun = DirectionalLight(shadows=True, shadow_map_resolution=Vec2(2048, 2048))
sun.look_at(Vec3(-0.5, -0.9, 1))
ambient = AmbientLight(color=color.rgba(0.62, 0.58, 0.62, 1))
sun.update_bounds(figure)

pose_label = Text(text="MODE: idle", position=window.top_left + Vec2(0.02, -0.03), scale=1.0, color=color.white)
Text(text="[1] Look behind [2] Face-Active [3] Face-Deactive [4] Hunt [5] Wave [6] Strut [7] Point   [G] glitch [L] light [Q/E] rotate [Esc] quit",
     position=window.bottom_left + Vec2(0.02, 0.02), scale=0.6, color=color.white)

def set_lighting(mode):
    state["light"] = mode
    for e in PARTS:
        e.shader = SHADERS[mode]
    print("lighting:", mode, flush=True)

# ---------------------------------------------------------------------
# Poses. Order is fixed: 1-4 unchanged, 5-7 appended.
# Sign conventions (verified against renders): shoulder/hip rx > 0 swings
# the limb FORWARD (toward the viewer); knee rx < 0 bends the shin back;
# head rx > 0 looks UP; head ry < 0 turns the face toward his left (+x).
# sh/el = (pitch, outward-roll) per side; roll is applied as -side*value.
# ---------------------------------------------------------------------
def both(v):
    return {-1: v, 1: v}

REST = dict(yaw=0, pitch=0, y=BASE_Y, sc=1.0, head=(0, 0, 0),
            sh=both((0, 12)), el=both((8, 0)), hip=both(0), knee=both(0),
            fing=both("rest"), mouth=1.0, eye=0.105, eyec=BLACK)

POSES = {
    "look_behind": dict(yaw=180),
    "face_active": dict(),
    "face_deactive": dict(y=BASE_Y - 0.05, head=(-10, 0, 5), sh=both((-6, 12)), el=both((4, 0)),
                          mouth=0.15, eye=0.07, eyec=DARK),
    "hunt": dict(pitch=-14, y=BASE_Y - 0.12, sc=1.06, head=(12, 0, 0),
                 sh=both((75, 12)), el=both((20, 0)), mouth=1.4, eye=0.12),
    "wave": dict(head=(18, -32, 6), sh={-1: (0, 12), 1: (0, 50)}, el={-1: (8, 0), 1: (0, 106)},
                 fing={-1: "rest", 1: "spread"}),
    "strut": dict(yaw=22, y=BASE_Y - 0.03, head=(0, -22, 4),
                  sh={-1: (35, 12), 1: (-32, 12)}, el={-1: (30, 0), 1: (10, 0)},
                  hip={-1: -18, 1: 32}, knee={-1: -55, 1: 0}),
    "point": dict(head=(-8, 0, 8), sh={-1: (82, 0), 1: (0, 12)}, el={-1: (6, 0), 1: (8, 0)},
                  fing={-1: "point", 1: "rest"}),
}
KEYS = {"1": "look_behind", "2": "face_active", "3": "face_deactive", "4": "hunt",
        "5": "wave", "6": "strut", "7": "point"}

def _face(open_amount, eye_scale, eye_color):
    mouth_cavity.animate_scale_y(0.07 * open_amount, duration=0.25)
    on = open_amount > 0.3
    mouth_gum.enabled = on
    for t in teeth:
        t.enabled = on
    for s in (-1, 1):
        pupils[s].animate_scale(Vec3(eye_scale * 0.8, eye_scale, EYE_T), duration=0.25)
        pupils[s].animate_color(eye_color, duration=0.25)

def _fingers(s, mode, d):
    index_k = 3 if s == -1 else 0
    for k, pv in enumerate(fingers[s]):
        fan = pv._fx * (-380 if mode == "spread" else 160)
        sy = 1.0
        if mode == "point":
            sy = 1.3 if k == index_k else 0.42
        pv.animate_rotation_z(fan, duration=d)
        pv.animate_scale_y(sy, duration=d)

def apply_pose(name):
    P = dict(REST)
    P.update(POSES[name])
    state["pose"] = name
    state["pose_t0"] = state["t"]
    state["auto_spin"] = False
    pose_label.text = f"MODE: {name}"
    d = 0.35
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
        _fingers(s, P["fing"][s], d)
    _face(P["mouth"], P["eye"], P["eyec"])

def _glitch_off():
    for e in PARTS:
        e.color = e._orig
    figure.x = 0
    if state["pose"] != "idle":
        apply_pose(state["pose"])

def input(key):
    if key in KEYS:
        apply_pose(KEYS[key])
    if key == "g":
        state["corrupted"] = not state["corrupted"]
        if not state["corrupted"]:
            _glitch_off()
    if key == "l":
        set_lighting(LIGHT_ORDER[(LIGHT_ORDER.index(state["light"]) + 1) % len(LIGHT_ORDER)])
    if key in ("q", "e"):
        state["auto_spin"] = False
        figure.rotation_y += -15 if key == "q" else 15

def update():
    state["t"] += time.dt
    if abs(getattr(window, "aspect_ratio", 4 / 3) - state["aspect"]) > 1e-3:
        fit_camera()
    if state["auto_spin"]:
        figure.y = BASE_Y + math.sin(state["t"] * 2.0) * 0.03
        figure.rotation_y += time.dt * 4
    if state["pose"] == "wave" and state["t"] - state["pose_t0"] > 0.5:
        w = math.sin((state["t"] - state["pose_t0"]) * 8)
        elbows[1].rotation_z = -(106 + 16 * w)          # hand sways side to side
    if state["corrupted"]:
        figure.x = math.sin(state["t"] * 40) * 0.02
        for e in PARTS:
            if random.random() < 0.03:
                e.color = random.choice(GLITCH_PALETTE)

print("[5/5] entering main loop", flush=True)
try:
    app.run()
except Exception as e:
    print(f"app.run() raised: {e!r}", file=sys.stderr, flush=True)
    raise
