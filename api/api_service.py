# ====================================================================
# FastAPI Service - REST API for Stock Predictions
# ====================================================================
# Module: api/api_service.py
#
# Mục đích: Expose predictions thông qua REST API
# - /predict/{ticker}: Dự đoán giá cho một cổ phiếu
# - /data: Lấy processed data
# - /models: List all available models
# - /health: Health check endpoint
#
# Chạy: uvicorn api.api_service:app --reload
#
# ====================================================================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
import pickle
import os

logger = logging.getLogger(__name__)

# ========== PYDANTIC MODELS ==========

class PredictionRequest(BaseModel):
    """Request model cho prediction endpoint"""
    ticker: str
    model_name: Optional[str] = None  # Optional: specify model, default = best
    days_ahead: Optional[int] = 1


class PredictionResponse(BaseModel):
    """Response model cho prediction"""
    ticker: str
    timestamp: str
    predicted_return: float
    confidence: Optional[float] = None
    model_used: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    version: str


class ModelInfo(BaseModel):
    """Model information"""
    name: str
    status: str
    metrics: Dict


class DataPoint(BaseModel):
    """Data point response"""
    date: str
    ticker: str
    close_price: float
    volume: int
    moving_average_10: Optional[float] = None
    moving_average_20: Optional[float] = None
    rsi: Optional[float] = None


# ========== MAIN API ==========

