"""Open-world generation and the modular world systems the brief names.

`build_open_world()` grows the existing downtown grid (city.build_city) into
an interconnected map: an outer HIGHWAY ring with on/off ramps, a lit TUNNEL
to the south, a BRIDGE over a river to the north, and three outlying
districts (suburbs, industrial, countryside) each with its own identity.
Everything is reachable by driving — no loading screens.

The named systems (WorldGeneration, RoadNetworkSystem, WeatherSystem,
NavigationSystem, PedestrianSystem, EnvironmentalInteractionSystem) are thin
facades so the architecture matches the design brief and stays swappable;
TrafficAI / PoliceSystem / EmergencyResponseSystem already live in
traffic.py / police.py.
"""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import math
import random

from ursina import Entity, Text, Color, Vec3

from .. import world
from . import city as citymod
from .config import WORLD, INFRA

B = WORLD['downtown_block']
RW = WORLD['road_width']
HWY = 200                       # highway ring half-extent


def _road(root, center, length, width, along, color=Color(.16, .16, .19, 1),
          dashes=True):
    world.road(root, center, length=length, width=width, along=along,
               dashes=dashes)


def build_open_world(root, night=False, rng=None):
    """Returns the enriched `places` dict used by the scenario."""
    rng = rng or random
    places = citymod.build_city(root, night=night)   # downtown core (unchanged)
    places['regions'] = WORLD['regions']

    _build_highway_ring(root, places, night)
    _build_tunnel(root, places, night)
    _build_bridge(root, places, night)
    _build_district(root, places, 'suburbs', rng)
    _build_district(root, places, 'industrial', rng)
    _build_district(root, places, 'countryside', rng)
    _connectors(root)
    return places


# --------------------------------------------------------------- highway ring
def _build_highway_ring(root, places, night):
    """A wide multi-lane loop around downtown with on/off ramps, guardrails,
    overhead signs and reflective lane markers."""
    ramps = []
    for sign_axis in ('z', 'x'):
        for side in (-1, 1):
            if sign_axis == 'z':
                center = (side * HWY, 0, 0)
                _road(root, center, HWY * 2 + RW, 16, 'z')
            else:
                center = (0, 0, side * HWY)
                _road(root, center, HWY * 2 + RW, 16, 'x')
    # lane reflectors + guardrails along the ring
    for t in range(-HWY, HWY + 1, 8):
        for side in (-1, 1):
            for base in ((side * HWY, t), (t, side * HWY)):
                r = Entity(parent=root, model='cube',
                           position=(base[0], .12, base[1]),
                           scale=(.2, .05, .2), color=Color(1, .85, .3, .9))
                r.setLightOff()
    for side in (-1, 1):                                   # guardrails / sound walls
        root_wall = Entity(parent=root, model='cube',
                           position=(side * (HWY + 9), 1.4, 0),
                           scale=(.5, 2.8, HWY * 2), color=Color(.4, .42, .45, 1),
                           collider='box')
        Entity(parent=root, model='cube', position=(0, 1.4, side * (HWY + 9)),
               scale=(HWY * 2, 2.8, .5), color=Color(.4, .42, .45, 1),
               collider='box')
    # on/off ramps connecting downtown to the ring on each side
    for (rx, rz, ax) in [(-HWY, -B, 'z'), (HWY, B, 'z'),
                         (-B, HWY, 'x'), (B, -HWY, 'x')]:
        if ax == 'z':
            _road(root, ((rx + (0 if rx < 0 else 0)) / 1, 0, rz), 40, 8, 'x',
                  dashes=False)
            mid = Vec3((rx + (-B if rx < 0 else B)) / 2, 0, rz)
        else:
            _road(root, (rx, 0, rz), 40, 8, 'z', dashes=False)
            mid = Vec3(rx, 0, (rz + (-B if rz < 0 else B)) / 2)
        ramps.append(mid)
    # overhead gantry signs
    for pos, txt in [((0, 6, HWY - 6), 'EXIT 4  DOWNTOWN'),
                     ((HWY - 6, 6, 0), 'EXIT 7  INDUSTRIAL'),
                     ((0, 6, -HWY + 6), 'TUNNEL  1 km'),
                     ((-HWY + 6, 6, 0), 'SUBURBS  NEXT RIGHT')]:
        for sx in (-8, 8):
            Entity(parent=root, model='cube', position=(pos[0] + sx, 3, pos[2]),
                   scale=(.4, 6, .4), color=Color(.35, .35, .4, 1))
        board = Entity(parent=root, model='cube', position=pos,
                       scale=(16, 1.8, .3), color=Color(.1, .15, .1, 1))
        t = Text(parent=root, text=txt, position=(pos[0], pos[1], pos[2] - .2),
                 origin=(0, 0), scale=7, color=Color(.4, 1, .5, 1))
        t.setLightOff()
    places['highway_ramps'] = ramps
    places['highway_half'] = HWY


