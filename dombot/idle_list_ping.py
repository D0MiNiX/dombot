from telethon import events
import re
import vars as bot_vars
import asyncio
from datetime import datetime

MAX_PIN_PER_MSG = 4
MAX_FWD_TIME = 360
msg_pattern = re.compile(r"#\d+ \S+\d+ \[\S+\] \w+\d+$", flags=re.M)
CW_BOT = 408101137
CW_ELITE_BOT = 5233916499

def calc_rem_time(fwd_time):
    time_format = '%m-%d-%y %H:%M:%S'
    utc_time = datetime.strptime(datetime.utcnow().strftime(time_format), time_format)
    event_time = datetime.strptime(fwd_time.strftime(time_format), time_format)
    diff = utc_time - event_time
    elapsed_secs = int(diff.total_seconds())
    return elapsed_secs

def check_forward(e):
    global msg_pattern

    if not msg_pattern.search(e.raw_text):
        return False

    if e.forward is None:
        return False

    if e.forward.from_id is None or not hasattr(e.forward.from_id, "user_id"):
        return False

    if e.forward.from_id.user_id == CW_BOT or e.forward.from_id.user_id == CW_ELITE_BOT:
        return True
    else:
        return False

@events.register(events.NewMessage(func=lambda e: check_forward(e)))
async def id_list(event):

    seconds_passed = calc_rem_time(event.message.forward.date)

    if seconds_passed > MAX_FWD_TIME:
        await event.reply("Please send fresh roster (not more than 5 mins old).")
        raise events.StopPropagation

    match = re.findall(r".+?\[🛌\].+(\d{9,})$", event.raw_text, re.M)
    ten_dig_match = re.findall(r".+?\[🛌\].+(\d{10,})$", event.raw_text, re.M)
    user_names = list(map(lambda x: int(x), match))
    ten_user_names = list(map(lambda x: int(x), ten_dig_match))
    ok_list = []

    for x in user_names:
        try:
            uname = await bot_vars.bot.get_entity(x)
            ok_list.append('@' + uname.username)
        except:
            pass

    for n in ten_user_names:
        try:
            uname = await bot_vars.bot.get_entity(n)
            ok_list.append('@' + uname.username)
        except:
            pass

    for i in range(0, len(ok_list), MAX_PIN_PER_MSG):
        await event.respond(" ".join(ok_list[i:i + MAX_PIN_PER_MSG]))
        await asyncio.sleep(0.5)

    if user_names:
        await event.respond("WAKE UP!! 🥱")

    raise events.StopPropagation
