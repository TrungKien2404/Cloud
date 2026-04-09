# 📚 IMPLEMENTATION & DEPLOYMENT GUIDE

## Quick Start (5 minutes)

### Option 1: Run Locally

```bash
# 1. Clone/Download project
cd stock-prediction-system

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run pipeline (sequential)
python -m ingestion.data_ingestion
python -m etl.etl_pipeline
python -m model.model_training

# 4. Launch API
cd api
uvicorn api_service:app --reload

# 5. In another terminal, launch dashboard
streamlit run dashboard/dashboard.py

# 6. Open browser
# API: http://localhost:8000/docs
# Dashboard: http://localhost:8501
```

### Option 2: Run on Databricks (Free Tier)

```bash
# 1. Create Databricks Community Edition account (free)
# https://community.cloud.databricks.com

# 2. Create new workspace/cluster

# 3. Create folder: /Workspace/stock-prediction

# 4. Upload notebooks from notebooks/ folder:
#    - 01_etl_pipeline.py
#    - 02_model_training.py

# 5. Run notebooks sequentially
# 6. Check Delta Lake tables:
#    SELECT * FROM bronze.stock_predictions LIMIT 10;
```

---

## 🎯 Detailed Implementation Steps

### STEP 1: Environment Setup

#### On Local Machine:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

#### On Databricks:

```python
# In first cell of notebook:
%pip install yfinance pandas numpy scikit-learn

# Or attach to existing cluster with libraries pre-installed
```

---

### STEP 2: Data Ingestion

#### Local Execution:

```python
# file: run_ingestion.py
from ingestion.data_ingestion import StockDataIngestion, setup_logging

# Setup
setup_logging(log_file="./logs/ingestion.log")

ingestion = StockDataIngestion(
    tickers=["AAPL", "TSLA", "MSFT"],
    history_years=5,
    raw_data_path="./data/raw"
)

# Run
stock_data = ingestion.run_ingestion_pipeline()

print("✅ Ingestion complete!")
print(f"Files saved in ./data/raw/")
```

#### Databricks Execution:

```python
# In notebook cell:
%pip install yfinance

import yfinance as yf
from datetime import datetime, timedelta

TICKERS = ["AAPL", "TSLA", "MSFT"]
HISTORY_YEARS = 5

# Fetch and combine
dfs = []
for ticker in TICKERS:
    df = yf.download(ticker, period=f"{HISTORY_YEARS}y")
    df['Ticker'] = ticker
    dfs.append(df.reset_index())

combined = pd.concat(dfs, ignore_index=True)

# Save to Delta Lake
spark_df = spark.createDataFrame(combined)
spark_df.write.mode("overwrite").saveAsTable("bronze.stock_data_raw")
```

---

### STEP 3: ETL Processing

#### Local Execution:

```python
# file: run_etl.py
import pandas as pd
from etl.etl_pipeline import StockETLPipeline
import logging

logging.basicConfig(level=logging.INFO)

# Load raw data
df_raw = pd.read_parquet("./data/raw/combined_stock_data.parquet")

# Initialize ETL pipeline
etl = StockETLPipeline(
    ma_windows=[10, 20, 50],
    lag_windows=[1, 5, 10],
    rsi_period=14,
    test_size=0.2,
    val_size=0.1
)

# Run ETL
result = etl.run_etl_pipeline(df_raw)

# Extract results
processed_df = result['processed_df']
train_data = result['train_data']
val_data = result['val_data']
test_data = result['test_data']
feature_cols = result['feature_columns']
scaler = result['scaler']

# Save preprocessed data
processed_df.to_parquet("./data/processed/features.parquet")
print("✅ ETL complete!")
print(f"Features created: {len(feature_cols)}")
print(f"Train/Val/Test split: {len(train_data[1])}/{len(val_data[1])}/{len(test_data[1])}")
```

---

### STEP 4: Model Training

#### Local Execution:

