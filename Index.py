import os
import asyncio
import json

from binance import AsyncClient, ThreadedWebsocketManager, ThreadedDepthCacheManager
from dotenv import load_dotenv

async def main():
    # initialise the client
    client = await AsyncClient.create()

    # get env variables for API KEY and SECRET
    load_dotenv()
    print(os.getenv('API_KEY'))
    client = AsyncClient(os.getenv('API_KEY'), os.getenv('API_SECRET'), tld='us')

    #API_URL = "https://api.binance.us"

    # run some simple requests
    #print(json.dumps(await client.get_exchange_info(), indent=2))
    
    print(json.dumps(await client.get_symbol_ticker(symbol="BTCUSDT"), indent=2))

    print("started main") 

    await client.close_connection()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
   

