"""Builds a lived-in modern home for the bedtime routine: master bedroom,
hallway, ensuite bathroom, walk-in closet and a laundry nook. Returns a dict
of interaction anchors (Vec3 the player must stand near) plus references to
objects that change state (lights, faucet, shower, toilet lid, curtains).

Everything is primitive-built but heavily dressed so the rooms read as
occupied rather than staged. `solid` colliders on furniture keep the player
from walking through it.
"""
if __package__ in (None, ''):
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import random

from ursina import Entity, Text, Color, Vec3

from .. import world


def _box(parent, pos, scale, color, collider='box', **kw):
    return Entity(parent=parent, model='cube', position=pos, scale=scale,
                  color=color, collider=collider, **kw)


def _lit(parent, pos, scale, color):
    e = Entity(parent=parent, model='cube', position=pos, scale=scale, color=color)
    e.setLightOff()
    return e


def build_house(s, night=True):
    """s is the scenario (an Entity). Returns the anchors/objects dict."""
    A = {}                      # anchors + stateful objects
    rng = random

    wall = Color(.86, .84, .8, 1)
    trim = Color(.7, .67, .62, 1)
    floor_wood = Color(.55, .4, .26, 1)
    tile = Color(.82, .84, .86, 1)

    # ============================================================ shell
    # Two rooms side by side + a hallway strip. Bedroom (left), bathroom
    # (right), closet (top-left), laundry (top-right), hallway between.
    #    x: bedroom -14..-1, hallway -1..1, bathroom 1..13
    #    z: main -10..8 ; closet/laundry 8..15
    floor = _box(s, (-1, -.5, 0), (30, 1, 20), floor_wood)
    floor.texture = 'white_cube'
    floor.texture_scale = (15, 10)
    _box(s, (0, 6, 0), (30, .4, 20), Color(.92, .92, .9, 1), collider=None)  # ceiling

    # outer walls
    for pos, sc in [((-1, 3, -10), (30, 6, .4)), ((-1, 3, 10), (30, 6, .4)),
                    ((-16, 3, 0), (.4, 6, 20)), ((14, 3, 0), (.4, 6, 20))]:
        _box(s, pos, sc, wall)
    # divider bedroom|bathroom with a doorway gap (hallway)
    _box(s, (0, 3, -6.5), (.4, 6, 7), wall)          # lower divider
    _box(s, (0, 3, 6.5), (.4, 6, 7), wall)           # upper divider
    # back rooms wall (closet/laundry) with door gaps
    _box(s, (-8, 3, 8), (12, 6, .4), wall)
    _box(s, (7, 3, 8), (10, 6, .4), wall)

    _build_bedroom(s, A, night)
    _build_bathroom(s, A, night)
    _build_hallway(s, A)
    _build_closet(s, A)
    _build_laundry(s, A)
    _lights(s, A, night)
    return A


