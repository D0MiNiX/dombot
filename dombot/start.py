from telethon import events
import re
import vars as bot_vars
from functions import Command, command, command_with_args
import random
from pytz import timezone, country_timezones
from datetime import datetime
from tcp_latency import measure_latency
import random
import asyncio
from functools import partial


HELP_FOLDER = "dombot/rss/help"

timezone_country = {}
for countrycode in country_timezones:
    timezones = country_timezones[countrycode]
    for timezonex in timezones:
        timezone_country[countrycode] = timezonex


prev_time = datetime.now()
spam_dict = {}

def prep_list(users):
    space, blank = " ", ""
    NA = "N/A"

    users_list = [f"{user.first_name + (space + str(user.last_name) if user.last_name else blank)}" +
                    f" ({user.username if user.username is not None else NA}, {user.id})" \
                        for user in users if not user.bot and not user.deleted]

    deleted_accounts = len([k for k in users if k.deleted])

    bots_list = [f"{user.first_name + (space + str(user.last_name) if user.last_name else blank)}" +
                    f" ({user.username if user.username is not None else NA}, {user.id})" \
                        for user in users if user.bot and not user.deleted]

    users_list = sorted(users_list, key=str.lower)
    bots_list = sorted(bots_list, key=str.lower)
    return users_list, deleted_accounts, bots_list

    # for user in users:
    #     if not user.bot:
    #         users_list.append(('@' + user.username) if user.username is not None \
    #             else f"[{user.first_name + ((space + user.last_name) if user.last_name else blank)}](tg://user?id={user.id})")


def check_time(sender):
    global prev_time, spam_dict
    time = datetime.now()
    if sender not in spam_dict:
        spam_dict[sender] = time
    else:
        difference = (time - spam_dict[sender]).total_seconds()
        if difference > 1.5:
            spam_dict[sender] = time
        else:
            spam_dict[sender] = time
            return False
    return True


@bot_vars.bot.on(events.ChatAction(chats=[bot_vars.BOT_TESTING, bot_vars.BOT_POD_GRP]))
async def user_action(event):
    try:
        if event.user_joined or event.user_added:
            await event.reply(file="AgADBQADsawxG55vWVaFDCt8Gl2Uv6Zzt290AAujjQUAAQI")   # bird with toy gun XD
            raise events.StopPropagation
        elif event.user_left or event.user_kicked:
            await event.reply(file="BAADBQADgAIAAp5vWVZ3R3xiH1OKbAI")   # cute crying gif cartoon
            raise events.StopPropagation
    except:
        pass


