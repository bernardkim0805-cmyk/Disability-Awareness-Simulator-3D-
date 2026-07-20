"""Hearing condition simulations. These install/remove hooks on the shared
AudioManager (see audio.py) so several audio effects can stack: attenuation
multiplies, muffling and delays are independent flags."""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

from .core import AudioEffect


class HearingLoss(AudioEffect):
    """Sensorineural-style loss: overall attenuation plus a low-pass
    'muffled' rendering of every cue (high frequencies go first). We have no
    positional audio engine, so reduced directionality is represented by the
    same information simply arriving weaker and less distinct."""

    def initialize(self):
        super().initialize()
        from ..audio import ensure_muffled_assets
        ensure_muffled_assets()

    def enable(self):
        super().enable()
        self._apply()

    def setIntensity(self, value):
        super().setIntensity(value)
        if self.enabled:
            self._apply()

    def _apply(self):
        a = self.audio()
        a.volume_scale = 1 - self.intensity * .85
        a.muffle = True

    def disable(self):
        a = self.audio()
        a.volume_scale = 1.0
        a.muffle = False
        super().disable()

    cleanup = disable


class Tinnitus(AudioEffect):
    """A constant ring that never stops. Pitch and laterality are
    configurable; intensity maps to loudness. Synthesized as a looping
    stereo sine with a slow shimmer (most patients report a steady
    high-frequency tone near 4-8 kHz)."""

    pitch_hz = 6000
    side = 'both'          # 'left' | 'right' | 'both'

    def __init__(self, context=None, pitch_hz=None, side=None):
        super().__init__(context)
        if pitch_hz:
            self.pitch_hz = pitch_hz
        if side:
            self.side = side
        self.tone = None

    def enable(self):
        super().enable()
        from ..audio import tinnitus_path
        path = tinnitus_path(self.pitch_hz, self.side)
        a = self.audio()
        self.tone = a._start(path, volume=self.intensity * .35, loop=True)

    def setIntensity(self, value):
        super().setIntensity(value)
        if self.tone:
            try:
                self.tone.volume = self.intensity * .35
            except Exception:
                pass

    def disable(self):
        if self.tone:
            try:
                self.tone.stop()
            except Exception:
                pass
            self.tone = None
        super().disable()

    cleanup = disable


class AuditoryProcessing(AudioEffect):
    """Auditory processing disorder: hearing is intact but decoding lags —
    cues arrive noticeably late and speech smears (a soft echo overlaps its
    own onset), making localization and comprehension harder."""

    def enable(self):
        super().enable()
        self._apply()

    def setIntensity(self, value):
        super().setIntensity(value)
        if self.enabled:
            self._apply()

    def _apply(self):
        a = self.audio()
        a.delay_max = .2 + self.intensity * .9
        a.echo = self.intensity

    def disable(self):
        a = self.audio()
        a.delay_max = 0.0
        a.echo = 0.0
        super().disable()

    cleanup = disable
