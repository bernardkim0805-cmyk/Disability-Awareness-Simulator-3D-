# Walk In My World — 3D Disability Awareness Simulator

Walk In My World is a first-person educational game built with Python, Ursina, and
Panda3D. It uses short scenarios to demonstrate a narrower and more defensible idea than
“experiencing somebody else's disability”: a task can become harder when information,
spaces, time limits, and controls are designed around only one kind of user.

The project includes seven original experience modes, four playable scenarios, and an
Accessibility Lab containing stackable visual, audio, movement, and cognitive effects.
Its design is informed by public-health guidance, accessibility standards, and disability
advocacy sources listed in [Research basis and references](#research-basis-and-references).

> [!IMPORTANT]
> This is **not a clinical, diagnostic, or scientifically validated reproduction of lived
> experience**. A short game cannot reproduce a person's knowledge, adaptation, identity,
> culture, assistive technology, support network, symptoms, or lifetime experience. Disabled
> advocates and researchers have warned that “disability simulations” can create fear, pity,
> or false confidence when they portray only sudden impairment and difficulty.[^simulation-advocacy]
> Use this project to examine **barriers and design choices**, then learn directly from people
> with the relevant lived experience. Do not use it to claim “now I know what it is like.”

## Quick start

Ursina 8.3.0 requires **Python 3.12 or newer**.

### macOS or Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

### Windows

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

Panda3D is installed automatically as a dependency of Ursina. Do not copy a `.venv`
directory between computers; it contains machine-specific paths and binaries.

On later runs, activate the environment and run `python main.py`. On macOS, narration in
visual-impairment mode uses the operating system's built-in `say` voice. Other game systems
are cross-platform.

## What the simulator is designed to teach

The project follows an interaction-based understanding of disability: outcomes depend not
only on a person's body or mind, but also on environmental and personal factors. The World
Health Organization describes disability as arising from the interaction between health
conditions and environmental and personal factors.[^who-disability] Accordingly, the game's
most important elements are barriers such as a broken elevator, sound-only warning, tiny
print, time pressure, inaccessible stairs, or an interruption-heavy environment.

The baseline is a comparison condition, not a claim that every nondisabled person has the
same abilities. Likewise, an effect's intensity slider is a game parameter—not a medical
severity scale.

Each experience should be discussed using three questions:

1. What important information or route did the environment make unavailable?
2. What accessible alternative changed the outcome?
3. Was the difficulty located in the person, or in the way the task was designed?

## Original experience modes

### No disability (baseline)

- **In the game:** Removes the original simulated effects so the same task can be replayed
  as a comparison.
- **Lesson:** A controlled comparison helps identify which barriers the game added or exposed.
- **Limit:** “Baseline” means only the game's default controls and senses. It is not a model
  of a universal or “normal” person.

### ADHD

- **In the game:** Notifications and intrusive prompts capture the screen, a focus meter
  falls, and the player presses **F** to return to the task. Some scenarios add interruptions
  and time costs.
- **Research connection:** ADHD can present with persistent inattention and/or
  hyperactivity-impulsivity. Difficulties can include organizing or finishing tasks,
  following instructions or conversations, resisting distractions, and remembering daily
  details.[^cdc-adhd]
- **Design lesson:** Quiet spaces, reduced notification load, written structure, breaks, and
  appropriate extra time can reduce avoidable demands. Support is not a reward for effort;
  it changes the conditions under which the task is performed.
- **Limit:** The focus meter is a gameplay metaphor. ADHD has multiple presentations, varies
  between people and situations, and is not simply “being distracted.” The simulation does
  not model the full range of executive-function, emotional, sensory, or hyperactive and
  impulsive experiences.

### Schizophrenia

- **In the game:** Intermittent whispers, threatening text, visual pulses, and shadow figures
  compete with scenario information.
- **Research connection:** Schizophrenia symptoms are commonly grouped as psychotic,
  negative, and cognitive symptoms. Psychotic symptoms may include hallucinations,
  delusions, and thought disorder; cognitive and negative symptoms can also substantially
  affect everyday functioning.[^nimh-schizophrenia]
- **Design lesson:** A person may be doing hidden cognitive work while completing an ordinary
  task. Respectful, consistent support and access to appropriate care matter more than
  ridicule or confrontation.
- **Limit:** This mode depicts only a stylized set of perceptual distractions. Not everyone
  with schizophrenia hallucinates, hallucinations are not always auditory or threatening,
  and the diagnosis cannot be reduced to “hearing voices.” It does **not** mean “split
  personality,” and this project does not portray schizophrenia as violence.

### Wheelchair user

- **In the game:** The player uses one simplified manual-wheelchair control profile, with a
  seated camera, no jumping, and no stair access. A ramp or working elevator becomes part of
  the route rather than optional scenery.
- **Research connection:** Accessible routes need step-free connections. The ADA Standards
  specify technical requirements for ramps and recommend the least possible running slope;
  the guidance also recognizes that stairs and longer ramps create different barriers for
  different people.[^ada-ramps]
- **Design lesson:** The central mechanic is an environmental barrier: a stair-only route or
  failed elevator can create exclusion even when the destination itself is usable.
- **Limit:** Wheelchair users are diverse. People use manual chairs, power chairs, scooters,
  and other mobility devices; some can stand or walk; skills, speed, strength, pain, fatigue,
  and access needs vary. A lower camera and slower movement do not define wheelchair use.

### Visual impairment

- **In the game:** A progressive defocus-blur effect is adjustable from the menu or with
  **[** and **]**. macOS narration provides an audio channel for selected text.
- **Research connection:** Visual impairment includes many different patterns and causes;
  it is not synonymous with complete darkness. WHO notes that vision rehabilitation and
  tools such as mobility training, braille, and digital assistive technologies can support
  independence.[^who-vision]
- **Design lesson:** Contrast, scalable text, screen-reader-compatible information, audio
  description, tactile cues, and consistent navigation provide alternatives to vision-only
  information.
- **Limit:** Uniform blur is a broad game abstraction, not a representation of most eye
  conditions. The Accessibility Lab contains more specific—but still simplified—field-loss
  and visual-disturbance effects.

### Deaf / hard of hearing

- **In the game:** The original mode removes game audio. Sound-only announcements and warnings
  are therefore unavailable unless the scenario also supplies visual information.
- **Research connection:** Hearing loss ranges from mild to profound, can affect one or both
  ears, and does not imply one communication preference. People may use spoken language,
  sign languages, captions, hearing aids, cochlear implants, or other approaches.[^who-hearing]
  W3C guidance calls for captions that include both speech and meaningful non-speech audio
  information.[^w3c-media]
- **Design lesson:** Critical information should not exist only as sound. Captions, visual or
  vibrating alerts, transcripts, interpreters, and redundant cues create access.
- **Limit:** Silence is a test of the game's audio dependency, not a model of every Deaf or
  hard-of-hearing person's perception. Deaf identity and sign-language culture cannot be
  represented by muting speakers.

### Dyslexia

- **In the game:** Signs, dialogue, and questions may scramble or require re-anchoring; the
  kitchen reader adds place-marker jumps, confusable-word substitutions, paced recognition,
  and comprehension checks. School accommodations can change print and narration support.
- **Research connection:** The International Dyslexia Association defines dyslexia around
  persistent difficulties in accurate and/or fluent word reading and spelling, with common
  but not universal phonological and morphological processing difficulties.[^ida-dyslexia]
- **Design lesson:** Text-to-speech, audiobooks, clear layouts, explicit instruction, and
  appropriate time can change access without changing what a learner knows.
- **Limit:** Dyslexia is **not low intelligence**, poor effort, or universally “letters moving
  around.” Scrambling text is an analogy that imposes decoding effort on a fluent reader; it
  is not a literal or diagnostic depiction of dyslexia.

## Scenarios and the barriers they test

### School Test

A timed five-question exam contrasts task knowledge with access to the test itself.

- A teacher gives one hint through speech, demonstrating the failure of audio-only
  information.
- Visual impairment and dyslexia modes add reading access costs.
- **V** toggles accommodations such as larger presentation and narration so the same knowledge
  can be assessed through a more accessible interface.
- Classmate progress and dismissive dialogue represent social pressure and stigma; they are
  scripted examples, not claims about every school or student.

The intended lesson is that an assessment can accidentally measure decoding speed, sensory
access, or resistance to interruption instead of the knowledge it claims to test.

### Catch the Train

The player must reach and board at platform 1 before departure.

- Stairs provide the short route, while the step-free route is longer and the elevator is
  unavailable.
- The departure board is visual; announcements and environmental cues use different channels.
- NPCs taking the short route reveal the time penalty created by infrastructure rather than
  by the destination.

The intended lesson is that reliable elevators, direct step-free routes, readable displays,
and redundant audio/visual announcements determine whether public transport is usable. WHO
reports that people with disabilities encounter inaccessible and unaffordable transport at
far higher rates than nondisabled people.[^who-disability]

### Zombie Escape

This fictional high-pressure scenario exaggerates the consequences of inaccessible design.

- Low light increases dependence on visual contrast and navigation.
- Groans and warnings behind the player demonstrate information available only through sound.
- Route speed and obstacles expose movement barriers.

Zombies are a gameplay device, not research evidence. The educational content is the
comparison between single-channel warnings and redundant, accessible cues.

### Home Kitchen

A randomized kitchen asks the player to read a recipe, gather ingredients, chop, cook, and
serve while managing heat and timing.

- Low-contrast objects and small controls test visual discoverability.
- A sound-only timer is contrasted with a large flashing visual indicator.
- Reading mechanics test place-keeping and decoding load.
- Notification and interruption tasks test attention capture.
- Motor effects can alter input timing during the chopping sequence.

The intended lesson is that ordinary appliances and instructions become safer when controls
are perceivable, warnings use more than one sensory channel, and tasks allow accessible ways
to verify each step.

## Accessibility Lab

The lab separates the seven original modes from stackable effects. These are educational
rendering and control approximations—not medical tests. **Mild**, **moderate**, and **severe**
are effect-strength presets only. Blocked combinations mean two implementations would fight
over or hide the same game output; they do not mean real conditions cannot coexist.

### Visual effects

| Effect | What the game changes | Research-grounded concept and limitation |
|---|---|---|
| Glaucoma | Narrows the visible field | Glaucoma damages the optic nerve and can cause peripheral field loss, but early disease may have no noticed symptoms; a hard-edged “tunnel” is only an analogy.[^nei-eyes] |
| Age-related macular degeneration | Adds a central obscured area | AMD affects central vision used for faces and fine detail while peripheral vision may remain; the generated spot is not an individual clinical field map.[^nei-eyes] |
| Cataracts | Adds haze, glare, faded colour, and reduced contrast | Cataracts cloud the eye's lens. A screen filter cannot reproduce optical scatter or individual adaptation.[^nei-eyes] |
| Diabetic retinopathy | Adds blotches, floaters, and changing clarity | Diabetes can damage retinal blood vessels, and risk increases with duration; annual dilated examination and early treatment matter.[^nei-diabetes] |
| Retinitis pigmentosa | Combines night difficulty with a narrowing field | RP is a group of inherited retinal diseases, often involving night-vision and peripheral-field loss; progression differs by gene and person.[^nei-rp] |
| Protanopia / deuteranopia / tritanopia | Transforms colour using severity matrices | Colour-vision deficiency has several types and is not simply grayscale. Meaning should never rely on hue alone.[^nei-colour] The matrices are based on Machado, Oliveira, and Fernandes' physiologically based model.[^machado] |
| Visual snow syndrome | Adds persistent visual static and light artifacts | A stylized overlay represents reported persistent visual phenomena; it cannot establish a diagnosis or reproduce the syndrome's full range.[^visual-snow] |
| Migraine aura | Animates an expanding shimmering blind arc | Visual aura can include temporary scintillating or field-loss phenomena and can occur with or without headache. The game compresses timing and uses one pattern.[^migraine-aura] |
| Oscillopsia | Makes the world appear to bounce with movement | Oscillopsia is the perception that the visual environment is moving or unstable, often related to gaze-stabilization problems; camera shake is only a rough analogy.[^veda-oscillopsia] |

### Audio effects

| Effect | What the game changes | Research-grounded concept and limitation |
|---|---|---|
| Hearing loss | Attenuates and filters game sounds | Hearing loss differs by frequency, ear, degree, cause, and listening environment. One low-pass filter is not a personal audiogram.[^who-hearing] |
| Tinnitus | Adds a continuous configurable tone | Tinnitus is sound perception without an external source and may be ringing, buzzing, roaring, or something else; the game's tone is one possible analogy.[^nidcd-tinnitus] |
| Auditory processing disorder | Delays and overlaps selected sounds | CAPD concerns neural processing of auditory information and may affect localization, discrimination, timing, and understanding speech in noise. Diagnosis and terminology require professional assessment; delayed audio is simplified.[^asha-capd] |

### Movement effects

| Effect | What the game changes | Research-grounded concept and limitation |
|---|---|---|
| Parkinsonian tremor | Adds a resting camera oscillation and slower movement initiation | Parkinson's disease can involve tremor, bradykinesia, rigidity, balance changes, and many non-motor symptoms. Camera movement captures neither the disease nor the skill of a person living with it.[^ninds-parkinsons] |
| Essential tremor | Adds faster oscillation that increases during action | Essential tremor is distinct from Parkinson's disease and commonly appears during posture or action. The game models only a control disturbance.[^ninds-tremor] |
| Vestibular disorder | Adds horizon tilt, drift, sway, and lateral pull | Vestibular disorders are diverse and may affect balance, gaze stability, spatial orientation, and participation. Artificial camera roll is not equivalent to vertigo or a specific diagnosis.[^veda-disorders] |

### Cognitive effects

| Effect | What the game changes | Research-grounded concept and limitation |
|---|---|---|
| Prosopagnosia | Removes facial detail and replaces names with clothing descriptions | Prosopagnosia impairs face recognition; it does not necessarily make faces visually blank. Clothing labels demonstrate a compensatory cue, not the person's perception.[^ninds-prosopagnosia] |
| Hemispatial neglect | Removes selected left-side interface information | Neglect is an attention disorder, often after right-hemisphere injury, and is not the same as blindness. Hiding half a HUD is a task analogy only.[^stroke-neglect] |
| ADHD attention capture | Adds intrusive prompts and fades the objective | This narrower lab effect demonstrates distraction and recovery cost, not ADHD as a whole.[^cdc-adhd] |
| Memory impairment | Fades objectives and names; **J** opens a journal | Memory disorders can affect different systems and causes in very different ways. The journal demonstrates external memory support rather than a universal symptom pattern.[^memory] |

## Controls

### Main menu

- **1–7** select an original experience.
- **8 / 9 / 0** select School Test, Catch the Train, or Zombie Escape.
- Use the on-screen scenario buttons to select Home Kitchen.
- **L** opens the Accessibility Lab.
- **Enter** starts the selected scenario.
- **Esc** quits.

### Walking scenarios

- **WASD** move; **mouse** look; **Space** jump when available.
- **E** talks to NPCs or interacts with desks, signs, doors, and objects.
- **1 / 2 / 3** answer school-test questions.
- **V** toggles school accommodations.
- **F** returns focus during ADHD attention-capture effects.
- **[ / ]** adjusts the original visual-impairment blur.
- Hold **N** to compare the normal rendering when compatible visual lab effects are active.
- **Esc** returns to the menu or exits.

### Accessibility Lab

- **1–5** changes category; arrow keys change the selection.
- **Space / Enter** toggles an effect.
- **P** cycles effect-strength presets.
- **S** toggles split-screen comparison.
- **D** opens the selected original experience's comparison space.
- **R** resets safely to baseline.
- **Esc** applies the current selection and returns.

## Deterministic development launches

Launch a scenario directly:

```bash
python main.py --scenario train --window-size 1280x720
```

Open the lab directly:

```bash
python main.py --open-lab
```

The command-line parser also supports original experience and lab-effect overrides. See
`simulator/windowing.py` for the accepted flags and validation behavior.

## Responsible classroom use

Before play, tell participants that the game demonstrates selected access barriers rather
than reproducing disability. During discussion, avoid asking whether the experience was
“scary” or whether players now feel sorry for disabled people. Ask which design decision
withheld access, which alternative fixed it, and who should participate in redesigning it.

After play:

- Pair the activity with first-person work by disabled authors, speakers, or creators.
- Compensate disabled contributors and involve them in design and evaluation: “nothing about
  us without us” should be a process, not a slogan.
- Discuss disability culture, identity, expertise, adaptation, and assistive technology—not
  only difficulty.
- Never use a player's game performance to diagnose a condition or judge a disabled person's
  abilities.
- Invite corrections. Language and preferred identity terms vary by person and community.

This framing follows disability-led criticism that temporary simulations omit adaptation and
can reinforce stereotypes.[^simulation-advocacy] The project's strongest defensible claim is:
**players can compare how specific interface and environmental barriers change a task.**

## Research basis and references

Sources were selected primarily from public-health agencies, government accessibility
standards, professional associations, peer-reviewed work, and disability-led organizations.
They support the educational descriptions and design rationale; they do not validate this
game as a faithful simulation. Accessed July 20, 2026.

[^who-disability]: World Health Organization, [Disability](https://www.who.int/news-room/fact-sheets/detail/disability-and-health).
[^simulation-advocacy]: Able South Carolina, [Disability Simulations position statement](https://www.able-sc.org/resource-library/position-statements/disability-simulations/); Sally French, [“Simulation Exercises in Disability Awareness Training: A Critique”](https://doi.org/10.1080/02674649266780261), *Disability, Handicap & Society* 7(3), 1992.
[^cdc-adhd]: U.S. Centers for Disease Control and Prevention, [Symptoms of ADHD](https://www.cdc.gov/adhd/signs-symptoms/index.html).
[^nimh-schizophrenia]: National Institute of Mental Health, [Schizophrenia](https://www.nimh.nih.gov/health/publications/schizophrenia).
[^ada-ramps]: U.S. Department of Justice, [2010 ADA Standards for Accessible Design, §405 Ramps](https://www.ada.gov/law-and-regs/design-standards/2010-stds/#405-ramps).
[^who-vision]: World Health Organization, [Blindness and vision impairment](https://www.who.int/news-room/fact-sheets/detail/blindness-and-visual-impairment).
[^who-hearing]: World Health Organization, [Deafness and hearing loss](https://www.who.int/news-room/fact-sheets/detail/deafness-and-hearing-loss).
[^w3c-media]: W3C Web Accessibility Initiative, [Making Audio and Video Media Accessible](https://www.w3.org/WAI/media/av/).
[^ida-dyslexia]: International Dyslexia Association, [Definition of Dyslexia](https://dyslexiaida.org/definition-of-dyslexia/).
[^nei-eyes]: National Eye Institute, [Eye Conditions and Diseases](https://www.nei.nih.gov/eye-health-information/eye-conditions-and-diseases) (links to NEI condition pages for glaucoma, AMD, cataracts, and diabetic retinopathy).
[^nei-diabetes]: National Eye Institute, [Diabetic Eye Disease Resources](https://www.nei.nih.gov/about/education-and-outreach/diabetic-eye-disease-resources).
[^nei-rp]: National Eye Institute, [Retinitis Pigmentosa](https://www.nei.nih.gov/eye-health-information/eye-conditions-and-diseases/retinitis-pigmentosa).
[^nei-colour]: National Eye Institute, [Color Blindness](https://www.nei.nih.gov/eye-health-information/eye-conditions-and-diseases/color-blindness).
[^machado]: Gustavo M. Machado, Manuel M. Oliveira, and Leandro A. F. Fernandes, [“A Physiologically-based Model for Simulation of Color Vision Deficiency”](https://doi.org/10.1109/TVCG.2009.113), *IEEE Transactions on Visualization and Computer Graphics* 15(6), 2009.
[^visual-snow]: National Organization for Rare Disorders, [Visual Snow Syndrome](https://rarediseases.org/rare-diseases/visual-snow-syndrome/).
[^migraine-aura]: American Migraine Foundation, [Migraine With Aura](https://americanmigrainefoundation.org/resource-library/migraine-with-aura/).
[^veda-oscillopsia]: Kim et al., [“Bilateral Vestibular Weakness”](https://pmc.ncbi.nlm.nih.gov/articles/PMC5990606/), *Current Opinion in Neurology* 31(1), 2018. The review describes oscillopsia as the illusion that the environment moves with head movement when the vestibulo-ocular reflex does not stabilize gaze.
[^nidcd-tinnitus]: National Institute on Deafness and Other Communication Disorders, [What Is Tinnitus?](https://www.nidcd.nih.gov/health/tinnitus).
[^asha-capd]: American Speech-Language-Hearing Association, [Central Auditory Processing Disorder](https://www.asha.org/practice-portal/clinical-topics/central-auditory-processing-disorder/).
[^ninds-parkinsons]: National Institute of Neurological Disorders and Stroke, [Parkinson's Disease](https://www.ninds.nih.gov/health-information/disorders/parkinsons-disease).
[^ninds-tremor]: National Institute of Neurological Disorders and Stroke, [Tremor](https://www.ninds.nih.gov/health-information/disorders/tremor).
[^veda-disorders]: Vestibular Disorders Association, [About Vestibular Disorders](https://vestibular.org/article/what-is-vestibular/about-vestibular-disorders/).
[^ninds-prosopagnosia]: National Institute of Neurological Disorders and Stroke, [Prosopagnosia](https://www.ninds.nih.gov/health-information/disorders/prosopagnosia).
[^stroke-neglect]: American Stroke Association, [Spatial Neglect](https://www.stroke.org/en/about-stroke/effects-of-stroke/cognitive-effects/spatial-neglect).
[^memory]: National Institute on Aging, [Memory Loss and Forgetfulness](https://www.nia.nih.gov/health/memory-loss-and-forgetfulness).

## Contributing

Research citations are necessary but not sufficient. Changes that represent a disability
should state exactly what is being approximated, what is omitted, what barrier or accessible
alternative is being taught, and whether people with that lived experience reviewed it.
Reports from disabled players—especially reports of stereotyping, inaccessible controls, or
misleading claims—should be treated as substantive design feedback.
