"""Small interactive space used to demonstrate original experience mechanics."""


from __future__ import annotations

if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

from ursina import Color, Entity, Text, camera, destroy, invoke, mouse, scene, time, window

from .audio import get_audio
from .config import DISABILITIES, STATE
from .dialogue import dyslexify
from .effects import EffectsManager
from .player import create_player
from . import world


class LabExperienceDemo(Entity):
    """A short, reversible terrain/audio/text comparison launched from the lab."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ui = Entity(parent=camera.ui)
        self.lights = world.day_lights()
        self.player = create_player(position=(0, 1, -12))
        self.effects = EffectsManager(player=self.player)
        self.base_sign = "STAIRS LEFT  |  ACCESSIBLE RAMP RIGHT"
        self.sign_timer = 0.0

        Entity(parent=self, model="plane", texture="white_cube", texture_scale=(8, 12),
               scale=(30, 1, 42), color=Color(.32, .35, .38, 1), collider="box")

        # A stepped shortcut demonstrates an environmental barrier. The parallel
        # ramp reaches the same platform without implying that either route is universal.
        for index in range(6):
            Entity(parent=self, model="cube", position=(-4, .25 + index * .25, index * 1.0),
                   scale=(5, .5 + index * .5, 1), color=Color(.52, .52, .56, 1),
                   collider="box")
        Entity(parent=self, model="cube", position=(5, 1.4, 3), rotation_x=-14,
               scale=(5, .35, 12), color=Color(.26, .52, .38, 1), collider="box")
        Entity(parent=self, model="cube", position=(0, 3.0, 7), scale=(16, .5, 6),
               color=Color(.42, .44, .48, 1), collider="box")

        self.world_sign = Text(parent=self, text=self.base_sign, position=(0, 4.1, 8.5),
                               billboard=True, origin=(0, 0), scale=7,
                               color=Color(1, .92, .55, 1))
        Text(parent=self.ui, text="ORIGINAL EXPERIENCE LIVE DEMO", origin=(0, 0), y=.46,
             scale=1.15, color=Color(1, .82, .35, 1))
        experience = DISABILITIES[STATE.disability or "none"]["name"]
        Text(parent=self.ui, text=f"Active: {experience}", position=(-.84, .41),
             scale=.78, color=Color(.75, .9, .82, 1))
        Text(parent=self.ui,
             text="Educational approximation—not a difficulty or horror mode. Experiences vary.",
             origin=(0, 0), y=.40, scale=.68, color=Color(.88, .88, .94, 1))
        Text(parent=self.ui,
             text="Try both routes · listen for the bell · read the sign · F refocus · Esc return",
             origin=(0, 0), y=-.47, scale=.7, color=Color(.78, .8, .86, 1))
        Text(parent=self.ui, text="VISUAL ALTERNATIVE: ramp route open on the right",
             origin=(0, 0), y=.34, scale=.72, color=Color(.5, 1, .72, 1))

        invoke(self._play_audio_information, delay=1.2)
        mouse.locked = True

    def _play_audio_information(self) -> None:
        if self.enabled:
            get_audio().play("bell", volume=.65)

    def update(self) -> None:
        if STATE.disability != "dyslexia":
            return
        self.sign_timer -= time.dt
        if self.sign_timer <= 0:
            self.sign_timer = .22
            self.world_sign.text = dyslexify(self.base_sign)

    def input(self, key: str) -> None:
        if key == "escape":
            self.exit_to_menu()

    def exit_to_menu(self) -> None:
        get_audio().stop_all()
        destroy(self.effects)
        destroy(self.player)
        destroy(self.ui)
        self.lights.destroy()
        camera.parent = scene
        camera.position = (0, 0, 0)
        camera.rotation = (0, 0, 0)
        camera.overlay.color = Color(0, 0, 0, 0)
        scene.clearFog()
        mouse.locked = False
        window.color = Color(.04, .05, .09, 1)
        destroy(self)
        from .menu import MainMenu
        MainMenu()
