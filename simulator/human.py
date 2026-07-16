"""Articulated human figure with anatomically proportioned segments and a
kinesiologically plausible gait: legs swing from the hip with knee flexion
during the swing phase, arms counter-swing from the shoulder with elbow bend,
the pelvis rocks and the torso bobs twice per stride and leans into movement.
"""
import math
import random

from ursina import Entity, Color, time

SKIN_TONES = [Color(.95, .8, .68, 1), Color(.87, .68, .55, 1), Color(.72, .53, .4, 1),
              Color(.55, .38, .28, 1), Color(.4, .28, .2, 1)]
HAIR_COLORS = [Color(.1, .08, .06, 1), Color(.25, .16, .08, 1), Color(.5, .35, .15, 1),
               Color(.15, .15, .15, 1), Color(.55, .5, .45, 1)]
SHIRT_COLORS = [Color(.7, .25, .25, 1), Color(.25, .4, .7, 1), Color(.25, .55, .35, 1),
                Color(.65, .55, .2, 1), Color(.5, .3, .6, 1), Color(.75, .45, .25, 1),
                Color(.35, .35, .4, 1), Color(.8, .8, .82, 1)]
PANTS_COLORS = [Color(.2, .22, .3, 1), Color(.25, .25, .27, 1), Color(.35, .28, .22, 1),
                Color(.3, .35, .3, 1)]


