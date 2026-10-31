"""
M.SOU / FRIENDLY PLUMBER body prototype v3 (Windows 10/11)
-----------------------------------------------------------
Primitives only, no imported meshes or textures.

Keys:
  1 Look behind   2 Face user (Active)   3 Face user (Deactive)   4 Hunt
  G glitch on/off      L cycle lighting: basic / shadows / flat
  Q / E nudge yaw      Esc quit

Starts in basic lighting. Press L to try the shadow shader (untested on real
GPUs, it segfaults under software GL); press L again to fall back.

FULL_OVERALLS = True  -> orange overalls cover the whole torso, red only on
                         sleeves, shoulders and collar.
FULL_OVERALLS = False -> red shirt chest with straps over it.
"""

import sys, math, random
print("[1/5] importing ursina...", flush=True)
from ursina import *
from ursina.shaders import unlit_shader, basic_lighting_shader, lit_with_shadows_shader
print("[2/5] ursina imported OK", flush=True)

FULL_OVERALLS = True

print("[3/5] creating window...", flush=True)
app = Ursina(borderless=False, fullscreen=False, vsync=False,
             title="FRIENDLY PLUMBER", development_mode=True)
window.position = Vec2(100, 100)
window.size = Vec2(1024, 768)
window.always_on_top = False
window.exit_button.visible = True
print("[4/5] window created OK", flush=True)


def make_cylinder(res=18):
    """Capped unit cylinder (radius .5, height 1, centred) with outward normals.
    Used double-sided, so it renders from any angle regardless of winding."""
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

cyl = "cyl"   # sentinel: every part builds its OWN mesh (a Mesh can only live under one Entity)

# ---------------------------------------------------------------------
# Palette (0-255 via rgb32; plain color.rgb wants 0-1 floats)
# ---------------------------------------------------------------------
SKIN      = color.rgb32(232, 197, 68)
CAP_RED   = color.rgb32(198, 28, 22)
SHIRT_RED = color.rgb32(180, 24, 20)
OVERALLS  = color.rgb32(216, 112, 18)
STRAP     = color.rgb32(150, 70, 12)
GLOVE     = color.rgb32(232, 197, 68)
CUFF      = color.rgb32(196, 150, 36)
BOOT      = color.rgb32(70, 14, 12)
EYE_RIM   = color.rgb32(170, 20, 16)
BLACK     = color.rgb32(6, 6, 6)
TOOTH     = color.rgb32(232, 224, 200)
GUM       = color.rgb32(150, 18, 18)
GLITCH_PALETTE = [color.rgb32(255, 0, 40), color.rgb32(0, 255, 120),
                  color.rgb32(255, 255, 0), color.rgb32(120, 0, 255)]

SHADERS = {"shadows": lit_with_shadows_shader, "basic": basic_lighting_shader, "flat": unlit_shader}
LIGHT_ORDER = ["basic", "shadows", "flat"]
BASE_Y = 0.4
state = {"pose": "idle", "t": 0.0, "auto_spin": True, "corrupted": False, "light": "basic"}

PARTS = []
def part(model, col, scale, position, parent, rotation=(0, 0, 0)):
    is_cyl = model is cyl
    e = Entity(model=make_cylinder() if is_cyl else model, color=col, scale=scale, position=position,
               rotation=rotation, parent=parent, shader=SHADERS[state["light"]])
    if is_cyl:
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

figure = Entity(y=BASE_Y)

# ---------------------------------------------------------------------
# HEAD. Face features sit ON the head sphere via on_head(). Camera looks
# toward +z, so the face is at NEGATIVE z.
# ---------------------------------------------------------------------
HEAD_R = 0.25
head_grp = Entity(parent=figure, position=(0, 0.56, 0))

def on_head(x, y, sink=0.0, side=-1):
    """Head-local point on the sphere. sink>0 buries it, sink<0 lifts it out."""
    sd = math.sqrt(max(HEAD_R ** 2 - x * x - y * y, 1e-5))
    return Vec3(x, y, side * sd - side * sink)

