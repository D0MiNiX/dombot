from datetime import datetime
from telethon import events, Button
import re
import vars
import asyncio
# import sqlite3 as db
from database import Database
from functions import cleanup, check_db_error

# db overview
# guild_data -> grp_id (int), guild (varchar(3)), monster (bool), ambush (bool)
# grp id tables -> user_name varchar(128), guild varchar(3), level (int)

db_path = "dombot/rss/databases/sqlite/monsters.db"
CW_BOT = 408101137 # Chatwars bot
grp_ids_for_hunts = []
ambush_text = "It's an ambush"
monster_text = "You met some hostile creatures"
MAX_GUILDS_PER_GROUP = 3
MONSTERS_TIMEOUT = 180
AMBUSH_TIMEOUT = 360
MAX_REP_FWD_TIME = 3600
MAX_CONSIDERABLE_LEVEL = 100
MAX_PIN_PER_MSG = 4
SQ_MAX_SEL = 500    # sqlite max "compound select" statement limit
MONSTER_MODIFIERS = ["armored", "enraged", "toughness", "poison bottles", "remedy bottles", "golem minion"]


# Sender username check
async def get_sender_username(event):
    if event.sender.username is not None:
        sender_uname = '@' + event.sender.username
        return sender_uname
    else:
        await cleanup(event, text="Yo, please set a username first.")


# Calculate low level and high level for mobs
def calc_limit(event):
    base_modifier = 20
    modifier_count = 0
    beasts_list = ["Boar", "Bear", "Wolf"]
    beast_counter, noobs_counter = 0, 0

    enc_lvl_list = [int(k) for k in re.findall(r"lvl\.(\d+)", event.raw_text)]
    low_level_encounter = min(enc_lvl_list)
    highest_lvl_encounter = max(enc_lvl_list)

    encounters = re.findall(r"(\d*)(?:\sx\s)*(?:Valley|Forest|Swamp|Forbidden)\s(\w+)", event.raw_text)
    encounters = list(map(lambda x: (int(x[0]) if x[0].isdigit() else 1, x[1]), encounters))

    mods = re.findall(r"╰ (.*)", event.raw_text)
    mods = [mod.strip() for split_mod in mods for mod in split_mod.split(',')]

    # Get the number of modifiers
    for mod in mods:
      if mod in MONSTER_MODIFIERS:
        modifier_count += 1

    # Get the total number of encounters and type
    for mob_level, mob_type in encounters:
        if mob_type in beasts_list:
            base_modifier = 10
            beast_counter += mob_level
        else:
            noobs_counter += mob_level

    total_encounters = noobs_counter + beast_counter
    high_bar = (low_level_encounter + 10)
    low_bar = highest_lvl_encounter - (base_modifier - (5 * (total_encounters - 1)) - (modifier_count * 2))
    low_bar = max(low_bar, 1)
    return low_bar, high_bar


# Invalid username check for adding, removing players
def check_user_name(user_name):
    if (user_name[0] != '@') or (user_name[1].isdigit()) or (len(user_name) < 5):
        return False
    else:
        return True


# If the message is forwarded from cw and the event occured in the grps that are registered for fights
def pre_check_fight_fwds(e):
    if e.forward is None:
        return False

    if e.forward.from_id is None or not hasattr(e.forward.from_id, "user_id"):
        return False

    if e.forward.from_id.user_id == CW_BOT and e.chat_id in grp_ids_for_hunts and \
        (ambush_text in e.raw_text or monster_text in e.raw_text):
        return True
    else:
        return False


def pre_check_reports_fwds(e):
    if e.forward is None:
        return False

    if e.forward.from_id is None or not hasattr(e.forward.from_id, "user_id"):
        return False

    if e.forward.from_id.user_id == CW_BOT and  e.chat_id in grp_ids_for_hunts and \
            "Your result on the battlefield:" in e.raw_text:
        return True
    else:
        return False


