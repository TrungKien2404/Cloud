# Architecture Documentation - Text Diagram

## 1. SYSTEM ARCHITECTURE - DETAILED VIEW

```
╔════════════════════════════════════════════════════════════════════════════╗
║                    STOCK PRICE PREDICTION SYSTEM ARCHITECTURE              ║
╚════════════════════════════════════════════════════════════════════════════╝

┌────────────────────────────────────────────────────────────────────────────┐
│ TIER 1: DATA INGESTION (Ingestion Layer)                                  │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│         Yahoo Finance API                                                │
│              │                                                           │
│    ┌─────────┼─────────┐                                               │
│    ▼         ▼         ▼                                               │
│  ┌────┐   ┌────┐   ┌────┐                                             │
│  │AAPL│   │TSLA│   │MSFT│  ──→ Raw Data (Parquet Format)             │
│  └────┘   └────┘   └────┘                                             │
│                                                                            │
│  Module: ingestion/data_ingestion.py                                     │
│  Output: ./data/raw/{ticker}_raw.parquet                                │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ (Raw Data)
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ TIER 2: ETL PROCESSING (Processing Layer)                                │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────────────────────────────────────────────────┐           │
│  │                  DATA CLEANING                            │           │
│  │  • Handle Missing Values (Forward/Backward Fill)          │           │
│  │  • Remove Outliers (Z-score > 3)                         │           │
│  └──────────────────────────────────────────────────────────┘           │
│                            │                                             │
│                            ▼                                             │
│  ┌──────────────────────────────────────────────────────────┐           │
│  │            FEATURE ENGINEERING                            │           │
│  │                                                           │           │
│  │  Moving Averages:                                        │           │
│  │  ├─ MA10 = 10-day average                               │           │
│  │  ├─ MA20 = 20-day average                               │           │
│  │  └─ MA50 = 50-day average                               │           │
│  │                                                           │           │
│  │  Lag Features:                                           │           │
│  │  ├─ Lag1 = Previous day price                           │           │
│  │  ├─ Lag5 = 5-day ago price                              │           │
│  │  └─ Lag10 = 10-day ago price                            │           │
│  │                                                           │           │
│  │  Technical Indicators:                                   │           │
│  │  ├─ RSI(14) = Relative Strength Index                   │           │
│  │  ├─ Daily_Return = (Price_t - Price_t-1) / Price_t-1  │           │
│  │  └─ Volatility = 20-day std dev of returns              │           │
│  └──────────────────────────────────────────────────────────┘           │
│                            │                                             │
│                            ▼                                             │
│  ┌──────────────────────────────────────────────────────────┐           │
│  │          STANDARDIZATION & SCALING                        │           │
│  │  • StandardScaler: (x - mean) / std                      │           │
│  │  • Prevent feature magnitude bias                        │           │
│  └──────────────────────────────────────────────────────────┘           │
│                            │                                             │
│                            ▼                                             │
│  ┌──────────────────────────────────────────────────────────┐           │
│  │    TRAIN/VALIDATION/TEST SPLIT (Time-Series)              │           │
│  │                                                           │           │
│  │  Total: 100% of data                                     │           │
│  │  ├─ TRAIN: 70% (oldest data)                            │           │
│  │  ├─ VAL:   10% (middle data)                            │           │
│  │  └─ TEST:  20% (newest data)                            │           │
│  │                                                           │           │
│  │  Note: Time-series order maintained (no shuffling)       │           │
│  └──────────────────────────────────────────────────────────┘           │
│                                                                            │
│  Module: etl/etl_pipeline.py                                              │
│  Output: Processed features, train/val/test sets                         │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ (Processed Data)
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ TIER 3: MACHINE LEARNING (Model Layer)                                   │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌────────────────┐  ┌─────────────────┐  ┌──────────────────┐         │
│  │    MODEL 1     │  │    MODEL 2      │  │    MODEL 3       │         │
│  ├────────────────┤  ├─────────────────┤  ├──────────────────┤         │
│  │ Linear         │  │ Random Forest   │  │ Gradient        │         │
│  │ Regression     │  │ Regressor       │  │ Boosting        │         │
│  │                │  │                 │  │ Regressor       │         │
│  │ Pros:          │  │ Pros:           │  │ Pros:            │         │
│  │ • Fast         │  │ • Non-linear    │  │ • High accuracy  │         │
│  │ • Interpretable│  │ • Auto feature  │  │ • Sequential     │         │
│  │ • Baseline     │  │  selection      │  │  optimization    │         │
│  │                │  │ • Robust        │  │ • Handles        │         │
│  │ Cons:          │  │                 │  │  interactions    │         │
│  │ • Linear only  │  │ Cons:           │  │                  │         │
│  │ • Low accuracy │  │ • Slower train  │  │ Cons:            │         │
│  │                │  │ • Less optimal  │  │ • Slower train   │         │
│  │ RMSE: 0.0152   │  │ RMSE: 0.0125    │  │ RMSE: 0.0101 ✓  │         │
│  │ MAE:  0.0089   │  │ MAE:  0.0072    │  │ MAE:  0.0057 ✓  │         │
│  │ R²:   0.3456   │  │ R²:   0.5234    │  │ R²:   0.6789 ✓  │         │
│  └────────────────┘  └─────────────────┘  └──────────────────┘         │
│                            │                                             │
│                            ▼                                             │
│  ┌────────────────────────────────────────┐                            │
│  │ MODEL EVALUATION (Validation Set)      │                            │
│  │                                         │                            │
│  │ Metrics:                               │                            │
│  │ ├─ RMSE: Root Mean Squared Error      │                            │
│  │ ├─ MAE: Mean Absolute Error           │                            │
│  │ └─ R²: Coefficient of Determination   │                            │
│  │                                         │                            │
│  │ Selection: Lowest RMSE on Validation   │                            │
│  └────────────────────────────────────────┘                            │
│                            │                                             │
│                            ▼                                             │
│  ┌────────────────────────────────────────┐                            │
│  │ BEST MODEL SELECTION                   │                            │
│  │ ➜ Gradient Boosting                    │                            │
│  └────────────────────────────────────────┘                            │
│                            │                                             │
│                            ▼                                             │
│  ┌────────────────────────────────────────┐                            │
│  │ FINAL TEST SET EVALUATION              │                            │
│  │ (Unseen data - true performance)       │                            │
│  └────────────────────────────────────────┘                            │
│                                                                            │
│  Module: model/model_training.py                                          │
│  Output: Trained models (pickle files)                                   │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ (Trained Models)
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ TIER 4: PREDICTION & SERVING (API Layer)                                 │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────────────────────────────────────────────────┐           │
│  │              FASTAPI REST ENDPOINTS                       │           │
│  │                                                           │           │
│  │  ┌─────────────────────────────────────────────────┐    │           │
│  │  │ POST /predict                                    │    │           │
│  │  │ Input: {"ticker": "AAPL", "model": "GB"}       │    │           │
│  │  │ Output: {"predicted_return": 0.0234, ...}      │    │           │
│  │  └─────────────────────────────────────────────────┘    │           │
│  │                                                           │           │
│  │  ┌─────────────────────────────────────────────────┐    │           │
│  │  │ GET /data/{ticker}?days=30                      │    │           │
│  │  │ Output: Historical data + technical indicators  │    │           │
│  │  └─────────────────────────────────────────────────┘    │           │
│  │                                                           │           │
│  │  ┌─────────────────────────────────────────────────┐    │           │
│  │  │ GET /models                                     │    │           │
│  │  │ Output: Available models & their metrics       │    │           │
│  │  └─────────────────────────────────────────────────┘    │           │
│  │                                                           │           │
│  │  ┌─────────────────────────────────────────────────┐    │           │
│  │  │ GET /health                                     │    │           │
│  │  │ Output: {"status": "healthy", ...}             │    │           │
│  │  └─────────────────────────────────────────────────┘    │           │
│  │                                                           │           │
│  │  ┌─────────────────────────────────────────────────┐    │           │
│  │  │ GET /stats/{ticker}                             │    │           │
│  │  │ Output: High/Low/Average prices, volatility    │    │           │
│  │  └─────────────────────────────────────────────────┘    │           │
│  │                                                           │           │
│  └──────────────────────────────────────────────────────────┘           │
│                            │                                             │
│                            ▼                                             │
│  Module: api/api_service.py                                              │
│  Server: uvicorn (runs on localhost:8000)                               │
│  Features: CORS enabled, automatic docs (Swagger UI)                     │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                        ┌───────────┼───────────┐
                        ▼           ▼           ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ TIER 5: VISUALIZATION & DASHBOARDS                                       │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────────────────────────────────────────────────┐           │
│  │         STREAMLIT INTERACTIVE DASHBOARD                  │           │
│  │                                                           │           │
│  │  Views:                                                  │           │
│  │  1️⃣  Price Analysis                                      │           │
│  │      ├─ Historical closing prices                       │           │
│  │      ├─ Moving averages overlay                         │           │
│  │      └─ Volume analysis                                 │           │
│  │                                                           │           │
│  │  2️⃣  Predictions                                         │           │
│  │      ├─ Actual vs Predicted prices                      │           │
│  │      ├─ Prediction error trends                         │           │
│  │      └─ Error statistics                                │           │
│  │                                                           │           │
│  │  3️⃣  Technical Indicators                               │           │
│  │      ├─ RSI(14) with overbought/oversold zones         │           │
│  │      ├─ Volatility trends                               │           │
│  │      └─ Daily returns distribution                      │           │
│  │                                                           │           │
│  │  4️⃣  Multi-Stock Comparison                             │           │
│  │      ├─ Normalized price comparison                     │           │
│  │      ├─ Correlation heatmap                             │           │
│  │      └─ Performance metrics                             │           │
│  │                                                           │           │
│  │  5️⃣  Model Performance                                   │           │
│  │      ├─ Model comparison charts                         │           │
│  │      ├─ RMSE/MAE/R² metrics                             │           │
│  │      └─ Training statistics                             │           │
│  │                                                           │           │
│  │  6️⃣  Statistics Panel                                    │           │
│  │      ├─ Latest close price                              │           │
│  │      ├─ 52-week high/low                                │           │
│  │      ├─ Average daily return                            │           │
│  │      └─ Volatility metrics                              │           │
│  │                                                           │           │
│  └──────────────────────────────────────────────────────────┘           │
│                                                                            │
│  Module: dashboard/dashboard.py                                           │
│  Server: streamlit (runs on localhost:8501)                             │
│  Features: Real-time updates, interactive filters                        │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                        ┌───────────┼───────────┐
                        ▼           ▼           ▼
                   ┌────────┐  ┌──────────┐  ┌──────────┐
                   │ Desktop│  │ Mobile   │  │  Web     │
                   │ Browser│  │ Browser  │  │ Portal   │
                   └────────┘  └──────────┘  └──────────┘


┌────────────────────────────────────────────────────────────────────────────┐
│ TIER 6: DATABRICKS ORCHESTRATION                                          │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  Scheduler: Databricks Jobs                                              │
│                                                                            │
│  Job 1: Daily Ingestion & ETL                                            │
│  ├─ Schedule: 09:00 UTC (daily)                                          │
│  ├─ Notebook: 01_etl_pipeline.py                                         │
│  ├─ Output: Delta Lake tables                                            │
│  └─ Duration: ~5-10 minutes                                              │
│        │                                                                  │
│        ▼ (sends completion upstream)                                     │
│                                                                            │
│  Job 2: Model Training & Evaluation                                      │
│  ├─ Schedule: 11:00 UTC (daily, after Job 1)                           │
│  ├─ Notebook: 02_model_training.py                                       │
│  ├─ Dependencies: Job 1 completed                                        │
│  ├─ Output: Trained models + predictions                                │
│  └─ Duration: ~15-20 minutes                                             │
│        │                                                                  │
│        ▼ (triggers dashboard refresh)                                    │
│                                                                            │
│  Storage: Delta Lake                                                     │
│  ├─ bronze.stock_data_raw                                               │
│  ├─ bronze.stock_data_processed                                         │
│  ├─ bronze.stock_data_train/val/test                                    │
│  └─ bronze.stock_predictions                                            │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. DATA FLOW DIAGRAM

```
Input Data (Yahoo Finance)
         │
         ▼
    INGESTION
    ├─ fetch_stock_data()
    ├─ handle_api_errors()
    └─ save_to_parquet()
         │
         ▼
    Raw DataFrame
    (Date, Open, High, Low, Close, Volume, Ticker)
         │
         ▼
    ETL PROCESSING
    ├─ handle_missing_values()     (Forward/Backward Fill)
    ├─ remove_outliers()            (Z-score > 3)
    ├─ compute_moving_averages()   (MA10, MA20, MA50)
    ├─ compute_lag_features()      (Lag1, Lag5, Lag10)
    ├─ compute_rsi()                (RSI = 100 - 100/(1+RS))
    ├─ compute_daily_returns()     (% change)
    ├─ compute_volatility()        (Std dev)
    ├─ create_target_variable()    (Target)
    └─ standardize_features()      (StandardScaler)
         │
         ▼
    Processed DataFrame
    (40+ features including engineered features)
         │
    ┌────────────┴────────────┐
    │                         │
    ▼                         ▼
