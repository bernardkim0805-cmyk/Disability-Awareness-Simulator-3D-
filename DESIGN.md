# Design System — Walk In My World

Reusable building blocks for scenarios and future disability modules.
Everything targets Panda3D's fixed-function pipeline (this project disables
GLSL shaders in `main.py` for macOS compatibility): real lights + vertex
normals for shading, `entity.setLightOff()` for anything that should glow.

## Characters — `simulator/human.py`

`Human(skin=…, shirt=…, pants=…, hair=…, hunched=False)` builds a ~1.75-unit
articulated figure around joint pivots:

- **Rig**: hips → torso (lean pivot) → head; per-side shoulder→elbow and
  hip→knee chains. Feet, hands, ears, nose, hair (4 random styles), optional
  glasses (28%) and beard (18%), random eye color, natural height/width
  variation, soft blob shadow.
- **Gait** — `advance(moving, speed)` each frame:
  legs swing from the hip, knees flex only during the swing phase, ankle
  pivots roll the feet (toe-off push / pre-strike toe-up), arms counter-swing
  with elbow bend, pelvis rocks and shifts weight laterally, torso bobs twice
  per stride and leans into the walk, shoulders counter-rotate while the head
  counter-rotates back to keep the gaze forward. speed > 4.5 switches to a
  run: bigger stride, deep elbow bend, forward lean, higher bounce.
  Every instance rolls a **gait personality** (`self.gait`): cadence, stride,
  arm swing, sway, slouch and bounce multipliers — no two people move alike.
  Idle = breathing sway + head glances. `hunched=True` = zombie shamble.
- **Lip sync** — set `human.talking = True` and the mouth flaps organically;
  `DialogueBox.say(..., speaker_entity=npc)` does it automatically while each
  line types out, restoring the posed expression after.
- **Identity accessories** (auto-rolled, skipped when hunched): baseball cap
  (16%) / beanie (12%), open jacket (25%) or tie (15%), wristwatch (30%).
- **Faces** — `set_expression(name)` with poses driven by brow angle/raise,
  mouth-corner curve, eyelid openness and mouth opening:
  `neutral · happy · sad · worried · angry · surprised · focused · tired ·
  smug · scared`.
  Blinking is automatic. Add new emotions by extending `Human.EXPRESSIONS`
  (tuple: brow_angle, brow_raise, mouth_curve, lid, open).
- **Zombie horror kit** (see `zombies.Zombie`): permanently gaping jaw with
  yellowed teeth, lolling head + random twitches, rotting face patches, blood
  runs down the shirt, 50% gouged chest with exposed ribs, 40% missing
  forearm with a stump.
- **Face anatomy**: eye whites + colored iris + pupil + emissive catchlight,
  optional lashes (45%), two-tone lips (dark upper / light lower), a dark
  mouth aperture with teeth revealed as `open` rises, nostrils, cheekbones,
  blush (40%), freckles (15%), hollow-rim glasses (28%), chin beard (18%),
  4 hair styles. Skin-derived colors: lips = skin with reduced G/B; brows =
  hair darkened 20%.

`NPC(name, lines, waypoints, speed, expression, …)` (`simulator/npc.py`) adds
wandering, `sprint_to()` (for "NPCs make it look easy" beats), `face(pos)`,
dialogue lines and the interaction marker.

## Environments — `simulator/world.py`

Lighting: `day_lights() / indoor_lights() / night_lights()` → `SceneLights`
(store as `self.lights` in a scenario; `BaseScenario.cleanup` destroys it).

Builders: `building()` (textured, roof lip, door, lit/dark window grid),
`tree()`, `street_lamp(on=…)` (glow + light pool), `bench()`, `fountain()`,
`night_sky()` (moon + halo + star dome), `road()` (dashed lines),
`sidewalk()`, `abandoned_car()`.

Micro-detail: `ground_details(area, cracks, pebbles, leaves, tufts, scraps)`,
`manhole()`, `puddle()`. Use these on every walkable surface — they sell scale.

## Audio — `simulator/audio.py`

All effects are **synthesized to WAV on first run** (`assets/audio/`) — no
external assets. Cues: `chime` (PA), `bell` (school), `groan` (zombie),
`rumble` (train), `buzz` (ADHD phone), `whisper` (schizophrenia),
`success`/`fail` (endings). Add a cue by adding a generator lambda to
`audio.CUES` built from `_tone/_noise/_mix/_seq`.

Accessibility routing (`AudioManager`, singleton via `get_audio()`):
- **Deaf mode** → `play()` and `speak()` are silent. Hearing players lose the
  same information a deaf player never receives — this asymmetry IS the sim.
