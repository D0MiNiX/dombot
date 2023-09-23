from vars import bot, dom, BOT_POD_GRP, CW_BOT, DOMBOT
from backup_job import get_job_sched
import asyncio, re

new_job_id = None

def sched_new_job():
    global new_job_id
    job_sched = get_job_sched()
    new_job_id = job_sched.add_job(remind_glory, "interval", minutes=15).id

async def remind_glory():
    global new_job_id
    resp = ""
    msg_cw, resp_cw = "", ""

    if new_job_id:
        job_sched = get_job_sched()
        job_sched.remove_job(new_job_id)
        new_job_id = None

    try:
        async with dom.conversation(CW_BOT) as conv:
            msg_cw = await conv.send_message("👥Guild")
            resp_cw = await conv.get_response()
    except asyncio.exceptions.TimeoutError:
        sched_new_job()
        return

    glory_regex = re.compile(r"^.*?Glory: \d+/\d+", flags=re.S)

    if not glory_regex.search(resp_cw.raw_text):
        sched_new_job()
        return

    try:
        async with dom.conversation(DOMBOT) as conv:
            msg_reminder = await conv.send_message("Glory reminder time!")
            msg_fwd = await dom.forward_messages(DOMBOT, resp_cw.id, from_peer=CW_BOT)
            await dom.delete_messages(CW_BOT, [msg_reminder.id, msg_cw.id, resp_cw.id])
            resp = await conv.get_response()
            await dom.delete_messages(DOMBOT, [msg_fwd.id, resp.id])
            resp = resp.raw_text
    except asyncio.exceptions.TimeoutError:
        return

    if "Remaining glory:" in resp:
        await bot.send_message(BOT_POD_GRP, resp)