def calc_rem_time(fwd_time):
    time_format = '%m-%d-%y %H:%M:%S'
    utc_time = datetime.strptime(datetime.utcnow().strftime(time_format), time_format)
    event_time = datetime.strptime(fwd_time.strftime(time_format), time_format)
    diff = utc_time - event_time
    elapsed_secs = int(diff.total_seconds())
    return elapsed_secs


def calc_passed_time(time_elapsed, timeout):
    total_sec = time_elapsed - timeout
    days = int(total_sec / (24 * 3600))
    total_sec = total_sec % (24 * 3600)
    hours = int(total_sec / 3600)
    total_sec %= 3600
    minutes = int(total_sec / 60)
    total_sec %= 60
    seconds = total_sec
    late_by = ((str(days) + (' RemDay ' if days == 1 else ' days ')) if days != 0 else '') + \
             ((str(hours) + (' hour ' if hours == 1 else ' hours ')) if hours != 0 else '') + \
             ((str(minutes) + (' minute ' if minutes == 1 else ' minutes '))
              if minutes != 0 else '') + str(seconds) + (' second' if seconds == 1 else ' seconds')
    return late_by


def user_exists(db, user_name):
    grp_ids_split = [grp_ids_for_hunts[k:k + SQ_MAX_SEL] for k in range(0, len(grp_ids_for_hunts), SQ_MAX_SEL)]
    query = ""
    UNION_ALL = " UNION ALL "
    user_names_list = []

    for grp_id_list in grp_ids_split:
        for grp_id in grp_id_list:
            query += f"SELECT user_name FROM `{grp_id}`{UNION_ALL}"
        query = query[:-len(f"{UNION_ALL}")]
        user_names = db.select(query)
        for x in user_names:
            user_names_list.append(x[0])
        query = ""

    if user_name in user_names_list:
        return True
    else:
        return False