```python
# file: run_training.py
from model.model_training import StockModelTrainer
import numpy as np

# Load preprocessed data
# (from previous ETL step)
X_train, y_train = train_data
X_val, y_val = val_data
X_test, y_test = test_data

# Initialize trainer
trainer = StockModelTrainer(model_save_path="./models")

# Run full pipeline
result = trainer.run_training_pipeline(
    X_train, y_train,
    X_val, y_val,
    X_test, y_test
)

# Access results
best_model_name = result['best_model_name']
best_model = result['best_model']
metrics = result['model_metrics']
saved_models = result['saved_models']

print(f"✅ Training complete!")
print(f"Best model: {best_model_name}")
print(f"RMSE: {metrics[best_model_name]['rmse']:.6f}")

# Models saved to ./models/
```

#### Databricks Execution:

```python
# In notebook (similar to local but uses Delta Lake)
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# Load data from Delta Lake
train_df = spark.table("bronze.stock_data_train").toPandas()
val_df = spark.table("bronze.stock_data_val").toPandas()
test_df = spark.table("bronze.stock_data_test").toPandas()

# Prepare features
feature_cols = [col for col in train_df.columns if col not in 
                ['Date', 'Ticker', 'Close', 'Target']]
X_train = train_df[feature_cols].values
y_train = train_df['Target'].values

# Train model
model = GradientBoostingRegressor(n_estimators=100)
model.fit(X_train, y_train)

# Save predictions
predictions_df = test_df[['Date', 'Ticker']].copy()
predictions_df['Predicted'] = model.predict(test_df[feature_cols].values)
predictions_df['Actual'] = test_df['Target'].values

# Save to Delta Lake
spark_predictions = spark.createDataFrame(predictions_df)
spark_predictions.write.mode("overwrite").saveAsTable("bronze.stock_predictions")
```

---

### STEP 5: API Service

#### Launch API:

```bash
cd api/

# Option 1: Direct run
python api_service.py

# Option 2: Using uvicorn
uvicorn api_service:app --host 0.0.0.0 --port 8000 --reload

# Option 3: Production deployment
gunicorn -w 4 -k uvicorn.workers.UvicornWorker api_service:app --bind 0.0.0.0:8000
```

#### Load Models into API:

```python
# In api_service.py initialization
api = StockPredictionAPI(model_path="./models")

# Manually load data
api.load_data("AAPL", "./data/processed/AAPL_features.parquet")
api.load_data("TSLA", "./data/processed/TSLA_features.parquet")
api.load_data("MSFT", "./data/processed/MSFT_features.parquet")

# Start server
uvicorn.run(api.get_app(), host="0.0.0.0", port=8000)
```

#### Test Endpoints:

```bash
# Health check
curl http://localhost:8000/health

# List models
curl http://localhost:8000/models

# Get prediction
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL"}'

# Get data
curl http://localhost:8000/data/AAPL?days=30

# Get statistics
curl http://localhost:8000/stats/AAPL
```

---

### STEP 6: Dashboard

#### Launch Dashboard:

```bash
# Navigate to dashboard folder
cd dashboard/

# Run streamlit
streamlit run dashboard.py

# App will open at http://localhost:8501
```

#### Load Data into Dashboard:

```python
# At top of dashboard.py
import pandas as pd
from pathlib import Path

# Load processed data
@st.cache_data
def load_stock_data():
    processed_path = Path("./data/processed")
    data = {}
    
    for ticker in ["AAPL", "TSLA", "MSFT"]:
        try:
            df = pd.read_parquet(f"{processed_path}/{ticker}_features.parquet")
            data[ticker] = df
        except:
            st.warning(f"Data for {ticker} not found")
    
    return data

stock_data = load_stock_data()

# Initialize dashboard
dashboard = StockDashboard()
dashboard.render_header()

# Render tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "Price Analysis", 
    "Predictions", 
    "Indicators", 
    "Metrics"
])

with tab1:
    ticker = st.selectbox("Select Stock", list(stock_data.keys()))
    fig = dashboard.plot_price_history(stock_data[ticker], ticker)
    st.plotly_chart(fig, use_container_width=True)
```

---

### STEP 7: Databricks Jobs Setup

#### Create Job via UI:

1. Go to Databricks workspace
2. Click **Workflows** → **Jobs**
3. Create new job:
   - Name: `Stock_ETL_Job`
   - Notebook: `/Workspace/stock-prediction/01_etl_pipeline`
   - Cluster: Select existing cluster
   - Schedule: Daily at 9:00 AM
4. Create another job for training (starts 11:00 AM)

#### Create Job via API:

