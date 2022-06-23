from telethon import events, Button
from functions import command, command_with_args
from functools import partial
from database import Database
from functions import cleanup, check_db_error
import random
import asyncio
import re
import vars


TYPO_TALES_BOT = 1436263237
dragon_db = r"dombot/typo_tales/dragon_egg/dragon_egg.db"
MAX_GUILD_TAG_LENGTH = 5
data_for_callback = {}


@vars.bot.on(events.CallbackQuery)
async def egg_confirmation(event):

    global data_for_callback
    data = event.data.decode("UTF-8")
    
    if not re.search(r"yes_egg|no_egg|red|green|blue", data):
        return

    if event.chat_id not in data_for_callback:
        await event.edit("Poof!! Vanished!! It was too old, or maybe program restarted (sorry, if this happened).")
        raise events.StopPropagation

    db = Database(dragon_db)
    dum = []
    guild_from_db = db.select_single(f"SELECT guild FROM access WHERE authorized_person={event.sender_id}")
    await check_db_error(db, event, guild_from_db, dum)

    if dum:
        db.close_all()
        await event.answer("Hmm...no, you can't.")
        return

    guild = data_for_callback[event.chat_id][event.message_id][0]

    if guild != guild_from_db:
        db.close_all()
        await event.answer("Hmm...no, you can't.")
        return

    if data == "yes_egg":
        buttons_layout = [Button.inline("❤️Red", b"red"), Button.inline("💚Green", b"green"),
                            Button.inline("💙Blue", b"blue")]
        await event.edit("Which color do they want? Ask them before clicking.", buttons=buttons_layout)
        raise events.StopPropagation

    elif data == "no_egg":
        await event.edit("Alright. No eggs given.")
        raise events.StopPropagation

    elif re.search(r"red|green|blue", data):
        print("In red, green, blue")
        guild = data_for_callback[event.chat_id][event.message_id][0]
        print(guild)
        player_name = data_for_callback[event.chat_id][event.message_id][1]
        print(player_name)
        db = Database(dragon_db)
        print("created db")
        color_count = db.select_single(f"SELECT {data} FROM `{guild}` WHERE player_name='{player_name}'")
        await check_db_error(db, event, color_count)
        print(color_count)
        color_count += 1
        query = db.query(f"UPDATE `{guild}` SET {data}={color_count} WHERE player_name='{player_name}'",
                            row_count=True)
        await check_db_error(db, event, query)

        print(query)

        if not query:
            await event.answer("Couldn't change.")
        else:
            await event.edit(f"Great, {player_name} now have {color_count} {data} egg(s).")

        # Add the name to the ignore_<guild> table so that it shouldn't appear at next pick
        query = db.insert(f"ignore_{guild}", [player_name])
        await check_db_error(db, event, query)

        del data_for_callback[event.chat_id]
        db.close_all()
        raise events.StopPropagation


