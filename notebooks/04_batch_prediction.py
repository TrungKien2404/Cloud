# Databricks notebook source
# ====================================================================
# DATABRICKS NOTEBOOK - STEP 4: BATCH PREDICTION
# ====================================================================
# Path: /Workspace/stock-prediction/04_batch_prediction
# Description: Tải mô hình tốt nhất, thực hiện dự báo lô cho phiên tiếp theo và lưu kết quả
# ====================================================================

# COMMAND ----------

# MAGIC %pip install pandas numpy scikit-learn pyyaml joblib

# COMMAND ----------

import pandas as pd
import numpy as np
import os
import sys
import yaml
import joblib
import json
from datetime import datetime, timedelta
import logging

# Đảm bảo các luồng stdout/stderr trên Windows luôn sử dụng mã hóa UTF-8 để chống lỗi Unicode/charmap
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("04_batch_prediction")

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
            "processed_data_path": config.data.get('processed_data_path', './data/processed'),
            "model_save_path": "./models",
            "model_registry_path": config.ml.get('model_registry_path', '/dbfs/mnt/models')
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
            ml_cfg = cfg.get('ml', {})
            return {
                "processed_data_path": data_cfg.get('processed_data_path', './data/processed'),
                "model_save_path": "./models",
                "model_registry_path": ml_cfg.get('model_registry_path', '/dbfs/mnt/models')
            }
        else:
            return {
                "processed_data_path": "./data/processed",
                "model_save_path": "./models",
                "model_registry_path": "/dbfs/mnt/models"
            }

config_data = load_project_config()
PROCESSED_DATA_PATH = config_data["processed_data_path"]
MODEL_SAVE_PATH = config_data["model_save_path"]
MODEL_REGISTRY_PATH = config_data["model_registry_path"]

if IS_DATABRICKS:
    if not PROCESSED_DATA_PATH.startswith("/dbfs"): PROCESSED_DATA_PATH = "/dbfs" + PROCESSED_DATA_PATH.lstrip(".")
    if not MODEL_SAVE_PATH.startswith("/dbfs") and not MODEL_SAVE_PATH.startswith("/Workspace"):
        MODEL_SAVE_PATH = "./models"
    if not MODEL_REGISTRY_PATH.startswith("/dbfs"): MODEL_REGISTRY_PATH = "/dbfs" + MODEL_REGISTRY_PATH.lstrip(".")

# COMMAND ----------

# ========== LOAD PROCESSED DATA ==========
df_processed = None
if spark is not None:
    try:
        print("Loading processed data from Delta Lake...")
        df_processed = spark.table("bronze.stock_data_processed").toPandas()
        print(f"✓ Loaded {len(df_processed)} records from Delta Table")
    except Exception as e:
        logger.warning(f"Could not load processed data from Delta Table: {e}. Falling back to Parquet file...")

if df_processed is None:
    processed_parquet_file = os.path.join(PROCESSED_DATA_PATH, "processed_stock_data.parquet")
    if os.path.exists(processed_parquet_file):
        print(f"Loading processed data from Parquet file: {processed_parquet_file}...")
        df_processed = pd.read_parquet(processed_parquet_file)
        print(f"✓ Loaded {len(df_processed)} records from Parquet")
    else:
        raise FileNotFoundError(f"Processed data file not found at {processed_parquet_file}")

tickers = df_processed['Ticker'].unique()
print(f"Found tickers in dataset: {list(tickers)}")

# COMMAND ----------

# ========== RUN BATCH PREDICTION ==========
predictions = []

