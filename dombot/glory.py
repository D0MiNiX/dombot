from telethon import events
import re, vars
from datetime import datetime
from dombot.monsters import r

glory_regex = re.compile(r"^.*?Glory: \d+/\d+", flags=re.S)
TARGET_GLORY = 17000

def pre_check(e):
    if e.forward is None or e.chat_id not in [vars.BOT_POD_GRP, vars.D0MiNiX]:
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

    if not target:
        r.set("target_glory", str(TARGET_GLORY))
        target = TARGET_GLORY

    if not prev:
        r.set("previous_glory", str(0))
        prev = 0

    target = int(target)
    prev = int(prev)

    glory = re.findall(r"Glory: (\d+)/\d+", event.raw_text, flags=re.M)
    glory = int(glory[0])
    diff = target - glory
    prev_diff = glory - prev

    progress = round((float(glory / target) * 100), 2)
    progress_diff = progress - round((float(prev / target) * 100), 2)
    string = f"Current glory: {glory}" + '\n'
    string += f"Previous battle glory: {prev}" + '\n'
    string += (f"Glory gain compared to previous battle: {progress_diff}%" \
               if progress_diff >= 0 else f"Glory loss compared to previous battle: {progress_diff}%") + '\n'
    string += f"Target glory: {target}" + '\n'
    string += f"Remaining glory: {diff}" + '\n'
    string += f"Total %age progress: {progress}%" + '\n' + '\n'

    if prev_diff > 0:
        perc = round((float(prev_diff / glory) * 100), 2)
        string += f"This battle's glory gain compared to previous one: {prev_diff} ({perc}%)"
    elif prev_diff < 0:
        perc = round((float(abs(prev_diff) / glory) * 100), 2)
        string += f"This battle's glory loss compared to previous one: -{prev_diff} -({perc}%)"
    else:
        string += "No glory difference compared to previous battle!"

    r.set("previous_glory", str(glory))
    await event.respond(string)
    raise events.StopPropagation