def head_rot(x, y, side=-1):
    sd = math.sqrt(max(HEAD_R ** 2 - x * x - y * y, 1e-5))
    return rot_from_inward((-x, -y, -side * sd))

part("sphere", SKIN, HEAD_R * 2, Vec3(0, 0, 0), head_grp)                      # skull
for s in (-1, 1):
    part("sphere", SKIN, 0.11, Vec3(s * 0.243, -0.012, 0.02), head_grp)         # ears

# cap dome + Mario-style brim (flat oval visor drooping forward)
part("sphere", CAP_RED, (0.58, 0.34, 0.58), Vec3(0, 0.17, 0.01), head_grp)
part(cyl, CAP_RED, (0.40, 0.028, 0.27), Vec3(0, 0.095, -0.19), head_grp, rotation=(-8, 0, 0))

# swoopy hair: temple curls beside the ears + tuft at the back under the cap
for s in (-1, 1):
    part("sphere", BLACK, (0.06, 0.13, 0.045), on_head(s * 0.215, 0.03, sink=0.01), head_grp, rotation=(0, 0, -s * 28))
    part("sphere", BLACK, (0.05, 0.07, 0.04), on_head(s * 0.222, -0.05, sink=0.01), head_grp, rotation=(0, 0, -s * 50))
    part("sphere", BLACK, (0.10, 0.16, 0.08), on_head(s * 0.12, 0.02, sink=0.02, side=1), head_grp)
part("sphere", BLACK, (0.30, 0.20, 0.10), on_head(0, 0.03, sink=0.02, side=1), head_grp)

# eyes, SUNK IN: flat red iris disc + flat huge black pupil disc lying on the
# skull (not bulging), inside a raised skin lip so the eye reads as recessed
# from the side profile.
EYE_T = 0.016
pupils = {}
eye_jitter = {-1: (0.0, 0.004), 1: (-0.004, -0.006)}
for s in (-1, 1):
    ex, ey = s * 0.115 + eye_jitter[s][0], 0.025 + eye_jitter[s][1]
    rot = head_rot(ex, ey)
    part("sphere", EYE_RIM, (0.17, 0.17, EYE_T), on_head(ex, ey, sink=0.0), head_grp, rotation=rot)
    pupils[s] = part("sphere", BLACK, (0.124, 0.124, EYE_T), on_head(ex, ey, sink=-0.007), head_grp, rotation=rot)
    squash = math.sqrt(max(1 - (ex / HEAD_R) ** 2, 0.2))
    for k in range(22):
        a = 2 * math.pi * k / 22
        part("sphere", SKIN, 0.05, on_head(ex + math.cos(a) * 0.108 * squash, ey + math.sin(a) * 0.108, sink=-0.002), head_grp)

# nose
part("sphere", SKIN, (0.15, 0.135, 0.16), on_head(0, -0.05, sink=-0.03), head_grp)

# mustache: blobs following the surface, curling up at the tips
for s in (-1, 1):
    for mx, my, mr in [(0.03, -0.108, 0.05), (0.085, -0.115, 0.05), (0.135, -0.105, 0.042), (0.172, -0.082, 0.032)]:
        part("sphere", BLACK, (mr * 2.4, mr * 1.7, mr * 1.6), on_head(s * mx, my, sink=0.02), head_grp)

# mouth: dark cavity, teeth row, gum line
mouth_cavity = part("sphere", BLACK, (0.17, 0.07, 0.05), on_head(0, -0.18, sink=0.0), head_grp)
mouth_gum = part("sphere", GUM, (0.17, 0.02, 0.045), on_head(0, -0.212, sink=-0.002), head_grp)
teeth = []
for tx in (-0.07, -0.042, -0.014, 0.014, 0.042, 0.07):
    teeth.append(part("cube", TOOTH, (0.026, 0.03, 0.012), on_head(tx, -0.165, sink=-0.004), head_grp))

