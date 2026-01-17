import random
import csv
from datetime import datetime, timedelta

# Stock symbols with realistic starting prices
stocks = {
    'AAPL': 250.0,
    'AMZN': 200.0,
    'GOOGL': 290.0,
    'MSFT': 420.0,
    'TSLA': 380.0,
    'NVDA': 480.0,
    'META': 350.0,
    'NFLX': 450.0
}

def generate_candle(prev_close, volatility=0.02):
    """Generate realistic OHLC data"""
    # Opening price near previous close with some gap
    open_price = prev_close * (1 + random.uniform(-volatility/2, volatility/2))
    
    # Daily movement
    trend = random.uniform(-volatility, volatility)
    close_price = open_price * (1 + trend)
    
    # High and low based on intraday volatility
    intraday_range = abs(close_price - open_price) * random.uniform(1.2, 2.0)
    high_price = max(open_price, close_price) + intraday_range * random.uniform(0.3, 0.7)
    low_price = min(open_price, close_price) - intraday_range * random.uniform(0.3, 0.7)
    
    return round(low_price, 2), round(high_price, 2), round(open_price, 2), round(close_price, 2)

def calculate_trend_line(closes, window=3):
    """Simple moving average for trend line"""
    if len(closes) < window:
        return closes[-1]
    return sum(closes[-window:]) / window

def generate_trading_days(start_date, num_days):
    """Generate trading days (skip weekends)"""
    days = []
    current = start_date
    while len(days) < num_days:
        if current.weekday() < 5:  # Monday = 0, Friday = 4
            days.append(current)
        current += timedelta(days=1)
    return days

# Generate data
output = []
start_date = datetime(2025, 9, 1)  # Start from September
num_days = 80  # ~80 trading days for 8 stocks = 640 rows

trading_days = generate_trading_days(start_date, num_days)

for symbol, start_price in stocks.items():
    price = start_price
    closes = []
    
    for date in trading_days:
        low, high, open_price, close_price = generate_candle(price, volatility=0.025)
        closes.append(close_price)
        trend_line = calculate_trend_line(closes)
        
        output.append({
            'SYMBOL': symbol,
            'CANDLE_TIME': date.strftime('%Y-%m-%d'),
            'CANDLE_LOW': low,
            'CANDLE_HIGH': high,
            'CANDLE_OPEN': open_price,
            'CANDLE_CLOSE': close_price,
            'TREND_LINE': round(trend_line, 9)
        })
        
        price = close_price

# Write to CSV
with open('stock_data.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['SYMBOL', 'CANDLE_TIME', 'CANDLE_LOW', 
                                            'CANDLE_HIGH', 'CANDLE_OPEN', 'CANDLE_CLOSE', 
                                            'TREND_LINE'])
    writer.writeheader()
    writer.writerows(output)

print(f"Generated {len(output)} rows of stock data")
print(f"Symbols: {list(stocks.keys())}")
print(f"Date range: {trading_days[0].strftime('%Y-%m-%d')} to {trading_days[-1].strftime('%Y-%m-%d')}")
print("\nFirst 10 rows:")
for row in output[:10]:
    print(f"{row['SYMBOL']},{row['CANDLE_TIME']},{row['CANDLE_LOW']},{row['CANDLE_HIGH']},{row['CANDLE_OPEN']},{row['CANDLE_CLOSE']},{row['TREND_LINE']}")