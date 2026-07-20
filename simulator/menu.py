"""Main menu: a slowly rotating 3D plaza behind the selection UI."""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import random

from ursina import (Entity, Text, Button, Color, Sky, Slider, camera, scene, mouse,
                    destroy, time, application, window, invoke)

from .config import STATE, DISABILITIES, SCENARIOS
from .lab_state import active_summary, select_experience
from .npc import NPC

SCENARIO_CLASSES = {}  # filled lazily to avoid circular imports


def _scenario_class(key):
    if not SCENARIO_CLASSES:
        from .school import SchoolTestScenario
        from .train import TrainScenario
        from .zombies import ZombieEscapeScenario
        from .kitchen import KitchenScenario
        from .driving import DrivingScenario
        from .agents import LivingCityScenario
        SCENARIO_CLASSES.update(school=SchoolTestScenario, train=TrainScenario,
                                zombies=ZombieEscapeScenario,
                                kitchen=KitchenScenario, driving=DrivingScenario,
                                living_city=LivingCityScenario)
    return SCENARIO_CLASSES[key]


class MainMenu(Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.accept_input = False
        mouse.locked = False
        self._build_backdrop()
        self._build_ui()
        invoke(self._enable_input, delay=.1)

    def _enable_input(self):
        self.accept_input = True

    # ------------------------------------------------------- 3D backdrop plaza
    def _build_backdrop(self):
        from . import world
        self.sky = Sky()
        self.lights = world.day_lights()
        self.world = Entity(parent=self)

        grass = Entity(parent=self.world, model='plane', scale=110,
                       texture='grass', color=Color(.8, .9, .75, 1))
        grass.texture_scale = (24, 24)
        world.sidewalk(self.world, (0, 0, 0), (12, 64))                # plaza paths
        world.sidewalk(self.world, (0, 0, 0), (64, 12))
        world.fountain(self.world)

        for x, z, size, style in [(-20, 16, (10, 9, 9), 'brick'),
                                  (18, 20, (11, 14, 9), 'concrete'),
                                  (-16, -20, (9, 7, 8), 'brick'),
                                  (22, -14, (10, 11, 9), 'concrete')]:
            world.building(self.world, (x, 0, z), size, style=style, lit_ratio=.45)
        for pos in [(-9, 0, 9), (9, 0, -9), (-26, 0, -4), (27, 0, 3),
                    (-8, 0, 26), (10, 0, 27), (-6, 0, -27)]:
            world.tree(self.world, pos, scale=random.uniform(.85, 1.3))
        for pos in [(7, 0, 7), (-7, 0, -7), (7, 0, -7), (-7, 0, 7)]:
            world.street_lamp(self.world, pos, on=False)
        world.bench(self.world, (0, 0, 12), rotation_y=180)
        world.bench(self.world, (12, 0, 0), rotation_y=90)

        world.ground_details(self.world, area=(60, 60), cracks=10, pebbles=16,
                             leaves=24, tufts=18)
        world.manhole(self.world, (3, 0, 14))
        world.puddle(self.world, (-4, 0, 18), scale=1.8)
        for ang in range(0, 360, 45):                          # flowerbed ring
            import math as _m
            fx = _m.cos(_m.radians(ang)) * 4.4
            fz = _m.sin(_m.radians(ang)) * 4.4
            Entity(parent=self.world, model='sphere', position=(fx, .25, fz),
                   scale=(.22, .3, .22),
                   color=random.choice([Color(.9, .3, .4, 1), Color(.95, .7, .25, 1),
                                        Color(.7, .4, .8, 1), Color(.95, .95, .9, 1)]))

        self.menu_npcs = [
            NPC(parent=self.world, position=(6, 0, 6), expression='happy',
                waypoints=[(6, 6), (12, -8), (-6, -10), (-10, 8)]),
            NPC(parent=self.world, position=(-8, 0, -4),
                waypoints=[(-8, -4), (8, 10), (14, 2)]),
            NPC(parent=self.world, position=(2, 0, -12), expression='tired',
                waypoints=[(2, -12), (-12, 2), (10, 14)], speed=1.8),
        ]

        self.cam_pivot = Entity()
        camera.parent = self.cam_pivot
        camera.position = (0, 16, -34)
        camera.rotation = (24, 0, 0)

    # ---------------------------------------------------------------------- UI
    def _build_ui(self):
        self.ui = Entity(parent=camera.ui)
        Entity(parent=self.ui, model='quad', color=Color(0, 0, 0, .45),
               scale=(2, 2), z=1)
        Entity(parent=self.ui, model='quad', color=Color(.05, .06, .09, .92),
               position=(-.5, .01), scale=(.78, .69), z=.5)
        Entity(parent=self.ui, model='quad', color=Color(.05, .06, .09, .92),
               position=(.5, .01), scale=(.78, .69), z=.5)

        Text(parent=self.ui, text='WALK  IN  MY  WORLD', origin=(0, 0), y=.44,
             scale=2.6, color=Color(1, 1, 1, 1))
        Text(parent=self.ui, text='a 3D disability-awareness simulator', origin=(0, 0),
             y=.38, scale=1, color=Color(.75, .8, .9, 1))

        Text(parent=self.ui, text='1  CHOOSE AN EXPERIENCE', position=(-.52, .30),
             origin=(0, 0), scale=.82, color=Color(.95, .72, .25, 1))
        self.dis_buttons = {}
        for i, (key, d) in enumerate(DISABILITIES.items()):
            b = Button(parent=self.ui, text=f"{d['icon']} {d['name']}",
                       scale=(.34, .055), position=(-.52, .25 - i * .068),
                       color=Color(.13, .15, .2, .9),
                       highlight_color=Color(.25, .3, .4, 1))
            b.text_entity.scale *= .85
            b.on_click = lambda k=key: self.select_disability(k)
            self.dis_buttons[key] = b

        Text(parent=self.ui, text='2  CHOOSE A SCENARIO', position=(.52, .30),
             origin=(0, 0), scale=.82, color=Color(.95, .72, .25, 1))
        self.scn_buttons = {}
        for i, (key, s) in enumerate(SCENARIOS.items()):
            b = Button(parent=self.ui, text=f"{s['icon']} {s['name']}",
                       scale=(.34, .058), position=(.52, .25 - i * .068),
                       color=Color(.13, .15, .2, .9),
                       highlight_color=Color(.25, .3, .4, 1))
            b.on_click = lambda k=key: self.select_scenario(k)
            self.scn_buttons[key] = b

        self.desc_text = Text(parent=self.ui, text='', position=(.36, -.09),
                              scale=.72, color=Color(.9, .9, .95, 1))
        self.active_text = Text(parent=self.ui, text='', position=(.36, -.26),
                                scale=.62, color=Color(.68, .88, .8, 1))

        # blindness slider — appears only for visual impairment
        self.blind_label = Text(parent=self.ui, text='VISUAL INTENSITY', origin=(0, 0),
                                position=(-.52, -.245), scale=.7,
                                color=Color(.8, .8, .8, 1), enabled=False)
        self.blind_slider = Slider(min=0, max=100, default=int(STATE.blindness * 100),
                                   step=1, dynamic=True, parent=self.ui,
                                   position=(-.72, -.29), scale=.78, enabled=False)
        self.blind_slider.on_value_changed = self._on_blindness

        self.start_button = Button(parent=self.ui, text='START SCENARIO', scale=(.3, .07),
                                   position=(.52, -.32), color=Color(.15, .45, .25, 1),
                                   highlight_color=Color(.2, .6, .35, 1),
                                   on_click=self.start_game)
        n_active = len(STATE.lab_effects)
        lab_label = f'ACCESSIBILITY LAB ({n_active} active)' if n_active else 'ACCESSIBILITY LAB'
        self.lab_button = Button(parent=self.ui, text=lab_label, scale=(.34, .055),
                                 position=(-.52, -.35), color=Color(.3, .25, .45, 1),
                                 highlight_color=Color(.4, .35, .55, 1),
                                 on_click=self.open_lab)
        Entity(parent=self.ui, model='quad', position=(0, -.465), scale=(.72, .035),
               color=Color(.03, .035, .05, .86))
        Text(parent=self.ui,
             text='Keyboard: 1-7 experience · 8/9/0 scenario · L lab · Enter start · Esc quit',
             origin=(0, 0), y=-.47, scale=.64, color=Color(.84, .85, .9, 1))

        self.select_disability(STATE.disability or 'none', apply=False)
        self.select_scenario(STATE.scenario)

    # ------------------------------------------------------------------ events
    def select_disability(self, key, apply=True):
        if apply:
            select_experience(STATE, key)
        for k, b in self.dis_buttons.items():
            b.color = DISABILITIES[k]['color'] if k == key else Color(.13, .15, .2, .9)
        self._refresh_desc()
        show = key == 'visual'
        self.blind_label.enabled = show
        self.blind_slider.enabled = show

    def select_scenario(self, key):
        STATE.scenario = key
        for k, b in self.scn_buttons.items():
            b.color = Color(.5, .4, .15, 1) if k == key else Color(.13, .15, .2, .9)
        self._refresh_desc()

    def _refresh_desc(self):
        d = DISABILITIES[STATE.disability or 'none']
        s = SCENARIOS[STATE.scenario]
        self.desc_text.text = f"{d['desc']}\n\n{s['icon']} {s['name']}: {s['desc']}"
        self.active_text.text = active_summary(STATE)

    def _on_blindness(self):
        STATE.blindness = self.blind_slider.value / 100

    def open_lab(self):
        from .lab import LabPanel
        self.ui.enabled = False
        def back():
            self.ui.enabled = True
            n = len(STATE.lab_effects)
            self.lab_button.text = (f'ACCESSIBILITY LAB ({n} active)' if n
                                    else 'ACCESSIBILITY LAB')
            for key, button in self.dis_buttons.items():
                button.color = (DISABILITIES[key]['color']
                                if key == (STATE.disability or 'none')
                                else Color(.13, .15, .2, .9))
            self._refresh_desc()
        LabPanel(on_close=back, on_demo=self.start_lab_demo)

    def start_lab_demo(self):
        from .lab_demo import LabExperienceDemo
        self._clear_menu()
        LabExperienceDemo()

    def start_game(self):
        cls = _scenario_class(STATE.scenario)
        self._clear_menu()
        cls()

    def _clear_menu(self):
        camera.parent = scene
        camera.position = (0, 0, 0)
        camera.rotation = (0, 0, 0)
        self.lights.destroy()
        for npc in self.menu_npcs:
            destroy(npc)
        destroy(self.sky)
        destroy(self.cam_pivot)
        destroy(self.ui)
        destroy(self)

    def update(self):
        self.cam_pivot.rotation_y += 5 * time.dt

    def input(self, key):
        if not self.ui.enabled or not self.accept_input:
            return
        experience_keys = dict(zip('1234567', DISABILITIES, strict=True))
        scenario_keys = {'8': 'school', '9': 'train', '0': 'zombies'}
        if key in experience_keys:
            self.select_disability(experience_keys[key])
        elif key in scenario_keys:
            self.select_scenario(scenario_keys[key])
        elif key == 'l':
            self.open_lab()
        elif key == 'enter':
            self.start_game()
        elif key == 'escape':
            application.quit()
