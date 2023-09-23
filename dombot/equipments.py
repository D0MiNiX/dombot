import re
from telethon import events
from datetime import datetime
from functions import command, command_with_args
import vars
from pandas_ods_reader import read_ods
import functools
import operator
from database import Database
from functions import cleanup, check_db_error
from functools import partial


GUILD_EQUIPS = "guild_equips"
GUILD_EQUIPS_BAG = "guild_equips_bag"
SHARE_URL = "t.me/share/url?url="
db_path = "dombot/rss/databases/sqlite/equipments.db"
path = "dombot/rss/equips/gears.ods"
sheet_idx = 1
reader = read_ods(path, sheet_idx)
names = [k for k in reader["Name"]]
timeFormat = '%m-%d-%y %H:%M:%S'
ATK = 0
DEF = 1
MAX_TIME = 600  # seconds

slot_dict = {
    "weapon" : ATK,
    "offhand" : ATK,
    "helmet" : DEF,
    "gloves" : DEF,
    "armor" : DEF,
    "boots" : DEF,
    "ring" : None,
    "amulet" : None,
    "cloak" : ATK,
    "misc" : None
}

quality = {
    0: "N",
    1: "E",
    2: "D",
    3: "C",
    4: "B",
    5: "A",
    6: "SE",
    7: "SD",
    8: "SC",
    9: "SB",
    10: "SA"
}

tiers = {
    0: "🐣",
    1: "📕",
    2: "📗",
    3: "📘",
    4: "📙",
    5: "📒"
}


def calculate_quality(ench, attack, defence, atk_or_def, rdr):
    common_atk = int(reader[rdr].Attack.values[0])
    common_defc = int(reader[rdr].Defense.values[0])
    tier = int(reader[rdr].Tier.values[0])
    pattern = reader[rdr].Ench_Ptn.values[0]

    if isinstance(pattern, float):
        pattern = str(int(pattern))
    if pattern == "0":
        return "?!", tier

    ench_pattern = [int(k) for k in pattern.split(',')]

    sum = 0
    ind = 0
    for _ in range(0, ench):
        sum += ench_pattern[ind]
        ind += 1
        if ind > len(ench_pattern) - 1:
            ind = 0

    without_enchantment = (attack if atk_or_def == ATK else defence) - sum
    qual = without_enchantment - (common_atk if atk_or_def == ATK else common_defc)
    try:
        if qual < 0:
            return "X", tier
        else:
            return quality[qual], tier
    except KeyError:
        return "!!!", tier


# provide a list of weapons (equips) and fills the list (location) with quality and tier
def fetch_data(location, equips):
    for weapons in equips:
        rgx = re.compile(r"^(\W*\+\d+)*(?:\s)*(.*?)(?:\s)*([+]\d+\S+.*)*$", flags=re.M)
        weapon = rgx.findall(weapons)
        wpn_lower = weapon[0][1].lower()
        split_stats = weapon[0][2].split(" ")
        ench = int(re.findall(r"\d+", weapon[0][0])[0]) if weapon[0][0] != "" else 0
        attack = 0; defence = 0; mana = 0; stamina = 0
        for x in split_stats:
            if "⚔" in x:
                attack = int(re.findall(r"\d+", x)[0])
            elif "🛡" in x:
                defence = int(re.findall(r"\d+", x)[0])
            elif "💧" in x:
                mana = int(re.findall(r"\d+", x)[0])
            elif "🔋" in x:
                stamina = int(re.findall(r"\d+", x)[0])

        engraved_weapon = check_for_engraved_weapon(wpn_lower)
        rdr = (reader.Name == wpn_lower) if engraved_weapon == "" else (reader.Name == engraved_weapon)
        vals = reader[rdr].Type.values
        qual = "..."
        type = "misc"

        if len(vals) > 0:
            type = vals[0]
            atk_or_def = slot_dict[type]

            # offhand shields
            if "shield" in wpn_lower or "shield" in engraved_weapon:
                atk_or_def = 1

            qual, tier = calculate_quality(ench, attack, defence, atk_or_def, rdr)
            location.append(f"({qual}) " + " ".join(weapon[0]).strip())
        else:
            location.append(f"({qual}) " + " ".join(weapon[0]).strip())


def check_for_engraved_weapon(wpn):
    engraved_weapon = ""
    if wpn not in names:
        for x in names:
            if x != wpn and x in wpn:
                engraved_weapon = x
    return engraved_weapon


