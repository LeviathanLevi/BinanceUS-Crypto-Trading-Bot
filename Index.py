from ast import Not
import os
import asyncio
import json
from symtable import Symbol
from operator import itemgetter

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

    symbolInfo = await client.get_symbol_info(TRADESYMBOL) # baseAssetPrecision and quotePrecision

    info = await client.get_account() # Fees: makerCommission and takerCommission 

    #Remove this and let the user enter the trading amount?
    availableQuoteBalance = None
    quoteBalance = next((balance for balance in info['balances'] if balance['asset'] == symbolInfo['quoteAsset']), None)
    if quoteBalance is not None:
        availableQuoteBalance = float(quoteBalance['free'])

    tradeData = {
        'positionExists': False,
        'lastPeakPrice': None,
        'lastValleyPrice': None
    }
    
    # initialise websocket factory manager
    bsm = BinanceSocketManager(client)

    async with bsm.trade_socket(TRADESYMBOL) as ts:

        while True:
            res = await ts.recv() # 'p'
            print(f'recv {res}')

    await client.close_connection()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())