# Databricks notebook source
# ====================================================================
# DATABRICKS NOTEBOOK - STEP 2: FEATURE ENGINEERING
# ====================================================================
# Path: /Workspace/stock-prediction/02_feature_engineering
# Description: Làm sạch dữ liệu và tính toán technical features, chia tập Train/Val/Test
# ====================================================================

# COMMAND ----------

# MAGIC %pip install pandas numpy scikit-learn pyyaml scipy

# COMMAND ----------

import pandas as pd
import numpy as np
from scipy.stats import zscore
import logging
import os
import sys
import yaml

# Đảm bảo các luồng stdout/stderr trên Windows luôn sử dụng mã hóa UTF-8 để chống lỗi Unicode/charmap
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("02_feature_engineering")

# COMMAND ----------

# ========== ENVIRONMENT DETECTION ==========
IS_DATABRICKS = "DATABRICKS_RUNTIME_VERSION" in os.environ

# ========== SPARK SESSION MANAGEMENT ==========
def get_spark_session():
    try:
        if 'spark' in globals():
            s = globals()['spark']
            s.range(1).collect()
            return s
    except Exception:
        pass

    try:
        from databricks.connect import DatabricksSession
        return DatabricksSession.builder.getOrCreate()
    except (ImportError, Exception):
        if not IS_DATABRICKS:
            return None
        try:
            from pyspark.sql import SparkSession
            return SparkSession.builder.getOrCreate()
        except Exception:
            return None

spark = get_spark_session()

# COMMAND ----------

# ========== CONFIGURATION LOADING ==========
for path in [os.getcwd(), "..", os.path.abspath(os.path.join(os.getcwd(), ".."))]:
    if path not in sys.path:
        sys.path.append(path)

def load_project_config():
    try:
        from configs.config import Config
        config = Config()
        return {
            "raw_data_path": config.data.get('raw_data_path', './data/raw'),
            "processed_data_path": config.data.get('processed_data_path', './data/processed'),
            "ma_windows": config.etl.get('moving_average_windows', [10, 20, 50]),
            "lag_windows": config.etl.get('lag_windows', [1, 5, 10]),
            "rsi_period": config.etl.get('rsi_period', 14),
            "test_size": config.etl.get('test_size', 0.2),
            "val_size": config.etl.get('validation_size', 0.1)
        }
    except Exception as e:
        logger.warning(f"Could not import Config: {e}. Reading config.yaml directly...")
        config_file = None
        for p in ['.', '..', 'configs', '../configs', '../../configs']:
            test_path = os.path.join(p, 'config.yaml')
            if os.path.exists(test_path):
                config_file = test_path
                break
        
        if config_file:
            with open(config_file, 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f)
            data_cfg = cfg.get('data', {})
            etl_cfg = cfg.get('etl', {})
            return {
                "raw_data_path": data_cfg.get('raw_data_path', './data/raw'),
                "processed_data_path": data_cfg.get('processed_data_path', './data/processed'),
                "ma_windows": etl_cfg.get('moving_average_windows', [10, 20, 50]),
                "lag_windows": etl_cfg.get('lag_windows', [1, 5, 10]),
                "rsi_period": etl_cfg.get('rsi_period', 14),
                "test_size": etl_cfg.get('test_size', 0.2),
                "val_size": etl_cfg.get('validation_size', 0.1)
            }
        else:
            return {
                "raw_data_path": "./data/raw",
                "processed_data_path": "./data/processed",
                "ma_windows": [10, 20, 50],
                "lag_windows": [1, 5, 10],
                "rsi_period": 14,
                "test_size": 0.2,
                "val_size": 0.1
            }

config_data = load_project_config()
RAW_DATA_PATH = config_data["raw_data_path"]
PROCESSED_DATA_PATH = config_data["processed_data_path"]
MA_WINDOWS = config_data["ma_windows"]
LAG_WINDOWS = config_data["lag_windows"]
RSI_PERIOD = config_data["rsi_period"]
TEST_SIZE = config_data["test_size"]
VAL_SIZE = config_data["val_size"]

if IS_DATABRICKS:
    if not RAW_DATA_PATH.startswith("/dbfs"): RAW_DATA_PATH = "/dbfs" + RAW_DATA_PATH.lstrip(".")
    if not PROCESSED_DATA_PATH.startswith("/dbfs"): PROCESSED_DATA_PATH = "/dbfs" + PROCESSED_DATA_PATH.lstrip(".")

os.makedirs(PROCESSED_DATA_PATH, exist_ok=True)

