import redis, json
import subprocess
from datetime import datetime
from telethon import events, Button
import re
import vars
import asyncio
from database import Database

HASH_KEY = "cw_monster_ambush"
CWE_HASH_KEY = "cwe_monster_ambush"

HASH_FIELD = "guild_data"
DFLT_LVL = 25
REDIS_ON = False

grp_ids_for_hunts = []
cwe_grp_ids_for_hunts = []

MAX_CONSIDERABLE_LEVEL = 100
CW_BOT = 408101137 # Chatwars bot
CW_ELITE_BOT = 5233916499
MAX_REP_FWD_TIME = 3600
AMBUSH_TIMEOUT = 360
MAX_PIN_PER_MSG = 4
MONSTERS_TIMEOUT = 180
ambush_text = "It's an ambush"
monster_text = "You met some hostile creatures"
MONSTER_MODIFIERS = ["armored", "enraged", "toughness", "poison bottles", "remedy bottles", "golem minion"]

r = redis.Redis(decode_responses=True)

def redis_status():
    global r
    try:
        r.ping()
        return True
    except:
        return False

def redis_run(redis_server):
    try:
        print("Waiting for 2 seconds to check if the server is up or not.")
        redis_server.wait(2)
        print("Server still not running. Please check manually.")
        return False
    except subprocess.TimeoutExpired:
        print("Timed out waiting on redis-server. Server is running!")
        return True

def load_group_ids():
    global grp_ids_for_hunts, cwe_grp_ids_for_hunts

    # CW
    ret = r.hget(HASH_KEY, HASH_FIELD)
    if ret:
        grp_ids_for_hunts = [int(k) for k in json.loads(ret)]

    # CWE
    ret = r.hget(CWE_HASH_KEY, HASH_FIELD)
    if ret:
        cwe_grp_ids_for_hunts = [int(k) for k in json.loads(ret)]

# Start the redis-server if not started
if not redis_status():
    print(f"Couldn't connect to redis server! Trying to run the server using `redis-server` command.")
    output = subprocess.Popen(["redis-server"], stdout=subprocess.DEVNULL)
    print(output)
    if redis_run(output):
        load_group_ids()
else:
    load_group_ids()

async def get_sender_username(event):
    if event.sender.username is not None:
        sender_uname = '@' + event.sender.username
        return sender_uname
    else:
        await event.reply("Yo, please set a username first.")
        raise events.StopPropagation

@events.register(events.NewMessage(
    pattern=r"^(/reg_hunt)$|^(/reg_hunt{})$|^(/reg_hunt_cwe)$|^(/reg_hunt_cwe{})$".format(vars.bot_tag, vars.bot_tag),
    func=lambda e: not e.is_private))
async def register(event):
    global r, HASH_KEY, CWE_HASH_KEY, HASH_FIELD

    if not redis_status():
        await event.respond("DB server is not up! Please feel free to annoy @D0MiNiX.")
        raise events.StopPropagation

    cw_type = ""
    data = {}

    if event.raw_text.endswith("cwe"):
        cw_type = "elite"
    else:
        cw_type = "int"

    hash_key = HASH_KEY if cw_type == "int" else CWE_HASH_KEY

    group_id = str(event.chat_id)
    ret = r.hget(hash_key, HASH_FIELD)
    grp_id = []

    if ret:
        data = json.loads(ret)
        grp_id = data.keys()

    if group_id not in grp_id:
        data[group_id] = [1, 1]
        r.hset(hash_key, HASH_FIELD, json.dumps(data))
    else:
        await event.reply("Group is already registered for the hunts!")
        raise events.StopPropagation

    sender_username = await get_sender_username(event)
    data.clear()
    data[sender_username] = DFLT_LVL
    r.hset(hash_key, group_id, json.dumps(data))
    r.bgsave()

    if cw_type == "int":
        grp_ids_for_hunts.append(event.chat_id)
    else:
        cwe_grp_ids_for_hunts.append(event.chat_id)

    await event.reply("Group registered for hunts successfully. Please set your level using `/level <your level>`. I have set it to 25.\nPings for both ambush and monster hunts are turned on. If you prefer to disable them, use `/monster off` or `/ambush off`.")
    raise events.StopPropagation

