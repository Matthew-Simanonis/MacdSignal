import numpy as np
import pandas as pd 
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
import requests, re, csv, math, datetime, smtplib
import yfinance as yf
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

TIMEFRAME = 100     # Set timeframe for graph
now = datetime.datetime.now()
date = now.strftime("%Y-%m-%d") # Get Date
PRINTBUYS = True
DIFFERENCE = 4
STOCKTICKERS = ['zm', 'atvi','znga', 'dis', 'appn', 'cwbhf', 'fb', 'bb', 'alk']
USERS = []


class Stock:
    def __init__(self, stockticker, user):
        self.stockticker = stockticker
        self.user = user
        self.ticker = yf.Ticker(stockticker)
        self.data = addmacd(self.ticker.history(period='max'), stockticker)
        self.price_history, self.buys, self.sells = isbuy(self.data, self.stockticker, self.user)
    def plotstock(self):
        self.plot = plotstock(self.price_history, self.stockticker)

class User():
    def __init__(self, name, email, tickers):
        self.name = name
        self.email = email
        self.tickers = tickers
        USERS.append(self)
    def add_ticker(self, ticker):
        self.tickers.append(ticker)
    def printall(self):
        for ticker in self.tickers:
            Stock(ticker, self)
    def __str__(self):
        return self.name
        

def main():
    Matt = User('Matt', 'email@email.com', ['eth-usd', 'btc-usd', 'link-usd',  'uber', 'amd', 'aapl', 'tsla', 'htz', 'snap', 'pypl'])
    Chris = User('Chris', 'email@email.com', ['zm', 'atvi','znga', 'dis', 'appn', 'cwbhf', 'fb', 'bb', 'alk'])
    arg = input('Input Stock Ticker: ').lower()
    fig, axes = plt.subplots(nrows=3, ncols=1,figsize=(20,10)) # Graphing
    plt.close()
    while arg != 'exit':
        if arg == 'check all' or arg == 'c':
            print('Checking All Tickers...')
            for user in USERS:
                print(user)
                for ticker in user.tickers:
                    Stock(ticker, user)
                    plt.close()
        elif arg == 'o':
            print('\nEnter new stock ticker\nPlot\nCheck All\n')
        elif arg == 'u':
            name = input('Username: ').title() 
            for user in USERS:
                if user.name == name:
                    user.printall()
        else:
            df = Stock(arg, Matt)
            print(df.price_history[-6:])
            df.plotstock()
            plt.show()
        arg = input('Input Stock Ticker: ').lower()

def isbuy(df, stock, user):
    counter, todays_price, profit = 0, 0, 0
    last_buy, last_sell = '0', '0'
    macd, stoch, ownshare = False, False, False
    buys, sells = [], []
    for i in df.itertuples():
        if i.STOCHCross == 1 and i.K2 < 80:
            stoch = True
            counter = 0
        elif counter <= DIFFERENCE and i.MACDCross == 1:
            macd = True
            df.at[i.Index, 'Buys'] = i.Close
            buys.append(i.Index.strftime('%Y-%m-%d') + ' at $' + str(i.Close))
            ownshare = True
            if PRINTBUYS == True: print('Buy ', stock, i.Close, i.Index)
        elif i.MACDCross == 0:
            macd = False
            df.at[i.Index, 'Sells'] = i.Close
            sells.append(i.Index.strftime('%Y-%m-%d') + ' at $' + str(i.Close))
            if PRINTBUYS == True: print('Sell ', stock, i.Close, i.Index)
        elif i.STOCHCross == 0:
            stoch = False
        elif counter > DIFFERENCE:
            counter = 0
        elif stoch == True:
            counter += 1
        todays_price = i.Close

    if PRINTBUYS == True:
        print(f'\nImplied Hold Profit: {df.Close[-1] - df.Close[0]}')
        #print(f'\nProfit: {profit}')
        #if ownshare == True: print(f'Bought share at: $', df[-1:]['Close'].values)
        print(f'Todays Close: ${todays_price} \n')
    if len(buys) > 0:
        last_buy = str(buys[-1])[0:10]
    if len(sells) > 0:
        last_sell = str(sells[-1])[0:10]

    if last_buy == date:
        plotstock(df, stock)
        send_mail_img(user, df, stock, 'buy', buys, sells)
    elif last_sell == date:
        plotstock(df, stock)
        send_mail_img(user, df, stock, 'sell', buys, sells)

    return df, buys, sells

