# ====================================================================
# DATABRICKS NOTEBOOK - Model Training
# ====================================================================
# Path: /Workspace/stock-prediction/02_model_training
# Runtime: Databricks Runtime with Python 3.10+
#
# Mục đích:
# - Load processed data từ Delta Lake
# - Train 3 ML models
# - Evaluate models
# - Save best model
# - Log metrics
#
# ====================================================================

# COMMAND ----------

# Install libraries
# %pip install scikit-learn pandas numpy

# COMMAND ----------

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import pickle
import os
from datetime import datetime

# COMMAND ----------

# ========== ENVIRONMENT DETECTION ==========

# Detect if running on Databricks or Locally
IS_DATABRICKS = "DATABRICKS_RUNTIME_VERSION" in os.environ
print(f"Environment: {'DATABRICKS' if IS_DATABRICKS else 'LOCAL'}")

# ========== SPARK SESSION MANAGEMENT ==========

def get_spark_session():
    """
    Get or create a Spark session. 
    1. First tries to use the existing global 'spark' if it's alive.
    2. Then tries DatabricksSession (for Databricks Connect / Refresh).
    3. On Local: Skips standard Spark initialization to avoid hanging on Windows 
       if Java/winutils are not configured.
    """
    # 1. Try global spark first (standard on-cluster behavior)
    try:
        if 'spark' in globals():
            s = globals()['spark']
            # Run a lightweight operation to check if the session is alive
            s.range(1).collect()
            return s
    except Exception:
        # Session is likely expired or broken, will try to refresh below
        pass

    # 2. Try to refresh or create a new session (Databricks Connect)
    try:
        from databricks.connect import DatabricksSession
        return DatabricksSession.builder.getOrCreate()
    except (ImportError, Exception):
        # 3. Local Fallback
        if not IS_DATABRICKS:
            print("Info: Running locally without Databricks Connect. Skipping local Spark initialization to avoid hanging.")
            return None
            
        # 4. Databricks Fallback (on cluster but spark not in globals)
        try:
            from pyspark.sql import SparkSession
            return SparkSession.builder.getOrCreate()
        except Exception:
            print("⚠️ Could not initialize Spark session.")
            return None

# Refresh session at the start
spark = get_spark_session()

# COMMAND ----------

# ========== CONFIGURATION ==========

DELTA_CATALOG = "bronze"
RANDOM_STATE = 42

if IS_DATABRICKS:
    MODELS_PATH = "/dbfs/mnt/models"
    DATA_PATH = "/dbfs/mnt/data"
else:
    # Local paths for Windows/Local development
    MODELS_PATH = os.path.join(os.getcwd(), "models")
    DATA_PATH = os.path.join(os.getcwd(), "data")

print(f"Models path: {MODELS_PATH}")
print(f"Data path: {DATA_PATH}")

# Create models directory if not exists
os.makedirs(MODELS_PATH, exist_ok=True)

# COMMAND ----------

# ========== STEP 1: LOAD DATA FROM DELTA LAKE ==========

# Load train/val/test data
if spark is not None:
    print("Loading data from Delta Lake...")
    train_df = spark.table(f"{DELTA_CATALOG}.stock_data_train").toPandas()
    val_df = spark.table(f"{DELTA_CATALOG}.stock_data_val").toPandas()
    test_df = spark.table(f"{DELTA_CATALOG}.stock_data_test").toPandas()
else:
    print("Info: Spark not available. Loading data from local CSV files...")
    train_df = pd.read_csv(os.path.join(DATA_PATH, "stock_data_train.csv"))
    val_df = pd.read_csv(os.path.join(DATA_PATH, "stock_data_val.csv"))
    test_df = pd.read_csv(os.path.join(DATA_PATH, "stock_data_test.csv"))
    
    # Ensure Date column is datetime
    for df in [train_df, val_df, test_df]:
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])

print(f"[OK] Train: {len(train_df)} records")
print(f"[OK] Val:   {len(val_df)} records")
print(f"[OK] Test:  {len(test_df)} records")