# COMMAND ----------

# ========== LOAD RAW DATA ==========
df_raw = None
if spark is not None:
    try:
        print("Loading raw data from Delta Lake (bronze.stock_data_raw)...")
        df_raw = spark.table("bronze.stock_data_raw").toPandas()
        print(f"✓ Loaded {len(df_raw)} records from Delta Table")
    except Exception as e:
        logger.warning(f"Could not load from Delta Table: {e}. Falling back to Parquet file...")

if df_raw is None:
    raw_parquet_file = os.path.join(RAW_DATA_PATH, "combined_stock_data.parquet")
    if os.path.exists(raw_parquet_file):
        print(f"Loading raw data from Parquet: {raw_parquet_file}...")
        df_raw = pd.read_parquet(raw_parquet_file)
        print(f"✓ Loaded {len(df_raw)} records from Parquet")
    else:
        raise FileNotFoundError(f"Raw data file not found at {raw_parquet_file} and Delta Table not available.")

# COMMAND ----------

# ========== CLEAN DATA & REMOVE OUTLIERS ==========
def clean_and_remove_outliers(df: pd.DataFrame) -> pd.DataFrame:
    df_cleaned = df.copy()
    # Sắp xếp theo Date và Ticker
    df_cleaned['Date'] = pd.to_datetime(df_cleaned['Date'])
    df_cleaned = df_cleaned.sort_values(['Ticker', 'Date']).reset_index(drop=True)
    
    # Forward fill then backward fill per ticker
    for ticker in df_cleaned['Ticker'].unique():
        idx = df_cleaned['Ticker'] == ticker
        df_cleaned.loc[idx] = df_cleaned.loc[idx].fillna(method='ffill').fillna(method='bfill')
    
    # Loại bỏ hàng có NaN
    df_cleaned = df_cleaned.dropna(subset=['Close'])
    
    # Loại bỏ outliers dựa trên Close price của từng ticker
    filtered_dfs = []
    for ticker in df_cleaned['Ticker'].unique():
        df_ticker = df_cleaned[df_cleaned['Ticker'] == ticker].copy()
        if len(df_ticker) > 10:
            z_scores = np.abs(zscore(df_ticker['Close']))
            # Ngưỡng Z-score là 3.0
            outliers = z_scores > 3.0
            n_outliers = outliers.sum()
            if n_outliers > 0:
                logger.info(f"Ticker {ticker}: Removed {n_outliers} outliers")
                df_ticker = df_ticker[~outliers]
        filtered_dfs.append(df_ticker)
        
    return pd.concat(filtered_dfs, ignore_index=True)

df_clean = clean_and_remove_outliers(df_raw)
print(f"Cleaned records: {len(df_clean)} (Raw: {len(df_raw)})")

# COMMAND ----------

# ========== FEATURE ENGINEERING ==========
def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()
    
    rs = avg_gain / avg_loss.replace(0, 1)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def compute_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df_fe = df.sort_values(['Ticker', 'Date']).copy()
    
    # 1. Moving Averages
    for window in MA_WINDOWS:
        df_fe[f'MA{window}'] = df_fe.groupby('Ticker')['Close'].transform(
            lambda x: x.rolling(window=window, min_periods=1).mean()
        )
    
    # 2. Lags
    for lag in LAG_WINDOWS:
        df_fe[f'Lag{lag}'] = df_fe.groupby('Ticker')['Close'].transform(
            lambda x: x.shift(lag)
        )
        
    # 3. Daily Returns
    df_fe['Daily_Return'] = df_fe.groupby('Ticker')['Close'].transform(
        lambda x: x.pct_change().fillna(0)
    )
    
    # 4. RSI
    df_fe['RSI'] = df_fe.groupby('Ticker')['Close'].transform(
        lambda x: calculate_rsi(x, RSI_PERIOD)
    )
    
    # 5. Volatility (std dev of Daily_Return on rolling 20 days)
    df_fe['Volatility'] = df_fe.groupby('Ticker')['Daily_Return'].transform(
        lambda x: x.rolling(window=20, min_periods=1).std().fillna(0)
    )
    
    # 6. Target Price (giá đóng cửa ngày hôm sau) và Target Return (tỉ suất sinh lời ngày hôm sau)
    df_fe['Target_Price'] = df_fe.groupby('Ticker')['Close'].transform(
        lambda x: x.shift(-1)
    )
    df_fe['Target_Return'] = (df_fe['Target_Price'] / df_fe['Close']) - 1
    
    # Bỏ các hàng không có Target (hàng cuối của từng ticker)
    df_fe = df_fe.dropna(subset=['Target_Price', 'Target_Return'])
    
    # Điền giá trị trống cho các MA/Lag ở đầu bằng ffill / bfill
    features_to_fill = [f'MA{w}' for w in MA_WINDOWS] + [f'Lag{l}' for l in LAG_WINDOWS] + ['RSI', 'Volatility']
    for col in features_to_fill:
        if col in df_fe.columns:
            df_fe[col] = df_fe.groupby('Ticker')[col].transform(lambda x: x.fillna(method='bfill').fillna(method='ffill'))
            
    # Drop rows that are still NaN if any
    df_fe = df_fe.dropna(subset=features_to_fill)
    
    return df_fe

