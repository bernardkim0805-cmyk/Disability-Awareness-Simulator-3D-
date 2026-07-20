"""Walk In My World — a 3D disability-awareness simulator.

Run with:  python3 main.py
"""
from panda3d.core import loadPrcFileData
loadPrcFileData('', 'notify-level-glgsg fatal')  # silence text-shader fallback spam
loadPrcFileData('', 'framebuffer-multisample 1')  # smooth edges (anti-aliasing)
loadPrcFileData('', 'multisamples 4')             # 8x fails to open a window here

from pathlib import Path
import sys

from ursina import Ursina, window, Color, Entity, Sky, application
from simulator.windowing import (
    requested_effects,
    requested_experience,
    requested_capture,
    requested_scenario,
    requested_window_size,
)

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

try:
    app = Ursina(title='Walk In My World — Disability Awareness Simulator',
                 development_mode=False)
except Exception:
    # some GPUs refuse a multisampled window — retry without anti-aliasing
    loadPrcFileData('', 'framebuffer-multisample 0')
    loadPrcFileData('', 'multisamples 0')
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

# ---------------------------------------------------------------------------
# Crash resilience. Ursina's frame loop runs every entity's update() and every
# scheduled invoke()/animate() callback with NO exception handling, so a single
# throw — most often a delayed callback firing after its scenario was destroyed
# — kills the whole process ("random shutdown"). A shipping game contains that:
# these two guards log the error and skip the offending call for one frame
# instead of tearing down the app.
# ---------------------------------------------------------------------------
import traceback as _tb
from ursina.sequence import Func as _Func

_orig_func_call = _Func.__call__
def _safe_func_call(self):
    try:
        return _orig_func_call(self)
    except Exception:
        _tb.print_exc()          # a stray invoke/animate callback — contained
        return None
_Func.__call__ = _safe_func_call

from direct.task.Task import Task as _Task

_orig_update = app._update
def _safe_update(task=None):
    try:
        return _orig_update(task)
    except Exception:
        _tb.print_exc()          # a bad entity.update() — skip this frame, keep running
        return _Task.cont
# replace ursina's already-registered 'update' task with the guarded one
app.taskMgr.remove('update')
app._update_task = app.taskMgr.add(_safe_update, 'update')


if size := requested_window_size(sys.argv[1:]):
    window.size = size

from simulator.config import DISABILITIES, SCENARIOS, STATE
from simulator.fx.registry import EFFECTS
from simulator.menu import MainMenu, _scenario_class

scenario_override = requested_scenario(sys.argv[1:], set(SCENARIOS))
experience_override = requested_experience(sys.argv[1:], set(DISABILITIES))
if experience_override:
    STATE.disability = experience_override
STATE.lab_effects = requested_effects(sys.argv[1:], set(EFFECTS))
STATE.lab_split = '--split' in sys.argv[1:]
if '--lab-demo' in sys.argv[1:]:
    from simulator.lab_demo import LabExperienceDemo
    LabExperienceDemo()
elif scenario_override:
    STATE.scenario = scenario_override
    _scenario_class(scenario_override)()
else:
    menu = MainMenu()
    if '--open-lab' in sys.argv[1:]:
        from ursina import invoke
        invoke(menu.open_lab, delay=.2)

capture_path = requested_capture(sys.argv[1:])
if capture_path:
    from panda3d.core import Filename
    from ursina import invoke

    def capture_and_quit():
        app.win.saveScreenshot(Filename.fromOsSpecific(capture_path))
        invoke(application.quit, delay=.2)

    invoke(capture_and_quit, delay=1.0)

app.run()
