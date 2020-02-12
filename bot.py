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

#global variables initialized
users = ""
watch = ""
queue = ""
colleges = ""
machines = {}


# Allows us to send messages without using context
bot = telegram.Bot(token=bottoken)

#json directories - edit before deploying
queuefilepath = "./queue.json"
watchfilepath = "./watch.json"
usersfilepath = "./users.json"

# function to add to JSON 
def write_json(id_data, filename=usersfilepath): 
    global usersfilepath
    with open(usersfilepath) as json_file: 
        json_full = json.load(json_file) 
        temp = json_full['people'] 
        # python object to be appended 
        y = {'id':data}
        # appending data  
        temp.append(y)

    with open(filename,'w') as f: 
        json.dump(json_full, f, indent=4) 

def loader():
    # Creates or loads json files in case of bot reboot
    # Stores all users' selected laundry college
    global users
    try:
        with open(usersfilepath) as usersfile:
            users = json.load(usersfile)
    except:
        with open(usersfilepath, 'w+'):
            users = {}
    # Stores current watchers for each machine
    global watch
    try:
        with open(watchfilepath) as watchfile:
            watch = json.load(watchfile)
    except:
        with open(watchfilepath, 'w+'):
            watch = {}
    # Stores current queue as list of user IDs
    global queue
    try:
        with open(queuefilepath) as queuefile:
            queue = json.load(queuefile)
    except:
        with open(queuefilepath, 'w+'):
            queue = {}
    # Load the machine database into memory
    from parameters import machine_database
    global colleges
    colleges = set()
    global machines
    machines = {}
    for college in machine_database:
        # Get all laundry colleges
        colleges.add(college)
        # Initialise queues for each college, like a dictionary.
        queue[college] = []
        print(queue)
        machines.update({college:{}})
        for washer in machine_database[college]:
            # Initialise all machines with state -1 (unknown if ON or OFF)
            # Set last updated to current time
            print(washer)
            print(machines)
            machines[college].update({washer : {'state': 1, 'updated': datetime.now() }})
    print(machines)
#Data of machines look like: {'Cendana': {'Cendana Washer 2': {'state': 1, 'updated': datetime.datetime(2020, 2, 13, 1, 27, 48, 289822)}, 'Cendana Washer 4': {'state': 1, 'updated': datetime.datetime(2020, 2, 13, 1, 27, 48, 289840)}, 'Cendana Washer 6': {'state': 1, 'updated': datetime.datetime(2020, 2, 13, 1, 27, 48, 289862)}, 'Cendana Washer 1': {'state': 1, 'updated': datetime.datetime(2020, 2, 13, 1, 27, 48, 289885)}, 'Cendana Washer 3': {'state': 1, 'updated': datetime.datetime(2020, 2, 13, 1, 27, 48, 289958)}}}
# Run webserver to receive POSTs
# Not recommended for production
@run_async
def webserver():
    app.run(host='0.0.0.0', port=5000, threaded=True)

# Handler for POSTs
# TODO: Change to a secret route to prevent people from tampering
@app.route('/', methods=['POST'])
def postupdate():
    # Assume incoming format is JSON e.g. {"washer": "Cendana Washer 1", "state": 0}
    try:
        req_data = request.get_json()
        washer = req_data['machineLabel']
        state = int(req_data['value'])
        college = req_data['college']
        machineupdate(washer, state, college) # Run necessary logic
        return ('Success', 200)  # HTTP success code
    except:
        return ('Error', 400)  # HTTP error code


def machineupdate(washer, state, college):
    global machines
    # Runs every time a machine changes state
    # Get duration (experimental feature)
    then = machines[washer]['updated']
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
        # Get college and dispatch next in queue
        college = machines[washer]['college']
        global queue
        # Remove and return first in line
        id = queue[college].pop(0)
        msg = "It's your turn! *{}* is now available.".format(washer)
        send(id, msg, [])
        with open(queuefilepath) as queuefile:
            json.dump(queue, queuefile)  # backup queue dictionary to file
        # Add user to watch list
        watch.setdefault(washer, []).append(id)  # create list if none exists
        with open(watchfilepath) as watchfile:
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
    msg = 'Hi *{}*, welcome to the YNC Laundry Bot!\n\nPlease select a laundry college.'.format(
        full_name)
    keyboard = []
    for college in colleges:
        keyboard.append([InlineKeyboardButton(
            college, callback_data='ROOM={}'.format(college))])
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
    # Activated from selecting a college
    print(data)
    if data.startswith('ROOM='):
        data = data.replace('ROOM=', '')
        # Save user's college selection to file
        global users
        users = {id:data}
        with open(usersfilepath, "a") as usersfile:
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
        # Overwrite the college selection message
        bot.edit_message_text(
            chat_id=id,
            message_id=query.message.message_id,
            text=msg,
            reply_markup=keyboard,
            parse_mode=telegram.ParseMode.MARKDOWN
        )
    elif data == 'available':
        # From "Check Available Washers" button
        college = users[id]
        available = getavailable(college)
        count = len(available)
        msg = '*There are {} available washers:*\n'.format(count)
        for item in available:
            msg += item + '\n'
        print(msg)
        send(id, msg, [])
    elif data == 'notify':
        # From "Notify when Done" button
        college = users[id]
        active = []
        for washer in machines[college]:
            if machines[college][washer]['state'] == 1:
                active.append(washer)
        active.sort()
        print(active)
        msg = 'Please select a washer:'
        keyboard = []
        for item in active:
            keyboard.append([InlineKeyboardButton(item, callback_data='WASHER='.format(item))])
        keyboard = InlineKeyboardMarkup(keyboard)
            # Overwrite the college selection message
        bot.edit_message_text(
            chat_id=id,
            message_id=query.message.message_id,
            text=msg,
            reply_markup=keyboard,
            parse_mode=telegram.ParseMode.MARKDOWN
        )
    elif data.startswith('WASHER='):
        data = data.replace('WASHER=', '')
        global watch
        print("yay")
        watch.setdefault(data, []).append(id)
        with open(watchfilepath) as watchfile:
            json.dump(watch, watchfile)
        # Pop-up notification instead of sending message
        context.bot.answer_callback_query(
            query.id, text='You will be notified when {} completes.'.format(data), show_alert=True)
        return
    elif data == 'queue':
        global queue
        college = users[id]
        available = getavailable(college)
        if len(available) > 0:
            context.bot.answer_callback_query(
                query.id, text='No need to queue, there are available washers.'.format(data), show_alert=True)
        elif id in queue[college]:
            context.bot.answer_callback_query(
                query.id, text='You are already in the queue.', show_alert=True)
        else:
            count = len(queue[college])
            queue[college].append(id)
            with open(queuefilepath) as queuefile:
                json.dump(queue, queuefile)
            context.bot.answer_callback_query(
                query.id, text='Added to queue. There are {} people ahead of you.'.format(count), show_alert=True)
        return
    context.bot.answer_callback_query(query.id)
    return


def getavailable(college):
    # Return list of available washers for a college
    global machines
    print(machines)
    available = []
    for washer in machines[college]:
        print("triggered")
        print(washer)
        if machines[college][washer]['state'] == 0:
            available.append(washer)
    available.sort()
    print(available)
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