class StockPredictionAPI:
    """
    FastAPI application cho stock prediction service
    """
    
    def __init__(self, model_path: str = "./models", data_path: str = "./data/processed"):
        """
        Initialize API
        
        Args:
            model_path: Path to saved models
            data_path: Path to processed data
        """
        self.app = FastAPI(
            title="Stock Prediction API",
            description="API for stock price prediction using ML models",
            version="1.0.0"
        )
        
        self.model_path = model_path
        self.data_path = data_path
        self.models = {}
        self.best_model = None
        self.best_model_name = None
        self.data = {}
        self.model_metrics = {}
        
        self._setup_middleware()
        self._setup_routes()
        self._load_models()
        
        logger.info("Stock Prediction API initialized")
    
    def _setup_middleware(self) -> None:
        """Setup CORS and other middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self) -> None:
        """Setup all API routes"""
        
        @self.app.get("/health", response_model=HealthResponse)
        def health_check():
            """
            Health check endpoint
            
            Returns:
                HealthResponse with status and timestamp
            """
            return HealthResponse(
                status="healthy",
                timestamp=datetime.now().isoformat(),
                version="1.0.0"
            )
        
        @self.app.get("/models", response_model=List[ModelInfo])
        def list_models():
            """
            List all available models
            
            Returns:
                List of ModelInfo
            """
            result = []
            for model_name in self.models.keys():
                result.append(ModelInfo(
                    name=model_name,
                    status="available" if model_name in self.models else "not_found",
                    metrics=self.model_metrics.get(model_name, {})
                ))
            return result
        
        @self.app.post("/predict", response_model=PredictionResponse)
        def predict(request: PredictionRequest):
            """
            Make prediction for a stock
            
            Args:
                request: PredictionRequest containing ticker and optional model name
                
            Returns:
                PredictionResponse with prediction result
                
            Raises:
                HTTPException: If ticker not found or prediction fails
            """
            try:
                ticker = request.ticker.upper()
                
                # Check if data exists
                if ticker not in self.data:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Data for ticker {ticker} not found"
                    )
                
                # Get latest data point
                df = self.data[ticker]
                latest_features = df.iloc[-1, :-2].values.reshape(1, -1)  # Exclude last 2 columns (target info)
                
                # Select model
                if request.model_name and request.model_name in self.models:
                    model = self.models[request.model_name]
                    model_used = request.model_name
                else:
                    model = self.best_model
                    model_used = self.best_model_name
                
                # Make prediction
                prediction = model.predict(latest_features)[0]
                
                return PredictionResponse(
                    ticker=ticker,
                    timestamp=datetime.now().isoformat(),
                    predicted_return=float(prediction),
                    model_used=model_used
                )
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Prediction error: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Prediction failed: {str(e)}"
                )
        
        @self.app.get("/predict/{ticker}", response_model=PredictionResponse)
        def predict_get(ticker: str):
            """
            Make prediction for a stock (GET endpoint)
            
            Args:
                ticker: Stock ticker symbol
                
            Returns:
                PredictionResponse
            """
            return predict(PredictionRequest(ticker=ticker))
        
        @self.app.get("/data/{ticker}")
        def get_data(ticker: str, days: int = 30):
            """
            Get historical data for a stock
            
            Args:
                ticker: Stock ticker symbol
                days: Number of recent days to return (default: 30)
                
            Returns:
                List of DataPoint objects
            """
            ticker = ticker.upper()
            
            if ticker not in self.data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Data for ticker {ticker} not found"
                )
            
            df = self.data[ticker].tail(days)
            
            result = []
            for idx, row in df.iterrows():
                result.append(DataPoint(
                    date=str(idx),
                    ticker=ticker,
                    close_price=float(row.get('Close', 0)),
                    volume=int(row.get('Volume', 0)),
                    moving_average_10=float(row.get('MA10', None)) if 'MA10' in row else None,
                    moving_average_20=float(row.get('MA20', None)) if 'MA20' in row else None,
                    rsi=float(row.get('RSI', None)) if 'RSI' in row else None
                ))
            
            return result
        
        @self.app.get("/tickers")
        def list_tickers():
            """
            List all available tickers
            
            Returns:
                List of ticker symbols
            """
            return list(self.data.keys())
        
        @self.app.get("/stats/{ticker}")
        def get_statistics(ticker: str):
            """
            Get statistics for a ticker
            
            Args:
                ticker: Stock ticker symbol
                
            Returns:
                Dictionary with statistics
            """
            ticker = ticker.upper()
            
            if ticker not in self.data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Data for ticker {ticker} not found"
                )
            
            df = self.data[ticker]
            close_prices = df['Close']
            
            return {
                'ticker': ticker,
                'latest_price': float(close_prices.iloc[-1]),
                'price_change_24h': float((close_prices.iloc[-1] - close_prices.iloc[-2]) / close_prices.iloc[-2] * 100),
                'price_high_52w': float(close_prices.max()),
                'price_low_52w': float(close_prices.min()),
                'price_avg_30d': float(close_prices.tail(30).mean()),
                'data_points': len(df)
            }
    
    def _load_models(self) -> None:
        """
        Load all saved models từ model directory
        
        Note:
            - Tìm tất cả .pkl files
            - Load vào self.models dictionary
        """
        try:
            if not os.path.exists(self.model_path):
                logger.warning(f"Model path {self.model_path} does not exist")
                return
            
            for file in os.listdir(self.model_path):
                if file.endswith('.pkl'):
                    file_path = os.path.join(self.model_path, file)
                    try:
                        with open(file_path, 'rb') as f:
                            model = pickle.load(f)
                        
                        # Extract model name from filename
                        model_name = file.replace('.pkl', '').replace('_', ' ')
                        self.models[model_name] = model
                        
                        logger.info(f"Loaded model: {model_name}")
                        
                    except Exception as e:
                        logger.error(f"Error loading model {file}: {str(e)}")
            
            # Set best model (first loaded)
            if self.models:
                self.best_model_name = list(self.models.keys())[0]
                self.best_model = self.models[self.best_model_name]
                logger.info(f"Best model set to: {self.best_model_name}")
        
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}")
    
    def load_data(self, ticker: str, file_path: str) -> None:
        """
        Load data từ parquet file
        
        Args:
            ticker: Stock ticker
            file_path: Path to parquet file
        """
        try:
            df = pd.read_parquet(file_path)
            if 'Date' in df.columns:
                df = df.set_index('Date')
            self.data[ticker] = df
            logger.info(f"Loaded data for {ticker}")
        except Exception as e:
            logger.error(f"Error loading data for {ticker}: {str(e)}")
    
    def get_app(self) -> FastAPI:
        """Return FastAPI app"""
        return self.app


# ========== GLOBAL INSTANCE FOR UVICORN ==========

# Setup paths (xử lý case chạy từ thư mục 'api' hoặc thư mục gốc)
base_dir = ".." if os.path.basename(os.getcwd()) == "api" else "."
model_path = os.path.join(base_dir, "models")
data_path = os.path.join(base_dir, "data", "processed")

api = StockPredictionAPI(
    model_path=model_path,
    data_path=data_path
)

# Biến 'app' để uvicorn hook vào qua lệnh 'uvicorn api_service:app'
app = api.get_app()

# Load dữ liệu ngay lúc khởi động (tùy chọn)
for ticker in ["AAPL", "TSLA", "MSFT"]:
    file_path = os.path.join(data_path, "processed_stock_data.parquet")
    if os.path.exists(file_path):
        api.load_data(ticker, file_path)

# ========== MAIN EXECUTION ==========

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run server
    uvicorn.run(
        "api_service:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
