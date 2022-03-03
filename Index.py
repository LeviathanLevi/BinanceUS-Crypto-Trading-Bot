import os

from binance import Client, ThreadedWebsocketManager, ThreadedDepthCacheManager
from dotenv import load_dotenv

load_dotenv()

client = Client(os.getenv('API_KEY'), os.getenv('API_SECRET'))

API_URL = "https://api.binance.us"

#print(os.getenv('API_KEY'))

# get all symbol prices
#prices = client.get_all_tickers()
while True:
    price = client.get_symbol_ticker(symbol='BTCUSDP')['price'] #Get price of a ticker
    print(price)