async def save_to_db(user_id, user_name, location, loc, ov_stats="", event=None):
    db = Database(db_path)
    qry = db.query(f"CREATE TABLE IF NOT EXISTS {GUILD_EQUIPS} (user_id INTEGER PRIMARY KEY, user_name VARCHAR, weapon VARCHAR, offhand VARCHAR, helmet VARCHAR, gloves VARCHAR, armor VARCHAR, boots VARCHAR, ring VARCHAR, amulet VARCHAR, cloak VARCHAR, misc VARCHAR, stats VARCHAR, last_updated VARCHAR)")
    await check_db_error(db, event, qry)
    qry = db.query(f"CREATE TABLE IF NOT EXISTS {GUILD_EQUIPS_BAG} (user_id INTEGER PRIMARY KEY, user_name VARCHAR, weapon VARCHAR, offhand VARCHAR, helmet VARCHAR, gloves VARCHAR, armor VARCHAR, boots VARCHAR, ring VARCHAR, amulet VARCHAR, cloak VARCHAR, misc VARCHAR, stats VARCHAR, last_updated VARCHAR)")
    await check_db_error(db, event, qry)

    weapon_and_type = {}
    rgx = re.compile(r"^(\W*\+\d+)*(?:\s)*(.*?)(?:\s)*([+]\d+\S+.*)*$", flags=re.M)
    for lines in rgx.findall(location):
        weapon_name = lines[1]
        wpn_lower = weapon_name.lower()
        engraved_weapon = check_for_engraved_weapon(wpn_lower)
        rdr = (reader.Name == wpn_lower) if engraved_weapon == "" else (reader.Name == engraved_weapon)
        vals = reader[rdr].Type.values
        type = "misc"
        final_string = ""

        if len(vals) > 0:
            type = vals[0]
        elif "ring" in wpn_lower:
            type = "ring"
        elif "amulet" in wpn_lower:
            type = "amulet"

        final_string = " ".join(lines)
        
        if type not in weapon_and_type.keys():
            weapon_and_type[type] = [final_string.strip()]
        else:
            weapon_and_type[type].append(final_string.strip())

    # start saving to db
    table = GUILD_EQUIPS if loc == 0 else GUILD_EQUIPS_BAG
    user_ids = [k[0] for k in db.select(f"SELECT user_id from {GUILD_EQUIPS};")]
    new_line = "\n"

    if user_id in user_ids:
        qry = db.delete(f"{table}", "user_id", user_id)
        await check_db_error(db, event, qry)

    qry = db.insert(f"{table}", [user_id, user_name, None, None, None, None, None, None, None, None, None, None, None, None])
    await check_db_error(db, event, qry)

    for key, value in weapon_and_type.items():
        val = new_line.join(value)
        
        # if single quote in value, use two single quotes to escape that
        val = val.replace("'", "''")
        qry = db.query(f"UPDATE {table} SET {key} = '{val}' WHERE user_id = {user_id}")
        await check_db_error(db, event, qry)

    if ov_stats != "":
        qry = db.query(f"UPDATE {table} SET stats = '{ov_stats}' WHERE user_id = {user_id}")
        await check_db_error(db, event, qry)

    curr_utc = datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S")
    qry = db.query(f"UPDATE {table} SET last_updated = '{curr_utc}' WHERE user_id = {user_id}")
    await check_db_error(db, event, qry)
    db.close_all()


def is_late(event_time):
    eventTime = datetime.strptime(event_time, timeFormat)
    CurrTime = datetime.utcnow().strftime(timeFormat)
    CurrTime = datetime.strptime(CurrTime, timeFormat)
    diff = CurrTime - eventTime
    if diff.total_seconds() > MAX_TIME:
        return True
    else:
        return False


