import os
import asyncio
import json

from binance import AsyncClient, DepthCacheManager, BinanceSocketManager
from dotenv import load_dotenv

async def main():
    # Get trading pair:
    TRADESYMBOL = input("Enter the symbol you'd like to trade (ex: BTCUSD): ")
    SELLPOSITIONDELTA = float(input("Enter the sell position delta (ex: .02): "))
    BUYPOSITIONDELTA = float(input("Enter the buy position delta (ex: .015): "))
    BASEAMOUNTTOTRADE = float(input("Enter the base currency amount to trade with (BTC ex: 0.00054): "))

    # initialise the client
    client = await AsyncClient.create()

    # get env variables for API KEY and SECRET
    load_dotenv()

    client = AsyncClient(os.getenv('API_KEY'), os.getenv('API_SECRET'), tld='us')

    symbolInfo = await client.get_symbol_info(TRADESYMBOL)

    info = await client.get_account()
    print(info)

    fees = await client.get_trade_fee(symbal=TRADESYMBOL)

    print(fees)

    # initialise websocket factory manager
    bsm = BinanceSocketManager(client)

    # create listener using async with
    # this will exit and close the connection after 5 messages
    async with bsm.trade_socket(TRADESYMBOL) as ts:
        while True:
            res = await ts.recv()
            print(f'recv {res}')

    await client.close_connection()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())