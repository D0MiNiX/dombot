from telethon import events, functions
from vars import dom, bot
from functions import list_string_in_text, Command
import asyncio
import random
import aiocron
import re
from datetime import datetime


# CW
BOT_TESTING = -1001460951730
TYPO_TALES_BOT = 1436263237
ForayText = "You were strolling around on your horse when you noticed"
CW_BOT = 408101137
quest_start = "Arena isn't a place for the weak. Here you fight against other players and if you stand victorious, you acquire precious experience."
quest_started = False
arena_started = False
dice = False
foray = False
pathfinder = "Being a naturally born pathfinder, you found a secret passage and saved some energy +1🔋"
stam = 0
rage = None
button_number = None

# me_regex = re.compile(r"🏅Level: \d+\n⚔️Atk: \d+ 🛡Def: \d+\n" + \
#                         "🔥Exp: \d+\/\d+\n❤️Hp: \d+\/\d+\n🔋Stamina: \d+\/\d+")

me_regex = re.compile(r".* \w*\s*of \w+ Castle")

foray_results = [
    "was completely clueless. Village was successfully pillaged",
    "noticed you and nearly beat you to death",
    "tried stopping you, but you were stronger"
]

monster_fight = [
    "Congratulations! You are still alive.", 
    "This is sad but You are nearly dead."
]

quest_over = [
    "You need to heal your wounds and recover, come back later.",
    "You should heal up a bit first.",
    "Not enough stamina. Come back after you take a rest.",
    "It’s hard to see your opponent in the dark.",
    "Battle is coming. You have no time for games.",
    "You are nearly dead",
    "Shouldn't you be ashamed of trying to play with no money?"
]

qst_txts = [
    'You received',
    'Walking through the winter mountains, you noticed an old mound',
    'Strolling through the mountains, you realised that you are fed up',
    'Your adventure got cut short when you came across a bridge',
    'no loot. Such a pity',
    'And guess what? Nothing interesting happened',
    'You returned home empty handed',
    'You\'ve stepped into a pile of dung',
    'It was a really nice and sunny',
    'Somewhere in the forest, you encounter a deer who stops',
    'Their leader, an orange man with crazy hair, looked dangerous',
    'As you were just about to enter the forest, something came to your attention',
    'Mrrrrgl mrrrgl mrrrrrrgl mrrrgl. Mrrrrrrrrrrrgl',
    'You fell asleep and in your dream there was a beautiful land where',
    'It was a cool and refreshing night',
    'You found yourself in a land you where you did not want to appear again',
    'Wandering around, you saw a little golden ball',
    'In the forest you came upon a bold man who offered to fulfill your every wish',
    'As you were about to head out for an adventure',
    'Walking through the forest you encountered a thick mist',          # new quest texts begins
    'In the swamp you seen a strange vision of an angel and a demon',
    'Walking through the swamp you find a bunch of crazy librarians',
    'On your way to the swamp, you saw a group of people shouting angrily at their supposed leader',
    'Looking at the overcast sky',
    'Walking through the swamp, you found yourself surrounded by the mist',
    'On your quest you came to the town of Honeywood',
    'As you were strolling through the forest',
    'You let yourself go and you returned to the village',
    'A knight writes haikus all',
    'In the forest you found a shrimp, a pizza and a brain',
    'In the forest you came across a tavern where all kinds of magical creatures played a card game',
    'As I walk through the valley of the shadow of death',
    'At a remote place in the mountains you spot some funny looking',
    'You noticed a book lying under the tree',
    'In and out, 20 second adventure!',
    'Being a naturally bad pathfinder, you got lost'
]

# TypoTales
tt_qst = False


async def go_offline():
    await asyncio.sleep(2)
    await dom(functions.account.UpdateStatusRequest(offline=True))


async def go_online():
    await asyncio.sleep(2)
    await dom(functions.account.UpdateStatusRequest(offline=False))


async def rage_up():
    await dom.send_message(CW_BOT, "/use_p01")
    await asyncio.sleep(5)
    await dom.send_message(CW_BOT, "/use_p02")
    await asyncio.sleep(5)
    await dom.send_message(CW_BOT, "/use_p03")
    await go_offline()
    if rage is not None:
        rage.stop()


def clear_variables():
    global stam, quest_started, arena_started, dice, foray, button_number, tt_qst
    stam = 0
    quest_started = False
    arena_started = False
    dice = False
    foray = False
    button_number = None
    tt_qst = False