@events.register(events.NewMessage(incoming=True, forwards=True, func=lambda e: pre_check_fight_fwds(e)))
async def fight(event):

    event_text = event.raw_text
    sender_username = await get_sender_username(event)
    db = Database(db_path)
    dummy_exception_list = []
    mob_level = re.findall(r"lvl\.(\d+)", event_text)
    mob_level = [int(k) for k in mob_level]
    average_level = round(sum(mob_level) / len(mob_level))
    min_mob_level = min(mob_level)
    seconds_passed = calc_rem_time(event.message.forward.date)
    guild = db.select_single(f"SELECT guild FROM `{event.chat_id}` WHERE user_name='{sender_username}'")
    await check_db_error(db, event, guild, dummy_exception_list)
    new_line = "\n"

    if dummy_exception_list:
        await cleanup(event, db)

    if ambush_text in event_text:
        champ_level, champ_text = None, None
        min_level = (min_mob_level - 11) if min_mob_level >= 11 else 0
        max_level = (min_mob_level + 11)

        if seconds_passed > AMBUSH_TIMEOUT:
            await cleanup(event, db, "OMG! What were you doing? Baking 🍪? You are late by " +
                                        calc_passed_time(seconds_passed, AMBUSH_TIMEOUT) + " 😳.")

        minutes = int((AMBUSH_TIMEOUT - seconds_passed) / 60)
        seconds = (AMBUSH_TIMEOUT - seconds_passed) % 60
        time_remaining = 	"**{} ".format(minutes) + ("minute" if minutes == 1 else "minutes") + \
                            " {} ".format(seconds) + ("second" if seconds == 1 else "seconds") + \
                            "** remaining!!"

        # Check if the guild has ambush enabled
        ambush_enabled = db.select_single(f"SELECT ambush FROM guild_data WHERE guild='{guild}'")
        await check_db_error(db, event, guild)

        if not ambush_enabled:
            await cleanup(event, db)

        ping_list = db.select(f"SELECT user_name, level FROM `{event.chat_id}` WHERE guild='{guild}'")
        await check_db_error(db, event, ping_list)

        if "Forbidden Champion" in event.raw_text:
            champ_level = int(re.findall(r"Forbidden Champion lvl\.(\d+)", event.raw_text)[0])
            max_level = (champ_level - 7) if champ_level >= 7 else champ_level
            min_level = 0
            champ_text = "**⚜️😳ITS AN CHAAAAAAMPPP!!!!!😱⚜️**"

        # Get only the usernames in that level range
        ping_list = [k[0] for k in ping_list if min_level < k[1] < max_level and sender_username != k[0]]

        if not ping_list:
            await cleanup(event, db, "Sorry mate! No players found in that level range. Fingers crossed 🤞.")

        fight_text = re.findall(r"/fight_.*", event.raw_text)[0]

        markup = vars.bot.build_reply_markup(
            Button.url("Fight", url="t.me/share/url?url=" + fight_text))

        for i in range(0, len(ping_list), MAX_PIN_PER_MSG):
            await event.respond(" ".join(ping_list[i:i + MAX_PIN_PER_MSG]))
            await asyncio.sleep(0.5)

        text =  f"Average level of the mob is approx. **{average_level}**.{new_line}" + \
                f"{time_remaining}{new_line}" + \
                f"Good luck ☺️👍.{new_line}" + \
                (f"{champ_text}" if champ_text else "")

        mob = await event.respond(text, buttons=markup)
        db.close_all()

        print("Caught ambush fight in:", event.chat_id)
        await vars.bot.pin_message(entity=event.chat_id, message=mob.id)
        await asyncio.sleep(AMBUSH_TIMEOUT - seconds_passed)
        await vars.bot.unpin_message(entity=event.chat_id, message=mob.id)
        raise events.StopPropagation

    elif monster_text in event_text:
        if seconds_passed > MONSTERS_TIMEOUT:
            await cleanup(event, db, "OMG! What were you doing? Baking 🍪? You are late by " +
                                        calc_passed_time(seconds_passed, MONSTERS_TIMEOUT) + " 😳.")

        # Check if the guild has monster enabled
        monster_enabled = db.select_single(f"SELECT monster FROM guild_data WHERE guild='{guild}'")
        await check_db_error(db, event, guild)

        if not monster_enabled:
            await cleanup(event, db)

        ping_list = db.select(f"SELECT user_name, level FROM `{event.chat_id}` WHERE guild='{guild}'")
        await check_db_error(db, event, ping_list)

        # Get only the usernames in that level range
        low, high = calc_limit(event)
        ping_list = [k[0] for k in ping_list if low <= k[1] <= high and sender_username != k[0]]

        if not ping_list:
            await cleanup(event, db, "Sorry mate! No players found in that level range. Fingers crossed 🤞.")

        fight_text = re.findall(r"/fight_.*", event.raw_text)[0]

        markup = vars.bot.build_reply_markup(
            Button.url("Fight", url="t.me/share/url?url=" + fight_text))

        for i in range(0, len(ping_list), MAX_PIN_PER_MSG):
            await event.respond(" ".join(ping_list[i:i + MAX_PIN_PER_MSG]))
            await asyncio.sleep(0.5)

        print("Caught monster fight in:", event.chat_id) 
        await cleanup(event, db)

    db.close_all()


@events.register(events.NewMessage(
    pattern=r"^(/reg_hunt)\s+\w{{0,3}}$|^(/reg_hunt{})\s+\w{{0,3}}$".format(vars.bot_tag), 
    func=lambda e: not e.is_private))
