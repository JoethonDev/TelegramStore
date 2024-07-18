import psycopg2
import logging
import pytz
import datetime


def is_expired(date):
    time_zone = pytz.timezone('Africa/Cairo')
    date = date.split(",")[0]
    now_date = datetime.datetime.now(time_zone)
    return now_date.strftime("%d/%m/%Y") == date

try:
    connection = psycopg2.connect(
                database="manager_builder",
                user="manager_builder_owner",
                password="QjbXi9gDNpP7",
                host="ep-delicate-tooth-a2u3cnv5.eu-central-1.aws.neon.tech",
                port="5432"
            )
except Exception as e:
    logging.exception("Connection Error!")
    logging.exception(e)

cursor = connection.cursor()
# Get bots
bots = []
try:
    query = "SELECT id, expiration_date FROM bots"
    cursor.execute(query)
    bots = cursor.fetchall()
except Exception as e:
    logging.exception("Fetching Bots Error!")
    logging.exception(e)

# Check Date
expired_bots = list()
for bot in bots:
    if is_expired(bot[1]):
        expired_bots.append(bot[0])

expired_bots = ",".join(expired_bots)

try:
    query = f"UPDATE bots SET status='stopped' WHERE id IN ({expired_bots})"
    cursor.execute(query)
except Exception as e:
    logging.exception("Updating Bots Error!")
    logging.exception(e)

connection.commit()
connection.close()