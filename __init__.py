import telebot
from flask import Flask, request
from bots import *
from constants import API_TOKEN, WEBHOOK_URL

WEBHOOK_PORT = 8000

bot = HostBot(API_TOKEN)
app = Flask(__name__)

@app.route('/bot', methods=['GET'])
def health():
    return {"message" : "Server is working!"}, 200

@app.route('/bot', methods=['POST'])  # Default route for all bots
def echo_all():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.bot.process_new_updates([update])
        return 'OK', 200
    else:
        return 'Unsupported Media Type', 415

@app.route('/bot/<token>', methods=['GET','POST'])
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
