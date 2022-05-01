from telethon import events, functions
from vars import dom, bot
from functions import list_string_in_text, Command
import asyncio
import random
import aiocron
import re
from datetime import datetime

BOT_TESTING = -1001460951730
CW_ELITE_BOT = 5233916499
CW_BOT = 408101137
me_regex = re.compile(r"Battle of the (five|seven) castles in")
stam_full_text = "Stamina restored. You are ready for more adventures!"
foray_intervene = "You were strolling around on your horse when you noticed"
quest_start_txt = "Arena isn't a place for the weak. Here you fight against other players and if you stand victorious, you acquire precious experience."
accept_tribute_txt = "To accept their offer, you shall /pledge to protect."

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

arena_text = [
    "Leaderboard of fighters are updated: /top5 & /top6",
    "You didn’t find an opponent. Return later."
]

class ChatWars:
    lost_torch_text = "You were looking at the bright sparks emitted from the flame of your torch"
    pathfinder = "Being a naturally born pathfinder, you found a secret passage and saved some energy +1🔋"

    def __init__(self, bot_id):
        self.bot_id = bot_id
        self.quest_started = False
        self.button_number = False
        self.random_quest = False
        self.foray_someone = False
        self.arena_started = False
        self.stam = 0

    async def go_offline(self):
        await asyncio.sleep(2)
        await dom(functions.account.UpdateStatusRequest(offline=True))

    async def go_online(self):
        await asyncio.sleep(2)
        await dom(functions.account.UpdateStatusRequest(offline=False))

    async def stam_full(self, event):
        self.quest_started = True
        await asyncio.sleep(random.randrange(10, 15))
        await event.respond("🏅Me")

    async def stop_foray(self, event):
        await asyncio.sleep(random.randrange(15, 25))
        await self.go_online()
        await event.click(0)
        await self.go_offline()

    async def start_quest(self, event):
        self.stam = int(re.findall(r"(?:🔋Stamina: )(\d+)/(?:\d+)",  event.raw_text)[0])

        if self.stam > 0:
            await asyncio.sleep(random.randrange(1, 5))
            await event.respond("🗺Quests")
            await self.go_offline()
        else:
            self.quest_started = False
            self.foray_someone = False

    async def send_quest(self, event):
        if eval(__class__.__name__).lost_torch_text in event.raw_text:
            await asyncio.sleep(random.randrange(1, 5))
            await event.respond("/on_tch")

        if eval(__class__.__name__).pathfinder not in event.raw_text:
         self.stam -= 1

        if self.stam <= 0 or not self.quest_started:
            self.quest_started = False
            await asyncio.sleep(random.randrange(1, 5))
            await event.respond("🛡Defend")
        else:
            await asyncio.sleep(random.randrange(1, 5))
            await dom.send_message(self.bot_id, "🗺Quests")

        await self.go_offline()

    async def click_quest(self, event):
        await asyncio.sleep(random.randrange(1, 5))

        if self.quest_started:
            self.button_number = None
            quest_type = None # re.findall(r".*🎩", event.raw_text, flags=re.MULTILINE)    # for noble hat

            if quest_type:
                if "Forest" in quest_type[0]:
                    self.button_number = 0
                elif "Swamp" in quest_type[0]:
                    self.button_number = 1
                elif "Valley" in quest_type[0]:
                    self.button_number = 2
            elif self.random_quest or self.button_number is None:
                    self.button_number = random.randrange(0, 3)

        # TODO: Temp fix
        if self.bot_id == CW_ELITE_BOT:
            self.button_number = 0
 
        await event.click(self.button_number)
        await self.go_offline()

    async def fast_fight(self, event):
        await asyncio.sleep(random.randrange(1, 5))
        await dom.send_message(self.bot_id, "▶️Fast fight")
        await self.go_offline()

    async def pledge(self, event):
        await asyncio.sleep(2)
        await event.respond("/pledge")
        await self.go_offline()

    async def go_foray_someone(self, event):
        self.stam -= 2

        if self.stam <= 1:
            self.foray_someone = False
            await asyncio.sleep(random.randrange(10, 15))
            await event.respond("🛡Defend")
        else:
            await asyncio.sleep(random.randrange(10, 15))
            await dom.send_message(self.bot_id, "🗺Quests")

        await self.go_offline()

    def clear_state(self):
        self.stam = 0
        self.quest_started = False
        self.foray_someone = False
        self.arena_started = False


