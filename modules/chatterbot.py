"""
chatterbot.py - Chat bot for sopel IRC bot
Copyright 2021, Roni Laukkarinen [roni@dude.fi]"
Licensed under the WTFPL. Do whatever the fuck you want with this. You just
  can't hold me responsible if it breaks something either.
A module for the Sopel IRC Bots.
"""
from __future__ import unicode_literals, absolute_import, print_function, division
import chatterbot
from chatterbot.trainers import ChatterBotCorpusTrainer
trainer = ChatterBotCorpusTrainer(chatbot)
trainer.train(
    "./chatterbot-corpus/chatterbot_corpus/data/finnish/"
)~

# Stores data in file so that it can remember
trainer.export_for_training('./export.json')

from sopel.module import commands, example
import sopel.module

@sopel.module.nickname_commands(".*")

def chatterbot(bot, trigger):
    query = trigger.replace('!', '')

    request = query
    response = chatbot.get_response(request)

    if chatbot.confidence > 0.80:
        bot.reply(response)
    if chatbot.confidence < 0.80:
        bot.reply('Sori, en ymmärtänyt.')