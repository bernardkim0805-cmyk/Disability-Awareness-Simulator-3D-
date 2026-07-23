"""Per-disability sensory and attention effects applied on top of any scenario."""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import random

from ursina import (Entity, Text, Color, camera, scene, destroy, time, Vec3)

from .config import STATE


ADHD_DISTRACTIONS = [
    'bzzt. bzzt. Your phone. Who texted? Check it. Check it now.',
    'That poster on the wall... you have read it four times already.',
    'A song is stuck in your head. All of it. On loop.',
    'Wait — did you lock the front door this morning?',
    'A fly. Where did it go. WHERE DID IT GO.',
    'Someone is tapping a pen. tap. tap. tap. tap.',
]

WHISPERS = [
    'they are watching you', "don't trust them", 'you will fail',
    'they all know', 'behind you', 'it was your fault',
    'why would they help you', 'leave. leave now.',
]


class VisualUIBlur(Entity):
    """Apply visual-mode blur to UI text created by any scenario."""

    DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1),
                  (.707, .707), (-.707, .707), (.707, -.707), (-.707, -.707))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.copies = []
        self.scan_timer = 0

    @staticmethod
    def _exempt(source):
        node = source
        while node and node != camera.ui:
            if getattr(node, 'visual_blur_exempt', False):
                return True
            node = getattr(node, 'parent', None)
        return False

    def _scan(self):
        known = {id(source) for source, _, _ in self.copies}
        for source in list(scene.entities):
            if (not isinstance(source, Text)
                    or getattr(source, '_visual_blur_copy', False)
                    or id(source) in known
                    or not source.has_ancestor(camera.ui)):
                continue
            ghosts = []
            for _ in self.DIRECTIONS:
                ghost = Text(parent=source.parent, text='', origin=source.origin,
                             color=source.color, enabled=False)
                ghost._visual_blur_copy = True
                ghosts.append(ghost)
            self.copies.append((source, ghosts, source.color.a))

    def update(self):
        self.scan_timer -= time.dt
        if self.scan_timer <= 0:
            self.scan_timer = .15
            self._scan()

        radius = .0015 + STATE.blindness * STATE.blindness * .012
        live = []
        for source, ghosts, base_alpha in self.copies:
            if source not in scene.entities:
                for ghost in ghosts:
                    destroy(ghost)
                continue
            visible = source.enabled and not self._exempt(source)
            layer_alpha = base_alpha * .34
            source.color = Color(source.color.r, source.color.g, source.color.b,
                                 layer_alpha if visible else base_alpha)
            for ghost, (dx, dy) in zip(ghosts, self.DIRECTIONS):
                ghost.enabled = visible
                if not visible:
                    continue
                ghost.text = source.text
                ghost.position = (source.x + dx * radius, source.y + dy * radius, source.z)
                ghost.rotation = source.rotation
                ghost.scale = source.scale
                # Core and blur copies share exactly the same RGBA, preventing
                # a sharp bright label surrounded by a differently colored halo.
                ghost.color = source.color
            live.append((source, ghosts, base_alpha))
        self.copies = live

    def cleanup(self):
        for source, ghosts, base_alpha in self.copies:
            if source in scene.entities:
                source.color = Color(source.color.r, source.color.g, source.color.b, base_alpha)
            for ghost in ghosts:
                destroy(ghost)
        self.copies.clear()
        destroy(self)


