# coding=utf-8
# Copyright 2008, Sean B. Palmer, inamidst.com
# Copyright 2012, Elsie Powell, embolalia.com
# Copyright 2018, Rusty Bower, rustybower.com
# Licensed under the Eiffel Forum License 2.
from __future__ import unicode_literals, absolute_import, print_function, division

import requests

from datetime import datetime

import pytz

from urllib.request import urlopen
import lxml.etree
from lxml import etree
import lxml.html
import requests
import datetime
import os
import json

from sopel.config.types import NO_DEFAULT, ChoiceAttribute, StaticSection, ValidatedAttribute
from sopel.module import commands, example, NOLIMIT
from sopel.modules.units import c_to_f
from sopel.tools import Identifier
from sopel.tools.time import format_time

from sopel.modules.weather.providers import openmeteo_forecast, openmeteo_weather
from sopel.modules.weather.providers import openweathermap_forecast, openweathermap_weather
from sopel.modules.weather.providers import pirateweather_forecast, pirateweather_weather

WEATHER_PROVIDERS = [
    'openmeteo',
    'openweathermap',
    'pirateweather',
]

GEOCOORDS_PROVIDERS = {
    'locationiq_eu': 'https://eu1.locationiq.com/v1/search.php',
    'locationiq_us': 'https://us1.locationiq.com/v1/search.php',
    # for backward compatibility with previous `geocoords_provider` default value
    'locationiq': 'https://us1.locationiq.com/v1/search.php',
}


# Define our sopel weather configuration
class WeatherSection(StaticSection):
    geocoords_provider = ChoiceAttribute('geocoords_provider', GEOCOORDS_PROVIDERS.keys(), default='locationiq_us')
    geocoords_api_key = ValidatedAttribute('geocoords_api_key', str, default='')
    weather_provider = ChoiceAttribute('weather_provider', WEATHER_PROVIDERS, default=NO_DEFAULT)
    weather_api_key = ValidatedAttribute('weather_api_key', str, default='')
    sunrise_sunset = ValidatedAttribute('sunrise_sunset', bool, default=False)
    nick_lookup = ValidatedAttribute('nick_lookup', bool, default=True)


def setup(bot):
    bot.config.define_section('weather', WeatherSection)


# Walk the user through defining variables required
def configure(config):
    config.define_section('weather', WeatherSection, validate=False)
    config.weather.configure_setting(
        'geocoords_provider',
        'Anna GeoCoords API Provider:',
        default=NO_DEFAULT
    )
    config.weather.configure_setting(
        'geocoords_api_key',
        'Anna GeoCoords rajapinta-avain:',
        default=NO_DEFAULT
    )
    config.weather.configure_setting(
        'weather_provider',
        'Anna Weather API Provider: ({}):'.format(', '.join(WEATHER_PROVIDERS)),
        default=NO_DEFAULT
    )
    config.weather.configure_setting(
        'weather_api_key',
        'Anna Weather rajapinta-avain:',
        default=NO_DEFAULT
    )
    config.weather.configure_setting(
        'sunrise_sunset',
        'Otetaanko käyttöön auringonnousu/auringonlasku:',
        default=False
    )
    config.weather.configure_setting(
        'nick_lookup',
        'Otetaanko käyttöön henkilön sijainnin kaivelu:',
        default=True
    )


def get_temp(temp):
    try:
        temp = float(temp)
    except (KeyError, TypeError, ValueError):
        return 'unknown'
    return u'%d\u00B0C (%d\u00B0F)' % (round(temp), round(c_to_f(temp)))


def get_humidity(humidity):
    try:
        humidity = int(humidity * 100)
    except (KeyError, TypeError, ValueError):
        return 'unknown'
    return "Humidity: %s%%" % humidity


def get_wind(speed, bearing):
    m_s = float(round(speed, 1))
    kph = int(round(speed * 3.6))
    mph = int(round(speed * 2.236936))
    speed = int(round(m_s * 1.94384))
    bearing = int(bearing)

    if speed < 1:
        description = 'Calm'
    elif speed < 4:
        description = 'Light air'
    elif speed < 7:
        description = 'Light breeze'
    elif speed < 11:
        description = 'Gentle breeze'
    elif speed < 16:
        description = 'Moderate breeze'
    elif speed < 22:
        description = 'Fresh breeze'
    elif speed < 28:
        description = 'Strong breeze'
    elif speed < 34:
        description = 'Near gale'
    elif speed < 41:
        description = 'Gale'
    elif speed < 48:
        description = 'Strong gale'
    elif speed < 56:
        description = 'Storm'
    elif speed < 64:
        description = 'Violent storm'
    else:
        description = 'Hurricane'

    if (bearing <= 22.5) or (bearing > 337.5):
        bearing = u'\u2193'
    elif (bearing > 22.5) and (bearing <= 67.5):
        bearing = u'\u2199'
    elif (bearing > 67.5) and (bearing <= 112.5):
        bearing = u'\u2190'
    elif (bearing > 112.5) and (bearing <= 157.5):
        bearing = u'\u2196'
    elif (bearing > 157.5) and (bearing <= 202.5):
        bearing = u'\u2191'
    elif (bearing > 202.5) and (bearing <= 247.5):
        bearing = u'\u2197'
    elif (bearing > 247.5) and (bearing <= 292.5):
        bearing = u'\u2192'
    elif (bearing > 292.5) and (bearing <= 337.5):
        bearing = u'\u2198'

    return description + ': ' + str(kph) + 'km/h ' + '(' + str(mph) + 'mph) ' + '(' + bearing + ')'

