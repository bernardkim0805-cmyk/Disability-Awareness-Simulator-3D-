"""Traffic AI: cars that follow lanes and lights, keep spacing and brake for
pedestrians — plus a small risky percentage (sudden stops, swerves,
speeding) to reproduce the unpredictability of real streets. Also: a
cyclist in the bike lane, a bus that services the stop, an ambulance event,
and pedestrians (one of whom crosses unexpectedly at the school).
"""
import random

from ursina import Entity, Color, Vec3, time as utime, destroy

from ..npc import NPC
from .city import B, ROAD_W

CAR_COLORS = [Color(.7, .2, .2, 1), Color(.2, .3, .6, 1), Color(.8, .8, .82, 1),
              Color(.2, .2, .22, 1), Color(.6, .55, .2, 1), Color(.4, .45, .5, 1)]


def _car_body(root, color, emergency=False):
    Entity(parent=root, model='cube', position=(0, .55, 0), scale=(1.9, .7, 4.1),
           color=color)
    Entity(parent=root, model='cube', position=(0, 1.1, -.2), scale=(1.7, .55, 2.2),
           color=Color(color.x * .8, color.y * .8, color.z * .8, 1))
    Entity(parent=root, model='quad', position=(0, 1.15, 1.0), rotation_x=-20,
           scale=(1.5, .5), color=Color(.15, .2, .25, 1))
    for sx in (-.85, .85):
        for sz in (-1.4, 1.4):
            Entity(parent=root, model='sphere', position=(sx, .32, sz),
                   scale=(.22, .5, .5), color=Color(.07, .07, .08, 1))
    brakes = []
    for sx in (-.7, .7):
        b = Entity(parent=root, model='quad', position=(sx, .6, -2.06),
                   rotation_y=180, scale=(.32, .18), color=Color(.35, .05, .05, 1))
        b.setLightOff()
        brakes.append(b)
        h = Entity(parent=root, model='quad', position=(sx, .6, 2.06),
                   scale=(.3, .18), color=Color(.9, .9, .75, 1))
        h.setLightOff()
    if emergency:
        bar = Entity(parent=root, model='cube', position=(0, 1.5, -.2),
                     scale=(1.2, .18, .5), color=Color(.9, .9, .9, 1))
        root.beacons = [Entity(parent=root, model='cube', position=(sx, 1.62, -.2),
                               scale=(.4, .14, .4),
                               color=Color(.9, .1, .1, 1) if sx < 0
                               else Color(.1, .3, .9, 1))
                        for sx in (-.35, .35)]
        for bcn in root.beacons:
            bcn.setLightOff()
    return brakes


class TrafficCar(Entity):
    """Follows a rectangular ring of waypoints, offset to its lane side."""

    def __init__(self, ring, lights, speed=7, risky=False, **kwargs):
        super().__init__(**kwargs)
        self.ring = ring
        self.wp = random.randint(0, len(ring) - 1)
        self.lights = lights
        self.base_speed = speed
        self.risky = risky
        self.risk_timer = random.uniform(6, 16)
        self.risk_mode = None
        self.risk_left = 0
        self.stopped = False
        self.others = []                     # set by scenario
        self.player = None
        self.brakes = _car_body(self, random.choice(CAR_COLORS))
        seg = self._target() - self.position
        self.position = self._target()
        self.wp = (self.wp + 1) % len(self.ring)

    def _target(self):
        wp = Vec3(*self.ring[self.wp])
        nxt = Vec3(*self.ring[(self.wp + 1) % len(self.ring)])
        d = (nxt - wp).normalized()
        right = Vec3(d.z, 0, -d.x)
        return wp + right * 2.6

    def update(self):
        dt = utime.dt
        target = self._target()
        to_t = target - self.position
        to_t.y = 0
        if to_t.length() < 2:
            self.wp = (self.wp + 1) % len(self.ring)
            return
        d = to_t.normalized()
        self.look_at(self.position + d)

        speed = self.base_speed
        # risky drivers misbehave on a timer
        if self.risky:
            self.risk_timer -= dt
            if self.risk_mode is None and self.risk_timer <= 0:
                self.risk_mode = random.choice(['stop', 'speed', 'swerve'])
                self.risk_left = random.uniform(1.5, 3)
            if self.risk_mode:
                self.risk_left -= dt
                if self.risk_mode == 'stop':
                    speed = 0
                elif self.risk_mode == 'speed':
                    speed *= 1.7
                elif self.risk_mode == 'swerve':
                    d = (d + Vec3(d.z, 0, -d.x) * .4).normalized()
                if self.risk_left <= 0:
                    self.risk_mode = None
                    self.risk_timer = random.uniform(8, 18)

        # red lights: stop short of signalized intersections
        axis = 'ew' if abs(d.x) > abs(d.z) else 'ns'
        for sig in self.lights:
            gap = Vec3(sig.world_position - self.position)
            gap.y = 0
            ahead = gap.dot(d)
            if 3 < ahead < 8 and gap.length() < 9 and not sig.green_for(axis):
                speed = 0
        # spacing: never rear-end the car (or player) ahead
        for other in self.others:
            if other is self:
                continue
            gap = other.position - self.position
            gap.y = 0
            if 0 < gap.dot(d) < 6.5 and abs(gap.dot(Vec3(d.z, 0, -d.x))) < 2:
                speed = 0
        if self.player is not None:
            gap = self.player.position - self.position
            gap.y = 0
            if 0 < gap.dot(d) < 7 and abs(gap.dot(Vec3(d.z, 0, -d.x))) < 2.2:
                speed = 0

        self.stopped = speed == 0
        for b in self.brakes:                # brake lights: non-color redundancy
            b.color = Color(1, .15, .1, 1) if self.stopped else Color(.35, .05, .05, 1)
        self.position += d * speed * dt


