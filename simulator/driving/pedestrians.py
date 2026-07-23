"""Rule-following pedestrian crowd for the driving world.

Each pedestrian is a logical agent that walks the sidewalks and only steps
onto the road at a crossing, after checking the traffic signal (and that the
road is clear) — so they obey the lights for the most part. They can be hit:
a collision knocks them down and severely damages the car.

DETAIL vs PERFORMANCE (honest note): the near pedestrians use the full
articulated classroom rig (`Human`); 450 of those at once (~20k primitives)
would not render on this fixed-function stack, so distant pedestrians fall
back to a cheap two-primitive proxy, swapping as the car moves. You always
see the detailed rig on the people around you.
"""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import math
import random

from ursina import Entity, Color, Vec3, time as utime, distance_xz, destroy

from ..human import Human, SKIN_TONES, SHIRT_COLORS
from .config import WORLD

B = WORLD['downtown_block']
RW = WORLD['road_width']
SIDE = RW / 2 + 2.2                 # sidewalk offset from a road centerline
FULL_RIG_NEAR = 30                  # promote to full Human within this range
FULL_RIG_FAR = 42                   # demote back to proxy beyond this (hysteresis)
MAX_FULL_RIGS = 16                  # hard cap on simultaneous detailed rigs

SHIRTS = list(SHIRT_COLORS)
SKIN = list(SKIN_TONES)


class _Proxy(Entity):
    """Cheap distant pedestrian: body + head, two draws."""
    def __init__(self, shirt, skin, **kwargs):
        super().__init__(**kwargs)
        self.body = Entity(parent=self, model='cube', y=.85,
                           scale=(.42, 1.7, .28), color=shirt)
        Entity(parent=self, model='sphere', y=1.8, scale=.3, color=skin)


class Pedestrian:
    """Logical agent. Owns a swappable visual body and a small state machine:
    WALK along the sidewalk, WAIT at a curb, CROSS the road, DOWN if hit."""

    def __init__(self, road_axis, road_coord, side, rng, crowd):
        self.axis = road_axis          # 'x' or 'z' — the road this walks beside
        self.road = road_coord         # centerline coord of that road
        self.side = side               # +1 / -1 (which sidewalk)
        self.rng = rng
        self.crowd = crowd
        self.speed = rng.uniform(1.2, 2.3)
        self.shirt = rng.choice(SHIRTS)
        self.skin = rng.choice(SKIN)
        self.phase = rng.uniform(0, 6.28)
        self.state = 'WALK'
        self.down_t = 0
        self.body = None
        self.body_kind = None          # 'full' | 'proxy'
        # place along the road within the downtown extent
        self.along = rng.uniform(-B - 30, B + 30)
        self.pos = self._point(self.along, self.side)
        self.target_along = self._new_target()
        self.cross_t = 0

    # -------------------------------------------------------------- geometry
    def _point(self, along, side):
        off = side * SIDE
        if self.axis == 'z':           # road runs along z; sidewalk offset in x
            return Vec3(self.road + off, 0, along)
        return Vec3(along, 0, self.road + off)

    def _new_target(self):
        return self.rng.uniform(-B - 30, B + 30)

    def _at_signal(self):
        """True only when standing at a signal-controlled crossing."""
        return self._nearest_signal() is not None

    def _nearest_signal(self):
        best, bd = None, 8
        for sig in self.crowd.signals:
            d = distance_xz(sig.position, self.pos)
            if d < bd:
                best, bd = sig, d
        return best

    def _road_is_clear(self, span=9):
        """No traffic car within `span` on this road near the crossing."""
        for v in self.crowd.vehicles:
            if v.isEmpty():
                continue
            r = v.position - self.pos
            if abs((r.x if self.axis == 'x' else r.z)) < span \
                    and abs((r.z if self.axis == 'x' else r.x)) < RW:
                return False
        return True

    def _may_cross(self):
        sig = self._nearest_signal()
        if sig is None:
            return False                        # never cross away from a signal
        # cross a z-road when E-W has green (z-traffic stopped); vice-versa
        traffic_stopped = not sig.green_for('ns' if self.axis == 'z' else 'ew')
        return traffic_stopped and self._road_is_clear()

    # ----------------------------------------------------------------- logic
    def tick(self, dt):
        if self.state == 'DOWN':
            self.down_t -= dt
            if self.down_t <= 0:
                self.state = 'WALK'
            return

        if self.state == 'WALK':
            step = self.speed * dt * (1 if self.target_along > self.along else -1)
            self.along += step
            if abs(self.along - self.target_along) < .5:
                self.target_along = self._new_target()
                # only consider crossing at a real signalized intersection,
                # and only occasionally — like a real pedestrian who mostly
                # just walks the sidewalk
                if self._at_signal() and self.rng.random() < .12:
                    self.state = 'WAIT'
                    self.wait_t = 0
            self.pos = self._point(self.along, self.side)

        elif self.state == 'WAIT':
            self.wait_t = getattr(self, 'wait_t', 0) + dt
            if self._may_cross():           # signal stops traffic AND road clear
                self.state = 'CROSS'
                self.cross_t = 0
            elif self.wait_t > 25:          # patience runs out -> stay put, walk on
                self.state = 'WALK'

        elif self.state == 'CROSS':
            self.cross_t += dt
            # slide perpendicular from this curb to the opposite one
            t = min(1, self.cross_t / (RW / self.speed + .8))
            here = self.side * SIDE
            there = -self.side * SIDE
            off = here + (there - here) * t
            if self.axis == 'z':
                self.pos = Vec3(self.road + off, 0, self.along)
            else:
                self.pos = Vec3(self.along + off if False else self.along, 0,
                                self.road + off)
            if t >= 1:
                self.side = -self.side
                self.state = 'WALK'

        # keep the (possibly rig) body in sync
        if self.body is not None and not self.body.isEmpty():
            self.body.position = self.pos
            moving = self.state in ('WALK', 'CROSS')
            self._face_travel()
            if self.body_kind == 'full':
                self.body.advance(moving=moving, speed=max(2.2, self.speed))
            elif moving:
                self.phase += dt * self.speed * 3
                self.body.body.y = .85 + abs(math.sin(self.phase)) * .05

    def _face_travel(self):
        if self.state == 'CROSS':
            # face across the road
            self.body.rotation_y = 90 if self.axis == 'z' else 0
        else:
            self.body.rotation_y = (0 if self.target_along > self.along else 180) \
                if self.axis == 'z' else (90 if self.target_along > self.along else 270)

    def knock_down(self, from_pos):
        self.state = 'DOWN'
        self.down_t = 3.0
        if self.body is not None and not self.body.isEmpty():
            self.body.rotation_x = 88          # crumple to the ground
            self.body.y = 0
            if self.body_kind == 'full':
                self.body.set_expression('scared')

    # ------------------------------------------------------------------- LOD
    def set_body(self, kind):
        if kind == self.body_kind:
            return
        if self.body is not None and not self.body.isEmpty():
            destroy(self.body)
            self.body = None
        if kind == 'full':
            self.body = Human(parent=self.crowd, position=self.pos,
                              shirt=self.shirt, skin=self.skin)
        elif kind == 'proxy':
            self.body = _Proxy(self.shirt, self.skin, parent=self.crowd,
                               position=self.pos)
        self.body_kind = kind
        if self.body is not None:
            self.body.rotation_x = 88 if self.state == 'DOWN' else 0


