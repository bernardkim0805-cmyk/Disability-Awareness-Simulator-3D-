"""The player's car: arcade physics, a modeled first-person cockpit
(steering wheel, dashboard, GPS screen, mirrors) and a modern-vehicle GUI
that adapts to the selected accessibility conditions.

Mirrors: without render-to-texture on this GPU, mirrors are implemented as
*proximity displays* — each mirror shows moving blips for the vehicles it
would reflect, and the side mirrors double as blind-spot warnings. That is
itself the accessibility lesson: information can be re-encoded.
"""
import math
import random

from ursina import Entity, Text, Color, camera, held_keys, time as utime, Vec3

from ..config import STATE

KMH = 4.2                    # display multiplier: world-units/s -> 'km/h'


def _motor_profile():
    wobble, delay = 0.0, 0.0
    if 'essential_tremor' in STATE.active_fx:
        wobble, delay = .7, .08
    if 'parkinsonian' in STATE.active_fx:
        wobble, delay = max(wobble, .5), .25
    return wobble, delay


def _vision_boost():
    """Larger text / stronger contrast when low-vision conditions are on."""
    vis = {'macular', 'cataracts', 'glaucoma', 'rp', 'visual_snow'}
    return (STATE.disability == 'visual') or bool(vis & STATE.active_fx)


