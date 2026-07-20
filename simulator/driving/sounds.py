"""Driving-only audio, synthesized on first run as `drive_*` cues.

Never modifies the shared audio module: it uses its public helpers and
plays through the AudioManager, so hearing-loss muffling, deaf-mode
silence, APD delays and tinnitus all apply automatically.

'Directional audio': the engine has no stereo panner, so direction is
conveyed the accessible way — approach = volume ramp (handled by the
traffic code, distance -> volume) paired with the HUD's directional
indicator, which doubles as the deaf-accessible alternative.
"""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import hashlib
import subprocess
import sys
import threading

from ..audio import AUDIO_DIR, TTS_DIR, SR, _write_wav, _tone, _noise, _mix, _seq

DRIVE_CUES = {
    'drive_engine': lambda: _mix(_tone(75, 3.0, .3, decay=.05, vibrato=.06),
                                 _tone(150, 3.0, .12, decay=.05, vibrato=.04),
                                 _noise(3.0, .05, lowpass=.9, decay=.05)),
    'drive_traffic': lambda: _mix(_noise(4.0, .18, lowpass=.93, decay=.04),
                                  _tone(95, 4.0, .06, decay=.04, vibrato=.3)),
    'drive_rain': lambda: _noise(3.0, .3, lowpass=.5, decay=.05),
    'drive_wiper': lambda: _seq(_noise(.25, .3, lowpass=.6, decay=6),
                                [0.0] * int(.5 * SR),
                                _noise(.25, .3, lowpass=.6, decay=6)),
    'drive_horn': lambda: _mix(_tone(420, .5, .5, decay=2), _tone(330, .5, .4, decay=2)),
    'drive_siren': lambda: _seq(*[_tone(f, .35, .5, decay=.5)
                                  for f in (960, 640, 960, 640, 960, 640)]),
    'drive_signal': lambda: _seq(_tone(1200, .06, .35, decay=20),
                                 [0.0] * int(.42 * SR)),
    'drive_crash': lambda: _mix(_noise(.6, .8, lowpass=.3, decay=6),
                                _tone(60, .6, .6, decay=5)),
    'drive_screech': lambda: _mix(_tone(1900, .7, .3, decay=3, vibrato=.25),
                                  _noise(.7, .25, lowpass=.4, decay=3)),
    'drive_ping': lambda: _seq(_tone(1568, .1, .8), _tone(2093, .25, .8, decay=6)),
}


def ensure_drive_assets():
    for name, gen in DRIVE_CUES.items():
        path = AUDIO_DIR / f'{name}.wav'
        if not path.exists():
            _write_wav(path, gen())


def say_nav(text, volume=.9):
    """Voice navigation (macOS `say`). Unlike the screen-reader in the shared
    AudioManager (visual-impairment only), this speaks whenever the player
    has voice guidance ON — it is an assistive *feature*, not a simulation.
    Deaf mode still silences it via the manager's volume hook."""
    from ..audio import get_audio
    manager = get_audio()
    if not manager.hearing() or sys.platform != 'darwin' or not text:
        return
    clean = text.replace('"', '')
    path = TTS_DIR / (hashlib.md5(clean.encode()).hexdigest()[:16] + '.wav')
    if path.exists():
        manager._play_file(path, volume)
        return
    job = threading.Thread(
        target=subprocess.run,
        args=(['say', '-o', str(path), '--data-format=LEI16@22050', clean],),
        kwargs=dict(capture_output=True), daemon=True)
    job.start()
    manager._poll_tts(job, path, volume, tries=0)