# ---------------------------------------------------------------------
# TORSO. Wide suspender straps run front AND back over the whole body.
# ---------------------------------------------------------------------
CH = (0.32, 0.31, 0.26)
CHC = -0.02
def on_chest(x, y, sink=0.0, side=-1):
    q = 1 - (x / CH[0]) ** 2 - ((y - CHC) / CH[1]) ** 2
    z = side * CH[2] * math.sqrt(max(q, 0.01))
    return Vec3(x, y, z - side * sink), rot_from_inward((-x / CH[0] ** 2, -(y - CHC) / CH[1] ** 2, -z / CH[2] ** 2))

TORSO = OVERALLS if FULL_OVERALLS else SHIRT_RED
part("sphere", SKIN, (0.16, 0.12, 0.14), Vec3(0, 0.29, 0), figure)                 # neck
part("sphere", TORSO, (0.64, 0.62, 0.52), Vec3(0, -0.02, 0), figure)               # chest
part("sphere", OVERALLS, (0.66, 0.44, 0.54), Vec3(0, -0.34, 0), figure)            # belly/hips
if FULL_OVERALLS:
    part("sphere", SHIRT_RED, (0.40, 0.22, 0.34), Vec3(0, 0.22, -0.02), figure)    # shirt collar

for s in (-1, 1):
    for side in (-1, 1):
        for sx, sy in [(0.14, 0.17), (0.15, 0.08), (0.16, -0.01), (0.17, -0.10), (0.18, -0.19), (0.19, -0.28)]:
            p, r = on_chest(s * sx, sy, sink=-0.006, side=side)
            part("cube", STRAP, (0.15, 0.11, 0.04), p, figure, rotation=r)
    p, r = on_chest(s * 0.18, -0.12, sink=-0.03)
    part("sphere", GLOVE, 0.06, p, figure)                                          # buttons

# ---------------------------------------------------------------------
# ARMS: shoulder -> upper arm -> elbow -> forearm -> cuff -> palm + fingers
# ---------------------------------------------------------------------
shoulders, elbows = {}, {}
for s in (-1, 1):
    sh = Entity(parent=figure, position=(s * 0.40, 0.14, 0), rotation=(0, 0, s * 10))
    shoulders[s] = sh
    part("sphere", SHIRT_RED, 0.30, Vec3(0, 0, 0), sh)
    part(cyl, SHIRT_RED, (0.15, 0.26, 0.15), Vec3(0, -0.13, 0), sh)
    el = Entity(parent=sh, position=(0, -0.26, 0), rotation=(-8, 0, 0))
    elbows[s] = el
    part("sphere", SHIRT_RED, 0.16, Vec3(0, 0, 0), el)
    part(cyl, SHIRT_RED, (0.13, 0.24, 0.13), Vec3(0, -0.12, 0), el)
    wr = Entity(parent=el, position=(0, -0.24, 0))
    part(cyl, CUFF, (0.15, 0.045, 0.15), Vec3(0, 0, 0), wr)
    part("sphere", GLOVE, (0.12, 0.14, 0.075), Vec3(0, -0.07, 0), wr)
    for fx, fl in [(-0.045, 0.11), (-0.015, 0.13), (0.015, 0.13), (0.045, 0.11)]:
        part("sphere", GLOVE, (0.03, fl, 0.03), Vec3(fx, -0.10 - fl / 2, -0.012), wr, rotation=(-8, 0, fx * 160))
    part("sphere", GLOVE, (0.032, 0.09, 0.032), Vec3(-s * 0.07, -0.10, -0.02), wr, rotation=(0, 0, -s * 30))

