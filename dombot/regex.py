import re
from telethon import events
import asyncio


RE_PATTERN = r"^/?s/((?:\\/|[^/])+)/((?:\\/|[^/])*)(?:/)*(.*)?"


async def regex_response(event, **data):
    try:
        assert all(k in data for k in ("fr", "to", "response", "msg_id"))
    except:
        await event.reply("`Assertion check failed.`")
        return

    try:
        response = re.sub(data["fr"], data["to"], data["response"])
    except Exception as e:
        await event.reply(f"{e.args[0]}")
        raise events.StopPropagation

    response = [response[i: i + 4095] for i in range(0, len(response), 4095)]

    for reply in response:
        await event.respond(reply, reply_to=data["msg_id"])
        await asyncio.sleep(1)


@events.register(events.NewMessage(pattern=RE_PATTERN))
async def regex(event):
    fr = event.pattern_match.group(1)
    to = event.pattern_match.group(2).replace('\\/', '/').replace('\\0', '\\g<0>')
    inline = event.pattern_match.group(3)

    if event.is_reply:
        msg = await event.get_reply_message()
        await regex_response(event, fr=fr, to=to, response=msg.text, msg_id=msg.id)
        raise events.StopPropagation
    elif inline:
        inline = inline.replace('\\/', '/').replace('\\0', '\\g<0>')
        await regex_response(event, fr=fr, to=to, response=inline, msg_id=event.id)
        raise events.StopPropagation
    else:
        await event.reply("Reply to some message. To use it independently, "
                            "use `/s/<pattern>/<replacement>/<text>`.\nExample: `/s/\w+/test/some text`.")
        raise events.StopPropagation