@events.register(events.NewMessage(pattern=r"^\/\S+.*", func=lambda e: e.chat_id in grp_ids_for_hunts or e.chat_id in cwe_grp_ids_for_hunts))
async def commands(event):
    global r
    event_text = event.raw_text

    if re.match(r"^(/ambush)\s\w+$|^(/monster)\s\w+$|^(/ambush{})\s\w+$|^(/monster{})\s\w+$".format(vars.bot_tag, vars.bot_tag) + r"^|(/ambush_cwe)\s\w+$|^(/monster_cwe)\s\w+$|^(/ambush_cwe{})\s\w+$|^(/monster_cwe{})\s\w+$"
                        .format(vars.bot_tag, vars.bot_tag), event.raw_text):
        if not redis_status():
            await event.respond("DB server is not up! Please feel free to annoy @D0MiNiX.")
            raise events.StopPropagation

        sender_username = await get_sender_username(event)
        data = event_text.split(" ")
        change_type = data[0].replace("/", "")
        option = data[1].lower()
        users_data = {}

        cw_type = ""
        if data[0].endswith("cwe"):
            cw_type = "elite"
        else:
            cw_type = "int"

        hash_key = HASH_KEY if cw_type == "int" else CWE_HASH_KEY

        ret = r.hget(hash_key, str(event.chat_id))
        users_list = []

        if ret:
            users_data = json.loads(ret)
            users_list = users_data.keys()

        if sender_username not in users_list:
            await event.reply("You're not in the ping list!")
            raise events.StopPropagation

        if option == "on":
            ret = r.hget(hash_key, HASH_FIELD)
            toggle_hunt = json.loads(ret)
            stored_val = toggle_hunt[str(event.chat_id)]
            toggle_hunt[str(event.chat_id)] = [1 if change_type == "monster" else stored_val[0],
                                               1 if change_type == "ambush" else stored_val[1]]
            r.hset(hash_key, HASH_FIELD, json.dumps(toggle_hunt))
            r.bgsave()
        elif option == "off":
            ret = r.hget(hash_key, HASH_FIELD)
            toggle_hunt = json.loads(ret)
            stored_val = toggle_hunt[str(event.chat_id)]
            toggle_hunt[str(event.chat_id)] = [0 if change_type == "monster" else stored_val[0],
                                               0 if change_type == "ambush" else stored_val[1]]
            r.hset(hash_key, HASH_FIELD, json.dumps(toggle_hunt))
            r.bgsave()
        else:
            await event.reply(f"Incorrect options provided. Usage: `/{change_type} <option>`, where option = \"on\" or \"off\".")
            raise events.StopPropagation

        await event.reply("Toggled successfully.")
        raise events.StopPropagation

    # Add players with level
    elif re.match(r"^(/add_hunter)\s+\S+\s+\d+$|^(/add_hunter{})\s+\S+\s+\d+$".format(vars.bot_tag) + r"|^(/add_hunter_cwe)\s+\S+\s+\d+$|^(/add_hunter_cwe{})\s+\S+\s+\d+$".format(vars.bot_tag), event.raw_text):
        if not redis_status():
            await event.respond("DB server is not up! Please feel free to annoy @D0MiNiX.")
            raise events.StopPropagation

        sender_username = await get_sender_username(event)
        data = re.split(r"\s+", event.raw_text)

        if len(data) != 3:
            await event.reply("Invalid. Usage `/add_hunter <user_name> <level>`.")

        cw_type = ""
        if data[0].endswith("cwe"):
            cw_type = "elite"
        else:
            cw_type = "int"

        hash_key = HASH_KEY if cw_type == "int" else CWE_HASH_KEY

        user_name = data[1]
        level = data[2]

        if not level.isdigit():
            await event.reply("Invalid level.")
            raise events.StopPropagation
        else:
            level = int(level)
            if level > MAX_CONSIDERABLE_LEVEL:
                await event.reply(f"Really? Level {level}? 😳")

        if not user_name.startswith('@'):
            user_name = '@' + user_name

        ret = r.hget(hash_key, str(event.chat_id))

        if ret:
            users_data = json.loads(ret)
            users_list = users_data.keys()

        if sender_username not in users_list:
            await event.reply("You're not in the ping list!")
            raise events.StopPropagation

        if user_name in users_list:
            await event.reply("User already exist in the ping list!")
            raise events.StopPropagation

        users_data[user_name] = level
        r.hset(hash_key, str(event.chat_id), json.dumps(users_data))
        r.bgsave()
        await event.reply(r"Added. \o/")
        raise events.StopPropagation

    # Remove players
    elif re.match(r"^(/rm_hunter)\s+\S+$|^(/rm_hunter{})\s+\S+$".format(vars.bot_tag) + r"|^(/rm_hunter_cwe)\s+\S+$|^(/rm_hunter_cwe{})\s+\S+$".format(vars.bot_tag), event.raw_text):
        if not redis_status():
            await event.respond("DB server is not up! Please feel free to annoy @D0MiNiX.")
            raise events.StopPropagation

        sender_username = await get_sender_username(event)
        data = re.split(r"\s+", event.raw_text)
        users_list = []

        if len(data) != 2:
            await event.reply("Invalid. Usage: `/rm <user_name>`.")
            raise events.StopPropagation

        cw_type = ""
        if data[0].endswith("cwe"):
            cw_type = "elite"
        else:
            cw_type = "int"

        hash_key = HASH_KEY if cw_type == "int" else CWE_HASH_KEY

        user_name = data[1]

        if not user_name.startswith('@'):
            user_name = '@' + user_name

        ret = r.hget(hash_key, str(event.chat_id))

        if ret:
            users_data = json.loads(ret)
            users_list = users_data.keys()

        if sender_username not in users_list:
            await event.reply("You're not in the ping list!")
            raise events.StopPropagation

        if user_name not in users_list:
            await event.reply("User doesn't exist in the ping list!")
            raise events.StopPropagation

        del users_data[user_name]
        r.hset(hash_key, str(event.chat_id), json.dumps(users_data))
        r.bgsave()
        await event.reply(r"Removed. \o/")
        raise events.StopPropagation

    # Set level
    elif re.match(r"^(/level)(\s+\S+)*(\s+\d+)$|^(/level{})(\s+\S+)*(\s+\d+)$".format(vars.bot_tag) + r"|^(/level_cwe)(\s+\S+)*(\s+\d+)$|^(/level_cwe{})(\s+\S+)*(\s+\d+)$".format(vars.bot_tag), event.raw_text):
        if not redis_status():
            await event.respond("DB server is not up! Please feel free to annoy @D0MiNiX.")
            raise events.StopPropagation

        sender_username = await get_sender_username(event)
        data = re.split(r"\s+", event.raw_text)
        user_name, level = "", ""
        users_list = []

        cw_type = ""
        if data[0].endswith("cwe"):
            cw_type = "elite"
        else:
            cw_type = "int"

        hash_key = HASH_KEY if cw_type == "int" else CWE_HASH_KEY

        if len(data) == 1:
            await event.reply("Invalid. Usage:\n- For yourself: `/level <level>`\n"
                                "- For someone else: `/level <user_name> <level>`")
            raise events.StopPropagation
        elif len(data) == 2:
            level = data[1]
        elif len(data) == 3:
            user_name = data[1]
            level = data[2]

        if not level.isdigit():
            await event.reply("Invalid parameter.")
            raise events.StopPropagation
        else:
            level = int(level)
            if level > MAX_CONSIDERABLE_LEVEL:
                await event.reply(f"Really? Level {level}? 😳")

        if not user_name:
            user_name = sender_username

        if not user_name.startswith('@'):
            user_name = '@' + user_name

        ret = r.hget(hash_key, str(event.chat_id))

        if ret:
            users_data = json.loads(ret)
            users_list = users_data.keys()

        if sender_username not in users_list:
            await event.reply("You're not in the ping list!")
            raise events.StopPropagation

        if user_name not in users_list:
            await event.reply("User doesn't exist in the ping list!")
            raise events.StopPropagation

        users_data[user_name] = level
        r.hset(hash_key, str(event.chat_id), json.dumps(users_data))
        r.bgsave()
        await event.reply(r"Level changed. \o/")
        raise events.StopPropagation

    elif re.match(r"^(/view_pings)$|^(/view_pings{})$".format(vars.bot_tag) + r"|^(/view_pings_cwe)$|^(/view_pings_cwe{})$".format(vars.bot_tag), event.raw_text):
        if not redis_status():
            await event.respond("DB server is not up! Please feel free to annoy @D0MiNiX.")
            raise events.StopPropagation

        cw_type = ""
        users_list = []
        if event.raw_text.endswith("cwe"):
            cw_type = "elite"
        else:
            cw_type = "int"

        hash_key = HASH_KEY if cw_type == "int" else CWE_HASH_KEY

        sender_username = await get_sender_username(event)
        ret = r.hget(hash_key, str(event.chat_id))

        if ret:
            users_data = json.loads(ret)
            users_list = users_data.keys()

        if sender_username not in users_list:
            await event.reply("You're not in the ping list!")
            raise events.StopPropagation

        new_line = '\n'
        ping_list = new_line.join(list(map(lambda x: f"`{x[0]}, {x[1]}`", users_data.items())))
        await event.respond(ping_list)
        raise events.StopPropagation

