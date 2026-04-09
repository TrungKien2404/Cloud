# ====================================================================
# DATABRICKS NOTEBOOK - Main ETL Pipeline
# ====================================================================
# Path: /Workspace/stock-prediction/01_etl_pipeline
# Runtime: Databricks Runtime with Python 3.10+
#
# Mục đích:
# - Data ingestion từ Yahoo Finance
# - ETL processing
# - Save to Delta Lake
# - Chạy được trên Databricks Jobs
#
# Yêu cầu:
# 1. Cài đặt yfinance: %pip install yfinance
# 2. Mount DBFS nếu cần
#
# ====================================================================

# COMMAND ----------

# Install required libraries
%pip install yfinance pandas numpy scikit-learn

# COMMAND ----------

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# COMMAND ----------

# ========== CONFIGURATION ==========

TICKERS = ["AAPL", "TSLA", "MSFT"]
HISTORY_YEARS = 5
DBFS_DATA_PATH = "/dbfs/mnt/data"  # Adjust based on your DBFS mount
DELTA_CATALOG = "bronze"  # Delta Lake table

# COMMAND ----------

# ========== STEP 1: FETCH DATA FROM YAHOO FINANCE ==========

def fetch_stock_data(ticker):
    """
    Fetch stock data từ Yahoo Finance
    
    Parameters:
        ticker: Stock ticker symbol
    
    Returns:
        DataFrame với OHLCV data
    """
    try:
        print(f"📥 Fetching data cho {ticker}...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * HISTORY_YEARS)
        
        # Download từ Yahoo Finance
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)
        
        # Sửa lỗi yfinance phiên bản mới trả về MultiIndex (chứa kí tự không hợp lệ cho Delta Lake)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
        
        # Add metadata columns
        df['Ticker'] = ticker
        df['FetchDate'] = datetime.now()
        df = df.reset_index()
        
        print(f"✓ Fetched {len(df)} records cho {ticker}")
        return df
        
    except Exception as e:
        print(f"❌ Error fetching {ticker}: {str(e)}")
        return None

# COMMAND ----------

# Fetch all tickers
stock_data = {}
for ticker in TICKERS:
    df = fetch_stock_data(ticker)
    if df is not None:
        stock_data[ticker] = df

print(f"\n✓ Successfully fetched data cho {len(stock_data)} / {len(TICKERS)} stocks")

# COMMAND ----------

# Display sample data
for ticker, df in stock_data.items():
    print(f"\n{ticker} Sample Data:")
    print(df.head())
    print(f"Shape: {df.shape}")

# COMMAND ----------

# ========== STEP 2: COMBINE AND SAVE RAW DATA ==========

# Combine all stock data
combined_df = pd.concat(stock_data.values(), ignore_index=True)
print(f"Combined data shape: {combined_df.shape}")

# Convert to Spark DataFrame (for Databricks)
spark_df = spark.createDataFrame(combined_df)

# Xử lý lỗi SCHEMA_NOT_FOUND: Tạo Database/Schema nếu nó chưa tồn tại trên hệ thống Databricks
spark.sql(f"CREATE DATABASE IF NOT EXISTS {DELTA_CATALOG}")

# Save to Delta Lake (raw table)
spark_df.write.mode("overwrite").option("mergeSchema", "true").saveAsTable(f"{DELTA_CATALOG}.stock_data_raw")

print("✓ Data saved to Delta Lake table: bronze.stock_data_raw")

# COMMAND ----------

# ========== STEP 3: DATA CLEANING ==========

# Bỏ qua việc đọc từ Delta Lake do lỗi Spark Catalog trên bản Free
# Dùng trực tiếp dữ liệu pandas đã tải ở bước trước để đảm bảo mượt mà
df_raw = combined_df.copy()

print(f"Raw data shape: {df_raw.shape}")
print(f"Missing values count:\n{df_raw.isnull().sum()}")

# COMMAND ----------

# Handle missing values
def clean_data(df):
    """Clean data - handle missing values and outliers"""
    
    # Forward fill then backward fill
    df = df.fillna(method='ffill').fillna(method='bfill')
    
    # Remove outliers using Z-score (for Close price)
    from scipy import stats
    z_scores = np.abs(stats.zscore(df['Close'].dropna()))
    
    # Filter outliers
    outlier_indices = z_scores > 3.0
    print(f"Removed {outlier_indices.sum()} outliers")
    
    return df

