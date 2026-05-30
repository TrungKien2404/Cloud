from model.model_training import StockModelTrainer
from configs.config import Config
from etl.etl_pipeline import StockETLPipeline
import pandas as pd
import os
import sys

# Đảm bảo các luồng stdout/stderr trên Windows luôn sử dụng mã hóa UTF-8 để chống lỗi Unicode/charmap
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

config = Config()

# Tạo thư mục models nếu chưa có
os.makedirs('./models', exist_ok=True)

print("=" * 60)
print("🤖 STEP 3: MODEL TRAINING - Huấn luyện ML models theo từng mã")
print("=" * 60)

# Load processed data
processed_path = os.path.join(config.data.get('processed_data_path', './data/processed'), 'processed_stock_data.parquet')
if not os.path.exists(processed_path):
    print(f"❌ Processed data not found at {processed_path}. Please run ETL first.")
    exit(1)

df = pd.read_parquet(processed_path)
print(f"\n📖 Load processed data from: {processed_path}")
print(f"📊 Total Records: {len(df)}")

tickers = df['Ticker'].unique()
print(f"🎯 Found tickers to train: {list(tickers)}\n")

# Prepare ETL
etl = StockETLPipeline(
    test_size=config.etl.get('test_size', 0.2),
    val_size=config.etl.get('validation_size', 0.1)
)

for ticker in tickers:
    print("-" * 50)
    print(f"📈 Training model for ticker: {ticker}")
    print("-" * 50)
    
    # Filter data for this ticker
    df_ticker = df[df['Ticker'] == ticker].copy()
    if 'Date' in df_ticker.columns:
        df_ticker = df_ticker.sort_values('Date')
        
    print(f"   Records for {ticker}: {len(df_ticker)}")
    
    if len(df_ticker) < 30:
        print(f"   ⚠️ Too few samples ({len(df_ticker)}) for training. Skipping.")
        continue
        
    # Split train/val/test
    train_data, val_data, test_data = etl.split_train_val_test(df_ticker)
    
    X_train, y_train = train_data
    X_val, y_val = val_data
    X_test, y_test = test_data
    
    print(f"   Train: {len(X_train)} samples, Val: {len(X_val)} samples, Test: {len(X_test)} samples")
    
    # Khởi tạo trainer
    trainer = StockModelTrainer(model_save_path='./models')
    
    # Chạy training pipeline
    result = trainer.run_training_pipeline(
        X_train=X_train, y_train=y_train,
        X_val=X_val, y_val=y_val,
        X_test=X_test, y_test=y_test
    )
    
    # Xác định feature columns chính xác cho model
    exclude_cols = ['Date', 'Ticker', 'FetchDate', 'Target_Price', 'Target_Return']
    feature_columns = [col for col in df_ticker.columns if col not in exclude_cols and pd.api.types.is_numeric_dtype(df_ticker[col])]
    
    # Lưu best model theo mã chứng khoán kèm features
    model_file = trainer.save_best_model_for_ticker(ticker, scaler=None, feature_columns=feature_columns)
    
    print(f"   🏆 BEST MODEL FOR {ticker}: {result['best_model_name']}")
    print(f"   Test RMSE: {result['test_metrics']['rmse']:.6f}")
    print(f"   Saved packaged model to: {model_file}\n")

print("=" * 60)
print("✅ Ticker model training completed!")
print("=" * 60)
