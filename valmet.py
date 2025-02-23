import backtrader as bt
import pandas as pd
import datetime

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

class YearlyVWAP(bt.Indicator):
    lines = ('vwap',)
    params = (("period", 252),)

    plotinfo = dict(subplot=False)  # Overlay VWAP on price chart

    def __init__(self):
        price_volume = self.data.close * self.data.volume
        cum_price_volume = bt.indicators.SumN(price_volume, period=self.params.period)
        cum_volume = bt.indicators.SumN(self.data.volume, period=self.params.period)
        self.lines.vwap = cum_price_volume / cum_volume

# This strategy looks at the 50-day SMA and 200-day SMA, P/E ratio, and VWAP To determine buy signals for longer term



# Strategy Using VWAP
class VWAPStrategy(bt.Strategy):
    params = (("buy_threshold", 0.05),  # Buy when price is 0.86% below VWAP
              ("sell_threshold", 0.04))  # Sell when price is 4% above VWAP

    def __init__(self):
        # Add VWAP Indicator
        self.vwap = VWAPIndicator(self.data)
        self.vwap.plotinfo.plot = True  # Ensure it's plotted
        self.vwap.plotinfo.subplot = False  # Overlay on main chart
        self.vwap.plotinfo.plotname = "VWAP"  # Label it on chart

    def log(self, txt):
        """Logging function"""
        dt = self.datas[0].datetime.date(0)
        print(f'{dt}, {txt}')

    def next(self):
        price = self.data.close[0]
        vwap_value = self.vwap.vwap[0]
        distance = (price - vwap_value) / vwap_value  # Percentage distance

        # ✅ Buy when price is significantly below VWAP
        if price < vwap_value and abs(distance) > self.params.buy_threshold:
            if not self.position:
                investment_size = 5000  # Fixed $2000 per trade
                num_shares = investment_size / price  # Calculate number of shares
                self.buy(size=num_shares)
                self.log(f'BUY ORDER: {num_shares:.2f} shares at {price:.2f}, Total: ${investment_size:.2f}')

        # ✅ Sell when price is significantly above VWAP
        elif price > vwap_value and distance > self.params.sell_threshold:
            if self.position:
                self.sell(size=self.position.size)  # Sell all held shares
                self.log(f'SELL ORDER: Closing position at {price:.2f}')

    def start(self):
        """Print starting cash"""
        print(f"Starting Cash: {self.broker.get_cash()}")

    def stop(self):
        """Print ending cash"""
        print(f"Ending Cash: {self.broker.get_cash()}")

# Load CSV
datafile = "data/valmet.csv"
df = pd.read_csv(datafile)

# Convert Date column to datetime
df['Date'] = pd.to_datetime(df['Date'], format="%m/%d/%Y")
df = df.sort_values("Date")

# Rename columns to match Backtrader format
df.rename(columns={"Date": "datetime", "Open": "open", "High": "high", "Low": "low", "Price": "close", "Vol.": "volume"}, inplace=True)
df.set_index("datetime", inplace=True)

# Convert Volume (Handle 'K' and 'M' notation)
df['volume'] = df['volume'].str.replace('K', 'e3').str.replace('M', 'e6')
df['volume'] = pd.to_numeric(df['volume'], errors='coerce')

# Convert Change % (Remove '%' and convert to float)
df['Change %'] = df['Change %'].str.replace('%', '', regex=True).astype(float)

# Handle missing values
df.fillna(method='ffill', inplace=True)
df.fillna(method='bfill', inplace=True)

# Create Backtrader data feed
data = bt.feeds.PandasData(dataname=df)

# Initialize Backtrader
cerebro = bt.Cerebro()
cerebro.addstrategy(VWAPStrategy)
cerebro.adddata(data)

# Set Initial Capital
initial_cash = 10000
cerebro.broker.set_cash(initial_cash)

# Run Backtest
cerebro.run()

# Plot Results (VWAP will now be overlaid!)
cerebro.plot()
