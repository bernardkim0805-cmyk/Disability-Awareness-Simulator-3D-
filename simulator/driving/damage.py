"""VehicleDamageSystem: progressive, driver-visible damage.

Honest scope: this is NOT crumple-zone / soft-body simulation (that needs a
physics engine wired to deformable meshes). It's a staged visual + handling
model that reads from the driver's seat — cracked windshield overlay, smoke
rising over the hood, a steering pull from knocked alignment, and top-speed
loss — driven by impact severity from config.DAMAGE.
"""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import random

from ursina import Entity, Color, camera, time as utime, destroy

from .config import DAMAGE


class VehicleDamageSystem:
    def __init__(self, car):
        self.car = car
        self.cfg = DAMAGE
        self.points = 0
        self.pull = 0.0                 # steering-alignment drift
        self.smoke = []
        self._smoke_t = 0
        # first-person damage overlays on the windshield (camera.ui via car.gui)
        gui = car.gui
        self.cracks = []
        for _ in range(5):
            c = Entity(parent=gui, model='quad', enabled=False,
                       position=(random.uniform(-.35, .35), random.uniform(-.05, .3)),
                       rotation_z=random.uniform(0, 180),
                       scale=(random.uniform(.004, .008), random.uniform(.06, .18)),
                       color=Color(.85, .9, .95, .55))
            c.setLightOff()
            self.cracks.append(c)

    def impact(self, speed, severe=False):
        """Register a collision. Returns the resulting damage tier string."""
        if speed < self.cfg['minor_impact'] and not severe:
            return 'scratch'
        add = 2 if (severe or speed > self.cfg['major_impact']) else 1
        self.points += add
        # knock the alignment to one side, and reveal a crack
        self.pull += random.choice((-1, 1)) * self.cfg['steering_pull_per_point'] * add
        for c in self.cracks[:self.points]:
            c.enabled = True
        return 'major' if add == 2 else 'minor'

    @property
    def totaled(self):
        return self.points >= self.cfg['undriveable']

    def update(self, dt):
        car = self.car
        # steering pull: alignment drift the driver must correct against
        if abs(self.pull) > .001 and abs(car.speed) > 1:
            car.rotation_y += self.pull * abs(car.speed) * dt * 4
        # top-speed loss
        penalty = 1 - min(.7, self.points * self.cfg['speed_loss_per_point'])
        car.MAX_SPEED = 16 * penalty
        # hood smoke once damaged enough
        if self.points >= self.cfg['smoke_threshold']:
            self._smoke_t -= dt
            if self._smoke_t <= 0:
                self._smoke_t = .15
                self._emit_smoke()
        for s in self.smoke[:]:
            s.y += dt * .12
            s.scale *= 1 + dt * .6
            s.color = Color(.3, .3, .3, max(0, s.color.a - dt * .5))
            if s.color.a <= 0:
                self.smoke.remove(s)
                destroy(s)

    def _emit_smoke(self):
        # smoke puffs rising over the hood, seen through the windshield
        s = Entity(parent=camera.ui, model='circle',
                   position=(random.uniform(-.1, .1), random.uniform(-.05, .05)),
                   scale=random.uniform(.05, .1),
                   color=Color(.35, .35, .37, .5))
        s.setLightOff()
        self.smoke.append(s)

    def cleanup(self):
        for s in self.smoke:
            destroy(s)
        self.smoke.clear()
