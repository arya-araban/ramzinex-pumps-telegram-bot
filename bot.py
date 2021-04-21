import os
import sys

from telegram.ext import Updater, CommandHandler
from threading import Timer, Thread, Event
import config
import requests

TOKEN = config.TOKEN
GROWTH_RATE_PERCENTAGE = 15  # growth rate % to compare once every n seconds. using 10 with 1 MINUTE is a good idea
# NOTE That for example: Growth rate % 10 means that if a new price is higher than old price + 10% old_price ...
UPDATE_SECONDS = 50

pumps = []
my_bots = {}

old_values = {}
new_values = {}
for key, value in requests.get('https://ramzinex.com/exchange/api/exchange/prices').json()['original'].items():
    if 'irr' in key:
        new_values[key] = value['buy']

print(new_values)


def pumps(update, context):
    chat_id = update.message.chat_id
    txt = ''
    if chat_id not in my_bots:
        my_bots[chat_id] = context.bot
        txt += 'you will receive pump notifications!'
    else:
        my_bots.pop(chat_id)
        txt += "you've disabled pump notifications!"

    context.bot.send_message(chat_id=chat_id, text=txt)


def start(update, context):
    chat_id = update.message.chat_id
    context.bot.send_message(chat_id=chat_id,
                             text="Hey! You can enable or disable pump notifications with the /pumps command")


class perpetualTimer():  # timer to run request once every few seconds!
    def __init__(self, t, hFunction):
        self.t = t
        self.hFunction = hFunction
        self.thread = Timer(self.t, self.handle_function)

    def handle_function(self):
        self.hFunction()
        self.thread = Timer(self.t, self.handle_function)
        self.thread.start()

    def start(self):
        self.thread.start()

    def cancel(self):
        self.thread.cancel()


def pumper():  # once every n seconds
    global pumps
    old_values.update(new_values)
    for key, value in requests.get('https://ramzinex.com/exchange/api/exchange/prices').json()['original'].items():
        if 'irr' in key:
            new_values[key] = value['buy']
    diff = {k: new_values[k] - old_values[k] for k in new_values}
    old_values.update(
        {k: int((old_values[k] * GROWTH_RATE_PERCENTAGE) / 100) for k in
         new_values})  # changing old_values to the percentage we're after
    diff.update({k: diff[k] - old_values[k] for k in
                 new_values})  # finding the differences of growth - (old_values* growth_rate)
    pumps = [k for k, v in diff.items() if v > 0]
    # print(diff)
    # print(pumps)

    if len(pumps) > 0:  # checking for any pumps!
        for id, bot in my_bots.items():
            bot.send_message(id, text=f'{str(pumps).translate({39: None})}\nis being pumped!')


def main():
    t = perpetualTimer(UPDATE_SECONDS, pumper)
    # t = perpetualTimer(10, pumper)
    t.start()
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler('pumps', pumps))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
