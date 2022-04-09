from ast import Not
import os
import asyncio
import json
import math
from symtable import Symbol
from operator import itemgetter
from binance import AsyncClient, DepthCacheManager, BinanceSocketManager
from dotenv import load_dotenv

async def buyPosition(tradeData):
    print("Attempting to buy position")
    tradeData['positionExists'] = True

async def losePosition(tradeData):
    while tradeData['positionExists'] == True:
        print('lose')

async def gainPosition(tradeData):
    while tradeData['positionExists'] == False:
        #update price:
        socketPriceUpdate = await tradeData['webSocket'].recv()
        tradeData['currentPrice'] = float(socketPriceUpdate['p'])
        print(tradeData['currentPrice'])
        if tradeData['lastPeakPrice'] < tradeData['currentPrice']:
            tradeData['lastPeakPrice'] = tradeData['currentPrice'] #new peak price hit

            target = tradeData['lastValleyPrice'] + (tradeData['lastValleyPrice'] * tradeData['BUYPOSITIONDELTA'])
            
            print(tradeData['lastPeakPrice'])
            print('>=')
            print(target)

            if tradeData['lastPeakPrice'] >= target:
                print("TRUE")
                await buyPosition(tradeData)

        elif tradeData['lastValleyPrice'] > tradeData['currentPrice']:
            tradeData['lastPeakPrice'] = tradeData['currentPrice']
            tradeData['lastValleyPrice'] = tradeData['currentPrice']
            print('LVP' + str(tradeData['lastValleyPrice']))

async def beginTrading(tradeData):
    res = await tradeData['webSocket'].recv() 

    tradeData['currentPrice'] = float(res['p'])
    tradeData['lastPeakPrice'] = float(res['p'])
    tradeData['lastValleyPrice'] = float(res['p'])
    
    while True:
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