# ------------------------------------------------------------------ bedroom
def _build_bedroom(s, A, night):
    room = Color(.55, .4, .26, 1)
    # queen bed with headboard, mattress, duvet, two pillows
    bed = Entity(parent=s, position=(-11, 0, -5))
    _box(bed, (0, .35, 0), (4.2, .6, 5), Color(.4, .3, .2, 1))          # frame
    _box(bed, (0, .7, -2.6), (4.2, 1.4, .3), Color(.45, .32, .22, 1))   # headboard
    _box(bed, (0, .75, .2), (3.9, .35, 4.4), Color(.9, .88, .82, 1))    # duvet
    _box(bed, (0, .95, -1.6), (3.9, .3, 1.1), Color(.75, .8, .9, 1))    # folded blanket
    for px in (-1.1, 1.1):                                               # pillows
        _box(bed, (px, 1.0, -1.9), (1.5, .3, .8), Color(.97, .97, .95, 1))
    A['bed'] = Vec3(-11, 0, -1.8)

    # two bedside tables + lamps + alarm clock + phone charger
    for sx, tag in ((-13.4, 'l'), (-8.6, 'r')):
        _box(s, (sx, .55, -6.6), (1.4, 1.1, 1.2), Color(.5, .36, .24, 1))
        base = _lit(s, (sx, 1.5, -6.6), (.15, .8, .15), Color(.5, .45, .4, 1))
        shade = _lit(s, (sx, 2.05, -6.6), (.7, .5, .7),
                     Color(1, .92, .7, 1) if night else Color(.85, .82, .78, 1))
        A[f'lamp_{tag}'] = shade
    A['alarm'] = _lit(s, (-13.4, 1.2, -6.6), (.5, .3, .3), Color(.1, .1, .12, 1))
    Text(parent=A['alarm'], text='9:47', scale=6, origin=(0, 0), z=-.55,
         color=Color(.9, .2, .2, 1)).setLightOff()
    A['alarm_pos'] = Vec3(-13.4, 0, -6.6)
    A['charger'] = _box(s, (-8.6, 1.18, -6.6), (.5, .05, .3), Color(.15, .15, .18, 1),
                        collider=None)
    A['charger_pos'] = Vec3(-8.6, 0, -6.4)

    # dresser + mirror + framed photos + tv on wall + bookshelf
    _box(s, (-15.3, .8, 2), (1, 1.6, 4), Color(.5, .36, .24, 1))
    mir = _lit(s, (-15.75, 2.4, 2), (.1, 2.4, 3), Color(.6, .75, .85, 1))  # mirror
    A['mirror_bed'] = mir
    for pz in (-2, 0, 2):                                              # wall photos
        Entity(parent=s, model='quad', rotation_y=90, position=(-15.75, 3.8, pz),
               scale=(1.2, 1.5), color=random.choice(
                   [Color(.7, .75, .8, 1), Color(.8, .7, .6, 1)])).setLightOff()
    tv = _lit(s, (-11, 3.6, -9.7), (4, 2.3, .2), Color(.05, .05, .07, 1))
    A['tv'] = tv
    shelf = _box(s, (-15.2, 2, 6), (1.2, 4, 3.5), Color(.45, .32, .22, 1))
    for lvl in (1, 2.4, 3.6):                                         # books
        bx = 4.6
        while bx < 7.2:
            bw = random.uniform(.12, .2)
            _lit(s, (-15.4, lvl + .35, bx), (.4, .7, bw),
                 Color(random.uniform(.2, .8), random.uniform(.2, .6),
                       random.uniform(.2, .7), 1))
            bx += bw + .05
    # the book to read is on the near nightstand
    A['book'] = _box(s, (-13.4, 1.2, -6.2), (.5, .1, .35), Color(.6, .2, .25, 1),
                     collider=None)
    A['book_pos'] = Vec3(-13.4, 0, -6.0)

    # ceiling fan, window + curtains, rug, plant, laundry hamper
    fan = Entity(parent=s, position=(-11, 5.6, -3))
    for r in range(4):
        _lit(fan, (0, 0, 0), (2.4, .05, .2), Color(.4, .3, .2, 1)).rotation_y = r * 45
    win = _lit(s, (-11, 3.4, 9.7), (4, 2.6, .1),
               Color(.08, .08, .18, 1) if night else Color(.7, .85, 1, 1))
    A['window'] = win
    A['curtain_l'] = _box(s, (-12.8, 3.4, 9.5), (.3, 3, .3), Color(.5, .4, .55, 1),
                          collider=None)
    A['curtain_r'] = _box(s, (-9.2, 3.4, 9.5), (.3, 3, .3), Color(.5, .4, .55, 1),
                          collider=None)
    A['curtains_open'] = False
    rug = Entity(parent=s, model='quad', rotation_x=90, position=(-11, .02, -1),
                 scale=(6, 7), color=Color(.35, .3, .45, 1))
    rug.setLightOff()
    Entity(parent=s, model='cube', position=(-15, .4, -8.5), scale=(.5, .8, .5),
           color=Color(.5, .35, .25, 1))
    Entity(parent=s, model='sphere', position=(-15, 1, -8.5), scale=(.7, .8, .7),
           color=Color(.25, .5, .28, 1))
    A['hamper'] = _box(s, (-8, .45, 3), (1, .9, 1), Color(.6, .55, .45, 1),
                       collider=None)
    A['hamper_pos'] = Vec3(-8, 0, 3)
    A['glass'] = None    # filled at the bathroom sink; placed on nightstand later


