"""Home Kitchen scenario.

Randomized on every run:
- layout: small apartment / large family / cluttered
- lighting: bright daylight / dim evening / flickering
- ambience: fridge hum + any of running water, radio, family chatter

Cooking chain: read the recipe card -> gather ingredients (fridge /
cupboard / counter) -> chop (close-up cutscene, fingers at risk) -> cook on
the stove (burn + house-fire risk) -> serve. Health drops with burns and
cuts; zero health, three lost fingers, or a kitchen fire ends the run.

Accessibility design baked into the room itself:
- low contrast on purpose: white plates on white counters, clear glasses
- stove: tiny knobs, small pale burner indicator (hard with low vision)
- the stove/timer BEEP is sound-only (deaf mode never hears it) but a
  flashing indicator light above the stove is the visual alternative
- glaucoma (lab): peripheral props genuinely vanish until looked at
- ADHD: loud phone notifications + interrupt tasks that block progress
- motor conditions: input delay + wobble inside the chopping cutscene
"""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import math
import random

from ursina import Entity, Text, Color, camera, distance_xz, time as utime, Vec3
from panda3d.core import Vec4 as PVec4

from ..base_scenario import BaseScenario
from ..config import STATE
from .. import world
from .sounds import ensure_kitchen_assets
from .reader import RecipeReader
from .cutscene import ChoppingCutscene

WHITE = Color(.93, .93, .91, 1)          # counters, cupboards, plates: all white
GLASS = Color(.85, .9, .95, .28)

RECIPES = [
    dict(name='Vegetable Stir Fry',
         ingredients=[('carrots', 'fridge'), ('peppers', 'fridge'),
                      ('oil', 'cupboard'), ('rice', 'cupboard')],
         card_lines=['heat oil in the pan on medium',
                     'chop the carrots and peppers small',
                     'stir fry them till they soften',
                     'serve over rice on a plate'],
         check=dict(q='what heat does the pan need?',
                    options=['medium', 'maximum'], answer=0)),
    dict(name='Tomato Soup',
         ingredients=[('tomatoes', 'fridge'), ('onion', 'fridge'),
                      ('stock', 'cupboard'), ('salt', 'counter')],
         card_lines=['dice the onion and the tomatoes',
                     'soften the onion in the pot first',
                     'add tomatoes stock and salt',
                     'simmer and serve it in a bowl'],
         check=dict(q='what goes in the pot first?',
                    options=['the tomatoes', 'the onion'], answer=1)),
    dict(name='Omelette',
         ingredients=[('eggs', 'fridge'), ('butter', 'fridge'),
                      ('cheese', 'fridge'), ('salt', 'counter')],
         card_lines=['whisk the eggs with a pinch of salt',
                     'melt butter in the pan on low heat',
                     'pour eggs and add the cheese',
                     'fold it over and plate it up'],
         check=dict(q='what heat for the butter?',
                    options=['low', 'high'], answer=0)),
]

INTERRUPTS = [
    dict(id='phone', prompt='your phone is BUZZING — press P to silence it', key='p'),
    dict(id='texts', prompt='3 new messages demand a reply — press P', key='p'),
    dict(id='trash', prompt='the trash reeks — take it out (E at the door)', key=None),
]


