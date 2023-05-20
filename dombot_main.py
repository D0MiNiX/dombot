from vars import bot, dom, D0MiNiX


def main():
    from dombot.typo_tales.dragon_egg import dragon_egg
    from dombot import admin, start, regex, equipments, monsters, triggers, user_tz, \
                        reminders, region, idle_list_ping, vpb_thres, filters
    from user_bot import blek_magic, report_leaders
    from backup_job import create_backup_job
    from dombot.text_to_speech import tts
    from dombot.image_processing import image_process
    from dombot.monsters import r

    # dom.add_event_handler(blek_magic.print_id)

    # dombot
    bot.add_event_handler(start.start)
    bot.add_event_handler(admin.admin_only)
    bot.add_event_handler(equipments.equips)
    bot.add_event_handler(regex.regex)
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

    # user join/leaves group
    bot.add_event_handler(start.user_action)

    # triggers
    bot.add_event_handler(triggers.triggers)
    bot.add_event_handler(triggers.title_of_yr_stape)

    # filters
    bot.add_event_handler(filters.filters)

    # typo tales - pick random player from guild member list
    # bot.add_event_handler(dragon_egg.random_pick)

    # tts
    bot.add_event_handler(tts.tts)

    # image processing
    bot.add_event_handler(image_process.process_image)

    # users timezones
    bot.add_event_handler(user_tz.tz_handler)

    # idle list pings
    bot.add_event_handler(idle_list_ping.id_list)

    # vpb threshold
    bot.add_event_handler(vpb_thres.calc_vpbs)

    # Update your CW level
    # bot.add_event_handler(blek_magic.set_current_level)

    # dom user bot
    dom.add_event_handler(blek_magic.cw)
    dom.add_event_handler(blek_magic.bot_testing)
    dom.add_event_handler(report_leaders.cw_report_channel)

    # create backup jobs
    create_backup_job()

    bot.send_message(D0MiNiX, "`commenced`")
    print("commenced")

    dom.run_until_disconnected()
    print("\nRDB saved." if r.save() else "Error saving RDB!")

if __name__ == '__main__':
    main()
