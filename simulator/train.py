"""Scenario: catch the train — stairs, a broken elevator, and one long ramp."""
from ursina import Entity, Text, Color, time, distance_xz, Vec3, curve

from .base_scenario import BaseScenario
from .config import STATE

TRAIN_ARRIVES = 90
DOORS_CLOSE = 115


class TrainScenario(BaseScenario):
    player_start = (0, 0, -30)

    def build(self):
        from . import world
        self.lights = world.day_lights()

        plaza = self.make_box((0, -.5, 0), (80, 1, 110), Color(.6, .6, .62, 1))
        plaza.texture = 'white_cube'
        plaza.texture_scale = (26, 36)
        # elevated platform, brick-faced
        self.platform = self.make_box((0, 1.5, 30), (60, 3, 14), Color(.75, .68, .6, 1))
        self.platform.texture = 'brick'
        self.platform.texture_scale = (20, 2)
        Entity(parent=self, model='quad', color=Color(.9, .85, .2, 1),        # warning strip
               position=(0, 3.01, 34), scale=(60, 1), rotation_x=90)

        # rails and sleepers alongside the platform
        bed = self.make_box((0, .1, 40), (80, .3, 6), Color(.3, .28, .26, 1), collider=None)
        for x_off in (-1.2, 1.2):
            rail = Entity(parent=self, model='cube', position=(0, .42, 40 + x_off),
                          scale=(80, .12, .12), color=Color(.55, .55, .6, 1))
            world.emissive(rail)
        for i in range(26):
            Entity(parent=self, model='cube', position=(-38 + i * 3, .3, 40),
                   scale=(1, .1, 3), color=Color(.32, .24, .18, 1))

        # canopy over the platform
        for px in (-24, -8, 8, 24):
            self.make_box((px, 4.5, 30), (.35, 3, .35), Color(.35, .38, .42, 1),
                          collider=None)
        canopy = self.make_box((0, 6.1, 30), (56, .25, 12), Color(.5, .32, .3, 1),
                               collider=None)
        world.bench(self, (-14, 3, 28), rotation_y=180)
        world.bench(self, (14, 3, 28), rotation_y=180)
        # a couple of trees and lamps around the plaza
        world.tree(self, (-30, 0, -10))
        world.tree(self, (30, 0, -14))
        for pos in [(-12, 0, -12), (12, 0, -12), (-20, 3.005, 27), (20, 3.005, 27)]:
            world.street_lamp(self, pos, on=False)

        world.ground_details(self, area=(60, 50), center=(0, -8), cracks=12,
                             pebbles=18, scraps=3)
        world.manhole(self, (-8, 0, -16))
        world.manhole(self, (10, 0, 2))
        world.puddle(self, (-15, 0, -5), scale=2)
        # platform posters and a trash bin
        for px, pc in [(-10, Color(.75, .35, .3, 1)), (4, Color(.3, .5, .75, 1))]:
            Entity(parent=self, model='quad', position=(px, 2.2, 22.95),
                   scale=(1.4, 1.9), color=pc)
        self.make_box((-6, 3.45, 25), (.55, .9, .55), Color(.3, .38, .35, 1),
                      collider=None)

        # stairs: a steep walkable slope on the left
        self.stairs = Entity(parent=self, model='cube', color=Color(.45, .45, .5, 1),
                             position=(-20, 1.4, 19), scale=(6, .5, 11),
                             rotation_x=-28, collider='box')
        Text(parent=self, text='STAIRS', position=(-20, 4.5, 24), scale=10, origin=(0, 0),
             billboard=True, color=Color(1, 1, 1, 1))

        # broken elevator on the right
        self.elevator = self.make_box((20, 2, 22.5), (4, 4, 1), Color(.6, .2, .2, 1))
        Text(parent=self, text='ELEVATOR\nOUT OF ORDER', position=(20, 5, 22), scale=8, origin=(0, 0),
             billboard=True, color=Color(1, .5, .5, 1))

        # the long accessible ramp, far to the right
        self.ramp = Entity(parent=self, model='cube', color=Color(.4, .5, .45, 1),
                           position=(26, 1.4, 16), scale=(5, .5, 32),
                           rotation_x=-11, collider='box')
        Text(parent=self, text='RAMP ->', position=(24, 3.5, 8), scale=10, origin=(0, 0),
             billboard=True, color=Color(.6, 1, .7, 1))

        # departure board — the visual source of truth
        self.board = self.make_box((6, 2.5, -22), (5, 2, .4), Color(.16, .16, .2, 1))
        self.make_box((6, .9, -22), (.3, 1.8, .3), Color(.25, .25, .28, 1), collider=None)
        screen = Entity(parent=self, model='quad', position=(6, 2.5, -22.25),
                        scale=(4.6, 1.6), color=Color(.05, .12, .08, 1))
        world.emissive(screen)
        for row in range(3):                                  # glowing schedule rows
            line = Entity(parent=self, model='quad',
                          position=(6 - .4, 2.95 - row * .45, -22.26),
                          scale=(2.8 - row * .4, .16), color=Color(1, .8, .25, 1))
            world.emissive(line)
        Text(parent=self, text='DEPARTURES', position=(6, 3.9, -22.3), scale=8, origin=(0, 0),
             billboard=True, color=Color(1, .9, .3, 1))

        # the train, waiting far down the track
        self.train = Entity(parent=self, position=(-90, 4.5, 40))
        body = Entity(parent=self.train, model='cube', color=Color(.25, .4, .75, 1),
                      scale=(40, 3.2, 4))
        Entity(parent=self.train, model='cube', color=Color(.85, .85, .88, 1),   # roof
               position=(0, 1.7, 0), scale=(40, .35, 3.6))
        Entity(parent=self.train, model='cube', color=Color(.9, .8, .2, 1),      # nose
               position=(-20.4, -.3, 0), scale=(1, 2.4, 3.4))
        stripe = Entity(parent=self.train, model='cube', color=Color(.9, .9, .95, 1),
                        position=(0, -.4, -2.01), scale=(40, .5, .05))
        for i in range(10):                                                      # windows
            win = Entity(parent=self.train, model='quad', color=Color(.7, .85, 1, 1),
                         position=(-17 + i * 3.6, .55, -2.02), scale=(2.2, 1.1))
            world.emissive(win)
        for i in range(3):                                                       # doors
            Entity(parent=self.train, model='quad', color=Color(.15, .25, .5, 1),
                   position=(-12 + i * 12, -.35, -2.02), scale=(1.6, 2.5))
        for i in range(6):                                                       # wheels
            for wz in (-1.6, 1.6):
                Entity(parent=self.train, model='sphere', color=Color(.1, .1, .12, 1),
                       position=(-16 + i * 6.5, -1.7, wz), scale=(1, 1, .35))
        self.door_zone = Vec3(0, 3, 36)

        self.add_npc(name='Commuter Dana', position=(-6, 0, -20), speed=2,
                     expression='tired',
                     waypoints=[(-6, -20), (-12, -10), (-2, -12)],
                     lines=["The elevator's been broken for three months.",
                            'Nobody seems in a hurry to fix it.'])
        self.runner = self.add_npc(name='Commuter Alex', position=(5, 0, -14),
                                   expression='happy',
                                   lines=['Plenty of time. The stairs take me ten seconds.',
                                          'Why, is that not enough for you?'])

        self.setup_mockery(spawn_pos=(-10, 0, -8))

        self.t = 0
        self.boarded = False
        self.announced = set()
        self.set_objective('Catch the train to Riverdale — get onto platform 1')

    def tick(self):
        self.t += time.dt
        self.tick_mockery(self.t)

        def announce_once(tag, fn, *args):
            if tag not in self.announced:
                self.announced.add(tag)
                fn(*args)

        if self.t > 3:
            announce_once('a1', self.announcer.sound,
                          'PA: "Train to Riverdale arrives at platform 1 in 90 seconds."', 6)
        if self.t > 60:
            announce_once('a2', self.announcer.sound, 'PA: "Train now approaching platform 1."', 5)
        if self.t > TRAIN_ARRIVES:
            def arrive():
                from .audio import get_audio
                get_audio().play('rumble', volume=.6)
                self.train.animate_position(Vec3(0, 4.5, 40), duration=3, curve=curve.out_quad)
                self.announcer.visual('the train pulls in — doors open', 5, Color(.6, 1, .7, 1))
            announce_once('arrive', arrive)
        if self.t > 80:
            announce_once('runner', lambda: (
                self.runner.sprint_to((-20, 0, 14), speed=7),
                self.announcer.visual('Alex bounds up the stairs in seconds...', 4)))
        if self.t > DOORS_CLOSE:
            def leave():
                self.train.animate_position(Vec3(120, 4.5, 40), duration=4, curve=curve.in_quad)
            announce_once('leave', leave)
            if not self.boarded:
                self.finish('TRAIN MISSED',
                            'The doors closed and the train left without you.\n'
                            'Everyone else made it look easy.', success=False)
                return

        # wheelchair users are pushed off the stairs
        if STATE.disability == 'wheelchair':
            p = self.player.position
            if -24 < p.x < -16 and 12 < p.z < 25 and p.y < 3.2:
                self.player.position = Vec3(p.x, p.y, 11.5)
                self.announcer.visual("You can't take stairs in a wheelchair. Find another way up.",
                                      3, Color(1, .6, .5, 1))

        # reading the departure board
        if distance_xz(self.player.position, self.board.position) < 4 and not self.dialogue.enabled:
            self.interact_hint.text = '[E] read the departure board'

        # boarding
        on_platform = self.player.position.y > 2.5
        doors_open = TRAIN_ARRIVES + 3 < self.t < DOORS_CLOSE
        if on_platform and doors_open and distance_xz(self.player.position, self.door_zone) < 6:
            self.interact_hint.text = '[E] board the train'

    def input(self, key):
        super().input(key)
        if key != 'e' or self.dialogue.enabled or self.finished:
            return
        if distance_xz(self.player.position, self.board.position) < 4:
            remaining = max(0, int(TRAIN_ARRIVES - self.t))
            status = f'arriving in {remaining}s' if remaining else (
                'AT PLATFORM — doors open' if self.t < DOORS_CLOSE else 'DEPARTED')
            self.announcer.visual(f'BOARD: RIVERDALE · platform 1 · {status}', 5,
                                  Color(1, .9, .3, 1))
        on_platform = self.player.position.y > 2.5
        doors_open = TRAIN_ARRIVES + 3 < self.t < DOORS_CLOSE
        if on_platform and doors_open and distance_xz(self.player.position, self.door_zone) < 6:
            self.boarded = True
            mins = int(self.t)
            self.finish('YOU MADE IT',
                        f'You boarded with {DOORS_CLOSE - mins} seconds to spare.\n'
                        'Think about which route you had to take — and why.', success=True)
