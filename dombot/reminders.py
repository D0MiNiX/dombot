import vars
import re
from telethon import events
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from pytz import utc
from database import Database
from functions import check_db_error, cleanup
from telethon.errors.rpcerrorlist import MessageIdInvalidError
from functions import command, command_with_args
from functools import partial
from datetime import datetime, timedelta
import arrow
from monsters import r
from region import HASH_KEY

HELP_FOLDER = "dombot/rss/help"
def_jobstore = SQLAlchemyJobStore(url="sqlite:///dombot/rss/databases/sqlite/reminders/jobs.db")
reminder_db_path = r"dombot/rss/databases/sqlite/reminders/reminders.db"
jobstores = {
    "default": def_jobstore
}

# Initialize and start the scheudler
scheduler = AsyncIOScheduler()
scheduler.configure(jobstores=jobstores, timezone=utc)
scheduler.start()


# only_from_db - job is removed from scheduler automatically if "date" is used as parameter
# so removal from db is only required
async def remove_job(job_id, message_info, only_from_db):
    global reminder_db_path
    if not only_from_db:
        scheduler.remove_job(job_id)
    db = Database(reminder_db_path)
    res = db.delete(message_info["chat_id"], "rem_id", job_id)
    err = await check_db_error(db, None, res, return_error=True)
    if isinstance(err, Exception):
        await vars.bot.send_message(message_info["chat_id"], 
                                    "Something went wrong deleting the reminder from database.")
    db.close_all()


async def task(msg_info, job_id):
    global reminder_db_path
    job_removed = False
    message_info = msg_info

    if message_info["forward"]:
        try:
            await vars.bot.forward_messages(message_info["chat_id"], 
                                            messages=message_info["message_id"], 
                                            from_peer=message_info["chat_id"])
        except MessageIdInvalidError:
            await vars.bot.send_message(message_info["chat_id"], "Original message was removed. " + 
                                            "Can't send the reminder.")
            if message_info["is_interval_start_time"]:
                await remove_job(job_id, message_info, True)
            else:
                await remove_job(job_id, message_info, False)
            job_removed = True
    else:
        if message_info["file_id"]:
            await vars.bot.send_message(message_info["chat_id"], file=message_info["file_id"])
        else:
            await vars.bot.send_message(message_info["chat_id"], message_info["text"])

    if not job_removed:
        if message_info["is_interval_start_time"]:
            await remove_job(job_id, message_info, True)
        elif not message_info["repeating"]:
            await remove_job(job_id, message_info, False)

    if message_info["start_time"] and not message_info["is_interval_start_time"]:
        message_info["start_time"] = False
        scheduler.modify_job(job_id, args=[message_info, job_id])


def has_time_passed(hours, mins=0, secs=0, region=False) -> bool:
    if region:
        current_time = arrow.now(tz=region)
        if hours < current_time.hour or (hours == current_time.hour and mins < current_time.minute) or \
                (hours == current_time.hour and mins == current_time.minute and secs <= current_time.second):
            return True
        else:
            return False
    else:
        current_utc = datetime.utcnow()
        if hours < current_utc.hour or (hours == current_utc.hour and mins < current_utc.minute) or \
                (hours == current_utc.hour and mins == current_utc.minute and secs <= current_utc.second):
            return True
        else:
            return False


def get_data(data_type, text):
    re_data = r".*?(\d+\.)*(\d+){}".format(data_type)
    if re.match(re_data, text):
        decimal_part = re.match(re_data, text).group(1)
        fractional_part = re.match(re_data, text).group(2)
        num = ""
        if decimal_part:
            num = decimal_part + fractional_part
        else:
            num = fractional_part
        if num.isdigit():
            return int(num)
        else:
            return float(num)
    else:
        return 0


def get_interval(interval, repeat):
    total_seconds = 0
    if re.match(r"^(\d+\.)?\d+$", interval):
        total_seconds = int(interval)
    else:
        times_list = ['w', 'd', 'h', 'mi', 's']
        data = re.findall(r"(?:\d+\.)*(?:\d+)(\D+)", interval)
        data_details =  "`w` for weeks, `d` for days, `h` for hours, `mi` for minutes, `s` for seconds. " \
                        "Interval timings will be ambiguous for years and months, and hence, " \
                        "they are not allowed for now."

        for datum in data:
            if datum not in times_list:
                return Exception(f"Invalid time provided.\nValid times are {data_details}.\nExample: 1.5w3h2.5d, "
                                    "12h50mi56s, etc. or in H:M:S, H:M or S (seconds) only format.")

        data = [get_data(k, interval) for k in times_list]
        time_map = arrow.now()._SECS_MAP    # contains dictionary like mapping of number of seconds in time period
        total_seconds = round(data[0]*time_map["week"] + data[1]*time_map["day"] + data[2]*time_map["hour"] + \
                        data[3]*time_map["minute"] + data[4]*time_map["second"])
    
    if 0 <= total_seconds < 1800 and repeat:
        return Exception("Minimum 30 minutes interval required for repeating reminders.")

    return total_seconds


