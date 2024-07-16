import telebot
from telebot import types
import psycopg2
import pytz
from datetime import datetime, timedelta


# Start => Register User + Display Hello Message + Keyboard [add bot - my bots - account - deposit - withdraw - check bot] | admin = [Bots Stats - Deposit Stats - Withdraw Stats - Orders]
# add_bot => Display message + wait for response with token  => add_bot_2 => valid token display success else add_bot function again
# my_bots => Display inline Keyboard limit 6 bots per page => choose bot => Display Inline Keyboard [Stop/Start - Delete]
# account => Display Stats [Username - User_id - No_of_bots - Balance]
# deposit => Display deposit message with Cash => Send Screenshot => Send admin request => Accept/Reject [like in client bot]
# withdraw => Display withdraw message with balance can be withdrawn => Send Number to withdraw => Send admin request => Accept/Reject [like in client bot]

class HostBot:

    # Functions
    def register_bot(self, token, username, user_id):
        try:
            self.cursor.execute('''
                INSERT INTO bots (bot_token, username, seller_id) VALUES (?, ?, ?)
            ''', (token, username, user_id))
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()

    def set_webhook(self, url):
        self.bot.remove_webhook()
        self.bot.set_webhook(url=url) 
         

    def create_bot(self, token, url):
        bot = ClientBot(token)
        bot.set_webhook(url)
        bot.initialize_handlers()

    def stop_bot(self, token, url):
        bot = ClientBot(token)
        bot.set_webhook(url)
        bot.initialize_handlers()

    def delete_bot(self, token):
        bot = ClientBot(token)
        bot.delete_webhook()

    def is_bot_exist(self, token):
        self.cursor.execute(f'''
                SELECT * from bots WHERE bot_token='{token}'
            ''')
        return self.cursor.fetchone()

    def get_self_id(self):
        username = str(self.bot.get_me().username)
        self.cursor.execute(f"""
            SELECT id from bots WHERE username = '{username}'
        """)
        return self.cursor.fetchone()[0]

    def get_seller(self, user_id):
        self.cursor.execute(f"""
            SELECT id from sellers WHERE user_id = '{user_id}'
        """)
        return self.cursor.fetchone()[0]

    def check_user(self, user_id):
        self.cursor.execute('''
            SELECT * FROM sellers WHERE user_id='%s'
        ''', (user_id,))
        return self.cursor.fetchone()

    def register_user(self, user_id):
        if not self.check_user(user_id):
            try:
                self.cursor.execute('''
                    INSERT INTO sellers (user_id) VALUES (%s)
                ''', (user_id,))
                self.connection.commit()
            except Exception as e:
                self.connection.rollback()
    
    def get_main_keyboard(self, user_id):
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        buttons = [
            types.KeyboardButton('اضافه بوتات'),
            types.KeyboardButton('البوتات الخاصه بي'),
            types.KeyboardButton('الحساب'),
            types.KeyboardButton('ايداع'),
            types.KeyboardButton('سحب')
        ]
        if self.is_admin(user_id):
            buttons = [
                types.KeyboardButton('Bots Stats'),
                types.KeyboardButton('Deposit Stats'),
                types.KeyboardButton('Withdraw Stats'),
                types.KeyboardButton('Orders')
            ]

        markup.add(*buttons)
        return markup
    
    def is_admin(self, user_id):
        # Check if the user is an admin
        return str(user_id) == self.admin # Remove hardcoded
        # self.cursor.execute('SELECT * FROM admins WHERE user_id = %s', (user_id,))
        # return self.cursor.fetchone() is not None

    def get_bot_username(self, token):
        test_bot = telebot.TeleBot(token)
        return test_bot.get_me().username

    def validate_token(self, token):
        try:
            test_bot = telebot.TeleBot(token)
            test_bot.get_me()
            return True
        except:
            return False

    def get_bots_keyboard(self, bots, page):
        try:
            markup = types.InlineKeyboardMarkup(row_width=2)
            paginated_bots = self.pagination_bots(bots, page)
            collection = []
            count = 0
            for bot in paginated_bots:
                button = types.InlineKeyboardButton(bot[2], callback_data=f'bot:{bot[0]};name:{bot[1]}')
                collection.append(button)
                count += 1
                if count%2 == 0:
                    markup.add(*collection)
                    collection = []
            
            if collection:  # Add any remaining button if the number of buttons is odd
                markup.row(*collection)

            # Add a "Next" button if there are more bots
            if len(bots) > 6 * page:
                next_button = types.InlineKeyboardButton("Next", callback_data=f'next:{page + 1}')
                markup.add(next_button)

            return markup
        except Exception as e:
            print(e)

    def add_navigation_buttons(self, markup, bots, page=1):
        if len(bots) > 6 * page:
            next_button = types.InlineKeyboardButton(">>", callback_data=f'page:{page + 1}')
            markup.add(next_button)
        if page != 1:
            previous_button = types.InlineKeyboardButton("<<", callback_data=f'page:{page - 1}')
            markup.add(previous_button)

    def pagination_bots(self, bots, page):
        end = 6 * page if len(bots) > 6 * page else len(bots)
        start = end - 6

        return bots[start:end]

    def add_transfer(self, bot_id, user_id, transfer, balance, photo_id=None, caption=None):
        try:
            date = datetime.now().strftime("%Y-%m-%d %H:%M")
            insert_transaction_query = '''
            INSERT INTO transactions (bot_id, user_id, date, photo_id, caption)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
            '''
            self.cursor.execute(insert_transaction_query, (bot_id, user_id, date, photo_id, caption))
            
            status = transaction_id = self.cursor.fetchone()[0]
            # Insert into the transfers table
            insert_transfer_query = '''
                INSERT INTO transfers (transactions_id, transfer, balance)
                VALUES (%s, %s, %s)
            '''
            self.cursor.execute(insert_transfer_query, (transaction_id, transfer, balance))
            self.connection.commit()

        except Exception as e:
            print(e)
            status = False
            self.connection.rollback()
        
        finally :
            return status

    def is_valid_amount(self, amount):
        try:
            amount = float(amount.strip())
            valid = amount > 0 
            return valid
        except :
            valid = False

    def check_photo(self, message):
        if message.content_type != "photo":
            force_reply = types.ForceReply()
            message_text = f"""
                لم تقم بارفاق صوره في الرساله من فضلك اعد الارسال المطلوب
            """
            self.bot.send_message(message.chat.id, message_text, reply_markup=force_reply)
            return False
        return True

    def parse_call(self, call):
        key_value = call.split(";")
        data = {}
        for pair in key_value:
            pair = pair.split(":")
            data[pair[0]] = pair[1]
        return data

    def get_transaction(self, transaction_id):
        self.cursor.execute(f"""
        SELECT transactions.user_id, transfers.balance 
        FROM transactions JOIN transfers ON transactions.id = transfers.transactions_id                   
        WHERE transactions.id = {transaction_id}
        """)
        result = self.cursor.fetchone()
        return {
            "user" : result[0],
            "amount" : result[1]
        }
    
    def back_keyboard(self):
        back_button = types.ReplyKeyboardMarkup(resize_keyboard=True)
        back_button.add("الغاء")
        return back_button

    def back_menu(func):
        def wrapper(self, message, *args, **kwargs):
            if message.text == "الغاء" or message.text == "/start":
                return self.start(message)
            else:
                return func(self, message, *args, **kwargs)
        return wrapper
    
    def get_balance(self, user_id):
        self.cursor.execute(f'''
            SELECT balance from sellers WHERE user_id = '{user_id}'
        ''')
        # print(f"Balance : {self.cursor.fetchone()}")
        balance =  self.cursor.fetchone()[0]
        return balance

    def change_balance(self, user_id, amount):
        balance = self.get_balance(user_id) + amount
        self.cursor.execute(f'''
            UPDATE sellers set balance={balance} WHERE user_id='{user_id}'
        ''')
    #==========================================
    def __init__(self, api_token):
        self.bot = telebot.TeleBot(api_token)
        self.bot_collection = {}
        self.connection = psycopg2.connect(
            database="manager_builder",
            user="manager_builder_owner",
            password="QjbXi9gDNpP7",
            host="ep-delicate-tooth-a2u3cnv5.eu-central-1.aws.neon.tech",
            port="5432"
        )
        self.url = "https://xenogeneic-jannelle-joethon-b834bbe8.koyeb.apps"
        self.cursor = self.connection.cursor()
        self.time_zone = pytz.timezone('Africa/Cairo')
        self.admin = "1019315752"
        
        # Register handlers
        self.bot.message_handler(commands=['start'])(self.start)
        self.bot.message_handler(func= lambda message : message.text == 'اضافه بوتات')(self.add_bot)
        self.bot.message_handler(func= lambda message : message.text == 'البوتات الخاصه بي')(self.my_bots)
        self.bot.message_handler(func= lambda message : message.text == 'الحساب')(self.account)
        self.bot.message_handler(func= lambda message : message.text == 'ايداع')(self.deposit)
        self.bot.message_handler(func= lambda message : message.text == 'سحب')(self.withdraw)
        # self.bot.message_handler(func= lambda message : message.text == 'اضافه بوتات')(self.add_bot)
        # self.bot.message_handler(func= lambda message : message.text == 'البوتات الخاصه بي')(self.my_bots)
        # self.bot.message_handler(func= lambda message : message.text == 'الحساب')(self.account)
        # self.bot.message_handler(func= lambda message : message.text == 'ايداع')(self.deposit)
        # self.bot.message_handler(func= lambda message : message.text == 'سحب')(self.withdraw)
        
        # Inline keyboard handler
        self.bot.callback_query_handler(func=lambda call: call.data.startswith("type:transfer"))(self.process_transfer)
        self.bot.callback_query_handler(func=lambda call: call.data.startswith("page:"))(self.pagination_handler)
        self.bot.callback_query_handler(func=lambda call: call.data.startswith("bot:"))(self.bot_display)              
        self.bot.callback_query_handler(func=lambda call: call.data.startswith("id:"))(self.process_bot)              

    # Start => Register User + Display Hello Message + Keyboard [add bot - my bots - account - deposit - withdraw - check bot] | admin = [Bots Stats - Deposit Stats - Withdraw Stats - Orders]
    def start(self, message):
        user_id = message.from_user.id
        self.register_user(user_id)
        markup = self.get_main_keyboard(user_id)
        self.bot.send_message(message.chat.id, "مرحبا بكم في مدير البوتات للتنظيم تجارتك", reply_markup=markup)
    
    # add_bot => Display message + wait for response with token  => add_bot_2 => valid token display success else add_bot function again
    def add_bot(self, message):
        keyboard = self.back_keyboard()
        msg = self.bot.send_message(message.chat.id, "قم بارسال التوكن الخاصه بالبوت للتفعيل", reply_markup=keyboard)
        self.bot.register_next_step_handler(msg, self.complete_bot_register)
    
    @back_menu
    def complete_bot_register(self, message):
        try:
            token = message.text
            user_id = message.from_user.id
            seller_id = self.get_seller(user_id)
            # Check if user has balance enough
            self.bot.send_message(message.chat.id, "يرجي العلم لتفعيل البوت يجب ان يكون حسابك به 50 جم.. يمكنك حفظ البوت و تفعيله عد الشحن")
            if self.validate_token(token):
                bot_username = self.get_bot_username(token)
                if self.is_bot_exist(token):
                    return
                
                self.cursor.execute(f'''
                    INSERT INTO bots (bot_token, username, status, seller_id) VALUES ('{token}', '{bot_username}', 'stopped', {seller_id})
                ''')
                self.connection.commit()
                self.create_bot(token, self.url)
                message_text = "تم اضافه البوت بنجاح!\nاذهب للبوتات الخاصه بي لتفعيل البوت"
                self.bot.send_message(message.chat.id, message_text)
                self.start(message)
            else:
                keyboard = self.back_keyboard()
                msg = self.bot.send_message(message.chat.id, "التوكن غير صالح برجاء ارسال التوكن الصحيح!", reply_markup=keyboard)
                self.bot.register_next_step_handler(msg, self.complete_bot_register)
        except Exception as e:
            self.connection.rollback()
            print(e)

    # my_bots => Display inline Keyboard limit 6 bots per page => choose bot => Display Inline Keyboard [Stop/Start - Delete]    
    def my_bots(self, message):
        user_id = message.from_user.id
        seller_id = self.get_seller(user_id)
        self.cursor.execute('''
            SELECT * FROM bots WHERE seller_id = %s
        ''', (seller_id,))
        bots = self.cursor.fetchall()
        try:
            if bots:
                markup = self.get_bots_keyboard(bots, 1)
                self.bot.send_message(message.chat.id, "البوتات الخاصه بيك", reply_markup=markup)
            else:
                self.bot.send_message(message.chat.id, "لا يوجد بوتات")
        except Exception as e:
            print(e)

    # Need to be fixed
    def pagination_handler(self, call):
        page = int(call.data.split(':')[1])
        user_id = call.from_user.id
        
        self.cursor.execute('''
            SELECT * FROM bots WHERE seller_id = %s
        ''', (user_id,))
        bots = self.cursor.fetchall()
        
        if bots:
            markup = self.get_bots_keyboard(bots, page)
            self.add_navigation_buttons(markup, bots, page)
            self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)

    # account => Display Stats [Username - User_id - No_of_bots - Balance]
    def account(self, message):
        user_id = message.from_user.id
        try :
            self.cursor.execute('''
                SELECT COUNT(bots.*), balance FROM bots RIGHT JOIN sellers ON bots.seller_id = sellers.id WHERE sellers.user_id = '%s'
                GROUP BY sellers.balance
            ''', (user_id,))
            bot_count, balance = self.cursor.fetchone()

        except Exception as e:
            print(e)
        username = message.from_user.username
        
        account_info = f"المعرف: {username} \n رقم الحساب ID: {user_id} \n عدد البوتات: {bot_count} \n الرصيد: {balance} جم"
        self.bot.send_message(message.chat.id, account_info)
    
    def deposit(self, message):
        text = """
        برجاء ارسال صوره من التحويل و قيمه المبلغ ارقام فقط في اسفل التحويل 
        مثال : 50
        """
        keyboard = self.back_keyboard()
        msg = self.bot.send_message(message.chat.id, text, reply_markup=keyboard)
        self.bot.register_next_step_handler(msg, self.handle_deposit)
    
    @back_menu
    def handle_deposit(self, message):
        try:
            amount = message.caption.strip()
            if not (self.check_photo(message) and self.is_valid_amount(amount)):
                self.deposit(message)
                return
            # Insert new Order
            amount = float(message.caption.strip())
            photo = message.photo[-1].file_id
            bot_id = self.get_self_id()
            user_id = message.from_user.id
            transfer = 'deposit'
            transaction_id = self.add_transfer(bot_id=bot_id, user_id=user_id, transfer=transfer, balance=amount, photo_id=photo)
            
            if not transaction_id:
                text = """
                    لقد حدث خطا برجاء الارسال مره اخري
                """
                self.bot.send_message(message.chat.id, text)
                self.deposit(message)
                return
            
            # Send Admin notification + Keyboard to handle acceptance, rejection
            data = f"type:transfer;transaction:{transaction_id};amount:{amount};action:"
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            accept = types.InlineKeyboardButton("accept", callback_data=f"{data}accept")
            reject = types.InlineKeyboardButton("reject", callback_data=f"{data}reject")
            keyboard.add(accept, reject)
            self.bot.send_photo(self.admin, photo, amount, reply_markup=keyboard)
            # Send Seller success message
            self.bot.send_message(message.chat.id, "لقد تم استلام الطلب بنجاح!")
            self.start(message)
        except Exception as e:
            print(e)
    
    def send_rejection(self, message, chat_id):
        text = f"""
        لقد تم رفض طلبكم بسبب :
        {message.text}
        """
        self.bot.send_message(chat_id, text)
    
    def withdraw(self, message):
        # Take Balance
        text = " قم بارسال المبلغ الذي تريد سحبه بدون كسور و يكون ارقام فقط مثل : 50"
        keyboard = self.back_keyboard()
        msg = self.bot.send_message(message.chat.id, text, reply_markup=keyboard)
        self.bot.register_next_step_handler(msg, self.get_payment_method)

    @back_menu
    def get_payment_method(self, message):
        if not self.is_valid_amount(message.text):
            self.withdraw(message)
            return
        amount = float(message.text.strip())
        user_id = message.from_user.id
        keyboard = self.back_keyboard()
        if not self.check_balance(user_id, amount):
            text = " المبلغ المطلوب اكبر من رصيدك الحالي برجاء اعاده المحاوله"
            self.bot.send_message(message.chat.id, text, reply_markup=keyboard)
            self.withdraw(message)
            return

        # Take Payment Method
        text = " قم بارسال وسيله الدفع مثال : رقم فودافون كاش 0123456789"
        msg = self.bot.send_message(message.chat.id, text, reply_markup=keyboard)
        self.bot.register_next_step_handler(msg, self.send_withdraw_request, amount)

    # Send Admin
    @back_menu
    def send_withdraw_request(self, message, amount):
        try :                                      
            bot_id = self.get_self_id()
            user_id = message.from_user.id
            transfer = 'withdraw'
            transaction_id = self.add_transfer(bot_id=bot_id, user_id=user_id, transfer=transfer, balance=-amount, caption=message.text)
            if not transaction_id:
                text = """
                    لقد حدث خطا برجاء الارسال مره اخري
                """
                self.bot.send_message(message.chat.id, text)
                self.withdraw(message)
                return
            
            # Send Admin notification + Keyboard to handle acceptance, rejection
            amount = -amount
            data = f"type:transfer;transaction:{transaction_id};amount:{amount};action:"
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            accept = types.InlineKeyboardButton("accept", callback_data=f"{data}accept")
            reject = types.InlineKeyboardButton("reject", callback_data=f"{data}reject")
            keyboard.add(accept, reject)
            withdraw_text = f"""
Withdraw Request
================
User : {user_id}
Amount : {amount}
Transaction_id : {transaction_id}
            """
            self.bot.send_message(self.admin, withdraw_text, reply_markup=keyboard)
            # Send Seller success message
            self.bot.send_message(message.chat.id, "لقد تم استلام الطلب بنجاح!")
            self.start(message)
        except Exception as e:
            print(e)
    
    def process_transfer(self, call):
        # Parse Data to Dict
        data = self.parse_call(call.data)
        # Change status => success
        action = data['action']
        transaction_id = data['transaction']
        self.cursor.execute(f"""
            UPDATE transactions set status='{action}' WHERE id={transaction_id}
        """)

        # Get Transaction
        transaction = self.get_transaction(transaction_id)
        user_id = transaction['user']

        # Extract message data
        admin_chat = call.message.chat.id
        message_id = call.message.id


        try:
        # Process Success
            if action == "accept":
                amount = float(transaction['amount'])
                # Add amount to seller
                self.change_balance(user_id, amount)
                # Send Seller notification
                self.bot.send_message(user_id, "لقد قد تم الموافقه علي طلبكم بنجاح!")

            else:
                msg = self.bot.send_message(call.message.chat.id, "Give reason for rejection")
                self.bot.register_next_step_handler(msg, self.send_rejection, user_id)

            self.bot.delete_message(admin_chat, message_id)
            self.connection.commit()
        except Exception as e:
                print(e)
                self.connection.rollback()

    def back_menu(self, message):
        self.start(message)

    def bot_display(self, call):
        try:
            message_id = call.message.id
            chat_id = call.message.chat.id
            data = self.parse_call(call.data)
            if "action" in data:
                # Delete then display
                self.bot.delete_message(chat_id=chat_id, message_id=message_id)
                self.my_bots(call.message)
                return
            
            bot_id = data['bot']
            name = data['name']
            markup = types.InlineKeyboardMarkup(row_width=2)
            start = types.InlineKeyboardButton('تشغيل', callback_data=f'id:{bot_id};action:start')
            stop = types.InlineKeyboardButton('ايقاف', callback_data=f'id:{bot_id};action:stop')
            delete = types.InlineKeyboardButton('حذف', callback_data=f'id:{bot_id};action:delete')
            back_menu = types.InlineKeyboardButton('الرجوع', callback_data=f'bot:{bot_id};action:back')
            markup.add(start, stop, delete, back_menu)
            self.bot.edit_message_text(f"البوت : {name}", chat_id=chat_id, message_id=message_id, reply_markup=markup)
        except Exception as e:
            print(e)

    def process_bot(self, call):
        data = self.parse_call(call.data)
        bot_id = data['id']
        action = data['action']
        message_id = call.message.id
        chat_id = call.message.chat.id
        self.bot.delete_message(chat_id=chat_id, message_id=message_id)

        query = f"""
        SELECT bot_token from bots 
        WHERE id = {bot_id}
        """
        self.cursor.execute(query)
        token = self.cursor.fetchone()[0]
        client_bot = ClientBot(token)
        try:
            if action == "delete":
                text = "تم حذف البوت بنجاح!"
                client_bot.delete_webhook()
                query = f"""
                DELETE FROM bots 
                WHERE id = {bot_id}
                """
                try:
                    self.cursor.execute(query)
                    self.connection.commit()
                except Exception as e:
                    print(e)
                    self.connection.rollback()
            
            elif action == "start" :
                text = client_bot.active_bot(chat_id, self.url)
            elif action == "stop" :
                text = "تم ايقاف البوت بنجاح"
                client_bot.deactive_bot()
            self.bot.send_message(chat_id, text)
        except Exception as e:
            print(e)
            

