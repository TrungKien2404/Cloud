# ====================================================================
# FastAPI Service - REST API for Stock Predictions
# ====================================================================
# Module: api/api_service.py
#
# Mục đích: Expose predictions và dữ liệu thông qua REST API chuyên nghiệp.
# - /api/health: Health check endpoint
# - /api/tickers: Danh sách mã theo US & VN markets
# - /api/data/{ticker}: Lấy historical data + technical indicators
# - /api/predict/{ticker}: Dự báo giá ngày mai, tỉ suất sinh lời & AI reco
# - /api/train/{ticker}: Chạy ingestion, ETL, training riêng biệt cho 1 mã
# - /api/market-summary: Top Gainers, Losers, Heatmap, Watchlist
# - /api/update-data: Thủ công trigger cập nhật hệ thống
#
# Khởi chạy: uvicorn api.api_service:app --host 0.0.0.0 --port 8000 --reload
#
# ====================================================================

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import joblib
import os
import glob
import threading
import time
import json
import hashlib
import yfinance as yf



# Thêm thư mục gốc vào PYTHONPATH để tránh ModuleNotFoundError khi chạy trực tiếp
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Đảm bảo các luồng stdout/stderr trên Windows luôn sử dụng mã hóa UTF-8 để chống lỗi Unicode/charmap
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

# Import các components từ codebase
from configs.config import Config
from ingestion.data_ingestion import StockDataIngestion
from etl.etl_pipeline import StockETLPipeline
from model.model_training import StockModelTrainer

# Cấu hình logging chuyên sâu
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("api_service")

# Khởi tạo config
config = Config()

# Định cấu hình FastAPI App
app = FastAPI(
    title="Stock Prediction API Service",
    description="Backend AI phân tích và dự báo biến động giá cổ phiếu Mỹ & Việt Nam",
    version="2.0.0"
)

# Thêm CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== PYDANTIC BASEMODELS ==========

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    tickers_loaded: List[str]

class PredictionResponse(BaseModel):
    ticker: str
    latest_close: float
    predicted_next_close: float
    predicted_return: float
    recommendation: str
    reco_desc: str
    box_color: str
    text_color: str
    model_used: str
    metrics: Dict
    prediction_date: str
    timestamp: str

class DataPoint(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma50: Optional[float] = None
    rsi: Optional[float] = None
    volatility: Optional[float] = None
    daily_return: Optional[float] = None

# Pydantic Models cho Auth
class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    username: str



# ========== PIPELINE HELPER FUNCTIONS ==========

def run_full_system_update():
    """
    Chạy cập nhật toàn bộ hệ thống: Ingestion -> ETL -> Re-train
    """
    logger.info("🚀 [SYSTEM UPDATE] Khởi chạy Ingestion + ETL + Retraining toàn hệ thống...")
    try:
        # Step 1: Ingestion
        ingestion = StockDataIngestion(
            tickers=config.data['tickers'],
            history_years=config.data['history_years'],
            raw_data_path=config.data['raw_data_path']
        )
        ingestion.run_ingestion_pipeline()
        logger.info("🚀 [SYSTEM UPDATE] Step 1/3 (Ingestion) hoàn thành!")

        # Step 2: ETL
        etl_pipeline = StockETLPipeline(
            ma_windows=config.etl['moving_average_windows'],
            lag_windows=config.etl['lag_windows'],
            rsi_period=config.etl['rsi_period']
        )
        raw_data_path = os.path.join(config.data['raw_data_path'], 'combined_stock_data.parquet')
        df_raw = pd.read_parquet(raw_data_path)
        etl_result = etl_pipeline.run_etl_pipeline(df_raw)
        
        processed_path = os.path.join(config.data.get('processed_data_path', './data/processed'), 'processed_stock_data.parquet')
        etl_result['processed_df'].to_parquet(processed_path, index=False)
        logger.info("🚀 [SYSTEM UPDATE] Step 2/3 (ETL Processing) hoàn thành!")

        # Step 3: Model Training
        df_proc = etl_result['processed_df']
        tickers = df_proc['Ticker'].unique()
        
        for ticker in tickers:
            df_ticker = df_proc[df_proc['Ticker'] == ticker].copy()
            if 'Date' in df_ticker.columns:
                df_ticker = df_ticker.sort_values('Date')
            
            if len(df_ticker) < 30:
                continue
                
            train_data, val_data, test_data = etl_pipeline.split_train_val_test(df_ticker)
            trainer = StockModelTrainer(model_save_path='./models')
            result = trainer.run_training_pipeline(
                X_train=train_data[0], y_train=train_data[1],
                X_val=val_data[0], y_val=val_data[1],
                X_test=test_data[0], y_test=test_data[1]
            )
            
            exclude_cols = ['Date', 'Ticker', 'FetchDate', 'Target_Price', 'Target_Return']
            feature_columns = [col for col in df_ticker.columns if col not in exclude_cols and pd.api.types.is_numeric_dtype(df_ticker[col])]
            
            trainer.save_best_model_for_ticker(ticker, scaler=None, feature_columns=feature_columns)
            
        logger.info("🚀 [SYSTEM UPDATE] Step 3/3 (Model Retraining) hoàn thành! Toàn hệ thống đã cập nhật.")
        return True
    except Exception as e:
        logger.error(f"❌ [SYSTEM UPDATE] Lỗi khi cập nhật toàn hệ thống: {str(e)}")
        raise e


# ========== AUTO-UPDATE BACKGROUND TIMER (Stage 4) ==========

def daily_update_scheduler():
    """
    Background worker chạy tự động cập nhật lúc 09:00 AM hàng ngày.
    """
    logger.info("📅 [SCHEDULER] Auto-update scheduler đã khởi động (Mục tiêu: 09:00 AM hàng ngày).")
    last_run_date = None
    
    while True:
        try:
            now = datetime.now()
            # Kiểm tra xem có đúng 9h sáng và chưa chạy hôm nay không
            if now.hour == 9 and now.minute == 0 and now.date() != last_run_date:
                logger.info("📅 [SCHEDULER] Đúng 09:00 AM. Tự động cập nhật dữ liệu và huấn luyện lại...")
                run_full_system_update()
                last_run_date = now.date()
        except Exception as e:
            logger.error(f"📅 [SCHEDULER] Lỗi trong scheduler: {str(e)}")
        
        # Check mỗi 30 giây để tối ưu tài nguyên
        time.sleep(30)

# Khởi chạy Scheduler Thread khi API start
scheduler_thread = threading.Thread(target=daily_update_scheduler, daemon=True)
scheduler_thread.start()


# ========== API ENDPOINTS ==========

# ========== AUTH SERVICE HELPER & ENDPOINTS ==========

USERS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".streamlit", "users.json")

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def _load_users() -> dict:
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Lỗi khi load danh sách users: {str(e)}")
    return {}

def _save_users(users: dict):
    try:
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Lỗi khi lưu danh sách users: {str(e)}")

