"""
kuha.py
Lannistajakuha.com
Sopel module made by rolle
"""

@commands('kuha', 'lannistajakuha')

def kuhadef(bot, trigger):
    kuha = random.choice(list(open('/home/rolle/.sopel/modules/kuhat.txt')))
    bot.say(kuha)
