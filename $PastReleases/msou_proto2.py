"""
M.SOU / FRIENDLY PLUMBER — desktop model prototype
----------------------------------------------------
Procedurally-built low-poly figure using only primitive shapes
(spheres, cylinders, cubes) — no imported meshes or textures.
Built with Ursina (github.com/pokepetter/ursina), which wraps Panda3D.

Controls:
  G      - toggle "corruption" glitch state
  Q / E  - rotate camera left / right
  Esc    - quit

Run:
  pip install ursina
  python msou_prototype.py
"""

"""
Windows 10/11 variant.

The most common cause of a silent hang on Windows with no window ever
appearing is Panda3D failing to negotiate a hardware OpenGL context
(bad/old GPU driver, remote desktop session, some VM/RDP setups) and
sitting there instead of raising. This variant prints a step-by-step
trace to the console so a hang tells you exactly where it's stuck,
and forces explicit windowed settings that are known-safe on Win10/11
(no borderless, no fullscreen, fixed size/position, vsync off).

If it STILL hangs with no window and no error after "creating window":
  - your GPU driver can't give Panda3D a context. Try:
      pip install --upgrade panda3d
    or update your GPU driver, or run on a machine with a real GPU
    (not a bare VM / some remote desktop sessions have no GL driver).
"""

import sys
print("[1/5] importing ursina...", flush=True)
from ursina import *
from ursina.models.procedural.cylinder import Cylinder
import random
print("[2/5] ursina imported OK", flush=True)

print("[3/5] creating window...", flush=True)
app = Ursina(
    borderless=False,     # bordered window — avoids Windows off-screen/undecorated weirdness
    fullscreen=False,
    vsync=False,          # some Windows GPU drivers stall on vsync in a fresh context
    title="FRIENDLY PLUMBER",
    development_mode=True,
)
window.position = Vec2(100, 100)   # force on-screen, in case it ever opens off your visible desktop
window.size = Vec2(1024, 768)
window.always_on_top = False
window.exit_button.visible = True
window.fps_counter.enabled = True   # if you see this update, the render loop IS running
print("[4/5] window created OK — if no window is visible, alt-tab or check other monitors now", flush=True)

# Ursina ships no baked 'cylinder.ursinamesh' — it's a procedural mesh class.
# Build one shared low-poly (6-sided) cylinder mesh, centered on its own
# origin like the built-in cube/sphere, and reuse it via model=cyl_mesh.
cyl_mesh = Cylinder(6, start=-0.5, height=1)

window.color = color.black
window.fullscreen = False

# ---------------------------------------------------------------------
# Palette — deliberately off, slightly too-saturated / too-dark, to read
# as a corrupted late-90s render rather than a clean modern one.
# ---------------------------------------------------------------------
SKIN      = color.rgb(214, 178, 96)    # sallow yellow-tan
CAP_RED   = color.rgb(196, 30, 24)
SHIRT_RED = color.rgb(178, 24, 20)
OVERALLS  = color.rgb(214, 110, 20)    # burnt orange
GLOVE     = color.rgb(232, 214, 96)
BOOT      = color.rgb(150, 20, 16)
EYE_RED   = color.rgb(120, 10, 10)
PUPIL     = color.black
MUSTACHE  = color.rgb(10, 8, 8)
PEDESTAL_GREEN = color.rgb(70, 170, 40)
BENCH_BROWN = color.rgb(35, 25, 20)

GLITCH_PALETTE = [
    color.rgb(255, 0, 40),
    color.rgb(0, 255, 120),
    color.rgb(255, 255, 0),
    color.rgb(120, 0, 255),
]

# ---------------------------------------------------------------------
# Root entity — everything else is parented to this so idle-bob and
# glitch-jitter only need to move / recolor one hierarchy.
# ---------------------------------------------------------------------
figure = Entity()

# --- pedestal (green cylinder, from reference) ---
pedestal = Entity(
    model=cyl_mesh,
    color=PEDESTAL_GREEN,
    scale=(2.2, 0.6, 2.2),
    position=(0, -1.4, 0),
    parent=figure,
)

# --- bench behind the figure (blocky, low-poly) ---
bench = Entity(parent=figure, position=(0, -0.6, -0.35))
Entity(model="cube", color=BENCH_BROWN, scale=(1.6, 0.08, 0.4), position=(0, 0.4, 0), parent=bench)
Entity(model="cube", color=BENCH_BROWN, scale=(0.1, 0.4, 0.1), position=(-0.65, 0.15, 0), parent=bench)
Entity(model="cube", color=BENCH_BROWN, scale=(0.1, 0.4, 0.1), position=(0.65, 0.15, 0), parent=bench)

# --- torso ---
torso = Entity(
    model=cyl_mesh,
    color=SHIRT_RED,
    scale=(0.6, 0.65, 0.5),
    position=(0, -0.05, 0),
    parent=figure,
)

