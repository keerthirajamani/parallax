import yfinance as yf
from datetime import datetime, timedelta

start_date = "2000-01-01"
end_date = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')

print("end_date", end_date)
# Download data
data = yf.download("GC=F", start=start_date, end=end_date)
print(data.tail(100))
data.to_csv("XAU_2000_01_01_2026_03_27.csv")