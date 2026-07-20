"""Procedural per-agent identity. Rolling a profile draws from continuous
and categorical distributions so the combination space is effectively
unbounded — no two agents share a walk, temperament and routine.

All the tunable knobs the brief asked for live here as named fields
(walking_speed_variation, gesture_probability, eye_contact_frequency,
conversation_chance, emotional_reaction_strength, awareness_radius,
curiosity_level, social_distance), derived from personality so they stay
believable instead of purely random."""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import random
from dataclasses import dataclass, field

PERSONALITIES = ['confident', 'shy', 'aggressive', 'cheerful', 'anxious',
                 'aloof', 'curious', 'tired']
ROUTINES = ['commute_to_work', 'shopping', 'meeting_friend', 'wait_transit',
            'exercising', 'grab_food', 'strolling', 'sightseeing']
BUILDS = ['slim', 'average', 'heavy', 'athletic']


@dataclass
class AgentProfile:
    name: str
    age: int
    personality: str
    routine: str
    build: str
    # ---- movement character -------------------------------------------------
    base_speed: float               # world-units/s at a normal walk
    walking_speed_variation: float  # +/- fraction jitter over time
    posture: float                  # 1 upright, <1 slouched/tired
    turn_rate: float                # deg/s the body can rotate (weight/momentum)
    # ---- social knobs -------------------------------------------------------
    gesture_probability: float
    eye_contact_frequency: float
    conversation_chance: float
    emotional_reaction_strength: float
    awareness_radius: float
    curiosity_level: float
    social_distance: float          # personal-space radius they defend
    # ---- baseline affect ----------------------------------------------------
    base_mood: float                # -1 sad .. +1 happy
    base_stress: float              # 0 calm .. 1 frazzled
    props: list = field(default_factory=list)   # 'phone' | 'coffee' | 'bag'


def roll_profile(rng=None, name=None):
    rng = rng or random
    pers = rng.choices(PERSONALITIES,
                       weights=[3, 2, 1, 3, 2, 2, 2, 2])[0]
    age = int(min(85, max(8, rng.gauss(36, 17))))
    build = rng.choice(BUILDS)

    # personality shapes the knobs so behaviour reads as intentional
    conf = {'confident': .9, 'aggressive': .85, 'cheerful': .7, 'curious': .6,
            'aloof': .5, 'tired': .4, 'anxious': .3, 'shy': .2}[pers]
    energy = {'cheerful': .85, 'confident': .75, 'aggressive': .8,
              'curious': .7, 'anxious': .6, 'aloof': .5, 'shy': .5,
              'tired': .3}[pers]

    old = age > 62
    child = age < 15
    speed = rng.uniform(2.0, 3.4) * (1 + (energy - .5) * .4)
    if old:
        speed *= .7
    if child:
        speed *= .85
    if build == 'heavy':
        speed *= .85
    if build == 'athletic':
        speed *= 1.12

    props = []
    if rng.random() < .5:
        props.append('phone')
    if rng.random() < .2:
        props.append('coffee')
    if rng.random() < .25:
        props.append('bag')

    return AgentProfile(
        name=name or _name(rng),
        age=age, personality=pers, routine=rng.choice(ROUTINES), build=build,
        base_speed=speed,
        walking_speed_variation=rng.uniform(.05, .25),
        posture=(.8 if old or pers == 'tired' else 1.0) - (build == 'heavy') * .04,
        turn_rate=rng.uniform(160, 320) * (.7 if old else 1),
        gesture_probability=conf * rng.uniform(.5, 1.1),
        eye_contact_frequency=conf * rng.uniform(.5, 1.0),
        conversation_chance=({'shy': .15, 'aloof': .2}.get(pers, .5)) * rng.uniform(.7, 1.2),
        emotional_reaction_strength=rng.uniform(.4, 1.0)
        * (1.3 if pers in ('anxious', 'cheerful') else 1),
        awareness_radius=rng.uniform(8, 18) * (1.3 if pers in ('anxious', 'curious') else 1),
        curiosity_level={'curious': .95, 'aloof': .2, 'tired': .3}.get(pers,
                        rng.uniform(.3, .7)),
        social_distance=rng.uniform(1.1, 2.2) * (1.4 if pers in ('shy', 'anxious') else 1),
        base_mood=({'cheerful': .5, 'confident': .35, 'tired': -.2,
                    'anxious': -.15, 'aggressive': -.1}.get(pers, 0))
        + rng.uniform(-.15, .15),
        base_stress={'anxious': .55, 'aggressive': .45, 'tired': .5}.get(pers, .2)
        + rng.uniform(0, .15),
        props=props,
    )


FIRST = ['Ava', 'Ben', 'Cara', 'Dev', 'Elle', 'Finn', 'Gia', 'Hugo', 'Ivy',
         'Jai', 'Kira', 'Leo', 'Mara', 'Noah', 'Omar', 'Pia', 'Quinn', 'Rue',
         'Sam', 'Tess', 'Uma', 'Vik', 'Wen', 'Xan', 'Yara', 'Zane']


def _name(rng):
    return rng.choice(FIRST)