Train/Val/Test Split    Delta Lake Storage
    │
    ├─ X_train: (70% data) → ML Models
    ├─ X_val:   (10% data) → Model Evaluation
    └─ X_test:  (20% data) → Final Testing
         │
         ▼
    MODEL TRAINING
    ├─ Model 1: LinearRegression()
    ├─ Model 2: RandomForestRegressor(n_estimators=100)
    ├─ Model 3: GradientBoostingRegressor(n_estimators=100)
    │
    ├─ Train on X_train, y_train
    ├─ Evaluate on X_val, y_val
    └─ Test on X_test, y_test
         │
         ▼
    Model Metrics
    ├─ RMSE, MAE, R²
    ├─ Feature importance
    └─ Prediction residuals
         │
         ▼
    Best Model Selection ──→ Save Models (pickle)
         │
         ▼
    Predictions Table
    (Date, Ticker, Actual, Predicted, Error)
         │
    ┌────────────┴────────────┬────────────┐
    │                         │            │
    ▼                         ▼            ▼
  API Layer            Dashboard Layer    Batch Export
  (REST/FastAPI)      (Streamlit)         (CSV/Parquet)
    │                         │            │
    ▼                         ▼            ▼
REST Clients         Web Browsers      Reports/Archives
```

---

## 3. MODEL TRAINING PIPELINE FLOW

```
                    Input Features (X)
                    Target Variable (y)
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
        Train Set (70%)         Val Set (10%) + Test Set (20%)
                │                       │
                │                       │
        ┌───────┴───────┬───────┬───────┴──────┬──────┐
        │               │       │               │      │
        ▼               ▼       ▼               ▼      ▼
    LinearReg    RandomForest  GradBoost   ...evaluate...
        │               │       │               │      │
        │ fit()         │ fit() │ fit()        │      │
        │               │       │               │      │
        ▼               ▼       ▼               ▼      ▼
      Model1          Model2  Model3         Metrics  Metrics
        │               │       │               │      │
        │               │       │               │      │
        ├───────────────┼───────┤               │      │
        │               │       │               │      │
        ▼               ▼       ▼               ▼      ▼
        ├─ RMSE: 0.0152 ├─ RMSE: 0.0125 ├─ RMSE: 0.0101 ◄──── Best
        ├─ MAE:  0.0089 ├─ MAE:  0.0072 ├─ MAE:  0.0057
        ├─ R²:   0.3456 ├─ R²:   0.5234 ├─ R²:   0.6789
        │               │       │               │      │
        └───────────────┴───────┴───────────────┤      │
                                                │      │
                                    Save Best Model (pickle)
                                                │
                                    Final Evaluation on Test Set
                                                │
                                      Predictions Generated