# ------------------------------------------------------------------ bathroom
def _build_bathroom(s, A, night):
    tile = Color(.82, .84, .86, 1)
    ftile = _box(s, (7, -.45, 0), (12, .1, 19.4), Color(.75, .78, .8, 1),
                 collider=None)
    ftile.texture = 'white_cube'
    ftile.texture_scale = (8, 12)
    A['bath_mat'] = Entity(parent=s, model='quad', rotation_x=90,
                           position=(4.5, .03, -3), scale=(2, 2.6),
                           color=Color(.5, .55, .65, 1))
    A['bath_mat'].setLightOff()

    # vanity: counter, two sinks region (one sink), faucet, mirror, cabinet
    _box(s, (5, .9, -8), (5, .3, 2), Color(.9, .9, .88, 1))           # counter
    _box(s, (5, .45, -8), (5, .9, 1.8), Color(.4, .3, .25, 1))        # cabinet body
    for dx in (-1.5, 1.5):                                            # drawers
        _box(s, (5 + dx, .45, -7.1), (1.3, .7, .1), Color(.5, .38, .3, 1),
             collider=None)
    A['sink'] = _lit(s, (5, 1.02, -8), (1.4, .12, 1.2), Color(.95, .95, .93, 1))
    A['faucet'] = _lit(s, (5, 1.25, -8.5), (.12, .4, .12), Color(.75, .78, .8, 1))
    A['faucet_on'] = False
    A['faucet_stream'] = _lit(s, (5, 1.0, -8.4), (.05, .5, .05), Color(.7, .85, 1, .6))
    A['faucet_stream'].enabled = False
    A['sink_pos'] = Vec3(5, 0, -6.6)
    # mirror + medicine cabinet + fog overlay
    A['mirror'] = _lit(s, (5, 3, -8.9), (3, 2.4, .1), Color(.6, .72, .82, 1))
    A['mirror_fog'] = _lit(s, (5, 3, -8.82), (3, 2.4, .02), Color(.85, .9, .92, 0))
    A['med_cabinet'] = _box(s, (7.2, 3, -8.85), (1.4, 1.8, .2), Color(.85, .85, .82, 1),
                            collider=None)
    A['cabinet_open'] = False
    # counter clutter: labelled toiletries (similar-looking bottles!)
    A['products'] = {}
    labels = [('toothpaste', Color(.3, .6, .9, 1)), ('cleanser', Color(.9, .5, .5, 1)),
              ('moisturizer', Color(.7, .8, .6, 1)), ('mouthwash', Color(.4, .8, .7, 1))]
    for i, (name, col) in enumerate(labels):
        b = _box(s, (3.3 + i * .55, 1.28, -8), (.28, .55, .28), col, collider=None)
        A['products'][name] = b
    A['toothbrush'] = _box(s, (6.3, 1.2, -8), (.08, .5, .08), Color(.2, .6, .8, 1),
                           collider=None)
    A['floss'] = _box(s, (6.6, 1.15, -8), (.25, .12, .25), Color(.9, .9, .95, 1),
                      collider=None)
    A['razor'] = _box(s, (6.9, 1.15, -8), (.1, .4, .06), Color(.3, .3, .35, 1),
                      collider=None)
    A['hairbrush'] = _box(s, (3, 1.18, -7.4), (.3, .1, .6), Color(.4, .25, .2, 1),
                          collider=None)
    # towels on a rack + hand towel
    _box(s, (11.5, 2.4, -6), (.1, .1, 3), Color(.6, .6, .6, 1), collider=None)
    A['towel'] = _box(s, (11.4, 1.8, -6), (.2, 1.4, 1.6), Color(.5, .7, .8, 1),
                      collider=None)
    A['towel_pos'] = Vec3(10.4, 0, -6)
    A['towel_hung'] = True

    # toilet with lid
    _box(s, (11, .4, 2), (1.2, .8, 1.4), Color(.95, .95, .93, 1))     # bowl
    _box(s, (11, 1.1, 2.6), (1.2, .7, .5), Color(.95, .95, .93, 1))   # tank
    A['toilet_lid'] = _box(s, (11, .85, 1.9), (1.1, .1, 1.2),
                           Color(.9, .9, .88, 1), collider=None)
    A['toilet_pos'] = Vec3(9.7, 0, 2)
    A['toilet_flushed'] = True
    A['toilet_used'] = False
    # toilet paper + trash + plant
    _box(s, (12.4, 1.3, 1.2), (.3, .3, .2), Color(.9, .9, .9, 1), collider=None)
    _box(s, (12.6, .4, 3), (.5, .8, .5), Color(.4, .42, .45, 1), collider=None)

    # shower stall: base, glass walls, sliding door, head, controls, steam
    _box(s, (10.5, .1, -3), (4, .2, 4), Color(.8, .82, .84, 1), collider=None)  # base
    for pos, sc in [((8.6, 3, -3), (.2, 6, 4)), ((10.5, 3, -1.1), (4, 6, .2))]:
        g = _box(s, pos, sc, Color(.7, .82, .88, .35), collider=None)
    A['shower_door'] = _box(s, (11.5, 3, -4.9), (2, 6, .2), Color(.7, .82, .88, .4),
                            collider=None)
    A['shower_door_open'] = False
    A['showerhead'] = _lit(s, (9, 5, -3), (.4, .3, .4), Color(.75, .78, .8, 1))
    A['shower_stream'] = _lit(s, (9, 3, -3), (.6, 3.5, .6), Color(.7, .85, 1, .4))
    A['shower_stream'].enabled = False
    # hot/cold controls (unlabeled shapes — hard with low vision, by design)
    A['ctrl_hot'] = _box(s, (8.7, 2.6, -1.3), (.25, .25, .25), Color(.85, .3, .3, 1),
                         collider=None)
    A['ctrl_cold'] = _box(s, (9.3, 2.6, -1.3), (.25, .25, .25), Color(.3, .5, .85, 1),
                          collider=None)
    A['shower_pos'] = Vec3(10.5, 0, -3)
    A['steam'] = 0.0