# overalls (lower torso, slightly wider, orange, overlapping torso)
overalls = Entity(
    model=cyl_mesh,
    color=OVERALLS,
    scale=(0.62, 0.4, 0.52),
    position=(0, -0.35, 0),
    parent=figure,
)
# overall straps (thin boxes over the shoulders)
Entity(model="cube", color=OVERALLS, scale=(0.12, 0.35, 0.08), position=(-0.2, 0.15, 0.22), rotation=(0, 0, 8), parent=figure)
Entity(model="cube", color=OVERALLS, scale=(0.12, 0.35, 0.08), position=(0.2, 0.15, 0.22), rotation=(0, 0, -8), parent=figure)
# overall buttons
Entity(model="sphere", color=GLOVE, scale=0.06, position=(-0.2, -0.02, 0.26), parent=figure)
Entity(model="sphere", color=GLOVE, scale=0.06, position=(0.2, -0.02, 0.26), parent=figure)

# --- head ---
head = Entity(
    model="sphere",
    color=SKIN,
    scale=0.42,
    position=(0, 0.55, 0),
    parent=figure,
)

# cap — dome + brim, sitting slightly too high (off-model)
cap_dome = Entity(model="sphere", color=CAP_RED, scale=(0.46, 0.32, 0.46), position=(0, 0.78, 0), parent=figure)
cap_brim = Entity(model=cyl_mesh, color=CAP_RED, scale=(0.5, 0.03, 0.36), position=(0, 0.66, 0.12), parent=figure)

# eyes — oversized red-ringed sockets with tiny black pupils (reference: unsettling, too-wide stare)
for side in (-1, 1):
    Entity(model="sphere", color=EYE_RED, scale=0.14, position=(side * 0.15, 0.58, 0.34), parent=figure)
    Entity(model="sphere", color=PUPIL, scale=0.05, position=(side * 0.15, 0.58, 0.41), parent=figure)

# mustache — flattened dark blob, nutcracker-ish jaw implied by its width
mustache = Entity(
    model="cube",
    color=MUSTACHE,
    scale=(0.34, 0.07, 0.05),
    position=(0, 0.42, 0.37),
    parent=figure,
)

# --- arms ---
for side in (-1, 1):
    upper_arm = Entity(
        model=cyl_mesh,
        color=SHIRT_RED,
        scale=(0.14, 0.35, 0.14),
        position=(side * 0.42, 0.05, 0),
        rotation=(0, 0, side * -20),
        parent=figure,
    )
    glove = Entity(
        model="sphere",
        color=GLOVE,
        scale=0.16,
        position=(side * 0.6, -0.25, 0),
        parent=figure,
    )

# --- legs ---
for side in (-1, 1):
    leg = Entity(
        model=cyl_mesh,
        color=OVERALLS,
        scale=(0.18, 0.45, 0.18),
        position=(side * 0.18, -0.75, 0),
        parent=figure,
    )
    boot = Entity(
        model=cyl_mesh,
        color=BOOT,
        scale=(0.2, 0.12, 0.28),
        position=(side * 0.18, -1.0, 0.05),
        parent=figure,
    )

figure.y += 0.4  # lift whole rig above pedestal top

# ---------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------
camera.position = (0, 0.3, -4.2)
camera.rotation = (0, 0, 0)
camera.look_at(figure.position + Vec3(0, 0.3, 0))

# ---------------------------------------------------------------------
# State
# ---------------------------------------------------------------------
state = {"corrupted": False, "t": 0.0}

all_parts = figure.children  # top-level; nested children walked in glitch()

def _walk(entity):
    yield entity
    for c in entity.children:
        yield from _walk(c)

def input(key):
    if key == "g":
        state["corrupted"] = not state["corrupted"]
    if key == "q":
        figure.rotation_y -= 15
    if key == "e":
        figure.rotation_y += 15

def update():
    state["t"] += time.dt

    # idle bob — small vertical sine sway, subtle enough to feel "alive"
    figure.y = 0.4 + math.sin(state["t"] * 2.0) * 0.03
    figure.rotation_y += time.dt * 4  # slow constant turntable spin

    if state["corrupted"]:
        # jitter position slightly + randomly recolor parts to a glitch palette
        figure.x = math.sin(state["t"] * 40) * 0.02
        if int(state["t"] * 12) % 2 == 0:
            for e in _walk(figure):
                if hasattr(e, "model") and e.model is not None and random.random() < 0.05:
                    e.color = random.choice(GLITCH_PALETTE)
    else:
        figure.x = 0

info = Text(
    text="[G] glitch   [Q/E] rotate   [Esc] quit",
    position=window.bottom_left + Vec2(0.02, 0.02),
    scale=0.8,
    color=color.white,
)

print("[5/5] entering main loop — a window should be visible now", flush=True)
try:
    app.run()
except Exception as e:
    print(f"app.run() raised: {e!r}", file=sys.stderr, flush=True)
    raise
print("app closed normally", flush=True)
