import sqlite3

# Establish a connection to the SQLite database
conn = sqlite3.connect('manager_bot.db')
cursor = conn.cursor()

# Insert records into the services table
services = [
    ('Website Development', 'Professional website development services', 1000.00, 'Bank Transfer', 1),
    ('SEO Optimization', 'Search engine optimization to improve website ranking', 500.00, 'Credit Card', 1),
    ('Graphic Design', 'Designing logos, banners, and other graphics', 300.00, 'PayPal', 1),
    ('Content Writing', 'High-quality content writing services', 200.00, 'PayPal', 2),
    ('Social Media Management', 'Managing social media accounts for businesses', 800.00, 'Bank Transfer', 2)
]

# Define the query to insert data
query = '''INSERT INTO service (name, description, price, payment_method, bot_id) 
           VALUES (?, ?, ?, ?, ?)'''

# Execute the query for each service
for service in services:
    cursor.execute(query, service)
    conn.commit()

# Commit the transaction
conn.commit()

# Print the number of inserted records
print(f"Inserted {cursor.rowcount} records into the services table.")

# Close the connection
conn.close()
