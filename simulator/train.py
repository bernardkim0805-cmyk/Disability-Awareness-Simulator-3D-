"""Scenario: a three-floor transit hub at rush hour.

You spawn on the CONCOURSE. Below is an underground SUBWAY platform so long
its ends disappear into the dark; above is the BUS TERMINAL. Your phone
gives you a randomized task: catch a specific train direction, or a
specific numbered bus before it departs. Stairs connect the floors — but
not for wheelchair users, who must use the elevator, and must ask the bus
driver to deploy the ramp. Every floor is packed with people; shove
through them and they get loud about it.
"""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import random

from ursina import (Entity, Text, Color, Vec3, camera, time as utime,
                    distance_xz, destroy, invoke, curve)

from .base_scenario import BaseScenario
from .config import STATE

CROWD_PER_FLOOR = 130        # stands in for the ~500-person rush-hour crush
FLOOR_Y = {'subway': -8, 'concourse': 0, 'bus': 8}
YELLS = ['HEY!', 'Watch it!!', 'Excuse YOU.', 'Seriously?!', 'OW — look up!']

SHIRTS = [Color(.6, .25, .25, 1), Color(.25, .35, .6, 1), Color(.3, .5, .35, 1),
          Color(.55, .5, .2, 1), Color(.45, .3, .5, 1), Color(.35, .35, .4, 1)]


class CrowdPerson(Entity):
    """A cheap 3-part commuter (there are hundreds; the full rig would melt
    the frame rate). Some wander; all get angry when bumped."""

    def __init__(self, mover=False, **kwargs):
        super().__init__(**kwargs)
        shirt = random.choice(SHIRTS)
        self.body = Entity(parent=self, model='cube', y=.85,
                           scale=(.45, 1.7, .3), color=shirt)
        self.base_color = shirt
        Entity(parent=self, model='sphere', y=1.85, scale=.32,
               color=random.choice([Color(.9, .75, .6, 1), Color(.7, .5, .38, 1),
                                    Color(.5, .35, .25, 1)]))
        self.rotation_y = random.uniform(0, 360)
        self.mover = mover
        if mover:
            self.home = Vec3(self.position)
            self.goal = self._new_goal()
        self.next_bump = 0
        self.yell = None

    def _new_goal(self):
        return self.home + Vec3(random.uniform(-6, 6), 0, random.uniform(-6, 6))

    def update(self):
        if not self.mover:
            return
        d = self.goal - self.position
        d.y = 0
        if d.length() < .5:
            self.goal = self._new_goal()
            return
        self.position += d.normalized() * 1.1 * utime.dt
        self.look_at(self.position + d)

    def bumped(self, t):
        if t < self.next_bump:
            return False
        self.next_bump = t + 3
        self.body.color = Color(.9, .25, .2, 1)
        invoke(setattr, self.body, 'color', self.base_color, delay=1.2)
        if self.yell:
            destroy(self.yell)
        self.yell = Text(parent=self, text=random.choice(YELLS), y=2.4,
                         origin=(0, 0), scale=9, billboard=True,
                         color=Color(1, .3, .25, 1))
        self.yell.setLightOff()
        destroy(self.yell, delay=1.6)
        # they shove back / step away, glaring
        away = self.position - Vec3(0, 0, 0)
        return True


