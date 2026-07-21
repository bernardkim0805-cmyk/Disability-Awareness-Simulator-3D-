"""Shared game state and static data (disabilities, scenarios, reflection text)."""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

from ursina import Color


class GameState:
    def __init__(self):
        self.disability = None      # key into DISABILITIES, or None = 'none'
        self.scenario = 'school'    # key into SCENARIOS
        self.blindness = 0.55       # 0..1, only used by 'visual'
        self.lab_effects = {}       # {effect_id: intensity} from the lab panel
        self.lab_split = False      # split-screen comparison mode
        self.active_fx = set()      # effect ids currently running in-scene

    @property
    def is_(self):
        return self.disability


STATE = GameState()


DISABILITIES = {
    'none': dict(
        name='No disability (baseline)',
        icon='[ o ]',
        color=Color(.45, .55, .65, 1),
        desc='Play the scenario with no simulated barriers,\nso you can compare both experiences.',
    ),
    'adhd': dict(
        name='ADHD',
        icon='[ ! ]',
        color=Color(.95, .6, .15, 1),
        desc='Your attention is pulled away constantly.\nDistractions hijack the screen — press F to refocus\nbefore you lose track of what you were doing.',
    ),
    'schizophrenia': dict(
        name='Schizophrenia',
        icon='[ ~ ]',
        color=Color(.55, .3, .7, 1),
        desc='Whispers, intrusive doubts and shadow figures\nappear that no one else can see.\nLooking straight at a figure makes it vanish.',
    ),
    'wheelchair': dict(
        name='Wheelchair user',
        icon='[ & ]',
        color=Color(.2, .55, .9, 1),
        desc='You move from a lower height and cannot use\nstairs or jump. Ramps and elevators are your only\nroutes — when they exist, and when they work.',
    ),
    'visual': dict(
        name='Visual impairment',
        icon='[ - ]',
        color=Color(.25, .25, .3, 1),
        desc='The world becomes progressively out of focus.\nUse the slider (or [ and ] keys in-game) to set\nthe blur intensity from clear to heavily blurred.',
    ),
    'deaf': dict(
        name='Deaf / hard of hearing',
        icon='[ x ]',
        color=Color(.2, .7, .5, 1),
        desc='You hear nothing. Announcements, warnings and\nsounds behind you simply never reach you —\nyou must rely on what you can see.',
    ),
    'dyslexia': dict(
        name='Dyslexia',
        icon='[ ? ]',
        color=Color(.85, .35, .4, 1),
        desc='Written words shift and scramble as you read.\nEvery sign, question and dialogue line keeps\nrearranging itself under your eyes.',
    ),
}

SCENARIOS = {
    'school': dict(
        name='School Test',
        icon='<TEST>',
        desc='Sit a timed 5-question exam while classmates\nbreeze through it around you.',
    ),
    'train': dict(
        name='Catch the Train',
        icon='<TRAIN>',
        desc='Reach platform 1 and board before the train\nleaves. Commuters make it look effortless.',
    ),
    'zombies': dict(
        name='Zombie Escape',
        icon='<NIGHT>',
        desc='Night has fallen and the streets are not safe.\nReach the safehouse before they reach you.',
    ),
    'driving': dict(
        name='City Drive',
        icon='<DRIVE>',
        desc="Doctor's appointment across town. Traffic,\nsignals, pedestrians, weather — and a clock.",
    ),
    'living_city': dict(
        name='Living City',
        icon='<CITY>',
        desc='An autonomous crowd — every NPC has its own\npersonality, mood, memory and reactions.\nTrigger events and watch them decide.',
    ),
    'bedtime': dict(
        name='Getting Ready for Bed',
        icon='<NIGHT>',
        desc='A full nightly routine in a lived-in home.\nRandomized tasks; every disability reshapes\nwashing, reading, showering and remembering.',
    ),
    'kitchen': dict(
        name='Home Kitchen',
        icon='<COOK>',
        desc='Cook a random recipe in a random kitchen.\nKnives, hot pans and timers are less forgiving\nthan they look.',
    ),
}

