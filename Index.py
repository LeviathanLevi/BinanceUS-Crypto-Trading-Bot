from ast import Not
import os
import asyncio
import json
import math
from symtable import Symbol
from operator import itemgetter
from binance import AsyncClient, DepthCacheManager, BinanceSocketManager
from dotenv import load_dotenv

async def sellPosition(tradeData):
    print("Attempting to sell position")
    tradeData['positionExists'] = False

async def buyPosition(tradeData):
    print("Attempting to buy position")
    tradeData['positionExists'] = True

async def losePosition(tradeData):
    while tradeData['positionExists'] == True:
        #update price:
        socketPriceUpdate = await tradeData['webSocket'].recv()
        tradeData['currentPrice'] = float(socketPriceUpdate['p'])

        if tradeData['lastPeakPrice'] < tradeData['currentPrice']:
            tradeData['lastPeakPrice'] = tradeData['currentPrice']
            tradeData['lastValleyPrice'] = tradeData['currentPrice']

        elif tradeData['lastValleyPrice'] > tradeData['currentPrice']: 
            tradeData['lastValleyPrice'] = tradeData['currentPrice']

            target = tradeData['lastPeakPrice'] - (tradeData['lastPeakPrice'] * tradeData['SELLPOSITIONDELTA'])
            receivedValue = (tradeData['currentPrice'] * tradeData['quoteTradeBalance']) - ((tradeData['currentPrice'] * tradeData['quoteTradeBalance']) * ((float(tradeData['info']['takerCommission']) * .0001)))

            if (tradeData['lastValleyPrice'] <= target) and (receivedValue > tradeData['positionAcquiredCost']): 
                await sellPosition(tradeData)

async def gainPosition(tradeData):
    while tradeData['positionExists'] == False:
        #update price:
        socketPriceUpdate = await tradeData['webSocket'].recv()
        tradeData['currentPrice'] = float(socketPriceUpdate['p'])

        if tradeData['lastPeakPrice'] < tradeData['currentPrice']:
            tradeData['lastPeakPrice'] = tradeData['currentPrice'] #new peak price hit

            target = tradeData['lastValleyPrice'] + (tradeData['lastValleyPrice'] * tradeData['BUYPOSITIONDELTA'])
            
            if tradeData['lastPeakPrice'] >= target:
                await buyPosition(tradeData)

        elif tradeData['lastValleyPrice'] > tradeData['currentPrice']:
            tradeData['lastPeakPrice'] = tradeData['currentPrice']
            tradeData['lastValleyPrice'] = tradeData['currentPrice']

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
            'webSocket': ts,
            'positionAcquiredCost': None
        }

        await beginTrading(tradeData)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())