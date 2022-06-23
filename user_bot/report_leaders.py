from telethon import events
import re
from vars import bot, BOT_POD_GRP, BOT_TESTING

CW_REPORT_CHANNEL = -1001108112459

term_atk_pod = "⚔️ The ⛺️Guildhall of 🌑POD was successfully attacked."
term_def_pod = "🛡 The ⛺️Guildhall of 🌑POD was protected."
term_atk_bot = "⚔️ The ⛺️Guildhall of 🌑BOT was successfully attacked."
term_def_bot = "🛡 The ⛺️Guildhall of 🌑BOT was protected."
guild_atk = r"(?:{}\nAttackers: )(?P<atkrs>.*)(?:\n)(?:Defenders: )(?P<dfrs>.*)"


def get_re_string(string):
    return guild_atk.format(string)


def get_names(players):
    string = []
    names = re.split(r"\s(?=\W)", players)
    for name in names:
        if re.search(r"\W\[BOT\]", name) or re.search(r"\W\[POD\]", name):
            string.append(name.strip())
    return ", ".join(string)


@events.register(events.NewMessage(chats=[CW_REPORT_CHANNEL, BOT_TESTING]))
async def cw_report_channel(event):

    if re.search(r"(^\d+ \w+ \d+)\nBattle reports\:", event.raw_text):

        rep_leaders_regex = r"(?:At\s)(.*?)(?:\sCastle.*\n.*" + \
                                r"🎖Attack leaders: )(.*)(?:\n🎖Defense leaders: )(.*)"
        data = re.findall(rep_leaders_regex, event.raw_text)
        string = ""
        attackers_dict = {}
        defenders_dict = {}

        for leader in data:
            castle = leader[0]
            attack_leaders = leader[1]
            defence_leaders = leader[2]
            if "[BOT]" in attack_leaders or "[POD]" in attack_leaders:
                attackers = get_names(attack_leaders)
                if castle not in attackers_dict.keys():
                    attackers_dict[castle] = []
                attackers_dict[castle].append(attackers)

            if "[BOT]" in defence_leaders or "[POD]" in defence_leaders:
                defenders = get_names(defence_leaders)
                if castle not in defenders_dict.keys():
                    defenders_dict[castle] = []
                defenders_dict[castle].append(defenders)

        if attackers_dict or defenders_dict:
            string += f"**Players on TV last** [battle](https://t.me/chtwrsreports/{event.id})" + "\n\n"

        if attackers_dict:
            string += "**⚔️ Attack leaders :**"
            string += "\n"
            for key, value in attackers_dict.items():
                string += f"At {key[0]} - {', '.join(value)}\n"
            string += "\n"

        if defenders_dict:
            string += "**🛡 Defence leaders :**"
            string += "\n"
            for key, value in defenders_dict.items():
                string += f"{', '.join(value)}"

        if string != "":
            if event.chat_id == BOT_TESTING:
                await event.respond(string, link_preview=False)
            else:
                await bot.send_message(BOT_POD_GRP, string, link_preview=False)
            raise events.StopPropagation

    # POD
    elif re.search(term_atk_pod, event.raw_text):
        attacked = re.compile(get_re_string(term_atk_pod))
        data = attacked.search(event.raw_text)
        attackers = data.group("atkrs")
        defenders = data.group("dfrs")
        string = f"POD got [attacked](https://t.me/chtwrsreports/{event.id}) " + \
                    f"😭\nAttackers: {attackers}\nDefenders: {defenders}"

        if event.chat_id == BOT_TESTING:
            await event.respond(string, link_preview=False)
        else:
            await bot.send_message(BOT_POD_GRP, string, link_preview=False)

    elif re.search(term_def_pod, event.raw_text):
        defended = re.compile(get_re_string(term_def_pod))
        data = defended.search(event.raw_text)
        attackers = data.group("atkrs")
        defenders = data.group("dfrs")
        string = f"POD stood [victorious](https://t.me/chtwrsreports/{event.id}) " + \
                    f"😎\nAttackers: {attackers}\nDefenders: {defenders}"

        if event.chat_id == BOT_TESTING:
            await event.respond(string, link_preview=False)
        else:
            await bot.send_message(BOT_POD_GRP, string, link_preview=False)

    # BOT
    if re.search(term_atk_bot, event.raw_text):
        attacked = re.compile(get_re_string(term_atk_bot))
        data = attacked.search(event.raw_text)
        attackers = data.group("atkrs")
        defenders = data.group("dfrs")
        string = f"BOT got [attacked](https://t.me/chtwrsreports/{event.id}) " + \
                    f"😭\nAttackers: {attackers}\nDefenders: {defenders}"

        if event.chat_id == BOT_TESTING:
            await event.respond(string, link_preview=False)
        else:
            await bot.send_message(BOT_POD_GRP, string, link_preview=False)

    elif re.search(term_def_bot, event.raw_text):
        defended = re.compile(get_re_string(term_def_bot))
        data = defended.search(event.raw_text)
        attackers = data.group("atkrs")
        defenders = data.group("dfrs")
        string = f"BOT stood [victorious](https://t.me/chtwrsreports/{event.id}) " + \
                    f"😎\nAttackers: {attackers}\nDefenders: {defenders}"

        if event.chat_id == BOT_TESTING:
            await event.respond(string, link_preview=False)
        else:
            await bot.send_message(BOT_POD_GRP, string, link_preview=False)