# COMMAND ----------

# ========== STEP 2: PREPARE FEATURES ==========

# Select feature columns (exclude metadata and target info)
exclude_cols = ['Date', 'Ticker', 'FetchDate', 'Close', 'Open', 'High', 'Low', 'Volume', 'Dividends', 'Stock Splits', 'Target']
feature_cols = [col for col in train_df.columns if col not in exclude_cols and train_df[col].dtype in [np.float64, np.float32, np.int64]]

print(f"Feature columns ({len(feature_cols)}):")
for i, col in enumerate(feature_cols):
    print(f"  {i+1}. {col}")

# COMMAND ----------

# Prepare X and y
X_train = train_df[feature_cols].values
y_train = train_df['Target'].values

X_val = val_df[feature_cols].values
y_val = val_df['Target'].values

X_test = test_df[feature_cols].values
y_test = test_df['Target'].values

print(f"\nData shapes:")
print(f"X_train: {X_train.shape}, y_train: {y_train.shape}")
print(f"X_val: {X_val.shape}, y_val: {y_val.shape}")
print(f"X_test: {X_test.shape}, y_test: {y_test.shape}")

# COMMAND ----------

# ========== STEP 3: STANDARDIZE FEATURES ==========

# Fit scaler on training data only
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)
X_test_scaled = scaler.transform(X_test)

print("[OK] Features standardized")

# COMMAND ----------

# ========== STEP 4: TRAIN MODELS ==========

print("\n" + "="*70)
print("MODEL TRAINING")
print("="*70 + "\n")

models = {}
training_times = {}

# Model 1: Linear Regression
print("Training Linear Regression...")
start_time = datetime.now()
lr_model = LinearRegression()
lr_model.fit(X_train_scaled, y_train)
models['Linear Regression'] = lr_model
training_times['Linear Regression'] = (datetime.now() - start_time).total_seconds()
print(f"[OK] Linear Regression trained ({training_times['Linear Regression']:.2f}s)")

# COMMAND ----------

# Model 2: Random Forest
print("\nTraining Random Forest...")
start_time = datetime.now()
rf_model = RandomForestRegressor(
    n_estimators=100,
    max_depth=10,
    min_samples_split=5,
    random_state=RANDOM_STATE,
    n_jobs=-1
)
rf_model.fit(X_train_scaled, y_train)
models['Random Forest'] = rf_model
training_times['Random Forest'] = (datetime.now() - start_time).total_seconds()
print(f"[OK] Random Forest trained ({training_times['Random Forest']:.2f}s)")

# COMMAND ----------

# Model 3: Gradient Boosting
print("\nTraining Gradient Boosting...")
start_time = datetime.now()
gb_model = GradientBoostingRegressor(
    n_estimators=100,
    learning_rate=0.1,
    max_depth=5,
    random_state=RANDOM_STATE
)
gb_model.fit(X_train_scaled, y_train)
models['Gradient Boosting'] = gb_model
training_times['Gradient Boosting'] = (datetime.now() - start_time).total_seconds()
print(f"[OK] Gradient Boosting trained ({training_times['Gradient Boosting']:.2f}s)")

print("\n[OK] All models trained successfully")

# COMMAND ----------

# ========== STEP 5: EVALUATE MODELS ==========

print("\n" + "="*70)
print("MODEL EVALUATION")
print("="*70 + "\n")

def evaluate_model(model, X_val, y_val, model_name):
    """Evaluate single model"""
    y_pred = model.predict(X_val)
    
    rmse = np.sqrt(mean_squared_error(y_val, y_pred))
    mae = mean_absolute_error(y_val, y_pred)
    r2 = r2_score(y_val, y_pred)
    
    return {'rmse': rmse, 'mae': mae, 'r2': r2, 'predictions': y_pred}

metrics = {}

print("Validation Set Results:")
print("-" * 70)
print(f"{'Model':<20} | {'RMSE':>12} | {'MAE':>12} | {'R2 Score':>12}")
print("-" * 70)

