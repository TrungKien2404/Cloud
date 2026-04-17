# ====================================================================
# Dashboard Module - Interactive Visualization
# ====================================================================
# Module: dashboard/dashboard.py
#
# Mục đích: Tạo interactive dashboard sử dụng Streamlit & Plotly
# - Hiển thị giá thực tế vs dự đoán
# - Multi-stock comparison
# - Technical indicators visualization
# - Model performance metrics
# - Real-time updates
#
# ====================================================================

# Install required packages
import subprocess
import sys

def install_packages():
    packages = ['streamlit', 'plotly']
    for package in packages:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', package])

install_packages()

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Configure Streamlit page at global scope (MUST be first)
st.set_page_config(
    page_title="Stock Price Prediction Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

class StockDashboard:
    """
    Interactive dashboard cho stock prediction system
    
    Features:
        - Price history visualization
        - Prediction vs Actual comparison
        - Technical indicators (MA, RSI)
        - Multi-stock analysis
        - Model performance metrics
    """
    
    def __init__(self, page_title: str = "Stock Price Prediction Dashboard"):
        """
        Khởi tạo Dashboard
        
        Args:
            page_title: Title của Streamlit page
        """
        self.page_title = page_title
        self._configure_streamlit()
    
    def _configure_streamlit(self) -> None:
        """Cấu hình Streamlit settings"""
        pass
        
        # Custom CSS
        st.markdown("""
            <style>
                .main {background-color: #f5f5f5;}
                .metric-card {
                    background-color: white;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
            </style>
        """, unsafe_allow_html=True)
    
    # ========== PAGE HEADER ==========
    
    def render_header(self) -> None:
        """Render main header"""
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.title("📈 Stock Price Prediction Dashboard")
            st.markdown("---")
        
        with col2:
            st.metric("Last Updated", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # ========== PRICE ANALYSIS ==========
    
    def plot_price_history(
        self,
        df: pd.DataFrame,
        ticker: str,
        ma_columns: list = None
    ) -> go.Figure:
        """
        Plot giá history với moving averages
        
        Args:
            df: DataFrame chứa dữ liệu
            ticker: Mã cổ phiếu
            ma_columns: Danh sách MA columns (e.g., ['MA10', 'MA20'])
            
        Returns:
            Plotly Figure
        """
        fig = go.Figure()
        
        # Add closing price
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['Close'],
            name='Closing Price',
            mode='lines',
            line=dict(color='blue', width=2)
        ))
        
        # Add moving averages
        if ma_columns:
            colors = ['orange', 'red', 'green']
            for i, ma_col in enumerate(ma_columns):
                if ma_col in df.columns:
                    fig.add_trace(go.Scatter(
                        x=df.index,
                        y=df[ma_col],
                        name=ma_col,
                        mode='lines',
                        line=dict(color=colors[i % len(colors)], width=1, dash='dash')
                    ))
        
        # Update layout
        fig.update_layout(
            title=f"{ticker} - Price History with Moving Averages",
            xaxis_title="Date",
            yaxis_title="Price (USD)",
            hovermode='x unified',
            height=500
        )
        
        return fig
    
    def plot_prediction_vs_actual(
        self,
        df_pred: pd.DataFrame,
        ticker: str
    ) -> go.Figure:
        """
        Plot predicted vs actual prices
        
        Args:
            df_pred: DataFrame với Actual, Predicted columns
            ticker: Mã cổ phiếu
            
        Returns:
            Plotly Figure
        """
        fig = go.Figure()
        
        # Add actual prices
        fig.add_trace(go.Scatter(
            x=df_pred.index,
            y=df_pred['Actual'],
            name='Actual Price',
            mode='lines',
            line=dict(color='blue', width=2)
        ))
        
        # Add predicted prices
        fig.add_trace(go.Scatter(
            x=df_pred.index,
            y=df_pred['Predicted'],
            name='Predicted Price',
            mode='lines+markers',
            line=dict(color='red', width=2),
            marker=dict(size=4)
        ))
        
        # Update layout
        fig.update_layout(
            title=f"{ticker} - Prediction vs Actual",
            xaxis_title="Date",
            yaxis_title="Price (USD)",
            hovermode='x unified',
            height=500
        )
        
        return fig
    
    def plot_prediction_error(self, df_pred: pd.DataFrame) -> go.Figure:
        """
        Plot prediction error over time
        
        Args:
            df_pred: DataFrame với Error column
            
        Returns:
            Plotly Figure
        """
        fig = go.Figure()
        
        # Add error bars
        fig.add_trace(go.Bar(
            x=df_pred.index,
            y=df_pred['Error'],
            name='Absolute Error',
            marker=dict(color='indianred')
        ))
        
        # Add mean error line
        mean_error = df_pred['Error'].mean()
        fig.add_hline(
            y=mean_error,
            annotation_text=f"Mean Error: ${mean_error:.2f}",
            line_dash="dash",
            line_color="green"
        )
        
        fig.update_layout(
            title="Prediction Error Over Time",
            xaxis_title="Date",
            yaxis_title="Absolute Error ($)",
            height=400
        )
        
        return fig
    
    # ========== TECHNICAL INDICATORS ==========
    
    def plot_rsi(self, df: pd.DataFrame, ticker: str) -> go.Figure:
        """
        Plot RSI indicator
        
        Args:
            df: DataFrame chứa RSI column
            ticker: Mã cổ phiếu
            
        Returns:
            Plotly Figure
        """
        fig = go.Figure()
        
        if 'RSI' not in df.columns:
            st.warning("RSI data not available")
            return fig
        
        # Add RSI line
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['RSI'],
            name='RSI(14)',
            mode='lines',
            line=dict(color='purple', width=2)
        ))
        
        # Add overbought/oversold zones
        fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)")
        fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)")
        
        fig.update_layout(
            title=f"{ticker} - RSI (Relative Strength Index)",
            xaxis_title="Date",
            yaxis_title="RSI",
            hovermode='x unified',
            height=400,
            yaxis=dict(range=[0, 100])
        )
        
        return fig
    
    def plot_volatility(self, df: pd.DataFrame, ticker: str) -> go.Figure:
        """
        Plot volatility over time
        
        Args:
            df: DataFrame chứa Volatility column
            ticker: Mã cổ phiếu
            
        Returns:
            Plotly Figure
        """
        fig = go.Figure()
        
        if 'Volatility' not in df.columns:
            st.warning("Volatility data not available")
            return fig
        
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['Volatility'],
            name='Volatility (20-day)',
            mode='lines',
            fill='tozeroy',
            line=dict(color='orange', width=2)
        ))
        
        fig.update_layout(
            title=f"{ticker} - Price Volatility",
            xaxis_title="Date",
            yaxis_title="Volatility",
            hovermode='x unified',
            height=400
        )
        
        return fig
    
    # ========== MULTI-STOCK COMPARISON ==========
    
    def plot_multiple_stocks(
        self,
        stock_data: Dict[str, pd.DataFrame]
    ) -> go.Figure:
        """
        Plot normalized prices của multiple stocks
        
        Args:
            stock_data: Dictionary mapping ticker -> DataFrame
            
        Returns:
            Plotly Figure
        """
        fig = go.Figure()
        
        colors = px.colors.qualitative.Set2
        
        for i, (ticker, df) in enumerate(stock_data.items()):
            # Normalize prices to start at 100
            normalized = (df['Close'] / df['Close'].iloc[0]) * 100
            
            fig.add_trace(go.Scatter(
                x=normalized.index,
                y=normalized,
                name=ticker,
                mode='lines',
                line=dict(color=colors[i % len(colors)], width=2)
            ))
        
        fig.update_layout(
            title="Multi-Stock Price Comparison (Normalized to 100)",
            xaxis_title="Date",
            yaxis_title="Indexed Price",
            hovermode='x unified',
            height=500
        )
        
        return fig
    
    # ========== MODEL METRICS ==========
    
    def display_model_metrics(self, metrics: Dict[str, Dict]) -> None:
        """
        Display model performance metrics
        
        Args:
            metrics: Dictionary mapping model_name -> {rmse, mae, r2}
        """
        st.subheader("📊 Model Performance Comparison")
        
        # Create comparison dataframe
        comparison_data = []
        for model_name, model_metrics in metrics.items():
            comparison_data.append({
                'Model': model_name,
                'RMSE': model_metrics['rmse'],
                'MAE': model_metrics['mae'],
                'R² Score': model_metrics['r2']
            })
        
        df_comparison = pd.DataFrame(comparison_data)
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Best RMSE", f"${df_comparison['RMSE'].min():.4f}")
        with col2:
            st.metric("Best MAE", f"${df_comparison['MAE'].min():.4f}")
        with col3:
            st.metric("Best R² Score", f"{df_comparison['R² Score'].max():.4f}")
        
        # Display table
        st.dataframe(df_comparison, width='stretch')
    
    def plot_metrics_comparison(self, metrics: Dict[str, Dict]) -> None:
        """
        Plot metrics comparison chart
        
        Args:
            metrics: Dictionary mapping model_name -> {rmse, mae, r2}
        """
        comparison_data = []
        for model_name, model_metrics in metrics.items():
            comparison_data.append({
                'Model': model_name,
                'RMSE': model_metrics['rmse'],
                'MAE': model_metrics['mae'],
                'R² Score': model_metrics['r2']
            })
        
        df_comp = pd.DataFrame(comparison_data)
        
        # Plot RMSE comparison
        fig1 = px.bar(df_comp, x='Model', y='RMSE', title='RMSE Comparison (Lower is Better)',
                     color='RMSE', color_continuous_scale='Reds')
        
        # Plot MAE comparison
        fig2 = px.bar(df_comp, x='Model', y='MAE', title='MAE Comparison (Lower is Better)',
                     color='MAE', color_continuous_scale='Oranges')
        
        # Plot R² Score comparison
        fig3 = px.bar(df_comp, x='Model', y='R² Score', title='R² Score Comparison (Higher is Better)',
                     color='R² Score', color_continuous_scale='Greens')
        
        st.plotly_chart(fig1, width='stretch')
        st.plotly_chart(fig2, width='stretch')
        st.plotly_chart(fig3, width='stretch')
    
    # ========== CORRELATION HEATMAP ==========
    
    def plot_correlation_heatmap(self, df: pd.DataFrame) -> None:
        """
        Plot correlation heatmap của features
        
        Args:
            df: DataFrame với numeric columns
        """
        # Select numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        if len(numeric_cols) > 1:
            # Calculate correlation
            corr_matrix = df[numeric_cols].corr()
            
            # Plot heatmap
            fig = px.imshow(
                corr_matrix,
                labels=dict(color="Correlation"),
                x=corr_matrix.columns,
                y=corr_matrix.columns,
                color_continuous_scale="RdBu",
                zmin=-1,
                zmax=1,
                height=600,
                width=600
            )
            
            fig.update_layout(title="Feature Correlation Heatmap")
            st.plotly_chart(fig, width='stretch')
    
    # ========== STATISTICS PANEL ==========
    
    def display_statistics(self, df: pd.DataFrame) -> None:
        """
        Display data statistics
        
        Args:
            df: DataFrame
        """
        st.subheader("📈 Data Statistics")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Latest Close", f"${df['Close'].iloc[-1]:.2f}")
        
        with col2:
            st.metric("52-Week High", f"${df['Close'].max():.2f}")
        
        with col3:
            st.metric("52-Week Low", f"${df['Close'].min():.2f}")
        
        with col4:
            avg_return = df['Daily_Return'].mean() * 100 if 'Daily_Return' in df.columns else 0
            st.metric("Avg Daily Return", f"{avg_return:.2f}%")
        
        with col5:
            volatility = df['Daily_Return'].std() * 100 if 'Daily_Return' in df.columns else 0
            st.metric("Volatility", f"{volatility:.2f}%")


