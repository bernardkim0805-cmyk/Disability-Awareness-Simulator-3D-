# Walk In My World — 3D Disability Awareness Simulator

A first-person 3D simulator (Python + [Ursina](https://www.ursinaengine.org/)) that lets you
experience everyday situations through the lens of a disability, while the NPCs around you
breeze through the same tasks.

## Run it

Requires Python 3.10+ on Windows, macOS, or Linux.

```bash
# from the project folder — create a FRESH virtual environment on each machine
python3 -m venv .venv                # Windows: py -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Do **not** copy a `.venv` folder from another computer — virtual environments
contain machine-specific binaries and must be recreated locally. Text-to-speech
narration (visual-impairment mode) uses the built-in voice on macOS only; the
rest of the game is cross-platform.

## The menu

A rotating 3D plaza sits behind the menu. Pick one **experience** and one **scenario**, then START.

**Experiences**

| Mode | What it does |
|---|---|
| No disability (baseline) | Play normally, for comparison |
| ADHD | Distractions hijack the screen; a focus meter drains; press **F** to refocus |
| Schizophrenia | Whispers fade in, shadow figures lurk (look at them and they vanish), reality pulses |
| Wheelchair user | Seated camera height, slower, no jumping, **stairs are impossible** |
| Visual impairment | Adjustable blindness — slider in the menu, `[` / `]` in game |
| Deaf / hard of hearing | All sound cues (PA announcements, warnings behind you) simply never appear |
| Dyslexia | Every sign, question and dialogue line continuously rescrambles |

**Scenarios**

- **School Test** — a timed 5-question exam. Classmates hand in perfect papers around you.
  The teacher gives one hint *out loud only*. Press **V** to toggle accommodations
  (large print / screen reader) and feel the difference they make.
- **Catch the Train** — reach platform 1 in 90 seconds. Stairs are fast, the elevator is
  out of order, and the accessible ramp is the long way round. The departure board is the
  only *visual* source of the announcement.
- **Zombie Escape** — reach the safehouse at night. Others sprint off instantly; groans
  behind you are a sound cue you may never receive.

## Controls

- **WASD** move · **mouse** look · **Space** jump (not in a wheelchair)
- **E** talk to NPCs / interact (desks, departure board, train doors)
- **1/2/3** answer test questions · **V** accommodations · **F** refocus (ADHD)
- **[ / ]** adjust blindness (visual impairment) · **Esc** back to menu / quit

Every scenario ends with a short reflection on what just happened and why it matters.

## Accessibility Lab

The lab separates the seven original full experience modes from newer stackable
visual, hearing, movement, and cognitive effects. Choose one original experience,
then add compatible individual effects and adjust their intensity. Baseline clears
all simulations. Combinations that would hide or duplicate one another are visibly
blocked rather than silently producing misleading results.

Controls in the lab: number keys `1`-`5` switch categories, arrow keys select,
`Space`/`Enter` toggles, `R` resets to baseline, and `Esc` applies and returns.
During scenarios, hold `N` to compare normal vision when visual effects are active.

For deterministic development checks, launch a scenario directly without changing
normal menu behavior:

```bash
python main.py --scenario train --window-size 1280x720
```
