"""Walk In My World — a 3D disability-awareness simulator.

Run with:  python3 main.py
"""
from panda3d.core import loadPrcFileData
loadPrcFileData('', 'notify-level-glgsg fatal')  # silence text-shader fallback spam
loadPrcFileData('', 'framebuffer-multisample 1')  # smooth edges (anti-aliasing)
loadPrcFileData('', 'multisamples 4')             # 8x fails to open a window here

from pathlib import Path

from ursina import Ursina, window, Color, Entity, Sky, application

application.asset_folder = Path(__file__).resolve().parent  # assets work from any cwd

# ---------------------------------------------------------------------------
# macOS compatibility: this Mac's OpenGL can't compile ursina's GLSL 130/140
# shaders, and geometry carrying a failed shader draws nothing at all.
# Fixed-function rendering handles everything this game uses (vertex colors,
# textures, fog, transparency), so entity shaders are dropped entirely.
# ---------------------------------------------------------------------------
Entity.shader = property(lambda self: getattr(self, '_shader', None),
                         lambda self, value: setattr(self, '_shader', None))
Sky.default_values = dict(Sky.default_values, shader=None)

app = Ursina(title='Walk In My World — Disability Awareness Simulator',
             development_mode=False)

# entities created during ursina's own import already had shaders applied —
# strip those so they render through the fixed-function pipeline too
from ursina import camera
for _root in (app.render, app.render2d, camera.ui):
    for _np in [_root] + list(_root.findAllMatches('**')):
        _np.clearShader()

# ursina attaches a linear black fog to the scene that only its shaders ignore;
# in fixed-function rendering it fogs every 3D object to solid black
from ursina import scene
scene.clearFog()

from panda3d.core import AntialiasAttrib
app.render.setAntialias(AntialiasAttrib.MMultisample)

window.color = Color(0.04, 0.05, 0.09, 1)
window.fps_counter.enabled = False
window.exit_button.visible = False
window.cog_button.visible = False

from simulator.menu import MainMenu
MainMenu()

app.run()