async def register(event):
    sender_username = await get_sender_username(event)
    dummy_exception_list = []
    data = re.split(r"\s+", event.raw_text)
    db = Database(db_path)
    successful_registeration = ("Successfully registered. Your level is set to 1 by default.\n"
                                "Please change it using `/level <level>` if it is not correct.\n"
                                "Also add new members using `/add <username> <level>`.")

    if len(data) != 2:
        await cleanup(event, db, "Invalid. Usage: `/register <guild_tag>`.")

    # Create table if doesn't exist
    query = "CREATE TABLE IF NOT EXISTS guild_data (grp_id INTEGER, guild VARCHAR(3) PRIMARY KEY, \
                monster BOOLEAN, ambush BOOLEAN)"
    res = db.query(query)
    await check_db_error(db, event, res)

    # Check if the sender already exists somewhere else
    if user_exists(db, sender_username):
        await cleanup(event, db, "You can't register, you are already in the ping list somewhere.")

    # Get the guild tag, and check for the validity
    guild_tag = data[1].upper()

    if not re.match(r"[A-Z0-9]+$", guild_tag) or len(guild_tag) > 3:
        await cleanup(event, db, "Invalid guild tag.")

    # Get the count of same grp_ids, more then 3 guilds per grp not allowed
    query = f"SELECT COUNT(grp_id) from guild_data WHERE grp_id={event.chat_id}"
    count = db.select_single(query)
    await check_db_error(db, event, res)

    if count >= MAX_GUILDS_PER_GROUP:
        await cleanup(event, db, "Can't register more than 3 guilds per group.")

    # Create a table of chat_id to hold all the usernames, their levels and the guild names
    query = (f"CREATE TABLE IF NOT EXISTS `{event.chat_id}` (user_name VARCHAR(128) PRIMARY KEY,"
                "guild VARCHAR(3), level INT)")
    res = db.query(query)
    await check_db_error(db, event, res)

    # Insert the given data, keeping monster hunt on by default and ambush off
    res = db.insert("guild_data", [event.chat_id, guild_tag, 1, 0])
    await check_db_error(db, event, res, dummy_exception_list)

    if dummy_exception_list:
        await cleanup(event, db, "Guild is already registered for hunts.")

    # Insert the values into the table
    # user_name = sender username, guild = guild_tag, level = 1
    res = db.insert(event.chat_id, [sender_username, guild_tag, 1])
    await check_db_error(db, event, res)

    grp_ids_for_hunts.append(event.chat_id)
    await cleanup(event, db, successful_registeration)


