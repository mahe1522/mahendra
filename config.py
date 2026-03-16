import os

CLIENT_ID = os.environ.get('CLIENT_ID')
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
MAX_LOSS = int(os.environ.get('MAX_LOSS', -2500))
TARGET = int(os.environ.get('TARGET', 10000))
RISK = int(os.environ.get('RISK', 1500))