# People who mock you, keyed by scenario then disability. `lines` spawns a
# talkable NPC with a smug face; `taunt` fires once mid-scenario. The sting is
# the point — this is what people actually deal with.
MOCKERY = {
    'school': {
        'dyslexia': dict(name='Dex', taunt_time=30,
                         lines=["Done already. What's taking YOU so long?",
                                "It's just reading. My little brother can do it."],
                         taunt='Dex snickers: "is the paper upside down or something?"'),
        'adhd': dict(name='Dex', taunt_time=30,
                     lines=['Can you stop fidgeting? Some of us are working.',
                            "Just focus. It's not that hard."],
                     taunt='Dex mutters: "distracted AGAIN? unbelievable."'),
        'schizophrenia': dict(name='Dex', taunt_time=35,
                              lines=['Why do you keep staring at the corner?',
                                     "There's NOTHING there. You're so weird."],
                              taunt='you catch Dex whispering to Maya and nodding at you'),
        'visual': dict(name='Dex', taunt_time=30,
                       lines=["Squinting won't help you pass.",
                              'Maybe sit closer to the board next time?'],
                       taunt='Dex laughs: "it\'s RIGHT THERE on the board."'),
        'wheelchair': dict(name='Dex', taunt_time=30,
                           lines=['You get the front desk AND extra time? Must be nice.'],
                           taunt='Dex mutters: "special treatment, as usual."'),
        'deaf': dict(name=None, taunt_time=25,
                     taunt='Two classmates burst out laughing at a joke you never heard.'),
    },
    'train': {
        'wheelchair': dict(name='Vic', taunt_time=45,
                           lines=["You're blocking the whole walkway.",
                                  'The stairs are RIGHT there. ...oh. Right.'],
                           taunt='someone sighs loudly behind you: "they always slow everything down."'),
        'visual': dict(name='Vic', taunt_time=40,
                       lines=['The departure board is right above you.',
                              'How does someone miss a whole train?'],
                       taunt='a stranger mutters: "just LOOK where you\'re going."'),
        'deaf': dict(name=None, taunt_time=40,
                     taunt="A commuter snaps at you — they'd been calling out to you for a while."),
    },
    'zombies': {
        'wheelchair': dict(name=None, taunt_time=12,
                           taunt='Jo screams back: "are you KIDDING me?! MOVE!"'),
        'visual': dict(name=None, taunt_time=15,
                       taunt='Sam: "it\'s right in front of you! How can you not SEE it?!"'),
        'deaf': dict(name=None, taunt_time=18,
                     taunt='Sam was screaming a warning at your back. You never knew.'),
    },
}

# Shown on the end-of-scenario reflection screen.
REFLECTIONS = {
    'none': 'You played the baseline. Try the same scenario with a disability\nselected and notice what suddenly becomes hard.',
    'adhd': 'ADHD is not a lack of willpower. Attention is pulled away\ninvoluntarily, and every interruption costs time others never lose.\nExtra time and quiet rooms are not favours — they level the field.',
    'schizophrenia': 'People living with schizophrenia often perform everyday tasks\nwhile filtering out voices and images that feel completely real.\nWhat looks like distraction from outside is constant hidden work.',
    'wheelchair': 'A single missing ramp or broken elevator can turn a 2-minute route\ninto a 20-minute one, or make it impossible. Accessibility is not\nan extra — for millions of people it is the only way in.',
    'visual': 'Visual impairment is diverse; this mode uses blur only as a task analogy.\nLarge print, screen readers, contrast, audio information and tactile cues\ncan make information and navigation independently accessible.',
    'deaf': 'Notice what you missed: it was never shown to you at all.\nDeaf people are not ignoring announcements — the information\nsimply never arrives unless someone makes it visual.',
    'dyslexia': 'Dyslexia does not touch intelligence. The letters really do seem\nto move. Extra reading time and fonts/layouts designed for\ndyslexia let the same mind show what it actually knows.',
}