cw2 = ChatWars(CW_BOT)
cw_elite = ChatWars(CW_ELITE_BOT)


@events.register(events.NewMessage(chats=[CW_BOT, CW_ELITE_BOT],  from_users=[CW_BOT, CW_ELITE_BOT]))
async def cw(event):

    global cw_elite, cw2
    global qst_txts, foray_results, quest_over, monster_fight, arena_text
    global stam_full_text, foray_intervene, quest_start_txt, accept_tribute_txt
    global me_regex
    cw = None

    if event.chat_id == CW_BOT:
        cw = cw2
    elif event.chat_id == CW_ELITE_BOT:
        cw = cw_elite

    if stam_full_text in event.raw_text:
        await cw.stam_full(event)
        raise events.StopPropagation

    elif foray_intervene in event.raw_text:
        await cw.stop_foray(event)
        raise events.StopPropagation

    elif me_regex.search(event.raw_text) and (cw.quest_started or cw.foray_someone):
        await cw.start_quest(event)
        raise events.StopPropagation

    elif list_string_in_text(event.raw_text, qst_txts) and not cw.arena_started:
        await cw.send_quest(event)
        raise events.StopPropagation

    elif quest_start_txt in event.raw_text and (cw.quest_started or cw.foray_someone):
        await cw.click_quest(event)
        raise events.StopPropagation

    elif list_string_in_text(event.raw_text, arena_text):
        await cw.fast_fight(event)
        raise events.StopPropagation

    elif list_string_in_text(event.raw_text, quest_over):
        cw.clear_state()
        raise events.StopPropagation

    elif list_string_in_text(event.raw_text, monster_fight):
        await asyncio.sleep(2)
        await event.click(1)
        raise events.StopPropagation

    elif accept_tribute_txt in event.raw_text:
        await cw.pledge(event)
        raise events.StopPropagation

    elif list_string_in_text(event.raw_text, foray_results):
        await cw.go_foray_someone(event)
        raise events.StopPropagation


@events.register(events.NewMessage(chats=[BOT_TESTING]))
async def bot_testing(event):
    global cw2, cw_elite
    cw = None

    if event.raw_text.endswith("_e"):
        cw = cw_elite
    else:
        cw = cw2

    if event.raw_text.startswith("qst"):
        quest_type = event.raw_text.split(" ")

        if len(quest_type) == 1:
            cw.random_quest = True
            cw.button_number = None
        elif int(quest_type[1]) == 0:
            cw.random_quest = False
            cw.button_number = 0
        elif int(quest_type[1]) == 1:
            cw.random_quest = False
            cw.button_number = 1
        elif int(quest_type[1]) == 2:
            cw.random_quest = False
            cw.button_number = 2

        cw.quest_started = True
        await event.delete()
        await dom.send_message(cw.bot_id, "🏅Me")
        await cw.go_offline()
        raise events.StopPropagation

    elif event.raw_text.startswith("stp"):
        cw.clear_state()
        await event.delete()
        raise events.StopPropagation

    elif event.raw_text.startswith("arn"):
        cw.arena_started = True
        await dom.send_message(cw.bot_id, "▶️Fast fight")
        await event.delete()
        raise events.StopPropagation

    # elif event.raw_text.startswith("rage"):
    #     current_hour = datetime.now().hour
    #     minute = random.randrange(10, 20)
    #     if current_hour <= 4 or (20 <= current_hour <= 23):
    #         rage = aiocron.crontab(f"{minute} 4 * * *", func=rage_up, start=True)
    #     elif current_hour <= 12:
    #         rage = aiocron.crontab(f"{minute} 12 * * *", func=rage_up, start=True)
    #     elif current_hour <= 20:
    #         rage = aiocron.crontab(f"{minute} 20 * * *", func=rage_up, start=True)
    # 
    #     await event.delete()
    #     raise events.StopPropagation

    elif event.raw_text.startswith("foray"):
        cw.foray_someone = True
        cw.random_quest = False
        cw.button_number = 3
        await event.delete()
        await dom.send_message(cw.bot_id, "🏅Me")
        await cw.go_offline()
        raise events.StopPropagation

    elif Command(event.raw_text, "cft"):
        await event.delete()
        stock_num = event.raw_text.split(" ")[1]
        cmd = f"/c_{stock_num}"
        for x in range(0, 5):
            await dom.send_message(cw.bot_id, cmd)
            await asyncio.sleep(2, 4)
        await cw.go_offline()
