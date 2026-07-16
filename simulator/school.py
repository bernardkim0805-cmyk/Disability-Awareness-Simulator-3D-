"""Scenario: sit a timed school test while classmates finish effortlessly."""
import random

from ursina import Entity, Text, Color, camera, mouse, time, destroy, distance_xz, Vec3

from .base_scenario import BaseScenario
from .config import STATE
from .dialogue import dyslexify

QUESTIONS = [
    ('What is 12 x 12?', ['124', '144', '154'], 1),
    ('Which planet is closest to the sun?', ['Mercury', 'Venus', 'Mars'], 0),
    ('Opposite of "expand"?', ['contract', 'extend', 'inflate'], 0),
    ('The teacher announced the answer to this one out loud.', ['A', 'B', 'C'], 1),
    ('7 + 6 x 2 = ?', ['26', '19', '20'], 1),
]

FAKE_OPTIONS = ["they're laughing at you", 'you already failed', "don't answer. leave."]


class SchoolTestScenario(BaseScenario):
    player_start = (0, 0, -8)

    def build(self):
        from . import world
        self.lights = world.indoor_lights()
        wall = Color(.78, .76, .68, 1)
        skirt = Color(.5, .45, .38, 1)

        floor = self.make_box((0, -.5, 0), (30, 1, 26), Color(.72, .58, .42, 1))
        floor.texture = 'white_cube'
        floor.texture_scale = (15, 13)
        ceiling = self.make_box((0, 6, 0), (30, .4, 26), Color(.9, .9, .88, 1))
        for i in range(3):                                               # ceiling lights
            lamp = Entity(parent=self, model='cube', position=(-8 + i * 8, 5.75, 0),
                          scale=(3, .15, 1), color=Color(1, .98, .9, 1))
            world.emissive(lamp)

        self.make_box((0, 3, 13), (30, 6.4, 1), wall)                    # front wall
        self.make_box((0, 3, -13), (30, 6.4, 1), wall)
        self.make_box((-15, 3, 0), (1, 6.4, 26), wall)
        self.make_box((15, 3, 0), (1, 6.4, 26), wall)
        # skirting boards
        self.make_box((0, .5, 12.4), (30, 1, .15), skirt, collider=None)
        self.make_box((0, .5, -12.4), (30, 1, .15), skirt, collider=None)
        self.make_box((-14.4, .5, 0), (.15, 1, 26), skirt, collider=None)
        self.make_box((14.4, .5, 0), (.15, 1, 26), skirt, collider=None)

        # windows along the right wall: daylight, frames, sills and curtains
        for wz in (-8, -3, 2, 7):
            win = Entity(parent=self, model='quad', rotation_y=90,
                         position=(14.4, 3.4, wz), scale=(3.4, 2.4),
                         color=Color(.75, .88, 1, 1))
            world.emissive(win)
            self.make_box((14.42, 3.4, wz), (.06, 2.5, .18), Color(.4, .35, .3, 1),
                          collider=None)                                 # center mullion
            self.make_box((14.42, 3.4, wz), (.06, .14, 3.5), Color(.4, .35, .3, 1),
                          collider=None)                                 # cross bar
            self.make_box((14.35, 2.1, wz), (.3, .1, 3.7), Color(.5, .45, .38, 1),
                          collider=None)                                 # sill
            Entity(parent=self, model='cube', color=Color(.5, .42, .3, 1),
                   position=(14.3, .95, wz - 1), scale=(.12, .25, .3))   # potted plant
            Entity(parent=self, model='sphere', color=Color(.25, .5, .25, 1),
                   position=(14.3, 1.2, wz - 1), scale=(.28, .3, .28))
            for cz in (wz - 1.9, wz + 1.9):                              # curtains
                Entity(parent=self, model='cube', color=Color(.85, .75, .45, 1),
                       position=(14.38, 3.5, cz), scale=(.1, 2.7, .5))
        # posters on the left wall
        for wz, c in [(-6, Color(.85, .4, .35, 1)), (0, Color(.35, .6, .8, 1)),
                      (6, Color(.9, .75, .3, 1))]:
            Entity(parent=self, model='quad', rotation_y=-90,
                   position=(-14.4, 3.4, wz), scale=(1.8, 2.4), color=c)
        # door at the back
        self.make_box((-10, 1.5, -12.4), (1.6, 3, .2), Color(.4, .28, .18, 1),
                      collider=None)

        from ursina import Text
        board_frame = Entity(parent=self, model='cube', color=Color(.45, .32, .2, 1),
                             position=(-3, 3, 12.45), scale=(7.6, 3.4, .12))
        Entity(parent=self, model='quad', color=Color(.12, .3, .2, 1),   # chalkboard
               position=(-3, 3, 12.35), scale=(7, 3))
        Entity(parent=self, model='cube', color=Color(.5, .38, .25, 1),  # chalk tray
               position=(-3, 1.25, 12.3), scale=(7, .12, .25))
        chalk_text = Text(parent=self, text='FRIDAY: TEST DAY\n5 questions - 75 seconds\ngood luck!',
                          position=(-3, 3.8, 12.34), scale=7, origin=(0, 0),
                          color=Color(.92, .95, .9, .9))
        chalk_text.setLightOff()
        for i, cl in enumerate([Color(.95, .95, .9, 1), Color(.95, .85, .6, 1)]):
            Entity(parent=self, model='cube', color=cl,                  # chalk sticks
                   position=(-4.5 + i * .35, 1.33, 12.28), scale=(.22, .05, .05))
        Entity(parent=self, model='cube', color=Color(.25, .2, .18, 1),  # board eraser
               position=(-1.5, 1.35, 12.28), scale=(.4, .1, .15))

        # whiteboard on the right half of the front wall
        Entity(parent=self, model='cube', color=Color(.75, .75, .78, 1), # silver frame
               position=(5.5, 3, 12.45), scale=(4.6, 2.6, .1))
        wb = Entity(parent=self, model='quad', color=Color(.96, .96, .97, 1),
                    position=(5.5, 3, 12.36), scale=(4.2, 2.2))
        wb.setLightOff()
        wb_text = Text(parent=self, text='12 x 12 = ?\n7 + 6 x 2 = ?',
                       position=(4.6, 3.5, 12.35), scale=6.5,
                       color=Color(.85, .2, .2, .95))
        wb_text.setLightOff()
        Entity(parent=self, model='cube', color=Color(.7, .7, .73, 1),   # marker tray
               position=(5.5, 1.75, 12.3), scale=(4.2, .1, .22))
        for i, mc in enumerate([Color(.85, .2, .2, 1), Color(.2, .3, .8, 1),
                                Color(.2, .6, .3, 1)]):
            Entity(parent=self, model='cube', color=mc,                  # markers
                   position=(4.5 + i * .5, 1.83, 12.27), scale=(.35, .06, .06))
        Entity(parent=self, model='cube', color=Color(.3, .3, .35, 1),   # wb eraser
               position=(6.6, 1.85, 12.27), scale=(.35, .12, .14))

        # wall clock above the boards
        Entity(parent=self, model='circle', position=(0, 5.3, 12.42), scale=.9,
               color=Color(.9, .9, .88, 1)).setLightOff()
        Entity(parent=self, model='circle', position=(0, 5.3, 12.43), scale=1,
               color=Color(.2, .2, .22, 1))
        Entity(parent=self, model='cube', position=(0, 5.42, 12.41),    # hands
               scale=(.045, .28, .02), color=Color(.15, .15, .18, 1)).setLightOff()
        Entity(parent=self, model='cube', position=(.1, 5.3, 12.41), rotation_z=90,
               scale=(.04, .2, .02), color=Color(.15, .15, .18, 1)).setLightOff()
        # alphabet strip above the chalkboard
        alpha = Text(parent=self, text='Aa  Bb  Cc  Dd  Ee  Ff  Gg  Hh  Ii  Jj',
                     position=(-3, 4.95, 12.4), scale=5, origin=(0, 0),
                     color=Color(1, .85, .4, .95))
        alpha.setLightOff()

        # bookshelf along the back wall
        shelf_x = 8
        self.make_box((shelf_x, 1.5, -12.1), (4.4, 3, .7), Color(.42, .3, .2, 1))
        for level in (0.62, 1.55, 2.48):
            self.make_box((shelf_x, level, -11.9), (4.2, .08, .5),
                          Color(.55, .4, .28, 1), collider=None)
            bx = shelf_x - 1.9
            while bx < shelf_x + 1.9:
                bw = random.uniform(.12, .22)
                bh = random.uniform(.5, .75)
                Entity(parent=self, model='cube', position=(bx, level + bh / 2 + .05, -11.9),
                       scale=(bw, bh, .4),
                       color=Color(random.uniform(.2, .8), random.uniform(.2, .6),
                                   random.uniform(.2, .7), 1))
                bx += bw + .04

        # door at the back with frame, window and handle
        self.make_box((-10, 1.6, -12.35), (1.9, 3.2, .18), Color(.55, .42, .3, 1),
                      collider=None)
        self.make_box((-10, 1.5, -12.4), (1.6, 3, .2), Color(.4, .28, .18, 1),
                      collider=None)
        win = Entity(parent=self, model='quad', position=(-10, 2.2, -12.28),
                     scale=(.7, .9), color=Color(.7, .82, .9, 1))
        win.setLightOff()
        Entity(parent=self, model='sphere', position=(-9.45, 1.4, -12.25),
               scale=.09, color=Color(.75, .7, .3, 1)).setLightOff()

        # floor life: scuff marks, a dropped pencil, paper scraps
        from . import world as _w
        _w.ground_details(self, area=(26, 22), y=.02, cracks=0, pebbles=0, scraps=2)
        for _ in range(8):
            Entity(parent=self, model='quad', rotation_x=90,
                   rotation_y=random.uniform(0, 180),
                   position=(random.uniform(-12, 12), .015, random.uniform(-11, 11)),
                   scale=(random.uniform(.3, .8), random.uniform(.04, .08)),
                   color=Color(0, 0, 0, .18))
        Entity(parent=self, model='cube', color=Color(.9, .75, .2, 1),   # dropped pencil
               position=(3.2, .05, -1.5), rotation_y=40, scale=(.5, .04, .04))

        # teacher desk with legs, chair, and clutter
        self.make_box((0, 1.05, 9.5), (4, .18, 1.6), Color(.5, .36, .22, 1))
        for lx, lz in [(-1.8, 9), (1.8, 9), (-1.8, 10), (1.8, 10)]:
            self.make_box((lx, .5, lz), (.15, 1, .15), Color(.35, .25, .15, 1),
                          collider=None)
        self.make_box((0, .55, 10.8), (.9, .08, .8), Color(.3, .25, .35, 1),  # chair
                      collider=None)
        self.make_box((0, 1.05, 11.2), (.9, .9, .08), Color(.3, .25, .35, 1),
                      collider=None)
        stack = Entity(parent=self, model='cube', color=Color(.9, .9, .88, 1),  # papers
                       position=(-1.2, 1.2, 9.5), scale=(.7, .12, .5))
        stack.setLightOff()
        Entity(parent=self, model='cube', color=Color(.7, .2, .2, 1),    # apple-ish
               position=(1.3, 1.25, 9.3), scale=(.18, .18, .18))
        Entity(parent=self, model='cube', color=Color(.2, .25, .3, 1),   # laptop base
               position=(.3, 1.17, 9.5), scale=(.75, .05, .5))
        Entity(parent=self, model='cube', color=Color(.25, .3, .38, 1),  # laptop lid
               position=(.3, 1.4, 9.72), rotation_x=-70, scale=(.75, .5, .04))
        # waste bin with crumpled paper
        self.make_box((-2.6, .35, 10.8), (.5, .7, .5), Color(.35, .37, .4, 1),
                      collider=None)
        for _ in range(2):
            ball = Entity(parent=self, model='sphere', color=Color(.92, .92, .88, 1),
                          position=(-2.6 + random.uniform(-.5, .5), .08,
                                    11.3 + random.uniform(0, .4)),
                          scale=.12)
            ball.setLightOff()

        self.teacher = self.add_npc(
            name='Ms. Rivera', position=(2.5, 0, 10),
            shirt=Color(.5, .35, .6, 1), expression='happy',
            lines=["Take your seat — the test is about to start.",
                   "You'll have 75 seconds for 5 questions.",
                   "Listen carefully. I sometimes give hints out loud."])

        student_names = ['Maya', 'Jonah', 'Priya', 'Leo']
        self.students = []

        def desk(x, z, top_color=Color(.55, .4, .26, 1), with_bag=True):
            self.make_box((x, .78, z), (1.5, .1, .9), top_color)          # top
            for lx, lz in [(-.65, -.35), (.65, -.35), (-.65, .35), (.65, .35)]:
                self.make_box((x + lx, .38, z + lz), (.09, .78, .09),
                              Color(.3, .3, .32, 1), collider=None)
            self.make_box((x, .45, z - 1.1), (.9, .08, .8),               # chair seat
                          Color(.4, .3, .2, 1), collider=None)
            self.make_box((x, .85, z - 1.45), (.9, .8, .08),              # chair back
                          Color(.4, .3, .2, 1), collider=None)
            for lx, lz in [(-.38, -.75), (.38, -.75), (-.38, -1.42), (.38, -1.42)]:
                self.make_box((x + lx, .22, z + lz), (.07, .45, .07),     # chair legs
                              Color(.25, .25, .27, 1), collider=None)
            # exam paper, notebook, pencil and eraser on the desk
            paper = Entity(parent=self, model='quad', rotation_x=90,
                           position=(x + .2, .84, z), scale=(.5, .65),
                           color=Color(.95, .95, .9, 1))
            paper.setLightOff()
            for row in range(4):                                          # writing lines
                line = Entity(parent=self, model='quad', rotation_x=90,
                              position=(x + .2, .845, z + .2 - row * .12),
                              scale=(.36, .02), color=Color(.4, .45, .6, .8))
                line.setLightOff()
            Entity(parent=self, model='cube', color=random.choice(
                       [Color(.7, .3, .3, 1), Color(.3, .4, .7, 1), Color(.3, .6, .4, 1)]),
                   position=(x - .45, .855, z + .1), rotation_y=random.uniform(-15, 15),
                   scale=(.42, .06, .55))                                 # notebook
            Entity(parent=self, model='cube', color=Color(.95, .8, .2, 1),
                   position=(x + .1, .87, z - .32), rotation_y=random.uniform(-40, 40),
                   scale=(.4, .035, .035))                                # pencil
            Entity(parent=self, model='cube', color=Color(.9, .5, .6, 1),
                   position=(x + .5, .87, z - .28), scale=(.1, .05, .06)) # eraser
            if with_bag:                                                  # backpack
                bag_c = random.choice([Color(.6, .25, .25, 1), Color(.25, .35, .6, 1),
                                       Color(.3, .5, .35, 1), Color(.45, .3, .5, 1)])
                bx, bz = x + random.choice((-1, 1)) * .95, z - 1.1
                self.make_box((bx, .3, bz), (.42, .55, .25), bag_c, collider=None)
                self.make_box((bx, .38, bz + .16), (.3, .28, .1),
                              Color(bag_c.x * .7, bag_c.y * .7, bag_c.z * .7, 1),
                              collider=None)
            # each desk gets its own clutter
            extras = random.sample(['bottle', 'ruler', 'case', 'book'], k=2)
            if 'bottle' in extras:
                Entity(parent=self, model='sphere', color=Color(.3, .55, .8, .9),
                       position=(x - .6, .95, z - .3), scale=(.09, .22, .09))
            if 'ruler' in extras:
                Entity(parent=self, model='cube', color=Color(.85, .8, .5, 1),
                       position=(x + .35, .855, z + .25), rotation_y=random.uniform(-25, 25),
                       scale=(.5, .015, .06))
            if 'case' in extras:
                Entity(parent=self, model='cube', color=random.choice(
                           [Color(.7, .4, .5, 1), Color(.4, .55, .7, 1)]),
                       position=(x - .5, .88, z - .25), scale=(.35, .1, .14))
            if 'book' in extras:                                          # open book
                for bs, br in ((-.11, 12), (.11, -12)):
                    page = Entity(parent=self, model='quad', rotation_x=90,
                                  rotation_y=br,
                                  position=(x + .45 + bs, .86, z + .05),
                                  scale=(.22, .3), color=Color(.96, .95, .9, 1))
                    page.setLightOff()

        def name_card(x, z, name):
            from ursina import Text
            card = Entity(parent=self, model='quad', position=(x, .92, z - .48),
                          rotation_x=-20, scale=(.5, .16), color=Color(.98, .97, .9, 1))
            card.setLightOff()
            label = Text(parent=self, text=name, position=(x, .93, z - .49),
                         rotation_x=-20, scale=4, origin=(0, 0),
                         color=Color(.2, .2, .3, 1))
            label.setLightOff()

        spots = [(-6, 2), (-2, 2), (2, 2), (6, 2), (-6, -3), (2, -3)]
        for i, (x, z) in enumerate(spots):
            desk(x, z)
            if i < 4:
                s = self.add_npc(name=student_names[i], position=(x, 0, z - 1.2),
                                 expression='focused',
                                 lines=['Shh — test time.',
                                        "This one's easy, we did it last week."])
                s.face(Vec3(x, 0, z + 5))
                self.students.append(s)
                name_card(x, z, student_names[i])

        # the player's desk, marked green
        desk(-2, -3, top_color=Color(.3, .65, .35, 1))
        name_card(-2, -3, 'YOU')
        self.player_desk = self.make_box((-2, .8, -3), (1.5, .12, .9),
                                         Color(.3, .68, .38, 1))
        marker = Entity(parent=self, model='diamond', color=Color(.4, 1, .5, 1),
                        scale=.3, position=(-2, 2, -3))
        marker.setLightOff()

        # ---- room dressing --------------------------------------------------
        from ursina import Text as _Text
        # world map poster on the back wall
        Entity(parent=self, model='quad', position=(0, 3.4, -12.35), rotation_y=180,
               scale=(3.6, 2.4), color=Color(.55, .7, .85, 1))
        for _ in range(6):                                               # landmasses
            Entity(parent=self, model='sphere',
                   position=(random.uniform(-1.4, 1.4), 3.4 + random.uniform(-.8, .8),
                             -12.32),
                   scale=(random.uniform(.3, .7), random.uniform(.2, .45), .02),
                   color=Color(.4, .6, .35, 1))
        # bulletin board with pinned notes
        Entity(parent=self, model='quad', position=(-5, 3.4, -12.35), rotation_y=180,
               scale=(2.6, 1.8), color=Color(.55, .4, .3, 1))
        for _ in range(6):
            note = Entity(parent=self, model='quad', rotation_y=180,
                          position=(-5 + random.uniform(-1, 1),
                                    3.4 + random.uniform(-.6, .6), -12.32),
                          rotation_z=random.uniform(-12, 12), scale=(.4, .5),
                          color=random.choice([Color(.95, .95, .8, 1),
                                               Color(.85, .95, .85, 1),
                                               Color(.95, .85, .85, 1)]))
            note.setLightOff()
        # coat hooks with hanging jackets, next to the door
        for i in range(4):
            hx = -7.5 + i * .8
            self.make_box((hx, 2.4, -12.3), (.08, .08, .12), Color(.6, .6, .65, 1),
                          collider=None)
            if random.random() < .7:
                jc = random.choice([Color(.5, .25, .25, 1), Color(.25, .3, .5, 1),
                                    Color(.3, .45, .3, 1)])
                self.make_box((hx, 1.9, -12.25), (.45, .95, .12), jc, collider=None)
        # radiators under the windows
        for wz in (-5.5, 4.5):
            self.make_box((14.3, .6, wz), (.25, 1, 2.6), Color(.8, .8, .78, 1),
                          collider=None)
            for fin in range(5):
                self.make_box((14.28, .6, wz - 1 + fin * .5), (.28, .9, .08),
                              Color(.7, .7, .68, 1), collider=None)
        # glowing EXIT sign above the door
        exit_sign = Entity(parent=self, model='quad', position=(-10, 3.4, -12.3),
                           rotation_y=180, scale=(.9, .35), color=Color(.1, .45, .2, 1))
        exit_sign.setLightOff()
        exit_text = _Text(parent=self, text='EXIT', position=(-10, 3.4, -12.28),
                          rotation_y=180, scale=6, origin=(0, 0),
                          color=Color(.6, 1, .7, 1))
        exit_text.setLightOff()
        # corner plant
        self.make_box((13.8, .35, -11.8), (.5, .7, .5), Color(.5, .35, .25, 1),
                      collider=None)
        for _ in range(3):
            Entity(parent=self, model='sphere', color=Color(.25, .5, .28, 1),
                   position=(13.8 + random.uniform(-.15, .15), 1.1 + random.uniform(0, .3),
                             -11.8 + random.uniform(-.15, .15)),
                   scale=random.uniform(.3, .5))

        mocker = self.setup_mockery(spawn_pos=(2, 0, -4.4))
        if mocker:
            mocker.face(Vec3(-2, 0, -3))            # smirking at your desk

        self.t = 0
        self.test = None
        self.handins = [(20, 0), (35, 1), (50, 2)]  # (time, student index)
        self.set_objective('Find the GREEN desk and press E to start the test')

    def tick(self):
        self.t += time.dt
        if self.test:
            self.tick_mockery(self.t - self.test_start)

        near_desk = distance_xz(self.player.position, self.player_desk.position) < 2.2
        if near_desk and not self.test and not self.dialogue.enabled:
            self.interact_hint.text = '[E] sit down and start the test'

        if self.test:
            self.test.tick(time.dt, self.effects)
            if not self.test:  # tick may have ended the test
                return
            # verbal hint for question 4 — deaf players never receive it
            if not getattr(self, 'hint_given', False) and self.test.timer < 55:
                self.hint_given = True
                self.announcer.sound('Ms. Rivera: "for the announced question, the answer is B."', 6)
            for when, idx in self.handins[:]:
                if self.t - self.test_start >= when:
                    self.handins.remove((when, idx))
                    s = self.students[idx]
                    s.sprint_to((2.5, 0, 9), speed=4)
                    self.announcer.visual(f'{s.npc_name} handed in their paper. Perfect score.', 4,
                                          Color(.6, 1, .7, 1))

    def input(self, key):
        if self.test and not self.finished:
            # TestUI is an entity, so ursina already delivers keys to it
            # directly — forwarding here would grade every answer twice
            if key == 'escape':
                self.exit_to_menu()
            return
        super().input(key)
        if key == 'e' and not self.test and not self.dialogue.enabled:
            if distance_xz(self.player.position, self.player_desk.position) < 2.2:
                self.start_test()

    def start_test(self):
        from .audio import get_audio
        get_audio().play('bell', volume=.5)
        self.player.enabled = False
        mouse.locked = False
        self.test_start = self.t
        self.set_objective('Answer with keys 1 / 2 / 3 — V toggles accommodations')
        self.test = TestUI(on_finish=self.end_test)

    def end_test(self, score, total):
        passed = score >= 3
        destroy(self.test)
        self.test = None
        self.finish(
            'TEST PASSED' if passed else 'TEST FAILED',
            f'You scored {score} / {total}.\n'
            f'Your classmates finished in half the time with perfect scores.',
            success=passed)


