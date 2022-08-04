import vars
import shutil
import arrow
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os, zipfile


DOMBOT_BACKUP_CHANNEL = -1001463171286


async def create_and_send_backup():
    dir_name = os.path.basename(os.getcwd())
    current_time = arrow.now().format("DD_MM_YYYY-HH_mm_ss")
    os.chdir("..")
    curr_dir = os.getcwd()
    zip_file_name = f"{curr_dir}/dombot_backup_{current_time}"
    zip_file_path = shutil.make_archive(zip_file_name, "zip", f"{curr_dir}/{dir_name}")
    await vars.bot.send_file(DOMBOT_BACKUP_CHANNEL, file=f"{zip_file_path}")

    if os.path.exists(zip_file_path):
        try:
            os.remove(zip_file_path)
        except Exception as e:
            print("Failed remove: ", e)


def create_backup_job():
    scheduler = AsyncIOScheduler()
    scheduler.configure(timezone="Asia/Kolkata")
    scheduler.start()
    scheduler.add_job(create_and_send_backup, 'cron', hour='20', minute='00')
