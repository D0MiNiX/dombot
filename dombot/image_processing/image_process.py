from telethon import events
from functools import partial
from functions import command, command_with_args
from PIL import Image, ImageFilter
import concurrent.futures
import random
from telethon.utils import get_extension
import os
import threading
import re
import asyncio
from vars import bot


IMG_PRC_PATH = "dombot/image_processing/"
MAX_FILE_SIZE = 5242880


def blur_image(img, radius):
    if radius is None:
        radius = 15
    blur = img.filter(ImageFilter.GaussianBlur(radius))
    blur.save(f"{img.filename}")


def pixelate(img, size):
    if size is None:
        size = 64
    pix = img.resize((size, size), resample=Image.BILINEAR)
    pix = pix.resize(img.size, Image.NEAREST)
    pix.save(f"{img.filename}")

	
def process_image_thread(name, edit_type, value):
    img = Image.open(name)

    if edit_type == "blur":
        blur_image(img, value)
    elif edit_type == "pixelate":
        pixelate(img, value)


async def send_processed_image(message, file_name):
    await bot.send_file(message.chat_id, file=file_name, reply_to=message.id, caption=message.text, force_document=True)
    os.remove(file_name)


def image_process_thread(message, file_name, effects_data, loop):
    for command, value in effects_data.items():
        process_image_thread(file_name, command, value)

    loop.call_soon_threadsafe(loop.create_task, send_processed_image(message, file_name))


def process_command(command):
    valid_effects = ["blur", "pixelate"]
    data = command.split(' ', 1)

    if len(data) == 1:
        return Exception("Need command(s).")

    details = data[1]
    multiple_effects = details.split(',')

    if len(multiple_effects) > 10:
        return Exception("Maximum of 10 effects can be applied at once.")

    multiple_effects = [cmd.strip() for cmd in multiple_effects]
    invalid_effect = False

    for valid_effect in multiple_effects:
        if valid_effect.split(' ')[0] not in valid_effects:
            return Exception(f"Invalid command detected. Valid commands are `{', '.join(valid_effects)}`.")
 
    effect_re = re.compile(r"^(\w+)\s(\d+)$")
    no_value_effect_re = re.compile(r"^(\w+)$")
    command, value, cmd_val_dict = None, None, {}
 
    for effect in multiple_effects:
        if effect_re.match(effect):
            info_re = effect_re.match(effect)
            command = info_re.group(1)
            value = int(info_re.group(2))
            cmd_val_dict[command] = value
        elif no_value_effect_re.match(effect):
            info_re = no_value_effect_re.match(effect)
            command = info_re.group(1)
            cmd_val_dict[command] = None
    
    return cmd_val_dict


@events.register(events.NewMessage())
async def process_image(event):

    cmd_with_args = partial(command_with_args, event.raw_text)

    if cmd_with_args("img"):
        allowed_exts = [".jpg", ".jpeg", ".png", ".bmp", ".webp"]

        if not event.is_reply:
            await event.reply("Please reply this with some image.")
            raise events.StopPropagation
        
        err = process_command(event.raw_text)

        if isinstance(err, Exception):
            await event.reply(err.args[0])
            raise events.StopPropagation
        
        effects_data = err
        
        message = await event.get_reply_message()
        media = hasattr(message, "media") and message.media
        file = hasattr(message, "file")
 
        if file:
            file = message.file
 
        if (media and message.photo) or (file and file.ext in allowed_exts): 
            if file.size > MAX_FILE_SIZE:
                await event.reply("File size too big to process. Max. size of 5 MB is allowed.")
                raise events.StopPropagation

            extension = get_extension(message.media)
            random_num = random.randrange(0, 1000)
            file_name = f"{IMG_PRC_PATH}media_{random_num}{extension}"
            while os.path.exists(file_name):
                random_num = random.rand_range(0, 1000)
                file_name = f"{IMG_PRC_PATH}media_{random_num}{extension}" 
            await message.download_media(file=file_name)
            loop = asyncio.get_running_loop()
            img_prc_thread = threading.Thread(target=image_process_thread, args=[message, file_name, effects_data, loop])
            img_prc_thread.start()
        else:
            await event.reply("Invalid media.")
            raise events.StopPropagation
        
        raise events.StopPropagation

