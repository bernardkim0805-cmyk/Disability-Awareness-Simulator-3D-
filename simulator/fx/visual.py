"""Visual condition simulations. Each class only *contributes* parameters to
the shared PostFX pass (see postfx.py merge rules), so all of them stack.

Color-vision matrices: Machado, Oliveira & Fernandes (2009), "A
Physiologically-based Model for Simulation of Color Vision Deficiency",
IEEE TVCG — severity-1.0 dichromacy matrices, interpolated toward identity
by the intensity slider (their recommended anomalous-trichromacy approach).
"""
import math
import random

from ursina import Entity, Color, camera, destroy

from .core import VisualEffect

IDENTITY = (1, 0, 0, 0, 1, 0, 0, 0, 1)

CVD_MATRICES = {
    'protanopia':   (0.152286, 1.052583, -0.204868,
                     0.114503, 0.786281, 0.099216,
                     -0.003882, -0.048116, 1.051998),
    'deuteranopia': (0.367322, 0.860646, -0.227968,
                     0.280085, 0.672501, 0.047413,
                     -0.011820, 0.042940, 0.968881),
    'tritanopia':   (1.255528, -0.076749, -0.178779,
                     -0.078411, 0.930809, 0.147602,
                     0.004733, 0.691367, 0.303900),
}


class Glaucoma(VisualEffect):
    """Progressive peripheral loss ("tunnel vision") with soft vignette
    edges. Intensity maps to how much of the visual field is gone, so
    threats genuinely approach unseen from the sides."""

    def contribute(self, params):
        params['tunnel'] = max(params['tunnel'], self.intensity * .78)
        params['tunnel_soft'] = .3 - self.intensity * .18   # harder edge late


class MacularDegeneration(VisualEffect):
    """Age-related macular degeneration: a central scotoma with a noise-
    randomized outline (u_scotoma_seed) and preserved periphery. The center
    is rendered as a gray-brown smudge — patients report a smear or void the
    brain fails to fill, not a black disc."""

    def initialize(self):
        super().initialize()
        self.seed = random.uniform(0, 40)   # randomized scotoma shape

    def contribute(self, params):
        params['scotoma'] = max(params['scotoma'], .06 + self.intensity * .3)
        params['scotoma_seed'] = self.seed
        params['blur'] = max(params['blur'], self.intensity * .3)


class Cataracts(VisualEffect):
    """Clouded lens: contrast loss, milky haze, bloom/glare around bright
    light, slight desaturation. All optical (media) effects, so they apply
    uniformly across the field."""

    def contribute(self, params):
        params['contrast'] = min(params['contrast'], 1 - self.intensity * .55)
        params['haze'] = max(params['haze'], self.intensity * .5)
        params['glare'] = max(params['glare'], self.intensity * .9)
        params['desat'] = max(params['desat'], self.intensity * .35)


class FloaterLayer(Entity):
    """CPU-side vitreous floaters: translucent blobs on the UI plane that
    drift slowly and lag behind head turns, the way debris suspended in the
    vitreous humour keeps moving after the eye stops."""

    def __init__(self, count=6, dark=.35, **kwargs):
        super().__init__(parent=camera.ui, **kwargs)
        self.blobs = []
        for _ in range(count):
            b = Entity(parent=self, model='circle',
                       scale=(random.uniform(.01, .05), random.uniform(.03, .09)),
                       position=(random.uniform(-.5, .5), random.uniform(-.4, .4)),
                       rotation_z=random.uniform(0, 180),
                       color=Color(.05, .05, .06, dark))
            b.setLightOff()
            b.vel = (random.uniform(-.004, .004), random.uniform(-.006, .002))
            self.blobs.append(b)
        self.last_cam_rot = camera.world_rotation_y

    def update(self):
        from ursina import time as utime
        # inertia: when the view turns, floaters swing the opposite way first
        swing = (camera.world_rotation_y - self.last_cam_rot) * .01
        self.last_cam_rot = camera.world_rotation_y
        for b in self.blobs:
            b.x += b.vel[0] * utime.dt * 10 - swing
            b.y += b.vel[1] * utime.dt * 10
            if abs(b.x) > .55:
                b.x = -.5 * (1 if b.x > 0 else -1)
            if abs(b.y) > .45:
                b.y = -.4 * (1 if b.y > 0 else -1)


