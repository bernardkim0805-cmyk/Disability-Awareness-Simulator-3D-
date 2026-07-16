"""Audio: procedurally generated sound effects + macOS text-to-speech.

Accessibility design:
- Deaf mode: ALL sound is suppressed — hearing players lose exactly what a
  deaf person never receives.
- Visual-impairment mode: a screen-reader style voice (macOS `say`) narrates
  announcements, dialogue and objectives, the way a blind player would
  actually experience the game.
Every effect is synthesized to WAV on first run — no external assets.
"""
import hashlib
import math
import random
import struct
import subprocess
import sys
import threading
import wave
from pathlib import Path

from .config import STATE

AUDIO_DIR = Path(__file__).resolve().parent.parent / 'assets' / 'audio'
TTS_DIR = AUDIO_DIR / 'tts'
SR = 22050


# ------------------------------------------------------------- synthesis
def _write_wav(path, samples):
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = b''.join(struct.pack('<h', max(-32767, min(32767, int(s * 32767))))
                      for s in samples)
    with wave.open(str(path), 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(frames)


def _tone(freq, dur, vol=.5, decay=4.0, vibrato=0.0):
    out = []
    for i in range(int(dur * SR)):
        t = i / SR
        f = freq * (1 + vibrato * math.sin(t * 6))
        out.append(vol * math.exp(-decay * t) * math.sin(6.2832 * f * t))
    return out


def _mix(*tracks):
    n = max(len(t) for t in tracks)
    return [sum(t[i] if i < len(t) else 0 for t in tracks) for i in range(n)]


def _seq(*tracks):
    out = []
    for t in tracks:
        out.extend(t)
    return out


def _noise(dur, vol=.3, lowpass=.9, decay=2.0):
    out, prev = [], 0.0
    for i in range(int(dur * SR)):
        t = i / SR
        prev = prev * lowpass + random.uniform(-1, 1) * (1 - lowpass)
        out.append(vol * math.exp(-decay * t) * prev * 8)
    return out


CUES = {
    'chime': lambda: _seq(_tone(880, .35, .35), _tone(660, .5, .35)),
    'bell': lambda: _mix(_tone(660, 1.6, .4, decay=2),
                         _tone(1320, 1.6, .15, decay=3),
                         _tone(1980, 1.2, .07, decay=4)),
    'groan': lambda: _mix(_tone(85, 1.4, .5, decay=1.2, vibrato=.12),
                          _tone(63, 1.4, .35, decay=1.0, vibrato=.2),
                          _noise(1.4, .12, lowpass=.97, decay=1.5)),
    'rumble': lambda: _mix(_noise(3.0, .5, lowpass=.985, decay=.4),
                           _tone(48, 3.0, .25, decay=.3, vibrato=.05)),
    'buzz': lambda: _seq(*[_mix(_tone(180, .12, .5, decay=1),
                                _noise(.12, .15, lowpass=.6, decay=1))
                           + [0.0] * int(.08 * SR) for _ in range(3)]),
    'whisper': lambda: _noise(1.2, .22, lowpass=.55, decay=2.2),
    'success': lambda: _seq(_tone(523, .18, .4), _tone(659, .18, .4),
                            _tone(784, .5, .45, decay=2.5)),
    'fail': lambda: _seq(_tone(392, .3, .4), _tone(330, .3, .4),
                         _tone(262, .7, .45, decay=2)),
}


def ensure_assets():
    for name, gen in CUES.items():
        path = AUDIO_DIR / f'{name}.wav'
        if not path.exists():
            _write_wav(path, gen())
    TTS_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------- manager
class AudioManager:
    """Plays cues and speech according to the selected disability."""

    def __init__(self):
        ensure_assets()
        self.playing = []

    def hearing(self):
        return STATE.disability != 'deaf'

    @staticmethod
    def _asset_name(path):
        """Ursina resolves audio relative to its asset folder."""
        from ursina import application
        try:
            return str(Path(path).relative_to(Path(application.asset_folder).resolve()))
        except ValueError:
            return str(path)

    def play(self, cue, volume=.5, loop=False):
        if not self.hearing():
            return None
        try:
            from ursina import Audio
            a = Audio(self._asset_name(AUDIO_DIR / f'{cue}.wav'), volume=volume,
                      loop=loop, autoplay=True)
            self.playing.append(a)
            return a
        except Exception:
            return None

    # ------------------------------------------------------ screen reader
    def speak(self, text, volume=.9):
        """Narrate text out loud — the blind player's screen reader."""
        if STATE.disability != 'visual' or not text or sys.platform != 'darwin':
            return
        clean = text.replace('"', '').replace('\n', '. ')
        h = hashlib.md5(clean.encode()).hexdigest()[:16]
        path = TTS_DIR / f'{h}.wav'
        if path.exists():
            self._play_file(path, volume)
            return
        job = threading.Thread(
            target=subprocess.run,
            args=(['say', '-o', str(path), '--data-format=LEI16@22050', clean],),
            kwargs=dict(capture_output=True), daemon=True)
        job.start()
        self._poll_tts(job, path, volume, tries=0)

    def _poll_tts(self, job, path, volume, tries):
        from ursina import invoke, Func
        if not job.is_alive() and path.exists():
            self._play_file(path, volume)
        elif tries < 40:
            invoke(Func(self._poll_tts, job, path, volume, tries + 1), delay=.25)

    def _play_file(self, path, volume):
        if not self.hearing():
            return
        try:
            from ursina import Audio
            self.playing.append(Audio(self._asset_name(path), volume=volume,
                                      autoplay=True))
        except Exception:
            pass

    def stop_all(self):
        for a in self.playing:
            try:
                a.stop()
            except Exception:
                pass
        self.playing.clear()


_manager = None


def get_audio():
    global _manager
    if _manager is None:
        _manager = AudioManager()
    return _manager
