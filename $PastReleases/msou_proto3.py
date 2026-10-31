"""
M.SOU / FRIENDLY PLUMBER — body prototype (Windows 10/11)
----------------------------------------------------------
Procedurally-built from primitives only (spheres + a couple flat
cylinders for the cap brim) — no imported meshes/textures.

Poses (bake keys 1-4, per spec):
  1  Look behind
  2  Face user - Active
  3  Face user - Deactive
  4  Hunt
  G  toggle corruption glitch (independent of pose)
  Q/E  manual yaw nudge
  Esc  quit

Run:
  pip install ursina
  python msou_proto.py
"""

import sys, random
print("[1/5] importing ursina...", flush=True)
from ursina import *
from ursina.models.procedural.cylinder import Cylinder
print("[2/5] ursina imported OK", flush=True)

print("[3/5] creating window...", flush=True)
app = Ursina(
    borderless=False,
    fullscreen=False,
    vsync=False,
    title="FRIENDLY PLUMBER",
    development_mode=True,
)
window.position = Vec2(100, 100)
window.size = Vec2(1024, 768)
window.always_on_top = False
window.exit_button.visible = True
print("[4/5] window created OK", flush=True)

cyl_mesh = Cylinder(6, start=-0.5, height=1)  # flat disc use only (brim)

# ---------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------
SKIN      = color.rgb32(232, 197, 68)
CAP_RED   = color.rgb32(198, 28, 22)
SHIRT_RED = color.rgb32(180, 24, 20)
OVERALLS  = color.rgb32(216, 112, 18)
GLOVE     = color.rgb32(232, 197, 68)   # same tone as skin, not white gloves
BOOT      = color.rgb32(70, 14, 12)
EYE_RIM   = color.rgb32(150, 18, 14)
BLACK     = color.rgb32(6, 6, 6)
TOOTH     = color.rgb32(232, 224, 200)
GUM       = color.rgb32(150, 18, 18)

GLITCH_PALETTE = [color.rgb32(255,0,40), color.rgb32(0,255,120), color.rgb32(255,255,0), color.rgb32(120,0,255)]

figure = Entity()

# ---------------------------------------------------------------------
# HEAD
# ---------------------------------------------------------------------
head = Entity(model="sphere", color=SKIN, scale=0.42, position=(0, 0.55, 0), parent=figure)

cap_dome = Entity(model="sphere", color=CAP_RED, scale=(0.47, 0.30, 0.47), position=(0, 0.78, 0), parent=figure)
cap_brim = Entity(model=cyl_mesh, color=CAP_RED, scale=(0.5, 0.03, 0.36), position=(0, 0.655, -0.13), parent=figure)

# swoopy black hair — side curls poking out under the cap, + back tuft.
# NOTE ON DEPTH: camera sits at -z looking toward +z, so *negative* z is
# "toward the camera" (front of face) and *positive* z is away (back of
# head) — every front-facing feature below uses negative z accordingly.
for side in (-1, 1):
    Entity(model="sphere", color=BLACK, scale=(0.09, 0.15, 0.06),
           position=(side * 0.35, 0.575, -0.05), rotation=(0, 0, side * 25), parent=figure)
Entity(model="sphere", color=BLACK, scale=(0.24, 0.17, 0.11), position=(0, 0.66, 0.30), parent=figure)

# brow ridge (dark band right under the cap line, clear of the eyes below it)
Entity(model="cube", color=BLACK, scale=(0.36, 0.035, 0.06), position=(0, 0.705, -0.335), parent=figure)

# eyes — big red rim, huge black pupil pushed forward of the socket
# (visibly "detached"/bulging rather than flush with the face), each eye
# nudged slightly off-true to read as a little wrong/asymmetric.
eye_offsets = {-1: (0.0, 0.008), 1: (-0.008, -0.014)}
pupils = {}
for side in (-1, 1):
    ox, oy = eye_offsets[side]
    Entity(model="sphere", color=EYE_RIM, scale=0.165, position=(side * 0.155 + ox, 0.575 + oy, -0.315), parent=figure)
    pupils[side] = Entity(model="sphere", color=BLACK, scale=0.122,
                           position=(side * 0.155 + ox, 0.575 + oy, -0.40), parent=figure)

# mustache — black bar + curled tips
Entity(model="cube", color=BLACK, scale=(0.30, 0.05, 0.06), position=(0, 0.415, -0.375), parent=figure)
for side in (-1, 1):
    Entity(model="sphere", color=BLACK, scale=0.055, position=(side * 0.165, 0.432, -0.375), parent=figure)

