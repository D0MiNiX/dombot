import asyncio
import re
from telethon import events
from telethon.tl import functions
from datetime import datetime, timedelta
from functions import DBError
import vars
import aiocron
import psycopg2
from collections import Counter


JASPER_DRAGON = -1001479733593
JASPER_DRAGON_WAR = -1001478762021
SHARE_URL = "t.me/share/url?url="
CastlesDict = {
    "sharkteeth": '🦈', "dragonscale": '🐉', "highnest": '🦅', "wolfpack": '🐺',
    "potato": '🥔', "moonlight": '🌑', "deerhorn": '🦌'
}

TotalAttack = TotalDefense = 0
MasterDict = {}
ReportsList = []
Evntlst = []
dct = {}
JAPER_DRAGON_REPORTS = -1001156435493
alliance_names_and_points = {}


@events.register(events.NewMessage(chats=[vars.D0MiNiX, JASPER_DRAGON_WAR, JASPER_DRAGON, JAPER_DRAGON_REPORTS]))
async def alliance(event):

    global TotalAttack, TotalDefense, MasterDict, ReportsList
    incomingText = event.raw_text

    if event.message.forward is not None and event.message.forward.from_id.user_id == vars.CW_BOT and \
            "Your result on the battlefield:" in incomingText:

        if event.chat_id == JAPER_DRAGON_REPORTS:
            await asyncio.sleep(3)

        time_format = '%m-%d-%y %H:%M:%S'
        event_time = datetime.strptime(event.message.forward.date.strftime(time_format), time_format)
        curr_time = datetime.utcnow().strftime(time_format)
        curr_time = datetime.strptime(curr_time, time_format)

        if await CheckTime(curr_time, event_time, time_format, mins_offset=0) == 0:
            await event.reply("No.")
            raise events.StopPropagation

        Stats = incomingText.split("\n")
        PlayerName = re.findall(r'.* ⚔', Stats[0])
        PlayerName = PlayerName[0].replace(" ⚔", "")
        Glist = ["SP", "LAN", "HAV", "FYT", "4NF", "GT", "XXX"]
        GuildName = re.findall(r'\[(.*?)\]', PlayerName)[0]
        if GuildName not in Glist:
            await event.reply("spai spai spai...")
            raise events.StopPropagation

        for x in ReportsList:
            if PlayerName in x[0]:
                if event.chat_id != JAPER_DRAGON_REPORTS:
                    await event.reply("Guess, I already saved {}'s stats 🤔. Deleting...".format(PlayerName))
                await event.delete()
                raise events.StopPropagation

        if not re.search(r"🔥Exp: \d+", incomingText):
            await event.reply("{} didn't attend battle :(\n"
                              "No need to send the report in that case :)".format(PlayerName))
            await event.delete()
            raise events.StopPropagation

        PlayerAttack = int(re.findall(r'⚔:(\d+)', Stats[0])[0])
        PlayerDefence = int(re.findall(r'🛡:(\d+)', Stats[0])[0])
        PlayerLevel = int(re.findall(r'Lvl: (\d+)', Stats[0])[0])
        TotalAttack = TotalAttack + PlayerAttack
        TotalDefense = TotalDefense + PlayerDefence
        EvntChtID = str(event.chat.id)

        Attribute = ""
        if "Critical strike" in event.text:
            Attribute = Attribute + ("⚡CS" if Attribute == "" else " + ⚡CS")
        if "You were healed by" in event.text:
            Attribute = Attribute + ("⚗️" if Attribute == "" else " + ⚗")
        if "You were poisoned by" in event.text:
            Attribute = Attribute + ("☠️" if Attribute == "" else " + ☠")
        if "Your taunts were successful" in event.text:
            Attribute = Attribute + ("🎩" if Attribute == "" else " + 🎩")
        if "You were outplayed by" in event.text:
            Attribute = Attribute + ("⚔️" if Attribute == "" else " + ⚔️")
        if "Lucky Defender" in event.text:
            Attribute = Attribute + ("⚡LD" if Attribute == "" else " + ⚡️LD")
        if "Battle Cry. You were inspired by" in event.text:
            Attribute = Attribute + ("⚡BC" if Attribute == "" else " + ⚡️BC")

        for x in event.raw_text.split("\n"):
            if re.match(r'You outplayed (\S).* by ⚔(\S+)', x):
                outplay = re.findall(r'You outplayed (\S).* by ⚔(\S+)', x)
                outplay = "⚔️OP " + outplay[0][0] + outplay[0][1]
                Attribute = Attribute + (outplay if Attribute == "" else (" + " + outplay))
                break

        event.text = (re.sub(r'\s+⚔:(\d+).*', "", event.text))
        if event.chat_id != JAPER_DRAGON_REPORTS:
            RespID = await event.respond(event.text)
            ReportsList.append([PlayerName, PlayerAttack, PlayerDefence, PlayerLevel, EvntChtID, str(RespID.id),
                                Attribute])
            WriteAlliance(PlayerName, PlayerAttack, PlayerDefence, PlayerLevel, EvntChtID, str(RespID.id), Attribute)
            await event.delete()
        else:
            RespID = str(event.id)
            ReportsList.append([PlayerName, PlayerAttack, PlayerDefence, PlayerLevel, EvntChtID, RespID,
                                Attribute])
            WriteAlliance(PlayerName, PlayerAttack, PlayerDefence, PlayerLevel, EvntChtID, RespID, Attribute)
        raise events.StopPropagation

    elif incomingText == "/cal_stats":
        if event.chat_id == JASPER_DRAGON:
            raise events.StopPropagation
        await CalStats(event)
        raise events.StopPropagation

    elif incomingText == "/clear_stats":
        if event.chat_id == JASPER_DRAGON:
            raise events.StopPropagation
        ReportsList.clear()
        DeleteAlliance()
        await event.reply("Reports cleared.")
        raise events.StopPropagation

    elif event.message.forward is not None and event.message.forward.from_id.user_id == vars.CW_BOT and \
            "Last shared balance report:" in incomingText:

        if not (event.chat_id == JASPER_DRAGON or event.chat_id == vars.D0MiNiX):
            raise events.StopPropagation

        time_format = '%m-%d-%y %H:%M:%S'
        event_time = datetime.strptime(event.message.forward.date.strftime(time_format), time_format)
        curr_time = datetime.utcnow().strftime(time_format)
        curr_time = datetime.strptime(curr_time, time_format)
        time = None

        # Check forwarded message time
        if await CheckTime(curr_time, event_time, time_format, mins_offset=30) == 0:
            await event.reply("No. Old?")
            raise events.StopPropagation

        # Check the last sent report with the current timing
        qry = "SELECT report_upd FROM alliance_stocks order by report_upd ASC;"
        try:
            vars.cur.execute(qry)
            LastReportTime = vars.cur.fetchone()[0]
            if curr_time.hour == 23 or 0 <= curr_time.hour <= 6:
                time = 23
                qry = "UPDATE alliance_stocks SET report_upd=23;"
            elif 7 <= curr_time.hour <= 14:
                time = 7
                qry = "UPDATE alliance_stocks SET report_upd=7;"
            elif 15 <= curr_time.hour <= 22:
                time = 15
                qry = "UPDATE alliance_stocks SET report_upd=15;"
            if time == LastReportTime:
                await event.reply("Seems like this report has already been saved.")
                raise events.StopPropagation
        except psycopg2.Error as Err:
            DBError(vars.conn, Err)

        # Update the last send battle time if everything is ok
        try:
            vars.cur.execute(qry)
            vars.conn.commit()
        except psycopg2.Error as Err:
            DBError(vars.conn, Err)

        # Storing stock and its respective quantity in DB
        rx_outer = re.compile(r'''
            \[(?P<section>[^][]+)\]
            (?P<content>(?:.+[\r\n]?)+)
            ''', re.M | re.X)

        rx_inner = re.compile(r'[^\n\s](\S+.*)\s(\d+)|\S+:\d+')

        result = [[section] + [value.group(0) for value in rx_inner.finditer(outer.group('content'))]
                  for outer in rx_outer.finditer(event.raw_text)
                  for section in [outer.group('section')]]

        GloryPattern = re.compile(r"(🎖Glory):(\d+)")
        StockPattern = re.compile(r"(\S+\w+.*)\s(\d+)")

        for stuff in result:
            GuildName = stuff.pop(0)
            if GuildName[0].isdigit():
                val = '"{}"'
            else:
                val = '{}'
            if GuildName not in dct.keys():
                dct[GuildName] = {}
                DbQuery(('ALTER TABLE alliance_stocks ADD COLUMN ' + val +
                                     ' integer default 0;').format(GuildName))
                await event.reply("New guild detected. Welcome {}. I spai bot. Thx.".format(GuildName))

            for stocks in stuff:
                StockName = StockQuant = None
                if re.search(GloryPattern, stocks):
                    StockName = re.findall(GloryPattern, stocks)[0][0]
                    StockQuant = int(re.findall(GloryPattern, stocks)[0][1])
                elif re.search(StockPattern, stocks):
                    StockName = re.findall(StockPattern, stocks)[0][0]
                    StockQuant = int(re.findall(StockPattern, stocks)[0][1])

                if StockName is None and StockQuant is None:
                    continue

                if StockName in dct[GuildName]:
                    dct[GuildName][StockName] += StockQuant
                else:
                    result = DbQuery("SELECT stocks FROM alliance_stocks;")
                    if StockName not in [data[0] for data in result]:
                        DbQuery("INSERT INTO alliance_stocks(stocks) VALUES('{}');".
                                format(StockName))
                        DbQuery("UPDATE alliance_stocks SET report_upd={} WHERE stocks='{}';".
                                format(time, StockName))
                    dct[GuildName][StockName] = StockQuant

                DbQuery(("UPDATE alliance_stocks SET " + val + "={} WHERE stocks='{}';")
                        .format(GuildName, dct[GuildName][StockName], StockName))

        await event.reply("Saved. Updated stocks as below.\n\n" + GetStocks())
        raise events.StopPropagation

    elif incomingText == "/get_stocks":
        await event.reply(GetStocks())
        raise events.StopPropagation

    elif event.message.forward is not None and event.message.forward.from_id.user_id == vars.CW_BOT and \
            "🤝Alliances top:" in incomingText:

        if not (event.chat_id == JASPER_DRAGON or event.chat_id == vars.D0MiNiX):
            raise events.StopPropagation

        global alliance_names_and_points

        time_format = '%m-%d-%y %H:%M:%S'
        event_time = datetime.strptime(event.message.forward.date.strftime(time_format), time_format)
        curr_time = datetime.utcnow().strftime(time_format)
        curr_time = datetime.strptime(curr_time, time_format)

        # Check forwarded message time
        if await CheckTime(curr_time, event_time, time_format, mins_offset=30) == 0:
            await event.reply("No. Old?")
            raise events.StopPropagation

        # Check the last sent /ga_top1 with the current timing
        qry = "SELECT time_upd FROM alliance_tops ORDER BY time_upd ASC;"
        try:
            vars.cur.execute(qry)
            LastReportTime = vars.cur.fetchone()[0]
            time = None
            if curr_time.hour == 23 or 0 <= curr_time.hour <= 6:
                time = 23
                qry = "UPDATE alliance_tops SET time_upd=23;"
            elif 7 <= curr_time.hour <= 14:
                time = 7
                qry = "UPDATE alliance_tops SET time_upd=7;"
            elif 15 <= curr_time.hour <= 22:
                time = 15
                qry = "UPDATE alliance_tops SET time_upd=15;"
            if time == LastReportTime:
                await event.reply("Seems like this report has already been saved.")
                raise events.StopPropagation
        except psycopg2.Error as Err:
            DBError(vars.conn, Err)

        # Update the last send time if everything is ok
        try:
            vars.cur.execute(qry)
            vars.conn.commit()
        except psycopg2.Error as Err:
            DBError(vars.conn, Err)

        alliance_names = re.findall(r"\d+ (\D+) ", event.raw_text)
        alliance_points = [float(k[0] + k[1] + k[2]) for k in re.findall(r"\w+\s+(\d+)*(\.)*(\d+)", event.raw_text)]
        alliance_names_and_points_local = dict(zip(alliance_names, alliance_points))
        res = {key: float((alliance_names_and_points_local[key] - alliance_names_and_points.get(key, 0)))
               .__format__(".2f") for key in alliance_names_and_points_local.keys()}

        for new_alliance_name in alliance_names:
            if new_alliance_name not in alliance_names_and_points.keys():
                alliance_names_and_points[new_alliance_name] = alliance_names_and_points_local[new_alliance_name]
                last_time_upd = int(DbQuery("SELECT time_upd from alliance_tops")[0][0])
                DbQuery("INSERT INTO alliance_tops(name, points, time_upd) VALUES ('{}', '{}', {});"
                        .format(new_alliance_name, alliance_names_and_points_local[new_alliance_name], last_time_upd))

        # alliance_names_and_points = alliance_names_and_points_local

        string = ""
        num = 1
        inc_dec = ""

        for name, change in res.items():
            if float(change) > 0:
                inc_dec = "↑"
            elif float(change) < 0:
                inc_dec = "↓"
            if float(change) != 0:
                string += (str(num) + ". " + name + " " + change + inc_dec + "\n")
                num += 1

        if string != "":
            await event.reply("Following change(s) detected:\n" + string)
        else:
            await event.reply("No change. Jajajajaja...")

        for name, points in alliance_names_and_points_local.items():
            DbQuery("UPDATE alliance_tops SET points='{}' WHERE name='{}';".format(points, name))

        raise events.StopPropagation


