"""Cognitive/perceptual condition simulations. These operate on gameplay
information — names, HUD, memory — rather than pixels, and restore
everything they touch when disabled."""
import random

from ursina import Entity, Text, Color, camera, destroy, time as utime

from ..config import STATE
from .core import CognitiveEffect

# nearest-name lookup for clothing descriptors (prosopagnosia workaround:
# people identify others by clothing, hair, voice and context, not faces)
_SHIRT_NAMES = [((.7, .25, .25), 'red'), ((.25, .4, .7), 'blue'),
                ((.25, .55, .35), 'green'), ((.65, .55, .2), 'mustard'),
                ((.5, .3, .6), 'purple'), ((.75, .45, .25), 'orange'),
                ((.35, .35, .4), 'gray'), ((.8, .8, .82), 'white')]


def shirt_descriptor(human):
    c = getattr(human, 'shirt_color', None)
    if c is None:
        return 'someone'
    best = min(_SHIRT_NAMES,
               key=lambda n: (n[0][0] - c.x) ** 2 + (n[0][1] - c.y) ** 2
                             + (n[0][2] - c.z) ** 2)
    return f'person in the {best[1]} shirt'


class Prosopagnosia(CognitiveEffect):
    """Face blindness: features stop carrying identity. We blank every
    face's identity cues (eyes/brows/mouth/nose) into a smooth oval and
    replace dialogue names with clothing descriptors — exactly the
    compensation strategy people with prosopagnosia actually use."""

    def initialize(self):
        super().initialize()
        self.hidden = []
        self.rescan_timer = 0

    def enable(self):
        super().enable()
        self._mask_all()

    def _mask_all(self):
        from ..human import Human
        from ursina import scene
        for e in scene.entities:
            if isinstance(e, Human):
                for part in getattr(e, 'face_parts', []):
                    if part.enabled:
                        part.enabled = False
                        self.hidden.append(part)

    def update(self, dt):
        # catch humans spawned after enable (e.g. second zombie wave)
        self.rescan_timer -= dt
        if self.rescan_timer <= 0:
            self.rescan_timer = 2
            self._mask_all()

    def disable(self):
        for part in self.hidden:
            try:
                part.enabled = True
            except Exception:
                pass
        self.hidden.clear()
        super().disable()

    cleanup = disable


class HemispatialNeglect(CognitiveEffect):
    """Left-side neglect (typical after right-hemisphere stroke): the left
    half of the world isn't dark — it simply stops being *attended to*. HUD
    elements on the left vanish, the objective drifts right, and markers
    over people on your left side silently disappear."""

    def enable(self):
        super().enable()
        self._hidden_hud = []
        ctx = self.context
        if ctx:
            for t in camera.ui.children:
                if isinstance(t, Text) and t.x < -.4:      # left-anchored HUD
                    if t.enabled:
                        t.enabled = False
                        self._hidden_hud.append(t)
            if getattr(ctx, 'objective_text', None):
                ctx.objective_text.x += .22 * self.intensity

    def update(self, dt):
        ctx = self.context
        if not ctx or not getattr(ctx, 'player', None):
            return
        player = ctx.player
        for npc in getattr(ctx, 'npcs', []):
            marker = getattr(npc, 'marker', None)
            if not marker:
                continue
            to_npc = npc.world_position - player.world_position
            on_left = player.right.dot(to_npc) < 0
            marker.visible = not (on_left and self.intensity > .25)

    def disable(self):
        for t in self._hidden_hud:
            try:
                t.enabled = True
            except Exception:
                pass
        self._hidden_hud = []
        ctx = self.context
        if ctx and getattr(ctx, 'objective_text', None):
            ctx.objective_text.x = 0
        if ctx:
            for npc in getattr(ctx, 'npcs', []):
                if getattr(npc, 'marker', None):
                    npc.marker.visible = True
        super().disable()

    cleanup = disable


class ADHDDistraction(CognitiveEffect):
    """Attention capture: intrusive notifications hijack the screen and the
    current objective literally fades from awareness until you press F to
    re-orient. Interruptions cost time that others never lose."""

    THOUGHTS = ['bzzt. your phone. who is it? check it. CHECK IT.',
                'that ceiling light hums. you can hear it now. only it.',
                'wait — did you reply to that message?',
                'a song fragment starts looping. all of it. again.']

    def initialize(self):
        super().initialize()
        self.timer = random.uniform(5, 9)
        self.popup = None
        self.distracted = False

    def update(self, dt):
        ctx = self.context
        self.timer -= dt
        if not self.distracted and self.timer <= 0:
            self.distracted = True
            camera.shake(duration=.35, magnitude=1.2)
            self.popup = Text(parent=camera.ui, origin=(0, 0), y=.18,
                              text=random.choice(self.THOUGHTS), scale=1.15,
                              color=Color(1, .75, .3, 1))
            self.hint = Text(parent=camera.ui, origin=(0, 0), y=.1, scale=.85,
                             text='( F — drag your attention back )',
                             color=Color(.85, .85, .85, .9))
        if self.distracted and ctx and getattr(ctx, 'objective_text', None):
            ctx.objective_text.color = Color(1, 1, .6, max(0.05, 1 - self.intensity))

    def refocus(self):
        if self.distracted:
            self.distracted = False
            self.timer = random.uniform(6, 12) * (1.3 - self.intensity * .8)
            for t in (self.popup, getattr(self, 'hint', None)):
                if t:
                    destroy(t)
            ctx = self.context
            if ctx and getattr(ctx, 'objective_text', None):
                ctx.objective_text.color = Color(1, 1, .6, 1)

    def disable(self):
        self.refocus()
        super().disable()

    cleanup = disable


class MemoryImpairment(CognitiveEffect):
    """Working/short-term memory load: the objective fades from the HUD a
    few seconds after you read it and names refuse to stick ('???'). Press
    J to check your journal — external memory becomes the strategy, exactly
    as it does for people using notes, alarms and journals daily."""

    def initialize(self):
        super().initialize()
        self.age = 0.0

    def update(self, dt):
        ctx = self.context
        if not ctx or not getattr(ctx, 'objective_text', None):
            return
        self.age += dt
        hold = 12 - self.intensity * 8            # seconds before fade begins
        fade = max(0.0, min(1.0, (self.age - hold) / 4))
        ctx.objective_text.color = Color(1, 1, .6, 1 - fade * .95)

    def journal(self):
        """J key: consult your notes — the objective comes back."""
        self.age = 0.0
        ctx = self.context
        if ctx and getattr(ctx, 'announcer', None):
            ctx.announcer.visual('you check your journal...', 2,
                                 Color(.7, .85, 1, 1))

    def disable(self):
        ctx = self.context
        if ctx and getattr(ctx, 'objective_text', None):
            ctx.objective_text.color = Color(1, 1, .6, 1)
        super().disable()

    cleanup = disable