# wide grinning mouth: dark cavity + gum line + teeth row
mouth_cavity = Entity(model="cube", color=BLACK, scale=(0.26, 0.09, 0.05), position=(0, 0.355, -0.375), parent=figure)
mouth_gum = Entity(model="cube", color=GUM, scale=(0.27, 0.02, 0.055), position=(0, 0.325, -0.375), parent=figure)
teeth = []
for i, tx in enumerate([-0.09, -0.045, 0, 0.045, 0.09]):
    t = Entity(model="cube", color=TOOTH, scale=(0.035, 0.035, 0.02), position=(tx, 0.375, -0.395), parent=figure)
    teeth.append(t)

# ---------------------------------------------------------------------
# TORSO / SHOULDERS / HIPS — rounded, "spuddy"
# ---------------------------------------------------------------------
torso = Entity(model="sphere", color=SHIRT_RED, scale=(0.62, 0.60, 0.5), position=(0, -0.02, 0), parent=figure)
overalls = Entity(model="sphere", color=OVERALLS, scale=(0.64, 0.42, 0.52), position=(0, -0.34, 0), parent=figure)

shoulders = {}
for side in (-1, 1):
    shoulders[side] = Entity(model="sphere", color=SHIRT_RED, scale=0.30, position=(side * 0.42, 0.16, 0), parent=figure)

for side in (-1, 1):
    Entity(model="cube", color=OVERALLS, scale=(0.10, 0.28, 0.06), position=(side * 0.20, 0.04, -0.22),
           rotation=(0, 0, side * -10), parent=figure)
    Entity(model="sphere", color=GLOVE, scale=0.055, position=(side * 0.19, -0.02, -0.27), parent=figure)

# ---------------------------------------------------------------------
# ARMS + long-oval-fingered hands
# ---------------------------------------------------------------------
upper_arms, hands = {}, {}
for side in (-1, 1):
    # Shoulder joint = an unscaled pivot Entity. The upper-arm sphere is
    # one child of it (carrying the visual scale/stretch); forearm, palm
    # and fingers are SIBLING children of that same pivot rather than
    # children of the scaled sphere — otherwise the sphere's non-uniform
    # scale (0.15, 0.27, 0.15) would also scale down their offsets.
    # upper_arms[side] is this pivot, so rotating it (Hunt pose, etc.)
    # correctly carries the whole arm, not just the upper-arm mesh.
    pivot = Entity(parent=figure, position=(side * 0.56, 0.0, 0), rotation=(0, 0, side * 12))
    upper_arms[side] = pivot
    Entity(model="sphere", color=SHIRT_RED, scale=(0.15, 0.27, 0.15), position=(0, 0, 0), parent=pivot)
    forearm = Entity(model="sphere", color=SHIRT_RED, scale=(0.12, 0.20, 0.12),
                      position=(side * 0.07, -0.24, -0.03), parent=pivot)
    palm = Entity(model="sphere", color=GLOVE, scale=0.11, position=(side * 0.10, -0.45, -0.06), parent=pivot)
    finger_offsets = [(-0.05, -0.09, -0.01, 22), (0.0, -0.115, -0.02, 0), (0.05, -0.09, -0.01, -22)]
    finger_list = []
    for fx, fy, fz, rz in finger_offsets:
        f = Entity(model="sphere", color=GLOVE, scale=(0.032, 0.115, 0.032),
                   position=(side * 0.10 + fx, -0.45 + fy, -0.06 + fz),
                   rotation=(0, 0, rz), parent=pivot)
        finger_list.append(f)
    hands[side] = {"forearm": forearm, "palm": palm, "fingers": finger_list}

# ---------------------------------------------------------------------
# LEGS — rounded thigh + shin, no pipe/pedestal underneath
# ---------------------------------------------------------------------
legs = {}
for side in (-1, 1):
    thigh = Entity(model="sphere", color=OVERALLS, scale=(0.24, 0.30, 0.24), position=(side * 0.19, -0.62, 0), parent=figure)
    shin = Entity(model="sphere", color=OVERALLS, scale=(0.18, 0.22, 0.18), position=(side * 0.19, -0.90, -0.02), parent=figure)
    boot = Entity(model="sphere", color=BOOT, scale=(0.20, 0.13, 0.27), position=(side * 0.19, -1.05, -0.07), parent=figure)
    legs[side] = {"thigh": thigh, "shin": shin, "boot": boot}

