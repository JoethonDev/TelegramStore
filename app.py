import telebot
from flask import Flask, request
from bots import *


API_TOKEN = '1156662740:AAEWzSmMZkdRiwlBX_fmLxdMeUuPQgE3ETM' # Store in env
WEBHOOK_URL = 'https://xenogeneic-jannelle-joethon-b834bbe8.koyeb.app' # Store in env

bot = HostBot(API_TOKEN)
app = Flask(__name__)

@app.route('/', methods=['POST'])  # Default route for all bots
def echo_all():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.bot.process_new_updates([update])
        return 'OK', 200
    else:
        return 'Unsupported Media Type', 415

@app.route('/<token>', methods=['GET','POST'])
def webhook(token):
    if request.headers.get('content-type') == 'application/json':
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            if token in bot.bot_collection: 
                client_bot = bot.bot_collection[token]
            else:
                bot.bot_collection[token] = ClientBot(token)
                client_bot = bot.bot_collection[token]
                client_bot.initialize_handlers()

            if client_bot.get_status() == "stopped":
                return "Stopped", 401

            client_bot.bot.process_new_updates([update])
            return 'OK', 200
    else:
        return 'Unsupported Media Type', 415

bot.set_webhook(WEBHOOK_URL)

# Start Flask server to listen for webhook requests
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=WEBHOOK_PORT, debug=True)
