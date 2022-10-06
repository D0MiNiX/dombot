import vars
import shutil
import arrow
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os
from dombot.monsters import r

DOMBOT_BACKUP_CHANNEL = -1001463171286
job_scheduler = AsyncIOScheduler()

async def create_and_send_backup():
    dir_name = os.path.basename(os.getcwd())
    current_time = arrow.now().format("DD_MM_YYYY-HH_mm_ss")
    bot_dir = os.getcwd()
    os.chdir("..")
    curr_dir = os.getcwd()
    zip_file_name = f"{curr_dir}/dombot_backup_{current_time}"
    zip_file_path = shutil.make_archive(zip_file_name, "zip", f"{curr_dir}/{dir_name}")
    await vars.bot.send_file(DOMBOT_BACKUP_CHANNEL, file=f"{zip_file_path}")
    os.chdir(bot_dir)

    if os.path.exists(zip_file_path):
        try:
            os.remove(zip_file_path)
        except Exception as e:
            print("Failed remove: ", e)

async def rdb_backup():
    r.bgsave()

def get_job_sched():
    global job_scheduler
    return job_scheduler

def create_backup_job():
    from user_bot.vpb_reminder import remind_vpb
    global job_scheduler, vpb_job_id
    job_scheduler.configure(timezone="Asia/Kolkata")
    job_scheduler.start()
    job_scheduler.add_job(create_and_send_backup, 'cron', hour='20', minute='00')
    job_scheduler.add_job(rdb_backup, 'cron', hour="*", minute="*/30", misfire_grace_time=None)
    job_scheduler.add_job(remind_vpb, 'cron', hour=21, minute=0, misfire_grace_time=None)