figure.y += 0.4

# ---------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------
camera.position = (0, 0.3, -4.6)
camera.rotation = (0, 0, 0)
camera.look_at(figure.position + Vec3(0, 0.3, 0))

# ---------------------------------------------------------------------
# Pose state machine
# ---------------------------------------------------------------------
state = {"pose": "idle", "t": 0.0, "auto_spin": True, "corrupted": False}
pose_label = Text(text="MODE: idle", position=window.top_left + Vec2(0.02, -0.03), scale=1.0, color=color.white)
controls_label = Text(
    text="[1] Look behind  [2] Face-Active  [3] Face-Deactive  [4] Hunt   [G] glitch  [Q/E] rotate  [Esc] quit",
    position=window.bottom_left + Vec2(0.02, 0.02), scale=0.7, color=color.white,
)

def _set_mouth(open_amount, eye_scale, eye_color):
    mouth_cavity.animate_scale_y(0.09 * open_amount, duration=0.25)
    mouth_gum.enabled = open_amount > 0.3
    for t in teeth:
        t.enabled = open_amount > 0.3
    for side in (-1, 1):
        pupils[side].animate_scale(eye_scale, duration=0.25)
        pupils[side].animate_color(eye_color, duration=0.25)

def apply_pose(name):
    state["pose"] = name
    state["auto_spin"] = False
    pose_label.text = f"MODE: {name}"

    # reset arm lean each time before applying pose-specific offsets
    for side in (-1, 1):
        upper_arms[side].animate_rotation_x(0, duration=0.3)

    if name == "look_behind":
        figure.animate_rotation_y(180, duration=0.4)
        figure.animate_rotation_x(0, duration=0.3)
        figure.animate_y(0.4, duration=0.3)
        figure.animate_scale(1.0, duration=0.3)
        _set_mouth(1.0, 0.122, BLACK)

    elif name == "face_active":
        figure.animate_rotation_y(0, duration=0.4)
        figure.animate_rotation_x(0, duration=0.3)
        figure.animate_y(0.4, duration=0.3)
        figure.animate_scale(1.0, duration=0.3)
        _set_mouth(1.0, 0.122, BLACK)

    elif name == "face_deactive":
        figure.animate_rotation_y(0, duration=0.4)
        figure.animate_rotation_x(0, duration=0.3)
        figure.animate_y(0.34, duration=0.3)
        figure.animate_scale(1.0, duration=0.3)
        _set_mouth(0.15, 0.09, color.rgb32(30, 30, 30))  # mouth ~shut, pupils dim + small

    elif name == "hunt":
        figure.animate_rotation_y(0, duration=0.25)
        figure.animate_rotation_x(-14, duration=0.25)
        figure.animate_y(0.22, duration=0.25)
        figure.animate_scale(1.06, duration=0.25)
        for side in (-1, 1):
            upper_arms[side].animate_rotation_x(-55, duration=0.25)
        _set_mouth(1.4, 0.16, BLACK)  # wider grin, biggest pupils

def input(key):
    if key in ("1", "2", "3", "4"):
        apply_pose({"1": "look_behind", "2": "face_active", "3": "face_deactive", "4": "hunt"}[key])
    if key == "g":
        state["corrupted"] = not state["corrupted"]
    if key == "q":
        state["auto_spin"] = False
        figure.rotation_y -= 15
    if key == "e":
        state["auto_spin"] = False
        figure.rotation_y += 15

def _walk(entity):
    yield entity
    for c in entity.children:
        yield from _walk(c)

def update():
    state["t"] += time.dt
    figure.y += math.sin(state["t"] * 2.0) * 0.0  # placeholder (bob handled below w/ base offset)
    base_y = 0.4 if state["pose"] in ("idle", "look_behind", "face_active") else figure.y
    if state["auto_spin"]:
        figure.y = 0.4 + math.sin(state["t"] * 2.0) * 0.03
        figure.rotation_y += time.dt * 4

    if state["corrupted"]:
        figure.x = math.sin(state["t"] * 40) * 0.02
        if int(state["t"] * 12) % 2 == 0:
            for e in _walk(figure):
                if getattr(e, "model", None) is not None and random.random() < 0.04:
                    e.color = random.choice(GLITCH_PALETTE)
    else:
        figure.x = 0

print("[5/5] entering main loop", flush=True)
try:
    app.run()
except Exception as e:
    print(f"app.run() raised: {e!r}", file=sys.stderr, flush=True)
    raise
