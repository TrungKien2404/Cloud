# Databricks notebook source
# ====================================================================
# DATABRICKS NOTEBOOK - STEP 3: MODEL TRAINING
# ====================================================================
# Path: /Workspace/stock-prediction/03_train_models
# Description: Huấn luyện các mô hình ML cho từng ticker, đánh giá và lưu best model
# ====================================================================

# COMMAND ----------

# MAGIC %pip install pandas numpy scikit-learn xgboost lightgbm pyyaml joblib

# COMMAND ----------

import pandas as pd
import numpy as np
import os
import sys
import yaml
import joblib
from datetime import datetime
import logging

# Đảm bảo các luồng stdout/stderr trên Windows luôn sử dụng mã hóa UTF-8 để chống lỗi Unicode/charmap
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

# ML Libraries
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb
import lightgbm as lgb

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("03_train_models")

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
        MODEL_SAVE_PATH = "./models" # Local path in Workspace is usually fine
    if not MODEL_REGISTRY_PATH.startswith("/dbfs"): MODEL_REGISTRY_PATH = "/dbfs" + MODEL_REGISTRY_PATH.lstrip(".")

os.makedirs(MODEL_SAVE_PATH, exist_ok=True)
if IS_DATABRICKS:
    try:
        os.makedirs(MODEL_REGISTRY_PATH, exist_ok=True)
    except Exception as e:
        logger.warning(f"Could not create registry path {MODEL_REGISTRY_PATH}: {e}")

# COMMAND ----------

# ========== LOAD DATA ==========
train_df, val_df, test_df = None, None, None

if spark is not None:
    try:
        print("Loading split datasets from Delta Lake...")
        train_df = spark.table("bronze.stock_data_train").toPandas()
        val_df = spark.table("bronze.stock_data_val").toPandas()
        test_df = spark.table("bronze.stock_data_test").toPandas()
        print("✓ Loaded train/val/test data from Delta tables.")
    except Exception as e:
        logger.warning(f"Could not load splits from Delta tables: {e}. Falling back to Parquet files...")

if train_df is None:
    try:
        print("Loading split datasets from Parquet files...")
        train_df = pd.read_parquet(os.path.join(PROCESSED_DATA_PATH, "train_stock_data.parquet"))
        val_df = pd.read_parquet(os.path.join(PROCESSED_DATA_PATH, "val_stock_data.parquet"))
        test_df = pd.read_parquet(os.path.join(PROCESSED_DATA_PATH, "test_stock_data.parquet"))
        print("✓ Loaded train/val/test data from Parquet files.")
    except Exception as e:
        logger.error(f"Error loading Parquet splits: {e}")
        # Fallback to full processed data and splitting on-the-fly
        processed_file = os.path.join(PROCESSED_DATA_PATH, "processed_stock_data.parquet")
        if os.path.exists(processed_file):
            print(f"Loading full processed data and splitting: {processed_file}")
            df_full = pd.read_parquet(processed_file)
            
            # Chia dataset
            train_dfs, val_dfs, test_dfs = [], [], []
            for ticker in df_full['Ticker'].unique():
                df_ticker = df_full[df_full['Ticker'] == ticker].sort_values('Date').copy()
                n = len(df_ticker)
                test_n = int(n * 0.2)
                val_n = int(n * 0.1)
                train_n = n - test_n - val_n
                train_dfs.append(df_ticker.iloc[:train_n])
                val_dfs.append(df_ticker.iloc[train_n:train_n+val_n])
                test_dfs.append(df_ticker.iloc[train_n+val_n:])
            
            train_df = pd.concat(train_dfs, ignore_index=True)
            val_df = pd.concat(val_dfs, ignore_index=True)
            test_df = pd.concat(test_dfs, ignore_index=True)
            print("✓ On-the-fly splitting completed.")
        else:
            raise FileNotFoundError("Could not find any processed dataset splits to load.")

tickers = train_df['Ticker'].unique()
print(f"Tickers to train: {list(tickers)}")

# COMMAND ----------

# ========== MODEL INITIALIZATION ==========
def get_models_dict():
    return {
        'Linear Regression': LinearRegression(),
        'Random Forest': RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        ),
        'Gradient Boosting': GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            min_samples_split=5,
            min_samples_leaf=2,
            subsample=0.8,
            random_state=42,
            verbose=0
        ),
        'XGBoost': xgb.XGBRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
            n_jobs=-1
        ),
        'LightGBM': lgb.LGBMRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
            n_jobs=-1,
            verbose=-1
        )
    }

# COMMAND ----------