# ------------------------------------------------------------------ hallway
def _build_hallway(s, A):
    _box(s, (0, 3, 0), (2, 6, .1), Color(.8, .78, .74, 0), collider=None)
    # a runner rug + wall art + a doorway light switch anchor
    r = Entity(parent=s, model='quad', rotation_x=90, position=(0, .02, 2),
               scale=(1.6, 6), color=Color(.4, .35, .3, 1))
    r.setLightOff()
    Entity(parent=s, model='quad', rotation_y=90, position=(.19, 3.6, 4),
           scale=(1.4, 1), color=Color(.6, .65, .7, 1)).setLightOff()
    A['door_lock'] = _box(s, (0, 1.4, -9.6), (.9, 1.9, .15), Color(.4, .3, .22, 1),
                          collider=None)
    A['door_pos'] = Vec3(0, 0, -8.6)
    A['door_locked'] = False


# ------------------------------------------------------------------ closet
def _build_closet(s, A):
    # walk-in closet top-left: rails of clothes, shelves, pajamas
    _box(s, (-13, 3.2, 8.2), (.1, .1, 6), Color(.6, .6, .6, 1), collider=None)
    for i in range(8):
        _box(s, (-14 + i * .6, 2.6, 11), (.5, 1.4, .2),
             Color(random.uniform(.2, .8), random.uniform(.2, .7),
                   random.uniform(.2, .8), 1), collider=None)
    A['pajamas'] = _box(s, (-11, 1.3, 12), (.7, .6, .5), Color(.35, .5, .7, 1),
                        collider=None)
    A['pajamas_pos'] = Vec3(-11, 0, 10.5)
    A['pajamas_on'] = False
    Text(parent=s, text='CLOSET', position=(-11, 5, 8.4), origin=(0, 0), scale=8,
         billboard=True, color=Color(.8, .8, .85, 1)).setLightOff()


# ------------------------------------------------------------------ laundry
def _build_laundry(s, A):
    # laundry nook top-right: washer, dryer, basket, medication organizer shelf
    _box(s, (9, 1, 12), (2, 2, 2), Color(.85, .87, .9, 1))            # washer
    _box(s, (11.5, 1, 12), (2, 2, 2), Color(.8, .82, .85, 1))         # dryer
    _lit(s, (9, 1.1, 10.95), (1.2, 1.2, .05), Color(.2, .25, .3, 1))  # washer door
    A['meds'] = _box(s, (6.5, 1.4, 12), (.8, .3, .5), Color(.9, .85, .4, 1),
                     collider=None)
    A['meds_pos'] = Vec3(6.5, 0, 10.6)
    A['meds_taken'] = False
    Text(parent=s, text='LAUNDRY', position=(10, 5, 8.4), origin=(0, 0), scale=8,
         billboard=True, color=Color(.8, .8, .85, 1)).setLightOff()


# ------------------------------------------------------------------ lights
def _lights(s, A, night):
    if night:
        s.lights = world.SceneLights(ambient=(.32, .3, .34), sun=(.35, .33, .4),
                                     sun_hpr=(30, -60, 0))
    else:
        s.lights = world.indoor_lights()
    A['bedroom_ceiling'] = _lit(s, (-11, 5.7, 0), (3, .2, 3),
                                Color(1, .97, .9, 1))
    A['bath_ceiling'] = _lit(s, (7, 5.7, -3), (3, .2, 3), Color(1, .98, .95, 1))
    A['bedroom_light_on'] = True
    A['bath_light_on'] = True
