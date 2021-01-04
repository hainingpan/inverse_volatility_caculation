#!/usr/local/bin/python3

# Author: Zebing Lin (https://github.com/linzebing)

from datetime import datetime, date
import math
import numpy as np
import time
import sys
import requests
import re
from ortools.linear_solver import pywraplp

if len(sys.argv) == 1:
    symbols = ['TMF', 'UPRO']
else:
    symbols = sys.argv[1].split(',')
    for i in range(len(symbols)):
        symbols[i] = symbols[i].strip().upper()

num_trading_days_per_year = 252
window_size = 20
date_format = "%Y-%m-%d"
end_timestamp = int(time.time())
start_timestamp = int(end_timestamp - (1.4 * (window_size + 1) + 4) * 86400)


def get_volatility_and_performance(symbol,cookie,crumb):
    download_url = "https://query1.finance.yahoo.com/v7/finance/download/{}?period1={}&period2={}&interval=1d&events=history&crumb={}".format(symbol, start_timestamp, end_timestamp,crumb)
    lines = requests.get(download_url, cookies={'B': cookie}).text.strip().split('\n')
#   print(cookie)
#   print(crumb)
#   print(lines)
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

    return np.std(volatilities_in_window, ddof = 1) * np.sqrt(num_trading_days_per_year), prices[0] / prices[window_size] - 1.0, prices[0]


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

def create_model(epsilon=0.01):
    alpha[0]/alpha[1]
    data={}
    data['constraint_coeffs']=[
        [current_prices[0],-(epsilon+alpha[0]/alpha[1])*current_prices[1],current_prices[0],-(epsilon+alpha[0]/alpha[1])*current_prices[1]],
        [current_prices[0],-(alpha[0]/alpha[1]-epsilon)*current_prices[1],current_prices[0],-(alpha[0]/alpha[1]-epsilon)*current_prices[1]],
        [current_prices[0],current_prices[1],current_prices[0],current_prices[1]],
        [current_prices[0],current_prices[1],0,0],
        [0,0,current_prices[0],current_prices[1]]
    ]
    data['lb']=[-np.inf, 0,0,0,0]
    data['ub']=[0, np.inf,S,S_Tax,S_IRA]
    data['obj_coeffs']=[current_prices[0],current_prices[1],current_prices[0],current_prices[1]]
    data['xub']=[np.floor(S_Tax/current_prices[0]),np.floor(S_Tax/current_prices[1]),np.floor(S_IRA/current_prices[0]),np.floor(S_IRA/current_prices[1])]
    data['num_vars']=len(data['obj_coeffs'])
    data['num_constraints']=len(data['constraint_coeffs'])                                        
    return data  
    
    
#cookie,crumb=get_cookie()
cookie='9mev4idf68vgk&b=3&s=g9'
crumb='Xpr8Z7BQn4W'
volatilities = []
performances = []
current_prices = []
sum_inverse_volatility = 0.0
for symbol in symbols:
    volatility, performance, current_price = get_volatility_and_performance(symbol,cookie,crumb)
    sum_inverse_volatility += 1 / volatility
    volatilities.append(volatility)
    performances.append(performance)
    current_prices.append(current_price)

alpha=1/(np.array(volatilities) * sum_inverse_volatility)
print ("Portfolio: {}, as of {} (window size is {} days)".format(str(symbols), date.today().strftime('%Y-%m-%d'), window_size))
for i in range(len(symbols)):
    print ('{} allocation ratio: {:.2f}% (anualized volatility: {:.2f}%, performance: {:.2f}%)'.format(symbols[i], float(100 / (volatilities[i] * sum_inverse_volatility)), float(volatilities[i] * 100), float(performances[i] * 100)))

Tax_T=float(input("Current "+symbols[0]+" in taxable: "))
Tax_U=float(input("Current "+symbols[1]+" in taxable: "))
Tax_C=float(input("Current cash: "))
IRA_T=float(input("Current "+symbols[0]+" in IRA: "))
IRA_U=float(input("Current "+symbols[1]+" in IRA: "))
IRA_C=float(input("Current cash in IRA: "))
S_Tax=Tax_T+Tax_U+Tax_C
S_IRA=IRA_T+IRA_U+IRA_C
S=S_Tax+S_IRA

data = create_model(0.02)
solver = pywraplp.Solver.CreateSolver('simple_mip_program', 'CBC')
x={}
for j in range(data['num_vars']):
    x[j] = solver.IntVar(0, data['xub'][i], 'x[%i]' % j)
for i in range(data['num_constraints']):
    constraint = solver.RowConstraint(data['lb'][i], data['ub'][i], '')
    for j in range(data['num_vars']):
        constraint.SetCoefficient(x[j], data['constraint_coeffs'][i][j])
# print('Number of constraints =', solver.NumConstraints())
objective = solver.Objective()
for j in range(data['num_vars']):
    objective.SetCoefficient(x[j], data['obj_coeffs'][j])
objective.SetMaximization()
status = solver.Solve()
if status == pywraplp.Solver.OPTIMAL:
    # print('Objective value =', solver.Objective().Value())
    # for j in range(data['num_vars']):
      # print(x[j].name(), ' = ', x[j].solution_value())
    print('-'*100)
    Tax_C2=S_Tax-x[0].solution_value()*current_prices[0]-x[1].solution_value()*current_prices[1]
    IRA_C2=S_IRA-x[2].solution_value()*current_prices[0]-x[3].solution_value()*current_prices[1]
    S_T2=(x[0].solution_value()+x[2].solution_value())*current_prices[0]
    S_U2=(x[1].solution_value()+x[3].solution_value())*current_prices[1]
    
    print('shares of TMF in Taxable: %d' % x[0].solution_value())
    print('shares of UPRO in Taxable: %d' % x[1].solution_value())
    print('shares of TMF in IRA: %d' % x[2].solution_value())
    print('shares of UPRO in Taxable: %d' % x[3].solution_value())
    print('Cash in Taxable %f' % Tax_C2)
    print('Cash in IRA %f' % IRA_C2) 
    print('Relative weight TMF/UPRO: ({:.2f}%/{:.2f}%), target ({:.2f}%/{:.2f}%)'.format(100*S_T2/(S_T2+S_U2),100*S_U2/(S_T2+S_U2),100*alpha[0],100*alpha[1]))
    # print('Problem solved in %f milliseconds' % solver.wall_time())
    # print('Problem solved in %d iterations' % solver.iterations())
    # print('Problem solved in %d branch-and-bound nodes' % solver.nodes())
    
else:
    print('The problem does not have an optimal solution.')