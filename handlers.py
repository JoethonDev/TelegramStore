from telebot import TeleBot


def reply_to_user(bot: TeleBot):
    # Function to handle the bot token input
    @bot.message_handler(func=lambda message: True)
    def handle_bot_token(message):
        bot.reply_to(message, message.text)
        