# Databricks notebook source
import sys
sys.path.append("/Workspace/Users/y7prolpvo2018@gmail.com/Cloud")

# COMMAND ----------

# MAGIC %pip install yfinance pandas scikit-learn plotly

# COMMAND ----------

# MAGIC %pip install yfinance pandas scikit-learn plotly
# MAGIC %restart_python or dbutils.library.restartPython()
# MAGIC from ingestion.data_ingestion import StockDataIngestion
# MAGIC from configs.config import Config
# MAGIC import os
# MAGIC import yfinance as yf
# MAGIC # Load config
# MAGIC config = Config()
# MAGIC
# MAGIC # Tạo thư mục data nếu chưa có
# MAGIC os.makedirs(config.data['raw_data_path'], exist_ok=True)
# MAGIC
# MAGIC # Khởi tạo ingestion
# MAGIC print("=" * 60)
# MAGIC print("📥 STEP 1: DATA INGESTION - Tải dữ liệu từ Yahoo Finance")
# MAGIC print("=" * 60)
# MAGIC
# MAGIC ingestion = StockDataIngestion(
# MAGIC     tickers=config.data['tickers'],
# MAGIC     history_years=config.data['history_years'],
# MAGIC     raw_data_path=config.data['raw_data_path']
# MAGIC )
# MAGIC
# MAGIC # Chạy pipeline
# MAGIC print(f"\n📊 Tickers: {config.data['tickers']}")
# MAGIC print(f"📅 History: {config.data['history_years']} năm")
# MAGIC print(f"💾 Save path: {config.data['raw_data_path']}\n")
# MAGIC
# MAGIC stock_data = ingestion.run_ingestion_pipeline()
# MAGIC
# MAGIC print("\n✅ Data ingestion completed!")
# MAGIC print(f"📦 Stocks fetched: {len(stock_data)}")
# MAGIC if stock_data:
# MAGIC     first_ticker = list(stock_data.keys())[0]
# MAGIC     print(f"📊 Columns: {list(stock_data[first_ticker].columns)}\n")
# MAGIC

# COMMAND ----------



# COMMAND ----------



# COMMAND ----------



# COMMAND ----------