class EffectsManager(Entity):
    """Attach once per scenario. Reads STATE.disability and drives overlays,
    distractions, hallucinations and the visual-blur level."""

    def __init__(self, player=None, announcer=None, **kwargs):
        super().__init__(**kwargs)
        self.player = player
        self.announcer = announcer
        self.ui = Entity(parent=camera.ui)
        self.focused = True            # ADHD: False while a distraction is active
        self.focus = 1.0               # ADHD: 0..1 attention meter
        self.distraction_ui = None
        self.distraction_timer = random.uniform(5, 9)
        self.whisper_timer = random.uniform(4, 8)
        self.shadow_figure = None
        self.pulse_timer = random.uniform(8, 14)

        d = STATE.disability
        if d == 'adhd':
            self.focus_label = Text(parent=self.ui, text='FOCUS', position=(-.86, .335),
                                    scale=.72, color=Color(.95, .6, .15, 1))
            self.focus_bg = Entity(parent=self.ui, model='quad', color=Color(.2, .2, .2, .8),
                                   position=(-.72, .33), scale=(.2, .02))
            self.focus_bar = Entity(parent=self.ui, model='quad', color=Color(.95, .6, .15, 1),
                                    position=(-.82, .33), origin=(-.5, 0), scale=(.2, .02))
        elif d == 'schizophrenia':
            self.shadow_figure = self._make_shadow()
        elif d == 'visual':
            self._apply_blindness()
            self.ui_blur = VisualUIBlur()
            Text(parent=self.ui, text='[ / ] blur intensity', position=(-.86, .335),
                 scale=.7, color=Color(.7, .7, .7, .8))

    # ------------------------------------------------------------------ visual
    def _apply_blindness(self):
        """Clear the legacy darkness/fog treatment.

        EffectStack reads STATE.blindness every frame and maps it to the
        post-process blur.  Keeping this method lets the existing slider
        callbacks request an immediate refresh without leaving old fog behind.
        """
        camera.overlay.color = Color(0, 0, 0, 0)
        scene.clearFog()

    # ------------------------------------------------------------ schizophrenia
    def _make_shadow(self):
        fig = Entity(model='cube', color=Color(.02, .02, .04, .9),
                     scale=(.6, 1.9, .4), position=self._shadow_spot())
        Entity(parent=fig, model='sphere', scale=(.5, .3, .5), y=.6,
               color=Color(.02, .02, .04, .9))
        return fig

    def _shadow_spot(self):
        if not self.player:
            return Vec3(0, 1, 10)
        ang = random.uniform(0, 360)
        offset = Vec3(random.uniform(8, 16), 0, random.uniform(8, 16))
        p = self.player.position + Vec3(offset.x * random.choice((-1, 1)), 0,
                                        offset.z * random.choice((-1, 1)))
        p.y = 1
        return p

    # ------------------------------------------------------------------- update
    def update(self):
        d = STATE.disability
        if d == 'adhd':
            self._update_adhd()
        elif d == 'schizophrenia':
            self._update_schizophrenia()

    def _update_adhd(self):
        self.distraction_timer -= time.dt
        if self.focused and self.distraction_timer <= 0:
            self.focused = False
            from .audio import get_audio
            get_audio().play('buzz', volume=.4)
            camera.shake(duration=.4, magnitude=1.5)
            self.distraction_ui = Text(parent=self.ui, origin=(0, 0), y=.15, scale=1.2,
                                       text=random.choice(ADHD_DISTRACTIONS),
                                       color=Color(1, .75, .3, 1))
            self._refocus_hint = Text(parent=self.ui, origin=(0, 0), y=.07, scale=.9,
                                      text='( press F to drag your attention back )',
                                      color=Color(.8, .8, .8, .9))
        if self.focused:
            self.focus = min(1, self.focus + time.dt * .25)
        else:
            self.focus = max(.05, self.focus - time.dt * .15)
        self.focus_bar.scale_x = .2 * self.focus
        if not self.focused:
            camera.overlay.color = Color(.3, .15, 0, .25)
        elif STATE.disability != 'visual':
            camera.overlay.color = Color(0, 0, 0, 0)

    def _update_schizophrenia(self):
        self.whisper_timer -= time.dt
        if self.whisper_timer <= 0:
            self.whisper_timer = random.uniform(3, 9)
            from .audio import get_audio
            get_audio().play('whisper', volume=.3)
            t = Text(parent=self.ui, text=random.choice(WHISPERS),
                     position=(random.uniform(-.55, .55), random.uniform(-.35, .35)),
                     origin=(0, 0), scale=random.uniform(.8, 1.4),
                     color=Color(.75, .55, .9, .0))
            t.animate_color(Color(.75, .55, .9, .85), duration=.8)
            destroy(t, delay=random.uniform(1.5, 3))

        self.pulse_timer -= time.dt
        if self.pulse_timer <= 0:
            self.pulse_timer = random.uniform(9, 16)
            camera.overlay.animate_color(Color(.2, 0, .25, .35), duration=.6)
            camera.overlay.animate_color(Color(0, 0, 0, 0), duration=1.2, delay=.8)

        # the shadow figure vanishes when looked at directly, then returns elsewhere
        if self.shadow_figure and self.player:
            to_fig = (self.shadow_figure.world_position - camera.world_position).normalized()
            if camera.forward.dot(to_fig) > .96:
                fig = self.shadow_figure
                self.shadow_figure = None
                fig.animate_color(Color(0, 0, 0, 0), duration=.25)
                destroy(fig, delay=.3)
                def respawn():
                    if self.enabled:
                        self.shadow_figure = self._make_shadow()
                from ursina import invoke
                invoke(respawn, delay=random.uniform(4, 9))

    def input(self, key):
        d = STATE.disability
        if d == 'adhd' and key == 'f' and not self.focused:
            self.focused = True
            self.distraction_timer = random.uniform(7, 14)
            for t in (self.distraction_ui, getattr(self, '_refocus_hint', None)):
                if t:
                    destroy(t)
            self.distraction_ui = None
        if d == 'visual' and key in (']', '['):
            STATE.blindness = round(min(1, max(0, STATE.blindness + (.05 if key == ']' else -.05))), 2)
            self._apply_blindness()
            if self.announcer:
                self.announcer.visual(f'blur: {int(STATE.blindness * 100)}%', duration=1.5)

    def on_destroy(self):
        if getattr(self, 'ui_blur', None):
            self.ui_blur.cleanup()
            self.ui_blur = None
        if self.shadow_figure:
            destroy(self.shadow_figure)
            self.shadow_figure = None
        camera.overlay.color = Color(0, 0, 0, 0)
        scene.clearFog()
        if self.ui:
            destroy(self.ui)
