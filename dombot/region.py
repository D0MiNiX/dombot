from telethon import events
from database import Database
from functions import cleanup, check_db_error
from functools import partial
from functions import command, command_with_args
from pytz import country_timezones


@events.register(events.NewMessage(pattern=r"^/\w+"))
async def tz_region(event):

    cmd = partial(command, event.raw_text)
    cmd_with_args = partial(command_with_args, event.raw_text)

    if cmd_with_args("set_region"):
        regions_db = r"dombot/rss/databases/sqlite/regions.db"
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

        db = Database(regions_db)
        query = f"CREATE TABLE IF NOT EXISTS regions (user_id INTEGER PRIMARY KEY, region VARCHAR(256))"
        db.query(query)
        await check_db_error(db, event, query)

        db.delete("regions", "user_id", event.sender.id)
        err = db.insert("regions", [event.sender.id, region])
        await check_db_error(db, event, err)

        await cleanup(event, db, "Saved region.")

    elif cmd("rm_region"):
        regions_db = r"dombot/rss/databases/sqlite/regions.db"
        db = Database(regions_db)
        rows = db.delete("regions", "user_id", event.sender.id)
        if not isinstance(rows, Exception):
            if rows == 0:
                await cleanup(event, db, "You have not set your region yet.")
            else:
                await cleanup(event, db, "Your region has been removed. UTC will be considered as default.")
        else:
            await cleanup(event, db, "Something went wrong accesing database.")
