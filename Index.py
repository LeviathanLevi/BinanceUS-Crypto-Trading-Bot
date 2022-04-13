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

async def roundOrderSizeDown(tradeData, quantity):
    step_size = [float(_['stepSize']) for _ in tradeData['symbolInfo']['filters'] if _['filterType'] == 'LOT_SIZE'][0]
    step_size = '%.8f' % step_size
    step_size = step_size.rstrip('0')
    decimals = len(step_size.split('.')[1])
    return math.floor(quantity * 10 ** decimals) / 10 ** decimals

async def getTotalFees(order):
    totalCommission = 0.0
    for fill in order['fills']:
        totalCommission += float(fill['commission'])
        if fill['commissionasset'] != 'USD':
            print('WE HAVE A PROBLEM: commision Asset =' + fill['commissionasset'])
            quit()

    return totalCommission

async def sellPosition(tradeData):
    priceToSell = round(tradeData['currentPrice'], tradeData['symbolInfo']['quoteAssetPrecision'])
    orderSize = roundOrderSizeDown(tradeData['baseBalance'])

    print('Placing sell order, orderSize: ' + str(orderSize) + ' priceToSell: ' + str(priceToSell))

    order = await tradeData['client'].create_order(
        symbol=tradeData['tradeSymbol'],
        side=SIDE_SELL,
        type=ORDER_TYPE_LIMIT,
        timeInForce=TIME_IN_FORCE_FOK,
        quantity=orderSize,
        price=priceToSell)

    print('ORDER:')
    print(order)

    # wait for order to be filled or cancelled:
    index = 0
    while tradeData['positionExists'] == True and index < 300:
        index += 1
        await asyncio.sleep(1) 

        if order['status'] == ORDER_STATUS_FILLED:
            print('Order state is filled.')

            tradeData['positionExists'] = False

            profit = ((float(order['executedQty']) * float(order['price'])) - tradeData['positionAcquiredCost']) - getTotalFees(order)

            print('Sell order fees: ' + str(getTotalFees(order)) + ' quantitiy: ' + str(order['executedQty']) + ' price: ' + str(order['price']))

            now = datetime.now()
            dt_string = now.strftime('%d/%m/%Y %H:%M:%S')
            fo = open('orders.txt', 'a')
            fo.write(dt_string + ': Sell:' + tradeData['tradeSymbol'] + ' Price: ' + str(order['price']) + ' Quantity: ' + str(order['executedQty']) + ' Profit: ' + str(profit) + '\n')
            fo.close()

            break
    
    if tradeData['positionExists'] == True:
        await tradeData['client'].cancel_order(
        symbol=tradeData['tradeSymbol'],
        orderId=order['orderId'])

    

async def buyPosition(tradeData):
    amountToSpend = tradeData['quoteTradeBalance'] - (tradeData['quoteTradeBalance'] * (float(tradeData['accountInfo']['takerCommission']) * .0001))  #Subtract fees
    priceToBuy = round(tradeData['currentPrice'], tradeData['symbolInfo']['quoteAssetPrecision'])
    orderSize = amountToSpend / priceToBuy
    orderSize = await roundOrderSizeDown(tradeData, orderSize)
    
    print('Placing buy order, orderSize: ' + str(orderSize) + ' priceToBuy: ' + str(priceToBuy))

    order = await tradeData['client'].create_order(
        symbol=tradeData['tradeSymbol'],
        side=SIDE_BUY,
        type=ORDER_TYPE_LIMIT,
        timeInForce=TIME_IN_FORCE_FOK,
        quantity=orderSize,
        price=priceToBuy)

    print('ORDER:')
    print(order)

    # wait for order to be filled or cancelled:
    index = 0
    while tradeData['positionExists'] == False and index < 300:
        index += 1
        await asyncio.sleep(1) 

        if order['status'] == ORDER_STATUS_FILLED:
            print('Order state is filled.')

            tradeData['positionExists'] = True
            tradeData['positionAcquiredPrice'] = float(order['price'])
            tradeData['baseBalance'] = float(order['executedQty'])
            fees = getTotalFees(order)
            tradeData['positionAcquiredCost'] = (tradeData['baseBalance'] * tradeData['positionAcquiredPrice']) + fees

            print('positionAcquiredPrice: ' + str(tradeData['positionAcquiredPrice']) + ' baseBalance: ' + str(tradeData['baseBalance']) + ' fees: ' + fees + ' positionAcquiredCost: ' + str(tradeData['positionAcquiredPrice']))

            now = datetime.now()
            dt_string = now.strftime('%d/%m/%Y %H:%M:%S')
            fo = open('orders.txt', 'a')
            fo.write(dt_string + ': Buy:' + tradeData['tradeSymbol'] + ' Price: ' + str(order['price']) + ' Quantity: ' + str(order['executedQty']) + ' Cost: ' + str(tradeData['positionAcquiredPrice']) + '\n')
            fo.close()

            break
    
    if tradeData['positionExists'] == False:
        await tradeData['client'].cancel_order(
        symbol=tradeData['tradeSymbol'],
        orderId=order['orderId'])