@events.register(events.NewMessage(chats=[vars.D0MiNiX, vars.BOT_POD_GRP]))
async def equips(event):

    cmd = partial(command, event.raw_text)
    cmd_with_args = partial(command_with_args, event.raw_text)
    
    if event.message.forward is not None and event.message.forward.from_id.user_id == vars.CW_BOT and \
            re.match(r"^(?:🎽Equipment )(.*)", event.raw_text):
        
        if is_late(event.message.forward.date.strftime(timeFormat)):
            await event.reply("Late. Max 10 minutes.")
            raise events.StopPropagation
        
        user_id = event.sender.id; user_name = event.sender.username
        overall_stats = re.findall(r"(?:🎽Equipment )(.*)", event.raw_text)[0]
        
        equipped = \
            re.sub(r"🎽Equipment.*?\n|\n\n🎒Bag.*|\s(?<=\s)/off_.*?(?=\n)", "", \
                event.raw_text, flags=re.S).strip()
        bag = re.sub(r".*🎒Bag.*?\n|\s(?<=\s)/on_.*?(?=\n|$)", "", event.raw_text, flags=re.S).strip()

        # saving to DB according to slots
        await save_to_db(user_id, user_name, equipped, 0, overall_stats, event)
        await save_to_db(user_id, user_name, bag, 1, "", event)
        await event.reply(f"Equipments of @{user_name} stolen successfully 💃.")
        raise events.StopPropagation

    elif cmd("equips"):
        db = Database(db_path)
        qry = db.select(f"SELECT user_name FROM {GUILD_EQUIPS}")
        await check_db_error(db, event, qry)
        user_names = [("[" + k[0]+ "](" + SHARE_URL + "/eq%20" + k[0] + ")") for k in qry]
        string = ", ".join(user_names)
        await event.reply(string)
        db.close_all()
        raise events.StopPropagation

    elif cmd_with_args("eq"):
        db = Database(db_path)
        equipped = []
        bag = []
        new_line = "\n"
        user_name = event.raw_text.split(" ", 1)
        
        if not len(user_name) > 1:
            await event.reply("Give username too!")
            raise events.StopPropagation

        user_name = user_name[1]
        string = ",".join([k for k in slot_dict.keys()])

        equips = db.select(f"SELECT {string} from {GUILD_EQUIPS} WHERE user_name = '{user_name}'")
        await check_db_error(db, event, equips)
        equips = [k for k in equips][0]
        equips = list(filter(None, equips)) # removing None entries
        equips = [item.split("\n") for item in equips]
        equips = functools.reduce(operator.add, equips)
        fetch_data(equipped, equips)

        stats = db.select(f"SELECT stats from {GUILD_EQUIPS} WHERE user_name = '{user_name}'")
        await check_db_error(db, event, stats)
        stats = [k[0] for k in stats][0]

        equips = db.select(f"SELECT {string} from {GUILD_EQUIPS_BAG} WHERE user_name = '{user_name}'")
        await check_db_error(db, event, equips)
        equips = [k for k in equips][0]

        equips = list(filter(None, equips))
        equips = [item.split("\n") for item in equips]
        equips = functools.reduce(operator.add, equips)
        fetch_data(bag, equips)

        last_updated = db.select(f"SELECT last_updated FROM {GUILD_EQUIPS_BAG} WHERE user_name='{user_name}'")
        await check_db_error(db, event, last_updated)
        last_updated = [k[0] for k in last_updated][0]

        final_string = f"**Equipped: {stats}**{new_line}{new_line.join(equipped)}" + \
            f"{new_line*2}**Bag:**{new_line}{new_line.join(bag)}{new_line*2}" + \
            f"**Last updated (UTC): {last_updated}**"

        await event.reply(final_string)
        db.close_all()
        raise events.StopPropagation

    elif cmd_with_args("slot"):
        db = Database(db_path)
        usr_and_their_weapons = {}
        new_line = "\n"
        slot = event.raw_text.split(" ", 1)
        
        if len(slot) == 1:
            string = f"Please use any of the following keywords with that command.{new_line}" + \
                     f"`{', '.join(list(slot_dict.keys()))}`."
            await event.reply(string)
            raise events.StopPropagation
        else:
            slot = slot[1]

        user_name_and_weapon = db.select(f"SELECT user_name, {slot} FROM {GUILD_EQUIPS} ORDER BY user_id")
        await check_db_error(db, event, user_name_and_weapon)
        
        for stuff in user_name_and_weapon:
            qual_weapon = []
            user_name = stuff[0]
            weapon = stuff[1]
            if weapon is None:
                continue
            weapon = weapon.split("\n")
            weapon = list(filter(None, weapon))
            fetch_data(qual_weapon, weapon)
            usr_and_their_weapons[user_name] = qual_weapon

        user_name_and_weapon = db.select(f"SELECT user_name, {slot} FROM {GUILD_EQUIPS_BAG} ORDER BY user_id")
        await check_db_error(db, event, user_name_and_weapon)
        
        for stuff in user_name_and_weapon:
            qual_weapon = []
            user_name = stuff[0]
            weapon = stuff[1]
            if weapon is None:
                continue
            weapon = weapon.split("\n")
            weapon = list(filter(None, weapon))
            fetch_data(qual_weapon, weapon)
            if user_name not in usr_and_their_weapons.keys():
                usr_and_their_weapons[user_name] = qual_weapon
            else:
                usr_and_their_weapons[user_name].append("\n".join(qual_weapon))
            
        string = ""
        for key, value in usr_and_their_weapons.items():
            string += "**" + key + "**" + "\n" + "\n".join(value) + "\n\n"
        await event.reply(string)
        db.close_all()
        raise events.StopPropagation

    elif cmd("eq_legend"):
        legend = "X - Broken\n!!! - Incorrect enchantment pattern\n" + \
                 "?! - Enchantment pattern not found\nN - No quality"
        await event.reply(legend)
        raise events.StopPropagation
    
    elif cmd_with_args("eq_search"):
        db = Database(db_path)
        search = event.raw_text.split(" ", 2)
        if len(search) < 3:
            await event.reply("Please supply the proper search term.\n" + \
                              "Format - /eq_search <slot> <weapon_name>" + \
                              "For example - /eq_search weapon Champion.")
            raise events.StopPropagation
        slot = search[1]
        weapon = search[2]
        qry = f"SELECT user_name, {slot} FROM {GUILD_EQUIPS} WHERE ({slot} LIKE '%{weapon}%' OR {slot} LIKE '%{weapon.lower()}%')"
        owners = db.select(qry)
        owners = [k for k in owners]
        await check_db_error(db, event, owners)

        string = ""
        for owner in owners:
            user_name = owner[0]
            weapon = owner[1]
            string += f"**{user_name}**" + "\n" + f"{weapon}" + "\n\n"
        
        if string:
            await event.reply(string)
        else:
            await event.reply("No results found.")

        db.close_all()
        raise events.StopPropagation