- **Visual-impairment mode** → `speak(text)` narrates via macOS `say`
  (cached WAVs in `assets/audio/tts/`, generated on a background thread) —
  a screen-reader experience. Announcements, dialogue, objectives and
  end-screens are already wired through it.
- `Announcer.sound(text, cue=…)` plays the cue + narration + on-screen text;
  `Announcer.visual(...)` shows text and narrates it for blind players.
- Scenarios call `get_audio().play(cue)` for events; `BaseScenario.cleanup`
  stops everything via `stop_all()`.

Rendering quality: `main.py` requests 8x MSAA
(`framebuffer-multisample 1`, `multisamples 8`, `AntialiasAttrib.MMultisample`).

## Effect architecture — `simulator/fx/`

`DisabilityEffect` (core.py) defines the lifecycle every condition follows:
`initialize() · enable() · disable() · setIntensity(0..1) · update(dt) ·
cleanup()`. Category bases: `VisualEffect` (contributes parameters, never
touches the GPU), `AudioEffect` (installs AudioManager hooks),
`MovementEffect` (additive camera/player offsets, removed each frame),
`CognitiveEffect` (gameplay info; must restore what it hides).
`EffectStack` builds from `STATE.lab_effects`, merges visual params into the
single **GLSL 1.20 post-process pass** (postfx.py — the newest GLSL this
Mac accepts; one fullscreen pass regardless of how many effects stack),
and handles hold-N normal-vision compare + split-screen (left normal /
right simulated, done in-shader).

Implemented conditions (registry.py holds the educational content —
medical, gameplay, misconception, assistive tech, references):
- **Visual**: glaucoma, AMD (noise-shaped central scotoma), cataracts,
  diabetic retinopathy (+CPU floater layer), retinitis pigmentosa,
  protan/deutan/tritanopia (Machado 2009 matrices), visual snow (+entoptic
  specks), migraine aura (scintillating scotoma on a timed cycle),
  oscillopsia.
- **Audio**: hearing loss (low-passed "muffled" variants of every cue +
  attenuation), tinnitus (synthesized stereo loop, pitch/side
  configurable), auditory processing disorder (onset delay + speech echo).
- **Movement**: parkinsonian tremor (resting tremor + bradykinesia ramp),
  essential tremor (action tremor), vestibular disorder (roll drift, step
  sway, lateral imbalance).
- **Cognitive**: prosopagnosia (face_parts blanked; dialogue names become
  clothing descriptors), hemispatial neglect (left HUD/markers dropped),
  ADHD attention capture (F to refocus), memory impairment (objective
  fades; J = journal).

UI: `simulator/lab.py` — Accessibility Simulator panel from the main menu:
category tabs, per-effect toggle + intensity slider, info pane, presets
(mild/moderate/severe), split-screen toggle, live preview on the menu
plaza, disclaimer. New condition = one class + one registry entry.

Lab selection rules live in `simulator/lab_state.py`, independently of Ursina UI.
This keeps original-experience exclusivity, effect compatibility, presets, reset,
active summaries, and educational metadata headlessly testable. The UI applies
changes live; there is no hidden draft state. Original visual and ADHD overlays
begin in scenarios because applying them to `camera.ui` would obscure the lab's
own accessible controls. The schizophrenia world-space preview remains available.

## Home Kitchen scenario — `simulator/kitchen/` (self-contained package)

Kept in its own package so parallel work elsewhere never conflicts; the only
shared-file touch points are the `SCENARIOS['kitchen']` entry (config.py)
and one import in `menu._scenario_class`.

- Randomized per run: layout (apartment / family / cluttered), lighting
  (day / evening / flicker — flicker modulates the SceneLights ambient node
  live), ambience (fridge hum + water/radio/chatter; all synthesized in
  `kitchen/sounds.py` as `kitchen_*` cues so audio.py stays untouched).
- Cooking chain: read recipe -> gather (fridge/cupboard/counter) -> chop
  cutscene -> stove -> serve. Health drops with burns/cuts; fire ends runs.
- `reader.py`: reading difficulty done right — place-marker jumps (R to
  re-anchor), word-by-word recognition (SPACE), mirrored letters and
  confusable-word swaps, unread text rendered as `~~~` shapes, plus a
  comprehension check. Severity from dyslexia mode / lab conditions.
- `cutscene.py`: chopping close-up (hand, knife, board, carrot) built in a
  diorama 60 units below the map; rhythm-timed slices; motor conditions add
  wobble + input latency + smaller windows; misses cost fingers.
- Accessibility mechanics: white-on-white counters/plates + clear glasses
  (low contrast by design), tiny stove knobs + pale indicator, sound-only
  timer beep (deaf mode hears nothing) with a big flashing beacon above the
  stove as the visual alternative, glaucoma culls peripheral props until
  looked toward, ADHD gets loud phone notifications + blocking interrupt
  tasks (P / door).

