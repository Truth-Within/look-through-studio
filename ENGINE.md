# Animation engine

A procedural 2D stickman engine in `engine/`. No GPU, no assets: everything is drawn with Pillow and runs on CPU
(about 25 frames/s at 720p, about 140 MB of RAM on a laptop-class CPU).

```
narration segment (cast, props, actions, camera)
        |  engine/director.py      plans the performance, retries with smoother blends if checks fail
        v
per-character timeline of Beats      engine/performance.py   (frame-rate independent: evaluate at any time t)
        |  poses, gaits, IK reaches, expressions, prop events
        v
skeleton + FK/IK + ground contact    engine/skeleton.py
        v
character + props drawn 2x, reduced  engine/character.py, props.py, draw.py, stage.py
        v
quality report                       engine/quality.py   -> output/<video>/quality.json
```

## What is in it

| Area | What exists |
|---|---|
| Skeleton | 17-bone hierarchy (spine, chest, neck, head, 2 arms x 2, 2 legs x 3 incl. feet), joint limits, forward kinematics, analytic two-bone IK, whole-body rotation (lying, handstand, cartwheel) |
| Poses | 70 named poses in `engine/library.py` (standing, sitting, squatting, crouching, kneeling, lying, bending, leaning, stretching, balancing, gestures, emotions, dance, kicks, punches...) |
| Locomotion | Distance-driven gait generator: walk, jog, run, sprint. Planted feet never slide because the gait phase comes from distance travelled. Jump, hop, crawl, climb, fall, get-up, stumble, turn |
| Foot placement | Feet are locked to the ground with IK during every stationary action (sitting, standing up, reaching, squatting) |
| Hands and objects | Hand IK to prop grips, body anchors (chest, overhead), hand-held items, carrying, throwing, handing over |
| Props | 16 types with attachment points and animated state: chair, desk, bed, door, ladder, board, book (opens, turns pages), phone, cup, apple (bites), ball, hammer, box, laptop, notebook, pot |
| Faces | 25 expressions built from continuous parameters (eye openness, pupils, two brows, brow tilt, mouth openness/curve/width, blush, tears, sweat, eyelids) plus posture offsets. Blends smoothly, blinks on its own |
| Appearance | 8 outfits (casual, hoodie, professional, prehistoric, toga, medieval, fantasy, sporty), 9 hairstyles, 13 accessories, 4 skin tones, 8 hair colours, 6 body builds |
| Views | A continuous heading angle: front, three-quarter, side, back and everything between. Hair, face and body width follow it |
| Actions | About 95 actions (see below). Complex acts are built from simple beats, IK reaches, prop events and expressions |
| Camera | wide, medium, close, follow, two_shot, with a slow push-in and smooth tracking |
| Quality checks | Broken joints, unreachable limbs, sliding feet, passing through furniture, hands off a held prop, leaving the frame, abrupt pose changes, repeated actions |
| Regeneration | Scenes are cached by content + starting state. Edit one scene and only it (and scenes whose starting state changed) re-render. `--regen 3,5` forces specific scenes |

## Action vocabulary

- **Postures:** stand, sit_down / sit_on, stand_up, squat, crouch, kneel, lie_down, wake_up, bend, lean, stretch, any pose name
- **Locomotion:** walk_to, jog_to, run_to, sprint_to, jump, hop, crawl_to, climb, dance, fall, get_up, stumble, turn_to
- **Upper body:** point_at, wave, clap, reach_for, push, pull, throw, catch, carry, lift, hug, cross_arms, shrug, bow, salute
- **Objects:** pick_up, put_down, pull_chair, open_book, turn_page, read, write, type, use_phone, eat, drink, cook, open_door, use_tool
- **Social:** greet, shake_hands, hand_over, argue, teach, listen, help
- **Feelings:** express, react, look_at

## How the planner works

`pipeline/script.py` asks the LLM to act as a director. For each narration segment it returns who is on stage, props, camera,
and an ordered list of actions. `engine/director.py` executes them: every action appends timed beats to the actor's timeline, so
"walk to the desk, pull out the chair, sit, pick up the book, open it, turn the page, react with surprise" is one continuous
performance with the same character, the same book and no teleporting. If the actions are too long for the narration they are played
faster; if the checks find abrupt changes the blends are doubled and the scene is re-planned.

## Extending it

- **New pose:** one line in `engine/library.py`, for example `legacy.static("thumbs_up", ra=(70, 165))`. Angles are screen degrees (0 down, 90 right, 180 up). Animated poses use `legacy.cycle(...)`. Add the name to a group in `GROUPS`.
- **New action:** a function decorated with `@act("name")` in `engine/actions.py`. Use `B(c, A, name, duration, pose=..., ik={...})` to add beats, `A.perf.express(...)` for faces, `P.set_phase(...)` / `P.anim(...)` for props. Reach targets are specs such as `("prop", id, "grip")`, `("body", "head", dx, dy)`, `("actor", id, "neck", dx, dy)`, or `("fn", callable)` for moving targets.
- **New prop:** a `@spec("name", grips=..., solid=..., surface=...)` draw function in `engine/props.py`.
- **New outfit, hairstyle, accessory:** `OUTFITS` / `_draw_hair` / `_draw_hat` in `engine/character.py`.
- **New expression:** one dict of parameters in `engine/face.py`.
- **New scene:** an `s_<name>` function in `pipeline/scenes.py`.

Preview anything with `python main.py --sheets` (pose, expression, outfit and scene PNGs) and check regressions with
`python tests/run_battery.py`.

## Honest limits of this first version

- Poses live in the 2D screen plane. Side and back views change the head, hair, face and body width, but a walk cycle is a side-view cycle and some front-view gestures do not foreshorten when the body turns. A true 3D rig would fix this.
- Turning through the front view flips the character's facing, which can pop on asymmetric poses.
- IK covers arms and legs. There is no spine IK, and "look at" is head tilt plus eye direction, not a full neck solve.
- Crawling and climbing are keyframed cycles, so their feet can slide a little. Throwing, catching, pushing and helping are first-pass.
- Characters share one depth plane. Overlapping characters (a hug) can hide each other's limbs.
- Unnatural-movement detection is limited to abrupt changes and over-bent joints; it does not judge style. Repetition detection looks at repeated actions, not near-duplicate motion.
- The LLM director makes the final call on staging, so weak plans (an action on an object that is not on stage) are reported in `quality.json` rather than silently fixed.
