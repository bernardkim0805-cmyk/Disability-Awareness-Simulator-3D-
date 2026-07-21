"""Bedtime-only sound cues, synthesized on first run as `bed_*` wavs. Reuses
the shared audio helpers and plays through the AudioManager, so deaf mode /
hearing-loss / tinnitus all apply automatically."""
if __package__ in (None, ''):
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

from ..audio import AUDIO_DIR, SR, _write_wav, _tone, _noise, _mix, _seq

BED_CUES = {
    'bed_faucet': lambda: _noise(3.0, .26, lowpass=.68, decay=.05),
    'bed_flush': lambda: _seq(_noise(.5, .4, lowpass=.5, decay=1.5),
                              _noise(2.2, .3, lowpass=.75, decay=.3)),
    'bed_shower': lambda: _mix(_noise(3.0, .32, lowpass=.62, decay=.04),
                               _noise(3.0, .08, lowpass=.9, decay=.04)),
    'bed_brush': lambda: _seq(*[_noise(.14, .22, lowpass=.55, decay=4)
                                + [0.0] * int(.05 * SR) for _ in range(6)]),
    'bed_alarm': lambda: _seq(*[_tone(2600, .22, .55, decay=2)
                                + [0.0] * int(.14 * SR) for _ in range(5)]),
    'bed_page': lambda: _noise(.35, .3, lowpass=.4, decay=8),
    'bed_click': lambda: _tone(900, .07, .4, decay=12),
    'bed_pour': lambda: _mix(_noise(1.4, .2, lowpass=.6, decay=.4),
                             _tone(520, 1.4, .05, decay=.6, vibrato=.4)),
    'bed_drop': lambda: _seq(_mix(_noise(.1, .5, lowpass=.4, decay=10),
                                  _tone(180, .1, .4, decay=14)),
                             _mix(_noise(.07, .3, lowpass=.4, decay=16),
                                  _tone(150, .07, .3, decay=18))),
    'bed_chime': lambda: _seq(_tone(660, .2, .35, decay=4), _tone(990, .4, .3, decay=3)),
}


def ensure_bed_assets():
    for name, gen in BED_CUES.items():
        path = AUDIO_DIR / f'{name}.wav'
        if not path.exists():
            _write_wav(path, gen())
