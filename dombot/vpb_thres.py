import json
from telethon import events
import re
import vars
import asyncio
from dombot.monsters import r 

vpb_regex = re.compile(r"Guild Warehouse: \d+", flags=re.M)
REDIS_KEY = "vpb_threshold"

code_name_dict = {
    "p01": "Vial of Rage",
    "p02": "Potion of Rage",
    "p03": "Bottle of Rage",
    "p04": "Vial of Peace",
    "p05": "Potion of Peace",
    "p06": "Bottle of Peace",
    "p07": "Vial of Greed",
    "p08": "Potion of Greed",
    "p09": "Bottle of Greed",
    "p10": "Vial of Nature",
    "p11": "Potion of Nature",
    "p12": "Bottle of Nature",
    "p13": "Vial of Mana",
    "p14": "Potion of Mana",
    "p15": "Bottle of Mana",
    "p16": "Vial of Twilight",
    "p17": "Potion of Twilight",
    "p18": "Bottle of Twilight",
    "p19": "Vial of Morph",
    "p20": "Potion of Morph",
    "p21": "Bottle of Morph"
}

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
    string = ""
    available_codes = re.findall(r"(p\d+).+x\s+?(\d+.?)+$", event.raw_text, flags=re.M)
    dct = dict(available_codes)
    string = ""

    for code in vpb_thresholds.keys():
        qty = int(dct[code]) if code in dct.keys() else 0
        name = code_name_dict[code]
        diff = qty - vpb_thresholds[code]
        if diff < 0:
            string += f"`{code}` " + name + f" [{qty}/{vpb_thresholds[code]}, {diff}]" + '\n'

    if string:
        await event.respond("**Missing VPBs:**\n" + string)

    raise events.StopPropagation
