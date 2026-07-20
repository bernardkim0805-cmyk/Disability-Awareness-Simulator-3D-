"""The Agent: a Human rig plus the full component stack and an NPCController
that makes autonomous decisions. The controller is a lightweight behaviour
state machine — wander / routine / observe / socialize / react / flee — but
which state it picks, and how it performs it, is driven by the agent's
personality, emotion, memory and perceived events, so behaviour emerges
rather than being scripted."""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import random

from ursina import Entity, Text, Color, Vec3, destroy, time as utime

from ..human import Human, SKIN_TONES, HAIR_COLORS
from .profile import roll_profile
from .systems import (PerceptionSystem, EmotionSystem, MemorySystem,
                      MovementController, AnimationController,
                      FacialExpressionController, GestureController,
                      PhysicsInteractionSystem)
from .dialogue_engine import DialogueEngine


class Agent(Human):
    def __init__(self, profile=None, bus=None, world_bounds=(40, 40),
                 pois=None, rng=None, **kwargs):
        self.rng = rng or random
        self.profile = profile or roll_profile(self.rng)
        # body proportions reflect age/build
        p = self.profile
        skin = self.rng.choice(SKIN_TONES)
        super().__init__(skin=skin, **kwargs)
        if p.age < 15:
            self.scale *= .78
        elif p.age > 65:
            self.scale_y *= .95
        if p.build == 'heavy':
            self.scale_x *= 1.12
        elif p.build == 'slim':
            self.scale_x *= .92

        self.bus = bus
        self.world_bounds = world_bounds
        self.pois = pois or {}            # {'shop': [Vec3...], 'bench': [...], ...}

        # ---- components ------------------------------------------------------
        self.perception = PerceptionSystem(self)
        self.emotion = EmotionSystem(self)
        self.memory = MemorySystem(self)
        self.movement = MovementController(self)
        self.animation = AnimationController(self)
        self.facial = FacialExpressionController(self)
        self.gesture = GestureController(self)
        self.physics = PhysicsInteractionSystem(self)
        self.dialogue = DialogueEngine(self)
        self.controller = NPCController(self)

        # props the profile granted (approximate hand interaction)
        self._build_props()

        self.speech = None
        if bus:
            self._sub = bus.subscribe(lambda: self.position, self._on_event)

    def _build_props(self):
        p = self.profile
        if 'phone' in p.props:
            self.phone = Entity(parent=self.arms['r'][1], model='cube',
                                color=Color(.1, .1, .12, 1), y=-.3,
                                scale=(.07, .13, .02))
        if 'coffee' in p.props:
            Entity(parent=self.arms['l'][1], model='cube',
                   color=Color(.85, .82, .78, 1), y=-.3, scale=(.06, .1, .06))
        if 'bag' in p.props:
            self.bag = Entity(parent=self.torso, model='cube',
                              color=self.rng.choice([Color(.5, .25, .25, 1),
                                                     Color(.25, .35, .5, 1)]),
                              position=(.28, .3, -.1), scale=(.18, .3, .12))

    # ------------------------------------------------------------- rig helpers
    def say_line(self, text):
        self.talking = True
        if self.speech:
            destroy(self.speech)
        self.speech = Text(parent=self, text=text, y=2.35, origin=(0, 0),
                           scale=7, billboard=True, color=Color(1, 1, .95, 1))
        self.speech.setLightOff()
        destroy(self.speech, delay=1.6)

    def face_toward(self, target_pos):
        import math
        to = Vec3(target_pos.x, self.y, target_pos.z) - self.position
        if to.length() > .01:
            self.rotation_y = math.degrees(math.atan2(to.x, to.z))
            self.movement.heading = to.normalized()

    def _on_event(self, event, distance):
        self.controller.perceive_event(event, distance)

    # ------------------------------------------------------------------ update
    def agent_update(self, dt, agents, player):
        self.perception.update(dt, agents, player)
        self.emotion.update(dt)
        self.controller.update(dt)
        self.movement.update(dt)
        self.physics.update(dt)
        self.animation.update(dt)      # after movement/physics so gait matches
        self.facial.update(dt)
        self.gesture.update(dt)
        self.dialogue.update(dt)

    def destroy_agent(self):
        if self.bus and hasattr(self, '_sub'):
            self.bus.unsubscribe(self._sub)
        destroy(self)