class TransitHubScenario(BaseScenario):
    player_start = (0, 0, -8)
    sky_color = Color(.05, .05, .08, 1)      # underground: no sky

    # ------------------------------------------------------------------ build
    def build(self):
        from . import world
        self.lights = world.indoor_lights()
        self.t = 0
        self.bumps = 0
        self.crowd = []
        self.announced = set()

        self._build_concourse()
        self._build_subway()
        self._build_bus_level()
        self._build_stairs_and_elevator()
        for floor, y in FLOOR_Y.items():
            self._spawn_crowd(floor, y)

        # ---- the randomized to-do ------------------------------------------
        if random.random() < .5:
            self.task = dict(kind='train',
                             dir=random.choice(['NORTHBOUND', 'SOUTHBOUND']))
            todo = (f'Take the {self.task["dir"]} train '
                    '(subway level, DOWN the stairs / elevator)')
        else:
            self.task = dict(kind='bus', number=random.choice([12, 47, 63]))
            todo = (f'Catch bus #{self.task["number"]} before it departs '
                    '(bus terminal, UP the stairs / elevator)')
        self.set_objective(todo)
        self.phone_text = todo
        self.phone = self._build_phone()

        self.setup_mockery(spawn_pos=(6, 0, -4))
        Text(parent=self.hud, text='TAB phone · E interact/board · elevator: E then 1/2/3',
             position=(0, -.455), origin=(0, 0), scale=.7, color=Color(.6, .6, .65, 1))

    # ------------------------------------------------------------- structures
    def _hall(self, y, w, d, wall_c, name):
        """Floor slab + walls + ceiling for one level, centered on x=0,z=0."""
        f = self.make_box((0, y - .5, 0), (w, 1, d), Color(.5, .5, .53, 1))
        f.texture = 'white_cube'
        f.texture_scale = (w // 3, d // 3)
        for pos, scale in [((0, y + 3, d / 2), (w, 6, .6)),
                           ((0, y + 3, -d / 2), (w, 6, .6)),
                           ((-w / 2, y + 3, 0), (.6, 6, d)),
                           ((w / 2, y + 3, 0), (.6, 6, d))]:
            self.make_box(pos, scale, wall_c)
        return f

    def _build_concourse(self):
        self._hall(0, 64, 44, Color(.6, .58, .55, 1), 'concourse')
        self.make_box((0, 6, 0), (64, .5, 44), Color(.35, .35, .38, 1),
                      collider=None)
        from . import world
        for px in (-20, 0, 20):                          # pillars
            for pz in (-12, 12):
                self.make_box((px, 3, pz), (1.2, 6, 1.2), Color(.55, .55, .6, 1))
        for i, (txt, col) in enumerate([('SUBWAY  (down)', Color(.3, .8, .5, 1)),
                                        ('BUS TERMINAL  (up)', Color(1, .8, .3, 1))]):
            sign = Entity(parent=self, model='quad', position=(-15 + i * 30, 4.2, 8),
                          scale=(7, 1.2), color=Color(.08, .1, .12, 1))
            sign.setLightOff()
            t = Text(parent=self, text=txt, position=(-15 + i * 30, 4.2, 7.9),
                     origin=(0, 0), scale=9, color=col)
            t.setLightOff()
        # ticket machines
        for mx in (-28, -25):
            self.make_box((mx, 1.1, -18), (1.4, 2.2, 1), Color(.2, .4, .5, 1))

    def _build_subway(self):
        y = FLOOR_Y['subway']
        L = 240                                          # ends vanish into dark
        # platform slab (walkable) with track pits either side
        p = self.make_box((0, y - .5, 0), (L, 1, 12), Color(.55, .52, .5, 1))
        p.texture = 'brick'
        p.texture_scale = (60, 3)
        for side in (-1, 1):                             # track pits + rails
            self.make_box((0, y - 1.6, side * 9), (L, .4, 6), Color(.1, .1, .12, 1),
                          collider=None)
            for rz in (side * 7.6, side * 10.4):
                r = self.make_box((0, y - 1.2, rz), (L, .12, .12),
                                  Color(.5, .5, .55, 1), collider=None)
            strip = Entity(parent=self, model='quad', rotation_x=90,
                           position=(0, y + .06, side * 5.4), scale=(L, .8),
                           color=Color(.9, .85, .2, .9))
            strip.setLightOff()
        # hall shell: walls beyond the tracks + ceiling; dim lamps every 15 m
        for side in (-1, 1):
            self.make_box((0, y + 2.5, side * 13), (L, 7, .6), Color(.3, .3, .34, 1))
        self.make_box((0, y + 5.5, 0), (L, .5, 27), Color(.2, .2, .24, 1),
                      collider=None)
        for lx in range(-int(L / 2) + 10, int(L / 2), 15):
            lamp = Entity(parent=self, model='cube', position=(lx, y + 5.1, 0),
                          scale=(1.6, .12, .8), color=Color(.85, .82, .7, 1))
            lamp.setLightOff()
        # direction boards (the deaf-accessible source of truth)
        self.boards = []
        for side, name in ((-1, 'SOUTHBOUND'), (1, 'NORTHBOUND')):
            b = Entity(parent=self, model='quad', position=(0, y + 3.4, side * 4.8),
                       rotation_y=180 if side > 0 else 0, scale=(8, 1),
                       color=Color(.05, .08, .05, 1))
            b.setLightOff()
            t = Text(parent=self, text=f'{name}', origin=(0, 0),
                     position=(0, y + 3.4, side * 4.7),
                     rotation_y=180 if side > 0 else 0, scale=8,
                     color=Color(1, .8, .25, 1))
            t.setLightOff()
            self.boards.append((name, t))
        # the two trains, parked far up the tunnels
        self.trains = {}
        for side, name in ((1, 'NORTHBOUND'), (-1, 'SOUTHBOUND')):
            tr = Entity(parent=self, position=(-L / 2 - 40, y + 1.4, side * 9))
            Entity(parent=tr, model='cube', scale=(46, 3, 3.6),
                   color=Color(.25, .4, .75, 1))
            for i in range(10):
                w = Entity(parent=tr, model='quad',
                           position=(-20 + i * 4.4, .4, -1.85 * side),
                           rotation_y=0 if side > 0 else 180,
                           scale=(2.4, 1), color=Color(.75, .85, 1, 1))
                w.setLightOff()
            self.trains[name] = dict(root=tr, state='away', timer=0, side=side)
        self.next_arrival = 12
        self.arrival_order = (['NORTHBOUND', 'SOUTHBOUND']
                              if random.random() < .5 else
                              ['SOUTHBOUND', 'NORTHBOUND'])

    def _build_bus_level(self):
        y = FLOOR_Y['bus']
        self._hall(y, 64, 40, Color(.55, .5, .45, 1), 'bus')
        self.make_box((0, y + 6, 0), (64, .5, 40), Color(.4, .42, .48, 1),
                      collider=None)
        self.buses = []
        numbers = [12, 47, 63]
        random.shuffle(numbers)
        departs = [75, 135, 200]
        for i, (num, dep) in enumerate(zip(numbers, departs)):
            bx = -20 + i * 20
            root = Entity(parent=self, position=(bx, y, 8))
            Entity(parent=root, model='cube', position=(0, 1.5, 0),
                   scale=(4, 3, 10), color=Color(.85, .6, .15, 1))
            for wz in range(-4, 5, 2):
                w = Entity(parent=root, model='quad', position=(-2.02, 2.2, wz),
                           rotation_y=90, scale=(1.6, 1), color=Color(.7, .82, .9, 1))
                w.setLightOff()
            door = Entity(parent=root, model='quad', position=(-2.02, 1.1, 3.5),
                          rotation_y=90, scale=(1.2, 2.2), color=Color(.2, .25, .3, 1))
            num_t = Text(parent=self, text=f'#{num}', position=(bx - 2.1, y + 3.4, 3.5),
                         rotation_y=90, origin=(0, 0), scale=10,
                         color=Color(1, 1, .5, 1))
            num_t.setLightOff()
            sign = Text(parent=self, text='', position=(bx, y + 4.6, 4),
                        origin=(0, 0), scale=8, color=Color(.5, 1, .6, 1))
            sign.setLightOff()
            self.buses.append(dict(num=num, root=root, departs=dep, sign=sign,
                                   door=Vec3(bx - 2.5, y, 11.5), gone=False,
                                   ramp=None, ramp_ready=False))

    def _build_stairs_and_elevator(self):
        from ursina import Entity as E
        # stairs down to subway (west) and up to the bus level (east)
        self.stair_zones = []
        down = Entity(parent=self, model='cube', color=Color(.45, .45, .5, 1),
                      position=(-15, -4, 16), scale=(6, .5, 18),
                      rotation_x=28, collider='box')
        self.stair_zones.append(((-15, 16), 'down'))
        up = Entity(parent=self, model='cube', color=Color(.45, .45, .5, 1),
                    position=(15, 4, 16), scale=(6, .5, 18),
                    rotation_x=-28, collider='box')
        self.stair_zones.append(((15, 16), 'up'))
        for x, label in ((-15, 'STAIRS DOWN'), (15, 'STAIRS UP')):
            t = Text(parent=self, text=label, position=(x, 2.6, 9), origin=(0, 0),
                     scale=8, billboard=True, color=Color(.9, .9, .95, 1))
            t.setLightOff()
        # the elevator: a glass shaft at the back of every floor
        self.elev_pos = Vec3(0, 0, 18)
        for y in FLOOR_Y.values():
            self.make_box((0, y + 1.6, 20.5), (3.4, 3.2, .4), Color(.5, .6, .65, .5))
            doorframe = self.make_box((0, y + 1.6, 18.9), (3.6, 3.2, .3),
                                      Color(.6, .62, .66, 1), collider=None)
            t = Text(parent=self, text='ELEVATOR', position=(0, y + 3.5, 18.8),
                     origin=(0, 0), scale=7, billboard=True,
                     color=Color(.6, .9, 1, 1))
            t.setLightOff()
        self.elev_busy = False

    def _build_phone(self):
        phone = Entity(parent=camera.ui, enabled=False)
        Entity(parent=phone, model='quad', position=(.55, -.1), scale=(.34, .55),
               color=Color(.08, .08, .1, .97))
        Text(parent=phone, text='MAPS', position=(.44, .14), scale=.9,
             color=Color(.4, .8, 1, 1))
        Text(parent=phone, text=self.phone_text, position=(.42, .06), scale=.62,
             color=Color(.9, .95, .9, 1))
        Text(parent=phone, text='[TAB] put phone away', position=(.42, -.3),
             scale=.6, color=Color(.6, .6, .6, 1))
        return phone

    def _spawn_crowd(self, floor, y):
        area = {'concourse': (28, 18), 'subway': (100, 4.5), 'bus': (28, 14)}[floor]
        for i in range(CROWD_PER_FLOOR):
            pos = Vec3(random.uniform(-area[0], area[0]), y,
                       random.uniform(-area[1], area[1]))
            if floor == 'concourse' and pos.z > 14:
                pos.z = 10                       # keep the elevator reachable
            if floor == 'concourse' and (pos - Vec3(0, 0, -8)).length() < 4:
                pos.x += 8                       # don't spawn inside the player
            person = CrowdPerson(parent=self, position=pos, mover=i % 3 == 0)
            person.floor = floor
            self.crowd.append(person)

    # ------------------------------------------------------------------ tick
    def tick(self):
        dt = utime.dt
        self.t += dt
        self.tick_mockery(self.t)
        self._tick_crowd()
        self._tick_trains(dt)
        self._tick_buses(dt)
        self._tick_stairs()
        self._tick_prompts()

    def player_floor(self):
        y = self.player.y
        return ('subway' if y < -4 else 'bus' if y > 4 else 'concourse')

    def _tick_crowd(self):
        p = self.player.position
        floor = self.player_floor()
        from ursina import held_keys
        moving = any(held_keys[k] for k in 'wasd')
        for person in self.crowd:
            if person.floor != floor:
                continue
            rel = person.position - p
            rel.y = 0
            d = rel.length()
            if d < .9 and moving:
                if person.bumped(self.t):
                    self.bumps += 1
                    person.position += rel.normalized() * .8
                    if self.bumps % 5 == 0:
                        self.announcer.visual(
                            f'{self.bumps} people shoved so far — the crowd '
                            'is getting hostile', 3, Color(1, .6, .5, 1))

    def _tick_trains(self, dt):
        y = FLOOR_Y['subway']
        self.next_arrival -= dt
        if self.next_arrival <= 0:
            name = self.arrival_order[0]
            self.arrival_order = self.arrival_order[1:] + [name]
            self.next_arrival = 40
            tr = self.trains[name]
            if tr['state'] == 'away':
                tr['state'] = 'arriving'
                tr['root'].x = -160
                tr['root'].animate_x(0, duration=4, curve=curve.out_quad)
                self.announcer.sound(f'PA: "{name} train now arriving."', 5)
                invoke(lambda n=name: self._doors_open(n), delay=4)
        for bname, btext in self.boards:
            tr = self.trains[bname]
            if tr['state'] == 'boarding':
                btext.text = f'{bname}  <<  BOARDING  >>'
            elif tr['state'] == 'arriving':
                btext.text = f'{bname}  arriving...'
            else:
                btext.text = f'{bname}  next train soon'

    def _doors_open(self, name):
        tr = self.trains[name]
        tr['state'] = 'boarding'
        def leave():
            if tr['state'] == 'boarding':
                tr['state'] = 'away'
                tr['root'].animate_x(160, duration=4, curve=curve.in_quad)
                invoke(setattr, tr['root'], 'x', -200, delay=5)
        invoke(leave, delay=14)

    def _tick_buses(self, dt):
        for bus in self.buses:
            if bus['gone']:
                continue
            left = bus['departs'] - self.t
            bus['sign'].text = (f'bus #{bus["num"]}  departs '
                                f'{max(0, int(left)) // 60}:{max(0, int(left)) % 60:02d}')
            if left <= 0:
                bus['gone'] = True
                bus['root'].animate_x(bus['root'].x - 80, duration=4,
                                      curve=curve.in_quad)
                self.announcer.sound(f'*bus #{bus["num"]} pulls away*', 4)
                if self.task['kind'] == 'bus' and bus['num'] == self.task['number']:
                    self.finish('MISSED THE BUS',
                                f'Bus #{bus["num"]} left on schedule. Between the '
                                'crowd and the route,\nyou never reached the door.',
                                success=False)

    def _tick_stairs(self):
        if STATE.disability != 'wheelchair':
            return
        p = self.player.position
        for (sx, sz), kind in self.stair_zones:
            if abs(p.x - sx) < 4 and 8 < p.z < 25 and abs(p.y) < 7.5:
                if (kind == 'down' and p.x < 0) or (kind == 'up' and p.x > 0):
                    self.player.position = Vec3(p.x, FLOOR_Y[self.player_floor()], 7)
                    self.announcer.visual(
                        'Stairs. In a wheelchair the elevator is the ONLY way.',
                        3, Color(1, .6, .5, 1))

    def _tick_prompts(self):
        if self.dialogue.enabled:
            return
        p = self.player.position
        if distance_xz(p, self.elev_pos) < 3.2:
            self.interact_hint.text = ('[1] subway   [2] concourse   [3] bus terminal'
                                       if not self.elev_busy else 'elevator moving...')
            return
        floor = self.player_floor()
        if floor == 'subway':
            for name, tr in self.trains.items():
                if tr['state'] == 'boarding' and abs(p.x) < 24 \
                        and abs(p.z - tr['side'] * 5) < 2.5:
                    self.interact_hint.text = f'[E] board the {name} train'
                    return
        if floor == 'bus':
            for bus in self.buses:
                if not bus['gone'] and distance_xz(p, bus['door']) < 2.2:
                    if STATE.disability == 'wheelchair' and not bus['ramp_ready']:
                        self.interact_hint.text = '[E] ask the driver for the ramp'
                    else:
                        self.interact_hint.text = f'[E] board bus #{bus["num"]}'
                    return

    # ------------------------------------------------------------------ input
    def input(self, key):
        super().input(key)
        if self.finished:
            return
        if key == 'tab':
            self.phone.enabled = not self.phone.enabled
            return
        if key in ('1', '2', '3') and distance_xz(self.player.position,
                                                  self.elev_pos) < 3.2 \
                and not self.elev_busy:
            floor = ('subway', 'concourse', 'bus')[int(key) - 1]
            self._ride_elevator(floor)
            return
        if key == 'e':
            self._try_board()

    def _ride_elevator(self, floor):
        self.elev_busy = True
        wait = 3 if STATE.disability == 'wheelchair' else 2
        self.announcer.visual('elevator on its way...', wait)
        def arrive():
            self.player.position = Vec3(0, FLOOR_Y[floor] + .1, 15)
            self.elev_busy = False
        invoke(arrive, delay=wait)

    def _try_board(self):
        p = self.player.position
        floor = self.player_floor()
        if floor == 'subway':
            for name, tr in self.trains.items():
                if tr['state'] == 'boarding' and abs(p.x) < 24 \
                        and abs(p.z - tr['side'] * 5) < 2.5:
                    if self.task['kind'] == 'train' and name == self.task['dir']:
                        self.finish('RIGHT TRAIN',
                                    f'You squeezed onto the {name} train through '
                                    f'{self.bumps} collisions worth of crowd.',
                                    success=True)
                    else:
                        why = ('that train goes the WRONG WAY'
                               if self.task['kind'] == 'train'
                               else 'your task was the BUS upstairs')
                        self.finish('WRONG TRAIN',
                                    f'The doors close. {why}.\n'
                                    'The phone map knew. The platform did not '
                                    'make it obvious.', success=False)
                    return
        if floor == 'bus':
            for bus in self.buses:
                if bus['gone'] or distance_xz(p, bus['door']) > 2.2:
                    continue
                if STATE.disability == 'wheelchair' and not bus['ramp_ready']:
                    self.announcer.visual('Driver nods. Deploying the ramp — '
                                          'everyone behind you waits...', 5)
                    def ramp(b=bus):
                        b['ramp'] = Entity(parent=self, model='cube',
                                           position=(b['door'].x + .8,
                                                     b['door'].y + .3, b['door'].z - 2),
                                           rotation_z=15, scale=(2.2, .1, 1.2),
                                           color=Color(.6, .6, .65, 1))
                        b['ramp_ready'] = True
                        self.announcer.visual('ramp is down — board now', 3,
                                              Color(.6, 1, .7, 1))
                    invoke(ramp, delay=5)
                    return
                if self.task['kind'] == 'bus' and bus['num'] == self.task['number']:
                    self.finish('RIGHT BUS',
                                f'Bus #{bus["num"]}, caught with the clock running'
                                + (' and a ramp request.' if STATE.disability ==
                                   'wheelchair' else '.'), success=True)
                else:
                    why = (f'you needed #{self.task["number"]}'
                           if self.task['kind'] == 'bus'
                           else 'your task was the TRAIN downstairs')
                    self.finish('WRONG BUS',
                                f'This is the #{bus["num"]} — {why}.',
                                success=False)
                return


# keep the old import name working for the menu registration
TrainScenario = TransitHubScenario