# ========== MAIN EXECUTION ==========

if __name__ == "__main__":
    import os
    import glob
    import joblib
    
    # Initialize dashboard
    dashboard = StockDashboard()
    
    # Render header
    dashboard.render_header()
    
    data_path = "./data/processed/processed_stock_data.parquet"
    if not os.path.exists(data_path):
        data_path = "../data/processed/processed_stock_data.parquet"
        
    try:
        df = pd.read_parquet(data_path)
        
        tickers = df['Ticker'].unique().tolist()
        st.sidebar.title("🎛️ Configurations")
        selected_ticker = st.sidebar.selectbox("Select Stock", tickers)
        
        # Prepare Data for Ticker
        df_ticker = df[df['Ticker'] == selected_ticker].copy()
        if 'Date' in df_ticker.columns:
            df_ticker['Date'] = pd.to_datetime(df_ticker['Date'])
            df_ticker.set_index('Date', inplace=True)
            
        dashboard.display_statistics(df_ticker)
        
        # Create Tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Price Analysis", "🎯 Predictions", "📊 Technical Indicators", "🔗 Multi-Stock", "🧩 Correlations"])
        
        with tab1:
            st.plotly_chart(dashboard.plot_price_history(df_ticker, selected_ticker, ['MA10', 'MA20', 'MA50']), width='stretch')
            
        with tab2:
            st.markdown("### Model Predictions (Target Return)")
            model_dir = "/Workspace/Users/y7prolpvo2018@gmail.com/Cloud/models"
            model_files = glob.glob(os.path.join(model_dir, "*.pkl"))
            if model_files:
                # Tìm xem có file 'best_model_latest.pkl' không để làm mặc định
                latest_model_name = "best_model_latest.pkl"
                default_index = 0
                for i, f_path in enumerate(model_files):
                    if os.path.basename(f_path) == latest_model_name:
                        default_index = i
                        break
                
                selected_model_path = st.selectbox(
                    "Select Trained Model", 
                    model_files, 
                    index=default_index,
                    format_func=lambda x: "✨ Best Model (Latest)" if os.path.basename(x) == latest_model_name else os.path.basename(x)
                )
                # Load model using joblib (now fully compatible after env sync)
                try:
                    model = joblib.load(selected_model_path)
                except Exception as e:
                    st.error(f"Error loading model: {e}")
                    st.stop()
                
                # Clean features like in training
                exclude_cols = ['Ticker', 'FetchDate', 'Target_Price', 'Target_Return']
                features_cols = [c for c in df_ticker.columns if c not in exclude_cols and pd.api.types.is_numeric_dtype(df_ticker[c])]
                
                X = df_ticker[features_cols].fillna(0).values
                y_pred_return = model.predict(X)
                
                # ---------------- NEW FEATURE: TOMORROW'S PREDICTION ----------------
                latest_pred_return = y_pred_return[-1]
                latest_close = df_ticker['Close'].iloc[-1]
                latest_date = df_ticker.index[-1]
                
                # Predict next valid business day
                next_day = latest_date + timedelta(days=1)
                # Skip weekends to find next trading day
                while next_day.weekday() >= 5:  # 5=Saturday, 6=Sunday
                    next_day += timedelta(days=1)
                
                predicted_next_close = latest_close * (1 + latest_pred_return)
                price_change = predicted_next_close - latest_close
                
                # AI Recommendation Logic
                if latest_pred_return >= 0.01:
                    reco_status = "🟢 STRONG BUY"
                    reco_desc = "Mô hình dự đoán cổ phiếu sẽ tăng trưởng tốt (>1%). Khuyến nghị giải ngân."
                    box_color = "#e6ffe6"
                    text_color = "green"
                elif 0 <= latest_pred_return < 0.01:
                    reco_status = "🟡 HOLD / BUY"
                    reco_desc = "Tăng trưởng nhẹ (<1%). Có thể giữ để quan sát hoặc mua thăm dò."
                    box_color = "#ffffe6"
                    text_color = "#b3b300"
                elif -0.01 < latest_pred_return < 0:
                    reco_status = "🟠 HOLD / SELL"
                    reco_desc = "Dự kiến giảm nhẹ. Cần theo dõi thêm hoặc hạ tỷ trọng."
                    box_color = "#fff0e6"
                    text_color = "#ff8000"
                else:
                    reco_status = "🔴 STRONG SELL"
                    reco_desc = "Cảnh báo giảm mạnh (âm >1%). Ưu tiên chốt lời/cắt lỗ bảo toàn vốn."
                    box_color = "#ffe6e6"
                    text_color = "red"
                
                st.markdown(f"###  Phân Tích & Khuyến Nghị Trực Tiếp Cho Ngày Tiếp Theo: {next_day.strftime('%d/%m/%Y')}")
                st.markdown(f"""
                <div style="background-color: {box_color}; padding: 20px; border-radius: 10px; margin-bottom: 25px; border-left: 5px solid {text_color};">
                    <h2 style="color: {text_color}; margin-top: 0;">{reco_status}</h2>
                    <p style="font-size: 16px;">{reco_desc}</p>
                    <div style="display: flex; justify-content: space-between; margin-top: 20px; flex-wrap: wrap;">
                        <div style="margin-right: 20px;">
                            <p style="margin: 0; color: #555;">Chốt Phiên Trước ({latest_date.strftime('%d/%m/%Y')}):</p>
                            <h3 style="margin: 0;">${latest_close:.2f}</h3>
                        </div>
                        <div style="margin-right: 20px;">
                            <p style="margin: 0; color: #555;">Giá Dự Đoán Mới ({next_day.strftime('%d/%m/%Y')}):</p>
                            <h3 style="margin: 0; color: {text_color};">${predicted_next_close:.2f} </h3>
                        </div>
                        <div>
                            <p style="margin: 0; color: #555;">Biến Động Dự Kiến:</p>
                            <h3 style="margin: 0; color: {text_color};">${price_change:+.2f} ({latest_pred_return*100:+.2f}%)</h3>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown("---")
                # --------------------------------------------------------------------
                
                df_pred = pd.DataFrame(index=df_ticker.index)
                df_pred['Actual'] = df_ticker['Target_Return'] if 'Target_Return' in df_ticker.columns else 0
                df_pred['Predicted'] = y_pred_return
                df_pred['Error'] = np.abs(df_pred['Actual'] - df_pred['Predicted'])
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.plotly_chart(dashboard.plot_prediction_vs_actual(df_pred.tail(100), selected_ticker), width='stretch')
                with col2:
                    st.plotly_chart(dashboard.plot_prediction_error(df_pred.tail(100)), width='stretch')
            else:
                st.warning("No trained models found. Run training pipeline first to view predictions.")
                
        with tab3:
            colA, colB = st.columns(2)
            with colA:
                st.plotly_chart(dashboard.plot_rsi(df_ticker, selected_ticker), width='stretch')
            with colB:
                st.plotly_chart(dashboard.plot_volatility(df_ticker, selected_ticker), width='stretch')
                
        with tab4:
            stock_data = {}
            for t in tickers:
                df_t = df[df['Ticker'] == t].copy()
                if 'Date' in df_t.columns:
                    df_t['Date'] = pd.to_datetime(df_t['Date'])
                    df_t.set_index('Date', inplace=True)
                stock_data[t] = df_t
            st.plotly_chart(dashboard.plot_multiple_stocks(stock_data), width='stretch')
            
        with tab5:
            dashboard.plot_correlation_heatmap(df_ticker)
            
    except Exception as e:
        st.error(f"Error loading dashboard data: {str(e)}")
        st.info("Make sure the ETL pipeline has run successfully and generated the processed data.")