df_features = compute_technical_indicators(df_clean)
print(f"Feature Engineered data shape: {df_features.shape}")
print(f"Columns in dataset: {list(df_features.columns)}")

# COMMAND ----------

# ========== SPLIT TRAIN/VAL/TEST (Time-series based) ==========
def split_datasets(df: pd.DataFrame, test_size: float = 0.2, val_size: float = 0.1):
    train_dfs = []
    val_dfs = []
    test_dfs = []
    
    for ticker in df['Ticker'].unique():
        df_ticker = df[df['Ticker'] == ticker].sort_values('Date').copy()
        n = len(df_ticker)
        
        test_n = int(n * test_size)
        val_n = int(n * val_size)
        train_n = n - test_n - val_n
        
        train_dfs.append(df_ticker.iloc[:train_n])
        val_dfs.append(df_ticker.iloc[train_n:train_n+val_n])
        test_dfs.append(df_ticker.iloc[train_n+val_n:])
        
    train_df = pd.concat(train_dfs, ignore_index=True)
    val_df = pd.concat(val_dfs, ignore_index=True)
    test_df = pd.concat(test_dfs, ignore_index=True)
    
    return train_df, val_df, test_df

train_df, val_df, test_df = split_datasets(df_features, TEST_SIZE, VAL_SIZE)
print(f"Train Set size: {len(train_df)} samples")
print(f"Val Set size:   {len(val_df)} samples")
print(f"Test Set size:  {len(test_df)} samples")

# COMMAND ----------

# ========== SAVE PROCESSED DATA AND SPLITS ==========
# 1. Lưu các bảng Delta Tables (cho Databricks)
if spark is not None:
    try:
        print("Saving tables to Delta Lake (bronze catalog)...")
        # Ghi đè processed_df
        spark.createDataFrame(df_features).write.mode("overwrite").option("mergeSchema", "true").saveAsTable("bronze.stock_data_processed")
        
        # Ghi đè splits
        spark.createDataFrame(train_df).write.mode("overwrite").option("mergeSchema", "true").saveAsTable("bronze.stock_data_train")
        spark.createDataFrame(val_df).write.mode("overwrite").option("mergeSchema", "true").saveAsTable("bronze.stock_data_val")
        spark.createDataFrame(test_df).write.mode("overwrite").option("mergeSchema", "true").saveAsTable("bronze.stock_data_test")
        print("✓ All tables saved to Delta Lake successfully.")
    except Exception as e:
        logger.error(f"Error saving to Delta Lake: {e}")
else:
    print("ℹ️ Spark not available. Skipping Delta Lake saves.")

# 2. Lưu Parquet cục bộ (để FastAPI / ModelTrainer cục bộ sử dụng được ngay)
processed_parquet_path = os.path.join(PROCESSED_DATA_PATH, "processed_stock_data.parquet")
try:
    print(f"Saving processed data to: {processed_parquet_path}...")
    df_features.to_parquet(processed_parquet_path, index=False)
    
    # Đồng thời lưu splits cục bộ dạng Parquet (hoặc CSV nếu muốn) để phòng hờ
    train_df.to_parquet(os.path.join(PROCESSED_DATA_PATH, "train_stock_data.parquet"), index=False)
    val_df.to_parquet(os.path.join(PROCESSED_DATA_PATH, "val_stock_data.parquet"), index=False)
    test_df.to_parquet(os.path.join(PROCESSED_DATA_PATH, "test_stock_data.parquet"), index=False)
    print("✓ Successfully saved Parquet data files.")
except Exception as e:
    logger.error(f"Error saving processed Parquet files: {e}")

# COMMAND ----------

print("\n" + "="*70)
print("🔄 STEP 2: FEATURE ENGINEERING PIPELINE COMPLETED")
print("="*70)