class PedestrianCrowd(Entity):
    def __init__(self, scenario, count=450, seed=7, **kwargs):
        super().__init__(**kwargs)
        self.s = scenario
        self.signals = scenario.places.get('lights', [])
        self.rng = random.Random(seed)
        self.peds = []
        self._spawn(count)

    @property
    def vehicles(self):
        return self.s.vehicles

    def _spawn(self, count):
        roads = [('z', -B), ('z', 0), ('z', B), ('x', -B), ('x', 0), ('x', B)]
        for _ in range(count):
            axis, coord = self.rng.choice(roads)
            side = self.rng.choice((-1, 1))
            self.peds.append(Pedestrian(axis, coord, side, self.rng, self))

    def update(self):
        car = self.s.car
        if car.isEmpty():
            return
        cp = car.position
        # LOD: promote nearest peds to the full rig (capped), proxy the rest
        near = []
        for ped in self.peds:
            d2 = (ped.pos.x - cp.x) ** 2 + (ped.pos.z - cp.z) ** 2
            if d2 < 90 * 90:
                near.append((d2, ped))
        near.sort(key=lambda t: t[0])
        full_ids = set()
        for i, (d2, ped) in enumerate(near):
            d = d2 ** .5
            if i < MAX_FULL_RIGS and d < FULL_RIG_NEAR:
                ped.set_body('full'); full_ids.add(id(ped))
            elif d < FULL_RIG_FAR and ped.body_kind == 'full' \
                    and id(ped) not in full_ids and i < MAX_FULL_RIGS:
                full_ids.add(id(ped))   # hysteresis: keep full a bit longer
            elif d < 90:
                ped.set_body('proxy')
        # ticks: only nearby peds run their logic each frame (LOD)
        dt = utime.dt
        for d2, ped in near:
            ped.tick(dt)
        # far peds shed their body to save draws
        for ped in self.peds:
            if (ped.pos.x - cp.x) ** 2 + (ped.pos.z - cp.z) ** 2 >= 90 * 90 \
                    and ped.body is not None:
                destroy(ped.body); ped.body = None; ped.body_kind = None

    def check_car_collision(self, car):
        """Return a pedestrian the car is currently hitting (and knock it
        down), else None."""
        cp = car.position
        for ped in self.peds:
            if ped.state == 'DOWN':
                continue
            if abs(ped.pos.x - cp.x) < 1.5 and abs(ped.pos.z - cp.z) < 2.2:
                ped.knock_down(cp)
                return ped
        return None

    def react(self, position, radius=16):
        for ped in self.peds:
            if ped.state in ('WALK',) and distance_xz(ped.pos, position) < radius:
                ped.state = 'WALK'
                ped.target_along = ped.along + (ped.rng.choice((-20, 20)))

    def on_destroy(self):
        for ped in self.peds:
            if ped.body is not None and not ped.body.isEmpty():
                destroy(ped.body)
        self.peds.clear()
