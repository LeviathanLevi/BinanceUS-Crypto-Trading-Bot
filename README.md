# BinanceUS-Crypto-Trading-Bot

## Overview
Uses the BinanceUS exchange API to trade crypto. Implemented with python and the [python_binance](https://python-binance.readthedocs.io/en/latest/index.html) library. Bot uses a basic momentum trading strategy by default. The strategy gets two deltas from the user as a decimal, such as .02 (2%). One as the sell delta and buy delta. When the price goes up by the buyPositionDelta the bot will buy into a position. When the price goes down by the sellPositionDelta the bot will attempt to sell out but only if the trade is profitable. 

## Getting started:
1. Create a Binance.US API key under your exchange profile
2. Create a file literally named '.env' and add the following fields:

API_KEY=\<your api key>

API_SECRET=\<your api secret>

3. `pip install -r requirements.txt`
4. `python Index.py`
5. Follow the prompts entering your desired inputs

There is a way to use the test net with the Binance.US API to trade with fake money for testing. If anyone would like to help me implement this enviornment that'd be greatly appreciated :) . 

This bot is fairly minimal but makes for a great starting point to work on a algo trading bot. Please consider contributing to the project. 

## Disclaimer
This project is for informational purposes only. You should not construe any such information or other material as legal, tax, investment, financial, or other advice. Nothing contained here constitutes a solicitation, recommendation, endorsement, or offer by me or any third party service provider to buy or sell any securities or other financial instruments in this or in any other jurisdiction in which such solicitation or offer would be unlawful under the securities laws of such jurisdiction.

If you plan to use real money, USE AT YOUR OWN RISK.

Under no circumstances will I be held responsible or liable in any way for any claims, damages, losses, expenses, costs, or liabilities whatsoever, including, without limitation, any direct or indirect damages for loss of profits.