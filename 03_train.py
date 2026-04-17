# Databricks notebook source
from model.model_training import StockModelTrainer
from configs.config import Config
from etl.etl_pipeline import StockETLPipeline
import pandas as pd
import os

config = Config()

# Tạo thư mục models nếu chưa có
os.makedirs('./models', exist_ok=True)

print("=" * 60)
print("🤖 STEP 3: MODEL TRAINING - Huấn luyện ML models")
print("=" * 60)

# Load processed data
processed_path = os.path.join(config.data.get('processed_data_path', './data/processed'), 'processed_stock_data.parquet')
df = pd.read_parquet(processed_path)

print(f"\n📖 Load processed data from: {processed_path}")
print(f"📊 Records: {len(df)}\n")

# Prepare data
etl = StockETLPipeline(
    test_size=config.etl.get('test_size', 0.2),
    val_size=config.etl.get('validation_size', 0.1)
)
train_data, val_data, test_data = etl.split_train_val_test(df)

X_train, y_train = train_data
X_val, y_val = val_data
X_test, y_test = test_data

print("📊 Data Split:")
print(f"   Train: {len(X_train)} samples")
print(f"   Val: {len(X_val)} samples")
print(f"   Test: {len(X_test)} samples\n")

# Khởi tạo trainer
trainer = StockModelTrainer(model_save_path='./models')

print("🤖 Training Models:")
print("   1️⃣ Linear Regression...")
print("   2️⃣ Random Forest...")
print("   3️⃣ Gradient Boosting...\n")

# Chạy training pipeline
result = trainer.run_training_pipeline(
    X_train=X_train, y_train=y_train,
    X_val=X_val, y_val=y_val,
    X_test=X_test, y_test=y_test
)

print("\n✅ Model Training Completed!\n")

# Kết quả đã được in trong thư viện model_training.py
print(f"\n{'='*80}")
print(f"🏆 BEST MODEL: {result['best_model_name']}")
print(f"   Test RMSE: {result['test_metrics']['rmse']:.6f}")
print(f"{'='*80}\n")



# COMMAND ----------

import numpy as np
import matplotlib.pyplot as plt

models = list(metrics.keys())
rmse = [float(metrics[m]['rmse']) for m in models]
mae = [float(metrics[m]['mae']) for m in models]

x = np.arange(len(models))
width = 0.35
print("\n📋 Model Comparison Table:")
display(df_metrics.sort_values(by="RMSE"))

plt.figure(figsize=(10,5))

plt.bar(x - width/2, rmse, width, label='RMSE')
plt.bar(x + width/2, mae, width, label='MAE')

plt.xticks(x, models, rotation=30)
plt.title("Model Comparison (RMSE vs MAE)")
plt.legend()

plt.show()