class Human(Entity):
    """~1.75 units tall, built from primitives around joint pivots.

    Call advance(moving=..., run=...) every frame (NPC does this for you).
    """

    def __init__(self, skin=None, shirt=None, pants=None, hair=None,
                 hunched=False, **kwargs):
        super().__init__(**kwargs)
        skin = skin or random.choice(SKIN_TONES)
        shirt = shirt or random.choice(SHIRT_COLORS)
        pants = pants or random.choice(PANTS_COLORS)
        hair = hair or random.choice(HAIR_COLORS)
        shoe = Color(.12, .1, .1, 1)
        self.hunched = hunched
        self.phase = random.uniform(0, 6.28)
        self.base_hip_y = .92
        self.talking = False
        self.talk_phase = 0.0
        self._was_talking = False
        # every person moves a little differently
        self.gait = dict(
            freq=random.uniform(.88, 1.15),      # cadence
            stride=random.uniform(.85, 1.15),    # leg swing amplitude
            arm=random.uniform(.75, 1.3),        # arm swing amplitude
            sway=random.uniform(.6, 1.4),        # lateral weight shift
            slouch=random.uniform(-3, 8),        # resting posture
            bounce=random.uniform(.7, 1.25),     # vertical bob
        )

        # ---- pelvis & spine -------------------------------------------------
        self.hips = Entity(parent=self, y=self.base_hip_y)
        Entity(parent=self.hips, model='cube', color=pants, scale=(.32, .18, .2))
        self.torso = Entity(parent=self.hips)                     # lean pivot
        Entity(parent=self.torso, model='cube', color=shirt,      # belly
               scale=(.3, .28, .2), y=.22)
        Entity(parent=self.torso, model='cube', color=shirt,      # chest
               scale=(.36, .3, .22), y=.48)
        Entity(parent=self.torso, model='cube', color=skin,       # neck
               scale=(.09, .12, .09), y=.66)

        # ---- head & face ----------------------------------------------------
        self.head = Entity(parent=self.torso, y=.82)
        Entity(parent=self.head, model='sphere', color=skin, scale=(.22, .26, .23))
        self._build_hair(hair)
        for side in (-.105, .105):                                # ears
            Entity(parent=self.head, model='sphere', color=skin,
                   scale=(.035, .055, .03), position=(side, 0, 0))
        Entity(parent=self.head, model='sphere', color=skin,      # nose
               scale=(.03, .045, .035), position=(0, -.01, .112))

        # eyes: white + iris + pupil + catchlight, grouped so blinking squashes them
        self.eyes = []
        dark = Color(.08, .08, .1, 1)
        iris_color = random.choice([Color(.25, .15, .08, 1), Color(.15, .3, .5, 1),
                                    Color(.2, .35, .2, 1), Color(.4, .3, .15, 1), dark])
        lashes = random.random() < .45
        for side in (-.05, .05):
            pivot = Entity(parent=self.head, position=(side, .025, .09))
            Entity(parent=pivot, model='sphere', color=Color(.95, .95, .93, 1),
                   scale=(.045, .042, .02))
            Entity(parent=pivot, model='sphere', color=iris_color,
                   scale=(.024, .024, .012), z=.012)
            Entity(parent=pivot, model='sphere', color=dark,
                   scale=(.012, .012, .008), z=.018)
            spark = Entity(parent=pivot, model='sphere',              # catchlight
                           color=Color(1, 1, 1, .9), scale=(.006, .006, .004),
                           position=(.007, .008, .022))
            spark.setLightOff()
            if lashes:
                Entity(parent=pivot, model='cube', color=dark,
                       position=(0, .026, .008), rotation_x=-14,
                       scale=(.05, .006, .012))
            self.eyes.append(pivot)
        self.blink_timer = random.uniform(1.5, 5)

        # nostrils, cheekbones, blush and freckles
        for side in (-.012, .012):
            Entity(parent=self.head, model='sphere',
                   color=Color(skin.x * .55, skin.y * .5, skin.z * .5, 1),
                   scale=(.009, .007, .006), position=(side, -.038, .125))
        for side in (-.075, .075):                                    # cheekbones
            Entity(parent=self.head, model='sphere', color=skin,
                   scale=(.05, .04, .03), position=(side, -.04, .075))
        if random.random() < .4:                                      # blush
            blush_c = Color(min(1, skin.x * 1.08), skin.y * .82, skin.z * .82, .4)
            for side in (-.075, .075):
                Entity(parent=self.head, model='sphere', color=blush_c,
                       scale=(.028, .016, .008), position=(side, -.038, .1))
        if random.random() < .15:                                     # freckles
            fr = Color(skin.x * .7, skin.y * .6, skin.z * .55, .9)
            for _ in range(7):
                Entity(parent=self.head, model='sphere', color=fr,
                       scale=.004,
                       position=(random.uniform(-.06, .06), random.uniform(-.05, -.02),
                                 .118 - abs(random.uniform(-.06, .06)) * .25))

        # eyebrows — angle carries most of the emotion
        self.brows = []
        brow_color = Color(hair.x * .8, hair.y * .8, hair.z * .8, 1)
        for side in (-.05, .05):
            brow = Entity(parent=self.head, model='cube', color=brow_color,
                          position=(side, .072, .102), scale=(.055, .013, .012))
            self.brows.append(brow)

        # mouth: two-tone lips, corner pieces that curve, teeth behind an
        # openable dark aperture
        lip_dark = Color(min(1, skin.x * .95), skin.y * .55, skin.z * .55, 1)
        lip_light = Color(min(1, skin.x * 1.05), skin.y * .68, skin.z * .68, 1)
        self.mouth_open_hole = Entity(parent=self.head, model='sphere',
                                      color=Color(.15, .06, .06, 1),
                                      position=(0, -.086, .1), scale=(.001, .001, .01))
        self.teeth = Entity(parent=self.head, model='cube',
                            color=Color(.95, .95, .9, 1),
                            position=(0, -.078, .103), scale=(.001, .001, .008))
        self.teeth.setLightOff()
        self.mouth_mid = Entity(parent=self.head, model='cube', color=lip_dark,
                                position=(0, -.07, .105), scale=(.045, .01, .008))
        self.lower_lip = Entity(parent=self.head, model='cube', color=lip_light,
                                position=(0, -.096, .104), scale=(.04, .009, .008))
        self.mouth_l = Entity(parent=self.head, model='cube', color=lip_dark,
                              position=(-.033, -.07, .104), scale=(.028, .009, .008))
        self.mouth_r = Entity(parent=self.head, model='cube', color=lip_dark,
                              position=(.033, -.07, .104), scale=(.028, .009, .008))

        if random.random() < .28:                                 # glasses (hollow rims)
            frame = Color(.12, .12, .15, 1)
            for side in (-.05, .05):
                Entity(parent=self.head, model='cube', color=frame,      # top / bottom
                       position=(side, .052, .112), scale=(.062, .007, .006))
                Entity(parent=self.head, model='cube', color=frame,
                       position=(side, -.002, .112), scale=(.062, .007, .006))
                for edge in (-.031, .031):                               # sides
                    Entity(parent=self.head, model='cube', color=frame,
                           position=(side + edge, .025, .112),
                           scale=(.007, .06, .006))
            Entity(parent=self.head, model='cube', color=frame,          # bridge
                   position=(0, .045, .112), scale=(.03, .007, .006))
        if random.random() < .18:                                 # chin beard
            Entity(parent=self.head, model='sphere', color=hair,
                   scale=(.085, .045, .05), position=(0, -.122, .07))

        self.expression = 'neutral'
        self.set_expression('neutral')

        # ---- arms (shoulder pivot -> elbow pivot) ---------------------------
        self.arms = {}
        for name, sx in (('l', -.23), ('r', .23)):
            shoulder = Entity(parent=self.torso, position=(sx, .58, 0))
            Entity(parent=shoulder, model='cube', color=shirt,    # upper arm
                   scale=(.09, .3, .1), y=-.15)
            elbow = Entity(parent=shoulder, y=-.31)
            Entity(parent=elbow, model='cube', color=skin,        # forearm
                   scale=(.075, .28, .085), y=-.14)
            Entity(parent=elbow, model='cube', color=skin,        # hand
                   scale=(.07, .09, .09), y=-.31)
            self.arms[name] = (shoulder, elbow)

        # ---- legs (hip pivot -> knee pivot -> ankle pivot) ------------------
        self.legs = {}
        self.feet = {}
        for name, sx in (('l', -.095), ('r', .095)):
            hip = Entity(parent=self.hips, position=(sx, -.06, 0))
            Entity(parent=hip, model='cube', color=pants,         # thigh
                   scale=(.13, .42, .15), y=-.21)
            knee = Entity(parent=hip, y=-.43)
            Entity(parent=knee, model='cube', color=pants,        # shin
                   scale=(.11, .4, .12), y=-.2)
            ankle = Entity(parent=knee, y=-.4)
            Entity(parent=ankle, model='cube', color=shoe,        # foot
                   scale=(.1, .07, .24), y=-.03, z=.05)
            self.legs[name] = (hip, knee)
            self.feet[name] = ankle

        # ---- identity accessories (skip for the hunched/undead) -------------
        if not hunched:
            acc = random.random()
            if acc < .16:                                          # baseball cap
                cap_c = random.choice(SHIRT_COLORS)
                Entity(parent=self.head, model='sphere', color=cap_c,
                       scale=(.24, .14, .25), y=.1)
                Entity(parent=self.head, model='cube', color=cap_c,
                       scale=(.16, .02, .14), position=(0, .09, .18))
            elif acc < .28:                                        # beanie
                Entity(parent=self.head, model='sphere',
                       color=random.choice(SHIRT_COLORS),
                       scale=(.235, .17, .245), y=.09)
            if random.random() < .25:                              # open jacket
                jk = Color(shirt.x * .5, shirt.y * .5, shirt.z * .55, 1)
                for side in (-.13, .13):
                    Entity(parent=self.torso, model='cube', color=jk,
                           position=(side, .35, .1), scale=(.11, .55, .04))
                Entity(parent=self.torso, model='cube', color=jk,   # collar
                       position=(0, .6, .06), scale=(.3, .06, .1))
            elif random.random() < .15:                            # tie
                tie_c = random.choice([Color(.6, .15, .15, 1), Color(.15, .25, .5, 1),
                                       Color(.2, .4, .25, 1)])
                Entity(parent=self.torso, model='cube', color=tie_c,
                       position=(0, .42, .115), scale=(.05, .3, .015))
                Entity(parent=self.torso, model='cube', color=tie_c,
                       position=(0, .24, .112), rotation_z=45, scale=(.05, .05, .015))
            if random.random() < .3:                               # wristwatch
                Entity(parent=self.arms['l'][1], model='cube',
                       color=Color(.2, .2, .25, 1), y=-.26, scale=(.085, .03, .095))

        # soft contact shadow
        self.shadow = Entity(parent=self, model='quad', rotation_x=90, y=.02,
                             scale=1.1, texture='radial_gradient',
                             color=Color(0, 0, 0, .35))
        self.shadow.setLightOff()

        # natural build variation
        self.scale_y *= random.uniform(.94, 1.05)
        self.scale_x *= random.uniform(.95, 1.04)

        if hunched:
            self.torso.rotation_x = 30
            self.head.rotation_x = -18

    # ------------------------------------------------------------------ hair
    def _build_hair(self, hair):
        style = random.choice(['short', 'short', 'long', 'bun', 'bald'])
        if style == 'bald':
            return
        Entity(parent=self.head, model='sphere', color=hair,      # cap
               scale=(.235, .2, .24), y=.06, z=-.02)
        if style == 'long':
            Entity(parent=self.head, model='sphere', color=hair,  # back length
                   scale=(.2, .3, .12), y=-.06, z=-.12)
            for side in (-.1, .1):
                Entity(parent=self.head, model='sphere', color=hair,
                       scale=(.06, .22, .1), position=(side, -.04, -.04))
        elif style == 'bun':
            Entity(parent=self.head, model='sphere', color=hair,
                   scale=(.09, .09, .09), position=(0, .12, -.12))

    # ------------------------------------------------------ facial expression
    EXPRESSIONS = {
        #            brow_angle  brow_raise  mouth_curve  lid   open
        'neutral':   (0,         0,          0,           1,    0),
        'happy':     (-4,        .008,       1,           1,    .3),
        'sad':       (12,        .004,      -1,           1,    0),
        'worried':   (16,        .012,      -.7,          1,    .2),
        'angry':     (-18,      -.008,      -.5,          1,    .4),
        'surprised': (0,         .02,        0,           1,    1),
        'focused':   (-8,       -.004,       0,           .8,   0),
        'tired':     (4,        -.004,      -.3,          .45,  .15),
        'smug':      (-10,       0,          .5,          .7,   0),
        'scared':    (18,        .018,      -.8,          1,    .8),
    }

    def set_expression(self, name):
        """Instantly pose brows, mouth corners, lips, teeth and eyelids."""
        angle, raise_, curve, lid, open_ = self.EXPRESSIONS.get(
            name, self.EXPRESSIONS['neutral'])
        self.expression = name
        left, right = self.brows
        left.rotation_z = -angle
        right.rotation_z = angle
        for brow in self.brows:
            brow.y = .072 + raise_
        self.mouth_l.rotation_z = curve * 18
        self.mouth_r.rotation_z = -curve * 18
        self.mouth_l.y = self.mouth_r.y = -.07 + curve * .008
        # opening the mouth drops the lower lip and reveals the aperture + teeth
        self.lower_lip.y = -.096 - open_ * .014
        if open_ > .05:
            self.mouth_open_hole.scale = (.04, .01 + open_ * .02, .01)
            self.teeth.scale = (.036, .007, .008)
        else:
            self.mouth_open_hole.scale = (.001, .001, .01)
            self.teeth.scale = (.001, .001, .008)
        for eye in self.eyes:
            eye.scale_y = lid

    def _blink(self):
        _, _, _, lid, _ = self.EXPRESSIONS.get(self.expression, self.EXPRESSIONS['neutral'])
        from ursina import invoke
        for eye in self.eyes:
            eye.scale_y = .06
        def reopen():
            for eye in self.eyes:
                eye.scale_y = lid
        invoke(reopen, delay=.12)

    # ------------------------------------------------------------------ gait
    def advance(self, moving=False, speed=2.5):
        """Drive the walk cycle and blinking. Call once per frame."""
        self.blink_timer -= time.dt
        if self.blink_timer <= 0:
            self.blink_timer = random.uniform(2, 6)
            self._blink()

        g = self.gait
        running = speed > 4.5 and not self.hunched
        if moving:
            self.phase += time.dt * (3.2 + speed * 1.1) * g['freq']
            swing = math.sin(self.phase)
            counter = math.sin(self.phase + math.pi)
            stride_amp = (38 if running else 27) * g['stride'] * (.6 if self.hunched else 1)
            knee_amp = 62 if running else 42

            for name, offset in (('l', 0.0), ('r', math.pi)):
                leg_phase = self.phase + offset
                hip, knee = self.legs[name]
                hip.rotation_x = math.sin(leg_phase) * stride_amp
                # knee flexes while its leg swings forward, near-straight in stance
                knee.rotation_x = -max(0.0, math.sin(leg_phase + 1.1)) * knee_amp
                # foot roll: toe-off push behind, toe-up before heel strike
                self.feet[name].rotation_x = (max(0.0, -math.sin(leg_phase + .5)) * 24
                                              - max(0.0, math.sin(leg_phase - .4)) * 10)

            if not self.hunched:
                arm_amp = (34 if running else 24) * g['arm']
                for name, offset in (('l', math.pi), ('r', 0.0)):   # arms counter legs
                    shoulder, elbow = self.arms[name]
                    shoulder.rotation_x = math.sin(self.phase + offset) * arm_amp
                    elbow.rotation_x = -70 if running else -18 - abs(swing) * 12
                self.torso.rotation_x = (14 if running else 5 + speed * .8) + g['slouch'] * .5
                self.torso.rotation_y = counter * (6 if running else 4)
                self.head.rotation_y = -self.torso.rotation_y * .7  # gaze stays forward
                self.head.rotation_x = -self.torso.rotation_x * .5
            else:                                          # zombie shamble
                for name in ('l', 'r'):
                    shoulder, elbow = self.arms[name]
                    shoulder.rotation_x = -72 + math.sin(self.phase * .7) * 8
                    elbow.rotation_x = -25
                self.rotation_z = math.sin(self.phase * .55) * 5

            self.hips.rotation_z = swing * 3               # pelvic rock
            self.hips.x = swing * .02 * g['sway']          # weight shifts side to side
            bob = (.05 if running else .035) * g['bounce']
            self.hips.y = self.base_hip_y - .015 + abs(math.cos(self.phase)) * bob
        else:
            # settle into idle with a slow breathing sway
            self.phase += time.dt * 1.2
            breathe = math.sin(self.phase) * 1.5
            for name in ('l', 'r'):
                hip, knee = self.legs[name]
                hip.rotation_x *= .8
                knee.rotation_x *= .8
                self.feet[name].rotation_x *= .8
                shoulder, elbow = self.arms[name]
                if self.hunched:
                    shoulder.rotation_x = -72
                    elbow.rotation_x = -25
                else:
                    shoulder.rotation_x = shoulder.rotation_x * .8 + breathe * .3
                    elbow.rotation_x = -8
            if not self.hunched:
                self.torso.rotation_x = (self.torso.rotation_x * .8
                                         + (breathe * .2 + g['slouch']) * .2)
                self.torso.rotation_y *= .8
                self.head.rotation_y = math.sin(self.phase * .35) * 7  # idle glances
                self.head.rotation_x *= .8
            self.hips.rotation_z *= .8
            self.hips.x *= .8
            self.hips.y = self.base_hip_y + math.sin(self.phase) * .004

        self._advance_mouth()

    def _advance_mouth(self):
        """Lip sync: flap the mouth while this person is delivering a line."""
        if self.talking:
            self._was_talking = True
            self.talk_phase += time.dt * 11
            open_ = .2 + .5 * abs(math.sin(self.talk_phase + math.sin(self.talk_phase * .53) * 1.7))
            self.mouth_open_hole.scale = (.04, .008 + open_ * .024, .01)
            self.teeth.scale = (.036, .007, .008)
            self.lower_lip.y = -.096 - open_ * .018
        elif self._was_talking:
            self._was_talking = False
            self.set_expression(self.expression)  # restore the posed mouth
