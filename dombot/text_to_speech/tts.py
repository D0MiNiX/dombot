from telethon import events, Button
from functools import partial
from functions import command, command_with_args
from gtts import gTTS
import os
from vars import bot
import asyncio
import threading


lock = threading.Lock()
MAX_CHARS = 32


async def task_done(text, lang_code, file_name, event_data):
    await bot.send_file(event_data["chat_id"], reply_to=event_data["msg_id"], file=file_name, voice_note=True, caption=text[:MAX_CHARS])
    os.remove(file_name)


def convert_thread(text, lang_code, file_name, event_data, loop):
    lock.acquire()
    tts_obj = gTTS(text=text, lang=lang_code, slow=False)
    tts_obj.save(file_name)
    lock.release()
    task = loop.create_task(task_done(text, lang_code, file_name, event_data))


def dummy():
    pass


@events.register(events.NewMessage())
async def tts(event):

    cmd_with_args = partial(command_with_args, event.raw_text)

    if cmd_with_args("tts"):
        data = event.raw_text.split(" ", 1)
        lang_code = "en"
        text = None
        msg_id = 0

        if len(data) <= 1:
            await event.reply("Give some text to be converted to speech. Optionally, language code can be provided " \
                              "in the end as `text|de` to use german language speech. Alternatively, reply to a message " \
                              "with a language code as `/tts ja`.")
            raise events.StopPropagation
        else:
            if event.is_reply:
                print("is reply")
                message = await event.get_reply_message()
                text = message.raw_text
                print(text)
                msg_id = message.id
                print(msg_id)
                lang_code = data[1]
                print(lang_code)
            else:
                text = data[1]
                _lang_code = text.rsplit('|', 1)
                if len(_lang_code) > 1:
                    text = _lang_code[0]
                    lang_code = _lang_code[1].strip()
 
        file_path = "dombot/text_to_speech/"
        file_name = f"{file_path}{text[:MAX_CHARS]}.mp3"

        try:
            if os.path.exists(file_name):
                await event.reply("File already exists/processing. Please try again later.")
                raise events.StopPropagation
            conv_thread = threading.Thread(target=convert_thread, args=(text, lang_code, file_name, {"chat_id":event.chat_id, "msg_id": msg_id if event.is_reply else event.id}, asyncio.get_running_loop()))
            conv_thread.start()
        except Exception as e:
            print(e)
            await event.reply("Something went wrong. Make sure there are no special characters in text. When used as reply, " \
                              "provide language code as an argument, eg. `/tts ja`.")
            await events.StopPropagation
        
        # dummy call to execute the async tick or smthng
        # w/o this, task_done doesn't get called immediately
        asyncio.get_event_loop().call_later(1, dummy)
        raise events.StopPropagation

