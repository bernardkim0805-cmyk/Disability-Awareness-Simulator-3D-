"""GPS minimap — a north-up top-down map in the top-right corner.

Draws the road network schematically (highway ring, downtown grid, district
blobs, bridge, tunnel), the destination, and a live player arrow. The route
line to the next waypoint updates each frame. High-contrast by default so it
stays readable for low-vision players (the accessibility brief)."""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import math

from ursina import Entity, Text, Color, camera

from .config import WORLD, INFRA


class MinimapGPS(Entity):
    def __init__(self, scenario, world_extent=215, **kwargs):
        super().__init__(parent=camera.ui, **kwargs)
        self.s = scenario
        self.ext = world_extent
        self.center = (.72, .30)          # panel center in UI space (top-right)
        self.half = .15                   # panel half-size
        self.scale_f = self.half / world_extent

        # panel + border + heading label
        Entity(parent=self, model='quad', position=self.center,
               scale=(self.half * 2 + .02, self.half * 2 + .02),
               color=Color(.85, .9, 1, .9)).setLightOff()               # border
        Entity(parent=self, model='quad', position=self.center,
               scale=(self.half * 2, self.half * 2),
               color=Color(.08, .12, .16, .95)).setLightOff()           # bg
        Text(parent=self, text='GPS', position=(self.center[0] - self.half,
                                                self.center[1] + self.half + .015),
             scale=.7, color=Color(.7, .9, 1, 1)).setLightOff()
        Text(parent=self, text='N', position=(self.center[0],
                                              self.center[1] + self.half - .01),
             origin=(0, 0), scale=.7, color=Color(.8, .85, .9, 1)).setLightOff()

        self._draw_static()
        # dynamic markers (created ONCE, repositioned each frame — no leaks)
        self.route_line = Entity(parent=self, model='quad',
                                 color=Color(.3, .9, .4, .9), enabled=False)
        self.route_line.setLightOff()
        self.dest = self._dot(Color(.2, 1, .4, 1), .014)
        self.player = Entity(parent=self, model='diamond',
                             color=Color(1, .3, .3, 1), scale=.016)
        self.player.setLightOff()
        self.traffic_dots = [self._dot(Color(1, .8, .3, .8), .006)
                             for _ in range(14)]

    # ---------------------------------------------------------------- helpers
    def _uv(self, wx, wz):
        """World (x,z) -> UI position on the panel (north-up: +z is up)."""
        return (self.center[0] + wx * self.scale_f,
                self.center[1] + wz * self.scale_f)

    def _dot(self, color, size):
        d = Entity(parent=self, model='circle', color=color, scale=size)
        d.setLightOff()
        return d

    def _line(self, a, b, color, thick=.004):
        ax, az = a
        bx, bz = b
        mx, mz = (ax + bx) / 2, (az + bz) / 2
        dx, dz = bx - ax, bz - az
        length = math.hypot(dx, dz) * self.scale_f
        e = Entity(parent=self, model='quad', position=self._uv(mx, mz),
                   rotation_z=math.degrees(math.atan2(dx, dz)),
                   scale=(thick, max(length, .002)), color=color)
        e.setLightOff()
        return e

    def _draw_static(self):
        H = self.s.places.get('highway_half', 200)
        ring = Color(.45, .5, .6, 1)
        for a, b in [((-H, -H), (H, -H)), ((H, -H), (H, H)),
                     ((H, H), (-H, H)), ((-H, H), (-H, -H))]:
            self._line(a, b, ring, .006)                    # highway ring
        B = WORLD['downtown_block']
        grid = Color(.4, .45, .5, 1)
        for k in (-B, 0, B):
            self._line((k, -B - 40), (k, B + 40), grid, .003)
            self._line((-B - 40, k), (B + 40, k), grid, .003)
        # district blobs
        for name, cfg in WORLD['regions'].items():
            if name in ('downtown', 'highway'):
                continue
            cx, cz = cfg['center']
            d = self._dot(Color(*cfg['tint'], .8), cfg['radius'] * self.scale_f * 2)
            d.position = self._uv(cx, cz)
            Text(parent=self, text=name[:4].upper(), position=self._uv(cx, cz),
                 origin=(0, 0), scale=.5, color=Color(.9, .9, .95, .9)).setLightOff()
        # bridge (blue) + tunnel (dark) segments
        bc = INFRA['bridge']['center']
        self._line((bc[0], bc[1] - INFRA['bridge']['length'] / 2),
                   (bc[0], bc[1] + INFRA['bridge']['length'] / 2),
                   Color(.4, .7, 1, 1), .006)
        tc = INFRA['tunnel']['center']
        self._line((tc[0], tc[1] - INFRA['tunnel']['length'] / 2),
                   (tc[0], tc[1] + INFRA['tunnel']['length'] / 2),
                   Color(.2, .2, .25, 1), .006)

    # ------------------------------------------------------------------ update
    def update(self):
        car = self.s.car
        if car.isEmpty():
            return
        px, pz = self._uv(car.position.x, car.position.z)
        self.player.position = (px, pz, -.1)
        self.player.rotation_z = -car.rotation_y      # north-up heading
        # destination (final route leg) + route line to the next waypoint
        try:
            dest = self.s.route[-1][0]
            nxt = self.s.route[self.s.leg][0]
        except Exception:
            return
        self.dest.position = (*self._uv(dest.x, dest.z), -.05)
        # reposition the single route line: player -> next waypoint
        ax, az = self._uv(car.position.x, car.position.z)
        bx, bz = self._uv(nxt.x, nxt.z)
        length = math.hypot(bx - ax, bz - az)
        self.route_line.enabled = length > .001
        self.route_line.position = ((ax + bx) / 2, (az + bz) / 2, -.03)
        self.route_line.rotation_z = math.degrees(math.atan2(bx - ax, bz - az))
        self.route_line.scale = (.004, max(length, .002))
        # a few live traffic blips
        for dot, v in zip(self.traffic_dots, self.s.vehicles):
            if v.isEmpty():
                dot.enabled = False
                continue
            dot.enabled = True
            dot.position = (*self._uv(v.position.x, v.position.z), -.02)


    def on_destroy(self):
        from ursina import destroy
        for c in self.children[:]:
            destroy(c)
