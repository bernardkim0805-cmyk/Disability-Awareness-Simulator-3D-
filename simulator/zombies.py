"""Scenario: night street — reach the safehouse before the zombies reach you."""
import random

from ursina import Entity, Color, Vec3, time, distance_xz

from .base_scenario import BaseScenario
from .config import STATE
from .npc import NPC

ZOMBIE_SPEED = 2.5
SAFEHOUSE = Vec3(0, 0, 62)


class Zombie(NPC):
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
        # permanently gaping jaw
        self.mouth_open_hole.scale = (.05, .055, .012)
        self.mouth_open_hole.y = -.095
        self.teeth.scale = (.042, .012, .008)
        self.teeth.color = Color(.75, .7, .55, 1)        # yellowed teeth
        self.lower_lip.y = -.128
        # head lolls to one side
        self.head.rotation_z = random.choice([-22, 17, 28])
        # rotting skin patches on face and body
        for _ in range(4):
            Entity(parent=self.head, model='sphere', color=rot,
                   scale=random.uniform(.03, .06),
                   position=(random.uniform(-.09, .09), random.uniform(-.06, .08),
                             .07 + random.uniform(0, .03)))
        for _ in range(3):                               # blood down the shirt
            Entity(parent=self.torso, model='cube', color=gore,
                   position=(random.uniform(-.12, .12), random.uniform(.15, .5), .105),
                   rotation_z=random.uniform(-30, 30),
                   scale=(random.uniform(.05, .1), random.uniform(.1, .28), .015))
        # gouged chest wound with exposed ribs
        if random.random() < .5:
            Entity(parent=self.torso, model='sphere', color=Color(.12, .03, .03, 1),
                   position=(.06, .4, .1), scale=(.12, .16, .05))
            for ry in (.34, .4, .46):
                Entity(parent=self.torso, model='cube', color=Color(.8, .75, .65, 1),
                       position=(.06, ry, .11), scale=(.11, .015, .01))
        # some have lost a forearm — a dark stump remains
        if random.random() < .4:
            arm = self.arms[random.choice(('l', 'r'))]
            arm[1].enabled = False
            Entity(parent=arm[0], model='sphere', color=gore, y=-.31,
                   scale=(.09, .05, .09))
        self.twitch_timer = random.uniform(1.5, 4)
        self.base_head_tilt = self.head.rotation_z
        self.marker.enabled = False
        self.lines = []
        self.groan_cooldown = 0

    def update(self):
        super().update()
        # sudden head twitches
        self.twitch_timer -= time.dt
        if self.twitch_timer <= 0:
            self.twitch_timer = random.uniform(1.5, 4)
            self.head.rotation_z = self.base_head_tilt + random.uniform(-25, 25)
        self.head.rotation_z += (self.base_head_tilt - self.head.rotation_z) * 2 * time.dt


