%pip install yfinance pandas scikit-learn plotly
%restart_python or dbutils.library.restartPython()
from ingestion.data_ingestion import StockDataIngestion
from configs.config import Config
import os
import yfinance as yf
# Load config
config = Config()

# Tạo thư mục data nếu chưa có
os.makedirs(config.data['raw_data_path'], exist_ok=True)

# Khởi tạo ingestion
print("=" * 60)
print("📥 STEP 1: DATA INGESTION - Tải dữ liệu từ Yahoo Finance")
print("=" * 60)

ingestion = StockDataIngestion(
    tickers=config.data['tickers'],
    history_years=config.data['history_years'],
    raw_data_path=config.data['raw_data_path']
)

# Chạy pipeline
print(f"\n📊 Tickers: {config.data['tickers']}")
print(f"📅 History: {config.data['history_years']} năm")
print(f"💾 Save path: {config.data['raw_data_path']}\n")

stock_data = ingestion.run_ingestion_pipeline()

print("\n✅ Data ingestion completed!")
print(f"📦 Stocks fetched: {len(stock_data)}")
if stock_data:
    first_ticker = list(stock_data.keys())[0]
    print(f"📊 Columns: {list(stock_data[first_ticker].columns)}\n")