def DbQuery(query):
    try:
        vars.cur.execute(query)
        if query.startswith("SELECT"):
            data = vars.cur.fetchall()
            return data
        vars.conn.commit()
    except psycopg2.Error as Err:
        DBError(vars.conn, Err)


def GetStocks():
    string = ""

    total_items = dct.items()

    # Per guild stock string
    def per_guild_stock_calc(item):
        return item[0], [(k + " : " + str(z)) for k, z in sorted(item[1].items(), key=lambda i: i[0]) if z != 0]

    result = (sorted(list(map(per_guild_stock_calc, total_items)), key=lambda i: i[0]))
    for items in result:
        string += (items[0] if items[1] else "") + ("\n" + " "*5) + ("\n     ".join(items[1])) + "\n\n"

    # Total stock gains
    string += "Total gains:\n"

    def func(item):
        return Counter(item[1])

    result = list(map(func, total_items))
    final_dict = Counter({})

    for results in result:
        final_dict = final_dict + results

    sorted_dict = [j[0] + " : " + str(j[1]) for j in (sorted(final_dict.items(), key=lambda i: i[0]))]
    string += (" "*5) + "\n     ".join(sorted_dict)
    return string


async def CheckTime(cur_time, evt_time, timefmt, mins_offset=0):    # Minutes offset for ga_balance reports
    # 00:00 to 06:59
    dt = (datetime.utcnow().date() + timedelta(days=-1)).strftime("%m-%d-%y")
    dt_t = dt + " 23:0:0"
    UTC23RefAt23Plus = datetime.strptime(dt_t, timefmt) + timedelta(minutes=mins_offset)

    # 23:00 to 23:59
    UTC23RefAt23 = datetime.strptime(datetime.utcnow().date().strftime("%m-%d-%y") + " 23:0:0", timefmt) + \
                   timedelta(minutes=mins_offset)

    # 07:00 to 14:59
    UTC7Ref = datetime.strptime(datetime.utcnow().date().strftime("%m-%d-%y") + " 7:0:0", timefmt) + \
              timedelta(minutes=mins_offset)

    # 15:00 to 22:59
    UTC15Ref = datetime.strptime(datetime.utcnow().date().strftime("%m-%d-%y") + " 15:0:0", timefmt) + \
               timedelta(minutes=mins_offset)

    if cur_time < evt_time:
        return 0

    if cur_time < UTC23RefAt23Plus:
        return 0

    EIGHT_HRS = 28800

    if 0 <= cur_time.hour < 7:

        if evt_time < UTC23RefAt23Plus:
            return 0

        if (evt_time - UTC23RefAt23Plus).total_seconds() > EIGHT_HRS or \
                (cur_time - evt_time).total_seconds() > EIGHT_HRS:
            return 0

    elif 7 <= cur_time.hour < 15:

        if evt_time < UTC7Ref:
            return 0

        if (evt_time - UTC7Ref).total_seconds() > EIGHT_HRS or \
                (cur_time - evt_time).total_seconds() > EIGHT_HRS:
            return 0

    elif 15 <= cur_time.hour < 23:

        if evt_time < UTC15Ref:
            return 0

        if (evt_time - UTC15Ref).total_seconds() > EIGHT_HRS or \
                (cur_time - evt_time).total_seconds() > EIGHT_HRS:
            return 0

    elif cur_time.hour == 23:

        if evt_time < UTC23RefAt23:
            return 0

        if (evt_time - UTC23RefAt23).total_seconds() > EIGHT_HRS or \
                (cur_time - evt_time).total_seconds() > EIGHT_HRS:
            return 0

    return 1