class PlayerCar(Entity):
    MAX_SPEED = 16

    def __init__(self, night=False, **kwargs):
        super().__init__(**kwargs)
        self.speed = 0.0
        self.steer = 0.0                     # -1..1 smoothed
        self.steer_target = 0.0
        self.signal = None                   # 'l' | 'r'
        self.signal_t = 0
        self.fuel = 1.0
        self.damage = 0
        self.wobble, self.input_delay = _motor_profile()
        self._delay_buf = []                 # (time_due, steer_target)
        self.t = 0
        self.controls_locked = False

        self._build_cockpit(night)
        self._build_gui()

        camera.parent = self
        camera.position = (-.38, 1.28, -.35)
        camera.rotation = (2, 0, 0)

    # ---------------------------------------------------------------- cockpit
    def _build_cockpit(self, night):
        dark = Color(.12, .12, .14, 1)
        Entity(parent=self, model='cube', position=(0, .55, .4),        # body
               scale=(1.9, .6, 4.2), color=Color(.2, .25, .35, 1))
        Entity(parent=self, model='cube', position=(0, 1.02, 1.6),      # hood
               scale=(1.8, .12, 1.4), color=Color(.25, .3, .4, 1))
        Entity(parent=self, model='cube', position=(0, .98, .35),       # dash
               scale=(1.8, .3, .5), color=dark)
        for sx in (-.92, .92):                                          # A pillars
            Entity(parent=self, model='cube', position=(sx, 1.5, .55),
                   rotation_x=-24, scale=(.09, 1.0, .09), color=dark)
        Entity(parent=self, model='cube', position=(0, 1.95, -.1),      # roof edge
               scale=(1.9, .08, 1.4), color=dark)
        # steering wheel: rim + spokes, rotates with input
        self.wheel = Entity(parent=self, position=(-.38, 1.05, .12), rotation_x=-18)
        Entity(parent=self.wheel, model='circle', scale=.46, color=Color(.05, .05, .06, 1),
               double_sided=True)
        Entity(parent=self.wheel, model='circle', scale=.4, color=dark, z=-.005,
               double_sided=True)
        for ang in (0, 120, 240):
            Entity(parent=self.wheel, model='cube', rotation_z=ang,
                   scale=(.05, .4, .03), color=Color(.05, .05, .06, 1))
        # GPS screen in the center console
        self.gps_bg = Entity(parent=self, model='quad', position=(.25, 1.12, .12),
                             rotation_x=-18, scale=(.55, .3),
                             color=Color(.03, .06, .05, 1))
        self.gps_bg.setLightOff()
        if night:                                                       # headlights
            for sx in (-.6, .6):
                pool = Entity(parent=self, model='quad', rotation_x=90,
                              position=(sx, .06, 6), scale=(2.5, 8),
                              texture='radial_gradient', color=Color(1, .95, .8, .3))
                pool.setLightOff()

    # -------------------------------------------------------------------- GUI
    def _build_gui(self):
        big = 1.45 if _vision_boost() else 1.0
        hc = _vision_boost()
        self.gui = Entity(parent=camera.ui)
        panel = Color(0, 0, 0, .85 if hc else .55)

        # center-bottom: speed + limit + lane status
        Entity(parent=self.gui, model='quad', position=(0, -.42), scale=(.5, .14),
               color=panel)
        self.speed_text = Text(parent=self.gui, text='0', origin=(0, 0),
                               position=(-.06, -.41), scale=2.2 * big,
                               color=Color(1, 1, 1, 1))
        Text(parent=self.gui, text='km/h', origin=(0, 0), position=(-.06, -.462),
             scale=.7 * big, color=Color(.7, .7, .7, 1))
        self.limit_text = Text(parent=self.gui, text='40', origin=(0, 0),
                               position=(.12, -.41), scale=1.2 * big,
                               color=Color(.1, .1, .1, 1))
        Entity(parent=self.gui, model='circle', position=(.12, -.41), scale=.055,
               color=Color(.95, .95, .95, 1), z=.1).setLightOff()
        Entity(parent=self.gui, model='circle', position=(.12, -.41), scale=.062,
               color=Color(.85, .1, .1, 1), z=.2)
        # bottom strip: fuel, engine, lights, signals
        self.fuel_bar = Entity(parent=self.gui, model='quad', origin=(-.5, 0),
                               position=(-.24, -.46), scale=(.1, .015),
                               color=Color(.3, .8, .4, 1))
        Text(parent=self.gui, text='fuel', position=(-.24, -.44), scale=.6 * big,
             color=Color(.7, .7, .7, 1))
        self.engine_light = Text(parent=self.gui, text='ENGINE', position=(.2, -.44),
                                 scale=.6 * big, color=Color(.3, .3, .3, 1))
        self.sig_l = Text(parent=self.gui, text='<', origin=(0, 0),
                          position=(-.14, -.41), scale=1.6, color=Color(.25, .3, .25, 1))
        self.sig_r = Text(parent=self.gui, text='>', origin=(0, 0),
                          position=(.2, -.41), scale=1.6, color=Color(.25, .3, .25, 1))

        # top: navigation bar (scenario writes into it)
        Entity(parent=self.gui, model='quad', position=(0, .44), scale=(.85, .1),
               color=panel)
        self.nav_text = Text(parent=self.gui, text='', origin=(0, 0),
                             position=(0, .45), scale=1.05 * big,
                             color=Color(.6, 1, .7, 1) if hc else Color(.8, .95, .85, 1))
        self.eta_text = Text(parent=self.gui, text='', origin=(0, 0),
                             position=(0, .41), scale=.75 * big,
                             color=Color(.8, .8, .8, 1))

        # mirrors as proximity displays
        self.rear_bg = Entity(parent=self.gui, model='quad', position=(0, .33),
                              scale=(.34, .05), color=Color(.05, .08, .08, .9))
        Text(parent=self.gui, text='rear', position=(-.16, .355), scale=.55,
             color=Color(.6, .6, .6, 1))
        self.side_l = Entity(parent=self.gui, model='quad', position=(-.52, -.3),
                             scale=(.09, .06), color=Color(.05, .08, .08, .9))
        self.side_r = Entity(parent=self.gui, model='quad', position=(.52, -.3),
                             scale=(.09, .06), color=Color(.05, .08, .08, .9))
        self.blips = [Entity(parent=self.gui, model='circle', scale=.012,
                             color=Color(1, .8, .3, 1), enabled=False)
                      for _ in range(10)]

        # big adaptive warning banner (the deaf-accessible channel)
        self.warn_bg = Entity(parent=self.gui, model='quad', position=(0, .2),
                              scale=(.9, .09), color=Color(.8, .1, .1, .85),
                              enabled=False)
        self.warn_text = Text(parent=self.gui, text='', origin=(0, 0),
                              position=(0, .2), scale=1.2 * big,
                              color=Color(1, 1, 1, 1))
        self.warn_until = 0

    # ------------------------------------------------------------- interface
    def set_nav(self, instruction, eta):
        self.nav_text.text = instruction
        self.eta_text.text = eta

    def warn(self, text, seconds=3.5, flash=True):
        """Adaptive warning. Deaf/hearing-loss players get it bigger, longer
        and with a 'vibration' pulse (camera nudge) as the tactile channel."""
        deaf = STATE.disability == 'deaf' or 'hearing_loss' in STATE.active_fx
        self.warn_text.text = ('!! ' + text + ' !!') if deaf else text
        self.warn_bg.enabled = True
        self.warn_until = self.t + (seconds * 1.6 if deaf else seconds)
        self._warn_flash = flash
        if deaf:
            camera.shake(duration=.3, magnitude=.6)      # vibration alert

    # ----------------------------------------------------------------- update
    def update(self):
        dt = utime.dt
        self.t += dt
        if self.controls_locked:
            self.speed = max(0, self.speed - 10 * dt)
        else:
            self._drive(dt)
        self._instruments(dt)

    def _drive(self, dt):
        accel = held_keys['w'] * 6.5 - held_keys['s'] * 12
        self.speed = max(-3, min(self.MAX_SPEED, self.speed + accel * dt))
        if not held_keys['w'] and not held_keys['s']:
            self.speed *= 1 - .6 * dt
        raw = (held_keys['d'] - held_keys['a'])
        # motor conditions: input arrives late...
        if self.input_delay > 0:
            self._delay_buf.append((self.t + self.input_delay, raw))
            while self._delay_buf and self._delay_buf[0][0] <= self.t:
                _, self.steer_target = self._delay_buf.pop(0)
        else:
            self.steer_target = raw
        self.steer += (self.steer_target - self.steer) * min(1, 6 * dt)
        steer = self.steer
        # ...and the wheel itself trembles
        if self.wobble > 0:
            steer += math.sin(self.t * 8.3) * .12 * self.wobble
        self.rotation_y += steer * 60 * dt * (self.speed / self.MAX_SPEED)
        self.position += self.forward * self.speed * dt
        self.wheel.rotation_z = -steer * 90
        self.fuel = max(0, self.fuel - dt * .0006 * (1 + abs(self.speed) / 8))

    def _instruments(self, dt):
        self.speed_text.text = str(int(abs(self.speed) * KMH))
        self.fuel_bar.scale_x = .1 * self.fuel
        self.fuel_bar.color = Color(.3, .8, .4, 1) if self.fuel > .25 else Color(.9, .5, .2, 1)
        self.engine_light.color = (Color(.95, .6, .1, 1) if self.damage >= 2
                                   else Color(.3, .3, .3, 1))
        # turn signals blink + tick
        if self.signal:
            self.signal_t += dt
            on = int(self.signal_t * 2.5) % 2 == 0
            lit = Color(.3, .95, .4, 1)
            off = Color(.25, .3, .25, 1)
            self.sig_l.color = lit if (self.signal == 'l' and on) else off
            self.sig_r.color = lit if (self.signal == 'r' and on) else off
            if on and self.signal_t % .4 < dt:
                from ..audio import get_audio
                get_audio().play('drive_signal', volume=.25)
        else:
            self.sig_l.color = self.sig_r.color = Color(.25, .3, .25, 1)
        # warning banner
        if self.warn_bg.enabled:
            if self.t > self.warn_until:
                self.warn_bg.enabled = False
                self.warn_text.text = ''
            elif getattr(self, '_warn_flash', False):
                self.warn_bg.color = (Color(.85, .1, .1, .9)
                                      if int(self.t * 5) % 2 else Color(.5, .05, .05, .9))

    def update_mirrors(self, vehicles):
        """Feed traffic into the mirror displays; returns True if something
        is sitting in a blind spot (used for assist metrics)."""
        for b in self.blips:
            b.enabled = False
        i = 0
        blind = False
        for v in vehicles:
            rel = v.position - self.position
            rel.y = 0
            behind = rel.dot(self.forward)
            side = rel.dot(self.right)
            if i >= len(self.blips):
                break
            if -26 < behind < -2 and abs(side) < 7:            # rear mirror
                b = self.blips[i]; i += 1
                b.enabled = True
                b.position = (max(-.15, min(.15, side * .02)), .33)
                b.color = Color(1, .8, .3, 1)
            elif -5 < behind < 2 and 1.6 < abs(side) < 5:      # blind spot!
                b = self.blips[i]; i += 1
                b.enabled = True
                b.position = ((-.52 if side < 0 else .52), -.3)
                b.color = Color(1, .2, .15, 1) if int(self.t * 6) % 2 else Color(.6, .1, .1, 1)
                blind = True
        return blind

    def input(self, key):
        if key == 'q':
            self.signal = None if self.signal == 'l' else 'l'
            self.signal_t = 0
        elif key == 'r':
            self.signal = None if self.signal == 'r' else 'r'
            self.signal_t = 0
        elif key == 'h':
            from ..audio import get_audio
            get_audio().play('drive_horn', volume=.5)
