"""Living City: a sandbox that showcases the autonomous crowd. Walk among
NPCs living independent lives, then trigger world events (C = crash, P =
police, G = shout) and watch each agent decide its own reaction based on
personality, curiosity, emotion and memory. Talk to anyone with E."""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import random

from ursina import Entity, Text, Color, Vec3, camera, distance_xz, destroy

from ..base_scenario import BaseScenario
from .. import world
from .crowd import AgentManager

BOUNDS = (34, 34)


class LivingCityScenario(BaseScenario):
    player_start = (0, 0, -20)

    def build(self):
        self.lights = world.day_lights()
        ground = self.make_box((0, -.5, 0), (BOUNDS[0] * 2 + 12, 1,
                                             BOUNDS[1] * 2 + 12),
                               Color(.55, .56, .55, 1))
        ground.texture = 'white_cube'
        ground.texture_scale = (24, 24)

        # a small district: plaza, shops, benches, a bus stop, a landmark
        pois = dict(shop=[], bench=[], stop=[], food=[], landmark=[], work=[])
        world.fountain(self, (0, 0, 0))
        pois['landmark'].append(Vec3(0, 0, 6))
        for i, (x, z) in enumerate([(-22, 14), (22, 16), (-20, -18), (24, -12)]):
            world.building(self, (x, 0, z), (10, 9 + i * 2, 9),
                           style='brick' if i % 2 else 'concrete', lit_ratio=.4)
            pois['work'].append(Vec3(x, 0, z - 6))
            # shopfront windows to window-shop at
            pois['shop'].append(Vec3(x + (6 if x < 0 else -6), 0, z - 5))
        for pos in [(-8, 8), (8, -8), (10, 10), (-10, -8)]:
            world.bench(self, pos, rotation_y=random.choice((0, 90)))
            pois['bench'].append(Vec3(pos[0], 0, pos[1] + 1.5))
        for pos in [(-14, 0, 0), (14, 0, 2), (0, 0, -16)]:
            world.street_lamp(self, pos, on=False)
        world.sidewalk(self, (0, 0, 0), (10, BOUNDS[1] * 2))
        world.sidewalk(self, (0, 0, 0), (BOUNDS[0] * 2, 10))
        # bus stop
        self.make_box((-16, 2.6, 18), (5, .2, 3), Color(.3, .35, .4, 1),
                      collider=None)
        pois['stop'].append(Vec3(-16, 0, 16))
        pois['food'].append(Vec3(12, 0, 6))
        world.ground_details(self, area=(60, 60), cracks=10, pebbles=14,
                             leaves=18)

        # the crowd
        self.manager = AgentManager(count=26, world_bounds=BOUNDS, pois=pois,
                                    get_player=lambda: self.player, parent=self)

        self.wreck = None
        self.set_objective('A living crowd. Walk around · [E] talk · '
                           '[C] crash  [P] police  [G] shout')
        Text(parent=self.hud, text='Each NPC has its own personality, mood, '
                                   'memory and reactions — trigger an event and watch.',
             position=(0, -.42), origin=(0, 0), scale=.72,
             color=Color(.7, .75, .8, 1))

    def tick(self):
        # let the player greet whoever they face (emits a 'greet' event)
        near = self._nearest_agent()
        if near and not self.dialogue.enabled:
            self.interact_hint.text = f'[E] greet {near.profile.name} '\
                f'({near.profile.personality}, {near.profile.routine.replace("_", " ")})'

    def _nearest_agent(self):
        best, bd = None, 3.5
        for a in self.manager.agents:
            d = distance_xz(a.position, self.player.position)
            if d < bd:
                best, bd = a, d
        return best

    def input(self, key):
        if self.finished:
            return
        if key == 'escape':
            self.exit_to_menu()
            return
        if key == 'c':
            self._spawn_crash()
        elif key == 'p':
            self.manager.fire_event('police', self.player.position
                                    + self.player.forward * 8, intensity=1.4)
            self.announcer.visual('you flag down police — watch the crowd gather '
                                  'or scatter', 3)
        elif key == 'g':
            self.manager.fire_event('gunshot', self.player.position, intensity=1.3)
            self.announcer.visual('a shout/bang — everyone reacts by personality',
                                  3, Color(1, .6, .5, 1))
        elif key == 'e':
            a = self._nearest_agent()
            if a and not self.dialogue.enabled:
                self._greet(a)

    def _spawn_crash(self):
        pos = self.player.position + self.player.forward * 10
        pos.y = 0
        if self.wreck:
            destroy(self.wreck)
        self.wreck = Entity(parent=self, model='cube', position=pos + Vec3(0, .6, 0),
                            rotation_y=random.uniform(0, 60), scale=(2, 1.2, 4),
                            color=Color(.5, .12, .12, 1))
        Entity(parent=self.wreck, model='cube', y=.8, scale=(.9, .5, 1.6),
               color=Color(.3, .08, .08, 1))
        from ..audio import get_audio
        get_audio().play('drive_crash', volume=.6)
        camera.shake(duration=.5, magnitude=1.5)
        self.manager.fire_event('crash', pos, intensity=1.6)
        self.announcer.visual('CRASH — nearby NPCs decide: gawk, film, flee, '
                              'or check on it', 4, Color(1, .6, .4, 1))

    def _greet(self, agent):
        # emit a greet event, then show a personality-flavoured reply
        self.manager.fire_event('greet', agent.position, intensity=.4,
                                source=self.player)
        recognized = agent.memory.recognizes_player()
        agent.memory.see_player(self._now(), positive=True)
        pers = agent.profile.personality
        if recognized:
            line = random.choice(['Oh, you again! Hey.', 'Good to see you back.',
                                  'We keep running into each other!'])
            agent.emotion.bump(.25, .1)
            agent.gesture.play('wave')
        elif pers in ('shy', 'aloof'):
            line = random.choice(['...hi.', 'Um, hello.', '*nods, looks away*'])
            agent.emotion.bump(-.05, .15)
        elif pers in ('cheerful', 'confident'):
            line = random.choice(['Hey there! Lovely day.', 'Well hello!',
                                  'How are you doing?'])
            agent.emotion.bump(.2, .05)
            agent.gesture.play('wave')
        else:
            line = random.choice(['Hi.', 'Hey.', 'Can I help you?'])
        agent.face_toward(self.player.position)
        agent.movement.stop()
        self.player.enabled = False
        from ursina import mouse
        mouse.locked = False
        def done():
            self.player.enabled = True
            mouse.locked = True
        self.dialogue.say(agent.profile.name, [line], on_done=done,
                          speaker_entity=agent)

    def _now(self):
        from .agent import a_now
        return a_now()

    def cleanup(self):
        self.manager.cleanup()
        super().cleanup()