"""
# Inform about /ga_balance_report and /ga_top1
@aiocron.crontab("25 2,10,18 * * *")
async def Notify():
    # Report time update for balance report
    qry = "SELECT report_upd FROM alliance_stocks ORDER BY report_upd ASC;"
    try:
        vars.cur.execute(qry)
        LastReportTime = vars.cur.fetchone()[0]
        EightHrCheck = datetime.strptime(datetime.utcnow().strftime("%m-%d-%y %H:%M:%S"),
                                         '%m-%d-%y %H:%M:%S') + timedelta(hours=-8)
        if EightHrCheck.hour != LastReportTime:
            await vars.bot.send_message(JASPER_DRAGON,
                                        "Genial, qué interesante."
                                        "Ninguno de los líderes compartió los últimos informes de balance aquí 😢.")
    except psycopg2.Error as Err:
        DBError(vars.conn, Err)

    # Report time update for /ga_top1
    qry = "SELECT time_upd FROM alliance_tops ORDER BY time_upd ASC;"
    try:
        vars.cur.execute(qry)
        LastReportTime = vars.cur.fetchone()[0]

        EightHrCheck = datetime.strptime(datetime.utcnow().strftime("%m-%d-%y %H:%M:%S"),
                                         '%m-%d-%y %H:%M:%S') + timedelta(hours=-8)
        if EightHrCheck.hour != LastReportTime:
            await vars.bot.send_message(JASPER_DRAGON,
                                        "Donde esta mi /ga_top1. Estoy llorando 😭.")
    except psycopg2.Error as Err:
        DBError(vars.conn, Err)
"""


