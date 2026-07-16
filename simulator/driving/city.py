"""City builder for the driving sim.

A 3x3 grid of signalized/signed intersections (block size B) with zone
character: downtown core (tall, lit), residential south-west (parked cars,
trees), a school zone on the north road, a construction zone eating the
right lane of the east road, a faster 'highway' stretch with a tunnel to
the south, a bus stop, a bike lane, and the destination clinic + parking
lot at the north-east. Everything visual a driver must read is modeled:
lane markings, turn arrows, crosswalks, stop/yield/speed/street signs,
pedestrian signals, potholes, debris and view-blocking parked cars.
"""
import random

from ursina import Entity, Text, Color, time as utime, Vec3

from .. import world

B = 30                     # block size: roads run along x,z in {-B, 0, B}
ROAD_W = 10
GRID = (-B, 0, B)


class IntersectionLights(Entity):
    """A 4-way signal. Cycles NS-green -> amber -> EW-green -> amber.
    Cars and the player query .state ('ns' | 'ew' | 'amber')."""

    CYCLE = [( 'ns', 9), ('amber', 2.2), ('ew', 9), ('amber', 2.2)]

    def __init__(self, pos, **kwargs):
        super().__init__(position=pos, **kwargs)
        self.phase_i = random.randint(0, 3)
        self.timer = random.uniform(0, 5)
        self.lamps = []
        for dx, dz, face in [(ROAD_W / 2, ROAD_W / 2, 180), (-ROAD_W / 2, -ROAD_W / 2, 0)]:
            pole = Entity(parent=self, model='cube', position=(dx, 2.6, dz),
                          scale=(.18, 5.2, .18), color=Color(.25, .25, .28, 1))
            head = Entity(parent=self, model='cube', position=(dx, 4.6, dz),
                          rotation_y=face, scale=(.4, 1.15, .3),
                          color=Color(.15, .15, .17, 1))
            lamps = []
            for i, _ in enumerate('rag'):
                l = Entity(parent=head, model='circle', position=(0, .32 - i * .32, -.52),
                           scale=.55, color=Color(.15, .15, .15, 1))
                l.setLightOff()
                lamps.append(l)
            self.lamps.append(lamps)

    @property
    def state(self):
        return self.CYCLE[self.phase_i][0]

    def green_for(self, axis):                     # axis: 'ns' or 'ew'
        return self.state == axis

    def update(self):
        self.timer += utime.dt
        if self.timer >= self.CYCLE[self.phase_i][1]:
            self.timer = 0
            self.phase_i = (self.phase_i + 1) % len(self.CYCLE)
        st = self.state
        # both heads show the NS aspect; EW is implied opposite (kept simple)
        colors = {'r': Color(.9, .1, .1, 1), 'a': Color(1, .7, .1, 1),
                  'g': Color(.1, .9, .3, 1)}
        lit = {'ns': 'g', 'ew': 'r', 'amber': 'a'}[st]
        for lamps in self.lamps:
            for i, ch in enumerate('rag'):
                lamps[i].color = colors[ch] if ch == lit else Color(.14, .14, .14, 1)


def _lane_arrow(parent, pos, rotation_y=0):
    a = Entity(parent=parent, model='arrow', rotation_x=90, rotation_y=rotation_y,
               position=(pos[0], .06, pos[2]), scale=(1.6, 1.2, 1),
               color=Color(.9, .9, .85, .9))
    a.setLightOff()
    return a


def _crosswalk(parent, pos, along='x'):
    for i in range(6):
        off = -2.5 + i
        p = (pos[0] + (off if along == 'x' else 0), .05,
             pos[2] + (off if along == 'z' else 0))
        stripe = Entity(parent=parent, model='quad', rotation_x=90, position=p,
                        scale=(.6, 2.6) if along == 'x' else (2.6, .6),
                        color=Color(.92, .92, .88, .95))
        stripe.setLightOff()


def _sign(parent, pos, text, bg=Color(.85, .1, .1, 1), shape='circle', scale=.8):
    Entity(parent=parent, model='cube', position=(pos[0], 1.4, pos[2]),
           scale=(.1, 2.8, .1), color=Color(.4, .4, .42, 1))
    s = Entity(parent=parent, model=shape, position=(pos[0], 2.6, pos[2]),
               scale=scale, color=bg)
    s.setLightOff()
    t = Text(parent=parent, text=text, position=(pos[0], 2.6, pos[2] - .07),
             origin=(0, 0), scale=6, color=Color(1, 1, 1, 1))
    t.setLightOff()
    return s


