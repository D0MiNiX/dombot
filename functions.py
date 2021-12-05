import sys
import time
import re
from telethon import events
import vars

def CurrentTime():
    return str(vars.datetime.now().strftime("%H:%M:%S"))

def RestartBot():
    vars.os.execl(sys.executable, sys.executable, *sys.argv)

def delay(sleep_time):
    time.sleep(sleep_time)

async def fun(event, **args):
    msg = ''
    for x in args.values():
        for i, k in x.items():
            msg += '# ' + str(i) + '\n\t\t\t╰ ' + '`' + str(k) + '`' + '\n'
    await event.respond(msg.strip())

def Command(in_text, text):
    if in_text.split(" ", 1)[0] == text:
        return True

# checks if there are any strings from the list in the given text
def list_string_in_text(text, lst):
    if any([k for k in lst if k in text]):
        return True
    else:
        return False

def command(text, cmd):
    if re.match(r"^/{}({})*$".format(cmd, vars.bot_tag), text):
        return True
    else:
        return False

def command_with_args(text, cmd):
    if re.match(r"^/{0}({1})*$|^/{0}({1})*\s+.*".format(cmd, vars.bot_tag), text):
        return True
    else:
        return False

async def cleanup(event, db=None, text=None):
    if text is not None:
        await event.reply(text)
    if db is not None:
        db.close_all()
    raise events.StopPropagation

async def check_db_error(db, event, exc, dummy_list=[], return_error=False):
    if isinstance(exc, Exception):
        err = exc.args[0]
        if err.startswith("UNIQUE") or err.startswith("no results fetched") or "is not unique" in err:
            dummy_list.append(1)
        else:
            if return_error:
                return err
            await cleanup(event, db, "Error in db.\n{}".format(err))
