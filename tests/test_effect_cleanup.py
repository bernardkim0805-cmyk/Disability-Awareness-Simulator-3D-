"""Device-free lifecycle checks for effects that modify shared runtime state."""

from types import SimpleNamespace

from simulator.fx.audio_fx import AuditoryProcessing, HearingLoss, Tinnitus
from simulator.fx.movement import CameraOffsetEffect, ParkinsonianTremor


class FakeAudio:
    def __init__(self):
        self.volume_scale = 1.0
        self.muffle = False
        self.delay_max = 0.0
        self.echo = 0.0
        self.tone = SimpleNamespace(volume=0.0, stopped=False)
        self.tone.stop = lambda: setattr(self.tone, "stopped", True)

    def _start(self, *_args, **_kwargs):
        return self.tone


def test_audio_effects_restore_shared_audio_state(monkeypatch):
    audio = FakeAudio()

    hearing = HearingLoss()
    hearing.initialized = True
    monkeypatch.setattr(hearing, "audio", lambda: audio)
    hearing.setIntensity(.6)
    hearing.enable()
    assert audio.volume_scale < 1 and audio.muffle
    hearing.cleanup()
    assert audio.volume_scale == 1 and not audio.muffle

    processing = AuditoryProcessing()
    processing.initialized = True
    monkeypatch.setattr(processing, "audio", lambda: audio)
    processing.setIntensity(.6)
    processing.enable()
    assert audio.delay_max > 0 and audio.echo > 0
    processing.cleanup()
    assert audio.delay_max == 0 and audio.echo == 0


def test_tinnitus_stops_owned_tone(monkeypatch):
    audio = FakeAudio()
    tinnitus = Tinnitus()
    tinnitus.initialized = True
    monkeypatch.setattr(tinnitus, "audio", lambda: audio)
    monkeypatch.setattr("simulator.audio.tinnitus_path", lambda *_args: "tone.wav")
    tinnitus.enable()
    tinnitus.cleanup()
    assert audio.tone.stopped
    assert tinnitus.tone is None


def test_camera_and_player_offsets_restore(monkeypatch):
    fake_camera = SimpleNamespace(rotation_x=0.0, rotation_y=0.0, rotation_z=0.0)
    monkeypatch.setattr("simulator.fx.movement.camera", fake_camera)

    offset = CameraOffsetEffect()
    offset._apply(2.0, -3.0, 4.0)
    offset.cleanup()
    assert (fake_camera.rotation_x, fake_camera.rotation_y, fake_camera.rotation_z) == (0, 0, 0)

    player = SimpleNamespace(speed=1.5)
    tremor = ParkinsonianTremor(context=SimpleNamespace(player=player))
    tremor.base_speed = 5.0
    player.speed = 0.0
    tremor.disable()
    assert player.speed == 5.0
