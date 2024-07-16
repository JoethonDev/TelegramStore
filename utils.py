import telebot
import sqlite3
import pytz
from telebot import types
from datetime import datetime
from json import loads
import sqlite3

conn = sqlite3.connect('manager_bot.db', check_same_thread=False)
cursor = conn.cursor()
UNFOUND_ERROR = "الاختيار ليس موجود بالقائمه برجاء الاختيار من القائمه"

def initalize_bot(token, webhook):
    bot = telebot.TeleBot(token)
    start_bot(bot, token, webhook)
    active_handlers(bot)
    return bot

def start_bot(bot: telebot.TeleBot, token, WEBHOOK_URL):
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{token}", drop_pending_updates=True)


def active_handlers(bot):
    def get_users():
        query = "SELECT user_id FROM users"
        return get_all(query)

    def send_order_request(photo, caption, data):
        buttons = {
            "قبول" : data + "accept",
            "رفض" : data + "reject"
        }
        keyboard = build_inline_keyboard(buttons)
        admin = "1019315752"
        bot.send_photo(admin, photo, caption, reply_markup=keyboard)

    def is_admin(user_id):
        return True

    def join_orders(orders):
        return """
        -------------------------------
        \n\n
        """.join(orders)

    def parse_orders(orders):
        parsed_orders = {
            "pending" : [],
            "completed" : [],
            "pending_transactions" : []
        }
        # Return Dict 
        for order in orders :
            order_message = f"""
            اسم الخدمه : {order[0]}
            حاله الطلب : {order[1]}
            التاريخ : {order[2]}
            """
            if order[5] == "pending":
                parsed_orders['pending'].append(order_message)
                parsed_orders['pending_transactions'].append({
                    "photo" : order[3],
                    "caption" : order[4],
                    "order_id" : order[5],
                    "user_id" : order[6]
                })
            else :
                parsed_orders['completed'].append(order_message)
        return parsed_orders

    def parse_call_back_query(data):
        pairs = data.split(",")
        result = {}
        for pair in pairs:
            pair_list = pair.split(":")
            result[pair_list[0]] = pair_list[1]

        return result

    def build_inline_keyboard(buttons):
        KEYBOARD = types.InlineKeyboardMarkup(row_width=2)
        for button, value in buttons.items():
            KEYBOARD.add(types.InlineKeyboardButton(button, callback_data=str(value)))
        return KEYBOARD

    def build_reply_keyboard(buttons):
        KEYBOARD = types.ReplyKeyboardMarkup()
        KEYBOARD.add(*buttons)
        return KEYBOARD

    def get_chat_id(message):
        return message.chat.id

    def send_message(message, text, markups=None):
        chat_id = get_chat_id(message)
        bot.send_message(chat_id, text, reply_markup=markups)

    def get_one(query):
        cursor.execute(query)
        result = cursor.fetchone()
        return result

    def get_all(query):
        cursor.execute(query)
        results = cursor.fetchall()
        return results

    def get_all_services():
        query = f"SELECT name FROM service"
        return get_all(query)

    def get_service_by_name(service_name):
        query = f"SELECT description, price, payment_method, id FROM service WHERE name = '{service_name}'"
        return get_one(query)

    def get_service_by_id(service_id):
        query = f"SELECT name, description, price, payment_method FROM service WHERE id = '{service_id}'"
        return get_one(query)

    def get_all_orders(status=None, user=None):
        if status :
            status = ", ".join(status)

        query = f"""
        SELECT services.name, orders.status, orders.date, orders.photo_id, orders.caption, orders.id, orders.user_id FROM orders JOIN services
        ON services.id = orders.service_id
        WHERE (user = '{user}' or {user} is NULL)
        AND (status IN ({status}) or {status} is NULL)
        """
        return get_all(query)
    
    @bot.message_handler(commands=['start'])
    def start_message(message):
        # Get start message from db
        welcome_message = "Hello to our Bot"
        # Display message with keyboard [Services - Orders - Notify or Contact]
        buttons = ["الخدمات", "الطلبات", "اذاعه"]
        KEYBOARD = build_reply_keyboard(buttons)
        # if not admin
        # buttons[2] = "تواصل مع البائع"
        # Replay to user
        send_message(message, welcome_message, KEYBOARD)

    @bot.message_handler(func=lambda message: message.text == "الخدمات")
    def get_services(message):
        # Get Services of bot from db
        services = [service[0] for service in get_all_services()]
        # List Names as buttons
        KEYBOARD = build_reply_keyboard(services)
        # Press on Service
        send_message(message, message.text, KEYBOARD)
        # Get service details
        bot.register_next_step_handler(message, display_service, KEYBOARD)
        

    def display_service(message, keyboard):
        service_name = message.text
        if service_name == "الرجوع للقائمه":
            start_message(message)
            return
        
        # get service from database
        service_description = get_service_by_name(service_name)
        # If service found
        if service_description:
            description = f"{service_description[0]} \n\nالسعر : {service_description[1]} \nتفاصيل الدفع : {service_description[2]}"
            # Start from here!!
            buttons = {
                "شراء" : f'type:service,id:{service_description[3]},name:{service_name}'
            }
            KEYBOARD = build_inline_keyboard(buttons)
            send_message(message, description, KEYBOARD)
        # else if service not found
        else:
            send_message(message, UNFOUND_ERROR, keyboard)
            bot.register_next_step_handler(message, display_service, keyboard)

    @bot.callback_query_handler(lambda query: query.data.startswith("type:service"))
    def initialize_order(query):
        data = parse_call_back_query(query.data)
        item_id = data['id']
        message = query.message
        force_reply = types.ForceReply()
        # ask for screenshot of transaction!
        message_text = f"""
        لقد قمت باختيار خدمه : {data['name']}

        برجاء ارسال صوره من التحويل
        مرفق المطلبات الخدمه مثل رقم او حساب..
        """
        send_message(message, message_text, force_reply)
        bot.register_next_step_handler(message, check_image, item_id)

    def check_image(message, item_id):
        if message.content_type != "photo":
            force_reply = types.ForceReply()
            message_text = f"""
            برجاء ارسال صوره من التحويل
            مرفق المطلبات الخدمه مثل رقم او حساب..
            """
            send_message(message, message_text, force_reply)
            bot.register_next_step_handler(message, check_image, item_id)
        place_order(message, item_id)

    def place_order(message, item_id): 
        photo = message.photo[-1].file_id
        caption = message.caption
        # send message order is placed
        message_text = """
        لقد تم استلام طلبكم بنجاح 
        سيتم الرد خلال 24-48 ساعه   
        """
        send_message(message, message_text)
        # add order to db
        user_id = message.from_user.id
        cairo_tz = pytz.timezone('Africa/Cairo')
        date = datetime.now(cairo_tz).strftime("%d/%m/%Y, %H:%M")
        query = f"INSERT INTO orders (service_id, bot_id, user_id, date, status, photo_id, caption) VALUES ({item_id}, 1, {user_id}, '{date}', 'pending', {photo}, {caption})"
        cursor.execute(query)
        conn.commit()
        # send notification to seller
        data = f'type:order,id:{cursor.lastrowid},user:{user_id},status:'
        send_order_request(photo, caption, data)


    @bot.message_handler(func=lambda message: message.text == "الطلبات")
    def get_orders(message):
        # Choose pending | completed | all
        keyboard = build_reply_keyboard(["قيد الانتظار", "الطلبات السابقه", "الكل"])
        message_text = "ما هي حاله الطلبات التي تريد؟"
        force_reply = types.ForceReply()
        send_message(message, message_text, force_reply)
        bot.register_next_step_handler(message, get_orders_from_db)

    def get_orders_from_db(message):
        # Get user id
        user_id = message.from_user.id
        status = message.text
        if status == "قيد الانتظار":
            status = "pending"
        elif status == "الطلبات السابقه" :
            status = ["completed", "canceled"]
        else :
            status = None

        orders = []
        # keyboard 
        if is_admin(user_id):
            orders = get_all_orders(status)
        else :
            orders = get_all_orders(status, user_id)
        parsed_orders = parse_orders(orders)
        send_orders_messages(message, parsed_orders)

    def send_orders_messages(message, parsed_orders):
        user_id = message.from_user.id
        completed_orders = join_orders(parsed_orders['completed'])
        if is_admin(user_id):
            for pending_transaction in parsed_orders['pending']:
                photo = pending_transaction['photo']
                caption = pending_transaction['caption']
                order_id = pending_transaction['order_id']
                user_id = user_id
                data = f'type:order,id:{order_id},user:{user_id},status:'
                send_order_request(photo, caption, data)
        else :
            pending_orders = join_orders(parsed_orders['pending'])
            send_message(message, pending_orders)
        send_message(message, completed_orders)

    @bot.message_handler(func=lambda message: message.text == "اذاعه")
    def send_notifications(message):
        force_reply = types.ForceReply()
        message_text = "برجاء ارسال الرساله حتي تصل الي المستخدمين"
        send_message(message, message_text, force_reply)
        bot.register_next_step_handler(message, send_message_to_users)

    def send_message_to_users(message):
        users = [user[1] for user in get_users()]
        for user in users:
            bot.send_message(user, message.text)
        send_message(message, "تم الارسال للكل بنجاح")