```bash
# Create ETL job
curl -X POST https://<databricks-instance>/api/2.1/jobs/create \
  -H "Authorization: Bearer <token>" \
  -d '{
    "name": "Stock_ETL_Job",
    "new_cluster": {
      "spark_version": "12.2.x-scala2.12",
      "node_type_id": "i3.xlarge",
      "num_workers": 2
    },
    "notebook_task": {
      "notebook_path": "/stock-prediction/01_etl_pipeline"
    },
    "schedule": {
      "quartz_cron_expression": "0 9 * * ?",
      "timezone_id": "UTC"
    }
  }'
```

---

### STEP 8: Monitoring & Maintenance

#### Monitor Jobs:

```sql
-- Check job history
SELECT job_id, start_time, end_time, state, duration_seconds
FROM system.jobs.job_run_history
WHERE job_name LIKE 'Stock_%'
ORDER BY start_time DESC
LIMIT 10;

-- Check prediction freshness
SELECT MAX(Timestamp) as latest_prediction
FROM bronze.stock_predictions
GROUP BY Model;

-- Monitor error rates
SELECT Ticker, COUNT(*) as predictions, 
       AVG(Prediction_Error) as avg_error
FROM bronze.stock_predictions
WHERE DATE(Timestamp) >= DATE_SUB(current_date, 7)
GROUP BY Ticker;
```

#### Performance Tuning:

```python
# If performance degrades:

# 1. Check data size
df.info()  # Check memory usage

# 2. Optimize features
# Remove low-variance features
df.var()[(df.var() < 0.01)]  # Remove these

# 3. Reduce history
# Change HISTORY_YEARS = 2 (instead of 5)

# 4. Use caching
@st.cache_data(ttl=3600)
def get_predictions():
    # Load data once per hour
    return ...

# 5. Optimize SQL queries
# Use LIMIT, WHERE conditions
SELECT * FROM bronze.stock_predictions 
WHERE Ticker = 'AAPL' 
AND Timestamp >= current_date - 30 LIMIT 1000;
```

---

## 🐳 Docker Deployment (Optional)

### Dockerfile for API Service:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ingestion/ ./ingestion/
COPY etl/ ./etl/
COPY model/ ./model/
COPY api/ ./api/
COPY models/ ./models/
COPY data/ ./data/

EXPOSE 8000

CMD ["uvicorn", "api.api_service:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Build and Run:

```bash
# Build image
docker build -t stock-prediction-api .

# Run container
docker run -p 8000:8000 stock-prediction-api

# With volume mount
docker run -p 8000:8000 \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/data:/app/data \
  stock-prediction-api
```

---

## ✅ Verification Checklist

- [ ] All dependencies installed
- [ ] Data ingestion successful (files created)
- [ ] ETL features engineered (shape increased)
- [ ] Models trained (3 PKL files created)
- [ ] API running (health check passes)
- [ ] Dashboard loads without errors
- [ ] Predictions generated
- [ ] Databricks jobs scheduled
- [ ] Logs reviewed (no critical errors)
- [ ] Performance metrics acceptable (RMSE < 0.02)

---

## 📊 Expected Output Examples

### Ingestion:
```
✓ Fetching data for AAPL...
✓ Successfully fetched 1255 records for AAPL
✓ Fetching data for TSLA...
✓ Successfully fetched 1204 records for TSLA
✓ Fetching data for MSFT...
✓ Successfully fetched 1260 records for MSFT
✓ Saved combined data (3719 records) to ./data/raw/combined_stock_data.parquet
```

### ETL:
```
Feature engineering completed. Final shape: (3195, 43)

Data split - Train: 2236, Val: 320, Test: 639
Features standardized (fitted on training data)
```

### Training:
```
================================================== 
MODEL COMPARISON RESULTS
==================================================
Model Name           |       RMSE |        MAE |  R² Score
--------------------------------------------------
Linear Regression    |   0.015234 |   0.008901 |   0.3456
Random Forest        |   0.012456 |   0.007234 |   0.5234
Gradient Boosting    |   0.010123 |   0.005678 |   0.6789
==================================================
✓ Best Model: Gradient Boosting (lowest RMSE)
==================================================
```

---

**Version**: 1.0.0  
**Last Updated**: April 2024  
**Status**: Production Ready ✅
