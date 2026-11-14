import sys, time, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from PIL import Image
from engine import director, actions as AC
from engine.character import Appearance
import config
size=config.LANDSCAPE
cast={"hero":Appearance("hoodie","short","brown","light",["glasses"]),
      "other":Appearance("professional","long","blond","tan",["tie"])}
def P(id,type,x,**k): return dict(id=id,type=type,x=x,**k)
cases={
 "walk/run/jog/sprint":([ "hero"],[],[("walk_to",dict(x=.8)),("run_to",dict(x=.2)),("jog_to",dict(x=.6)),("sprint_to",dict(x=.9))]),
 "poses":(["hero"],[],[("jump",{}),("dance",{}),("hop",{}),("clap",{}),("kick",{}),("punch",{}),("bow",{}),("stretch",{}),("cheer",{}),("shrug",{})]),
 "postures":(["hero"],[],[("squat",{}),("stand_up",{}),("crouch",{}),("stand_up",{}),("kneel",{}),("get_up",{}),("sit_down",{}),("stand_up",{}),("lie_down",{}),("get_up",{})]),
 "fall/crawl/climb":(["hero"],[P("lad","ladder",.7)],[("fall",{}),("get_up",{}),("crawl_to",dict(x=.5)),("stand",{}),("climb",dict(target="lad"))]),
 "bed":(["hero"],[P("bed1","bed",.35,facing=1)],[("wake_up",dict(target="bed1")),("stand_up",{}),("walk_to",dict(x=.8)),("lie_down",dict(target="bed1"))]),
 "carry/box":(["hero"],[P("box1","box",.7)],[("pick_up",dict(target="box1")),("walk_to",dict(x=.2)),("put_down",{})]),
 "throw/catch":(["hero","other"],[P("ball1","ball",.2)],[("pick_up",dict(target="ball1")),("throw",dict(x=.75)),]),
 "cook/type/write":(["hero"],[P("desk1","desk",.6),P("pot1","pot",.62,on="desk1"),P("lap","laptop",.6,on="desk1"),P("nb","notebook",.58,on="desk1")],
                    [("cook",dict(target="pot1")),("type",dict(target="lap")),("write",dict(target="nb"))]),
 "phone/eat/drink/tool":(["hero"],[P("ph","phone",.5),P("ap","apple",.6),P("cp","cup",.7),P("hm","hammer",.8)],
                    [("use_phone",dict(target="ph")),("put_down",{}),("eat",dict(target="ap")),("put_down",{}),("drink",dict(target="cp")),("put_down",{}),("use_tool",dict(target="hm"))]),
 "door/push/point":(["hero"],[P("door1","door",.85),P("bx","box",.5),P("bd","board",.2)],
                    [("point_at",dict(target="bd")),("push",dict(target="bx",x=.7)),("open_door",dict(target="door1")),("teach",dict(target="bd"))]),
 "social":(["hero","other"],[P("bk","book",.5)],[("greet",dict(target="other")),("shake_hands",dict(with_="other")),("hug",dict(target="other")),
        ("pick_up",dict(target="bk")),("hand_over",dict(target="bk",with_="other")),("argue",dict(target="other"))]),
 "emotions":(["hero"],[],[("react",dict(emotion=e)) for e in ("surprise","fear","anger","sadness","confusion","laughter","excited","embarrassment","realization","disgust")]),
}

HARD = {"collision", "out_of_frame", "detached_prop"}  # these must never appear; other issues are reported as warnings
crashes, hard = 0, 0
for name, (ch, props, acts) in cases.items():
    actions = [dict(do=do, actor="hero", **{("with" if k == "with_" else k): v for k, v in kw.items()}) for do, kw in acts]
    seg = {"scene": "room", "camera": "wide", "characters": [{"id": c, "x": (0.2 if c == "hero" else 0.8)} for c in ch],
           "props": props, "actions": actions}
    try:
        plan = director.plan_segment(size, cast, None, seg, speech=40.0, fps=12, seed=3)
        for k in range(6):
            t = plan.T * (k + 0.5) / 6
            plan.stage.render(t, k, "wide", ["hero"], plan.T, "", "x")
        bad = [i for i in plan.issues if i["type"] in HARD]
        hard += len(bad)
        warn = sorted({i["type"] for i in plan.issues} - HARD)
        print(f"{'FAIL' if bad or plan.notes else 'ok  '} {name:24s} warnings={warn} hard={[i['type'] for i in bad]} notes={plan.notes}")
    except Exception as e:
        crashes += 1
        print("CRASH", name, repr(e))
print(f"\n{len(cases)} scenarios, {crashes} crashes, {hard} hard quality failures")
sys.exit(1 if crashes or hard else 0)