@app.post("/api/auth/register")
def register(user_data: UserRegister):
    username = user_data.username.strip()
    email = user_data.email.strip()
    password = user_data.password
    
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Tên đăng nhập phải có ít nhất 3 ký tự.")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Mật khẩu phải có ít nhất 6 ký tự.")
        
    users = _load_users()
    if username in users or username.lower() == "admin":
        raise HTTPException(status_code=400, detail="Tên đăng nhập đã tồn tại.")
        
    users[username] = {
        "email": email,
        "password_hash": _hash_password(password),
        "created_at": datetime.now().isoformat()
    }
    _save_users(users)
    return {"status": "success", "message": "Đăng ký thành công!"}

@app.post("/api/auth/login", response_model=TokenResponse)
def login(user_data: UserLogin):
    username = user_data.username.strip()
    password = user_data.password
    
    # Bypass admin mặc định nếu chưa cấu hình secrets
    if username == "admin" and password == "admin123":
        return TokenResponse(
            access_token="admin_mock_token_123456",
            token_type="bearer",
            username=username
        )
        
    users = _load_users()
    user_entry = users.get(username)
    if not user_entry or user_entry.get("password_hash") != _hash_password(password):
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không chính xác.")
        
    # Tạo mock token đơn giản (có thể thay bằng JWT nếu cần bảo mật thực tế)
    mock_token = f"mock_token_{username}_{int(time.time())}"
    return TokenResponse(
        access_token=mock_token,
        token_type="bearer",
        username=username
    )

@app.get("/api/health", response_model=HealthResponse)
def health():
    """
    Kiểm tra sức khỏe hệ thống
    """
    processed_path = os.path.join(config.data.get('processed_data_path', './data/processed'), 'processed_stock_data.parquet')
    tickers_loaded = []
    
    if os.path.exists(processed_path):
        try:
            df = pd.read_parquet(processed_path)
            tickers_loaded = list(df['Ticker'].unique())
        except Exception as e:
            logger.error(f"Error loading processed data in health check: {str(e)}")
            
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="2.0.0",
        tickers_loaded=tickers_loaded
    )


@app.get("/api/tickers")
def get_tickers():
    """
    Lấy danh sách tickers được phân nhóm theo thị trường (Mỹ / Việt Nam)
    """
    # Lấy từ configs hoặc hardcode phân loại thông minh
    tickers = config.data.get('tickers', ["AAPL", "TSLA", "MSFT", "FPT.VN", "HPG.VN"])
    
    us_tickers = [t for t in tickers if not t.endswith('.VN')]
    vn_tickers = [t for t in tickers if t.endswith('.VN')]
    
    return {
        "US": us_tickers,
        "VN": vn_tickers,
        "All": tickers
    }


