"""Event bus. Systems communicate through events, not hardcoded sequences:
a world event (a crash, a gunshot, police arriving, a greeting) is published
once, and every agent within earshot decides its OWN response based on
distance, personality, emotion and memory."""
if __package__ in (None, ''):    # file was run directly, not imported
    raise SystemExit('This file is part of the game and cannot be run by itself.\n'
                     'Run the game from the project folder with:  python main.py')

from dataclasses import dataclass, field


@dataclass
class WorldEvent:
    kind: str                       # 'crash' | 'gunshot' | 'police' | 'greet' | ...
    position: object                # Vec3
    intensity: float = 1.0          # scales how far it carries / how strong the reaction
    source: object = None           # the agent/entity that caused it
    data: dict = field(default_factory=dict)


class EventBus:
    """Radius-filtered pub/sub. Agents subscribe with a callback; publishers
    fire a WorldEvent and the bus delivers it only to subscribers whose
    position is within (intensity * base_range) of the event."""

    BASE_RANGE = 30.0

    def __init__(self):
        self._subs = []             # (get_position_fn, callback)

    def subscribe(self, get_position, callback):
        entry = (get_position, callback)
        self._subs.append(entry)
        return entry

    def unsubscribe(self, entry):
        try:
            self._subs.remove(entry)
        except ValueError:
            pass

    def publish(self, event):
        reach = self.BASE_RANGE * max(.2, event.intensity)
        for get_position, callback in list(self._subs):
            try:
                pos = get_position()
                if pos is None:
                    continue
                d = (pos - event.position).length()
                if d <= reach:
                    callback(event, d)
            except Exception:
                pass
