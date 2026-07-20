"""Scenario: night city maze — reach the safehouse through twisting alleys.

A generated maze of dark city blocks (recursive backtracker, plus a few
knocked-through walls so there are loops, not one solution). You can pick a
stick up off the ground: it takes 20% health per hit off a normal zombie
but only 5% off the fast dark ones — those you outmaneuver, not outfight,
because they steer with momentum and overshoot sharp turns. Rubble patches
can trip you: 3 seconds on the ground, 5 in a wheelchair.
"""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import math
import random

from ursina import (Entity, Text, Color, Vec3, camera, time as utime,
                    distance_xz, destroy, invoke)

from .base_scenario import BaseScenario
from .config import STATE
from .npc import NPC

CELL = 7                    # corridor width
WALL_H = 5
COLS, ROWS = 9, 11          # maze size (odd numbers work nicely)


# --------------------------------------------------------------------- maze
def generate_maze(cols, rows, extra_openings=6, rng=None):
    """Recursive backtracker. Returns set of open edges ((c1,r1),(c2,r2))."""
    rng = rng or random.Random()
    open_edges = set()
    visited = {(0, 0)}
    stack = [(0, 0)]
    while stack:
        c, r = stack[-1]
        options = [(c + dc, r + dr) for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))
                   if 0 <= c + dc < cols and 0 <= r + dr < rows
                   and (c + dc, r + dr) not in visited]
        if not options:
            stack.pop()
            continue
        nxt = rng.choice(options)
        open_edges.add(frozenset(((c, r), nxt)))
        visited.add(nxt)
        stack.append(nxt)
    # loops: knock a few extra walls through so there is more than one path
    for _ in range(extra_openings):
        c, r = rng.randint(0, cols - 2), rng.randint(0, rows - 2)
        nxt = rng.choice([(c + 1, r), (c, r + 1)])
        open_edges.add(frozenset(((c, r), nxt)))
    return open_edges


# ------------------------------------------------------------------ zombies
class Zombie(NPC):
    speed = 2.5
    stick_damage = 20
    turn_limit = 240            # degrees/second of steering

    def __init__(self, **kwargs):
        super().__init__(name='???', hunched=True,
                         skin=Color(.5, .6, .45, 1), shirt=Color(.28, .34, .24, 1),
                         pants=Color(.22, .22, .18, 1), hair=Color(.12, .14, .1, 1),
                         **kwargs)
        gore = Color(.35, .08, .06, 1)
        rot = Color(.22, .28, .16, 1)
        for side in (-.05, .05):                         # glowing red eyes
            eye = Entity(parent=self.head, model='sphere', scale=.055,
                         position=(side, .025, .1), color=Color(1, .15, .1, 1))
            eye.setLightOff()
        self.set_expression('angry')
        self.mouth_open_hole.scale = (.05, .055, .012)   # permanently gaping jaw
        self.mouth_open_hole.y = -.095
        self.teeth.scale = (.042, .012, .008)
        self.teeth.color = Color(.75, .7, .55, 1)
        self.lower_lip.y = -.128
        self.head.rotation_z = random.choice([-22, 17, 28])
        for _ in range(4):                               # rotting patches
            Entity(parent=self.head, model='sphere', color=rot,
                   scale=random.uniform(.03, .06),
                   position=(random.uniform(-.09, .09), random.uniform(-.06, .08),
                             .07 + random.uniform(0, .03)))
        for _ in range(3):                               # blood down the shirt
            Entity(parent=self.torso, model='cube', color=gore,
                   position=(random.uniform(-.12, .12), random.uniform(.15, .5), .105),
                   rotation_z=random.uniform(-30, 30),
                   scale=(random.uniform(.05, .1), random.uniform(.1, .28), .015))
        if random.random() < .4:                         # missing forearm
            arm = self.arms[random.choice(('l', 'r'))]
            arm[1].enabled = False
            Entity(parent=arm[0], model='sphere', color=gore, y=-.31,
                   scale=(.09, .05, .09))
        self.twitch_timer = random.uniform(1.5, 4)
        self.base_head_tilt = self.head.rotation_z
        self.marker.enabled = False
        self.lines = []
        self.health = 100
        self.dead = False
        self.heading = Vec3(0, 0, 1)
        self.hp_bar = Entity(parent=self, model='quad', y=2.1, scale=(.8, .07),
                             color=Color(.8, .15, .1, 1), billboard=True,
                             enabled=False)
        self.hp_bar.setLightOff()

    def update(self):
        if self.dead:
            return
        super().update()
        self.twitch_timer -= utime.dt
        if self.twitch_timer <= 0:
            self.twitch_timer = random.uniform(1.5, 4)
            self.head.rotation_z = self.base_head_tilt + random.uniform(-25, 25)
        self.head.rotation_z += (self.base_head_tilt - self.head.rotation_z) * 2 * utime.dt

    def chase(self, target_pos, dt):
        """Steer toward the target with a limited turn rate — fast zombies
        overshoot sharp corners, which is exactly how you escape them."""
        if self.dead:
            return
        desired = target_pos - self.position
        desired.y = 0
        if desired.length() < .05:
            return
        desired = desired.normalized()
        cur = math.degrees(math.atan2(self.heading.x, self.heading.z))
        want = math.degrees(math.atan2(desired.x, desired.z))
        diff = (want - cur + 180) % 360 - 180
        step = max(-self.turn_limit * dt, min(self.turn_limit * dt, diff))
        ang = math.radians(cur + step)
        self.heading = Vec3(math.sin(ang), 0, math.cos(ang))
        self.position += self.heading * self.speed * dt
        self.look_at(self.position + self.heading)
        self.walking = True

    def hit(self, damage):
        if self.dead:
            return False
        self.health -= damage
        self.hp_bar.enabled = True
        self.hp_bar.scale_x = .8 * max(0, self.health) / 100
        for part in (self.torso,):
            part.rotation_x += 12                       # recoil
        if self.health <= 0:
            self.dead = True
            self.animate('rotation_x', 90, duration=.4)
            self.animate('y', -.4, duration=.4)
            destroy(self, delay=3)
            return True
        return False


