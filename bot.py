# Dependency: pip install python-telegram-bot --upgrade
import telegram.bot
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Updater, CommandHandler,
                          MessageHandler, Filters, CallbackQueryHandler)
from telegram.ext.dispatcher import run_async
# Dependency: pip install flask requests
from flask import Flask, request
import logging
from datetime import datetime
from secrets import bottoken
import json

# Beware of this log level - file size grows quickly with bot polling
logging.basicConfig(filename='debug.log', filemode='a+', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def loader():
    # Creates or loads json files in case of bot reboot
    # Stores active users
    global users
    try:
        with open('users.json') as usersfile:
            users = json.load(usersfile)
    except:
        with open('users.json', 'w+'):
            users = {}
    # Stores current queue
    global queue
    try:
        with open('queue.json') as queuefile:
            queue = json.load(queuefile)
    except:
        with open('queue.json', 'w+'):
            queue = {}
    # Initialise all machines with state 2 (unknown if ON or OFF)
    # Set last updated to current time
    global machines
    machines = {}
    from parameters import machine_ids
    for id in machine_ids:
        machines[id] = {'state': 2, 'updated': datetime.now()}

# Run webserver to receive POSTs
# Not recommended for production
@run_async
def webserver():
    app.run(host='0.0.0.0', port=80, threaded=True)

# Handler for POSTs
# TODO: Change to a secret route to prevent people from tampering
@app.route('/', methods=['POST'])
def postupdate():
    # Incoming format is JSON e.g. {"id": "c1", "state": 0}
    try:
        req_data = request.get_json()
        id = req_data['id']
        state = int(req_data['state'])
        machines[id] = {'state': state, 'updated': datetime.now()}
        machineupdate(id)
        return ('Success', 200)  # HTTP success code
    except:
        return ('Error', 400)  # HTTP error code


def machineupdate(id):
    return

# Send all messages via asynchronous function so main program does not wait for it
@run_async
def send(context, id, keyboard, msg):
    # Convert list of InlineKeyboardButton to final format
    keyboard = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        chat_id=id, reply_markup=keyboard, text=msg, parse_mode=telegram.ParseMode.MARKDOWN)


def start(update, context):
    user_id = str(update.message.chat_id)
    first_name = update.message.from_user.first_name
    last_name = update.message.from_user.last_name
    full_name = (str(first_name or '') + ' ' +
                 str(last_name or '')).strip()
    msg = 'Hi {}, welcome to the *Laundry Bot*!\n\nWhat would you like to do?'.format(
        full_name)


'''
def groupinit(context):
    global groups
    for group in groups:
        groups[group] = str(message.message_id)
        with open('groups.json', 'w') as groupfile:
            json.dump(groups, groupfile)
        groupedit(context)
        break


def groupedit(context):
    for key, value in groups.items():
        context.bot.edit_message_text(
            chat_id=int(key),
            message_id=int(value),
            text=compose,
            parse_mode=telegram.ParseMode.HTML
        )
'''


def main():
    updater = Updater(token=bottoken, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    # dp.add_handler(MessageHandler(Filters.text, prayer))

    loader()
    webserver()

    updater.start_polling(1)  # Check updates every second

    print("Bot is running. Press Ctrl+C to stop.")
    updater.idle()
    print("Bot stopped successfully.")


if __name__ == '__main__':
    main()
