# coding=utf-8
"""
matka.py
Made by rolle
"""
import sopel.module
from urllib.request import urlopen
import json

url = 'https://www.vaelimatka.org/route.json?stops=%s|%s'

@sopel.module.example('!matka Helsinki Riihimäki')
@sopel.module.commands('matka', 'välimatka', 'valimatka')
def module(bot, trigger):
    start = trigger.group(1)
    end = trigger.group(2)

    if not start or not end:
        bot.reply('Tarvitaan lähtö- ja saapumispaikat')
    
    response = urlopen(url)
    data_json = json.loads(response.read())
    bot.reply(data_json.distance)
