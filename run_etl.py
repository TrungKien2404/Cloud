<<<<<<< HEAD

=======
>>>>>>> 383b956792a3d7dd9cabc8ad4291ac812e1bd434
from etl.etl_pipeline import StockETLPipeline
from configs.config import Config
import pandas as pd
import os
<<<<<<< HEAD
import yfinance as yf
=======

>>>>>>> 383b956792a3d7dd9cabc8ad4291ac812e1bd434
config = Config()

# Tạo thư mục nếu chưa có
os.makedirs(config.data.get('processed_data_path', './data/processed'), exist_ok=True)

print("=" * 60)
print("🔄 STEP 2: ETL PROCESSING - Xử lý dữ liệu & tạo features")
print("=" * 60)

# Load raw data
raw_data_path = os.path.join(config.data['raw_data_path'], 'combined_stock_data.parquet')
print(f"\n📖 Load raw data from: {raw_data_path}\n")
df = pd.read_parquet(raw_data_path)

print(f"📊 Input records: {len(df)}")
print(f"📺 Input columns: {list(df.columns)}\n")

# Khởi tạo ETL pipeline
etl_pipeline = StockETLPipeline(
    ma_windows=config.etl['moving_average_windows'],
    lag_windows=config.etl['lag_windows'],
    rsi_period=config.etl['rsi_period']
)

print("🔧 Processing pipeline:")
print("   ✓ Handling missing values")
print("   ✓ Removing outliers")
print("   ✓ Computing moving averages (MA10, MA20, MA50)")
print("   ✓ Computing lag features (Lag1, Lag5, Lag10)")
print("   ✓ Computing RSI indicator")
print("   ✓ Computing daily returns & volatility")
print("   ✓ Creating target variable")
print("   ✓ Standardizing features")
print("   ✓ Splitting train/val/test (70/10/20)\n")

# Chạy ETL
result = etl_pipeline.run_etl_pipeline(df)

processed_df = result['processed_df']
train_data, val_data, test_data = result['train_data'], result['val_data'], result['test_data']

print("✅ ETL processing completed!\n")

print("📊 Output Statistics:")
print(f"   Processed records: {len(processed_df)}")
print(f"   Features engineered: {len(processed_df.columns) - 3}")  # -3 for Date, Ticker, Target
print(f"   Train set: {len(train_data[0])} samples")
print(f"   Val set: {len(val_data[0])} samples")
print(f"   Test set: {len(test_data[0])} samples")
print(f"   Total: {len(train_data[0]) + len(val_data[0]) + len(test_data[0])}")
print(f"\n📋 Features: {list(processed_df.columns)}\n")

# Save processed data
processed_path = os.path.join(config.data.get('processed_data_path', './data/processed'), 'processed_stock_data.parquet')
processed_df.to_parquet(processed_path, index=False)
print(f"✅ Processed data saved: {processed_path}\n")