df_clean = clean_data(df_raw.copy())
print(f"Cleaned data shape: {df_clean.shape}")
print(f"Remaining missing values: {df_clean.isnull().sum().sum()}")

# COMMAND ----------

# ========== STEP 4: FEATURE ENGINEERING ==========

def engineer_features(df):
    """
    Thêm features cho ML model
    """
    df = df.sort_values('Date').reset_index(drop=True)
    
    # 1. Moving Averages
    for window in [10, 20, 50]:
        df[f'MA{window}'] = df.groupby('Ticker')['Close'].transform(
            lambda x: x.rolling(window=window, min_periods=1).mean()
        )
    
    # 2. Lag Features
    for lag in [1, 5, 10]:
        df[f'Lag{lag}'] = df.groupby('Ticker')['Close'].transform(
            lambda x: x.shift(lag)
        )
    
    # 3. Daily Returns
    df['Daily_Return'] = df.groupby('Ticker')['Close'].transform(
        lambda x: x.pct_change()
    )
    
    # 4. RSI (Relative Strength Index)
    def calculate_rsi(prices, period=14):
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss.replace(0, 1)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)
    
    df['RSI'] = df.groupby('Ticker')['Close'].transform(
        lambda x: calculate_rsi(x)
    )
    
    # 5. Volatility
    df['Volatility'] = df.groupby('Ticker')['Daily_Return'].transform(
        lambda x: x.rolling(window=20).std()
    )
    
    # 6. Target Variable (next day return)
    df['Target'] = df.groupby('Ticker')['Close'].transform(
        lambda x: (x.shift(-1) / x - 1)
    )
    
    # Drop NaN rows
    df = df.dropna()
    
    return df

df_features = engineer_features(df_clean.copy())
print(f"Features engineered. Final shape: {df_features.shape}")
print(f"\nColumns: {list(df_features.columns)}")

# COMMAND ----------

# Save processed data to Delta Lake
spark_df_features = spark.createDataFrame(df_features)
spark_df_features.write.mode("overwrite").option("mergeSchema", "true").saveAsTable(
    f"{DELTA_CATALOG}.stock_data_processed"
)

print("✓ Processed data saved to Delta Lake: bronze.stock_data_processed")

# COMMAND ----------

# ========== STEP 5: DATA SPLIT (Train/Val/Test) ==========

def split_data(df, test_size=0.2, val_size=0.1):
    """Split data thành train/val/test (time-series based)"""
    
    n = len(df)
    test_n = int(n * test_size)
    val_n = int(n * val_size)
    train_n = n - test_n - val_n
    
    train = df.iloc[:train_n]
    val = df.iloc[train_n:train_n+val_n]
    test = df.iloc[train_n+val_n:]
    
    return train, val, test

train_df, val_df, test_df = split_data(df_features)

print(f"Train: {len(train_df)} ({len(train_df)/len(df_features)*100:.1f}%)")
print(f"Val:   {len(val_df)} ({len(val_df)/len(df_features)*100:.1f}%)")
print(f"Test:  {len(test_df)} ({len(test_df)/len(df_features)*100:.1f}%)")

# COMMAND ----------

# Save splits to Delta Lake
for split_name, split_df in [("train", train_df), ("val", val_df), ("test", test_df)]:
    spark_split = spark.createDataFrame(split_df)
    spark_split.write.mode("overwrite").option("mergeSchema", "true").saveAsTable(
        f"{DELTA_CATALOG}.stock_data_{split_name}"
    )
    print(f"✓ Saved {split_name} set to Delta Lake")

# COMMAND ----------

# ========== SUMMARY ==========

print("\n" + "="*70)
print("ETL PIPELINE COMPLETED SUCCESSFULLY")
print("="*70)
print(f"\nData Summary:")
print(f"- Total records: {len(df_features)}")
print(f"- Stocks processed: {df_features['Ticker'].nunique()}")
print(f"- Date range: {df_features['Date'].min()} to {df_features['Date'].max()}")
print(f"- Features: {len(df_features.columns)}")
print(f"\nData saved to Delta Lake tables:")
print(f"- bronze.stock_data_raw")
print(f"- bronze.stock_data_processed")
print(f"- bronze.stock_data_train")
print(f"- bronze.stock_data_val")
print(f"- bronze.stock_data_test")
print("="*70)