def addmacd(df, stockticker):
    df['High14'] = df['High'].rolling(14).max()         # Create 14 Day high
    df['Low14'] = df['Low'].rolling(14).min()
    df['FiftyMA'] = df['Close'].rolling(window=50).mean()
    df['TwohundredMA'] = df['Close'].rolling(window=200).mean()
    df['FiftyEMA'] = df['Close'].ewm(span=50, adjust=False).mean()

    df['K'] = 100*((df['Close'] - df['Low14']) / (df['High14'] - df['Low14']) )
    df['D'] = df['K'].rolling(window=3).mean()
    df['K2'] = df['D'].rolling(window=3).mean()

    try:
        df = df.drop(['High', 'Low', 'Dividends', 'Stock Splits', 'Low14', 'High14'], axis=1)
    except:
        df = df.drop(['High', 'Low', 'Low14', 'High14'], axis=1)
    exp1 = df["Close"].ewm(span=12, adjust=False).mean()
    exp2 = df["Close"].ewm(span=26, adjust=False).mean()
    macd = exp1-exp2
    signalline = macd.ewm(span=10, adjust=False).mean()
    df['MACD'] = macd
    df['Signal'] = signalline
    df['Histogram'] = macd - signalline

    df = df[-TIMEFRAME:]
    findcrossmacd(df)
    findcrossstocastic(df)
    return df
    
def findcrossmacd(df):
    bullish = False
    for i in df.itertuples():
        if i.MACD >= i.Signal and bullish==False:
            df.at[i.Index, 'MACDCross'] = 1
            bullish=True
        elif i.MACD <= i.Signal and bullish==True:
            df.at[i.Index, 'MACDCross'] = 0
            bullish=False

def findcrossstocastic(df):
    bullish = False
    for i in df.itertuples():
        if i.K2 >= i.D and bullish==False and i.K2 > 50:
            df.at[i.Index, 'STOCHCross'] = 1
            bullish=True
        elif i.K2 <= i.D and bullish==True:
            df.at[i.Index, 'STOCHCross'] = 0
            bullish=False

def plotstock(df, stock):
    plt.style.use('bmh')

    fig, axes = plt.subplots(nrows=3, ncols=1,figsize=(18,14)) # Graphing
    plt.margins(.1)
    df[['Close', 'FiftyEMA', 'TwohundredMA']].plot(ax=axes[0]); axes[0].set_title(f'{stock.upper()} Price')
    df[['K2','D']].plot(ax=axes[2]); axes[1].set_title('Oscillator')
    df[['MACD','Signal']].plot(ax=axes[1]); axes[1].set_title('MACD')
    
    try:
        df['Buys'].plot(ax=axes[0], fillstyle='none', marker='o', color='green', markersize=11)
    except:
        pass
    try:
        df['Sells'].plot(ax=axes[0], fillstyle='none', marker='o', color='red', markersize=11)
    except:
        pass
    return fig


def send_mail_img(user, dataframe, stock, action, buys, sells):
    plt.savefig('plot.jpg')
    attachment = 'plot.jpg'
    msg = MIMEMultipart()
    msg["To"] = user.email
    msg["From"] = 'email@email.com'
    msg["Subject"] = 'We got a '+ action.title() + ' signal for ' + stock.upper() + '!'
    body = f'The stock {stock.upper()} showed a minor {action} signal today at close at ${dataframe.Close[-1]}. Take a look! <br><br> Buys: {buys} <br><br> Sells: {sells} <br><br><br> https://finance.yahoo.com/quote/{stock}?p={stock} <br>'

    msgText = MIMEText('<b>%s</b><br><img src="cid:%s"><br>' % (body, attachment), 'html')  
    msg.attach(msgText)   # Added, and edited the previous line

    fp = open(attachment, 'rb')                                                    
    img = MIMEImage(fp.read())
    fp.close()
    img.add_header('Content-ID', '<{}>'.format(attachment))
    msg.attach(img)
    
    # Send the message via local SMTP server.
    server = smtplib.SMTP('smtp.gmail.com', 587)    # Server Stuff
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login('email@email.com', 'ouepwzqkbydclmre')
    server.sendmail("email@email.com", user.email, msg.as_string())
    server.quit()

    print('\n\nEmail has been sent \n')
    print(action, stock, user, '\n\n\n')


main()