@events.register(events.NewMessage(pattern=r"^\/\S+.*", func=lambda e: e.chat_id in grp_ids_for_hunts))
async def commands(event):

    event_text = event.raw_text

    if re.match(r"^(/ambush)\s\w+$|^(/monster)\s\w+$|^(/ambush{})\s\w+$|^(/monster{})\s\w+$"
                        .format(vars.bot_tag, vars.bot_tag), event.raw_text):
        sender_username = await get_sender_username(event)
        data = event_text.split(" ")
        db = Database(db_path)
        user_does_not_exist = []
        type = data[0].replace("/","")
        option = data[1].lower()

        query = f"SELECT guild FROM `{event.chat_id}` WHERE user_name='{sender_username}'"
        guild = db.select_single(query)
        await check_db_error(db, event, guild, user_does_not_exist)

        if user_does_not_exist:
            # you have no power here gif
            await event.reply(file="BAADBQADvQIAAkdJQFVWh485H6rPRwI")
            await event.respond("...which means you are not in the ping list.")
            db.close_all()
            raise events.StopPropagation

        if option == "on":
            query = f"UPDATE guild_data SET {type}=1 WHERE guild='{guild}'"
        elif option == "off":
            query = f"UPDATE guild_data SET {type}=0 WHERE guild='{guild}'"
        else:
            await cleanup(event, db, f"Incorrect options provided. Usage: `/{type} <option>`, \
                                where option = \"on\" or \"off\".")

        res = db.query(query)
        await check_db_error(db, event, res)
        await event.reply(f"{type.title()} pings turned {option} successfully.")
        await cleanup(event, db)

    elif re.match(r"^(/view_pings)$|^(/view_pings{})$".format(vars.bot_tag), event.raw_text):
        sender_username = await get_sender_username(event)
        db = Database(db_path)
        user_does_not_exist = []

        query = f"SELECT guild FROM `{event.chat_id}` WHERE user_name='{sender_username}'"
        guild = db.select_single(query)
        await check_db_error(db, event, guild, user_does_not_exist)

        if user_does_not_exist:
            # you have no power here gif
            await event.reply(file="BAADBQADvQIAAkdJQFVWh485H6rPRwI")
            await event.respond("...whichs mean you are not in the ping list.")
            await cleanup(event, db)

        query = f"SELECT user_name, level FROM `{event.chat_id}` WHERE guild='{guild}' ORDER BY level DESC"
        res = db.select(query)
        await check_db_error(db, event, res)
        user_names = [k for k in res]
        user_names = "\n".join(map(lambda e: f"`{e[0]}, {e[1]}`", user_names))
        nl = "\n"
        await event.reply(f"**{guild}** members being pinged in this group:{nl}{user_names}")
        await cleanup(event, db)

    # Add players with level
    elif re.match(r"^(/add_hunter)\s+\S+\s+\d+$|^(/add_hunter{})\s+\S+\s+\d+$".format(vars.bot_tag), \
                    event.raw_text):
        sender_username = await get_sender_username(event)
        db = Database(db_path)
        data = re.split(r"\s+", event.raw_text)
        dummy_exception_list = []

        if len(data) != 3:
            await cleanup(event, db, "Invalid. Usage `/add <user_name> <level>`.")
        
        user_name = data[1]
        level = data[2]

        if not check_user_name(user_name):
            await cleanup(event, db, "Invalid username.")

        if not level.isdigit():
            await cleanup(event, db, "Invalid level.")
        else:
            level = int(level)
            if level > MAX_CONSIDERABLE_LEVEL:
                await cleanup(event, db, f"Really? Level {level}? 😳")

        if user_exists(db, user_name):
            await cleanup(event, db, "The player is already in ping list somewhere.")

        query = f"SELECT guild FROM `{event.chat_id}` WHERE user_name='{sender_username}'"
        guild = db.select_single(query)
        await check_db_error(db, event, guild, dummy_exception_list)

        if dummy_exception_list:
            # you have no power here gif
            await event.reply(file="BAADBQADvQIAAkdJQFVWh485H6rPRwI")
            await event.reply("...which means you are not in the ping list.")
            await cleanup(event, db)

        res = db.insert(event.chat_id, [user_name, guild, level])
        await check_db_error(db, event, res, dummy_exception_list)

        if dummy_exception_list:
            await cleanup(event, db, "Player already exists.")

        await event.reply(r"Added. \o/")
        await cleanup(event, db)

    # Remove players
    elif re.match(r"^(/rm_hunter)\s+\S+$|^(/rm_hunter{})\s+\S+$".format(vars.bot_tag), event.raw_text):
        sender_username = await get_sender_username(event)
        db = Database(db_path)
        data = re.split(r"\s+", event.raw_text)
        dummy_exception_list = []

        if len(data) != 2:
            await cleanup(event, db, "Invalid. Usage `/rm <user_name>`.")

        user_name = data[1]

        if not check_user_name(user_name):
            await cleanup(event, db, "Invalid username.")

        query = f"SELECT guild FROM `{event.chat_id}` WHERE user_name='{sender_username}'"
        guild = db.select_single(query)
        await check_db_error(db, event, guild, dummy_exception_list)

        if dummy_exception_list:
            # you have no power here gif
            await event.reply(file="BAADBQADvQIAAkdJQFVWh485H6rPRwI")
            await event.reply("...which means you are not in the ping list.")
            await cleanup(event, db)

        res = db.delete(event.chat_id, "user_name", user_name)
        await check_db_error(db, event, res)

        if not res:
            await cleanup(event, db, "Player doesn't exists.")

        # If that was the last member of the guild, delete from the guild_data
        query = f"SELECT COUNT(user_name) FROM `{event.chat_id}` WHERE guild='{guild}'"
        count = db.select_single(query)
        await check_db_error(db, event, count)

        if count == 0:
            db.query(f"DELETE FROM guild_data WHERE guild='{guild}'")
        
        # If that was the last member of the guild and the group, delete the related table
        query = f"SELECT COUNT(user_name) FROM `{event.chat_id}`"
        count = db.select_single(query)
        await check_db_error(db, event, count)

        if count == 0:
            db.query(f"DROP TABLE `{event.chat_id}`")

        await event.reply(r"Removed. \o/")
        await cleanup(event, db)

    # Set level
    elif re.match(r"^(/level)(\s+\S+)*(\s+\d+)$|^(/level{})(\s+\S+)*(\s+\d+)$"
                        .format(vars.bot_tag), event.raw_text):
        sender_username = await get_sender_username(event)
        db = Database(db_path)
        data = re.split(r"\s+", event.raw_text)
        user_name, level, dummy_exception_list = None, None, []

        if len(data) == 1:
            await cleanup(event, db, "Invalid. Usage:\n- For yourself: `/level <level>`\n"
                            "- For someone else: `/level <user_name> <level>`")
        elif len(data) == 2:
            level = data[1]
        elif len(data) == 3:
            user_name = data[1]
            level = data[2]

        if user_name and not check_user_name(user_name):
            await cleanup(event, db, "Invalid user name.")

        if not level.isdigit():
            await cleanup(event, db, "Invalid parameter.")
        else:
            level = int(level)
            if level > MAX_CONSIDERABLE_LEVEL:
                await cleanup(event, db, f"Really? Level {level}? 😳")

        query = f"SELECT guild FROM `{event.chat_id}` WHERE user_name='{sender_username}'"
        guild = db.select_single(query)
        await check_db_error(db, event, guild, dummy_exception_list)

        if dummy_exception_list:
            # you have no power here gif
            await event.reply(file="BAADBQADvQIAAkdJQFVWh485H6rPRwI")
            await event.reply("...which means you are not in the ping list.")
            await cleanup(event, db)

        if user_name:
            query = f"UPDATE `{event.chat_id}` SET level={level} WHERE user_name='{user_name}'"
        else:
            query = f"UPDATE `{event.chat_id}` SET level={level} WHERE user_name='{sender_username}'"

        res = db.query(query, row_count=True)
        await check_db_error(db, event, res)

        if not res:
            await cleanup(event, db, "Player doesn't exist.")

        await event.reply(f"Level of `{user_name if user_name else sender_username}` "  
                            f"set to {level} successfully.")
        await cleanup(event, db)