```

---

## 4. DEPLOYMENT MODES

### Local Development Mode
```
Your Machine
├─ Python 3.10+
├─ Installed packages
├─ Jupyter/Notebooks
└─ Local data storage
    →→ Script execution
    →→ Debug/Test
```

### Cloud Databricks Mode
```
Databricks Workspace
├─ Cluster (Spark)
├─ DBFS (Storage)
├─ Jobs (Orchestration)
├─ Notebooks (Code)
└─ Delta Lake (Tables)
    →→ Distributed processing
    →→ Production-grade
    →→ Automated scheduling
```

### Hybrid Mode (Recommended)
```
Local Scripts      →→→  Databricks Notebooks
  (Test/Dev)              (Production)
     │
     └──→ API Service (Cloud VM / Cloud Run)
     └──→ Dashboard (Cloud Storage / Cloud Hosting)
```

---

## 5. TECHNOLOGY STACK

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Data Ingestion** | yfinance, pandas | Stock data collection |
| **Processing** | PySpark, pandas | Data transformation |
| **Storage** | Delta Lake, Parquet | Versioned data storage |
| **ML** | scikit-learn | Model training |
| **API** | FastAPI, uvicorn | REST endpoints |
| **Dashboard** | Streamlit, Plotly | Interactive visualization |
| **Orchestration** | Databricks Jobs | Workflow automation |
| **Cloud** | Databricks, Azure | Managed services |

---

## 6. DATA FLOW WITH VOLUMES

```
Input (Yahoo Finance) ─→ 5 years × 3 stocks × ~250 trading days
                        = ~3750 data points

Raw Data              ─→ 3750 records (8-10 columns)
                        ~500 KB uncompressed

After Feature Eng.    ─→ 3200 records (after removing NaN)
                        ~2.5 MB (40+ features)

Train/Val/Test Split  ─→ Train: 2240 records (70%)
                        Val:   320 records (10%)
                        Test:  640 records (20%)

Model Objects         ─→ ~2-5 MB each (pickle files)

Predictions           ─→ One prediction per day per model
                        = 3 predictions/day × 365 days × 3 stocks
                        = 3285 predictions/year

```

---

**Architecture Created By**: GitHub Copilot  
**Version**: 1.0.0  
**Status**: Production Ready ✅