async def losePosition(tradeData):
    while tradeData['positionExists'] == True:
        socketPriceUpdate = await tradeData['webSocket'].recv()
        tradeData['currentPrice'] = float(socketPriceUpdate['p'])

        if tradeData['lastPeakPrice'] < tradeData['currentPrice']:
            tradeData['lastPeakPrice'] = tradeData['currentPrice']
            tradeData['lastValleyPrice'] = tradeData['currentPrice']

        elif tradeData['lastValleyPrice'] > tradeData['currentPrice']: 
            tradeData['lastValleyPrice'] = tradeData['currentPrice']

            target = tradeData['lastPeakPrice'] - (tradeData['lastPeakPrice'] * tradeData['sellPositionDelta'])
            receivedValue = (tradeData['currentPrice'] * tradeData['baseBalance']) - ((tradeData['currentPrice'] * tradeData['baseBalance']) * ((float(tradeData['accountInfo']['takerCommission']) * .0001))) #Should Taker or Maker fees be used in this calculation?

            print('New Valley Price: ' + str(tradeData['lastValleyPrice']))
            print('Must be less than or equal to target to trigger a sell, target: ' + str(target) + ' and ' + 'the received value: ' + str(receivedValue) + ' must be greater than the  ' + 'positionAcquiredCost: ' + str(tradeData['positionAcquiredCost']))

            if (tradeData['lastValleyPrice'] <= target) and (receivedValue > tradeData['positionAcquiredCost']): 
                print('Entering sell position.')
                await sellPosition(tradeData)

async def gainPosition(tradeData):
    while tradeData['positionExists'] == False:
        socketPriceUpdate = await tradeData['webSocket'].recv()
        tradeData['currentPrice'] = float(socketPriceUpdate['p'])

        if tradeData['lastPeakPrice'] < tradeData['currentPrice']:
            tradeData['lastPeakPrice'] = tradeData['currentPrice'] #new peak price hit

            target = tradeData['lastValleyPrice'] + (tradeData['lastValleyPrice'] * tradeData['buyPositionDelta'])
            
            print('New Peak Price: ' + str(tradeData['lastPeakPrice']))
            print('Must be greater than or equal to target to trigger a purchase, target: ' + str(target))

            if tradeData['lastPeakPrice'] >= target:
                print('Entering buy position.')
                await buyPosition(tradeData)

        elif tradeData['lastValleyPrice'] > tradeData['currentPrice']:
            tradeData['lastPeakPrice'] = tradeData['currentPrice']
            tradeData['lastValleyPrice'] = tradeData['currentPrice']

async def beginTrading(tradeData):
    socketPriceUpdate = await tradeData['webSocket'].recv() 
    tradeData['currentPrice'] = float(socketPriceUpdate['p'])
    tradeData['lastPeakPrice'] = tradeData['currentPrice']
    tradeData['lastValleyPrice'] = tradeData['currentPrice']

    while True:
        if tradeData['positionExists'] == False:
            print('Entering gain position function.')
            await gainPosition(tradeData)
        else:
            print('Entering lose position function.')
            await losePosition(tradeData)

async def main():
    tradeSymbol = input('Enter the symbol you\'d like to trade (ex: BTCUSD): ')
    sellPositionDelta = float(input('Enter the sell position delta (ex: .02): '))
    buyPositionDelta = float(input('Enter the buy position delta (ex: .015): '))

    client = await AsyncClient.create()

    load_dotenv()

    client = AsyncClient(os.getenv('API_KEY'), os.getenv('API_SECRET'), tld='us')

    symbolInfo = await client.get_symbol_info(tradeSymbol)

    accountInfo = await client.get_account()

    quoteTradeBalance = float(input('Enter the amount of {0} to trade with (BTC ex: 0.00054, should be less then the max for rounding errors, and greater then the minimum order amount): '.format(symbolInfo['quoteAsset'])))

    bsm = BinanceSocketManager(client)

    async with bsm.trade_socket(tradeSymbol) as ts:
        tradeData = {
            'positionExists': False,
            'lastPeakPrice': None,
            'lastValleyPrice': None,
            'tradeSymbol': tradeSymbol,
            'sellPositionDelta': sellPositionDelta,
            'buyPositionDelta': buyPositionDelta,
            'client': client,
            'symbolInfo': symbolInfo,
            'accountInfo': accountInfo,
            'quoteTradeBalance': quoteTradeBalance,
            'currentPrice': None,
            'webSocket': ts,
            'positionAcquiredCost': None,
            'positionAcquiredPrice': None,
            'baseBalance': None
        }

        print('Initial Trade Data: ')
        print(tradeData)

        await beginTrading(tradeData)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())