class KitchenScenario(BaseScenario):
    player_start = (0, 0, -2.5)
    sky_color = Color(.05, .05, .07, 1)      # indoors: no skybox

    # ------------------------------------------------------------------ build
    def build(self):
        ensure_kitchen_assets()
        self.layout = random.choice(['apartment', 'family', 'cluttered'])
        self.light_mode = random.choice(['day', 'evening', 'flicker'])
        self.recipe = random.choice(RECIPES)

        self.health = 100
        self.stage = 'read'
        self.collected = set()
        self.fingers_lost = 0
        self.pan_on = False
        self.heat = 0.0
        self.flames = []
        self.fire_deadline = None
        self.interrupt = None
        self.interrupt_cooldown = 8
        self.periph_props = []               # glaucoma: things that can vanish
        self.t = 0
        self.flicker_t = 0
        self.reader_open = False

        self._build_room()
        self._build_lighting()
        self._start_ambience()
        self.player.rotation_y = 205        # face the counters and stove

        self.health_text = Text(parent=self.hud, text='', position=(.66, .385),
                                scale=.78, color=Color(.95, .6, .6, 1))
        self.set_objective('Read the recipe card on the counter (E)')

    # -------------------------------------------------------------- the room
    def _build_room(self):
        big = self.layout != 'apartment'
        self.W = 16 if big else 9            # room width  (x)
        self.D = 12 if big else 8            # room depth  (z)
        W, D = self.W, self.D
        wall_c = Color(.88, .87, .83, 1)

        floor = self.make_box((0, -.5, 0), (W, 1, D), Color(.82, .78, .72, 1))
        floor.texture = 'white_cube'
        floor.texture_scale = (W // 2, D // 2)
        self.make_box((0, 3.2, 0), (W, .3, D), Color(.92, .92, .9, 1))     # ceiling
        for pos, scale in [((0, 1.6, D / 2), (W, 3.2, .3)),
                           ((0, 1.6, -D / 2), (W, 3.2, .3)),
                           ((-W / 2, 1.6, 0), (.3, 3.2, D)),
                           ((W / 2, 1.6, 0), (.3, 3.2, D))]:
            self.make_box(pos, scale, wall_c)

        # window(s) on the back wall — their glow sells the time of day
        glow = {'day': Color(.85, .92, 1, 1), 'evening': Color(.18, .16, .3, 1),
                'flicker': Color(.14, .13, .22, 1)}[self.light_mode]
        for wx in ([-W / 4, W / 4] if big else [0]):
            win = Entity(parent=self, model='quad', position=(wx, 1.9, D / 2 - .14),
                         scale=(2.2, 1.5), color=glow)
            win.setLightOff()
            self.make_box((wx, 1.9, D / 2 - .12), (.08, 1.6, .1),
                          Color(.5, .45, .4, 1), collider=None)

        # ceiling lamp (the one that flickers)
        self.lamp = Entity(parent=self, model='cube', position=(0, 3.02, 0),
                           scale=(1.6, .12, .8), color=Color(1, .97, .88, 1))
        self.lamp.setLightOff()

        # ---- counters along the left wall: white on white on purpose -------
        cz = -D / 2 + .8
        counter_y = .95
        self.make_box((-W / 2 + 2.6, .45, cz), (5, .9, 1.4), WHITE)        # base
        self.make_box((-W / 2 + 2.6, counter_y, cz), (5.2, .12, 1.5), WHITE)
        for i in range(3):                                                 # cupboards
            door = self.make_box((-W / 2 + 1.2 + i * 1.6, .45, cz + .76),
                                 (1.4, .7, .06), WHITE, collider=None)
            Entity(parent=self, model='sphere', scale=.05,                 # handle
                   position=(-W / 2 + 1.7 + i * 1.6, .5, cz + .8),
                   color=Color(.8, .8, .8, 1))
        # white plates stacked on the white counter (deliberate low contrast)
        for i in range(4):
            self.make_box((-W / 2 + 1.2, 1.03 + i * .05, cz), (.5, .04, .5),
                          Color(.96, .96, .95, 1), collider=None)
        for gx in (-W / 2 + 2.2, -W / 2 + 2.5):                            # clear glasses
            g = Entity(parent=self, model='cube', position=(gx, 1.13, cz),
                       scale=(.12, .22, .12), color=GLASS)
            self.periph_props.append(g)

        # cutting board on the counter
        self.board_pos = Vec3(-W / 2 + 3.8, 0, cz)
        self.make_box((self.board_pos.x, 1.03, cz), (.9, .05, .6),
                      Color(.7, .53, .34, 1), collider=None)
        # the recipe card next to it
        self.recipe_pos = Vec3(-W / 2 + 2.6, 0, cz)
        card = Entity(parent=self, model='quad', rotation_x=90,
                      position=(self.recipe_pos.x, 1.03, cz + .3),
                      scale=(.35, .45), color=Color(.95, .93, .85, 1))
        card.setLightOff()

        # ---- fridge ----------------------------------------------------------
        self.fridge_pos = Vec3(-W / 2 + .9, 0, -D / 2 + 2.6)
        self.make_box((self.fridge_pos.x, 1.05, self.fridge_pos.z),
                      (1.1, 2.1, 1), Color(.9, .91, .9, 1))
        self.make_box((self.fridge_pos.x + .5, 1.2, self.fridge_pos.z + .3),
                      (.06, .8, .06), Color(.7, .7, .7, 1), collider=None)

        # ---- stove -----------------------------------------------------------
        self.stove_pos = Vec3(W / 2 - 1.4, 0, -D / 2 + 1)
        sp = self.stove_pos
        self.make_box((sp.x, .48, sp.z), (1.6, .96, 1.3), Color(.85, .85, .84, 1))
        self.make_box((sp.x, .98, sp.z), (1.62, .06, 1.32), Color(.2, .2, .22, 1))
        self.burners = []
        for bx, bz in [(-.4, -.25), (.4, -.25), (-.4, .3), (.4, .3)]:
            b = Entity(parent=self, model='circle', rotation_x=90,
                       position=(sp.x + bx, 1.02, sp.z + bz), scale=.42,
                       color=Color(.1, .1, .1, 1))
            self.burners.append(b)
        # tiny knobs + a small pale indicator: hard to read with low vision BY DESIGN
        for i in range(4):
            k = Entity(parent=self, model='sphere', scale=.045,
                       position=(sp.x - .45 + i * .3, .93, sp.z - .68),
                       color=Color(.75, .75, .73, 1))
            self.periph_props.append(k)
        self.small_indicator = Entity(parent=self, model='circle',
                                      position=(sp.x + .62, .93, sp.z - .66),
                                      rotation_x=20, scale=.04,
                                      color=Color(.4, .3, .3, 1))
        # the BIG flashing light above the stove: the deaf-accessible signal
        self.stove_beacon = Entity(parent=self, model='circle',
                                   position=(sp.x, 2.4, sp.z + .4),
                                   scale=.22, color=Color(.25, .25, .25, 1))
        self.stove_beacon.setLightOff()
        # the pan
        self.pan = Entity(parent=self, model='circle', rotation_x=90,
                          position=(sp.x - .4, 1.05, sp.z - .25), scale=.5,
                          color=Color(.25, .25, .28, 1))
        Entity(parent=self.pan, model='cube', position=(0, .8, 0),
               scale=(.15, 1.2, .06), color=Color(.15, .15, .15, 1))

        # ---- sink ------------------------------------------------------------
        self.make_box((W / 2 - 1.4, .48, -D / 2 + 3), (1.4, .96, 1.2), WHITE)
        self.make_box((W / 2 - 1.4, .99, -D / 2 + 3), (1, .08, .8),
                      Color(.8, .82, .84, 1), collider=None)
        Entity(parent=self, model='cube', position=(W / 2 - 1.4, 1.25, -D / 2 + 3.35),
               scale=(.07, .5, .07), color=Color(.75, .77, .8, 1))

        # ---- table (serving zone) ---------------------------------------------
        self.table_pos = Vec3(W / 4 if self.layout == 'family' else 0, 0, D / 2 - 2.2)
        tp = self.table_pos
        self.make_box((tp.x, .8, tp.z), (2.4 if self.layout == 'family' else 1.6,
                                         .1, 1.2), Color(.6, .45, .3, 1))
        for lx, lz in [(-.7, -.4), (.7, -.4), (-.7, .4), (.7, .4)]:
            self.make_box((tp.x + lx, .4, tp.z + lz), (.1, .8, .1),
                          Color(.45, .33, .22, 1), collider=None)
        # a white plate on the table (again: white, hard to spot)
        self.make_box((tp.x, .88, tp.z), (.5, .04, .5), Color(.96, .96, .95, 1),
                      collider=None)

        # the door (used by the ADHD 'take out the trash' interruption)
        self.door_pos = Vec3(0, 0, -self.D / 2 + .4)
        self.make_box((0, 1.3, -D / 2 + .2), (1.5, 2.6, .15),
                      Color(.5, .38, .26, 1), collider=None)

        # clutter pass for the cluttered layout
        if self.layout == 'cluttered':
            for _ in range(14):
                p = Entity(parent=self, model='cube',
                           position=(random.uniform(-W / 2 + 1.5, W / 2 - 1.5), .2,
                                     random.uniform(-D / 2 + 1.8, D / 2 - 1.8)),
                           rotation_y=random.uniform(0, 90),
                           scale=(random.uniform(.2, .6), random.uniform(.15, .5),
                                  random.uniform(.2, .5)),
                           color=random.choice([Color(.6, .5, .35, 1), WHITE,
                                                Color(.4, .45, .5, 1)]))
                self.periph_props.append(p)
            for i in range(5):                                     # dish mountain
                d = self.make_box((self.W / 2 - 1.4, 1.06 + i * .06, -self.D / 2 + 3),
                                  (.45 - i * .04, .05, .45 - i * .04),
                                  Color(.95, .95, .93, 1), collider=None)
                self.periph_props.append(d)

        # family layout: someone else is in the room, making it look easy
        if self.layout == 'family':
            self.add_npc(name='Sam (family)', position=(tp.x, 0, tp.z - 1.6),
                         expression='happy',
                         lines=["Smells... interesting. Need a hand?",
                                'I could do this with my eyes closed.'])

    # ------------------------------------------------------------- lighting
    def _build_lighting(self):
        if self.light_mode == 'day':
            self.lights = world.SceneLights(ambient=(.55, .55, .58),
                                            sun=(.7, .68, .6), sun_hpr=(30, -60, 0))
        else:
            self.lights = world.SceneLights(ambient=(.42, .38, .36),
                                            sun=(.4, .36, .32), sun_hpr=(30, -60, 0))
        self._ambient_base = (.55, .55, .58) if self.light_mode == 'day' else (.42, .38, .36)

    def _start_ambience(self):
        from ..audio import get_audio
        audio = get_audio()
        audio.play('kitchen_hum', volume=.25, loop=True)          # fridge, always
        extra = random.sample(['kitchen_water', 'kitchen_radio', 'kitchen_chatter'],
                              k=random.randint(1, 3))
        self.ambience = ['fridge hum'] + extra
        for cue in extra:
            audio.play(cue, volume=.22, loop=True)

    # ------------------------------------------------------------------ tick
    def tick(self):
        dt = utime.dt
        self.t += dt
        self.health_text.text = f'health {int(self.health)}'

        # flickering lights
        if self.light_mode == 'flicker':
            self.flicker_t -= dt
            if self.flicker_t <= 0:
                self.flicker_t = random.uniform(.08, .9)
                on = random.random() > .35
                r, g, b = self._ambient_base
                scale = 1.0 if on else .25
                self.lights.ambient_np.node().setColor(
                    PVec4(r * scale, g * scale, b * scale, 1))
                self.lamp.color = (Color(1, .97, .88, 1) if on
                                   else Color(.3, .3, .3, 1))

        # glaucoma (lab): peripheral props vanish until looked toward
        if 'glaucoma' in STATE.active_fx:
            for p in self.periph_props:
                to_p = (p.world_position - camera.world_position).normalized()
                p.visible = camera.forward.dot(to_p) > .82
        # stove heat / fire simulation
        self._tick_stove(dt)
        # ADHD interruptions block progress
        self._tick_interrupts(dt)
        # zone prompts
        if not self.dialogue.enabled and not self.reader_open:
            self.interact_hint.text = self._zone_prompt() or self.interact_hint.text

        if self.health <= 0:
            self.finish('OVERCOME BY INJURIES',
                        'Burns and cuts added up. Cooking dinner should not\n'
                        'bring anyone this close to the edge.', success=False)

    def _tick_stove(self, dt):
        if not self.pan_on:
            return
        self.heat = min(130, self.heat + dt * 6)
        hot = self.heat > 45
        done = 70 <= self.heat <= 100
        burning = self.heat > 100
        # small pale indicator (the inaccessible one)
        self.small_indicator.color = (Color(.8, .45, .3, 1) if hot
                                      else Color(.4, .3, .3, 1))
        # the accessible beacon: green flash when done, fast red when burning
        blink = math.sin(self.t * (14 if burning else 6)) > 0
        if burning:
            self.stove_beacon.color = Color(1, .15, .1, 1) if blink else Color(.3, .05, .05, 1)
        elif done:
            self.stove_beacon.color = Color(.2, 1, .3, 1) if blink else Color(.1, .35, .12, 1)
        else:
            self.stove_beacon.color = Color(.25, .25, .25, 1)
        if done and not getattr(self, '_beeped', False):
            self._beeped = True
            from ..audio import get_audio
            get_audio().play('kitchen_timer', volume=.6)     # deaf mode: silence
            self.announcer.sound('the stove timer beeps', 3, cue=None)
        if burning and not self.flames:
            self._ignite()
        # standing against a hot stove burns you
        if hot and distance_xz(self.player.position, self.stove_pos) < 1.1:
            self.health -= dt * 6
            if random.random() < dt:
                self.announcer.visual('you brush the hot stove — step back!', 2,
                                      Color(1, .5, .4, 1))
        if self.flames:
            for f in self.flames:
                f.scale_y = 1 + math.sin(self.t * 9 + f.x) * .3
            if self.t > self.fire_deadline:
                self.finish('THE KITCHEN CAUGHT FIRE',
                            'The pan burned, the fire spread, and the house was\n'
                            'lost. A timer you cannot hear is a timer that does\n'
                            'not exist — unless someone designs a visual one.',
                            success=False)

    def _ignite(self):
        from ..audio import get_audio
        get_audio().play('kitchen_alarm', volume=.7)          # deaf: never heard
        self.announcer.visual('!! THE PAN IS ON FIRE — press X to smother it !!',
                              6, Color(1, .4, .3, 1))
        self.fire_deadline = self.t + 9
        sp = self.stove_pos
        for i in range(4):
            f = Entity(parent=self, model='cube',
                       position=(sp.x - .4 + random.uniform(-.2, .2),
                                 1.3 + i * .18, sp.z - .25),
                       scale=(.3 - i * .05, .35, .25 - i * .04),
                       color=Color(1, .45 + i * .1, .1, .9))
            f.setLightOff()
            self.flames.append(f)

    def _tick_interrupts(self, dt):
        adhd = STATE.disability == 'adhd' or 'adhd_fx' in STATE.active_fx
        if not adhd:
            return
        if self.interrupt is None:
            self.interrupt_cooldown -= dt
            if self.interrupt_cooldown <= 0:
                self.interrupt = dict(random.choice(INTERRUPTS))
                from ..audio import get_audio
                get_audio().play('kitchen_notify', volume=1.0)   # LOUD, by design
                self.announcer.visual('* ' + self.interrupt['prompt'] + ' *', 5,
                                      Color(1, .75, .3, 1))

    def _blocked(self):
        if self.interrupt:
            self.announcer.visual("you can't focus on cooking — deal with: "
                                  + self.interrupt['prompt'], 3, Color(1, .7, .3, 1))
            return True
        return False

    # ------------------------------------------------------------------ zones
    def _near(self, pos, r=1.6):
        return distance_xz(self.player.position, pos) < r

    def _zone_prompt(self):
        if self.interrupt and self.interrupt['id'] == 'trash' and self._near(self.door_pos):
            return '[E] take out the trash'
        if self.stage == 'read' and self._near(self.recipe_pos):
            return '[E] read the recipe card'
        if self.stage == 'gather':
            for name, src in self.recipe['ingredients']:
                if name in self.collected:
                    continue
                pos = {'fridge': self.fridge_pos, 'cupboard': self.recipe_pos,
                       'counter': self.board_pos}[src]
                if self._near(pos):
                    return f'[E] take the {name} ({src})'
        if self.stage == 'chop' and self._near(self.board_pos):
            return '[E] start chopping'
        if self.stage == 'cook':
            if self._near(self.stove_pos, 1.8):
                if self.flames:
                    return '[X] smother the fire!'
                if not self.pan_on:
                    return '[E] start cooking (watch the stove light!)'
                return '[E] take the pan off'
        if self.stage == 'serve' and self._near(self.table_pos, 1.8):
            return '[E] plate up and serve'
        return ''

    # ------------------------------------------------------------------ input
    def input(self, key):
        if self.reader_open:
            return
        super().input(key)
        if self.finished:
            return
        if key == 'p' and self.interrupt and self.interrupt.get('key') == 'p':
            self._clear_interrupt('phone silenced... where was I?')
            return
        if key == 'x' and self.flames and self._near(self.stove_pos, 2.2):
            self._extinguish()
            return
        if key != 'e':
            return
        if self.interrupt and self.interrupt['id'] == 'trash' and self._near(self.door_pos):
            self._clear_interrupt('trash is out. now... what was I doing?')
            return
        if self.stage == 'read' and self._near(self.recipe_pos):
            self._open_reader()
        elif self.stage == 'gather':
            self._try_gather()
        elif self.stage == 'chop' and self._near(self.board_pos):
            if not self._blocked():
                self._start_chop()
        elif self.stage == 'cook' and self._near(self.stove_pos, 1.8):
            if not self._blocked():
                self._stove_interact()
        elif self.stage == 'serve' and self._near(self.table_pos, 1.8):
            if not self._blocked():
                self.finish('DINNER IS SERVED',
                            f'{self.recipe["name"]} — cooked in a {self.layout} '
                            f'kitchen under {self.light_mode} light.\n'
                            f'Health left: {int(self.health)}'
                            + (f' · fingers lost: {self.fingers_lost}'
                               if self.fingers_lost else ''),
                            success=True)

    def _clear_interrupt(self, msg):
        self.interrupt = None
        self.interrupt_cooldown = random.uniform(14, 26)
        self.announcer.visual(msg, 3, Color(.7, .9, .7, 1))

    # ------------------------------------------------------------- stage steps
    def _open_reader(self):
        self.reader_open = True
        self.player.enabled = False
        from ursina import mouse
        mouse.locked = False

        def done(understood):
            self.reader_open = False
            self.player.enabled = True
            mouse.locked = True
            if understood:
                self.stage = 'gather'
                need = ', '.join(n for n, _ in self.recipe['ingredients'])
                self.set_objective(f'Gather: {need}')
            else:
                self.announcer.visual('...that is not what it said. Read it again.',
                                      4, Color(1, .6, .5, 1))
        RecipeReader(self.recipe, on_done=done)

    def _try_gather(self):
        if self._blocked():
            return
        for name, src in self.recipe['ingredients']:
            if name in self.collected:
                continue
            pos = {'fridge': self.fridge_pos, 'cupboard': self.recipe_pos,
                   'counter': self.board_pos}[src]
            if self._near(pos):
                self.collected.add(name)
                self.announcer.visual(f'got the {name}', 2, Color(.7, .9, .7, 1))
                break
        if len(self.collected) == len(self.recipe['ingredients']):
            self.stage = 'chop'
            self.set_objective('Chop the vegetables at the cutting board (E)')

    def _start_chop(self):
        self.reader_open = True                      # reuse the modal flag
        self.player.enabled = False

        def done(success, fingers):
            self.reader_open = False
            self.player.enabled = True
            self.fingers_lost += fingers
            self.health -= fingers * 22
            if not success:
                self.finish('THE KNIFE WON',
                            'Three fingers on the board. With an unsteady hand,\n'
                            'a task this ordinary is this dangerous.', success=False)
                return
            if self.health > 0:
                self.stage = 'cook'
                self.set_objective('Cook it on the stove — watch the beacon light')
        ChoppingCutscene(on_done=done)

    def _stove_interact(self):
        if not self.pan_on:
            self.pan_on = True
            self.heat = 0
            self._beeped = False
            from ..audio import get_audio
            get_audio().play('kitchen_sizzle', volume=.4)
            self.announcer.visual('cooking... take the pan off when the light '
                                  'above the stove flashes GREEN', 5)
            return
        # taking the pan off
        if self.heat > 100:                          # grabbing a flaming pan
            self.health -= 20
            self.announcer.visual('you grabbed the burning pan — BURNED', 3,
                                  Color(1, .4, .3, 1))
            from ..audio import get_audio
            get_audio().play('kitchen_hurt', volume=.6)
        elif self.heat >= 70:
            self.pan_on = False
            self.stage = 'serve'
            self.stove_beacon.color = Color(.25, .25, .25, 1)
            self.set_objective('Perfect. Serve it at the table (E)')
        else:
            self.announcer.visual('not cooked yet — wait for the green flash', 2)

    def _extinguish(self):
        for f in self.flames:
            from ursina import destroy
            destroy(f)
        self.flames = []
        self.pan_on = False
        self.heat = 0
        self.health -= 10                            # you got singed doing it
        self.stove_beacon.color = Color(.25, .25, .25, 1)
        self.announcer.visual('fire out. hands shaking. dinner: ruined. '
                              'put the pan back on to retry.', 5)
        self.stage = 'cook'
