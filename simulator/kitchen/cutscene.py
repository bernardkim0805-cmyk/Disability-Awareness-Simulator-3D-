"""Chopping cutscene: the camera cuts to a close-up diorama of the player's
hand, the knife, the cutting board and the vegetable.

Rhythm game: the knife rises and falls; press SPACE at the TOP of the arc to
slice cleanly. Tremor / cerebral-palsy style motor conditions add:
- hand + knife wobble (the safe window physically moves)
- input latency (the press registers late)
- a shrunken timing window
Mistimed cuts on an unsteady hand cost a finger: red flash, health damage,
and one finger stays on the board. The diorama is built far below the map
so it never collides with the kitchen."""
import math
import random

from ursina import Entity, Text, Color, camera, scene, destroy, invoke, time as utime

from ..config import STATE

SKIN = Color(.9, .74, .6, 1)
DIORAMA_POS = (0, -60, 0)          # far below the world


def motor_difficulty():
    """(wobble 0..1, input_delay seconds) from active motor conditions."""
    wobble, delay = 0.0, 0.0
    if 'essential_tremor' in STATE.active_fx:
        wobble = max(wobble, .8)
        delay = max(delay, .12)
    if 'parkinsonian' in STATE.active_fx:
        wobble = max(wobble, .6)
        delay = max(delay, .3)
    if 'vestibular' in STATE.active_fx:
        wobble = max(wobble, .3)
    return wobble, delay


