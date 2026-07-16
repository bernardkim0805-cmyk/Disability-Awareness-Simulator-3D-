"""Environment builders: scene lighting, textured buildings, trees, street
lamps, benches, fountains and a star-field night sky. Everything targets the
fixed-function pipeline: real lights + normals, `setLightOff` for emissives."""
import random

from ursina import Entity, Color, scene
from panda3d.core import AmbientLight, DirectionalLight, Vec4 as PVec4


class SceneLights:
    """Ambient + directional key light attached to the ursina scene root."""

    def __init__(self, ambient=(.4, .4, .45), sun=(.85, .8, .7), sun_hpr=(-40, -55, 0)):
        al = AmbientLight('ambient')
        al.setColor(PVec4(*ambient, 1))
        self.ambient_np = scene.attachNewNode(al)
        scene.setLight(self.ambient_np)

        dl = DirectionalLight('sun')
        dl.setColor(PVec4(*sun, 1))
        self.sun_np = scene.attachNewNode(dl)
        self.sun_np.setHpr(*sun_hpr)
        scene.setLight(self.sun_np)

    def destroy(self):
        for np in (self.ambient_np, self.sun_np):
            scene.clearLight(np)
            np.removeNode()


def day_lights():
    return SceneLights(ambient=(.45, .45, .5), sun=(.9, .85, .72))


def indoor_lights():
    return SceneLights(ambient=(.55, .54, .5), sun=(.55, .55, .5), sun_hpr=(30, -70, 0))


def night_lights():
    return SceneLights(ambient=(.16, .17, .26), sun=(.3, .32, .45), sun_hpr=(-60, -40, 0))


def emissive(e):
    e.setLightOff()
    return e


# --------------------------------------------------------------------- props
def building(parent, position, size, style='brick', lit_ratio=.4,
             window_rows=None, tint=None):
    """A textured block with a roof lip, door and a grid of window quads."""
    x, y0, z = position
    w, h, d = size
    root = Entity(parent=parent, position=(x, y0, z))
    body = Entity(parent=root, model='cube', position=(0, h / 2, 0), scale=(w, h, d),
                  texture='brick' if style == 'brick' else 'white_cube',
                  color=tint or (Color(.8, .72, .65, 1) if style == 'brick'
                                 else Color(.55, .58, .62, 1)),
                  collider='box')
    body.texture_scale = (max(1, int(w / 3)), max(1, int(h / 3)))
    Entity(parent=root, model='cube', position=(0, h + .25, 0),          # roof lip
           scale=(w + .6, .5, d + .6), color=Color(.3, .3, .33, 1))
    Entity(parent=root, model='cube', position=(0, 1.1, d / 2 + .02),    # door
           scale=(1.4, 2.2, .1), color=Color(.25, .18, .12, 1))

    rows = window_rows or max(1, int(h / 3))
    cols = max(1, int(w / 3))
    lit = Color(1, .9, .55, 1)
    dark = Color(.12, .16, .24, 1)
    for r in range(rows):
        wy = 2.2 + r * (h - 3) / max(1, rows - 1) if rows > 1 else h / 2
        for c in range(cols):
            wx = -w / 2 + (c + .5) * w / cols
            win = Entity(parent=root, model='quad', position=(wx, wy, d / 2 + .03),
                         scale=(1.1, 1.4),
                         color=lit if random.random() < lit_ratio else dark)
            if win.color == lit:
                emissive(win)
    return root


def tree(parent, position, scale=1.0):
    root = Entity(parent=parent, position=position, scale=scale,
                  rotation_y=random.uniform(0, 360))
    Entity(parent=root, model='cube', position=(0, 1.1, 0), scale=(.35, 2.2, .35),
           color=Color(.35, .25, .15, 1))
    green = Color(.2 + random.uniform(0, .1), .42 + random.uniform(0, .12), .2, 1)
    for pos, s in [((0, 2.8, 0), 2.2), ((.7, 2.3, .3), 1.4), ((-.6, 2.4, -.3), 1.5),
                   ((0, 3.6, 0), 1.3)]:
        Entity(parent=root, model='sphere', position=pos, scale=s, color=green)
    shadow = Entity(parent=root, model='quad', rotation_x=90, y=.02, scale=3,
                    texture='radial_gradient', color=Color(0, 0, 0, .3))
    emissive(shadow)
    return root


