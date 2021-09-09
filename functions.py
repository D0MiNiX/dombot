import sys
import time
import re
from telethon import events
import psycopg2
import vars


def CurrentTime():
    return str(vars.datetime.now().strftime("%H:%M:%S"))


def RestartBot():
    vars.os.execl(sys.executable, sys.executable, *sys.argv)


def delay(sleep_time):
    time.sleep(sleep_time)


def WriteToDB(*db_list):
    import psycopg2
    for x in db_list:
        qry = "UPDATE variables SET var_value = '{}' WHERE var_name = '{}';".format(x[1], x[0])
        try:
            vars.cur.execute(qry)
            vars.conn.commit()
        except psycopg2.Error as e:
            print("Couldn't update table. Error writing values. Error code : {}".format(e.pgcode))
            sys.stdout.flush()
            break


async def fun(event, **args):
    msg = ''
    for x in args.values():
        for i, k in x.items():
            msg += '# ' + str(i) + '\n\t\t\t╰ ' + '`' + str(k) + '`' + '\n'
    await event.respond(msg.strip())


def Command(in_text, text):
    if in_text.split(" ", 1)[0] == text:
        return True


def DBError(conn, exc):
    conn.rollback()
    # print("Couldn't execute query. Error code : {}".format(exc.pgcode))
    sys.stdout.flush()
    return exc.pgcode


def DbQuery(query, row_count=0):
    try:
        vars.cur.execute(query)
        if query.startswith("SELECT"):
            data = vars.cur.fetchall()
            return data
        vars.conn.commit()
        if row_count == 1:
            return vars.cur.rowcount
    except psycopg2.Error as Err:
        return DBError(vars.conn, Err)


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
    if re.match(r"^/{0}({1})*$|^/{0}({1})*\s+.*$".format(cmd, vars.bot_tag), text):
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
