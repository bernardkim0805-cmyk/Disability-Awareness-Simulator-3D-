"""Kitchen-only sound cues, synthesized on first run.

Deliberately does NOT modify simulator/audio.py (shared file): we reuse its
public helpers to write `kitchen_*.wav` files into the shared asset folder,
then play them through the AudioManager so deaf mode / hearing-loss hooks
still apply automatically.
"""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import math
import random

from ..audio import AUDIO_DIR, SR, _write_wav, _tone, _noise, _mix, _seq


def _radio_melody():
    """A tinny 8-note loop, band-passed feel via mid-frequency tones."""
    notes = [392, 440, 523, 440, 392, 330, 392, 440]
    return _seq(*[_tone(n, .28, .18, decay=3) for n in notes])


def _chatter():
    """Unintelligible family conversation: overlapping vowel-ish formants
    with speechlike rhythm — enough to register as 'people talking'. """
    out = []
    for _ in range(10):                                     # ten 'syllables'
        f = random.choice([160, 190, 220, 250])
        syl = _mix(_tone(f, .16, .22, decay=6),
                   _tone(f * 2.4, .16, .1, decay=7))
        out.extend(syl)
        out.extend([0.0] * int(random.uniform(.03, .12) * SR))
    return out


KITCHEN_CUES = {
    # ambience (looped)
    'kitchen_hum': lambda: _mix(_tone(120, 3.0, .16, decay=.05, vibrato=.02),
                                _noise(3.0, .05, lowpass=.98, decay=.05)),
    'kitchen_water': lambda: _noise(3.0, .3, lowpass=.7, decay=.05),
    'kitchen_radio': _radio_melody,
    'kitchen_chatter': _chatter,
    'kitchen_sizzle': lambda: _noise(2.5, .35, lowpass=.45, decay=.3),
    # events
    'kitchen_timer': lambda: _seq(*[_tone(1400, .18, .5, decay=6)
                                    + [0.0] * int(.12 * SR) for _ in range(4)]),
    'kitchen_alarm': lambda: _seq(*[_tone(2800, .3, .6, decay=2)
                                    + [0.0] * int(.15 * SR) for _ in range(5)]),
    'kitchen_notify': lambda: _seq(_tone(1568, .12, .9), _tone(2093, .3, .9, decay=5)),
    'kitchen_chop': lambda: _mix(_noise(.09, .5, lowpass=.35, decay=18),
                                 _tone(180, .09, .3, decay=25)),
    'kitchen_hurt': lambda: _seq(_tone(220, .15, .6, decay=8),
                                 _tone(160, .3, .5, decay=6)),
}


def ensure_kitchen_assets():
    for name, gen in KITCHEN_CUES.items():
        path = AUDIO_DIR / f'{name}.wav'
        if not path.exists():
            _write_wav(path, gen())