def build_city(root, night=False):
    """Builds everything static. Returns a dict of important places."""
    places = {}

    ground = Entity(parent=root, model='plane', scale=260, y=-.02,
                    texture='grass', color=Color(.75, .85, .7, 1))
    ground.texture_scale = (40, 40)

    # ---- roads: grid + the southern 'highway' stretch with a tunnel --------
    for k in GRID:
        world.road(root, (k, 0, 6), length=3 * B + 70, width=ROAD_W, along='z')
        world.road(root, (0, 0, k), length=3 * B + 40, width=ROAD_W, along='x')
    world.road(root, (0, 0, -B - 35), length=140, width=ROAD_W, along='x')  # highway
    for k in GRID:                                                    # sidewalks
        world.sidewalk(root, (k + ROAD_W / 2 + 2, 0, 6), (3.5, 3 * B + 70))
        world.sidewalk(root, (k - ROAD_W / 2 - 2, 0, 6), (3.5, 3 * B + 70))

    # bike lane: green strip on the west road's east edge
    bike = Entity(parent=root, model='cube', position=(-B + ROAD_W / 2 - 1, .02, 6),
                  scale=(1.8, .04, 3 * B + 60), color=Color(.25, .55, .35, .9))
    bike.setLightOff()

    # ---- intersections -------------------------------------------------------
    places['lights'] = []
    for x in GRID:
        for z in GRID:
            if (x, z) in ((0, 0), (0, B), (B, 0)):        # signalized
                places['lights'].append(IntersectionLights((x, 0, z), parent=root))
                _crosswalk(root, (x, 0, z - ROAD_W / 2 - 1), along='x')
                _crosswalk(root, (x - ROAD_W / 2 - 1, 0, z), along='z')
            else:                                          # stop-controlled
                _sign(root, (x + ROAD_W / 2 + 1, 0, z + ROAD_W / 2 + 1), 'STOP',
                      bg=Color(.8, .1, .1, 1), shape='circle')
            _lane_arrow(root, (x + 2.5, 0, z - ROAD_W / 2 - 4))

    # street name plates
    for x, name in zip(GRID, ('Ash Ave', 'Main St', 'Cedar Ave')):
        t = Text(parent=root, text=name, position=(x + 2, 3.4, 2), origin=(0, 0),
                 scale=7, billboard=True, color=Color(.9, .95, .9, 1))
        t.setLightOff()

    # ---- zones ---------------------------------------------------------------
    # downtown core around (0,0): tall lit buildings
    for bx, bz, h in [(-14, 14, 18), (14, 16, 22), (16, -14, 15), (-16, -16, 12)]:
        world.building(root, (bx, 0, bz), (10, h, 10), style='concrete',
                       lit_ratio=.6 if night else .25)
    # residential SW: small houses, trees, parked cars against the curb
    for i, (bx, bz) in enumerate([(-B - 14, -B - 12), (-B - 14, -B + 8),
                                  (-B + 12, -B - 14), (-B + 15, -B + 12)]):
        world.building(root, (bx, 0, bz), (8, 5, 8), style='brick', lit_ratio=.4)
        world.tree(root, (bx + 6, 0, bz + 5))
    for pz in (-B - 8, -B + 2, -B + 14):                    # visibility blockers
        world.abandoned_car(root, (-B - ROAD_W / 2 + 1.2, 0, pz), rotation_y=90)

    # school zone: north road near (0, B)
    _sign(root, (8, 0, B + ROAD_W / 2 + 2), 'SCHOOL\n20', bg=Color(.95, .8, .2, 1),
          shape='quad')
    world.building(root, (14, 0, B + 16), (14, 6, 10), style='brick', lit_ratio=.3,
                   tint=Color(.8, .7, .55, 1))
    _crosswalk(root, (8, 0, B), along='z')
    places['school_cross'] = Vec3(8, 0, B)

    # construction zone: east road (B, z 8..20), right lane closed
    for i in range(6):
        cone = Entity(parent=root, model='cube', position=(B + 2.2, .4, 6 + i * 2.6),
                      scale=(.35, .8, .35), color=Color(1, .45, .1, 1))
        cone.setLightOff()
    Entity(parent=root, model='cube', position=(B + 2.2, .6, 4),
           scale=(2.4, 1.2, .2), color=Color(1, .6, .15, 1)).setLightOff()
    _sign(root, (B + ROAD_W / 2 + 1, 0, 2), 'ROAD\nWORK', bg=Color(.95, .55, .15, 1),
          shape='quad')
    Entity(parent=root, model='cube', position=(B + 6, 1.2, 12),   # excavator-ish
           scale=(2.4, 2, 1.6), color=Color(.9, .7, .15, 1))
    places['construction'] = Vec3(B + 2.2, 0, 12)

    # highway + tunnel (south stretch)
    _sign(root, (-30, 0, -B - 35 + ROAD_W / 2 + 2), '60', bg=Color(.9, .9, .9, 1))
    for tx in range(-8, 9, 4):                              # tunnel shell
        Entity(parent=root, model='cube', position=(tx, 3.4, -B - 35),
               scale=(4.2, .5, ROAD_W + 4), color=Color(.35, .35, .4, 1))
    for side in (-1, 1):
        Entity(parent=root, model='cube', position=(0, 1.7, -B - 35 + side * (ROAD_W / 2 + 1.4)),
               scale=(18, 3.4, .6), color=Color(.35, .35, .4, 1), collider='box')

    # bus stop on the west road
    Entity(parent=root, model='cube', position=(-B - ROAD_W / 2 - 3, 1.4, 20),
           scale=(.15, 2.8, 4), color=Color(.6, .7, .75, .5))
    Entity(parent=root, model='cube', position=(-B - ROAD_W / 2 - 3.5, 2.6, 20),
           scale=(1.6, .2, 4.4), color=Color(.3, .35, .4, 1))
    world.bench(root, (-B - ROAD_W / 2 - 3.4, 0, 20), rotation_y=90)
    places['bus_stop'] = Vec3(-B - ROAD_W / 2 + 1.5, 0, 20)

    # speed limit default
    _sign(root, (ROAD_W / 2 + 1, 0, -12), '40', bg=Color(.9, .9, .9, 1))

    # ---- hazards -------------------------------------------------------------
    places['potholes'] = []
    for pos in [(2.2, 0, -18), (-B + 2.5, 0, 24), (B - 2.4, 0, -8)]:
        Entity(parent=root, model='circle', rotation_x=90,
               position=(pos[0], .06, pos[2]), scale=random.uniform(.9, 1.4),
               color=Color(.08, .08, .09, 1)).setLightOff()
        places['potholes'].append(Vec3(*pos))
    Entity(parent=root, model='cube', position=(-2.4, .2, B - 12),   # debris
           rotation_y=30, scale=(.8, .4, .5), color=Color(.4, .32, .2, 1))
    places['debris'] = Vec3(-2.4, 0, B - 12)

    # ---- destination: clinic + parking lot (NE) ------------------------------
    world.building(root, (B + 24, 0, B + 10), (14, 10, 12), style='concrete',
                   lit_ratio=.5, tint=Color(.75, .8, .85, 1))
    cross = Entity(parent=root, model='quad', position=(B + 24, 8, B + 3.9),
                   scale=(1.6, 1.6), color=Color(.9, .2, .25, 1))
    cross.setLightOff()
    lot = Entity(parent=root, model='cube', position=(B + 24, 0, B - 6),
                 scale=(20, .06, 12), color=Color(.3, .3, .33, 1))
    for i in range(5):                                     # bay lines
        Entity(parent=root, model='quad', rotation_x=90,
               position=(B + 16 + i * 4, .08, B - 6), scale=(.25, 5.5),
               color=Color(.9, .9, .85, .9)).setLightOff()
    bay = Entity(parent=root, model='quad', rotation_x=90,
                 position=(B + 22, .09, B - 6), scale=(3.4, 5.2),
                 color=Color(.2, .85, .35, .5))
    bay.setLightOff()
    places['bay'] = Vec3(B + 22, 0, B - 6)
    places['home'] = Vec3(-B + 2.5, 0, -B - 14)            # where you start

    if night:
        for x in GRID:
            for z in range(-B - 10, B + 30, 22):
                world.street_lamp(root, (x + ROAD_W / 2 + 1.5, 0, z), on=True)
        world.night_sky(root)
    return places
