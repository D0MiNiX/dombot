from telethon import events
from functools import partial
from functions import command, command_with_args
from pytz import country_timezones
from monsters import r

HASH_KEY = "user_region"

@events.register(events.NewMessage(pattern=r"^/\w+"))
async def tz_region(event):
    global HASH_KEY

    cmd = partial(command, event.raw_text)
    cmd_with_args = partial(command_with_args, event.raw_text)

    if cmd_with_args("set_region"):
        args = event.raw_text.split()
        args_len = len(args)

        if args_len == 1:
            await event.reply("Provide country region. You can use `/get_tz <country_code or flag>` to get the regions.")
            raise events.StopPropagation

        region = args[1]
        region_found = False
        timezone_data = dict(country_timezones.items())

        for country_code in timezone_data:
            if region in timezone_data[country_code]:
                region_found = True
                break

        if not region_found:
            await event.reply("Incorrect region. You can use `/get_tz <country_code or flag>` to get the regions.")
            raise events.StopPropagation

        ret = r.hset(HASH_KEY, str(event.sender.id), region)

        if ret > 0:
            await event.reply("Saved region.")
        else:
            await event.reply("Could not save region.")

        raise events.StopPropagation

    elif cmd("rm_region"):
        ret = r.hdel(HASH_KEY, str(event.sender.id))

        if ret > 0:
            await event.reply("Deleted region.")
        else:
            await event.reply("Could not delete region.")

        raise events.StopPropagation
