import re
import sys
from datetime import datetime
from functions import Command, RestartBot, CurrentTime, fun, delay
import psycopg2
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon import events
import vars as bot_vars
import aiocron
from dombot.start import spam_dict


# test
@events.register(events.NewMessage(chats=[bot_vars.D0MiNiX],
                                   from_users=[bot_vars.D0MiNiX], forwards=False))
async def admin_only(event):

    incomingText = event.text
    IncomingRawText = event.raw_text

    if incomingText == '/bot_status':
        await fun(
            event,
            RunSince={"Running since": str(bot_vars.runSinceDate) + ', ' + str(bot_vars.runSinceTime)}
        )
        raise events.StopPropagation

    elif Command(incomingText, '/whois'):
        expression = incomingText.replace('/whois', '')
        expression = "".join(expression.split())
        cgTitle = 0
        msg = ''

        try:
            int(expression)
            user = await bot_vars.bot.get_entity(int(expression))
            try:
                full = await bot_vars.bot(GetFullUserRequest(int(expression)))
            except:
                full = await bot_vars.bot(GetFullChannelRequest(int(expression)))
                cgTitle = 1
        except:
            uid = await bot_vars.bot.get_input_entity(expression)
            try:
                user = await bot_vars.bot.get_entity(uid.user_id)
                full = await bot_vars.bot(GetFullUserRequest(expression))
            except:
                user = await bot_vars.bot.get_entity(uid.channel_id)
                full = await bot_vars.bot(GetFullChannelRequest(expression))
                cgTitle = 1

        if not cgTitle:
            msg = '`Username   : `' + '@' + str(user.username) + '\n' + \
                  '`User ID    : `' + '`' + str(user.id) + '`' + '\n' + \
                  '`First Name : `' + '`' + str(user.first_name) + '`' + '\n' + \
                  (('`Last Name  : `' + '`' + str(user.last_name) + '`' + '\n')
                   if user.last_name is not None else '') + \
                  '`Last seen  : `' + '`' + str(user.status) + '`' + '\n' + \
                  '`Bio        : `' + '\n' + '`' + str(full.about) + '`'

        elif cgTitle:
            msg = '`Title : ' + str(user.title) + '`' + '\n' + \
                  '`Link  : `@' + str(user.username) + '\n' + \
                  '`ID    : ' + str(user.id) + '`' + '\n' + \
                  '`Desc  : \n' + str(full.full_chat.about) + '`'

        await event.reply(msg)
        raise events.StopPropagation

    elif Command(incomingText, "/send_msg"):
        expression = incomingText.split(" ", 2)
        entityToSend = expression[1]
        if entityToSend.isdigit():
            entityToSend = int(expression[1])
        try:
            await bot_vars.bot.send_message(entityToSend, expression[2])
        except:
            await event.reply("Couldn't send.")
        raise events.StopPropagation

    elif Command(IncomingRawText, "/sql"):
        qry = IncomingRawText.split(" ", 1)[1]

        try:
            bot_vars.cur.execute(qry)
        except psycopg2.Error as e:
            bot_vars.conn.rollback()
            await event.reply('Error : {}'.format(e.pgcode))
            raise events.StopPropagation

        qry = ""
        try:
            if bot_vars.cur.statusmessage.startswith('SELECT'):
                stsMsg = len(bot_vars.cur.description)  # re.findall(r'\d+', bot_vars.cur.statusmessage)
                for x in bot_vars.cur.fetchall():
                    for y in range(0, stsMsg):
                        qry += str(x[y]) + (' - ' if y < (stsMsg - 1) else '')
                    qry += '\n\n'
                await event.reply('Rows affected : ' + str(bot_vars.cur.rowcount) + '\n\n' + qry, parse_mode=None)
                raise events.StopPropagation
            else:
                bot_vars.conn.commit()
                await event.reply('Query executed successfully. Rows affected : ' + str(bot_vars.cur.rowcount))
                raise events.StopPropagation

        except psycopg2.Error as e:
            bot_vars.conn.rollback()
            await event.reply('Error : {}'.format(e.pgcode))
            raise events.StopPropagation

    elif incomingText == "/restart":
        delay(0.5)
        await event.respond('`Restarting bot...`')
        print('Restarting bot...', CurrentTime())
        RestartBot()

    elif incomingText == "/get_users":
        users = [str(k) for k in spam_dict.keys()]
        string = ", ".join(users)
        await event.reply(string)
        raise events.StopPropagation
