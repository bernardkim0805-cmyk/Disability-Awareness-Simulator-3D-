"""The smartphone: navigation map, route list, voice-guidance toggle and —
for ADHD — a stream of competing notifications that must be dismissed.

TAB opens/closes it (glancing at your phone while driving is itself the
hazard: the scenario counts time spent with it open). With low-vision
conditions the screen text is deliberately small and dim — the push is
toward the accessible alternative, voice navigation (V).
"""
import random

from ursina import Entity, Text, Color, camera, time as utime

from ..config import STATE

NOTIFY = ['Mom: "call me when you arrive"', 'Weather: rain expected later',
          '50% OFF at BurgerZone today only!', 'Reminder: pick up prescriptions',
          'GroupChat: 7 new messages', 'News alert: traffic on Main St']


class Phone(Entity):
    def __init__(self, scenario, **kwargs):
        super().__init__(parent=camera.ui, enabled=False, **kwargs)
        self.scenario = scenario
        self.open_time = 0
        low_vision = (STATE.disability == 'visual'
                      or {'macular', 'cataracts', 'rp'} & STATE.active_fx)
        # a small dim screen if you have low vision — by design, like real phones
        dim = .55 if low_vision else 1.0
        sc = .8 if low_vision else 1.0

        Entity(parent=self, model='quad', position=(.55, -.1), scale=(.34, .62),
               color=Color(.08, .08, .1, .97))
        Entity(parent=self, model='quad', position=(.55, .09), scale=(.3, .22),
               color=Color(.1, .16, .12, 1))
        self.map_dot = Entity(parent=self, model='circle', scale=.012,
                              color=Color(.3, .9, 1, 1), position=(.55, .05))
        self.map_route = Entity(parent=self, model='quad', position=(.56, .1),
                                rotation_z=40, scale=(.008, .18),
                                color=Color(.3, .8, .4, 1))
        self.route_text = Text(parent=self, text='', position=(.415, -.05),
                               scale=.62 * sc, color=Color(.85 * dim, .9 * dim, .85 * dim, 1))
        self.voice_text = Text(parent=self, text='[V] voice guidance: OFF',
                               position=(.415, -.3), scale=.7 * sc,
                               color=Color(.6, .8, 1, 1))
        Text(parent=self, text='[TAB] put phone away', position=(.415, -.34),
             scale=.6, color=Color(.6, .6, .6, 1))
        self.notif_bg = Entity(parent=self, model='quad', position=(.55, .28),
                               scale=(.32, .07), color=Color(.9, .75, .2, .95),
                               enabled=False)
        self.notif_text = Text(parent=self, text='', position=(.4, .3), scale=.6,
                               color=Color(.1, .1, .1, 1))

    def set_route(self, lines):
        self.route_text.text = 'ROUTE\n' + '\n'.join(lines[:5])

    def show_notification(self, text):
        self.notif_bg.enabled = True
        self.notif_text.text = text + '\n[P] dismiss'

    def dismiss(self):
        self.notif_bg.enabled = False
        self.notif_text.text = ''

    def update(self):
        if self.enabled:
            self.open_time += utime.dt


class NotificationEngine(Entity):
    """ADHD: the phone competes for attention. Notifications ping loudly and
    pile up until dismissed; the scenario counts undismissed seconds as
    cognitive load."""

    def __init__(self, scenario, phone, **kwargs):
        super().__init__(**kwargs)
        self.scenario = scenario
        self.phone = phone
        self.active = (STATE.disability == 'adhd' or 'adhd_fx' in STATE.active_fx)
        self.timer = random.uniform(8, 14)
        self.pending = None
        self.pending_since = 0

    def update(self):
        if not self.active:
            return
        dt = utime.dt
        if self.pending is None:
            self.timer -= dt
            if self.timer <= 0:
                self.pending = random.choice(NOTIFY)
                self.pending_since = 0
                from ..audio import get_audio
                get_audio().play('drive_ping', volume=.9)        # LOUD by design
                self.phone.show_notification(self.pending)
                self.scenario.metrics['notifications'] += 1
        else:
            self.pending_since += dt
            self.scenario.metrics['distracted_s'] += dt

    def dismiss(self):
        if self.pending:
            self.pending = None
            self.timer = random.uniform(12, 22)
            self.phone.dismiss()
