import telebot
import sqlite3
import pytz
from telebot import types
from datetime import datetime
from json import loads

API_TOKEN = '1384750648:AAE1SywKz06JUk72qN3xVMZrvEAChNl4p7U'
bot = telebot.TeleBot(API_TOKEN)
conn = sqlite3.connect('manager_bot.db', check_same_thread=False)
cursor = conn.cursor()
UNFOUND_ERROR = "الاختيار ليس موجود بالقائمه برجاء الاختيار من القائمه"
photo_id = ""

# Functions
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

# Handlers
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
    bot.register_next_step_handler(message, place_order, item_id)

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

# Seller Section
def add_service(self, message):
    if self.is_admin(message.from_user.id):
        force_reply = types.ForceReply()
        self.send_message(message, "ما هي اسم الخدمه التي تقدمها؟", force_reply)
        self.bot.register_next_step_handler(message, self.get_service_description)
    else:
        self.send_message(message, "لست مصرح لك لتكون هنا")

def get_service_description(self, message):
    service_name = message.text
    message.chat.data = {'service_name': service_name}
    force_reply = types.ForceReply()
    self.send_message(message, "ضح وصف للخدمه و الشروط المطلوبه", force_reply)
    self.bot.register_next_step_handler(message, self.get_service_payment_method)

def get_service_payment_method(self, message):
    service_description = message.text
    message.chat.data['service_description'] = service_description
    force_reply = types.ForceReply()
    self.send_message(message, "ما هي وسيله الدفع و الحساب الخاص بيها مثال : فودافون كاش 010000000", force_reply)
    self.bot.register_next_step_handler(message, self.get_service_price)

def get_service_price(self, message):
    service_payment_method = message.text
    message.chat.data['service_payment_method'] = service_payment_method
    force_reply = types.ForceReply()
    self.send_message(message, " ما هو سعر الخدمه؟", force_reply)
    self.bot.register_next_step_handler(message, self.save_service)

def save_service(self, message):
    try:
        service_price = float(message.text)
        service_data = message.chat.data
        self.cursor.execute('''
            INSERT INTO services (name, description, price, payment_method, bot_id)
            VALUES (%s, %s, %s, %s, %s)
        ''', (service_data['service_name'], service_data['service_description'], service_price, service_data['service_payment_method'], 1))
        self.conn.commit()
        self.send_message(message, "تم حفظ الخدمه بنجاح")
    except ValueError:
        self.send_message(message, "برجاء ادخال ارقام فقط..")
        self.bot.register_next_step_handler(message, self.get_service_price)

def edit_delete_service(self, message):
    if self.is_admin(message.from_user.id):
        services = [service[0] for service in self.get_all_services()]
        keyboard = self.build_reply_keyboard(services)
        self.send_message(message, "Select a service to edit or delete:", keyboard)
        self.bot.register_next_step_handler(message, self.choose_edit_delete_action)
    else:
        self.send_message(message, "لست مصرح لك لتكون هنا")

def choose_edit_delete_action(self, message):
    service_name = message.text
    message.chat.data = {'service_name': service_name}
    buttons = {"Edit": "edit_service", "Delete": "delete_service"}
    keyboard = self.build_inline_keyboard(buttons)
    self.send_message(message, f"Selected service: {service_name}", keyboard)

@bot.callback_query_handler(func=lambda query: query.data == "edit_service")
def edit_service(self, query):
    service_name = query.message.chat.data['service_name']
    buttons = ["Name", "Description", "Payment Method", "Price", "All"]
    keyboard = self.build_reply_keyboard(buttons)
    self.send_message(query.message, "What do you want to change?", keyboard)
    self.bot.register_next_step_handler(query.message, self.process_edit_choice)

def process_edit_choice(self, message):
    edit_choice = message.text
    message.chat.data['edit_choice'] = edit_choice
    if edit_choice == "All":
        self.get_service_description(message)
    else:
        self.ask_for_new_value(message)

def ask_for_new_value(self, message):
    edit_choice = message.chat.data['edit_choice']
    prompt = f"Please enter the new {edit_choice.lower()} for the service:"
    force_reply = types.ForceReply()
    self.send_message(message, prompt, force_reply)
    self.bot.register_next_step_handler(message, self.update_service)

def update_service(self, message):
    new_value = message.text
    service_name = message.chat.data['service_name']
    edit_choice = message.chat.data['edit_choice']
    field_map = {
        "Name": "name",
        "Description": "description",
        "Payment Method": "payment_method",
        "Price": "price"
    }
    field = field_map[edit_choice]
    self.cursor.execute(f'''
        UPDATE services SET {field} = %s WHERE name = %s
    ''', (new_value, service_name))
    self.conn.commit()
    self.send_message(message, f"Service {edit_choice.lower()} updated successfully.")

@bot.callback_query_handler(func=lambda query: query.data == "delete_service")
def delete_service(self, query):
    service_name = query.message.chat.data['service_name']
    self.cursor.execute('''
        DELETE FROM services WHERE name = %s
    ''', (service_name,))
    self.conn.commit()
    self.send_message(query.message, f"تم حذف الخدمه  {service_name} بنجاح")


# @bot.message_handler(func=lambda message: message.text == "تواصل مع البائع")
# def get_services(message):
#     pass

# Back Buttons
# @bot.message_handler(func=lambda message: message.text == "الرجوع للقائمه")
# def get_services(message):
#     pass

print("Bot started!")
bot.polling()