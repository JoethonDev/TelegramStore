import psycopg2

# Establish connection
connection = psycopg2.connect(
    database="manager_builder",
    user="manager_builder_owner",
    password="QjbXi9gDNpP7",
    host="ep-delicate-tooth-a2u3cnv5.eu-central-1.aws.neon.tech",
    port="5432"
)
cursor = connection.cursor()

# Create the 'sellers' table
cursor.execute('''
CREATE TABLE IF NOT EXISTS sellers (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    balance REAL DEFAULT 0
)
''')

# Create the 'bots' table
cursor.execute('''
CREATE TABLE IF NOT EXISTS bots (
    id SERIAL PRIMARY KEY,
    bot_token TEXT NOT NULL,
    username TEXT NOT NULL,
    seller_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT ('stopped'),
    welcome_message TEXT DEFAULT ('welcome to service bot'),
    expiration_date TEXT,
    FOREIGN KEY (seller_id) REFERENCES sellers(id) ON DELETE CASCADE
)
''')

# Create the 'users' table
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    bot_id INTEGER,
    FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE
)
''')

# Create the 'transactions' table
cursor.execute('''
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    bot_id INTEGER,
    user_id TEXT,
    date TEXT,
    status TEXT DEFAULT ('pending'),
    photo_id TEXT,
    caption TEXT,
    FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE
)
''')

# Create the 'transfers' table
cursor.execute('''
CREATE TABLE IF NOT EXISTS transfers (
    id SERIAL PRIMARY KEY,
    transactions_id INTEGER NOT NULL,
    transfer TEXT NOT NULL,
    balance REAL,
    FOREIGN KEY (transactions_id) REFERENCES transactions(id) ON DELETE CASCADE
)
''')

# Create the 'services' table
cursor.execute('''
CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    quantity INTEGER NOT NULL,
    payment_method TEXT,
    bot_id INTEGER,
    FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE
)
''')

# Create the 'services' table
cursor.execute('''
CREATE TABLE IF NOT EXISTS plans (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    duration INTEGER NOT NULL,
    bot_id INTEGER,
    FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE
)
''')

# Create the 'orders' table
cursor.execute('''
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    service_id INTEGER,
    transactions_id INTEGER NOT NULL,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    FOREIGN KEY (transactions_id) REFERENCES transactions(id) ON DELETE CASCADE
)
''')

# Commit the changes
connection.commit()

# Close the cursor and connection
cursor.close()
connection.close()
