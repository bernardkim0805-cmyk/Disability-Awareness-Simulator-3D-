"""Effect architecture.

DisabilityEffect defines the lifecycle every simulation effect follows:

    initialize()          one-time setup (resources, baselines)
    enable() / disable()  turn the effect on or off at runtime
    setIntensity(f)       0..1 severity; effects rescale live
    update(dt)            called every frame while enabled
    cleanup()             release everything; must be safe to call twice

Category bases (VisualEffect, AudioEffect, MovementEffect, CognitiveEffect)
add the plumbing their family needs. Rendering stays in postfx.py; gameplay
state stays in the effect classes (separation of concerns).

EffectStack owns a set of effects and guarantees they stack without
conflict: visual effects don't write to the GPU directly — they *contribute*
to a shared parameter dict that PostFX merges once per frame (max/sum rules),
so any combination of effects is safe.
"""
from ursina import Entity, camera, time as utime

from ..config import STATE


class DisabilityEffect:
    """Base lifecycle for every simulated condition."""

    effect_id = 'base'

    def __init__(self, context=None):
        self.context = context          # the running scenario (may be None in menus)
        self.enabled = False
        self.intensity = 0.6
        self.initialized = False

    # -- lifecycle ---------------------------------------------------------
    def initialize(self):
        self.initialized = True

    def enable(self):
        if not self.initialized:
            self.initialize()
        self.enabled = True

    def disable(self):
        self.enabled = False

    def setIntensity(self, value):
        self.intensity = max(0.0, min(1.0, float(value)))

    def update(self, dt):
        pass

    def cleanup(self):
        self.disable()
        self.initialized = False

    # snake_case alias so codebase style stays consistent
    set_intensity = setIntensity


class VisualEffect(DisabilityEffect):
    """Visual effects contribute post-process parameters each frame.

    Override contribute(params) and write into the shared dict using
    PostFX's merge conventions (documented in postfx.py). Never touch the
    shader directly — that is what makes stacking safe.
    """

    def contribute(self, params):
        pass


class AudioEffect(DisabilityEffect):
    """Audio effects install hooks on the AudioManager (see audio.py):
    hooks are pure functions the manager consults, so several audio
    effects can chain without fighting over global state."""

    def audio(self):
        from ..audio import get_audio
        return get_audio()


class MovementEffect(DisabilityEffect):
    """Movement effects perturb the camera/player every frame. They must
    apply *offsets* (additive, remembered and removed next frame) rather
    than absolute values so multiple movement effects can stack."""

    def player(self):
        return getattr(self.context, 'player', None)


class CognitiveEffect(DisabilityEffect):
    """Cognitive effects change gameplay information (HUD, names, memory).
    They read the scenario through self.context and must restore whatever
    they hide in disable()/cleanup()."""
    pass


class EffectStack(Entity):
    """Owns the active effects for a scenario and drives them every frame.

    - builds effect instances from STATE.lab_effects {effect_id: intensity}
    - merges visual contributions into PostFX once per frame
    - handles 'normal vision' compare (hold N) and split-screen mode
    """

    def __init__(self, context=None, **kwargs):
        super().__init__(**kwargs)
        from .registry import EFFECTS
        self.context = context
        self.effects = []
        self.compare_held = False
        for effect_id, intensity in STATE.lab_effects.items():
            spec = EFFECTS.get(effect_id)
            if not spec:
                continue
            eff = spec['cls'](context=context)
            eff.effect_id = effect_id
            eff.setIntensity(intensity)
            eff.enable()
            self.effects.append(eff)
        STATE.active_fx = {e.effect_id for e in self.effects}

    def update(self):
        dt = utime.dt
        from .postfx import get_postfx
        fx = get_postfx()
        params = fx.default_params()
        any_visual = False
        for eff in self.effects:
            if not eff.enabled:
                continue
            eff.update(dt)
            if isinstance(eff, VisualEffect):
                eff.contribute(params)
                any_visual = True
        params['bypass'] = 1.0 if (self.compare_held or not any_visual) else 0.0
        params['split'] = 1.0 if STATE.lab_split else 0.0
        fx.apply(params)

    def input(self, key):
        if key == 'n':                       # hold N: normal-vision comparison
            self.compare_held = True
        elif key == 'n up':
            self.compare_held = False
        elif key == 'f':                     # re-focus (ADHD)
            for eff in self.effects:
                if hasattr(eff, 'refocus'):
                    eff.refocus()
        elif key == 'j':                     # journal (memory impairment)
            for eff in self.effects:
                if hasattr(eff, 'journal'):
                    eff.journal()

    def cleanup(self):
        from .postfx import get_postfx
        for eff in self.effects:
            eff.cleanup()
        self.effects.clear()
        STATE.active_fx = set()
        get_postfx().reset()
        from ursina import destroy
        destroy(self)
