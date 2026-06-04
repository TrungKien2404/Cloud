# Databricks notebook source
# ====================================================================
# DATABRICKS NOTEBOOK - STEP 1: DATA INGESTION
# ====================================================================
# Path: /Workspace/stock-prediction/01_ingestion
# Description: Tải dữ liệu lịch sử từ Yahoo Finance và lưu thô (raw data)
# ====================================================================

# COMMAND ----------

# MAGIC %pip install yfinance pandas numpy pyyaml

# COMMAND ----------

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional, List, Dict
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
logger = logging.getLogger("01_ingestion")

# COMMAND ----------

# ========== ENVIRONMENT DETECTION ==========
IS_DATABRICKS = "DATABRICKS_RUNTIME_VERSION" in os.environ
print(f"🌍 Running in {'DATABRICKS' if IS_DATABRICKS else 'LOCAL'} environment")

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
            print("ℹ️ Running locally without Databricks Connect. Skipping Spark initialization.")
            return None
        try:
            from pyspark.sql import SparkSession
            return SparkSession.builder.getOrCreate()
        except Exception:
            print("⚠️ Could not initialize Spark session.")
            return None

spark = get_spark_session()

# COMMAND ----------

# ========== CONFIGURATION LOADING ==========
# Thêm các thư mục vào sys.path để import config từ repo nếu chạy trên Databricks Git folders
for path in [os.getcwd(), "..", os.path.abspath(os.path.join(os.getcwd(), ".."))]:
    if path not in sys.path:
        sys.path.append(path)

# Hàm load config linh hoạt
def load_project_config():
    try:
        from configs.config import Config
        config = Config()
        logger.info("Successfully imported Config from configs.config")
        return {
            "tickers": config.data.get('tickers', []),
            "history_years": config.data.get('history_years', 5),
            "raw_data_path": config.data.get('raw_data_path', './data/raw'),
            "delta_path": config.data.get('delta_path', './data/delta')
        }
    except Exception as e:
        logger.warning(f"Could not import config dynamically ({e}). Reading config.yaml directly...")
        
        # Tìm config.yaml
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
            return {
                "tickers": data_cfg.get('tickers', ["AAPL", "TSLA", "MSFT"]),
                "history_years": data_cfg.get('history_years', 5),
                "raw_data_path": data_cfg.get('raw_data_path', './data/raw'),
                "delta_path": data_cfg.get('delta_path', './data/delta')
            }
        else:
            logger.warning("config.yaml not found. Falling back to default settings.")
            return {
                "tickers": ["AAPL", "TSLA", "MSFT", "FPT.VN", "HPG.VN"],
                "history_years": 5,
                "raw_data_path": "./data/raw",
                "delta_path": "./data/delta"
            }

config_data = load_project_config()
TICKERS = config_data["tickers"]
HISTORY_YEARS = config_data["history_years"]
RAW_DATA_PATH = config_data["raw_data_path"]

# Override DBFS path if running on Databricks but paths are local
if IS_DATABRICKS:
    if not RAW_DATA_PATH.startswith("/dbfs"):
        RAW_DATA_PATH = "/dbfs" + RAW_DATA_PATH.lstrip(".")
        
os.makedirs(RAW_DATA_PATH, exist_ok=True)
print(f"🎯 Tickers to ingest: {TICKERS}")
print(f"📅 History length: {HISTORY_YEARS} years")
print(f"💾 Save path: {RAW_DATA_PATH}")

# COMMAND ----------

# ========== STEP 1: FETCH DATA FROM YAHOO FINANCE ==========
def fetch_stock_data(ticker: str, history_years: int) -> Optional[pd.DataFrame]:
    try:
        logger.info(f"Downloading data for {ticker}...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * history_years)
        
        df = yf.download(
            ticker,
            start=start_date,
            end=end_date,
            progress=False
        )
        
        if df.empty:
            logger.warning(f"No data returned for ticker {ticker}")
            return None
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Thêm metadata
        df['Ticker'] = ticker
        df['FetchDate'] = datetime.now()
        df = df.reset_index()
        
        # Đảm bảo cột Date có kiểu datetime
        df['Date'] = pd.to_datetime(df['Date'])
        
        logger.info(f"Successfully fetched {len(df)} records for {ticker}")
        return df
    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {str(e)}")
        return None

# COMMAND ----------

# Fetch all stock data
fetched_data = {}
for ticker in TICKERS:
    df = fetch_stock_data(ticker, HISTORY_YEARS)
    if df is not None:
        fetched_data[ticker] = df

if not fetched_data:
    raise RuntimeError("Failed to fetch data for all stocks. Pipeline aborted.")

# COMMAND ----------

# ========== STEP 2: COMBINE AND SAVE RAW DATA ==========
# Gộp các DataFrame
new_dfs = []
for t, df in fetched_data.items():
    new_dfs.append(df.copy())
combined_df = pd.concat(new_dfs, ignore_index=True)
print(f"Combined data shape: {combined_df.shape}")

# 1. Lưu dưới dạng Delta Table (nếu chạy trên Databricks Spark)
if spark is not None:
    try:
        print("Saving raw data to Delta Lake (bronze.stock_data_raw)...")
        # Chuyển đổi sang Spark DataFrame
        spark_df = spark.createDataFrame(combined_df)
        
        # Tạo database bronze nếu chưa có
        spark.sql("CREATE DATABASE IF NOT EXISTS bronze")
        
        # Ghi đè vào Delta table
        spark_df.write.mode("overwrite").option("mergeSchema", "true").saveAsTable("bronze.stock_data_raw")
        print("✓ Successfully saved to Delta Table: bronze.stock_data_raw")
    except Exception as spark_err:
        logger.error(f"Failed to save to Delta Lake: {spark_err}")
else:
    print("ℹ️ Spark not available. Skipping Delta Lake save.")

# 2. Lưu dưới dạng Parquet cục bộ (để đảm bảo khả năng tương thích ngược hoàn toàn)
combined_parquet_path = os.path.join(RAW_DATA_PATH, "combined_stock_data.parquet")
try:
    print(f"Saving combined data locally/DBFS to: {combined_parquet_path}...")
    
    # Nếu file đã tồn tại, thực hiện cập nhật thông minh
    if os.path.exists(combined_parquet_path):
        try:
            existing_df = pd.read_parquet(combined_parquet_path)
            existing_df['Date'] = pd.to_datetime(existing_df['Date'])
            
            # Lọc bỏ các mã vừa tải để tránh trùng lặp
            new_tickers = list(fetched_data.keys())
            filtered_existing = existing_df[~existing_df['Ticker'].isin(new_tickers)]
            
            # Ghép mới
            final_df = pd.concat([combined_df, filtered_existing], ignore_index=True)
        except Exception as read_err:
            logger.warning(f"Could not read existing combined parquet file, overwriting: {read_err}")
            final_df = combined_df
    else:
        final_df = combined_df
        
    final_df.to_parquet(combined_parquet_path, index=False)
    print(f"✓ Saved {len(final_df)} records to {combined_parquet_path}")
except Exception as e:
    logger.error(f"Error saving raw Parquet file: {str(e)}")

# COMMAND ----------

print("\n" + "="*70)
print("📥 STEP 1: INGESTION PIPELINE COMPLETED")
print("="*70)
