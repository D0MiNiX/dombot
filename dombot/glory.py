from telethon import events
import re, vars
from datetime import datetime


@events.register(events.NewMessage(chats=[vars.BOT_POD_GRP, vars.D0MiNiX]))
async def cal_glory(event):

    if event.message.forward is not None and event.message.forward.from_id.user_id == 408101137 and \
         "🌑[POD] Pint Of Deer" in event.raw_text and re.search(r"🏅Level: (\d+) 🎖Glory: (\d+)", event.raw_text):
        timeFormat = '%m-%d-%y %H:%M:%S'
        eventTime = datetime.strptime(event.message.forward.date.strftime(timeFormat), timeFormat)
        CurrTime = datetime.utcnow().strftime(timeFormat)
        CurrTime = datetime.strptime(CurrTime, timeFormat)

        if (CurrTime - eventTime).total_seconds() > 600:
            await event.reply("Old. Max 10 mins older.")
            raise events.StopPropagation

        vars.cur.execute("SELECT * from glory;")
        x = vars.cur.fetchall()
        RemBtls = x[0][0]
        TargetGlory = 16000
        CurrentGlory = int(re.findall(r"🎖Glory: (\d+)", event.raw_text)[0])
        GainedGlory = CurrentGlory - x[0][1]
        vars.cur.execute(f"UPDATE glory SET glory_gained={CurrentGlory};")
        vars.conn.commit()
        RemainingGlory = TargetGlory - CurrentGlory
        string = "Remaining glory : " + str(RemainingGlory) + "\n" + "Required glory per battle : " + \
                 str(round(RemainingGlory / RemBtls)) + "\nBattles remaining : " + str(RemBtls) + "\n" + \
                 "Glory Gained : " + str(GainedGlory)
        await event.reply(string)
        raise events.StopPropagation