def street_lamp(parent, position, on=True, warm=True):
    root = Entity(parent=parent, position=position)
    Entity(parent=root, model='cube', position=(0, 2.4, 0), scale=(.16, 4.8, .16),
           color=Color(.2, .2, .23, 1))
    Entity(parent=root, model='cube', position=(0, 4.85, .4), scale=(.12, .12, 1),
           color=Color(.2, .2, .23, 1))
    glow_color = Color(1, .85, .5, 1) if warm else Color(.8, .9, 1, 1)
    bulb = Entity(parent=root, model='sphere', position=(0, 4.7, .85),
                  scale=(.4, .3, .4), color=glow_color if on else Color(.25, .25, .28, 1))
    if on:
        emissive(bulb)
        pool = Entity(parent=root, model='quad', rotation_x=90, position=(0, .04, .85),
                      scale=7, texture='radial_gradient',
                      color=Color(glow_color.x, glow_color.y, glow_color.z, .22))
        emissive(pool)
    return root


def bench(parent, position, rotation_y=0):
    root = Entity(parent=parent, position=position, rotation_y=rotation_y)
    wood = Color(.45, .32, .2, 1)
    Entity(parent=root, model='cube', position=(0, .45, 0), scale=(1.8, .08, .5),
           color=wood, collider='box')
    Entity(parent=root, model='cube', position=(0, .75, -.22), scale=(1.8, .5, .08),
           color=wood)
    for sx in (-.75, .75):
        Entity(parent=root, model='cube', position=(sx, .22, 0), scale=(.1, .45, .45),
               color=Color(.2, .2, .22, 1))
    return root


def fountain(parent, position=(0, 0, 0)):
    root = Entity(parent=parent, position=position)
    stone = Color(.6, .6, .64, 1)
    Entity(parent=root, model='sphere', position=(0, .1, 0), scale=(6, .7, 6),
           color=stone, collider='box')
    water = Entity(parent=root, model='sphere', position=(0, .42, 0), scale=(5.2, .25, 5.2),
                   color=Color(.3, .6, .85, .9))
    emissive(water)
    Entity(parent=root, model='cube', position=(0, .8, 0), scale=(.7, 1.4, .7), color=stone)
    Entity(parent=root, model='sphere', position=(0, 1.6, 0), scale=(2.2, .3, 2.2),
           color=stone)
    jet = Entity(parent=root, model='sphere', position=(0, 2.1, 0), scale=(.5, 1.1, .5),
                 color=Color(.55, .8, 1, .8))
    emissive(jet)
    return root


def night_sky(parent, stars=160):
    """Moon + scattered emissive stars on a far dome."""
    root = Entity(parent=parent)
    moon = Entity(parent=root, model='sphere', position=(120, 160, 260), scale=26,
                  color=Color(.92, .93, .88, 1))
    emissive(moon)
    halo = Entity(parent=root, model='quad', position=(120, 160, 261), scale=90,
                  billboard=True, texture='radial_gradient',
                  color=Color(.8, .85, 1, .18))
    emissive(halo)
    for _ in range(stars):
        import math
        ang = random.uniform(0, 6.283)
        elev = random.uniform(.12, 1.4)
        r = 380
        x = r * math.cos(ang) * math.cos(elev)
        z = r * math.sin(ang) * math.cos(elev)
        y = r * math.sin(elev) * .6 + 20
        s = random.uniform(.5, 1.6)
        star = Entity(parent=root, model='quad', position=(x, y, z), scale=s,
                      billboard=True,
                      color=Color(1, 1, random.uniform(.85, 1), random.uniform(.5, 1)))
        emissive(star)
    return root


def road(parent, position, length, width=8, along='z', dashes=True):
    """Asphalt strip with dashed center line and side walks."""
    x, y, z = position
    lz = length if along == 'z' else width
    lx = width if along == 'z' else length
    Entity(parent=parent, model='cube', position=(x, y - .05, z), scale=(lx, .1, lz),
           color=Color(.16, .16, .18, 1), collider='box')
    if dashes:
        n = int(length / 6)
        for i in range(n):
            offs = -length / 2 + 3 + i * 6
            dx, dz = (x, z + offs) if along == 'z' else (x + offs, z)
            dash = Entity(parent=parent, model='quad', rotation_x=90,
                          position=(dx, y + .01, dz),
                          scale=(.35, 2.4) if along == 'z' else (2.4, .35),
                          color=Color(.85, .82, .7, .9))
            emissive(dash)


