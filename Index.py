from ast import Not
import os
import asyncio
import json
import math
from symtable import Symbol
from operator import itemgetter
from binance import AsyncClient, DepthCacheManager, BinanceSocketManager
from dotenv import load_dotenv
from binance.enums import *
from datetime import datetime

async def round_down(tradeData, quantity):
    step_size = [float(_['stepSize']) for _ in tradeData['symbolInfo']['filters'] if _['filterType'] == 'LOT_SIZE'][0]
    step_size = '%.8f' % step_size
    step_size = step_size.rstrip('0')
    decimals = len(step_size.split('.')[1])
    return math.floor(quantity * 10 ** decimals) / 10 ** decimals

async def sellPosition(tradeData):
    print('Attempting to sell position')
    tradeData['positionExists'] = False

async def buyPosition(tradeData):
    amountToSpend = tradeData['quoteTradeBalance'] - (tradeData['quoteTradeBalance'] * (float(tradeData['info']['takerCommission']) * .0001))  #Subtract fees
    amountToSpend = round(amountToSpend, tradeData['symbolInfo']['quoteAssetPrecision'])
    priceToBuy = round(tradeData['currentPrice'], tradeData['symbolInfo']['baseAssetPrecision'])
    orderSize = amountToSpend / priceToBuy
    orderSize = await round_down(tradeData, orderSize)
    
    print('order info: ')
    print(amountToSpend)
    print(priceToBuy)
    print(orderSize)

    order = await tradeData['client'].create_order(
        symbol=tradeData['TRADESYMBOL'],
        side=SIDE_BUY,
        type=ORDER_TYPE_LIMIT,
        timeInForce=TIME_IN_FORCE_FOK,
        quantity=orderSize,
        price=priceToBuy)

    print('ORDER:')
    print(order)

    orderID = order['orderId']

    # wait for order to be filled or cancelled:
    index = 0
    while tradeData['positionExists'] == False and index < 300:
        index += 1
        await asyncio.sleep(1) 

        orderDetails = await tradeData['client'].get_order(symbol=tradeData['TRADESYMBOL'], orderId=orderID)

        print('orderDetails')
        print(orderDetails)

        if orderDetails['status'] == ORDER_STATUS_FILLED:
            tradeData['positionExists'] = True
            tradeData['positionAcquiredPrice'] = float(orderDetails['price'])
            tradeData['positionAcquiredCost'] = (float(orderDetails['origQty']) * float(orderDetails['price'])) + ((float(orderDetails['origQty']) * float(orderDetails['price'])) * (float(tradeData['info']['takerCommission']) * .0001)) 
            tradeData['baseBalance'] = float(orderDetails['executedQty'])

            now = datetime.now()
            dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

            fo = open("orders.txt", "a")
            fo.write(dt_string + ': Buy:' + tradeData['TRADESYMBOL'] + ' Price: ' + str(orderDetails['price']) + ' Quantity: ' + str(orderDetails['origQty']) + ' Cost: ' + str(tradeData['positionAcquiredPrice']) + '\n')
            fo.close()

            break
    
    if tradeData['positionExists'] == False:
        await tradeData['client'].cancel_order(
        symbol=tradeData['TRADESYMBOL'],
        orderId=orderID)

async def losePosition(tradeData):
    while tradeData['positionExists'] == True:
        #update price:
        socketPriceUpdate = await tradeData['webSocket'].recv()
        tradeData['currentPrice'] = float(socketPriceUpdate['p'])

        if tradeData['lastPeakPrice'] < tradeData['currentPrice']:
            tradeData['lastPeakPrice'] = tradeData['currentPrice']
            tradeData['lastValleyPrice'] = tradeData['currentPrice']
            print('LPP: ' + str(tradeData['lastPeakPrice']))

        elif tradeData['lastValleyPrice'] > tradeData['currentPrice']: 
            tradeData['lastValleyPrice'] = tradeData['currentPrice']

            target = tradeData['lastPeakPrice'] - (tradeData['lastPeakPrice'] * tradeData['SELLPOSITIONDELTA'])
            receivedValue = (tradeData['currentPrice'] * tradeData['baseBalance']) - ((tradeData['currentPrice'] * tradeData['baseBalance']) * ((float(tradeData['info']['takerCommission']) * .0001))) #Should Taker or Maker fees be used in this calculation?
            print(str(tradeData['currentPrice'] * tradeData['baseBalance']))
            print('-')
            print(str((tradeData['currentPrice'] * tradeData['baseBalance'])))
            print('*')
            print(str(((float(tradeData['info']['takerCommission']) * .0001))))

            print('testing: ' + 'LPP: ' + str(tradeData['lastValleyPrice']) + ' <= ' + str(target))
            print('and: ' + 'recivedValue: ' + str(receivedValue) + ' > ' + 'positionAcquiredCost: ' + str(tradeData['positionAcquiredCost']))

            if (tradeData['lastValleyPrice'] <= target) and (receivedValue > tradeData['positionAcquiredCost']): 
                await sellPosition(tradeData)

async def gainPosition(tradeData):
    while tradeData['positionExists'] == False:
        #update price:
        socketPriceUpdate = await tradeData['webSocket'].recv()
        tradeData['currentPrice'] = float(socketPriceUpdate['p'])

        if tradeData['lastPeakPrice'] < tradeData['currentPrice']:
            tradeData['lastPeakPrice'] = tradeData['currentPrice'] #new peak price hit
            print('NPP: ' + str(tradeData['currentPrice']))

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

    #TESTING:
    #tradeData['positionExists'] = True
    #tradeData['positionAcquiredCost'] = tradeData['quoteTradeBalance']
    #tradeData['positionAcquiredPrice'] = tradeData['currentPrice'] - (tradeData['currentPrice'] * .02)
    #tradeData['baseBalance'] = round((tradeData['quoteTradeBalance'] / tradeData['positionAcquiredPrice']), 8)
    #print('currentPrice: ' + str(tradeData['currentPrice']) + 'positionAcquiredPrice: ' + str(tradeData['positionAcquiredPrice']) + 'baseBalance: ' + str(tradeData['baseBalance']))

    

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
    print(symbolInfo)
    info = await client.get_account() # Fees: makerCommission and takerCommission 

    quoteTradeBalance = float(input('Enter the amount of {0} to trade with (BTC ex: 0.00054, should be less then the max for rounding errors, and greater then the minimum order amount): '.format(symbolInfo['quoteAsset'])))

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
            'positionAcquiredCost': None,
            'baseBalance': None
        }

        await beginTrading(tradeData)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

    