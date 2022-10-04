import json
from telethon import events
import re
import vars
import asyncio
from dombot.monsters import r 

vpb_regex = re.compile(r"Guild Warehouse: \d+", flags=re.M)
REDIS_KEY = "vpb_threshold"

def pre_check(e):
    if e.forward is None or e.chat_id not in [vars.BOT_POD_GRP, vars.D0MiNiX]:
        return False

    if e.forward.from_id is None or not hasattr(e.forward.from_id, "user_id"):
        return False

    if not e.forward.from_id.user_id == vars.CW_BOT:
        return False

    return True

@events.register(events.NewMessage(pattern=vpb_regex, forwards=True, func=lambda e: pre_check(e)))
async def calc_vpbs(event):
    global r, REDIS_KEY
    vpb_thresholds = json.loads(r.get(REDIS_KEY))
    vpbs = re.findall(r"(p\d+.+$)", event.raw_text, flags=re.M)
    string = ""

    for vpb in vpbs:
        c = re.match(r"(p\d+)\s(.+?)\sx\s(\d+)", vpb, flags=re.M)
        code = c.group(1)
        name = c.group(2)
        qty = int(c.group(3))

        if code in vpb_thresholds.keys():
            diff = qty - vpb_thresholds[code]
            if diff < 0:
                string += f"`{code}` " + name + f" [{qty}/{vpb_thresholds[code]}, {diff}]" + '\n'

    if string:
        await event.respond("**Missing VPBs:**\n" + string)
    
    raise events.StopPropagation