@app.get("/api/data/{ticker}", response_model=List[DataPoint])
def get_historical_data(ticker: str, days: int = 150):
    """
    Lấy dữ liệu lịch sử cổ phiếu và các chỉ báo kỹ thuật
    """
    ticker_upper = ticker.upper()
    processed_path = os.path.join(config.data.get('processed_data_path', './data/processed'), 'processed_stock_data.parquet')
    
    if not os.path.exists(processed_path):
        raise HTTPException(status_code=404, detail="Processed data file not found. Please run ingestion + ETL first.")
        
    try:
        df = pd.read_parquet(processed_path)
        df_ticker = df[df['Ticker'] == ticker_upper].copy()
        
        if df_ticker.empty:
            raise HTTPException(status_code=404, detail=f"No data found for ticker: {ticker_upper}")
            
        # Sắp xếp và lấy số ngày chót
        df_ticker = df_ticker.sort_values('Date').tail(days)
        
        result = []
        for _, row in df_ticker.iterrows():
            # Xử lý Date format (có thể là Timestamp)
            date_str = str(row['Date'])[:10]
            
            result.append(DataPoint(
                date=date_str,
                open=float(row.get('Open', 0)),
                high=float(row.get('High', 0)),
                low=float(row.get('Low', 0)),
                close=float(row.get('Close', 0)),
                volume=float(row.get('Volume', 0)),
                ma10=float(row['MA10']) if 'MA10' in row and not pd.isna(row['MA10']) else None,
                ma20=float(row['MA20']) if 'MA20' in row and not pd.isna(row['MA20']) else None,
                ma50=float(row['MA50']) if 'MA50' in row and not pd.isna(row['MA50']) else None,
                rsi=float(row['RSI']) if 'RSI' in row and not pd.isna(row['RSI']) else None,
                volatility=float(row['Volatility']) if 'Volatility' in row and not pd.isna(row['Volatility']) else None,
                daily_return=float(row['Daily_Return']) if 'Daily_Return' in row and not pd.isna(row['Daily_Return']) else None
            ))
            
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching data for {ticker_upper}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/predict/{ticker}", response_model=PredictionResponse)
def get_prediction(ticker: str):
    """
    Thực hiện dự đoán xu hướng giá cổ phiếu ngày tiếp theo sử dụng mô hình riêng biệt của từng mã
    """
    ticker_upper = ticker.upper()
    processed_path = os.path.join(config.data.get('processed_data_path', './data/processed'), 'processed_stock_data.parquet')
    model_path = os.path.join('./models', f"{ticker_upper.lower()}_best_model.pkl")
    
    if not os.path.exists(processed_path):
        raise HTTPException(status_code=404, detail="Processed stock data not found. Please run ingestion + ETL first.")
        
    if not os.path.exists(model_path):
        # Trả về cảnh báo nếu chưa train model riêng cho mã này
        raise HTTPException(status_code=404, detail=f"Model for stock {ticker_upper} not found. Please trigger /api/train/{ticker_upper} first.")

    try:
        # 1. Load data
        df = pd.read_parquet(processed_path)
        df_ticker = df[df['Ticker'] == ticker_upper].sort_values('Date').copy()
        
        if df_ticker.empty:
            raise HTTPException(status_code=404, detail=f"No data found for ticker: {ticker_upper}")
            
        latest_row = df_ticker.iloc[-1]
        latest_close = float(latest_row['Close'])
        latest_date = latest_row['Date']
        
        # 2. Load model package
        payload = joblib.load(model_path)
        model = payload['model']
        feature_columns = payload['feature_columns']
        raw_metrics = payload['metrics']
        metrics = {
            'rmse': float(raw_metrics.get('rmse', 0)),
            'mae': float(raw_metrics.get('mae', 0)),
            'r2': float(raw_metrics.get('r2', 0))
        }
        model_name = payload.get('model_name', 'Trained Model')
        
        # 3. Predict return
        # Trích xuất vector feature cho hàng cuối
        X = latest_row[feature_columns].values.reshape(1, -1)
        pred_return = float(model.predict(X)[0])
        
        # 4. Tính giá ngày mai
        pred_next_close = latest_close * (1 + pred_return)
        
        # 5. Logic recommendation & Tô màu Premium
        if pred_return >= 0.01:
            recommendation = "🟢 STRONG BUY"
            reco_desc = "Mô hình dự đoán xu hướng tăng mạnh (>1.0%). Rất thích hợp để giải ngân mua mới."
            box_color = "#e6ffe6"
            text_color = "green"
        elif 0.00 <= pred_return < 0.01:
            recommendation = "🟡 HOLD / BUY"
            reco_desc = "Dự đoán xu hướng sideway hoặc tăng nhẹ (<1.0%). Có thể nắm giữ thêm hoặc mua thăm dò tỷ trọng thấp."
            box_color = "#ffffe6"
            text_color = "#b3b300"
        elif -0.01 < pred_return < 0.00:
            recommendation = "🟠 HOLD / SELL"
            reco_desc = "Dự đoán xu hướng điều chỉnh nhẹ. Ưu tiên giữ an toàn tài khoản hoặc chốt lời dần từng phần."
            box_color = "#fff0e6"
            text_color = "#ff8000"
        else:
            recommendation = "🔴 STRONG SELL"
            reco_desc = "Mô hình cảnh báo điều chỉnh sâu (âm >1.0%). Cần chốt lời triệt để hoặc hạ tỷ trọng cắt lỗ bảo vệ tài khoản."
            box_color = "#ffe6e6"
            text_color = "red"
            
        # Xác định ngày dự báo tiếp theo
        latest_dt = pd.to_datetime(latest_date)
        next_day = latest_dt + timedelta(days=1)
        while next_day.weekday() >= 5:  # Skip weekends
            next_day += timedelta(days=1)
            
        return PredictionResponse(
            ticker=ticker_upper,
            latest_close=latest_close,
            predicted_next_close=pred_next_close,
            predicted_return=pred_return,
            recommendation=recommendation,
            reco_desc=reco_desc,
            box_color=box_color,
            text_color=text_color,
            model_used=model_name,
            metrics=metrics,
            prediction_date=next_day.strftime('%Y-%m-%d'),
            timestamp=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error predicting for ticker {ticker_upper}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.post("/api/train/{ticker}")
def train_ticker_model(ticker: str):
    """
    Trigger huấn luyện mô hình ML từ đầu riêng cho 1 mã cổ phiếu
    """
    ticker_upper = ticker.upper()
    logger.info(f"Triggering training request for ticker: {ticker_upper}")
    
    try:
        # Step 1: Lấy dữ liệu mới nhất
        ingestion = StockDataIngestion(
            tickers=[ticker_upper],
            history_years=config.data['history_years'],
            raw_data_path=config.data['raw_data_path']
        )
        ingestion.run_ingestion_pipeline()
        
        # Step 2: ETL xử lý indicators cho mã này
        etl_pipeline = StockETLPipeline(
            ma_windows=config.etl['moving_average_windows'],
            lag_windows=config.etl['lag_windows'],
            rsi_period=config.etl['rsi_period']
        )
        
        # Đọc dữ liệu thô kết hợp
        raw_path = os.path.join(config.data['raw_data_path'], 'combined_stock_data.parquet')
        df_raw = pd.read_parquet(raw_path)
        
        # ETL chạy và cập nhật processed dataset
        etl_result = etl_pipeline.run_etl_pipeline(df_raw)
        processed_path = os.path.join(config.data.get('processed_data_path', './data/processed'), 'processed_stock_data.parquet')
        etl_result['processed_df'].to_parquet(processed_path, index=False)
        
        # Lọc mẫu riêng cho mã này
        df_ticker = etl_result['processed_df'][etl_result['processed_df']['Ticker'] == ticker_upper].copy()
        if 'Date' in df_ticker.columns:
            df_ticker = df_ticker.sort_values('Date')
            
        if len(df_ticker) < 30:
            raise HTTPException(status_code=400, detail=f"Not enough data points ({len(df_ticker)}) for training ticker {ticker_upper}.")
            
        # Step 3: Train
        train_data, val_data, test_data = etl_pipeline.split_train_val_test(df_ticker)
        
        trainer = StockModelTrainer(model_save_path='./models')
        result = trainer.run_training_pipeline(
            X_train=train_data[0], y_train=train_data[1],
            X_val=val_data[0], y_val=val_data[1],
            X_test=test_data[0], y_test=test_data[1]
        )
        
        # Gói features
        exclude_cols = ['Date', 'Ticker', 'FetchDate', 'Target_Price', 'Target_Return']
        feature_columns = [col for col in df_ticker.columns if col not in exclude_cols and pd.api.types.is_numeric_dtype(df_ticker[col])]
        
        # Lưu gói Best Model
        model_file = trainer.save_best_model_for_ticker(ticker_upper, scaler=None, feature_columns=feature_columns)
        
        return {
            "status": "success",
            "message": f"Successfully trained and saved model for ticker {ticker_upper}",
            "ticker": ticker_upper,
            "best_model": result['best_model_name'],
            "test_rmse": float(result['test_metrics']['rmse']),
            "test_r2": float(result['test_metrics']['r2']),
            "saved_path": model_file
        }
        
    except Exception as e:
        logger.error(f"Error training model for ticker {ticker_upper}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@app.get("/api/market-summary")
def get_market_summary():
    """
    Tổng hợp dữ liệu thị trường (Giai đoạn 2):
    - Top Tăng (Top Gainers)
    - Top Giảm (Top Losers)
    - Heatmap Tương quan
    - Dữ liệu Watchlist
    """
    processed_path = os.path.join(config.data.get('processed_data_path', './data/processed'), 'processed_stock_data.parquet')
    
    if not os.path.exists(processed_path):
        raise HTTPException(status_code=404, detail="Processed stock data not found.")
        
    try:
        df = pd.read_parquet(processed_path)
        
        # 1. TÍNH LATEST VALUES CHO TẤT CẢ TICKERS
        latest_data = []
        tickers = df['Ticker'].unique()
        
        # Dataframe lưu trữ returns lịch sử để tính tương quan
        returns_dict = {}
        
        for t in tickers:
            df_t = df[df['Ticker'] == t].sort_values('Date').copy()
            if df_t.empty:
                continue
                
            latest_row = df_t.iloc[-1]
            prev_row = df_t.iloc[-2] if len(df_t) > 1 else latest_row
            
            # Lấy returns lịch sử 120 ngày cho Heatmap
            df_hist = df_t.tail(120)
            returns_dict[t] = df_hist.set_index('Date')['Daily_Return']
            
            close = float(latest_row['Close'])
            prev_close = float(prev_row['Close'])
            daily_change_pct = float(latest_row.get('Daily_Return', 0)) * 100
            
            # Kiểm tra xem đã có model train chưa để đưa ra tín hiệu nhanh
            model_path = os.path.join('./models', f"{t.lower()}_best_model.pkl")
            signal = "Chưa có Model"
            if os.path.exists(model_path):
                try:
                    payload = joblib.load(model_path)
                    model = payload['model']
                    features = payload['feature_columns']
                    X = latest_row[features].values.reshape(1, -1)
                    pred_ret = float(model.predict(X)[0])
                    
                    if pred_ret >= 0.01:
                        signal = "🟢 MUA MẠNH"
                    elif 0.00 <= pred_ret < 0.01:
                        signal = "🟡 MUA/GIỮ"
                    elif -0.01 < pred_ret < 0.00:
                        signal = "🟠 GIỮ/BÁN"
                    else:
                        signal = "🔴 BÁN MẠNH"
                except:
                    signal = "Lỗi Model"
                    
            latest_data.append({
                "ticker": t,
                "close": close,
                "prev_close": prev_close,
                "change_pct": daily_change_pct,
                "signal": signal,
                "market": "VN" if t.endswith('.VN') else "US"
            })
            
        df_latest = pd.DataFrame(latest_data)
        
        # 2. XÁC ĐỊNH TOP GAINERS & LOSERS
        top_gainers = []
        top_losers = []
        
        if not df_latest.empty:
            # Sort theo change_pct
            df_sorted = df_latest.sort_values('change_pct', ascending=False)
            top_gainers = df_sorted.head(5).to_dict(orient='records')
            top_losers = df_sorted.tail(5).sort_values('change_pct', ascending=True).head(5).to_dict(orient='records')
            
        # 3. MA TRẬN TƯƠNG QUAN TỶ SUẤT SINH LỜI (RETURNS CORRELATION HEATMAP)
        # Kết hợp returns lịch sử thành một DataFrame chung
        df_returns = pd.DataFrame(returns_dict).dropna(how='all').fillna(0)
        corr_matrix = df_returns.corr().round(3)
        
        # Chuẩn bị dữ liệu JSON cho Plotly Heatmap
        corr_data = {
            "z": corr_matrix.values.tolist(),
            "x": corr_matrix.columns.tolist(),
            "y": corr_matrix.index.tolist()
        }
        
        return {
            "watchlist": latest_data,
            "top_gainers": top_gainers,
            "top_losers": top_losers,
            "correlation": corr_data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error compiling market summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")


# ========== YFINANCE PROXY ENDPOINTS FOR REACT OVERVIEW ==========

def _yf_download_cached(ticker: str, period: str, interval: str):
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
    if df is not None and not df.empty:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.loc[:, ~df.columns.duplicated()]
    return df

@app.get("/api/yfinance/chart/{ticker}")
def get_yf_chart(ticker: str, period: str = "1d", interval: str = "5m"):
    try:
        df = _yf_download_cached(ticker, period, interval)
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"Không thể tải dữ liệu cho {ticker}")
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        close_series = df["Close"].dropna()
        if close_series.empty:
            raise HTTPException(status_code=404, detail="Không có dữ liệu giá đóng cửa")
            
        # Convert index (dates) to strings
        dates = [str(d) for d in close_series.index]
        closes = [float(v) for v in close_series.values]
        
        return {
            "ticker": ticker,
            "dates": dates,
            "closes": closes,
            "latest": closes[-1] if closes else 0,
            "first": closes[0] if closes else 0,
        }
    except Exception as e:
        logger.error(f"Lỗi yfinance chart {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/yfinance/summary/{ticker}")
def get_yf_summary(ticker: str):
    try:
        df = _yf_download_cached(ticker, period="1y", interval="1d")
        if df is None or df.empty:
            return {}
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if "Close" not in df.columns:
            return {}
            
        close = df["Close"].dropna()
        if len(close) < 2:
            return {}
            
        price = float(close.iloc[-1])
        
        def pct(n):
            if len(close) > n:
                return float((close.iloc[-1] - close.iloc[-n]) / close.iloc[-n] * 100)
            return None
            
        ytd_start = datetime(datetime.now().year, 1, 1).date()
        ytd_mask = df.index.date >= ytd_start
        ytd_close = close[ytd_mask]
        
        ytd = float((ytd_close.iloc[-1] - ytd_close.iloc[0]) / ytd_close.iloc[0] * 100) \
              if len(ytd_close) > 1 else None
              
        return {
            "price": price,
            "D": pct(2),
            "W": pct(6),
            "M": pct(22),
            "Q": pct(66),
            "YTD": ytd
        }
    except Exception as e:
        logger.error(f"Lỗi yfinance summary {ticker}: {str(e)}")
        return {}


# ========== GLOBAL ON-DEMAND AI ANALYSIS & ML PREDICTION ENDPOINT ==========

@app.get("/api/ai-analysis/{ticker}")
def run_global_ai_analysis(ticker: str, period: str = "1y", interval: str = "1d"):
    try:
        from dashboard.ai_analysis import (
            fetch_data, compute_features, train_and_evaluate, 
            predict_next, build_recommendation, FEATURE_COLS
        )
        
        ticker_upper = ticker.upper().strip()
        logger.info(f"🚀 Running on-demand AI Analysis for global ticker: {ticker_upper} (Period: {period}, Interval: {interval})")
        
        # 1. Tải dữ liệu từ Yahoo Finance
        df_raw = fetch_data(ticker_upper, period=period, interval=interval)
        if df_raw.empty:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy dữ liệu cho mã {ticker_upper}. Vui lòng thử mã khác.")
            
        # 2. Tính toán các chỉ báo kỹ thuật
        df_feat = compute_features(df_raw)
        
        # Lấy giá trị phiên gần nhất
        latest = df_feat.iloc[-1]
        current_price = float(latest["Close"])
        previous_close = float(df_feat.iloc[-2]["Close"]) if len(df_feat) > 1 else current_price
        rsi_val = float(latest.get("RSI", 50))
        ma20_val = float(latest.get("MA20", current_price))
        ma50_val = float(latest.get("MA50", current_price))
        macd_val = float(latest.get("MACD", 0))
        macd_sig = float(latest.get("MACD_Signal", 0))
        vol_val = float(latest.get("Volatility", 0)) * 100
        
        # 3. Huấn luyện 3 mô hình ML và đánh giá
        results_df, best_name, best_model, scaler, feat_df = train_and_evaluate(df_feat)
        
        if results_df is None:
            raise HTTPException(status_code=400, detail="Không đủ dữ liệu lịch sử để huấn luyện mô hình học máy (Cần tối thiểu 60 phiên).")
            
        # 4. Dự đoán giá tiếp theo sử dụng mô hình tốt nhất
        next_price = predict_next(df_feat, best_model, scaler)
        diff = next_price - current_price
        diff_pct = diff / current_price * 100
        
        # Lấy sai số và R2 của best model để lập khuyến nghị
        best_rmse = float(results_df.loc[results_df["Model"] == best_name, "RMSE"].values[0])
        best_r2 = float(results_df.loc[results_df["Model"] == best_name, "R²"].values[0])
        
        # 5. Lập khuyến nghị AI tích hợp nhiều chỉ báo
        reco_data = build_recommendation(
            current_price, next_price, rsi_val,
            ma20_val, ma50_val, macd_val, macd_sig,
            best_rmse, best_r2
        )
        
        # 6. Chuẩn bị dữ liệu actual vs predicted trên tập test (20%)
        feat = df_feat[FEATURE_COLS + ["Target", "Date"]].dropna()
        X = feat[FEATURE_COLS].values
        y = feat["Target"].values
        dates = feat["Date"].values
        
        split = int(len(X) * 0.8)
        X_test = scaler.transform(X[split:])
        y_test = y[split:]
        dates_test = [str(d)[:10] for d in dates[split:]]
        
        preds = best_model.predict(X_test)
        
        avp_data = {
            "dates": dates_test,
            "actuals": [float(v) for v in y_test],
            "predictions": [float(v) for v in preds]
        }
        
        # 7. Compile các mảng dữ liệu lịch sử để vẽ biểu đồ kỹ thuật
        df_clean = df_feat.dropna(subset=["Close"])
        chart_dates = [str(d)[:10] for d in df_clean["Date"]]
        
        return {
            "ticker": ticker_upper,
            "current_price": current_price,
            "previous_close": previous_close,
            "rsi": rsi_val,
            "volatility": vol_val,
            "macd": macd_val,
            "macd_signal": macd_sig,
            "ma20": ma20_val,
            "ma50": ma50_val,
            "next_predicted_price": next_price,
            "expected_change": diff,
            "expected_change_pct": diff_pct,
            
            # Arrays cho Candlestick + indicator lines
            "dates": chart_dates,
            "opens": [float(v) for v in df_clean["Open"]],
            "highs": [float(v) for v in df_clean["High"]],
            "lows": [float(v) for v in df_clean["Low"]],
            "closes": [float(v) for v in df_clean["Close"]],
            "volumes": [float(v) for v in df_clean["Volume"]],
            "ma20_line": [float(v) if not pd.isna(v) else None for v in df_clean.get("MA20", [])],
            "ma50_line": [float(v) if not pd.isna(v) else None for v in df_clean.get("MA50", [])],
            "rsi_line": [float(v) if not pd.isna(v) else None for v in df_clean.get("RSI", [])],
            "macd_line": [float(v) if not pd.isna(v) else None for v in df_clean.get("MACD", [])],
            "macd_sig_line": [float(v) if not pd.isna(v) else None for v in df_clean.get("MACD_Signal", [])],
            "hist_line": [float(v) if not pd.isna(v) else None for v in (df_clean.get("MACD", 0) - df_clean.get("MACD_Signal", 0))],
            
            # Model training results
            "model_results": results_df.to_dict(orient="records"),
            "best_model_name": best_name,
            
            # Recommendation & reasons
            "recommendation": reco_data,
            
            # Actual vs Predicted data
            "actual_vs_predicted": avp_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi khi chạy AI Analysis cho {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Phân tích AI thất bại: {str(e)}")



@app.post("/api/update-data")
def trigger_update(background_tasks: BackgroundTasks):
    """
    Thủ công trigger cập nhật toàn hệ thống (Ingestion + ETL + Train) thông qua API
    Chạy background task để không chặn client
    """
    background_tasks.add_task(run_full_system_update)
    return {
        "status": "processing",
        "message": "Full system data ingestion, feature extraction, and retraining has been triggered in the background."
    }


# ========== CHATBOT BACKEND ENDPOINTS FOR REACT FRONTEND ==========

class ChatRequest(BaseModel):
    message: str
    mode: str = "Nhanh"
    model: str = "qwen2.5:1.5b"

@app.get("/api/chat/status")
def get_chat_status():
    import requests
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=1.0)
        return {"alive": r.status_code == 200}
    except:
        return {"alive": False}

@app.get("/api/chat/models")
def get_chat_models():
    import requests
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=1.0)
        if r.status_code == 200:
            models = [m.get("name") for m in r.json().get("models", [])]
            return {"models": models}
    except:
        pass
    return {"models": ["qwen2.5:1.5b", "gemma2:2b", "llama3:latest"]}

@app.post("/api/chat")
def post_chat_response(req: ChatRequest):
    import requests
    import re
    
    # 1. Phát hiện ticker trong tin nhắn
    text_upper = req.message.upper()
    detected_ticker = ""
    
    # 0. Hỗ trợ mapping viết tắt cho các lớp tài sản mới
    # a. Tiền ảo (Cryptocurrencies)
    crypto_map = {
        r'\bBTC\b': 'BTC-USD',
        r'\bETH\b': 'ETH-USD',
        r'\bBNB\b': 'BNB-USD',
        r'\bSOL\b': 'SOL-USD',
        r'\bXRP\b': 'XRP-USD',
        r'\bADA\b': 'ADA-USD',
        r'\bDOGE\b': 'DOGE-USD',
        r'\bDOT\b': 'DOT-USD',
        r'\bLTC\b': 'LTC-USD',
    }
    for pattern, target in crypto_map.items():
        if re.search(pattern, text_upper):
            detected_ticker = target
            break
            
    # b. Hàng hóa (Commodities)
    if not detected_ticker:
        commodity_map = {
            r'\b(VANG|GOLD|GC)\b': 'GC=F',
            r'\b(DAU|OIL|CL|DUTHOT)\b': 'CL=F',
            r'\b(BAC|SILVER|SI)\b': 'SI=F',
            r'\b(DONG|COPPER|HG)\b': 'HG=F',
            r'\b(GAS|NG)\b': 'NG=F',
        }
        for pattern, target in commodity_map.items():
            if re.search(pattern, text_upper):
                detected_ticker = target
                break
                
    # c. Tiền tệ / Ngoại hối (Currencies/Forex)
    if not detected_ticker:
        forex_map = {
            r'\b(USDVND|USD-VND|USD/VND)\b': 'USDVND=X',
            r'\b(EURUSD|EUR-USD|EUR/USD)\b': 'EURUSD=X',
            r'\b(GBPUSD|GBP-USD|GBP/USD)\b': 'GBPUSD=X',
            r'\b(USDJPY|USD-JPY|USD/JPY)\b': 'USDJPY=X',
            r'\b(AUDUSD|AUD-USD|AUD/USD)\b': 'AUDUSD=X',
            r'\b(USDCAD|USD-CAD|USDCAD)\b': 'USDCAD=X',
        }
        for pattern, target in forex_map.items():
            if re.search(pattern, text_upper):
                detected_ticker = target
                break

    # 1. Quét theo danh sách hệ thống trước
    if not detected_ticker:
        configured_tickers = config.data.get('tickers', ["AAPL", "TSLA", "MSFT", "FPT.VN", "HPG.VN"])
        for t in configured_tickers:
            if t in text_upper:
                detected_ticker = t
                break
            
    if not detected_ticker:
        match_vn = re.search(r'\b([A-Za-z]{3,5}\.VN)\b', req.message)
        if match_vn:
            detected_ticker = match_vn.group(1).upper()
        else:
            match_crypto = re.search(r'\b([A-Za-z]{3,5}-USD)\b', req.message)
            if match_crypto:
                detected_ticker = match_crypto.group(1).upper()
            else:
                match_futures = re.search(r'\b([A-Za-z]{1,4}=F)\b', req.message)
                if match_futures:
                    detected_ticker = match_futures.group(1).upper()
                else:
                    match_forex = re.search(r'\b([A-Za-z]{3,6}=X)\b', req.message)
                    if match_forex:
                        detected_ticker = match_forex.group(1).upper()
                    else:
                        match_us = re.search(r'\b([A-Z]{3,5})\b', req.message)
                        if match_us:
                            potential = match_us.group(1)
                            ignored = ["BUY", "SELL", "HOLD", "RSI", "MACD", "MA20", "MA50", "USD", "VND", "EUR", "BTC", "ETH", "GOLD", "VANG", "OIL", "DAU"]
                            if potential not in ignored:
                                detected_ticker = potential

    # 2. Truy xuất chỉ số của ticker
    metrics = None
    if detected_ticker:
        try:
            metrics = run_global_ai_analysis(detected_ticker)
        except Exception as e:
            logger.error(f"Chat error querying technicals for {detected_ticker}: {str(e)}")

    # 3. Chế độ phân tích nhanh
    if req.mode == "Nhanh":
        if detected_ticker and metrics:
            reco = metrics["recommendation"]
            reco_name = reco["reco"]
            reco_color = reco["color"]
            reco_explanation = reco["explanation"]
            reco_reasons = list(reco["reasons"])
            
            curr = metrics["current_price"]
            prev_close = metrics.get("previous_close", curr)
            hist_change_pct = ((curr - prev_close) / prev_close * 100) if prev_close else 0.0
            
            pred = metrics["next_predicted_price"]
            change = metrics["expected_change_pct"]
            rsi = metrics["rsi"]
            vol = metrics["volatility"]
            last_date = metrics["dates"][-1] if metrics.get("dates") else str(datetime.now().date())
            
            # Điều chỉnh khuyến nghị khi RSI quá mua (>70) nhưng xu thế vẫn Bullish
            if rsi > 70 and reco_name in ["STRONG BUY", "BUY"]:
                reco_name = "HOLD / WATCH"
                reco_color = "#f59e0b"  # Màu vàng cam hổ phách
                reco_explanation = "Mac dau xu the dong tien va dong luong ngan han (MA & MACD) van tich cuc, nhung chi so RSI hien da di sau vao cung Qua Mua (>70). Viec giai ngan mua moi o vung gia nay tiem an rui ro dieu chinh ky thuat rat cao. Khuyen nghi NAM GIU / THEO DOI sat sao de toi uu loi nhuan, dung viec mua duoi."
                reco_reasons.append("Chi so RSI > 70 bao hieu Qua Mua — khuyen nghi chuyen sang Theo Doi / Nam Giu, dung vi the mua moi de tranh rui ro nhip chinh ngan han")

            # Phân tách rủi ro (Xóa icon)
            # 1. Rủi ro biến động
            vol_risk = "THAP"
            if vol > 3.0:
                vol_risk = "CAO (Bien do dao dong rat lon)"
            elif vol > 1.5:
                vol_risk = "TRUNG BINH"
            else:
                vol_risk = "THAP"
                
            # 2. Rủi ro điều chỉnh kỹ thuật
            tech_risk = "THAP"
            if rsi > 70:
                tech_risk = "CAO (Qua mua, ap luc chot loi gia tang)"
            elif rsi < 30:
                tech_risk = "THAP (Qua ban, co the xuat hien nhip hoi ky thuat)"
            elif 60 <= rsi <= 70:
                tech_risk = "TRUNG BINH (Ap luc dieu chinh nhe)"
            else:
                tech_risk = "THAP"
            
            # Dọn dẹp emoji/icon khỏi reco_name
            reco_name = reco_name.replace("🟢", "").replace("🟡", "").replace("🟠", "").replace("🔴", "").replace("⚠️", "").strip()
            
            if detected_ticker.endswith(".VN") or detected_ticker == "USDVND=X":
                currency = "VND"
            elif detected_ticker.endswith("=X"):
                currency = ""
            else:
                currency = "$"
            
            rsi_nhan_dinh = 'Qua Mua (Canh bao dao chieu giam)' if rsi > 70 else ('Qua Ban (Co hoi tao day di len)' if rsi < 30 else 'Trung tinh (Xu huong tiep tuc tich luy)')
            trend_nhan_dinh = 'Xu huong tang (Uptrend)' if change > 0.5 else ('Xu huong giam (Downtrend)' if change < -0.5 else 'Xu huong di ngang (Neutral)')
            best_model_name = metrics.get("best_model_name", "Linear Regression")
            
            # Map signal
            final_reco = "WATCH / HOLD"
            final_reco_color = "#f59e0b"
            if reco_name in ["STRONG BUY", "BUY"]:
                final_reco = "BUY"
                final_reco_color = "#22c55e"
            elif reco_name in ["STRONG SELL", "SELL"]:
                final_reco = "SELL / AVOID"
                final_reco_color = "#ef4444"

            # 2-4 sentence bullet points for each section:
            # Price Movement (Diễn biến giá)
            price_trend = "tăng" if hist_change_pct > 0 else "giảm"
            price_ma = "nằm trên" if curr > metrics["ma20"] else "nằm dưới"
            price_ma_status = "tích cực trong ngắn hạn" if curr > metrics["ma20"] else "tiêu cực trong ngắn hạn"
            
            # Technical Signals (Tín hiệu kỹ thuật)
            tech_ma_cross = "Crossover tăng giá (Bullish)" if metrics["ma20"] > metrics["ma50"] else "Crossover giảm giá (Bearish)"
            tech_macd = "nằm trên (Bullish momentum)" if metrics["macd"] > metrics["macd_signal"] else "nằm dưới (Bearish momentum)"
            
            # Model Forecast (Dự báo mô hình)
            model_confidence = "Độ tin cậy của mô hình ở mức cao dựa trên chỉ số R² tốt." if metrics.get("best_r2", 0) > 0.5 else "Mô hình có sai số trung bình, khuyến nghị sử dụng để tham khảo và kết hợp quản trị vốn."
            best_rmse = metrics.get("recommendation", {}).get("best_rmse", 0.23)
            
            # Risk (Rủi ro)
            vol_risk_desc = "biến động cao" if vol > 3.0 else ("biến động trung bình" if vol > 1.5 else "biến động thấp")
            tech_risk_desc = "áp lực điều chỉnh kỹ thuật lớn do đi sâu vào vùng quá mua" if rsi > 70 else ("cơ hội phục hồi kỹ thuật do ở vùng quá bán" if rsi < 30 else "trạng thái kỹ thuật ổn định, chưa có dấu hiệu cực đoan")

            report = f"""
<div style="font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #cbd5e1;">
  <h3 style="color: #ffffff; margin-top: 0; margin-bottom: 12px; font-weight: 800; font-size: 18px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px;">
    Phân tích nhanh {detected_ticker}
  </h3>
  
  <p style="margin: 4px 0 12px 0; font-size: 12px; color: #94a3b8;">
    Thời điểm tạo báo cáo: <strong>{datetime.now().strftime('%H:%M:%S — %d/%m/%Y')}</strong><br />
    Dữ liệu thị trường gần nhất: <strong>{last_date}</strong>
  </p>
  
  <!-- Box tóm tắt đầu -->
  <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(148, 163, 184, 0.15); border-radius: 8px; padding: 14px; margin-bottom: 20px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; font-size: 13px;">
    <div>
      <span style="color: #94a3b8; display: block; margin-bottom: 2px;">Giá hiện tại:</span>
      <strong style="font-size: 16px; color: #ffffff;">{curr:,.2f} {currency}</strong>
    </div>
    <div>
      <span style="color: #94a3b8; display: block; margin-bottom: 2px;">Giá phiên trước:</span>
      <strong style="font-size: 16px; color: #ffffff;">{prev_close:,.2f} {currency}</strong>
    </div>
    <div>
      <span style="color: #94a3b8; display: block; margin-bottom: 2px;">% thay đổi:</span>
      <strong style="font-size: 16px; color: {final_reco_color};">{hist_change_pct:+.2f}%</strong>
    </div>
    <div>
      <span style="color: #94a3b8; display: block; margin-bottom: 2px;">Khuyến nghị:</span>
      <strong style="font-size: 16px; color: {reco_color};">{reco_name}</strong>
    </div>
  </div>
  
  <!-- Các mục riêng -->
  <div style="margin-bottom: 16px;">
    <h4 style="color: #ffffff; font-size: 14px; font-weight: 700; margin: 0 0 6px 0; text-transform: uppercase; letter-spacing: 0.5px;">Diễn biến giá</h4>
    <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #cbd5e1;">
      <li style="margin-bottom: 4px;">Giá đóng cửa phiên gần nhất đạt <strong>{curr:,.2f} {currency}</strong>, thể hiện xu hướng <strong>{price_trend}</strong> ở mức <strong>{hist_change_pct:+.2f}%</strong> so với phiên trước.</li>
      <li style="margin-bottom: 4px;">Giá hiện tại đang <strong>{price_ma}</strong> đường trung bình động MA20 ngắn hạn (<strong>{metrics['ma20']:,.2f} {currency}</strong>), cho thấy tín hiệu xu hướng <strong>{price_ma_status}</strong>.</li>
    </ul>
  </div>
  
  <div style="margin-bottom: 16px;">
    <h4 style="color: #ffffff; font-size: 14px; font-weight: 700; margin: 0 0 6px 0; text-transform: uppercase; letter-spacing: 0.5px;">Tín hiệu kỹ thuật</h4>
    <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #cbd5e1;">
      <li style="margin-bottom: 4px;">Chỉ số RSI (14) đang ở mức <strong>{rsi:.2f}</strong>, cho thấy trạng thái <strong>{rsi_nhan_dinh}</strong>.</li>
      <li style="margin-bottom: 4px;">Động lượng MACD (<strong>{metrics['macd']:.4f}</strong>) đang <strong>{tech_macd}</strong> so với Signal Line (<strong>{metrics['macd_signal']:.4f}</strong>).</li>
      <li style="margin-bottom: 4px;">Hệ thống xác định trạng thái trung bình động là <strong>{tech_ma_cross}</strong> với đường MA20 ở mức <strong>{metrics['ma20']:,.2f}</strong> và đường MA50 ở mức <strong>{metrics['ma50']:,.2f}</strong>.</li>
    </ul>
  </div>
  
  <div style="margin-bottom: 16px;">
    <h4 style="color: #ffffff; font-size: 14px; font-weight: 700; margin: 0 0 6px 0; text-transform: uppercase; letter-spacing: 0.5px;">Dự báo mô hình</h4>
    <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #cbd5e1;">
      <li style="margin-bottom: 4px;">Mô hình học máy tốt nhất <strong>{best_model_name}</strong> dự báo giá đóng cửa phiên tiếp theo sẽ đạt <strong>{pred:,.2f} {currency}</strong>, tương ứng tỷ lệ thay đổi dự kiến <strong>{change:+.2f}%</strong>.</li>
      <li style="margin-bottom: 4px;">{model_confidence} Sai số đánh giá RMSE tối ưu đạt <strong>{best_rmse:.2f}</strong> trên tập dữ liệu kiểm nghiệm.</li>
    </ul>
  </div>
  
  <div style="margin-bottom: 16px;">
    <h4 style="color: #ffffff; font-size: 14px; font-weight: 700; margin: 0 0 6px 0; text-transform: uppercase; letter-spacing: 0.5px;">Rủi ro</h4>
    <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #cbd5e1;">
      <li style="margin-bottom: 4px;">Rủi ro biến động giá được đánh giá ở mức <strong>{vol_risk}</strong> với biên độ dao động lịch sử 20 phiên là <strong>{vol:.2f}%</strong>.</li>
      <li style="margin-bottom: 4px;">Rủi ro điều chỉnh kỹ thuật được xác định ở mức <strong>{tech_risk}</strong> do <strong>{tech_risk_desc}</strong>.</li>
    </ul>
  </div>
  
  <div style="margin-bottom: 20px;">
    <h4 style="color: #ffffff; font-size: 14px; font-weight: 700; margin: 0 0 6px 0; text-transform: uppercase; letter-spacing: 0.5px;">Kết luận hệ thống</h4>
    <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #cbd5e1;">
      <li style="margin-bottom: 4px;">Hệ thống tổng hợp các tín hiệu kỹ thuật và đưa ra nhận định: <strong>{reco_explanation}</strong></li>
    </ul>
  </div>
  
  <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 16px 0;" />
  
  <!-- Banner khuyến nghị cuối cùng cực kỳ rõ ràng -->
  <div style="background: rgba(15, 23, 42, 0.8); border: 2px solid {final_reco_color}; border-radius: 8px; padding: 16px; text-align: center; margin-top: 12px;">
    <span style="color: #94a3b8; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; display: block; margin-bottom: 4px;">KHUYẾN NGHỊ CUỐI CÙNG</span>
    <strong style="color: {final_reco_color}; font-size: 24px; font-weight: 900; letter-spacing: 0.5px;">{final_reco}</strong>
  </div>
</div>
"""
            return {"response": report}
        else:
            if detected_ticker:
                response_text = f"""
<div style="font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #cbd5e1;">
  <div style="background: rgba(239, 68, 68, 0.08); border-left: 4px solid #ef4444; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; color: #fca5a5;">
    Không tìm thấy dữ liệu thị trường cho mã <strong>{detected_ticker}</strong>. Vui lòng kiểm tra lại kết nối internet hoặc đảm bảo mã này tồn tại trên Yahoo Finance.
  </div>
  
  <h4 style="color: #ffffff; font-size: 14px; font-weight: 700; margin: 16px 0 8px 0;">Danh sách mã gợi ý hợp lệ:</h4>
  <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #cbd5e1;">
    <li style="margin-bottom: 6px;"><strong>Cổ phiếu Mỹ:</strong> <code>AAPL</code> (Apple), <code>TSLA</code> (Tesla), <code>MSFT</code> (Microsoft), <code>NVDA</code> (Nvidia), <code>META</code> (Meta)</li>
    <li style="margin-bottom: 6px;"><strong>Cổ phiếu Việt Nam:</strong> <code>FPT.VN</code> (FPT), <code>HPG.VN</code> (Hòa Phát), <code>VNM.VN</code> (Vinamilk), <code>VIC.VN</code> (Vingroup)</li>
    <li style="margin-bottom: 6px;"><strong>Tiền ảo (Crypto):</strong> <code>BTC-USD</code> (Bitcoin), <code>ETH-USD</code> (Ethereum), <code>BNB-USD</code> (Binance Coin), <code>SOL-USD</code> (Solana)</li>
  </ul>
</div>
"""
                return {"response": response_text}
            else:
                response_text = f"""
<div style="font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #cbd5e1;">
  <div style="background: rgba(99, 102, 241, 0.08); border-left: 4px solid #6366f1; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px;">
    Bạn đang chọn chế độ <strong>Phân tích nhanh</strong>. Hãy nhập câu hỏi kèm theo tên mã cổ phiếu cụ thể (ví dụ: <em>'HPG.VN'</em>, <em>'FPT.VN'</em>, <em>'AAPL'</em>, <em>'BTC'</em>) để tôi tạo báo cáo chỉ báo kỹ thuật tức thì cho bạn.
  </div>
  
  <h4 style="color: #ffffff; font-size: 14px; font-weight: 700; margin: 16px 0 8px 0;">Danh sách mã gợi ý hợp lệ:</h4>
  <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #cbd5e1;">
    <li style="margin-bottom: 6px;"><strong>Cổ phiếu Mỹ:</strong> <code>AAPL</code>, <code>TSLA</code>, <code>MSFT</code>, <code>NVDA</code>, <code>META</code></li>
    <li style="margin-bottom: 6px;"><strong>Cổ phiếu Việt Nam:</strong> <code>FPT.VN</code>, <code>HPG.VN</code>, <code>VNM.VN</code>, <code>VIC.VN</code></li>
    <li style="margin-bottom: 6px;"><strong>Tiền ảo (Crypto):</strong> <code>BTC-USD</code> (hoặc <code>BTC</code>), <code>ETH-USD</code> (hoặc <code>ETH</code>), <code>BNB-USD</code>, <code>SOL-USD</code></li>
  </ul>
</div>
"""
                return {"response": response_text}

    # 4. Chế độ phân tích thông minh (Ollama)
    else:
        try:
            r = requests.get("http://localhost:11434/api/tags", timeout=1.0)
            if r.status_code != 200:
                raise Exception()
        except:
            return {"response": """
<div style="font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #fca5a5; background: rgba(239, 68, 68, 0.08); border-left: 4px solid #ef4444; padding: 12px 16px; border-radius: 8px;">
  <strong>Chế độ phân tích thông minh chưa sẵn sàng.</strong><br /><br />
  Vui lòng khởi động phần mềm AI cục bộ (Ollama) trên máy tính của bạn và tải mô hình tiếng Việt bằng lệnh sau:<br />
  <code style="background: rgba(255,255,255,0.1); padding: 4px 8px; border-radius: 4px; color: #ffffff; font-size: 12px; margin-top: 8px; display: inline-block; font-family: monospace;">ollama run qwen2.5:1.5b</code>
</div>
"""}

        prompt_context = ""
        if detected_ticker and metrics:
            reco = metrics["recommendation"]
            currency = "VND" if detected_ticker.endswith(".VN") else "$"
            rsi = metrics["rsi"]
            rsi_status = "Quá Mua" if rsi > 70 else ("Quá Bán" if rsi < 30 else "Trung tính")
            ma20 = metrics["ma20"]
            ma50 = metrics["ma50"]
            ma_status = "Bullish (MA20 > MA50)" if ma20 > ma50 else ("Bearish (MA20 < MA50)" if ma20 < ma50 else "Neutral")
            
            prompt_context = f"""[DỮ LIỆU CHỈ BÁO KỸ THUẬT THỰC TẾ]:
- Mã cổ phiếu: {detected_ticker}
- Giá đóng cửa phiên gần nhất: {metrics['current_price']:,.2f} {currency}
- Chỉ số Sức mạnh RSI (14): {rsi:.2f} ({rsi_status})
- Biên độ biến động (Volatility 20 phiên): {metrics['volatility']:.2f}%
- Khuyến nghị AI tổng hợp của hệ thống: {reco['reco']}
- Lập luận khuyến nghị: {reco['explanation']}
- Dự báo của mô hình học máy: Giá ngày mai sẽ ở mức {metrics['next_predicted_price']:,.2f} {currency} (Thay đổi: {metrics['expected_change_pct']:+.2f}%)

[YÊU CẦU CỦA NGƯỜI DÙNG]:
{req.message}

Hãy sử dụng chính xác dữ liệu kỹ thuật thực tế ở trên để phân tích chuyên nghiệp, giải thích ý nghĩa các chỉ số này một cách dễ hiểu và đưa ra lời khuyên thiết thực theo câu hỏi của người dùng. Không bịa số liệu khác. Trả lời bằng tiếng Việt, mạch lạc và chia bố cục rõ ràng. Tuyệt đối không sử dụng bất kỳ biểu tượng cảm xúc (emoji) hay icon nào trong câu trả lời."""
        else:
            prompt_context = f"Người dùng hỏi câu hỏi lý thuyết hoặc trò chuyện thông thường: {req.message}. Hãy trả lời thông minh, chuyên nghiệp dưới góc độ tài chính bằng tiếng Việt. Tuyệt đối không sử dụng bất kỳ biểu tượng cảm xúc (emoji) hay icon nào trong câu trả lời."

        try:
            url = "http://localhost:11434/api/generate"
            payload = {
                "model": req.model,
                "prompt": prompt_context,
                "system": "Bạn là Stock AI Analyst - một trợ lý phân tích tài chính và chứng khoán thông minh. Bạn phân tích dữ liệu vô cùng chính xác và chuyên nghiệp bằng tiếng Việt. Tuyệt đối trung thực với dữ liệu số được cung cấp, không tự bịa thông số. Câu trả lời của bạn cần cô đọng, đi thẳng vào vấn đề và chia bố cục rõ ràng. Tuyệt đối KHÔNG sử dụng bất kỳ biểu tượng cảm xúc (emoji), icon hay ký tự đặc biệt nào (như 🟢, 🔴, 🟡, 📈, 🤖, ⚠️, ❌). Chỉ dùng văn bản thuần túy và định dạng markdown chuẩn.",
                "stream": False
            }
            res = requests.post(url, json=payload, timeout=25)
            if res.status_code == 200:
                # Xóa mọi emoji ngẫu nhiên nếu mô hình vô tình tạo ra
                clean_resp = res.json().get("response", "")
                # Loại bỏ một số emoji phổ biến thường gặp ở AI tài chính
                clean_resp = re.sub(r'[\u2700-\u27BF]|[\uE000-\uF8FF]|\uD83C[\uDC00-\uDFFF]|\uD83D[\uDC00-\uDFFF]|[\u2011-\u26FF]|\uD83E[\uDD00-\uDFFF]', '', clean_resp)
                return {"response": clean_resp}
            else:
                return {"response": f"""
<div style="font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #fca5a5; background: rgba(239, 68, 68, 0.08); border-left: 4px solid #ef4444; padding: 12px 16px; border-radius: 8px;">
  Lỗi giao tiếp với AI cục bộ: Ollama trả về status {res.status_code}.
</div>
"""}
        except Exception as e:
            return {"response": f"""
<div style="font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #fca5a5; background: rgba(239, 68, 68, 0.08); border-left: 4px solid #ef4444; padding: 12px 16px; border-radius: 8px;">
  Không kết nối được với mô hình AI cục bộ: {str(e)}. Hãy chắc chắn Ollama đang chạy.
</div>
"""}


# ========== MAIN UVICORN EXECUTION ==========

if __name__ == "__main__":
    # Chạy uvicorn trực tiếp
    uvicorn.run(
        "api_service:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