def convert_timestamp(timestamp, tz):
    # Partial logic from sopel/tools/time.format_time
    time = datetime.fromtimestamp(timestamp, pytz.timezone('UTC'))
    # We only return the time, without a date or timezone.
    tz = pytz.timezone(tz)
    return time.astimezone(tz).strftime('%H:%M')

def get_geocoords(bot, trigger):
    target = trigger.group(2)

    if target == 'rolle':
        url_rolle = "https://c.rolle.wtf/raw.php"
        temps = urlopen(url_rolle).read().decode("utf-8")
        bot.say('\x02Jyväskylä, Rollen ja mustikkasopan koti\x0F: ' + temps + '')
    else:

        if not target:
            latitude = bot.db.get_nick_value(trigger.nick, 'latitude')
            longitude = bot.db.get_nick_value(trigger.nick, 'longitude')
            location = bot.db.get_nick_value(trigger.nick, 'location')

            if latitude and longitude and location:
                return latitude, longitude, location
            else:
                raise ValueError

        if bot.config.weather.nick_lookup and ' ' not in target:
            # Try to look up nickname in DB, if enabled
            nick = Identifier(target)
            latitude = bot.db.get_nick_value(nick, 'latitude')
            longitude = bot.db.get_nick_value(nick, 'longitude')
            location = bot.db.get_nick_value(nick, 'location')

            if latitude and longitude and location:
                return latitude, longitude, location

        # geocode location if not a nick or not found in DB
        url = GEOCOORDS_PROVIDERS[bot.config.weather.geocoords_provider]
        data = {
            'key': bot.config.weather.geocoords_api_key,
            'q': trigger.group(2),
            'format': 'json',
            'addressdetails': 1,
            'limit': 1
        }

        try:
            r = requests.get(url, params=data)
        except requests.exceptions.RequestException:
            # requests likes to include the full URL in its exceptions, which would
            # mean the API key gets printed to the channel
            raise Exception("En saanut geolokaatiota. Katso lokit.")

        if r.status_code != 200:
            raise Exception(r.json()['error'])

        latitude = r.json()[0]['lat']
        longitude = r.json()[0]['lon']
        address = r.json()[0]['address']

        parts = []

        # Zip codes give us town versus city
        if 'city' in address:
            parts.append(address['city'])
        elif 'town' in address:
            parts.append(address['town'])
        elif 'county' in address:
            parts.append(address['county'])
        elif 'city_district' in address:
            parts.append(address['city_district'])

        if 'state' in address:
            parts.append(address['state'])

        if parts:
            parts.append(address['country_code'].upper())
            location = ', '.join(parts)
        else:
            location = 'Unknown'

        return latitude, longitude, location


def get_forecast(bot, trigger):
    try:
        latitude, longitude, location = get_geocoords(bot, trigger)
    except ValueError as e:
        bot.reply(str(e))
        return NOLIMIT

    # Open-Meteo
    if bot.config.weather.weather_provider == 'openmeteo':
        return openmeteo_forecast(bot, latitude, longitude, location)
    # OpenWeatherMap
    elif bot.config.weather.weather_provider == 'openweathermap':
        return openweathermap_forecast(bot, latitude, longitude, location)
    # Pirate Weather
    elif bot.config.weather.weather_provider == 'pirateweather':
        return pirateweather_forecast(bot, latitude, longitude, location)
    # Unsupported Provider
    else:
        raise Exception('Error: Unsupported Provider')


def get_weather(bot, trigger):
    try:
        latitude, longitude, location = get_geocoords(bot, trigger)
    except ValueError as e:
        bot.reply(str(e))
        return NOLIMIT

    # Open-Meteo
    if bot.config.weather.weather_provider == 'openmeteo':
        return openmeteo_weather(bot, latitude, longitude, location)
    # OpenWeatherMap
    elif bot.config.weather.weather_provider == 'openweathermap':
        return openweathermap_weather(bot, latitude, longitude, location)
    # Pirate Weather
    elif bot.config.weather.weather_provider == 'pirateweather':
        return pirateweather_weather(bot, latitude, longitude, location)
    # Unsupported Provider
    else:
        raise Exception('Error: Unsupported Provider')


