from telethon import events, Button
from functools import partial
from functions import command, command_with_args
from gtts import gTTS
import os
from vars import bot


@events.register(events.NewMessage())
async def tts(event):

    cmd_with_args = partial(command_with_args, event.raw_text)

    if cmd_with_args("tts"):
        data = event.raw_text.split(" ", 1)
        lang_code = "en"
        text = None

        if len(data) <= 1:
            await event.reply("Give some text to be converted to speech.")
            raise events.StopPropagation
        else:
            text = data[1]
            _lang_code = text.rsplit('|', 1)
            if len(_lang_code) > 1:
                text = _lang_code[0]
                lang_code = _lang_code[1].strip()
 
        MAX_CHARS = 32
        file_path = "dombot/text_to_speech/"
        file_name = f"{file_path}{text[:MAX_CHARS]}.mp3"

        try:
            if os.path.exists(file_name):
                await event.reply("File already exists/processing. Please try again later.")
                raise events.StopPropagation
            tts_obj = gTTS(text=text, lang=lang_code, slow=False)
            tts_obj.save(file_name)
        except:
            await event.reply("Something went wrong. Make sure there are no special characters in text.")
            await events.StopPropagation

        await bot.send_file(event.chat_id, reply_to=event.id, file=file_name, voice_note=True, caption=text[:MAX_CHARS])
        os.remove(file_name)
        raise events.StopPropagation

