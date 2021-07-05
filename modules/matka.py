# coding=utf-8
"""
matka.py
Made by rolle
"""
import sopel.module
from urllib.request import urlopen
import json

@sopel.module.example('!matka Helsinki Riihimäki')
@sopel.module.commands('matka', 'välimatka', 'valimatka')
def module(bot, trigger):
    start = trigger.group(3).encode('utf-8')
    end = trigger.group(4).encode('utf-8')

    if not start or not end:
        bot.reply('Tarvitaan lähtö- ja saapumispaikat')
    else:
        url = 'https://www.vaelimatka.org/route.json?stops=' + start + '|' + end
        response = urlopen(url)
        data_json = json.loads(response.read())
        bot.reply(data_json["distance"])
