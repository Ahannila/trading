import yfinance as yf

obj = yf.Ticker("GOOG")

print(obj.info)