## City Drive scenario — `simulator/driving/` (self-contained package)

Registration-only shared edits (SCENARIOS entry + one menu import), same
partner-safe pattern as the kitchen.

- `city.py`: 3x3 signalized grid (working `IntersectionLights` state
  machines cars/player both obey), stop signs, speed/school/construction
  signage, street names, crosswalks, lane arrows, bike lane, tunnel,
  bus stop, potholes/debris/parked-car blockers, clinic + parking bay.
- `traffic.py`: lane-following ring AI with light compliance, spacing and
  brake lights; ~15% risky drivers (sudden stops, swerves, speeding);
  cyclist in the bike lane; a bus that dwells at its stop; an `Ambulance`
  whose siren volume tracks distance (paired with the HUD direction banner
  — the deaf-accessible channel).
- `car.py`: first-person cockpit (rotating wheel, dash, GPS console, A
  pillars, hood) + modern-vehicle GUI: nav bar w/ ETA, big speed + limit
  roundel, fuel/engine/signals, and **mirrors as proximity displays** with
  blind-spot flash (no render-to-texture on this GPU — re-encoding the
  information IS the accessibility lesson). GUI adapts: low-vision -> 1.45x
  text + high contrast; deaf -> bigger/longer flashing warnings + camera
  'vibration' pulse. Motor conditions add steering wobble + input latency.
- `phone.py`: TAB smartphone (map, route list, voice-nav toggle); ADHD gets
  loud competing notifications (P to dismiss); time-open and
  distracted-driving seconds are metered.
- `scenario.py`: doctor's-appointment objective with 6-leg GPS route,
  'recalculating' wrong-turn detection, voice navigation via `say_nav`
  (assistive feature, works for everyone, silent in deaf mode), weather
  (day/night/rain with windshield drops + animated wiper), scripted school
  pedestrian + ambulance events, law tracking (red lights, speed zones
  20/40/60), collisions/potholes, and an end **analysis panel** (time,
  crashes, close calls, violations, wrong turns, distraction seconds,
  assist usage) framing the accessibility thesis.

## Driving law enforcement — `simulator/driving/laws.py` + `police.py`

- `laws.py`: `DrivingEvaluator` continuously scores behaviour — speeding
  (two tiers), red lights, rolled stop signs, pedestrian/EV yielding,
  oncoming-lane, tailgating, turn-signal use, unsafe lane changes,
  collisions, near misses, potholes. Real-time SAFETY score + hidden "heat".
  Every threshold/penalty/weight is in `LAW_CONFIG` — tune without touching
  detectors. **Fairness is structural**: the evaluator's inputs are only
  positions/speeds/signals; no disability flag reaches it, so an identical
  drive scores identically for everyone.
- `police.py`: `PoliceManager` dispatches a `PoliceCar` purely on accumulated
  heat, closes in with lights/siren (siren volume ~ distance; deaf players
  get the HUD PULL-OVER banner + vibration), and requires a sustained stop.
  Keep driving -> grace window -> pursuit + backup unit -> license suspended.
  On stopping, an officer NPC walks to the window and the DialogueBox quotes
  `evaluator.recent_violations()` verbatim. Severity ladder from score/repeat:
  warning -> citation (fine + record) -> suspension. Officer script ALWAYS
  states the stop is about observed driving that would stop any driver, never
  the disability. `edu_summary()` maps active conditions -> assistive-tech
  recommendations (adaptive controls, voice nav, blind-spot monitoring, etc.)
  shown on every major consequence and the end screen. Major collision =
  tow + $450 + vehicle lost.

## Driving open world — `simulator/driving/worldgen.py` + `config.py`

`build_open_world()` grows the downtown grid into an interconnected map (no
loading screens): an outer **highway ring** with on/off ramps, guardrails,
reflectors and overhead gantry signs; a **lit tunnel** to the south; a
**suspension bridge** over a river (towers, cables, guard barriers, water +
boat below) to the north; and **suburbs / industrial / countryside**
districts, each with its own identity, plus gas stations and spur-road
connectors. `config.py` holds every tunable (region speeds/densities/tints,
traffic + truck fractions, weather probabilities, police, tunnel/bridge
params). Modular facades match the brief: `WorldGeneration`,
`RoadNetworkSystem` (region_at / speed_limit / in_tunnel / on_bridge);
TrafficAI/Police/Emergency already exist in traffic.py/police.py. Driving
effects: tunnel darkens the view + echoes the engine and warns of weak GPS;
the bridge applies a crosswind nudge; region banners announce district
changes; region-aware speed limits (downtown 40, highway 90, etc.); heavy
`Truck` traffic on the ring/industrial with slower accel + wider mass.
Scale is bounded (fixed-function primitive renderer) — AAA-structured, not a
literal square-mile map.

