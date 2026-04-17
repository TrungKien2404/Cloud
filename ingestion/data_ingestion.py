# ====================================================================
# Ingestion Module - Data Collection from Yahoo Finance
# ====================================================================
# Module: ingestion/data_ingestion.py
# 
# Mục đích: Lấy dữ liệu giá cổ phiếu từ Yahoo Finance (yfinance)
# - Support multiple tickers (AAPL, TSLA, MSFT)
# - Lưu dữ liệu dạng Parquet (raw data)
# - Xử lý lỗi khi không thể fetch dữ liệu
# - Logging toàn bộ quá trình
#
# ====================================================================

import logging
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os

logger = logging.getLogger(__name__)

class StockDataIngestion:
    """
    Class để download dữ liệu giá cổ phiếu từ Yahoo Finance
    
    Attributes:
        tickers (List[str]): Danh sách mã cổ phiếu cần download
        history_years (int): Số năm dữ liệu lịch sử cần lấy
        raw_data_path (str): Đường dẫn lưu file raw data (parquet)
    """
    
    def __init__(self, tickers: List[str], history_years: int = 5, raw_data_path: str = "./data/raw"):
        """
        Khởi tạo Data Ingestion
        
        Args:
            tickers: List of stock tickers (e.g., ["AAPL", "TSLA", "MSFT"])
            history_years: Number of years of historical data to fetch (default: 5 years)
            raw_data_path: Path to save raw data files
        """
        self.tickers = tickers
        self.history_years = history_years
        self.raw_data_path = raw_data_path
        self._ensure_path_exists()
        
    def _ensure_path_exists(self) -> None:
        """Tạo thư mục nếu chưa tồn tại"""
        os.makedirs(self.raw_data_path, exist_ok=True)
        logger.info(f"Data path ensured: {self.raw_data_path}")
    
    def fetch_stock_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """
        Lấy dữ liệu giá cổ phiếu từ Yahoo Finance
        
        Args:
            ticker (str): Mã cổ phiếu (e.g., "AAPL")
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu OHLCV (Open, High, Low, Close, Volume)
                         Index: DateTime
                         Columns: [Open, High, Low, Close, Volume, Dividends, Stock Splits]
        
        Raises:
            Exception: Nếu fetch data thất bại
        """
        try:
            logger.info(f"Fetching data for {ticker}...")
            
            # Tính toán ngày bắt đầu
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365 * self.history_years)
            
            # Download dữ liệu từ Yahoo Finance
            df = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                progress=False
            )
            
            # Xử lý MultiIndex column ở các phiên bản yfinance mới
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # Thêm cột ticker để dễ tracking
            df['Ticker'] = ticker
            df['FetchDate'] = datetime.now()
            
            logger.info(f"Successfully fetched {len(df)} records for {ticker}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {str(e)}")
            return None
    
    def fetch_all_stocks(self) -> Dict[str, pd.DataFrame]:
        """
        Lấy dữ liệu cho tất cả cổ phiếu
        
        Returns:
            Dict[str, pd.DataFrame]: Dictionary mapping ticker -> DataFrame
        
        Example:
            >>> ingestion = StockDataIngestion(["AAPL", "TSLA"])
            >>> data = ingestion.fetch_all_stocks()
            >>> print(data["AAPL"].head())
        """
        stock_data = {}
        
        for ticker in self.tickers:
            df = self.fetch_stock_data(ticker)
            if df is not None:
                stock_data[ticker] = df
        
        logger.info(f"Fetched data for {len(stock_data)} / {len(self.tickers)} stocks")
        return stock_data
    
    def save_to_parquet(self, data: Dict[str, pd.DataFrame]) -> None:
        """
        Lưu dữ liệu vào file Parquet (raw format)
        
        Args:
            data: Dictionary mapping ticker -> DataFrame
            
        Note:
            - Lưu mỗi ticker vào một file riêng
            - File naming: {ticker}_raw.parquet
            - Timestamp được thêm vào để tracking version
        """
        for ticker, df in data.items():
            try:
                file_path = os.path.join(self.raw_data_path, f"{ticker}_raw.parquet")
                df.to_parquet(file_path)
                logger.info(f"Saved {len(df)} records for {ticker} to {file_path}")
                
            except Exception as e:
                logger.error(f"Error saving data for {ticker}: {str(e)}")
    
    def save_combined_parquet(self, data: Dict[str, pd.DataFrame]) -> None:
        """
        Lưu tất cả dữ liệu vào một file Parquet chung
        
        Args:
            data: Dictionary mapping ticker -> DataFrame
            
        Note:
            - File naming: combined_stock_data.parquet
            - Giúp dễ dàng load toàn bộ dữ liệu một lần
        """
        try:
            # Combine tất cả DataFrames
            combined_df = pd.concat(data.values(), ignore_index=False)
            
            # Reset index để Date trở thành column
            combined_df = combined_df.reset_index()
            
            file_path = os.path.join(self.raw_data_path, "combined_stock_data.parquet")
            combined_df.to_parquet(file_path)
            
            logger.info(f"Saved combined data ({len(combined_df)} records) to {file_path}")
            
        except Exception as e:
            logger.error(f"Error saving combined data: {str(e)}")
    
    def run_ingestion_pipeline(self) -> Dict[str, pd.DataFrame]:
        """
        Chạy toàn bộ pipeline ingestion:
        1. Fetch dữ liệu từ Yahoo Finance
        2. Lưu raw data thành Parquet
        
        Returns:
            Dict[str, pd.DataFrame]: Dữ liệu đã fetch
        """
        logger.info("=" * 70)
        logger.info("Starting Stock Data Ingestion Pipeline")
        logger.info("=" * 70)
        
        # Fetch dữ liệu
        stock_data = self.fetch_all_stocks()
        
        if stock_data:
            # Lưu dữ liệu
            self.save_to_parquet(stock_data)
            self.save_combined_parquet(stock_data)
            logger.info("Ingestion pipeline completed successfully")
        else:
            logger.warning("No data was fetched")
        
        logger.info("=" * 70)
        return stock_data


# ========== HELPER FUNCTIONS ==========

def setup_logging(log_file: Optional[str] = None) -> None:
    """
    Cấu hình logging cho module
    
    Args:
        log_file: Path to log file (optional)
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=logging.INFO,
        format=log_format
    )
    
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(file_handler)


# ========== MAIN EXECUTION ==========

if __name__ == "__main__":
    # Setup logging
    setup_logging()
    
    # Configure tickers and parameters
    TICKERS = ["AAPL", "TSLA", "MSFT"]
    HISTORY_YEARS = 5
    RAW_DATA_PATH = "./data/raw"
    
    # Initialize ingestion
    ingestion = StockDataIngestion(
        tickers=TICKERS,
        history_years=HISTORY_YEARS,
        raw_data_path=RAW_DATA_PATH
    )
    
    # Run pipeline
    stock_data = ingestion.run_ingestion_pipeline()
    
    # Display sample data
    if stock_data:
        for ticker, df in stock_data.items():
            print(f"\n{ticker} data shape: {df.shape}")
            print(df.head())