@events.register(events.NewMessage(forwards=False, pattern=r"^/\w+"))
async def start(event):

    # if hasattr(event, "media") and hasattr(event.media, "emoticon"):
    #     await event.reply(f"Value is {event.media.value}")
        
    if not check_time(event.sender.id):
        raise events.StopPropagation
    
    incomingText = event.raw_text

    cmd = partial(command, event.raw_text)
    cmd_with_args = partial(command_with_args, event.raw_text)

    if cmd("start"):
        await event.reply(file="CAADBQADlQADjmVUIHU2zLOseAnEAg")    # cock running sticker
        raise events.StopPropagation

    elif cmd_with_args("cal"):
        expression = incomingText.split(" ", 1)
        if len(expression) == 1:
            await event.reply("Requires an expression.")
            raise events.StopPropagation
        expression = expression[1].replace(" ", "")
        if re.match('^([-+]?([(]?[0-9][)]?[+-/*]?))*$', expression):
            try:
                await event.reply(str(eval(expression)))
            except:
                await event.reply('Oops error calculating!!')
        else:
            await event.reply('Incorrect format!!')
        raise events.StopPropagation

    elif cmd("ping"):
        chat_id = event.chat_id
        msg_id = await event.reply("pong!!\n`Calculating respose time...`")

        try:
            response = measure_latency(host="google.com")
            await bot_vars.bot.edit_message(chat_id, msg_id.id, "pong!!\n" + f"`{response[0]} ms.`")
        except:
            await bot_vars.bot.edit_message(chat_id, msg_id.id, "Something went wrong. BLEEP BLOOP!!")

        raise events.StopPropagation

    elif cmd("id"):
        if event.is_private:
            await event.reply("Your ID : `" + str(event.sender.id) + "`")
            raise events.StopPropagation
        elif event.is_group or event.is_channel:
            if event.is_reply:
                reply = await event.get_reply_message()
                await event.reply(reply.sender.first_name + "'s ID : `" + str(reply.from_id.user_id) + "`")
                raise events.StopPropagation
            else:
                await event.reply("Your ID : `" + str(event.sender.id) + "`\n" + "This place's ID : `" +
                                  str(event.chat_id) + "`")
                raise events.StopPropagation

    elif cmd("help"):
        f = open(f"{HELP_FOLDER}/general.txt")
        await event.reply(f.read())
        f.close()
        raise events.StopPropagation

    elif cmd("cw_help"):
        f = open(f"{HELP_FOLDER}/cw.txt")
        await event.reply(f.read())
        f.close()
        raise events.StopPropagation

    elif cmd("cw_mobs_help"):
        f = open(f"{HELP_FOLDER}/monsters_and_ambush.txt")
        await event.reply(f.read())
        f.close()
        raise events.StopPropagation

    elif cmd_with_args("time"):
        CountryCode = incomingText.split(" ", 1)
        if len(CountryCode) == 1:
            await event.reply("Please provide the country code. Use `/time list` for available options.\n"
                              "Date will be displayed in (dd/mm/yy) and time will be displayed in (hh:mm:ss).")
            return
        else:
            CountryCode = incomingText.split(" ", 1)[1].upper()

        if CountryCode.lower() == "list":
            await event.reply("Available options:\n" + ', '.join(timezone_country.keys()))
            raise events.StopPropagation

        if CountryCode not in timezone_country.keys():
            await event.reply("Invalid country code. Use `/time list` for available options.")
            raise events.StopPropagation

        utc_time = datetime.utcnow()
        tz = timezone(timezone_country[CountryCode])
        time = str(tz.fromutc(utc_time).__format__("%H:%M:%S"))
        date = str(tz.fromutc(utc_time).__format__("%d/%m/%y"))
        UTC_Offset = str(tz.fromutc(utc_time).__format__("%Z %z"))
        # string = "Date in dd/mm/yy and time in hh:mm:ss format.\n\n"
        string = "It's `{}`, `{}` in `{}`, `{} ({})`.".format(date, time, CountryCode,
                                                            timezone_country[CountryCode], UTC_Offset)
        await event.reply(string)
        raise events.StopPropagation

    elif cmd("toss"):
        tosses_list = ["Heads", "Tails", "Coin went down the sewer!!"]
        await event.reply(random.choice(tosses_list))
        raise events.StopPropagation

    elif cmd("fw_info"):
        if event.is_reply:
            reply_msg = await event.get_reply_message()
            string = "**Message info (UTC)**\n" + "`Date : " + str(reply_msg.date.strftime("%d/%m/%y")) + "`\n" + \
                     "`Time : " + str(reply_msg.date.strftime("%H:%M:%S")) + "`"
            if reply_msg.forward is not None:
                string = string + "\n\n" + "**Forwarded message info (UTC)**\n" + \
                         "`Date : " + str(reply_msg.forward.date.strftime("%d/%m/%y")) + "`\n" + \
                         "`Time : " + str(reply_msg.forward.date.strftime("%H:%M:%S")) + "`"
            await event.reply(string)
        else:
            await event.reply("You need to reply it to some message, por favor.")
        raise events.StopPropagation

    elif cmd("cancerize"):
        if not event.is_reply:
            await event.reply("Please reply to some message.")
            raise events.StopPropagation

        msg = await event.get_reply_message()
        res = ""
        text = msg.raw_text.replace(" ", "")
        
        for idx in range(len(text)):
            if not idx % 2 :
                res = res + text[idx].lower()
            else:
                res = res + text[idx].upper()

        await event.respond(res, reply_to=msg.id)
        raise events.StopPropagation

    elif cmd("list_members"):
        users = await bot_vars.bot.get_participants(event.chat_id)
        users_list, deleted_accounts, bots_list = prep_list(users)
        word = "is" if deleted_accounts == 1 else "are"
        s = "" if deleted_accounts == 1 else "s"
        string = "**Hoomans:**\n" + "\n".join(users_list) + \
                ("\n\n**Bots:**\n" + "\n".join(bots_list) if bots_list else "") + \
                 (f"\n\n**There {word} {deleted_accounts} deleted account{s}.**" if deleted_accounts > 0 else "")
        
        await event.reply(string)
        raise events.StopPropagation

    elif cmd_with_args("len"):
        msg = None
        
        if event.is_reply:
            msg = await event.get_reply_message()
            length = len(msg.raw_text)
            await event.reply(str(length))
        else:
            data = event.raw_text.split(" ", 1)
            if len(data) > 1:
                length = len(data[1])
                await event.reply(str(length))
            else:
                await event.reply("Please provide text like `/len <text>` or use it with reply to other message.")

        raise events.StopPropagation

    elif cmd("utc"):
        await event.reply(datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"))
        raise events.StopPropagation

    elif cmd("reverse"):
        if not event.is_reply:
            await event.reply("Please reply to a message")
            raise events.StopPropagation

        message = await event.get_reply_message()
        reverse_text = message.text[::-1]
        await event.respond(reverse_text, reply_to=message.id)
        raise events.StopPropagation