# ---------------------------------------------------------------------- tunnel
def _build_tunnel(root, places, night):
    cfg = INFRA['tunnel']
    cx, cz = cfg['center']
    L = cfg['length']
    # the approach road from downtown down to the tunnel and on to the ring
    _road(root, (cx, 0, cz), L + 120, 12, 'z', dashes=True)
    # portal + shell (a covered box with interior lamps)
    for zoff in range(-L // 2, L // 2 + 1, 6):
        z = cz + zoff
        Entity(parent=root, model='cube', position=(cx, 5, z),
               scale=(16, .6, 6.2), color=Color(.3, .3, .34, 1))       # ceiling
        lamp = Entity(parent=root, model='cube', position=(cx, 4.7, z),
                      scale=(3, .12, .8), color=Color(1, .85, .5, 1))  # tunnel lamp
        lamp.setLightOff()
    for side in (-1, 1):
        Entity(parent=root, model='cube', position=(cx + side * 7, 2.6, cz),
               scale=(1, 5.2, L), color=Color(.35, .35, .4, 1), collider='box')
    # bright portal rings at each mouth
    for end in (-1, 1):
        Entity(parent=root, model='cube', position=(cx, 3.2, cz + end * L / 2),
               scale=(17, 6.6, 1.2), color=Color(.2, .2, .24, 1))
    places['tunnel'] = dict(center=Vec3(cx, 0, cz), half=L / 2, width=8,
                            darkness=cfg['darkness'], echo=cfg['echo'])


# ---------------------------------------------------------------------- bridge
def _build_bridge(root, places, night):
    cfg = INFRA['bridge']
    cx, cz = cfg['center']
    L = cfg['length']
    wy = cfg['water_y']
    # the river below (and the world under the bridge: water + a boat + rail)
    Entity(parent=root, model='cube', position=(cx, wy + .2, cz),
           scale=(200, .4, 46), color=Color(.2, .35, .5, .9)).setLightOff()
    Entity(parent=root, model='cube', position=(cx - 40, wy + 1, cz + 6),
           scale=(8, 2, 3), color=Color(.6, .5, .35, 1))               # a boat
    # the deck (elevated) + approach ramps up from grade
    Entity(parent=root, model='cube', position=(cx, 3, cz), scale=(14, .8, L),
           color=Color(.4, .4, .43, 1), collider='box')
    for end in (-1, 1):
        ramp = Entity(parent=root, model='cube',
                      position=(cx, 1.5, cz + end * (L / 2 + 12)),
                      scale=(14, .8, 26), rotation_x=end * 7, collider='box')
    # suspension towers + cables
    for end in (-1, 1):
        tz = cz + end * L / 3
        for sx in (-7, 7):
            Entity(parent=root, model='cube', position=(cx + sx, 12, tz),
                   scale=(1.4, 24, 1.4), color=Color(.7, .4, .35, 1))
            for c in range(1, 8):
                Entity(parent=root, model='cube',
                       position=(cx + sx, 3.5 + c * 2.4, tz - end * c * 3),
                       scale=(.14, .14, 6.5), rotation_x=end * 22,
                       color=Color(.55, .55, .58, 1)).setLightOff()
    # low guard barriers (limited emergency stopping space)
    for sx in (-6.6, 6.6):
        Entity(parent=root, model='cube', position=(cx + sx, 3.6, cz),
               scale=(.4, 1, L), color=Color(.75, .75, .35, 1), collider='box')
    places['bridge'] = dict(center=Vec3(cx, 3, cz), half=L / 2, width=7,
                            wind=cfg['wind'])


# ------------------------------------------------------------------ districts
def _build_district(root, places, name, rng):
    cfg = WORLD['regions'][name]
    cx, cz = cfg['center']
    r = cfg['radius']
    tint = Color(*cfg['tint'], 1)
    # local road cross so you can drive into and around the district
    _road(root, (cx, 0, cz), r * 2, RW, 'z')
    _road(root, (cx, 0, cz), r * 2, RW, 'x')

    if name == 'suburbs':
        for _ in range(10):
            hx = cx + rng.uniform(-r + 8, r - 8)
            hz = cz + rng.uniform(-r + 8, r - 8)
            if abs(hx - cx) < RW or abs(hz - cz) < RW:
                continue
            world.building(root, (hx, 0, hz), (7, rng.uniform(4, 6), 7),
                           style='brick', lit_ratio=.4, tint=tint)
            world.tree(root, (hx + 5, 0, hz + 4))
        Text(parent=root, text='MAPLE HEIGHTS', position=(cx, 4, cz + r - 8),
             origin=(0, 0), scale=9, billboard=True,
             color=Color(.9, .95, .8, 1)).setLightOff()
    elif name == 'industrial':
        for _ in range(6):
            wx = cx + rng.uniform(-r + 10, r - 10)
            wz = cz + rng.uniform(-r + 10, r - 10)
            if abs(wx - cx) < RW or abs(wz - cz) < RW:
                continue
            world.building(root, (wx, 0, wz), (16, rng.uniform(6, 9), 14),
                           style='concrete', lit_ratio=.2, tint=tint)
        for _ in range(6):                              # parked trucks/containers
            Entity(parent=root, model='cube',
                   position=(cx + rng.uniform(-r, r), 1,
                             cz + rng.uniform(-r, r)),
                   scale=(3, 2, 8), color=rng.choice(
                       [Color(.5, .3, .25, 1), Color(.25, .4, .35, 1)]))
        Text(parent=root, text='PORT DISTRICT', position=(cx, 5, cz + r - 8),
             origin=(0, 0), scale=9, billboard=True,
             color=Color(.9, .8, .6, 1)).setLightOff()
    elif name == 'countryside':
        gnd = Entity(parent=root, model='plane', position=(cx, .01, cz),
                     scale=r * 2.2, texture='grass', color=Color(.6, .7, .5, 1))
        gnd.texture_scale = (18, 18)
        for _ in range(30):
            world.tree(root, (cx + rng.uniform(-r, r), 0,
                              cz + rng.uniform(-r, r)),
                       scale=rng.uniform(.9, 1.6))
        for _ in range(3):                              # barns / farmhouses
            world.building(root, (cx + rng.uniform(-r + 12, r - 12), 0,
                                  cz + rng.uniform(-r + 12, r - 12)),
                           (10, 6, 10), style='brick', lit_ratio=.3,
                           tint=Color(.6, .4, .3, 1))
        Text(parent=root, text='RIVERBEND  ROAD', position=(cx, 4, cz + r - 10),
             origin=(0, 0), scale=9, billboard=True,
             color=Color(.85, .9, .7, 1)).setLightOff()

    # gas station on the way into most districts (roadside life w/ gameplay use)
    if name != 'countryside':
        gx, gz = cx + r - 6, cz
        Entity(parent=root, model='cube', position=(gx, 3, gz),
               scale=(10, .4, 6), color=Color(.85, .8, .5, 1))          # canopy
        for px in (gx - 3, gx + 3):
            Entity(parent=root, model='cube', position=(px, .1, gz),
                   scale=(.4, 6, .4), color=Color(.6, .6, .6, 1))
            Entity(parent=root, model='cube', position=(px, 1.1, gz + 1.6),
                   scale=(.5, 1.2, .3), color=Color(.8, .2, .2, 1))     # pump
        Text(parent=root, text='FUEL', position=(gx, 4, gz), origin=(0, 0),
             scale=8, billboard=True, color=Color(1, .9, .3, 1)).setLightOff()
        places.setdefault('gas_stations', []).append(Vec3(gx, 0, gz))


def _connectors(root):
    """Spur roads linking downtown to each district and the ring."""
    for target in [(-130, 40), (120, -50), (-40, 150)]:
        d = Vec3(target[0], 0, target[1])
        mid = d * .5
        length = d.length()
        ang = math.degrees(math.atan2(d.x, d.z))
        seg = Entity(parent=root, model='cube', position=(mid.x, -.05, mid.z),
                     rotation_y=ang, scale=(RW, .1, length),
                     color=Color(.17, .17, .2, 1), collider='box')
        seg.texture = 'white_cube'


# ============================================================ MODULAR FACADES
class WorldGeneration:
    """Facade over build_open_world so the pipeline is swappable/config-driven."""
    def __init__(self, root, night=False, rng=None):
        self.places = build_open_world(root, night=night, rng=rng)


class RoadNetworkSystem:
    """Queries the built road graph: which region a point is in, its speed
    limit, and whether a point is inside the tunnel or on the bridge."""

    def __init__(self, places):
        self.places = places
        self.regions = places.get('regions', {})

    def region_at(self, pos):
        best, bestd = 'downtown', 1e9
        for name, cfg in self.regions.items():
            if name == 'highway':
                continue
            cx, cz = cfg['center']
            d = ((pos.x - cx) ** 2 + (pos.z - cz) ** 2) ** .5 - cfg['radius']
            if d < bestd:
                best, bestd = name, d
        # on the ring itself?
        h = self.places.get('highway_half', 0)
        if abs(abs(pos.x) - h) < 10 or abs(abs(pos.z) - h) < 10:
            return 'highway'
        return best

    def speed_limit(self, pos):
        return self.regions.get(self.region_at(pos), {}).get('speed', 40)

    def in_tunnel(self, pos):
        t = self.places.get('tunnel')
        if not t:
            return 0.0
        d = pos - t['center']
        if abs(d.x) < t['width'] and abs(d.z) < t['half']:
            edge = min(t['half'] - abs(d.z), t['width'])
            return min(1.0, edge / 6) * t['darkness']
        return 0.0

    def on_bridge(self, pos):
        b = self.places.get('bridge')
        if not b:
            return 0.0
        d = pos - b['center']
        if abs(d.x) < b['width'] + 2 and abs(d.z) < b['half']:
            return b['wind']
        return 0.0
