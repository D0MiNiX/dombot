from vars import bot, dom, D0MiNiX
import asyncio


def main():
    from dombot.typo_tales.dragon_egg import dragon_egg
    from dombot import admin, start, regex, equipments, glory, monsters, triggers, user_tz, reminders, region
    from user_bot import blek_magic, report_leaders
    from backup_job import create_backup_job
    from dombot.text_to_speech import tts
    from dombot.image_processing import image_process

    # dombot
    bot.add_event_handler(start.start)
    bot.add_event_handler(admin.admin_only)
    bot.add_event_handler(equipments.equips)
    bot.add_event_handler(regex.regex)
    # bot.add_event_handler(alliance_cw.alliance)
    # bot.add_event_handler(glory.cal_glory)

    # reminders
    bot.add_event_handler(reminders.reminders)

    # region
    bot.add_event_handler(region.tz_region)

    # monsters and ambush fights
    bot.add_event_handler(monsters.fight)
    bot.add_event_handler(monsters.register)
    bot.add_event_handler(monsters.commands)
    bot.add_event_handler(monsters.reports)

    bot.add_event_handler(start.user_action)

    # triggers
    bot.add_event_handler(triggers.triggers)

    # typo tales - pick random player from guild member list
    bot.add_event_handler(dragon_egg.random_pick)

    # tts
    bot.add_event_handler(tts.tts)

    # image processing
    bot.add_event_handler(image_process.process_image)

    # dom user bot
    dom.add_event_handler(blek_magic.cw)
    dom.add_event_handler(blek_magic.typo_tales)
    dom.add_event_handler(blek_magic.bot_testing)
    dom.add_event_handler(report_leaders.cw_report_channel)

    # users timezones
    bot.add_event_handler(user_tz.tz_handler)

    # create backup job
    create_backup_job()

    bot.send_message(D0MiNiX, "`commenced`")
    print("commenced")

    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        asyncio.get_event_loop().stop()
        print("Shutting down...")


if __name__ == '__main__':
    main()
