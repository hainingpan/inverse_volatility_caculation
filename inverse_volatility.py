#!/usr/local/bin/python3

# Author: Zebing Lin (https://github.com/linzebing)

from datetime import datetime, date
import math
import numpy as np
import time
import sys
import requests
import re

if len(sys.argv) == 1:
    symbols = ['UPRO', 'TMF']
else:
    symbols = sys.argv[1].split(',')
    for i in range(len(symbols)):
        symbols[i] = symbols[i].strip().upper()

num_trading_days_per_year = 252
window_size = 10
date_format = "%Y-%m-%d"
end_timestamp = int(time.time())
start_timestamp = int(end_timestamp - (1.4 * (window_size + 1) + 4) * 86400)


def get_volatility_and_performance(symbol,cookie,crumb):
    download_url = "https://query1.finance.yahoo.com/v7/finance/download/{}?period1={}&period2={}&interval=1d&events=history&crumb={}".format(symbol, start_timestamp, end_timestamp,crumb)
    lines = requests.get(download_url, cookies={'B': cookie}).text.strip().split('\n')
    print(download_url)
    print(lines)
    assert lines[0].split(',')[0] == 'Date'
    assert lines[0].split(',')[4] == 'Close'
    prices = []
    for line in lines[1:]:
        prices.append(float(line.split(',')[4]))
    prices.reverse()
    volatilities_in_window = []

    for i in range(window_size):
        volatilities_in_window.append(math.log(prices[i] / prices[i+1]))
        
    most_recent_date = datetime.strptime(lines[-1].split(',')[0], date_format).date()
    assert (date.today() - most_recent_date).days <= 4, "today is {}, most recent trading day is {}".format(date.today(), most_recent_date)

    return np.std(volatilities_in_window, ddof = 1) * np.sqrt(num_trading_days_per_year), prices[0] / prices[window_size] - 1.0


def get_cookie():
    url = 'https://finance.yahoo.com/quote/VOO/history?p=VOO'
    r = requests.get(url)
    txt = r.text 
    cookie = r.cookies['B']
    pattern = re.compile('.*"CrumbStore":\{"crumb":"(?P<crumb>[^"]+)"\}')
    for line in txt.splitlines():
        m = pattern.match(line)
        if m is not None:
            crumb = m.groupdict()['crumb']
        
    return cookie,crumb
    
cookie,crumb=get_cookie()
volatilities = []
performances = []
sum_inverse_volatility = 0.0
for symbol in symbols:
    volatility, performance = get_volatility_and_performance(symbol,cookie,crumb)
    sum_inverse_volatility += 1 / volatility
    volatilities.append(volatility)
    performances.append(performance)

print ("Portfolio: {}, as of {} (window size is {} days)".format(str(symbols), date.today().strftime('%Y-%m-%d'), window_size))
for i in range(len(symbols)):
    print ('{} allocation ratio: {:.2f}% (anualized volatility: {:.2f}%, performance: {:.2f}%)'.format(symbols[i], float(100 / (volatilities[i] * sum_inverse_volatility)), float(volatilities[i] * 100), float(performances[i] * 100)))