def get_start_time(start_time, sender_id):
    region = False
    ret = r.hget(HASH_KEY, str(sender_id))

    if ret:
        region = ret

    start_time_t = ""

    if re.match(r"^(\d+\.)?\d+$", start_time):
        if start_time.isdigit():
            secs = int(start_time)
        else:
            secs = float(start_time)
        start_time_t = arrow.utcnow().shift(seconds=secs).format("YYYY-MM-DD HH:mm:ss")
    elif re.match(r"\d+:*\d*:*\d*$", start_time):
        hours, mins, secs = 0, 0, 0
        time = start_time.split(':')
        length = len(time)
        secs_only = False

        try:
            if length == 1:
                secs = int(time[0])
                secs_only = True
            elif length == 2:
                hours = int(time[0])
                mins = int(time[1])
            elif length == 3:
                hours = int(time[0])
                mins = int(time[1])
                secs = int(time[2])
            else:
                return Exception("Invalid time provided. Please use H:M, H:M:S or S (seconds) only format.")
        except ValueError:
            return Exception("Time cannot have string values.")

        if hours > 24 or (hours == 24 and (mins > 0 or secs > 0)) or mins > 59 or secs > 59:
            return Exception("Invalid time.")

        # If region of the user exists
        if region:
            if secs_only:
                start_time_t = f"{arrow.now(tz=region).shift(seconds=secs).to('utc').format('YYYY-MM-DD HH:mm:ss')}"
            elif has_time_passed(hours, mins, secs, region):
                now = arrow.now(tz=region).format("YYYY-MM-DD") + " " + f"{hours}:{mins}:{secs}"
                make_time = arrow.get(now, "YYYY-MM-DD H:m:s", tzinfo=region)
                start_time_t = f"{make_time.shift(days=1).to('utc').format('YYYY-MM-DD HH:mm:ss')}"
            else:
                now = arrow.now(tz=region).format("YYYY-MM-DD") + " " + f"{hours}:{mins}:{secs}"
                make_time = arrow.get(now, "YYYY-MM-DD H:m:s", tzinfo=region)
                start_time_t = f"{make_time.to('utc').format('YYYY-MM-DD HH:mm:ss')}"
        else:
            if secs_only:
                start_time_t = arrow.utcnow().shift(seconds=secs).format('YYYY-MM-DD HH:mm:ss')
            elif has_time_passed(hours, mins, secs):
                start_time_t = arrow.utcnow().shift(days=1).format('YYYY-MM-DD') + " " + f"{hours}:{mins}:{secs}"
            else:
                start_time_t = arrow.utcnow().format('YYYY-MM-DD') + " " + f"{hours}:{mins}:{secs}"
    else:
        times_list = ['y', 'mo', 'w', 'd', 'h', 'mi', 's']
        data = re.findall(r"(?:\d+\.)*(?:\d+)(\D+)", start_time)
        data_details = "`y` for year, `mo` for months, `w` for weeks, `d` for days, `h` for hours, `mi`" \
                " for minutes, `s` for seconds"

        for datum in data:
            if datum not in times_list:
                return Exception(f"Invalid time provided.\nValid times are {data_details}.\nExample: 1.5y3.2w2d, "
                                    "12h50mi56s, etc. or in H:M:S, H:M or S (seconds) only format.")

        data = [get_data(k, start_time) for k in times_list]
        current_utc = arrow.utcnow()

        try:
            shift = current_utc.shift(years=data[0], months=data[1], weeks=data[2], days=data[3], \
                                        hours=data[4], minutes=data[5], seconds=data[6])
            start_time_t = shift.format("YYYY-MM-DD HH:mm:ss")
        except ValueError:
            return Exception("Months and years have to be integers, rest is fine.")

    return start_time_t