class NPCController:
    """The decision brain. Runs a behaviour state machine whose transitions
    are weighted by personality, emotion, memory and perception. States:
      routine   — head to a point of interest that fits the day's routine
      wander    — amble to a random nearby spot
      observe   — pause to look at something (phone, storefront, event)
      socialize — approach and talk to a nearby agent
      react     — startle/gawk at an event
      flee      — move away from danger
    """

    def __init__(self, agent):
        self.a = agent
        self.state = 'routine'
        self.state_t = 0
        self.substate_timer = 0
        self._pick_routine_goal()

    # ------------------------------------------------------- event perception
    def perceive_event(self, event, distance):
        a = self.a
        a.memory.note_event(event.kind, a_now())
        strength = max(.1, 1 - distance / a.profile.awareness_radius)
        if event.kind in ('crash', 'gunshot'):
            a.emotion.bump(-.3, .8 * strength)
            a.physics.startle(event.position, strength)
            # personality decides: flee, gawk, or record
            curious = a.profile.curiosity_level
            if event.kind == 'gunshot' or a.profile.personality == 'anxious':
                self._enter('flee', danger=event.position)
            elif curious > .55:
                self._enter('react', focus=event.position)
            else:
                self._enter('flee', danger=event.position)
        elif event.kind == 'police':
            a.emotion.bump(-.05, .3 * strength)
            if a.profile.curiosity_level > .5:
                self._enter('react', focus=event.position)
        elif event.kind == 'greet' and event.source is not None:
            a.perception.focus = event.position

    # ------------------------------------------------------------------ states
    def _enter(self, state, **kw):
        self.state = state
        self.state_t = 0
        self._kw = kw
        if state == 'react':
            self.a.movement.stop()
            self.a.perception.focus = kw.get('focus')
            if 'phone' in self.a.profile.props and self.a.rng.random() < .5:
                self.a.gesture.play('point')      # recording / pointing
        elif state == 'flee':
            danger = kw['danger']
            away = (self.a.position - danger)
            away.y = 0
            if away.length() < .1:
                away = Vec3(1, 0, 0)
            goal = self.a.position + away.normalized() * 12
            self.a.movement.go_to(self._clamp(goal), run=True)
        elif state == 'observe':
            self.a.movement.stop()

    def update(self, dt):
        a = self.a
        self.state_t += dt
        if self.state == 'routine':
            self._update_routine(dt)
        elif self.state == 'wander':
            if a.movement.target is None:
                self._enter_default()
        elif self.state == 'observe':
            self._update_observe(dt)
        elif self.state == 'socialize':
            self._update_socialize(dt)
        elif self.state == 'react':
            if self.state_t > 3 + a.profile.curiosity_level * 3:
                self._enter_default()
        elif self.state == 'flee':
            if self.state_t > 4 and a.movement.target is None:
                a.emotion.bump(.1, -.3)
                self._enter_default()

    def _enter_default(self):
        self.state = 'routine'
        self.state_t = 0
        self._pick_routine_goal()

    def _update_routine(self, dt):
        a = self.a
        # spontaneous life: occasionally pause to observe / check phone / socialize
        self.substate_timer -= dt
        if self.substate_timer <= 0:
            self.substate_timer = a.rng.uniform(4, 10)
            r = a.rng.random()
            if r < a.profile.conversation_chance * .4 and a.perception.nearby:
                other = a.perception.nearby[0][0]
                if (other.position - a.position).length() < 5:
                    self._enter('socialize')
                    return
            if r < .55 and ('phone' in a.profile.props or a.profile.curiosity_level > .5):
                self._enter('observe')
                return
        if a.movement.target is None:
            self._pick_routine_goal()

    def _update_observe(self, dt):
        a = self.a
        if 'phone' in a.profile.props and a.rng.random() < .02:
            a.head.rotation_x = 18            # look down at phone
        dur = 1.5 + a.profile.curiosity_level * 3
        if self.state_t > dur:
            a.head.rotation_x = 0
            self._enter_default()

    def _update_socialize(self, dt):
        a = self.a
        if not a.perception.nearby:
            self._enter_default()
            return
        other, dist = a.perception.nearby[0]
        if dist > a.profile.social_distance + .8:
            a.movement.go_to(other.position)   # approach
        else:
            a.movement.stop()
            a.perception.focus = other.position + Vec3(0, 1.7, 0)
            if not a.dialogue.busy and not other.dialogue.busy \
                    and a.rng.random() < .04:
                a.dialogue.start_with(other)
                if a.rng.random() < a.profile.gesture_probability:
                    a.gesture.play(a.rng.choice(['shrug', 'point', 'wave']))
            if self.state_t > 6:
                self._enter_default()

    # --------------------------------------------------------------- goals
    def _pick_routine_goal(self):
        a = self.a
        pool = self._routine_pois()
        if pool and a.rng.random() < .7:
            self.a.movement.go_to(a.rng.choice(pool))
        else:
            self.state = 'wander'
            self.a.movement.go_to(self._random_point())

    def _routine_pois(self):
        a = self.a
        m = {'commute_to_work': 'work', 'shopping': 'shop',
             'meeting_friend': 'bench', 'wait_transit': 'stop',
             'grab_food': 'food', 'sightseeing': 'landmark'}
        key = m.get(a.profile.routine)
        return a.pois.get(key, [])

    def _random_point(self):
        a = self.a
        bx, bz = a.world_bounds
        return self._clamp(Vec3(a.rng.uniform(-bx, bx), a.y,
                                a.rng.uniform(-bz, bz)))

    def _clamp(self, p):
        bx, bz = self.a.world_bounds
        return Vec3(max(-bx, min(bx, p.x)), self.a.y, max(-bz, min(bz, p.z)))


# a tiny clock shared without importing scenario time
_CLOCK = [0.0]


def a_now():
    return _CLOCK[0]


def tick_clock(dt):
    _CLOCK[0] += dt