@events.register(events.NewMessage(chats=CW_BOT, from_users=CW_BOT))
async def cw(event):

    global stam, quest_started, arena_started, dice, monster_fight, foray, foray_results, quest_over, \
        qst_txts, button_number, me_regex

    if "🎲You threw the dice on the table:" in event.raw_text or "No one sat down next to you =/" in \
            event.raw_text:
        await asyncio.sleep(random.randrange(1, 5))
        if dice:
            await event.respond("🎲Play some dice")
        # else:
        #     await event.respond("🛡Defend")   ... pn
        await go_offline()
        raise events.StopPropagation

    elif ForayText in event.raw_text:
        await asyncio.sleep(random.randrange(15, 25))
        await go_online()
        await event.click(0)
        await go_offline()
        raise events.StopPropagation

    elif me_regex.search(event.raw_text) and (quest_started or foray):
        stam = int(re.findall(r"(?:🔋Stamina: )(\d+)/(?:\d+)", event.raw_text)[0])
        if stam > 0:
            await asyncio.sleep(random.randrange(1, 5))
            await event.respond("🗺Quests")
            await go_offline()
        else:
            quest_started = False
            foray = False
            await bot.send_message(BOT_TESTING, "No stam dude.")

        raise events.StopPropagation

    elif list_string_in_text(event.raw_text, qst_txts) and not arena_started:

        if "You were looking at the bright sparks emitted from the flame of your torch" in event.raw_text:
            await asyncio.sleep(random.randrange(1, 5))
            await event.respond("/on_tch")

        if pathfinder not in event.raw_text:
            stam -= 1

        if stam <= 0 or not quest_started:
            quest_started = False
            await asyncio.sleep(random.randrange(1, 5))
            # await event.respond("🛡Defend")   ... pn
        else:
            await asyncio.sleep(random.randrange(1, 5))
            await dom.send_message(CW_BOT, "🗺Quests")

        await go_offline()
        raise events.StopPropagation

    elif quest_start in event.raw_text and (quest_started or foray):

        await asyncio.sleep(random.randrange(1, 5))

        if quest_started:   #  and button_number is None

            quest_type = re.findall(r".*🔥", event.raw_text, flags=re.MULTILINE)
            
            if len(quest_type) == 0:
                button_number = random.randrange(0, 3)
            elif "Forest" in quest_type[0]:
                button_number = 0
            elif "Swamp" in quest_type[0]:
                button_number = 1
            elif "Valley" in quest_type[0]:
                button_number = 2

            await event.click(button_number)

        await go_offline()
        raise events.StopPropagation

    elif ("Leaderboard of fighters are updated: /top5 & /top6" in event.raw_text or \
            "You didn’t find an opponent. Return later." in event.raw_text) and arena_started:
        await asyncio.sleep(random.randrange(1, 5))
        await dom.send_message(CW_BOT, "▶️Fast fight")
        await go_offline()
        raise events.StopPropagation

    elif list_string_in_text(event.raw_text, quest_over):
        clear_variables()
        raise events.StopPropagation

    elif list_string_in_text(event.raw_text, monster_fight):
        await asyncio.sleep(2)
        await event.click(1)
        raise events.StopPropagation

    elif "To accept their offer, you shall /pledge to protect." in event.raw_text:
        await asyncio.sleep(2)
        await event.respond("/pledge")
        await go_offline()
        raise events.StopPropagation

    elif list_string_in_text(event.raw_text, foray_results):
        stam -= 2
        if stam <= 1:
            foray = False
            await asyncio.sleep(random.randrange(10, 15))
            # await event.respond("🛡Defend") ...disabling bcz of pn
        else:
            await asyncio.sleep(random.randrange(10, 15))
            await dom.send_message(CW_BOT, "🗺Quests")
        await go_offline()
        raise events.StopPropagation


@events.register(events.NewMessage(chats=[BOT_TESTING]))
async def bot_testing(event):

    global stam, quest_started, arena_started, dice, foray, button_number, tt_qst

    if event.raw_text.startswith("qst"):
        quest_type = event.raw_text.split(" ")
        if len(quest_type) == 1:
            button_number = None
        elif int(quest_type[1]) == 0:
            button_number = 0
        elif int(quest_type[1]) == 1:
            button_number = 1
        elif int(quest_type[1]) == 2:
            button_number = 2
        quest_started = True
        await event.delete()
        await dom.send_message(CW_BOT, "🏅Me")
        await go_offline()
        raise events.StopPropagation

    elif event.raw_text == "stp":
        clear_variables()
        await event.delete()
        raise events.StopPropagation

    elif event.raw_text == "arn":
        arena_started = True
        await dom.send_message(CW_BOT, "▶️Fast fight")
        await event.delete()
        raise events.StopPropagation

    elif event.raw_text == "dice":
        dice = True
        await dom.send_message(CW_BOT, "🎲Play some dice")
        await event.delete()
        raise events.StopPropagation

    elif event.raw_text == "rage":
        current_hour = datetime.now().hour
        minute = random.randrange(10, 20)
        if current_hour <= 4 or (20 <= current_hour <= 23):
            rage = aiocron.crontab(f"{minute} 4 * * *", func=rage_up, start=True)
        elif current_hour <= 12:
            rage = aiocron.crontab(f"{minute} 12 * * *", func=rage_up, start=True)
        elif current_hour <= 20:
            rage = aiocron.crontab(f"{minute} 20 * * *", func=rage_up, start=True)
        
        await event.delete()
        raise events.StopPropagation

    elif event.raw_text == "foray":
        foray = True
        button_number = 3
        await event.delete()
        await dom.send_message(CW_BOT, "🏅Me")
        await go_offline()
        raise events.StopPropagation

    elif Command(event.raw_text, "cft"):
        await event.delete()
        stock_num = event.raw_text.split(" ")[1]
        cmd = f"/c_{stock_num}"
        for x in range(0, 5):
            await dom.send_message(CW_BOT, cmd)
            await asyncio.sleep(2, 4)
        await go_offline()
    
    elif event.raw_text == "tt_qst":
        tt_qst = True
        await event.delete()
        await go_offline()
        raise events.StopPropagation


# @aiocron.crontab("31 4,12,20 * * * ")
async def start_dice():
    await dom.send_message(CW_BOT, "🎲Play some dice")


@events.register(events.NewMessage(chats=[TYPO_TALES_BOT], incoming=True))
async def typo_tales(event):

    global tt_qst

    if ("You return from a bountiful harvest" in event.raw_text or \
        "You found some shiny stones" in event.raw_text) and tt_qst:
        await asyncio.sleep(5, 20)
        await event.click(0)
        await go_offline()
        raise events.StopPropagation


# @events.register(events.NewMessage())
# async def user_bot_testing(event):
#     if event.chat_id == 1436263237:
#         print(event.raw_text)