@events.register(events.NewMessage(forwards=False, pattern=r"^/\w+"))
async def random_pick(event):

    global data_for_callback
    cmd = partial(command, event.raw_text)
    cmd_with_args = partial(command_with_args, event.raw_text)

    if cmd("setup_random_picker"):

        sender_id = event.sender.id

        if not event.is_reply:
            await event.reply("Please reply to a list of guild members from TypoTales bot.")
            raise events.StopPropagation

        message = await event.get_reply_message()

        if not message.forward:
            await event.reply("Doesn't look like a forwarded message 👀.")
            raise events.StopPropagation

        if message.forward.from_id.user_id != TYPO_TALES_BOT:
            await event.reply("Doesn't look like its from TypoTales bot 👀.")
            raise events.StopPropagation

        guild_re = f"^\\[(\\w{{1,{MAX_GUILD_TAG_LENGTH}}})\\].*"
        guild = re.findall(guild_re, message.raw_text)

        if not guild:
            await cleanup(event, text="Couldn't identify guild.")
        else:
            guild = guild[0]

        db = Database(dragon_db)

        # Create table "access" if it does not exist already
        query = db.query(f"CREATE TABLE IF NOT EXISTS access (guild VARCHAR({MAX_GUILD_TAG_LENGTH}), " + \
                            "authorized_person INTEGER PRIMARY KEY)")
        await check_db_error(db, event, query)

        # Fetch the names of authorized persons
        auth_persons = db.select(f"SELECT authorized_person FROM access")
        await check_db_error(db, event, query)
        auth_persons = [k[0] for k in auth_persons]

        if sender_id in auth_persons:
            await cleanup(event, db=db, text="Can't, you are already authorized for one guild already.")

        query = db.select(f"SELECT DISTINCT guild FROM access")
        guild_in_db = [k[0] for k in query]

        if guild in guild_in_db:
            await cleanup(event, db=db, text="Guild is already registered for random picks.")

        query = db.insert("access", [guild, sender_id])
        await check_db_error(db, event, query)

        query = db.query(f"CREATE TABLE IF NOT EXISTS `{guild}` " + \
                            "(player_name VARCHAR(64) PRIMARY KEY, red BOOLEAN DEFAULT 0, " + \
                            "green BOOLEAN DEFAULT 0, blue BOOLEAN DEFAULT 0)")
        await check_db_error(db, event, query)

        # Create the table to ignore the already picked ones
        query = db.query(f"CREATE TABLE IF NOT EXISTS ignore_{guild} (player_name VARCHAR(128) PRIMARY KEY)")
        await check_db_error(db, event, query)

        msg = await event.reply("`Doing stuff...`")

        # Add players to db
        players_list = re.findall(r"(?:SL.*?)(\w+)$", message.raw_text, flags=re.M)
        for player in players_list:
            query = db.insert(guild, [player, 0, 0, 0])
            await check_db_error(db, event, query)

        await vars.bot.edit_message(event.chat_id, msg, f"Done. Added players:\n`{', '.join(players_list)}`.")
        db.close_all()
        raise events.StopPropagation

    elif cmd("eggs"):
        dum = []
        db = Database(dragon_db)
        guild = db.select_single(f"SELECT guild FROM access WHERE authorized_person={event.sender.id}")
        await check_db_error(db, event, guild, dum)

        if dum:
            await cleanup(event, db, "Not authorized.")

        data = db.select(f"SELECT * FROM `{guild}`")
        await check_db_error(db, event, data)
        string = "<player_name> (<red>,<green>,<blue>)\n"

        for datum in data:
            string += datum[0] + " (" + str(datum[1]) + "," + str(datum[2]) + "," + str(datum[3]) + ")\n"
        
        await event.respond(string)
        db.close_all()
        raise events.StopPropagation

    elif cmd_with_args("set_eggs"):
        
        if not re.match(r"\/set_eggs\s\w+\s\d,\d,\d", event.raw_text):
            await event.reply("Invalid. Usage `/set_eggs <player_name> <red_ec>,<green_ec>,<blue_ec>`, where " + \
                                "ec = eggs count")
            raise events.StopPropagation

        dum = []
        db = Database(dragon_db)
        guild = db.select_single(f"SELECT guild FROM access WHERE authorized_person={event.sender.id}")
        await check_db_error(db, event, guild, dum)

        if dum:
            await cleanup(event, db, "Not authorized.")

        data = event.raw_text.split(' ')
        player_name = data[1]
        eggs = data[2]
        colors = [int(k) for k in eggs.split(',')]

        count = db.query(f"UPDATE `{guild}` SET red={colors[0]}, green={colors[1]}, blue={colors[2]} " + \
                            f"WHERE player_name='{player_name}'", row_count=True)
        await check_db_error(db, event, guild)

        if not count:
            await cleanup(event, db, "No changes made. Does the player exists?")

        await event.reply("Updated.")
        db.close_all()
        raise events.StopPropagation

    if cmd("pick"):
        dum = []

        if not event.is_reply:
            await event.reply("Please use it to reply to a list of guild members from TypoTales bot.")
            raise events.StopPropagation

        msg = await event.get_reply_message()

        if not msg.forward:
            await event.reply("Doesn't look like a forwarded message 👀.")
            raise events.StopPropagation

        if msg.forward.from_id.user_id != TYPO_TALES_BOT:
            await event.reply("Doesn't look like its from TypoTales bot 👀.")
            raise events.StopPropagation

        if not re.match(r"^\[.*?\]\s\w+\n.*?Guild Members\s\(\d+\/\d+\)\n\nSL.*$", msg.raw_text, re.S):
            raise events.StopPropagation

        guild_re = f"\\[(\\w{{1,{MAX_GUILD_TAG_LENGTH}}})\\].*"
        guild_from_msg = re.findall(guild_re, msg.raw_text)

        if not guild_from_msg:
            await cleanup(event, text="Something went wrong.")
        else:
            guild_from_msg = guild_from_msg[0]

        db = Database(dragon_db)
        guild_from_db = db.select_single(f"SELECT guild FROM access WHERE authorized_person={event.sender.id}")
        await check_db_error(db, event, guild_from_db, dum)

        if dum:
            await cleanup(event, db, "Not authorized.")

        if guild_from_db != guild_from_msg:
            await cleanup(event, db, "Guild mismatch. You are not registered as authorized person for that guild.")

        # Get the players stored in database
        stored_players_list = db.select(f"SELECT player_name FROM `{guild_from_msg}`")
        await check_db_error(db, event, stored_players_list)
        stored_players_list = [k[0] for k in stored_players_list]

        # Players from the message
        players_list = re.findall(r"(?:SL.*?)(\w+)$", msg.raw_text, flags=re.M)

        # Find the difference of players from both lists to add and remove to/from db
        players_to_be_added = [k for k in players_list if k not in stored_players_list]
        players_to_be_removed = [k for k in stored_players_list if k not in players_list]

        # Add players to db
        for player in players_to_be_added:
            query = db.insert(guild_from_msg, [player, 0, 0, 0])
            await check_db_error(db, event, query)

        # Remove players from db
        for player in players_to_be_removed:
            query = db.delete(guild_from_msg, "player_name", player)
            await check_db_error(db, event, query)

        # New list of players
        players_list = db.select(f"SELECT player_name FROM `{guild_from_msg}`")
        await check_db_error(db, event, players_list)
        players_list = [k[0] for k in players_list]

        # Length of full players list
        length = len(players_list)

        # Players to be ignored
        ignore_list = db.select(f"SELECT player_name FROM `ignore_{guild_from_msg}`")
        await check_db_error(db, event, ignore_list)
        ignore_list = [k[0] for k in ignore_list]

        # Final players list
        players_list = [k for k in players_list if k not in ignore_list]

        difference = length - len(ignore_list)
        warning = None
        numbers = 3 if difference >= 3 else difference
        s = "s" if numbers > 1 else ""
        lucky_one = None
        buttons_layout = [Button.inline("Yes", b"yes_egg"), Button.inline("Nope", b"no_egg")]

        if difference > 1:
            random.shuffle(players_list)
            await event.respond(f"Hmmmm, let me pick my {numbers} favourite one{s} for this round 👀")
            await asyncio.sleep(4)
            three = players_list[0:numbers]
            await event.respond(f"They are `{', '.join(three)}`.\nEenie, meenie, minie, moe," + \
                                    " let me pick one by their toe 🙆‍♂️")
            await asyncio.sleep(6)
            random.shuffle(three)
            lucky_one = random.choice(three)
            await event.respond(f"Aaaaaaand the lucky one is `{lucky_one}` 🥳🥳")
            await asyncio.sleep(2)
        elif difference == 0:
            await cleanup(event, db, "No one remaining to receive eggs. Use `/reset_egg_round` to reset.")
        else:
            lucky_one = players_list[0]
            await event.respond(f"`{lucky_one}` is the sole participant of this round.")
            await asyncio.sleep(2)

        if difference == 2:
            warning =   "Only two players are remaining to recevie eggs. Use the `/reset_egg_round` " + \
                        "if you want to start counting again after this pick, but then you will need" + \
                        " to set the eggs count manually for the remaining ones using `/set_eggs`."
            await event.respond(warning)

        msg_id = await event.respond(f"Do you want to give the egg to `{lucky_one}`?", buttons=buttons_layout)
        
        if event.chat_id not in data_for_callback:
            data_for_callback[event.chat_id] = {}

        data_for_callback[event.chat_id][msg_id.id] = [guild_from_msg, lucky_one]
        
        db.close_all()
        raise events.StopPropagation

    elif cmd("reset_egg_round"):
        dum = []
        db = Database(dragon_db)
        guild = db.select_single(f"SELECT guild FROM access WHERE authorized_person={event.sender.id}")
        await check_db_error(db, event, guild, dum)

        if dum:
            await cleanup(event, db, "Not authorized.")

        query = db.query(f"DELETE FROM `ignore_{guild}`", row_count=True)
        await check_db_error(db, event, guild, query)
        
        if not query:
            await cleanup(event, db, "No one has received eggs yet.")

        await event.reply("Reset successful.")
        db.close_all()
        raise events.StopPropagation

    elif cmd_with_args("give_egg_perm"):
        dum = []
        db = Database(dragon_db)
        guild = db.select_single(f"SELECT guild FROM access WHERE authorized_person={event.sender.id}")
        await check_db_error(db, event, guild, dum)

        if dum:
            await cleanup(event, db, "Not authorized.")

        data = event.raw_text.split(" ")

        if len(data) == 1:
            await cleanup(event, db, "Please provide the user id as well. Usage: `/give_perm <user_id>`")

        auth = data[1]

        if not auth.isdigit():
            await cleanup(event, db, "Not a valid ID.")
        else:
            auth = int(auth)

        query = db.insert("access", [guild, auth])
        await check_db_error(db, event, query)
        await event.reply("Authorized.")
        await cleanup(event, db)

    elif cmd_with_args("rm_egg_perm"):
        dum = []
        db = Database(dragon_db)
        guild = db.select_single(f"SELECT guild FROM access WHERE authorized_person={event.sender.id}")
        await check_db_error(db, event, guild, dum)

        if dum:
            await cleanup(event, db, "Not authorized.")

        data = event.raw_text.split(" ")

        if len(data) == 1:
            await cleanup(event, db, "Please provide the user id as well. Usage: `/give_perm <user_id>`")

        auth = data[1]

        if not auth.isdigit():
            await cleanup(event, db, "Not a valid ID.")
        else:
            auth = int(auth)

        query = db.delete("access", "authorized_person", auth)
        if isinstance(query, Exception):
            await cleanup(event, db, "Something went wrong.")
        elif not query:
            await cleanup(event, db, "Person doesn't exist.")
        else:
            await cleanup(event, db,"Removed perms.")

    elif cmd("eggs_given"):
        dum = []
        db = Database(dragon_db)
        guild = db.select_single(f"SELECT guild FROM access WHERE authorized_person={event.sender.id}")
        await check_db_error(db, event, guild, dum)

        if dum:
            await cleanup(event, db, "Not authorized.")

        players = db.select(f"SELECT player_name FROM `ignore_{guild}`")
        await check_db_error(db, event, players, dum)

        if dum:
            await cleanup(event, db, "No one has received eggs yet.")

        players = [k[0] for k in players]

        nl = "\n"
        string = '\n'.join(players)
        await event.reply(f"Given eggs for the current round to the following players:{nl}{string}")
        await cleanup(event, db)

    elif cmd_with_args("ignore_egg_for"):
        data = event.raw_text.split(" ")
        name = ""

        if len(data) >= 2:
            name = data[1]
        else:
            await event.reply("Invalid arguments.")
            raise events.StopPropagation
        
        dum = []
        db = Database(dragon_db)
        guild = db.select_single(f"SELECT guild FROM access WHERE authorized_person={event.sender.id}")
        await check_db_error(db, event, guild, dum)

        if dum:
            await cleanup(event, db, "Not authorized.")

        # players = db.select(f"SELECT player_name FROM `{guild}`")
        # await check_db_error(db, event, guild, dum)

        # players = [k[0] for k in players]

        # if name in players:
        query = f"DELETE FROM `{guild}` WHERE player_name='{name}'"
        query = db.delete(guild, "player_name", name)
        await check_db_error(db, event, query)

        query = db.insert(f"ignore_{guild}", [name])
        await check_db_error(db, event, query, dum)
        if dum:
            await cleanup(event, db, "Player already exists in ignore list.")
        # else:
        #     await cleanup(event, db, "Player does not exist.")

        await cleanup(event, db, "Added to ignore list.")

    # elif cmd("qrandom"):

    #     if not event.is_reply:
    #         await event.reply("Please use it to reply to a list of guild members from TypoTales bot.")
    #         raise events.StopPropagation

    #     msg = await event.get_reply_message()

    #     if not msg.forward:
    #         await event.reply("Doesn't look like a forwarded message 👀.")
    #         raise events.StopPropagation

    #     if msg.forward.from_id.user_id != TYPO_TALES_BOT:
    #         await event.reply("Doesn't look like its from TypoTales bot 👀.")
    #         raise events.StopPropagation

    #     players_list = re.findall(r"(?:SL.*?)(\w+)$", msg.raw_text, flags=re.M)
    #     lucky_one = random.choice(players_list)
    #     await event.respond(f"`{lucky_one}`")
    #     raise events.StopPropagation