# ========== TRAINING PIPELINE PER TICKER ==========
exclude_cols = ['Date', 'Ticker', 'FetchDate', 'Target_Price', 'Target_Return', 'Target']
feature_columns = [col for col in train_df.columns if col not in exclude_cols and pd.api.types.is_numeric_dtype(train_df[col])]

print(f"Training models with {len(feature_columns)} features:")
print(f"Features: {feature_columns}\n")

for ticker in tickers:
    print("=" * 60)
    print(f"📈 Huấn luyện mô hình cho cổ phiếu: {ticker}")
    print("=" * 60)
    
    # Lọc dữ liệu theo ticker
    df_train_t = train_df[train_df['Ticker'] == ticker].sort_values('Date')
    df_val_t = val_df[val_df['Ticker'] == ticker].sort_values('Date')
    df_test_t = test_df[test_df['Ticker'] == ticker].sort_values('Date')
    
    if len(df_train_t) < 30:
        print(f"⚠️ Quá ít dữ liệu ({len(df_train_t)}) để huấn luyện cho {ticker}. Bỏ qua.")
        continue
        
    # Chuẩn bị X và y (sử dụng Raw/Unscaled features để đồng bộ với API Serving hiện tại)
    X_train = df_train_t[feature_columns].values
    y_train = df_train_t['Target_Return'].values
    
    X_val = df_val_t[feature_columns].values
    y_val = df_val_t['Target_Return'].values
    
    X_test = df_test_t[feature_columns].values
    y_test = df_test_t['Target_Return'].values
    
    print(f"   Dữ liệu: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}")
    
    # Khởi tạo mô hình
    models = get_models_dict()
    trained_models = {}
    val_metrics = {}
    
    # Huấn luyện và đánh giá trên validation set
    for name, model in models.items():
        try:
            model.fit(X_train, y_train)
            trained_models[name] = model
            
            # Predict và tính metrics trên validation
            preds = model.predict(X_val)
            rmse = np.sqrt(mean_squared_error(y_val, preds))
            mae = mean_absolute_error(y_val, preds)
            r2 = r2_score(y_val, preds)
            
            val_metrics[name] = {
                'rmse': rmse,
                'mae': mae,
                'r2': r2
            }
            print(f"   ✓ Model {name:<18} | Val RMSE: {rmse:.6f} | Val R2: {r2:.4f}")
        except Exception as e:
            logger.error(f"Error training {name} for {ticker}: {e}")
            
    if not val_metrics:
        print(f"❌ Không có mô hình nào huấn luyện thành công cho {ticker}.")
        continue
        
    # Chọn mô hình tốt nhất dựa trên RMSE thấp nhất
    best_model_name = min(val_metrics, key=lambda x: val_metrics[x]['rmse'])
    best_model = trained_models[best_model_name]
    best_val_metrics = val_metrics[best_model_name]
    
    # Đánh giá cuối trên tập Test
    test_preds = best_model.predict(X_test)
    test_rmse = np.sqrt(mean_squared_error(y_test, test_preds))
    test_mae = mean_absolute_error(y_test, test_preds)
    test_r2 = r2_score(y_test, test_preds)
    
    print(f"\n   🏆 Best Model: {best_model_name}")
    print(f"   📊 Test RMSE:  {test_rmse:.6f}")
    print(f"   📊 Test R2:    {test_r2:.4f}")
    
    # Đóng gói package model giống hệt cấu trúc hiện tại của dự án
    payload = {
        'model_name': best_model_name,
        'model': best_model,
        'scaler': None, # Gán None vì ta không scale features
        'feature_columns': feature_columns,
        'metrics': {
            'rmse': test_rmse,
            'mae': test_mae,
            'r2': test_r2
        },
        'timestamp': datetime.now().isoformat()
    }
    
    # 1. Lưu mô hình vào workspace cục bộ (phục vụ FastAPI)
    local_model_path = os.path.join(MODEL_SAVE_PATH, f"{ticker.lower()}_best_model.pkl")
    joblib.dump(payload, local_model_path)
    print(f"   💾 Saved model to Workspace path: {local_model_path}")
    
    # 2. Lưu mô hình vào model registry / DBFS (cho Databricks deployment)
    if IS_DATABRICKS and os.path.exists(MODEL_REGISTRY_PATH):
        registry_model_path = os.path.join(MODEL_REGISTRY_PATH, f"{ticker.lower()}_best_model.pkl")
        try:
            joblib.dump(payload, registry_model_path)
            print(f"   💾 Saved model to Registry path:  {registry_model_path}")
        except Exception as e:
            logger.warning(f"Could not copy model to registry: {e}")

# COMMAND ----------

print("\n" + "="*70)
print("🤖 STEP 3: MODEL TRAINING PIPELINE COMPLETED")
print("="*70)