for ticker in tickers:
    print("-" * 50)
    print(f"🔮 Predicting for: {ticker}")
    print("-" * 50)
    
    # 1. Tìm tệp model pkl
    model_paths_to_try = [
        os.path.join(MODEL_SAVE_PATH, f"{ticker.lower()}_best_model.pkl"),
        os.path.join(MODEL_REGISTRY_PATH, f"{ticker.lower()}_best_model.pkl")
    ]
    
    model_file = None
    for p in model_paths_to_try:
        if os.path.exists(p):
            model_file = p
            break
            
    if not model_file:
        logger.warning(f"❌ Best model pkl for ticker {ticker} not found in Workspace or Registry. Skipping prediction.")
        continue
        
    try:
        # Load packaged model
        payload = joblib.load(model_file)
        model = payload['model']
        feature_columns = payload['feature_columns']
        metrics = payload['metrics']
        model_name = payload.get('model_name', 'Unknown Model')
        
        # 2. Lọc hàng dữ liệu cuối cùng của ticker này (phiên gần nhất)
        df_ticker = df_processed[df_processed['Ticker'] == ticker].sort_values('Date').copy()
        if df_ticker.empty:
            logger.warning(f"No data points for ticker {ticker}")
            continue
            
        latest_row = df_ticker.iloc[-1]
        latest_close = float(latest_row['Close'])
        latest_date = latest_row['Date']
        
        # 3. Trích xuất vector feature cho inference
        X = latest_row[feature_columns].values.reshape(1, -1)
        pred_return = float(model.predict(X)[0])
        
        # 4. Tính toán giá ngày tiếp theo và ngày dự báo
        pred_next_close = latest_close * (1 + pred_return)
        
        latest_dt = pd.to_datetime(latest_date)
        next_day = latest_dt + timedelta(days=1)
        while next_day.weekday() >= 5:  # Bỏ qua cuối tuần
            next_day += timedelta(days=1)
            
        # 5. Logic phân tích quyết định & màu sắc đồng nhất với FastAPI backend
        if pred_return >= 0.01:
            recommendation = "🟢 STRONG BUY"
            reco_desc = "Mô hình dự đoán xu hướng tăng mạnh (>1.0%). Rất thích hợp để giải ngân mua mới."
            box_color = "#e6ffe6"
            text_color = "green"
            signal = "🟢 MUA MẠNH"
        elif 0.00 <= pred_return < 0.01:
            recommendation = "🟡 HOLD / BUY"
            reco_desc = "Dự đoán xu hướng sideway hoặc tăng nhẹ (<1.0%). Có thể nắm giữ thêm hoặc mua thăm dò tỷ trọng thấp."
            box_color = "#ffffe6"
            text_color = "#b3b300"
            signal = "🟡 MUA/GIỮ"
        elif -0.01 < pred_return < 0.00:
            recommendation = "🟠 HOLD / SELL"
            reco_desc = "Dự đoán xu hướng điều chỉnh nhẹ. Ưu tiên giữ an toàn tài khoản hoặc chốt lời dần từng phần."
            box_color = "#fff0e6"
            text_color = "#ff8000"
            signal = "🟠 GIỮ/BÁN"
        else:
            recommendation = "🔴 STRONG SELL"
            reco_desc = "Mô hình cảnh báo điều chỉnh sâu (âm >1.0%). Cần chốt lời triệt để hoặc hạ tỷ trọng cắt lỗ bảo vệ tài khoản."
            box_color = "#ffe6e6"
            text_color = "red"
            signal = "🔴 BÁN MẠNH"
            
        # Gom kết quả
        prediction_record = {
            'ticker': ticker,
            'latest_close': latest_close,
            'predicted_next_close': pred_next_close,
            'predicted_return': pred_return,
            'recommendation': recommendation,
            'reco_desc': reco_desc,
            'box_color': box_color,
            'text_color': text_color,
            'model_used': model_name,
            'metrics': json.dumps({
                'rmse': float(metrics.get('rmse', 0)),
                'mae': float(metrics.get('mae', 0)),
                'r2': float(metrics.get('r2', 0))
            }),
            'prediction_date': next_day.strftime('%Y-%m-%d'),
            'timestamp': datetime.now().isoformat(),
            'signal': signal
        }
        
        predictions.append(prediction_record)
        print(f"   ✓ Pred close: {pred_next_close:.2f} ({pred_return*100:+.2f}%) | {recommendation}")
        
    except Exception as e:
        logger.error(f"Error predicting for ticker {ticker}: {e}")

if not predictions:
    raise RuntimeError("No predictions generated. Batch prediction pipeline aborted.")

df_pred = pd.DataFrame(predictions)

# COMMAND ----------

# ========== SAVE PREDICTIONS ==========
# 1. Lưu Delta Table (cho Databricks)
if spark is not None:
    try:
        print("Saving predictions to Delta Lake (bronze.stock_predictions)...")
        spark.createDataFrame(df_pred).write.mode("overwrite").option("mergeSchema", "true").saveAsTable("bronze.stock_predictions")
        print("✓ Successfully saved predictions to Delta Lake: bronze.stock_predictions")
    except Exception as e:
        logger.error(f"Error saving predictions to Delta Lake: {e}")
else:
    print("ℹ️ Spark not available. Skipping Delta Lake prediction save.")

# 2. Lưu Parquet cục bộ (FastAPI backend sẽ đọc file này để hiển thị trên Dashboard)
batch_parquet_path = os.path.join(PROCESSED_DATA_PATH, "batch_predictions.parquet")
try:
    print(f"Saving batch predictions parquet locally to: {batch_parquet_path}...")
    df_pred.to_parquet(batch_parquet_path, index=False)
    print("✓ Successfully saved batch predictions Parquet file.")
except Exception as e:
    logger.error(f"Error saving batch predictions Parquet: {e}")

# COMMAND ----------

print("\n" + "="*70)
print("🔮 STEP 4: BATCH PREDICTION PIPELINE COMPLETED")
print("="*70)
