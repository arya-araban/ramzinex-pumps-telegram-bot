import os

import telegram
from telegram.ext import Updater, CommandHandler
from threading import Timer, Thread, Event
import requests
import sqlite3 as sl

from ramzinex_git import config

con = sl.connect('my-db.db', check_same_thread=False)  # con has a user table which has a user_id

TOKEN = config.TOKEN

GROWTH_RATE_PERCENTAGE = 10  # growth rate % to compare once every n seconds. using 10 with 1 MINUTE is a good idea
# NOTE That for example: Growth rate % 10 means that if a new price is higher than old price + 10% old_price ...
UPDATE_SECONDS = 40

pumps = []

bt = telegram.Bot
old_values = {}
new_values = {}

data_str = requests.get("https://publicapi.ramzinex.com/exchange/api/v1.0/exchange/pairs?base_id=2").json().get('data')
for i in range(len(data_str)):
    new_values[data_str[i]["base_currency_symbol"]["en"]] = data_str[i]['buy']
del (data_str)


def update_prices():
    global old_values, new_values
    req = requests.get("https://publicapi.ramzinex.com/exchange/api/v1.0/exchange/pairs?base_id=2")
    old_values.update(new_values)
    data_str = req.json().get('data')
    for i in range(len(data_str)):
        new_values[data_str[i]["base_currency_symbol"]["en"]] = data_str[i]['buy']


# print(new_values)


def pumps(update, context):
    chat_id = str(update.message.chat_id)
    txt = ''
    c = con.execute(f"SELECT 1 FROM USER WHERE user_id = {chat_id}")
    userAlreadyExists = c.fetchone()
    if not userAlreadyExists:
        with con:
            con.execute(f"INSERT INTO USER (user_id) values({chat_id})")
        txt += 'you will receive pump notifications!'
    else:
        with con:
            con.execute(f"DELETE FROM USER WHERE user_id = {chat_id}")
        txt += "you've disabled pump notifications!"
    context.bot.send_message(chat_id=int(chat_id), text=txt)


def start(update, context):
    chat_id = update.message.chat_id
    context.bot.send_message(chat_id=chat_id,
                             text="Hey! You can enable or disable pump notifications with the /pumps command")


class perpetualTimer():  # timdp.boter to run request once every few seconds!
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
    # print('hola')
    update_prices()
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
        c = con.execute('SELECT * FROM USER')
        for row in c:
            bt.send_message(int(row[0]), text=f'{str(pumps).translate({39: None})}\nis being pumped!')


def main():
    global bt
    t = perpetualTimer(UPDATE_SECONDS, pumper)
    t.start()

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    bt = dp.bot
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler('pumps', pumps))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
