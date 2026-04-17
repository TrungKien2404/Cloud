# ====================================================================
# ETL Pipeline Module - Data Cleaning & Feature Engineering
# ====================================================================
# Module: etl/etl_pipeline.py
#
# Mục đích: Xử lý và làm sạch dữ liệu, tính toán technical indicators
# - Làm sạch missing values, outliers
# - Feature Engineering:
#   * Moving Average (MA10, MA20, MA50)
#   * Lag features (t-1, t-5, t-10)
#   * RSI (Relative Strength Index)
#   * Daily Returns
#   * Volatility
# - Chuẩn hóa dữ liệu (Normalization/Standardization)
# - Chia train/validation/test sets
#
# ====================================================================

import pandas as pd
import numpy as np
import logging
from typing import Tuple, Dict, Optional
from sklearn.preprocessing import StandardScaler
import os

logger = logging.getLogger(__name__)

class StockETLPipeline:
    """
    Class để xử lý dữ liệu sau khi ingest
    
    Attributes:
        ma_windows (list): Moving average windows [10, 20, 50]
        lag_windows (list): Lag feature windows [1, 5, 10]
        rsi_period (int): RSI indicator period (default: 14)
        test_size (float): Train/Test split ratio (default: 0.2)
    """
    
    def __init__(
        self,
        ma_windows: list = None,
        lag_windows: list = None,
        rsi_period: int = 14,
        test_size: float = 0.2,
        val_size: float = 0.1
    ):
        """
        Khởi tạo ETL Pipeline
        
        Args:
            ma_windows: Moving average windows (default: [10, 20, 50])
            lag_windows: Lag feature windows (default: [1, 5, 10])
            rsi_period: RSI period (default: 14)
            test_size: Test set size (default: 0.2 = 20%)
            val_size: Validation set size (default: 0.1 = 10%)
        """
        self.ma_windows = ma_windows or [10, 20, 50]
        self.lag_windows = lag_windows or [1, 5, 10]
        self.rsi_period = rsi_period
        self.test_size = test_size
        self.val_size = val_size
        self.scaler = StandardScaler()
        
        logger.info("ETL Pipeline initialized")
    
    # ========== DATA CLEANING ==========
    
    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Xử lý missing values
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame với missing values được xử lý
            
        Logic:
            - Forward fill: Giữ giá trị trước đó (phù hợp với time series)
            - Backward fill: Lấp đầu nếu vẫn còn NaN
            - Drop các rows còn lại với NaN
        """
        df_cleaned = df.copy()
        
        # Count missing values before
        missing_before = df_cleaned.isnull().sum().sum()
        if missing_before > 0:
            logger.info(f"Found {missing_before} missing values before cleaning")
            
            # Forward fill (lấy giá trị trước đó)
            df_cleaned = df_cleaned.fillna(method='ffill')
            
            # Backward fill (nếu vẫn còn NaN ở đầu)
            df_cleaned = df_cleaned.fillna(method='bfill')
            
            # Drop remaining NaN rows
            df_cleaned = df_cleaned.dropna()
            
            logger.info(f"Missing values after cleaning: {df_cleaned.isnull().sum().sum()}")
        
        return df_cleaned
    
    def remove_outliers(self, df: pd.DataFrame, column: str = 'Close', threshold: float = 3.0) -> pd.DataFrame:
        """
        Xóa outliers sử dụng Z-score method
        
        Args:
            df: Input DataFrame  
            column: Column to check for outliers (default: 'Close')
            threshold: Z-score threshold (default: 3.0)
            
        Returns:
            DataFrame without outliers
            
        Note:
            - Z-score > 3 được coi là outlier
            - Thường loại bỏ dữ liệu bất thường (gap-up/gap-down quá lớn)
        """
        df_cleaned = df.copy()
        
        if column in df_cleaned.columns:
            z_scores = np.abs((df_cleaned[column] - df_cleaned[column].mean()) / df_cleaned[column].std())
            outliers = z_scores > threshold
            
            n_outliers = outliers.sum()
            if n_outliers > 0:
                logger.info(f"Removed {n_outliers} outliers from {column}")
                df_cleaned = df_cleaned[~outliers]
        
        return df_cleaned
    
    # ========== FEATURE ENGINEERING ==========
    
    def compute_moving_averages(self, df: pd.DataFrame, price_col: str = 'Close') -> pd.DataFrame:
        """
        Tính Moving Average (MA)
        
        Args:
            df: Input DataFrame
            price_col: Price column name (default: 'Close')
            
        Returns:
            DataFrame với các cột MA được thêm vào
            
        Công thức: MA_n = Average of last n closing prices
        
        Features thêm vào:
            - MA10: 10-day moving average
            - MA20: 20-day moving average
            - MA50: 50-day moving average
            
        Sử dụng:
            - Xác định xu hướng (trend)
            - Support/Resistance levels
        """
        df_fe = df.copy()
        
        try:
            for window in self.ma_windows:
                col_name = f'MA{window}'
                df_fe[col_name] = df_fe[price_col].rolling(window=window).mean()
                logger.info(f"Computed {col_name}")
        except Exception as e:
            logger.error(f"Error computing moving averages: {str(e)}")
        
        return df_fe
    
    def compute_lag_features(self, df: pd.DataFrame, price_col: str = 'Close') -> pd.DataFrame:
        """
        Tính Lag Features (giá trong quá khứ)
        
        Args:
            df: Input DataFrame
            price_col: Price column name (default: 'Close')
            
        Returns:
            DataFrame với lag features
            
        Công thức: Lag_n = Price from n days ago
        
        Features thêm vào:
            - Lag1: Giá 1 ngày trước
            - Lag5: Giá 5 ngày trước
            - Lag10: Giá 10 ngày trước
            
        Sử dụng:
            - Auto-regressive models (AR, ARIMA)
            - Capturing temporal dependencies
        """
        df_fe = df.copy()
        
        try:
            for lag in self.lag_windows:
                col_name = f'Lag{lag}'
                df_fe[col_name] = df_fe[price_col].shift(lag)
                logger.info(f"Computed {col_name}")
        except Exception as e:
            logger.error(f"Error computing lag features: {str(e)}")
        
        return df_fe
    
    def compute_rsi(
        self,
        df: pd.DataFrame,
        price_col: str = 'Close',
        period: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Tính RSI (Relative Strength Index) - Technical Indicator
        
        Args:
            df: Input DataFrame
            price_col: Price column name (default: 'Close')
            period: RSI period (default: self.rsi_period = 14)
            
        Returns:
            DataFrame với RSI column
            
        Công thức:
            RSI = 100 - (100 / (1 + RS))
            RS = Avg(Ups) / Avg(Downs)
            
        Giải thích:
            - RSI = 0-100
            - RSI > 70: Overbought (có thể sell)
            - RSI < 30: Oversold (có thể buy)
            - RSI = 50: Neutral
            
        Sử dụng:
            - Xác định momentum
            - Potential reversal points
        """
        df_fe = df.copy()
        
        if period is None:
            period = self.rsi_period
        
        try:
            # Tính daily change
            delta = df_fe[price_col].diff()
            
            # Separate gains and losses
            gains = delta.where(delta > 0, 0)
            losses = -delta.where(delta < 0, 0)
            
            # Calculate average gains and losses
            avg_gain = gains.rolling(window=period).mean()
            avg_loss = losses.rolling(window=period).mean()
            
            # Avoid division by zero
            rs = avg_gain / avg_loss.replace(0, 1)
            rsi = 100 - (100 / (1 + rs))
            
            df_fe['RSI'] = rsi.fillna(50)  # Fill initial NaN with 50 (neutral)
            logger.info(f"Computed RSI with period {period}")
            
        except Exception as e:
            logger.error(f"Error computing RSI: {str(e)}")
        
        return df_fe
    
    def compute_daily_returns(self, df: pd.DataFrame, price_col: str = 'Close') -> pd.DataFrame:
        """
        Tính Daily Returns (phần trăm thay đổi giá)
        
        Args:
            df: Input DataFrame
            price_col: Price column name (default: 'Close')
            
        Returns:
            DataFrame với Daily_Return column
            
        Công thức: Daily_Return = (Price_t - Price_t-1) / Price_t-1
        
        Sử dụng:
            - Risk assessment (volatility)
            - Performance tracking
        """
        df_fe = df.copy()
        
        try:
            df_fe['Daily_Return'] = df_fe[price_col].pct_change()
            df_fe['Daily_Return'] = df_fe['Daily_Return'].fillna(0)
            logger.info("Computed Daily Returns")
        except Exception as e:
            logger.error(f"Error computing daily returns: {str(e)}")
        
        return df_fe
    
    def compute_volatility(self, df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        """
        Tính Volatility (biến động giá)
        
        Args:
            df: Input DataFrame
            window: Rolling window size (default: 20 days)
            
        Returns:
            DataFrame với Volatility column
            
        Công thức: Volatility = Standard Deviation of Returns
        
        Sử dụng:
            - Risk assessment
            - Options pricing
        """
        df_fe = df.copy()
        
        try:
            if 'Daily_Return' not in df_fe.columns:
                df_fe = self.compute_daily_returns(df_fe)
            
            df_fe['Volatility'] = df_fe['Daily_Return'].rolling(window=window).std()
            df_fe['Volatility'] = df_fe['Volatility'].fillna(0)
            logger.info(f"Computed Volatility with window {window}")
        except Exception as e:
            logger.error(f"Error computing volatility: {str(e)}")
        
        return df_fe
    
    # ========== TARGET VARIABLE ==========
    
    def create_target_variable(self, df: pd.DataFrame, price_col: str = 'Close', prediction_days: int = 1) -> pd.DataFrame:
        """
        Tạo target variable cho supervised learning
        
        Args:
            df: Input DataFrame
            price_col: Price column name
            prediction_days: Days ahead to predict (default: 1)
            
        Returns:
            DataFrame với Target column
            
        Logic:
            - Shift price column forward by prediction_days
            - Tạo binary target: 1 nếu giá tăng, 0 nếu giảm
            - HOẶC tạo regression target: giá tương lai
        """
        df_fe = df.copy()
        
        try:
            # Regression target: actual future price
            df_fe['Target_Price'] = df_fe[price_col].shift(-prediction_days)
            
            # Shift target back so it aligns properly
            df_fe['Target_Return'] = (df_fe['Target_Price'] / df_fe[price_col]) - 1
            
            # Drop last rows with NaN targets
            df_fe = df_fe.dropna()
            
            logger.info(f"Created target variable ({prediction_days}-day ahead prediction)")
        except Exception as e:
            logger.error(f"Error creating target variable: {str(e)}")
        
        return df_fe
    
    # ========== DATA PREPROCESSING ==========
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Chuyên biên hoá (Feature Engineering) - Tính toàn bộ features
        
        Args:
            df: Raw input DataFrame
            
        Returns:
            DataFrame với toàn bộ engineered features
            
        Pipeline:
            1. Handle missing values
            2. Remove outliers
            3. Compute moving averages
            4. Compute lag features
            5. Compute RSI
            6. Compute daily returns
            7. Compute volatility
            8. Create target variable
        """
        logger.info("Starting feature engineering...")
        
        # 1. Data cleaning
        df = self.handle_missing_values(df)
        df = self.remove_outliers(df)
        
        # 2. Feature engineering
        df = self.compute_moving_averages(df)
        df = self.compute_lag_features(df)
        df = self.compute_rsi(df)
        df = self.compute_daily_returns(df)
        df = self.compute_volatility(df)
        
        # 3. Target variable
        df = self.create_target_variable(df)
        
        # 4. Drop initial NaN rows (từ MA, Lag, etc.)
        df = df.dropna()
        
        logger.info(f"Feature engineering completed. Final shape: {df.shape}")
        return df
    
    # ========== DATA SPLITTING ==========
    
    def split_train_val_test(
        self,
        df: pd.DataFrame,
        features_cols: Optional[list] = None
    ) -> Tuple[Tuple[np.ndarray, np.ndarray], Tuple[np.ndarray, np.ndarray], Tuple[np.ndarray, np.ndarray]]:
        """
        Chia dữ liệu thành train/validation/test sets
        
        Args:
            df: Full DataFrame
            features_cols: Feature columns to use. If None, auto-select numeric columns
            
        Returns:
            Tuple of ((X_train, y_train), (X_val, y_val), (X_test, y_test))
            
        Proportion:
            - Train: Các còn lại (70%)
            - Validation: 10%
            - Test: 20%
            
        Note:
            - Time-series sequence được maintain (không random shuffle)
            - Quan trọng: Không được leak future data vào train set
        """
        if features_cols is None:
            # Auto-select numeric columns except targets
            exclude_cols = ['Date', 'Ticker', 'FetchDate', 'Target_Price', 'Target_Return']
            features_cols = [col for col in df.columns if df[col].dtype in [np.float64, np.float32, np.int64] 
                            and col not in exclude_cols]
        
        # Prepare features and target
        X = df[features_cols].values
        y = df['Target_Return'].values
        
        # Calculate split indices
        n_samples = len(df)
        test_size_n = int(n_samples * self.test_size)
        val_size_n = int(n_samples * self.val_size)
        train_size_n = n_samples - test_size_n - val_size_n
        
        # Split data (maintaining time order)
        X_train, X_val, X_test = X[:train_size_n], X[train_size_n:train_size_n+val_size_n], X[train_size_n+val_size_n:]
        y_train, y_val, y_test = y[:train_size_n], y[train_size_n:train_size_n+val_size_n], y[train_size_n+val_size_n:]
        
        logger.info(f"Data split - Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
        
        return (X_train, y_train), (X_val, y_val), (X_test, y_test)
    
    def standardize_features(self, X_train, X_val, X_test):
        """
        Chuẩn hóa features sử dụng StandardScaler
        
        Args:
            X_train, X_val, X_test: Feature arrays
            
        Returns:
            Chuẩn hóa X values
            
        Note:
            - Fit scaler trên TRAINING DATA ONLY
            - Transform validation và test data sử dụng fitted scaler
            - Tránh data leakage
        """
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        X_test_scaled = self.scaler.transform(X_test)
        
        logger.info("Features standardized (fitted on training data)")
        return X_train_scaled, X_val_scaled, X_test_scaled
    
    # ========== MAIN PIPELINE ==========
    
    def run_etl_pipeline(
        self,
        df: pd.DataFrame,
        features_cols: Optional[list] = None
    ) -> Dict:
        """
        Chạy toàn bộ ETL pipeline
        
        Args:
            df: Raw data DataFrame
            features_cols: Feature columns (optional)
            
        Returns:
            Dictionary containing:
                - 'processed_df': Full processed DataFrame
                - 'train_data': (X_train, y_train)
                - 'val_data': (X_val, y_val)
                - 'test_data': (X_test, y_test)
                - 'feature_columns': List of feature column names
                - 'scaler': Fitted StandardScaler object
        """
        logger.info("=" * 70)
        logger.info("Starting ETL Pipeline")
        logger.info("=" * 70)
        
        # Step 1: Feature engineering
        processed_df = self.prepare_features(df)
        
        # Step 2: Split train/val/test
        if features_cols is None:
            exclude_cols = ['Date', 'Ticker', 'FetchDate', 'Target_Price', 'Target_Return']
            features_cols = [col for col in processed_df.columns 
                           if processed_df[col].dtype in [np.float64, np.float32, np.int64] 
                           and col not in exclude_cols]
        
        train_data, val_data, test_data = self.split_train_val_test(processed_df, features_cols)
        
        # Step 3: Standardize features
        X_train_scaled, X_val_scaled, X_test_scaled = self.standardize_features(
            train_data[0], val_data[0], test_data[0]
        )
        
        # Update data tuples
        train_data = (X_train_scaled, train_data[1])
        val_data = (X_val_scaled, val_data[1])
        test_data = (X_test_scaled, test_data[1])
        
        logger.info("=" * 70)
        
        return {
            'processed_df': processed_df,
            'train_data': train_data,
            'val_data': val_data,
            'test_data': test_data,
            'feature_columns': features_cols,
            'scaler': self.scaler
        }


# ========== MAIN EXECUTION ==========

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # Example usage
    print("This module should be imported and used in the pipeline")
    print("Example:")
    print("  from etl.etl_pipeline import StockETLPipeline")
    print("  etl = StockETLPipeline()")
    print("  result = etl.run_etl_pipeline(df)")
