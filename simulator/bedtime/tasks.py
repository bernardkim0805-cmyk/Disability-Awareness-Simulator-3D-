"""The bedtime task pool + randomized routine builder.

Each task is (id, label, anchor_key, kind). `kind` tells the scenario how the
interaction resolves — an instant action, a reading panel, the shower
sub-sequence, or a stateful toggle with a consequence if skipped.
"""
if __package__ in (None, ''):
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import random

# id, label, anchor, kind
TASK_POOL = [
    ('toilet',    'Use the toilet (then flush!)',        'toilet_pos',   'toilet'),
    ('wash_hands','Wash your hands with soap',           'sink_pos',     'wash_hands'),
    ('brush',     'Brush your teeth with toothpaste',    'sink_pos',     'brush'),
    ('floss',     'Floss your teeth',                    'sink_pos',     'floss'),
    ('mouthwash', 'Rinse with mouthwash',                'sink_pos',     'product'),
    ('face',      'Wash your face with cleanser',        'sink_pos',     'product'),
    ('moist',     'Apply moisturizer',                   'sink_pos',     'product'),
    ('hair',      'Brush your hair',                     'sink_pos',     'action'),
    ('shower',    'Take a shower',                        'shower_pos',   'shower'),
    ('meds',      'Take your night medication',          'meds_pos',     'reading'),
    ('pajamas',   'Change into pajamas',                 'pajamas_pos',  'pajamas'),
    ('laundry',   'Put dirty clothes in the hamper',     'hamper_pos',   'laundry'),
    ('water',     'Fill a glass of water',               'sink_pos',     'water'),
    ('read',      'Read your book for a while',          'book_pos',     'reading'),
    ('charge',    'Put your phone on the charger',       'charger_pos',  'action'),
    ('alarm',     'Set the morning alarm',               'alarm_pos',    'action'),
    ('lock',      'Lock the bedroom door',               'door_pos',     'toggle'),
    ('curtains',  'Close the curtains',                  'bed',          'curtains'),
    ('bath_light','Turn off the bathroom light',         'sink_pos',     'bath_light'),
    ('bed_light', 'Turn off the bedroom light',          'bed',          'bed_light'),
]

# tasks that ALWAYS anchor the routine (start and finish)
FINISH = ('sleep', 'Get into bed and go to sleep', 'bed', 'sleep')


def build_routine(rng=None, length=None):
    """Pick a randomized subset+order. Core hygiene tasks are always present;
    the rest are sampled, so no two nights are identical."""
    rng = rng or random
    core = ['toilet', 'brush', 'shower', 'pajamas']
    optional = [t[0] for t in TASK_POOL if t[0] not in core]
    n_extra = (length or rng.randint(5, 7))
    chosen = set(core) | set(rng.sample(optional, min(n_extra, len(optional))))
    tasks = [t for t in TASK_POOL if t[0] in chosen]
    rng.shuffle(tasks)
    # turning off the bedroom light should come near the end (before sleep)
    tasks.sort(key=lambda t: 1 if t[0] in ('bed_light', 'curtains') else 0)
    tasks.append(FINISH)
    return tasks
