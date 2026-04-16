# ====================================================================
# Machine Learning Model Training Module
# ====================================================================
# Module: model/model_training.py
#
# Mục đích: Training và evaluation của 3 ML models
# - Linear Regression: Baseline model
# - Random Forest: Non-linear, robust model
# - Gradient Boosting: High-performance model
#
# Workflow:
# 1. Train mỗi model trên training data
# 2. Evaluate trên validation data
# 3. So sánh RMSE, MAE, R²
# 4. Chọn best model
# 5. Save best model
#
# ====================================================================

import logging
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import pickle
import os
from datetime import datetime

# ML Libraries
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

logger = logging.getLogger(__name__)

class StockModelTrainer:
    """
    Class để train và evaluate stock prediction models
    
    Attributes:
        models: Dictionary containing model configurations
        best_model: Best performing model
        model_metrics: Performance metrics for all models
    """
    
    def __init__(self, model_save_path: str = "./models"):
        """
        Khởi tạo Model Trainer
        
        Args:
            model_save_path: Path to save trained models
        """
        self.model_save_path = model_save_path
        self.models = {}
        self.trained_models = {}
        self.model_metrics = {}
        self.best_model_name = None
        self.best_model = None
        self.scaler = None
        
        self._ensure_path_exists()
        self._initialize_models()
        
        logger.info("Model Trainer initialized")
    
    def _ensure_path_exists(self) -> None:
        """Tạo thư mục lưu model nếu chưa tồn tại"""
        os.makedirs(self.model_save_path, exist_ok=True)
        logger.info(f"Model save path: {self.model_save_path}")
    
    def _initialize_models(self) -> None:
        """
        Khởi tạo 3 models với configurations tối ưu
        
        Models được khởi tạo:
        1. Linear Regression - Simple baseline
        2. Random Forest - Robust non-linear
        3. Gradient Boosting - High performance
        """
        
        # Model 1: Simple Linear Regression
        # Đơn giản, dễ interpret, nhanh
        self.models['Linear Regression'] = LinearRegression()
        
        # Model 2: Random Forest
        # Robust, xử lý feature interactions, giảm overfitting
        self.models['Random Forest'] = RandomForestRegressor(
            n_estimators=100,        # Số cây (trees)
            max_depth=10,            # Độ sâu tối đa
            min_samples_split=5,     # Tối thiểu samples để split
            min_samples_leaf=2,      # Tối thiểu samples ở leaf
            random_state=42,         # Reproducibility
            n_jobs=-1                # Sử dụng tất cả CPU cores
        )
        
        # Model 3: Gradient Boosting
        # Sequential tree building, thường có performance cao nhất
        self.models['Gradient Boosting'] = GradientBoostingRegressor(
            n_estimators=100,        # Số boosting stages
            learning_rate=0.1,       # Shrinkage rate (0-1)
            max_depth=5,             # Độ sâu tối đa của trees
            min_samples_split=5,     # Tối thiểu samples để split
            min_samples_leaf=2,      # Tối thiểu samples ở leaf
            subsample=0.8,           # Fraction của samples cho training
            random_state=42,         # Reproducibility
            verbose=0
        )
        
        logger.info(f"Initialized {len(self.models)} models: {list(self.models.keys())}")
    
    # ========== TRAINING ==========
    
    def train_model(
        self,
        model_name: str,
        X_train: np.ndarray,
        y_train: np.ndarray
    ) -> object:
        """
        Train một model
        
        Args:
            model_name: Tên model ("Linear Regression", "Random Forest", etc.)
            X_train: Training features (n_samples, n_features)
            y_train: Training targets (n_samples,)
            
        Returns:
            Trained model object
            
        Raises:
            ValueError: Nếu model_name không tồn tại
        """
        if model_name not in self.models:
            raise ValueError(f"Model '{model_name}' not found. Available: {list(self.models.keys())}")
        
        try:
            logger.info(f"Training {model_name}...")
            
            model = self.models[model_name]
            model.fit(X_train, y_train)
            
            self.trained_models[model_name] = model
            
            logger.info(f"{model_name} training completed")
            return model
            
        except Exception as e:
            logger.error(f"Error training {model_name}: {str(e)}")
            raise
    
    def train_all_models(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray
    ) -> Dict:
        """
        Train tất cả 3 models
        
        Args:
            X_train: Training features
            y_train: Training targets
            
        Returns:
            Dictionary mapping model_name -> trained_model
        """
        logger.info("=" * 70)
        logger.info("Starting model training...")
        logger.info("=" * 70)
        
        for model_name in self.models.keys():
            self.train_model(model_name, X_train, y_train)
        
        logger.info("All models trained successfully")
        return self.trained_models
    
    # ========== EVALUATION ==========
    
    def evaluate_model(
        self,
        model_name: str,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict:
        """
        Evaluate một model trên test set
        
        Args:
            model_name: Tên model
            X_test: Test features
            y_test: Test targets
            
        Returns:
            Dictionary với metrics:
                - rmse: Root Mean Squared Error
                - mae: Mean Absolute Error
                - r2: R² Score
                - predictions: Model predictions trên test data
                
        Công thức metrics:
            - RMSE = sqrt(MSE) = sqrt(mean((y_true - y_pred)²))
            - MAE = mean(|y_true - y_pred|)
            - R² = 1 - (SS_res / SS_tot)
        """
        if model_name not in self.trained_models:
            raise ValueError(f"Model '{model_name}' not trained yet")
        
        try:
            logger.info(f"Evaluating {model_name}...")
            
            model = self.trained_models[model_name]
            y_pred = model.predict(X_test)
            
            # Calculate metrics
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            metrics = {
                'rmse': rmse,
                'mae': mae,
                'r2': r2,
                'predictions': y_pred
            }
            
            self.model_metrics[model_name] = metrics
            
            logger.info(f"{model_name} - RMSE: {rmse:.6f}, MAE: {mae:.6f}, R²: {r2:.6f}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error evaluating {model_name}: {str(e)}")
            raise
    
    def evaluate_all_models(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict:
        """
        Evaluate tất cả trained models
        
        Args:
            X_test: Test features
            y_test: Test targets
            
        Returns:
            Dictionary mapping model_name -> metrics_dict
        """
        logger.info("=" * 70)
        logger.info("Model Evaluation")
        logger.info("=" * 70)
        
        for model_name in self.trained_models.keys():
            self.evaluate_model(model_name, X_test, y_test)
        
        return self.model_metrics
    
    # ========== MODEL SELECTION & COMPARISON ==========
    
    def get_best_model(self, metric: str = 'rmse') -> Tuple[str, object, Dict]:
        """
        Chọn best model dựa trên một metric
        
        Args:
            metric: Metric để so sánh ('rmse', 'mae', 'r2')
            
        Returns:
            Tuple (model_name, model_object, metrics_dict)
            
        Note:
            - Với RMSE, MAE: Lower is better
            - Với R²: Higher is better
        """
        if not self.model_metrics:
            raise ValueError("No models evaluated yet")
        
        if metric == 'r2':
            # Higher R² is better
            best_name = max(self.model_metrics, key=lambda x: self.model_metrics[x].get('r2', -np.inf))
        else:
            # Lower RMSE/MAE is better
            best_name = min(self.model_metrics, key=lambda x: self.model_metrics[x].get(metric, np.inf))
        
        self.best_model_name = best_name
        self.best_model = self.trained_models[best_name]
        
        logger.info(f"Best model selected: {best_name} (metric: {metric})")
        
        return best_name, self.best_model, self.model_metrics[best_name]
    
    def print_model_comparison(self) -> None:
        """
        In bảng so sánh tất cả models
        
        Format:
            Model Name | RMSE | MAE | R²
            --------------------------------
        """
        if not self.model_metrics:
            logger.warning("No models evaluated yet")
            return
        
        print("\n" + "=" * 80)
        print("MODEL COMPARISON RESULTS")
        print("=" * 80)
        print(f"{'Model Name':<20} | {'RMSE':>12} | {'MAE':>12} | {'R² Score':>12}")
        print("-" * 80)
        
        for model_name, metrics in self.model_metrics.items():
            print(f"{model_name:<20} | {metrics['rmse']:>12.6f} | {metrics['mae']:>12.6f} | {metrics['r2']:>12.6f}")
        
        print("=" * 80)
        print(f"✓ Best Model: {self.best_model_name} (lowest RMSE)")
        print("=" * 80 + "\n")
    
    # ========== PREDICTION ==========
    
    def predict(self, X: np.ndarray, model_name: Optional[str] = None) -> np.ndarray:
        """
        Dự đoán sử dụng best model hoặc specified model
        
        Args:
            X: Feature array
            model_name: Model name (optional, default: best model)
            
        Returns:
            Predictions array
        """
        if model_name is None:
            if self.best_model is None:
                raise ValueError("No best model selected yet")
            model = self.best_model
        else:
            if model_name not in self.trained_models:
                raise ValueError(f"Model '{model_name}' not trained")
            model = self.trained_models[model_name]
        
        return model.predict(X)
    
    # ========== MODEL PERSISTENCE ==========
    
    def save_model(self, model_name: Optional[str] = None) -> str:
        """
        Lưu trained model vào file
        
        Args:
            model_name: Model name (optional, default: best model)
            
        Returns:
            File path of saved model
        """
        if model_name is None:
            if self.best_model is None:
                raise ValueError("No best model selected")
            model_name = self.best_model_name
            model = self.best_model
        else:
            if model_name not in self.trained_models:
                raise ValueError(f"Model '{model_name}' not trained")
            model = self.trained_models[model_name]
        
        try:
            # Create timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Safe filename
            safe_name = model_name.replace(" ", "_").lower()
            file_path = os.path.join(self.model_save_path, f"{safe_name}_{timestamp}.pkl")
            
            # Save model
            with open(file_path, 'wb') as f:
                pickle.dump(model, f)
            
            logger.info(f"Model '{model_name}' saved to {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")
            raise
            
    def save_best_model_as_latest(self) -> str:
        """
        Lưu mô hình tốt nhất vào một file cố định để dễ dàng sử dụng trong Dashboard.
        File này sẽ bị ghi đè mỗi khi chạy huấn luyện mới.
        
        Returns:
            File path của best model latest
        """
        if self.best_model is None:
            raise ValueError("No best model selected")
            
        try:
            file_path = os.path.join(self.model_save_path, "best_model_latest.pkl")
            
            # Save best model to fixed filename
            with open(file_path, 'wb') as f:
                pickle.dump(self.best_model, f)
                
            logger.info(f"Best model '{self.best_model_name}' saved as latest to {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving best model as latest: {str(e)}")
            raise
    
    def save_all_models(self) -> Dict[str, str]:
        """
        Lưu tất cả trained models
        
        Returns:
            Dictionary mapping model_name -> file_path
        """
        saved_paths = {}
        
        for model_name in self.trained_models.keys():
            path = self.save_model(model_name)
            saved_paths[model_name] = path
        
        return saved_paths
    
    def load_model(self, file_path: str) -> object:
        """
        Load model từ file
        
        Args:
            file_path: Path to model file
            
        Returns:
            Loaded model object
        """
        try:
            with open(file_path, 'rb') as f:
                model = pickle.load(f)
            
            logger.info(f"Model loaded from {file_path}")
            return model
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise
    
    # ========== MAIN PIPELINE ==========
    
    def run_training_pipeline(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict:
        """
        Chạy toàn bộ training pipeline
        
        Args:
            X_train, y_train: Training data
            X_val, y_val: Validation data
            X_test, y_test: Test data
            
        Returns:
            Dictionary containing:
                - 'best_model_name': Best model name
                - 'best_model': Best model object
                - 'model_metrics': All models' metrics
                - 'saved_models': Paths to saved models
        """
        logger.info("=" * 70)
        logger.info("STARTING FULL TRAINING PIPELINE")
        logger.info("=" * 70)
        
        # Step 1: Train all models
        self.train_all_models(X_train, y_train)
        
        # Step 2: Evaluate on validation set first
        logger.info("\n--- Validation Evaluation ---")
        for model_name in self.trained_models.keys():
            self.evaluate_model(model_name, X_val, y_val)
        
        # Step 3: Select best model based on validation RMSE
        best_name, best_model, best_metrics = self.get_best_model(metric='rmse')
        
        # Step 4: Re-evaluate best model on test set
        logger.info("\n--- Final Test Evaluation ---")
        test_metrics = self.evaluate_model(best_name, X_test, y_test)
        
        # Step 5: Print comparison
        self.print_model_comparison()
        
        # Step 6: Save models
        saved_models = self.save_all_models()
        self.save_best_model_as_latest()
        
        logger.info("=" * 70)
        logger.info("TRAINING PIPELINE COMPLETED")
        logger.info("=" * 70)
        
        return {
            'best_model_name': best_name,
            'best_model': best_model,
            'model_metrics': self.model_metrics,
            'saved_models': saved_models,
            'test_metrics': test_metrics
        }


# ========== HELPER FUNCTIONS ==========

def create_predictions_dataframe(
    dates: np.ndarray,
    y_actual: np.ndarray,
    y_pred: np.ndarray,
    ticker: str
) -> pd.DataFrame:
    """
    Tạo DataFrame với actual vs predicted prices
    
    Args:
        dates: Date array
        y_actual: Actual prices/returns
        y_pred: Predicted prices/returns
        ticker: Stock ticker
        
    Returns:
        DataFrame with columns: Date, Ticker, Actual, Predicted, Error
    """
    df_pred = pd.DataFrame({
        'Date': dates,
        'Ticker': ticker,
        'Actual': y_actual,
        'Predicted': y_pred,
        'Error': np.abs(y_actual - y_pred),
        'Error_Pct': np.abs((y_actual - y_pred) / y_actual) * 100
    })
    
    return df_pred


# ========== MAIN EXECUTION ==========

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    print("This module should be imported and used in the pipeline")
    print("Example:")
    print("  from model.model_training import StockModelTrainer")
    print("  trainer = StockModelTrainer()")
    print("  result = trainer.run_training_pipeline(X_train, y_train, X_val, y_val, X_test, y_test)")