@events.register(events.NewMessage(incoming=True, forwards=True, func=lambda e: pre_check_reports_fwds(e)))
async def reports(event):
    sender_username = await get_sender_username(event)
    db = Database(db_path)
    detected_level, player_level, dummy_exception_list = None, None, []

    try:
        detected_level = int(re.findall(r"(?:Lvl\:\s)(\d+)", event.raw_text)[0])
    except:
        await cleanup(event, db)

    seconds_passed = calc_rem_time(event.message.forward.date)

    if seconds_passed > MAX_REP_FWD_TIME:
        await cleanup(event, db, "Old report, make sure its not older than an hour.")

    query = f"SELECT level FROM `{event.chat_id}` WHERE user_name='{sender_username}'"
    player_level = db.select_single(query)
    await check_db_error(db, event, player_level, dummy_exception_list)

    if dummy_exception_list:
        await cleanup(event, db)

    query = f"SELECT guild FROM `{event.chat_id}` WHERE user_name='{sender_username}'"
    guild = db.select_single(query)
    await check_db_error(db, event, guild, dummy_exception_list)

    if dummy_exception_list:
        await cleanup(event, db)

    if player_level != detected_level:
        query = f"UPDATE `{event.chat_id}` SET level={detected_level} WHERE user_name='{sender_username}'"
        res = db.query(query, row_count=True)
        if res:
            await cleanup(event, db, f"Updated new level of `{sender_username}` "
                            f"to {detected_level} successfully.")
    else:
        await cleanup(event, db)


# Fill the list of all the registered groups
db = Database(db_path)
query = "SELECT DISTINCT grp_id FROM guild_data"
res = db.select(query)
if isinstance(res, Exception):
    err = res.args[0]
    if "no such table" in err:
        pass
    else:
        vars.bot.send_message(vars.D0MiNiX, f"{err}")
else:
    grp_ids_for_hunts = [k[0] for k in res]

db.close_all()