# Refactor code to use SQL 
# Refactor Sql schema to make use same table for more bots
# Add Buttons and Functionalities of Admin

class ClientBot:
    def __init__(self, api_token):
        self.bot = telebot.TeleBot(api_token)
        self.bot_token = api_token
        self.connection = psycopg2.connect(
            database="manager_builder",
            user="manager_builder_owner",
            password="QjbXi9gDNpP7",
            host="ep-delicate-tooth-a2u3cnv5.eu-central-1.aws.neon.tech",
            port="5432"
        )
        self.cursor = self.connection.cursor()
        self.time_zone = pytz.timezone('Africa/Cairo')
        self.welcome_message = ""
        self.changed = True

    # Functions
    def get_status(self):
        self.cursor.execute(f"""
            SELECT status FROM bots 
            WHERE bot_token='{self.bot_token}'
        """)
        return self.cursor.fetchone()[0]

    def change_status(self):
        try:
            print(self.active)
            self.cursor.execute(f"""
                UPDATE bots SET status='{self.active}' WHERE bot_token='{self.bot_token}'
            """)
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()

    def get_balance(self, user_id):
        print(user_id)
        self.cursor.execute(f'''
            SELECT balance from sellers WHERE user_id = '{user_id}'
        ''')
        # print(f"Balance : {self.cursor.fetchone()}")
        balance =  self.cursor.fetchone()[0]
        return balance

    def check_balance(self, user_id, amount=50):
        balance = self.get_balance(user_id)
        return balance >= amount

    def extend_expiration_date(self, date=None):
        if not date:
            date = datetime.now(self.time_zone)
        expriation_date = date + timedelta(days=30)
        return expriation_date.strftime("%d/%m/%Y, %H:%M")


    def change_balance(self, user_id, amount):
        balance = self.get_balance(user_id) + amount
        self.cursor.execute(f'''
            UPDATE sellers set balance={balance} WHERE user_id='{user_id}'
        ''')

    def check_expired(self, end_date):
        date_str = datetime.now(self.time_zone).strftime("%d/%m/%Y, %H:%M")
        date = datetime.strptime(date_str, "%d/%m/%Y, %H:%M")
        return end_date < date

    def active_bot(self, user_id, url):
        self.active = "active"
        if self.get_status() == self.active:
            return "البوت مفعل سابقا!"
        
        self.set_webhook(url)
        # Put expiration date
        self.cursor.execute(f"""
        SELECT expiration_date from bots
        WHERE bot_token='{self.bot_token}'
        """)
        end_date = self.cursor.fetchone()[0] or None
        if end_date:
            end_date = datetime.strptime(end_date, "%d/%m/%Y, %H:%M")
            if self.check_expired(end_date):
                if not self.check_balance(user_id):
                    return "ليس لديك رصيد كافي لاضافه البوت برجاء الشحن ب 50 جم اولا"
                expiration_date = self.extend_expiration_date(end_date)
                self.cursor.execute(f"""
                UPDATE bots SET expiration_date='{expiration_date}'
                WHERE bot_token='{self.bot_token}'
                """)
                
                # Charge User
                self.change_balance(user_id, -50)
                self.connection.commit()
        self.change_status()
        self.initialize_handlers()
        return "تم تفعيل البوت بنجاح!"

    def deactive_bot(self):
        self.active = "stopped"
        self.change_status()

    def set_webhook(self, url):
        self.active = "active"
        self.bot.delete_webhook()
        self.bot.set_webhook(url=f"{url}/{self.bot_token}", drop_pending_updates=True) 
    
    def delete_webhook(self):
        self.bot.remove_webhook()

    def get_self_id(self):
        query = f"SELECT id FROM bots WHERE bot_token='{self.bot_token}'"
        return self.get_one(query)[0]
    
    def get_admin(self):
        query = f"""
            SELECT sellers.user_id 
            FROM bots JOIN sellers ON sellers.id = bots.seller_id
            WHERE bots.bot_token='{self.bot_token}'
        """
        return self.get_one(query)[0]

    # Functions
    def get_users(self):
        bot_id = self.get_self_id()
        query = f"SELECT user_id FROM users WHERE bot_id={bot_id}"
        return self.get_all(query)

    def send_order_request(self, photo, caption, data):
        buttons = {
            "قبول" : data + "accept",
            "رفض" : data + "reject"
        }
        keyboard = self.build_inline_keyboard(buttons)
        admin = self.get_admin()
        self.bot.send_photo(admin, photo, caption, reply_markup=keyboard)

    def is_admin(self, user_id):
        admin = self.get_admin()
        return admin == str(user_id)

    def join_orders(self, orders):
        return """
-------------------------------
        """.join(orders)

    def parse_orders(self, orders):
        parsed_orders = {
            "pending" : [],
            "completed" : [],
            "pending_transactions" : []
        }
        status_table = {
            "reject" : "مرفوض",
            "accept" : "مقبول",
            "pending" : "تحت المراجعه"
        }
        # Return Dict 
        for order in orders :
            order_message = f"""
اسم الخدمه : {order[0]}
حاله الطلب : {status_table[order[1]]}
التاريخ : {order[2]}
\n
            """
            if order[1] == "pending":
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

    def parse_call_back_query(self, data):
        pairs = data.split(",")
        result = {}
        for pair in pairs:
            pair_list = pair.split(":")
            result[pair_list[0]] = pair_list[1]

        return result

    def build_inline_keyboard(self, buttons):
        KEYBOARD = types.InlineKeyboardMarkup(row_width=2)
        for button, value in buttons.items():
            KEYBOARD.add(types.InlineKeyboardButton(button, callback_data=str(value)))
        return KEYBOARD

    def build_reply_keyboard(self, buttons):
        KEYBOARD = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        KEYBOARD.add(*buttons)
        return KEYBOARD

    def get_chat_id(self, message):
        return message.chat.id

    def send_message(self, message, text, markups=None):
        chat_id = self.get_chat_id(message)
        try:
            self.bot.send_message(chat_id, text, reply_markup=markups)
        except Exception as e:
            print(e)

    def get_one(self, query):
        self.cursor.execute(query)
        result = self.cursor.fetchone()
        return result

    def get_all(self, query):
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        return results

    def get_all_services(self):
        query = f"SELECT name FROM services"
        return self.get_all(query)

    def get_service_by_name(self, service_name):
        query = f"SELECT description, price, quantity, payment_method, id FROM services WHERE name = '{service_name}' and bot_token='{self.bot_token}'"
        return self.get_one(query)

    def get_service_by_id(self, service_id):
        query = f"SELECT name, description, price, payment_method FROM services WHERE id = '{service_id}'"
        return self.get_one(query)

    def get_all_orders(self, status=[], user=None):
        if status :
            status_query = f"status IN ({repr(status)})"
            if isinstance(status, list):
                status = ", ".join(repr(value) for value in status)
                status_query = f"status IN ({status})"
        else:
            status_query = "1=1"

        query = f"""
        SELECT services.name, transactions.status, transactions.date, transactions.photo_id, transactions.caption, transactions.id, transactions.user_id FROM orders JOIN services
        ON services.id = orders.service_id
        JOIN transactions ON orders.transactions_id = transactions.id
        WHERE (user_id = '{user}' or '{user}' = 'None')
        AND ({status_query})
        AND transactions.bot_id = {self.get_self_id()}
        """
        return self.get_all(query)

    def check_user(self, user_id):
        self.cursor.execute('''
        SELECT * FROM users WHERE user_id='%s' and bot_id=%s
        ''', (user_id, self.get_self_id()))
        return self.cursor.fetchone()

    def register_user(self, user_id):
        if not self.check_user(user_id):
            try:
                self.cursor.execute('''
                    INSERT INTO users (user_id, bot_id) VALUES (%s, %s)
                ''', (user_id, self.get_self_id()))
                self.connection.commit()
            except Exception as e:
                self.connection.rollback()

    def get_welcome_message(self):
        if self.changed:
            self.cursor.execute(f"""
                SELECT welcome_message FROM bots
                WHERE bot_token='{self.bot_token}'
            """)
            self.welcome_message = self.cursor.fetchone()[0]
            self.changed = False
        return self.welcome_message

    def initialize_handlers(self):
        self.bot.message_handler(commands=['start'])(self.start_message)
        self.bot.message_handler(func=lambda message: message.text == "الخدمات")(self.get_services)
        self.bot.message_handler(func=lambda message: message.text == "الطلبات")(self.get_orders)
        self.bot.message_handler(func=lambda message: message.text == "اذاعه")(self.send_notifications)
        self.bot.message_handler(func=lambda message: message.text == "تواصل مع البائع")(self.send_admin)
        self.bot.message_handler(func=lambda message: message.text == "الاعدادات")(self.display_settings)
        self.bot.message_handler(func=lambda message: message.text)(self.forward_message)
        self.bot.callback_query_handler(lambda query: query.data.startswith("type:service"))(self.initialize_order)
        self.bot.callback_query_handler(lambda query: query.data.startswith("type:order"))(self.process_transfer)
        self.bot.callback_query_handler(func=lambda query: query.data.startswith("type:edit_service"))(self.edit_service)
        self.bot.callback_query_handler(func=lambda query: query.data.startswith("type:delete_service"))(self.delete_service)

    def send_admin(self, message):
        keyboard = self.build_reply_keyboard(['الغاء'])
        self.send_message(message, "ارسل رسالتك للبائع", keyboard)
        self.bot.register_next_step_handler(message, self.forward_message, True)

    def forward_message(self, message, step_handler=False):
        try:
            if step_handler or message.reply_to_message.forward_from:
                to_chat = self.get_admin()
                user = message.from_user.id
                if self.is_admin(user):
                    to_chat = message.reply_to_message.forward_from.id
                self.bot.forward_message(to_chat, message.chat.id, message.message_id)
        except Exception as e:
            print(e)


    def start_message(self, message):
        try:
            welcome_message = self.get_welcome_message()
            self.register_user(message.from_user.id)
            buttons = ["الخدمات", "الطلبات", "تواصل مع البائع"]
            if self.is_admin(message.from_user.id):
                buttons[2] = "اذاعه"
                buttons.append("الاعدادات")
            keyboard = self.build_reply_keyboard(buttons)
            self.send_message(message, welcome_message, keyboard)
        except Exception as e:
            print(e)

    def get_services(self, message):
        try:
            services = [service[0] for service in self.get_all_services()]
            if self.is_admin(message.from_user.id):
                services.append("اضافه خدمه")
            services.append("الرجوع للقائمه")
            keyboard = self.build_reply_keyboard(services)
            self.send_message(message, message.text, keyboard)
            self.bot.register_next_step_handler(message, self.display_service, keyboard)
        except Exception as e:
            print(e)

    def display_service(self, message, keyboard):
        try:
            service_name = message.text
            if service_name == "الرجوع للقائمه":
                self.start_message(message)
                return
            elif service_name == "اضافه خدمه":
                self.add_service(message)
                return
            
            service_description = self.get_service_by_name(service_name)
            if service_description:
                description = f"{service_description[0]} \n\nالسعر : {service_description[1]}\الكميه : {service_description[2]} \nتفاصيل الدفع : {service_description[3]}"
                service_id = f"id:{service_description[4]}"
                buttons = {
                    "شراء": f'type:service,{service_id},name:{service_name}'
                }
                if self.is_admin(message.from_user.id):
                    buttons = {"تعديل": f"type:edit_service,{service_id}", "حذف": f"type:delete_service,{service_id}"}
                keyboard = self.build_inline_keyboard(buttons)
                self.send_message(message, description, keyboard)
            else:
                self.send_message(message, "لا يوجد خدمات في الوقت الحالي", keyboard)
                self.bot.register_next_step_handler(message, self.display_service, keyboard)
        except Exception as e:
            print(e)

    def initialize_order(self, query):
        data = self.parse_call_back_query(query.data)
        item_id = data['id']
        message = query.message
        force_reply = types.ForceReply()
        message_text = f"""
        لقد قمت باختيار خدمه : {data['name']}
        برجاء ارسال صوره من التحويل
        مرفق المطلبات الخدمه مثل رقم او حساب..
        """
        self.send_message(message, message_text, force_reply)
        self.bot.register_next_step_handler(message, self.check_image, item_id)

    def check_image(self, message, item_id):
        if message.content_type != "photo":
            force_reply = types.ForceReply()
            message_text = f"""
            برجاء ارسال صوره من التحويل
            مرفق المطلبات الخدمه مثل رقم او حساب..
            """
            self.send_message(message, message_text, force_reply)
            self.bot.register_next_step_handler(message, self.check_image, item_id)
        else:
            self.place_order(message, item_id)

    def place_order(self, message, item_id):
        try:
            photo = message.photo[-1].file_id
            caption = message.caption
            message_text = """
            لقد تم استلام طلبكم بنجاح 
            سيتم الرد خلال 24-48 ساعه   
            """
            self.send_message(message, message_text)

            user_id = message.from_user.id
            cairo_tz = pytz.timezone('Africa/Cairo')
            date = datetime.now(cairo_tz).strftime("%d/%m/%Y, %H:%M")
            query = f"INSERT INTO transactions (bot_id, user_id, date, status, photo_id, caption) VALUES ({self.get_self_id()}, {user_id}, '{date}', 'pending', '{photo}', '{caption}') RETURNING id"
            self.cursor.execute(query)
            transaction_id = self.cursor.fetchone()[0]
            query = f"INSERT INTO orders (service_id, transactions_id) VALUES ({item_id}, {transaction_id})"
            self.cursor.execute(query)
            self.connection.commit()

            data = f'type:order,id:{transaction_id},user:{user_id},status:'
            self.send_order_request(photo, caption, data)
        except Exception as e:
            print(e)
            self.connection.rollback()

    def get_orders(self, message):
        keyboard = self.build_reply_keyboard(["قيد الانتظار", "الطلبات السابقه", "الكل"])
        message_text = "ما هي حاله الطلبات التي تريد؟"
        self.send_message(message, message_text, keyboard)
        self.bot.register_next_step_handler(message, self.get_orders_from_db)

    def get_orders_from_db(self, message):
        user_id = message.from_user.id
        status = message.text
        if status == "قيد الانتظار":
            status = "pending"
        elif status == "الطلبات السابقه":
            status = ["accept", "reject"]
        else:
            status = None
        try:
            if self.is_admin(user_id):
                orders = self.get_all_orders(status)
            else:
                orders = self.get_all_orders(status, user_id)
            parsed_orders = self.parse_orders(orders)
            print(parsed_orders)
            self.send_orders_messages(message, parsed_orders)
        except Exception as e:
            print(e)

    def send_orders_messages(self, message, parsed_orders):
        user_id = message.from_user.id
        self.send_message(message, message.text)
        completed_orders = self.join_orders(parsed_orders['completed'])
        if self.is_admin(user_id):
            for pending_transaction in parsed_orders['pending_transactions']:
                photo = pending_transaction['photo']
                caption = pending_transaction['caption']
                order_id = pending_transaction['order_id']
                data = f'type:order,id:{order_id},user:{pending_transaction["user_id"]},status:'
                self.send_order_request(photo, caption, data)
        else:
            pending_orders = self.join_orders(parsed_orders['pending'])
            self.send_message(message, pending_orders)
        if completed_orders:
            self.send_message(message, completed_orders)

    def send_notifications(self, message):
        force_reply = types.ForceReply()
        message_text = "برجاء ارسال الرساله حتي تصل الي المستخدمين"
        self.send_message(message, message_text, force_reply)
        self.bot.register_next_step_handler(message, self.send_message_to_users)

    def send_message_to_users(self, message):
        users = [user[0] for user in self.get_users()]
        print(users)
        for user in users:
            self.bot.send_message(user, message.text)
        self.send_message(message, "تم الارسال للكل بنجاح")
    
    # Seller Section
    def process_transfer(self, call):
        # Parse Data to Dict
        data = self.parse_call_back_query(call.data)
        # Change status => success
        action = data['status']
        transaction_id = data['id']
        self.cursor.execute(f"""
            UPDATE transactions set status='{action}' WHERE id={transaction_id}
        """)
        # Extract message data
        user_id = data['user']
        admin_chat = call.message.chat.id
        message_id = call.message.id

        try:
        # Process Success
            if action == "accept":
                # Send Seller notification
                self.bot.send_message(user_id, "لقد قد تم الموافقه علي طلبكم بنجاح!")

            else:
                msg = self.bot.send_message(call.message.chat.id, "اعطي سبب الرفض للعميل")
                self.bot.register_next_step_handler(msg, self.send_rejection, user_id)

            self.bot.delete_message(admin_chat, message_id)
            self.connection.commit()
        except Exception as e:
            print(e)
            self.connection.rollback()

    def send_rejection(self, message, chat_id):
        text = f"""
    لقد تم رفض طلبكم بسبب :
    {message.text}
        """
        self.bot.send_message(chat_id, text)

    def add_service(self, message):
        if self.is_admin(message.from_user.id):
            force_reply = types.ForceReply()
            self.send_message(message, "ما هي اسم الخدمه التي تقدمها؟", force_reply)
            self.bot.register_next_step_handler(message, self.get_service_description)
        else:
            self.send_message(message, "لست مصرح لك لتكون هنا")

    def get_service_description(self, message, service_id=None):
        try:
            service_name = message.text
            data = {'service_name': service_name}
            force_reply = types.ForceReply()
            self.send_message(message, "ضح وصف للخدمه و الشروط المطلوبه", force_reply)
            self.bot.register_next_step_handler(message, self.get_service_payment_method, data, service_id)
        except Exception as e:
            print(e)

    def get_service_payment_method(self, message, data, service_id):
        try:
            service_description = message.text
            data['service_description'] = service_description
            force_reply = types.ForceReply()
            self.send_message(message, "ما هي وسيله الدفع و الحساب الخاص بيها مثال : فودافون كاش 010000000", force_reply)
            self.bot.register_next_step_handler(message, self.get_service_quantity, data, service_id)
        except Exception as e:
            print(e)

    def get_service_quantity(self, message, data, service_id):
        try:
            service_payment_method = message.text
            data['service_payment_method'] = service_payment_method
            force_reply = types.ForceReply()
            self.send_message(message, " ما هو الكميه المتاحه؟ ادخل رقم بدون كسور او حروف", force_reply)
            self.bot.register_next_step_handler(message, self.get_service_price, data, service_id)
        except Exception as e:
            print(e)
    
    def get_service_price(self, message, data, service_id):
        service_quantity = message.text
        try:
            service_quantity = int(service_quantity)
            data['service_quantity'] = service_quantity
            force_reply = types.ForceReply()
            self.send_message(message, " ما هو سعر الخدمه؟", force_reply)
            self.bot.register_next_step_handler(message, self.save_service, data, service_id)
        except ValueError:
            self.send_message(message, "برجاء ادخال ارقام صحيحه فقط..")
            self.bot.register_next_step_handler(message, self.get_service_price, data, service_id)
        except Exception as e:
            print(e)

    def save_service(self, message, data, service_id):
        try:
            service_price = float(message.text)
            service_data = data
            bot_id = self.get_self_id()
            query = """
                INSERT INTO services (name, description, price, payment_method, bot_id, quantity)
                VALUES (%s, %s, %s, %s, %s, %s)"""
            if service_id :
                query = """
            UPDATE services SET name=%s, description=%s, price=%s, payment_method=%s, bot_id=%s, quantity=%s
            """
            self.cursor.execute(query, (service_data['service_name'], service_data['service_description'], service_price, service_data['service_payment_method'], bot_id, service_data['service_quantity']))
            self.connection.commit()
            self.send_message(message, "تم حفظ الخدمه بنجاح")
            self.start_message(message)
        except ValueError:
            self.send_message(message, "برجاء ادخال ارقام فقط..")
            self.bot.register_next_step_handler(message, self.save_service)
        except Exception as e:
            print(e)
            self.connection.rollback()

    def edit_service(self, query):
        try:
            service_id = self.parse_call_back_query(query.data)['id']
            buttons = ["الاسم", "الوصف", "وسيله الدفع", "السعر", "الكميه" ,"الكل"]
            keyboard = self.build_reply_keyboard(buttons)
            self.send_message(query.message, "ما الذي تريد تغيره؟", keyboard)
            self.bot.register_next_step_handler(query.message, self.process_edit_choice, service_id)
        except Exception as e:
            print(e)

    def process_edit_choice(self, message, service_id):
        edit_choice = message.text
        data = {
            "edit_choice" :  edit_choice
        }
        if edit_choice == "All":
            self.get_service_description(message, service_id)
        else:
            self.ask_for_new_value(message, service_id, data)

    def ask_for_new_value(self, message, service_id, data):
        edit_choice = data['edit_choice']
        prompt = f" ادخل القيمه الجديده ل {edit_choice}"
        force_reply = types.ForceReply()
        self.send_message(message, prompt, force_reply)
        self.bot.register_next_step_handler(message, self.update_service, service_id, edit_choice)

    def update_service(self, message, service_id, edit_choice):
        try:
            new_value = message.text
            field_map = {
                "الاسم": "name",
                "الوصف": "description",
                "وسيله الدفع": "payment_method",
                "السعر": "price",
                "الكميه" : "quantity"
            }
            field = field_map[edit_choice]
            self.cursor.execute(f'''
                UPDATE services SET {field} = %s WHERE id = %s
            ''', (new_value, service_id))
            self.connection.commit()
            self.send_message(message, f"تم تحديث الخدمه {edit_choice} بنجاح!")
        except Exception as e:
            self.connection.rollback()


    def delete_service(self, query):
        try:
            service_id = self.parse_call_back_query(query.data)['id']
            self.cursor.execute('''
                DELETE FROM services WHERE id = %s
            ''', (service_id,))
            self.connection.commit()
            self.bot.delete_message(query.message.chat.id, query.message.id)
            msg = "تم حذف الخدمه بنجاح"
        except Exception as e:
            self.connection.rollback()
            msg = "حدث خطا برجاء المحاوله مره اخري"

            print(e)

        self.send_message(query.message, msg)
        
    def display_settings(self, message):
        if not self.is_admin(message.from_user.id):
            return
        buttons = ['تغيير رساله بدايه البوت', 'العوده']
        keyboard = self.build_reply_keyboard(buttons)
        self.send_message(message, message.text, keyboard)
        self.bot.register_next_step_handler(message, self.handle_settings)

    def handle_settings(self, message):
        text = message.text
        if text in ["/start", "العوده"]:
            self.start_message(message)
            return
        if text == 'تغيير رساله بدايه البوت':
            self.send_message(message, "ارسل الرساله الترحيبيه الجديده")
            self.bot.register_next_step_handler(message, self.save_welcome_message)
            return
    
    def save_welcome_message(self, message):
        text = "تم تسجيل الرساله بنجاح!"
        try:
            self.cursor.execute(f"""
            UPDATE bots SET welcome_message='{message.text}'
            WHERE bot_token='{self.bot_token}'
            """)
            self.connection.commit()
            self.changed = True
        except Exception as e:
            print(e)
            self.connection.rollback()
            text = "حدث خطا برجاء المحاوله مره اخري!"

        self.send_message(message, text)
        self.start_message(message)
        return