class ChoppingCutscene(Entity):
    SLICES_NEEDED = 6

    def __init__(self, on_done, **kwargs):
        super().__init__(position=DIORAMA_POS, **kwargs)
        self.on_done = on_done
        self.wobble, self.input_delay = motor_difficulty()
        self.t = 0
        self.slices = 0
        self.fingers_lost = 0
        self.finished = False
        self.pending_press = None      # time a delayed press will land

        self._build_diorama()

        # UI overlay
        self.ui = Entity(parent=camera.ui)
        Text(parent=self.ui, text='CHOP — press SPACE when the knife is raised',
             origin=(0, 0), y=.42, scale=1, color=Color(1, 1, .8, 1))
        self.status = Text(parent=self.ui, text='', origin=(0, 0), y=.36, scale=.9,
                           color=Color(.9, .9, .9, 1))
        self.flash = Entity(parent=self.ui, model='quad', scale=(2, 2), z=-.1,
                            color=Color(1, 0, 0, 0))
        if self.input_delay > 0:
            Text(parent=self.ui, text='(your movements respond with a delay)',
                 origin=(0, 0), y=-.42, scale=.8, color=Color(1, .7, .6, .9))

        # steal the camera for the close-up
        self._cam_state = (camera.parent, camera.position, camera.rotation)
        camera.parent = scene
        camera.position = (DIORAMA_POS[0], DIORAMA_POS[1] + 1.1, DIORAMA_POS[2] - 1.35)
        camera.rotation = (38, 0, 0)

    # ---------------------------------------------------------------- diorama
    def _build_diorama(self):
        Entity(parent=self, model='cube', scale=(3, .1, 2),          # counter
               color=Color(.9, .9, .88, 1))
        Entity(parent=self, model='cube', position=(0, .09, 0),      # board
               scale=(1.6, .08, 1.1), color=Color(.72, .55, .35, 1))
        # the vegetable: a carrot that shortens as slices come off
        self.veg = Entity(parent=self, model='cube', position=(-.1, .2, .1),
                          scale=(.8, .14, .14), color=Color(.9, .5, .15, 1))
        self.slice_pile = []
        # the guiding hand, fingertips curled on the food (as taught) —
        # but a wobbling hand drifts INTO the blade's path
        self.hand = Entity(parent=self)
        Entity(parent=self.hand, model='cube', position=(-.5, .24, .1),  # palm
               scale=(.3, .12, .3), color=SKIN)
        self.fingers = []
        for i in range(4):
            f = Entity(parent=self.hand, model='cube',
                       position=(-.34, .2, -.02 + i * .085),
                       scale=(.16, .07, .06), color=SKIN)
            self.fingers.append(f)
        # knife: pivot at the heel so it chops in an arc
        self.knife = Entity(parent=self, position=(.35, .28, .1))
        Entity(parent=self.knife, model='cube', position=(-.3, 0, 0),   # blade
               scale=(.62, .16, .02), color=Color(.85, .87, .9, 1))
        Entity(parent=self.knife, model='cube', position=(.12, .05, 0), # handle
               scale=(.26, .09, .05), color=Color(.2, .12, .08, 1))

    # ----------------------------------------------------------------- update
    def update(self):
        if self.finished:
            return
        self.t += utime.dt
        # knife bobs: raised at sin=1, striking at sin=-1
        arc = math.sin(self.t * 2.2)
        self.knife.rotation_z = -20 + arc * 24
        self.knife.y = .28 + arc * .1
        # tremor: the whole hand (and target) wanders
        if self.wobble > 0:
            self.hand.x = math.sin(self.t * 9) * .05 * self.wobble
            self.hand.z = math.cos(self.t * 7.3) * .04 * self.wobble
            self.knife.x = .35 + math.sin(self.t * 8.1 + 1) * .05 * self.wobble
        self.status.text = (f'slices {self.slices}/{self.SLICES_NEEDED}'
                            + (f'  ·  fingers cut: {self.fingers_lost}'
                               if self.fingers_lost else ''))
        # delayed input lands now?
        if self.pending_press is not None and self.t >= self.pending_press:
            self.pending_press = None
            self._resolve_chop()

    def input(self, key):
        if key == 'space' and not self.finished and self.pending_press is None:
            if self.input_delay > 0:
                self.pending_press = self.t + self.input_delay
            else:
                self._resolve_chop()

    # ------------------------------------------------------------------ chop
    def _resolve_chop(self):
        arc = math.sin(self.t * 2.2)
        window = .55 - self.wobble * .25          # tremor shrinks the window
        hand_drift = abs(self.hand.x) + abs(self.hand.z)
        good = arc > window and hand_drift < .05
        if good:
            self._slice()
        elif arc > window - .35 and (self.wobble > 0 or hand_drift >= .05):
            self._cut_finger()
        else:
            self.status.text = 'too early — wait for the top of the arc'

    def _slice(self):
        from ..audio import get_audio
        get_audio().play('kitchen_chop', volume=.5)
        self.slices += 1
        self.veg.scale_x -= .11
        self.veg.x += .055
        s = Entity(parent=self, model='cube', color=Color(.95, .6, .2, 1),
                   position=(.35 + len(self.slice_pile) * .09, .17, .25),
                   rotation_y=random.uniform(-20, 20), scale=(.04, .12, .12))
        self.slice_pile.append(s)
        if self.slices >= self.SLICES_NEEDED:
            self._end(success=True)

    def _cut_finger(self):
        from ..audio import get_audio
        get_audio().play('kitchen_hurt', volume=.6)
        self.fingers_lost += 1
        self.flash.color = Color(1, 0, 0, .55)
        self.flash.animate_color(Color(1, 0, 0, 0), duration=.7)
        if self.fingers:
            f = self.fingers.pop()
            f.parent = self                      # it stays on the board.
            f.color = Color(.75, .35, .3, 1)
            f.position = (f.x, .16, f.z + .1)
            f.rotation_y = random.uniform(-40, 40)
        Entity(parent=self, model='circle', rotation_x=90,   # blood
               position=(-.3, .14, .1), scale=random.uniform(.12, .2),
               color=Color(.5, .05, .05, .9))
        if self.fingers_lost >= 3:
            self._end(success=False)

    def _end(self, success):
        self.finished = True
        def close():
            camera.parent, camera.position, camera.rotation = self._cam_state
            cb = self.on_done
            fingers = self.fingers_lost
            destroy(self.ui)
            destroy(self)
            cb(success, fingers)
        invoke(close, delay=1.0)
