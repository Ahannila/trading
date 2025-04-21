import backtrader as bt
import pandas as pd

# Custom VWAP Indicator
class VWAPIndicator(bt.Indicator):
    lines = ('vwap',)
    params = (("period", 14),)
    plotinfo = dict(subplot=False)  # Overlay VWAP on price chart

    def __init__(self):
        price_volume = self.data.close * self.data.volume
        cum_price_volume = bt.indicators.SumN(price_volume, period=self.params.period)
        cum_volume = bt.indicators.SumN(self.data.volume, period=self.params.period)
        self.lines.vwap = cum_price_volume / cum_volume  # VWAP Calculation

# Turnaround Tuesday Strategy with VWAP-Based Selling
class TurnaroundTuesdayVWAPStrategy(bt.Strategy):
    params = {
        "sell_threshold": 0.0001,  # Sell only if price is 2% above VWAP
        # 0.002 = 12099
        # 0.001 = 12565

    }

    def __init__(self):
        self.vwap = VWAPIndicator(self.data)

    def log(self, txt):
        dt = self.datas[0].datetime.date(0)  # Get date for logging
        print(f'{dt}, {txt}')

    def next(self):
        current_day = self.datas[0].datetime.date(0).weekday()  # 0=Monday, 1=Tuesday, etc.
        price = self.data.close[0]
        previous_close = self.data.close[-1]
        previous_open = self.data.open[-1]
        vwap_value = self.vwap.vwap[0]
        distance_from_vwap = (price - vwap_value) / vwap_value  # % distance from VWAP

        # ✅ Buy if today is Tuesday AND Monday was a red day
        if current_day == 0 and previous_close < previous_open and not self.position:
            num_shares = 100000 / price  # Fixed $1000 per trade
            self.buy(size=num_shares)
            self.log(f'BUY: {num_shares:.2f} shares at {price:.2f}')

        # ✅ Sell if price is 2% above VWAP before the market closes on Tuesday
        if current_day == 1 and self.position and distance_from_vwap > self.params.sell_threshold:
            self.sell(size=self.position.size)
            self.log(f'SELL: Closing at {price:.2f}, VWAP {vwap_value:.2f}, Distance {distance_from_vwap:.2%}')

    def start(self):
        print(f"Starting Cash: {self.broker.get_cash()}")

    def stop(self):
        print(f"Ending Cash: {self.broker.get_cash()}")

# Load Valmet Data
datafile = "data/valmet.csv"
df = pd.read_csv(datafile)

# Convert Date
df['datetime'] = pd.to_datetime(df['Date'], format="%m/%d/%Y")
df = df.sort_values("datetime")
df.set_index("datetime", inplace=True)

# Rename columns for Backtrader
df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Price": "close", "Vol.": "volume"}, inplace=True)

# Convert Volume (Handling 'K' and 'M' notation)
df['volume'] = df['volume'].astype(str).str.replace('K', 'e3').str.replace('M', 'e6').astype(float)

# Handle Missing Data
df.fillna(method='ffill', inplace=True)
df.fillna(method='bfill', inplace=True)

# Create Backtrader Data Feed
data = bt.feeds.PandasData(dataname=df)

# Initialize Backtrader
cerebro = bt.Cerebro()
cerebro.addstrategy(TurnaroundTuesdayVWAPStrategy)
cerebro.adddata(data)

# Set Initial Capital
cerebro.broker.set_cash(100000)

# Run Backtest
cerebro.run()

# Plot Results
cerebro.plot(style='candlestick')
