"""Ambient dialogue generation. Two nearby agents can strike up a short
conversation whose topic is chosen from location, personality, relationship
and current events. Lines are assembled procedurally (opener + body + reply)
so exchanges rarely repeat, and an active world event hijacks the topic — a
nearby crash makes everyone talk about the crash."""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

import random

TOPICS = {
    'work': (['Long shift?', 'You off work?', 'Boss is a nightmare lately.'],
             ['Tell me about it.', 'Counting the minutes.', 'Same every day.']),
    'weather': (['Nice out, finally.', 'Think it\'ll rain?', 'Bit cold, huh?'],
                ['Been waiting for this.', 'Brought a jacket just in case.',
                 'Never can tell here.']),
    'sports': (['Catch the game?', 'We got robbed last night.', 'Big match Sunday.'],
               ['Don\'t get me started.', 'I had money on that.', 'Should be good.']),
    'gossip': (['You hear about Jai?', 'People, I swear.', 'Did you SEE that?'],
               ['No! What happened?', 'Every time.', 'Unbelievable.']),
    'directions': (['Know where 4th is?', 'Is the station this way?'],
                   ['Two blocks up.', 'Other direction, I think.']),
    'smalltalk': (['How\'s the family?', 'Long time!', 'Good to see you.'],
                  ['Can\'t complain.', 'Way too long.', 'You too!']),
}

EVENT_LINES = {
    'crash': (['Did you SEE that?!', 'Oh my god, the car—', 'Is everyone okay?!'],
              ['Call someone!', 'I got it on video.', 'Let\'s get back.']),
    'police': (['What\'s going on over there?', 'Cops everywhere.'],
               ['Best not to look.', 'Keep walking.', 'Wonder what happened.']),
    'gunshot': (['Was that—?', 'GET DOWN!', 'We need to GO.'],
                ['Move, move!', 'This way!', 'Don\'t stop!']),
}

LAUGH = ['ha!', 'heh.', '*laughs*']


class DialogueEngine:
    """Owns one agent's speech. Conversations are brokered between two
    engines: one leads, the other replies, alternating with pauses."""

    def __init__(self, agent):
        self.a = agent
        self.partner = None
        self.queue = []
        self.line_t = 0
        self.topic = None

    @property
    def busy(self):
        return self.partner is not None

    def start_with(self, other, topic=None, event=None):
        if self.busy or other.dialogue.busy:
            return False
        topic = topic or self._pick_topic()
        openers, replies = (EVENT_LINES.get(event) if event else None) \
            or TOPICS[topic]
        lead = random.choice(openers)
        reply = random.choice(replies)
        # build a short alternating script with a little colour
        script = [(self, lead), (other, reply)]
        if random.random() < .5:
            script.append((self, random.choice(
                TOPICS['smalltalk'][1] + LAUGH)))
        self.partner = other
        other.dialogue.partner = self.a
        self.topic = topic
        self._run_script(script)
        return True

    def _pick_topic(self):
        pers = self.a.profile.personality
        if pers == 'aggressive':
            return random.choice(['sports', 'gossip', 'work'])
        if pers == 'cheerful':
            return random.choice(['smalltalk', 'weather', 'sports'])
        if pers == 'curious':
            return random.choice(['gossip', 'directions', 'weather'])
        return random.choice(list(TOPICS))

    def _run_script(self, script):
        # translate into a shared timeline both engines consume
        t = 0
        for speaker, line in script:
            speaker.dialogue.queue.append((t, line))
            t += 1.4 + len(line) * .035 + random.uniform(.2, .6)   # speaking speed
        end = t + .4
        self._end_at = end
        if self.partner:
            self.partner.dialogue._end_at = end

    def update(self, dt):
        a = self.a
        if not self.busy and not self.queue:
            return
        self.line_t += dt
        # emit queued lines as floating speech + rig lip-sync
        while self.queue and self.line_t >= self.queue[0][0]:
            _, line = self.queue.pop(0)
            a.say_line(line)
        if self.busy and self.line_t >= getattr(self, '_end_at', 0):
            self._finish()

    def _finish(self):
        a = self.a
        a.talking = False
        if self.partner:
            other = self.partner
            self.partner = None
            if other.dialogue.partner is a:
                other.dialogue.partner = None
                other.talking = False
        self.line_t = 0
        self.queue.clear()

    def hijack_for_event(self, other, event_kind):
        if event_kind in EVENT_LINES:
            self.start_with(other, event=event_kind)