class DiabeticRetinopathy(VisualEffect):
    """Scattered dark patches (retinal hemorrhage/ischemia), drifting
    vitreous floaters, blur regions, and slow fluctuation of acuity over
    time (blood-sugar swings measurably shift refraction)."""

    def initialize(self):
        super().initialize()
        self.seed = random.uniform(0, 40)
        self.t = 0
        self.floaters = FloaterLayer(count=5)

    def update(self, dt):
        self.t += dt

    def contribute(self, params):
        params['patches'] = max(params['patches'], self.intensity * .85)
        params['patch_seed'] = self.seed
        # acuity drifts on a slow ~20 s cycle
        fluct = .5 + .5 * math.sin(self.t * .3)
        params['blur'] = max(params['blur'], self.intensity * (.3 + .5 * fluct))

    def cleanup(self):
        if self.initialized:
            destroy(self.floaters)
        super().cleanup()


class RetinitisPigmentosa(VisualEffect):
    """Rod-first degeneration: constricting tunnel plus night blindness.
    The darkness term makes dim scenes (the zombie street) near-impossible
    while lit rooms stay workable — matching the lived asymmetry."""

    def contribute(self, params):
        params['tunnel'] = max(params['tunnel'], .15 + self.intensity * .6)
        params['tunnel_soft'] = .18
        params['dark'] = max(params['dark'], self.intensity * .55)


class ColorVisionDeficiency(VisualEffect):
    """Dichromacy via the Machado (2009) matrices; the intensity slider
    interpolates identity -> full dichromat, approximating anomalous
    trichromacy at partial settings."""

    variant = 'deuteranopia'

    def contribute(self, params):
        m = CVD_MATRICES[self.variant]
        t = self.intensity
        params['cvd_mat'] = tuple(IDENTITY[i] * (1 - t) + m[i] * t for i in range(9))


class Protanopia(ColorVisionDeficiency):
    variant = 'protanopia'


class Deuteranopia(ColorVisionDeficiency):
    variant = 'deuteranopia'


class Tritanopia(ColorVisionDeficiency):
    variant = 'tritanopia'


class VisualSnow(VisualEffect):
    """Visual snow syndrome: persistent film-grain static, high-frequency
    flicker, mild photophobia (glare boost), floaters, and — as a nod to the
    blue-field entoptic phenomenon — a few bright specks darting along short
    arcs. Afterimages are approximated by the flicker term (true frame
    feedback isn't available in this single-pass pipeline)."""

    def initialize(self):
        super().initialize()
        self.floaters = FloaterLayer(count=3, dark=.2)
        self.specks = []
        for _ in range(4):                      # blue-field entoptic specks
            s = Entity(parent=camera.ui, model='circle', scale=.004,
                       color=Color(1, 1, 1, .8),
                       position=(random.uniform(-.3, .3), random.uniform(-.3, .3)))
            s.setLightOff()
            s.phase = random.uniform(0, 6.28)
            self.specks.append(s)
        self.t = 0

    def update(self, dt):
        self.t += dt
        for s in self.specks:
            s.phase += dt * 3
            s.x += math.cos(s.phase) * dt * .12
            s.y += math.sin(s.phase * 1.7) * dt * .1
            s.color = Color(1, 1, 1, .5 + .4 * math.sin(s.phase * 5))
            if abs(s.x) > .45 or abs(s.y) > .4:
                s.position = (random.uniform(-.3, .3), random.uniform(-.3, .3))

    def contribute(self, params):
        params['snow'] = max(params['snow'], self.intensity)     # noise slider
        params['flicker'] = max(params['flicker'], self.intensity * .6)
        params['glare'] = max(params['glare'], self.intensity * .4)  # photophobia

    def cleanup(self):
        if self.initialized:
            destroy(self.floaters)
            for s in self.specks:
                destroy(s)
        super().cleanup()


class MigraineAura(VisualEffect):
    """Scintillating scotoma on a ~55 s cycle: a shimmering zigzag arc
    expands from near fixation toward the periphery, with a poorly-defined
    blind region inside it and rolling wave distortion, then clears —
    matching the classic cortical-spreading-depression time course
    (compressed for gameplay)."""

    CYCLE = 55.0

    def initialize(self):
        super().initialize()
        self.t = random.uniform(0, 10)

    def update(self, dt):
        self.t += dt

    def contribute(self, params):
        phase = (self.t % self.CYCLE) / self.CYCLE
        if phase < .7:                          # aura expands for ~70% of cycle
            progress = phase / .7
        else:                                    # then fades out
            progress = max(0.0, 1 - (phase - .7) / .3)
        strength = progress * self.intensity
        params['aura'] = max(params['aura'], strength)
        params['wave'] = max(params['wave'], strength * .8)


class Oscillopsia(VisualEffect):
    """The world appears to bounce (failed gaze stabilization, e.g. after
    vestibular damage): continuous micro-oscillation of the image plus
    motion-blur ghosting, making fine focus genuinely difficult."""

    def contribute(self, params):
        params['osc'] = max(params['osc'], self.intensity)
        params['blur'] = max(params['blur'], self.intensity * .25)
