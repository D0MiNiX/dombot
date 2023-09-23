from datetime import datetime
from telethon.sync import TelegramClient
import os

API_ID      =   os.getenv('API_ID')
API_HASH    =   os.getenv('API_HASH')
TOKEN       =   os.getenv('TOKEN')

# dombot
bot = TelegramClient('bot', int(API_ID), API_HASH, connection_retries = None, retry_delay = 60).start(bot_token=TOKEN)

# user bot
ssn = "user_bot/dom_user_bot"
dom = TelegramClient(ssn, int(API_ID), API_HASH, connection_retries = None, retry_delay = 60).start()
 
runSinceTime = str(datetime.now().strftime("%H:%M:%S"))
runSinceDate = str(datetime.now().strftime("%d/%m/%y"))

CW_BOT                  =       408101137           # Chatwars bot
MOON_ORDER_BOT          =       850594820           # Moon Order Bot
D0MiNiX                 =       542401934           # Me
BOT_POD_GRP             =       -1001315084266      # BOT POD Group
BOT_TESTING             =       -1001460951730      # dombot testing
DOMBOT                  =        863692807          # DOMBOT

# dombot vars
AMTCH               =   -346320914

bot_tag = "@domxxbot"