for model_name, model in models.items():
    metric = evaluate_model(model, X_val_scaled, y_val, model_name)
    metrics[model_name] = metric
    print(f"{model_name:<20} | {metric['rmse']:>12.6f} | {metric['mae']:>12.6f} | {metric['r2']:>12.6f}")

# COMMAND ----------

# Select best model based on RMSE
best_model_name = min(metrics, key=lambda x: metrics[x]['rmse'])
best_model = models[best_model_name]

print("\n" + "="*70)
print(f"\n[OK] BEST MODEL: {best_model_name}")
print(f"  RMSE: {metrics[best_model_name]['rmse']:.6f}")
print(f"  MAE:  {metrics[best_model_name]['mae']:.6f}")
print(f"  R2:   {metrics[best_model_name]['r2']:.6f}")
print("="*70)

# COMMAND ----------

# ========== STEP 6: TEST SET EVALUATION ==========

print("\nTest Set Results (Final Evaluation):")
print("-" * 70)

test_metrics = {}
for model_name, model in models.items():
    metric = evaluate_model(model, X_test_scaled, y_test, model_name)
    test_metrics[model_name] = metric
    print(f"{model_name:<20} | RMSE: {metric['rmse']:>12.6f} | R2: {metric['r2']:>12.6f}")

# COMMAND ----------

# ========== STEP 7: SAVE MODELS ==========

print("\nSaving models...")

saved_models = {}
for model_name, model in models.items():
    safe_name = model_name.replace(" ", "_").lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(MODELS_PATH, f"{safe_name}_{timestamp}.pkl")
    
    with open(file_path, 'wb') as f:
        pickle.dump(model, f)
    
    saved_models[model_name] = file_path
    print(f"[OK] Saved {model_name} to {file_path}")

# COMMAND ----------

# Save scaler
scaler_path = os.path.join(MODELS_PATH, f"scaler_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl")
with open(scaler_path, 'wb') as f:
    pickle.dump(scaler, f)
print(f"[OK] Saved scaler to {scaler_path}")

# COMMAND ----------

# ========== STEP 8: CREATE PREDICTIONS TABLE ==========

print("\nCreating predictions table...")

# Generate predictions on test set using best model
y_pred_best = best_model.predict(X_test_scaled)

# Create predictions dataframe
pred_df = test_df[['Date', 'Ticker', 'Close']].copy()
pred_df['Actual_Return'] = y_test
pred_df['Predicted_Return'] = y_pred_best
pred_df['Prediction_Error'] = np.abs(y_test - y_pred_best)
pred_df['Model'] = best_model_name
pred_df['Timestamp'] = datetime.now()

# Save predictions
if spark is not None:
    # Save to Delta Lake
    spark_pred_df = spark.createDataFrame(pred_df)
    spark_pred_df.write.mode("overwrite").option("mergeSchema", "true").saveAsTable(
        f"{DELTA_CATALOG}.stock_predictions"
    )
    print(f"[OK] Saved {len(pred_df)} predictions to Delta Lake table: {DELTA_CATALOG}.stock_predictions")
else:
    # Save to local CSV
    pred_path = os.path.join(DATA_PATH, "stock_predictions.csv")
    pred_df.to_csv(pred_path, index=False)
    print(f"[OK] Saved {len(pred_df)} predictions to local CSV: {pred_path}")

# End of prediction saving

# COMMAND ----------

# ========== SUMMARY ==========

print("\n" + "="*70)
print("MODEL TRAINING COMPLETED SUCCESSFULLY")
print("="*70)
print(f"\nTraining Summary:")
print(f"- Total models trained: {len(models)}")
print(f"- Best model: {best_model_name}")
print(f"- Best RMSE: {metrics[best_model_name]['rmse']:.6f}")
print(f"- Models saved to: {MODELS_PATH}")
print(f"- Predictions table: {DELTA_CATALOG}.stock_predictions")
print("="*70)