## Driving world managers + damage — `driving/managers.py`, `damage.py`

Modular manager layer over the existing systems (the brief's architecture):
`WorldManager` owns `TrafficManager`, `PedestrianManager`, `PoliceManager
Facade`, `WeatherManager`, `CollisionManager`, `EventManager`,
`MaterialSystem`, `RenderingManager` — all config-driven from `config.py`
(QUALITY/DENSITY/DAMAGE blocks). `CollisionManager` routes every crash
through `VehicleDamageSystem` (damage.py): progressive, driver-visible
damage — windshield-crack overlays, hood smoke, steering-alignment pull,
top-speed loss, tow when totaled — plus notifying nearby drivers (brake) and
pedestrians (startle). `RenderingManager.report()` is deliberately HONEST:
it enumerates what the fixed-function stack CANNOT do (PBR, deferred, HDR,
SSAO, SSR, volumetrics, TAA, reflection probes, GI, ragdoll/Euphoria,
rigidbody destruction) rather than faking a AAA pipeline. Those need
programmable shaders this Mac can't compile — not implementable here.

## Autonomous NPC agents — `simulator/agents/` (self-contained tab)

Component-based, event-reactive crowd (Living City scenario). Fidelity is
BEHAVIOURAL, not rendered — no true IK/cloth/muscle sim on the fixed-function
primitive rig; those are approximated.

- `events.py`: `EventBus` — radius-filtered pub/sub. World events (crash,
  gunshot, police, greet) reach only agents within `intensity * range`;
  each decides its own reaction.
- `profile.py`: `roll_profile()` — procedural identity (age, personality,
  routine, build) that derives all the tunable knobs the brief named
  (walking_speed_variation, gesture_probability, eye_contact_frequency,
  conversation_chance, emotional_reaction_strength, awareness_radius,
  curiosity_level, social_distance) from personality so variation stays
  believable. Effectively unbounded combinations.
- `systems.py`: the component stack — `PerceptionSystem` (rate-limited
  scan + gaze focus), `EmotionSystem` (valence/arousal model -> emotion
  label), `MemorySystem` (recognizes repeat player encounters, sentiment),
  `MovementController` (weight/momentum: rotate-then-move, eased accel,
  terrain-follow), `AnimationController` (feeds the rig's live procedural
  gait — no canned clips — plus emotional posture), `FacialExpression
  Controller` (emotion face + eye-contact/aversion saccades + blink),
  `GestureController` (personality-scaled wave/shrug/point/check-watch/…),
  `PhysicsInteractionSystem` (startle/stumble/recoil with recovery easing).
- `dialogue_engine.py`: ambient two-agent conversations, topic by
  location/personality; a nearby event hijacks the topic.
- `agent.py`: `Agent(Human)` + `NPCController` behaviour state machine
  (routine/wander/observe/socialize/react/flee) whose transitions are
  weighted by personality/emotion/memory/perception — emergent, not
  scripted.
- `crowd.py`: `AgentManager` spawns the crowd with near/far LOD and owns
  the bus; `fire_event()` broadcasts. `demo.py`: Living City sandbox
  (C crash / P police / G shout / E greet). Verified: 26 agents, all
  different gaits, split 18-flee / 8-gawk on a crash by personality.

## Adding a new disability module

1. `config.py`: add an entry to `DISABILITIES` (name, icon, color, desc) and
   `REFLECTIONS` (the empathy text at the end).
2. `effects.py`: add its sensory/attention mechanics in `EffectsManager`
   (`__init__` for HUD, `update`/`input` for behavior). Overlays via
   `camera.overlay.color`; fog via the exponential-fog pattern in
   `_apply_blindness`.
3. Scenarios automatically pick it up through `STATE.disability`; add
   scenario-specific twists inside each scenario's `tick()` (see the deaf
   PA-announcement or wheelchair stairs-block patterns).
4. Give NPCs contrasting ease: `sprint_to`, expressions, and an
   `announcer.visual(...)` beat showing them succeed effortlessly.
5. Optionally add social sting: an entry in `config.MOCKERY[scenario][disability]`
   (`name`+`lines` spawns a smug mocker via `BaseScenario.setup_mockery(pos)`;
   `taunt`+`taunt_time` fires once via `tick_mockery(t)`). Keep taunts
   realistic, PG, and let the reflection screen land the counterpoint.

## Conventions

- Text in the world: `Text(parent=self, scale≈6–10, billboard=True)` for
  signs; never above scale 12.
- Quads face −z by default — visible to a player approaching from lower z.
- Every glowing thing (windows, lamps, screens, markers) must call
  `setLightOff()`, otherwise scene lighting dims it.
- Emoji don't render in the bundled font — ASCII markers only.
