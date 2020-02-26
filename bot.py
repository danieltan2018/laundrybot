# Dependency: pip install python-telegram-bot --upgrade
import telegram
import telegram.bot
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Updater, CommandHandler,
                          MessageHandler, Filters, CallbackQueryHandler)
from telegram.ext.dispatcher import run_async
# Dependency: pip install flask requests
from flask import Flask, request
import logging
from datetime import datetime
# Ensure secrets.py exists - refer to secrets_dummy.py format
from secrets import bottoken, admins
import json

# Beware of this log level - file size grows quickly with bot polling
logging.basicConfig(filename='debug.log', filemode='a+', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define Flask webserver
app = Flask(__name__)

# Allows us to send messages without using context
bot = telegram.Bot(token=bottoken)


def loader():
    # Creates or loads json files in case of bot reboot
    # Stores all users' selected laundry room
    global users
    try:
        with open('users.json') as usersfile:
            users = json.load(usersfile)
    except:
        with open('users.json', 'w+'):
            users = {}
    # Stores current watchers for each machine
    global watch
    try:
        with open('watch.json') as watchfile:
            watch = json.load(watchfile)
    except:
        with open('watch.json', 'w+'):
            watch = {}
    # Stores current queue as list of user IDs
    global queue
    try:
        with open('queue.json') as queuefile:
            queue = json.load(queuefile)
    except:
        with open('queue.json', 'w+'):
            queue = {}
    # Load the machine database into memory
    from parameters import machine_database
    global rooms
    rooms = set()
    global machines
    machines = {}
    for room in machine_database:
        # Get all laundry rooms
        rooms.add(room)
        # Initialise queues for each room
        queue[room] = []
        for washer in room:
            # Initialise all machines with state -1 (unknown if ON or OFF)
            # Set last updated to current time
            machines[washer] = {'room': room,
                                'state': -1, 'updated': str(datetime.now())}

# Run webserver to receive POSTs
# Not recommended for production
@run_async
def webserver():
    app.run(host='0.0.0.0', port=80, threaded=True)

# Handler for POSTs
# TODO: Change to a secret route to prevent people from tampering
@app.route('/', methods=['POST'])
def postupdate():
    # Assume incoming format is JSON e.g. {"washer": "Cendana Washer 1", "state": 0}
    try:
        req_data = request.get_json()
        washer = req_data['washer']
        state = int(req_data['state'])
        machineupdate(washer, state)  # Run necessary logic
        return ('Success', 200)  # HTTP success code
    except:
        return ('Error', 400)  # HTTP error code


def machineupdate(washer, state):
    global machines
    # Runs every time a machine changes state
    # Get duration (experimental feature)
    then = datetime.fromisoformat(machines[washer]['updated'])
    now = datetime.now()
    timer = then-now
    duration = (timer.strftime(
        "Your wash took %H hours, %M minutes and %S seconds."))
    # Update master list of machine states
    machines[washer]['state'] = state
    machines[washer]['updated'] = now
    # Notify user when done
    global watch
    if state == 0:
        for id in watch[washer]:
            msg = '*{}* has completed! _{}_'.format(washer, duration)
            send(id, msg, [])
        # Get room and dispatch next in queue
        room = machines[washer]['room']
        global queue
        # Remove and return first in line
        id = queue[room].pop(0)
        msg = "It's your turn! *{}* is now available.".format(washer)
        send(id, msg, [])
        with open('queue.json', 'w') as queuefile:
            json.dump(queue, queuefile)  # backup queue dictionary to file
        # Add user to watch list
        watch.setdefault(washer, []).append(id)  # create list if none exists
        with open('watch.json', 'w') as watchfile:
            json.dump(watch, watchfile)  # backup watch dictionary to file
        msg = 'You will be notified automatically when your wash is done.'
        send(id, msg, [])
    return

# Send all messages via asynchronous function so main program does not wait for it
@run_async
def send(id, msg, keyboard):
    # Convert list of InlineKeyboardButton to final format
    keyboard = InlineKeyboardMarkup(keyboard)
    bot.send_message(
        chat_id=id, reply_markup=keyboard, text=msg, parse_mode=telegram.ParseMode.MARKDOWN)
    return

# Start page for new users or when using /start
@run_async
def start(update, context):
    id = str(update.message.chat_id)
    first_name = update.message.from_user.first_name
    last_name = update.message.from_user.last_name
    full_name = (str(first_name or '') + ' ' +
                 str(last_name or '')).strip()
    msg = 'Hi *{}*, welcome to the YNC Laundry Bot!\n\nPlease select a laundry room.'.format(
        full_name)
    keyboard = []
    for room in rooms:
        keyboard.append([InlineKeyboardButton(
            room, callback_data='ROOM={}'.format(room))])
    send(id, msg, keyboard)
    msg = "_You can type a message at any time to send feedback to the admins, or type /start to return to this page._"
    send(id, msg, [])  # Call function with empty list if no buttons

# Forwards incoming text messages to admins
@run_async
def feedback(update, context):
    id = str(update.message.chat_id)
    first_name = update.message.from_user.first_name
    last_name = update.message.from_user.last_name
    full_name = (str(first_name or '') + ' ' +
                 str(last_name or '')).strip()
    tagged_name = '[{}](tg://user?id={})'.format(full_name, id)
    message = update.message.text
    msg = '*Feedback from {}:*\n\n'.format(tagged_name) + message
    for id in admins:
        send(id, msg, [])
    update.message.reply_text(
        "_Your feedback has been sent to the admins._", parse_mode=telegram.ParseMode.MARKDOWN)


def callbackquery(update, context):
    query = update.callback_query
    data = query.data
    id = str(query.message.chat_id)
    # Activated from selecting a room
    if data.startswith('ROOM='):
        data = data.replace('ROOM=', '')
        # Save user's room selection to file
        global users
        users[id] = data
        with open('users.json', 'w') as usersfile:
            json.dump(users, usersfile)
        msg = 'You have selected *{}*.\n\nWhat would you like to do?'.format(
            data)
        keyboard = [
            [InlineKeyboardButton(
                "Check Available Washers", callback_data='available')],
            [InlineKeyboardButton(
                "Notify when Done", callback_data='notify')],
            [InlineKeyboardButton(
                "Join Queue", callback_data='queue')]
        ]
        keyboard = InlineKeyboardMarkup(keyboard)
        # Overwrite the room selection message
        bot.edit_message_text(
            chat_id=id,
            message_id=query.message.message_id,
            text=msg,
            reply_markup=keyboard,
            parse_mode=telegram.ParseMode.MARKDOWN
        )
    elif data == 'available':
        # From "Check Available Washers" button
        room = users[id]
        available = getavailable(room)
        count = len(available)
        msg = '*There are {} available washers:*\n'.format(count)
        for item in available:
            msg += item + '\n'
        send(id, msg, [])
    elif data == 'notify':
        # From "Notify when Done" button
        room = users[id]
        active = []
        for washer in room:
            if machines[washer]['state'] == 1:
                active.append(washer)
        active.sort()
        msg = 'Please select a washer:'
        keyboard = []
        for item in active:
            keyboard.append([InlineKeyboardButton(
                active, callback_data='WASHER={}'.format(active))])
    elif data.startswith('WASHER='):
        data = data.replace('WASHER=', '')
        global watch
        watch.setdefault(data, []).append(id)
        with open('watch.json') as watchfile:
            json.dump(watch, watchfile)
        # Pop-up notification instead of sending message
        context.bot.answer_callback_query(
            query.id, text='You will be notified when {} completes.'.format(data), show_alert=True)
        return
    elif data == 'queue':
        global queue
        room = users[id]
        available = getavailable(room)
        if len(available) > 0:
            context.bot.answer_callback_query(
                query.id, text='No need to queue, there are available washers.'.format(data), show_alert=True)
        elif id in queue[room]:
            context.bot.answer_callback_query(
                query.id, text='You are already in the queue.', show_alert=True)
        else:
            count = len(queue[room])
            queue[room].append(id)
            with open('queue.json', 'w') as queuefile:
                json.dump(queue, queuefile)
            context.bot.answer_callback_query(
                query.id, text='Added to queue. There are {} people ahead of you.'.format(count), show_alert=True)
        return
    context.bot.answer_callback_query(query.id)
    return


def getavailable(room):
    # Return list of available washers for a room
    available = []
    for washer in room:
        if machines[washer]['state'] == 0:
            available.append(washer)
    available.sort()
    return available


def main():
    updater = Updater(token=bottoken, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text, feedback))
    dp.add_handler(CallbackQueryHandler(callbackquery))

    loader()
    webserver()

    updater.start_polling(1)  # Check for updates every 1 second

    print("Bot is running. Press Ctrl+C to stop.")
    updater.idle()
    print("Bot stopped successfully.")


if __name__ == '__main__':
    main()