def pre_check_reports_fwds(e):
    if e.forward is None:
        return False

    if e.forward.from_id is None or not hasattr(e.forward.from_id, "user_id"):
        return False

    if ((e.forward.from_id.user_id == CW_BOT and e.chat_id in grp_ids_for_hunts) or \
        (e.forward.from_id.user_id == CW_ELITE_BOT and e.chat_id in cwe_grp_ids_for_hunts)) and \
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

@events.register(events.NewMessage(incoming=True, forwards=True, func=lambda e: pre_check_reports_fwds(e)))
async def reports(event):
    sender_username = await get_sender_username(event)
    detected_level, player_level = None, None
    cw_type = ""
    users_list = []

    seconds_passed = calc_rem_time(event.message.forward.date)

    if seconds_passed > MAX_REP_FWD_TIME:
        await event.reply("Old report, make sure its not older than an hour.")
        raise events.StopPropagation

    if event.forward.from_id.user_id == CW_BOT:
        cw_type = "int"
    else:
        cw_type = "elite"

    hash_key = HASH_KEY if cw_type == "int" else CWE_HASH_KEY

    try:
        detected_level = int(re.findall(r"(?:Lvl\:\s)(\d+)", event.raw_text)[0])
    except:
        raise events.StopPropagation

    ret = r.hget(hash_key, str(event.chat_id))

    if ret:
        users_data = json.loads(ret)
        users_list = users_data.keys()

    if sender_username not in users_list:
        raise events.StopPropagation

    player_level = int(users_data[sender_username])

    if player_level != detected_level:
        users_data[sender_username] = detected_level
        r.hset(hash_key, str(event.chat_id), json.dumps(users_data))
        r.bgsave()
        await event.respond(f"Updated new level of `{sender_username}` "
                            f"to {detected_level} successfully.")

    raise events.StopPropagation

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