class Ambulance(TrafficCar):
    """Runs the Main St ring fast with lights; siren volume tracks distance
    (the accessible 'directional audio' pairing is the HUD indicator)."""

    def __init__(self, ring, lights, **kwargs):
        super().__init__(ring, lights, speed=13, risky=False, **kwargs)
        for c in self.children[:]:
            destroy(c)
        self.brakes = _car_body(self, Color(.95, .95, .95, 1), emergency=True)
        self.t = 0
        self.siren = None

    def update(self):
        super().update()
        self.t += utime.dt
        on = int(self.t * 6) % 2 == 0
        for i, bcn in enumerate(getattr(self, 'beacons', [])):
            base = Color(.9, .1, .1, 1) if i == 0 else Color(.1, .3, .9, 1)
            bcn.color = base if on == (i == 0) else Color(.3, .3, .3, 1)
        if self.siren and self.player is not None:
            dist = (self.player.position - self.position).length()
            try:
                self.siren.volume = max(.05, min(.8, 14 / max(6, dist)))
            except Exception:
                pass


class Cyclist(Entity):
    """Rides the bike lane end to end — right through driver blind spots."""

    def __init__(self, x=-B + ROAD_W / 2 - 1, **kwargs):
        super().__init__(position=(x, 0, -B - 10), **kwargs)
        self.rider = NPC(parent=self, name='cyclist', lines=[], speed=0)
        self.rider.marker.enabled = False
        self.rider.hips.y = 1.05
        for fz in (-.5, .5):
            Entity(parent=self, model='sphere', position=(0, .45, fz),
                   scale=(.1, .9, .9), color=Color(.1, .1, .1, 1))
        Entity(parent=self, model='cube', position=(0, .9, 0), scale=(.08, .1, 1.2),
               color=Color(.7, .25, .2, 1))
        self.speed = 5

    def update(self):
        self.z += self.speed * utime.dt
        self.rider.advance(moving=True, speed=3)
        if self.z > B + 30:
            self.z = -B - 20


class Bus(TrafficCar):
    def __init__(self, ring, lights, stop_z, **kwargs):
        super().__init__(ring, lights, speed=6, **kwargs)
        for c in self.children[:]:
            destroy(c)
        Entity(parent=self, model='cube', position=(0, 1.3, 0), scale=(2.3, 2.2, 8),
               color=Color(.85, .6, .15, 1))
        for i in range(5):
            w = Entity(parent=self, model='quad', position=(1.16, 1.7, -3 + i * 1.5),
                       rotation_y=-90, scale=(1.1, .8), color=Color(.65, .8, .9, 1))
            w.setLightOff()
        self.brakes = []
        self.stop_z = stop_z
        self.dwell = 0

    def update(self):
        if self.dwell > 0:
            self.dwell -= utime.dt
            return
        if abs(self.z - self.stop_z) < 1.5 and random.random() < .02:
            self.dwell = 5
        super().update()
