import vars
import shutil
import arrow
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os


DOMBOT_BACKUP_CHANNEL = -1001463171286


async def create_and_send_backup():
    current_time = arrow.now().format("DD_MM_YYYY-HH_mm_ss")
    home_path = os.path.expanduser("~")
    zip_file_name = f"{home_path}/dombot_backup_{current_time}"
    zip_file_path = shutil.make_archive(zip_file_name, "zip", f"{home_path}/dombot")
    await vars.bot.send_file(DOMBOT_BACKUP_CHANNEL, file=f"{zip_file_path}")
    
    if os.path.exists(zip_file_path):
       os.remove(zip_file_path)


def create_backup_job():
    scheduler = AsyncIOScheduler()
    scheduler.configure(timezone="Asia/Kolkata")
    scheduler.start()
    scheduler.add_job(create_and_send_backup, 'cron', hour='20', minute='00')
