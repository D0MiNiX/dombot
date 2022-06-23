from telethon import events, Button
import pytz
import flag as fg
import re
from pytz import country_timezones
from functions import check_db_error, cleanup, command_with_args, command
from datetime import datetime, timedelta
from database import Database
import vars
import arrow
import demoji


data = dict(country_timezones.items())
timezones_dict = {}
data_for_callback = {}
tz_data = dict(country_timezones.items())
tz_pattern = r"^(.+)\s+([+-]\d{4})\s*(\S{1,3})*"
tz_reply_pattern = r"^([+-]\d{4})\s*(\S{1,3})*"
tz_db = r"dombot/rss/databases/sqlite/timezones.db"


for key, value in data.items():
    timezones_dict[key] = {}
    for region in data[key]:
        utc_off = datetime.now(pytz.timezone(region)).strftime('%z')
        timezones_dict[key][region] = utc_off


def get_time(offset):
    hrs = int(offset[0:3])
    mins = int(offset[3:5])
    actual_time = arrow.utcnow().shift(hours=hrs, minutes=mins)
    return actual_time


@vars.bot.on(events.CallbackQuery)
async def add_duplicate(event):

    global data_for_callback

    data = event.data.decode("UTF-8")

    if not re.match(r"^(yes_tz|no_tz)$", data):
        return

    if event.chat_id not in data_for_callback and not event.message_id in data_for_callback[event.chat_id]:
        return

    if data == "yes_tz":
        db = Database(tz_db)
        query = db.insert(event.chat_id, data_for_callback[event.chat_id][event.message_id])
        await check_db_error(db, event, query)
        await event.edit("Added.")
        db.close_all()
    else:
        await event.edit("Oke, not adding.")

    del data_for_callback[event.chat_id][event.message_id]

    if not data_for_callback[event.chat_id]:
        del data_for_callback[event.chat_id]

    raise events.StopPropagation


@events.register(events.NewMessage())
async def tz_handler(event):

    global data_for_callback

    if command_with_args(event.raw_text, "set_tz"):

        name, tz, cnt_flag = "", "", ""

        db = Database(tz_db)
        
        query = db.query(f"CREATE TABLE IF NOT EXISTS `{event.chat_id}` (name VARCHAR(256), offset VARCHAR(10), "
                            "flag VARCHAR(10))")

        await check_db_error(db, event, query)

        query = db.select(f"SELECT name FROM `{event.chat_id}`")
        await check_db_error(db, event, query)
        res = [k[0] for k in query] if query is not None else []

        if event.is_reply:
            data = event.raw_text.split(" ", 1)
            data = re.match(tz_reply_pattern, data[1])

            if data is None:
                await event.reply("Invalid arguments.\nUsage while replying: `/set_tz <tz> <flag>(optional)`.")
                raise events.StopPropagation

            message = await event.get_reply_message()
            name = message.sender.first_name + ((" " + message.sender.last_name) if \
                                                    message.sender.last_name else "")
            tz = data.group(1)
            text = data.group(2)
            emo = []

            if text is not None:
                emo = demoji.findall_list(text, desc=False)

            if len(emo) >= 1:
                emo = emo[0]
            elif not emo:
                await cleanup(event, db, "Please give one emo as last argument.")

            if name in res:
                buttons_layout = [Button.inline("Yes", b"yes_tz"), Button.inline("Nope", b"no_tz")]
                msg_id = await event.reply("Name already exist. Still want to add?", buttons=buttons_layout)

                if event.chat_id not in data_for_callback:
                    data_for_callback[event.chat_id] = {}

                data_for_callback[event.chat_id][msg_id.id] = [name, tz, emo]
                raise events.StopPropagation
        else:
            data = event.raw_text.split(" ", 1)
            data = re.match(tz_pattern, data[1])

            if data is None:
                await event.reply("Invalid arguments.\nUsage: `/set_tz <name> <tz> <flag>(optional)`.")
                raise events.StopPropagation

            name = data.group(1)
            tz = data.group(2)
            text = data.group(3)
            emo = []

            if text is not None:
                emo = demoji.findall_list(text, desc=False)

            if len(emo) >= 1:
                emo = emo[0]
            elif not emo:
                await cleanup(event, db, "Please give one emo as last argument.")

            if name in res:
                buttons_layout = [Button.inline("Yes", b"yes_tz"), Button.inline("Nope", b"no_tz")]
                msg_id = await event.reply("Name already exist. Still want to add?", buttons=buttons_layout)

                if event.chat_id not in data_for_callback:
                    data_for_callback[event.chat_id] = {}
                
                data_for_callback[event.chat_id][msg_id.id] = [name, tz, emo]
                raise events.StopPropagation

        query = db.insert(event.chat_id, [name, tz, emo])
        await check_db_error(db, event, query)
        await cleanup(event, db, "Added.")

    elif command_with_args(event.raw_text, "rm_tz"):
        args = event.raw_text.split(" ", 1)
        db = Database(tz_db)
        query = db.query(f"DELETE FROM `{event.chat_id}` WHERE name='{args[1]}'", row_count=True)
        await check_db_error(db, event, query)

        if not query:
            await cleanup(event, db, "No player with that name is recorded in this chat.")
        else:
            await cleanup(event, db, "Deleted.")

    elif command_with_args(event.raw_text, "get_tz"):

        args = event.raw_text.split(" ", 1)

        if len(args) <= 1:
            await event.reply("Please give country code too.")
            raise events.StopPropagation

        country_code = args[1].upper()
        country = fg.dflagize(country_code)
        country = country.replace(':', '')

        if timezones_dict.get(country) is not None:
            regions = [f"[`{k}`] `{j}`" for (j, k) in timezones_dict[country].items()]
            regions = '\n'.join(regions)
            await event.reply(f"Available regions for {country}.\n{regions}")
            raise events.StopPropagation
        else:
            await event.reply("Incorrect country code.")
            raise events.StopPropagation

    elif command(event.raw_text, "times"):
        db = Database(tz_db)
        query = db.select(f"SELECT * FROM `{event.chat_id}`")

        err = await check_db_error(db, event, query, return_error=True)

        if err and err.startswith("no such table"):
            await cleanup(event, db, "No times recorded for any user in this chat.")

        result = [k for k in query]
        result = sorted(result, key=lambda x: x[0])
        times_list = []

        for res in result:
            name = res[0]
            offset = res[1]
            flag = res[2]
            current_time = get_time(offset)
            times_list.append((flag, name, current_time))

        if times_list:
            times_list = sorted(times_list, key=lambda x: x[2] or x[1])
            string = ""
            for item in times_list:
                string += item[2].format("HH:mm") + " " + (item[0] if item[0] else "❓") + " " + item[1] + "\n"
            await cleanup(event, db, string)
        else:
            await cleanup(event, db, "No times recorded for any user in this chat.")