class TestUI(Entity):
    """The exam panel: 5 questions, keys 1/2/3, 75 second timer."""

    def __init__(self, on_finish, **kwargs):
        super().__init__(parent=camera.ui, **kwargs)
        self.on_finish = on_finish
        self.q_index = 0
        self.score = 0
        self.timer = 75
        self.accommodations = False
        self.rescramble = 0

        Entity(parent=self, model='quad', color=Color(.05, .08, .1, .92),
               scale=(1, .7), y=.05, z=1)
        self.timer_text = Text(parent=self, text='', position=(.36, .34), scale=1.2,
                               color=Color(1, .8, .3, 1))
        self.progress = Text(parent=self, text='', position=(-.44, .34), scale=1,
                             color=Color(.7, .9, .7, 1))
        self.q_text = Text(parent=self, text='', origin=(0, 0), y=.2, scale=1.3,
                           color=Color(1, 1, 1, 1))
        self.opts = [Text(parent=self, text='', origin=(0, 0), y=.08 - i * .08,
                          scale=1.1, color=Color(.85, .85, .95, 1)) for i in range(3)]
        self.fake_opt = Text(parent=self, text='', origin=(0, 0), y=-.19, scale=1,
                             color=Color(.7, .45, .9, .9))
        self.feedback = Text(parent=self, text='', origin=(0, 0), y=-.27, scale=1.1,
                             color=Color(1, 1, 1, 1))

    def tick(self, dt, effects):
        self.timer -= dt
        if self.timer <= 0:
            self.on_finish(self.score, len(QUESTIONS))
            return
        self.timer_text.text = f'{int(self.timer)}s'
        self.progress.text = f'question {self.q_index + 1} / {len(QUESTIONS)}'

        q, options, _ = QUESTIONS[self.q_index]
        opt_lines = [f'{i + 1})  {o}' for i, o in enumerate(options)]

        if STATE.disability == 'adhd' and not effects.focused:
            self.q_text.text = '. . . your mind is somewhere else . . .'
            for t in self.opts:
                t.text = ''
            return

        if STATE.disability == 'dyslexia' and not self.accommodations:
            self.rescramble -= dt
            if self.rescramble <= 0:
                self.rescramble = .4
                self._q_cache = dyslexify(q)
                self._o_cache = [dyslexify(o) for o in opt_lines]
            q, opt_lines = self._q_cache, self._o_cache

        alpha = 1.0
        if STATE.disability == 'visual' and not self.accommodations:
            alpha = max(.06, 1 - STATE.blindness * 1.05)

        scale = 1.6 if self.accommodations else 1.3
        self.q_text.text = q
        self.q_text.scale = scale
        self.q_text.color = Color(1, 1, 1, alpha)
        for t, line in zip(self.opts, opt_lines):
            t.text = line
            t.color = Color(.85, .85, .95, alpha)

        if STATE.disability == 'schizophrenia' and random.random() < .004:
            self.fake_opt.text = f'4)  {random.choice(FAKE_OPTIONS)}'
        elif random.random() < .01:
            self.fake_opt.text = ''

    def input(self, key):
        if key == 'v':
            self.accommodations = not self.accommodations
            self.feedback.text = ('accommodations ON: large print, plain layout, screen reader'
                                  if self.accommodations else 'accommodations OFF')
            self.feedback.color = Color(.5, .9, 1, 1)
            return
        if key in ('1', '2', '3'):
            _, options, correct = QUESTIONS[self.q_index]
            if int(key) - 1 == correct:
                self.score += 1
                self.feedback.text = 'correct!'
                self.feedback.color = Color(.4, .95, .5, 1)
            else:
                self.feedback.text = f'wrong — the answer was {correct + 1}) {options[correct]}'
                self.feedback.color = Color(.95, .4, .4, 1)
            self.q_index += 1
            self.fake_opt.text = ''
            if self.q_index >= len(QUESTIONS):
                self.on_finish(self.score, len(QUESTIONS))