@commands('saa', 'sää', 'keli')
@example('!sää')
@example('!sää London')
@example('!sää Seattle, US')
@example('!sää 90210')
def weather_command(bot, trigger):
    """!sää sijainti - Näyttää säätiedot annetulle sijainnille."""
    if bot.config.weather.weather_api_key is None or bot.config.weather.weather_api_key == '':
        return bot.reply("Sään rajapinta-avain puuttuu. Konfiguroipas moduuli kunnolla.")
    if bot.config.weather.geocoords_api_key is None or bot.config.weather.geocoords_api_key == '':
        return bot.reply("GeoCoords-rajapinta-avain puuttuu. Konfiguroipas moduuli oikein.")

    # Ensure we have a location for the user
    location = trigger.group(2)
    if not location:
        latitude = bot.db.get_nick_value(trigger.nick, 'latitude')
        longitude = bot.db.get_nick_value(trigger.nick, 'longitude')
        if not latitude or not longitude:
            return bot.say("En tiedä missä sinä asut. "
                           "Annapas sijainti, esim. {pfx}{command} Helsinki, "
                           "tai kerro minulle missä olet komennolla {pfx}asetasää "
                           "Esimerkiksi Helsinki.".format(command=trigger.group(1),
                                                         pfx=bot.config.core.help_prefix))

    try:
        data = get_weather(bot, trigger)
    except Exception as err:
        bot.reply("En saanut säätietoja: " + str(err))
        return

    weather = u'{location}: {temp}, {condition}, {humidity}'.format(
        location=data['location'],
        temp=get_temp(data['temp']),
        condition=data['condition'],
        humidity=get_humidity(data['humidity'])
    )
    # Some providers don't give us UV Index
    if 'uvindex' in data.keys():
        weather += ', UV Index: {uvindex}'.format(uvindex=data['uvindex'])
    # User wants sunrise/sunset information
    if bot.config.weather.sunrise_sunset:
        tz = data['timezone']
        sr = convert_timestamp(data['sunrise'], tz)
        ss = convert_timestamp(data['sunset'], tz)
        weather += ', Auringonnousu: {sunrise} Auringonlasku: {sunset}'.format(sunrise=sr, sunset=ss)
    weather += ', {wind}'.format(wind=get_wind(data['wind']['speed'], data['wind']['bearing']))
    return bot.say(weather)


@commands('saaennuste', 'sääennuste')
@example('!sääennuste')
@example('!sääennuste London')
@example('!sääennuste Seattle, US')
@example('!sääennuste 90210')
def forecast_command(bot, trigger):
    """!sääennuste sijainti - Näyttää annetulle sijainnille neljän päivän sääennusteen."""
    if bot.config.weather.weather_api_key is None or bot.config.weather.weather_api_key == '':
        return bot.reply("Sään rajapinta-avain puuttuu. Konfiguroipas moduuli oikein.")
    if bot.config.weather.geocoords_api_key is None or bot.config.weather.geocoords_api_key == '':
        return bot.reply("GeoCoords-rajapinta-avain puuttuu. Konfiguroipas moduuli oikein.")

    # Ensure we have a location for the user
    location = trigger.group(2)
    if not location:
        latitude = bot.db.get_nick_value(trigger.nick, 'latitude')
        longitude = bot.db.get_nick_value(trigger.nick, 'longitude')
        if not latitude or not longitude:
            return bot.say("En tiedä missä sinä asut. "
                           "Annapas sijainti, esim. {pfx}{command} Helsinki, "
                           "tai kerro missä asut komennolla {pfx}asetasää "
                           "Esimerkiksi Helsinki.".format(command=trigger.group(1),
                                                         pfx=bot.config.core.help_prefix))

    try:
        data = get_forecast(bot, trigger)
    except Exception as err:
        bot.reply("En saanut sääennustetta: " + str(err))
        return

    forecast = '{location}'.format(location=data['location'])
    for day in data['data']:
        forecast += ' :: {dow} - {summary} - {high_temp} / {low_temp}'.format(
            dow=day.get('dow'),
            summary=day.get('summary'),
            high_temp=get_temp(day.get('high_temp')),
            low_temp=get_temp(day.get('low_temp'))
        )
    return bot.say(forecast)


@commands('asetasää', 'asetasaa')
@example('!asetasää Helsinki')
@example('!asetasää Seattle, US')
@example('!asetasää 90210')
@example('!asetasää w7174408')
def update_location(bot, trigger):
    """Aseta sijaintisi säätä varten."""
    if bot.config.weather.geocoords_api_key is None or bot.config.weather.geocoords_api_key == '':
        return bot.reply("GeoCoords-rajapinta-avain puuttuu. Konfiguroipas moduuli oikein.")

    # Return an error if no location is provided
    if not trigger.group(2):
        bot.reply('Annapas sijainti, esim. "Helsinki" tai "00100".')
        return NOLIMIT

    # Get GeoCoords
    try:
        latitude, longitude, location = get_geocoords(bot, trigger)
    except Exception as err:
        # Reply with the error message if geocoding fails
        bot.reply("En löytänyt sijaintitietoja tälle: " + str(err))
        return

    # Assign Latitude & Longitude to user
    bot.db.set_nick_value(trigger.nick, 'latitude', latitude)
    bot.db.set_nick_value(trigger.nick, 'longitude', longitude)
    bot.db.set_nick_value(trigger.nick, 'location', location)

    return bot.reply('Sinä olet nyt sijainnissa {}'.format(location))
