from telethon import events
import re, vars
from datetime import datetime
from dombot.monsters import r

glory_regex = re.compile(r"^.*?Glory: \d+/\d+", flags=re.S)
TARGET_GLORY = 17000
TARGET_BATTLES = 273 

def pre_check(e):
    if e.forward is None or e.chat_id != vars.D0MiNiX:
        return False

    if e.forward.from_id is None or not hasattr(e.forward.from_id, "user_id"):
        return False

    if not e.forward.from_id.user_id == vars.CW_BOT:
        return False

    return True

@events.register(events.NewMessage(pattern=glory_regex, forwards=True, func=lambda e: pre_check(e)))
async def cal_glory(event):
    target = r.get("target_glory")
    prev = r.get("previous_glory")
    battles_done = r.get("battles_done")

    if not target:
        r.set("target_glory", str(TARGET_GLORY))
        target = TARGET_GLORY

    if not prev:
        r.set("previous_glory", str(0))
        prev = 0

    if not battles_done:
        r.set("battles_done", str(0))
        battles_done = 0

    target = int(target)
    prev = int(prev)
    battles_done = int(battles_done)

    glory = re.findall(r"Glory: (\d+)/\d+", event.raw_text, flags=re.M)
    glory = int(glory[0])
    diff = target - glory
    # prev_diff = glory - prev
    battles_done += 1

    progress = round((float(glory / target) * 100), 2)
    progress_diff = round(progress - round((float(prev / target) * 100), 2), 2)
    battles_progress = round((float(battles_done / TARGET_BATTLES) * 100), 2)

    string = f"Current glory: {glory}" + '\n'
    string += f"Previous battle glory: {prev}" + '\n'

    if progress_diff > 0:
        string += f"Glory gain: {progress_diff}%"
    elif progress_diff < 0:
        string += f"Glory loss: {progress_diff}%"
    else:
        string += "No glory change!"

    string += '\n'
    string += f"Target glory: {target}" + '\n'
    string += f"Remaining glory: {diff}" + '\n'
    string += f"Total %age progress: {progress}%" + '\n'
    string += f"Season's progress (battles): {battles_done}/{TARGET_BATTLES} ({battles_progress}%)" + '\n'

    # if prev_diff > 0:
    #     perc = round((float(prev_diff / glory) * 100), 2)
    #     string += f"This battle's glory gain compared to previous one: {prev_diff} ({perc}%)"
    # elif prev_diff < 0:
    #     perc = round((float(abs(prev_diff) / glory) * 100), 2)
    #     string += f"This battle's glory loss compared to previous one: -{prev_diff} -({perc}%)"
    # else:
    #     string += "No glory difference compared to previous battle!"

    r.set("previous_glory", str(glory))
    r.set("battles_done", str(battles_done))
    await event.respond(string)
    raise events.StopPropagation
