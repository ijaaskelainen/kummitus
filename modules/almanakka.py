"""
almanakka.py - Sopel Almanakka Module
Copyright 2020, Roni "rolle" Laukkarinen <roni@dude.fi>
Licensed under the Eiffel Forum License 2.
http://sopel.chat/
"""
import schedule
import sopel.module
from sopel.module import commands
from bs4 import BeautifulSoup
import requests
import datetime
import os
import json
from babel.dates import format_date, format_datetime, format_time

names_file = '/home/rolle/.sopel/modules/nimipaivat.json'

def scheduled_message(bot):
    url = "https://almanakka.helsinki.fi/"
    url_accurate_names = "http://xn--nimipiv-9wac.fi/%s.%s./"   
    now = datetime.datetime.now()

    # Get HTML page
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36'
    headers = {"user-agent": user_agent}
    req = requests.get(url, headers=headers, verify=False)

    # Get stuff
    soup = BeautifulSoup(req.text, "html.parser")
    day = soup.select("#rt-sidebar-a > div.rt-block.nosto > div > div > h2")
    names = soup.select("#rt-sidebar-a > div.rt-block.nosto > div > div > p:nth-child(3)")
    findate = format_date(now, format='full', locale='fi_FI')

    bot.say('Päivä vaihtui! Tänään on \x02' + findate + '\x0F. ' + names[0].text.strip() + '', '#pulina')

def scheduled_message_morning(bot):
    url = "https://almanakka.helsinki.fi/"
    now = datetime.datetime.now()

    # Get HTML page
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36'
    headers = {"user-agent": user_agent}
    req = requests.get(url, headers=headers, verify=False)

    # Get stuff
    soup = BeautifulSoup(req.text, "html.parser")
    day = soup.select("#rt-sidebar-a > div.rt-block.nosto > div > div > h2")
    names = soup.select("#rt-sidebar-a > div.rt-block.nosto > div > div > p:nth-child(3)")
    findate = format_date(now, format='full', locale='fi_FI')

    bot.say('Huomenta aamuvirkut! Tänään on \x02' + findate + '\x0F. ' + names[0].text.strip() + '', '#pulina')

def setup(bot):
    schedule.every().day.at('00:00').do(scheduled_message, bot=bot)
    schedule.every().day.at('06:00').do(scheduled_message_morning, bot=bot)

@sopel.module.interval(60)
def run_schedule(bot):
    schedule.run_pending()
    
@commands(u'almanakka', u'tänään', u'nimipäivät', 'pvm')
def almanakka(bot, trigger):
    
    now = datetime.datetime.now()
    day = now.strftime("%d")
    month = now.strftime("%m")

    if os.path.exists(names_file):
      filehandle = open(names_file, 'r')
      data_json = json.loads(filehandle.read())
      filehandle.close()
      names = data_json[day + '-' + month]

    findate = format_date(now, format='full', locale='fi_FI')

    bot.say('Tänään on \x02' + findate + '\x0F. Nimipäiviään viettävät: ' + names + '')