def process_args(args, sender_id):
    args = args.split()
    args_len = len(args)
    rem_name, rem_interval, rem_start_time, rem_repeat = "", "", False, False
    is_interval_start_time = False

    if args_len == 2:
        rem_name = args[0]
        interval = args[1]
        is_interval_start_time = True
        rem_start_time = get_start_time(interval, sender_id)
    elif args_len == 3:
        rem_repeat = True
        start_time = False
        rem_name = args[0]
        interval = args[1]
        if not args[2] == "repeat":
            start_time = args[2]
        if start_time:
            rem_start_time = get_start_time(start_time, sender_id)
        rem_interval = get_interval(interval, rem_repeat)
    elif args_len == 4:
        rem_name = args[0]
        interval = args[1]
        start_time = args[2]
        if args[3] == "repeat":
            rem_repeat = True
        else:
            return Exception("Invalid arguments provided."), None, None, None, None
        rem_start_time = get_start_time(start_time, sender_id)
        rem_interval = get_interval(interval, rem_repeat)
    else:
        return Exception("Invalid number of arguments provided."), None, None, None, None

    return rem_name, rem_interval, rem_start_time, rem_repeat, is_interval_start_time


@events.register(events.NewMessage(pattern=r"^/\w+"))   # , from_users=[vars.D0MiNiX]
async def reminders(event):

    global scheduler, reminder_db_path, def_jobstore

    cmd = partial(command, event.raw_text)
    cmd_with_args = partial(command_with_args, event.raw_text)

    if cmd_with_args("resume_reminder"):
        db = Database(reminder_db_path)
        args = event.raw_text.split(" ", 1)
        dum = []
        name = ""

        if len(args) >= 2:
            name = args[1]
        else:
            await cleanup(event, db, "Please provide the name of the reminder too.")

        job_id = f"SELECT rem_id FROM `{event.chat_id}` WHERE rem_name='{name}'"
        job_id = db.select_single(job_id)
        res = await check_db_error(db, event, job_id, return_error=True)

        if res and "no such table" in res:
            await cleanup(event, db, "Reminders were never created here.")

        if dum or isinstance(job_id, Exception):
            await cleanup(event, db, "Reminder not found.")
        else:
            info = scheduler.get_job(job_id)
            message_info = info.args[0]
            if not message_info["paused"]:
                await cleanup(event, db, "Reminder is already running.")
            message_info["paused"] = False
            scheduler.resume_job(job_id)
            scheduler.modify_job(job_id, args=[message_info, job_id])

        await cleanup(event, db, "Reminder started.")

    elif cmd_with_args("pause_reminder"):
        db = Database(reminder_db_path)
        args = event.raw_text.split(" ", 1)
        dum = []
        name = ""

        if len(args) >= 2:
            name = args[1]
        else:
            await cleanup(event, db, "Please provide the name of the reminder too.")

        job_id = f"SELECT rem_id FROM `{event.chat_id}` WHERE rem_name='{name}'"
        job_id = db.select_single(job_id)
        res = await check_db_error(db, event, job_id, return_error=True)

        if res and "no such table" in res:
            await cleanup(event, db, "Reminders were never created here.")

        if dum or isinstance(job_id, Exception):
            await cleanup(event, db, "Reminder not found.")
        else:
            info = scheduler.get_job(job_id)
            message_info = info.args[0]
            if message_info["paused"]:
                await cleanup(event, db, "Reminder is already paused.")
            message_info["paused"] = True
            scheduler.pause_job(job_id)
            scheduler.modify_job(job_id, args=[message_info, job_id])

        await cleanup(event, db, "Reminder paused.")

    elif cmd("reminders"):
        db = Database(reminder_db_path)
        found = False
        n = 1
        string = ""
        dum = []
        reminders_list = f"SELECT rem_name, rem_id FROM `{event.chat_id}`"
        reminders_list = db.select(reminders_list)
        exc = await check_db_error(db, event, reminders_list, dum, return_error=True)

        if exc and "no such table" in exc:
            await cleanup(event, db, "Reminders were never created here.")

        if dum:
            await cleanup(event, db, "Reminders not found.")

        for name, rem_id in reminders_list:
            found = True
            info = scheduler.get_job(rem_id)
            rem_name = info.name
            if info.next_run_time:
                next_run_time = f"\nNext run time: {info.next_run_time.strftime('%d/%m/%y %H:%M:%S')}"
                info_time = info.next_run_time.strftime('%d/%m/%y %H:%M:%S')
                info_time = datetime.strptime(info_time, '%d/%m/%y %H:%M:%S')
                current_time = datetime.utcnow().strftime('%d/%m/%y %H:%M:%S')
                current_time = datetime.strptime(current_time, '%d/%m/%y %H:%M:%S')
                difference = info_time - current_time
                remaining_time = f"\nTime remaining: {timedelta(seconds=difference.total_seconds())}"
            else:
                next_run_time = ""
                remaining_time = ""
            message_info = info.args[0]
            start_time = message_info["start_time"]
            interval = "No"
            if message_info["repeating"]:
                interval = message_info["interval"]
                interval = timedelta(seconds=interval)
                interval = f"Every {interval}"
            will_start_on = f"Will start on {start_time}\n\n" if start_time else ""
            status = ("Running" if not message_info["paused"] else "Paused") + ("\n" if will_start_on else "\n\n")
            string +=   f"{n}. `{rem_name}`" + \
                        f"{next_run_time}{remaining_time}\nRepeating: {interval}\nStatus: {status}" + \
                        f"{will_start_on}"
            n += 1

        if not found:
            await cleanup(event, db, "Reminders not found.")

        await cleanup(event, db, string)

    elif cmd_with_args("rm_reminder"):
        db = Database(reminder_db_path)
        args = event.raw_text.split(" ", 1)
        dum = []
        name = ""

        if len(args) >= 2:
            name = args[1]
        else:
            await cleanup(event, db, "Please provide the name of the reminder too.")

        job_id = f"SELECT rem_id FROM `{event.chat_id}` WHERE rem_name='{name}'"
        job_id = db.select_single(job_id)
        res = await check_db_error(db, event, job_id, return_error=True)

        if res and "no such table" in res:
            await cleanup(event, db, "Reminders were never created here.")

        if dum or isinstance(job_id, Exception):
            await cleanup(event, db, "Reminder not found.")
        else:
            scheduler.remove_job(job_id)
            query = db.delete(event.chat_id, "rem_name", name)
            await check_db_error(db, event, query)
            await cleanup(event, db, "Reminder deleted.")

    elif cmd_with_args("set_reminder"):

        if not event.is_reply:
            await event.reply("Please reply to a message.")
            raise events.StopPropagation

        db = Database(reminder_db_path)
        query = f"CREATE TABLE IF NOT EXISTS `{event.chat_id}` (rem_name VARCHAR(64) PRIMARY KEY, " + \
                                    "rem_id VARCHAR (128))"
        res = db.query(query)
        await check_db_error(db, event, res)

        message = await event.get_reply_message()

        # Check if message contains media or is a forward
        media = hasattr(message, "media") and message.media
        forward = True if message.forward else False
        message_id = message.id
        text = message.text
        file_id = None
        chat_id = event.chat_id

        if media and not forward:
            if hasattr(message, "file") and hasattr(message.file, "id"):
                file_id = message.file.id
            else:
                forward = True

        args = event.raw_text.split(" ", 1)

        if len(args) == 2:
            args = args [1]
        else:
            f = open(f"{HELP_FOLDER}/reminders.txt")
            reminder_help = f.read()
            f.close()
            await cleanup(event, db, reminder_help)

        # Get properties
        name, interval, start_time, repeat, is_interval_start_time = process_args(args, event.sender.id)

        # Send exception if occured
        exceptions = [k for k in [name, interval, start_time, repeat] if isinstance(k, Exception)]
        if exceptions:
            await cleanup(event, db, exceptions[0].args[0])

        # Make sure lengeth of name is not greater tha 64
        if name and len(name) > 64:
            await cleanup(event, db, "Name length cant be greater than 64 characters.")
        elif not name:
            await cleanup(event, db, "Please provide a name for the reminder.")

        query = f"SELECT rem_name FROM `{event.chat_id}`"
        reminder_names = db.select(query)
        await check_db_error(db, event, res)
        reminder_names = [k[0] for k in reminder_names]

        if name in reminder_names:
            await cleanup(event, db, f"The reminder named `{name}` already exists. Please choose different name.")

        start_time_for_job_arg = start_time

        if start_time:
            start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            if start_time <= datetime.utcnow():
                start_time = False
            else:
                start_time = start_time.strftime("%d/%m/%Y %H:%M:%S")

        message_info = {
            "chat_id": chat_id, 
            "media": media, 
            "forward": forward, 
            "message_id": message_id, 
            "text": text, 
            "file_id": file_id, 
            "repeating": repeat,
            "interval": interval,
            "paused": False,
            "start_time": start_time if start_time else False,
            "is_interval_start_time": is_interval_start_time
        }

        if is_interval_start_time:
            job_info = scheduler.add_job(task, "date", run_date=start_time_for_job_arg, args=[None, None], 
                                            name=name)
        else:
            job_info = scheduler.add_job(task, "interval", seconds=interval, args=[None, None], 
                                            start_date=start_time_for_job_arg, name=name)

        scheduler.modify_job(job_info.id, args=[message_info, job_info.id])

        res = db.insert(event.chat_id, [name, job_info.id])
        dum = []
        await check_db_error(db, event, res, dum)

        if dum:
            scheduler.remove_job(job_info.id)
            await cleanup(event, db, "Error adding reminder.")

        await cleanup(event, db, "Reminder added successfully.")
