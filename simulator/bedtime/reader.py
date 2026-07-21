"""A small reading panel for the book and medication-label tasks. Reading is
hard the way it's actually hard: dyslexia scrambles letters and swaps
confusable words, low vision fades and shrinks the text, and there is a brief
comprehension check so you can't just skip it."""
if __package__ in (None, ''):
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import random

from ursina import Entity, Text, Button, Color, camera, destroy, time as utime

from ..config import STATE
from ..dialogue import dyslexify


def reading_severity():
    s = .1
    if STATE.disability == 'dyslexia':
        s = 1.0
    if STATE.disability == 'visual':
        s = max(s, STATE.blindness)
    if {'macular', 'cataracts'} & STATE.active_fx:
        s = max(s, .7)
    return s


BOOK_PAGES = [
    'The lighthouse keeper climbed the spiral stair as the storm gathered '
    'over the black water below.',
    'She had read the letter a hundred times, and still the words refused '
    'to mean what she needed them to mean.',
    'Morning came slow and grey, and the town woke to find the tide had '
    'left something strange upon the sand.',
]

MED_LABEL = dict(
    text='NIGHT DOSE: take ONE (1) tablet with water. Do NOT exceed one '
         'tablet in 24 hours. Take after food.',
    q='How many tablets tonight?', options=['One', 'Two'], answer=0)


class ReadingPanel(Entity):
    def __init__(self, kind, on_done, **kwargs):
        super().__init__(parent=camera.ui, **kwargs)
        self.on_done = on_done
        self.sev = reading_severity()
        self.rescr = 0
        Entity(parent=self, model='quad', color=Color(0, 0, 0, .82),
               scale=(2, 2), z=1)
        card = Color(.95, .93, .85, 1)
        Entity(parent=self, model='quad', color=card, scale=(1.0, .62), z=.5)

        if kind == 'reading_book' or kind == 'read':
            self.body_src = random.choice(BOOK_PAGES)
            title, self.check = 'YOUR BOOK', None
            Text(parent=self, text='SPACE: keep reading   ·   time passes',
                 origin=(0, 0), y=-.26, scale=.8, color=Color(.35, .3, .25, 1))
            self.reading_left = 4.0
        else:
            self.body_src = MED_LABEL['text']
            title, self.check = 'MEDICATION LABEL', MED_LABEL
            self.reading_left = 0
        Text(parent=self, text=title, origin=(0, 0), y=.24, scale=1.2,
             color=Color(.3, .2, .15, 1))
        self.body = Text(parent=self, text='', origin=(0, 0), y=.05,
                         scale=1.0, color=Color(.15, .12, .1, 1))
        self.quiz = []
        self.done = False

    def _render(self):
        txt = self.body_src
        alpha = max(.15, 1 - self.sev * .8)
        if self.sev > .3:
            txt = dyslexify(txt)
        self.body.text = '\n'.join(_wrap(txt, 46))
        self.body.color = Color(.15, .12, .1, alpha)

    def update(self):
        self.rescr -= utime.dt
        if self.rescr <= 0:
            self.rescr = .4
            self._render()
        if self.reading_left > 0:
            self.reading_left -= utime.dt

    def input(self, key):
        if self.done:
            if key in ('1', '2'):
                self._answer(int(key) - 1)
            return
        if key == 'space' and self.check is None:
            if self.reading_left <= 0:
                self._finish(True)
        elif key == 'space' and self.check is not None:
            self._quiz()

    def _quiz(self):
        self.done = True
        self.body.text = ''
        q = self.check
        self.quiz.append(Text(parent=self, text=q['q'], origin=(0, 0), y=.08,
                              scale=1, color=Color(.2, .15, .1, 1)))
        for i, opt in enumerate(q['options']):
            self.quiz.append(Text(parent=self, text=f'{i + 1}) {opt}', origin=(0, 0),
                                  y=-.02 - i * .06, scale=1,
                                  color=Color(.25, .2, .15, 1)))

    def _answer(self, i):
        self._finish(i == self.check['answer'])

    def _finish(self, ok):
        cb = self.on_done
        destroy(self)
        cb(ok)


def _wrap(text, width):
    out, line = [], ''
    for w in text.split(' '):
        if len(line) + len(w) + 1 > width:
            out.append(line)
            line = w
        else:
            line = (line + ' ' + w).strip()
    if line:
        out.append(line)
    return out