# ----------------------------------------------------------- micro details
def ground_details(parent, area=(40, 40), center=(0, 0), y=.03,
                   cracks=6, pebbles=14, leaves=0, tufts=0, scraps=0):
    """Scatter small imperfections: cracks, pebbles, leaves, grass tufts, litter."""
    ax, az = area
    cx, cz = center
    def spot():
        return (cx + random.uniform(-ax / 2, ax / 2), cz + random.uniform(-az / 2, az / 2))
    for _ in range(cracks):
        x, z = spot()
        Entity(parent=parent, model='quad', rotation_x=90,
               rotation_y=random.uniform(0, 180), position=(x, y, z),
               scale=(random.uniform(.06, .14), random.uniform(1, 3.2)),
               color=Color(0, 0, 0, .35))
    for _ in range(pebbles):
        x, z = spot()
        g = random.uniform(.3, .5)
        Entity(parent=parent, model='sphere', position=(x, y, z),
               scale=(random.uniform(.06, .18), .05, random.uniform(.06, .16)),
               color=Color(g, g, g * 1.05, 1))
    for _ in range(leaves):
        x, z = spot()
        Entity(parent=parent, model='quad', rotation_x=90,
               rotation_y=random.uniform(0, 360), position=(x, y, z),
               scale=random.uniform(.12, .22),
               color=random.choice([Color(.6, .4, .15, 1), Color(.7, .5, .2, 1),
                                    Color(.45, .5, .2, 1)]))
    for _ in range(tufts):
        x, z = spot()
        for _ in range(3):
            Entity(parent=parent, model='sphere',
                   position=(x + random.uniform(-.1, .1), y + .03,
                             z + random.uniform(-.1, .1)),
                   scale=(.08, random.uniform(.12, .22), .08),
                   color=Color(.25, .5, .22, 1))
    for _ in range(scraps):
        x, z = spot()
        paper = Entity(parent=parent, model='quad', rotation_x=90,
                       rotation_y=random.uniform(0, 360), position=(x, y, z),
                       scale=(.25, .32), color=Color(.9, .9, .85, 1))
        emissive(paper)


def manhole(parent, position):
    ring = Entity(parent=parent, model='circle', rotation_x=90,
                  position=(position[0], position[1] + .03, position[2]),
                  scale=1.1, color=Color(.22, .22, .24, 1))
    Entity(parent=parent, model='circle', rotation_x=90,
           position=(position[0], position[1] + .035, position[2]),
           scale=.9, color=Color(.3, .3, .33, 1))
    return ring


def puddle(parent, position, scale=1.5):
    p = Entity(parent=parent, model='circle', rotation_x=90,
               position=(position[0], position[1] + .025, position[2]),
               scale=(scale, scale * random.uniform(.5, .8)),
               color=Color(.35, .42, .55, .55))
    emissive(p)
    return p


def abandoned_car(parent, position, rotation_y=0, color_=None):
    """A weathered parked car for night streets."""
    root = Entity(parent=parent, position=position, rotation_y=rotation_y)
    body_c = color_ or random.choice([Color(.3, .12, .12, 1), Color(.15, .2, .3, 1),
                                      Color(.25, .25, .27, 1)])
    Entity(parent=root, model='cube', position=(0, .55, 0), scale=(4.2, .75, 1.8),
           color=body_c, collider='box')
    Entity(parent=root, model='cube', position=(-.2, 1.15, 0), scale=(2.2, .55, 1.6),
           color=body_c)
    for wx in (-1.1, .9):                                      # window strip
        Entity(parent=root, model='quad', position=(wx, 1.15, -.81), scale=(.9, .4),
               color=Color(.1, .12, .15, 1))
        Entity(parent=root, model='quad', rotation_y=180,
               position=(wx, 1.15, .81), scale=(.9, .4), color=Color(.1, .12, .15, 1))
    for wx in (-1.4, 1.4):                                     # wheels
        for wz in (-.85, .85):
            Entity(parent=root, model='sphere', position=(wx, .3, wz),
                   scale=(.6, .6, .25), color=Color(.08, .08, .09, 1))
    shadow = Entity(parent=root, model='quad', rotation_x=90, y=.02, scale=(5, 2.6),
                    texture='radial_gradient', color=Color(0, 0, 0, .4))
    emissive(shadow)
    return root


def sidewalk(parent, position, size):
    e = Entity(parent=parent, model='cube', position=position,
               scale=(size[0], .22, size[1]), color=Color(.52, .52, .55, 1),
               texture='white_cube', collider='box')
    e.texture_scale = (max(1, int(size[0] / 2)), max(1, int(size[1] / 2)))
    return e