@aiocron.crontab("32 4,12,20 * * *")
async def ClearReports():
    global JASPER_DRAGON
    ReportsList.clear()
    DeleteAlliance()
    await vars.bot.send_message(JASPER_DRAGON_WAR, "Reports cleared.")
    try:
        FCR = await vars.bot(functions.channels.GetFullChannelRequest(channel=JASPER_DRAGON))
        MR = await vars.bot(functions.channels.GetMessagesRequest
                            (channel=JASPER_DRAGON, id=[FCR.full_chat.pinned_msg_id]))
        if MR.messages[0].from_id == vars.DOMBOT:
            await vars.bot.pin_message(JASPER_DRAGON, message=None)
    except:
        pass

    # Report time update for next balance report
    qry = "SELECT report_upd FROM alliance_stocks ORDER BY report_upd ASC;"
    try:
        vars.cur.execute(qry)
        LastReportTime = vars.cur.fetchone()[0]

        EightHrCheck = datetime.strptime(datetime.utcnow().strftime("%m-%d-%y %H:%M:%S"),
                                         '%m-%d-%y %H:%M:%S') + timedelta(hours=-8)
        if EightHrCheck.hour != LastReportTime:
            await vars.bot.send_message(JASPER_DRAGON,
                                        "Baaaaad people. Despite of reminder, no one sent the "
                                        "/ga_balance_report 🚶‍♂️.")
            qry = "UPDATE alliance_stocks SET report_upd={};".format(EightHrCheck.hour)
            vars.cur.execute(qry)
            vars.conn.commit()
    except psycopg2.Error as Err:
        DBError(vars.conn, Err)

    # Report time update for next /ga_top1
    qry = "SELECT time_upd FROM alliance_tops ORDER BY time_upd ASC;"
    try:
        vars.cur.execute(qry)
        LastReportTime = vars.cur.fetchone()[0]

        EightHrCheck = datetime.strptime(datetime.utcnow().strftime("%m-%d-%y %H:%M:%S"),
                                         '%m-%d-%y %H:%M:%S') + timedelta(hours=-8)
        if EightHrCheck.hour != LastReportTime:
            await vars.bot.send_message(JASPER_DRAGON,
                                        "/ga_top1, where? 😡")
            qry = "UPDATE alliance_tops SET time_upd={};".format(EightHrCheck.hour)
            vars.cur.execute(qry)
            vars.conn.commit()
    except psycopg2.Error as Err:
        DBError(vars.conn, Err)

    # Glory Update
    try:
        vars.cur.execute("SELECT * from glory;")
        y = vars.cur.fetchall()
        RemBat = y[0][0] - 1
        qryy = "UPDATE glory SET rem_btl=%s;"
        data = (RemBat,)
        vars.cur.execute(qryy, data)
        vars.conn.commit()
    except psycopg2.Error as e:
        vars.conn.rollback()
        print("Couldn't execute query. Using variable's default values. Error code : {}".format(e.pgcode))