# If the message is forwarded from cw and the event occured in the grps that are registered for fights
def pre_check_fight_fwds(e):
    if e.forward is None:
        return False

    if e.forward.from_id is None or not hasattr(e.forward.from_id, "user_id"):
        return False

    if ((e.forward.from_id.user_id == CW_BOT and e.chat_id in grp_ids_for_hunts) or \
        (e.forward.from_id.user_id == CW_ELITE_BOT and e.chat_id in cwe_grp_ids_for_hunts)) and \
        (ambush_text in e.raw_text or monster_text in e.raw_text):
        return True
    else:
        return False

@events.register(events.NewMessage(incoming=True, forwards=True, func=lambda e: pre_check_fight_fwds(e)))
async def fight(event):

    event_text = event.raw_text
    sender_username = await get_sender_username(event)
    mob_level = re.findall(r"lvl\.(\d+)", event_text)
    mob_level = [int(k) for k in mob_level]
    average_level = round(sum(mob_level) / len(mob_level))
    min_mob_level = min(mob_level)
    seconds_passed = calc_rem_time(event.message.forward.date)
    new_line = "\n"
    cw_type = ""

    if event.forward.from_id.user_id == CW_BOT:
        cw_type = "int"
    else:
        cw_type = "elite"

    hash_key = HASH_KEY if cw_type == "int" else CWE_HASH_KEY

    if ambush_text in event_text:
        champ_text, ping_list = "", []
        min_level = (min_mob_level - 11) if min_mob_level >= 11 else 0
        max_level = (min_mob_level + 11)

        if seconds_passed > AMBUSH_TIMEOUT:
            await event.reply("OMG! What were you doing? Baking 🍪? You are late by " +
                                calc_passed_time(seconds_passed, AMBUSH_TIMEOUT) + " 😳.")
            raise events.StopPropagation

        minutes = int((AMBUSH_TIMEOUT - seconds_passed) / 60)
        seconds = (AMBUSH_TIMEOUT - seconds_passed) % 60
        time_remaining = 	"**{} ".format(minutes) + ("minute" if minutes == 1 else "minutes") + \
                            " {} ".format(seconds) + ("second" if seconds == 1 else "seconds") + \
                            "** remaining!!"

        # Check if the guild has ambush enabled
        ret = r.hget(hash_key, HASH_FIELD)

        if ret:
            fight_type = json.loads(ret)
            if not fight_type[str(event.chat_id)][1]:
                raise events.StopPropagation

        if "Forbidden Champion" in event.raw_text:
            champ_level = int(re.findall(r"Forbidden Champion lvl\.(\d+)", event.raw_text)[0])
            max_level = (champ_level - 7) if champ_level >= 7 else champ_level
            min_level = 0
            champ_text = "**⚜️😳ITS AN CHAAAAAAMPPP!!!!!😱⚜️**"

        ret = r.hget(hash_key, str(event.chat_id))

        if ret:
            ping_list = json.loads(ret)
            ping_list = [k for k, v in ping_list.items() if min_level < v < max_level]
            if not ping_list: 
                await event.reply("Sorry mate! No players found in that level range. Fingers crossed 🤞.")
                raise events.StopPropagation
        else:
            raise events.StopPropagation

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

        print(f"[{cw_type}] Caught ambush fight in:", event.chat_id)

        try:
            await vars.bot.pin_message(entity=event.chat_id, message=mob.id)
            await asyncio.sleep(AMBUSH_TIMEOUT - seconds_passed)
            await vars.bot.unpin_message(entity=event.chat_id, message=mob.id)
        except:
            raise events.StopPropagation

        raise events.StopPropagation

    elif monster_text in event_text:
        ping_list = []
        if seconds_passed > MONSTERS_TIMEOUT:
            await event.reply("OMG! What were you doing? Baking 🍪? You are late by " +
                               calc_passed_time(seconds_passed, MONSTERS_TIMEOUT) + " 😳.")
            raise events.StopPropagation

        # Check if the guild has monster enabled
        ret = r.hget(hash_key, HASH_FIELD)

        if ret:
            fight_type = json.loads(ret)
            if not fight_type[str(event.chat_id)][0]:
                raise events.StopPropagation

        ret = r.hget(hash_key, str(event.chat_id))

        if ret:
            ping_list = json.loads(ret)
        else:
            raise events.StopPropagation

        # Get only the usernames in that level range
        low, high = calc_limit(event)
        ping_list = [k for k, v in ping_list.items() if low <= v <= high and sender_username != k]

        if not ping_list: 
            await event.reply("Sorry mate! No players found in that level range. Fingers crossed 🤞.")
            raise events.StopPropagation

        fight_text = re.findall(r"/fight_.*", event.raw_text)[0]

        markup = vars.bot.build_reply_markup(
            Button.url("Fight", url="t.me/share/url?url=" + fight_text))

        for i in range(0, len(ping_list), MAX_PIN_PER_MSG):
            await event.respond(" ".join(ping_list[i:i + MAX_PIN_PER_MSG]))
            await asyncio.sleep(0.5)

        print(f"[{cw_type}] Caught monster fight in:", event.chat_id)
        raise events.StopPropagation
