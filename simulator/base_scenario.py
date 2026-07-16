"""Base scenario: world root, player, HUD, NPC interaction, reflection screen."""
from ursina import (Entity, Text, Button, Color, camera, scene, mouse, destroy,
                    distance_xz, Sky, window)

from .config import STATE, DISABILITIES, REFLECTIONS
from .dialogue import DialogueBox, Announcer
from .effects import EffectsManager
from .npc import NPC
from .player import create_player


class BaseScenario(Entity):
    """Subclasses build their world in build(), then drive it via tick()."""

    player_start = (0, 0, 0)
    sky_color = None  # None = default Sky()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.finished = False
        self.npcs = []

        if self.sky_color:
            window.color = self.sky_color
        else:
            self.sky = Sky()

        self.player = create_player(position=self.player_start)
        self.dialogue = DialogueBox()
        self.announcer = Announcer()
        self.effects = EffectsManager(player=self.player, announcer=self.announcer)

        d = DISABILITIES[STATE.disability or 'none']
        Text(parent=camera.ui, text=f"{d['icon']} {d['name']}", position=(-.86, .40),
             scale=.85, color=Color(.8, .8, .8, .9))
        self.objective_text = Text(parent=camera.ui, text='', origin=(0, 0), y=.47,
                                   scale=1.1, color=Color(1, 1, .6, 1))
        self.interact_hint = Text(parent=camera.ui, text='', origin=(0, 0), y=-.2,
                                  scale=.9, color=Color(.9, .9, .9, .9))
        Text(parent=camera.ui, text='WASD move · mouse look · E interact · Esc quit to menu',
             position=(0, -.48), origin=(0, 0), scale=.75, color=Color(.55, .55, .55, 1))

        self.build()
        mouse.locked = True

    # ------------------------------------------------------------ overridables
    def build(self):
        pass

    def tick(self):
        pass

    # ----------------------------------------------------------------- helpers
    def set_objective(self, text):
        self.objective_text.text = f'> {text}'
        from .audio import get_audio
        get_audio().speak(f'Objective: {text}')

    def add_npc(self, *args, **kwargs):
        npc = NPC(*args, **kwargs)
        self.npcs.append(npc)
        return npc

    def nearest_npc(self, max_dist=3):
        best, best_d = None, max_dist
        for npc in self.npcs:
            if not npc.enabled:
                continue
            d = distance_xz(npc.position, self.player.position)
            if d < best_d:
                best, best_d = npc, d
        return best

    def make_box(self, position, scale, color, collider='box', **kwargs):
        return Entity(parent=self, model='cube', position=position, scale=scale,
                      color=color, collider=collider, **kwargs)

    # ------------------------------------------------------------- mockery
    def setup_mockery(self, spawn_pos=None):
        """Spawn the scenario's mocker for the current disability, if any."""
        from .config import MOCKERY
        self.mock_conf = MOCKERY.get(STATE.scenario, {}).get(STATE.disability)
        self.mock_fired = False
        if self.mock_conf and self.mock_conf.get('lines') and spawn_pos:
            self.mocker = self.add_npc(name=self.mock_conf['name'],
                                       position=spawn_pos, expression='smug',
                                       lines=self.mock_conf['lines'])
            return self.mocker

    def tick_mockery(self, t):
        conf = getattr(self, 'mock_conf', None)
        if conf and not self.mock_fired and t >= conf['taunt_time']:
            self.mock_fired = True
            self.announcer.visual(conf['taunt'], 5, Color(1, .55, .5, 1))

    # ------------------------------------------------------------------ update
    def update(self):
        if self.finished:
            return
        npc = self.nearest_npc()
        if npc and not self.dialogue.enabled:
            self.interact_hint.text = f'[E] talk to {npc.npc_name}'
        elif not self.dialogue.enabled:
            self.interact_hint.text = ''
        self.tick()

    def input(self, key):
        if self.finished:
            return
        if key == 'escape':
            self.exit_to_menu()
            return
        if key == 'e' and not self.dialogue.enabled:
            npc = self.nearest_npc()
            if npc:
                npc.face(self.player.position)
                self.player.enabled = False
                mouse.locked = False
                def done():
                    self.player.enabled = True
                    mouse.locked = True
                self.dialogue.say(npc.npc_name, npc.lines, on_done=done,
                                  speaker_entity=npc)

    # -------------------------------------------------------------- end states
    def finish(self, title, summary, success=True):
        if self.finished:
            return
        self.finished = True
        self.player.enabled = False
        mouse.locked = False
        self.objective_text.text = ''
        self.interact_hint.text = ''
        from .audio import get_audio
        audio = get_audio()
        audio.play('success' if success else 'fail', volume=.55)
        audio.speak(f'{title}. {summary}')

        ui = Entity(parent=camera.ui)
        Entity(parent=ui, model='quad', color=Color(0, 0, 0, .88), scale=(2, 2), z=1)
        Text(parent=ui, text=title, origin=(0, 0), y=.32, scale=2.2,
             color=Color(.4, .9, .5, 1) if success else Color(.95, .4, .4, 1))
        Text(parent=ui, text=summary, origin=(0, 0), y=.16, scale=1.1,
             color=Color(.95, .95, .95, 1))
        Text(parent=ui, text='— why this matters —', origin=(0, 0), y=.02, scale=.9,
             color=Color(.7, .7, .5, 1))
        Text(parent=ui, text=REFLECTIONS[STATE.disability or 'none'], origin=(0, 0),
             y=-.12, scale=1, color=Color(.85, .85, 1, 1))
        Button(parent=ui, text='Try again', scale=(.22, .07), position=(-.15, -.32),
               color=Color(.2, .4, .3, 1), on_click=self.retry)
        Button(parent=ui, text='Back to menu', scale=(.22, .07), position=(.15, -.32),
               color=Color(.25, .25, .35, 1), on_click=self.exit_to_menu)

    def retry(self):
        cls = type(self)
        self.cleanup()
        cls()

    def exit_to_menu(self):
        self.cleanup()
        from .menu import MainMenu
        MainMenu()

    def cleanup(self):
        from .audio import get_audio
        get_audio().stop_all()
        if hasattr(self, 'lights'):
            self.lights.destroy()
        camera.parent = scene
        camera.position = (0, 0, 0)
        camera.rotation = (0, 0, 0)
        camera.overlay.color = Color(0, 0, 0, 0)
        scene.clearFog()
        mouse.locked = False
        window.color = Color(0.04, 0.05, 0.09, 1)
        destroy(self.player)
        destroy(self.dialogue)
        destroy(self.announcer)
        destroy(self.effects)
        if hasattr(self, 'sky'):
            destroy(self.sky)
        for npc in self.npcs:
            destroy(npc)
        # UI texts parented to camera.ui but created via helpers hang off camera.ui;
        # destroy everything we own by destroying self last (children go with it).
        for child in camera.ui.children[:]:
            if child not in (camera.overlay,):
                destroy(child)
        destroy(self)
