import re
from telethon import events
from datetime import datetime
from functions import Command, DbQuery
import vars, psycopg2
from pandas_ods_reader import read_ods
import functools
import operator

GUILD_EQUIPS = "guild_equips"
GUILD_EQUIPS_BAG = "guild_equips_bag"
SHARE_URL = "t.me/share/url?url="

path = "dombot/rss/equips/gears.ods"
sheet_idx = 1
reader = read_ods(path, sheet_idx)
names = [k for k in reader["Name"]]
timeFormat = '%m-%d-%y %H:%M:%S'

ATK = 0
DEF = 1

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
            # tiers[tier] + " " + 
            location.append(f"({qual}) " + " ".join(weapon[0]).strip())
        else:
            # string = ""
            # if "ring" in wpn_lower:
            #     string = "💍 "
            # elif "amulet" in wpn_lower:
            #     string = "🧿 "
            # elif "torch" in wpn_lower:
            #     string = "🔦 "
            # elif "bell" in wpn_lower:
            #     string = "🔔 "
            # elif "basket" in wpn_lower:
            #     string = "🧺 "
            # elif "bag" in wpn_lower:
            #     string = "🎒 "
            # elif "arrow" in  wpn_lower:
            #     string = "🏹 "
            # elif "bottle" in wpn_lower:
            #     string = "🍼 "
            # elif "jar" in wpn_lower:
            #     string = "🔋 "
            # else:
            #     string = "❓ "
            location.append(f"({qual}) " + " ".join(weapon[0]).strip())


def check_for_engraved_weapon(wpn):
    engraved_weapon = ""
    if wpn not in names:
        for x in names:
            if x != wpn and x in wpn:
                engraved_weapon = x
    return engraved_weapon


def save_to_db(user_id, user_name, location, loc, ov_stats=""):
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
    user_ids = [k[0] for k in DbQuery(f"SELECT user_id from {GUILD_EQUIPS};")]
    new_line = "\n"

    if user_id in user_ids:
        DbQuery(f"DELETE FROM {table} WHERE user_id = {user_id};")

    DbQuery(f"INSERT INTO {table}(user_id, user_name) VALUES({user_id}, '{user_name}');")

    for key, value in weapon_and_type.items():
        DbQuery(f"UPDATE {table} SET {key} = $${new_line.join(value)}$$ WHERE user_id = {user_id};")
    
    if ov_stats != "":
        DbQuery(f"UPDATE {table} SET stats = '{ov_stats}' WHERE user_id = {user_id};")

    curr_utc = datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S")
    DbQuery(f"UPDATE {table} SET last_updated = '{curr_utc}' WHERE user_id = '{user_id}';")


def is_late(event_time):
    eventTime = datetime.strptime(event_time, timeFormat)
    CurrTime = datetime.utcnow().strftime(timeFormat)
    CurrTime = datetime.strptime(CurrTime, timeFormat)
    diff = CurrTime - eventTime
    if diff.total_seconds() > 600:
        return True
    else:
        return False


@events.register(events.NewMessage(chats=[vars.D0MiNiX, vars.BOT_POD_GRP]))
async def equips(event):

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
        save_to_db(user_id, user_name, equipped, 0, overall_stats)
        save_to_db(user_id, user_name, bag, 1)
        await event.reply(f"Equipments of @{user_name} stolen successfully 💃.")
        raise events.StopPropagation
    
    elif Command(event.raw_text, "/equips"):
        query = DbQuery(f"SELECT user_name FROM {GUILD_EQUIPS} ORDER BY user_id;")
        user_names = [("[" + k[0]+ "](" + SHARE_URL + "/eq%20" + k[0] + ")") for k in query]
        string = ", ".join(user_names)
        await event.reply(string + ".")
        raise events.StopPropagation

    elif Command(event.raw_text, "/eq"):
        equipped = []
        bag = []
        new_line = "\n"
        user_name = event.raw_text.split(" ", 1)[1]
        string = ",".join([k for k in slot_dict.keys()])
        
        equips = DbQuery(f"SELECT {string} from {GUILD_EQUIPS} WHERE user_name = '{user_name}';")[0]
        equips = list(filter(None, equips)) # removing None entries
        equips = [item.split("\n") for item in equips]
        equips = functools.reduce(operator.add, equips)
        fetch_data(equipped, equips)
        
        stats = DbQuery(f"SELECT stats from {GUILD_EQUIPS} WHERE user_name = '{user_name}';")[0][0]
        
        equips = DbQuery(f"SELECT {string} from {GUILD_EQUIPS_BAG} WHERE user_name = '{user_name}';")[0]
        equips = list(filter(None, equips))
        equips = [item.split("\n") for item in equips]
        equips = functools.reduce(operator.add, equips)
        fetch_data(bag, equips)

        last_updated = DbQuery(f"SELECT last_updated FROM {GUILD_EQUIPS_BAG} WHERE user_name='{user_name}';")[0][0]

        final_string = f"**Equipped: {stats}**{new_line}{new_line.join(equipped)}" + \
            f"{new_line*2}**Bag:**{new_line}{new_line.join(bag)}{new_line*2}" + \
            f"**Last updated (UTC): {last_updated}**"

        await event.reply(final_string)
        raise events.StopPropagation

    elif Command(event.raw_text, "/slot"):
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

        user_name_and_weapon = DbQuery(f"SELECT user_name, {slot} FROM {GUILD_EQUIPS} ORDER BY user_id;")
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

        user_name_and_weapon = DbQuery(f"SELECT user_name, {slot} FROM {GUILD_EQUIPS_BAG} ORDER BY user_id;")
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
        raise events.StopPropagation

    elif event.raw_text == "/eq_legend":
        legend = "X - Broken\n!!! - Incorrect enchantment pattern\n" + \
                 "?! - Enchantment pattern not found\nN - No quality"
        await event.reply(legend)
        raise events.StopPropagation
    
    elif Command(event.raw_text, "/eq_search"):
        search = event.raw_text.split(" ", 2)
        if len(search) < 3:
            await event.reply("Please supply the proper search term.\n" + \
                              "Format - /eq_search <slot> <weapon_name>" + \
                              "For example - /eq_search weapon Champion.")
            raise events.StopPropagation
        slot = search[1]
        weapon = search[2]
        owners = DbQuery(f"SELECT user_name, {slot} FROM {GUILD_EQUIPS} WHERE {slot} " + \
                         f"SIMILAR TO '%{weapon}%|%{weapon.lower()}%';")
        string = ""
        for owner in owners:
            user_name = owner[0]
            weapon = owner[1]
            string += f"**{user_name}**" + "\n" + f"{weapon}" + "\n\n"
        await event.reply(string)
        raise events.StopPropagation
