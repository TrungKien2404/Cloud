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
    allow_origins=["*"],
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


# ========== MAIN UVICORN EXECUTION ==========

if __name__ == "__main__":
    # Chạy uvicorn trực tiếp
    uvicorn.run(
        "api_service:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