# ---------------------------------------------------------------------
# LEGS: round thigh, shin tube, knee/ankle ball, boot
# ---------------------------------------------------------------------
hips = {}
for s in (-1, 1):
    hp = Entity(parent=figure, position=(s * 0.19, -0.55, 0))
    hips[s] = hp
    part("sphere", OVERALLS, (0.27, 0.34, 0.27), Vec3(0, -0.08, 0), hp)
    part(cyl, OVERALLS, (0.15, 0.26, 0.15), Vec3(0, -0.31, -0.005), hp)
    part("sphere", OVERALLS, 0.16, Vec3(0, -0.44, -0.01), hp)
    part("sphere", BOOT, (0.21, 0.13, 0.30), Vec3(0, -0.50, -0.06), hp)

# ---------------------------------------------------------------------
# Camera + lights
# ---------------------------------------------------------------------
camera.position = (0, 0.30, -4.4)
camera.rotation = (0, 0, 0)

sun = DirectionalLight(shadows=True, shadow_map_resolution=Vec2(2048, 2048))
sun.look_at(Vec3(-0.5, -0.9, 1))
ambient = AmbientLight(color=color.rgba(0.55, 0.50, 0.55, 1))
sun.update_bounds(figure)

pose_label = Text(text="MODE: idle", position=window.top_left + Vec2(0.02, -0.03), scale=1.0, color=color.white)
Text(text="[1] Look behind  [2] Face-Active  [3] Face-Deactive  [4] Hunt   [G] glitch  [L] light  [Q/E] rotate  [Esc] quit",
     position=window.bottom_left + Vec2(0.02, 0.02), scale=0.7, color=color.white)

def set_lighting(mode):
    state["light"] = mode
    for e in PARTS:
        e.shader = SHADERS[mode]
    print("lighting:", mode, flush=True)

# ---------------------------------------------------------------------
# Poses
# ---------------------------------------------------------------------
def _face(open_amount, eye_scale, eye_color):
    mouth_cavity.animate_scale_y(0.07 * open_amount, duration=0.25)
    on = open_amount > 0.3
    mouth_gum.enabled = on
    for t in teeth:
        t.enabled = on
    for s in (-1, 1):
        pupils[s].animate_scale(Vec3(eye_scale, eye_scale, EYE_T), duration=0.25)
        pupils[s].animate_color(eye_color, duration=0.25)

def apply_pose(name):
    state["pose"] = name
    state["auto_spin"] = False
    pose_label.text = f"MODE: {name}"
    d = 0.35
    yaw, pitch, y, sc = 0, 0, BASE_Y, 1.0
    head_x, head_z, sh_x, el_x = 0, 0, 0, -8
    mouth, eye_s, eye_c = 1.0, 0.124, BLACK
    if name == "look_behind":
        yaw = 180
    elif name == "face_deactive":
        y = BASE_Y - 0.05
        head_x, head_z, sh_x, el_x = 22, 5, 8, -4
        mouth, eye_s, eye_c = 0.15, 0.09, color.rgb32(30, 30, 30)
    elif name == "hunt":
        pitch, y, sc = -14, BASE_Y - 0.18, 1.06
        head_x, sh_x, el_x = -12, -80, -25
        mouth, eye_s = 1.4, 0.16
    figure.animate_rotation_y(yaw, duration=d)
    figure.animate_rotation_x(pitch, duration=d)
    figure.animate_y(y, duration=d)
    figure.animate_scale(sc, duration=d)
    head_grp.animate_rotation_x(head_x, duration=d)
    head_grp.animate_rotation_z(head_z, duration=d)
    for s in (-1, 1):
        shoulders[s].animate_rotation_x(sh_x, duration=d)
        elbows[s].animate_rotation_x(el_x, duration=d)
    _face(mouth, eye_s, eye_c)

def _glitch_off():
    for e in PARTS:
        e.color = e._orig
    figure.x = 0
    if state["pose"] != "idle":
        apply_pose(state["pose"])

def input(key):
    if key in ("1", "2", "3", "4"):
        apply_pose({"1": "look_behind", "2": "face_active", "3": "face_deactive", "4": "hunt"}[key])
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
    if state["auto_spin"]:
        figure.y = BASE_Y + math.sin(state["t"] * 2.0) * 0.03
        figure.rotation_y += time.dt * 4
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