class ZombieEscapeScenario(BaseScenario):
    player_start = (0, 0, -55)
    sky_color = Color(.03, .03, .08, 1)

    def build(self):
        from . import world
        self.lights = world.night_lights()
        world.night_sky(self)

        base = self.make_box((0, -.5, 0), (90, 1, 170), Color(.14, .14, .17, 1))
        world.road(self, (0, 0, 0), length=160, width=10, along='z')
        world.sidewalk(self, (-7.5, 0, 0), (5, 160))
        world.sidewalk(self, (7.5, 0, 0), (5, 160))

        for i, z in enumerate(range(-45, 56, 16)):                            # street lamps
            world.street_lamp(self, (-6, .2, z), on=i % 2 == 0)   # some are broken
            world.street_lamp(self, (6, .2, z + 8), on=True)
        for z in range(-45, 56, 15):                                          # buildings
            for x in (-22, 22):
                world.building(self, (x, 0, z), (11, 7 + (z % 9), 9),
                               style='brick' if (x + z) % 2 else 'concrete',
                               lit_ratio=.15,
                               tint=Color(.35, .33, .38, 1) if (x + z) % 2
                               else Color(.25, .27, .32, 1))
        for _ in range(10):                                                   # debris to dodge
            self.make_box((random.uniform(-10, 10), .5, random.uniform(-40, 50)),
                          (random.uniform(1, 2.5), 1, random.uniform(1, 2.5)),
                          Color(.2, .17, .14, 1))
        for pos in [(-11, 0, -30), (11, 0, 10), (-11, 0, 35)]:
            world.tree(self, pos, scale=random.uniform(.9, 1.2))

        world.ground_details(self, area=(20, 130), cracks=22, pebbles=20,
                             leaves=14, scraps=8)
        world.manhole(self, (2, 0, -20))
        world.manhole(self, (-2.5, 0, 25))
        for pos in [(-4, 0, -8), (3.5, 0, 30), (-3, 0, 48)]:
            world.puddle(self, pos, scale=random.uniform(1.4, 2.4))
        world.abandoned_car(self, (-6.5, 0, -18), rotation_y=8)
        world.abandoned_car(self, (6.5, 0, 22), rotation_y=-100)
        # a knocked-over bin spilling litter
        self.make_box((8.5, .3, -5), (.6, .6, .9), Color(.28, .3, .28, 1),
                      collider=None)
        world.ground_details(self, area=(4, 4), center=(8, -6.5), cracks=0,
                             pebbles=0, scraps=4)

        # the safehouse and its glowing green door
        house = self.make_box((0, 3, 68), (16, 6, 8), Color(.4, .36, .34, 1))
        house.texture = 'brick'
        house.texture_scale = (6, 2)
        self.make_box((0, 6.4, 68), (17, .8, 9), Color(.22, .2, .2, 1), collider=None)
        for wx in (-5, 5):                                                    # boarded windows
            Entity(parent=self, model='quad', position=(wx, 3.4, 63.95),
                   scale=(2, 1.6), color=Color(.28, .22, .16, 1))
        self.door = Entity(parent=self, model='quad', position=(0, 1.6, 63.9),
                           scale=(2.5, 3.2), color=Color(.2, 1, .4, 1))
        world.emissive(self.door)
        glow = Entity(parent=self, model='quad', position=(0, 1.8, 63.85), scale=6,
                      texture='radial_gradient', color=Color(.2, 1, .4, .25))
        world.emissive(glow)
        sign = Entity(parent=self, model='quad', position=(0, 4.4, 63.9),
                      scale=(3.4, .8), color=Color(.1, .5, .25, 1))
        world.emissive(sign)

        self.runners = [
            self.add_npc(name='Runner Sam', position=(-3, 0, -50), expression='worried',
                         lines=["They're coming. RUN.", "...why are you still here?!"]),
            self.add_npc(name='Runner Jo', position=(3, 0, -51), expression='surprised',
                         lines=['Just sprint! It\'s not hard!']),
        ]

        self.zombies = []
        for pos in [(-8, -82), (8, -85), (0, -90), (-18, -78), (18, -80)]:
            z = Zombie(parent=self, position=(pos[0], 0, pos[1]))
            self.zombies.append(z)

        self.setup_mockery()

        self.t = 0
        self.groan_timer = 0
        self.set_objective('Reach the glowing green door of the safehouse!')

    def tick(self):
        self.t += time.dt
        self.tick_mockery(self.t)

        if 3 < self.t < 3.2 and not getattr(self, 'runners_gone', False):
            self.runners_gone = True
            self.announcer.visual('"RUN!!" — the others sprint off without looking back', 5,
                                  Color(1, .7, .5, 1))
            for r in self.runners:
                r.sprint_to((random.uniform(-3, 3), 0, 61), speed=8, then_vanish=True)
        if self.t > 20 and not getattr(self, 'wave2', False):
            self.wave2 = True
            self.announcer.sound('*shuffling and groans, closing in from the sides*', 4,
                                 cue='groan')
            for pos in [(-25, self.player.position.z - 15), (25, self.player.position.z - 15)]:
                self.zombies.append(Zombie(parent=self, position=(pos[0], 0, pos[1])))

        for z in self.zombies:
            direction = self.player.position - z.position
            direction.y = 0
            d = direction.length()
            if d > .1:
                z.position += direction.normalized() * ZOMBIE_SPEED * time.dt
                z.look_at(Vec3(self.player.position.x, z.y, self.player.position.z))
                z.walking = True
            # sound cue when one is close behind — deaf players never get this
            behind = self.player.forward.dot(direction.normalized()) < -.3
            if d < 10 and behind and self.groan_timer <= 0:
                self.groan_timer = 4
                self.announcer.sound('*wet groaning, RIGHT behind you*', 2.5,
                                     Color(1, .4, .4, 1), cue='groan')
            if d < 1.4:
                self.finish('CAUGHT',
                            'They got you.\nThe others were already inside, watching '
                            'through the window.', success=False)
                return
        self.groan_timer -= time.dt

        if distance_xz(self.player.position, SAFEHOUSE) < 3.5:
            self.finish('SAFE',
                        f'You made it inside in {int(self.t)} seconds.\n'
                        'Now imagine that run was your daily commute.', success=True)
