import os
# from dotenv import load_dotenv, find_dotenv

# Load the environment variables from the .env file
# if find_dotenv():
#     load_dotenv(find_dotenv())

API_TOKEN = os.environ["TOKEN"] # Store in env
WEBHOOK_URL = os.environ["WEBHOOK"] # Store in env
WEBHOOK_PORT = 8000