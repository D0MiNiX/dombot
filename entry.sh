#!/bin/bash
echo dombot@123 | sudo -S cp ~/dombot/dump.rdb /var/lib/redis/
sudo chown redis:redis /var/lib/redis/dump.rdb
sudo /etc/init.d/redis-server start
cd ~/dombot
python3 dombot_main.py
/bin/bash
