import telebot
from flask import Flask, request
from utils import *

API_TOKEN = '1156662740:AAEWzSmMZkdRiwlBX_fmLxdMeUuPQgE3ETM'
WEBHOOK_URL = 'https://c0c8-45-244-195-213.ngrok-free.app'
WEBHOOK_PORT = 8443

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# Dictionary to store bot instances
bot_clients = {}

@app.route('/', methods=['POST'])  # Default route for all bots
def echo_all():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    else:
        return 'Unsupported Media Type', 415

@app.route('/<token>', methods=['GET','POST'])
def webhook(token):
    if request.headers.get('content-type') == 'application/json':
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot_clients[token].process_new_updates([update])
            return 'OK', 200
    else:
        return 'Unsupported Media Type', 415

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Hello! I'm your bot.")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    text = str(message.text).strip().split(" ")
    action = text[0]
    token = text[1]
    bot_clients[token] = telebot.TeleBot(token)
    bot_clients[token].remove_webhook()
    if action == "start":
        bot_clients[token] = initalize_bot(token, WEBHOOK_URL)
    bot.reply_to(message, f"Bot : {token} is un-registered")

bot.remove_webhook()
bot.set_webhook(url=WEBHOOK_URL)

# Start Flask server to listen for webhook requests
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=WEBHOOK_PORT)