class FastZombie(Zombie):
    """Darker, faster, barely hurt by the stick — evade, don't fight."""
    speed = 5.4
    stick_damage = 5
    turn_limit = 110            # momentum: it cannot corner like you can

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._darken(self)          # near-black all over: hard to see at night

    def _darken(self, ent):
        for child in ent.children:
            try:
                c = child.color
                child.color = Color(c.x * .28, c.y * .3, c.z * .28, c.w)
            except Exception:
                pass
            self._darken(child)
        # keep the eyes burning
        for side_eye in self.head.children:
            if side_eye.color and side_eye.color.x > .9:
                side_eye.color = Color(1, .15, .1, 1)


# ----------------------------------------------------------------- scenario
class ZombieEscapeScenario(BaseScenario):
    player_start = (0, 0, 0)    # replaced in build
    sky_color = Color(.03, .03, .08, 1)

    def build(self):
        from . import world
        from .kitchen.sounds import ensure_kitchen_assets
        ensure_kitchen_assets()          # reuses the chop THWACK for stick hits
        # brighter-than-usual night: the maze must be readable
        self.lights = world.SceneLights(ambient=(.3, .3, .4),
                                        sun=(.4, .42, .55), sun_hpr=(-60, -40, 0))
        world.night_sky(self)

        rng = random.Random()
        self.edges = generate_maze(COLS, ROWS, rng=rng)
        self.origin = Vec3(-(COLS - 1) * CELL / 2, 0, -20)

        total_w = COLS * CELL
        total_d = ROWS * CELL
        self.make_box((0, -.5, self.origin.z + total_d / 2 - CELL / 2),
                      (total_w + 30, 1, total_d + 60), Color(.13, .13, .16, 1))

        self._build_maze_walls()
        self._place_props(rng)

        # start position: south entrance
        start = self.cell_pos(COLS // 2, 0)
        self.player.position = Vec3(start.x, 0, start.z - CELL)
        # safehouse beyond the north exit
        exit_cell = self.cell_pos(COLS // 2, ROWS - 1)
        sh = Vec3(exit_cell.x, 0, exit_cell.z + CELL + 5)
        house = self.make_box((sh.x, 3, sh.z + 4), (14, 6, 8), Color(.4, .36, .34, 1))
        house.texture = 'brick'
        self.door = Entity(parent=self, model='quad', position=(sh.x, 1.6, sh.z + .05),
                           scale=(2.5, 3.2), color=Color(.2, 1, .4, 1))
        world.emissive(self.door)
        glow = Entity(parent=self, model='quad', position=(sh.x, 1.8, sh.z),
                      scale=6, texture='radial_gradient', color=Color(.2, 1, .4, .25))
        world.emissive(glow)
        self.safehouse = sh

        # runners who make it look easy (they hop a fence and are gone)
        self.runners = [
            self.add_npc(name='Runner Sam', position=self.player.position + Vec3(-2, 0, -2),
                         expression='worried',
                         lines=["They're in the alleys. RUN.", 'Grab a stick at least!']),
            self.add_npc(name='Runner Jo', position=self.player.position + Vec3(2, 0, -3),
                         expression='surprised',
                         lines=['Just weave the corners, the fast ones overshoot!']),
        ]

        # zombies: slow ones scattered inside, fast ones join later
        self.zombies = []
        for _ in range(7):
            c, r = rng.randint(0, COLS - 1), rng.randint(2, ROWS - 1)
            z = Zombie(parent=self, position=self.cell_pos(c, r))
            self.zombies.append(z)

        # inventory / combat state
        self.has_stick = False
        self.swing_t = 0
        self.viewmodel = None
        self.inv_text = Text(parent=self.hud, text='inventory: (empty) — find a stick',
                             position=(-.86, -.38), scale=.85,
                             color=Color(.9, .85, .6, 1))
        # trip state
        self.tripped_until = 0
        self.trip_cooldown = 0
        self.t = 0
        self.groan_timer = 0
        self.wave2 = False
        self.setup_mockery()
        self.set_objective('Reach the glowing green door — through the maze')

    # ------------------------------------------------------------- maze build
    def cell_pos(self, c, r):
        return Vec3(self.origin.x + c * CELL, 0, self.origin.z + r * CELL)

    def _build_maze_walls(self):
        wall_c = Color(.16, .15, .19, 1)
        def wall(pos, scale):
            w = self.make_box(pos, scale, wall_c)
            w.texture = 'brick'
            w.texture_scale = (max(1, int(scale[0] / 3 + scale[2] / 3)), 2)
        # internal walls where no edge is open
        for c in range(COLS):
            for r in range(ROWS):
                p = self.cell_pos(c, r)
                if c + 1 < COLS and frozenset(((c, r), (c + 1, r))) not in self.edges:
                    wall((p.x + CELL / 2, WALL_H / 2, p.z), (1.2, WALL_H, CELL + 1.2))
                if r + 1 < ROWS and frozenset(((c, r), (c, r + 1))) not in self.edges:
                    wall((p.x, WALL_H / 2, p.z + CELL / 2), (CELL + 1.2, WALL_H, 1.2))
        # outer boundary, with gaps at the south entrance / north exit
        half_w = COLS * CELL / 2
        for c in range(COLS):
            p = self.cell_pos(c, 0)
            if c != COLS // 2:
                wall((p.x, WALL_H / 2, p.z - CELL / 2), (CELL + 1.2, WALL_H, 1.2))
            p = self.cell_pos(c, ROWS - 1)
            if c != COLS // 2:
                wall((p.x, WALL_H / 2, p.z + CELL / 2), (CELL + 1.2, WALL_H, 1.2))
        for r in range(ROWS):
            p = self.cell_pos(0, r)
            wall((p.x - CELL / 2, WALL_H / 2, p.z), (1.2, WALL_H, CELL + 1.2))
            p = self.cell_pos(COLS - 1, r)
            wall((p.x + CELL / 2, WALL_H / 2, p.z), (1.2, WALL_H, CELL + 1.2))

    def _place_props(self, rng):
        from . import world
        self.trip_zones = []
        self.sticks = []
        cells = [(c, r) for c in range(COLS) for r in range(1, ROWS - 1)]
        rng.shuffle(cells)
        for c, r in cells[:8]:                          # rubble you can trip on
            p = self.cell_pos(c, r)
            for _ in range(4):
                Entity(parent=self, model='cube',
                       position=(p.x + rng.uniform(-2, 2), .12,
                                 p.z + rng.uniform(-2, 2)),
                       rotation_y=rng.uniform(0, 90),
                       scale=(rng.uniform(.4, 1), .25, rng.uniform(.3, .8)),
                       color=Color(.22, .2, .18, 1))
            self.trip_zones.append(p)
        for c, r in cells[8:11]:                        # sticks on the ground
            p = self.cell_pos(c, r)
            stick = Entity(parent=self, model='cube', position=(p.x, .15, p.z),
                           rotation=(0, rng.uniform(0, 90), 80),
                           scale=(.09, 1.3, .09), color=Color(.45, .3, .15, 1))
            ring = Entity(parent=self, model='circle', rotation_x=90,
                          position=(p.x, .05, p.z), scale=1.4,
                          color=Color(.9, .8, .3, .25))
            ring.setLightOff()
            self.sticks.append((stick, ring))
        for c, r in cells[11:22]:                       # lamps light the way
            p = self.cell_pos(c, r)
            world.street_lamp(self, (p.x + 2, 0, p.z), on=rng.random() < .7)

    # ------------------------------------------------------------------ tick
    def tick(self):
        dt = utime.dt
        self.t += dt
        self.tick_mockery(self.t)

        if 3 < self.t < 3.2 and not getattr(self, 'runners_gone', False):
            self.runners_gone = True
            self.announcer.visual('"RUN!" — the others vault a fence and are gone', 5,
                                  Color(1, .7, .5, 1))
            for r in self.runners:
                r.sprint_to((r.x, 0, r.z - 14), speed=8, then_vanish=True)
        if self.t > 25 and not self.wave2:
            self.wave2 = True
            self.announcer.sound('*something FAST is shrieking through the alleys*',
                                 4, cue='groan')
            for _ in range(3):
                c = random.randint(0, COLS - 1)
                z = FastZombie(parent=self, position=self.cell_pos(c, 1))
                self.zombies.append(z)

        tripped = self.t < self.tripped_until
        # zombies chase (they path straight; walls force YOU to plan)
        for z in self.zombies[:]:
            if z.dead:
                self.zombies.remove(z)
                continue
            z.chase(self.player.position, dt)
            d = (z.position - self.player.position).length()
            behind = self.player.forward.dot(
                (z.position - self.player.position).normalized()) < -.3
            if d < 10 and behind and self.groan_timer <= 0:
                self.groan_timer = 4
                self.announcer.sound('*wet groaning, RIGHT behind you*', 2.5,
                                     Color(1, .4, .4, 1), cue='groan')
            if d < (1.6 if tripped else 1.3):
                self.finish('CAUGHT',
                            'They got you' + (' while you were down.' if tripped
                                              else ' in a dead end.'),
                            success=False)
                return
        self.groan_timer -= dt

        self._tick_trip(dt, tripped)
        self._tick_pickup()
        if self.swing_t > 0:
            self.swing_t -= dt
            if self.viewmodel:
                self.viewmodel.rotation_x = -70 + (1 - self.swing_t / .3) * 90

        if distance_xz(self.player.position, self.safehouse) < 3:
            self.finish('SAFE',
                        f'Through the maze in {int(self.t)} seconds.\n'
                        'The fast ones overshoot corners. The slow ones never stop.',
                        success=True)

    def _tick_trip(self, dt, tripped):
        if tripped:
            return
        if self.trip_cooldown > 0:
            self.trip_cooldown -= dt
            return
        from ursina import held_keys
        moving = any(held_keys[k] for k in 'wasd')
        if not moving:
            return
        for p in self.trip_zones:
            if distance_xz(self.player.position, p) < 2 and random.random() < dt * .8:
                wheelchair = STATE.disability == 'wheelchair'
                downtime = 5 if wheelchair else 3
                self.tripped_until = self.t + downtime
                self.trip_cooldown = downtime + 4
                self.player.enabled = False
                camera.animate('rotation_z', 25, duration=.3)
                extra = ('Getting back into the chair takes longer — '
                         if wheelchair else '')
                self.announcer.visual(
                    f'You tripped on the rubble! {extra}down for {downtime}s',
                    downtime, Color(1, .5, .4, 1))
                def stand():
                    camera.animate('rotation_z', 0, duration=.4)
                    self.player.enabled = True
                invoke(stand, delay=downtime)
                break

    def _tick_pickup(self):
        for stick, ring in self.sticks[:]:
            if distance_xz(self.player.position, stick.position) < 1.6:
                self.interact_hint.text = '[E] pick up the stick'

    # ------------------------------------------------------------------ input
    def input(self, key):
        super().input(key)
        if self.finished:
            return
        if key == 'e' and not self.has_stick:
            for stick, ring in self.sticks[:]:
                if distance_xz(self.player.position, stick.position) < 1.6:
                    self.sticks.remove((stick, ring))
                    destroy(stick)
                    destroy(ring)
                    self.has_stick = True
                    self.inv_text.text = 'inventory: [ stick ] — click/F to swing'
                    self.viewmodel = Entity(parent=camera, model='cube',
                                            position=(.45, -.35, .8),
                                            rotation=(-70, 10, 0),
                                            scale=(.06, .9, .06),
                                            color=Color(.45, .3, .15, 1))
                    break
        if key in ('left mouse down', 'f') and self.has_stick and self.swing_t <= 0:
            self._swing()

    def _swing(self):
        from .audio import get_audio
        self.swing_t = .3
        hit_any = False
        for z in self.zombies:
            rel = z.position - self.player.position
            rel.y = 0
            if rel.length() < 2.8 and self.player.forward.dot(rel.normalized()) > .5:
                killed = z.hit(z.stick_damage)
                hit_any = True
                if killed:
                    self.announcer.visual('it drops.', 2, Color(.7, .9, .7, 1))
                elif isinstance(z, FastZombie):
                    self.announcer.visual('the stick barely marks it — RUN', 2,
                                          Color(1, .6, .5, 1))
        get_audio().play('kitchen_chop' if hit_any else 'whisper', volume=.4)
