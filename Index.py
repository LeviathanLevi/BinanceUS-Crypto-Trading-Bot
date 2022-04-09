from ast import Not
import os
import asyncio
import json
import math
from symtable import Symbol
from operator import itemgetter
from binance import AsyncClient, DepthCacheManager, BinanceSocketManager
from dotenv import load_dotenv

async def losePosition(tradeData):
    while tradeData['positionExists'] == True:
        print('lose')

async def gainPosition(tradeData):
    while tradeData['positionExists'] == False:
        print('gain')

async def beginTrading(tradeData):
    res = await tradeData['webSocket'].recv() 

    tradeData['currentPrice'] = res['p']
    tradeData['lastPeakPrice'] = res['p']
    tradeData['lastValleyPrice'] = res['p']

    if tradeData['positionExists'] == False:
        await gainPosition(tradeData)
    else:
        await losePosition(tradeData)

async def main():
    # Get trading pair:
    TRADESYMBOL = input('Enter the symbol you\'d like to trade (ex: BTCUSD): ')
    SELLPOSITIONDELTA = float(input('Enter the sell position delta (ex: .02): '))
    BUYPOSITIONDELTA = float(input('Enter the buy position delta (ex: .015): '))

    # initialise the client
    client = await AsyncClient.create()

    # get env variables for API KEY and SECRET
    load_dotenv()

    client = AsyncClient(os.getenv('API_KEY'), os.getenv('API_SECRET'), tld='us')

    symbolInfo = await client.get_symbol_info(TRADESYMBOL) # baseAssetPrecision and quotePrecision

    info = await client.get_account() # Fees: makerCommission and takerCommission 

    quoteTradeBalance = float(input('Enter the amount of {0} to trade with (BTC ex: 0.00054): '.format(symbolInfo['quoteAsset'])))

    # initialise websocket factory manager
    bsm = BinanceSocketManager(client)

    async with bsm.trade_socket(TRADESYMBOL) as ts:
        tradeData = {
            'positionExists': False,
            'lastPeakPrice': None,
            'lastValleyPrice': None,
            'TRADESYMBOL': TRADESYMBOL,
            'SELLPOSITIONDELTA': SELLPOSITIONDELTA,
            'BUYPOSITIONDELTA': BUYPOSITIONDELTA,
            'client': client,
            'symbolInfo': symbolInfo,
            'info': info,
            'quoteTradeBalance': quoteTradeBalance,
            'currentPrice': None,
            'webSocket': ts
        }

        await beginTrading(tradeData)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())