def WriteAlliance(name, atk, defc, lvl, chat_id, evnt_id, attrib):
    try:
        query = "INSERT INTO alliance VALUES (%s, %s, %s, %s, %s, %s, %s);"
        data = (name, atk, defc, lvl, chat_id, evnt_id, attrib,)
        vars.cur.execute(query, data)
        vars.conn.commit()
    except psycopg2.Error as xs:
        DBError(vars.conn, xs)
        return


def DeleteAlliance():
    try:
        query = "DELETE FROM alliance;"
        vars.cur.execute(query)
        vars.conn.commit()
    except psycopg2.Error as xv:
        DBError(vars.conn, xv)
        return


async def CalStats(event):
    OverallAttack = OverallDefence = 0
    string = ""

    if len(ReportsList) == 0:
        if event is not None:
            await event.reply("No reports found.")
        else:
            await vars.bot.send_message(JASPER_DRAGON_WAR, "No reports found.")
        return

    SortedList = sorted(ReportsList, key=lambda i: i[3])
    LowList, MidList, HighList = [], [], []
    LowAttack = LowDefence = MidAttack = MidDefence = HighAttack = HighDefence = 0

    for x in SortedList:

        if 20 <= x[3] < 40:
            LowList.append([x[0], str(x[1]), str(x[2]), str(x[3]), x[4], x[5], x[6]])
            LowAttack = LowAttack + x[1]
            LowDefence = LowDefence + x[2]

        if 40 <= x[3] <= 60:
            MidList.append([x[0], str(x[1]), str(x[2]), str(x[3]), x[4], x[5], x[6]])
            MidAttack = MidAttack + x[1]
            MidDefence = MidDefence + x[2]

        if x[3] > 60:
            HighList.append([x[0], str(x[1]), str(x[2]), str(x[3]), x[4], x[5], x[6]])
            HighAttack = HighAttack + x[1]
            HighDefence = HighDefence + x[2]

        OverallAttack = OverallAttack + x[1]
        OverallDefence = OverallDefence + x[2]

    string = string + "Report history from the last battle.\n" \
                      "Format - Name : Attack, Defence, Level.\n\n"

    if len(LowList) > 0:
        string = string + "🐣**Low Level (20-40):**\n"
        for x in LowList:
            string = string + GenStr(x[0], x[1], x[2], x[4], x[5], x[6])
        string = string + "\n"
        string = string + "🐣Total Atk: " + str(LowAttack) + ", Total Def: " + str(LowDefence) + \
                 "\nTotal Reports: " + str(len(LowList)) + "\n\n"

    if len(MidList) > 0:
        string = string + "🐴**Mid Level (40-60):**\n"
        for x in MidList:
            string = string + GenStr(x[0], x[1], x[2], x[4], x[5], x[6])
        string = string + "\n"
        string = string + "🐴Total Atk: " + str(MidAttack) + ", Total Def: " + str(MidDefence) + \
                 "\nTotal Reports: " + str(len(MidList)) + "\n\n"

    if len(HighList) > 0:
        string = string + "🦁**High Level (60+):**\n"
        for x in HighList:
            string = string + GenStr(x[0], x[1], x[2], x[4], x[5], x[6])
        string = string + "\n"
        string = string + "🦁Total Atk: " + str(HighAttack) + ", Total Def: " + str(HighDefence) + \
                 "\nTotal Reports: " + str(len(HighList)) + "\n\n"

    OvrSt = "⚔️**Overall Attack : " + str(OverallAttack) + "\n🛡️Overall Defence : " + str(OverallDefence) + \
            "\n📋Total Reports sent : " + str(len(LowList) + len(MidList) + len(HighList)) + "**"

    if event is not None:
        await event.reply((string + OvrSt))
    else:
        await vars.bot.send_message(JASPER_DRAGON_WAR, (string + OvrSt))


def GenStr(a, b, c, e, f, g):
    return "[" + a + "](https://t.me/c/" + e + "/" + f + ")" + " : " + \
            str(b) + ", " + \
            str(c) + (("\n\t\t\t\t\t\t╰" + str(g)) if g != "" else "") + "\n"


try:
    qry = "SELECT * FROM alliance;"
    vars.cur.execute(qry)
    for n in vars.cur.fetchall():
        ReportsList.append([n[0], n[1], n[2], n[3], n[4], n[5], (n[6] if n[6] is not None else "")])
except psycopg2.Error as zz:
    DBError(vars.conn, zz)


aiocron.crontab("29 4,12,20 * * *", args=(None,), start=True, func=CalStats)

qry = "SELECT column_name FROM information_schema.COLUMNS WHERE table_name='alliance_stocks';"
vars.cur.execute(qry)
xx = vars.cur.fetchall()
for cc in xx:
    if len(cc[0]) > 3:
        continue
    dct[cc[0].upper()] = {}

for x in dct.keys():
    if x[0].isdigit():
        qry = 'SELECT stocks, "{}" from alliance_stocks order by stocks;'.format(x)
    else:
        qry = "SELECT stocks, {} from alliance_stocks order by stocks;".format(x)

    vars.cur.execute(qry)
    xx = vars.cur.fetchall()
    for xxx in xx:
        dct[x][xxx[0]] = xxx[1]

# GA tops
c = DbQuery("SELECT * FROM alliance_tops")
for v in c:
    alliance_names_and_points[v[0]] = float(v[1])
alliance_names_and_points = dict(sorted(alliance_names_and_points.items(), key=lambda i: float(i[1]), reverse=True))
